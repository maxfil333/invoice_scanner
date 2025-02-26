import openai
from openai import OpenAI
from openai.types.chat import ChatCompletion, ParsedChatCompletion

import os
from PIL import Image
from time import perf_counter
from dotenv import load_dotenv

from src.logger import logger
from config.config import config, running_params
from src.utils import extract_text_with_fitz, base64_encode_pil
from src.utils_config import get_stream_dotenv

# ___________________________ general ___________________________

start = perf_counter()
load_dotenv(stream=get_stream_dotenv())
openai.api_key = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")
client = OpenAI()


def log_response(response: ChatCompletion | ParsedChatCompletion, time_start: float) -> None:
    logger.print('chat model:', response.model)
    logger.print(f'completion_tokens: {response.usage.completion_tokens}')
    logger.print(f'cached_tokens: {response.usage.prompt_tokens_details}')
    logger.print(f'prompt_tokens: {response.usage.prompt_tokens}')
    logger.print(f'total_tokens: {response.usage.total_tokens}')
    logger.print(f'time: {perf_counter() - time_start:.2f}')


# ___________________________ CHAT (json_schema) ___________________________

def run_chat(*file_paths: str,
             response_format,
             prompt=config['system_prompt'],
             model=config['GPTMODEL'],
             text_content: list | None = None
             ) -> str:

    if text_content:
        content = '\n'.join(text_content)
    else:
        content = []
        for img_path in file_paths:
            d = {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_encode_pil(Image.open(img_path))}",
                              "detail": "high"}
            }
            content.append(d)

    response = client.chat.completions.create(
        model=model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": content}
        ],
        max_tokens=3000,
        response_format=response_format,
    )

    log_response(response=response, time_start=start)

    response = response.choices[0].message.content
    return response


def run_chat_pydantic(*file_paths: str,
                      response_format_pydantic,
                      prompt=config['system_prompt'],
                      model=config['GPTMODEL'],
                      text_content: list | None = None,
                      ) -> str:

    if text_content:
        content = '\n'.join(text_content)
    else:
        content = []
        for img_path in file_paths:
            d = {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_encode_pil(Image.open(img_path))}",
                              "detail": "high"}
            }
            content.append(d)

    response = client.beta.chat.completions.parse(
        model=model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": content}
        ],
        max_tokens=3000,
        response_format=response_format_pydantic,
    )

    log_response(response=response, time_start=start)

    response = response.choices[0].message.content
    return response


# ___________________________ ASSISTANT ___________________________

def run_assistant(file_path):
    running_params['current_texts'] = extract_text_with_fitz(file_path)

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
