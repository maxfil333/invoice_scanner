import openai
from langchain_openai import OpenAIEmbeddings

import os
import re
import json
import inspect
import difflib
import numpy as np
from PIL import Image
from dotenv import load_dotenv
from typing import Union, Literal
from win32com.client import CDispatch

from src.logger import logger
from config.config import config, NAMES, current_file_params
from src.crop_tables import extract_text_from_image
from src.connector import cup_http_request, response_to_deals
from src.utils import chroma_similarity_search, is_without_nds, is_invoice
from src.utils import convert_json_values_to_strings, handling_openai_json
from src.utils import replace_container_with_latin, replace_container_with_none, switch_to_latin, remove_dates
from src.utils import get_stream_dotenv, check_sums, propagate_nds, order_goods, sort_transactions

load_dotenv(stream=get_stream_dotenv())


# ___________________________________________ HANDLING OPENAI OUTPUT (JSON) ___________________________________________

def local_postprocessing(response, **kwargs) -> str | None:
    re_response = handling_openai_json(response)
    if re_response is None:
        return None
    logger.print(f'function "{inspect.stack()[1].function}":')
    logger.print('re_response:\n', repr(re_response))
    dct = json.loads(re_response)
    dct = convert_json_values_to_strings(dct)

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
        logger.print(f"--- DB response {i_ + 1} ---:")

        query = replace_container_with_none(good_dct[NAMES.name], container_regex)
        query = remove_dates(query)
        # query = re.sub(r'[^\s\w]', '', query)  # убираем спец символы: влияют на смысл больше чем нужно
        logger.print(f"query:\n{query}")

        relevant_results = chroma_similarity_search(query=query,
                                                    chroma_path=config['chroma_path'],
                                                    embedding_func=embedding_func,
                                                    k=1)
        if relevant_results:
            # берем первый (наиболее вероятный) элемента из списка результатов поиска
            relevant_result = relevant_results[0]
            score = relevant_result[1]
            if score < config['similarity_threshold']:
                good_dct['Услуга1С'] = config['not_found_service']
            else:
                comment_id, comment_content = relevant_result[0].metadata['id'], relevant_result[0].page_content

                # id в каждом словарике {id:.., comment:.., service_code:..} совпадает с порядковым номером словарика
                uniq_comments_dct_by_idx = config['unique_comments_dict'][comment_id]  # {id:, comment:, service_code: }
                logger.print(f"response:\n{uniq_comments_dct_by_idx}")

                # берем первый "service#code#" в ключе "service_code" элемента словаря с индексом comment_id,
                # заполняем поле "Услуга1С"
                good_dct['Услуга1С'] = uniq_comments_dct_by_idx['service_code'][0]
            logger.print(f"score: {score} found service: {good_dct['Услуга1С']}")

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
        logger.print(f'!! ОШИБКА В CHECK_SUMS: {error} !!')

    # 6.1. уточнение НДС (0.0 или "Без НДС")
    if float(dct[NAMES.total_nds]) == 0:
        if is_without_nds(current_text):  # classify current text
            dct[NAMES.nds_percent] = NAMES.noNDS

    # 6.2. split nds
    dct = propagate_nds(dct)

    # 7. order dct['Услуги']
    dct = order_goods(dct, config['services_order'])

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

    # 10. Коносаменты from list to string: ["RU0163 075", "CO-NC94999", "CONOS 88"] -> "CO-NC94999 CONOS88 RU0163075"
    list_of_conos = list(set(map(lambda x: x.replace(' ', ''), dct['additional_info']['Коносаменты'])))
    dct['additional_info']['Коносаменты'] = " ".join(list(filter(lambda x: x not in containers and x not in DT_copy,
                                                                 list_of_conos)))

    for i_, good_dct in enumerate(dct[NAMES.goods]):
        original_name = good_dct[NAMES.name]  # Наименование
        conoses = dct['additional_info']['Коносаменты'].split()
        if conoses:
            conoses_regex = r'|'.join(conoses)  # регулярка формата r'RU1234|RU5678'
            list_of_conos = list(set([x for x in re.findall(conoses_regex, original_name) if x]))
            good_dct[NAMES.local_conos] = " ".join(list(filter(lambda x: x not in containers, list_of_conos)))
        else:
            good_dct[NAMES.local_conos] = ''

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


