
@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment .venv not found.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name "ChadCivilRegistry" ^
  --onedir ^
  --add-data "app\templates;app\templates" ^
  --add-data "app\static;app\static" ^
  --collect-all webview ^
  --collect-all flask ^
  --collect-all flask_sqlalchemy ^
  --collect-all flask_login ^
  --collect-all flask_migrate ^
  --collect-all flask_bcrypt ^
  --collect-all flask_mail ^
  desktop.py

if errorlevel 1 (
    echo BUILD FAILED.
    pause
    exit /b 1
)

echo.
echo BUILD COMPLETE.
echo Executable: dist\ChadCivilRegistry\ChadCivilRegistry.exe
pause
