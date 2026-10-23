import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _resource_path(*parts):
    """
    取得隨程式一起打包的資源檔案（例如 icon）的正確路徑。

    直接用原始碼執行（python main.py）時，資源就在專案資料夾裡，
    以 PROJECT_ROOT 為基準即可找到。

    打包成 PyInstaller --onefile 執行檔後，執行時會把 --add-data
    指定的檔案解壓縮到一個暫存資料夾，路徑存在 sys._MEIPASS，
    這時候必須改成以它為基準，否則會找不到檔案。
    """

    base = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))

    return base.joinpath(*parts)

from core.sync_engine import sync_folder
from core.sync_preview import preview_sync
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from core.watcher import FolderWatcher

import ttkbootstrap as ttk

from database.project_manager import (
    get_projects,
    add_project,
    delete_project,
    update_project as db_update_project,
    get_sync_logs
)

from core.scanner import scan_folder


APP_VERSION = "0.3.0-alpha.3"


TRANSLATIONS = {
    "zh_TW": {
        "app_title": "FolderSyncPro",
        "workflow_step_project": "步驟 1/4：準備專案",
        "workflow_step_paths": "步驟 2/4：設定資料夾",
        "workflow_step_preview": "步驟 3/4：預覽同步",
        "workflow_step_preview_running": "步驟 3/4：產生預覽",
        "workflow_step_review": "步驟 4/4：檢查結果",
        "workflow_step_sync_running": "步驟 4/4：同步執行中",
        "workflow_step_done": "完成：同步結果",
        "workflow_hint_project": "請從「檔案」選擇「新增專案」，或選取現有專案。",
        "workflow_hint_paths": "請填寫來源與目的資料夾，或按「瀏覽」選擇資料夾。",
        "workflow_hint_preview": "請從「功能」選擇「預覽同步」，先檢查即將處理的檔案。",
        "workflow_hint_preview_running": "正在計算變更，需要時可從「功能」選擇「停止同步」。",
        "workflow_hint_review": "請檢查下方結果表格；確認後從「功能」選擇「開始同步」。",
        "workflow_hint_sync_running": "正在執行同步，進度會顯示在上方，需要時可停止。",
        "workflow_hint_done": "同步已完成，可查看結果，或再次預覽下一次變更。",
        "toolbar_new_project": "新增專案",
        "toolbar_update_project": "更新專案",
        "toolbar_scan": "分析/掃描",
        "toolbar_preview": "預覽同步",
        "toolbar_sync": "開始同步",
        "toolbar_stop": "停止",
        "toolbar_start_watch": "啟動監控",
        "toolbar_stop_watch": "停止監控",
        "toolbar_history": "同步歷史",
        "toolbar_file": "檔案",
        "toolbar_features": "功能",
        "toolbar_view": "檢視",
        "view_sync_history": "同步歷史",
        "view_language": "語言",
        "language_zh_tw": "繁體中文",
        "language_en": "English",
        "file_new_project": "新增專案",
        "file_select_project": "選擇專案",
        "file_save_project": "儲存專案",
        "file_update_project": "更新專案",
        "file_delete_project": "刪除選取專案",
        "file_exit": "離開",
        "toolbar_usage": "使用說明",
        "toolbar_about": "關於",
        "section_project_info": "專案資訊",
        "label_project_name": "專案名稱",
        "label_source_folder": "來源資料夾",
        "label_target_folder": "目的資料夾",
        "btn_browse": "瀏覽",
        "btn_add_project": "新增專案",
        "btn_update_project": "更新專案",
        "btn_scan_source": "掃描來源",
        "section_sync_settings": "同步設定與控制",
        "label_sync_mode": "同步模式：",
        "mode_backup": "備份模式",
        "mode_mirror": "鏡像模式",
        "mode_two_way": "雙向同步",
        "check_auto_watch": "啟動時自動監控",
        "btn_preview_sync": "預覽同步",
        "btn_start_sync": "開始同步",
        "btn_stop_sync": "停止同步",
        "btn_start_watch": "啟動監控",
        "btn_stop_watch": "停止監控",
        "section_project_list": "專案清單",
        "btn_delete_project": "刪除選取專案",
        "btn_sync_history": "同步歷史",
        "btn_open_recycle": "開啟回收桶",
        "btn_empty_recycle": "清空回收桶",
        "card_project_count": "專案數",
        "card_monitoring": "監控中",
        "card_synced_files": "同步檔案",
        "card_conflicts": "衝突數",
        "section_log": "同步日誌",
        "section_result": "最近處理結果",
        "result_idle": "尚未執行同步或預覽。",
        "result_running": "{operation}執行中...",
        "result_completed": "{operation}完成，新增 {add}，更新 {update}，刪除 {delete}，衝突 {conflict}",
        "result_cancelled": "{operation}已停止",
        "result_error": "{operation}失敗：{err}",
        "result_column_action": "動作",
        "result_column_path": "檔案路徑",
        "result_column_direction": "方向",
        "result_column_status": "狀態",
        "result_column_reason": "說明",
        "result_done": "完成",
        "result_processing": "處理中",
        "result_error_status": "錯誤",
        "result_preview": "預覽",
        "dialog_close": "關閉",
        "log_app_started": "FolderSyncPro 已啟動",
        "log_enter_project_name": "請輸入專案名稱",
        "log_new_project_ready": "已準備建立新專案，請輸入資料後選擇「檔案 > 儲存專案」",
        "log_project_added": "新增專案成功：{name}",
        "log_project_exists": "專案名稱已存在：{name}",
        "log_add_failed": "新增失敗：{err}",
        "log_select_project_to_update": "請先選擇要更新的專案",
        "log_project_updated": "專案更新成功：{name}",
        "log_update_failed": "更新失敗：{err}",
        "log_select_project": "請先選擇專案",
        "log_project_deleted": "專案刪除成功：{name}",
        "log_select_source_folder": "請先選擇來源資料夾",
        "log_scan_done": "掃描完成：{files} 個檔案，{folders} 個資料夾",
        "log_select_source": "請選擇來源資料夾",
        "log_select_target": "請選擇目的資料夾",
        "log_preview_start": "產生同步預覽...",
        "log_preview_done": "同步預覽完成 新增:{add} 更新:{update} 刪除:{delete} 衝突:{conflict}",
        "log_preview_failed": "同步預覽失敗：{err}",
        "log_preview_cancelled": "同步預覽已停止",
        "log_risk_check_start": "檢查同步風險...",
        "log_risk_check_failed": "同步風險檢查失敗：{err}",
        "log_risk_check_cancelled": "同步風險檢查已停止",
        "log_sync_start": "開始同步...",
        "log_sync_done": "同步完成 新增:{copied} 更新:{updated} 刪除:{deleted}",
        "log_sync_failed": "同步失敗：{err}",
        "log_sync_cancelled": "同步已取消",
        "log_stop_sync_requested": "已要求停止同步，將在目前檔案處理完成後停止...",
        "log_sync_stopped": "同步已停止 新增:{copied} 更新:{updated} 刪除:{deleted}",
        "log_select_target_folder": "請先選擇目的資料夾",
        "log_source_not_exist": "來源不存在：{path}",
        "log_target_not_exist": "目的不存在：{path}",
        "log_watch_already_started": "監控已啟動",
        "log_watch_started": "即時監控已啟動",
        "log_watch_start_failed": "啟動監控失敗：{err}",
        "log_watch_stopped": "監控已停止",
        "log_recycle_not_exist": "回收桶不存在",
        "log_sync_history_header": "==========同步歷史==========",
        "log_recycle_emptied": "已清空回收桶：{count} 個檔案",
        "log_project_loaded": "已載入專案：{name}",
        "preview_title": "同步預覽",
        "preview_empty": "沒有需要同步的檔案。",
        "preview_summary": "摘要：新增 {add}，更新 {update}，刪除 {delete}，衝突 {conflict}，略過 {skip}，總計 {total}",
        "preview_add": "新增",
        "preview_update": "更新",
        "preview_delete": "刪除",
        "preview_conflict": "衝突",
        "preview_skip": "略過",
        "preview_more": "...還有 {count} 筆未顯示",
        "preview_column_action": "動作",
        "preview_column_path": "檔案路徑",
        "preview_column_direction": "方向",
        "preview_column_reason": "原因",
        "preview_direction_source_to_target": "來源 -> 目的",
        "preview_direction_target_to_source": "目的 -> 來源",
        "preview_direction_delete_from_target": "從目的刪除",
        "preview_direction_delete_from_source": "從來源刪除",
        "preview_direction_none": "無",
        "risk_confirm_title": "同步風險確認",
        "risk_confirm_message": "此次同步預覽包含 {delete} 個刪除、{conflict} 個衝突。\n是否仍要繼續同步？",
        "usage_title": "使用說明",
        "usage_text": (
            "FolderSyncPro 使用說明\n\n"
            "1. 在「專案資訊」輸入專案名稱、來源資料夾與目的資料夾，"
            "點選「新增專案」即可建立新的同步專案。\n\n"
            "2. 在「同步設定與控制」選擇同步模式：\n"
            "   • 備份模式：只新增/更新，不會刪除任何檔案。\n"
            "   • 鏡像模式：目的資料夾會完全比照來源，來源沒有的檔案"
            "會從目的移入回收桶。\n"
            "   • 雙向同步：來源、目的雙邊互相同步；兩邊都修改過的檔案"
            "以較新的修改時間為準；任一邊刪除的檔案，另一邊會移入回收桶。\n\n"
            "3. 按「開始同步」執行一次性同步；按「啟動監控」讓程式即時監看"
            "資料夾變動並自動同步。\n\n"
            "4. 「專案清單」可以切換、刪除已建立的專案，並查看同步歷史、"
            "回收桶內容。\n\n"
            "5. 所有操作紀錄都會顯示在下方的「同步日誌」。"
        ),
        "about_title": "關於 FolderSyncPro",
        "about_text": (
            "FolderSyncPro\n"
            f"版本 {APP_VERSION}\n\n"
            "© 2026 FolderSyncPro. 保留所有權利。\n\n"
            "本程式由中國醫藥大學人文與科技學院科法碩士學位學程"
            "盧裕倉老師開發。\n\n"
            "本軟體以現狀提供，不附帶任何明示或默示的擔保。"
        ),
    },
    "en": {
        "app_title": "FolderSyncPro",
        "workflow_step_project": "Step 1/4: Prepare Project",
        "workflow_step_paths": "Step 2/4: Set Folders",
        "workflow_step_preview": "Step 3/4: Preview Sync",
        "workflow_step_preview_running": "Step 3/4: Building Preview",
        "workflow_step_review": "Step 4/4: Review Results",
        "workflow_step_sync_running": "Step 4/4: Syncing",
        "workflow_step_done": "Complete: Sync Results",
        "workflow_hint_project": "Choose File > New Project, or select an existing project.",
        "workflow_hint_paths": "Enter the source and target folders, or use Browse.",
        "workflow_hint_preview": "Choose Features > Preview Sync to review the planned changes first.",
        "workflow_hint_preview_running": "Calculating changes. Choose Features > Stop when needed.",
        "workflow_hint_review": "Review the results table, then choose Features > Start Sync.",
        "workflow_hint_sync_running": "Sync is running. Progress is shown above and can be stopped.",
        "workflow_hint_done": "Sync completed. Review the results or preview the next change set.",
        "toolbar_new_project": "New Project",
        "toolbar_update_project": "Update Project",
        "toolbar_scan": "Analyze / Scan",
        "toolbar_preview": "Preview Sync",
        "toolbar_sync": "Start Sync",
        "toolbar_stop": "Stop",
        "toolbar_start_watch": "Start Watching",
        "toolbar_stop_watch": "Stop Watching",
        "toolbar_history": "Sync History",
        "toolbar_file": "File",
        "toolbar_features": "Features",
        "toolbar_view": "View",
        "view_sync_history": "Sync History",
        "view_language": "Language",
        "language_zh_tw": "Traditional Chinese",
        "language_en": "English",
        "file_new_project": "New Project",
        "file_select_project": "Select Project",
        "file_save_project": "Save Project",
        "file_update_project": "Update Project",
        "file_delete_project": "Delete Selected Project",
        "file_exit": "Exit",
        "toolbar_usage": "Usage Guide",
        "toolbar_about": "About",
        "section_project_info": "Project Info",
        "label_project_name": "Project Name",
        "label_source_folder": "Source Folder",
        "label_target_folder": "Target Folder",
        "btn_browse": "Browse",
        "btn_add_project": "Add Project",
        "btn_update_project": "Update Project",
        "btn_scan_source": "Scan Source",
        "section_sync_settings": "Sync Settings & Control",
        "label_sync_mode": "Sync Mode:",
        "mode_backup": "Backup",
        "mode_mirror": "Mirror",
        "mode_two_way": "Two-Way Sync",
        "check_auto_watch": "Auto-watch on start",
        "btn_preview_sync": "Preview Sync",
        "btn_start_sync": "Start Sync",
        "btn_stop_sync": "Stop Sync",
        "btn_start_watch": "Start Watching",
        "btn_stop_watch": "Stop Watching",
        "section_project_list": "Project List",
        "btn_delete_project": "Delete Selected",
        "btn_sync_history": "Sync History",
        "btn_open_recycle": "Open Recycle Bin",
        "btn_empty_recycle": "Empty Recycle Bin",
        "card_project_count": "Projects",
        "card_monitoring": "Watching",
        "card_synced_files": "Synced Files",
        "card_conflicts": "Conflicts",
        "section_log": "Sync Log",
        "section_result": "Recent Results",
        "result_idle": "No sync or preview has run yet.",
        "result_running": "{operation} in progress...",
        "result_completed": "{operation} complete  Added {add}, Updated {update}, Deleted {delete}, Conflicts {conflict}",
        "result_cancelled": "{operation} stopped",
        "result_error": "{operation} failed: {err}",
        "result_column_action": "Action",
        "result_column_path": "File Path",
        "result_column_direction": "Direction",
        "result_column_status": "Status",
        "result_column_reason": "Details",
        "result_done": "Done",
        "result_processing": "Processing",
        "result_error_status": "Error",
        "result_preview": "Preview",
        "dialog_close": "Close",
        "log_app_started": "FolderSyncPro started",
        "log_enter_project_name": "Please enter a project name",
        "log_new_project_ready": "New project form is ready. Enter the details, then choose File > Save Project.",
        "log_project_added": "Project added: {name}",
        "log_project_exists": "Project name already exists: {name}",
        "log_add_failed": "Failed to add: {err}",
        "log_select_project_to_update": "Please select a project to update",
        "log_project_updated": "Project updated: {name}",
        "log_update_failed": "Update failed: {err}",
        "log_select_project": "Please select a project",
        "log_project_deleted": "Project deleted: {name}",
        "log_select_source_folder": "Please select a source folder first",
        "log_scan_done": "Scan complete: {files} files, {folders} folders",
        "log_select_source": "Please select a source folder",
        "log_select_target": "Please select a target folder",
        "log_preview_start": "Building sync preview...",
        "log_preview_done": "Sync preview complete  Add:{add}  Update:{update}  Delete:{delete}  Conflict:{conflict}",
        "log_preview_failed": "Sync preview failed: {err}",
        "log_preview_cancelled": "Sync preview stopped",
        "log_risk_check_start": "Checking sync risks...",
        "log_risk_check_failed": "Sync risk check failed: {err}",
        "log_risk_check_cancelled": "Sync risk check stopped",
        "log_sync_start": "Starting sync...",
        "log_sync_done": "Sync complete  Added:{copied}  Updated:{updated}  Deleted:{deleted}",
        "log_sync_failed": "Sync failed: {err}",
        "log_sync_cancelled": "Sync cancelled",
        "log_stop_sync_requested": "Stop requested. Sync will stop after the current file finishes...",
        "log_sync_stopped": "Sync stopped  Added:{copied}  Updated:{updated}  Deleted:{deleted}",
        "log_select_target_folder": "Please select a target folder first",
        "log_source_not_exist": "Source does not exist: {path}",
        "log_target_not_exist": "Target does not exist: {path}",
        "log_watch_already_started": "Watching is already running",
        "log_watch_started": "Real-time watching started",
        "log_watch_start_failed": "Failed to start watching: {err}",
        "log_watch_stopped": "Watching stopped",
        "log_recycle_not_exist": "Recycle bin does not exist",
        "log_sync_history_header": "========== Sync History ==========",
        "log_recycle_emptied": "Recycle bin emptied: {count} files",
        "log_project_loaded": "Project loaded: {name}",
        "preview_title": "Sync Preview",
        "preview_empty": "No files need to be synchronized.",
        "preview_summary": "Summary: add {add}, update {update}, delete {delete}, conflict {conflict}, skip {skip}, total {total}",
        "preview_add": "Add",
        "preview_update": "Update",
        "preview_delete": "Delete",
        "preview_conflict": "Conflict",
        "preview_skip": "Skip",
        "preview_more": "...{count} more item(s) not shown",
        "preview_column_action": "Action",
        "preview_column_path": "File Path",
        "preview_column_direction": "Direction",
        "preview_column_reason": "Reason",
        "preview_direction_source_to_target": "Source -> Target",
        "preview_direction_target_to_source": "Target -> Source",
        "preview_direction_delete_from_target": "Delete from Target",
        "preview_direction_delete_from_source": "Delete from Source",
        "preview_direction_none": "None",
        "risk_confirm_title": "Sync Risk Confirmation",
        "risk_confirm_message": "This sync preview includes {delete} delete action(s) and {conflict} conflict(s).\nDo you still want to continue?",
        "usage_title": "Usage Guide",
        "usage_text": (
            "FolderSyncPro Usage Guide\n\n"
            "1. Enter a project name, source folder, and target folder under "
            "\"Project Info\", then click \"Add Project\" to create a new sync "
            "project.\n\n"
            "2. Choose a sync mode under \"Sync Settings & Control\":\n"
            "   • Backup: only adds/updates files, never deletes anything.\n"
            "   • Mirror: the target folder mirrors the source exactly; files "
            "missing from the source are moved to the recycle bin on the "
            "target.\n"
            "   • Two-Way Sync: source and target sync in both directions; "
            "when both sides changed the same file, the newer one wins; "
            "if either side deletes a file, the other side moves it to the "
            "recycle bin.\n\n"
            "3. Click \"Start Sync\" for a one-time sync, or \"Start "
            "Watching\" to let the app watch for changes and sync "
            "automatically.\n\n"
            "4. Use \"Project List\" to switch between or delete saved "
            "projects, and to view sync history and the recycle bin.\n\n"
            "5. All activity is shown in the \"Sync Log\" panel below."
        ),
        "about_title": "About FolderSyncPro",
        "about_text": (
            "FolderSyncPro\n"
            f"Version {APP_VERSION}\n\n"
            "\u00a9 2026 FolderSyncPro. All rights reserved.\n\n"
            "Developed by Prof. Lu Yu-Tsang, Master's Program in "
            "Technology Law, College of Humanities and Technology, "
            "China Medical University.\n\n"
            "This software is provided \"as is\", without warranty of any "
            "kind, express or implied."
        ),
    },
}


