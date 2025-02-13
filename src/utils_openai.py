import os
from src.logger import logger
from src.utils import extract_text_with_fitz, extract_excel_text, count_extensions
from src.main_openai import run_chat, run_assistant


def pdf_to_ai(file: str, test_mode: bool, text_to_assistant: bool, config: dict, running_params: dict) -> str:
    running_params['text_or_scanned_folder'] = config['NAME_text']
    running_params['current_texts'] = extract_text_with_fitz(file)
    if test_mode:
        with open(config['TESTFILE'], 'r', encoding='utf-8') as f:
            return f.read()
    if not text_to_assistant:
        result = run_chat(file, text_content=running_params['current_texts'])
        return result
    else:
        result = run_assistant(file)
        return result


def excel_to_ai(file: str, test_mode: bool, text_to_assistant: bool, config: dict, running_params: dict) -> str:
    running_params['text_or_scanned_folder'] = config['NAME_text']
    running_params['current_texts'] = extract_excel_text(file)
    if test_mode:
        with open(config['TESTFILE'], 'r', encoding='utf-8') as f:
            return f.read()
    result = run_chat('', text_content=running_params['current_texts'])
    return result


def images_to_ai(files: list, test_mode: bool, text_to_assistant: bool, config: dict, running_params: dict) -> str:
    running_params['text_or_scanned_folder'] = config['NAME_scanned']
    files.sort(reverse=True)
    if test_mode:
        with open(config['TESTFILE'], 'r', encoding='utf-8') as f:
            return f.read()
    result = run_chat(*files, detail='high', text_content=None)
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
                result = run_chat('', text_content=running_params['current_texts'])
                return result


def title_page_to_ai(title_path: str, test_mode: bool, text_to_assistant: bool, config: dict, running_params: dict):
    if os.path.splitext(title_path)[-1].lower() == '.pdf':
        running_params['title_page_texts'] = extract_text_with_fitz(title_path)
        if test_mode:
            with open(config['TESTFILE'], 'r', encoding='utf-8') as f:
                return f.read()
        if not text_to_assistant:
            result = run_chat(title_path, text_content=running_params['title_page_texts'])
            return result
        else:
            result = run_assistant(title_path)
            return result
    elif os.path.splitext(title_path)[-1].lower() in ['.jpg', '.jpeg', '.png']:
        if test_mode:
            with open(config['TESTFILE'], 'r', encoding='utf-8') as f:
                return f.read()
        result = run_chat(title_path, detail='high', text_content=None)
        return result
