# -*- coding: utf-8 -*-
"""MarkItDown 转换器 —— 傻瓜式图形界面（中文 / English 双语）
把文件拖进来 / 从微信选择，选好输出文件夹，一键批量转换成 Markdown。

普通运行 = 图形界面；带 --worker 参数运行 = 后台转换工作进程
（转换在独立进程中进行，界面永不卡顿）。

界面语言：安装时选择的语言由安装程序写入 language.txt；便携模式首次启动时询问，
也可用 --lang zh / --lang en 强制指定。
"""
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from importlib.util import find_spec
from pathlib import Path

# ---------------- 基础配置 ----------------
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = SCRIPT_DIR / "markitdown_gui_config.json"
LANG_FILE = SCRIPT_DIR / "language.txt"   # 安装程序把安装时选择的语言写在这里
ICON_FILE = SCRIPT_DIR / "app.ico"
MANUAL_FILE = SCRIPT_DIR / "MarkItDown转换器使用说明书.pdf"
MANUAL_FILE_EN = SCRIPT_DIR / "MarkItDown Converter User Guide.pdf"   # 英文说明书（后续随包提供）

WORKER_PARALLEL = min(4, os.cpu_count() or 4)   # 工作进程内并行转换数
# 界面运行期间一直持有的命名互斥体：安装/卸载程序（setup.iss 的 AppMutex）与
# 更新器据此判断转换器是否在运行（三处名字必须一致）
APP_MUTEX_NAME = "MarkItDownConverterGUI"

# ---------------- 配色：深空科技风 ----------------
C_BG      = "#0a0e17"
C_PANEL   = "#101827"
C_CARD    = "#141f33"
C_BORDER  = "#1f3050"
C_TERM    = "#050a12"
C_CYAN    = "#22d3ee"
C_CYAN_H  = "#67e8f9"
C_CYAN_D  = "#0e7490"
C_PURPLE  = "#a78bfa"
C_GREEN   = "#34d399"
C_RED     = "#fb7185"
C_AMBER   = "#fbbf24"
C_TEXT    = "#dbe7ff"
C_DIM     = "#54709e"

IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
# 转换时把内嵌图片一并导出的文档格式：图片落盘为 <文件名>.assets/ 下的文件，
# md 中以相对路径引用（PPTX 默认只输出指向不存在文件的失效引用；DOCX 默认
# 内嵌 base64 巨串，两者都统一改为文件引用）
EMBED_IMG_EXTS = {".pptx", ".docx"}

# ---------------- 界面文案：中文 / English ----------------
STRINGS = {
    "zh": {
        "app_title": "MarkItDown 转换器",
        "title_suffix": " 转换器",
        "supported_label": "支持格式",
        "supported_hint": "PDF · DOCX · XLSX · PPTX · HTML · CSV · JSON · XML · 图片(OCR) · 音频",
        "st_waiting": "● 等待",
        "st_running": "◉ 转换中",
        "st_done": "✓ 完成",
        "st_failed": "✗ 失败",
        "st_empty": "⚠ 无文字",
        "st_stopped": "■ 已停止",
        "empty_img": "OCR 未能从图中识别出文字",
        "empty_pdf": "PDF 无文字层且 OCR 未识别到文字（扫描件需要 OCR 组件，可运行「检查更新」自动安装；文档也可能已加密）",
        "empty_audio": "音频转文字需要语音识别模型（本地版 markitdown 不具备）",
        "empty_default": "该文件中没有可提取的文字",
        "ocr_img_title": "— 图片文字识别",
        "ocr_img_note": "以下内容由 Windows OCR 本地识别",
        "ocr_pdf_title": "— 扫描件文字识别",
        "ocr_pdf_note": "该 PDF 无文字层，以下内容由 Windows OCR 本地识别",
        "ocr_page_empty": "（第 {n} 页未识别到文字）",
        "ocr_page_limit": "（页数较多，仅识别前 {n} 页）",
        "alt_img": "图片",
        "wc_title": "从微信选择文件",
        "wc_head": "◢ 微信文件",
        "wc_search": "🔍 搜索文件名…",
        "wc_select_all": "全选",
        "wc_select_none": "清空选择",
        "wc_scanning": "正在扫描微信文件目录…",
        "wc_none_found": "未找到微信接收的文件\n（请确认微信已登录并收到过文件）",
        "wc_load_more": "▼ 加载更多（还有 {n} 条）",
        "wc_no_match": "没有匹配「{kw}」的文件",
        "wc_selected": "已选 {n} 个",
        "wc_confirm": "＋ 添加到队列",
        "wc_log_added": "微信：已加入 {n} 个文件",
        "notice_head": "◢ 提示 NOTICE",
        "notice_dont_show": "不再提示",
        "notice_ok": "知道了",
        "media_title": "媒体文件提示",
        "media_img_ocr": "• 图片 × {n}：将自动调用 Windows OCR 在本地识别图中文字，识别结果会保存为 .md 文件",
        "media_img_no_ocr": "• 图片 × {n}：未检测到 OCR 组件，可能无法提取图中文字",
        "media_audio": "• 音频 × {n}：暂不支持语音转写，将标记为「无文字」",
        "media_local_note": "全部识别均在本地完成，不会上传任何内容。",
        "drop_label": "⇩  拖 入 文 件\nDRAG & DROP FILES HERE",
        "sec_queue": "任务队列 TASK QUEUE",
        "queue_empty": "[ 队列为空 ]",
        "btn_add": "＋ 添加文件",
        "btn_wechat": "💬 微信文件",
        "btn_clear": "清空列表",
        "sec_output": "输出目录 OUTPUT DIR",
        "btn_browse": "浏览…",
        "sec_terminal": "执行终端 TERMINAL",
        "status_ready": "[ READY ] 准备就绪",
        "btn_convert": "▶ 开始转换 EXECUTE",
        "btn_converting": "◉ 转换中 RUNNING…",
        "btn_stop": "■ 停止转换 STOP",
        "btn_stopping": "◌ 正在停止…",
        "log_stop_req": "── 已请求停止，正在结束转换进程… ──",
        "log_skip_done": "── 跳过 {n} 个已转换过的文件（只转换新加入、失败或未完成的）──",
        "reconvert_title": "重新转换",
        "reconvert_msg": "队列中的 {n} 个文件都已转换过。\n\n要全部重新转换吗？输出目录没变时，会覆盖上次生成的 Markdown 文件。",
        "reconvert_ok": "全部重新转换",
        "dlg_cancel": "取消",
        "btn_open_output": "📂 打开输出目录",
        "btn_logs": "📄 日志中心",
        "sys_ready": "SYSTEM READY — 等待任务输入",
        "fatal_no_lib": "未找到 markitdown 库，请确认已安装。",
        "dlg_pick_files": "选择要转换的文件",
        "dlg_pick_output": "选择输出文件夹",
        "status_queue": "[ QUEUE ] 已加入 {n} 个任务",
        "no_log_center": "未找到日志中心（update.pyw），当前为便携模式运行",
        "open_logs_fail": "无法打开日志中心：{e}",
        "wait_add_files": "[ WAIT ] 请先添加要转换的文件",
        "err_outdir": "[ ERROR ] 输出文件夹无效：{e}",
        "err_outdir_notdir": "[ ERROR ] 输出路径不是一个文件夹",
        "log_task_start": "── 任务开始，共 {n} 个文件 ──",
        "log_worker_fail": "  ✗ 失败  工作进程异常",
        "log_worker_crash": "  ✗ 失败  {name}：转换进程意外退出（文件可能已损坏或格式异常）",
        "log_worker_restart": "  ↻ 转换进程已重启，继续处理剩余 {n} 个文件",
        "log_engine_fail": "  ✗ 转换引擎加载失败：{msg}",
        "log_engine_fix": "  ➜ 请运行开始菜单「检查更新 · 日志中心」自动修复；若仍失败，请重新运行安装包",
        "log_done": "  ✓ 完成{tag}  {secs:.2f}s",
        "tag_ocr": "（OCR 识别）",
        "tag_imgs": "（图片×{n}）",
        "log_empty": "  ⚠ 无文字内容，未生成文件（{hint}）",
        "log_more": "  … 以及另外 {n} 个文件（省略命令回显）",
        "engine_broken": "转换引擎不可用：请运行开始菜单「检查更新 · 日志中心」自动修复；若仍失败，请重新运行安装包",
        "open_output_fail": "无法打开输出目录：{e}",
        "status_run": "[ RUN ] 正在转换 {done} / {total} …",
        "sum_ok": "完成 {n}",
        "sum_empty": "无内容 {n}",
        "sum_fail": "失败 {n}",
        "sum_stopped": "已停止 {n}",
        "sum_join": "，",
        "status_done": "[ DONE ] 全部完成 {total}/{total}，用时 {secs:.1f}s",
        "log_done_all": "── 任务完成：{total}/{total}，总耗时 {secs:.1f}s ──",
        "status_warn": "[ WARN ] {summary}，用时 {secs:.1f}s",
        "log_end": "── 任务结束：{summary} ──",
        "status_stopped": "[ STOP ] 已停止：{summary}，用时 {secs:.1f}s",
        "log_end_stopped": "── 任务已停止：{summary} ──",
        "output_dirname": "输出",
    },
    "en": {
        "app_title": "MarkItDown Converter",
        "title_suffix": " Converter",
        "supported_label": "Supported formats",
        "supported_hint": "PDF · DOCX · XLSX · PPTX · HTML · CSV · JSON · XML · Images (OCR) · Audio",
        "st_waiting": "● Waiting",
        "st_running": "◉ Running",
        "st_done": "✓ Done",
        "st_failed": "✗ Failed",
        "st_empty": "⚠ No text",
        "st_stopped": "■ Stopped",
        "empty_img": "OCR could not recognize any text in the image",
        "empty_pdf": "The PDF has no text layer and OCR found no text (scanned PDFs need the OCR component, which \"Check for Updates\" can install; the file may also be encrypted)",
        "empty_audio": "Audio transcription requires a speech recognition model (not included in this local markitdown build)",
        "empty_default": "No extractable text was found in this file",
        "ocr_img_title": "— Image Text Recognition",
        "ocr_img_note": "The text below was recognized locally on this PC by Windows OCR",
        "ocr_pdf_title": "— Scanned PDF Text Recognition",
        "ocr_pdf_note": "This PDF has no text layer; the text below was recognized locally on this PC by Windows OCR",
        "ocr_page_empty": "(No text recognized on page {n})",
        "ocr_page_limit": "(The document has many pages; only the first {n} pages were processed)",
        "alt_img": "image",
        "wc_title": "Select Files from WeChat",
        "wc_head": "◢ WeChat Files",
        "wc_search": "🔍 Search file names…",
        "wc_select_all": "Select All",
        "wc_select_none": "Clear Selection",
        "wc_scanning": "Scanning WeChat file folders…",
        "wc_none_found": "No received WeChat files were found\n(make sure WeChat is signed in and has received files)",
        "wc_load_more": "▼ Load more ({n} more)",
        "wc_no_match": 'No files match "{kw}"',
        "wc_selected": "{n} selected",
        "wc_confirm": "＋ Add to Queue",
        "wc_log_added": "WeChat: added {n} file(s)",
        "notice_head": "◢ NOTICE",
        "notice_dont_show": "Don't show again",
        "notice_ok": "Got It",
        "media_title": "Media File Notice",
        "media_img_ocr": "• Images × {n}: the text in the images will be recognized locally with Windows OCR and saved as .md files",
        "media_img_no_ocr": "• Images × {n}: the OCR component was not detected, so text in the images may not be extracted",
        "media_audio": "• Audio × {n}: speech transcription is not supported; these files will be marked as \"No text\"",
        "media_local_note": "All recognition runs locally on this PC. Nothing is uploaded.",
        "drop_label": "⇩  DRAG & DROP FILES HERE",
        "sec_queue": "Task Queue",
        "queue_empty": "[ Queue is empty ]",
        "btn_add": "＋ Add Files",
        "btn_wechat": "💬 WeChat Files",
        "btn_clear": "Clear List",
        "sec_output": "Output Folder",
        "btn_browse": "Browse…",
        "sec_terminal": "Terminal",
        "status_ready": "[ READY ] Ready",
        "btn_convert": "▶ Start Conversion",
        "btn_converting": "◉ Converting…",
        "btn_stop": "■ Stop",
        "btn_stopping": "◌ Stopping…",
        "log_stop_req": "── Stop requested; ending the conversion process… ──",
        "log_skip_done": "── Skipping {n} file(s) already converted (only new, failed or unfinished files are converted) ──",
        "reconvert_title": "Convert Again",
        "reconvert_msg": "All {n} file(s) in the queue have already been converted.\n\nConvert them all again? If the output folder has not changed, the Markdown files created last time will be overwritten.",
        "reconvert_ok": "Convert All Again",
        "dlg_cancel": "Cancel",
        "btn_open_output": "📂 Open Output Folder",
        "btn_logs": "📄 Log Center",
        "sys_ready": "SYSTEM READY — waiting for tasks",
        "fatal_no_lib": "The markitdown library was not found. Please run the installer again, or use \"Check for Updates\" to repair.",
        "dlg_pick_files": "Select files to convert",
        "dlg_pick_output": "Select output folder",
        "status_queue": "[ QUEUE ] {n} task(s) added",
        "no_log_center": "Log Center (update.pyw) was not found; running in portable mode",
        "open_logs_fail": "Could not open the Log Center: {e}",
        "wait_add_files": "[ WAIT ] Add files to convert first",
        "err_outdir": "[ ERROR ] The output folder is invalid: {e}",
        "err_outdir_notdir": "[ ERROR ] The output path is not a folder",
        "log_task_start": "── Task started: {n} file(s) ──",
        "log_worker_fail": "  ✗ Failed  worker process error",
        "log_worker_crash": "  ✗ Failed  {name}: the conversion process exited unexpectedly (the file may be damaged or malformed)",
        "log_worker_restart": "  ↻ Conversion process restarted; continuing with the remaining {n} file(s)",
        "log_engine_fail": "  ✗ The conversion engine failed to load: {msg}",
        "log_engine_fix": "  ➜ Run \"Check for Updates · Log Center\" from the Start Menu to repair automatically; if it still fails, run the installer again",
        "log_done": "  ✓ Done{tag}  {secs:.2f}s",
        "tag_ocr": " (OCR)",
        "tag_imgs": " (images × {n})",
        "log_empty": "  ⚠ No text content; no file was created ({hint})",
        "log_more": "  … and {n} more file(s) (command echo omitted)",
        "engine_broken": "The conversion engine is unavailable. Run \"Check for Updates · Log Center\" from the Start Menu to repair it; if that fails, run the installer again.",
        "open_output_fail": "Could not open the output folder: {e}",
        "status_run": "[ RUN ] Converting {done} / {total} …",
        "sum_ok": "{n} succeeded",
        "sum_empty": "{n} empty",
        "sum_fail": "{n} failed",
        "sum_stopped": "{n} stopped",
        "sum_join": ", ",
        "status_done": "[ DONE ] All {total} file(s) converted in {secs:.1f}s",
        "log_done_all": "── All done: {total}/{total} in {secs:.1f}s ──",
        "status_warn": "[ WARN ] {summary}, {secs:.1f}s",
        "log_end": "── Task finished: {summary} ──",
        "status_stopped": "[ STOP ] Stopped: {summary}, {secs:.1f}s",
        "log_end_stopped": "── Task stopped: {summary} ──",
        "output_dirname": "Output",
    },
}


