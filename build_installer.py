"""
Build script for LocalReader Pro v2.2 installer
Compiles both setup.exe and uninstall.exe using PyInstaller
"""

import subprocess
import shutil
from pathlib import Path
import os


def clean_build_artifacts():
    """Remove old build artifacts"""
    print("[CLEAN] Removing old build artifacts...")
    artifacts = [
        "build",
        "dist/setup.exe",
        "dist/uninstall.exe",
        "setup.spec",
        "uninstaller.spec",
    ]
    for item in artifacts:
        path = Path(item)
        if path.is_dir():
            try:
                shutil.rmtree(path)
                print(f"  [REMOVED] {item}/")
            except Exception as e:
                print(f"  [Partial] Could not remove {item}: {e}")
        elif path.is_file():
            try:
                path.unlink()
                print(f"  [REMOVED] {item}")
            except Exception as e:
                print(f"  [Partial] Could not remove {item}: {e}")
    print("[OK] Clean complete\n")


def build_uninstaller():
    """Build uninstall.exe first"""
    print("[BUILD] Building uninstaller...")
    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        "--name=uninstall",
        "--uac-admin",
        "dist/uninstaller.py",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("[ERROR] Uninstaller build failed:")
        print(result.stderr)
        return False

    # Move uninstall.exe to dist/
    uninstall_src = Path("dist/uninstall.exe")
    uninstall_dst = Path("dist/uninstall.exe")

    # If pyinstaller output to ./dist/uninstall.exe (default), we are good.
    # But usually it outputs to ./dist/ (relative to script).
    # Since we are running from project root, pyinstaller creates ./dist/uninstall.exe

    print("[OK] Uninstaller built successfully\n")
    return True


def get_app_data_args(dist_dir):
    """Dynamically generate --add-data args for the app directory"""
    app_dir = dist_dir / "app"
    add_data = []

    print(f"[SCAN] Scanning {app_dir} for inclusions...")

    # Items to explicitly EXCLUDE
    exclude_dirs = {
        "models",
        "userdata",
        "__pycache__",
        ".git",
        ".vscode",
        "node_modules",
    }
    exclude_extensions = {".pyc", ".tmp", ".log"}

    # 1. Add app root files (server.py, state.py, etc.)
    for file in app_dir.glob("*"):
        if file.is_file():
            if file.suffix in exclude_extensions:
                continue
            add_data.append(f"--add-data={file};app")
            print(f"  + File: app/{file.name}")

    # 2. Add subdirectories recursively, avoiding excluded ones
    for item in app_dir.iterdir():
        if item.is_dir():
            if item.name in exclude_dirs:
                print(f"  - Skipped: app/{item.name}/ (EXCLUDED)")
                continue

            # For valid directories (ui, locales, logic, routers), include them
            # We can just add the folder root: --add-data=path/to/folder;target/folder
            add_data.append(f"--add-data={item};app/{item.name}")
            print(f"  + Dir:  app/{item.name}/")

    return add_data


def build_installer():
    """Build setup.exe with bundled app files"""
    print("[BUILD] Building installer...")

    # Paths
    project_root = Path.cwd()
    dist_dir = project_root / "dist"

    # Base inclusions
    add_data_args = [
        f"--add-data={dist_dir}/requirements.txt;.",
        f"--add-data={dist_dir}/launch.vbs;.",
        f"--add-data={dist_dir}/main.py;.",
        f"--add-data={dist_dir}/uninstaller.py;.",
        f"--add-data={dist_dir}/uninstall.exe;.",
    ]

    # Dynamic app inclusions
    add_data_args.extend(get_app_data_args(dist_dir))

    # Build PyInstaller command
    cmd = (
        [
            "pyinstaller",
            "--onefile",
            "--noconsole",
            "--name=setup",
            "--uac-admin",
        ]
        + add_data_args
        + [
            "--exclude-module=numpy",
            "--exclude-module=pandas",
            "--exclude-module=torch",
            "--exclude-module=PIL",
            "--exclude-module=cv2",
            "--exclude-module=matplotlib",
            "--exclude-module=scipy",
            "--exclude-module=sklearn",
            "--exclude-module=tensorflow",
            "installer_logic.py",
        ]
    )

    print(f"[CMD] Running PyInstaller with {len(add_data_args)} data rules...")
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

    setup_exe = Path("dist/setup.exe")

    if not setup_exe.exists():
        print("[ERROR] setup.exe not found!")
        return False

    setup_size = setup_exe.stat().st_size / (1024 * 1024)
    print(f"[OK] setup.exe: {setup_size:.1f} MB")

    if setup_size > 100:
        print(
            "[WARNING] Setup size is unusually large. Did we include models randomly?"
        )

    print("\n[SUCCESS] Build complete!\n")
    return True


def create_shortcuts():
    """Create shortcut files for easy access"""
    print("[SHORTCUTS] Creating shortcut files...")

    install_lnk_content = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = oWS.ExpandEnvironmentStrings("%CD%") & "\\Install LocalReader Pro.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = oWS.ExpandEnvironmentStrings("%CD%") & "\\dist\\setup.exe"
oLink.WindowStyle = 1
oLink.Save
"""
    # Create temp vbs to make shortcut? No, usually users just run setup.
    print("[INFO] Run 'dist/setup.exe' to install.")


def main():
    """Main build process"""
    print("\n" + "=" * 60)
    print("LocalReader Pro v2.3 - Build System")
    print("=" * 60 + "\n")

    clean_build_artifacts()

    if not build_uninstaller():
        print("[FATAL] Uninstaller build failed, aborting.")
        return

    if not build_installer():
        print("[FATAL] Installer build failed.")
        return

    if not verify_output():
        print("[FATAL] Output verification failed.")
        return

    create_shortcuts()


if __name__ == "__main__":
    main()
