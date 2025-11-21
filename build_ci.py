# -*- coding: utf-8 -*-
import os
import subprocess
import sys


def main():
    # Устанавливаем UTF-8 кодировку для вывода
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    print("=== Building RedShapeEditor in GitHub Actions ===")

    # Показываем структуру директории
    print("Current directory:", os.getcwd())
    print("Directory contents:")
    for item in os.listdir('.'):
        if os.path.isdir(item):
            print(f"  [DIR] {item}/")
            try:
                for subitem in os.listdir(item):
                    print(f"    [FILE] {subitem}")
            except:
                pass
        else:
            print(f"  [FILE] {item}")

    # Команда PyInstaller для Windows
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

    print("Building...")
    print("Command:", ' '.join(cmd))

    try:
        # Запускаем с указанием кодировки
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        print("SUCCESS: Build completed!")

        # Проверяем созданный файл
        exe_path = "dist/RedShapeEditor.exe"
        if os.path.exists(exe_path):
            size = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"SUCCESS: EXE file created: {exe_path}")
            print(f"SUCCESS: Size: {size:.1f} MB")

            # Дополнительная оптимизация UPX
            try:
                print("UPX optimization...")
                subprocess.run(['upx', '--best', '--lzma', exe_path], check=True)
                optimized_size = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"SUCCESS: Optimized size: {optimized_size:.1f} MB")
            except Exception as e:
                print(f"INFO: UPX not available: {e}")

        else:
            print("ERROR: EXE file not found!")
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print("ERROR: Build failed!")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()