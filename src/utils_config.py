import sys
import msvcrt
from io import StringIO
from cryptography.fernet import Fernet

from config.config import config
from src.logger import logger


def get_stream_dotenv():
    """ uses crypto.key to decrypt encrypted environment.
    returns StringIO (for load_dotenv(stream=...)"""

    f = Fernet(config['crypto_key'])
    try:
        with open(config['crypto_env'], 'rb') as file:
            encrypted_data = file.read()
    except FileNotFoundError:
        logger.print(f'Файл {config["crypto_env"]} не найден.')
        if getattr(sys, 'frozen', False):
            msvcrt.getch()
            sys.exit()
        else:
            raise
    decrypted_data = f.decrypt(encrypted_data)  # bytes
    decrypted_data_str = decrypted_data.decode('utf-8')  # string
    string_stream = StringIO(decrypted_data_str)
    return string_stream
