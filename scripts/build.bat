@echo off
REM ============================================================
REM TZH Promet vs Banka — Full Build Script
REM Builds PyInstaller exe + NSIS installer
REM ============================================================
REM Prerequisites:
REM   - Python with PyInstaller: pip install pyinstaller
REM   - NSIS 3.x: https://nsis.sourceforge.io/Download
REM   - makensis.exe in PATH (or set NSIS_PATH below)
REM ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0\.."

echo.
echo ====================================
echo  TZH Promet vs Banka - Build
echo ====================================
echo.

REM --- Step 0: Validate prerequisites ---
echo [0/4] Provjera preduvjeta...

if not exist "version.py" (
    echo       GRESKA: version.py ne postoji.
    pause
    exit /b 1
)

if not exist "assets\icon.ico" (
    echo       GRESKA: assets\icon.ico ne postoji.
    pause
    exit /b 1
)

if not exist "build.spec" (
    echo       GRESKA: build.spec ne postoji.
    pause
    exit /b 1
)

if not exist "installer.nsi" (
    echo       GRESKA: installer.nsi ne postoji.
    pause
    exit /b 1
)

where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo       GRESKA: pyinstaller nije pronadjen. Instaliraj: pip install pyinstaller
    pause
    exit /b 1
)

echo       Sve OK.
echo.

REM --- Step 1: Clean previous build ---
echo [1/4] Ciscenje prethodnog builda...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
echo       Gotovo.
echo.

REM --- Step 2: PyInstaller ---
echo [2/4] PyInstaller - kreiranje exe...
pyinstaller build.spec
if errorlevel 1 (
    echo.
    echo GRESKA: PyInstaller nije uspio. Provjeri output iznad.
    pause
    exit /b 1
)

REM Verify PyInstaller output exists
if not exist "dist\TZH-Promet-vs-Banka\TZH-Promet-vs-Banka.exe" (
    echo.
    echo GRESKA: PyInstaller output nije pronadjen u dist\TZH-Promet-vs-Banka\
    pause
    exit /b 1
)
echo       Gotovo.
echo.

REM --- Step 3: Find NSIS ---
echo [3/4] NSIS - kreiranje installera...

where makensis >nul 2>&1
if errorlevel 1 (
    if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
        set "MAKENSIS=C:\Program Files (x86)\NSIS\makensis.exe"
    ) else if exist "C:\Program Files\NSIS\makensis.exe" (
        set "MAKENSIS=C:\Program Files\NSIS\makensis.exe"
    ) else (
        echo.
        echo GRESKA: makensis.exe nije pronadjen.
        echo Instaliraj NSIS: https://nsis.sourceforge.io/Download
        echo Ili dodaj NSIS u PATH.
        pause
        exit /b 1
    )
) else (
    set "MAKENSIS=makensis"
)

"%MAKENSIS%" installer.nsi
if errorlevel 1 (
    echo.
    echo GRESKA: NSIS nije uspio. Provjeri output iznad.
    pause
    exit /b 1
)

REM --- Step 4: Verify output ---
echo [4/4] Provjera rezultata...

REM Extract version from version.py
for /f "usebackq tokens=*" %%a in (`findstr "__version__" version.py`) do set "VERLINE=%%a"
REM VERLINE is now: __version__ = "1.0.0"
REM Extract just the version between quotes
for /f "tokens=2 delims=^= " %%b in ("!VERLINE!") do set "VER=%%b"
set "VER=!VER:"=!"
set "VER=!VER: =!"

if "!VER!"=="" (
    echo       UPOZORENJE: Nije moguce procitati verziju iz version.py
    set "VER=unknown"
)

set "SETUP_FILE=TZH-Promet-vs-Banka-Setup-!VER!.exe"

if not exist "!SETUP_FILE!" (
    echo       GRESKA: !SETUP_FILE! nije kreiran.
    pause
    exit /b 1
)

echo       Gotovo.
echo.
echo ====================================
echo  BUILD ZAVRSEN USPJESNO!
echo ====================================
echo.
echo  Installer: !SETUP_FILE!
for %%F in ("!SETUP_FILE!") do echo  Velicina:  %%~zF bytes
echo.
pause
