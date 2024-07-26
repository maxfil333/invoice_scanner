import os
import shutil
import subprocess
import numpy as np
from glob import glob
from PIL import Image
from itertools import count
from natsort import os_sorted
from pdf2image import convert_from_path

from logger import logger
from config.config import config, NAMES
from rotator import main as rotate
from crop_tables import define_and_return
from utils import add_text_bar, image_upstanding, rename_files_in_directory
from utils import is_scanned_pdf, count_pages, align_pdf_orientation


def main(hide_logs=False, stop_when=-1):
    """ take all files in IN_FOLDER, preprocess, extract additional and save to IN_FOLDER_EDIT"""

    rename_files_in_directory(config['IN_FOLDER'], hide_logs=hide_logs)

    # collect files
    files, extensions = [], ['.pdf', '.jpeg', '.jpg', '.png']
    for ext in extensions:
        files.extend(glob(os.path.join(config['IN_FOLDER'], f'*{ext}')))

    # preprocess and copy to "edited"
    c = count(1)
    for file in os_sorted(files):
        file_type = os.path.splitext(file)[1]
        file_name = os.path.basename(file).rsplit('.', 1)[0]

        # if digital pdf
        if (file_type.lower() == '.pdf') and (is_scanned_pdf(file) is False):
            if count_pages(file) > 6:
                logger.print(f'page limit exceeded in {file}')
                continue
            save_path = os.path.join(config['EDITED'], file_name + f'_{file_type.replace(".", "")}' + '.pdf')
            align_pdf_orientation(file, save_path)

        # if file is image, or file is scanned pdf
        else:
            # if file is scanned pdf -> get first page in jpg
            if file_type.lower() == '.pdf':
                image = np.array(convert_from_path(file, first_page=0, last_page=1, fmt='jpg',
                                                   poppler_path=config["POPPLER_PATH"],
                                                   jpegopt={"quality": 100})[0])
            # if file is image
            elif file_type.lower() in ['.jpg', '.jpeg', '.png']:
                image = np.array(Image.open(file))
            else:
                logger.print(f'ERROR IN: {file}')
                continue
            upstanding = image_upstanding(image)  # 0-90-180-270 rotate
            rotated = Image.fromarray(rotate(upstanding))  # accurate rotate
            save_path = os.path.join(config['EDITED'], file_name + f'_{file_type.replace(".", "")}' + '.jpg')
            if rotated.mode == "RGBA":
                rotated = rotated.convert('RGB')
            rotated.save(save_path, quality=100)

            # extract and crop two tables
            cropped_save_pth1 = os.path.splitext(save_path)[0] + '_TAB1+' + os.path.splitext(save_path)[1]
            cropped_save_pth2 = os.path.splitext(save_path)[0] + '_TAB2+' + os.path.splitext(save_path)[1]
            table_title, table_ship = define_and_return(save_path)
            if table_title:
                table_title = add_text_bar(table_title, 'Банковские реквизиты поставщика')
                table_title.save(cropped_save_pth1)
                command = [config["magick_exe"], "convert", cropped_save_pth1, *config["magick_opt"], cropped_save_pth1]
                subprocess.run(command)
            if table_ship:
                table_ship = add_text_bar(table_ship, NAMES.goods)
                table_ship.save(cropped_save_pth2)
                command = [config["magick_exe"], "convert", cropped_save_pth2, *config["magick_opt"], cropped_save_pth2]
                subprocess.run(command)

            command = [config["magick_exe"], "convert", save_path, *config["magick_opt"], save_path]
            subprocess.run(command)

        logger.print(save_path)

        # _____  STOP ITERATION  _____
        if stop_when > 0:
            stop = next(c)
            if stop == stop_when:
                break

    logger.print(f"\nФайлы сохранены в {config['EDITED']}\n")


if __name__ == '__main__':
    main()
