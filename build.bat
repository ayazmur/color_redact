@echo off
chcp 65001
echo ========================================
echo    Сборка RedShapeEditor
echo ========================================

echo Установка зависимостей...
pip install -r requirements.txt

echo Очистка предыдущих сборок...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Сборка EXE...
pyinstaller --name=RedShapeEditor --windowed --onefile --clean --noconfirm --add-data="core;core" --add-data="ui;ui" --add-data="utils;utils" --hidden-import=docx.oxml --hidden-import=docx.opc.constants --hidden-import=docx.image --hidden-import=docx.oxml.shape --hidden-import=docx.oxml.ns --hidden-import=docx.opc.phys_pkg --hidden-import=PIL._imaging --hidden-import=cv2 --hidden-import=lxml.etree --hidden-import=lxml._elementpath --exclude-module=tkinter --exclude-module=matplotlib --exclude-module=scipy main.py

if %errorlevel% neq 0 (
    echo.
    echo ✗ Ошибка сборки!
    pause
    exit /b %errorlevel%
)

echo.
echo ✓ Сборка завершена!
echo EXE файл: dist\RedShapeEditor.exe
dir dist\RedShapeEditor.exe

echo.
echo Дополнительная оптимизация...
python optimize.py

echo.
echo ========================================
echo    СБОРКА УСПЕШНО ЗАВЕРШЕНА!
echo ========================================
pause