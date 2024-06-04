import os

config = dict()
config['BASE_DIR'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config['IN_FOLDER'] = os.path.join(config["BASE_DIR"], 'IN')
config['IN_FOLDER_EDIT'] = os.path.join(config["IN_FOLDER"], 'edited')
config['CHECK_FOLDER'] = os.path.join(config["BASE_DIR"], 'CHECK')
config['NAME_scanned'] = 'scannedPDFs'
config['NAME_text'] = 'textPDFs'
config['NAME_verified'] = 'verified'
config['OUT_FOLDER'] = os.path.join(config["BASE_DIR"], 'OUT')
config["POPPLER_PATH"] = r'C:\Program Files\poppler-22.01.0\Library\bin'
config['CSS_PATH'] = os.path.join(config["BASE_DIR"], 'config', 'styles.css')
config['JS_PATH'] = os.path.join(config["BASE_DIR"], 'config', 'scripts.js')
config['magick_opt'] = '-colorspace Gray'

# "magick_opt": '-colorspace Gray -white-threshold 85% -level 0%,100%,0.5 -bilateral-blur 15 '
#               '-gaussian-blur 6 -quality 100 -units PixelsPerInch -density 350',
# "magick_opt": '-colorspace Gray -level 0%,100%,0.7 '
#               '-quality 100 -units PixelsPerInch -density 350',
# "magick_opt": '-colorspace Gray -auto-threshold OTSU -gaussian-blur 3 -enhance -enhance -enhance '
#               '-quality 100 -units PixelsPerInch -density 350',

config['json_struct'] = '{"Банковские реквизиты поставщика":{"ИНН":"","КПП":"","БИК":"","корреспондентский счет":"",' \
                        '"расчетный счет":""},"Банковские реквизиты покупателя":{"ИНН":"","КПП":""},"Номер счета с ' \
                        'датой":"","Услуги":[{"Наименование":"","Единица":"","Количество":"",' \
                        '"Цена":"","Сумма без НДС":"","Сумма НДС":"","Cумма с учетом НДС":""}, ...],'\
                         '"Итого без НДС":"","Сумма НДС":"","Итого с учетом НДС":""}'

config['system_prompt'] = f"""
Ты бот, заполняющий json шаблон основе отсканированного файла.

Шаблон:
{config['json_struct'].strip()}

Если какой-то из параметров не найден, впиши значение ''.
Денежные данные записывай как число.
Запиши результат в одну строку.
""".strip()

if __name__ == '__main__':
    for k, v in config.items():
        print(k)
        print(v)
        print('-' * 50)
