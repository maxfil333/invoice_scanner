import os
import time
from dotenv import load_dotenv
import win32com.client

import base64
import requests
from requests.auth import HTTPBasicAuth

from config.config import config, NAMES
from src.logger import logger
from src.utils import get_stream_dotenv

load_dotenv(stream=get_stream_dotenv())


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

def cup_http_request(function, *args, kappa=False):
    user_1C = os.getenv('user_1C')
    password_1C = os.getenv('password_1C')

    if kappa:
        base = r'http://kappa5.group.ru:81/ca/hs/interaction/'
    else:
        base = r'http://10.10.0.10:81/ca/hs/interaction/'

    function_args = r'/'.join(map(lambda x: base64.urlsafe_b64encode(x.encode()).decode(), args))
    url = base + function + r'/' + function_args
    logger.write(url)

    response = requests.get(url, auth=HTTPBasicAuth(user_1C, password_1C))
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Ошибка: {response.status_code} - {response.reason}")


if __name__ == '__main__':
    # from config.config import config
    # create_connection(config['V83_CONN_STRING'])

    print(cup_http_request(r'TransactionNumberFromContainer', r'ADMU9000937'))
