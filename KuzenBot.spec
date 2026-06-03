# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],      # Główny plik startowy
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),  # Dołączamy TYLKO pliki graficzne/dane, a nie kod Pythona!
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'requests',
        'certifi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --- ⏱️ DODANA SEKCJA SPLASH SCREENA ---
splash = Splash(
    'assets/logo.jpg',         # Ścieżka do Twojego obrazka ładowania
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,             # Brak paska postępu z tekstem (czysty obrazek)
    text_size=12,
    minify_script=True,
    always_on_top=True         # Splash zawsze na wierzchu, żeby był dobrze widoczny
)
# ---------------------------------------

exe = EXE(
    pyz,
    a.scripts,
    splash,                    # <--- DODANE: Przekazujemy splash
    splash.binaries,           # <--- DODANE: Binarne pliki splasha
    exclude_binaries=True,     # Oddzielamy pliki od pliku .exe (szybsze uruchamianie)
    name='KuzenBot_App',           # Nazwa pliku startowego
    version='version.txt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,             # Brak czarnego okna
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.ico',    # Twoje logo
    uac_admin=True,            # Uprawnienia Administratora dla skrótów!
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KuzenBot_App',
)