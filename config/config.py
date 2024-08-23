import os
import sys
import json
import msvcrt
from glob import glob
from logger import logger

# main.spec
r"""
datas=[
    ('C:\\Program Files\\poppler-22.01.0\\Library\\bin', 'poppler'),
    ('src', 'src'),
    ('config', 'config'),
    ('C:\\Program Files\\Tesseract-OCR', 'Tesseract-OCR'),
    ('C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI', 'magick')
],
"""

config = dict()
config['magick_opt'] = '-colorspace Gray -quality 100 -units PixelsPerInch -density 350'.split(' ')
config['NAME_scanned'] = 'scannedPDFs'
config['NAME_text'] = 'textPDFs'
config['NAME_verified'] = 'verified'

if getattr(sys, 'frozen', False):  # в сборке
    config['BASE_DIR'] = os.path.dirname(sys.executable)
    config['POPPLER_PATH'] = os.path.join(sys._MEIPASS, 'poppler')
    config['magick_exe'] = os.path.join(sys._MEIPASS, 'magick', 'magick.exe')
else:
    config['BASE_DIR'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config['POPPLER_PATH'] = r'C:\Program Files\poppler-22.01.0\Library\bin'
    config['magick_exe'] = 'magick'  # или полный путь до ...magick.exe файла, если не добавлено в Path

config['CONFIG'] = os.path.join(config['BASE_DIR'], 'config')
config['IN_FOLDER'] = os.path.join(config['BASE_DIR'], 'IN')
config['EDITED'] = os.path.join(config['BASE_DIR'], 'EDITED')
config['CHECK_FOLDER'] = os.path.join(config['BASE_DIR'], 'CHECK')
config['CSS_PATH'] = os.path.join(config['CONFIG'], 'styles.css')
config['JS_PATH'] = os.path.join(config['CONFIG'], 'scripts.js')
config['crypto_env'] = os.path.join(config['CONFIG'], 'encrypted.env')
config['TESTFILE'] = os.path.join(config['CONFIG'], '__test.json')
config['GPTMODEL'] = 'gpt-4o-2024-08-06'
# config['GPTMODEL'] = 'gpt-4o'
# config['GPTMODEL'] = 'gpt-4o-mini'
config['chroma_path'] = os.path.join(config['CONFIG'], 'chroma')

if not getattr(sys, 'frozen', False):  # в сборке
    config['services_excel_file'] = os.path.join(config['CONFIG'], 'Услуги_поставщиков.xls')

config['unique_comments_file'] = os.path.join(config['CONFIG'], 'unique_comments.json')
config['unique_comments_dict'] = None  # to html <div id="services_dict..."
try:
    with open(config['unique_comments_file'], 'r', encoding='utf-8') as f:
        config['unique_comments_dict'] = json.load(f)
except FileNotFoundError:
    logger.print(f"!!! FILE {config['unique_comments_file']} NOT FOUND !!!")
    logger.save(config['CHECK_FOLDER'])
    raise

try:
    with open(os.path.join(config['CONFIG'], 'crypto.key'), 'r') as f:
        config['crypto_key'] = f.read()
except FileNotFoundError as e:
    logger.print(e)
    logger.print('Не найден crypto.key')
    if getattr(sys, 'frozen', False):
        msvcrt.getch()
        sys.exit()


class ConfigNames:
    goods = 'Услуги'
    name = 'Наименование'
    good1C = 'Услуга1С'
    good1C_new = 'Услуга1С (новая)'
    cont = 'Контейнеры'
    cont_names = 'Контейнеры (наименование)'
    unit = 'Единица'
    amount = 'Количество'
    price = 'Цена'
    sum_with = 'Сумма включая НДС'
    sum_nds = 'Сумма НДС'
    total_with = 'Всего к оплате включая НДС'
    total_nds = 'Всего НДС'
    price_type = 'price_type'


NAMES = ConfigNames()

# 11 = 7(оригинальных) - (price - sum_with - sum_nds)(3) + (2*Сумма + 2*Цена)(4) + price_type + good1C + cont_names
# 11 = 7 - 3 + 4 + 3
config['services_order'] = [NAMES.name, NAMES.good1C, NAMES.good1C_new,
                            NAMES.cont, NAMES.cont_names, NAMES.unit, NAMES.amount,
                            'Цена (без НДС)', 'Сумма (без НДС)', 'Цена (с НДС)', 'Сумма (с НДС)',
                            'price_type']

JSON_SCHEMA = {
    "name": "document",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "Банковские реквизиты поставщика": {
                "type": "object",
                "properties": {
                    "ИНН": {"type": "string"},
                    "КПП": {"type": "string"},
                    "БИК": {"type": "string"},
                    "корреспондентский счет": {"type": "string"},
                    "расчетный счет": {"type": "string"}
                },
                "required": ["ИНН", "КПП", "БИК", "корреспондентский счет", "расчетный счет"],
                "additionalProperties": False
            },
            "Банковские реквизиты покупателя": {
                "type": "object",
                "properties": {
                    "ИНН": {"type": "string"},
                    "КПП": {"type": "string"}
                },
                "required": ["ИНН", "КПП"],
                "additionalProperties": False
            },
            "Номер счета": {"type": "string"},
            "Дата счета": {"type": "string", "description": "DD-MM-YYYY"},
            "Услуги": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "Наименование": {"type": "string", "description": "полное описание услуги (ничего не изменяй)"},
                        "Контейнеры": {"type": "string", "description": "в формате [A-Z]{{4}}\s?[0-9]{{7}}"},
                        "Единица": {"type": "string"},
                        "Количество": {"type": "number"},
                        "Цена": {"type": "number"},
                        "Сумма включая НДС": {"type": "number"},
                        "Сумма НДС": {"type": "number"}
                    },
                    "required": ["Наименование", "Контейнеры", "Единица", "Количество", "Цена", "Сумма включая НДС",
                                 "Сумма НДС"],
                    "additionalProperties": False
                }
            },
            "additional_info": {
                "type": "object",
                "properties": {
                    "Коносаменты": {"type": "array", "items": {"type": "string"}, "description": "коносамент, к/с, кс"},
                    "Судно": {"type": "string", "description": "наименование судна, т/х"},
                    "ДТ": {"type": "string", "description": "в формате \d{8}/\d{6}/\d{7}"}
                },
                "required": ["Коносаменты", "Судно", "ДТ"],
                "additionalProperties": False
            },
            "Всего к оплате включая НДС": {"type": "number"},
            "Всего НДС": {"type": "number"}
        },
        "required": [
            "Банковские реквизиты поставщика",
            "Банковские реквизиты покупателя",
            "Номер счета",
            "Дата счета",
            "Услуги",
            "additional_info",
            "Всего к оплате включая НДС",
            "Всего НДС"
        ],
        "additionalProperties": False
    }
}

config['response_format'] = {"type": "json_schema", "json_schema": JSON_SCHEMA}

config['system_prompt'] = f"""
Ты бот, анализирующий документы (счета).
Если какой-то из параметров не найден, впиши значение ''.
""".strip()

if not getattr(sys, 'frozen', False):  # не в сборке
    params_path = os.path.join(config['BASE_DIR'], 'config', 'parameters.json')
    with open(params_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    print('sys.frozen:', getattr(sys, 'frozen', False))
    for k, v in config.items():
        if k not in ['unique_comments_dict']:
            print('-' * 50)
            print(k)
            print(v)
            if k == 'json_struct':
                try:
                    json.loads(v)
                except json.decoder.JSONDecodeError:
                    print("Нарушена структура json")
                    break
