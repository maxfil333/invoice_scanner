import os
import sys
import re
import numpy as np
import pytesseract
from PIL import Image
from time import perf_counter
from img2table.document import Image as IMAGE

from src.preprocessor import main as main_preprocessor


def extract_text_from_image(image: np.ndarray, psm=3):
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS
        pytesseract.pytesseract.tesseract_cmd = os.path.join(bundle_dir, 'Tesseract-OCR', 'tesseract.exe')

    config = f'--psm {psm}'  # --psm 4 --oem 3
    text = pytesseract.image_to_string(image, config=config, lang='rus+eng')
    return text


def define_tables_on_bboxes(img_path: str) -> dict:
    img_tables = IMAGE(src=img_path).extract_tables()  # детекция "пустых" таблиц без содержимого
    # print(f'1) найдено пустых таблиц: {len(img_tables)}')
    image = Image.fromarray(main_preprocessor(img_path))

    tables_and_marks = {'title': None, 'shipment': None, 'untitled': []}
    for table in img_tables:
        bbox = table.bbox
        x1, y1, x2, y2 = bbox.x1, bbox.y1, bbox.x2, bbox.y2
        cropped = image.crop((x1, y1, x2, y2))
        table_content = extract_text_from_image(np.array(cropped))

        shipment_regex = r'\b(Сумма|Цена|Всего|Итого|Услуг\w?|Товары|Товара)\b'
        title_regex = r'\b(ИНН|КПП|БИК|получатель|получателя|(?:408\d{17}|407\d{17}|406\d{17}|405\d{17})|(?:30101\d{15}))\b'

        if bool(re.search(shipment_regex, table_content, flags=re.IGNORECASE)) and tables_and_marks['shipment'] != '#':
            if tables_and_marks['shipment'] is None:
                tables_and_marks['shipment'] = table
            else:
                tables_and_marks['untitled'].extend([tables_and_marks['shipment'], table])
                tables_and_marks['shipment'] = "#"
        elif bool(re.search(title_regex, table_content, flags=re.IGNORECASE)) and tables_and_marks['title'] != '#':
            if tables_and_marks['title'] is None:
                tables_and_marks['title'] = table
            else:
                tables_and_marks['untitled'].extend([tables_and_marks['title'], table])
                tables_and_marks['title'] = '#'
        else:
            tables_and_marks['untitled'].extend([table])

    for k, v in tables_and_marks.items():
        if v == "#":
            tables_and_marks[k] = None

    return tables_and_marks


def resize_image_to_width(image, target_width):
    width_percent = target_width / float(image.size[0])
    target_height = int((float(image.size[1]) * float(width_percent)))
    return image.resize((target_width, target_height), Image.LANCZOS)


def combine_two_tables(img1: Image.Image, img2: Image.Image) -> Image.Image | None:
    if img1 is None:
        return img2
    if img2 is None:
        return img1

    # Получение ширин изображений
    width1, height1 = img1.size
    width2, height2 = img2.size

    # Определяем целевую ширину (например, берем минимальную ширину)
    target_width = min(width1, width2)

    # Изменение размеров изображений до целевой ширины
    img1_resized = resize_image_to_width(img1, target_width)
    img2_resized = resize_image_to_width(img2, target_width)

    # Конвертация изображений в numpy массивы
    img1_np = np.array(img1_resized)
    img2_np = np.array(img2_resized)

    # Объединение изображений вертикально
    img_combined_np = np.vstack((img1_np, img2_np))
    img_combined = Image.fromarray(img_combined_np)
    return img_combined


def define_and_combine(image_path: str):
    image = Image.open(image_path)
    defined_tables_on_bboxes = define_tables_on_bboxes(image_path)

    table_ttl = defined_tables_on_bboxes['title']
    if table_ttl:
        x1, y1, x2, y2 = table_ttl.bbox.x1, table_ttl.bbox.y1, table_ttl.bbox.x2, table_ttl.bbox.y2
        table_ttl = image.crop((x1, y1, x2, y2))

    table_shp = defined_tables_on_bboxes['shipment']
    if table_shp:
        x1, y1, x2, y2 = table_shp.bbox.x1, table_shp.bbox.y1, table_shp.bbox.x2, table_shp.bbox.y2
        table_shp = image.crop((x1, y1, x2, y2))

    if table_ttl is None and table_shp is None:
        return None
    else:
        return combine_two_tables(table_ttl, table_shp)


def define_and_return(image_path: str):
    image = Image.open(image_path)
    defined_tables_on_bboxes = define_tables_on_bboxes(image_path)

    coords = {"table_ttl": [], "table_shp": []}
    table_ttl = defined_tables_on_bboxes['title']
    if table_ttl:
        x1, y1, x2, y2 = table_ttl.bbox.x1, table_ttl.bbox.y1, table_ttl.bbox.x2, table_ttl.bbox.y2
        coords["table_ttl"].extend([x1, y1, x2, y2])
        table_ttl = image.crop((x1, y1, x2, y2))

    table_shp = defined_tables_on_bboxes['shipment']
    if table_shp:
        x1, y1, x2, y2 = table_shp.bbox.x1, table_shp.bbox.y1, table_shp.bbox.x2, table_shp.bbox.y2
        coords["table_shp"].extend([x1, y1, x2, y2])
        table_shp = image.crop((x1, y1, x2, y2))

    return table_ttl, table_shp, coords


if __name__ == '__main__':
    file = os.path.join('..', 'IN/edited/Альфа_транс_24032708_pdf.jpg')
    start = perf_counter()
    combined = define_and_combine(file)
    print(f'time: {perf_counter() - start:.2f}')
    combined.show()
