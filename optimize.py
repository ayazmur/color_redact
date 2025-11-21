import os
import shutil


def optimize_build():
    """Дополнительная оптимизация размера"""
    dist_dir = "dist"
    exe_path = os.path.join(dist_dir, "RedShapeEditor.exe")

    if not os.path.exists(exe_path):
        print("EXE файл не найден!")
        return

    # Размер до оптимизации
    original_size = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"Размер до оптимизации: {original_size:.1f} MB")

    # Используем UPX если установлен
    try:
        import subprocess
        # Сжимаем EXE
        subprocess.run(['upx', '--best', '--lzma', exe_path], check=True)

        # Размер после оптимизации
        optimized_size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"Размер после оптимизации: {optimized_size:.1f} MB")
        print(f"Сжатие: {((original_size - optimized_size) / original_size * 100):.1f}%")

    except Exception as e:
        print(f"UPX не доступен: {e}")


if __name__ == "__main__":
    optimize_build()