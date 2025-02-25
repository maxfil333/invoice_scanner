import os
import json

from config.config import config, NAMES
from src.logger import logger
from src.utils import extract_text_with_fitz, extract_text_with_pdfplumber, extract_excel_text, count_extensions
from src.main_openai import run_chat, run_assistant, run_chat_pydantic
from src.models import ResponseDetails, processResponseDetails


def pdf_to_ai(file: str, test_mode: bool, text_to_assistant: bool, config: dict, running_params: dict,
              response_format=config['full_response_format']) -> str:

    running_params.setdefault('text_or_scanned_folder', config['NAME_text'])
    running_params.setdefault('current_texts', extract_text_with_fitz(file))
    running_params.setdefault('doc_type', 'pdf')

    if test_mode:
        with open(config['TESTFILE'], 'r', encoding='utf-8') as f:
            return f.read()
    if not text_to_assistant:
        result = run_chat(file,
                          response_format=response_format, text_content=running_params['current_texts'])
        return result
    else:
        result = run_assistant(file)
        return result


def excel_to_ai(file: str, test_mode: bool, text_to_assistant: bool, config: dict, running_params: dict) -> str:
    running_params['text_or_scanned_folder'] = config['NAME_text']
    running_params['current_texts'] = extract_excel_text(file)
    running_params['doc_type'] = 'excel'
    if test_mode:
        with open(config['TESTFILE'], 'r', encoding='utf-8') as f:
            return f.read()
    result = run_chat('',
                      response_format=config['full_response_format'], text_content=running_params['current_texts'])
    return result


def images_to_ai(files: list, test_mode: bool, text_to_assistant: bool, config: dict, running_params: dict) -> str:
    running_params['text_or_scanned_folder'] = config['NAME_scanned']
    files.sort(reverse=True)
    if test_mode:
        with open(config['TESTFILE'], 'r', encoding='utf-8') as f:
            return f.read()
    result = run_chat(*files,
                      response_format=config['full_response_format'], text_content=None)
    return result


def extra_excel_to_ai(extra_files: list,
                      test_mode: bool,
                      text_to_assistant: bool,
                      config: dict,
                      running_params: dict) -> str | None:

    extra_files_extensions = count_extensions(files=extra_files)
    if extra_files_extensions:
        excel_ext_intersect = set(extra_files_extensions.keys()).intersection(set(config['excel_ext']))
        if excel_ext_intersect:
            excel_files = list(filter(lambda x: os.path.splitext(x)[-1] in excel_ext_intersect, extra_files))
            if len(excel_files) > 1:
                logger.print("! Количество Excel файлов больше 1 !")
            if excel_files:
                excel_file = excel_files[0]
                running_params['current_texts'] = extract_excel_text(excel_file)
                if test_mode:
                    with open(config['TESTFILE'], 'r', encoding='utf-8') as f:
                        return f.read()
                result = run_chat('',
                                  response_format=config['full_response_format'], text_content=running_params['current_texts'])
                return result


def title_page_to_ai(title_path: str, test_mode: bool, text_to_assistant: bool, config: dict, running_params: dict):
    if os.path.splitext(title_path)[-1].lower() == '.pdf':
        running_params['title_page_texts'] = extract_text_with_fitz(title_path)
        if test_mode:
            with open(config['TESTFILE'], 'r', encoding='utf-8') as f:
                return f.read()
        if not text_to_assistant:
            result = run_chat(title_path,
                              response_format=config['full_response_format'], text_content=running_params['title_page_texts'])
            return result
        else:
            result = run_assistant(title_path)
            return result
    elif os.path.splitext(title_path)[-1].lower() in ['.jpg', '.jpeg', '.png']:
        if test_mode:
            with open(config['TESTFILE'], 'r', encoding='utf-8') as f:
                return f.read()
        result = run_chat(title_path,
                          response_format=config['full_response_format'], text_content=None)
        return result


def pdf_to_ai_details(file: str, test_mode: bool, text_to_assistant: bool, config: dict, running_params: dict) -> str:
    running_params.setdefault('text_or_scanned_folder', config['NAME_text'])
    running_params.setdefault('current_texts', extract_text_with_fitz(file))
    running_params.setdefault('current_texts_plumber', extract_text_with_pdfplumber(file))
    running_params.setdefault('doc_type', 'pdf')
    if test_mode:
        with open(config['TESTFILE'], 'r', encoding='utf-8') as f:
            result = f.read()
            details_dct = {k: v for k, v in json.loads(result).items() if k in [NAMES.supplier, NAMES.customer]}
            return json.dumps(details_dct)

    if not text_to_assistant:
        result = run_chat_pydantic(file,
                                   response_format_pydantic=ResponseDetails,
                                   text_content=running_params['current_texts_plumber'])
        return processResponseDetails(result)
    else:
        result = run_assistant(file)
        return result
