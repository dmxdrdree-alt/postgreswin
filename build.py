#!/usr/bin/env python
"""
Build script for PostgreSQL Backup Manager
Compiles the application to a standalone .exe file using PyInstaller
"""

import os
import sys
import subprocess
from pathlib import Path


def build_executable():
    """Build the application executable using PyInstaller"""
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Define the spec file content for building a single file executable
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include any additional data files if needed
    ],
    hiddenimports=[],
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PostgreSQL_Backup_Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add path to icon file if desired
)
'''
    
    # Write the spec file
    with open('PostgreSQL_Backup_Manager.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("Building executable...")
    
    # Run PyInstaller with the spec file
    result = subprocess.run([
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        'PostgreSQL_Backup_Manager.spec'
    ], check=True, capture_output=False)
    
    if result.returncode == 0:
        print("Build completed successfully!")
        print(f"Executable located at: {Path.cwd()}/dist/PostgreSQL_Backup_Manager.exe")
    else:
        print("Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    build_executable()