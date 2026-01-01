"""
LocalReader Pro v2.3 - Self-Contained Installer
Installs Python (if needed), dependencies, and creates shortcuts.
Installs in the CURRENT directory (where setup.exe is located).
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import subprocess
import urllib.request
import tempfile


def is_admin():
    """Check if running with admin privileges"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def check_python():
    """Check if Python 3.12+ is installed"""
    try:
        result = subprocess.run(
            ['python', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version_str = result.stdout.strip().split()[1]
            major, minor = map(int, version_str.split('.')[:2])
            if major == 3 and minor >= 12:
                return True, version_str
        return False, None
    except:
        return False, None


def download_python(progress_callback=None):
    """Download Python 3.12 installer"""
    url = "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe"
    temp_dir = tempfile.gettempdir()
    installer_path = os.path.join(temp_dir, "python_installer.exe")
    
    if progress_callback:
        progress_callback("Downloading Python 3.12...")
    
    try:
        urllib.request.urlretrieve(url, installer_path)
        return installer_path
    except Exception as e:
        raise Exception(f"Failed to download Python: {e}")


def install_python(installer_path, progress_callback=None):
    """Install Python silently"""
    if progress_callback:
        progress_callback("Installing Python 3.12...")
    
    try:
        subprocess.run(
            [installer_path, '/quiet', 'InstallAllUsers=1', 'PrependPath=1'],
            check=True,
            timeout=600
        )
        return True
    except Exception as e:
        raise Exception(f"Failed to install Python: {e}")


def install_dependencies(install_dir, progress_callback=None):
    """Install Python dependencies in current directory"""
    if progress_callback:
        progress_callback("Installing dependencies... (This may take 5-10 minutes)")
    
    requirements = Path(install_dir) / 'requirements.txt'
    if not requirements.exists():
        raise Exception("requirements.txt not found in current directory")
    
    try:
        subprocess.run(
            ['python', '-m', 'pip', 'install', '-r', str(requirements)],
            check=True,
            timeout=1200,
            cwd=install_dir
        )
        return True
    except Exception as e:
        raise Exception(f"Failed to install dependencies: {e}")


def create_shortcuts(install_dir, progress_callback=None):
    """Create Desktop and Start Menu shortcuts"""
    if progress_callback:
        progress_callback("Creating shortcuts...")
    
    launch_vbs = Path(install_dir) / 'launch.vbs'
    if not launch_vbs.exists():
        raise Exception("launch.vbs not found in current directory")
    
    try:
        # Use PowerShell to create shortcuts
        create_shortcuts_powershell(install_dir, launch_vbs)
        return True
    except Exception as e:
        raise Exception(f"Failed to create shortcuts: {e}")


def create_shortcuts_powershell(install_dir, launch_vbs):
    """Create shortcuts using PowerShell"""
    # Desktop shortcut
    ps_script = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{Path.home() / 'Desktop' / 'LocalReader Pro.lnk'}")
$Shortcut.TargetPath = "{launch_vbs}"
$Shortcut.WorkingDirectory = "{install_dir}"
$Shortcut.IconLocation = "C:\\Windows\\System32\\shell32.dll,13"
$Shortcut.Save()
'''
    subprocess.run(['powershell', '-Command', ps_script], check=True, timeout=10)
    
    # Start Menu shortcut
    start_menu = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    ps_script = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{start_menu / 'LocalReader Pro.lnk'}")
$Shortcut.TargetPath = "{launch_vbs}"
$Shortcut.WorkingDirectory = "{install_dir}"
$Shortcut.IconLocation = "C:\\Windows\\System32\\shell32.dll,13"
$Shortcut.Save()
'''
    subprocess.run(['powershell', '-Command', ps_script], check=True, timeout=10)


class InstallerGUI:
    def __init__(self, install_dir):
        self.install_dir = install_dir
        
        self.root = tk.Tk()
        self.root.title("LocalReader Pro v2.3 - Setup")
        self.root.geometry("500x250")
        self.root.resizable(False, False)
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.root.winfo_screenheight() // 2) - (250 // 2)
        self.root.geometry(f"500x250+{x}+{y}")
        
        # UI Components
        tk.Label(self.root, text="LocalReader Pro v2.3", font=("Arial", 14, "bold")).pack(pady=10)
        
        self.status_label = tk.Label(self.root, text="Ready to install", font=("Arial", 10))
        self.status_label.pack(pady=10)
        
        self.progress = ttk.Progressbar(self.root, mode='indeterminate', length=400)
        self.progress.pack(pady=10)
        
        self.log_text = tk.Text(self.root, height=6, width=60, state='disabled', font=("Consolas", 8))
        self.log_text.pack(pady=10)
        
        # Auto-start installation after showing window
        self.root.after(500, self.start_installation)
        
    def log(self, message):
        """Add message to log"""
        self.log_text.config(state='normal')
        self.log_text.insert('end', message + '\n')
        self.log_text.see('end')
        self.log_text.config(state='disabled')
        self.root.update()
        
    def update_status(self, message):
        """Update status label"""
        self.status_label.config(text=message)
        self.root.update()
        
    def start_installation(self):
        """Run installation process"""
        # Check admin
        if not is_admin():
            messagebox.showerror(
                "Admin Required",
                "This installer requires administrator privileges.\nPlease run as administrator."
            )
            self.root.destroy()
            sys.exit(1)
        
        # Start progress
        self.progress.start()
        
        try:
            # Step 1: Check Python
            self.update_status("Checking Python installation...")
            self.log("[1/4] Checking Python...")
            has_python, version = check_python()
            
            if has_python:
                self.log(f"[OK] Python {version} detected")
            else:
                self.log("[INFO] Python 3.12+ not found, downloading...")
                installer_path = download_python(self.update_status)
                self.log("[OK] Downloaded Python installer")
                
                self.log("[INFO] Installing Python 3.12...")
                install_python(installer_path, self.update_status)
                self.log("[OK] Python installed successfully")
            
            # Step 2: Install dependencies
            self.update_status("Installing dependencies (this may take 5-10 minutes)...")
            self.log("[2/4] Installing dependencies...")
            install_dependencies(self.install_dir, self.update_status)
            self.log("[OK] Dependencies installed")
            
            # Step 3: Create shortcuts
            self.update_status("Creating shortcuts...")
            self.log("[3/4] Creating shortcuts...")
            create_shortcuts(self.install_dir, self.update_status)
            self.log("[OK] Shortcuts created")
            
            # Step 4: Complete
            self.update_status("Installation complete!")
            self.log("[4/4] Installation complete!")
            self.progress.stop()
            
            messagebox.showinfo(
                "Installation Complete",
                f"LocalReader Pro has been successfully installed!\n\n"
                f"Installation directory:\n{self.install_dir}\n\n"
                f"Shortcuts created:\n"
                f"  - Desktop: LocalReader Pro\n"
                f"  - Start Menu: LocalReader Pro\n\n"
                f"Click OK to close the installer."
            )
            
            self.root.destroy()
            
        except Exception as e:
            self.progress.stop()
            self.log(f"[ERROR] {e}")
            messagebox.showerror("Installation Failed", f"An error occurred:\n\n{e}")
            self.root.destroy()
            sys.exit(1)
    
    def run(self):
        """Start GUI"""
        self.root.mainloop()


def main():
    """Main entry point"""
    # Get the directory where setup.exe is located
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        install_dir = Path(sys.executable).parent.absolute()
    else:
        # Running as script (development)
        install_dir = Path(__file__).parent.absolute()
    
    # Ensure we're in the dist folder
    if install_dir.name != 'dist':
        # If setup.exe is run from root, look for dist/
        if (install_dir / 'dist').exists():
            install_dir = install_dir / 'dist'
    
    print(f"[INFO] Installing in: {install_dir}")
    
    app = InstallerGUI(str(install_dir))
    app.run()


if __name__ == "__main__":
    main()
