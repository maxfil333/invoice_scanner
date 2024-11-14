import os
import re
import json
from html import escape
from bs4 import BeautifulSoup

from config.config import config, NAMES, current_file_params
from src.logger import logger


def generate_input_html(key, val):
    def generate_selection(key, char_key, select_list, value):
        html = f'<select name="{escape(key)}" class="{escape(char_key)}">'
        for option_value in select_list:
            selected = 'selected' if value == option_value else ''
            html += f'<option value="{escape(option_value)}" {selected}>{escape(option_value)}</option>'
        html += '</select></div>\n'
        return html

    char_key = re.sub(r'\W', '', str(key))
    input_type = "text"

    # если ключ начинается с __, label не создаем, input - скрытый
    if str(key).startswith('__'):
        html_content = f'<div class="input-group">\n'
        html_content += (f'<input type="{input_type}" name="{escape(key)}" '
                         f'class="{escape(char_key)}" value="{escape(str(val))}" hidden></div>\n')
        return html_content

    # обычный случай
    html_content = (f'<div class="input-group">\n'
                    f'<label>{escape(key)}</label>\n')

    if key == NAMES.price_type:
        html_content += generate_selection(key=key, char_key=char_key, select_list=NAMES.price_type_opts, value=val)

    elif key == NAMES.type_of_document:
        html_content += generate_selection(key=key, char_key=char_key, select_list=NAMES.type_of_document_opts,
                                           value=val)

    elif key == NAMES.currency:
        html_content += generate_selection(key=key, char_key=char_key, select_list=NAMES.currency_opts, value=val)

    # создание дополнительного поля для суммирования по услугам рядом с "Всего к оплате включая НДС" и "Всего НДС"
    elif key in [NAMES.total_with, NAMES.total_nds]:
        html_content += '<div class="input-group">\n'
        html_content += (f'<input type="{input_type}" name="{escape(key)}" '
                         f'class="{escape(char_key)}" value="{escape(str(val))}">\n')
        if key == NAMES.total_with:
            html_content += (f'<input type="{input_type}" name="{escape(key)}" '
                             f'class="not_for_json" value="" id="last_total_with" disabled>\n')
        else:
            html_content += (f'<input type="{input_type}" name="{escape(key)}" '
                             f'class="not_for_json" value="" id="last_total_nds" disabled>\n')
        html_content += '</div>\n</div>\n'

    elif isinstance(val, bool):
        input_type = "checkbox"
        checked = 'checked' if val else ''
        html_content += f'<input type="{input_type}" name="{escape(key)}" {checked}></div>\n'

    elif (isinstance(val, str) and (key in [NAMES.name, NAMES.cont, NAMES.good1C,
                                            NAMES.good1C_new, 'Сделки по коносаментам'] or len(val) > 30)):
        html_content += (f'<textarea name="{escape(key)}" class="{escape(char_key)}" rows="1" style="resize:none;" '
                         f'oninput="autoResize(this)">{escape(val)}</textarea>')
        if key == NAMES.good1C:
            html_content += '<div class="dropdown"></div>\n'
        html_content += '</div>\n'

    else:
        html_content += (f'<input type="{input_type}" name="{escape(key)}" '
                         f'class="{escape(char_key)}" value="{escape(str(val))}"></div>\n')

    return html_content


def generate_html_from_json(data, parent_key="", prefix=""):
    html_content = ""
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f'{parent_key}.{key}' if parent_key else key
            display_key = key
            char_key = re.sub(r'\W', '', str(key))
            if isinstance(value, (dict, list)):

                # номер сделки
                if key == NAMES.transactions:
                    html_content += f'<div class="input-group">'
                    html_content += f'<label>Номер сделки</label>'
                    html_content += f'<select class={char_key} name={char_key}>'
                    for v in value:
                        html_content += f'<option value="{v}">{v}</option>'
                    html_content += f'<option value="Нет">Нет</option>'
                    html_content += f'</select>'
                    html_content += f'</div>'
                else:
                    html_content += f'<fieldset><legend>{escape(display_key)}</legend>\n'
                    html_content += generate_html_from_json(value, new_key, prefix)
                    html_content += '</fieldset>\n'
            else:
                html_content += generate_input_html(display_key, value)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            new_key = f'{parent_key}[{i}]'
            display_key = f'{i + 1}'
            if parent_key.endswith(NAMES.goods):
                html_content += f'<fieldset class="service"><legend>{escape(display_key)}</legend>\n'
            else:
                html_content += f'<fieldset><legend>{escape(display_key)}</legend>\n'
            html_content += generate_html_from_json(item, new_key, prefix)
            html_content += '</fieldset>\n'
        if parent_key.endswith(NAMES.goods):
            html_content += '<button type="button" onclick="addService(this)">+</button>\n'
            html_content += '<button type="button" onclick="removeService(this)">-</button>\n'
    return html_content


def create_html_form(json_file, output_file, file_path):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Определяем тип файла на основе расширения
    file_extension = os.path.splitext(file_path)[-1].lower()
    if file_extension == '.pdf':
        file_display = (f'<iframe src="{os.path.basename(file_path)}" '
                        f'width="100%" height="100%"></iframe>')
    elif file_extension in ['.jpg', '.jpeg', '.png']:
        file_display = (f'<img src="{os.path.basename(file_path)}" '
                        f'alt="Image" width="100%" height="100%" style="object-fit: contain;">')
    else:
        file_display = '<p>Unsupported file type. Please upload a PDF or JPG file.</p>'

    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Roboto:400,700&display=swap">
        <link rel="stylesheet" type="text/css" href="{config['CSS_PATH']}">
    </head>
    <body>
        <div class="container">
            <div class="left-pane">
                <form id="invoice-form" autocomplete="off">
                
    '''

    html_content += generate_html_from_json(data)

    switch_checked_status = 'checked'  # по умолчанию включен Авто-расчет
    if current_file_params.get('balance_fixes', False):  # если были распределения остатков - выключаем
        switch_checked_status = ''

    html_content += f'''
                     <div class="button-container">
                         <button type="button" id="save-button">Сохранить</button>
                         <label class="switch">
                             <span class="switch-label">Авторасчет</span>
                             <input type="checkbox" class="not_for_json" {switch_checked_status}>
                             <span class="slider"></span>
                         </label>
                     </div>
                </form>
            </div>
            <div class="right-pane">
                {file_display}
            </div>
        </div>
        <script src="{config['JS_PATH']}"></script>
        <div jsonfilename="{os.path.basename(json_file)}" id="jsonfilenameid"></div>
        <div id="jsonfiledataid" hidden>{json.dumps(data, ensure_ascii=False)}</div>
        <div id="unique_services" hidden>{json.dumps(config['unique_services'], ensure_ascii=False)}</div>
    </body>
    </html>
    '''

    soup = BeautifulSoup(html_content, 'html.parser')
    prettified = soup.prettify()

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(prettified)

    logger.print(f'HTML страница сгенерирована и сохранена в {output_file}')


if __name__ == '__main__':
    create_html_form(r"C:\Users\Filipp\Desktop\0_DATA\Новая папка (4)\0.json",
                     r"C:\Users\Filipp\Desktop\0_DATA\Новая папка (4)\0.html",
                     r"C:\Users\Filipp\Desktop\0_DATA\Новая папка (4)\20_Содружество_Балтика-Транс.pdf")
