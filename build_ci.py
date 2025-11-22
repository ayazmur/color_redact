# -*- coding: utf-8 -*-
import os
import subprocess
import sys


def main():
    # Устанавливаем UTF-8 кодировку
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

    print("=== Building Release Version ===")

    # Определяем что это релизная сборка
    is_release = os.environ.get('GITHUB_REF', '') == 'refs/heads/release' or 'release' in os.environ.get(
        'GITHUB_EVENT_NAME', '')
    print(f"Release build: {is_release}")

    # Команда PyInstaller с оптимизацией для релиза
    cmd = [
        'pyinstaller',
        '--name=RedShapeEditor',
        '--windowed',
        '--onefile',
        '--clean',
        '--noconfirm',
        '--add-data=core;core',
        '--add-data=ui;ui',
        '--add-data=utils;utils',
        '--hidden-import=docx.oxml',
        '--hidden-import=docx.opc.constants',
        '--hidden-import=docx.image',
        '--hidden-import=docx.oxml.shape',
        '--hidden-import=docx.oxml.ns',
        '--hidden-import=docx.opc.phys_pkg',
        '--hidden-import=PIL._imaging',
        '--hidden-import=cv2',
        '--hidden-import=lxml.etree',
        '--hidden-import=lxml._elementpath',
        '--exclude-module=tkinter',
        '--exclude-module=matplotlib',
        '--exclude-module=scipy',
        'main.py'
    ]

    print("Building release EXE...")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        print("SUCCESS: Release build completed!")

        # Проверяем созданный файл
        exe_path = "dist/RedShapeEditor.exe"
        if os.path.exists(exe_path):
            size = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"SUCCESS: EXE file created: {exe_path}")
            print(f"SUCCESS: Size: {size:.1f} MB")

            # Обязательная UPX оптимизация для релиза
            try:
                print("Applying UPX compression for release...")
                subprocess.run(['upx', '--best', '--lzma', exe_path], check=True)
                optimized_size = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"SUCCESS: Optimized release size: {optimized_size:.1f} MB")
            except Exception as e:
                print(f"WARNING: UPX not available: {e}")

        else:
            print("ERROR: EXE file not found!")
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print("ERROR: Release build failed!")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()