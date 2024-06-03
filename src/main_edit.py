from config import config
from glob import glob
from natsort import os_sorted
import os
import shutil
import numpy as np
from pdf2image import convert_from_path
from PIL import Image

from rotator import main as rotate
from utils import is_scanned_pdf, count_pages
from utils import rename_files_in_directory
from utils import add_text_bar
from crop_tables import define_and_combine, define_and_return


def main():
    """ take all files in IN_FOLDER, preprocess, extract additional and save to IN_FOLDER_EDIT"""

    rename_files_in_directory(config['IN_FOLDER'])

    # collect files
    files, extensions = [], ['.pdf', '.jpeg', '.jpg', '.png']
    for ext in extensions:
        files.extend(glob(os.path.join(config['IN_FOLDER'], f'*{ext}')))

    # preprocess and copy to "edited"
    for file in os_sorted(files):
        file_type = os.path.splitext(file)[1]
        file_name = os.path.basename(file).rsplit('.', 1)[0]

        # if digital pdf
        if (file_type.lower() == '.pdf') and (is_scanned_pdf(file) is False):
            if count_pages(file) > 5:
                print(f'page limit exceeded in {file}')
                continue
            save_path = os.path.join(config['IN_FOLDER_EDIT'], file_name + f'_{file_type.replace(".", "")}' + '.pdf')
            shutil.copy(file, save_path)

        # if file is image, or file is scanned pdf
        else:
            # if scanned pdf-file -> get first page in jpg
            if file_type.lower() == '.pdf':
                image = np.array(convert_from_path(file, first_page=0, last_page=1,
                                                   fmt='jpg', poppler_path=config["POPPLER_PATH"])[0])
            # if image-file
            elif file_type.lower() in ['.jpg', '.jpeg', '.png']:
                image = np.array(Image.open(file))
            else:
                print(f'ERROR IN: {file}')
                continue
            rotated = Image.fromarray(rotate(image))
            save_path = os.path.join(config['IN_FOLDER_EDIT'], file_name + f'_{file_type.replace(".", "")}' + '.jpg')
            if rotated.mode == "RGBA":
                rotated = rotated.convert('RGB')
            rotated.save(save_path, quality=100)

            # # extract, crop and stuck image tables
            # cropped_save_path = os.path.splitext(save_path)[0] + '_TAB+' + os.path.splitext(save_path)[1]
            # cropped = define_and_combine(save_path)
            # if cropped:
            #     cropped.save(cropped_save_path)
            #     command = f'magick convert {cropped_save_path} {config["magick_opt"]} {cropped_save_path}'
            #     os.system(command)

            # extract and crop two tables
            cropped_save_path1 = os.path.splitext(save_path)[0] + '_TAB1+' + os.path.splitext(save_path)[1]
            cropped_save_path2 = os.path.splitext(save_path)[0] + '_TAB2+' + os.path.splitext(save_path)[1]
            table_title, table_ship = define_and_return(save_path)
            if table_title:
                table_title = add_text_bar(table_title, 'Банковские реквизиты поставщика')
                table_title.save(cropped_save_path1)
                command = f'magick convert {cropped_save_path1} {config["magick_opt"]} {cropped_save_path1}'
                os.system(command)
            if table_ship:
                table_ship = add_text_bar(table_ship, 'Услуги')
                table_ship.save(cropped_save_path2)
                command = f'magick convert {cropped_save_path2} {config["magick_opt"]} {cropped_save_path2}'
                os.system(command)

            command = f'magick convert {save_path} {config["magick_opt"]} {save_path}'
            print(command)
            os.system(command)

        print(save_path)
    print('Завершено!')


if __name__ == '__main__':
    main()
    # z = os.path.join(os.path.dirname(__file__), '..', 'data', '620.jpg')
    # z = r'C:\Users\Filipp\PycharmProjects\Invoice_scanner\IN\edited\620.jpg'
    # print(os.path.splitext(z)[0]+'_tab')
    # print(os.path.split(z))
