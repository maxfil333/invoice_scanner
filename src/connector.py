import re
import time
import json
import win32com.client
from datetime import datetime

from logger import logger
from config.config import NAMES


def create_connection(connection_params):
    logger.print('connector initialization...')
    connection_start = time.perf_counter()
    v8com = win32com.client.Dispatch("V83.COMConnector")
    connection = v8com.Connect(connection_params)
    logger.print('connection time:', time.perf_counter() - connection_start)
    return connection


def response_to_deals(response: str) -> list[str] | None:
    if response:
        list_of_transactions = [x.strip() for x in response.strip("|").split("|") if x.strip()]
        if list_of_transactions:
            return list_of_transactions
        else:
            return
    else:
        return


def get_transaction_number(json_formatted_str: str, connection) -> str:
    dct = json.loads(json_formatted_str)
    dct['Номера сделок'] = []
    dct['Тип поиска сделки'] = ''

    # если не соединения возвращаем то, что было + dct['Номера сделок'] = []; + dct['Тип поиска сделки'] = ''.
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
        numbers_DT = connection.InteractionWithExternalApplications.TransactionNumberFromGTD(DT)
        deals = response_to_deals(numbers_DT)
        if deals:
            dct['Тип поиска сделки'] = 'DT'

    if not deals and CONTAINERS:
        deals = []
        for CONTAINER in CONTAINERS:
            numbers_CONTAINERS = connection.InteractionWithExternalApplications.TransactionNumberFromContainer(
                CONTAINER)
            deal = response_to_deals(numbers_CONTAINERS)
            if deal:
                deals.extend(deal)
        if deals:
            dct['Тип поиска сделки'] = 'CONTAINERS'

    if not deals and CONOSES:
        deals = []
        for CONOS in CONOSES:
            numbers_CONOSES = connection.InteractionWithExternalApplications.TransactionNumberFromBillOfLading(
                CONOS)
            deal = response_to_deals(numbers_CONOSES)
            if deal:
                deals.extend(deal)
        if deals:
            dct['Тип поиска сделки'] = 'CONOS'

    if not deals and SHIP:
        numbers_SHIP = connection.InteractionWithExternalApplications.TransactionNumberFromShip(SHIP)
        deals = response_to_deals(numbers_SHIP)
        if deals:
            dct['Тип поиска сделки'] = 'SHIP'

    if not deals and AUTOS:
        deals = []
        for AUTO in AUTOS:
            numbers_AUTOS = connection.InteractionWithExternalApplications.TransactionNumberFromCar(AUTO)
            deal = response_to_deals(numbers_AUTOS)
            if deal:
                deals.extend(deal)
        if deals:
            dct['Тип поиска сделки'] = 'AUTO'

    if not deals and TRAILERS:
        deals = []
        for TRAILER in TRAILERS:
            numbers_TRAILERS = connection.InteractionWithExternalApplications.TransactionNumberFromCarTrailer(
                TRAILER)
            deal = response_to_deals(numbers_TRAILERS)
            if deal:
                deals.extend(deal)
        if deals:
            dct['Тип поиска сделки'] = 'TRAILER'

    if deals:
        regex = r'(.*) (от) (.*)'
        deals.sort(key=lambda x: datetime.strptime(re.fullmatch(regex, x).group(3), '%d.%m.%Y').date()
                   if re.fullmatch(regex, x)
                   else datetime.fromtimestamp(0).date(), reverse=True)

        dct['Номера сделок'] = deals

    return json.dumps(dct, ensure_ascii=False, indent=4)
