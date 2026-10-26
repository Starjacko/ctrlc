@echo off
setlocal
cd /d "%~dp0"

python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

python make_icon.py
if errorlevel 1 exit /b 1

python -m PyInstaller --noconfirm --clean ^
  --windowed ^
  --onefile ^
  --name "粘贴历史" ^
  --icon icon.ico ^
  --add-data "icon.ico;." ^
  --hidden-import pystray._win32 ^
  --hidden-import PIL._tkinter_finder ^
  main.py

if errorlevel 1 exit /b 1

echo.
echo Built: dist\粘贴历史.exe
echo Close this window and double-click the exe to run in the background.
endlocal