# ___________________________________________ ADD TRANSACTIONS TO RESULT ___________________________________________

def get_transaction_number(json_formatted_str: str, connection: Union[None, Literal['http'], CDispatch]) -> str:
    dct = json.loads(json_formatted_str)

    if not connection:
        # если нет соединения возвращаем что было плюс:
        # (1) dct['Номер сделки'] = []
        # (2) dct['Номер сделки (ввести свой)'] = ''
        # (3) dct['Тип поиска сделки'] = ''
        return json.dumps(dct, ensure_ascii=False, indent=4)

    # Вывести в доп.инфо список сделок для коносаментов
    conos_deals = []
    for conos in dct['additional_info']['Коносаменты'].split():
        if connection == 'http':
            conos_deals_ = cup_http_request('TransactionNumberFromBillOfLading', conos)
        else:
            numbers_CONOSES = connection.InteractionWithExternalApplications.TransactionNumberFromBillOfLading(conos)
            conos_deals_ = response_to_deals(numbers_CONOSES)
        conos_deals_ = [f"{deal} - {conos}" for deal in conos_deals_]
        conos_deals.extend(conos_deals_)
    dct['additional_info']['Сделки по коносаментам'] = '\n'.join(conos_deals)

    common_deals = []  # список ОБЩИХ сделок (найденных по контейнерам и коносаментам во всех услугах)
    history = []  # список индексов услуг, которые пытались найти сделку по контейнеру или коносаменту

    # проходим по услугам, где есть контейнер или коносамент
    for i, good_dct in enumerate(dct[NAMES.goods]):
        local_deals = []
        local_container = good_dct[NAMES.cont]
        local_conos = good_dct[NAMES.local_conos]

        # ЕСЛИ есть контейнер, берем список сделок по нему и идем к следующей услуге
        if local_container:
            if connection == 'http':
                deals_ = cup_http_request(r'TransactionNumberFromContainer', local_container)
            else:
                numbers_CONTAINERS = connection.InteractionWithExternalApplications.TransactionNumberFromContainer(
                    local_container)
                deals_ = response_to_deals(numbers_CONTAINERS)
            if deals_:
                local_deals.extend(deals_)
                common_deals.extend(deals_)
                good_dct[NAMES.transactions] = sort_transactions(local_deals)
                good_dct[NAMES.transactions_type] = 'CONTAINERS'
                history.append(i)

                # ______________ дополнительно смэтчим сделки от контейнеров со сделками от коносаментов _______________
                # если для данной позиции найдено сделок по контейнерам больше 1, и кол-во коносаментов = 1
                if len(local_deals) > 1 and len(local_conos.split()) == 1:
                    # берем сделки по этому коносаменту (m_deals)
                    if connection == 'http':
                        m_deals_ = cup_http_request(r'TransactionNumberFromBillOfLading', local_conos)
                    else:
                        m_CONOSES = connection.InteractionWithExternalApplications.TransactionNumberFromBillOfLading(
                            local_conos)
                        m_deals_ = response_to_deals(m_CONOSES)
                    # если нашли, находим общие со сделками по контейнерам, оставляем общие
                    if m_deals_:
                        deals_intersect = set(deals_).intersection(set(m_deals_))
                        if deals_intersect:
                            good_dct[NAMES.transactions] = sort_transactions(list(deals_intersect))
                            good_dct[NAMES.transactions_type] = 'CONTAINER+CONOS'
                # ______________________________________________________________________________________________________

                continue

        # ЕСЛИ нет контейнера, но есть коносамент, берем список сделок по нему и идем к следующей услуге
        if not local_deals and local_conos:
            if connection == 'http':
                deals_ = cup_http_request(r'TransactionNumberFromBillOfLading', local_conos)
            else:
                numbers_CONOSES = connection.InteractionWithExternalApplications.TransactionNumberFromBillOfLading(
                    local_conos)
                deals_ = response_to_deals(numbers_CONOSES)
            if deals_:
                local_deals.extend(deals_)
                common_deals.extend(deals_)
                good_dct[NAMES.transactions] = sort_transactions(local_deals)
                good_dct[NAMES.transactions_type] = 'CONOS'
                history.append(i)
                continue

    if len(history) == len(dct[NAMES.goods]):  # если обработаны все услуги
        logger.print('все услуги были найдены по контейнерам и коносаментам')
        return json.dumps(dct, ensure_ascii=False, indent=4)  # возврат

    if common_deals:  # если какие-то сделки по контейнерам/коносаментам уже найдены
        for i, good_dct in enumerate(dct[NAMES.goods]):  # то для каждой услуги где:
            if i not in history:  # не было контейнера или коносамента или сделка не была найдена
                good_dct[NAMES.transactions] = sort_transactions(list(set(common_deals)))  # сделки = общие сделки
                good_dct[NAMES.transactions_type] = ('нет конт-а/конос-а или сделка не найдена'
                                                     '(наследуется от найденных)')
            else:
                pass

    else:  # если не было найдено никаких сделок
        # извлекаем ОБЩИЕ параметры, по которым будет выполняться поиск номеров сделок (общие для всех позиций)
        SHIP = dct['additional_info']['Судно']
        # предварительно отформатированы разделителем-пробелом:
        DT = dct['additional_info']['ДТ'].split()
        AUTOS = dct['additional_info']['Номера_Авто'].split()
        TRAILERS = dct['additional_info']['Номера_Прицепов'].split()

        # ищем сделки
        common_deals = []
        transactions_type = ''

        # поиск сделки по ДТ
        if DT:
            common_deals = []
            for dt in DT:
                if connection == 'http':
                    deals_ = cup_http_request(r'TransactionNumberFromGTD', dt)
                else:
                    numbers_DT = connection.InteractionWithExternalApplications.TransactionNumberFromGTD(dt)
                    deals_ = response_to_deals(numbers_DT)
                if deals_:
                    common_deals.extend(deals_)
            if common_deals:
                transactions_type = 'DT'

        # поиск сделки по ТХ
        if not common_deals and SHIP:
            if connection == 'http':
                common_deals = cup_http_request(r'TransactionNumberFromShip', SHIP)
            else:
                numbers_SHIP = connection.InteractionWithExternalApplications.TransactionNumberFromShip(SHIP)
                common_deals = response_to_deals(numbers_SHIP)
            if common_deals:
                transactions_type = 'SHIP'

        # поиск сделки по номеру авто
        if not common_deals and AUTOS:
            common_deals = []
            for AUTO in AUTOS:
                if connection == 'http':
                    deals_ = cup_http_request(r'TransactionNumberFromCar', AUTO)
                else:
                    numbers_AUTOS = connection.InteractionWithExternalApplications.TransactionNumberFromCar(AUTO)
                    deals_ = response_to_deals(numbers_AUTOS)
                if deals_:
                    common_deals.extend(deals_)
            if common_deals:
                transactions_type = 'AUTO'

        # поиск сделки по номеру прицепа
        if not common_deals and TRAILERS:
            common_deals = []
            for TRAILER in TRAILERS:
                if connection == 'http':
                    deals_ = cup_http_request(r'TransactionNumberFromCarTrailer', TRAILER)
                else:
                    numbers_TRAILERS = connection.InteractionWithExternalApplications.TransactionNumberFromCarTrailer(
                        TRAILER)
                    deals_ = response_to_deals(numbers_TRAILERS)
                if deals_:
                    common_deals.extend(deals_)
            if common_deals:
                transactions_type = 'TRAILER'

        # для каждой услуги заполняем "Номер сделки" и "Тип сделки" (будут одинаковы для всех услуг)
        for good_dct in dct[NAMES.goods]:
            good_dct[NAMES.transactions] = sort_transactions(common_deals)  # список сделок = список общих сделок
            good_dct[NAMES.transactions_type] = transactions_type

    return json.dumps(dct, ensure_ascii=False, indent=4)
