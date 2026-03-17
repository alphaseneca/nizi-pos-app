# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for NiziPOS Background App.
Build with:  pyinstaller build.spec
"""

import os

import platform

# Identify pystray backend based on OS
pystray_backend = []
if platform.system() == "Windows":
    pystray_backend = ['pystray._win32']
elif platform.system() == "Darwin":
    pystray_backend = ['pystray._darwin']
else: # Linux
    pystray_backend = ['pystray._xorg', 'pystray._appindicator']

base_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(base_dir, 'main.py')],
    pathex=[base_dir],
    binaries=[],
    datas=[
        (os.path.join(base_dir, 'static'), 'static'),
        (os.path.join(base_dir, 'assets'), 'assets'),
    ],
    hiddenimports=[
        'flask',
        'flask_socketio',
        'engineio.async_drivers.threading',
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        'pystray',
        'PIL',
        'platformdirs',
    ] + pystray_backend,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NiziPOS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # ← no terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,               # add .ico path here if desired
)
