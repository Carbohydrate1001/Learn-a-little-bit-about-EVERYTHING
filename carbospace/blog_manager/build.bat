@echo off
chcp 65001 >nul
echo ============================================================
echo   CarboBlogManager - Build Script
echo ============================================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [!] PyInstaller not found. Installing...
    pip install pyinstaller
    echo.
)

echo [1/2] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo       Done.
echo.

echo [2/2] Building CarboBlogManager.exe ...
pyinstaller build.spec --clean --noconfirm
echo.

if exist dist\CarboBlogManager.exe (
    echo ============================================================
    echo   Build successful!
    echo   Output: dist\CarboBlogManager.exe
    echo.
    echo   Usage:
    echo     1. Copy CarboBlogManager.exe to your carbospace/ folder
    echo     2. Double-click to run
    echo     3. Or: CarboBlogManager.exe --project-dir "path\to\carbospace"
    echo ============================================================
) else (
    echo ============================================================
    echo   Build FAILED. Check the output above for errors.
    echo ============================================================
)

echo.
pause
