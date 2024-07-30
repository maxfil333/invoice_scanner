import os
import re
import io
import sys
import json
import fitz
import shutil
import PyPDF2
import msvcrt
import base64
import openai
import datetime
import pytesseract
import numpy as np
from openai import OpenAI
from typing import Literal
from dotenv import load_dotenv
from io import BytesIO, StringIO
from collections import defaultdict
from cryptography.fernet import Fernet
from PIL import Image, ImageDraw, ImageFont
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

from logger import logger
from config.config import config, NAMES


# _________ ENCODERS _________

# Function to encode the image
def base64_encode_image(image_path: str):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def base64_encode_pil(image: Image.Image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')


# _________ COMMON _________

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


def convert_json_values_to_strings(obj):
    if isinstance(obj, dict):
        return {k: convert_json_values_to_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_json_values_to_strings(i) for i in obj]
    elif obj is None:
        return ""
    else:
        return str(obj)


def get_stream_dotenv():
    """ uses crypto.key to decrypt encrypted environment.
    returns StringIO (for load_dotenv(stream=...)"""

    f = Fernet(config['crypto_key'])
    try:
        with open(config['crypto_env'], 'rb') as file:
            encrypted_data = file.read()
    except FileNotFoundError:
        logger.print(f'Файл {config["crypto_env"]} не найден.')
        if getattr(sys, 'frozen', False):
            msvcrt.getch()
            sys.exit()
        else:
            raise
    decrypted_data = f.decrypt(encrypted_data)  # bytes
    decrypted_data_str = decrypted_data.decode('utf-8')  # string
    string_stream = StringIO(decrypted_data_str)
    return string_stream


def postprocessing_openai_response(response: str, hide_logs=False) -> str:
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


# _________ FOLDERS _________

def rename_files_in_directory(directory_path, hide_logs=False):
    def get_unique_filename(filepath):
        base, ext = os.path.splitext(filepath)
        counter = 1
        while os.path.exists(f"{base}({counter}){ext}"):
            counter += 1
        return f"{base}({counter}){ext}"

    for filename in os.listdir(directory_path):
        # если путь - директория
        if os.path.isdir(os.path.join(directory_path, filename)):
            rename_files_in_directory(os.path.join(directory_path, filename))

        new_filename = re.sub(r'\s+', '_', filename)
        old_filepath = os.path.join(directory_path, filename)
        new_filepath = os.path.join(directory_path, new_filename)
        try:
            os.rename(old_filepath, new_filepath)
        except FileExistsError:
            new_filepath = get_unique_filename(new_filepath)
            os.rename(old_filepath, new_filepath)

        if not hide_logs and old_filepath != new_filepath:
            logger.print(f"Файл '{filename}'переименован в '{new_filename}'")


def delete_all_files(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            logger.print(f"Error deleting file {file_path}: {e}")


def create_date_folder_in_check(root_dir):
    """Создать внутри в указанной директории папку с текущей датой-временем и 3 подпапки"""

    # Создаем строку с текущей датой и временем
    folder_name = datetime.datetime.now().strftime("%d-%m-%Y___%H-%M-%S")
    # Создаем папку с указанным именем
    folder_path = os.path.join(root_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    # Создаем подпапки
    subfolders = [config['NAME_scanned'], config['NAME_text'], config['NAME_verified']]
    for subfolder in subfolders:
        subfolder_path = os.path.join(folder_path, subfolder)
        os.makedirs(subfolder_path, exist_ok=True)
    return folder_path


# _________ IMAGES _________

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


# _________ PDF _________

def is_scanned_pdf(file_path):
    try:
        # Открытие PDF файла
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)
            # Проверка текста на каждой странице
            for page_num in range(num_pages):
                page = reader.pages[page_num]
                text = page.extract_text()
                if text.strip():  # Если текст найден
                    return False

            return True  # Если текст не найден на всех страницах

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


def extract_text_with_fitz(pdf_path):
    document = fitz.open(pdf_path)
    text = ""
    for page_num in range(len(document)):
        page = document.load_page(page_num)  # загружаем страницу
        text += page.get_text()  # извлекаем текст
    return text


def align_pdf_orientation(input_file: str | bytes, output_pdf_path):
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
            if blocks:
                _, _, width, height, _, _, _ = blocks[0]
                if width > height:
                    # Текст ориентирован горизонтально
                    page.set_rotation(0)
                else:
                    # Текст ориентирован вертикально (90 градусов)
                    page.set_rotation(90)
    # Сохраняем PDF-документ с поворотами
    pdf_document.save(output_pdf_path)
    pdf_document.close()


def extract_pages(input_pdf_path, pages_to_keep, output_pdf_path=None):
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


# _________ OPENAI _________

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


# _________ LOCAL _________

def check_sums(dct: dict) -> dict:
    """
    Если количество == '': принимается количество равное 1
    nds_type = "Сверху" / "В т.ч." - выбирается исходя из того как в чеке записана цена (без НДС / с НДС)
    если nds == 0, cum_amount_and_price == total_with_nds, nds_type = "В т.ч."
    """
    logger.print('--- start check_sums ---')

    # _____ Определение ставки НДС _____
    total_with_nds = float(dct[NAMES.total_with]) if dct[NAMES.total_with] != '' else None
    if not total_with_nds:  # Всего к оплате включая НДС
        logger.print('!!! total_with_nds not found !!! total_with_nds = sum("Сумма включая НДС")')
        total_with_nds = sum([x[NAMES.sum_with] for x in dct[NAMES.goods]])

    total_nds = float(dct[NAMES.total_nds]) if dct[NAMES.total_nds] != '' else None
    if total_nds is not None:  # Всего НДС
        total_without_nds = round(total_with_nds - total_nds, 2)
        nds = round((total_nds / total_without_nds) * 100, 2)
    else:
        logger.print('! total_nds not found ! nds = 0; total_nds = 0')
        nds = 0.0
        dct[NAMES.total_nds] = 0.0  # если НДС = 0, то Всего НДС = 0.
        total_without_nds = total_with_nds
    dct['nds (%)'] = nds

    # _____ считаем сумму "сумм с НДС" _____
    cum_sum = 0
    for good_dct in dct[NAMES.goods]:
        try:
            cum_sum += float(good_dct[NAMES.sum_with])
        except:
            logger.print('cum_sum pass')
            pass

    # сравниваем сумму "сумм с НДС" с Всего -> определяем тип "сумм"
    if round(cum_sum, 1) == round(total_with_nds, 1):
        sum_type = 'with'
    elif round(cum_sum, 1) == round(total_without_nds, 1):
        sum_type = 'without'
    else:
        sum_type = 'None'

    # в зависимости от того была ли "сумма" из оригинального json "суммой с НДС" или "суммой без НДС" заполняем поля:
    for good_dct in dct[NAMES.goods]:
        old_sum = round(float(good_dct.pop(NAMES.sum_with)), 2)  # Сумма "включая/не включая" НДС
        good_dct.pop(NAMES.sum_nds)
        if sum_type in ['with', 'None']:
            good_dct['Сумма (без НДС)'] = round(old_sum / (1 + (nds / 100)), 2)
            good_dct['Сумма (с НДС)'] = old_sum
        elif sum_type == 'without':
            good_dct['Сумма (без НДС)'] = old_sum
            good_dct['Сумма (с НДС)'] = round(old_sum * (1 + (nds / 100)), 2)

    # _____ считаем сумму (количество * цена) _____
    cum_amount_and_price = 0
    for good_dct in dct[NAMES.goods]:
        try:
            amount = float(good_dct[NAMES.amount]) if good_dct[NAMES.amount] != '' else 1
            cum_amount_and_price += float(amount) * float(good_dct[NAMES.price])
        except:
            logger.print('cum_amount_and_price pass')
            pass

    # сравниваем сумму (количество * цена) с Всего -> определяем тип "Цены"
    # исходя из того как в чеке записана цена (тип: без НДС / с НДС) выбирается nds_type
    if round(cum_amount_and_price, 1) == round(total_with_nds, 1):  # с НДС -> В т.ч.
        nds_type = 'В т.ч.'
        for good_dct in dct[NAMES.goods]:
            old_price = float(good_dct.pop(NAMES.price))
            good_dct['Цена (без НДС)'] = round(old_price / (1 + (nds / 100)), 2)
            good_dct['Цена (с НДС)'] = old_price
            good_dct['price_type'] = nds_type
    elif round(cum_amount_and_price, 1) == round(total_without_nds, 1):  # без НДС -> Сверху
        nds_type = 'Сверху'
        for good_dct in dct[NAMES.goods]:
            old_price = float(good_dct.pop(NAMES.price))
            good_dct['Цена (без НДС)'] = old_price
            good_dct['Цена (с НДС)'] = round(old_price * (1 + (nds / 100)), 2)
            good_dct['price_type'] = nds_type
    else:
        # Цена неправильно считана (ее вообще нет или она взята из неправильного поля).
        logger.print('Неверно посчитана цена: рассчитываем. Тип такой же, как у sum_type')
        for good_dct in dct[NAMES.goods]:
            amount = float(good_dct[NAMES.amount]) if good_dct[NAMES.amount] != '' else 1
            old_price = float(good_dct.pop(NAMES.price))
            good_dct['Цена (без НДС)'] = round(good_dct['Сумма (без НДС)'] / amount, 2)
            good_dct['Цена (с НДС)'] = round(good_dct['Сумма (с НДС)'] / amount, 2)
            if nds != 0:
                nds_type = 'В т.ч.'
                good_dct['price_type'] = nds_type
            else:
                nds_type = 'Сверху'
                good_dct['price_type'] = nds_type
            good_dct['price_type'] = nds_type

    # _____ сортировка ключей Услуг _____
    new_order = config['services_order']
    for i in dct[NAMES.goods]:  # цикл на случай если dct['Услуги'] == []
        if len(new_order) != len(i):
            logger.print('\n!!! При сортировке ключей в "Услугах" произошла ошибка.\n'
                         'проверьте количество ключей по следующей формуле:\n'
                         'KEYS(config[system_prompt]) + NEWKEYS(local_postprocessing) = config[services_order] !!!\n')
        else:
            ordered_goods = []
            for good_dct in dct[NAMES.goods]:
                one_reordered_goods_dct = {k: good_dct[k] for k in new_order}
                ordered_goods.append(one_reordered_goods_dct)
            dct[NAMES.goods] = ordered_goods
        break

    logger.print('--- end check_sums ---')

    return dct


# _________ CHROMA DATABASE (CREATE CHUNKS AND DB) _________

def create_chunks_from_json(json_path, truncation=200):
    with open(json_path, encoding='utf-8') as f:
        json_ = json.load(f)
        chunks = [f"[{d['id']}] {d['comment'][0:truncation]}" for d in json_]
        return chunks


def chroma_create_db_from_chunks(chroma_path, chunks: list[str]):
    load_dotenv(stream=get_stream_dotenv())
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    embedding_func = OpenAIEmbeddings()

    # Clear out the database first.
    if os.path.exists(chroma_path):
        shutil.rmtree(chroma_path)

    Chroma.from_texts(chunks, embedding_func, persist_directory=chroma_path)


def create_vector_database():
    chunks = create_chunks_from_json(json_path=config['unique_comments_file'])
    chroma_create_db_from_chunks(chroma_path=config['chroma_path'], chunks=chunks)
    print('БАЗА ДАННЫХ СОЗДАНА.')


def chroma_get_relevant(query, chroma_path, embedding_func, k=1, query_truncate=600):
    def get_idx_and_comment(lst):
        idx_comment_tuples = []
        regex = r'\[(\d{1,10})\] (.*)'
        for s in lst:
            match = re.fullmatch(regex, s)
            idx, text = int(match[1]), match[2]
            idx_comment_tuples.append((idx, text))
        return idx_comment_tuples

    db = Chroma(persist_directory=chroma_path, embedding_function=embedding_func)
    retriever = db.as_retriever(search_type='similarity', search_kwargs={"k": k})
    results = retriever.invoke(query[0:query_truncate])  # aka get_relevant_documents
    if len(results) == 0:
        logger.print(f"!!! CHROMA: Unable to find matching results !!!")
        return

    return get_idx_and_comment(list(map(lambda x: x.page_content, results)))


# _________ MAIN_EDIT _________

def pack_folders(dir_path: str = config['IN_FOLDER']):
    """ Упаковка одиночных файлов в папки """
    for entry in os.scandir(dir_path):
        path = os.path.abspath(entry.path)
        if not os.path.isdir(path):  # папки не обрабатываются
            base, ext = tuple(os.path.basename(path).rsplit('.', 1))
            counter = 1
            folder_name = f'{base}({ext})'
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
        logger.print(f'mark_get_required_pages. error reading {pdf_path}')
        return
    valid_pages = list(range(1, num_pages + 1))
    # print('valid_pages', valid_pages)
    regex = r'(.*?)((?:@\d+)+)$'
    basename = os.path.basename(pdf_path)
    name, ext = os.path.splitext(basename)
    pages = re.findall(regex, name)
    if pages:
        pages = [int(x) for x in pages[0][1].split('@') if (x != '' and int(x) in valid_pages)]
    return pages


def mark_get_main_file(folder_path: str) -> str:
    regex = r'(.*?)((?:@\d+)+)$'
    files = os.listdir(folder_path)
    if not files:
        return
    extensions = ['.pdf', '.jpeg', '.jpg', '.png']
    filter_files = [f for f in files if os.path.splitext(f)[-1] in extensions]
    result = [f for f in filter_files if re.fullmatch(regex, os.path.splitext(f)[0])]
    # logger.print(f'mark_get_main_file. detected files: {result}')
    if result:
        return result[0]
    else:
        return files[0]


# _________ TEST _________

if __name__ == '__main__':
    # load_dotenv(stream=get_stream_dotenv())
    # openai.api_key = os.environ.get("OPENAI_API_KEY")
    # embedding_func = OpenAIEmbeddings()

    # print(chroma_get_relevant('Лабораторные исследования',
    #                           config['chroma_path'],
    #                           OpenAIEmbeddings(),
    #                           k=5))

    pass
