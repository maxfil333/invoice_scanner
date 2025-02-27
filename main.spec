# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

datas = [
    ('C:\\Program Files\\poppler-24.07.0\\Library\\bin', 'poppler'),
    ('src', 'src'),
    ('config', 'config'),
    ('C:\\Program Files\\Tesseract-OCR', 'Tesseract-OCR'),
    ('C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI', 'magick')
]

binaries = []
hiddenimports = ['tiktoken_ext.openai_public', 'tiktoken_ext']

# Список библиотек для автоматического сбора данных
libraries = ['chromadb', 'geotext', 'natasha']

# Автоматический сбор данных, бинарников и скрытых импортов для указанных библиотек
for lib in libraries:
    tmp_ret = collect_all(lib)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main'
)
