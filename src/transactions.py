import json
from dotenv import load_dotenv
from typing import Union, Literal
from win32com.client import CDispatch

from src.logger import logger
from config.config import NAMES
from src.connector import cup_http_request_partner
from src.utils import get_stream_dotenv, sort_transactions

load_dotenv(stream=get_stream_dotenv())


def get_transaction_number(json_formatted_str: str, connection: Union[None, Literal['http'], CDispatch]) -> str:
    dct = json.loads(json_formatted_str)

    if not connection:
        # если нет соединения возвращаем что было плюс:
        # (1) dct['Номер сделки'] = []
        # (2) dct['Номер сделки (ввести свой)'] = ''
        # (3) dct['Тип поиска сделки'] = ''
        return json.dumps(dct, ensure_ascii=False, indent=4)

    # _____________________________________ Заполнение additional_info.extra_deals _____________________________________

    dct['additional_info'][NAMES.extra_deals] = ''

    def add_extra_deals(field_name: str, func_name: str, encode_off: bool = False) -> None:
        deals = []
        for field_item in dct['additional_info'][field_name].split():
            deals_ = cup_http_request_partner(func_name, field_item, encode_off=encode_off)
            deals_ = [f"{deal} - {field_item}" for deal in deals_]
            deals.extend(deals_)
        dct['additional_info'][NAMES.extra_deals] += ('\n' + '\n'.join(deals)) if deals else ''

    # Вывести в доп.инфо список сделок для коносаментов
    add_extra_deals('Коносаменты', 'TransactionNumberFromBillOfLading')
    # Вывести в доп.инфо список сделок для ДТ
    add_extra_deals('ДТ', 'TransactionNumberFromGTD')
    # Вывести в доп.инфо список сделок для Заключений
    add_extra_deals('Заключения', 'TransactionNumberByConclusion', encode_off=True)

    # ________________________________________________ Основная логика ________________________________________________

    history = []  # индексы услуг, которые нашли сделку по контейнеру / коносаменту / ДТ
    common_deals = []  # список ОБЩИХ сделок (для наследования)

    # ------------------------ 1. DT. Проверяем можно ли получить сделки по local_dt ------------------------
    local_dt_list = [good_dct.get(NAMES.local_dt, '') for good_dct in dct[NAMES.goods]]

    # Если все поля local_dt существуют, и они не пустые (т.е. была вызвана функция split_by_dt)
    if all(local_dt_list):
        logger.print('--- Все локальные ДТ заполнены. Получаем сделки по ДТ ---')
        for i, good_dct in enumerate(dct[NAMES.goods]):
            local_deals = cup_http_request_partner(r'TransactionNumberFromGTD', good_dct[NAMES.local_dt])
            if local_deals:
                good_dct[NAMES.transactions] = sort_transactions(local_deals)
                good_dct[NAMES.transactions_type] = 'ДТ'
                history.append(i)
                common_deals.extend(good_dct[NAMES.transactions])

        if len(history) == len(dct[NAMES.goods]):
            logger.print('--- Все услуги были найдены по ДТ ---')
            return json.dumps(dct, ensure_ascii=False, indent=4)
        elif len(history) >= 1:
            for i, good_dct in enumerate(dct[NAMES.goods]):
                if i not in history:
                    good_dct[NAMES.transactions] = sort_transactions(common_deals)
                    good_dct[NAMES.transactions_type] = 'ДТ (наследуется)'
            logger.print('--- Некоторые услуги были найдены по ДТ. Остальные наследуются ---')
            return json.dumps(dct, ensure_ascii=False, indent=4)
        else:
            logger.print("Все запросы в ЦУП по всем ДТ ничего не вернули")  # Переходим к LOCAL
    else:
        pass  # Не все поля local_dt существуют/заполнены. Переходим к LOCAL

    # ------------ 2. LOCAL. Проходим по услугам, где есть ЛОКАЛЬНЫЙ контейнер или ЛОКАЛЬНЫЙ коносамент ------------
    for i, good_dct in enumerate(dct[NAMES.goods]):
        local_deals = []
        local_container = good_dct[NAMES.cont]
        local_conos = good_dct.get(NAMES.local_conos, '')
        local_report = good_dct.get(NAMES.local_reports, '')

        # ЕСЛИ есть контейнер, берем список сделок по нему и идем к следующей услуге
        if local_container:
            deals_ = cup_http_request_partner(r'TransactionNumberFromContainer', local_container)
            if deals_:
                local_deals.extend(deals_)
                common_deals.extend(deals_)
                good_dct[NAMES.transactions] = sort_transactions(local_deals)
                good_dct[NAMES.transactions_type] = 'КОНТЕЙНЕР'
                history.append(i)
                # ______________ дополнительно смэтчим сделки от контейнеров со сделками от коносаментов ____________...
                # Если для данной позиции найдено сделок по контейнерам больше 1, и кол-во коносаментов = 1
                if len(local_deals) > 1 and len(local_conos.split()) == 1:
                    # берем сделки по этому коносаменту (m_deals)
                    m_deals_ = cup_http_request_partner(r'TransactionNumberFromBillOfLading', local_conos)
                    # если нашли, находим общие со сделками по контейнерам, оставляем общие
                    if m_deals_:
                        deals_intersect = set(deals_).intersection(set(m_deals_))
                        if deals_intersect:
                            good_dct[NAMES.transactions] = sort_transactions(list(deals_intersect))
                            good_dct[NAMES.transactions_type] = 'КОНТЕЙНЕР+КС'
                # ...___________________________________________________________________________________________________
                continue

        # ЕСЛИ нет контейнера, но есть коносамент, берем список сделок по нему и идем к следующей услуге
        if not local_deals and local_conos:
            deals_ = cup_http_request_partner(r'TransactionNumberFromBillOfLading', local_conos)
            if deals_:
                local_deals.extend(deals_)
                common_deals.extend(deals_)
                good_dct[NAMES.transactions] = sort_transactions(local_deals)
                good_dct[NAMES.transactions_type] = 'КС'
                history.append(i)
                continue

        # ЕСЛИ нет контейнера и коноса, но есть заключение, берем список сделок по нему и идем к следующей услуге
        if not local_deals and local_report:
            deals_ = cup_http_request_partner(r'TransactionNumberByConclusion', local_report, encode_off=True)
            if deals_:
                local_deals.extend(deals_)
                common_deals.extend(deals_)
                good_dct[NAMES.transactions] = sort_transactions(local_deals)
                good_dct[NAMES.transactions_type] = 'ЗАКЛЮЧЕНИЕ'
                history.append(i)
                continue

    if len(history) == len(dct[NAMES.goods]):  # Все услуги были найдены по контейнерам и коносаментам
        logger.print('Все услуги были найдены по КОНТ/КС/ЗАКЛ')

    elif common_deals:  # если какие-то сделки по контейнерам/коносаментам уже найдены,
        logger.print('Наследование некоторых сделок по КОНТ/КС/ЗАКЛ')
        for i, good_dct in enumerate(dct[NAMES.goods]):  # то для каждой услуги где:
            if i not in history:  # не было КОНТ/КС/ЗАКЛ, или сделка не была найдена:
                good_dct[NAMES.transactions] = sort_transactions(common_deals)  # сделки = общие сделки
                good_dct[NAMES.transactions_type] = 'Нет КОНТ/КС/ЗАКЛ или сделка не найдена: наследуется от найденных'

    else:  # Если не было найдено никаких сделок по контейнерам и коносаментам. Переходим к GLOBAL
        logger.print('--- ИЗВЛЕЧЕНИЕ ОБЩИХ ПАРАМЕТРОВ (ДТ/ТХ/АВТО/ПРИЦЕП) ---')

        # ------------------------ 3. GLOBAL. Извлекаем ОБЩИЕ (для всего документа) параметры ------------------------

        SHIP = dct['additional_info']['Судно']
        # предварительно отформатированы разделителем-пробелом:
        DT = dct['additional_info']['ДТ'].split()
        KS = dct['additional_info']['Коносаменты'].split()
        REPORTS = dct['additional_info']['Заключения'].split()
        AUTOS = dct['additional_info']['Номера_Авто'].split()
        TRAILERS = dct['additional_info']['Номера_Прицепов'].split()

        # ищем сделки
        common_deals = []
        transactions_type = ''

        # поиск сделки по ДТ
        if DT:
            common_deals = []
            for dt in DT:
                deals_ = cup_http_request_partner(r'TransactionNumberFromGTD', dt)
                if deals_:
                    common_deals.extend(deals_)
            if common_deals:
                transactions_type = 'ДТ'

        # поиск сделки по КС (не локальному)
        if not common_deals and KS:
            common_deals = []
            for ks in KS:
                deals_ = cup_http_request_partner(r'TransactionNumberFromBillOfLading', ks)
                if deals_:
                    common_deals.extend(deals_)
            if common_deals:
                transactions_type = 'КС (общий)'

        # поиск сделки по Заключению
        if not common_deals and REPORTS:
            common_deals = []
            for report in REPORTS:
                deals_ = cup_http_request_partner(r'TransactionNumberByConclusion', report, encode_off=True)
                if deals_:
                    common_deals.extend(deals_)
            if common_deals:
                transactions_type = 'ЗАКЛЮЧЕНИЕ (общее)'

        # поиск сделки по ТХ
        if not common_deals and SHIP:
            common_deals = cup_http_request_partner(r'TransactionNumberFromShip', SHIP)
            if common_deals:
                transactions_type = 'ТХ'

        # поиск сделки по номеру авто
        if not common_deals and AUTOS:
            common_deals = []
            for AUTO in AUTOS:
                deals_ = cup_http_request_partner(r'TransactionNumberFromCar', AUTO)
                if deals_:
                    common_deals.extend(deals_)
            if common_deals:
                transactions_type = 'АВТО'

        # поиск сделки по номеру прицепа
        if not common_deals and TRAILERS:
            common_deals = []
            for TRAILER in TRAILERS:
                deals_ = cup_http_request_partner(r'TransactionNumberFromCarTrailer', TRAILER)
                if deals_:
                    common_deals.extend(deals_)
            if common_deals:
                transactions_type = 'ПРИЦЕП'

        # для каждой услуги заполняем "Номер сделки" и "Тип сделки" (будут одинаковы для всех услуг)
        for good_dct in dct[NAMES.goods]:
            good_dct[NAMES.transactions] = sort_transactions(common_deals)  # список сделок = список общих сделок
            good_dct[NAMES.transactions_type] = transactions_type

    return json.dumps(dct, ensure_ascii=False, indent=4)
