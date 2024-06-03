import shutil
from glob import glob
from os import path
import os


def parse(pdf_path, n=2, shift=0):
    result_pdf_files = []

    folders = glob(pdf_path)
    folders.sort(key=os.path.getmtime)
    folders = folders[-(shift + n):-shift] if shift != 0 else folders[-(shift + n):]
    for f in folders:
        invoice_path = path.join(path.abspath(f), r'Счет поставщика\*.pdf')
        pdfs = glob(invoice_path)
        for pdf in pdfs:
            result_pdf_files.append(pdf)

    return result_pdf_files


# pdf_path=r'\\10.10.0.3\docs\Baltimpex\Invoice\TR\Import\*'
# print(glob(pdf_path))

# files = glob(r'\\10.10.0.3\docs\Baltimpex\Invoice\TR\Import\*')
# files.sort(key=os.path.getmtime)
# print(parse(pdf_path=r'\\10.10.0.3\docs\Baltimpex\Invoice\TR\Import\*'))

pdf_path = r'\\10.10.0.3\docs\Baltimpex\Invoice\TR\Import\*'

if __name__ == '__main__':
    res = parse(pdf_path=pdf_path, n=100, shift=400)
    for r in res:
        shutil.copy(r, r'C:\Users\Filipp\PycharmProjects\Invoice_scanner\IN')
