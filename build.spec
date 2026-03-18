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
        'engineio.async_drivers.eventlet',
        'eventlet',
        'bidict',
        'engineio',
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
    [],                      # Move binaries/zipfiles/datas to COLLECT for non-onefile macOS bundle
    exclude_binaries=True,   # Required for BUNDLE on macOS sometimes
    name='NiziPOS',       # Internal name
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NiziPOS',
)

# Added BUNDLE for macOS to create a proper .app and hide terminal
if is_mac:
    app = BUNDLE(
        coll,                # Use collective binaries
        name='NiziPOS.app',
        icon=None,
        bundle_identifier='com.nizistore.nizipos',
        info_plist={
            'LSUIElement': True,
            'NSHighResolutionCapable': 'True'
        },
    )
