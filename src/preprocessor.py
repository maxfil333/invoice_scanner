import numpy as np
import cv2


def cyrillic_processing(image_path: str) -> np.array:
    """ Функция обработчик путей файлов содержащих кириллицу """

    try:
        f = open(image_path, "rb")
    except FileNotFoundError:
        return None
    chunk = f.read()
    chunk_arr = np.frombuffer(chunk, dtype=np.uint8)
    image = cv2.imdecode(chunk_arr, cv2.IMREAD_COLOR)
    f.close()
    return image


def gray_and_threshold(image: np.array, thresh=127, maxval=255) -> np.array:
    """ Перевод в градации серого и бинаризация """

    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = gray_image

    # blur = cv2.GaussianBlur(blur,(3,3),0)
    # kernel = np.ones((2, 2), np.uint8)
    # blur = cv2.dilate(blur, kernel, iterations=1)

    # ret, threshold_image = cv2.threshold(gray_image, thresh, maxval, cv2.THRESH_BINARY)
    ret, threshold_image = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    np_image = np.array(threshold_image)
    return np_image


def gray_to_rgb(image: np.array) -> np.array:
    """ Преобразовать одноканальное изображение в трехканальное """

    if len(np.array(image).shape) == 2:
        np_image = np.repeat(np.array(image)[:, :, np.newaxis], 3, axis=2)
        return np_image
    else:
        return image


def main(image_path: str) -> np.array:
    """ Принимает на вход путь, возвращает np.array """

    return gray_to_rgb(gray_and_threshold(cyrillic_processing(image_path)))
