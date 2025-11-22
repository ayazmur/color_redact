import os
import subprocess
import sys


def main():
    print("Building RedShapeEditor Release...")

    # Команда PyInstaller
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
        'main.py'
    ]

    print("Running build command...")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build successful!")

        # Проверяем созданный файл
        exe_path = "dist/RedShapeEditor.exe"
        if os.path.exists(exe_path):
            size = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"✅ EXE created: {exe_path}")
            print(f"✅ Size: {size:.1f} MB")

            # Оптимизация UPX
            try:
                print("Optimizing with UPX...")
                subprocess.run(['upx', '--best', '--lzma', exe_path], check=True)
                optimized_size = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"✅ Optimized size: {optimized_size:.1f} MB")
            except Exception as e:
                print(f"ℹ️ UPX not available: {e}")

        else:
            print("❌ EXE file not found!")
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print("❌ Build failed!")
        print("Error output:", e.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()