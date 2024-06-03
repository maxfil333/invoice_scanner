import os
from os import path
import re
from glob import glob
import base64
from io import BytesIO
from time import perf_counter
import PyPDF2
from PIL import Image, ImageDraw, ImageFont
from collections import defaultdict


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


# _________ IMAGE _________

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


if __name__ == '__main__':
    start = perf_counter()
    # Пример использования
    for file in glob('./*.pdf'):
        print(path.basename(file))
        result = is_scanned_pdf(file)
        if result is True:
            print("Этот PDF файл является сканом документа.")
        elif result is False:
            print("Этот PDF файл является цифровым документом.")
        elif result is None:
            pass
    print(perf_counter() - start)
