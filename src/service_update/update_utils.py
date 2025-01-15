import json

from config.config import config


def reindex_unique_comments(unique_comments_file_path: str) -> None:
    """
    Если вручную добавлялись/удалялись услуги, unique_comments нужно переиндексировать,
    так как id словарика должен быть равен его порядковому номеру.
    """
    with open(unique_comments_file_path, 'r', encoding='utf-8') as f:
        dct = json.load(f)
        for i, d, in enumerate(dct):
            d['id'] = i

    with open(unique_comments_file_path, 'w', encoding='utf-8') as f:
        json.dump(dct, f, ensure_ascii=False, indent=4)


reindex_unique_comments(config['unique_comments_file'])
