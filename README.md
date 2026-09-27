# FolderSyncPro

一個輕量級的資料夾同步 / 備份工具，支援中英文介面切換。

## 功能

- **三種同步模式**
  - 備份模式：只新增、更新，不會刪除任何檔案
  - 鏡像模式：目的資料夾完全比照來源，來源沒有的檔案會移入回收桶
  - 雙向同步：來源、目的雙邊互相同步；衝突以較新的修改時間為準；任一邊刪除的檔案，另一邊會移入回收桶（軟刪除，不做硬刪除）
- **即時監控**：資料夾有變動時自動觸發同步
- **多專案管理**：可同時管理多組來源/目的資料夾配對
- **同步歷史紀錄**與**回收桶**（誤刪可復原）
- **中文 / 英文介面切換**
- 淡色主題、高對比配色

## 系統需求

- Windows 10 / 11（目前提供 Windows 安裝檔；macOS 打包腳本已附上，需自行在 macOS 上編譯）
- Python 3.10+（若要從原始碼執行）

## 安裝方式

### 一般使用者

至 [Releases](../../releases) 頁面下載最新的 `FolderSyncPro_Setup.exe`，執行安裝即可。

### 從原始碼執行

```bash
pip install -r requirements.txt
python main.py
```

### 自行打包成執行檔

Windows：

```bash
build_exe.bat
```

macOS（需在 macOS 機器上執行）：

```bash
chmod +x build_mac.sh make_dmg.sh
./build_mac.sh
./make_dmg.sh
```

## 專案結構

```
FolderSyncPro/
├── main.py              # 程式進入點
├── gui/                 # 使用者介面（dashboard.py）
├── core/                # 同步引擎、監控、掃描、回收桶邏輯
├── database/            # 專案資料存取
├── assets/              # 圖示等靜態資源
├── build_exe.bat        # Windows 打包腳本
├── build_mac.sh          # macOS 打包腳本
├── make_dmg.sh           # macOS DMG 安裝映像檔打包腳本
└── installer.iss          # Inno Setup 安裝程式腳本（Windows）
```

## 授權

本專案採用 [MIT License](LICENSE)。

## 開發者

本程式由中國醫藥大學人文與科技學院科法碩士學位學程盧裕倉老師開發。
