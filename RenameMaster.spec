# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/Desktop/SD/13.Rename/src/rename_master/main.py'],
    pathex=['D:/Desktop/SD/13.Rename/src'],
    binaries=[],
    datas=[('D:/Desktop/SD/13.Rename/assets', 'assets')],
    hiddenimports=['PIL', 'openpyxl', 'docx', 'pypdf', 'tkinterdnd2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'fontTools', 'scipy', 'pandas', 'matplotlib', 'cv2', 'skimage', 'sklearn', 'PyWavelets', 'blind_watermark', 'pydoc_data', 'unittest', 'pytest', 'setuptools', 'pip', 'yaml', 'psutil', 'PIL.AvifImagePlugin', 'PIL.WebPImagePlugin', 'PIL.Jpeg2KImagePlugin', 'PIL.TiffImagePlugin', 'PIL.ImageQt'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RenameMaster',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:/Desktop/SD/13.Rename/assets/rename_master.ico'],
)
