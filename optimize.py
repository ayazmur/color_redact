import os
import subprocess
import sys


def optimize_build():
    """Additional EXE size optimization"""
    dist_dir = "dist"
    exe_path = os.path.join(dist_dir, "RedShapeEditor.exe")

    if not os.path.exists(exe_path):
        print("ERROR: EXE file not found!")
        return False

    # Size before optimization
    original_size = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"Size before optimization: {original_size:.1f} MB")

    # Try to use UPX for compression
    try:
        print("Applying UPX compression...")
        result = subprocess.run([
            'upx', '--best', '--lzma', exe_path
        ], capture_output=True, text=True, check=True)

        # Size after optimization
        optimized_size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"SUCCESS: Size after optimization: {optimized_size:.1f} MB")
        print(f"SUCCESS: Compression: {((original_size - optimized_size) / original_size * 100):.1f}%")
        return True

    except subprocess.CalledProcessError as e:
        print(f"INFO: UPX error: {e}")
        return False
    except FileNotFoundError:
        print("INFO: UPX not installed, skipping compression")
        return True
    except Exception as e:
        print(f"INFO: Optimization error: {e}")
        return True


if __name__ == "__main__":
    print("=== EXE Optimization ===")
    success = optimize_build()
    sys.exit(0 if success else 1)