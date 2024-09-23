import os
import tqdm
from glob import glob
from pdf2image import convert_from_path

from config.config import config
from src.pdf_files_parser import parse


def convert_pdfs(pdf_paths, output_folder, first_page=0, last_page=1, dpi=350, fmt='jpeg'):
    for pdf_path in tqdm.tqdm(pdf_paths):
        output_filename = os.path.basename(pdf_path).strip('.pdf')
        if fmt == 'jpeg':
            convert_from_path(pdf_path, dpi, output_folder, first_page, last_page, fmt,
                              poppler_path=config['POPPLER_PATH'],
                              thread_count=4,
                              output_file=output_filename,
                              jpegopt={"quality": 100, "progressive": False, "optimize": True})
        else:
            convert_from_path(pdf_path, dpi, output_folder, first_page, last_page, fmt,
                              poppler_path=config['POPPLER_PATH'],
                              thread_count=4,
                              output_file=output_filename)


if __name__ == '__main__':
    result_pdf_files = glob(r'C:\Users\Filipp\PycharmProjects\Invoice_scanner\IN\__data2\*.pdf')
    convert_pdfs(result_pdf_files, r'C:\Users\Filipp\PycharmProjects\Invoice_scanner\IN\__data2\jpg')
