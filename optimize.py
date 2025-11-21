import os
import subprocess
import sys


def optimize_build():
    """Дополнительная оптимизация размера EXE"""
    dist_dir = "dist"
    exe_path = os.path.join(dist_dir, "RedShapeEditor.exe")

    if not os.path.exists(exe_path):
        print("✗ EXE файл не найден!")
        return False

    # Размер до оптимизации
    original_size = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"Размер до оптимизации: {original_size:.1f} MB")

    # Пытаемся использовать UPX для сжатия
    try:
        print("Сжатие UPX...")
        result = subprocess.run([
            'upx', '--best', '--lzma', exe_path
        ], capture_output=True, text=True, check=True)

        # Размер после оптимизации
        optimized_size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"✓ Размер после оптимизации: {optimized_size:.1f} MB")
        print(f"✓ Сжатие: {((original_size - optimized_size) / original_size * 100):.1f}%")
        return True

    except subprocess.CalledProcessError as e:
        print(f"⚠ UPX ошибка: {e}")
        return False
    except FileNotFoundError:
        print("ℹ UPX не установлен, пропускаем сжатие")
        return True
    except Exception as e:
        print(f"⚠ Ошибка оптимизации: {e}")
        return True


if __name__ == "__main__":
    print("=== Оптимизация EXE ===")
    success = optimize_build()
    sys.exit(0 if success else 1)