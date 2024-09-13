import openai
from openai import OpenAI
from langchain_openai import OpenAIEmbeddings

import os
import re
import json
import inspect
import difflib
from PIL import Image
from time import perf_counter
from dotenv import load_dotenv

from logger import logger
from config.config import config, NAMES
from utils import chroma_get_relevant
from utils import extract_text_with_fitz, check_sums, order_goods
from utils import replace_container_with_latin, replace_container_with_none, switch_to_latin
from utils import base64_encode_pil, convert_json_values_to_strings, get_stream_dotenv, postprocessing_openai_response

# ___________________________ general ___________________________

start = perf_counter()
load_dotenv(stream=get_stream_dotenv())
openai.api_key = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")
client = OpenAI()


def local_postprocessing(response, hide_logs=False) -> str | None:
    re_response = postprocessing_openai_response(response, hide_logs)
    if re_response is None:
        return None
    if not hide_logs:
        logger.print(f'function "{inspect.stack()[1].function}":')
        logger.print('re_response:\n', repr(re_response))
    dct = json.loads(re_response)
    dct = convert_json_values_to_strings(dct)

    container_regex = r'[A-ZА-Я]{3}U\s?[0-9]{7}'
    container_regex_lt = r'[A-Z]{3}U\s?[0-9]{7}'
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
        containers_name = list(map(lambda x: re.sub(r'\s', '', x), re.findall(container_regex_lt, name)))
        uniq_containers_from_name = list(dict.fromkeys(containers_name))

        # 2.2 Замена кириллицы в Контейнеры
        cont = good_dct[NAMES.cont]
        good_dct[NAMES.cont] = replace_container_with_latin(cont, container_regex)
        cont = good_dct[NAMES.cont]
        containers_cont = list(map(lambda x: re.sub(r'\s', '', x), re.findall(container_regex_lt, cont)))
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


# ___________________________ CHAT ___________________________

def run_chat(*img_paths: str, detail='high', hide_logs=False, text_mode=False) -> str:
    if text_mode:
        if len(img_paths) != 1:
            logger.print("ВНИМАНИЕ! На вход run_chat пришли pdf-файлы в количестве != 1")
        content = extract_text_with_fitz(img_paths[0])
    else:
        content = []
        for img_path in img_paths:
            d = {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_encode_pil(Image.open(img_path))}",
                              "detail": detail}
            }
            content.append(d)

    response = client.chat.completions.create(
        model=config['GPTMODEL'],
        temperature=0.1,
        messages=[
            {"role": "system", "content": config['system_prompt']},
            {"role": "user", "content": content}
        ],
        max_tokens=3000,
        response_format=config['response_format'],
    )
    logger.print('chat model:', response.model)
    logger.print(f'time: {perf_counter() - start:.2f}')
    logger.print(f'completion_tokens: {response.usage.completion_tokens}')
    logger.print(f'prompt_tokens: {response.usage.prompt_tokens}')
    logger.print(f'total_tokens: {response.usage.total_tokens}')

    response = response.choices[0].message.content
    return local_postprocessing(response, hide_logs=hide_logs)


# ___________________________ ASSISTANT ___________________________

def run_assistant(file_path, hide_logs=False):
    assistant = client.beta.assistants.retrieve(assistant_id=ASSISTANT_ID)
    message_file = client.files.create(file=open(file_path, "rb"), purpose="assistants")
    # Create a thread and attach the file to the message
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": " ",
                "attachments": [{"file_id": message_file.id, "tools": [{"type": "file_search"}]}],
            }
        ]
    )

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id, assistant_id=assistant.id
    )
    if run.status == 'completed':
        logger.print('assistant model:', assistant.model)
        logger.print(f'file_path: {file_path}')
        logger.print(f'time: {perf_counter() - start:.2f}')
        logger.print(f'completion_tokens: {run.usage.completion_tokens}')
        logger.print(f'prompt_tokens: {run.usage.prompt_tokens}')
        logger.print(f'total_tokens: {run.usage.total_tokens}')

    messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))
    response = messages[0].content[0].text.value
    return local_postprocessing(response, hide_logs=hide_logs)


# ___________________________ TEST ___________________________

if __name__ == '__main__':
    pass
