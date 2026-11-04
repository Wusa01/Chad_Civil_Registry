
# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

# Application templates and static assets
datas = [
    ('app/templates', 'app/templates'),
    ('app/static', 'app/static'),
]

binaries = []
hiddenimports = []

# Collect Flask dependencies and their required files
for package in [
    'flask',
    'flask_sqlalchemy',
    'flask_login',
    'flask_migrate',
    'flask_bcrypt',
    'flask_mail',
]:
    tmp_ret = collect_all(package)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

a = Analysis(
    ['desktop.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'webview',
        'pythonnet',
        'clr',
        'clr_loader',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ChadCivilRegistry',
    icon='app/static/images/chad-civil-registry.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
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
    name='ChadCivilRegistry',
)
