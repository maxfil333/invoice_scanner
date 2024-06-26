import os
import shutil
from glob import glob

from config.config import config


class BreakException(Exception):
    pass


def parse(pdf_path, n=2, shift=0, max_pdf_amount=100):
    result_pdf_files = []
    folders = glob(pdf_path)
    folders.sort(key=os.path.getmtime)
    folders = folders[-(shift + n):-shift] if shift != 0 else folders[-(shift + n):]

    try:
        for f in folders:
            invoice_path = os.path.join(os.path.abspath(f), r'Счет поставщика\*.pdf')
            pdfs = glob(invoice_path)
            for pdf in pdfs:
                result_pdf_files.append(pdf)
                if len(result_pdf_files) == max_pdf_amount:
                    raise BreakException
    except BreakException:
        pass

    return result_pdf_files


if __name__ == '__main__':
    pdf_path = r'\\10.10.0.3\docs\Baltimpex\Invoice\TR\Import\*'
    save_folder = os.path.join(config['IN_FOLDER'], '__data3')
    res = parse(pdf_path=pdf_path, n=500, shift=0, max_pdf_amount=50)
    for r in res:
        shutil.copy(r, save_folder)
