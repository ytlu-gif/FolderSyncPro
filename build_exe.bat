@echo off
REM ============================================================
REM FolderSyncPro build script (Windows)
REM Packages main.py into a single .exe using PyInstaller.
REM
REM Usage: place this file in the project root
REM        (same folder as main.py, core, database, gui),
REM        then double-click build_exe.bat
REM ============================================================

echo [1/4] Installing dependencies...
pip install -r requirements.txt

echo [2/4] Cleaning previous build output...
rmdir /s /q build_v0_3_alpha3 2>nul
rmdir /s /q build_v0_3_alpha3_usn_helper 2>nul
rmdir /s /q dist_v0_3_alpha3 2>nul
del /q FolderSyncPro.spec 2>nul
del /q usn_helper.spec 2>nul

echo [3/4] Building main application...
REM If main.py also needs to read files from a config folder at
REM runtime, add another line here: --add-data "config;config" ^
python -m PyInstaller ^
    --add-data "assets;assets" ^
    --name "FolderSyncPro" ^
    --onefile ^
    --windowed ^
    --distpath dist_v0_3_alpha3 ^
    --workpath build_v0_3_alpha3 ^
    --icon "assets\icon.ico" ^
    --collect-all ttkbootstrap ^
    --hidden-import watchdog.observers ^
    --hidden-import watchdog.events ^
    main.py

echo [4/4] Building elevated USN helper...
python -m PyInstaller ^
    --name "FolderSyncProUsnHelper" ^
    --onefile ^
    --windowed ^
    --distpath dist_v0_3_alpha3 ^
    --workpath build_v0_3_alpha3_usn_helper ^
    usn_helper.py

echo.
echo Done. Executables:
echo   dist_v0_3_alpha3\FolderSyncPro.exe
echo   dist_v0_3_alpha3\FolderSyncProUsnHelper.exe
pause
