@echo off
chcp 65001
echo Установка зависимостей...
pip install PyQt5 opencv-python python-docx Pillow lxml numpy pyinstaller

echo Очистка предыдущих сборок...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Сборка оптимизированного EXE...
pyinstaller build.spec --clean --noconfirm

echo.
echo === СБОРКА ЗАВЕРШЕНА ===
echo EXE файл: dist\RedShapeEditor.exe
dir dist\RedShapeEditor.exe

pause