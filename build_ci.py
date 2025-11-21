import os
import subprocess
import sys


def main():
    print("=== Сборка RedShapeEditor в GitHub Actions ===")

    # Показываем структуру директории
    print("Текущая директория:", os.getcwd())
    print("Содержимое директории:")
    for item in os.listdir('.'):
        if os.path.isdir(item):
            print(f"  📁 {item}/")
            try:
                for subitem in os.listdir(item):
                    print(f"    📄 {subitem}")
            except:
                pass
        else:
            print(f"  📄 {item}")

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

    print("Выполняется сборка...")
    print("Команда:", ' '.join(cmd))

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        print("✓ Сборка успешно завершена!")

        # Проверяем созданный файл
        exe_path = "dist/RedShapeEditor.exe"
        if os.path.exists(exe_path):
            size = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"✓ EXE файл создан: {exe_path}")
            print(f"✓ Размер: {size:.1f} MB")

            # Дополнительная оптимизация UPX
            try:
                print("Оптимизация UPX...")
                subprocess.run(['upx', '--best', '--lzma', exe_path], check=True)
                optimized_size = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"✓ Оптимизированный размер: {optimized_size:.1f} MB")
            except Exception as e:
                print(f"⚠ UPX не доступен: {e}")

        else:
            print("✗ EXE файл не найден!")
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print("✗ Ошибка сборки!")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()