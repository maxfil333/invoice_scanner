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

from config.config import config, running_params, NAMES
from config.project_config import main as project_postprocessing
from src.logger import logger
from src.connector import create_connection
from src.main_edit import main as main_edit
from src.utils_openai import pdf_to_ai, excel_to_ai, images_to_ai, extra_excel_to_ai, title_page_to_ai, pdf_to_ai_details
from src.response_postprocessing import local_postprocessing
from src.transactions import get_transaction_number
from src.generate_html import create_html_form
from src.utils import create_vector_database, balance_remainders_intact, create_date_folder_in_check
from src.utils import split_by_local_field, split_by_dt, combined_split_by_conos, combined_split_by_reports, distribute_conversion
from src.utils import order_goods, cleanup_empty_fields, order_keys, convert_json_values_to_strings


def main(date_folder: str,
         hide_logs: bool = False,
         test_mode: bool = False,
         use_existing: bool = False,
         text_to_assistant: bool = False,
         use_com_connector: bool = False, ignore_connection: bool = False, stop_when: int = 0):
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
        files = [file for file in files if os.path.splitext(file)[-1] in config['valid_ext'] + config['excel_ext']]

        with open(os.path.join(folder, 'params.json'), 'r', encoding='utf-8') as f:
            params_dict = json.load(f)
            original_file: str = params_dict['main_file']
            extra_files: list = params_dict['extra_files']

        try:
            # _____  CREATE JSON  _____
            logger.print('-' * 30)
            logger.print('\nedited.folder:', folder, sep='\n')
            logger.print('edited.files:', *files, sep='\n')
            json_name = folder_name + '_' + '0' * 11 + '.json'

            # _____________ RUN MAIN_OPENAI.PY _____________
            if os.path.splitext(files[0])[-1].lower() == '.pdf':  # достаточно проверить 1-й файл, чтобы определить .ext
                pdf_file = files[0]
                result_no_details = pdf_to_ai(pdf_file, test_mode, text_to_assistant, config, running_params,
                                              response_format=config['no_details_response_format'])
                result_details = pdf_to_ai_details(pdf_file, test_mode, text_to_assistant, config, running_params)
                full_result = json.loads(result_details) | json.loads(result_no_details)
                result = json.dumps(full_result, ensure_ascii=False)
            elif os.path.splitext(files[0])[-1].lower() in config['excel_ext']:
                excel_file = files[0]
                result = excel_to_ai(excel_file, test_mode, text_to_assistant, config, running_params)
            else:
                result = images_to_ai(files, test_mode, text_to_assistant, config, running_params)

            # _____________________ RUN MAIN_OPENAI.PY (EXCEL FILE) _____________________
            # если основной файл не excel
            if not os.path.splitext(files[0])[-1].lower() in config['excel_ext']:
                extra_excel_result = extra_excel_to_ai(extra_files, test_mode, text_to_assistant, config, running_params)
                if extra_excel_result:
                    logger.print("REPLACING GOODS FROM EXCEL ...")
                    result_dct = json.loads(result)
                    excel_result_dct = json.loads(extra_excel_result)
                    result_dct[NAMES.goods] = excel_result_dct[NAMES.goods]  # replace common-goods by excel-goods
                    result = json.dumps(result_dct, ensure_ascii=False)

            # _____________________ RUN MAIN_OPENAI (TITLE FILE) _____________________
            if os.path.exists(os.path.join(folder, config['EDITED_title_page'])):
                title_folder_files = os.listdir(os.path.join(folder, config['EDITED_title_page']))
                if title_folder_files:
                    title_file = os.path.join(folder, config['EDITED_title_page'], title_folder_files[0])
                    title_result = title_page_to_ai(title_file, test_mode, text_to_assistant, config, running_params)
                    if title_result:
                        logger.print("REPLACING TITLE FROM TITLE_PAGE ...")
                        result_dct = json.loads(result)
                        title_result_dct = json.loads(title_result)
                        result_dct[NAMES.invoice_number] = title_result_dct[NAMES.invoice_number]
                        result_dct[NAMES.invoice_date] = title_result_dct[NAMES.invoice_date]
                        result_dct[NAMES.supplier] = title_result_dct[NAMES.supplier]
                        result_dct[NAMES.customer] = title_result_dct[NAMES.customer]
                        result = json.dumps(result_dct, ensure_ascii=False)
                        running_params['title_fixed'] = True

            # _____________________ LOGS _____________________
            logger.print('openai result:\n', repr(result))
            with open(os.path.join(config['CONFIG'], 'openai_response_log.json'), 'w', encoding='utf-8') as f:
                json.dump(json.loads(result), f, ensure_ascii=False, indent=4)

            # _____________ LOCAL POSTPROCESSING _____________
            result = local_postprocessing(result, hide_logs=hide_logs, folder=folder)

            if result is None:
                continue

            # _____________ PROJECT PROCESSING _____________
            result = project_postprocessing(result)

            # _____________ SPLIT BY CONTAINERS _____________
            original_goods = json.loads(result)[NAMES.goods]
            result, cont_edited = split_by_local_field(result=result, loc_field_name=NAMES.cont, was_edited=[])

            # _____________ SPLIT BY REPORT _____________
            report_edited = None
            if not cont_edited:  # если не было распределения по контейнерам
                if json.loads(result)[NAMES.add_info][NAMES.reports]:
                    result, report_edited = combined_split_by_reports(json_str=result, was_edited=[])

            # _____________ SPLIT BY DT _____________
            dt_edited = None
            if not cont_edited and not report_edited:  # если не было распределения по контейнерам/заключениям
                if json.loads(result)[NAMES.add_info][NAMES.dt]:
                    result, dt_edited = split_by_dt(result)

            # _____________ SPLIT BY CONOSES _____________
            if not report_edited and not dt_edited:  # если не было распределения по заключениям/ДТ
                if len(cont_edited) < len(original_goods):  # если есть услуги, которые не были split
                    if json.loads(result)[NAMES.add_info][NAMES.conos]:
                        result, was_edited = combined_split_by_conos(result, cont_edited)

            # _____________ BALANCE REMAINDERS _____________
            result = balance_remainders_intact(result)

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
            local_check_folder: str = os.path.join(date_folder, running_params['text_or_scanned_folder'], folder_name)
            os.makedirs(local_check_folder, exist_ok=False)
            json_path = os.path.join(date_folder, config['NAME_verified'], json_name)
            with open(json_path, 'w', encoding='utf-8') as file:
                file.write(result)

            # _____ * COPY ORIGINAL FILE | COPY EXTRA FILES * _____
            shutil.copy(original_file, os.path.join(local_check_folder, os.path.basename(original_file)))

            os.makedirs(os.path.join(local_check_folder, 'extra_files'), exist_ok=True)
            for file in extra_files:
                shutil.copy(file, os.path.join(local_check_folder, 'extra_files', os.path.basename(file)))

            # _____ * CREATE HTML FILE * _____
            html_name = os.path.basename(local_check_folder) + '.html'
            html_path = os.path.join(local_check_folder, html_name)
            create_html_form(json_path, html_path, original_file)

            # _____ clear temp variable running_params _____
            running_params.clear()

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
    return (f'Обработано счетов: {stop}'
            f'\n{date_folder}')


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
        logger.print(f'\n{result_message}\n')
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
