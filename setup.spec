# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['installer_logic.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\revis\\art\\Git Hub Projects\\LocalReader-Pro\\dist/requirements.txt', '.'), ('C:\\Users\\revis\\art\\Git Hub Projects\\LocalReader-Pro\\dist/launch.vbs', '.'), ('C:\\Users\\revis\\art\\Git Hub Projects\\LocalReader-Pro\\dist/main.py', '.'), ('C:\\Users\\revis\\art\\Git Hub Projects\\LocalReader-Pro\\dist/uninstaller.py', '.'), ('C:\\Users\\revis\\art\\Git Hub Projects\\LocalReader-Pro\\dist/uninstall.exe', '.'), ('C:\\Users\\revis\\art\\Git Hub Projects\\LocalReader-Pro\\dist\\app\\config.py', 'app'), ('C:\\Users\\revis\\art\\Git Hub Projects\\LocalReader-Pro\\dist\\app\\models.py', 'app'), ('C:\\Users\\revis\\art\\Git Hub Projects\\LocalReader-Pro\\dist\\app\\server.py', 'app'), ('C:\\Users\\revis\\art\\Git Hub Projects\\LocalReader-Pro\\dist\\app\\state.py', 'app'), ('C:\\Users\\revis\\art\\Git Hub Projects\\LocalReader-Pro\\dist\\app\\utils.py', 'app'), ('C:\\Users\\revis\\art\\Git Hub Projects\\LocalReader-Pro\\dist\\app\\__init__.py', 'app'), ('C:\\Users\\revis\\art\\Git Hub Projects\\LocalReader-Pro\\dist\\app\\locales', 'app/locales'), ('C:\\Users\\revis\\art\\Git Hub Projects\\LocalReader-Pro\\dist\\app\\logic', 'app/logic'), ('C:\\Users\\revis\\art\\Git Hub Projects\\LocalReader-Pro\\dist\\app\\routers', 'app/routers'), ('C:\\Users\\revis\\art\\Git Hub Projects\\LocalReader-Pro\\dist\\app\\ui', 'app/ui')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'pandas', 'torch', 'PIL', 'cv2', 'matplotlib', 'scipy', 'sklearn', 'tensorflow'],
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
    name='setup',
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
    uac_admin=True,
)
