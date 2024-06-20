<i>примеры команд:</i>
> pyinstaller --add-data "C:\Program Files\poppler-22.01.0\Library\bin;poppler" --onefile config/config.py


## Добавление дополнительных файлов и папок к сборке.

### 1. Как добавить к сборке tesseract:

- 1.1. Командой ..
> pyinstaller --add-data "C:\Program Files\Tesseract-OCR;Tesseract-OCR" --onefile main.py
> 
.. добавляем копию тессаракта в папку \
Users\User\AppData\Local\Temp\%TEMPFOLDERNAME%\Tesseract-OCR;
- 1.2. Получить путь к копии tesseract.exe через ..
> bundle_dir = sys._MEIPASS\
> pytesseract.pytesseract.tesseract_cmd = os.path.join(bundle_dir, 'Tesseract-OCR', 'tesseract.exe')


### 2. Создание и редактирование файла .spec:

- 2.1. Создать файл filename.spec командой
> pyinstaller --onefile src/filename.py
> 
- 2.2. Файл filename.spec отредактировать. Добавить в datas имена папок с алиасами:\
  (это второй способ добавить tesseract в сборку)
>datas=[\
('C:\\Program Files\\poppler-22.01.0\\Library\\bin', 'poppler'), \
('src', 'src'), \
('config', 'config'),\
('C:\Program Files\Tesseract-OCR', 'Tesseract-OCR')\
],
- 2.3. Удалить dist, build
- 2.4. Выполнить pyinstaller filename.spec

### 3. Добавление ImageMagick
- IM доступен через cmd-команду \
*magick convert ...* \
т.к. обычно находится в системных переменных **Path**.
- Команда *magick* может быть заменена полным путем до исполняемого файла, например \
*"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe" convert ...* 
- Таким образом надо переписать команду \
**"magick convert..."** на 
**"%MAGICK_EXE_PATH% convert ..."** \
где %MAGICK_EXE_PATH% может быть получен либо через sys._MEIPASS, \
либо через абсолютный путь к файлу 
magick.exe, в случае, если проект собирается без опции --onefile.

