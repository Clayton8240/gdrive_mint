# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('/home/clayton/Documentos/GitHub/gdrive_mint/.venv/lib/python3.12/site-packages/customtkinter', 'customtkinter'), ('/home/clayton/Documentos/GitHub/gdrive_mint/.venv/lib/python3.12/site-packages/PIL', 'PIL'), ('app', 'app')]
binaries = []
hiddenimports = ['PIL._tkinter_finder', 'customtkinter', 'pystray._xorg', 'google.auth.transport.requests', 'google_auth_oauthlib.flow', 'googleapiclient.discovery', 'watchdog.observers', 'watchdog.observers.inotify', 'cryptography.fernet', 'plyer.platforms.linux.notification']
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


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
    a.binaries,
    a.datas,
    [],
    name='GDrive-Mint-Universal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
