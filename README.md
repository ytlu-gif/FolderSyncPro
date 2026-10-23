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
- Windows NTFS 可使用 USN Journal 變更索引加速；不支援或權限不足時會自動回到完整掃描

## v0.3.0-alpha.3 重點

- 新增專業操作工具列，集中管理專案、掃描、預覽、同步與監控功能
- 同步與預覽期間顯示進度、停止控制與執行狀態
- 新增「最近處理結果」表格，動態列出新增、更新、刪除、衝突與略過項目
- 結果表格支援繁體中文 / English 欄位切換，並保留最後一次操作摘要
- 將同步歷史與語言切換集中到工具列的「檢視」選單
- 將專案管理集中到「檔案」選單，將掃描、預覽、同步與監控集中到「功能」選單

## USN Journal 加速

在 Windows NTFS 磁碟上，USN Journal 會記錄檔案建立、修改、重新命名與刪除等變更，
FolderSyncPro 可以利用這些記錄找出上次同步後的候選路徑，減少每次從頭掃描整個資料夾的需要。

這項功能是可選的加速層，不是同步正確性的唯一依據。第一次同步、Journal 被重建或覆寫、
磁碟不是 NTFS 時，程式會自動使用完整掃描。程式不會自行建立或刪除 Windows 的 USN Journal。

若目前使用者無法直接讀取 USN Journal，Windows 會要求一次提升權限；程式只會啟動
`FolderSyncProUsnHelper.exe` 讀取變更索引，主程式本身仍維持一般使用者權限。helper 只在
FolderSyncPro 執行期間提供本機查詢，關閉程式後會一併結束。

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
├── core/                # 同步引擎、監控、掃描、USN Journal、回收桶邏輯
├── database/            # 專案資料存取
├── assets/              # 圖示等靜態資源
├── build_exe.bat        # Windows 打包腳本
├── usn_helper.py        # 提升權限的 USN Journal 查詢入口
├── build_mac.sh          # macOS 打包腳本
├── make_dmg.sh           # macOS DMG 安裝映像檔打包腳本
└── installer.iss          # Inno Setup 安裝程式腳本（Windows）
```

## 授權

本專案採用 [MIT License](LICENSE)。

## 開發者

本程式由中國醫藥大學人文與科技學院科法碩士學位學程盧裕倉老師開發。
