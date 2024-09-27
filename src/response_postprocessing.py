import openai
from langchain_openai import OpenAIEmbeddings

import os
import re
import json
import inspect
import difflib
from datetime import datetime
from dotenv import load_dotenv

from src.logger import logger
from config.config import config, NAMES
from src.connector import cup_http_request, response_to_deals
from src.utils import convert_json_values_to_strings, handling_openai_json
from src.utils import chroma_get_relevant, get_stream_dotenv, check_sums, order_goods
from src.utils import replace_container_with_latin, replace_container_with_none, switch_to_latin

load_dotenv(stream=get_stream_dotenv())


# ____________________________________ HANDLING OPENAI OUTPUT (JSON) ____________________________________

def local_postprocessing(response, hide_logs=False) -> str | None:
    re_response = handling_openai_json(response, hide_logs)
    if re_response is None:
        return None
    if not hide_logs:
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
    embedding_func = OpenAIEmbeddings()

    for i_, good_dct in enumerate(dct[NAMES.goods]):

        name = good_dct[NAMES.name]  # Наименование

        # 1 Сбор номеров авто и прицепов
        am_plates_ru.extend(
            list(map(lambda x: switch_to_latin(x, reverse=True).replace(' ', ''), re.findall(am_plate_regex, name)))
        )
        am_trailer_plates_ru.extend(
            list(map(lambda x: switch_to_latin(x, reverse=True).replace(' ', ''), re.findall(am_trailer_regex, name)))
        )

        # 2 Контейнеры
        # 2.1 Замена кириллицы в Наименование
        good_dct[NAMES.name] = replace_container_with_latin(name, container_regex)  # re.sub(pattern, repl, text)
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
        name_without_containers = replace_container_with_none(good_dct[NAMES.name], container_regex)
        idx_comment_tuples = chroma_get_relevant(query=name_without_containers,
                                                 chroma_path=config['chroma_path'],
                                                 embedding_func=embedding_func,
                                                 k=1)
        if idx_comment_tuples:
            # берем id и comment первого (наиболее вероятного) элемента из списка кортежей
            idx, comment = idx_comment_tuples[0]
            logger.print(f"--- DB response {i_ + 1} ---:")
            logger.print(f"query:\n{name_without_containers}")
            logger.print(f"response:\n{config['unique_comments_dict'][idx - 1]}")
            # берем первый "service" в ключе "service_list" элемента словаря с индексом idx-1
            good1C = config['unique_comments_dict'][idx - 1]['service_list'][0]
            # перезаписываем поле "Услуга1С"
            good_dct['Услуга1С'] = good1C

    # 6. check_sums
    try:
        dct = check_sums(dct)
    except Exception as error:
        dct['nds (%)'] = 0
        for good in dct[NAMES.goods]:
            del good[NAMES.price]
            del good[NAMES.sum_with]
            del good[NAMES.sum_nds]
            good["Цена (без НДС)"] = ""
            good["Сумма (без НДС)"] = ""
            good["Цена (с НДС)"] = ""
            good["Сумма (с НДС)"] = ""
            good["price_type"] = ""
        logger.print(f'!! ОШИБКА В CHECK_SUMS: {error} !!')

    # 7. order dct['Услуги']
    dct = order_goods(dct)

    # 8. AUTO | TRAILER
    dct['additional_info']['Номера_Авто'] = " ".join(am_plates_ru)
    dct['additional_info']['Номера_Прицепов'] = " ".join(am_trailer_plates_ru)

    # 9. Коносаменты from list to string: ["RU0163 075", "CO-NC94999", "CONOS 88"] -> "CO-NC94999 CONOS88 RU0163075"
    list_of_conos = list(set(map(lambda x: x.replace(' ', ''), dct['additional_info']['Коносаменты'])))
    dct['additional_info']['Коносаменты'] = " ".join(list(filter(lambda x: x not in containers, list_of_conos)))

    # 9. ДТ check regex
    dt_regex = r'\d{8}/\d{6}/\d{7}'
    if not re.fullmatch(dt_regex, dct['additional_info']['ДТ']):
        dct['additional_info']['ДТ'] = ''
    else:
        if dct['additional_info']['ДТ'] == dct['additional_info']['Коносаменты']:
            dct['additional_info']['Коносаменты'] = ''

    # 10. Судно
    ship = dct['additional_info']['Судно']
    closest_match = difflib.get_close_matches(ship.upper(), config['ships'], n=1, cutoff=0.7)
    if closest_match:
        dct['additional_info']['Судно'] = closest_match[0]
        logger.print(f'find ship: {ship} --> {closest_match[0]}')

    string_dictionary = convert_json_values_to_strings(dct)
    return json.dumps(string_dictionary, ensure_ascii=False, indent=4)


