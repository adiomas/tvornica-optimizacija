@echo off
REM ============================================================
REM TZH Promet vs Banka — Build Script (Nuitka + NSIS)
REM ============================================================
REM Prerequisites:
REM   - Python 3.12+ with dependencies: pip install -r requirements.txt
REM   - Nuitka: pip install nuitka
REM   - C compiler (MSVC or MinGW — Nuitka downloads automatically)
REM   - NSIS 3.x: https://nsis.sourceforge.io/Download
REM ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0\.."

echo.
echo ====================================
echo  TZH Promet vs Banka - Build
echo ====================================
echo.

REM --- Step 0: Validate ---
echo [0/4] Provjera preduvjeta...

if not exist "version.py" ( echo GRESKA: version.py ne postoji. & pause & exit /b 1 )
if not exist "assets\icon.ico" ( echo GRESKA: assets\icon.ico ne postoji. & pause & exit /b 1 )
if not exist "installer.nsi" ( echo GRESKA: installer.nsi ne postoji. & pause & exit /b 1 )

python -c "import nuitka" >nul 2>&1
if errorlevel 1 (
    echo       Nuitka nije instaliran. Instaliram...
    pip install nuitka
)

echo       Sve OK.
echo.

REM --- Step 1: Clean ---
echo [1/4] Ciscenje prethodnog builda...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "launcher.build" rmdir /s /q "launcher.build"
if exist "launcher.dist" rmdir /s /q "launcher.dist"
if exist "launcher.onefile-build" rmdir /s /q "launcher.onefile-build"
echo       Gotovo.
echo.

REM --- Step 2: Nuitka ---
echo [2/4] Nuitka - kompajliranje u exe...
python -m nuitka ^
    --mode=onefile ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=assets/icon.ico ^
    --include-data-dir=src=src ^
    --include-data-dir=.streamlit=.streamlit ^
    --include-data-files=app.py=app.py ^
    --include-data-files=version.py=version.py ^
    --enable-plugin=anti-bloat ^
    --noinclude-pytest-mode=nofollow ^
    --noinclude-setuptools-mode=nofollow ^
    --noinclude-unittest-mode=nofollow ^
    --noinclude-IPython-mode=nofollow ^
    --product-name="TZH Promet vs Banka" ^
    --company-name="Tvornica Zdrave Hrane" ^
    --output-dir=dist ^
    --output-filename=TZH-Promet-vs-Banka.exe ^
    launcher.py

if errorlevel 1 (
    echo.
    echo GRESKA: Nuitka build nije uspio.
    pause
    exit /b 1
)

if not exist "dist\TZH-Promet-vs-Banka.exe" (
    echo GRESKA: exe nije kreiran.
    pause
    exit /b 1
)
echo       Gotovo.
echo.

REM --- Step 3: NSIS ---
echo [3/4] NSIS - kreiranje installera...

where makensis >nul 2>&1
if errorlevel 1 (
    if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
        set "MAKENSIS=C:\Program Files (x86)\NSIS\makensis.exe"
    ) else if exist "C:\Program Files\NSIS\makensis.exe" (
        set "MAKENSIS=C:\Program Files\NSIS\makensis.exe"
    ) else (
        echo GRESKA: NSIS nije pronadjen.
        pause
        exit /b 1
    )
) else (
    set "MAKENSIS=makensis"
)

"%MAKENSIS%" installer.nsi
if errorlevel 1 ( echo GRESKA: NSIS nije uspio. & pause & exit /b 1 )
echo       Gotovo.
echo.

REM --- Step 4: Verify ---
echo [4/4] Provjera rezultata...
for /f "usebackq tokens=*" %%a in (`findstr "__version__" version.py`) do set "VERLINE=%%a"
for /f "tokens=2 delims=^= " %%b in ("!VERLINE!") do set "VER=%%b"
set "VER=!VER:"=!"
set "VER=!VER: =!"

set "SETUP_FILE=TZH-Promet-vs-Banka-Setup-!VER!.exe"
set "EXE_FILE=dist\TZH-Promet-vs-Banka.exe"

echo.
echo ====================================
echo  BUILD ZAVRSEN USPJESNO!
echo ====================================
echo.
for %%F in ("!EXE_FILE!") do echo  Portable: %%~nxF (%%~zF bytes)
for %%F in ("!SETUP_FILE!") do echo  Installer: %%~nxF (%%~zF bytes)
echo.
pause
