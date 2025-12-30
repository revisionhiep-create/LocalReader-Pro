"""
LocalReader Pro - Uninstaller
Removes shortcuts and optionally the application folder.
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import shutil


def is_admin():
    """Check if running with admin privileges"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def remove_shortcuts():
    """Remove Desktop and Start Menu shortcuts"""
    removed = []
    failed = []
    
    # Desktop shortcut
    desktop = Path.home() / "Desktop" / "LocalReader Pro.lnk"
    if desktop.exists():
        try:
            desktop.unlink()
            removed.append(str(desktop))
        except Exception as e:
            failed.append(f"Desktop shortcut: {e}")
    
    # Start Menu shortcut
    start_menu = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "LocalReader Pro.lnk"
    if start_menu.exists():
        try:
            start_menu.unlink()
            removed.append(str(start_menu))
        except Exception as e:
            failed.append(f"Start Menu shortcut: {e}")
    
    return removed, failed


def main():
    # Create hidden root window
    root = tk.Tk()
    root.withdraw()
    
    # Check admin
    if not is_admin():
        messagebox.showerror(
            "Admin Required",
            "This uninstaller requires administrator privileges.\nPlease run as administrator."
        )
        sys.exit(1)
    
    # Confirmation dialog
    result = messagebox.askyesno(
        "Uninstall LocalReader Pro",
        "This will remove LocalReader Pro shortcuts from your system.\n\n"
        "The application files will remain in the installation folder.\n"
        "You can manually delete the folder if desired.\n\n"
        "Continue with uninstall?"
    )
    
    if not result:
        sys.exit(0)
    
    # Remove shortcuts
    removed, failed = remove_shortcuts()
    
    # Build result message
    if removed:
        message = "Uninstall complete!\n\nRemoved shortcuts:\n"
        for item in removed:
            message += f"  - {Path(item).name}\n"
    else:
        message = "No shortcuts found to remove.\n"
    
    if failed:
        message += "\n\nErrors:\n"
        for error in failed:
            message += f"  - {error}\n"
    
    # Get install directory
    install_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path.cwd()
    
    message += f"\n\nApplication files remain at:\n{install_dir}"
    message += "\n\nYou can manually delete this folder if you want to completely remove LocalReader Pro."
    
    messagebox.showinfo("Uninstall Complete", message)


if __name__ == "__main__":
    main()