# ____________________________________ ADD TRANSACTIONS TO RESULT ____________________________________

def get_transaction_number(json_formatted_str: str, connection) -> str:
    dct = json.loads(json_formatted_str)
    dct[NAMES.transactions] = []
    dct[NAMES.transactions_new] = ''
    dct[NAMES.transactions_type] = ''

    # если нет соединения возвращаем что было + dct['Номера сделок'] = []; + dct['Тип поиска сделки'] = ''.
    if not connection:
        return json.dumps(dct, ensure_ascii=False, indent=4)

    # извлекаем параметры, по которым будет выполняться поиск номеров сделок
    DT = dct['additional_info']['ДТ']
    CONTAINERS = []
    for good in dct[NAMES.goods]:
        CONTAINERS.extend(good[NAMES.cont].split())
    CONTAINERS = [x for x in CONTAINERS if x]
    CONOSES = dct['additional_info']['Коносаменты'].split()  # предварительно отформатированы разделителем-пробелом
    SHIP = dct['additional_info']['Судно']
    AUTOS = dct['additional_info']['Номера_Авто'].split()  # предварительно отформатированы разделителем-пробелом
    TRAILERS = dct['additional_info']['Номера_Прицепов'].split()  # предварительно отформатированы разделителем-пробелом

    deals = []

    if DT:
        if connection == 'http':
            deals = cup_http_request(r'TransactionNumberFromGTD', DT)
        else:
            numbers_DT = connection.InteractionWithExternalApplications.TransactionNumberFromGTD(DT)
            deals = response_to_deals(numbers_DT)
        if deals:
            dct[NAMES.transactions_type] = 'DT'

    if not deals and CONTAINERS:
        deals = []
        for CONTAINER in CONTAINERS:
            if connection == 'http':
                deals_ = cup_http_request(r'TransactionNumberFromContainer', CONTAINER)
            else:
                numbers_CONTAINERS = connection.InteractionWithExternalApplications.TransactionNumberFromContainer(
                    CONTAINER)
                deals_ = response_to_deals(numbers_CONTAINERS)
            if deals_:
                deals.extend(deals_)
        if deals:
            dct[NAMES.transactions_type] = 'CONTAINERS'

    if not deals and CONOSES:
        deals = []
        for CONOS in CONOSES:
            if connection == 'http':
                deals_ = cup_http_request(r'TransactionNumberFromBillOfLading', CONOS)
            else:
                numbers_CONOSES = connection.InteractionWithExternalApplications.TransactionNumberFromBillOfLading(
                    CONOS)
                deals_ = response_to_deals(numbers_CONOSES)
            if deals_:
                deals.extend(deals_)
        if deals:
            dct[NAMES.transactions_type] = 'CONOS'

    if not deals and SHIP:
        if connection == 'http':
            deals = cup_http_request(r'TransactionNumberFromShip', SHIP)
        else:
            numbers_SHIP = connection.InteractionWithExternalApplications.TransactionNumberFromShip(SHIP)
            deals = response_to_deals(numbers_SHIP)
        if deals:
            dct[NAMES.transactions_type] = 'SHIP'

    if not deals and AUTOS:
        deals = []
        for AUTO in AUTOS:
            if connection == 'http':
                deals_ = cup_http_request(r'TransactionNumberFromCar', AUTO)
            else:
                numbers_AUTOS = connection.InteractionWithExternalApplications.TransactionNumberFromCar(AUTO)
                deals_ = response_to_deals(numbers_AUTOS)
            if deals_:
                deals.extend(deals_)
        if deals:
            dct[NAMES.transactions_type] = 'AUTO'

    if not deals and TRAILERS:
        deals = []
        for TRAILER in TRAILERS:
            if connection == 'http':
                deals_ = cup_http_request(r'TransactionNumberFromCarTrailer', TRAILER)
            else:
                numbers_TRAILERS = connection.InteractionWithExternalApplications.TransactionNumberFromCarTrailer(
                    TRAILER)
                deals_ = response_to_deals(numbers_TRAILERS)
            if deals_:
                deals.extend(deals_)
        if deals:
            dct[NAMES.transactions_type] = 'TRAILER'

    if deals:
        regex = r'(.*) (от) (.*)'
        deals = list(set(deals))
        deals.sort(
            key=lambda x: datetime.strptime(re.fullmatch(regex, x).group(3), '%d.%m.%Y').date() if re.fullmatch(
                regex, x) else datetime.fromtimestamp(0).date(), reverse=True)

        dct[NAMES.transactions] = deals

    return json.dumps(dct, ensure_ascii=False, indent=4)
