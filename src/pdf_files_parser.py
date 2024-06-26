import os
import shutil
from glob import glob

from config.config import config


class BreakException(Exception):
    pass


def parse(pdf_path, n_folders, shift_folders, max_pdf_amount):
    folders = glob(pdf_path)
    folders.sort(key=os.path.getmtime, reverse=True)
    folders = folders[0 + shift_folders: n_folders + shift_folders]  # <-- новые : старые -->
    result = []
    try:
        for f in folders:
            invoice_path1 = os.path.join(os.path.abspath(f), r'Счет поставщика\*.pdf')
            invoice_path2 = os.path.join(os.path.abspath(f), '*.pdf')
            pdfs1 = glob(invoice_path1)
            pdfs2 = glob(invoice_path2)
            pdfs = []
            pdfs.extend(pdfs1)
            pdfs.extend(pdfs2)
            for pdf in pdfs:
                result.append(pdf)
                if len(result) == max_pdf_amount:
                    raise BreakException
    except BreakException:
        pass
    return result


if __name__ == '__main__':
    base_path = r'\\10.10.0.3\docs\Baltimpex\Invoice\TR\Import\*'
    save_folder = os.path.join(config['IN_FOLDER'], '__data3')
    res = parse(base_path, 50, 0, max_pdf_amount=9999)
    for i, r in enumerate(res):
        print(i, r)
        shutil.copy(r, save_folder)
