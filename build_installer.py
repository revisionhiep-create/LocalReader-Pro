"""
Build script for LocalReader Pro v1.9 installer
Compiles both setup.exe and uninstall.exe using PyInstaller
"""

import subprocess
import shutil
from pathlib import Path
import os


def clean_build_artifacts():
    """Remove old build artifacts"""
    print("[CLEAN] Removing old build artifacts...")
    artifacts = ['build', 'dist/setup.exe', 'dist/uninstall.exe', 'setup.spec', 'uninstaller.spec']
    for item in artifacts:
        path = Path(item)
        if path.is_dir():
            shutil.rmtree(path)
            print(f"  [REMOVED] {item}/")
        elif path.is_file():
            path.unlink()
            print(f"  [REMOVED] {item}")
    print("[OK] Clean complete\n")


def build_uninstaller():
    """Build uninstall.exe first"""
    print("[BUILD] Building uninstaller...")
    cmd = [
        'pyinstaller',
        '--onefile',
        '--noconsole',
        '--name=uninstall',
        '--uac-admin',
        'dist/uninstaller.py'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("[ERROR] Uninstaller build failed:")
        print(result.stderr)
        return False
    
    # Move uninstall.exe to dist/
    uninstall_src = Path('dist/uninstall.exe')
    uninstall_dst = Path('dist/uninstall.exe')
    
    if uninstall_src.exists() and uninstall_src != uninstall_dst:
        shutil.move(str(uninstall_src), str(uninstall_dst))
    
    print("[OK] Uninstaller built successfully\n")
    return True


def build_installer():
    """Build setup.exe with bundled app files"""
    print("[BUILD] Building installer...")
    
    # Paths
    project_root = Path.cwd()
    dist_dir = project_root / 'dist'
    
    # Build PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',
        '--noconsole',
        '--name=setup',
        '--uac-admin',
        f'--add-data={dist_dir}/requirements.txt;.',
        f'--add-data={dist_dir}/launch.vbs;.',
        f'--add-data={dist_dir}/main.py;.',
        f'--add-data={dist_dir}/uninstaller.py;.',
        f'--add-data={dist_dir}/app;app',
        f'--add-data={dist_dir}/uninstall.exe;.',
        '--exclude-module=numpy',
        '--exclude-module=pandas',
        '--exclude-module=torch',
        '--exclude-module=PIL',
        '--exclude-module=cv2',
        '--exclude-module=matplotlib',
        '--exclude-module=scipy',
        '--exclude-module=sklearn',
        '--exclude-module=tensorflow',
        'installer_logic.py'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("[ERROR] Installer build failed:")
        print(result.stderr)
        return False
    
    print("[OK] Installer built successfully\n")
    return True


def verify_output():
    """Verify that output files exist"""
    print("[VERIFY] Checking output files...")
    
    setup_exe = Path('dist/setup.exe')
    uninstall_exe = Path('dist/uninstall.exe')
    
    if not setup_exe.exists():
        print("[ERROR] setup.exe not found!")
        return False
    
    if not uninstall_exe.exists():
        print("[ERROR] uninstall.exe not found!")
        return False
    
    setup_size = setup_exe.stat().st_size / (1024 * 1024)
    uninstall_size = uninstall_exe.stat().st_size / (1024 * 1024)
    
    print(f"[OK] setup.exe: {setup_size:.1f} MB")
    print(f"[OK] uninstall.exe: {uninstall_size:.1f} MB")
    print("\n[SUCCESS] Build complete!\n")
    return True


def create_shortcuts():
    """Create shortcut files for easy access"""
    print("[SHORTCUTS] Creating shortcut files...")
    
    # Create Install shortcut
    install_lnk_content = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = oWS.ExpandEnvironmentStrings("%CD%") & "\\Install LocalReader Pro.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = oWS.ExpandEnvironmentStrings("%CD%") & "\\dist\\setup.exe"
oLink.WindowStyle = 1
oLink.Save
"""
    
    # Create Uninstall shortcut placeholder (actual uninstaller will be in install directory)
    uninstall_lnk_content = """
Note: The uninstaller (uninstall.exe) will be available in the installation directory after setup.
"""
    
    print("[INFO] Shortcuts should be created manually or via Windows Explorer")
    print("[OK] Build script complete!\n")
    
    print("=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print("1. Test setup.exe in a clean environment")
    print("2. Verify all dependencies install correctly")
    print("3. Check that shortcuts work properly")
    print("4. Test uninstall.exe removes shortcuts")
    print("=" * 60)


def main():
    """Main build process"""
    print("\n" + "=" * 60)
    print("LocalReader Pro v1.9 - Build System")
    print("=" * 60 + "\n")
    
    # Step 1: Clean
    clean_build_artifacts()
    
    # Step 2: Build uninstaller first
    if not build_uninstaller():
        print("[FATAL] Uninstaller build failed, aborting.")
        return
    
    # Step 3: Build installer (includes uninstaller)
    if not build_installer():
        print("[FATAL] Installer build failed.")
        return
    
    # Step 4: Verify
    if not verify_output():
        print("[FATAL] Output verification failed.")
        return
    
    # Step 5: Info
    create_shortcuts()


if __name__ == "__main__":
    main()

