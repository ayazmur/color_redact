@echo off
chcp 65001
echo ========================================
echo    Red Shape Editor - Build System
echo ========================================

echo Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found! Please install Python 3.9+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Checking pip...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: pip not found! Please install pip
    pause
    exit /b 1
)

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Building EXE...
python build_ci.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b %errorlevel%
)

echo.
echo SUCCESS: Build completed!
echo EXE file: dist\RedShapeEditor.exe
dir dist\RedShapeEditor.exe

echo.
echo ========================================
echo    BUILD SUCCESSFUL!
echo ========================================
echo Program is ready in: dist\RedShapeEditor.exe
echo You can now run the program!
pause