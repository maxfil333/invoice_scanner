import os
import sys
import time
import shutil
import msvcrt
import argparse
import traceback
from glob import glob
from itertools import count
from natsort import os_sorted
from openai import PermissionDeniedError

from logger import logger
from config.config import config
from main_edit import main as main_edit
from generate_html import create_html_form
from main_openai import run_chat, run_assistant
from utils import group_files_by_name, delete_all_files, create_date_folder_in_check


def main(date_folder, hide_logs=False, test_mode=False, use_existing=False, text_to_assistant=False, stop_when=0):
    """
    :param date_folder: folder for saving results
    :param hide_logs: run without logs
    :param test_mode: run without main_openai using "config/__test.json"
    :param use_existing: run without main_edit using files in "IN/edited" folder
    :param text_to_assistant: do not use OCR to extract text from digital pdf, use loading pdf to assistant instead
    :param stop_when: stop script after N files
    :return:
    """
    # _____  FILL IN_FOLDER_EDIT  _____
    if not use_existing:
        delete_all_files(config['EDITED'])
        main_edit(hide_logs=hide_logs, stop_when=stop_when)

    files = os_sorted(glob(f"{config['EDITED']}/*.*"))
    files = [file for file in files if os.path.splitext(file)[-1] in ['.pdf', '.jpeg', '.jpg', '.png']]

    grouped_files = group_files_by_name(files)
    # TODO: вместо группирования по наименованию, сделать в main_edit группировку в папки
    c = count(1)
    for base, files in grouped_files.items():
        try:
            # _____  CREATE JSON  _____
            logger.print('-' * 20)
            logger.print('\nbase:', base, sep='\n')
            logger.print('files:', *files, sep='\n')
            json_name = os.path.basename(base[0]) + '_' + '0' * 11 + '.json'
            if base[-1] == 'pdf':
                text_or_scanned_folder = config['NAME_text']
                # ___ RUN ASSISTANT (or CHAT in text_to_assistant is False) ___
                if test_mode:
                    with open(config['TESTFILE'], 'r', encoding='utf-8') as file:
                        result = file.read()
                else:
                    if not text_to_assistant:
                        result = run_chat(files[0], detail='high', hide_logs=hide_logs, text_mode=True)
                    else:
                        result = run_assistant(files[0], hide_logs=hide_logs)
            else:
                text_or_scanned_folder = config['NAME_scanned']
                files.sort(reverse=True)
                # ___ RUN CHAT ___
                if test_mode:
                    with open(config['TESTFILE'], 'r', encoding='utf-8') as file:
                        result = file.read()
                else:
                    result = run_chat(*files, detail='high', hide_logs=hide_logs, text_mode=False)

            if result is None:
                continue

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
        except PermissionDeniedError:
            raise
        except Exception as error:
            logger.print('ERROR!:', error)
            logger.print(traceback.format_exc())
            continue

    # _____  RESULT MESSAGE  _____
    return (f'Сохранено {len(grouped_files.items())} x 3 = {len(grouped_files.items()) * 3} '
            f'файлов в: \n{date_folder}')


if __name__ == "__main__":
    logger.print("CONFIG INFO:")
    logger.print('sys._MEIPASS:', hasattr(sys, '_MEIPASS'))
    logger.print(f'POPPLER_RPATH = {config["POPPLER_PATH"]}')
    logger.print(f'magick_exe = {config["magick_exe"]}')
    logger.print(f'magick_opt = {config["magick_opt"]}')

    parser = argparse.ArgumentParser(description="DESCRIPTION: Invoice Scanner")
    parser.add_argument('--hide_logs', action='store_true', help='Скрыть логи')
    parser.add_argument('--test_mode', action='store_true', help='Режим тестирования')
    parser.add_argument('--use_existing', action='store_true', help='Использовать существующие файлы')
    parser.add_argument('--text_to_assistant', action='store_true', help='Извлечь текст из pdf')
    parser.add_argument('--no_exit', action='store_true', help='Не закрывать окно')
    parser.add_argument('--stop_when', type=int, default=-1, help='Максимальное количество файлов')
    args = parser.parse_args()
    logger.print(args, end='\n\n')

    date_folder = create_date_folder_in_check(config['CHECK_FOLDER'])
    try:
        result_message = main(date_folder=date_folder,
                              hide_logs=args.hide_logs,
                              test_mode=args.test_mode,
                              use_existing=args.use_existing,
                              text_to_assistant=args.text_to_assistant,
                              stop_when=args.stop_when)
        logger.print(f'\nresult_message:\n{result_message}\n')
    except PermissionDeniedError:
        logger.print('ОШИБКА ВЫПОЛНЕНИЯ:\n!!! Включите VPN !!!')
    except Exception as global_error:
        logger.print('GLOBAL_ERROR!:', global_error)
        logger.print(traceback.format_exc())

    if getattr(sys, 'frozen', False):
        if args.no_exit:
            msvcrt.getch()
        else:
            logger.print('Завершено. Выполняется закрытие...')

    logger.save(date_folder)
    time.sleep(3)
