@echo off
setlocal

REM ---------------------------------------------------------------------------
REM Build the exe via PyInstaller, then compile the Inno Setup installer.
REM ---------------------------------------------------------------------------

cd /d "%~dp0"

call build.bat
if errorlevel 1 (
    echo [ERROR] build.bat failed; aborting installer build.
    exit /b 1
)

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if not exist "%ISCC%" (
    echo.
    echo [ERROR] Inno Setup 6 ISCC.exe was not found.
    echo         Install Inno Setup 6 from https://jrsoftware.org/isdl.php
    echo         and re-run this script.
    exit /b 1
)

"%ISCC%" "installer\setup.iss"
if errorlevel 1 (
    echo [ERROR] Inno Setup compilation failed.
    exit /b 1
)

echo.
echo [OK] Installer written to installer\Output\
endlocal
