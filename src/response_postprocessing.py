import openai
from langchain_openai import OpenAIEmbeddings

import os
import re
import json
import inspect
import difflib
import traceback
import numpy as np
from PIL import Image
from dotenv import load_dotenv

from src.logger import logger
from config.config import config, NAMES, current_file_params
from src.crop_tables import extract_text_from_image
from src.utils import chroma_similarity_search, is_without_nds, is_invoice, perfect_similarity, switch_to_latin
from src.utils import convert_json_values_to_strings, handling_openai_json
from src.utils import replace_container_with_latin, replace_container_with_none, remove_dates
from src.utils import check_sums, propagate_nds, replace_conos_with_none, replace_ship_with_none
from src.utils_config import get_stream_dotenv
from src.utils import delete_NER, delete_en_loc

load_dotenv(stream=get_stream_dotenv())


# ___________________________________________ HANDLING OPENAI OUTPUT (JSON) ___________________________________________

def local_postprocessing(response, **kwargs) -> str | None:
    re_response = handling_openai_json(response)
    if re_response is None:
        return None
    logger.print(f'function "{inspect.stack()[1].function}":')
    dct = json.loads(re_response)
    dct = convert_json_values_to_strings(dct)

    additional_info: dict = dct['additional_info']
    container_regex = r'[A-ZА-Я]{3}U\s?[0-9]{6}-?[0-9]'
    container_regex_lt = r'[A-Z]{3}U\s?[0-9]{6}-?[0-9]'
    am_plate_regex = r'[АВЕКМНОРСТУХABEKMHOPCTYX]{1}\s{0,3}\d{3}\s*[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\s{0,3}\d{2,3}'
    am_plates_ru = []
    am_trailer_regex = r'\b[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\s{0,3}\d{4}\s{0,3}\d{2,3}\b'
    am_trailer_plates_ru = []
    containers = []

    load_dotenv(stream=get_stream_dotenv())
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    embedding_func = OpenAIEmbeddings(model=config['embedding_model'])

    # __________ CURRENT TEXT __________

    # если текст был извлечен из PDF с помощью fitz в run_chat или в run_assistant
    if current_file_params.get('current_texts', None):
        texts = current_file_params['current_texts']
        current_text = '\n'.join(texts)
        current_text_page0 = texts[0]

    # если из PDF нельзя извлечь (image OR scanned)
    else:
        edited_folder = kwargs.get('folder')
        with open(os.path.join(edited_folder, 'params.json'), 'r', encoding='utf-8') as params_file:
            params_dict = json.load(params_file)
            main_local_files = params_dict['main_local_files']

        current_text = ''
        current_text_page0 = ''
        for i, local_file in enumerate(main_local_files):
            current_text += extract_text_from_image(np.array(Image.open(local_file)))
            if i == 0:
                current_text_page0 = current_text

    # СЧЕТ / НЕ СЧЕТ
    is_inv = is_invoice(current_text_page0)

    if is_inv is True:
        dct['Тип документа'] = 'Счет'
    elif is_inv is False:
        dct['Тип документа'] = 'Другое'
    elif is_inv is None:
        dct['Тип документа'] = 'Неизвестно'

    # currency
    currency = dct['Валюта документа']  # распознанная валюта
    currency_dict = config['currency_dict']  # словарь валют с кодами
    dct['Валюта документа'] = currency_dict[currency]  # распознанная валюта -> валюта с кодом

    # конвертация
    if currency == "РУБ":
        additional_info['Конвертация'] = 0
    else:
        additional_info['Конвертация'] = int(float(additional_info['Конвертация']))

    # Услуги

    for i_, good_dct in enumerate(dct[NAMES.goods]):

        original_name = good_dct[NAMES.name]  # Наименование

        # 1 Сбор номеров авто и прицепов
        am_plates_ru.extend(
            list(map(lambda x: switch_to_latin(x, reverse=True).replace(' ', ''),
                     re.findall(am_plate_regex, original_name)))
        )
        am_trailer_plates_ru.extend(
            list(map(lambda x: switch_to_latin(x, reverse=True).replace(' ', ''),
                     re.findall(am_trailer_regex, original_name)))
        )

        # 2 Контейнеры
        # 2.1 Замена кириллицы в Наименование
        good_dct[NAMES.name] = replace_container_with_latin(original_name,
                                                            container_regex)  # re.sub(pattern, repl, text)
        name = good_dct[NAMES.name]
        # Найти контейнеры, оставить уникальные
        containers_name = list(map(lambda x: re.sub(r'[\s\-]', '', x), re.findall(container_regex_lt, name)))
        uniq_containers_from_name = list(dict.fromkeys(containers_name))

        # 2.2 Замена кириллицы в Контейнеры
        cont = good_dct[NAMES.cont]
        good_dct[NAMES.cont] = replace_container_with_latin(cont, container_regex)
        cont = good_dct[NAMES.cont]
        containers_cont = list(map(lambda x: re.sub(r'[\s\-]', '', x), re.findall(container_regex_lt, cont)))
        uniq_containers_from_cont = list(dict.fromkeys(containers_cont))

        # 2.3 Объединить
        for con in uniq_containers_from_name:
            if con not in uniq_containers_from_cont:
                uniq_containers_from_cont.append(con)
        good_dct[NAMES.cont] = ' '.join(uniq_containers_from_cont)
        containers.extend(uniq_containers_from_cont)

        # 3. Количество, Единица измерения (очистка от лишних символов)
        amount = good_dct[NAMES.amount]
        good_dct[NAMES.amount] = re.sub(r'[^\d.]', '', amount).strip('.')
        unit = good_dct[NAMES.unit]
        good_dct[NAMES.unit] = re.sub(r'[^a-zA-Zа-яА-Я]', '', unit)

        # 4. добавление 'Услуга1С'
        good_dct[NAMES.good1C] = ''
        good_dct[NAMES.good1C_new] = ''

        # 5. заполнение 'Услуга1С'
        logger.print(f"------ DB response {i_ + 1} ------:")

        query = replace_container_with_none(good_dct[NAMES.name], container_regex)
        query = remove_dates(query)
        query = replace_conos_with_none(query, additional_info['Коносаменты'])
        query = replace_ship_with_none(query, additional_info['Судно'])

        # query = re.sub(r'[^\s\w]', '', query)  # убираем спец символы: влияют на смысл больше чем нужно
        logger.print(f"query:\n{query}")

        # 5.0 DIFFLIB (PERFECT MATCH)
        perfect_result = None
        data = config.get('all_services_dict')
        if data:
            perfect_result = perfect_similarity(query, data)
            if perfect_result:
                service, code = perfect_result['service'], perfect_result['code']
                # заполняем поле "Услуга1С"
                good_dct['Услуга1С'] = f"{service}#{code}"
                logger.print(f"--- perfect match ---")
                logger.print(f"response:\n{perfect_result}")

        # 5.5 CHROMA (FULL SEARCH)
        if not perfect_result:

            def fill_in_service1c(good_dct: dict, prefix='') -> None:
                comment_id, comment_content = relevant_result[0].metadata['id'], relevant_result[0].page_content
                # id в каждом словарике {id:.., comment:.., service_code:..} совпадает с порядковым ном. словарика
                uniq_comments_dct_by_idx = config['unique_comments_dict'][comment_id]
                # > {id:, comment:, service_code: }
                logger.print(f"{prefix}response:\n{uniq_comments_dct_by_idx}")

                # берем первый "service#code#" в ключе "service_code" элемента словаря с индексом comment_id,
                # заполняем поле "Услуга1С"
                good_dct['Услуга1С'] = uniq_comments_dct_by_idx['service_code'][0]
                logger.print(f"{prefix}score: {score} found service: {good_dct['Услуга1С']}")

            good_dct['Услуга1С'] = config['not_found_service']
            relevant_results = chroma_similarity_search(query=query,
                                                        chroma_path=config['chroma_path'],
                                                        embedding_func=embedding_func,
                                                        k=1)
            if relevant_results:
                # берем первый (наиболее вероятный) элемента из списка результатов поиска
                relevant_result = relevant_results[0]
                score = relevant_result[1]
                if score >= config['high_threshold']:
                    fill_in_service1c(good_dct=good_dct)  # если высокая уверенность, заполняем Услуга1С сразу

                elif config['low_threshold'] <= score < config['high_threshold']:
                    ner_cleaned_query = delete_NER(delete_en_loc(query))
                    logger.print(f"geoquery:\n{ner_cleaned_query}")
                    relevant_results = chroma_similarity_search(query=ner_cleaned_query,
                                                                chroma_path=config['chroma_path'],
                                                                embedding_func=embedding_func,
                                                                k=1)
                    if relevant_results:
                        # берем первый (наиболее вероятный) элемента из списка результатов поиска
                        relevant_result = relevant_results[0]
                        score = relevant_result[1]
                        if score >= config['low_threshold']:
                            fill_in_service1c(good_dct, prefix='geo')  # если средняя уверенность, убираем географию
                        else:
                            logger.print(f"geoTHRESHOLD TRIMMED: score: {score}")
                else:
                    logger.print(f"THRESHOLD TRIMMED: score: {score}")

        # 6. Добавить local_transaction, local_transactions_new, local_transaction_type
        good_dct[NAMES.transactions] = []
        good_dct[NAMES.transactions_new] = ''
        good_dct[NAMES.transactions_type] = ''

    # 6. check_sums
    try:
        dct = check_sums(dct)
    except Exception as error:
        dct[NAMES.nds_percent] = 0
        for good in dct[NAMES.goods]:
            good.pop(NAMES.price, None)
            good.pop(NAMES.sum_with, None)
            good.pop(NAMES.sum_nds, None)
            good["Цена (без НДС)"] = ""
            good["Сумма (без НДС)"] = ""
            good["Цена (с НДС)"] = ""
            good["Сумма (с НДС)"] = ""
            good["price_type"] = ""
        logger.print(f'!! ОШИБКА В CHECK_SUMS: {error} !!', traceback.format_exc())

    # 6.1. уточнение НДС (0.0 или "Без НДС")
    if float(dct[NAMES.total_nds]) == 0:
        if is_without_nds(current_text):  # classify current text
            dct[NAMES.nds_percent] = NAMES.noNDS

    # 6.2. split nds
    dct = propagate_nds(dct)

    # 8. AUTO | TRAILER
    dct['additional_info']['Номера_Авто'] = " ".join(am_plates_ru)
    dct['additional_info']['Номера_Прицепов'] = " ".join(am_trailer_plates_ru)

    # 9. ДТ check regex
    DT_copy = dct['additional_info']['ДТ'].copy()  # изначальный список ДТ (копия)
    dt_regex = r'\d{8}/\d{6}/\d{7}'  # регулярка для проверки ДТ
    for dt in DT_copy:
        if not re.fullmatch(dt_regex, dt):
            dct['additional_info']['ДТ'].remove(dt)

    dct['additional_info']['ДТ'] = " ".join(dct['additional_info']['ДТ'])  # ДТ from list to string

    # 10. Коносаменты
    if not dct['additional_info']['Коносаменты']:
        dct['additional_info']['Коносаменты'] = ''
    else:
        # Коносаменты from list to string: ["RU0163 075", "CO-NC94999", "CONOS 88"] -> "CO-NC94999 CONOS88 RU0163075"
        list_of_conos = list(set(map(lambda x: x.replace(' ', ''), dct['additional_info']['Коносаменты'])))
        # Убираем из кс контейнеры и ДТ, которые могли случайно попасть в кс
        dct['additional_info']['Коносаменты'] = " ".join(list(filter(lambda x: x not in containers and x not in DT_copy,
                                                                     list_of_conos)))
        # Заполняем "Коносаменты (для услуги)" на основе "Наименования"
        for i_, good_dct in enumerate(dct[NAMES.goods]):
            original_name = good_dct[NAMES.name]  # Наименование
            conoses = dct['additional_info']['Коносаменты'].split()
            conoses_regex = r'|'.join(conoses)  # регулярка формата 'RU1234|RU5678|...'
            list_of_conos = list(set([x for x in re.findall(conoses_regex, original_name) if x]))

            # INIT local_conos
            if list_of_conos:
                good_dct[NAMES.local_conos] = " ".join(list(filter(lambda x: x not in containers, list_of_conos)))
            else:
                good_dct[NAMES.local_conos] = ''

    # 10.5 Заключения
    if not dct['additional_info']['Заключения']:
        dct['additional_info']['Заключения'] = ''
    else:
        dct['additional_info']['Заключения'] = list(set(map(lambda x: x.replace(' ', ''),
                                                            dct['additional_info']['Заключения'])))
        report_copy = dct['additional_info']['Заключения'].copy()  # изначальный список Заключений (копия)
        report_regex = r'\d{6}-\d{3}-\d{2}'  # регулярка для проверки ДТ
        for report in report_copy:
            if not re.fullmatch(report_regex, report):
                dct['additional_info']['Заключения'].remove(report)

        dct['additional_info']['Заключения'] = " ".join(dct['additional_info']['Заключения'])  # from list to string
        # Заполняем "Заключения (для услуги)" на основе "Наименования"
        for i_, good_dct in enumerate(dct[NAMES.goods]):
            original_name = good_dct[NAMES.name]  # Наименование
            reports = dct['additional_info'][NAMES.reports].split()
            reports_regex = r'|'.join(reports)  # регулярка формата 'FOO|BAR|...'
            list_of_reports = list(set([x for x in re.findall(reports_regex, original_name) if x]))

            # INIT local_reports
            if list_of_reports:
                good_dct[NAMES.local_reports] = " ".join(list_of_reports)
            else:
                good_dct[NAMES.local_reports] = ''

    # 11. Судно
    ship = dct['additional_info']['Судно']
    closest_match = difflib.get_close_matches(ship.upper(), config['ships'], n=1, cutoff=0.7)
    if closest_match:
        dct['additional_info']['Судно'] = closest_match[0]
        logger.print(f'find ship: {ship} --> {closest_match[0]}')

    # 12. Идентификатор исходной позиции
    initial_id_counter = 1
    for i_, good_dct in enumerate(dct[NAMES.goods]):
        good_dct['__исходный_айди'] = f"{initial_id_counter}|{good_dct['Сумма (без НДС)']}|{good_dct['Сумма (с НДС)']}"
        initial_id_counter += 1

    string_dictionary = convert_json_values_to_strings(dct)
    return json.dumps(string_dictionary, ensure_ascii=False, indent=4)
