import os
import json
import subprocess
import numpy as np
from PIL import Image
from itertools import count
from pdf2image import convert_from_path

from config.config import config, NAMES
from src.utils import is_scanned_pdf, count_pages, align_pdf_orientation, extract_pages
from src.utils import pack_folders, mark_get_required_pages, mark_get_main_file
from src.utils import add_text_bar, image_upstanding, rename_files_in_directory
from src.crop_tables import define_and_return
from src.rotator import main as rotate
from src.logger import logger


def main(dir_path: str = config['IN_FOLDER'], hide_logs=False, stop_when=-1):
    """ for folder in dir_path(IN), creates folder in EDITED, preprocess, extract additional and save to this folder """

    # переименование файлов и папок
    rename_files_in_directory(dir_path, hide_logs=hide_logs)
    # упаковка одиночных файлов в папки
    pack_folders(dir_path)

    c = count(1)

    for folder_ in os.scandir(dir_path):
        if not os.listdir(folder_):
            continue
        folder, folder_name = folder_.path, folder_.name
        main_file = os.path.abspath(os.path.join(folder, mark_get_main_file(folder)))
        main_base = os.path.basename(main_file)
        main_type = os.path.splitext(main_file)[-1]
        extra_files = [os.path.abspath(x.path) for x in os.scandir(folder) if x.is_dir() is False]
        extra_files.remove(main_file)
        required_pages = mark_get_required_pages(main_file)
        print('main_file:', main_file)
        print('required_pages:', required_pages)
        print('extra_files:', extra_files)

        edited_folder = os.path.join(config['EDITED'], folder_name)
        main_save_path = os.path.join(edited_folder, main_base)
        os.makedirs(edited_folder, exist_ok=False)
        main_local_files = []  # список главных файлов (без _TAB1, _TAB2)

        # if digital pdf
        if (main_type.lower() == '.pdf') and (is_scanned_pdf(main_file, required_pages) is False):
            print('file type: digital')
            if required_pages:
                pdf_bytes = extract_pages(main_file, pages_to_keep=required_pages)
                align_pdf_orientation(pdf_bytes, main_save_path)
            else:
                if count_pages(main_file) > 7:
                    logger.print(f'page limit exceeded in {main_file}')
                    continue
                align_pdf_orientation(main_file, main_save_path)

        # if file is (image | scanned pdf)
        else:
            print('file type: scanned')
            # scanned pdf
            if main_type.lower() == '.pdf':
                images = []
                if required_pages:
                    for page in required_pages:
                        image = np.array(convert_from_path(main_file, first_page=page, last_page=page, fmt='jpg',
                                                           poppler_path=config["POPPLER_PATH"],
                                                           jpegopt={"quality": 100})[0])
                        images.append(image)

                else:  # get first page in jpg
                    image = np.array(convert_from_path(main_file, first_page=1, last_page=1, fmt='jpg',
                                                       poppler_path=config["POPPLER_PATH"],
                                                       jpegopt={"quality": 100})[0])
                    images.append(image)

            # if file is image
            elif main_type.lower() in ['.jpg', '.jpeg', '.png']:
                images = [np.array(Image.open(main_file))]
            else:
                logger.print(f'main edit. ERROR IN: {main_file}')
                continue

            for i, image in enumerate(images):
                try:
                    upstanding = image_upstanding(image)  # 0-90-180-270 rotate
                except:
                    upstanding = image
                try:
                    rotated = Image.fromarray(rotate(upstanding))  # accurate rotate
                except:
                    rotated = upstanding
                name, ext = os.path.splitext(main_save_path)
                idx_save_path = f'{name}({i}).jpg'
                if rotated.mode == "RGBA":
                    rotated = rotated.convert('RGB')
                rotated.save(idx_save_path, quality=100)
                main_local_files.append(idx_save_path)

                # extract and crop two tables
                cropped_save_pth1 = os.path.splitext(idx_save_path)[0] + '_TAB1+' + os.path.splitext(idx_save_path)[1]
                cropped_save_pth2 = os.path.splitext(idx_save_path)[0] + '_TAB2+' + os.path.splitext(idx_save_path)[1]
                table_title, table_ship = define_and_return(idx_save_path)
                if table_title:
                    table_title = add_text_bar(table_title, 'Банковские реквизиты поставщика')
                    table_title.save(cropped_save_pth1)
                    command = [config["magick_exe"], "convert", cropped_save_pth1, *config["magick_opt"],
                               cropped_save_pth1]
                    subprocess.run(command)
                if table_ship:
                    table_ship = add_text_bar(table_ship, NAMES.goods)
                    table_ship.save(cropped_save_pth2)
                    command = [config["magick_exe"], "convert", cropped_save_pth2, *config["magick_opt"],
                               cropped_save_pth2]
                    subprocess.run(command)

                command = [config["magick_exe"], "convert", idx_save_path, *config["magick_opt"], idx_save_path]
                subprocess.run(command)

        with open(os.path.join(edited_folder, 'params.json'), 'w', encoding='utf-8') as f:
            params_dict = {"main_file": main_file, "extra_files": extra_files, "main_local_files": main_local_files}
            json.dump(params_dict, f, ensure_ascii=False, indent=4)

        print('------------------------------')
        # _____  STOP ITERATION  _____
        if stop_when > 0:
            stop = next(c)
            if stop == stop_when:
                break


if __name__ == '__main__':
    main()
