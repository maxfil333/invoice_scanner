from glob import glob
import os
import sys
from utils import group_files_by_name, delete_all_files, create_date_folder_in_check
from config.config import config
from main_edit import main as main_edit
from main_openai import run_chat, run_assistant
from generate_html import create_html_form
import json
from itertools import count
from natsort import os_sorted
import shutil
import msvcrt


def main(show_logs=False, test_mode=True, use_existing=False, stop_when=0):
    # _____  FILL IN_FOLDER_EDIT  _____
    date_folder = create_date_folder_in_check(config['CHECK_FOLDER'])

    if not use_existing:
        delete_all_files(config['IN_FOLDER_EDIT'])
        main_edit()

    files = os_sorted(glob(f"{config['IN_FOLDER_EDIT']}/*.*"))
    files = [file for file in files if os.path.splitext(file)[-1] in ['.pdf', '.jpeg', '.jpg', '.png']]

    grouped_files = group_files_by_name(files)
    c = count(1)
    for base, files in grouped_files.items():

        # _____  CREATE JSON  _____
        print('base:', base, sep='\n')
        print('files:', *files, sep='\n')
        json_name = os.path.basename(base[0]) + '_' + '0' * 11 + '.json'
        if base[-1] == 'pdf':
            text_or_scanned_folder = config['NAME_text']
            # __ RUN ASSISTANT __
            if test_mode:
                with open(os.path.join(config['BASE_DIR'], '__test.json'), 'r', encoding='utf-8') as file:
                    result = file.read()
            else:
                result = run_assistant(files[0], show_logs=show_logs)
        else:
            text_or_scanned_folder = config['NAME_scanned']
            files.sort(reverse=True)
            # __ RUN CHAT __
            if test_mode:
                with open(os.path.join(config['BASE_DIR'], '__test.json'), 'r', encoding='utf-8') as file:
                    result = file.read()
            else:
                result = run_chat(*files, detail='high', show_logs=show_logs)

        json_path = os.path.join(date_folder, text_or_scanned_folder, json_name)
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
        original_save_path = os.path.join(date_folder, text_or_scanned_folder, original_save_path)
        shutil.copy(original_file_path, original_save_path)

        # _____  CREATE HTML  _____
        html_name = os.path.basename(base[0]) + '.html'
        html_path = os.path.join(date_folder, text_or_scanned_folder, html_name)

        create_html_form(json_path, html_path, original_save_path)

        # _____  STOP ITERATION  _____
        if stop_when > 0:
            stop = next(c)
            if stop == stop_when:
                break

    # _____  RESULT MESSAGE  _____
    return (f'Сохранено {len(grouped_files.items())} x 3 = {len(grouped_files.items()) * 3} '
            f'файлов в: \n{date_folder}')


if __name__ == "__main__":
    try:
        result_message = main(show_logs=True, test_mode=False, use_existing=False, stop_when=10)
        print(f'\nresult_message:\n{result_message}\n')
    except Exception as error:
        print(error)

    if getattr(sys, 'frozen', False):
        msvcrt.getch()
