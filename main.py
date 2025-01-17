import os
import sys
import time
import json
import shutil
import msvcrt
import argparse
import traceback
from glob import glob
from itertools import count
from natsort import os_sorted
from openai import PermissionDeniedError

from config.config import config, current_file_params, NAMES
from src.logger import logger
from src.connector import create_connection
from src.main_edit import main as main_edit
from src.main_openai import run_chat, run_assistant
from src.response_postprocessing import local_postprocessing
from src.transactions import get_transaction_number
from src.generate_html import create_html_form
from src.utils import create_vector_database
from src.utils import split_by_containers, split_by_conoses, split_by_dt, combined_split_by_reports
from src.utils import create_date_folder_in_check, distribute_conversion
from src.utils import order_goods, cleanup_empty_fields, order_keys, convert_json_values_to_strings


def main(date_folder, hide_logs=False, test_mode=False, use_existing=False, text_to_assistant=False,
         use_com_connector=False, ignore_connection=False, stop_when=0):
    """
    :param date_folder: folder for saving results
    :param hide_logs: run without logs
    :param test_mode: run without main_openai using "config/__test.json"
    :param use_existing: run without main_edit using files in "IN/edited" folder
    :param text_to_assistant: do not use OCR to extract text from digital pdf, use loading pdf to assistant instead
    :param use_com_connector: use COM-object instead of http-request
    :param ignore_connection: do not use any CUP requests
    :param stop_when: stop script after N files
    :return:
    """

    # _______ CONNECTION ________
    if ignore_connection is False:
        if use_com_connector:
            connection = create_connection()
        else:
            connection = 'http'
    else:
        connection = None

    # _____  FILL IN_FOLDER_EDIT  _____
    if not use_existing:
        main_edit(hide_logs=hide_logs, stop_when=stop_when)

    # _____  UPDATE CHROMA  _____
    if config.get('update_chroma'):
        create_vector_database()
        del config['update_chroma']

    c, stop = count(1), 0
    for folder_ in os.scandir(config['EDITED']):
        folder, folder_name = folder_.path, folder_.name

        files = os_sorted(glob(f"{folder}/*.*"))
        files = [file for file in files if os.path.splitext(file)[-1] in ['.pdf', '.jpeg', '.jpg', '.png']]

        try:
            # _____  CREATE JSON  _____
            logger.print('-' * 30)
            logger.print('\nedited.folder:', folder, sep='\n')
            logger.print('edited.files:', *files, sep='\n')
            json_name = folder_name + '_' + '0' * 11 + '.json'

            # _____________ RUN MAIN_OPENAI.PY _____________
            if os.path.splitext(files[0])[-1].lower() == '.pdf':  # достаточно проверить 1-й файл, чтобы определить .ext
                text_or_scanned_folder = config['NAME_text']
                # ___ RUN ASSISTANT (or CHAT, if text_to_assistant is False) ___
                if test_mode:
                    with open(config['TESTFILE'], 'r', encoding='utf-8') as file:
                        result = file.read()
                        from src.utils import extract_text_with_fitz
                        current_file_params['current_texts'] = extract_text_with_fitz(files[0])
                else:
                    if not text_to_assistant:
                        result = run_chat(files[0], detail='high', text_mode=True)
                    else:
                        result = run_assistant(files[0])
            else:
                text_or_scanned_folder: str = config['NAME_scanned']
                files.sort(reverse=True)
                # ___ RUN CHAT ___
                if test_mode:
                    with open(config['TESTFILE'], 'r', encoding='utf-8') as file:
                        result = file.read()
                else:
                    result = run_chat(*files, detail='high', text_mode=False)

            # _____________________ LOGS _____________________
            logger.print('openai result:\n', repr(result))
            with open(os.path.join(config['CONFIG'], 'openai_response_log.json'), 'w', encoding='utf-8') as f:
                json.dump(json.loads(result), f, ensure_ascii=False, indent=4)

            # _____________ LOCAL POSTPROCESSING _____________
            result = local_postprocessing(result, hide_logs=hide_logs, folder=folder)

            if result is None:
                continue

            # _____________ SPLIT BY CONTAINERS _____________
            result, was_edited = split_by_containers(result)

            # _____________ SPLIT BY CONOSES _____________
            if not was_edited:  # если уже было распределение по контейнерам, ничего не делать
                if json.loads(result)['additional_info']['Коносаменты']:
                    result, was_edited = split_by_conoses(result)

            # _____________ SPLIT BY DT _____________
            if not was_edited:  # если уже было распределение по контейнерам/коносаментам, ничего не делать
                if json.loads(result)['additional_info']['ДТ']:
                    result, was_edited = split_by_dt(result)

            # _____________ SPLIT BY REPORT _____________
            if not was_edited:  # если уже было распределение по контейнерам/коносаментам/ДТ, ничего не делать
                if json.loads(result)['additional_info'][NAMES.reports]:
                    result, was_edited = combined_split_by_reports(result)

            # _____________ distribute_conversion _____________
            result = distribute_conversion(result)

            # _____________ order and cleanup _____________
            dct = json.loads(result)
            dct = order_goods(dct, config['services_order'])
            dct = cleanup_empty_fields(dct, config['extra_local_fields'])
            result = json.dumps(dct, ensure_ascii=False, indent=4)

            # _____________ GET TRANS.NUMBER FROM 1C _____________
            result = get_transaction_number(result, connection=connection)

            # _____________ ADD DETAILS TO JSON _____________
            from src.utils_html import result_add_details, details_from_result

            details: dict | None = details_from_result(result)
            result = result_add_details(result, details)

            # _____________ CONVERT VALUES TO STRING _____________
            result = json.dumps(convert_json_values_to_strings(json.loads(result)), ensure_ascii=False, indent=4)

            # _____________ ORDER RESULT JSON KEYS _____________
            result = order_keys(result)

            # _____ * SAVE JSON FILE * _____
            local_check_folder = os.path.join(date_folder, text_or_scanned_folder, folder_name)
            os.makedirs(local_check_folder, exist_ok=False)
            json_path = os.path.join(date_folder, config['NAME_verified'], json_name)
            with open(json_path, 'w', encoding='utf-8') as file:
                file.write(result)

            # _____ * COPY ORIGINAL FILE | COPY EXTRA FILES * _____
            with open(os.path.join(folder, 'params.json'), 'r', encoding='utf-8') as f:
                params_dict = json.load(f)
                original_file = params_dict['main_file']
                extra_files = params_dict['extra_files']
            shutil.copy(original_file, os.path.join(local_check_folder, os.path.basename(original_file)))

            os.makedirs(os.path.join(local_check_folder, 'extra_files'), exist_ok=True)
            for file in extra_files:
                shutil.copy(file, os.path.join(local_check_folder, 'extra_files', os.path.basename(file)))

            # _____ * CREATE HTML FILE * _____
            html_name = os.path.basename(local_check_folder) + '.html'
            html_path = os.path.join(local_check_folder, html_name)
            create_html_form(json_path, html_path, original_file)

            # _____ clear temp variable current_file_params _____
            current_file_params.clear()

            # _____  STOP ITERATION  _____
            stop = next(c)
            if stop_when > 0:
                if stop == stop_when:
                    break

        except PermissionDeniedError:
            raise
        except Exception as error:
            logger.print('ERROR!:', error)
            logger.print(traceback.format_exc())
            continue

    # _____  RESULT MESSAGE  _____
    return (f'Сохранено {stop} x 3 = {stop * 3} '
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
    parser.add_argument('--text_to_assistant', action='store_true', help='Обрабатывать цифровые pdf ассистентом')
    parser.add_argument('--use_com_connector', action='store_true', help='Использовать COM объект')
    parser.add_argument('--ignore_connection', action='store_true', help='Не обращаться в ЦУП')
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
                              use_com_connector=args.use_com_connector,
                              ignore_connection=args.ignore_connection,
                              stop_when=args.stop_when)
        logger.print(f'\nresult_message:\n{result_message}\n')
    except PermissionDeniedError:
        logger.print(traceback.format_exc())
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
