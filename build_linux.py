#!/usr/bin/env python3
"""
Linux Build Script for PrismDesktop.

Builds a standalone AppImage that works on the host architecture.
Auto-detects x86_64 or aarch64 (Raspberry Pi) and produces the correct output.

Requirements:
    1. Python 3 with PyInstaller (auto-installed if missing)
    2. appimagetool in PATH or in this directory
       Download from: https://github.com/AppImage/appimagetool/releases
       - x86_64 PCs:  appimagetool-x86_64.AppImage
       - Raspberry Pi: appimagetool-aarch64.AppImage

Usage:
    python3 build_linux.py
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path


def get_arch():
    """Detect host architecture and return normalized name."""
    machine = platform.machine().lower()
    if machine in ('x86_64', 'amd64'):
        return 'x86_64'
    elif machine in ('aarch64', 'arm64'):
        return 'aarch64'
    else:
        print(f"Warning: Unrecognized architecture '{machine}', proceeding as '{machine}'.")
        return machine


def find_appimagetool(arch):
    """Find appimagetool in PATH or current directory."""
    # 1. Check PATH
    path_tool = shutil.which('appimagetool')
    if path_tool:
        return path_tool

    # 2. Check current directory for common filenames
    base_dir = Path(__file__).parent.absolute()
    candidates = [
        'appimagetool',
        f'appimagetool-{arch}.AppImage',
        'appimagetool.AppImage',
    ]

    for name in candidates:
        local_path = base_dir / name
        if local_path.exists():
            # Ensure executable
            try:
                current_mode = os.stat(local_path).st_mode
                os.chmod(local_path, current_mode | 0o111)
            except Exception as e:
                print(f"Warning: Could not make {name} executable: {e}")
            return str(local_path)

    return None


def build_binary(base_dir):
    """Build the standalone binary using PyInstaller."""
    # Ensure PyInstaller is installed
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)

    pyinstaller_args = [
        sys.executable, '-m', 'PyInstaller',
        'main.py',
        '--name=PrismDesktop',
        '--onefile',
        '--windowed',
        '--add-data=materialdesignicons-webfont.ttf:.',
        '--add-data=mdi_mapping.json:.',
        '--add-data=icon.png:.',
        '--icon=icon.png',
        '--clean',
    ]

    print(f"Command: {' '.join(pyinstaller_args)}")
    result = subprocess.run(pyinstaller_args, cwd=str(base_dir))

    if result.returncode != 0:
        print("\n❌ PyInstaller build failed!")
        sys.exit(1)

    binary = base_dir / 'dist' / 'PrismDesktop'
    if not binary.exists():
        print("Error: Binary not found at dist/PrismDesktop")
        sys.exit(1)

    return binary


def package_appimage(base_dir, binary_path, arch, appimagetool):
    """Package the binary into an AppImage."""
    app_dir = base_dir / 'AppDir'

    # Clean previous AppDir
    if app_dir.exists():
        shutil.rmtree(app_dir)

    # Create directory structure
    (app_dir / 'usr' / 'bin').mkdir(parents=True)
    (app_dir / 'usr' / 'share' / 'icons' / 'hicolor' / '256x256' / 'apps').mkdir(parents=True)

    # Copy binary
    shutil.copy2(binary_path, app_dir / 'usr' / 'bin' / 'PrismDesktop')

    # Copy icon
    icon_src = base_dir / 'icon.png'
    if icon_src.exists():
        shutil.copy2(icon_src, app_dir / 'usr' / 'share' / 'icons' / 'hicolor' / '256x256' / 'apps' / 'prism-desktop.png')
        shutil.copy2(icon_src, app_dir / 'prism-desktop.png')
    else:
        print("Warning: icon.png not found.")

    # Create AppRun symlink
    (app_dir / 'AppRun').symlink_to('usr/bin/PrismDesktop')

    # Create .desktop file
    desktop_content = """[Desktop Entry]
Type=Application
Name=PrismDesktop
Comment=Home Assistant Tray Application
Exec=PrismDesktop
Icon=prism-desktop
Categories=Utility;
Terminal=false
"""
    (app_dir / 'PrismDesktop.desktop').write_text(desktop_content)

    # Set ARCH env var for appimagetool
    env = os.environ.copy()
    env['ARCH'] = arch

    # Run appimagetool
    try:
        subprocess.run([appimagetool, str(app_dir)], cwd=str(base_dir), env=env, check=True)
    except subprocess.CalledProcessError:
        print("\n❌ AppImage packaging failed!")
        sys.exit(1)

    # Find and rename the output
    # appimagetool outputs: PrismDesktop-<arch>.AppImage
    expected_output = base_dir / f'PrismDesktop-{arch}.AppImage'
    if expected_output.exists():
        print(f"\n✅ Build complete: {expected_output.name}")
    else:
        # Might have a different default name, find it
        for f in base_dir.glob('PrismDesktop*.AppImage'):
            print(f"\n✅ Build complete: {f.name}")
            break

    # Clean up AppDir
    if app_dir.exists():
        shutil.rmtree(app_dir)


def main():
    if sys.platform != 'linux':
        print("Error: This script must be run on Linux.")
        sys.exit(1)

    arch = get_arch()
    base_dir = Path(__file__).parent.absolute()

    print(f"╔══════════════════════════════════════════╗")
    print(f"║   PrismDesktop Linux Build               ║")
    print(f"║   Architecture: {arch:<25s}║")
    print(f"╚══════════════════════════════════════════╝")

    # Check for appimagetool
    appimagetool = find_appimagetool(arch)
    if not appimagetool:
        print(f"\nError: 'appimagetool' not found.")
        print(f"Download 'appimagetool-{arch}.AppImage' from:")
        print(f"  https://github.com/AppImage/appimagetool/releases")
        print(f"Place it in this directory or add it to your PATH.")
        sys.exit(1)

    print(f"Using appimagetool: {appimagetool}")

    # Step 1: Build binary
    print(f"\n[1/2] Building binary with PyInstaller...")
    binary = build_binary(base_dir)

    # Step 2: Package AppImage
    print(f"\n[2/2] Packaging AppImage for {arch}...")
    package_appimage(base_dir, binary, arch, appimagetool)

    print(f"\nDone! Distribute the .AppImage file to {arch} users.")


if __name__ == '__main__':
    main()
