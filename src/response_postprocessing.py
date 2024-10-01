import openai
from langchain_openai import OpenAIEmbeddings

import os
import re
import json
import inspect
import difflib
from dotenv import load_dotenv
from typing import Union, Literal
from win32com.client import CDispatch

from src.logger import logger
from config.config import config, NAMES
from src.connector import cup_http_request, response_to_deals
from src.utils import convert_json_values_to_strings, handling_openai_json
from src.utils import chroma_get_relevant, get_stream_dotenv, check_sums, order_goods
from src.utils import replace_container_with_latin, replace_container_with_none, switch_to_latin, sort_transactions

load_dotenv(stream=get_stream_dotenv())


# ___________________________________________ HANDLING OPENAI OUTPUT (JSON) ___________________________________________

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

        # 6. Добавить local_transaction, local_transactions_new, local_transaction_type
        good_dct[NAMES.transactions] = []
        good_dct[NAMES.transactions_new] = ''
        good_dct[NAMES.transactions_type] = ''

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
    dct = order_goods(dct, config['services_order'])

    # 8. AUTO | TRAILER
    dct['additional_info']['Номера_Авто'] = " ".join(am_plates_ru)
    dct['additional_info']['Номера_Прицепов'] = " ".join(am_trailer_plates_ru)

    # 9. Коносаменты from list to string: ["RU0163 075", "CO-NC94999", "CONOS 88"] -> "CO-NC94999 CONOS88 RU0163075"
    list_of_conos = list(set(map(lambda x: x.replace(' ', ''), dct['additional_info']['Коносаменты'])))
    dct['additional_info']['Коносаменты'] = " ".join(list(filter(lambda x: x not in containers, list_of_conos)))

    for i_, good_dct in enumerate(dct[NAMES.goods]):
        original_name = good_dct[NAMES.name]  # Наименование
        conoses = dct['additional_info']['Коносаменты'].split()
        if conoses:
            conoses_regex = r'|'.join(conoses)  # регулярка формата r'RU1234|RU5678'
            list_of_conos = list(set([x for x in re.findall(conoses_regex, original_name) if x]))
            good_dct[NAMES.local_conos] = " ".join(list(filter(lambda x: x not in containers, list_of_conos)))
        else:
            good_dct[NAMES.local_conos] = ''

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
                good_dct[NAMES.transactions_type] = 'нет конт-а/конос-а или сделка не найдена (наследуется от найденных)'
            else:
                pass

    else:  # если не было найдено никаких сделок
        # извлекаем ОБЩИЕ параметры, по которым будет выполняться поиск номеров сделок (общие для всех позиций)
        DT = dct['additional_info']['ДТ']
        SHIP = dct['additional_info']['Судно']
        AUTOS = dct['additional_info']['Номера_Авто'].split()  # предварительно отформатированы разделителем-пробелом
        TRAILERS = dct['additional_info'][
            'Номера_Прицепов'].split()  # предварительно отформатированы разделителем-пробелом

        # ищем сделки
        common_deals = []
        transactions_type = ''
        if DT:
            if connection == 'http':
                common_deals = cup_http_request(r'TransactionNumberFromGTD', DT)
            else:
                numbers_DT = connection.InteractionWithExternalApplications.TransactionNumberFromGTD(DT)
                common_deals = response_to_deals(numbers_DT)
            if common_deals:
                transactions_type = 'DT'

        if not common_deals and SHIP:
            if connection == 'http':
                common_deals = cup_http_request(r'TransactionNumberFromShip', SHIP)
            else:
                numbers_SHIP = connection.InteractionWithExternalApplications.TransactionNumberFromShip(SHIP)
                common_deals = response_to_deals(numbers_SHIP)
            if common_deals:
                transactions_type = 'SHIP'

        if not common_deals and AUTOS:
            common_deals = []
            for AUTO in AUTOS:
                if connection == 'http':
                    deals_ = cup_http_request(r'TransactionNumberFromCar', AUTO)
                else:
                    numbers_AUTOS = connection.InteractionWithExternalApplications.TransactionNumberFromCar(
                        AUTO)
                    deals_ = response_to_deals(numbers_AUTOS)
                if deals_:
                    common_deals.extend(deals_)
            if common_deals:
                transactions_type = 'AUTO'

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
            good_dct[NAMES.transactions_type] = transactions_type  # список сделок = список общих сделок

    return json.dumps(dct, ensure_ascii=False, indent=4)
