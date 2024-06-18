import os
import sys
import msvcrt

config = dict()
config['magick_opt'] = '-colorspace Gray'
config['POPPLER_PATH'] = r'C:\Program Files\poppler-22.01.0\Library\bin'
config['NAME_scanned'] = 'scannedPDFs'
config['NAME_text'] = 'textPDFs'
config['NAME_verified'] = 'verified'

if getattr(sys, 'frozen', False):
    config['BASE_DIR'] = os.path.dirname(sys.executable)
else:
    config['BASE_DIR'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

config['IN_FOLDER'] = os.path.join(config['BASE_DIR'], 'IN')
config['IN_FOLDER_EDIT'] = os.path.join(config['IN_FOLDER'], 'edited')
config['CHECK_FOLDER'] = os.path.join(config['BASE_DIR'], 'CHECK')
config['CSS_PATH'] = os.path.join(config['BASE_DIR'], 'config', 'styles.css')
config['JS_PATH'] = os.path.join(config['BASE_DIR'], 'config', 'scripts.js')
config['crypto_env'] = os.path.join(config['BASE_DIR'], 'encrypted.env')

try:
    with open(os.path.join(config['BASE_DIR'], 'crypto.key'), 'r') as f:
        config['crypto_key'] = f.read()
except FileNotFoundError as e:
    print(e)
    if getattr(sys, 'frozen', False):
        msvcrt.getch()
        sys.exit()

# "magick_opt": '-colorspace Gray -white-threshold 85% -level 0%,100%,0.5 -bilateral-blur 15 '
#               '-gaussian-blur 6 -quality 100 -units PixelsPerInch -density 350',
# "magick_opt": '-colorspace Gray -level 0%,100%,0.7 '
#               '-quality 100 -units PixelsPerInch -density 350',
# "magick_opt": '-colorspace Gray -auto-threshold OTSU -gaussian-blur 3 -enhance -enhance -enhance '
#               '-quality 100 -units PixelsPerInch -density 350',

config['json_struct'] = ('{"Банковские реквизиты поставщика":{"ИНН":"","КПП":"","БИК":"","корреспондентский счет":"",'
                         '"расчетный счет":""},"Банковские реквизиты покупателя":{"ИНН":"","КПП":""},"Номер счета":"",'
                         '"Дата счета":"","Услуги":[{"Наименование":"","Единица":"","Количество":"","Цена":"",'
                         '"Сумма без НДС":"","Сумма НДС":"","Сумма с учетом НДС":""}, ...],"Итого без НДС":"",'
                         '"Сумма НДС":"","Итого с учетом НДС":""}')

config['system_prompt'] = f"""
Ты бот, заполняющий json шаблон основе отсканированного файла.

Шаблон:
{config['json_struct'].strip()}

Если какой-то из параметров не найден, впиши значение ''.
Дату записывай как DD-MM-YYYY.
Денежные данные записывай как число.
Верни только JSON-строку и ничего более.
""".strip()

if __name__ == '__main__':
    print(getattr(sys, 'frozen', False))
    for k, v in config.items():
        print(k)
        print(v)
        print('-' * 50)

    if getattr(sys, 'frozen', False):
        msvcrt.getch()
