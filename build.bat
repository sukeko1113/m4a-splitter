@echo off
setlocal

REM ---------------------------------------------------------------------------
REM Build the m4a Splitter exe with PyInstaller.
REM Run download_ffmpeg.ps1 once first to populate bin\ffmpeg.exe / bin\ffprobe.exe.
REM ---------------------------------------------------------------------------

cd /d "%~dp0"

if not exist "bin\ffmpeg.exe" (
    echo [ERROR] bin\ffmpeg.exe not found.
    echo         Run: powershell -ExecutionPolicy Bypass -File download_ffmpeg.ps1
    exit /b 1
)
if not exist "bin\ffprobe.exe" (
    echo [ERROR] bin\ffprobe.exe not found.
    echo         Run: powershell -ExecutionPolicy Bypass -File download_ffmpeg.ps1
    exit /b 1
)

where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller not found. Install with: pip install -r requirements.txt
    exit /b 1
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist m4a-splitter.spec del /q m4a-splitter.spec

pyinstaller --onefile --windowed --name m4a-splitter ^
  --icon=assets\icon.ico ^
  --add-binary "bin\ffmpeg.exe;bin" ^
  --add-binary "bin\ffprobe.exe;bin" ^
  --add-data "licenses;licenses" ^
  src\m4a_splitter.py

if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    exit /b 1
)

echo.
echo [OK] Built dist\m4a-splitter.exe
endlocal