def _saved_language() -> str | None:
    """已保存的语言选择：--lang 参数 > language.txt（安装程序写入）> 配置文件。"""
    if "--lang" in sys.argv:
        try:
            v = sys.argv[sys.argv.index("--lang") + 1].strip().lower()
            if v in STRINGS:
                return v
        except IndexError:
            pass
    try:
        v = LANG_FILE.read_text(encoding="utf-8", errors="ignore").strip().lower()
        if v in STRINGS:
            return v
    except OSError:
        pass
    try:
        v = str(json.loads(CONFIG_FILE.read_text(encoding="utf-8")).get("language", "")).lower()
        if v in STRINGS:
            return v
    except Exception:
        pass
    return None


def _ask_language() -> str:
    """便携模式首次运行：启动时询问界面语言（仅此一次，之后记住选择）。"""
    import tkinter as _tk
    root = _tk.Tk()
    root.title("Language / 语言")
    root.resizable(False, False)
    root.configure(bg=C_BG)
    choice = {"v": "zh"}

    def pick(v):
        choice["v"] = v
        root.destroy()

    _tk.Label(root, text="请选择界面语言\nPlease select a language",
              bg=C_BG, fg=C_TEXT, font=("Microsoft YaHei UI", 12),
              justify="center").pack(padx=36, pady=(24, 16))
    row = _tk.Frame(root, bg=C_BG)
    row.pack(pady=(0, 24))
    _tk.Button(row, text="中文", width=10, command=lambda: pick("zh"),
               font=("Microsoft YaHei UI", 11)).pack(side="left", padx=8)
    _tk.Button(row, text="English", width=10, command=lambda: pick("en"),
               font=("Microsoft YaHei UI", 11)).pack(side="left", padx=8)
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    root.geometry(f"+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 3}")
    root.mainloop()
    # 记住选择（配置文件不存在时新建；已有其他设置原样保留）
    cfg = {}
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    if cfg.get("language") != choice["v"]:
        cfg["language"] = choice["v"]
        try:
            CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    return choice["v"]


LANG = _saved_language()
if LANG is None:
    LANG = "zh" if "--worker" in sys.argv else _ask_language()
T = STRINGS[LANG]

STATUS_STYLE = {  # 状态 -> (文字, 颜色)
    "waiting":  (T["st_waiting"], C_DIM),
    "running":  (T["st_running"], C_AMBER),
    "done":     (T["st_done"],    C_GREEN),
    "failed":   (T["st_failed"],  C_RED),
    "empty":    (T["st_empty"],   C_AMBER),
    "stopped":  (T["st_stopped"], C_DIM),
}

# 空内容的解释：markitdown 本地版对图片只提取元数据、对音频需语音识别
EMPTY_HINTS = {
    **{e: T["empty_img"] for e in IMG_EXTS},
    ".pdf": T["empty_pdf"],
    **{e: T["empty_audio"] for e in AUDIO_EXTS},
}
DEFAULT_EMPTY_HINT = T["empty_default"]

SUPPORTED_HINT = T["supported_hint"]

FONT = "Microsoft YaHei UI"
MONO = "Consolas"


def _manual_path() -> Path | None:
    """使用说明书：优先当前语言版本，缺失时退回另一种语言（英文说明书后续随包提供）。"""
    cands = [MANUAL_FILE_EN, MANUAL_FILE] if LANG == "en" else [MANUAL_FILE, MANUAL_FILE_EN]
    for p in cands:
        if p.exists():
            return p
    return None


def lib_available() -> bool:
    """不真正 import（很贵），只探测 markitdown 库是否存在。"""
    try:
        return find_spec("markitdown") is not None
    except Exception:
        return False


def fmt_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def unique_output_path(output_dir: Path, stem: str, reserved: set = frozenset()) -> Path:
    """避免覆盖已有文件或同批次已占用的名字：重名时自动加 (1)、(2)…
    超长文件名自动截断（Windows 默认 260 字符路径上限）。"""
    max_stem = max(20, 240 - len(str(output_dir)))
    if len(stem) > max_stem:
        stem = stem[:max_stem]
    out = output_dir / f"{stem}.md"
    n = 1
    while out.exists() or out in reserved:
        out = output_dir / f"{stem} ({n}).md"
        n += 1
    return out


# ---------------- 微信文件 ----------------
def find_wechat_roots() -> list[Path]:
    """定位微信接收文件的根目录（兼容微信 4.x 和 3.x 结构）。"""
    data_dirs: list[Path] = []
    # 1) 注册表：微信 4.x 安装目录的同级 xwechat_files；3.x 的 FileSavePath
    try:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Tencent\Weixin") as k:
                inst, _ = winreg.QueryValueEx(k, "InstallPath")
                if inst:
                    data_dirs.append(Path(inst).parent / "xwechat_files")
        except OSError:
            pass
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Tencent\WeChat") as k:
                fsp, _ = winreg.QueryValueEx(k, "FileSavePath")
                if fsp and str(fsp).strip():
                    data_dirs.append(Path(fsp))
                    data_dirs.append(Path(fsp) / "WeChat Files")
        except OSError:
            pass
    except ImportError:
        pass
    # 2) 文档目录默认位置
    docs = Path.home() / "Documents"
    data_dirs += [docs / "xwechat_files", docs / "WeChat Files"]
    # 3) 各盘符浅层搜索 xwechat_files（处理自定义数据目录，如 D:\微信\xwechat_files）
    for letter in "CDEFG":
        drive = Path(f"{letter}:/")
        if not drive.exists():
            continue
        try:
            entries = list(drive.iterdir())
        except OSError:
            continue
        for d in entries:
            try:
                if not d.is_dir():
                    continue
                if d.name == "xwechat_files":
                    data_dirs.append(d)
                elif (d / "xwechat_files").is_dir():
                    data_dirs.append(d / "xwechat_files")
            except OSError:
                continue
    # 收集账号下的文件根目录
    roots, seen = [], set()
    for dd in data_dirs:
        try:
            if not dd.is_dir():
                continue
            accounts = list(dd.iterdir())
        except OSError:
            continue
        for acc in accounts:
            if not acc.is_dir() or acc.name in ("all_users", "Backup"):
                continue
            for sub in (acc / "msg" / "file",            # 微信 4.x
                        acc / "FileStorage" / "File"):    # 微信 3.x
                if sub.is_dir() and sub not in seen:
                    seen.add(sub)
                    roots.append(sub)
    return roots


