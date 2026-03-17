# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for NiziPOS Background App.
Build with:  pyinstaller build.spec
"""

import os

import platform

# Identify platform details
is_mac = platform.system() == "Darwin"

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
        'PyQt6',
        'PIL',
        'platformdirs',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pystray'],
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
    console=False,           # ← no terminal window on Windows
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,               # add .ico path here if desired
)

# Added BUNDLE for macOS to create a proper .app and hide terminal
if is_mac:
    app = BUNDLE(
        exe,
        name='NiziPOS.app',
        icon=None,
        bundle_identifier='com.nizipos.backgroundapp',
        info_plist={
            'LSUIElement': True,  # Hide from Dock (optional, usually good for tray apps)
            'NSHighResolutionCapable': 'True'
        },
    )
