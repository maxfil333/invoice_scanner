import openai
from openai import OpenAI

import os
from PIL import Image
from time import perf_counter
from dotenv import load_dotenv

from src.logger import logger
from config.config import config
from src.utils import extract_text_with_fitz, get_stream_dotenv, base64_encode_pil


# ___________________________ general ___________________________

start = perf_counter()
load_dotenv(stream=get_stream_dotenv())
openai.api_key = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")
client = OpenAI()


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
    logger.print(f'cached_tokens: {response.usage.prompt_tokens_details}')
    logger.print(f'prompt_tokens: {response.usage.prompt_tokens}')
    logger.print(f'total_tokens: {response.usage.total_tokens}')

    response = response.choices[0].message.content
    return response


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
    return response


# ___________________________ TEST ___________________________

if __name__ == '__main__':
    pass
