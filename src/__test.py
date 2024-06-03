import json
import os
import shutil
from os import path
import re
from glob import glob
import base64
from io import BytesIO
from time import perf_counter
import PyPDF2
from PIL import Image, ImageDraw, ImageFont
from collections import defaultdict
from config import config
from utils import group_files_by_name
from itertools import count
from natsort import os_sorted, natsorted


files = ['123456.jpg',
         '123456_af.jpg',
         '0_1.jpg',
         '0_1_TAB1+.jpg',
         '0_1_TAB2+.jpg',
         '0_.jpg',
         '0__TAB1+.jpg',
         '0__TAB2+.jpg',
         '1.pdf',
         '15_ks_5-6.jpg',
         '15_ks_5-6_TAB1+.jpg',
         '15_ks_5-6_TAB2+.jpg',
         '16_first_inn.jpg',
         '16_first_inn_TAB1+.jpg',
         '123']

# grouped_files = group_files_by_name(files)
#
# for k,v in grouped_files.items():
#     print(k, v)
#
# json_name = '0_1' + '.json'
# print(os.path.join(config['CHECK_FOLDER'], json_name))

# print(config['IN_FOLDER_EDIT'])
# print("current dir", os.path.dirname(__file__))
# print(os_sorted(glob(f"{config['IN_FOLDER_EDIT']}\*.*")))
# for base, files in grouped_files.items():
#     print(f"BASE: {base}")
#     for file in files:
#         print(f"  - {file}")

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# print(config['IN_FOLDER_EDIT'])
# if os.path.exists(config['IN_FOLDER_EDIT']):
#     shutil.rmtree(config['IN_FOLDER_EDIT'])
# # os.makedirs(config['IN_FOLDER'])

s = r'C:\Users\Filipp\PycharmProjects\Invoice_scanner\IN\edited\DP_REZRUISP_2BE79f3d7fe84be4f4c9cb1f7b13ecd33b5_2BEd6b0181a280a40db8acc0ab94a16e03e_20240408_e97cbda6-58a8-49cf-92f8-85f07ccb8090'
print(os.path.basename(s))

result = """
{
    "Банковские реквизиты поставщика": {
        "ИНН": "781900474904",
        "КПП": "",
        "БИК": "",
        "корреспондентский счет": "",
        "расчетный счет": ""
    },
    "Банковские реквизиты покупателя": {
        "ИНН": "7814406186",
        "КПП": "783801001"
    },
    "Номер счета с датой": "Акт № 38 от 25 марта 2024 г.",
    "Услуги": [
        {
            "Наименование": "Организация перевозки по маршруту Санкт-Петербург - МО, го Подольск, д. Новоселки с 23.03.2024 по 25.03.2024, водитель Махмудов Э. Н., а/м Х599КТ178, заявка 92964 от 23.03.24, контейнер SLVU4410272.",
            "Единица": "шт",
            "Количество": 1,
            "Цена": 80000.0,
            "Сумма без НДС": 80000.0,
            "Сумма НДС": "",
            "Cумма с учетом НДС": 80000.0,
            "Номера контейнеров": "SLVU4410272"
        }
    ],
    "Итого без НДС": 80000.0,
    "Сумма НДС": "",
    "Итого с учетом НДС": 80000.0
}
"""

# json_name = 'C:\\Users\\Filipp\\PycharmProjects\\Invoice_scanner\\IN\\edited\\DP_REZRUISP_2BE79f3d7fe84be4f4c9cb1f7b13ecd33b5_2BEd6b0181a280a40db8acc0ab94a16e03e_20240408_e97cbda6-58a8-49cf-92f8-85f07ccb8090' + '.json'
# print(json_name)
# json_path = os.path.join(config['CHECK_FOLDER'], json_name)
# print(config['CHECK_FOLDER'])
# print(json_path)
# with open(json_path, 'w', encoding='utf-8') as file:
#     file.write(result)
