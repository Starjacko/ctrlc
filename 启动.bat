@echo off
cd /d "%~dp0"
if exist "dist\粘贴历史.exe" (
  start "" "dist\粘贴历史.exe"
  exit /b 0
)
if exist "粘贴历史.exe" (
  start "" "粘贴历史.exe"
  exit /b 0
)
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw main.py
) else (
  python main.py
)