def scan_wechat_files(roots: list[Path], limit: int = 500) -> list[tuple[Path, float, int]]:
    """按月份目录（新->旧）收集文件，返回 [(路径, 修改时间, 大小)]，按时间倒序。
    用 os.scandir：目录项自带类型/ stat 缓存，比 iterdir 省一半系统调用。
    每个 root（微信账号 / 3.x 与 4.x 共存）各自收满 limit 条再合并排序：
    若用全局计数提前停止，第一个账号文件一多就会把其余账号（哪怕有最新收到
    的文件）整个跳过。"""
    items: list[tuple[Path, float, int]] = []
    for root in roots:
        try:
            with os.scandir(root) as it:
                months = sorted((e for e in it if e.is_dir()),
                                key=lambda e: e.name, reverse=True)
        except OSError:
            continue
        got = 0
        for m in months:
            try:
                with os.scandir(m.path) as it:
                    for e in it:
                        if not e.is_file():
                            continue
                        try:
                            st = e.stat()
                            items.append((Path(e.path), st.st_mtime, st.st_size))
                            got += 1
                        except OSError:
                            pass
            except OSError:
                continue
            if got >= limit:   # 本账号最新的 limit 个已收齐，更早的月份不必再扫
                break
    items.sort(key=lambda x: x[1], reverse=True)
    return items[:limit]


# ==================== 工作进程模式 ====================
_ocr_tls = threading.local()   # 每个线程一个 OCR 引擎（见 _get_ocr_engine）
_ocr_broken = False            # 组件缺失 / 系统没有识别语言：记住结论，不再反复尝试
_ocr_max_dim = 0               # OCR 引擎能接受的最大图片边长（Windows 为 10000 像素）


def _ocr_api():
    """返回 (OcrEngine, BitmapDecoder, FileAccessMode, StorageFile)。
    优先 pywinrt（winrt-* 系列包，仍在维护，支持 Python 3.12~3.14）；没有时退回旧版本
    安装留下的 winsdk（已停止维护、只有 3.12 的包，两者 API 相同）。
    只在转换进程里调用：界面进程不导入 winrt（它会初始化 COM 套间，可能影响拖放）。"""
    try:
        from winrt.windows.graphics.imaging import BitmapDecoder
        from winrt.windows.media.ocr import OcrEngine
        from winrt.windows.storage import FileAccessMode, StorageFile
    except ImportError:
        from winsdk.windows.graphics.imaging import BitmapDecoder
        from winsdk.windows.media.ocr import OcrEngine
        from winsdk.windows.storage import FileAccessMode, StorageFile
    return OcrEngine, BitmapDecoder, FileAccessMode, StorageFile


def _get_ocr_engine():
    """取当前线程专用的 Windows OCR 引擎；不可用时返回 None。
    必须每个线程一个：同一个 OcrEngine 不允许并发识别（会抛「Another RecognizeAsync
    operation is already running」）。旧版 4 个转换线程共用一个引擎，同时转多张图片时
    会随机失败、被误报成「无文字」；每线程一个引擎还能真正并行（实测快约 4 倍）。
    识别语言优先跟随 Windows 用户语言（中文系统用中文模型，中英文都能认），
    其次界面语言，最后任一已安装的模型。"""
    global _ocr_broken, _ocr_max_dim
    if _ocr_broken:
        return None
    engine = getattr(_ocr_tls, "engine", None)
    if engine is not None:
        return engine
    try:
        OcrEngine = _ocr_api()[0]
        engine = OcrEngine.try_create_from_user_profile_languages()
        if engine is None:
            langs = list(OcrEngine.available_recognizer_languages)
            preferred = "zh" if LANG == "zh" else "en"
            chosen = next((lg for lg in langs if lg.language_tag.lower().startswith(preferred)),
                          langs[0] if langs else None)
            if chosen is not None:
                engine = OcrEngine.try_create_from_language(chosen)
        if not _ocr_max_dim:
            _ocr_max_dim = int(OcrEngine.max_image_dimension) or 10000
    except Exception:  # noqa: BLE001
        engine = None
    if engine is None:
        _ocr_broken = True
        return None
    _ocr_tls.engine = engine
    return engine


async def _ocr_one(engine, path: str) -> list[str]:
    """识别单张图片，返回原始文本行（协程，供单张/批量复用）。"""
    _, BitmapDecoder, FileAccessMode, StorageFile = _ocr_api()
    f = await StorageFile.get_file_from_path_async(path)
    stream = await f.open_async(FileAccessMode.READ)
    try:
        dec = await BitmapDecoder.create_async(stream)
        bmp = await dec.get_software_bitmap_async()
        result = await engine.recognize_async(bmp)
        return [ln.text for ln in result.lines]
    finally:
        try:
            stream.close()   # 及时释放文件句柄，临时图片才能马上删掉
        except Exception:  # noqa: BLE001
            pass


def _clean_ocr_lines(lines) -> str:
    # Windows OCR 会在每个汉字之间塞空格，清掉非 ASCII 字符之间的空格
    cleaned = [re.sub(r"(?<=[^\x00-\x7F])\s+(?=[^\x00-\x7F])", "", ln) for ln in lines]
    return "\n".join(ln for ln in cleaned if ln.strip())


def _ocr_images(paths: list[str]) -> list[str | None]:
    """批量识别（共用一个事件循环），逐张容错：识别不到文字返回 ''，
    图片解码/识别出错返回 None（调用方据此换种方式重试）。"""
    import asyncio

    engine = _get_ocr_engine()
    if engine is None or not paths:
        return [None] * len(paths)

    async def _run():
        out = []
        for p in paths:
            try:
                out.append(_clean_ocr_lines(await _ocr_one(engine, p)))
            except Exception:  # noqa: BLE001
                out.append(None)
        return out

    try:
        return asyncio.run(_run())
    except Exception:  # noqa: BLE001
        return [None] * len(paths)


def _quiet_row(gray, lo: int, hi: int) -> int:
    """在 [lo, hi) 内找最「平」的一行像素（标准差最小，即两行字之间的空白）作为切点，
    尽量不把一行字拦腰截断。从下往上找，遇到纯色行立即采用（切得越靠下段数越少）。"""
    from PIL import ImageStat
    best_y, best_sd = hi, None
    for y in range(hi - 1, lo - 1, -1):
        sd = ImageStat.Stat(gray.crop((0, y, gray.width, y + 1))).stddev[0]
        if best_sd is None or sd < best_sd:
            best_y, best_sd = y, sd
            if sd == 0:
                break
    return best_y


