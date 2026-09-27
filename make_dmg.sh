#!/bin/bash
# ============================================================
# FolderSyncPro macOS DMG 打包腳本
# 用途：把 dist/FolderSyncPro.app 包成 FolderSyncPro.dmg
# ============================================================

set -e

APP_NAME="FolderSyncPro"
APP_PATH="dist/${APP_NAME}.app"
DMG_NAME="${APP_NAME}.dmg"
STAGING_DIR="dmg_staging"

if [ ! -d "$APP_PATH" ]; then
    echo "找不到 $APP_PATH，請先執行 ./build_mac.sh"
    exit 1
fi

echo "[1/3] 準備暫存資料夾..."
rm -rf "$STAGING_DIR" "$DMG_NAME"
mkdir "$STAGING_DIR"
cp -R "$APP_PATH" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"

echo "[2/3] 建立 DMG..."
hdiutil create -volname "$APP_NAME" \
    -srcfolder "$STAGING_DIR" \
    -ov -format UDZO \
    "$DMG_NAME"

echo "[3/3] 清理暫存檔案..."
rm -rf "$STAGING_DIR"

echo ""
echo "完成！安裝映像檔：$DMG_NAME"
