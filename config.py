import os

config = {
    "CURRENT_DIR": os.path.dirname(__file__),
    "IN_FOLDER": 'IN',
    "IN_FOLDER_EDIT": 'edited',
    "CHECK_FOLDER": 'CHECK',
    "OUT_FOLDER": 'OUT',
    "POPPLER_PATH": r'C:\Program Files\poppler-22.01.0\Library\bin',
    # "magick_opt": '-colorspace Gray -white-threshold 85% -level 0%,100%,0.5 -bilateral-blur 15 '
    #               '-gaussian-blur 6 -quality 100 -units PixelsPerInch -density 350',
    # "magick_opt": '-colorspace Gray -level 0%,100%,0.7 '
    #               '-quality 100 -units PixelsPerInch -density 350',
    # "magick_opt": '-colorspace Gray -auto-threshold OTSU -gaussian-blur 3 -enhance -enhance -enhance '
    #               '-quality 100 -units PixelsPerInch -density 350',
    "magick_opt": '-colorspace Gray',
    # "magick_opt": '',
    "json_struct": '{"Банковские реквизиты поставщика":{"ИНН":"","КПП":"","БИК":"","корреспондентский счет":"",'
                   '"расчетный счет":""},"Банковские реквизиты покупателя":{"ИНН":"","КПП":""},"Номер счета с '
                   'датой":"","Услуги":[{"Наименование":"","Единица":"","Количество":"",'
                   '"Цена":"","Сумма без НДС":"", "Сумма НДС":"", "Cумма с учетом НДС":""}, ...],"Итого без НДС":"",'
                   '"Сумма НДС":"","Итого с учетом НДС":""}',
    "system_prompt": None,
    "CSS_PATH": 'styles.css',
    "JS_PATH": 'scripts.js',
}

current_dir = config['CURRENT_DIR']
print('# config current dir:', current_dir)
config['IN_FOLDER'] = os.path.join(current_dir, config['IN_FOLDER'])
config['CHECK_FOLDER'] = os.path.join(current_dir, config['CHECK_FOLDER'])
config['OUT_FOLDER'] = os.path.join(current_dir, config['OUT_FOLDER'])
config['IN_FOLDER_EDIT'] = os.path.join(config['IN_FOLDER'], config['IN_FOLDER_EDIT'])
config['CSS_PATH'] = os.path.join(config['CURRENT_DIR'], config['CSS_PATH'])
config['JS_PATH'] = os.path.join(config['CURRENT_DIR'], config['JS_PATH'])
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
