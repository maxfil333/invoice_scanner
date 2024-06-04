from glob import glob
import os
from utils import group_files_by_name
from config.config import config
from main_edit import main as main_edit
from main_openai import run_chat, run_assistant
from generate_html import create_html_form
import json
from itertools import count
from natsort import os_sorted
import shutil


def main(show_logs=False):
    # _____  FILL IN_FOLDER_EDIT  _____
    # main_edit()
    files = os_sorted(glob(f"{config['IN_FOLDER_EDIT']}/*.*"))
    files = [file for file in files if os.path.splitext(file)[-1] in ['.pdf', '.jpeg', '.jpg', '.png']]
    print(files)

    grouped_files = group_files_by_name(files)
    c = count(1)
    for base, files in grouped_files.items():

        # _____  CREATE JSON  _____
        print('base:', base, sep='\n')
        print('files:', *files, sep='\n')
        json_name = os.path.basename(base[0]) + '_' + '0' * 11 + '.json'
        if base[-1] == 'pdf':
            # result = run_assistant(files[0], show_logs=show_logs)

            # result = '1'
            with open(r'C:\Users\Filipp\PycharmProjects\Invoice_scanner\__test.json', 'r', encoding='utf-8') as file: result = file.read()

        else:
            files.sort(reverse=True)

            # result = run_chat(*files, detail='high', show_logs=show_logs)

            # result = '2'
            with open(r'C:\Users\Filipp\PycharmProjects\Invoice_scanner\__test.json', 'r', encoding='utf-8') as file: result = file.read()

        json_path = os.path.join(config['CHECK_FOLDER'], json_name)
        with open(json_path, 'w', encoding='utf-8') as file:
            file.write(result)

        # _____  COPY ORIGINAL FILE  _____
        main_file = files[-1]
        # изначальный тип файла (записанное в конце после _ )
        original_file_type = os.path.basename(main_file).rsplit(".", 1)[0].rsplit("_", 1)[-1]
        # изначальное имя файла без _pdf.pdf
        original_file_name = os.path.basename(main_file).rsplit(".", 1)[0].rsplit("_", 1)[0]

        original_file_full = original_file_name + '.' + original_file_type
        original_file_path = os.path.join(config['IN_FOLDER'], original_file_full)
        original_save_path = os.path.basename((os.path.splitext(original_file_path)[0]
                                               + f'_{original_file_type}'
                                               + os.path.splitext(original_file_path)[1]))
        original_save_path = os.path.join(config['CHECK_FOLDER'], original_save_path)
        shutil.copy(original_file_path, original_save_path)

        # _____  CREATE HTML  _____
        html_name = os.path.basename(base[0]) + '.html'
        html_path = os.path.join(config['CHECK_FOLDER'], html_name)

        create_html_form(json_path, html_path, original_save_path)

        # _____  STOP ITERATION  _____
        stop = next(c)
        if stop == 1:
            break


if __name__ == "__main__":
    main(show_logs=True)
