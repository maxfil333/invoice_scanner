примеры команд:
pyinstaller --add-data "C:\Program Files\poppler-22.01.0\Library\bin;poppler" --onefile config/config.py


## Добавление дополнительных файлов и папок к сборке.

### 1. Получение путей в скомпилированном файле:

- 1.1. Командой
> pyinstaller --add-data "C:\Program Files\Tesseract-OCR;local_tes" --onefile main.py
> 
добавляем копию тессаракта в папку local_tes;
- 1.2. Получить путь к tesseract.exe через sys._MEIPASS / local_tes / tesseract.exe
- 1.3. Линкануть полученный путь через pytesseract.tesseract_cmd


### 2. Создание и редактирование файла .spec:

- 2.1. Создать файл ___.spec командой
> pyinstaller --onefile src/___.py
> 
- 2.2. Файл ___.spec отредактировать. Добавить в datas имена папок с алиасами: 
    datas=[
        ('src', 'src'),
        ('config', 'config')
    ],
- 2.3. Удалить dist, build
- 2.4. Выполнить pyinstaller ___.spec
