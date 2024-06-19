import os
from os import path
import re
import json
from glob import glob
import base64
from io import BytesIO, StringIO
from time import perf_counter
import PyPDF2
from PIL import Image, ImageDraw, ImageFont
from collections import defaultdict
import datetime
from cryptography.fernet import Fernet
from config.config import config
from dotenv import load_dotenv


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
        print(f"Error reading PDF file: {e}")
        return None


def count_pages(file_path):
    try:
        # Открытие PDF файла
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            return len(reader.pages)

    except Exception as e:
        print(f"Error reading PDF file: {e}")
        return None


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
    with open(config['crypto_env'], 'rb') as file:
        encrypted_data = file.read()
    decrypted_data = f.decrypt(encrypted_data)  # bytes
    decrypted_data_str = decrypted_data.decode('utf-8')  # string
    string_stream = StringIO(decrypted_data_str)
    return string_stream


def postprocessing_openai_response(response: str, show_logs=False) -> str:
    # удаление двойных пробелов и переносов строк
    re_response = re.sub(r'(\s{2,}|\n)', '', response)

    # проверка на json-формат
    try:
        json.loads(re_response)
        if show_logs: print('RECOGNIZED: JSON')
        return re_response
    except json.decoder.JSONDecodeError:
        # поиск ```json (RESPONSE)```
        json_response = re.findall(r'```\s?json\s?(.*)```', re_response, flags=re.DOTALL|re.IGNORECASE)
        if json_response:
            if show_logs: print('RECOGNIZED: ``` json... ```')
            return json_response[0]
        else:
            # поиск текста в {}
            figure_response = re.findall(r'{.*}', re_response, flags=re.DOTALL|re.IGNORECASE)
            if figure_response:
                if show_logs: print('RECOGNIZED: {...}')
                return figure_response[0]
            else:
                print('NOT RECOGNIZED JSON')
                return None


# _________ FOLDERS _________

def rename_files_in_directory(directory_path):
    files = os.listdir(directory_path)  # список файлов в указанной папке

    for filename in files:
        if not os.path.isdir(os.path.join(directory_path, filename)):  # Исключаем директории из списка файлов
            new_filename = filename.replace(" ", "_")
            # new_filename = str(next(counter)) + '.jpg'

            old_filepath = os.path.join(directory_path, filename)
            new_filepath = os.path.join(directory_path, new_filename)
            os.rename(old_filepath, new_filepath)

            print(f"Файл '{filename}' переименован в '{new_filename}'")


def delete_all_files(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")


def create_date_folder_in_check(root_dir):
    """Создать внутри в указанной директории папку с текущей датой-временем и 3 подпапки"""

    # Создаем строку с текущей датой и временем
    folder_name = datetime.datetime.now().strftime("%d-%m-%Y___%H-%M-%S")
    # Создаем папку с указанным именем
    folder_path = os.path.join(root_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    # Создаем подпапки
    subfolders = ["scannedPDFs", "textPDFs", "verified"]
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


# _________ OPENAI _________

def update_assistant(client, assistant_id: str, model: int):
    if model == 3:
        model = 'gpt-3.5-turbo'
    if model == 4:
        model = 'gpt-4o'

    my_updated_assistant = client.beta.assistants.update(
        assistant_id,
        model=model
    )
    return my_updated_assistant


# _________ TEST _________

if __name__ == '__main__':

    load_dotenv(stream=get_stream_dotenv())
    print(os.getenv('OPENAI_API_KEY'))
