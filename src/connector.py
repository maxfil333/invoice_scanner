import re
import time
import json
import win32com.client
from datetime import datetime

import base64
import requests
from requests.auth import HTTPBasicAuth

from config.config import config, NAMES
from src.logger import logger


# __________________ COM-OBJECT __________________

def create_connection(connection_params):
    logger.print('connector initialization...')
    connection_start = time.perf_counter()
    v8com = win32com.client.Dispatch("V83.COMConnector")
    connection = v8com.Connect(connection_params)
    logger.print(f'connection time: {time.perf_counter() - connection_start:.2f}\n')
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


# __________________ HTTP-REQUEST __________________

def cup_http_request(function, *args, kappa=False):
    username = config["user_1C"]
    password = config["password_1C"]

    if kappa:
        base = r'http://kappa5.group.ru:81/ca/hs/interaction/'
    else:
        base = r'http://10.10.0.10:81/ca/hs/interaction/'

    function_args = r'/'.join(map(lambda x: base64.urlsafe_b64encode(x.encode()).decode(), args))
    url = base + function + r'/' + function_args
    logger.write(url)

    response = requests.get(url, auth=HTTPBasicAuth(username, password))
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Ошибка: {response.status_code} - {response.reason}")


# __________________ ADD TRANSACTIONS TO RESULT __________________

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


if __name__ == '__main__':
    # from config.config import config
    # create_connection(config['V83_CONN_STRING'])

    print(cup_http_request(r'TransactionNumberFromContainer', r'ADMU9000937'))
