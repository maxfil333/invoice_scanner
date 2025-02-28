import os
import json
import shutil
import traceback
import subprocess
import numpy as np
from PIL import Image
from itertools import count
from pdf2image import convert_from_path

from config.config import config, NAMES
from src.logger import logger
from src.utils import is_scanned_pdf, count_pages, align_pdf_orientation, extract_pages, delete_all_files
from src.utils import filtering_and_foldering_files, mark_get_required_pages, mark_get_main_file, mark_get_title
from src.utils import add_text_bar, image_upstanding_and_rotate, rename_files_in_directory
from src.crop_tables import define_and_return


def main(dir_path: str = config['IN_FOLDER'], hide_logs=False, stop_when=-1):
    """ for folder in dir_path(IN), creates folder in EDITED, preprocess, extract additional and save to this folder """

    # очистка EDITED
    delete_all_files(config['EDITED'])
    # переименование файлов и папок
    rename_files_in_directory(dir_path, hide_logs=hide_logs)
    # упаковка одиночных файлов в папки
    filtering_and_foldering_files(dir_path)

    c = count(1)

    for folder_ in os.scandir(dir_path):
        if not os.path.isdir(folder_):  # folder_ это не папка -> пропускаем
            continue
        if not os.listdir(folder_):  # если пустая папка -> пропускам
            continue
        folder, folder_name = folder_.path, folder_.name
        main_file = os.path.abspath(os.path.join(folder, mark_get_main_file(folder)))
        if os.path.isdir(main_file):
            continue
        main_base = os.path.basename(main_file)
        main_type = os.path.splitext(main_file)[-1]
        if main_type not in config['valid_ext'] + config['excel_ext']:  # если недопустимое расширение -> пропускам
            continue
        extra_files = [os.path.abspath(x.path) for x in os.scandir(folder) if x.is_dir() is False]
        extra_files.remove(main_file)
        required_pages = mark_get_required_pages(main_file)
        title_page = mark_get_title(main_file)
        if title_page:
            required_pages.remove(title_page)

        print('main_file:', main_file)
        print('title_page:', title_page)
        print('required_pages:', required_pages)
        print('extra_files:', extra_files)

        edited_folder = os.path.join(config['EDITED'], folder_name)
        main_save_path = os.path.join(edited_folder, main_base)
        os.makedirs(edited_folder, exist_ok=False)
        goods_tables_images = []  # список изображений _TAB2+ (таблиц с услугами)
        main_local_files = []  # список главных изображений (без _TAB1, _TAB2);
        # если scannedPDF + required_pages, то len(main_local_files) может быть > 1

        try:
            # if digital pdf
            if (main_type.lower() == '.pdf') and (is_scanned_pdf(main_file, required_pages) is False):
                print('file type: digital')
                if required_pages:
                    pdf_bytes = extract_pages(main_file, pages_to_keep=required_pages)
                    align_pdf_orientation(pdf_bytes, main_save_path)
                    if title_page:
                        pdf_bytes = extract_pages(main_file, pages_to_keep=[title_page])
                        os.makedirs(os.path.join(edited_folder, 'title_page'))
                        align_pdf_orientation(pdf_bytes, os.path.join(edited_folder, 'title_page', main_base))

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
                        if title_page:
                            image = np.array(convert_from_path(main_file, first_page=title_page, last_page=title_page,
                                                               fmt='jpg',
                                                               poppler_path=config["POPPLER_PATH"],
                                                               jpegopt={"quality": 100})[0])
                            os.makedirs(os.path.join(edited_folder, 'title_page'))
                            rotated = image_upstanding_and_rotate(image)
                            save_path = os.path.join(edited_folder, 'title_page', 'title.jpg')
                            rotated.save(save_path, quality=100)
                            main_local_files.append(save_path)

                    else:  # get first page in jpg
                        image = np.array(convert_from_path(main_file, first_page=1, last_page=1, fmt='jpg',
                                                           poppler_path=config["POPPLER_PATH"],
                                                           jpegopt={"quality": 100})[0])
                        images.append(image)

                # if file is image
                elif main_type.lower() in ['.jpg', '.jpeg', '.png']:
                    images = [np.array(Image.open(main_file))]
                elif main_type.lower() in config['excel_ext']:
                    shutil.copy(main_file, main_save_path)
                    images = []
                else:
                    logger.print(f'main edit. ERROR IN: {main_file}')
                    continue

                for i, image in enumerate(images):
                    rotated = image_upstanding_and_rotate(image)
                    name, ext = os.path.splitext(main_save_path)
                    idx_save_path = f'{name}({i}).jpg'
                    rotated.save(idx_save_path, quality=100)
                    main_local_files.append(idx_save_path)

                    # extract and crop two tables
                    cropped_save_pth1 = os.path.splitext(idx_save_path)[0] + '_TAB1+' + os.path.splitext(idx_save_path)[1]
                    cropped_save_pth2 = os.path.splitext(idx_save_path)[0] + '_TAB2+' + os.path.splitext(idx_save_path)[1]
                    table_title, table_ship, coords = define_and_return(idx_save_path)
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
                        goods_tables_images.append(cropped_save_pth2)
                    if coords and coords['table_shp']:
                        try:
                            x1, y1, x2, y2 = coords['table_shp']
                            coords_name, coords_ext = os.path.splitext(idx_save_path)
                            cropped_save_pth3 = coords_name + '_TAB3+' + coords_ext
                            Image.fromarray(image).crop((x1, 0, x2, y1)).save(cropped_save_pth3)
                            command = [config["magick_exe"], "convert", cropped_save_pth3, *config["magick_opt"],
                                       cropped_save_pth3]
                            subprocess.run(command)
                        except Exception:
                            logger.print(traceback.format_exc())

                    command = [config["magick_exe"], "convert", idx_save_path, *config["magick_opt"], idx_save_path]
                    subprocess.run(command)

            with open(os.path.join(edited_folder, 'params.json'), 'w', encoding='utf-8') as f:
                params_dict = {"main_file": main_file,
                               "extra_files": extra_files,
                               "main_local_files": main_local_files,
                               "goods_tables_images": goods_tables_images}
                json.dump(params_dict, f, ensure_ascii=False, indent=4)
        except:
            logger.print("ERROR IN MAIN_EDIT:", traceback.format_exc(), sep='\n')

        print('------------------------------')
        # _____  STOP ITERATION  _____
        if stop_when > 0:
            stop = next(c)
            if stop == stop_when:
                break


if __name__ == '__main__':
    main()
