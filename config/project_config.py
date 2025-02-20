import json
from config.config import NAMES


PROJECT_DATA: dict = dict()
PROJECT_DATA['customer_inn'] = '7814406186'


def main(result: str) -> str:
    dct = json.loads(result)

    replace_customer_inn(dct)
    FESCO_inn(dct)

    return json.dumps(dct, ensure_ascii=False, indent=4)


def replace_customer_inn(dct: dict):
    dct[NAMES.customer]['ИНН'] = PROJECT_DATA['customer_inn']


def FESCO_inn(dct: dict):
    if dct[NAMES.supplier]['ИНН'] == '7710293280':
        dct[NAMES.supplier]['КПП'] = '770501001'
