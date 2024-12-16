import re
from typing import Union
from textwrap import dedent

from src.connector import cup_http_request


def get_deal_details(post_inn: str, post_kpp: str, pok_inn: str, date: str) -> Union[list, dict, None]:
    date_regex = r'\d\d-\d\d-\d\d\d\d'
    if not re.fullmatch(date_regex, date):
        date = '01-01-1000'

    if post_inn == '':
        post_inn = '**'
    if post_kpp == '':
        post_kpp = '**'
    if pok_inn == '':
        pok_inn = '**'

    return cup_http_request('GetContractByINN', post_inn, post_kpp, pok_inn, date, encode_off=True)


def generate_details(post_inn: str, post_kpp: str, pok_inn: str, date: str):
    details = get_deal_details(post_inn, post_kpp, pok_inn, date)
    if not details:
        details = {}
    content_ = ''
    for i in ['Контрагент', 'Организация', 'Договор', 'ДатаОплаты']:
        parameter = details.get(i, "")
        content_ += dedent(f"""
            <div class="input-group-details">
                <label>{i}:</label>
                <textarea name="{i}" class="{i}" rows="1" style="resize:none;"oninput="autoResize(this)">{parameter}</textarea>
            </div>
            """.strip())

    content = f"<fieldset>{content_}</fieldset>"
    return content


if __name__ == '__main__':
    post_inn = '7802876660'
    post_kpp = '780201001'
    pok_inn = '7814406186'
    date = '26-07-2024'
    res = get_deal_details(post_inn, post_kpp, pok_inn, date)
    print(res)

    print()
    content = generate_details(post_inn, post_kpp, pok_inn, date)
    print(content)
