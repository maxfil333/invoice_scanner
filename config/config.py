import os
import sys
import json
import msvcrt
import shutil

from src.logger import logger

# main.spec
r"""
datas=[
    ('C:\\Program Files\\poppler-24.07.0\\Library\\bin', 'poppler'),
    ('src', 'src'),
    ('config', 'config'),
    ('C:\\Program Files\\Tesseract-OCR', 'Tesseract-OCR'),
    ('C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI', 'magick')
],
"""

current_file_params: dict = dict()

config: dict = dict()
config['magick_opt'] = '-colorspace Gray -quality 100 -units PixelsPerInch -density 350'.split(' ')
config['NAME_scanned'] = '0_scan'
config['NAME_text'] = '1_text'
config['NAME_verified'] = 'EXPORT'

if getattr(sys, 'frozen', False):  # в сборке
    config['BASE_DIR'] = os.path.dirname(sys.executable)
    config['POPPLER_PATH'] = os.path.join(sys._MEIPASS, 'poppler')
    config['magick_exe'] = os.path.join(sys._MEIPASS, 'magick', 'magick.exe')
else:
    config['BASE_DIR'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config['POPPLER_PATH'] = r'C:\Program Files\poppler-24.07.0\Library\bin'
    config['magick_exe'] = 'magick'  # или полный путь до ...magick.exe файла, если не добавлено в Path

config['server_datas'] = os.path.normpath("\\\\10.10.0.3\\docs\\Transfer\\Filipp\\1_shared\\invoice_scanner")
config['CONFIG'] = os.path.join(config['BASE_DIR'], 'config')
config['IN_FOLDER'] = os.path.join(config['BASE_DIR'], 'IN')
config['EDITED'] = os.path.join(config['BASE_DIR'], 'EDITED')
os.makedirs(config['EDITED'], exist_ok=True)
config['CHECK_FOLDER'] = os.path.join(config['BASE_DIR'], 'CHECK')
os.makedirs(config['CHECK_FOLDER'], exist_ok=True)
config['CSS_PATH'] = "../../../../config/styles.css"
config['JS_PATH'] = "../../../../config/scripts.js"
config['crypto_env'] = os.path.join(config['CONFIG'], 'encrypted.env')
config['TESTFILE'] = os.path.join(config['CONFIG'], 'test.json')
config['GPTMODEL'] = 'gpt-4o-2024-08-06'
# config['GPTMODEL'] = 'gpt-4o'
# config['GPTMODEL'] = 'gpt-4o-mini'
config['chroma_path'] = os.path.join(config['CONFIG'], 'chroma')
config['embedding_model'] = "text-embedding-3-large"

config['low_threshold'] = 0.2
config['high_threshold'] = 0.7

try:
    with open(os.path.join(config['CONFIG'], 'crypto.key'), 'r') as f:
        config['crypto_key'] = f.read()
except FileNotFoundError as e:
    logger.print(e)
    logger.print('Не найден crypto.key')
    if getattr(sys, 'frozen', False):
        msvcrt.getch()
        sys.exit()

if not getattr(sys, 'frozen', False):  # не в сборке
    config['services_excel_file'] = os.path.join(config['CONFIG'], 'Услуги_поставщиков.xls')
    config['ships_excel_file'] = os.path.join(config['CONFIG'], 'Список_судов.xls')

config['ships_json'] = os.path.join(config['CONFIG'], 'ships.json')

try:
    with open(config['ships_json'], 'r', encoding='utf-8') as f:
        config['ships'] = tuple(set(json.load(f).values()))
except Exception as e:
    logger.print('Ошибка чтения ships.json:', e)
    logger.save(config['CHECK_FOLDER'])
    raise

# _____________________ list of services _____________________

# JSON файл, содержащий словарь {Услуга1С: Код, ..}
config['all_services_file'] = os.path.join(config['CONFIG'], 'all_services.json')
config['all_services_file_server'] = os.path.join(config['server_datas'], 'all_services.json')
try:
    server_file_time = os.path.getmtime(config['all_services_file_server'])
    local_file_time = os.path.getmtime(config['all_services_file'])
    if server_file_time > local_file_time:
        # копируем с сервера новый `all_services.json` в config
        shutil.copy2(config['all_services_file_server'], config['all_services_file'])
        # параметр для логов
        config['update_all_services'] = True
except:
    pass

try:
    with open(config['all_services_file'], 'r', encoding='utf-8') as f:
        config['all_services_dict'] = json.load(f)
        # список уникальных Услуга1С#Код#
        config['all_services'] = [f"{k}#{v}#" for k, v in config['all_services_dict'].items()]
except FileNotFoundError:
    config['all_services'] = []
    logger.print(f"! FILE {config['all_services_file']} NOT FOUND !")

# JSON файл, содержащий список словарей [ {id: 7, comment: Услуга, service_code: [Услуга1С#Код#, ..]} , {..} ]
config['unique_comments_file'] = os.path.join(config['CONFIG'], 'unique_comments.json')
config['unique_comments_file_server'] = os.path.join(config['server_datas'], 'unique_comments.json')
try:
    local_unique_date = os.path.getmtime(config['unique_comments_file'])
    server_unique_date = os.path.getmtime(config['unique_comments_file_server'])
    # если файл unique_comments.json на сервере свежее чем config/unique_comments.json
    if server_unique_date > local_unique_date:
        # копируем с сервера новый `unique_comments.json` в config
        shutil.copy2(config['unique_comments_file_server'], config['unique_comments_file'])
        # добавляем параметр, по которому в main.py вызовется функция пересоздания базы chroma
        config['update_chroma'] = True
except:
    pass

config['unique_services'] = []
config['not_found_service'] = 'Не найдено'
try:
    with open(config['unique_comments_file'], 'r', encoding='utf-8') as f:
        dct = json.load(f)
        config['unique_comments_dict'] = dct
        # список уникальных Услуга1С#Код#
        config['unique_services'] = list(dict.fromkeys([code for mini_dct in dct for code in mini_dct['service_code']]))
        config['unique_services'].append(config['not_found_service'])
except FileNotFoundError:
    logger.print(f"!!! FILE {config['unique_comments_file']} NOT FOUND !!!")
    logger.save(config['CHECK_FOLDER'])
    raise

# объединенный список уникальных Услуга1С#Код# (в html <div id="unique_services" hidden>)
config['unique_services'] = list(set(config['unique_services'] + config['all_services']))

config['currency_dict'] = {'BYN': 'BYN#933', 'CHF': 'CHF#756', 'CNY': 'CNY#156', 'EUR': 'EUR#978', 'GBP': 'GBP#826',
                           'ILS': 'ILS#376', 'INR': 'INR#356', 'JPY': 'JPY#392', 'KZT': 'KZT#398', 'RSD': 'RSD#941',
                           'TRY': 'TRY#949', 'USD': 'USD#840', 'VND': 'VND#704', 'РУБ': 'РУБ#643'}
config['valid_ext'] = ['.pdf', '.jpg', '.jpeg', '.png']
config['excel_ext'] = ['.xls', '.xltx', '.xlsx']


class ConfigNames:
    goods = 'Услуги'
    name = 'Наименование'  # 1
    good1C = 'Услуга1С'
    good1C_new = 'Услуга1С (новая)'
    cont = 'Контейнеры'  # 2
    local_conos = 'Коносаменты (для услуги)'
    local_dt = 'ДТ (для услуги)'
    unit = 'Единица'  # 3
    amount = 'Количество'  # 4
    price = 'Цена'  # 5
    sum_with = 'Сумма включая НДС'  # 6
    sum_nds = 'Сумма НДС'  # 7
    total_with = 'Всего к оплате включая НДС'
    total_nds = 'Всего НДС'
    price_type = 'price_type'
    price_type_opts = ['Сверху', 'В т.ч.']
    transactions = 'Номер сделки'
    transactions_new = 'Номер сделки (ввести свой)'
    transactions_type = 'Тип поиска сделки'
    nds_percent = 'nds (%)'
    noNDS = 'Без НДС'
    sum_w_nds = 'Сумма (с НДС)'
    sum_wo_nds = 'Сумма (без НДС)'
    price_w_nds = 'Цена (с НДС)'
    price_wo_nds = 'Цена (без НДС)'
    type_of_document = 'Тип документа'
    type_of_document_opts = ['Счет', 'Другое']
    currency = 'Валюта документа'
    currency_opts = list(config['currency_dict'].values())
    reports = 'Заключения'
    local_reports = 'Заключения (для услуги)'
    extra_deals = 'Найденные сделки'
    extra_deals_not = 'Ненайденные сделки'
    contract_details = "contract_details"
    add_info = 'additional_info'
    conversion = 'Конвертация'
    init_id = "__исходный_айди"
    date_range = "Даты"


NAMES = ConfigNames()

config['textarea_fields'] = [NAMES.name, NAMES.cont, NAMES.good1C, NAMES.good1C_new,
                             NAMES.extra_deals, NAMES.extra_deals_not]

# 15 = 7(prompt) - (price - sum_with - sum_nds)(3) + (2*Сумма + 2*Цена)(4)
# + (good1C + good1C_new + price_type)(3) + (tran, tran_new, tran_type)(3) + local_conos(1)
# 15 = 7 - 3 + 4 + 3 + 3 + 1
config['services_order'] = [NAMES.name, NAMES.good1C, NAMES.good1C_new, NAMES.cont,
                            NAMES.local_conos, NAMES.local_dt, NAMES.local_reports,
                            NAMES.date_range, NAMES.unit, NAMES.amount,
                            NAMES.price_wo_nds, NAMES.sum_wo_nds, NAMES.price_w_nds, NAMES.sum_w_nds, NAMES.price_type,
                            NAMES.transactions, NAMES.transactions_new, NAMES.transactions_type, NAMES.nds_percent]

config['extra_local_fields'] = [NAMES.local_conos, NAMES.local_dt, NAMES.local_reports]

config['conversion_dict'] = {
    1: "Конвертация#000000397#",
    2: "Конвертация 2%#ТК-007260#",
    3: "КОМИССИЯ +3%#ТК-009590#",
    5: "Конвертация 5%#ТК-007499#",
    'untitled': "Конвертация#000000397#"
}

config['placeholders'] = {'Даты': 'ДД.ММ.ГГГГ ДД.ММ.ГГГГ'}

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
            "Дата счета": {"type": "string", "description": "DD.MM.YYYY"},
            "Валюта документа": {"type": "string",
                                 "description": "РУБ, если не указано другое",
                                 "enum": ["РУБ", "USD", "EUR"]},
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
                    "ДТ": {"type": "array", "items": {"type": "string"}, "description": "в формате \d{8}/\d{6}/\d{7}"},
                    "Заключения": {"type": "array", "items": {"type": "string"},
                                   "description": "в формате \d{6}-\d{3}-\d{2}"},
                    "Конвертация": {"type": "number", "description": "% конвертации. Оплата в рублях по курсу ЦБ РФ + %. 0 если не указано"}
                },
                "required": ["Коносаменты", "Судно", "ДТ", "Заключения", "Конвертация"],
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
            "Валюта документа",
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

# if not getattr(sys, 'frozen', False):  # не в сборке
#     params_path = os.path.join(config['BASE_DIR'], 'config', 'parameters.json')
#     with open(params_path, 'w', encoding='utf-8') as f:
#         json.dump(config, f, ensure_ascii=False, indent=4)


logger.print("CONFIG INFO:")
logger.print('sys.frozen:', getattr(sys, 'frozen', False))

for k, v in config.items():
    if k not in ['unique_comments_dict',
                 'unique_services',
                 'union_services',
                 'all_services_dict',
                 'all_services',
                 'all_services_file_server',
                 'ships', 'currency_dict',
                 'services_order',
                 'response_format',
                 'system_prompt']:
        logger.print(f"{k}: {v}")


if __name__ == '__main__':
    pass
