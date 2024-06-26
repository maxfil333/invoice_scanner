import openai
from openai import OpenAI

import os
import re
import json
import inspect
from PIL import Image
from time import perf_counter
from dotenv import load_dotenv

from config.config import config
from utils import replace_container_with_latin
from utils import base64_encode_pil, convert_json_values_to_strings, get_stream_dotenv, postprocessing_openai_response

# ___________________________ general ___________________________

start = perf_counter()
load_dotenv(stream=get_stream_dotenv())
openai.api_key = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")
client = OpenAI()


def local_postprocessing(response, hide_logs=False):
    re_response = postprocessing_openai_response(response, hide_logs)
    if re_response is None:
        return None
    if not hide_logs:
        print(f'function "{inspect.stack()[1].function}":')
        print('response:')
        print(repr(response))
        print('re_response:')
        print(repr(re_response))
    dictionary = json.loads(re_response)

    # Найти все контейнеры по паттерну вне зависимости от языка
    container_regex = r'[A-ZА-Я]{4}\s?[0-9]{7}'
    container_regex_lt = r'[A-Z]{4}\s?[0-9]{7}'

    for good_dict in dictionary['Услуги']:

        # 1. Замена кириллицы в контейнерах
        name = good_dict['Наименование']
        # Заменить в Наименовании кириллицу в контейнерах
        good_dict['Наименование'] = replace_container_with_latin(name, container_regex)
        name = good_dict['Наименование']
        # Найти контейнеры
        good_dict['Номера контейнеров'] = ' '.join(list(map(lambda x:
                                                            re.sub(r'\s', '', x),
                                                            re.findall(container_regex_lt, name)
                                                            )
                                                        )
                                                   )

        # 2. Дозаполнение Сумма НДС, Сумма с учетом НДС
        summa = good_dict['Сумма без НДС']
        summa_nds = good_dict['Сумма НДС']
        summa_with_nds = good_dict['Сумма с учетом НДС']
        if summa_nds == "" or summa_nds is None:
            summa_nds = good_dict['Сумма НДС'] = "0"
        if summa_nds in ["0", "0.0", "0.00", "0.000"] and (summa_with_nds == "" or summa_with_nds is None):
            good_dict['Сумма с учетом НДС'] = summa

    string_dictionary = convert_json_values_to_strings(dictionary)
    return json.dumps(string_dictionary, ensure_ascii=False, indent=4)


# ___________________________ CHAT ___________________________

def run_chat(*img_paths: str, detail='high', hide_logs=False) -> str:
    content = []
    for img_path in img_paths:
        d = {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_encode_pil(Image.open(img_path))}",
                          "detail": detail}
        }
        content.append(d)

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        temperature=0.1,
        messages=
        [
            {"role": "system", "content": config['system_prompt']},
            {"role": "user", "content": content}
        ],
        max_tokens=3000,
    )
    print(f'img_paths: {img_paths}')
    print(f'time: {perf_counter() - start:.2f}')
    print(f'completion_tokens: {response.usage.completion_tokens}')
    print(f'prompt_tokens: {response.usage.prompt_tokens}')
    print(f'total_tokens: {response.usage.total_tokens}')

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
        print('assistant model:', assistant.model)
        print(f'file_path: {file_path}')
        print(f'time: {perf_counter() - start:.2f}')
        print(f'completion_tokens: {run.usage.completion_tokens}')
        print(f'prompt_tokens: {run.usage.prompt_tokens}')
        print(f'total_tokens: {run.usage.total_tokens}')

    messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))
    response = messages[0].content[0].text.value
    return local_postprocessing(response, hide_logs=hide_logs)


# ___________________________ TEST ___________________________

if __name__ == '__main__':
    pass
