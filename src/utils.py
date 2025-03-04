import copy
import os
import re
import io
import time
import glob
import json
import fitz
import shutil
import PyPDF2
import base64
import openai
import hashlib
import difflib
import traceback
import pdfplumber
import pytesseract
import numpy as np
import pandas as pd
from io import BytesIO
from openai import OpenAI
from geotext import GeoText
from datetime import datetime
from dotenv import load_dotenv
from collections import Counter
from collections import defaultdict
from typing import Literal, Optional
from PIL import Image, ImageDraw, ImageFont
from decimal import Decimal, ROUND_HALF_DOWN
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from natasha import Segmenter, NewsEmbedding, NewsNERTagger, Doc

from src.logger import logger
from src.utils_config import get_stream_dotenv
from config.config import config, NAMES, running_params
from src.rotator import main as custom_rotate


class BreakLoop(Exception):
    pass


# _____________________________________________________________________________________________________________ ENCODERS

# Function to encode the image
def base64_encode_image(image_path: str):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def base64_encode_pil(image: Image.Image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')


def calculate_hash(file_path):
    # Инициализация хэш-объекта MD5
    md5_hash = hashlib.md5()

    # Открываем файл в бинарном режиме для чтения
    with open(file_path, "rb") as f:
        # Чтение файла блоками по 4096 байт (можно настроить)
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)

    # Возвращаем хэш-сумму в виде шестнадцатеричной строки
    return md5_hash.hexdigest()


# _______________________________________________________________________________________________________________ COMMON

