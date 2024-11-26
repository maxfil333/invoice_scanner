import re
import os
import time
import win32com.client
from typing import Union
from functools import wraps
from dotenv import load_dotenv

import base64
import requests
from requests.auth import HTTPBasicAuth

from src.logger import logger
from config.config import config, NAMES
from src.utils import get_stream_dotenv

load_dotenv(stream=get_stream_dotenv())

config['user_1C'] = os.getenv('user_1C')
config['password_1C'] = os.getenv('password_1C')


# __________________ COM-OBJECT __________________

def create_connection():
    logger.print('connector initialization...')
    user_1C = os.getenv('user_1C')
    password_1C = os.getenv('password_1C')
    V83_CONN_STRING = f"Srvr=kappa; Ref=CUP; Usr={user_1C}; Pwd={password_1C}"
    connection_start = time.perf_counter()
    v8com = win32com.client.Dispatch("V83.COMConnector")
    connection = v8com.Connect(V83_CONN_STRING)
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

def cache_http_requests(func):
    """ Декоратор для кэширования запросов на основе URL """

    cache = {}
    max_cache_size = 40

    @wraps(func)
    def wrapper(function, *args, **kwargs):
        # Формируем ключ кэша из функции + "_" + аргументы
        function_args = r'_'.join(args)
        url_cache_key = function + r'_' + function_args

        # Проверяем, есть ли результат в кэше для данного URL
        if url_cache_key in cache:
            logger.print("Получение результата из кэша...")
            return cache[url_cache_key]

        # Выполняем запрос и сохраняем результат в кэше
        result = func(function, *args, **kwargs)
        cache[url_cache_key] = result

        if len(cache) > max_cache_size:
            cache.pop(next(iter(cache)))

        return result

    return wrapper


@cache_http_requests
def cup_http_request(function, *args, kappa=False) -> Union[list, dict, None]:
    user_1C = config['user_1C']
    password_1C = config['password_1C']

    # Определение серверов
    if kappa:
        primary_base = r'http://kappa5.group.ru:81/ca/hs/interaction/'
        secondary_base = r'http://10.10.0.10:81/ca/hs/interaction/'
    else:
        primary_base = r'http://10.10.0.10:81/ca/hs/interaction/'
        secondary_base = r'http://kappa5.group.ru:81/ca/hs/interaction/'

    function_args = r'/'.join(map(lambda x: base64.urlsafe_b64encode(x.encode()).decode(), args))

    try:
        # Формируем URL для первого сервера
        primary_url = primary_base + function + r'/' + function_args
        logger.print(f"Попытка запроса: {primary_url}")

        # Попытка отправить запрос на первый сервер
        response = requests.get(primary_url, auth=HTTPBasicAuth(user_1C, password_1C))

        # Если первый запрос успешен, возвращаем результат
        if response.status_code == 200:
            return response.json()
        else:
            logger.print(f"Ошибка при запросе к первому серверу: {response.status_code} - {response.reason}")
    except Exception as error:
        logger.print(error)

    try:
        # Формируем URL для второго сервера
        secondary_url = secondary_base + function + r'/' + function_args
        logger.print(f"Попытка запроса ко второму серверу: {secondary_url}")

        # Попытка отправить запрос на второй сервер
        response = requests.get(secondary_url, auth=HTTPBasicAuth(user_1C, password_1C))

        # Возвращаем результат, если успешен
        if response.status_code == 200:
            return response.json()
        else:
            logger.print(f"Ошибка при запросе ко второму серверу: {response.status_code} - {response.reason}")
            return None
    except Exception as error:
        logger.print(error)
        return None


def add_partner(response: Union[list, dict, None]):
    if not isinstance(response, list):
        return response

    regex = r'(.*) (от) (.*)'
    matches = [re.fullmatch(regex, deal, re.IGNORECASE) for deal in response]
    if all(matches):
        deals = [match.group(1) for match in matches]
        partners = [cup_http_request(r'ValueByTransactionNumber', deal, 'Контрагент') for deal in deals]
        partners = [p[0] if p else '' for p in partners]

        new_response = []
        for m, p in zip(matches, partners):
            deal_and_partner = m.group() + f" | {p}"
            new_response.append(deal_and_partner)
        return new_response

    else:
        return response


def cup_http_request_partner(function, *args, kappa=False) -> Union[list, dict, None]:
    response = cup_http_request(function, *args, kappa=kappa)
    return add_partner(response)


if __name__ == '__main__':
    # from config.config import config
    # create_connection(config['V83_CONN_STRING'])

    print(cup_http_request(r'TransactionNumberFromContainer', r'UNIU6002157'))
    print(cup_http_request(r'TransactionNumberFromContainer', r'VEZU2602114'))
    print(cup_http_request(r'TransactionNumberFromContainer', r'FENU2604371'))
    print(cup_http_request(r'TransactionNumberFromBillOfLading', r'ULDALYNVK000033'))

    print("ДТ1:", cup_http_request(r'TransactionNumberFromGTD', "10228010/241024/5298812"))
    print("ДТ2:", cup_http_request(r'TransactionNumberFromGTD', "10228010/231024/5298058"))
    print("ДТ3:", cup_http_request(r'TransactionNumberFromGTD', "10228010/231024/5297337"))
    print('-------------------------------------------------------')
    print("SHIP:", cup_http_request_partner(r'TransactionNumberFromShip', "MSC SHANNON III"))