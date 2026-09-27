@echo off
REM ============================================================
REM FolderSyncPro build script (Windows)
REM Packages main.py into a single .exe using PyInstaller.
REM
REM Usage: place this file in the project root
REM        (same folder as main.py, core, database, gui),
REM        then double-click build_exe.bat
REM ============================================================

echo [1/3] Installing dependencies...
pip install -r requirements.txt

echo [2/3] Cleaning previous build output...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q FolderSyncPro.spec 2>nul

echo [3/3] Building...
REM If main.py also needs to read files from a config folder at
REM runtime, add another line here: --add-data "config;config" ^
python -m PyInstaller ^
    --add-data "assets;assets" ^
    --name "FolderSyncPro" ^
    --onefile ^
    --windowed ^
    --icon "assets\icon.ico" ^
    --collect-all ttkbootstrap ^
    --hidden-import watchdog.observers ^
    --hidden-import watchdog.events ^
    main.py

echo.
echo Done. Executable location: dist\FolderSyncPro.exe
pause