class DashboardApp(ttk.Window):

    def __init__(self):

        super().__init__(
            title="FolderSyncPro",
            themename="litera",
            size=(1400, 900)
        )

        self._set_window_icon()

        self.current_lang = "zh_TW"
        self.i18n_registry = []
        self.i18n_heading_registry = []
        self.i18n_menu_registry = []
        self.file_menu_items = {}
        self.feature_menu_items = {}
        self.ui_font_family = self._pick_font_family()
        self.workflow_step_key = "workflow_step_project"
        self.workflow_hint_key = "workflow_hint_project"

        self.project_name = tk.StringVar()
        self.source_path = tk.StringVar()
        self.target_path = tk.StringVar()
        self.sync_mode = tk.StringVar(value="backup")
        
        # 新增這行
        self.auto_watch = tk.BooleanVar(value=False)

        self.projects = []
        self.watcher = None
        self.sync_cancel_requested = False
        self.sync_thread = None
        self.operation_started_at = None
        self.operation_name = ""
        self.result_row_limit = 250

        self.build_ui()
        self.load_statistics()
        self.protocol(
            "WM_DELETE_WINDOW",
            self.on_closing
        )

    def _set_window_icon(self):
        """
        設定視窗左上角與工作列的圖示。
        Windows 用 assets/icon.ico；macOS/Linux 用 assets/icon.png
        （.ico 在非 Windows 平台上通常無法正確顯示）。
        找不到檔案時安靜略過，不影響程式啟動。
        """

        try:

            if sys.platform.startswith("win"):

                icon_path = _resource_path("assets", "icon.ico")

                if icon_path.exists():
                    self.iconbitmap(str(icon_path))

            else:

                icon_path = _resource_path("assets", "icon.png")

                if icon_path.exists():

                    # 保留參考，避免被垃圾回收導致圖示消失
                    self._window_icon_image = tk.PhotoImage(
                        file=str(icon_path)
                    )

                    self.iconphoto(True, self._window_icon_image)

        except Exception:

            pass

    def _pick_font_family(self):

        import tkinter.font as tkfont

        available = set(tkfont.families())

        # 依序嘗試：Windows 常見繁中字型 -> macOS 常見繁中字型 -> 通用字型
        candidates = [
            "Microsoft JhengHei",
            "PingFang TC",
            "Heiti TC",
            "Noto Sans TC",
            "Microsoft YaHei",
            "Arial"
        ]

        for name in candidates:

            if name in available:
                return name

        return "TkDefaultFont"

    def tr(self, key, **kwargs):

        text = TRANSLATIONS[self.current_lang].get(
            key,
            TRANSLATIONS["zh_TW"].get(key, key)
        )

        if kwargs:
            return text.format(**kwargs)

        return text

    def reg(self, widget, key):
        """
        註冊一個會隨語言切換而更新文字的元件。
        呼叫後立刻套用目前語言的文字。
        """

        self.i18n_registry.append((widget, key))

        widget.config(text=self.tr(key))

    def reg_heading(self, tree, column, key):

        self.i18n_heading_registry.append((tree, column, key))

        tree.heading(
            column,
            text=self.tr(key)
        )

    def reg_menu_item(self, menu, index, key):

        self.i18n_menu_registry.append((menu, index, key))

        menu.entryconfigure(
            index,
            label=self.tr(key)
        )

    def add_feature_menu_item(self, key, command, state="normal"):

        self.feature_menu.add_command(
            label=self.tr(key),
            command=command,
            state=state
        )

        index = self.feature_menu.index("end")
        self.feature_menu_items[key] = index
        self.reg_menu_item(
            self.feature_menu,
            index,
            key
        )

    def add_file_menu_item(self, key, command, state="normal"):

        self.file_menu.add_command(
            label=self.tr(key),
            command=command,
            state=state
        )

        index = self.file_menu.index("end")
        self.file_menu_items[key] = index
        self.reg_menu_item(
            self.file_menu,
            index,
            key
        )

    def set_feature_menu_state(self, key, state):

        index = self.feature_menu_items.get(key)

        if index is None:
            return

        try:
            self.feature_menu.entryconfigure(
                index,
                state=state
            )
        except tk.TclError:
            pass

    def set_language(self, lang_code):

        if lang_code not in TRANSLATIONS:
            return

        self.current_lang = lang_code

        for widget, key in self.i18n_registry:

            try:
                widget.config(text=self.tr(key))
            except tk.TclError:
                pass

        for tree, column, key in self.i18n_heading_registry:

            try:
                tree.heading(
                    column,
                    text=self.tr(key)
                )
            except tk.TclError:
                pass

        for menu, index, key in self.i18n_menu_registry:

            try:
                menu.entryconfigure(
                    index,
                    label=self.tr(key)
                )
            except tk.TclError:
                pass

        self.render_workflow_hint()

    def set_workflow_state(self, step_key, hint_key):

        self.workflow_step_key = step_key
        self.workflow_hint_key = hint_key
        self.render_workflow_hint()

    def render_workflow_hint(self):

        if not hasattr(self, "workflow_step_label"):
            return

        self.workflow_step_label.config(
            text=self.tr(self.workflow_step_key)
        )
        self.workflow_hint_label.config(
            text=self.tr(self.workflow_hint_key)
        )

    def refresh_workflow_from_form(self):

        if self.sync_thread and self.sync_thread.is_alive():
            return

        if not self.project_name.get().strip() and not self.source_path.get() and not self.target_path.get():
            self.set_workflow_state(
                "workflow_step_project",
                "workflow_hint_project"
            )
        elif not self.source_path.get() or not self.target_path.get():
            self.set_workflow_state(
                "workflow_step_paths",
                "workflow_hint_paths"
            )
        else:
            self.set_workflow_state(
                "workflow_step_preview",
                "workflow_hint_preview"
            )

    def build_ui(self):

        # 淡色背景 + 高對比文字/框線的自訂色票
        self.configure(background="#f4f6f8")

        LOG_BG = "#ffffff"
        LOG_FG = "#1a1a1a"
        LOG_BORDER = "#8c96a3"

        # ======================
        # 工具列(檔案 / 功能 / 檢視 / 使用說明 / 關於)
        # ======================

        toolbar = ttk.Frame(self)

        toolbar.pack(
            fill="x",
            padx=10,
            pady=(8, 0)
        )

        self.file_menu = tk.Menu(
            toolbar,
            tearoff=False
        )

        self.add_file_menu_item(
            "file_new_project",
            self.new_project
        )
        self.add_file_menu_item(
            "file_select_project",
            self.focus_project_list
        )
        self.file_menu.add_separator()
        self.add_file_menu_item(
            "file_save_project",
            self.save_project
        )
        self.add_file_menu_item(
            "file_update_project",
            self.update_project
        )
        self.add_file_menu_item(
            "file_delete_project",
            self.delete_selected_project
        )
        self.file_menu.add_separator()
        self.add_file_menu_item(
            "file_exit",
            self.on_closing
        )

        self.file_menu_button = ttk.Menubutton(
            toolbar,
            menu=self.file_menu,
            bootstyle="link"
        )
        self.reg(self.file_menu_button, "toolbar_file")
        self.file_menu_button.pack(side="left", padx=(0, 2))

        self.feature_menu = tk.Menu(
            toolbar,
            tearoff=False
        )

        self.add_feature_menu_item(
            "toolbar_scan",
            self.scan_source
        )
        self.add_feature_menu_item(
            "toolbar_preview",
            self.show_sync_preview
        )
        self.add_feature_menu_item(
            "toolbar_sync",
            self.start_sync
        )
        self.add_feature_menu_item(
            "toolbar_stop",
            self.stop_sync,
            state="disabled"
        )
        self.feature_menu.add_separator()
        self.add_feature_menu_item(
            "toolbar_start_watch",
            self.start_watch
        )
        self.add_feature_menu_item(
            "toolbar_stop_watch",
            self.stop_watch,
            state="disabled"
        )

        self.feature_menu_button = ttk.Menubutton(
            toolbar,
            menu=self.feature_menu,
            bootstyle="link"
        )
        self.reg(self.feature_menu_button, "toolbar_features")
        self.feature_menu_button.pack(side="left", padx=(0, 2))

        self.view_menu = tk.Menu(
            toolbar,
            tearoff=False
        )

        self.view_menu.add_command(
            label=self.tr("view_sync_history"),
            command=self.show_sync_logs
        )
        self.reg_menu_item(
            self.view_menu,
            0,
            "view_sync_history"
        )

        self.language_menu = tk.Menu(
            self.view_menu,
            tearoff=False
        )

        self.language_menu.add_command(
            label=self.tr("language_zh_tw"),
            command=lambda: self.set_language("zh_TW")
        )
        self.reg_menu_item(
            self.language_menu,
            0,
            "language_zh_tw"
        )

        self.language_menu.add_command(
            label=self.tr("language_en"),
            command=lambda: self.set_language("en")
        )
        self.reg_menu_item(
            self.language_menu,
            1,
            "language_en"
        )

        self.view_menu.add_cascade(
            label=self.tr("view_language"),
            menu=self.language_menu
        )
        self.reg_menu_item(
            self.view_menu,
            1,
            "view_language"
        )

        self.view_menu_button = ttk.Menubutton(
            toolbar,
            menu=self.view_menu,
            bootstyle="link"
        )
        self.reg(self.view_menu_button, "toolbar_view")
        self.view_menu_button.pack(side="left", padx=(0, 2))

        ttk.Separator(
            toolbar,
            orient="vertical"
        ).pack(side="left", fill="y", padx=8)

        about_btn = ttk.Button(
            toolbar,
            command=self.show_about,
            bootstyle="link"
        )

        about_btn.pack(side="right", padx=(2, 5))

        self.reg(about_btn, "toolbar_about")

        usage_btn = ttk.Button(
            toolbar,
            command=self.show_usage_guide,
            bootstyle="link"
        )

        usage_btn.pack(side="right", padx=2)

        self.reg(usage_btn, "toolbar_usage")

        # ======================
        # 標題
        # ======================

        title = ttk.Label(
            self,
            text="FolderSyncPro",
            font=(self.ui_font_family, 24, "bold"),
            bootstyle="dark"
        )

        title.pack(pady=(15, 5))

        workflow_frame = ttk.Frame(self)
        workflow_frame.pack(
            fill="x",
            padx=20,
            pady=(0, 5)
        )

        self.workflow_step_label = ttk.Label(
            workflow_frame,
            bootstyle="primary",
            anchor="w"
        )
        self.workflow_step_label.pack(
            side="left",
            padx=(0, 12)
        )

        self.workflow_hint_label = ttk.Label(
            workflow_frame,
            bootstyle="secondary",
            anchor="w"
        )
        self.workflow_hint_label.pack(
            side="left",
            fill="x",
            expand=True
        )
        self.render_workflow_hint()

        # ======================
        # 第一列：專案清單(左) + 專案資訊(右)
        # ======================

        top_row_frame = ttk.Frame(self)

        top_row_frame.pack(
            fill="x",
            padx=20,
            pady=10
        )

        # ---- 專案清單(左) ----

        project_frame = ttk.Labelframe(
            top_row_frame,
            bootstyle="primary"
        )

        self.reg(project_frame, "section_project_list")

        project_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 10)
        )

        self.project_listbox = tk.Listbox(
            project_frame,
            height=6,
            bg="#ffffff",
            fg="#1a1a1a",
            selectbackground="#4a7fd6",
            selectforeground="#ffffff",
            highlightthickness=1,
            highlightbackground=LOG_BORDER,
            highlightcolor="#4a7fd6",
            relief="flat"
        )

        self.project_listbox.bind(
            "<<ListboxSelect>>",
            self.load_selected_project
        )

        self.project_listbox.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        # 專案清單下方的按鈕依用途分組:專案動作 / 紀錄 / 回收桶,群組之間留較大間距

        list_action_frame = ttk.Frame(project_frame)

        list_action_frame.pack(
            fill="x",
            padx=10,
            pady=(0, 10)
        )

        delete_project_btn = ttk.Button(
            list_action_frame,
            command=self.delete_selected_project,
            bootstyle="danger"
        )

        self.reg(delete_project_btn, "btn_delete_project")

        delete_project_btn.pack(side="left", padx=(0, 20))

        recycle_group = ttk.Frame(list_action_frame)

        recycle_group.pack(side="left")

        open_recycle_btn = ttk.Button(
            recycle_group,
            command=self.open_recycle_bin,
            bootstyle="secondary"
        )

        self.reg(open_recycle_btn, "btn_open_recycle")

        open_recycle_btn.pack(side="left", padx=(0, 5))

        empty_recycle_btn = ttk.Button(
            recycle_group,
            command=self.empty_recycle,
            bootstyle="warning"
        )

        self.reg(empty_recycle_btn, "btn_empty_recycle")

        empty_recycle_btn.pack(side="left")

        # ---- 專案資訊(右) ----

        form_frame = ttk.Labelframe(
            top_row_frame,
            bootstyle="primary"
        )

        self.reg(form_frame, "section_project_info")

        form_frame.pack(
            side="left",
            fill="both",
            expand=True
        )

        label_project_name = ttk.Label(
            form_frame,
            bootstyle="dark"
        )

        self.reg(label_project_name, "label_project_name")

        label_project_name.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.project_name_entry = ttk.Entry(
            form_frame,
            textvariable=self.project_name,
            width=40
        )
        self.project_name_entry.grid(
            row=0,
            column=1,
            padx=5,
            pady=5,
            sticky="w"
        )

        label_source_folder = ttk.Label(
            form_frame,
            bootstyle="dark"
        )

        self.reg(label_source_folder, "label_source_folder")

        label_source_folder.grid(row=1, column=0, padx=5, pady=5, sticky="e")

        ttk.Entry(
            form_frame,
            textvariable=self.source_path,
            width=70
        ).grid(row=1, column=1, padx=5, sticky="w")

        browse_source_btn = ttk.Button(
            form_frame,
            command=self.choose_source,
            bootstyle="outline-secondary"
        )

        self.reg(browse_source_btn, "btn_browse")

        browse_source_btn.grid(row=1, column=2, padx=5)

        label_target_folder = ttk.Label(
            form_frame,
            bootstyle="dark"
        )

        self.reg(label_target_folder, "label_target_folder")

        label_target_folder.grid(row=2, column=0, padx=5, pady=5, sticky="e")

        ttk.Entry(
            form_frame,
            textvariable=self.target_path,
            width=70
        ).grid(row=2, column=1, padx=5, sticky="w")

        browse_target_btn = ttk.Button(
            form_frame,
            command=self.choose_target,
            bootstyle="outline-secondary"
        )

        self.reg(browse_target_btn, "btn_browse")

        browse_target_btn.grid(row=2, column=2, padx=5)

        # ---- 專案操作(新增 / 更新 / 掃描 皆為對「這筆專案資訊」的動作,集中一列) ----

        project_action_frame = ttk.Frame(form_frame)

        project_action_frame.grid(
            row=3,
            column=0,
            columnspan=3,
            pady=(12, 5),
            sticky="w"
        )

        add_project_btn = ttk.Button(
            project_action_frame,
            command=self.save_project,
            bootstyle="success"
        )

        self.reg(add_project_btn, "btn_add_project")

        add_project_btn.pack(side="left", padx=5)

        update_project_btn = ttk.Button(
            project_action_frame,
            command=self.update_project,
            bootstyle="warning"
        )

        self.reg(update_project_btn, "btn_update_project")

        update_project_btn.pack(side="left", padx=5)

        scan_source_btn = ttk.Button(
            project_action_frame,
            command=self.scan_source,
            bootstyle="info"
        )

        self.reg(scan_source_btn, "btn_scan_source")

        scan_source_btn.pack(side="left", padx=5)

        # ======================
        # 同步設定與控制(模式選擇 + 自動監控 + 執行動作 全部與「同步這件事」有關,集中一區)
        # ======================

        sync_frame = ttk.Labelframe(
            self,
            bootstyle="primary"
        )

        self.reg(sync_frame, "section_sync_settings")

        sync_frame.pack(
            fill="x",
            padx=20,
            pady=(0, 10)
        )

        mode_frame = ttk.Frame(sync_frame)

        mode_frame.pack(
            fill="x",
            padx=10,
            pady=(10, 5)
        )

        label_sync_mode = ttk.Label(
            mode_frame,
            bootstyle="dark"
        )

        self.reg(label_sync_mode, "label_sync_mode")

        label_sync_mode.pack(side="left", padx=(0, 5))

        radio_backup = ttk.Radiobutton(
            mode_frame,
            variable=self.sync_mode,
            value="backup",
            bootstyle="primary"
        )

        self.reg(radio_backup, "mode_backup")

        radio_backup.pack(side="left", padx=10)

        radio_mirror = ttk.Radiobutton(
            mode_frame,
            variable=self.sync_mode,
            value="mirror",
            bootstyle="primary"
        )

        self.reg(radio_mirror, "mode_mirror")

        radio_mirror.pack(side="left", padx=10)

        radio_two_way = ttk.Radiobutton(
            mode_frame,
            variable=self.sync_mode,
            value="two_way",
            bootstyle="primary"
        )

        self.reg(radio_two_way, "mode_two_way")

        radio_two_way.pack(side="left", padx=10)

        check_auto_watch = ttk.Checkbutton(
            mode_frame,
            variable=self.auto_watch,
            bootstyle="round-toggle"
        )

        self.reg(check_auto_watch, "check_auto_watch")

        check_auto_watch.pack(side="left", padx=20)

        sync_action_frame = ttk.Frame(sync_frame)

        sync_action_frame.pack(
            fill="x",
            padx=10,
            pady=(5, 10)
        )

        self.start_sync_btn = ttk.Button(
            sync_action_frame,
            command=self.start_sync,
            bootstyle="warning"
        )

        self.reg(self.start_sync_btn, "btn_start_sync")

        self.start_sync_btn.pack(side="left", padx=5)

        self.stop_sync_btn = ttk.Button(
            sync_action_frame,
            command=self.stop_sync,
            state="disabled",
            bootstyle="outline-danger"
        )

        self.reg(self.stop_sync_btn, "btn_stop_sync")

        self.stop_sync_btn.pack(side="left", padx=5)

        self.preview_sync_btn = ttk.Button(
            sync_action_frame,
            command=self.show_sync_preview,
            bootstyle="info"
        )

        self.reg(self.preview_sync_btn, "btn_preview_sync")

        self.preview_sync_btn.pack(side="left", padx=5)

        self.start_watch_btn = ttk.Button(
            sync_action_frame,
            command=self.start_watch,
            bootstyle="secondary"
        )

        self.reg(self.start_watch_btn, "btn_start_watch")

        self.start_watch_btn.pack(side="left", padx=5)

        self.stop_watch_btn = ttk.Button(
            sync_action_frame,
            command=self.stop_watch,
            state="disabled",
            bootstyle="danger"
        )

        self.reg(self.stop_watch_btn, "btn_stop_watch")

        self.stop_watch_btn.pack(side="left", padx=5)

        # ---- 同步進度條 ----

        progress_frame = ttk.Frame(sync_frame)

        progress_frame.pack(
            fill="x",
            padx=10,
            pady=(0, 10)
        )

        self.sync_progress = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            bootstyle="success-striped"
        )

        self.sync_progress.pack(
            side="left",
            fill="x",
            expand=True
        )

        self.sync_progress_label = ttk.Label(
            progress_frame,
            text="",
            bootstyle="dark",
            width=16,
            anchor="e"
        )

        self.sync_progress_label.pack(side="left", padx=(10, 0))

        # ======================
        # Dashboard 卡片
        # ======================

        stat_frame = ttk.Frame(self)

        stat_frame.pack(
            fill="x",
            padx=20
        )

        self.project_count_label = self.create_card(
            stat_frame,
            "card_project_count",
            "0"
        )

        self.monitor_count_label = self.create_card(
            stat_frame,
            "card_monitoring",
            "0"
        )

        self.file_count_label = self.create_card(
            stat_frame,
            "card_synced_files",
            "0"
        )

        self.conflict_count_label = self.create_card(
            stat_frame,
            "card_conflicts",
            "0"
        )

        # ======================
        # 最近處理結果
        # ======================

        result_frame = ttk.Labelframe(
            self,
            bootstyle="primary"
        )

        self.reg(result_frame, "section_result")

        result_frame.pack(
            fill="both",
            expand=False,
            padx=20,
            pady=(10, 0)
        )

        self.result_summary_label = ttk.Label(
            result_frame,
            anchor="w",
            bootstyle="dark"
        )

        self.result_summary_label.pack(
            fill="x",
            padx=10,
            pady=(7, 4)
        )

        result_table_frame = ttk.Frame(result_frame)
        result_table_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 8)
        )

        result_columns = (
            "action",
            "path",
            "direction",
            "status",
            "reason",
        )

        self.result_tree = ttk.Treeview(
            result_table_frame,
            columns=result_columns,
            show="headings",
            height=6
        )

        self.reg_heading(
            self.result_tree,
            "action",
            "result_column_action"
        )
        self.reg_heading(
            self.result_tree,
            "path",
            "result_column_path"
        )
        self.reg_heading(
            self.result_tree,
            "direction",
            "result_column_direction"
        )
        self.reg_heading(
            self.result_tree,
            "status",
            "result_column_status"
        )
        self.reg_heading(
            self.result_tree,
            "reason",
            "result_column_reason"
        )

        self.result_tree.column(
            "action",
            width=85,
            anchor="center",
            stretch=False
        )
        self.result_tree.column("path", width=420, anchor="w")
        self.result_tree.column(
            "direction",
            width=135,
            anchor="center",
            stretch=False
        )
        self.result_tree.column(
            "status",
            width=85,
            anchor="center",
            stretch=False
        )
        self.result_tree.column("reason", width=330, anchor="w")

        self.result_tree.tag_configure(
            "error",
            foreground="#b42318"
        )
        self.result_tree.tag_configure(
            "conflict",
            foreground="#9a6700"
        )
        self.result_tree.tag_configure(
            "delete",
            foreground="#b42318"
        )
        self.result_tree.tag_configure(
            "add",
            foreground="#067647"
        )

        result_y_scroll = ttk.Scrollbar(
            result_table_frame,
            orient="vertical",
            command=self.result_tree.yview
        )
        result_x_scroll = ttk.Scrollbar(
            result_table_frame,
            orient="horizontal",
            command=self.result_tree.xview
        )

        self.result_tree.configure(
            yscrollcommand=result_y_scroll.set,
            xscrollcommand=result_x_scroll.set
        )

        self.result_tree.grid(row=0, column=0, sticky="nsew")
        result_y_scroll.grid(row=0, column=1, sticky="ns")
        result_x_scroll.grid(row=1, column=0, sticky="ew")

        result_table_frame.grid_rowconfigure(0, weight=1)
        result_table_frame.grid_columnconfigure(0, weight=1)

        self.result_summary_label.config(
            text=self.tr("result_idle")
        )

        # ======================
        # 日誌
        # ======================

        log_frame = ttk.Labelframe(
            self,
            bootstyle="primary"
        )

        self.reg(log_frame, "section_log")

        log_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        self.log_text = ScrolledText(
            log_frame,
            bg=LOG_BG,
            fg=LOG_FG,
            insertbackground=LOG_FG,
            highlightthickness=1,
            highlightbackground=LOG_BORDER,
            highlightcolor="#4a7fd6",
            relief="flat"
        )

        self.log_text.pack(
            fill="both",
            expand=True,
            padx=1,
            pady=1
        )

        self.write_log(self.tr("log_app_started"))

    def create_card(self, parent, title_key, value):

        frame = ttk.LabelFrame(
            parent,
            bootstyle="primary"
        )

        self.reg(frame, title_key)

        frame.pack(
            side="left",
            fill="x",
            expand=True,
            padx=10
        )

        label = ttk.Label(
            frame,
            text=value,
            font=(self.ui_font_family, 20, "bold"),
            bootstyle="dark"
        )

        label.pack(pady=20)

        return label

    def write_log(self, text):

        self.log_text.insert(
            "end",
            text + "\n"
        )

        self.log_text.see("end")

    def _show_text_dialog(self, title, body):

        win = tk.Toplevel(self)

        win.title(title)
        win.geometry("560x440")
        win.configure(background="#f4f6f8")

        text_widget = ScrolledText(
            win,
            wrap="word",
            bg="#ffffff",
            fg="#1a1a1a",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#8c96a3"
        )

        text_widget.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=15
        )

        text_widget.insert("1.0", body)
        text_widget.config(state="disabled")

        ttk.Button(
            win,
            text=self.tr("dialog_close"),
            command=win.destroy,
            bootstyle="secondary"
        ).pack(pady=(0, 15))

    def show_usage_guide(self):

        self._show_text_dialog(
            self.tr("usage_title"),
            self.tr("usage_text")
        )

    def show_about(self):

        self._show_text_dialog(
            self.tr("about_title"),
            self.tr("about_text")
        )

    def load_statistics(self):

        self.projects = get_projects()

        self.project_count_label.config(
            text=str(len(self.projects))
        )

        self.project_listbox.delete(
            0,
            tk.END
        )

        for row in self.projects:

            self.project_listbox.insert(
                tk.END,
                row[1]
            )

    def load_selected_project(self, event=None):

        selected = self.project_listbox.curselection()

        if not selected:
            return

        idx = selected[0]

        project = self.projects[idx]

        self.project_name.set(project[1])
        self.source_path.set(project[2])
        self.target_path.set(project[3])

        self.auto_watch.set(
            bool(project[4])
        )

        self.refresh_workflow_from_form()

        self.write_log(
            self.tr("log_project_loaded", name=project[1])
        )

        if bool(project[4]):

            self.start_watch()

    def choose_source(self):

        folder = filedialog.askdirectory()

        if folder:
            self.source_path.set(folder)
            self.refresh_workflow_from_form()

    def choose_target(self):

        folder = filedialog.askdirectory()

        if folder:
            self.target_path.set(folder)
            self.refresh_workflow_from_form()

    def focus_project_list(self):

        self.project_listbox.focus_set()

    def new_project(self):

        if self.sync_thread and self.sync_thread.is_alive():
            return

        self.project_listbox.selection_clear(0, tk.END)
        self.project_name.set("")
        self.source_path.set("")
        self.target_path.set("")
        self.auto_watch.set(False)
        self._reset_result_panel()
        self.project_name_entry.focus_set()
        self.set_workflow_state(
            "workflow_step_paths",
            "workflow_hint_paths"
        )
        self.write_log(self.tr("log_new_project_ready"))

    def save_project(self):

        project_name = self.project_name.get().strip()

        if not project_name:

            self.write_log(
                self.tr("log_enter_project_name")
            )

            return

        try:

            add_project(
                project_name,
                self.source_path.get(),
                self.target_path.get(),
                int(self.auto_watch.get())
            )

            self.write_log(
                self.tr("log_project_added", name=project_name)
            )

            self.load_statistics()
            self.set_workflow_state(
                "workflow_step_preview",
                "workflow_hint_preview"
            )

        except Exception as e:

            if "UNIQUE constraint failed" in str(e):

                self.write_log(
                    self.tr("log_project_exists", name=project_name)
                )

            else:

                self.write_log(
                    self.tr("log_add_failed", err=e)
                )

    def update_project(self):

        selected = self.project_listbox.curselection()

        if not selected:

            self.write_log(
                self.tr("log_select_project_to_update")
            )

            return

        idx = selected[0]

        project_id = self.projects[idx][0]

        try:

            db_update_project(
                project_id,
                self.source_path.get(),
                self.target_path.get(),
                int(self.auto_watch.get())
            )

            self.load_statistics()

            self.project_listbox.selection_clear(
                0,
                tk.END
            )

            self.project_listbox.selection_set(
                idx
            )

            self.write_log(
                self.tr("log_project_updated", name=self.project_name.get())
            )
            self.set_workflow_state(
                "workflow_step_preview",
                "workflow_hint_preview"
            )

        except Exception as e:

            self.write_log(
                self.tr("log_update_failed", err=e)
            )

    def delete_selected_project(self):

        selected = self.project_listbox.curselection()

        if not selected:

            self.write_log(
                    self.tr("log_select_project")
            )

            return

        idx = selected[0]

        project_id = self.projects[idx][0]

        project_name = self.projects[idx][1]

        delete_project(project_id)

        self.project_name.set("")
        self.source_path.set("")
        self.target_path.set("")

        self.write_log(
            self.tr("log_project_deleted", name=project_name)
         )

        self.load_statistics()
        self.set_workflow_state(
            "workflow_step_project",
            "workflow_hint_project"
        )

    def scan_source(self):

        folder = self.source_path.get()

        if not folder:

            self.write_log(
                self.tr("log_select_source_folder")
            )

            return

        result = scan_folder(folder)

        self.file_count_label.config(
            text=str(result["files"])
        )

        self.write_log(
            self.tr(
                "log_scan_done",
                files=result["files"],
                folders=result["folders"]
            )
        )

    def show_sync_preview(self):

        source = self.source_path.get()
        target = self.target_path.get()

        if not source:

            self.write_log(
                self.tr("log_select_source")
            )

            return

        if not target:

            self.write_log(
                self.tr("log_select_target")
            )

            return

        self.write_log(
            self.tr("log_preview_start")
        )

        self.set_workflow_state(
            "workflow_step_preview_running",
            "workflow_hint_preview_running"
        )

        self._reset_result_panel(
            self.tr("toolbar_preview")
        )
        self._set_operation_controls(True)

        self.sync_progress["value"] = 0
        self.sync_progress_label.config(text="0%")

        self.sync_cancel_requested = False
        self.preview_sync_btn.config(state="disabled")
        self.stop_sync_btn.config(state="normal")

        self.sync_thread = threading.Thread(
            target=self._run_preview_worker,
            args=(
                source,
                target,
                self.sync_mode.get(),
                self.project_name.get() or "未命名專案"
            ),
            daemon=True
        )

        self.sync_thread.start()

    def _run_preview_worker(self, source, target, mode, project_name):

        try:

            preview = preview_sync(
                source,
                target,
                mode=mode,
                project_name=project_name,
                progress_func=self._on_sync_progress,
                cancel_func=self._is_sync_cancel_requested
            )

        except Exception as e:

            self.after(
                0,
                lambda err=e: self._on_preview_error(err)
            )

            return

        self.after(
            0,
            lambda result=preview: self._on_preview_success(result)
        )

    def _on_preview_success(self, preview):

        if preview.get("cancelled"):

            self.write_log(
                self.tr("log_preview_cancelled")
            )

            self._complete_result_panel({}, cancelled=True)
            self._set_operation_controls(False)
            self.set_workflow_state(
                "workflow_step_preview",
                "workflow_hint_preview"
            )
            self.sync_cancel_requested = False

            return

        summary = preview["summary"]

        self.sync_progress["value"] = 100
        self.sync_progress_label.config(text="100%")

        self.write_log(
            self.tr(
                "log_preview_done",
                add=summary["add"],
                update=summary["update"],
                delete=summary["delete"],
                conflict=summary["conflict"]
            )
        )

        self._append_preview_results(preview)
        self._complete_result_panel(summary)
        self.set_workflow_state(
            "workflow_step_review",
            "workflow_hint_review"
        )

        self._show_preview_table_dialog(
            self.tr("preview_title"),
            preview
        )

        self._set_operation_controls(False)
        self.sync_cancel_requested = False

    def _on_preview_error(self, err):

        self.write_log(
            self.tr("log_preview_failed", err=err)
        )

        self._set_result_error(err)
        self._set_operation_controls(False)
        self.set_workflow_state(
            "workflow_step_preview",
            "workflow_hint_preview"
        )
        self.sync_cancel_requested = False

    def _show_preview_table_dialog(self, title, preview):

        summary = preview["summary"]

        win = tk.Toplevel(self)

        win.title(title)
        win.geometry("920x560")
        win.configure(background="#f4f6f8")

        summary_text = self.tr(
            "preview_summary",
            add=summary["add"],
            update=summary["update"],
            delete=summary["delete"],
            conflict=summary["conflict"],
            skip=summary["skip"],
            total=summary["total"]
        )

        summary_label = ttk.Label(
            win,
            text=summary_text,
            bootstyle="dark",
            anchor="w"
        )

        summary_label.pack(
            fill="x",
            padx=15,
            pady=(15, 10)
        )

        if summary["total"] == 0:
            empty_label = ttk.Label(
                win,
                text=self.tr("preview_empty"),
                bootstyle="dark",
                anchor="center"
            )

            empty_label.pack(
                fill="both",
                expand=True,
                padx=15,
                pady=15
            )

            ttk.Button(
                win,
                text=self.tr("dialog_close"),
                command=win.destroy,
                bootstyle="secondary"
            ).pack(pady=(0, 15))

            return

        table_frame = ttk.Frame(win)

        table_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15)
        )

        columns = (
            "action",
            "path",
            "direction",
            "reason",
        )

        tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=16
        )

        tree.heading(
            "action",
            text=self.tr("preview_column_action")
        )
        tree.heading(
            "path",
            text=self.tr("preview_column_path")
        )
        tree.heading(
            "direction",
            text=self.tr("preview_column_direction")
        )
        tree.heading(
            "reason",
            text=self.tr("preview_column_reason")
        )

        tree.column("action", width=90, anchor="center", stretch=False)
        tree.column("path", width=360, anchor="w")
        tree.column("direction", width=140, anchor="center", stretch=False)
        tree.column("reason", width=300, anchor="w")

        y_scroll = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=tree.yview
        )
        x_scroll = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=tree.xview
        )

        tree.configure(
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )

        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        for action_type, action in self._iter_preview_rows(preview):
            tree.insert(
                "",
                "end",
                values=(
                    self.tr(f"preview_{action_type}"),
                    action.get("path", ""),
                    self._format_preview_direction(
                        action.get("direction", "")
                    ),
                    action.get("reason", ""),
                )
            )

        ttk.Button(
            win,
            text=self.tr("dialog_close"),
            command=win.destroy,
            bootstyle="secondary"
        ).pack(pady=(0, 15))

    def _iter_preview_rows(self, preview):

        sections = (
            "add",
            "update",
            "delete",
            "conflict",
            "skip",
        )

        for action_type in sections:

            for action in preview.get(action_type, []):

                yield action_type, action

    def _format_preview_direction(self, direction):

        key = f"preview_direction_{direction}"

        return self.tr(key)

    def _format_sync_preview(self, preview):

        summary = preview["summary"]

        lines = [
            self.tr(
                "preview_summary",
                add=summary["add"],
                update=summary["update"],
                delete=summary["delete"],
                conflict=summary["conflict"],
                skip=summary["skip"],
                total=summary["total"]
            ),
            ""
        ]

        if summary["total"] == 0:
            lines.append(
                self.tr("preview_empty")
            )
            return "\n".join(lines)

        sections = [
            ("add", "preview_add"),
            ("update", "preview_update"),
            ("delete", "preview_delete"),
            ("conflict", "preview_conflict"),
            ("skip", "preview_skip"),
        ]

        max_items_per_section = 100

        for key, title_key in sections:

            actions = preview.get(key, [])

            if not actions:
                continue

            lines.append(
                self.tr(title_key)
            )

            for action in actions[:max_items_per_section]:

                lines.append(
                    f"- {action['path']} ({action['direction']})"
                )

                if action.get("reason"):

                    lines.append(
                        f"  {action['reason']}"
                    )

            remaining = len(actions) - max_items_per_section

            if remaining > 0:

                lines.append(
                    self.tr("preview_more", count=remaining)
                )

            lines.append("")

        return "\n".join(lines).rstrip()

    def _reset_result_panel(self, operation=None):

        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

        if operation:
            self.operation_name = operation
            self.operation_started_at = time.monotonic()
            self.result_summary_label.config(
                text=self.tr(
                    "result_running",
                    operation=operation
                )
            )
        else:
            self.operation_name = ""
            self.operation_started_at = None
            self.result_summary_label.config(
                text=self.tr("result_idle")
            )

    def _set_operation_controls(self, running):

        normal = "disabled" if running else "normal"

        for button in (
            self.start_sync_btn,
            self.preview_sync_btn,
        ):
            button.config(state=normal)

        for key in (
            "toolbar_scan",
            "toolbar_preview",
            "toolbar_sync",
        ):
            self.set_feature_menu_state(key, normal)

        for key in (
            "file_new_project",
            "file_select_project",
            "file_save_project",
            "file_update_project",
            "file_delete_project",
        ):
            self.file_menu.entryconfigure(
                self.file_menu_items[key],
                state=normal
            )

        stop_state = "normal" if running else "disabled"

        self.stop_sync_btn.config(state=stop_state)
        self.set_feature_menu_state(
            "toolbar_stop",
            stop_state
        )

    def _append_result_row(
        self,
        action,
        path,
        direction,
        status,
        reason,
        tag="",
    ):

        children = self.result_tree.get_children()

        if len(children) >= self.result_row_limit:
            self.result_tree.delete(children[0])

        values = (
            action,
            path,
            direction,
            status,
            reason,
        )

        self.result_tree.insert(
            "",
            "end",
            values=values,
            tags=(tag,) if tag else ()
        )

        self.result_tree.yview_moveto(1.0)

    def _parse_sync_log(self, text):

        entries = (
            ("[新增至目的]", "preview_add", "source_to_target", "add"),
            ("[新增至來源]", "preview_add", "target_to_source", "add"),
            ("[新增]", "preview_add", "source_to_target", "add"),
            ("[更新]", "preview_update", "source_to_target", ""),
            ("[衝突/以來源較新為準]", "preview_conflict", "source_to_target", "conflict"),
            ("[衝突/以目的較新為準]", "preview_conflict", "target_to_source", "conflict"),
            ("[回收桶/來源]", "preview_delete", "delete_from_source", "delete"),
            ("[回收桶/目的]", "preview_delete", "delete_from_target", "delete"),
            ("[回收桶]", "preview_delete", "delete_from_target", "delete"),
            ("[跳過]", "preview_skip", "none", ""),
            ("[錯誤]", "result_error_status", "none", "error"),
        )

        for prefix, action_key, direction, tag in entries:

            if not text.startswith(prefix):
                continue

            path = text[len(prefix):].strip()
            action = self.tr(action_key)
            direction_text = self._format_preview_direction(direction)
            status = self.tr(
                "result_error_status"
                if tag == "error"
                else "result_done"
            )

            return (
                action,
                path,
                direction_text,
                status,
                "",
                tag,
            )

        return None

    def _append_worker_result(self, text):

        parsed = self._parse_sync_log(text)

        if parsed:
            self._append_result_row(*parsed)

    def _append_preview_results(self, preview):

        displayed = 0

        for action_type, action in self._iter_preview_rows(preview):

            if displayed >= self.result_row_limit:
                break

            tag = action_type if action_type in {
                "add",
                "delete",
                "conflict",
            } else ""

            self._append_result_row(
                self.tr(f"preview_{action_type}"),
                action.get("path", ""),
                self._format_preview_direction(
                    action.get("direction", "none")
                ),
                self.tr("result_preview"),
                action.get("reason", ""),
                tag,
            )
            displayed += 1

    def _complete_result_panel(self, result, cancelled=False):

        operation = self.operation_name or self.tr("toolbar_sync")

        if cancelled:
            self.result_summary_label.config(
                text=self.tr(
                    "result_cancelled",
                    operation=operation
                )
            )
            return

        elapsed = ""
        if self.operation_started_at is not None:
            elapsed = f"  ·  {time.monotonic() - self.operation_started_at:.1f}s"

        self.result_summary_label.config(
            text=self.tr(
                "result_completed",
                operation=operation,
                add=result.get("copied", result.get("add", 0)),
                update=result.get("updated", result.get("update", 0)),
                delete=result.get("deleted", result.get("delete", 0)),
                conflict=result.get("conflicts", result.get("conflict", 0)),
            ) + elapsed
        )

    def _set_result_error(self, err):

        operation = self.operation_name or self.tr("toolbar_sync")
        self.result_summary_label.config(
            text=self.tr(
                "result_error",
                operation=operation,
                err=err,
            )
        )

    def start_sync(self):

        source = self.source_path.get()
        target = self.target_path.get()

        if not source:

            self.write_log(
                self.tr("log_select_source")
            )

            return

        if not target:

            self.write_log(
                self.tr("log_select_target")
            )

            return

        mode = self.sync_mode.get()
        project_name = self.project_name.get()
        self.sync_cancel_requested = False
        self.set_workflow_state(
            "workflow_step_sync_running",
            "workflow_hint_sync_running"
        )
        self._set_operation_controls(True)

        if mode in ("mirror", "two_way"):

            self.start_sync_btn.config(state="disabled")
            self.stop_sync_btn.config(state="normal")

            self.sync_progress["value"] = 0
            self.sync_progress_label.config(text="0%")

            self.write_log(
                self.tr("log_risk_check_start")
            )

            self.sync_thread = threading.Thread(
                target=self._run_sync_risk_check_worker,
                args=(source, target, mode, project_name),
                daemon=True
            )

            self.sync_thread.start()

            return

        self._start_sync_worker_thread(
            source,
            target,
            mode,
            project_name
        )

    def _run_sync_risk_check_worker(self, source, target, mode, project_name):

        try:

            preview = preview_sync(
                source,
                target,
                mode=mode,
                project_name=project_name or "未命名專案",
                progress_func=self._on_sync_progress,
                cancel_func=self._is_sync_cancel_requested
            )

        except Exception as e:

            self.after(
                0,
                lambda err=e: self._on_sync_risk_check_error(err)
            )

            return

        self.after(
            0,
            lambda result=preview: self._on_sync_risk_check_success(
                source,
                target,
                mode,
                project_name,
                result
            )
        )

    def _on_sync_risk_check_success(
        self,
        source,
        target,
        mode,
        project_name,
        preview
    ):

        if preview.get("cancelled"):

            self.write_log(
                self.tr("log_risk_check_cancelled")
            )

            self._complete_result_panel({}, cancelled=True)
            self._set_operation_controls(False)
            self.set_workflow_state(
                "workflow_step_review",
                "workflow_hint_review"
            )
            self.sync_cancel_requested = False

            return

        summary = preview["summary"]
        delete_count = summary["delete"]
        conflict_count = summary["conflict"]

        if delete_count or conflict_count:

            should_continue = messagebox.askyesno(
                self.tr("risk_confirm_title"),
                self.tr(
                    "risk_confirm_message",
                    delete=delete_count,
                    conflict=conflict_count
                ),
                parent=self
            )

            if not should_continue:

                self.write_log(
                    self.tr("log_sync_cancelled")
                )

                self._complete_result_panel({}, cancelled=True)
                self._set_operation_controls(False)
                self.set_workflow_state(
                    "workflow_step_review",
                    "workflow_hint_review"
                )

                return

        self._start_sync_worker_thread(
            source,
            target,
            mode,
            project_name
        )

    def _on_sync_risk_check_error(self, err):

        self.write_log(
            self.tr("log_risk_check_failed", err=err)
        )

        self._set_result_error(err)
        self._set_operation_controls(False)
        self.set_workflow_state(
            "workflow_step_review",
            "workflow_hint_review"
        )

    def _start_sync_worker_thread(self, source, target, mode, project_name):

        self.sync_cancel_requested = False
        self.set_workflow_state(
            "workflow_step_sync_running",
            "workflow_hint_sync_running"
        )
        self._reset_result_panel(
            self.tr("toolbar_sync")
        )
        self._set_operation_controls(True)

        self.sync_progress["value"] = 0
        self.sync_progress_label.config(text="0%")

        self.write_log(
            self.tr("log_sync_start")
        )

        self.sync_thread = threading.Thread(
            target=self._run_sync_worker,
            args=(source, target, mode, project_name),
            daemon=True
        )

        self.sync_thread.start()

    def _run_sync_worker(self, source, target, mode, project_name):
        """
        實際執行同步的工作，跑在背景執行緒，
        避免大量檔案同步時把整個視窗卡住。

        注意：這個方法裡不能直接操作任何 tkinter 元件
        （write_log、進度條……），因為 tkinter 不是執行緒安全的，
        一律透過 self.after(0, ...) 把更新丟回主執行緒處理。
        """

        try:

            result = sync_folder(
                source,
                target,
                self._threadsafe_log,
                mode=mode,
                project_name=project_name,
                progress_func=self._on_sync_progress,
                cancel_func=self._is_sync_cancel_requested
            )

            scan_result = scan_folder(source)

            self.after(
                0,
                lambda: self._on_sync_success(result, scan_result)
            )

        except Exception as e:

            self.after(
                0,
                lambda err=e: self._on_sync_error(err)
            )

    def _threadsafe_log(self, text):

        self.after(
            0,
            lambda t=text: self._handle_worker_log(t)
        )

    def _handle_worker_log(self, text):

        self.write_log(text)
        self._append_worker_result(text)

    def _is_sync_cancel_requested(self):

        return self.sync_cancel_requested

    def stop_sync(self):

        if not self.sync_thread or not self.sync_thread.is_alive():
            return

        self.sync_cancel_requested = True
        self.stop_sync_btn.config(state="disabled")

        self.write_log(
            self.tr("log_stop_sync_requested")
        )

    def _on_sync_progress(self, done, total, relative):

        percent = int(done / total * 100) if total else 0

        now = time.monotonic()
        if (
            done < total
            and now - getattr(self, "last_progress_update", 0) < 0.1
        ):
            return

        self.last_progress_update = now

        self.after(
            0,
            lambda p=percent, d=done, t=total: self._update_progress_ui(
                p, d, t
            )
        )

    def _update_progress_ui(self, percent, done, total):

        self.sync_progress["value"] = percent

        self.sync_progress_label.config(
            text=f"{percent}% ({done}/{total})"
        )

    def _on_sync_success(self, result, scan_result):

        if result.get("cancelled"):

            self.write_log(
                self.tr(
                    "log_sync_stopped",
                    copied=result["copied"],
                    updated=result["updated"],
                    deleted=result["deleted"]
                )
            )

        else:

            self.write_log(
                self.tr(
                    "log_sync_done",
                    copied=result["copied"],
                    updated=result["updated"],
                    deleted=result["deleted"]
                )
            )

        self._complete_result_panel(
            result,
            cancelled=result.get("cancelled", False)
        )

        self.set_workflow_state(
            "workflow_step_review"
            if result.get("cancelled")
            else "workflow_step_done",
            "workflow_hint_review"
            if result.get("cancelled")
            else "workflow_hint_done"
        )

        self.file_count_label.config(
            text=str(scan_result["files"])
        )

        self.conflict_count_label.config(
            text=str(result.get("conflicts", 0))
        )

        self.sync_progress["value"] = 100
        self.sync_progress_label.config(text="100%")

        self._set_operation_controls(False)
        self.sync_cancel_requested = False

    def _on_sync_error(self, err):

        self.write_log(
            self.tr("log_sync_failed", err=err)
        )

        self._set_result_error(err)
        self._set_operation_controls(False)
        self.set_workflow_state(
            "workflow_step_review",
            "workflow_hint_review"
        )
        self.sync_cancel_requested = False

    def start_watch(self):

        source = self.source_path.get()
        target = self.target_path.get()

        if not source:

            self.write_log(
                self.tr("log_select_source_folder")
            )
            return

        if not target:

            self.write_log(
                self.tr("log_select_target_folder")
            )
            return

        if not Path(source).exists():

            self.write_log(
                self.tr("log_source_not_exist", path=source)
            )
            return

        if not Path(target).exists():

            self.write_log(
                self.tr("log_target_not_exist", path=target)
            )
            return

        try:

            if self.watcher:

                self.write_log(
                    self.tr("log_watch_already_started")
                )
                return

            self._watch_source = source

            self.watcher = FolderWatcher(
                source,
                target,
                self._threadsafe_log,
                mode=self.sync_mode.get(),
                project_name=self.project_name.get() or "未命名專案",
                result_func=self._on_watch_sync_result
            )

            self.watcher.start()

            self.monitor_count_label.config(
                text="1"
            )

            self.start_watch_btn.config(state="disabled")
            self.stop_watch_btn.config(state="normal")
            self.set_feature_menu_state(
                "toolbar_start_watch",
                "disabled"
            )
            self.set_feature_menu_state(
                "toolbar_stop_watch",
                "normal"
            )

            self.write_log(
                self.tr("log_watch_started")
            )

        except Exception as e:

            self.write_log(
                self.tr("log_watch_start_failed", err=e)
            )

    def _on_watch_sync_result(self, result):
        """
        監控觸發同步後的結果回報，跑在 watchdog 自己的背景執行緒，
        一律透過 self.after(0, ...) 丟回主執行緒才能安全更新畫面。
        """

        self.after(
            0,
            lambda r=result: self._update_watch_stats(r)
        )

    def _update_watch_stats(self, result):

        self.conflict_count_label.config(
            text=str(result.get("conflicts", 0))
        )

        try:

            scan_result = scan_folder(self._watch_source)

            self.file_count_label.config(
                text=str(scan_result["files"])
            )

        except Exception:

            pass

    def on_closing(self):

        if self.watcher:
            self.watcher.stop()

        self.destroy()
        
    def stop_watch(self):

        if self.watcher:

            self.watcher.stop()

            self.watcher = None

            self.monitor_count_label.config(
                text="0"
            )

            self.write_log(
                self.tr("log_watch_stopped")
            )

        self.start_watch_btn.config(state="normal")
        self.stop_watch_btn.config(state="disabled")
        self.set_feature_menu_state(
            "toolbar_start_watch",
            "normal"
        )
        self.set_feature_menu_state(
            "toolbar_stop_watch",
            "disabled"
        )

    def open_recycle_bin(self):

        import os
        import sys
        import subprocess

        recycle_bin = os.path.join("data", "recycle_bin")

        if not os.path.exists(recycle_bin):

            self.write_log(
                self.tr("log_recycle_not_exist")
            )
            return

        try:

            if sys.platform.startswith("win"):

                os.startfile(recycle_bin)

            elif sys.platform == "darwin":

                subprocess.Popen(["open", recycle_bin])

            else:

                subprocess.Popen(["xdg-open", recycle_bin])

        except Exception as e:

            self.write_log(
                self.tr("log_add_failed", err=e)
            )
            
    def show_sync_logs(self):

        logs = get_sync_logs()

        self.write_log(
            self.tr("log_sync_history_header")
        )

        for row in logs:

            self.write_log(
                f"{row[0]} | "
                f"{row[1]} | "
                f"{row[2]} | "
                f"{row[3]}"
            )
            
    def empty_recycle(self):

        from core.recycle_manager import (
            empty_recycle_bin
        )

        count = empty_recycle_bin()

        self.write_log(
            self.tr("log_recycle_emptied", count=count)
        )

if __name__ == "__main__":

    app = DashboardApp()
    app.mainloop()
