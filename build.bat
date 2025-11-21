@echo off
chcp 65001
echo Установка зависимостей...
pip install -r requirements.txt
pip install pyinstaller

echo Очистка предыдущих сборок...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Сборка оптимизированного EXE...
pyinstaller build.spec --clean --noconfirm

echo.
echo === СБОРКА ЗАВЕРШЕНА ===
echo EXE файл: dist\RedShapeEditor.exe
dir dist\RedShapeEditor.exe

echo.
echo Дополнительная оптимизация...
python optimize.py

pause