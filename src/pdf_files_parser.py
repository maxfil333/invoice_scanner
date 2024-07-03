import os
import re
import shutil
from glob import glob

from config.config import config


class BreakException(Exception):
    pass


def parse(pdf_path, n_folders, shift_folders, max_pdf_amount):
    folders = glob(pdf_path)
    folders.sort(key=os.path.getmtime, reverse=True)
    folders = [f for f in folders if os.path.isdir(f)]
    folders = folders[0 + shift_folders: n_folders + shift_folders]  # <-- новые : старые -->
    result = []
    try:
        for f in folders:
            pdfs = glob(os.path.join(os.path.abspath(f), '**', '*.pdf'), recursive=True)
            for pdf in pdfs:
                if re.findall(r'.*PATTERN.*', pdf, re.IGNORECASE):
                    print(f, pdf)
                result.append(pdf)
                if len(result) == max_pdf_amount:
                    raise BreakException
    except BreakException:
        pass
    return result


if __name__ == '__main__':
    base_path = r'\\10.10.0.3\docs\Baltimpex\Invoice\Import\*'
    save_folder = os.path.join(config['IN_FOLDER'], '__new_data2')
    res = parse(base_path, 1000, 1000, max_pdf_amount=200)

    # for i, r in enumerate(res):
    #     print(i, r)
    #     shutil.copy(r, save_folder)
