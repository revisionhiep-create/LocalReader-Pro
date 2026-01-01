# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['installer_logic.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\revis\\art\\Git Hub Projects\\Local Reader Project\\LocalReader-Pro-v2.3\\dist/requirements.txt', '.'), ('C:\\Users\\revis\\art\\Git Hub Projects\\Local Reader Project\\LocalReader-Pro-v2.3\\dist/launch.vbs', '.'), ('C:\\Users\\revis\\art\\Git Hub Projects\\Local Reader Project\\LocalReader-Pro-v2.3\\dist/main.py', '.'), ('C:\\Users\\revis\\art\\Git Hub Projects\\Local Reader Project\\LocalReader-Pro-v2.3\\dist/uninstaller.py', '.'), ('C:\\Users\\revis\\art\\Git Hub Projects\\Local Reader Project\\LocalReader-Pro-v2.3\\dist/app', 'app'), ('C:\\Users\\revis\\art\\Git Hub Projects\\Local Reader Project\\LocalReader-Pro-v2.3\\dist/uninstall.exe', '.')],
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
