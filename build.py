import os
import subprocess
import sys


def build_exe():
    # Проверяем установлен ли PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("Установка PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Команда сборки
    cmd = [
        'pyinstaller',
        '--name=RedShapeEditor',
        '--windowed',  # Без консоли
        '--onefile',  # Один EXE файл
        '--add-data=core;core',
        '--add-data=ui;ui',
        '--add-data=utils;utils',
        '--hidden-import=docx',
        '--hidden-import=docx.oxml',
        '--hidden-import=docx.opc.constants',
        '--hidden-import=docx.compat',
        '--hidden-import=docx.image',
        '--hidden-import=docx.oxml.shape',
        '--hidden-import=docx.oxml.ns',
        '--hidden-import=docx.opc.phys_pkg',
        '--hidden-import=PIL._imaging',
        '--hidden-import=cv2',
        '--hidden-import=lxml.etree',
        '--hidden-import=lxml._elementpath',
        '--clean',
        'main.py'
    ]

    print("Сборка EXE...")
    subprocess.check_call(cmd)
    print("Готово! EXE файл: dist/RedShapeEditor.exe")


if __name__ == "__main__":
    build_exe()