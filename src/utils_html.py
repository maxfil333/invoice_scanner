import re
import json
from textwrap import dedent

from src.connector import cup_http_request
from src.logger import logger
from config.config import NAMES


def details_from_result(result: str) -> dict | None:
    """ Get details from result using: ИНН, КПП, ИНН, Дата """

    dct = json.loads(result)
    post_inn = dct['Банковские реквизиты поставщика']['ИНН']
    post_kpp = dct['Банковские реквизиты поставщика']['КПП']
    pok_inn = dct['Банковские реквизиты покупателя']['ИНН']
    date = dct['Дата счета']

    return details_request(post_inn, post_kpp, pok_inn, date)


def details_request(post_inn: str, post_kpp: str, pok_inn: str, date: str) -> dict | None:
    """ Send request to CUP for details """

    date_regex = r'\d\d-\d\d-\d\d\d\d'
    if not re.fullmatch(date_regex, date):
        date = '01-01-1000'

    if post_inn == '':
        post_inn = '**'
    if post_kpp == '':
        post_kpp = '**'
    if pok_inn == '':
        pok_inn = '**'

    details = cup_http_request('GetContractByINN', post_inn, post_kpp, pok_inn, date, encode_off=True)
    if isinstance(details, dict):
        details['Варианты'] = json.dumps(details['Варианты'], ensure_ascii=False)  # список словарей --> в строку
        return details
    else:
        logger.print("!! не удалось получить детали по счету !!")
        return None


def result_add_details(result: str, details: dict | None) -> str:
    """ Add details to result """

    dct = json.loads(result)

    if details:
        dct[NAMES.contract_details] = details
    else:
        empty_dict = {"Контрагент": "", "Организация": "", "Договор": "", "ДоговорИдентификатор": "", "Варианты": ""}
        dct[NAMES.contract_details] = empty_dict

    return json.dumps(dct, ensure_ascii=False, indent=4)


def html_generate_contract(details: dict) -> str:
    main_contract: str = details.get('Договор', '')

    options = ''
    variants_string: str = details.get('Варианты')

    if variants_string:
        variants = json.loads(variants_string)
        for variant in variants:
            contract: str = variant['Договор']
            options += f'<div>{contract}</div>\n'

    content = dedent(f"""
    <div class="input-group-details">
        <label>Договор</label>
        <div class="custom-select" id="contract-custom">
            <div class="select-display" id="contract-selector">{main_contract}</div>
            <div class="options">{options}</div>
        </div>
    </div>
    """).strip()

    return content


def html_generate_details(details: dict) -> str:
    if not details:
        details = {}

    content_ = ''

    for i in ['Контрагент', 'Организация', 'Договор', 'ДоговорИдентификатор', 'ДатаОплаты', "Варианты"]:
        parameter = details.get(i, "")

        if i == 'Договор':
            content_ += html_generate_contract(details)
        elif i == "ДоговорИдентификатор":  # скрытое поле (регулируется js, добавляется в json для выгрузки)
            content_ += dedent(f"""
                <div class="input-group-details" style="display: none;">
                    <label>{i}</label>
                    <textarea name="{i}" class="{i}" rows="1" style="resize:none;"oninput="autoResize(this)">{parameter}</textarea>
                </div>
                """.strip())
        elif i == 'Варианты':  # скрытое поле, чтобы брать из него "ДоговорИдентификатор" к выбранному "Договору"
            content_ += dedent(f"""
                <div class="input-group-details" style="display: none;">
                    <label>{i}</label>
                    <textarea name="{i}" class="{i}" rows="1" style="resize:none;"oninput="autoResize(this)">{parameter}</textarea>
                </div>
                """.strip())
        else:
            content_ += dedent(f"""
                <div class="input-group-details">
                    <label>{i}</label>
                    <textarea name="{i}" class="{i}" rows="1" style="resize:none;"oninput="autoResize(this)" disabled="disabled">{parameter}</textarea>
                </div>
                """.strip())

    content = f'<fieldset><legend style="display: none">{NAMES.contract_details}</legend>{content_}</fieldset>'
    return content


if __name__ == '__main__':
    pass

    # post_inn = '7802876660'
    # post_kpp = '780201001'
    # pok_inn = '7814406186'
    # date = '26-07-2024'
    # res = get_deal_details(post_inn, post_kpp, pok_inn, date)
    # print(res)

    # print()
    # content = generate_details(post_inn, post_kpp, pok_inn, date)
    # print(content)