def _prepare_ocr_images(path: str, tmpdir: str) -> list[str]:
    """把一张图片整理成可以直接交给 Windows OCR 的一张或几张图：
    - 普通图片：原样返回，不做任何转换（最常见、最快）；
    - 带 EXIF 旋转信息的照片：先摆正（Windows 解码器不处理方向，横躺的字认不出）；
    - 超过 OCR 尺寸上限（10000 像素）的长图（微信长截图很常见，旧版直接识别失败）：
      在两行字之间的空白处切成几段分别识别，再按顺序拼接；过宽的图等比缩小。"""
    from PIL import Image, ImageOps
    max_dim = _ocr_max_dim or 10000
    with Image.open(path) as src:
        try:
            orient = src.getexif().get(0x0112, 1)
        except Exception:  # noqa: BLE001
            orient = 1
        if orient in (None, 1) and max(src.size) <= max_dim:
            return [path]
        im = ImageOps.exif_transpose(src) if orient not in (None, 1) else src
        im = im.convert("RGB")
    w, h = im.size
    if w > max_dim:
        h, w = max(1, h * max_dim // w), max_dim
        im = im.resize((w, h))
    gray = im.convert("L") if h > max_dim else None
    out, top = [], 0
    while top < h:
        bottom = min(h, top + max_dim)
        if bottom < h:
            bottom = _quiet_row(gray, max(top + max_dim // 2, bottom - 800), bottom)
        part = os.path.join(tmpdir, f"part{len(out)}.bmp")
        im.crop((0, top, w, bottom)).save(part)
        out.append(part)
        top = bottom
    return out


def _ocr_image(path: str) -> str:
    """用 Windows 本地 OCR 识别图片文字，返回清理后的多行文本。失败返回 ''。"""
    if _get_ocr_engine() is None:
        return ""
    import shutil
    import tempfile

    tmp = tempfile.mkdtemp(prefix="mid_ocr_")
    try:
        try:
            parts = _prepare_ocr_images(path, tmp)
        except Exception:  # noqa: BLE001  PIL 打不开的格式：直接交给 Windows 解码器
            parts = [path]
        texts = _ocr_images(parts)
        if parts == [path] and texts[0] is None:
            # Windows 解码器不认（如没装「WebP 图像扩展」时的 .webp）：PIL 转成 BMP 再试一次
            try:
                from PIL import Image
                alt = os.path.join(tmp, "converted.bmp")
                with Image.open(path) as im:
                    im.convert("RGB").save(alt)
                texts = _ocr_images([alt])
            except Exception:  # noqa: BLE001
                pass
        return "\n".join(t for t in texts if t)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_pdfium_lock = threading.Lock()   # pdfium 非线程安全：所有渲染调用串行化


def _ocr_pdf(path: str, max_pages: int = 30) -> str:
    """图片型（扫描件）PDF 兜底：逐页渲染成图片，再用 Windows OCR 识别文字。
    无 OCR 引擎、未安装 pypdfium2 或所有页都识别不到文字时返回 ''
    （交给上层按「无文字」上报，而不是生成一份全是「未识别到文字」占位的 md）。

    逐页「渲染 → 识别 → 删图」：pdfium 锁只在渲染单页时持有，其他线程的 PDF
    可以在本线程 OCR 期间渲染；临时图用 BMP（存盘比 PNG 快约 18 倍，且
    Windows 解码器原生支持），每个线程同一时刻只占一页的临时空间。"""
    if _get_ocr_engine() is None:
        return ""
    try:
        import pypdfium2 as pdfium
    except Exception:
        return ""
    import shutil
    import tempfile

    tmp = tempfile.mkdtemp(prefix="mid_pdfocr_")
    pdf = None
    try:
        with _pdfium_lock:        # pdfium 非线程安全：所有调用串行化
            pdf = pdfium.PdfDocument(path)
            n_total = len(pdf)
        parts = []
        any_text = False
        for i in range(min(n_total, max_pages)):
            img = os.path.join(tmp, f"p{i}.bmp")
            try:
                with _pdfium_lock:
                    page = pdf[i]
                    try:
                        page.render(scale=2.78).to_pil().save(img)   # ≈200 DPI
                    finally:
                        page.close()
                t = _ocr_image(img)
            except Exception:
                t = ""            # 单页渲染失败不拖垮整份 PDF 的 OCR
            try:
                os.remove(img)
            except OSError:
                pass              # 句柄未释放时留给最后的 rmtree
            if t.strip():
                any_text = True
                parts.append(t)
            else:
                parts.append(T["ocr_page_empty"].format(n=i + 1))
        if not any_text:
            return ""
        if n_total > max_pages:
            parts.append(T["ocr_page_limit"].format(n=max_pages))
        return "\n\n".join(parts)
    except Exception:
        return ""
    finally:
        if pdf is not None:
            with _pdfium_lock:
                try:
                    pdf.close()
                except Exception:
                    pass
        shutil.rmtree(tmp, ignore_errors=True)


# base64 段用贪婪匹配：字符集不含 ')'，与惰性匹配结果完全相同，但对 MB 级
# 内嵌图片快约 7 倍（惰性匹配每吃一个字符都要回头试一次 ')'）
_IMG_DATA_URI_RE = re.compile(r"!\[([^\]]*)\]\(data:([^;\s]+);base64,([A-Za-z0-9+/=\s]+)\)")
_IMG_MIME_EXT = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg",
    "image/gif": ".gif", "image/webp": ".webp", "image/svg+xml": ".svg",
    "image/bmp": ".bmp", "image/tiff": ".tif", "image/x-icon": ".ico",
}


def _sniff_img_ext(blob: bytes) -> str:
    """MIME 缺失时按文件头魔数判断图片格式。"""
    if blob.startswith(b"\x89PNG"):
        return ".png"
    if blob.startswith(b"\xff\xd8"):
        return ".jpg"
    if blob.startswith(b"GIF8"):
        return ".gif"
    if blob.startswith(b"RIFF") and blob[8:12] == b"WEBP":
        return ".webp"
    if blob.startswith(b"BM"):
        return ".bmp"
    if blob.lstrip()[:1] == b"<":
        return ".svg"
    return ".png"


def _extract_embedded_images(text: str, md_path: Path):
    """把转换结果里 data URI 形式的内嵌图片落盘到 <文件名>.assets/ 目录，
    md 中替换为相对路径引用（Typora / VSCode / Obsidian 可直接预览）。
    返回 (新文本, 提取出的图片数)；无法写盘时降级为仅保留 alt 引用。"""
    if "data:image" not in text:
        return text, 0
    matches = list(_IMG_DATA_URI_RE.finditer(text))
    if not matches:
        return text, 0
    import base64
    import hashlib
    from urllib.parse import quote

    assets_dir = md_path.parent / f"{md_path.stem}.assets"
    writable = True
    try:
        assets_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        writable = False
    seen: dict = {}        # 内容哈希 -> 相对路径（同一张图多处引用只存一份）
    counter = 0

    def _sub(m):
        nonlocal counter, writable
        alt, mime, b64 = m.group(1), m.group(2).lower(), m.group(3)
        # alt 净化：来自 PPT 作者机器的绝对路径只保留文件名（避免泄露隐私、
        # 防止超长）；$ 换成全角，避免被 Typora 等当成行内公式定界符
        alt = alt.strip()
        if re.match(r"^([A-Za-z]:[\\/]|\\\\)", alt):
            alt = alt.replace("\\", "/").rsplit("/", 1)[-1].strip() or T["alt_img"]
        alt = alt.replace("$", "＄")
        if not writable:
            return f"![{alt}]"
        try:
            blob = base64.b64decode(re.sub(r"\s", "", b64), validate=False)
        except Exception:
            return f"![{alt}]"
        h = hashlib.sha1(blob).hexdigest()
        if h not in seen:
            counter += 1
            ext = _IMG_MIME_EXT.get(mime) or _sniff_img_ext(blob)
            fname = f"img{counter:02d}{ext}"
            try:
                (assets_dir / fname).write_bytes(blob)
            except OSError:
                writable = False
                return f"![{alt}]"
            # 文件名/文件夹可能含空格、括号、#、% 等字符：URL 编码后才是合法的
            # CommonMark 链接目标，否则各 Markdown 阅读器解析失败、图片不显示。
            # 括号也要编码：文件名里不成对的括号（如「方案(草稿.docx」）会截断链接
            seen[h] = quote(f"{assets_dir.name}/{fname}", safe="/!$&'*+,;=:@~-._")
        return f"![{alt}]({seen[h]})"

    return _IMG_DATA_URI_RE.sub(_sub, text), counter


def _run_worker() -> int:
    """常驻子进程：循环从 stdin 读一批任务（JSON 行），转换并把进度以 JSON 行写回 stdout。
    转换在独立进程中进行，即使大文件占满 CPU，界面进程也丝毫不受影响。"""
    from concurrent.futures import ThreadPoolExecutor, wait

    # 进度协议独占真实 stdout；第三方库的 print() 改道到 stderr（界面接的是 DEVNULL）。
    # 否则一行杂散输出就可能和进度 JSON 挤在同一行，该文件的结果随之丢失
    proto = sys.stdout
    sys.stdout = sys.stderr if sys.stderr is not None else open(os.devnull, "w")

    try:
        from markitdown import MarkItDown   # 先加载引擎（预热的关键），再等任务
        engines: queue.SimpleQueue = queue.SimpleQueue()   # 引擎池：跨批次复用
        engines.put(MarkItDown())           # 预热阶段就建好第一个引擎
    except Exception as e:  # noqa: BLE001
        # 引擎加载失败（如缺少 VC++ 运行库 / 组件损坏）：把真实原因上报给界面再退出
        proto.write(json.dumps({"event": "engine_error", "msg": str(e)[:300]}) + "\n")
        proto.flush()
        return 1

    lock = threading.Lock()

    def report(d: dict):
        with lock:
            proto.write(json.dumps(d) + "\n")   # 纯 ASCII，无编码问题
            proto.flush()

    def work(i: int, src: str, dst: str):
        report({"i": i, "event": "start"})
        t0 = time.time()
        try:
            ext_lower = os.path.splitext(src)[1].lower()
            if ext_lower in AUDIO_EXTS:
                # 本地版不含语音转写组件：不调用转换引擎（markitdown 的 wav 识别
                # 会把音频上传到 Google，mp3/m4a 依赖安装包没有的 ffmpeg，
                # 与界面「全部本地完成」的承诺冲突），直接按「无文字」上报
                report({"i": i, "event": "empty", "secs": round(time.time() - t0, 2)})
                return
            try:
                engine = engines.get_nowait()   # 每个引擎同一时刻只给一个线程用
            except queue.Empty:
                engine = MarkItDown()
            try:
                if ext_lower in EMBED_IMG_EXTS:
                    # PPT 等文档里的图片：让 markitdown 以 data URI 带出，
                    # 再落盘为 <文件名>.assets/ 图片文件并在 md 中相对引用
                    result = engine.convert(src, keep_data_uris=True)
                else:
                    result = engine.convert(src)
                text = result.text_content or ""
            except Exception:
                if ext_lower not in IMG_EXTS:
                    raise
                # markitdown 只接受 jpg/png；gif/bmp/webp/tif 等直接抛
                # UnsupportedFormatException —— 不判失败，落入下方 Windows OCR 兜底
                text = ""
            finally:
                engines.put(engine)
            used_ocr = False
            n_imgs = 0
            if text.strip() and ext_lower in EMBED_IMG_EXTS:
                text, n_imgs = _extract_embedded_images(text, Path(dst))
            if not text.strip() and ext_lower in IMG_EXTS:
                # markitdown 对图片只能提取元数据 → 用 Windows OCR 兜底识别图中文字
                ocr_text = _ocr_image(src)
                if ocr_text.strip():
                    text = (f"# {os.path.basename(src)} {T['ocr_img_title']}\n\n"
                            f"> {T['ocr_img_note']}\n\n" + ocr_text + "\n")
                    used_ocr = True
            elif not text.strip() and ext_lower == ".pdf":
                # 图片型/扫描件 PDF 没有文字层 → 逐页渲染后走 Windows OCR
                ocr_text = _ocr_pdf(src)
                if ocr_text.strip():
                    text = (f"# {os.path.basename(src)} {T['ocr_pdf_title']}\n\n"
                            f"> {T['ocr_pdf_note']}\n\n"
                            + ocr_text + "\n")
                    used_ocr = True
            if not text.strip():
                # 提取结果为空：不落盘 0 字节文件，单独上报
                report({"i": i, "event": "empty", "secs": round(time.time() - t0, 2)})
            else:
                # 先写 .part 再整体改名：中途被「停止」或崩溃时不会留下写了一半的 md，
                # 「重新转换」覆盖旧文件时也不会出现半新半旧的内容
                part = dst + ".part"
                try:
                    Path(part).write_text(text, encoding="utf-8")
                    os.replace(part, dst)
                except BaseException:
                    try:
                        os.remove(part)
                    except OSError:
                        pass
                    raise
                report({"i": i, "event": "done", "secs": round(time.time() - t0, 2),
                        "ocr": used_ocr, "imgs": n_imgs})
        except Exception as e:  # noqa: BLE001
            report({"i": i, "event": "fail", "msg": str(e)[:200]})

    # 线程池常驻：一批接一批，不用每批重新加载引擎、重建线程
    pool = ThreadPoolExecutor(max_workers=WORKER_PARALLEL)
    while True:
        line = sys.stdin.readline()
        if not line:
            return 0
        line = line.strip()
        if not line:
            continue
        try:
            jobs = [(str(src), str(dst)) for src, dst in json.loads(line)]
        except (ValueError, TypeError):
            report({"event": "all_done"})   # 坏批次也要收尾，界面才不会一直等
            continue
        wait([pool.submit(work, i, src, dst) for i, (src, dst) in enumerate(jobs)])
        report({"event": "all_done"})


if "--worker" in sys.argv:
    sys.exit(_run_worker())


# ==================== 图形界面 ====================
import tkinter as tk

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class WorkerManager:
    """管理常驻转换子进程：预热即启动并加载好引擎，之后所有批次复用同一进程。"""

    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def _spawn(self) -> subprocess.Popen:
        return subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--worker", "--lang", LANG],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def prewarm(self):
        self.get()

    def get(self) -> subprocess.Popen:
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                self._proc = self._spawn()
            return self._proc

    def kill(self):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                try:
                    self._proc.kill()
                except OSError:
                    pass
            self._proc = None


class FileRow(tk.Frame):
    """任务队列一行：轻量 tk 控件。由 FileList 复用，滚动时换成别的文件显示。"""

    def __init__(self, master, on_remove):
        super().__init__(master, bg=C_CARD, highlightbackground=C_BORDER,
                         highlightthickness=1, bd=0)
        self.path: Path | None = None
        self._status: str | None = None

        tk.Label(self, text="▸", bg=C_CARD, fg=C_CYAN,
                 font=(MONO, 11)).pack(side="left", padx=(10, 2))
        self.name_label = tk.Label(self, text="", anchor="w", bg=C_CARD,
                                   fg=C_TEXT, font=(FONT, 10))
        self.name_label.pack(side="left", fill="x", expand=True)

        self.remove_btn = tk.Label(self, text="✕", bg=C_CARD, fg=C_DIM,
                                   font=(FONT, 11), cursor="hand2", padx=8)
        self.remove_btn.pack(side="right", padx=(2, 6), pady=7)
        self.remove_btn.bind("<Button-1>", lambda e: on_remove(self))
        self.remove_btn.bind("<Enter>", lambda e: self.remove_btn.configure(fg=C_RED))
        self.remove_btn.bind("<Leave>", lambda e: self.remove_btn.configure(fg=C_DIM))

        self.status_label = tk.Label(self, text="", width=10, bg=C_CARD, font=(FONT, 10))
        self.status_label.pack(side="right", padx=6)

    def show(self, path: Path, status: str):
        if path != self.path:
            self.path = path
            self.name_label.configure(text=path.name)
        self.set_status(status)

    def set_status(self, status: str):
        if status == self._status:   # 没变就不发 Tk 调用
            return
        self._status = status
        text, color = STATUS_STYLE[status]
        self.status_label.configure(text=text, fg=color)


class FileList(ctk.CTkFrame):
    """任务队列（虚拟列表）：只为可见区域建十几行控件，滚动时复用它们换内容。

    Windows 上每个 Tk 控件都是一个原生子窗口，控件越多每次布局/重绘越慢。
    旧版每个文件建一整行控件（5 个原生窗口），实测 2000 个文件要 37 秒才渲染完，
    期间界面持续卡顿、越往后越慢，且 grid 行号上限 9998，上万个文件直接报错。
    虚拟列表下上万个文件也是瞬间加入，增删、清空、更新状态都只动可见的那十几行。"""

    def __init__(self, master, files: list, status: dict, on_remove):
        super().__init__(master, fg_color=C_PANEL, corner_radius=10)
        self.files = files      # 与 App.files 是同一个列表（由 App 增删）
        self.status = status    # 与 App._row_status 是同一个字典
        self.on_remove = on_remove
        self.first = 0          # 可见区第一行对应的文件序号
        self.row_h = 0          # 行高（含行间距），首次显示时按实际字体测量
        self.pool: list[FileRow] = []
        self.visible: dict[Path, FileRow] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.body = tk.Frame(self, bg=C_PANEL, bd=0, highlightthickness=0)
        self.body.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        self.scrollbar = ctk.CTkScrollbar(self, command=self._on_scrollbar,
                                          button_color=C_BORDER, button_hover_color=C_CYAN_D)
        self.scrollbar.grid(row=0, column=1, sticky="ns", padx=(2, 4), pady=8)
        self.empty_label = tk.Label(self.body, text=T["queue_empty"], bg=C_PANEL,
                                    fg=C_DIM, font=(MONO, 12))
        self.body.bind("<Configure>", lambda e: self.refresh())
        for w in (self.body, self.empty_label):
            w.bind("<MouseWheel>", self._on_wheel)

    def _grow_pool(self, n: int):
        while len(self.pool) < n:
            row = FileRow(self.body, lambda r: r.path is not None and self.on_remove(r.path))
            for w in (row, *row.winfo_children()):
                w.bind("<MouseWheel>", self._on_wheel)
            self.pool.append(row)

    def refresh(self):
        """按当前滚动位置把可见的文件填进复用行。"""
        n = len(self.files)
        self.visible.clear()
        if n == 0:
            for row in self.pool:
                row.place_forget()
            self.first = 0
            self.empty_label.place(relx=0.5, y=18, anchor="n")
            self.scrollbar.set(0.0, 1.0)
            return
        self.empty_label.place_forget()
        if not self.row_h:
            self._grow_pool(1)
            self.pool[0].update_idletasks()
            self.row_h = self.pool[0].winfo_reqheight() + 6
        h = max(self.body.winfo_height(), self.row_h)
        full = max(1, h // self.row_h)              # 完整可见的行数
        self.first = max(0, min(self.first, n - full))
        cap = full + 1                              # 多一行显示底部的半行
        self._grow_pool(min(cap, n))
        for k, row in enumerate(self.pool):
            idx = self.first + k
            if k < cap and idx < n:
                p = self.files[idx]
                row.show(p, self.status.get(p, "waiting"))
                row.place(x=2, y=k * self.row_h + 3, relwidth=1, width=-4,
                          height=self.row_h - 6)
                self.visible[p] = row
            else:
                row.place_forget()
        self.scrollbar.set(self.first / n, min(1.0, (self.first + h / self.row_h) / n))

    def set_status(self, path: Path, status: str):
        row = self.visible.get(path)
        if row is not None:
            row.set_status(status)

    def _on_scrollbar(self, *args):
        n = len(self.files)
        if not n or not self.row_h:
            return
        if args[0] == "moveto":
            self.first = int(float(args[1]) * n + 0.5)
        elif args[0] == "scroll":
            full = max(1, self.body.winfo_height() // self.row_h)
            self.first += int(args[1]) * (full if args[2] == "pages" else 1)
        self.refresh()

    def _on_wheel(self, event):
        if not event.delta:
            return "break"
        steps = -event.delta / 120 * 3     # 每格滚 3 行；触控板的小增量至少滚 1 行
        self.first += int(steps) if abs(steps) >= 1 else (1 if steps > 0 else -1)
        self.refresh()
        return "break"


class WeChatPicker(ctk.CTkToplevel):
    """微信文件选择器：列出微信聊天收到的文件，勾选后加入转换队列。"""

    PAGE = 120   # 每次渲染的行数上限，避免一次性创建几百个控件卡死界面

    def __init__(self, app: "App"):
        super().__init__(app)
        self.app = app
        self.items: list[tuple[Path, float, int]] = []
        self.vars: dict[Path, tk.BooleanVar] = {}
        self.row_widgets: list = []
        self.render_limit = self.PAGE
        self._render_job = None

        self.title(T["wc_title"])
        self.geometry("680x560")
        self.minsize(560, 460)
        self.configure(fg_color=C_BG)
        self.transient(app)
        if ICON_FILE.exists():
            try:
                self.after(250, lambda: self.iconbitmap(str(ICON_FILE)))
            except Exception:
                pass

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 4))
        ctk.CTkLabel(head, text=T["wc_head"], text_color=C_CYAN,
                     font=ctk.CTkFont(family=MONO, size=17, weight="bold")).pack(side="left")
        ctk.CTkLabel(head, text=" WECHAT INBOX", text_color=C_DIM,
                     font=ctk.CTkFont(family=MONO, size=11)).pack(side="left", pady=(4, 0))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=18, pady=(4, 6))
        bar.grid_columnconfigure(0, weight=1)
        self.filter_var = ctk.StringVar()
        self.filter_var.trace_add("write", self._schedule_render)   # 防抖，打字不卡
        ctk.CTkEntry(bar, textvariable=self.filter_var, placeholder_text=T["wc_search"],
                     font=ctk.CTkFont(family=FONT, size=12),
                     fg_color=C_TERM, border_color=C_BORDER, text_color=C_TEXT,
                     ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._small_btn(bar, T["wc_select_all"], self._select_all).grid(row=0, column=1, padx=(0, 6))
        self._small_btn(bar, T["wc_select_none"], self._select_none).grid(row=0, column=2)

        self.list_frame = ctk.CTkScrollableFrame(
            self, fg_color=C_PANEL, corner_radius=10,
            scrollbar_button_color=C_BORDER, scrollbar_button_hover_color=C_CYAN_D,
        )
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 6))
        self.list_frame.grid_columnconfigure(0, weight=1)
        self.hint_label = ctk.CTkLabel(
            self.list_frame, text=T["wc_scanning"],
            font=ctk.CTkFont(family=MONO, size=12), text_color=C_DIM,
        )
        self.hint_label.grid(row=0, column=0, pady=30)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew", padx=18, pady=(4, 14))
        bottom.grid_columnconfigure(0, weight=1)
        self.count_var = ctk.StringVar(value=T["wc_selected"].format(n=0))
        ctk.CTkLabel(bottom, textvariable=self.count_var,
                     font=ctk.CTkFont(family=MONO, size=12), text_color=C_DIM
                     ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(bottom, text=T["wc_confirm"], height=36, corner_radius=6,
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      fg_color=C_CYAN, hover_color=C_CYAN_H, text_color=C_BG,
                      command=self._confirm).grid(row=0, column=1)

        threading.Thread(target=self._scan, daemon=True).start()

    def _small_btn(self, master, text, cmd):
        return ctk.CTkButton(
            master, text=text, command=cmd, height=30, corner_radius=6,
            font=ctk.CTkFont(family=FONT, size=12),
            fg_color="transparent", hover_color=C_PANEL,
            text_color=C_DIM, border_width=1, border_color=C_BORDER,
        )

    def _scan(self):
        # 先用上次缓存的目录秒开列表，再在后台重新探测一遍：新登录的微信账号、改过的
        # 存储位置都能被发现（旧版只要缓存目录还在就永不重新探测），有变化时自动刷新列表。
        # 注意：配置不在本线程写，随结果经 ui_queue 交回 UI 线程统一保存（防并发写坏 JSON）
        cached = [Path(p) for p in self.app.cfg.get("wechat_roots", [])]
        cached = [p for p in cached if p.is_dir()]
        if cached:
            self.app.ui_queue.put(("wechat_items", self, scan_wechat_files(cached), None))
        roots = cached + [p for p in find_wechat_roots() if p not in cached]
        if roots != cached or not cached:
            self.app.ui_queue.put(("wechat_items", self, scan_wechat_files(roots),
                                   [str(p) for p in roots]))

    def populate(self, items):
        self.items = items
        self.render_limit = self.PAGE
        self._render_sig = None   # 列表内容可能整个换了（后台探测后刷新），必须重绘
        self._render()

    def _filtered(self):
        kw = self.filter_var.get().strip().lower()
        if not kw:
            return self.items
        return [it for it in self.items if kw in it[0].name.lower()]

    def _schedule_render(self, *_):
        if not self.winfo_exists():
            return
        if self._render_job is not None:
            self.after_cancel(self._render_job)
        self._render_job = self.after(220, self._render)

    def _render(self):
        self._render_job = None
        if not self.winfo_exists():      # 防抖定时器可能在窗口关闭后才触发
            return
        sig = (self.filter_var.get(), self.render_limit, len(self.items))
        if sig == getattr(self, "_render_sig", None):
            return   # 输入/分页/列表都没变，跳过一次全量销毁重建（每键一次重建约百毫秒）
        self._render_sig = sig
        for w in self.row_widgets:
            w.destroy()
        self.row_widgets.clear()
        if not self.items:
            self.hint_label.configure(text=T["wc_none_found"])
            self.hint_label.grid(row=0, column=0, pady=30)
            self._update_count()
            return
        self.hint_label.grid_remove()
        filtered = self._filtered()
        shown = 0
        for p, mtime, size in filtered:
            if shown >= self.render_limit:
                remain = len(filtered) - shown
                more = tk.Label(
                    self.list_frame, cursor="hand2",
                    text=T["wc_load_more"].format(n=remain),
                    bg=C_PANEL, fg=C_CYAN, font=(FONT, 10), pady=6,
                )
                more.grid(row=shown, column=0, pady=4)
                more.bind("<Button-1>", lambda e: self._load_more())
                self.row_widgets.append(more)
                break
            var = self.vars.get(p)
            if var is None:
                var = tk.BooleanVar(value=False)
                self.vars[p] = var
            row = tk.Frame(self.list_frame, bg=C_CARD,
                           highlightbackground=C_BORDER, highlightthickness=1, bd=0)
            row.grid(row=shown, column=0, sticky="ew", pady=2, padx=2)
            cb = tk.Checkbutton(
                row, variable=var, bg=C_CARD, activebackground=C_CARD,
                selectcolor=C_BG, fg=C_CYAN, activeforeground=C_CYAN,
                bd=0, highlightthickness=0, command=self._update_count,
            )
            cb.pack(side="left", padx=(6, 0))
            meta = time.strftime("%m-%d %H:%M", time.localtime(mtime)) + f" · {fmt_size(size)}"
            meta_lbl = tk.Label(row, text=meta, bg=C_CARD, fg=C_DIM, font=(MONO, 9))
            meta_lbl.pack(side="right", padx=(4, 10))
            name_lbl = tk.Label(row, text=p.name, anchor="w", bg=C_CARD,
                                fg=C_TEXT, font=(FONT, 10))
            name_lbl.pack(side="left", fill="x", expand=True, pady=6)
            for w in (row, name_lbl, meta_lbl):
                w.bind("<Button-1>", lambda e, c=cb: c.invoke())
            self.row_widgets.append(row)
            shown += 1
        if shown == 0:
            lbl = tk.Label(self.list_frame, text=T["wc_no_match"].format(kw=self.filter_var.get()),
                           bg=C_PANEL, fg=C_DIM, font=(FONT, 10))
            lbl.grid(row=0, column=0, pady=20)
            self.row_widgets.append(lbl)
        self._update_count()

    def _load_more(self):
        self.render_limit += self.PAGE
        self._render()

    def _update_count(self):
        n = sum(1 for v in self.vars.values() if v.get())
        self.count_var.set(T["wc_selected"].format(n=n))

    def _select_all(self):
        for p, _, _ in self._filtered():
            v = self.vars.get(p)
            if v is None:
                v = tk.BooleanVar(value=False)
                self.vars[p] = v
            v.set(True)
        self._update_count()

    def _select_none(self):
        for v in self.vars.values():
            v.set(False)
        self._update_count()

    def _confirm(self):
        selected = [p for p, v in self.vars.items() if v.get() and p.exists()]
        if selected:
            self.app.add_files(selected)
            self.app._log(T["wc_log_added"].format(n=len(selected)), "sys")
        self.app.picker = None
        self.destroy()


class NoticeDialog(ctk.CTkToplevel):
    """模态提示弹窗：添加图片/音频类文件时告知处理方式。"""

    def __init__(self, app: "App", title: str, message: str, dont_show_key: str | None = None):
        super().__init__(app)
        self.app = app
        self.dont_show_key = dont_show_key

        self.title(title)
        self.configure(fg_color=C_BG)
        self.resizable(False, False)
        self.transient(app)
        if ICON_FILE.exists():
            try:
                self.after(250, lambda: self.iconbitmap(str(ICON_FILE)))
            except Exception:
                pass

        ctk.CTkLabel(self, text=T["notice_head"], text_color=C_CYAN,
                     font=ctk.CTkFont(family=MONO, size=15, weight="bold"),
                     ).pack(anchor="w", padx=20, pady=(18, 8))
        ctk.CTkLabel(self, text=message, justify="left", anchor="w",
                     font=ctk.CTkFont(family=FONT, size=13), text_color=C_TEXT,
                     wraplength=420,
                     ).pack(anchor="w", padx=20, fill="x")

        self.dont_show_var = ctk.BooleanVar(value=False)
        if dont_show_key:
            ctk.CTkCheckBox(self, text=T["notice_dont_show"], variable=self.dont_show_var,
                            font=ctk.CTkFont(family=FONT, size=12), text_color=C_DIM,
                            fg_color=C_CYAN, hover_color=C_CYAN_H, border_color=C_BORDER,
                            ).pack(anchor="w", padx=20, pady=(12, 0))

        ctk.CTkButton(self, text=T["notice_ok"], height=36, corner_radius=6, width=140,
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      fg_color=C_CYAN, hover_color=C_CYAN_H, text_color=C_BG,
                      command=self._close).pack(pady=(14, 18))

        self.update_idletasks()
        # 居中于主窗口
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + (app.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.grab_set()          # 模态
        self.focus()

    def _close(self):
        if self.dont_show_key and self.dont_show_var.get():
            self.app.cfg[self.dont_show_key] = True
            self.app._save_config()
        self.destroy()


class ConfirmDialog(ctk.CTkToplevel):
    """深色风格的确认弹窗（模态）。用户点确认按钮后 result 为 True。"""

    def __init__(self, app: "App", title: str, message: str, ok_text: str):
        super().__init__(app)
        self.result = False

        self.title(title)
        self.configure(fg_color=C_BG)
        self.resizable(False, False)
        self.transient(app)
        if ICON_FILE.exists():
            try:
                self.after(250, lambda: self.iconbitmap(str(ICON_FILE)))
            except Exception:
                pass

        ctk.CTkLabel(self, text=T["notice_head"], text_color=C_CYAN,
                     font=ctk.CTkFont(family=MONO, size=15, weight="bold"),
                     ).pack(anchor="w", padx=20, pady=(18, 8))
        ctk.CTkLabel(self, text=message, justify="left", anchor="w",
                     font=ctk.CTkFont(family=FONT, size=13), text_color=C_TEXT,
                     wraplength=420,
                     ).pack(anchor="w", padx=20, fill="x")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=(16, 18))
        ctk.CTkButton(row, text=ok_text, height=36, corner_radius=6, width=150,
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      fg_color=C_CYAN, hover_color=C_CYAN_H, text_color=C_BG,
                      command=self._ok).pack(side="left", padx=6)
        ctk.CTkButton(row, text=T["dlg_cancel"], height=36, corner_radius=6, width=110,
                      font=ctk.CTkFont(family=FONT, size=13),
                      fg_color="transparent", hover_color=C_PANEL, text_color=C_DIM,
                      border_width=1, border_color=C_BORDER,
                      command=self.destroy).pack(side="left", padx=6)

        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + (app.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.grab_set()          # 模态
        self.focus()

    def _ok(self):
        self.result = True
        self.destroy()


class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        # 注意不能叫 self.config：那会覆盖 Tk 自带的 config() 方法
        self.cfg = self._load_config()
        self._config_lock = threading.Lock()
        self.files: list[Path] = []
        self._file_set: set[Path] = set()   # O(1) 去重（大批量添加时避免对 list 做线性扫描）
        self._row_status: dict[Path, str] = {}   # 每个文件的最新状态（虚拟列表据此显示）
        self.ui_queue: queue.Queue = queue.Queue()
        self.converting = False
        self._closed = False          # 关窗后禁止再预热/启动 worker，杜绝孤儿进程
        self._engine_broken = False   # 引擎加载失败后不再反复预热注定失败的新进程
        self.picker: WeChatPicker | None = None
        self.worker_man = WorkerManager()
        self._active_procs: set = set()
        self._stop_requested = False  # 用户点了「停止转换」
        self._outputs: dict[Path, Path] = {}   # 源文件 -> 上次生成的 md（「全部重新转换」时原地覆盖）

        self.title(T["app_title"])
        self.geometry("700x760")
        self.minsize(600, 660)
        self.configure(fg_color=C_BG)
        if ICON_FILE.exists():
            try:
                self.after(200, lambda: self.iconbitmap(str(ICON_FILE)))
            except Exception:
                pass

        self._build_ui()
        self._poll_queue()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        # 延迟预热转换进程：界面先出来，后台进程再悄悄加载 markitdown 引擎
        self._prewarm_timer = threading.Timer(0.6, self._prewarm)
        self._prewarm_timer.daemon = True
        self._prewarm_timer.start()
        self._log(T["sys_ready"], "sys")
        self._maybe_open_manual()
        if not lib_available():
            self._fatal(T["fatal_no_lib"])

    def _maybe_open_manual(self):
        """首次运行时自动打开使用说明书（只此一次，之后可在安装目录手动查看）。"""
        if self.cfg.get("manual_shown"):
            return
        manual = _manual_path()
        if manual is None:
            return
        self.cfg["manual_shown"] = True
        self._save_config()
        try:
            os.startfile(manual)  # noqa: S606
        except OSError:
            pass

    # ---------- 配置读写 ----------
    def _prewarm(self):
        """预热 worker：窗口已关或引擎已坏时不再启动新进程。"""
        if not self._closed and not self._engine_broken:
            self.worker_man.prewarm()

    def _load_config(self) -> dict:
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_config(self):
        try:
            with self._config_lock:
                CONFIG_FILE.write_text(
                    json.dumps(self.cfg, ensure_ascii=False, indent=2), encoding="utf-8"
                )
        except Exception:
            pass

    def _on_close(self):
        self._closed = True
        try:
            self._prewarm_timer.cancel()
        except Exception:
            pass
        for p in list(self._active_procs):
            try:
                if p.poll() is None:
                    p.kill()
            except OSError:
                pass
        self.worker_man.kill()
        self.destroy()

    # ---------- 界面 ----------
    def _section(self, text: str, row: int):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.grid(row=row, column=0, sticky="w", padx=22, pady=(10, 2))
        ctk.CTkLabel(f, text="//", font=ctk.CTkFont(family=MONO, size=12, weight="bold"),
                     text_color=C_CYAN).pack(side="left")
        ctk.CTkLabel(f, text=f" {text}", font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
                     text_color=C_DIM).pack(side="left")

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # ── 标题区 ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 4))
        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(anchor="w")
        ctk.CTkLabel(title_row, text="◢ ", text_color=C_CYAN,
                     font=ctk.CTkFont(family=MONO, size=20, weight="bold")).pack(side="left")
        ctk.CTkLabel(title_row, text="MARKITDOWN", text_color=C_TEXT,
                     font=ctk.CTkFont(family=MONO, size=20, weight="bold")).pack(side="left")
        ctk.CTkLabel(title_row, text=T["title_suffix"], text_color=C_PURPLE,
                     font=ctk.CTkFont(family=FONT, size=20, weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text=f"{T['supported_label']}  [ {SUPPORTED_HINT} ]",
                     font=ctk.CTkFont(family=FONT, size=11), text_color=C_DIM
                     ).pack(anchor="w", pady=(3, 0))

        # ── 拖拽区 ──
        self.drop_frame = ctk.CTkFrame(self, fg_color=C_PANEL, corner_radius=10,
                                       border_width=2, border_color=C_CYAN_D)
        self.drop_frame.grid(row=1, column=0, sticky="ew", padx=22, pady=8)
        self.drop_label = ctk.CTkLabel(
            self.drop_frame, text=T["drop_label"],
            font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
            text_color=C_CYAN, pady=20,
        )
        self.drop_label.pack(expand=True, fill="both")
        for widget in (self.drop_frame, self.drop_label):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop)
            widget.dnd_bind("<<DragEnter>>", lambda e: self._drop_hover(True))
            widget.dnd_bind("<<DragLeave>>", lambda e: self._drop_hover(False))

        # ── 任务队列 ──
        self._section(T["sec_queue"], 2)
        self.queue_view = FileList(self, self.files, self._row_status, self._remove_path)
        self.queue_view.grid(row=3, column=0, sticky="nsew", padx=22, pady=(0, 6))

        # ── 按钮行 ──
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=4, column=0, sticky="ew", padx=22)
        self._btn(btns, T["btn_add"], self._pick_files, accent=True).pack(side="left")
        self._btn(btns, T["btn_wechat"], self._open_wechat, accent=True).pack(side="left", padx=8)
        self._btn(btns, T["btn_clear"], self._clear_files).pack(side="left")

        # ── 输出目录 ──
        self._section(T["sec_output"], 5)
        out_row = ctk.CTkFrame(self, fg_color="transparent")
        out_row.grid(row=6, column=0, sticky="ew", padx=22)
        out_row.grid_columnconfigure(0, weight=1)
        default_out = self.cfg.get("output_dir") or str(SCRIPT_DIR / T["output_dirname"])
        self.out_var = ctk.StringVar(value=default_out)
        self.out_entry = ctk.CTkEntry(
            out_row, textvariable=self.out_var,
            font=ctk.CTkFont(family=MONO, size=12),
            fg_color=C_TERM, border_color=C_BORDER, text_color=C_CYAN,
        )
        self.out_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._btn(out_row, T["btn_browse"], self._pick_output_dir).grid(row=0, column=1)

        # ── 执行终端 ──
        self._section(T["sec_terminal"], 7)
        self.term = ctk.CTkTextbox(
            self, height=110, fg_color=C_TERM, corner_radius=8,
            border_width=1, border_color=C_BORDER,
            font=ctk.CTkFont(family=MONO, size=11), text_color=C_TEXT,
            state="disabled", wrap="none",
        )
        self.term.grid(row=8, column=0, sticky="ew", padx=22)
        self.term._textbox.tag_config("cmd", foreground=C_CYAN)
        self.term._textbox.tag_config("ok", foreground=C_GREEN)
        self.term._textbox.tag_config("err", foreground=C_RED)
        self.term._textbox.tag_config("warn", foreground=C_AMBER)
        self.term._textbox.tag_config("sys", foreground=C_PURPLE)
        self.term._textbox.tag_config("dim", foreground=C_DIM)

        # ── 进度条 + 状态 ──
        self.progress = ctk.CTkProgressBar(self, height=6, fg_color=C_PANEL,
                                           progress_color=C_CYAN, corner_radius=3)
        self.progress.grid(row=9, column=0, sticky="ew", padx=22, pady=(12, 0))
        self.progress.set(0)

        self.status_var = ctk.StringVar(value=T["status_ready"])
        ctk.CTkLabel(self, textvariable=self.status_var,
                     font=ctk.CTkFont(family=MONO, size=12), text_color=C_DIM
                     ).grid(row=10, column=0, sticky="w", padx=24, pady=(4, 0))

        # ── 转换按钮 ──
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=11, column=0, sticky="ew", padx=22, pady=(8, 16))
        bottom.grid_columnconfigure(0, weight=1)
        self.convert_btn = ctk.CTkButton(
            bottom, text=T["btn_convert"], height=44,
            font=ctk.CTkFont(family=FONT, size=15, weight="bold"),
            fg_color=C_CYAN, hover_color=C_CYAN_H, text_color=C_BG,
            corner_radius=8, command=self._on_convert_click,
        )
        self.convert_btn.grid(row=0, column=0, sticky="ew")
        self._btn(bottom, T["btn_open_output"], self._open_output).grid(row=0, column=1, padx=(8, 0))
        self._btn(bottom, T["btn_logs"], self._open_logs).grid(row=0, column=2, padx=(8, 0))

    def _drop_hover(self, on: bool):
        self.drop_frame.configure(border_color=C_GREEN if on else C_CYAN_D)
        self.drop_label.configure(text_color=C_GREEN if on else C_CYAN)

    def _btn(self, master, text, cmd, accent=False):
        if accent:
            return ctk.CTkButton(
                master, text=text, command=cmd, height=32, corner_radius=6,
                font=ctk.CTkFont(family=FONT, size=13),
                fg_color=C_CYAN_D, hover_color=C_CYAN, text_color=C_TEXT,
            )
        return ctk.CTkButton(
            master, text=text, command=cmd, height=32, corner_radius=6,
            font=ctk.CTkFont(family=FONT, size=13),
            fg_color="transparent", hover_color=C_PANEL,
            text_color=C_DIM, border_width=1, border_color=C_BORDER,
        )

    def _fatal(self, msg):
        self.status_var.set("[ ERROR ] " + msg)
        self.convert_btn.configure(state="disabled")
        self._log("FATAL: " + msg, "err")

    def _log(self, text: str, tag: str = "dim"):
        self._log_batch([(text, tag)])

    def _log_batch(self, entries):
        """批量写入终端：一批只翻转一次状态、滚动一次。
        大批量转换时逐行写入意味着每行约 6 次 Tk 调用，会在 UI 线程堆积。"""
        tb = self.term._textbox
        self.term.configure(state="normal")
        for text, tag in entries:
            tb.insert("end", text + "\n", tag)
        if int(tb.index("end-1c").split(".")[0]) > 500:   # 日志上限，防膨胀
            tb.delete("1.0", "201.0")
        tb.see("end")
        self.term.configure(state="disabled")

    # ---------- 文件管理 ----------
    def _parse_drop(self, data: str) -> list[Path]:
        # tkdnd 以 Tcl 列表格式传路径（含空格的用 {} 包裹，特殊字符反斜杠转义），
        # 交给 Tcl 自己拆最可靠；手写解析遇到文件名本身带 { } 时会拆错
        try:
            return [Path(p) for p in self.tk.splitlist(data)]
        except tk.TclError:
            return []

    def _on_drop(self, event):
        self._drop_hover(False)
        self.add_files(self._parse_drop(event.data))

    def _pick_files(self):
        from tkinter import filedialog
        paths = filedialog.askopenfilenames(title=T["dlg_pick_files"])
        if paths:
            self.add_files([Path(p) for p in paths])

    def add_files(self, paths: list[Path]):
        new: list[Path] = []
        for p in paths:
            if not os.path.isfile(p):
                continue
            # abspath 是纯字符串运算；resolve() 要为每个文件打开句柄查真实路径，
            # 实测 1.2 万个文件 2.5s → 0.6s。Windows 下 Path 比较本就不区分大小写，去重效果相同
            p = Path(os.path.abspath(p))
            if p in self._file_set:
                continue
            self._file_set.add(p)
            self.files.append(p)
            new.append(p)
        if not new:
            return
        self.status_var.set(T["status_queue"].format(n=len(self.files)))
        self.queue_view.refresh()   # 虚拟列表：只刷新可见的十几行
        self._maybe_media_notice(new)

    def _maybe_media_notice(self, added: list[Path]):
        """添加图片/音频类文件时弹窗告知处理方式（每次运行只弹一次，可勾选永久关闭）。"""
        if self.cfg.get("media_notice_shown") or getattr(self, "_media_notice_done", False):
            return
        n_img = sum(1 for p in added if p.suffix.lower() in IMG_EXTS)
        n_aud = sum(1 for p in added if p.suffix.lower() in AUDIO_EXTS)
        if not n_img and not n_aud:
            return
        self._media_notice_done = True
        ocr_ok = _ocr_installed()
        lines = []
        if n_img:
            if ocr_ok:
                lines.append(T["media_img_ocr"].format(n=n_img))
            else:
                lines.append(T["media_img_no_ocr"].format(n=n_img))
        if n_aud:
            lines.append(T["media_audio"].format(n=n_aud))
        if ocr_ok:
            lines.append("")
            lines.append(T["media_local_note"])
        NoticeDialog(self, T["media_title"], "\n".join(lines), "media_notice_shown")

    def _remove_path(self, path: Path):
        if self.converting or path not in self._file_set:
            return
        self.files.remove(path)
        self._file_set.discard(path)
        self._row_status.pop(path, None)
        self.queue_view.refresh()

    def _clear_files(self):
        if self.converting:
            return
        self.files.clear()
        self._file_set.clear()
        self._row_status.clear()
        self.queue_view.refresh()
        self.progress.set(0)
        self.status_var.set(T["status_ready"])

    # ---------- 微信文件 ----------
    def _open_wechat(self):
        try:
            if self.picker is not None and self.picker.winfo_exists():
                self.picker.focus()
                return
        except Exception:
            pass
        self.picker = WeChatPicker(self)

    # ---------- 输出目录 ----------
    def _pick_output_dir(self):
        from tkinter import filedialog
        d = filedialog.askdirectory(title=T["dlg_pick_output"], initialdir=self.out_var.get())
        if d:
            self.out_var.set(d)
            self.cfg["output_dir"] = d
            self._save_config()

    def _open_output(self):
        try:
            d = Path(self.out_var.get())
            d.mkdir(parents=True, exist_ok=True)
            os.startfile(d)  # noqa: S606
        except OSError as e:
            self.status_var.set("[ ERROR ] " + T["open_output_fail"].format(e=e))
            self._log(T["open_output_fail"].format(e=e), "err")

    def _open_logs(self):
        """打开日志中心：查看/导出安装日志与更新日志（只读模式，不执行更新）。"""
        updater = SCRIPT_DIR / "update.pyw"
        if not updater.exists():
            self._log(T["no_log_center"], "warn")
            return
        try:
            subprocess.Popen([sys.executable, str(updater), "--view"],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as e:
            self._log(T["open_logs_fail"].format(e=e), "err")

    # ---------- 转换流程 ----------
    def _on_convert_click(self):
        """转换按钮兼作停止按钮：转换中再点一下就是「停止转换」。"""
        if self.converting:
            self._stop_convert()
        else:
            self._start_convert()

    def _ask_yes_no(self, title: str, message: str, ok_text: str) -> bool:
        dlg = ConfirmDialog(self, title, message, ok_text)
        self.wait_window(dlg)
        return dlg.result

    def _start_convert(self):
        if self.converting:
            return
        if not self.files:
            self.status_var.set(T["wait_add_files"])
            return
        if self._engine_broken:
            # 引擎加载失败后不再反复启动注定失败的进程，直接给出修复指引
            self.status_var.set("[ ERROR ] " + T["engine_broken"])
            self._log(T["engine_broken"], "err")
            return
        raw_out = self.out_var.get().strip()
        if not raw_out:      # 留空会静默写进进程工作目录，回退到默认目录
            raw_out = str(SCRIPT_DIR / T["output_dirname"])
            self.out_var.set(raw_out)
        out_dir = Path(raw_out)
        if not out_dir.is_absolute():   # 相对路径锚定到程序目录，而非进程 CWD
            out_dir = SCRIPT_DIR / out_dir
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.status_var.set(T["err_outdir"].format(e=e))
            return
        if not out_dir.is_dir():
            self.status_var.set(T["err_outdir_notdir"])
            return
        self.cfg["output_dir"] = str(out_dir)
        self._save_config()

        # 只转换还没成功处理的文件（新加入 / 失败 / 被停止的）：旧版每点一次都把整个
        # 队列重转一遍，已完成的文件又生成一份「xxx (1).md」。全部都转过时才询问是否
        # 全部重新转换——此时原地覆盖上次生成的 md，不再新增带序号的副本
        todo = [p for p in self.files if self._row_status.get(p) not in ("done", "empty")]
        overwrite = False
        if not todo:
            if not self._ask_yes_no(T["reconvert_title"],
                                    T["reconvert_msg"].format(n=len(self.files)),
                                    T["reconvert_ok"]):
                return
            todo, overwrite = list(self.files), True
        if self.converting:   # 保险：确认弹窗等待期间不可能开始别的批次
            return

        self.converting = True
        self._stop_requested = False
        for p in todo:
            self._row_status.pop(p, None)   # 本批文件重新显示为「等待」
        self.queue_view.refresh()
        self.convert_btn.configure(state="normal", text=T["btn_stop"],
                                   fg_color=C_RED, hover_color="#fda4af")
        self.progress.set(0)
        total = len(todo)
        self.status_var.set(T["status_run"].format(done=0, total=total))
        self._log(T["log_task_start"].format(n=total), "sys")
        if len(self.files) > total:
            self._log(T["log_skip_done"].format(n=len(self.files) - total), "sys")

        threading.Thread(target=self._worker, args=(out_dir, todo, overwrite), daemon=True).start()

    def _stop_convert(self):
        """停止转换：结束转换进程，已完成的文件保留，其余标记为「已停止」，
        下次点「开始转换」时接着转。"""
        if not self.converting or self._stop_requested:
            return
        # 先置标志、再杀进程：_worker 拿到进程后会复查标志（见那里），两边总有一边能杀掉它
        self._stop_requested = True
        self.convert_btn.configure(state="disabled", text=T["btn_stopping"])
        self._log(T["log_stop_req"], "warn")
        for proc in list(self._active_procs):
            try:
                proc.kill()
            except OSError:
                pass
        self.worker_man.kill()

    WORKER_MAX_RUNS = 3   # 一批任务最多动用几个转换进程（首个 + 崩溃后重启 2 次）

    def _worker(self, out_dir: Path, files: list[Path], overwrite: bool = False):
        """把整批任务交给预热好的子进程执行，读取它的进度输出。界面进程零负担。

        子进程中途崩溃时（畸形文件可能让底层 C 库直接带崩整个进程），只把崩溃
        时正在转换的文件判失败，尚未开始的文件换新进程接着转——不让一个坏文件
        连累整批。用户点「停止」时不再重启，没转完的文件标记为「已停止」。
        无论出现什么异常，最后都一定发出 finished，按钮不会永久变灰。"""
        total = len(files)
        done = ok = empty = stopped = 0
        t0 = time.time()
        reported: set[int] = set()
        jobs: list[list[str]] = []

        def drop_part(g: int):
            # 转到一半被打断的文件：删掉没写完的 .part 临时文件
            if g < len(jobs):
                try:
                    os.remove(jobs[g][1] + ".part")
                except OSError:
                    pass

        def give_up(g: int, log_text: str | None):
            nonlocal done, stopped
            reported.add(g)
            done += 1
            drop_part(g)
            if self._stop_requested:
                stopped += 1
                self.ui_queue.put(("status", files[g], "stopped"))
            else:
                self.ui_queue.put(("status", files[g], "failed"))
                if log_text:
                    self.ui_queue.put(("log", log_text, "err"))
            self.ui_queue.put(("progress", done, total))

        try:
            # 「全部重新转换」：输出目录没变的文件原地覆盖上次的 md。先把这些名字全部
            # 占住，免得别的文件（比如上次的 md 已被用户删掉时）抢先用了同名
            reuse: dict[Path, Path] = {}
            if overwrite:
                for p in files:
                    prev = self._outputs.get(p)
                    if prev is not None and prev.parent == out_dir:
                        reuse[p] = prev
            reserved = set(reuse.values())
            ECHO_LIMIT = 20   # 大批量时只回显前 20 条命令，防止日志洪泛卡住界面
            for p in files:
                dst = reuse.get(p) or unique_output_path(out_dir, p.stem, reserved)
                reserved.add(dst)
                jobs.append([str(p), str(dst)])
                if len(jobs) <= ECHO_LIMIT:
                    self.ui_queue.put(("log", f'$ markitdown "{p.name}" -o "{dst.name}"', "cmd"))
            if len(jobs) > ECHO_LIMIT:
                self.ui_queue.put(("log", T["log_more"].format(n=len(jobs) - ECHO_LIMIT), "cmd"))

            pending = list(range(total))   # 本轮要交给子进程的序号
            for run in range(self.WORKER_MAX_RUNS):
                if not pending or self._closed or self._stop_requested:
                    break
                if run:
                    self.ui_queue.put(("log", T["log_worker_restart"].format(n=len(pending)), "warn"))
                proc = self.worker_man.get()
                self._active_procs.add(proc)
                if self._stop_requested:   # 停止请求恰好发生在取进程期间：自己杀掉
                    try:
                        proc.kill()
                    except OSError:
                        pass
                started: set[int] = set()
                batch_over = False   # 收到 all_done / engine_error：本批到此为止，不再重启
                try:
                    # 常驻进程：不能 close stdin
                    proc.stdin.write(json.dumps([jobs[g] for g in pending]) + "\n")
                    proc.stdin.flush()
                    for line in proc.stdout:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            msg = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        ev, li = msg.get("event"), msg.get("i")
                        # 子进程上报的是本轮内的序号，映射回本批序号
                        g = pending[li] if isinstance(li, int) and 0 <= li < len(pending) else None
                        if ev == "engine_error":
                            # 子进程启动即失败（引擎没加载起来）：真实原因 + 修复指引，整批标记失败
                            self._engine_broken = True
                            self.ui_queue.put(("log", T["log_engine_fail"].format(msg=msg.get("msg", "")), "err"))
                            self.ui_queue.put(("log", T["log_engine_fix"], "err"))
                            for j in range(total):
                                if j not in reported:
                                    reported.add(j)
                                    done += 1
                                    self.ui_queue.put(("status", files[j], "failed"))
                                    self.ui_queue.put(("progress", done, total))
                            batch_over = True
                            break
                        if ev == "start" and g is not None:
                            started.add(g)
                            self.ui_queue.put(("status", files[g], "running"))
                        elif ev in ("done", "fail", "empty") and g is not None and g not in reported:
                            reported.add(g)
                            done += 1
                            if ev == "done":
                                ok += 1
                                self._outputs[files[g]] = Path(jobs[g][1])
                                self.ui_queue.put(("status", files[g], "done"))
                                tag = T["tag_ocr"] if msg.get("ocr") else ""
                                if msg.get("imgs"):
                                    tag += T["tag_imgs"].format(n=msg["imgs"])
                                self.ui_queue.put(("log", T["log_done"].format(tag=tag, secs=msg.get("secs", 0)), "ok"))
                            elif ev == "empty":
                                empty += 1
                                self.ui_queue.put(("status", files[g], "empty"))
                                hint = EMPTY_HINTS.get(files[g].suffix.lower(), DEFAULT_EMPTY_HINT)
                                self.ui_queue.put(("log", T["log_empty"].format(hint=hint), "warn"))
                            else:
                                self.ui_queue.put(("status", files[g], "failed"))
                                self.ui_queue.put(("log", f"  ✗ {T['st_failed']}  {msg.get('msg', '')}", "err"))
                            self.ui_queue.put(("progress", done, total))
                        elif ev == "all_done":
                            batch_over = True
                            break
                except (ValueError, OSError):   # 管道已断（BrokenPipeError 是 OSError 子类）
                    pass
                finally:
                    self._active_procs.discard(proc)   # 常驻进程：正常结束时留给下一批复用
                if batch_over:
                    break
                # 子进程中途退出（崩溃或被「停止」）：杀掉换新
                self.worker_man.kill()
                if self._stop_requested:
                    break
                # 崩溃时正在转换的文件判失败，其余下一轮续转
                for g in pending:
                    if g in started and g not in reported:
                        give_up(g, T["log_worker_crash"].format(name=files[g].name))
                pending = [g for g in pending if g not in reported]
        except Exception:   # noqa: BLE001  任何意外都不能让界面卡在「转换中」
            pass
        finally:
            # 仍没有结果的文件：用户停止 → 已停止；重启次数用尽 / 意外异常 → 失败
            for i in range(total):
                if i not in reported:
                    give_up(i, T["log_worker_fail"])
            self.ui_queue.put(("finished", ok, empty, stopped, total, time.time() - t0))
            # 为下一批再预热一个备用进程（窗口已关/引擎已坏时 _prewarm 会自行跳过）
            threading.Thread(target=self._prewarm, daemon=True).start()

    def _apply_progress(self, done: int, total: int):
        self.progress.set(done / total)
        self.status_var.set(T["status_run"].format(done=done, total=total))

    def _poll_queue(self):
        """按时间预算（每拍约 20ms）而不是固定条数消化消息：大批量小文件时每个文件
        约 4 条消息，固定 60 条/拍会让界面进度越积越落后于实际进度。
        进度消息只保留最新一条（中间值刷了也看不见），日志攒批一次插入。"""
        logs = []
        progress = None
        deadline = time.perf_counter() + 0.02
        try:
            while time.perf_counter() < deadline:
                item = self.ui_queue.get_nowait()
                kind = item[0]
                if kind == "log":
                    logs.append((item[1], item[2]))   # 攒批，一次插入
                    continue
                if kind == "progress":
                    progress = item[1:]
                    continue
                if logs:
                    self._log_batch(logs)
                    logs = []
                if kind == "status":
                    _, p, st = item
                    self._row_status[p] = st
                    self.queue_view.set_status(p, st)
                elif kind == "wechat_items":
                    _, picker, items, new_roots = item
                    if new_roots:   # 配置统一由 UI 线程写，杜绝跨线程写坏 JSON
                        self.cfg["wechat_roots"] = new_roots
                        self._save_config()
                    try:
                        if picker.winfo_exists():
                            picker.populate(items)
                    except Exception:
                        pass
                elif kind == "finished":
                    if progress is not None:   # 先把进度条推到最终值，再写收尾文案
                        self._apply_progress(*progress)
                        progress = None
                    _, ok, empty, stopped, total, secs = item
                    self.converting = False
                    self.convert_btn.configure(state="normal", text=T["btn_convert"],
                                               fg_color=C_CYAN, hover_color=C_CYAN_H)
                    fail = total - ok - empty - stopped
                    parts = [T["sum_ok"].format(n=ok)]
                    if empty:
                        parts.append(T["sum_empty"].format(n=empty))
                    if fail:
                        parts.append(T["sum_fail"].format(n=fail))
                    if stopped:
                        parts.append(T["sum_stopped"].format(n=stopped))
                    summary = T["sum_join"].join(parts)
                    if self._stop_requested:
                        self.status_var.set(T["status_stopped"].format(summary=summary, secs=secs))
                        self._log(T["log_end_stopped"].format(summary=summary), "warn")
                    elif ok == total:
                        self.status_var.set(T["status_done"].format(total=total, secs=secs))
                        self._log(T["log_done_all"].format(total=total, secs=secs), "sys")
                    else:
                        self.status_var.set(T["status_warn"].format(summary=summary, secs=secs))
                        self._log(T["log_end"].format(summary=summary), "warn")
        except queue.Empty:
            pass
        if logs:
            self._log_batch(logs)
        if progress is not None:
            self._apply_progress(*progress)
        self.after(80, self._poll_queue)


def _ocr_installed() -> bool:
    """OCR 组件是否已安装。只查安装元数据、不 import：winrt 运行时会初始化 COM 套间，
    在界面线程导入可能影响拖放和文件对话框（它们要求 STA）。"""
    from importlib import metadata
    for dist in ("winrt-Windows.Media.Ocr", "winsdk"):
        try:
            metadata.distribution(dist)
            return True
        except metadata.PackageNotFoundError:
            pass
    return False


def _hold_app_mutex():
    """创建命名互斥体并在进程存活期间一直持有（句柄随进程退出自动释放）。
    安装/卸载程序据此提示「请先关闭转换器」，更新器据此拒绝在组件被占用时更新。"""
    try:
        import ctypes
        return ctypes.windll.kernel32.CreateMutexW(None, False, APP_MUTEX_NAME)
    except Exception:  # noqa: BLE001
        return None


if __name__ == "__main__":
    _app_mutex = _hold_app_mutex()
    app = App()
    app.mainloop()
