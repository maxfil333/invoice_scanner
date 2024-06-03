import os.path
import tqdm
from glob import glob

from pdf_files_parser import parse
from pdf2image import convert_from_path

POPPLER_PATH = r'C:\Program Files\poppler-22.01.0\Library\bin'
result_pdf_files = parse(pdf_path=r'\\10.10.0.3\docs\Baltimpex\Invoice\TR\Import\*', n=15, shift=0)


def convert_pdfs(pdf_paths, output_folder, first_page=0, last_page=1, dpi=350, fmt='jpeg'):
    for pdf_path in tqdm.tqdm(pdf_paths):
        output_filename = os.path.basename(pdf_path).strip('.pdf')
        if fmt == 'jpeg':
            convert_from_path(pdf_path, dpi, output_folder, first_page, last_page, fmt, poppler_path=POPPLER_PATH,
                              thread_count=4,
                              output_file=output_filename,
                              jpegopt={"quality": 100, "progressive": False, "optimize": True})
        else:
            convert_from_path(pdf_path, dpi, output_folder, first_page, last_page, fmt, poppler_path=POPPLER_PATH,
                              thread_count=4,
                              output_file=output_filename)


if __name__ == '__main__':
    # print(result_pdf_files)
    # convert_pdfs(result_pdf_files, r'output')
    # convert_pdfs(pdf_paths= ['777.pdf'],output_folder= '.',  first_page=0 ,last_page=1, fmt='PNG')
    image = convert_from_path('2.pdf',output_folder='.',  first_page=0 ,last_page=1, fmt='jpeg', poppler_path=POPPLER_PATH)
    # convert_pdfs(['PCSLSYF601240207.pdf'], '.')
    # convert_pdfs(glob('new_pdfs/*.pdf'), 'new_raw_images')
