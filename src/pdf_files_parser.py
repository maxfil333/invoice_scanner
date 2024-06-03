import shutil
from glob import glob
from os import path
import os
from config.config import config


def parse(pdf_path, n=2, shift=0, max_pdf_amount=100):
    result_pdf_files = []
    folders = glob(pdf_path)
    folders.sort(key=os.path.getmtime)
    folders = folders[-(shift + n):-shift] if shift != 0 else folders[-(shift + n):]
    for f in folders:
        invoice_path = path.join(path.abspath(f), r'Счет поставщика\*.pdf')
        pdfs = glob(invoice_path)
        for pdf in pdfs:
            result_pdf_files.append(pdf)
        if len(result_pdf_files) > max_pdf_amount:
            break

    return result_pdf_files


pdfpath = r'\\10.10.0.3\docs\Baltimpex\Invoice\TR\Import\*'

if __name__ == '__main__':
    res = parse(pdf_path=pdfpath, n=500, shift=0)
    for r in res:
        shutil.copy(r, config['IN_FOLDER'])
