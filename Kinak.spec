# -*- mode: python ; coding: utf-8 -*-

print(">>> SPEC FILE LOADED - ONEFILE MODE <<<")

a = Analysis(
    ['Kinak.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('icons/*', 'icons'), # Používame doprednú lomku pre lepšiu kompatibilitu
    ],
    hiddenimports=[
        'screeninfo',
        'screeninfo.common',
        'screeninfo.win32',
        # --- pridané pre lazy import sťahovania ---
        'requests',
        'urllib3',
        'idna',
        'charset_normalizer',
        'certifi',
        'bs4',
        'bs4.builder',
        'bs4.builder._htmlparser',
        'bs4.builder._lxml',
        'html.parser',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['setuptools'],
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
    name='Kinak',
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
    icon='icons/Kinak32.ico',
)

# BLOK COLLECT SME VYMAZALI - v Onefile režime nie je potrebný