def time_it(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Функция {func.__name__} выполнялась {end_time - start_time:.6f} секунд")
        return result
    return wrapper


def group_files_by_name(file_list: list[str]) -> dict:
    groups = defaultdict(list)
    pattern = re.compile(r'^(.*?)(?:_TAB\d+\+)?\.(\w{3,4})$')
    for file_name in file_list:
        match = pattern.match(file_name)
        if match:
            basename = match.group(1)
            extension = match.group(2).lower()
            groups[basename, extension].append(file_name)
        else:
            groups[file_name].append(file_name)
    return groups


def convert_json_values_to_strings(obj) -> dict | list | str:
    if isinstance(obj, dict):
        return {k: convert_json_values_to_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_json_values_to_strings(i) for i in obj]
    elif obj is None:
        return ""
    else:
        return str(obj)


def handling_openai_json(response: str, hide_logs=False) -> str | None:
    # удаление двойных пробелов и переносов строк
    re_response = re.sub(r'(\s{2,}|\n)', ' ', response)

    # проверка на json-формат
    try:
        json.loads(re_response)
        if not hide_logs:
            logger.print('RECOGNIZED: JSON')
        return re_response
    except json.decoder.JSONDecodeError:
        # поиск ```json (RESPONSE)```
        json_response = re.findall(r'```\s?json\s?(.*)```', re_response, flags=re.DOTALL | re.IGNORECASE)
        if json_response:
            if not hide_logs:
                logger.print('RECOGNIZED: ``` json... ```')
            return json_response[0]
        else:
            # поиск текста в {}
            figure_response = re.findall(r'{.*}', re_response, flags=re.DOTALL | re.IGNORECASE)
            if figure_response:
                if not hide_logs:
                    logger.print('RECOGNIZED: {...}')
                return figure_response[0]
            else:
                logger.print('NOT RECOGNIZED JSON')
                return None


# _________________________________________________________________________________________________________________ TEXT

def replace_symbols_with_latin(match_obj):
    """ Замена кириллических символов на латиницу """

    text = match_obj.group(0)
    cyrillic_to_latin = {
        'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y',
        'Х': 'X'
    }
    result = ''
    for char in text:
        if char in cyrillic_to_latin:
            result += cyrillic_to_latin[char]
        else:
            result += char
    return result


def replace_container_with_latin(text, container_regex):
    """ Замена в тексте контейнеров на контейнеры латиницей """

    return re.sub(pattern=container_regex,
                  repl=replace_symbols_with_latin,
                  string=text)


def replace_container_with_none(text, container_regex):
    """ Замена в тексте контейнеров на контейнеры латиницей """

    return re.sub(pattern=container_regex,
                  repl='',
                  string=text)


def switch_to_latin(s: str, reverse: bool = False) -> str:
    cyrillic_to_latin = {'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 'Р': 'P', 'С': 'C',
                         'Т': 'T', 'У': 'Y', 'Х': 'X'}
    latin_to_cyrillic = {'A': 'А', 'B': 'В', 'E': 'Е', 'K': 'К', 'M': 'М', 'H': 'Н', 'O': 'О', 'P': 'Р', 'C': 'С',
                         'T': 'Т', 'Y': 'У', 'X': 'Х'}
    new = ''
    if not reverse:
        for letter in s:
            if letter in cyrillic_to_latin:
                new += cyrillic_to_latin[letter]
            else:
                new += letter
    else:
        for letter in s:
            if letter in latin_to_cyrillic:
                new += latin_to_cyrillic[letter]
            else:
                new += letter
    return new


def remove_dates(text: str) -> str:
    date_pattern = r'\b\d{1,2}[-./]\d{1,2}[-./]\d{2,4}\b'
    return re.sub(date_pattern, '', text)


def replace_conos_with_none(text: str, conoses: list[str]) -> str:
    regex = r"|".join(conoses)
    return re.sub(r'\s{2,}', ' ', (re.sub(regex, '', text)))


def replace_ship_with_none(text: str, ship: str) -> str:
    return re.sub(r'\s{2,}', ' ', (re.sub(ship, '', text, flags=re.IGNORECASE)))


def delete_en_loc(text: str) -> str:
    """ deletes en locations with geotext """
    regex = r"|".join(GeoText(text).cities)
    return re.sub(regex, '', text)


segmenter = Segmenter()
ner_tagger = NewsNERTagger(NewsEmbedding())


def delete_NER(text: str, entities: tuple[str] = ('LOC',)) -> str:
    doc = Doc(text)
    doc.segment(segmenter)
    doc.tag_ner(ner_tagger)
    pass_index = []
    loc_spans = [span for span in doc.spans if span.type in entities]
    for d in loc_spans:
        m = int(d.start)
        n = int(d.stop)
        pass_index.extend(list(range(m, n)))
    return "".join([x for i, x in enumerate(text) if i not in pass_index])


# ______________________________________________________________________________________________________________ FOLDERS

def rename_files_in_directory(directory_path: str, max_len: int = 45, hide_logs: bool = False) -> None:
    def get_unique_filename(filepath):
        base, ext = os.path.splitext(filepath)
        counter = 1
        while os.path.exists(f"{base}({counter}){ext}"):
            counter += 1
        return f"{base}({counter}){ext}"

    def sanitize_filename(filename: str) -> str:
        # Заменяем все недопустимые символы на пробелы
        sanitized = re.sub(r'[<>/\"\\|?*#]', ' ', filename)
        # Убираем пробелы в начале и конце строки
        sanitized = sanitized.strip()
        # Заменяем пробелы на "_"
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized

    def crop_filename(filename: str, max_len: int) -> str:
        base, ext = os.path.splitext(filename)
        base = base[-max_len:]
        return base + ext

    def lower_extension(filename: str) -> str:
        base, ext = os.path.splitext(filename)
        return base + ext.lower()

    for filename in os.listdir(directory_path):
        # если путь - директория
        if os.path.isdir(os.path.join(directory_path, filename)):
            rename_files_in_directory(os.path.join(directory_path, filename))

        new_filename = sanitize_filename(filename)
        new_filename = crop_filename(new_filename, max_len=max_len)
        new_filename = lower_extension(new_filename)

        old_filepath = os.path.join(directory_path, filename)
        new_filepath = os.path.join(directory_path, new_filename)
        try:
            os.rename(old_filepath, new_filepath)
        except FileExistsError:
            new_filepath = get_unique_filename(new_filepath)
            os.rename(old_filepath, new_filepath)

        if not hide_logs and old_filepath != new_filepath:
            logger.print(f"Файл '{filename}'переименован в '{new_filename}'")


def delete_all_files(dir_path: str):
    for folder_ in os.scandir(dir_path):
        if folder_.is_dir():
            shutil.rmtree(folder_.path)
        else:
            os.remove(folder_.path)


def create_date_folder_in_check(root_dir):
    """Создать внутри в указанной директории папку с текущей датой-временем и 3 подпапки"""

    # Создаем строку с текущей датой и временем
    folder_name = datetime.now().strftime("%d-%m-%Y___%H-%M-%S")
    # Создаем папку с указанным именем
    folder_path = os.path.join(root_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    # Создаем подпапки
    subfolders = [config['NAME_scanned'], config['NAME_text'], config['NAME_verified']]
    for subfolder in subfolders:
        subfolder_path = os.path.join(folder_path, subfolder)
        os.makedirs(subfolder_path, exist_ok=True)
    return folder_path


def count_extensions(folder: Optional[str] = None, files: Optional[list[str]] = None) -> Optional[dict]:
    """ returns {'.xls': 4, '.pdf': 1, '.xlsx': 12} like dict """
    extensions = {}

    if folder:
        files = glob.glob(fr"{folder}/*")
    elif files:
        files = files
    else:
        return None

    for file in files:
        if not os.path.isdir(file):
            ext = os.path.splitext(file)[-1]
            extensions[ext] = extensions.setdefault(ext, 0) + 1
    return extensions


def extract_excel_text(file_path: str) -> str:
    """Читает первую страницу Excel-файла (счет на оплату) и преобразует данные в текст."""
    file_ext = os.path.splitext(file_path)[-1]
    if file_ext in ['.xlsx', '.xltx']:
        df = pd.read_excel(file_path, sheet_name=0, header=None, engine='openpyxl')  # Читаем без заголовков
    else:
        df = pd.read_excel(file_path, sheet_name=0, header=None, engine='xlrd')  # Читаем без заголовков

    raw_lines = []  # Список всех строк без удаления пустых
    table_start = None  # Индекс начала таблицы

    # Перебираем строки, сохраняя пустые строки для корректного индекса
    for i, row in df.iterrows():
        row_values = [str(cell).strip() if pd.notna(cell) else "" for cell in row]  # Оставляем пустые ячейки
        text_line = " | ".join(row_values).strip(" |")  # Убираем лишние разделители
        raw_lines.append(text_line)

    # Определяем начало таблицы – ищем первую строку, содержащую числа (например, цену, количество)
    for i, row in enumerate(df.itertuples(index=False, name=None)):
        row_values = [str(cell).strip() if pd.notna(cell) else "" for cell in row]
        if any(cell.replace('.', '', 1).isdigit() for cell in row_values if cell):  # Проверяем, есть ли числа
            if len(list(filter(bool, row_values))) >= 5:
                table_start = i
                break

    # Разделяем "Шапку" и "Товары/услуги"
    if table_start is not None:
        header_text = "\n".join(raw_lines[:table_start]).strip()
        table_text = "\n".join(raw_lines[table_start:]).strip()
        formatted_text = f"*****\n{header_text}\n\n*****\n{table_text}"
    else:
        z = '\n'.join(raw_lines)
        formatted_text = f"*****\n\n{z}"

    return formatted_text


# _______________________________________________________________________________________________________________ IMAGES

def add_text_bar(image: str | Image.Image, text, h=75, font_path='verdana.ttf', font_size=50):
    # Открыть изображение
    if isinstance(image, Image.Image):
        pass
    else:
        image = Image.open(image)

    width, height = image.size

    # Создать новое изображение с дополнительной высотой h
    new_image = Image.new('RGB', (width, height + h), (255, 255, 255))
    new_image.paste(image, (0, h))

    # Создать объект для рисования
    draw = ImageDraw.Draw(new_image)

    # Загрузить шрифт
    if font_path:
        font = ImageFont.truetype(font_path, font_size)
    else:
        font = ImageFont.load_default()

    # Определить размер текста с помощью textbbox
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Определить позицию текста по центру полоски
    text_x = (width - text_width) // 2
    text_y = (h - text_height) // 2

    # Добавить текст на полоску
    draw.text((text_x, text_y), text, fill=(0, 0, 0), font=font)

    return new_image


def image_upstanding(img: np.ndarray) -> np.ndarray:
    """ Приведение изображений в вертикальное положение с помощью tesseract"""

    pil_img = Image.fromarray(img)
    osd = pytesseract.image_to_osd(pil_img)
    rotation = int(osd.split("\n")[2].split(":")[1].strip())
    confidence = float(osd.split("\n")[3].split(":")[1].strip())
    # logger.print('rotation:', rotation, 'confidence:', confidence)
    if confidence > 3:
        return np.array(pil_img.rotate(-rotation, expand=True))
    return img


def image_upstanding_and_rotate(image: np.ndarray) -> Image:
    try:
        upstanding = image_upstanding(image)  # 0-90-180-270 rotate
    except:
        upstanding = image
    try:
        rotated = Image.fromarray(custom_rotate(upstanding))  # accurate rotate
    except:
        rotated = upstanding
    if rotated.mode == "RGBA":
        rotated = rotated.convert('RGB')
    return rotated


# __________________________________________________________________________________________________________________ PDF

def is_scanned_pdf(file_path, pages_to_analyse=None) -> Optional[bool]:
    try:
        # Открытие PDF файла
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)
            if pages_to_analyse:
                pages = list(map(lambda x: x - 1, pages_to_analyse))
            else:
                pages = list(range(num_pages))

            # Проверка текста на каждой странице
            scan_list, digit_list = [], []
            for page_num in pages:
                page = reader.pages[page_num]
                text = page.extract_text()
                if text.strip():
                    digit_list.append(page_num)  # Если текст найден
                else:
                    scan_list.append(page_num)  # Если текст не найден

            if not scan_list:
                return False
            elif not digit_list:
                return True
            else:
                logger.print(f'! utils.is_scanned_pdf: mixed pages types in {file_path} !')
                return 0 in scan_list  # определяем по первой странице

    except Exception as e:
        logger.print(f"Error reading PDF file: {e}")
        return None


def count_pages(file_path):
    try:
        # Открытие PDF файла
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            return len(reader.pages)

    except Exception as e:
        logger.print(f"Error reading PDF file: {e}")
        return None


def extract_text_with_fitz(pdf_path) -> list[str]:
    """ return list of texts for every page """

    document = fitz.open(pdf_path)
    texts = []
    for page_num in range(len(document)):
        page = document.load_page(page_num)  # загружаем страницу
        texts.append(page.get_text())  # извлекаем текст
    return texts


def extract_text_with_pdfplumber(pdf_path) -> list[str]:
    """ return list of texts for every page """

    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
    return texts


def align_pdf_orientation(input_file: str | bytes, output_pdf_path: str) -> None:
    """ get input_pdf_path - save to output_pdf_path - returns None """

    if isinstance(input_file, bytes):
        pdf_document = fitz.open("pdf", input_file)
    elif isinstance(input_file, str):
        pdf_document = fitz.open(input_file)
    else:
        print(f'!! align_pdf_orientation input: {input_file} is not valid !!')
        return

    for page_number in range(len(pdf_document)):
        page = pdf_document[page_number]
        # Извлекаем текст со страницы
        text = page.get_text("text")
        # Если текст есть, определяем его ориентацию
        if text:
            # Определяем ориентацию страницы (0, 90, 180, 270 градусов)
            # Основываемся на высоте и ширине bounding box для текста
            blocks = page.get_text("blocks")
            middle = len(blocks) // 2
            if blocks:
                # берем среднее по трем блокам
                _, _, width1, height1, _, _, _ = blocks[0]
                _, _, width2, height2, _, _, _ = blocks[middle]
                _, _, width3, height3, _, _, _ = blocks[-1]
                width = (width1 + width2 + width3) / 3
                height = (height1 + height2 + height3) / 3
                if width > height:
                    # Текст ориентирован горизонтально
                    page.set_rotation(0)
                else:
                    # Текст ориентирован вертикально (90 градусов)
                    page.set_rotation(90)
    # Сохраняем PDF-документ с поворотами
    pdf_document.save(output_pdf_path)
    pdf_document.close()


def extract_pages(input_pdf_path, pages_to_keep, output_pdf_path=None) -> bytes:
    """ Извлечение страниц из pdf. Если output_pdf_path не задан, возвращает байты """

    # Открываем исходный PDF файл
    with open(input_pdf_path, "rb") as input_pdf_file:
        reader = PyPDF2.PdfReader(input_pdf_file)
        writer = PyPDF2.PdfWriter()

        # Извлекаем указанные страницы
        for page_num in pages_to_keep:
            # Нумерация страниц в PyPDF2 начинается с 0
            writer.add_page(reader.pages[page_num - 1])

        if output_pdf_path:
            # Записываем результат в новый PDF файл
            with open(output_pdf_path, "wb") as output_pdf_file:
                writer.write(output_pdf_file)
        else:
            # Создаем байтовый буфер для хранения результата
            output_buffer = io.BytesIO()
            writer.write(output_buffer)

            # Возвращаем байты PDF-файла
            return output_buffer.getvalue()


# _______________________________________________________________________________________________________________ OPENAI

def update_assistant(model: Literal['gpt-4o', 'gpt-4o-mini']):
    load_dotenv(stream=get_stream_dotenv())
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    ASSISTANT_ID = os.environ.get("ASSISTANT_ID")
    client = OpenAI()

    my_updated_assistant = client.beta.assistants.update(
        ASSISTANT_ID,
        model=model
    )
    print(f'model replaced by {model}')

    return my_updated_assistant


def update_assistant_system_prompt(new_prompt: str):
    load_dotenv(stream=get_stream_dotenv())
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    ASSISTANT_ID = os.environ.get("ASSISTANT_ID")
    client = OpenAI()
    client.beta.assistants.update(
        ASSISTANT_ID,
        instructions=new_prompt
    )


# _________________________________________________________________________________________________ LOCAL POSTPROCESSING

@time_it
def extract_goods_gaps(raw_text: str, names: list[str]) -> list[str] | None:
    """ Extract full text gaps between goods """

    # Создаём нормализованный текст без пробельных символов и карту соответствий позиций
    normalized_chars = []
    index_mapping = []  # для каждого символа нормализованного текста запоминаем его индекс в raw_text
    for index, char in enumerate(raw_text):
        if not char.isspace():
            normalized_chars.append(char)
            index_mapping.append(index)
    normalized_text = ''.join(normalized_chars)

    occurrences: list[tuple[int, int]] = []
    search_start = 0  # Начальная позиция поиска в normalized_text

    # Ищем каждое имя (нормализованное – без пробелов) в нормализованном тексте
    for name in names:
        # Берём первые 30 символов имени и удаляем пробельные символы
        short_name = re.sub(r"\s+", "", name[:30])
        # Ищем short_name начиная с search_start
        match = re.search(re.escape(short_name), normalized_text[search_start:])
        if not match:
            return  # если хотя бы одно Наименование не найдено, это ошибка
        match_start = search_start + match.start()
        match_end = search_start + match.end()
        occurrences.append((match_start, match_end))
        search_start = match_end

    # Обработка общего итогового шаблона.
    # В нормализованном тексте пробелов нет, поэтому удаляем "\s" из шаблона.
    total_regex = r"итого|в\sтом\sчисле\sндс|всего|общая\sсумма|т\.ч\.\sндс|без\sналога|без\sндс|сумма\sндс"
    normalized_total_regex = total_regex.replace(r"\s", "")
    total_match = re.search(normalized_total_regex, normalized_text[search_start:], re.IGNORECASE)
    if occurrences:
        last_start, last_end = occurrences[-1]
        if total_match:
            occurrences[-1] = (last_start, search_start + total_match.end())
        else:
            occurrences[-1] = (last_start, len(normalized_text) - 1)

    # Если интервалов несколько, корректируем их так,
    # чтобы граница одного совпадения была началом следующего
    for i in range(len(occurrences) - 1):
        occurrences[i] = (occurrences[i][0], occurrences[i + 1][0])

    # Восстанавливаем отрезки исходного текста по найденным интервалам,
    # преобразуя индексы из нормализованного текста в индексы оригинального
    result = []
    for start_norm, end_norm in occurrences:
        if start_norm < len(index_mapping) and (end_norm - 1) < len(index_mapping):
            start_orig = index_mapping[start_norm]
            end_orig = index_mapping[end_norm - 1] + 1
            result.append(raw_text[start_orig:end_orig])
    return result


def order_goods(dct: dict, new_order: list[str]) -> dict:
    """ Сортировка ключей Услуг """

    if not dct[NAMES.goods]:
        return dct

    ordered_goods = []  # упорядоченные услуги (список словариков)

    for good_dct in dct[NAMES.goods]:
        current_keys = list(good_dct)  # все ключи словаря

        # Ошибочно попавшие в new_order ключи. (есть в new_order, но нет в словаре)
        wrong_keys = set(new_order).difference(set(current_keys))

        # Прочие ключи. (есть в словаре, но нет указания на их порядок в new_order)
        extra_keys = set(current_keys).difference(set(new_order))

        one_reordered_goods_dct = {}  # одна услуга (словарик) с упорядоченными ключами

        # сначала идут по порядку ключи хранящиеся в new_order
        for k in new_order:
            if k not in wrong_keys:
                one_reordered_goods_dct[k] = good_dct[k]

        # далее идут остальные ключи, не отраженные в new_order
        for k in extra_keys:
            one_reordered_goods_dct[k] = good_dct[k]

        ordered_goods.append(one_reordered_goods_dct)

    dct[NAMES.goods] = ordered_goods
    return dct


def insert_key(fixed_k: str, movable_k: str, dct: dict, position: str = 'after') -> dict:
    """Change the order of dictionary keys by inserting movable key after or before fixed key"""

    dct_keys = dct.keys()
    if fixed_k == movable_k or fixed_k not in dct_keys or movable_k not in dct_keys:
        logger.print(f"ERROR: insert_key. keys: {fixed_k}, {movable_k}")
        return dct

    new_order_keys = []
    for k in dct_keys:
        if k == movable_k:  # skip the movable key
            continue
        if position == 'before' and k == fixed_k:  # insert before fixed key
            new_order_keys.append(movable_k)
        new_order_keys.append(k)  # add the current key
        if position == 'after' and k == fixed_k:  # insert after fixed key
            new_order_keys.append(movable_k)

    return {k: dct[k] for k in new_order_keys}


def order_keys(result_string: str) -> str:
    """ Сортировать ключи словаря """
    dct = json.loads(result_string)
    dct = insert_key("Дата счета", "Тип документа", dct, position='after')
    dct = insert_key("Тип документа", "Валюта документа", dct, position='after')
    dct = insert_key("Банковские реквизиты поставщика", NAMES.contract_details, dct, position='before')
    return json.dumps(dct, ensure_ascii=False, indent=4)


def cleanup_empty_fields(dct: dict, fields_names: list[str]):
    """ deletes empty extra keys in goods """
    goods = dct[NAMES.goods]
    for field in fields_names:
        if any([good.get(field) for good in goods]) is False:  # удаляем только если все поля пустые
            for good in goods:
                value = good.get(field)
                if value is not None and value == "":
                    del good[field]
    return dct


# ____________________________________________________________________________________ LOCAL POSTPROCESSING (CHECK_SUMS)
def check_sums(dct: dict) -> dict:
    """
    1. Если количество == '': принимается количество равное 1
    nds_type = "Сверху" / "В т.ч." - выбирается исходя из того как в чеке записана цена (без НДС / с НДС)
    если nds == 0, cum_amount_and_price == total_with_nds, nds_type = "В т.ч.";
    2. Округление до 2 знаков, выполняется только при сравнении величин.
    В конце выполняется для 4 Цен и Сумм (не округляем промежуточные вычисления для большей точности).
    """
    logger.print('--- start check_sums ---')

    # _____ Определение ставки НДС _____

    # 1. Берем ВСЕГО ВКЛЮЧАЯ НДС из счета (если не найдено, суммируем услуги по "Сумма включая НДС")
    total_with_nds = float(dct[NAMES.total_with]) if dct[NAMES.total_with] != '' else None
    if not total_with_nds:
        logger.print('!!! total_with_nds not found !!! total_with_nds = sum("Сумма включая НДС")')
        total_with_nds = sum([float(x[NAMES.sum_with]) for x in dct[NAMES.goods]])

    # 2. Берем ВСЕГО НДС, вычисляем ВСЕГО БЕЗ НДС и ставку НДС
    total_nds = float(dct[NAMES.total_nds]) if dct[NAMES.total_nds] != '' else None
    if total_nds is not None:  # если ВСЕГО НДС найдено
        total_without_nds = round(total_with_nds - total_nds, 2)  # ВСЕГО БЕЗ НДС =  ВСЕГО ВКЛЮЧАЯ НДС - ВСЕГО НДС
        try:
            nds = round((total_nds / total_without_nds) * 100, 2)  # nds = ВСЕГО НДС / ВСЕГО БЕЗ НДС * 100
        except ZeroDivisionError:
            nds = 0
    else:  # если ВСЕГО НДС не найдено: nds = 0, ВСЕГО НДС = 0
        logger.print('! total_nds not found ! nds = 0; total_nds = 0')
        nds = 0.0
        dct[NAMES.total_nds] = 0.0  # если НДС = 0, то Всего НДС = 0.
        total_without_nds = total_with_nds
    dct[NAMES.nds_percent] = nds

    # __________________ Цена -> Цена (с НДС), Цена (без НДС) -> nds_type __________________

    # 1) считаем сумму (количество * цена)
    cum_amount_and_price = 0
    for good_dct in dct[NAMES.goods]:
        try:
            amount = float(good_dct[NAMES.amount]) if good_dct[NAMES.amount] != '' else 1
            cum_amount_and_price += float(amount) * float(good_dct[NAMES.price])
        except:
            pass
    # 2) сравниваем сумму (количество * цена) с ВСЕГО ВКЛЮЧАЯ НДС -> определяем *ТИП ЦЕН*
    # создание вместо старого "Цена", новых Цена (без НДС)/(с НДС)
    # исходя из того как в чеке записана цена (тип: без НДС / с НДС) выбирается nds_type
    if round(cum_amount_and_price, 2) == round(total_with_nds, 2):  # с НДС -> В т.ч.
        nds_type = 'В т.ч.'
        for good_dct in dct[NAMES.goods]:
            old_price = float(good_dct.pop(NAMES.price))
            good_dct[NAMES.price_wo_nds] = old_price / (1 + (nds / 100))
            good_dct[NAMES.price_w_nds] = old_price
            good_dct['price_type'] = nds_type
            del good_dct[NAMES.sum_with]
            del good_dct[NAMES.sum_nds]
    elif round(cum_amount_and_price, 2) == round(total_without_nds, 2):  # без НДС -> Сверху
        nds_type = 'Сверху'
        for good_dct in dct[NAMES.goods]:
            old_price = float(good_dct.pop(NAMES.price))
            good_dct[NAMES.price_wo_nds] = old_price
            good_dct[NAMES.price_w_nds] = old_price * (1 + (nds / 100))
            good_dct['price_type'] = nds_type
            del good_dct[NAMES.sum_with]
            del good_dct[NAMES.sum_nds]
    else:
        # Цена неправильно считана (ее вообще нет или она взята из неправильного поля).
        logger.print('Неверно посчитана цена: рассчитываем ее на основе параметра "Сумма"')

        # __________________ Сумма с НДС -> Сумма (с НДС), Сумма (без НДС) __________________

        # 1) считаем сумму "сумм с НДС"
        sum_of_sums_with_nds = 0
        for good_dct in dct[NAMES.goods]:
            try:
                sum_of_sums_with_nds += float(good_dct[NAMES.sum_with])
            except:
                logger.print('sum_of_sums_with_nds pass')
                pass
        # 2) сравниваем сумму "сумм с НДС" и ВСЕГО ВКЛЮЧАЯ НДС;
        # определяем действительно ли сумма "сумм с НДС" включает в себя НДС (или это сумма "сумм без НДС");
        # если сумма "сумм с НДС" == ВСЕГО ВКЛЮЧАЯ НДС: то действительно включает
        if round(sum_of_sums_with_nds, 1) == round(total_with_nds, 1):
            sum_type = 'with'
        # если сумма "сумм с НДС" == ВСЕГО БЕЗ НДС: сумма "сумм с НДС" на самом деле сумма "сумм без НДС"
        elif round(sum_of_sums_with_nds, 1) == round(total_without_nds, 1):
            sum_type = 'without'
        else:
            sum_type = 'None'

        # Создание из (sum_with='Сумма включая НДС' # 6), (sum_nds='Сумма НДС' # 7) новых полей Сумма (без НДС)/(с НДС)
        # В зависимости от того была ли "сумма" из openai-json "суммой с НДС" или "суммой без НДС" заполняем поля:
        for good_dct in dct[NAMES.goods]:
            old_sum = round(float(good_dct.pop(NAMES.sum_with)), 2)  # Сумма услуги из openai-json
            good_dct.pop(NAMES.sum_nds)
            if sum_type in ['with', 'None']:
                good_dct[NAMES.sum_wo_nds] = old_sum / (1 + (nds / 100))
                good_dct[NAMES.sum_w_nds] = old_sum
            elif sum_type == 'without':
                good_dct[NAMES.sum_wo_nds] = old_sum
                good_dct[NAMES.sum_w_nds] = old_sum * (1 + (nds / 100))

        # __________________ Расчет "Цен (с/без)" на основе "Сумм (с/без)" __________________

        for good_dct in dct[NAMES.goods]:
            if str(good_dct[NAMES.amount]) not in ['', '0']:
                amount = float(good_dct[NAMES.amount])
            else:
                amount = 1
                good_dct[NAMES.amount] = '1'
            del good_dct[NAMES.price]
            good_dct[NAMES.price_wo_nds] = good_dct[NAMES.sum_wo_nds] / amount
            good_dct[NAMES.price_w_nds] = good_dct[NAMES.sum_w_nds] / amount
            if nds != 0:
                nds_type = 'В т.ч.'
            else:
                nds_type = 'Сверху'
            good_dct['price_type'] = nds_type

    # __________________ расчет "Сумм" на основе "Цена" и "Количество" __________________
    for good_dct in dct[NAMES.goods]:
        amount = float(good_dct[NAMES.amount]) if good_dct[NAMES.amount] != '' else 1
        good_dct[NAMES.sum_wo_nds] = good_dct[NAMES.price_wo_nds] * amount
        good_dct[NAMES.sum_w_nds] = good_dct[NAMES.price_w_nds] * amount

    # __________________ округляем все рассчитанные суммы и цены до 2 знаков __________________
    for good_dct in dct[NAMES.goods]:
        good_dct[NAMES.price_wo_nds] = round(good_dct[NAMES.price_wo_nds], 2)
        good_dct[NAMES.price_w_nds] = round(good_dct[NAMES.price_w_nds], 2)
        good_dct[NAMES.sum_wo_nds] = round(good_dct[NAMES.sum_wo_nds], 2)
        good_dct[NAMES.sum_w_nds] = round(good_dct[NAMES.sum_w_nds], 2)

    logger.print('--- end check_sums ---')

    return dct


def propagate_nds(dct: dict):
    nds = dct[NAMES.nds_percent]
    for good_dct in dct[NAMES.goods]:
        good_dct[NAMES.nds_percent] = nds
    dct.pop(NAMES.nds_percent)
    return dct


def is_without_nds(text: str) -> bool:
    """
    checks: nds = 'Без НДС' OR nds = 0.00
    :param text: text data from the invoice
    :return: True if: nds == "Без НДС"
    """

    zero_nds_regex = r'НДС 0%'
    matches = re.findall(zero_nds_regex, text, flags=re.IGNORECASE)
    if len(matches) >= 1:
        logger.print("nds regex matches:", matches)
        return False
    else:
        # Как вариант для избежания попаданий (сумма без ндс) под рег-ку (без\s{0,4}НДС)
        # вынести (без\s{0,4}НДС) в отдельную рег-ку; и если matches от нее больше 2
        # (т.е. БЕЗ НДС в услугах) а не в шапке, то True (тут ошибка только если 1 позиция)
        without_nds_regex = r'без\s{0,4}НДС|НДС не облагается|Без налога \(НДС\)|Услуги не подлежат начислению НДС'
        matches = re.findall(without_nds_regex, text, flags=re.IGNORECASE)
        if len(matches) >= 1:
            logger.print("nds regex matches:", matches)
            return True
        else:
            return False


def is_invoice(text: str) -> bool | None:
    """
    :param text: text of the first page
    :return: True or False or None if no info
    """

    no_regex_list = (r"\bуниверсальный\s{1,2}передаточный\s{1,2}документ|"
                     r"\bсч[её]т-фактура|"
                     r"\bакт.оказанных|"
                     r"\bакт.выполненных|"
                     r"\bакт.приема.передачи|"
                     r"\bакт сдачи|"
                     r"\bакт принципала|"
                     r"\bакт\b№")

    yes_regex_list = (r"invoice|"
                      r"i n v o i c e|"
                      r"\bсч[её]т на оплату|"
                      r"\bсч[её]т-оферта|"
                      r"\bсч[её]т №?\s?.{2,14} от|"
                      r"\bсч[её]т от \d|"
                      r"^сч[её]т$")

    stage1 = re.findall(no_regex_list, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if len(stage1) > 0:
        logger.print(f"IS_INVOICE keywords: {stage1}")
        return False

    stage2 = re.findall(yes_regex_list, text, re.IGNORECASE | re.MULTILINE)
    if len(stage2) > 0:
        logger.print(f"IS_INVOICE keywords: {stage2}")
        return True

    stage3 = re.findall(r"\bакт\b", text, re.IGNORECASE)
    if len(stage3) > 0:
        logger.print(f"IS_INVOICE keywords: {stage3}")
        return False

    stage4 = re.findall(r"\bсч[её]т\b", text, re.IGNORECASE)
    if len(stage4) > 0:
        logger.print(f"IS_INVOICE keywords: {stage4}")
        return True

    logger.print(f"IS_INVOICE keywords: not found")
    return False


def extract_date_range(text: str) -> str:
    pattern_init = (r"(\d{1,2}[./]\d{1,2}(?:[./](?:\d{2}){1,2})?(:?(\s?г\.?)?))"
                    r"(\s{0,2}(-|по|до)\s{0,2}"
                    r"\d{1,2}[./]\d{1,2}[./](?:\d{2}){1,2}(:?(\s?г\.?)?))+")
    pattern_last = pattern_init[0:-1] + r"$"
    pattern_single = r"\d{1,2}[./]\d{1,2}(?:[./](?:\d{2}){1,2})?"

    match = re.search(pattern_init, text)
    if not match:
        return ''

    match_post = re.search(pattern_last, match.group(0))
    if not match_post:
        return ''

    match_single = re.findall(pattern_single, match_post.group(0))
    if not match_single:
        return ''

    try:
        slash_to_dot = [x.replace("/", ".") for x in match_single]

        # 09.08 - 10.08.2025 -> ['09.08.2025', '10.08.2025']
        add_year = [(x + "." + str(max(slash_to_dot, key=len)).split('.')[-1]) if len(x.split('.')) < 3 else x
                    for x in slash_to_dot]

        # 02.07.24 - 08.07.24 -> ['02.07.2024', '08.07.2024']
        add_20_to_year = []
        for date in add_year:
            d, m, year = date.split('.')
            if len(year) == 2:
                year = '20' + year
            new_date = ".".join([d, m, year])
            add_20_to_year.append(new_date)

        # 25.01.25-1.1.26 -> ['25.01.2025', '01.01.2026']
        add_zeros = ['.'.join(map(lambda x: '0' + x if len(x) < 2 else x, i.split('.'))) for i in add_20_to_year]

        return " ".join(add_zeros)
    except Exception:
        logger.print(traceback.format_exc())
        return ''


def DT_processing(dt_list: list[str], logger) -> list[str]:

    dt_list = list(dict.fromkeys(dt_list))
    dt_regex = r'\d{8}/\d{6}/\d{7}'  # регулярка для проверки ДТ

    DT_true = []  # правильные ДТ
    DT_true_indexes = []  # индексы правильных ДТ в result['add_inf...']['ДТ']
    DT_buffer: list[str] = []  # не подошедшие под регулярку строки будут дополнительно проверены

    for dt in dt_list:
        if re.fullmatch(dt_regex, dt):
            DT_true.append(dt)
            DT_true_indexes.append(dt_list.index(dt))
        else:
            DT_buffer.append(dt)

    # проверка спорных ДТ:
    # бывает что ДТ "10131010/270125/5028217,5011336" распознается как ["10131010/270125/5028217","5011336"]
    if DT_true:
        for dt_buffer in DT_buffer:
            if dt_buffer.isdigit() and len(dt_buffer) == 7:
                dt_buffer_index = dt_list.index(dt_buffer)
                if dt_buffer_index != 0:
                    closest_smaller_dt_true_index = max([x for x in DT_true_indexes if x < dt_buffer_index])
                    dt_buffer_base = dt_list[closest_smaller_dt_true_index]
                    if re.fullmatch(dt_regex, dt_buffer_base):
                        dt_buffer_base_parts = dt_buffer_base.split(r'/')
                        if len(dt_buffer_base_parts) == 3:
                            new_dt = dt_buffer_base_parts[0] + r'/' + dt_buffer_base_parts[1] + r'/' + dt_buffer
                            logger.print(f"created DT: {dt_buffer} -> {new_dt}")
                            DT_true.append(new_dt)

    return DT_true


def reports_processing(reports_list: list[str], logger) -> list[str]:

    reports_regex = r'\d{6}-\d{3}-\d{2}'  # регулярка для проверки

    reports_true = []
    reports_true_indexes = []
    reports_buffer = []

    for report in reports_list:
        match = re.search(reports_regex, report)
        if match:
            reports_true.append(match.group())
            reports_true_indexes.append(reports_list.index(report))
        else:
            reports_buffer.append(report)

    # проверка спорных Заключений:
    # бывает что Заключения "059612,059614,059611-015-24" распознается как ["059612", "059614", "059611-015-24"]
    if reports_true:
        for report_buffer in reports_buffer:
            if report_buffer.isdigit() and len(report_buffer) == 6:
                report_buffer_index = reports_list.index(report_buffer)
                if report_buffer_index != len(reports_list) - 1:  # если не последний
                    closest_bigger_dt_true_index = min([x for x in reports_true_indexes if x > report_buffer_index])
                    reports_buffer_base = reports_list[closest_bigger_dt_true_index]
                    if re.fullmatch(reports_regex, reports_buffer_base):
                        reports_buffer_base_parts = reports_buffer_base.split(r'-')
                        if len(reports_buffer_base_parts) == 3:
                            new_report = report_buffer + '-' + reports_buffer_base_parts[1] + '-' + reports_buffer_base_parts[2]
                            logger.print(f"created report: {report_buffer} -> {new_report}")
                            reports_true.append(new_report)
    return reports_true


# _________________________________________________________________________ LOCAL POSTPROCESSING (distribute_conversion)

# Чтобы получить конвертацию в РУБ нужен текущий курс, поэтому передаем конвертацию в ЦУП только! в валюте.
# В ЦУП встречаются случаи, когда конвертация записана как в USD, так и в РУБ.

def update_total(dct: dict, new_services: list):
    total = float(dct[NAMES.total_with])
    total_nds = float(dct[NAMES.total_nds])
    for new_service in new_services:
        total += float(new_service[NAMES.sum_w_nds])
        total_nds += (float(new_service[NAMES.sum_w_nds]) - float(new_service[NAMES.sum_wo_nds]))
    dct[NAMES.total_with] = float(round(total, 2))
    dct[NAMES.total_nds] = float(round(total_nds, 2))


def distribute_conversion(result: str):
    """Distribute conversion by containers or conoses"""

    dct = json.loads(result)

    if float(dct[NAMES.add_info][NAMES.conversion]) == 0:
        return result

    goods = dct[NAMES.goods]

    uniq_containers, uniq_conoses = {}, {}
    for i, good in enumerate(dct[NAMES.goods]):
        local_cont = good.get(NAMES.cont)
        local_conos = good.get(NAMES.local_conos)
        if local_cont:
            uniq_containers.setdefault(local_cont, []).append(i)
        if local_conos:
            uniq_conoses.setdefault(local_conos, []).append(i)
    distribute_type: Literal['single', 'cont', 'conos'] = 'single' if len(uniq_containers) <= 1 and len(
        uniq_conoses) <= 1 \
        else 'cont' if len(uniq_containers) >= len(uniq_conoses) else 'conos'

    conversion = int(dct[NAMES.add_info][NAMES.conversion])
    conversion_service = config['conversion_dict'].get(conversion, config['conversion_dict']['untitled'])
    conversion_value_w_nds = float(dct[NAMES.total_with]) * (conversion / 100)
    conversion_value_wo_nds = (float(dct[NAMES.total_with]) - float(dct[NAMES.total_nds])) * (conversion / 100)
    conversion_services_num = {'single': 1, 'cont': len(uniq_containers), 'conos': len(uniq_conoses)}

    new_conversion_services = []

    if distribute_type == 'single':
        sum_w_nds = round(float(dct[NAMES.total_with]) *
                          (conversion / 100) / conversion_services_num[distribute_type], 2)
        price_w_nds = sum_w_nds

        sum_wo_nds = round((float(dct[NAMES.total_with]) - float(dct[NAMES.total_nds])) *
                           (conversion / 100) / conversion_services_num[distribute_type], 2)
        price_wo_nds = sum_wo_nds

        new_conversion_service: dict = copy.deepcopy(goods[0])
        new_conversion_service.update({
            NAMES.name: 'Конвертация',
            NAMES.good1C: conversion_service,
            NAMES.amount: 1,
            NAMES.unit: 'шт',
            NAMES.init_id: '',
            NAMES.sum_w_nds: sum_w_nds,
            NAMES.price_w_nds: price_w_nds,
            NAMES.sum_wo_nds: sum_wo_nds,
            NAMES.price_wo_nds: price_wo_nds
        })
        new_conversion_services.append(new_conversion_service)
        goods.extend(new_conversion_services)
        update_total(dct, new_conversion_services)
        return json.dumps(dct, indent=4, ensure_ascii=False)

    # {'ABCU1234567': {'Сумма (без НДС)': 6000, 'Сумма (c НДС)': 7000}, 'DFGU1234567': {... }}
    conv_part_for_service = {}
    proportion_indexes_taken = []
    uniq_c = uniq_containers if distribute_type == 'cont' else uniq_conoses
    for c, indexes in uniq_c.items():
        for index in indexes:
            conv_part_for_service.setdefault(c, {})
            conv_part_for_service[c].setdefault(NAMES.sum_w_nds, 0)
            conv_part_for_service[c][NAMES.sum_w_nds] += float(goods[index][NAMES.sum_w_nds])
            conv_part_for_service[c].setdefault(NAMES.sum_wo_nds, 0)
            conv_part_for_service[c][NAMES.sum_wo_nds] += float(goods[index][NAMES.sum_wo_nds])
            proportion_indexes_taken.append(index)

    indexes_without_c = [i for i in range(len(goods)) if i not in proportion_indexes_taken]
    indexes_without_c_sum_w = sum([float(goods[i][NAMES.sum_w_nds]) for i in indexes_without_c])
    indexes_without_c_sum_wo = sum([float(goods[i][NAMES.sum_wo_nds]) for i in indexes_without_c])
    indexes_without_c_sum_w_per_c = round(indexes_without_c_sum_w / len(uniq_c), 2)
    indexes_without_c_sum_wo_per_c = round(indexes_without_c_sum_wo / len(uniq_c), 2)
    for c, d in conv_part_for_service.items():
        conv_part_for_service[c][NAMES.sum_w_nds] += indexes_without_c_sum_w_per_c
        conv_part_for_service[c][NAMES.sum_wo_nds] += indexes_without_c_sum_wo_per_c

    for c, indexes in uniq_c.items():
        new_conversion_service: dict = copy.deepcopy(goods[indexes[0]])
        new_conversion_service.update({
            NAMES.name: 'Конвертация',
            NAMES.good1C: conversion_service,
            NAMES.amount: 1,
            NAMES.unit: 'шт',
            NAMES.init_id: '',
            NAMES.sum_w_nds: round(conv_part_for_service[c][NAMES.sum_w_nds] * float((conversion / 100)), 2),
            NAMES.price_w_nds: round(conv_part_for_service[c][NAMES.sum_w_nds] * float((conversion / 100)), 2),
            NAMES.sum_wo_nds: round(conv_part_for_service[c][NAMES.sum_wo_nds] * float((conversion / 100)), 2),
            NAMES.price_wo_nds: round(conv_part_for_service[c][NAMES.sum_wo_nds] * float((conversion / 100)), 2)
        })

        new_conversion_services.append(new_conversion_service)

    balance_remainders(new_conversion_services, NAMES.sum_w_nds, conversion_value_w_nds, running_params)
    balance_remainders(new_conversion_services, NAMES.sum_wo_nds, conversion_value_wo_nds, running_params)

    goods.extend(new_conversion_services)
    update_total(dct, new_conversion_services)
    return json.dumps(dct, indent=4, ensure_ascii=False)


# _________________________________________________________________________________________________________ TRANSACTIONS

def sort_transactions(transactions: list[str]) -> list:
    def sort_func(x):
        regex = r'(.*) (от) (.*)'
        match = re.fullmatch(regex, x)
        if match:
            match_date = match.group(3).split('|')[0].strip()
            return datetime.strptime(match_date, '%d.%m.%Y').date()
        else:
            return datetime.fromtimestamp(0).date()

    try:
        if transactions:
            transactions = list(set(transactions))
            transactions.sort(key=sort_func, reverse=True)

            # Сделки тб в конец списка
            broker_deals, other_deals = [], []
            for t in transactions:
                if t.startswith('ТБ'):
                    broker_deals.append(t)
                else:
                    other_deals.append(t)
            transactions = other_deals + broker_deals

            return transactions
        else:
            return []
    except:
        return transactions


# ____________________________________________________________________________________________________ BALANCE_REMINDERS

def balance_remainders(data: list[dict], key_name: str, target_sum: int | float, param_file: dict, precision=2) -> None:
    """ Функция для распределения остатков. Используется в конце one_good_split_by... """

    # Вычисляем текущую сумму всех цен в списке, округляя её до нужной точности
    current_sum = round(sum(float(d[key_name]) for d in data), precision)

    # Рассчитываем разницу между целевой суммой и текущей суммой
    difference = round(target_sum - current_sum, precision)
    if not difference:
        return

    param_file['balance_fixes'] = True  # записываем в параметры файла, чтобы потом отключить автобаланс в html

    # Определяем базовую корректировку для каждого элемента, распределяя разницу пропорционально
    n = len(data)  # Количество элементов в списке
    difference_for_decimal = Decimal(str(difference / n))

    # Корректировка для каждого элемента
    adjustment_per_item = float(difference_for_decimal.quantize(Decimal('0.01'), rounding=ROUND_HALF_DOWN))
    # Оставшаяся часть разницы после равного распределения
    remainder = round(difference - (adjustment_per_item * n), precision)

    # Применяем базовую корректировку к каждому элементу, округляя каждый результат до нужной точности
    for i in range(n):
        data[i][key_name] = round(float(data[i][key_name]) + adjustment_per_item, precision)

    # Распределяем оставшийся остаток по последним элементам списка, начиная с конца
    for i in range(int(abs(remainder) * (10 ** precision))):
        idx = n - 1 - i  # Индекс для обратного обхода списка
        # Корректируем элемент, прибавляя либо +0.01, либо -0.01 в зависимости от знака remainder
        data[idx][key_name] = round(float(data[idx][key_name]) + (1 if remainder > 0 else -1) * (10 ** -precision),
                                    precision)


def balance_remainders_intact(result: str) -> str:
    result_dct = json.loads(result)

    goods = result_dct[NAMES.goods]
    init_ids = [good[NAMES.init_id].split("|")[0] for good in goods]
    intact_init_ids = [k for k, v in dict(Counter(init_ids)).items() if v == 1]  # ['1', '2' ...]

    intact_total = float(result_dct[NAMES.total_with])
    intact_total_nds = float(result_dct[NAMES.total_nds])
    intact_goods = []
    for good in goods:
        init_id = good[NAMES.init_id].split("|")[0]
        if init_id in intact_init_ids:
            intact_goods.append(good)
        else:
            intact_total -= float(good[NAMES.sum_w_nds])
            intact_total_nds -= float(good[NAMES.sum_w_nds]) - float(good[NAMES.sum_wo_nds])
    if intact_goods:
        balance_remainders(intact_goods, NAMES.sum_w_nds, intact_total, param_file=running_params)
        balance_remainders(intact_goods, NAMES.sum_wo_nds, intact_total - intact_total_nds, param_file=running_params)
    return json.dumps(result_dct, ensure_ascii=False)


# _________________________________________________________________________________________ TRANSACTIONS (service_split)
def split_one_good(good: dict, loc_field_name: str) -> list[dict]:
    """ Вспомогательная функция для split_by_local_field """

    # Разделение строки по указанному полю
    items = good[loc_field_name].split()  # разделение по local параметру
    num_items = len(items)

    # Исходные суммы позиции
    old_sum_without_tax = float(good[NAMES.sum_wo_nds])
    old_sum_with_tax = float(good[NAMES.sum_w_nds])

    # Разделение количественных данных
    quantity_per_item = float(good[NAMES.amount]) / num_items
    sum_without_tax_per_item = old_sum_without_tax / num_items
    sum_with_tax_per_item = old_sum_with_tax / num_items

    # Создание списка новых объектов
    split_objects = []
    for item in items:
        new_obj = good.copy()  # Копирование исходного объекта

        # INIT local_param
        new_obj[loc_field_name] = item  # Присваивание одного элемента (контейнер/коносамент)
        new_obj[NAMES.amount] = round(quantity_per_item, 2)  # Новое количество
        new_obj[NAMES.sum_wo_nds] = round(sum_without_tax_per_item, 2)  # Новая сумма без НДС
        new_obj[NAMES.sum_w_nds] = round(sum_with_tax_per_item, 2)  # Новая сумма с НДС
        split_objects.append(new_obj)

    # Распределение остатков
    balance_remainders(split_objects, NAMES.sum_w_nds, old_sum_with_tax, param_file=running_params)
    balance_remainders(split_objects, NAMES.sum_wo_nds, old_sum_without_tax, param_file=running_params)

    return split_objects


def split_by_local_field(result: str, loc_field_name: str, was_edited: list) -> tuple[str, list]:
    """ Разделяет услугу если в local_field несколько (конт/кс/закл.) """

    dct = json.loads(result)
    goods = dct[NAMES.goods]
    new_goods = []
    for good in goods:
        init_id = good[NAMES.init_id].split("|")[0]
        if len(good.get(loc_field_name, '').split()) > 1 and init_id not in was_edited:
            _new_goods = split_one_good(good, loc_field_name)
            new_goods.extend(_new_goods)
            was_edited.append(init_id)
        else:
            new_goods.append(good)

    dct[NAMES.goods] = new_goods

    return json.dumps(dct, ensure_ascii=False, indent=4), was_edited


def split_by_global_filed(json_formatted_str: str, global_field: str, local_field: str) -> str:
    def one_split(good: dict, items) -> list[dict]:

        # Исходные суммы позиции
        old_sum_without_tax = float(good[NAMES.sum_wo_nds])
        old_sum_with_tax = float(good[NAMES.sum_w_nds])
        amount = float(good[NAMES.amount])

        # Разделение количественных данных
        quantity_per_item = float(good[NAMES.amount]) / len(items)
        sum_without_tax_per_item = old_sum_without_tax / len(items)
        sum_with_tax_per_item = old_sum_with_tax / len(items)

        # Создание списка новых объектов
        split_objects = []
        for item in items:
            new_obj = good.copy()  # Копирование исходного объекта

            # INIT local_field:
            new_obj[local_field] = item
            new_obj[NAMES.amount] = round(quantity_per_item, 2)  # Новое количество
            new_obj[NAMES.sum_wo_nds] = round(sum_without_tax_per_item, 2)  # Новая сумма без НДС
            new_obj[NAMES.sum_w_nds] = round(sum_with_tax_per_item, 2)  # Новая сумма с НДС
            split_objects.append(new_obj)

        # Распределение остатков
        balance_remainders(split_objects, NAMES.amount, amount, param_file=running_params)
        balance_remainders(split_objects, NAMES.sum_w_nds, old_sum_with_tax, param_file=running_params)
        balance_remainders(split_objects, NAMES.sum_wo_nds, old_sum_without_tax, param_file=running_params)

        return split_objects

    dct = json.loads(json_formatted_str)
    items: list[str] = dct['additional_info'][global_field].split()  # список всех (общих) ДТ/Заключений

    new_goods = []

    # частный алгоритм для ДТ (если есть goods_gaps)
    try:
        if running_params.get(NAMES.goods_gaps) and global_field == NAMES.dt:
            for i, good in enumerate(dct[NAMES.goods]):
                local_dts: list[str] = []
                gap = running_params[NAMES.goods_gaps][i]
                gap = re.sub(r'\s+', '', gap)
                for global_dt in items:
                    global_dt_last_part = global_dt.split(r'/')[-1]  # ищем не полный ДТ, а только последние 7 цифр
                    if global_dt_last_part in gap:
                        local_dts.append(global_dt)
                # Если хотя бы 1 услуга не имеет в своем GAP части ДТ, переходим к общему алгоритму
                if not local_dts:
                    raise BreakLoop
                else:
                    _new_goods = one_split(good=good, items=local_dts)  # позицию разбиваем на len(local_dts) подпозиций
                    new_goods.extend(_new_goods)
    except BreakLoop:
        new_goods = []
        logger.print("--- В одной из услуг не найдено ДТ. Распределяю по всем ДТ ---")

    # общий алгоритм (деление всех услуг на все ДТ)
    if not new_goods:
        for i, good in enumerate(dct[NAMES.goods]):
            _new_goods = one_split(good=good, items=items)  # каждую позицию разбиваем на len(items) подпозиций
            new_goods.extend(_new_goods)

    dct[NAMES.goods] = new_goods
    return json.dumps(dct, ensure_ascii=False, indent=4)


def split_by_dt(json_str: str) -> tuple[str, bool]:
    """ split by global dt """

    DT = json.loads(json_str)['additional_info']['ДТ']
    if DT and len(DT.split()) > 1:  # если есть global ДТ и их несколько
        result = split_by_global_filed(json_str, global_field='ДТ', local_field=NAMES.local_dt)
        return result, True  # was_edited
    else:
        return json_str, False  # если нет, возвращаем без изменений


def combined_split_by_reports(json_str: str, was_edited) -> tuple[str, list]:
    # try to split by local_reports
    start_was_edited = copy.copy(was_edited)
    result, was_edited = split_by_local_field(json_str, loc_field_name=NAMES.local_reports, was_edited=was_edited)
    end_was_edited = copy.copy(was_edited)
    if start_was_edited != end_was_edited:
        return result, was_edited

    # try to split by global reports
    # если все local_reports пустые, сплит по global reports
    if not any([x.get(NAMES.local_reports) for x in json.loads(result)[NAMES.goods]]):
        reports = json.loads(result)[NAMES.add_info][NAMES.reports]
        if reports and len(reports.split()) > 1:  # если есть Заключения и их несколько
            result = split_by_global_filed(json_str, global_field=NAMES.reports, local_field=NAMES.local_reports)
            return result, was_edited

    return json_str, was_edited


# _________ CHROMA DATABASE (CREATE CHUNKS AND DB) _________

def create_chunks_from_json(json_path: str, truncation=200) -> dict:
    with open(json_path, encoding='utf-8') as f:
        json_ = json.load(f)
        chunks = [d['comment'][0:truncation] for d in json_]  # ['chunk1', 'chunk2', 'chunk3']
        metadata_ids = [{'id': d['id']} for d in json_]  # [{'id': 1}, {'id': 2}, {'id': 3}]
        return {'chunks': chunks, 'metadata_ids': metadata_ids}


def chroma_create_db_from_chunks(chroma_path: str, chunks_and_meta: dict, embedding_func) -> None:
    load_dotenv(stream=get_stream_dotenv())
    openai.api_key = os.environ.get("OPENAI_API_KEY")

    try:
        OpenAIEmbeddings(model=config['embedding_model']).embed_query('X')  # testing VPN connection before del CHROMA
        # Clear out the database first.
        if os.path.exists(chroma_path):
            shutil.rmtree(chroma_path)

        chunks, ids = chunks_and_meta['chunks'], chunks_and_meta['metadata_ids']
        Chroma.from_texts(texts=chunks, embedding=embedding_func, metadatas=ids, persist_directory=chroma_path)
    except:
        raise


def create_chunks_and_db(embedding_func) -> None:
    """ create_chunks_from_json + chroma_create_db_from_chunks """
    logger.print("ОБНОВЛЕНИЕ БАЗЫ ДАННЫХ...")
    chunks_and_meta = create_chunks_from_json(json_path=config['unique_comments_file'])
    chroma_create_db_from_chunks(chroma_path=config['chroma_path'],
                                 chunks_and_meta=chunks_and_meta,
                                 embedding_func=embedding_func)
    logger.print('БАЗА ДАННЫХ СОЗДАНА.')


def create_vector_database() -> None:
    load_dotenv(stream=get_stream_dotenv())
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    embedding_func = OpenAIEmbeddings(model=config['embedding_model'])
    create_chunks_and_db(embedding_func)


def chroma_get_relevant(query, chroma_path, embedding_func, k=1, query_truncate=600):
    db = Chroma(persist_directory=chroma_path, embedding_function=embedding_func)

    retriever = db.as_retriever(search_type='similarity', search_kwargs={"k": k})
    results = retriever.invoke(query[0:query_truncate])  # aka get_relevant_documents

    # retriever = db.as_retriever(search_type='similarity_score_threshold',
    #                             search_kwargs={"k": k, "score_threshold": 0.9})
    # results = retriever.invoke(query[0:query_truncate])

    if len(results) == 0:
        logger.print(f"!!! CHROMA: Unable to find matching results !!!")
        return
    return results


def chroma_similarity_search(query, chroma_path, embedding_func, k=1, query_truncate=600) -> list[tuple] | None:
    db = Chroma(persist_directory=chroma_path, embedding_function=embedding_func)
    results = db.similarity_search_with_relevance_scores(query=query[0:query_truncate], k=k)
    if len(results) == 0:
        logger.print(f"!!! CHROMA: Unable to find matching results !!!")
        return
    return results


# _________ ALL SERVICES DIFFLIB SIMILARITY SEARCH (PERFECT MATCH) _________

def perfect_similarity(query: str, data: dict, cutoff: float = 0.95) -> dict | None:
    close_service = difflib.get_close_matches(query, data, n=1, cutoff=cutoff)
    if close_service:
        close_service = close_service[0]  # берем единственный элемент списка
        return {'service': close_service, 'code': data[close_service]}


# _________ MAIN_EDIT _________

def filtering_and_foldering_files(dir_path: str):
    """ Фильтрация по расширению и упаковка одиночных файлов в папки """
    for entry in os.scandir(dir_path):
        path = os.path.abspath(entry.path)
        if not os.path.isdir(path):  # папки пропускаются
            base = os.path.basename(os.path.basename(path))
            ext = os.path.splitext(os.path.basename(path))[-1]
            if ext not in config['valid_ext'] + config['excel_ext']:  # недопустимые расширения пропускаются
                continue
            counter = 1
            folder_name = f'{os.path.splitext(base)[0]}({ext.strip(".")})'
            folder_path = os.path.join(dir_path, folder_name)
            while os.path.exists(folder_path):
                folder_name = f'{base}({ext})({counter})'
                folder_path = os.path.join(dir_path, folder_name)
                counter += 1
            os.makedirs(folder_path, exist_ok=False)
            shutil.move(path, folder_path)


def mark_get_required_pages(pdf_path: str) -> list[int] | None:
    """ gets [2, 3] from '...EDITED\img@2@3.pdf' """

    if os.path.splitext(pdf_path)[-1] != '.pdf':
        return

    num_pages = count_pages(pdf_path)
    if not num_pages:
        return
    valid_pages = list(range(1, num_pages + 1))
    regex = r'(.*?)((?:@\d+)+)$'
    basename = os.path.basename(pdf_path)
    name, ext = os.path.splitext(basename)
    pages = re.findall(regex, name)
    if pages:
        pages = [int(x) for x in pages[0][1].split('@') if (x != '' and int(x) in valid_pages)]
    return sorted(list(set(pages)))


def mark_get_main_file(dir_path: str) -> str | None:
    # all files in dir
    files = os.listdir(dir_path)
    if not files:
        return

    # pdf, jpg or png files
    valid_files = [f for f in files if os.path.splitext(f)[-1] in config['valid_ext']]

    # 1. Главный файл .pdf или .jpg/.png + содержит @1 или @@1 или @
    regex1 = r'(.*?)(:?@)?((?:@\d+)+)$'  # ...@1@2@3 или ...@@1@2@3
    regex2 = r'(.*?)((?:@))$'  # ...@
    regexes = [regex1, regex2]
    for regex in regexes:
        valid_files_matched = [f for f in valid_files if re.fullmatch(regex, os.path.splitext(f)[0])]
        if valid_files_matched:
            return valid_files_matched[0]

    if valid_files:  # 2. Главный файл .pdf или .jpg/.png
        return valid_files[0]
    else:  # 3. Главный файл - случайный
        return files[0]


def mark_get_title(pdf_path: str) -> int | None:
    regex = r'(.*?)(:?@)?((?:@\d+)+)$'
    basename = os.path.basename(pdf_path)
    name, ext = os.path.splitext(basename)
    match = re.fullmatch(regex, name)
    if match:
        title_group = match.group(2)
        if title_group:
            main_group = match.group(3)
            title_page = int(main_group.strip('@').split('@')[0])
            return title_page


# _________ TEST _________

if __name__ == '__main__':
    create_vector_database()
    pass
