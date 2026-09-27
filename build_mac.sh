#!/bin/bash
# ============================================================
# FolderSyncPro macOS 打包腳本
# 用途：把 main.py 打包成 FolderSyncPro.app
#
# 注意：這個腳本必須在真正的 macOS 機器上執行。
#
# 使用方式：
#   1. 在專案根目錄打開 Terminal
#   2. chmod +x build_mac.sh
#   3. ./build_mac.sh
# ============================================================

set -e

echo "[1/3] 安裝相依套件..."
pip3 install -r requirements.txt

echo "[2/3] 清除舊的打包結果..."
rm -rf build dist FolderSyncPro.spec

echo "[3/3] 開始打包..."
pyinstaller \
    --add-data "assets:assets" \
    --name "FolderSyncPro" \
    --windowed \
    --onedir \
    --collect-all ttkbootstrap \
    --hidden-import watchdog.observers \
    --hidden-import watchdog.events \
    main.py

echo ""
echo "完成！應用程式位置：dist/FolderSyncPro.app"
echo "雙擊即可執行，或拖到 Applications 資料夾安裝。"
