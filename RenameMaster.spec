# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/Desktop/SD/13.Rename/src/rename_master/main.py'],
    pathex=['D:/Desktop/SD/13.Rename/src'],
    binaries=[],
    datas=[],
    hiddenimports=['PIL', 'openpyxl', 'docx', 'pypdf'],
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
