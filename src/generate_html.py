import json
from html import escape
import os
from config.config import config
from bs4 import BeautifulSoup as bs


def generate_input_html(key, value):
    input_type = "text"
    html_content = f'<div class="input-group"><label>{escape(key)}</label>'

    if isinstance(value, bool):
        input_type = "checkbox"
        checked = 'checked' if value else ''
        html_content += f'<input type="{input_type}" name="{escape(key)}" {checked}></div>\n'
    elif isinstance(value, str) and len(value) > 30:
        html_content += (f'<textarea name="{escape(key)}" rows="1" style="resize:none;" '
                         f'oninput="this.style.height=\'auto\'; '
                         f'this.style.height=(this.scrollHeight)+\'px\';">{escape(value)}</textarea></div>\n')
    else:
        html_content += f'<input type="{input_type}" name="{escape(key)}" value="{escape(str(value))}"></div>\n'

    return html_content


def generate_html_from_json(data, parent_key="", prefix=""):
    html_content = ""
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f'{parent_key}.{key}' if parent_key else key
            display_key = key
            if isinstance(value, (dict, list)):
                html_content += f'<fieldset><legend>{escape(display_key)}</legend>\n'
                html_content += generate_html_from_json(value, new_key, prefix)
                html_content += '</fieldset>\n'
            else:
                html_content += generate_input_html(display_key, value)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            new_key = f'{parent_key}[{i}]'
            display_key = f'{i + 1}'
            if parent_key.endswith("Услуги"):
                html_content += f'<fieldset class="service"><legend>{escape(display_key)}</legend>\n'
            else:
                html_content += f'<fieldset><legend>{escape(display_key)}</legend>\n'
            html_content += generate_html_from_json(item, new_key, prefix)
            html_content += '</fieldset>\n'
        if parent_key.endswith("Услуги"):
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
    elif file_extension == '.jpg' or file_extension == '.jpeg':
        file_display = (f'<img src="{os.path.basename(file_path)}" '
                        f'alt="Image" width="100%" height="100%" style="object-fit: contain;">')
    else:
        file_display = '<p>Unsupported file type. Please upload a PDF or JPG file.</p>'

    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Roboto:400,700&display=swap">
        <link rel="stylesheet" type="text/css" href="{config['CSS_PATH']}">
    </head>
    <body>
        <div class="container">
            <div class="left-pane">
                <form id="invoice-form">
                
    '''

    html_content += generate_html_from_json(data)

    html_content += f'''
    
                     <button type="button" id="save-button">Сохранить</button>
                </form>
            </div>
            <div class="right-pane">
                {file_display}
            </div>
        </div>
        <script src="{config['JS_PATH']}"></script>
        <div jsonfilename="{os.path.basename(json_file)}" id="jsonfilenameid"></div>
        <div id="jsonfiledataid" hidden>{json.dumps(data, ensure_ascii=False)}</div>
        <div id="jsononegoodid" hidden>{data['Услуги'][0]}</div>
    </body>
    </html>
    '''

    soup = bs(html_content, 'html.parser')
    prettified = soup.prettify()

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(prettified)

    print(f'HTML страница сгенерирована и сохранена в {output_file}')
