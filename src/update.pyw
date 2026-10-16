# -*- coding: utf-8 -*-
"""MarkItDown 转换器 —— 检查更新 · 日志中心（中文 / English 双语）

- 实时显示更新过程，并同步逐行写入更新日志（UTF-8，含时间戳）
- 可切换查看：更新日志 / 安装日志 / 诊断报告
- 一键导出 TXT 或 PDF（PDF 为纯标准库生成，支持中文，见 logtools.py）
- 多线路安装：GitHub 直连 → 两个加速代理 → PyPI 镜像；每步装完即校验

从开始菜单「MarkItDown 转换器 > 检查更新」启动；
加 --view 参数启动则只打开日志中心，不执行更新。

界面语言：读取安装程序写入的 language.txt（或配置文件中的 language），
英文模式下日志文件使用英文文件名（Install Log.txt / Update Log.txt），方便查找。
也可用 --lang zh / --lang en 强制指定。
"""
import datetime
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from collections import deque
from pathlib import Path
from tkinter import filedialog, messagebox
from urllib.parse import urlsplit

SCRIPT_DIR = Path(__file__).resolve().parent
VENV_PY = SCRIPT_DIR / ".venv" / "Scripts" / "python.exe"
CONFIG_FILE = SCRIPT_DIR / "markitdown_gui_config.json"
LANG_FILE = SCRIPT_DIR / "language.txt"
sys.path.insert(0, str(SCRIPT_DIR))

# ---------------- 界面文案：中文 / English ----------------
STRINGS = {
    "zh": {
        "window_title": "MarkItDown 转换器 — 检查更新 · 日志中心",
        "header": "◢ 检查更新 · 日志中心 UPDATE & LOGS",
        "view_update": "更新日志",
        "view_install": "安装日志",
        "view_report": "诊断报告",
        "btn_close": "关闭",
        "btn_open_dir": "打开日志文件夹",
        "btn_export_pdf": "导出 PDF",
        "btn_export_txt": "导出 TXT",
        "view_only_hint": "日志查看模式（如需更新请从开始菜单启动「检查更新」）",
        "updating_no_switch": "更新进行中，完成后可切换查看其他日志…",
        "collecting_report": "正在收集诊断信息（含组件版本清单，约几秒钟）…",
        "report_ready": "诊断报告（可直接导出，发给技术支持定位问题）",
        "export_log": "导出日志",
        "export_empty": "当前没有可导出的日志内容。",
        "export_txt_title": "导出 TXT 日志",
        "export_pdf_title": "导出 PDF 日志",
        "filetype_txt": "文本文件",
        "filetype_pdf": "PDF 文件",
        "export_fail": "导出失败",
        "export_fail_msg": "导出日志时出错：\n{e}",
        "exported": "已导出：{path}",
        "export_ok": "导出成功",
        "export_ok_msg": "日志已保存到：\n{path}\n\n是否现在打开？",
        "updating_no_close": "更新进行中，完成后才能关闭窗口…",
        "session_start": "本次更新开始于 {t}",
        "log_truncated": "……(早期日志已截断)……",
        "cmd_start_fail": "无法启动命令：{e}",
        "offline_no_wheels": "（本机已删除内置离线组件目录以节省磁盘，离线修复不可用；请联网后重试）",
        "wait_retry": "等待 10 秒后重试（杀毒软件可能正在扫描文件）…",
        "vcrt_deployed": "已部署 {n} 个 VC++ 运行库到 onnxruntime 组件目录",
        "vcrt_exc": "VC++ 运行库部署异常（忽略，继续自检）: {e}",
        "diag_collecting": "收集诊断信息（写入日志，便于排查）…",
        "diag_fail": "诊断信息收集失败（忽略）: {e}",
        "selfcheck_loading": "自检：加载转换引擎 …",
        "selfcheck_retry": "首次自检失败，等待 20 秒后重试（杀毒软件可能正在扫描文件）…",
        "selfcheck_fail": "自检未通过：请把本日志发给发送安装包的人，上方 [diag] 段落可直接定位问题。",
        "pip_self_update": "正在更新 pip 自身 …",
        "mirror1_fail": "清华镜像失败，改用阿里云镜像重试 …",
        "gui_installing": "\n正在安装/更新界面组件 customtkinter、tkinterdnd2 …",
        "online_fail_offline": "在线安装失败，改用内置离线组件 …",
        "core_installing": "\n正在从清华镜像安装/更新 markitdown …",
        "core_mirror2": "清华镜像失败，改用阿里云镜像 …",
        "core_github": "国内镜像均失败，尝试 GitHub 直连（快速判定）…",
        "core_proxy": "GitHub 直连失败，通过加速代理下载（快速判定）…",
        "all_online_fail": "\n在线线路全部失败，改用内置离线组件修复 …",
        "optional_installing": "\n尝试安装可选组件 {pkg}（失败不影响使用）…",
        "pip_list_header": "---- 更新后组件版本（pip list）----",
        "update_error": "\n✗ 更新出错：{e}",
        "venv_missing": "\n✗ 未找到运行环境（.venv 目录不存在或已损坏），无法执行更新。\n请重新运行安装程序修复；若多次失败，请把「诊断报告」发给发送安装包的人。",
        "update_ok": "\n✓ 更新完成！重新启动转换器即可使用最新版本。",
        "status_ok": "更新成功。可用上方按钮导出日志（TXT / PDF）。",
        "update_fail": "\n✗ 更新未完成：请检查网络后重试；也可导出「诊断报告」发给技术支持。",
        "status_fail": "更新未完成。建议：导出诊断报告 → 发送给技术支持。",
        "update_log_file": "更新日志.txt",
        "install_log_file": "安装日志.txt",
        "export_base": "MarkItDown{name}_{t}",
        "app_running_title": "转换器正在运行",
        "app_running_msg": "检测到 MarkItDown 转换器正在运行。\n请先关闭转换器窗口再更新：正在使用的组件无法替换，强行更新可能失败或损坏运行环境。\n\n关闭后点「重试」继续更新。",
        "update_cancelled": "已取消更新（转换器仍在运行）。当前为日志查看模式。",
        "net_skip": "{host} 3 秒内无法连接，跳过该线路",
    },
    "en": {
        "window_title": "MarkItDown Converter — Check for Updates · Log Center",
        "header": "◢ CHECK FOR UPDATES · LOG CENTER",
        "view_update": "Update Log",
        "view_install": "Install Log",
        "view_report": "Diagnostic Report",
        "btn_close": "Close",
        "btn_open_dir": "Open Log Folder",
        "btn_export_pdf": "Export PDF",
        "btn_export_txt": "Export TXT",
        "view_only_hint": "Log viewer mode (to check for updates, launch \"Check for Updates\" from the Start Menu)",
        "updating_no_switch": "An update is in progress; you can switch views when it finishes…",
        "collecting_report": "Collecting diagnostic information (including component versions; this takes a few seconds)…",
        "report_ready": "Diagnostic Report (export it and send it to technical support for troubleshooting)",
        "export_log": "Export Log",
        "export_empty": "There is no log content to export.",
        "export_txt_title": "Export TXT Log",
        "export_pdf_title": "Export PDF Log",
        "filetype_txt": "Text files",
        "filetype_pdf": "PDF files",
        "export_fail": "Export Failed",
        "export_fail_msg": "An error occurred while exporting the log:\n{e}",
        "exported": "Exported: {path}",
        "export_ok": "Export Succeeded",
        "export_ok_msg": "The log was saved to:\n{path}\n\nOpen it now?",
        "updating_no_close": "An update is in progress; the window can be closed when it finishes…",
        "session_start": "This update started at {t}",
        "log_truncated": "......(earlier log entries were truncated)......",
        "cmd_start_fail": "Could not start the command: {e}",
        "offline_no_wheels": "(The bundled offline components were removed after a successful online installation to save disk space; offline repair is unavailable. Connect to the Internet and try again.)",
        "wait_retry": "Retrying in 10 seconds (antivirus software may be scanning files)…",
        "vcrt_deployed": "Deployed {n} VC++ runtime files to the onnxruntime component folder",
        "vcrt_exc": "VC++ runtime deployment error (ignored; continuing self-check): {e}",
        "diag_collecting": "Collecting diagnostic information (written to the log for troubleshooting)…",
        "diag_fail": "Failed to collect diagnostic information (ignored): {e}",
        "selfcheck_loading": "Self-check: loading the conversion engine …",
        "selfcheck_retry": "First self-check failed; retrying in 20 seconds (antivirus software may be scanning files)…",
        "selfcheck_fail": "Self-check failed: send this log to the person who gave you the installer; the [diag] section above pinpoints the problem.",
        "pip_self_update": "Updating pip itself …",
        "mirror1_fail": "Tsinghua mirror failed; retrying with the Aliyun mirror …",
        "gui_installing": "\nInstalling/updating the GUI components customtkinter and tkinterdnd2 …",
        "online_fail_offline": "Online installation failed; switching to the bundled offline components …",
        "core_installing": "\nInstalling/updating markitdown from the Tsinghua mirror …",
        "core_mirror2": "Tsinghua mirror failed; switching to the Aliyun mirror …",
        "core_github": "Both mirrors failed; trying a direct GitHub connection (quick check)…",
        "core_proxy": "Direct GitHub connection failed; downloading through an acceleration proxy (quick check)…",
        "all_online_fail": "\nAll online sources failed; repairing with the bundled offline components …",
        "optional_installing": "\nTrying to install the optional component {pkg} (failure does not affect normal use)…",
        "pip_list_header": "---- Component versions after update (pip list) ----",
        "update_error": "\n✗ Update error: {e}",
        "venv_missing": "\n✗ The runtime environment was not found (the .venv folder is missing or damaged), so the update cannot run.\nRun the installer again to repair; if it fails repeatedly, send the \"Diagnostic Report\" to the person who gave you the installer.",
        "update_ok": "\n✓ Update complete! Restart the converter to use the latest version.",
        "status_ok": "Update succeeded. Use the buttons above to export the log (TXT / PDF).",
        "update_fail": "\n✗ Update incomplete: check your Internet connection and try again; you can also export the \"Diagnostic Report\" and send it to technical support.",
        "status_fail": "Update incomplete. Suggestion: export the Diagnostic Report and send it to technical support.",
        "update_log_file": "Update Log.txt",
        "install_log_file": "Install Log.txt",
        "export_base": "MarkItDown {name} {t}",
        "app_running_title": "Converter Is Running",
        "app_running_msg": "MarkItDown Converter is currently running.\nClose the converter window before updating: components that are in use cannot be replaced, and forcing the update may fail or damage the runtime environment.\n\nClick Retry after closing it.",
        "update_cancelled": "Update cancelled (the converter is still running). Log viewer mode.",
        "net_skip": "{host} could not be reached within 3 seconds; skipping this source",
    },
}


def _saved_language() -> str | None:
    """--lang 参数 > language.txt（安装程序写入）> 配置文件。"""
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


LANG = _saved_language() or "zh"
T = STRINGS[LANG]

UPDATE_LOG = SCRIPT_DIR / T["update_log_file"]
INSTALL_LOG = SCRIPT_DIR / T["install_log_file"]
# 另一种语言的日志文件名：升级安装/语言切换后仍能找到旧日志
LOG_ALTERNATES = {
    "update": [SCRIPT_DIR / "更新日志.txt", SCRIPT_DIR / "Update Log.txt"],
    "install": [SCRIPT_DIR / "安装日志.txt", SCRIPT_DIR / "Install Log.txt"],
}

import logtools  # noqa: E402

# 不含 audio-transcription：该组件的 wav 识别会把音频上传到 Google（界面承诺
# 「全部本地完成」），mp3/m4a 又依赖安装包没有的 ffmpeg；不装它，
# 音频文件统一走「无文字」提示路径，与界面文案一致（与 setup.iss 的 ExtrasSpec 保持一致）
PYPI_SPEC = "markitdown[pptx,docx,xlsx,xls,pdf,outlook]"
GITHUB_SPEC = ("markitdown[pptx,docx,xlsx,xls,pdf,outlook] @ "
               "https://codeload.github.com/microsoft/markitdown/zip/refs/heads/main#subdirectory=packages/markitdown")
GITHUB_PROXY_SPEC = ("markitdown[pptx,docx,xlsx,xls,pdf,outlook] @ "
                     "https://gh-proxy.com/https://codeload.github.com/microsoft/markitdown/zip/refs/heads/main#subdirectory=packages/markitdown")
OTHER_PKGS = ["customtkinter", "tkinterdnd2"]
# 图片/扫描件 OCR（Windows 本地 OCR）：pywinrt 的 winrt-* 系列包，仍在维护，
# Python 3.12~3.14 都有预编译包（取代已停止维护、只有 3.12 包的 winsdk）。
# 各包版本必须一致；锁在 3.x，防止将来的大版本改动 API
OCR_PKGS = [f"{name}>=3.2.1,<4" for name in (
    "winrt-runtime", "winrt-Windows.Foundation", "winrt-Windows.Foundation.Collections",
    "winrt-Windows.Globalization", "winrt-Windows.Graphics.Imaging", "winrt-Windows.Media.Ocr",
    "winrt-Windows.Storage", "winrt-Windows.Storage.Streams")]
# pypdfium2 把扫描件/图片型 PDF 渲染成图片供 OCR（wheel 内置 pdfium 二进制，全版本可装）
# （显示名, 包列表）：各组独立安装，互不连累
OPTIONAL_GROUPS = [("OCR (winrt)", OCR_PKGS), ("pypdfium2", ["pypdfium2"])]
# 可选组件只装预编译包：没有 wheel 时 pip 会下载源码包、装 CMake 编译环境再编译失败
# （旧版 winsdk 实测每次约 25 秒，加上重试白等 2 分钟以上）；只装 wheel 时 1~2 秒即可判定
OPTIONAL_FLAGS = ["--only-binary=:all:"]
# pip 的这两类报错是确定性失败（该 Python 版本没有可用的包），重试只会白等
NO_DIST_MARKERS = ("No matching distribution found", "Could not find a version that satisfies")
APP_MUTEX_NAME = "MarkItDownConverterGUI"   # 与 markitdown_gui.py、setup.iss 的 AppMutex 一致
MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"
MIRROR2 = "https://mirrors.aliyun.com/pypi/simple/"
PIP_FLAGS = ["--disable-pip-version-check", "--no-input", "--retries", "5", "--timeout", "30", "--no-cache-dir"]
# GitHub 线路对中国大陆用户大多不通：降低重试与超时，快速判定后切换下一条
PIP_FLAGS_FAST = ["--disable-pip-version-check", "--no-input", "--retries", "1", "--timeout", "15", "--no-cache-dir"]

C_BG, C_PANEL, C_TERM = "#0a0e17", "#101827", "#050a12"
C_CYAN, C_CYAN_D, C_TEXT, C_DIM = "#22d3ee", "#0e7490", "#dbe7ff", "#54709e"
C_GREEN, C_RED = "#34d399", "#fb7185"
FONT = "Microsoft YaHei UI"
LOG_ROTATE_BYTES = 1024 * 1024   # 日志超过 1MB 时截断保留尾部，防无限膨胀


def converter_running() -> bool:
    """转换器界面运行期间持有命名互斥体（见 markitdown_gui._hold_app_mutex）。"""
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.OpenMutexW(0x00100000, False, APP_MUTEX_NAME)   # SYNCHRONIZE
        if h:
            k32.CloseHandle(h)
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def tcp_reachable(host: str, timeout: float = 3.0) -> bool:
    """3 秒 TCP 连通性预检（与安装程序的 NetProbe 同理）：对静默丢包的网络，pip
    每条线路都会空转 retries×timeout 好几分钟，预检不通就直接跳过该线路。
    配置了代理（环境变量或系统代理，pip 也会走代理）时直连探测说明不了问题，视为可达。"""
    import socket
    import urllib.request
    try:
        if urllib.request.getproxies():
            return True
    except Exception:  # noqa: BLE001
        pass
    try:
        with socket.create_connection((host, 443), timeout=timeout):
            return True
    except OSError:
        return False


def existing_log(kind: str) -> Path:
    """当前语言的日志文件优先；不存在时退回另一种语言的历史日志文件。"""
    primary = UPDATE_LOG if kind == "update" else INSTALL_LOG
    if primary.exists():
        return primary
    for p in LOG_ALTERNATES[kind]:
        if p.exists():
            return p
    return primary


class Updater(tk.Tk):
    def __init__(self, view_only: bool):
        super().__init__()
        self.title(T["window_title"])
        self.geometry("780x560")
        self.minsize(660, 460)
        self.configure(bg=C_BG)
        self._running = False
        self._view = "update"
        self._report_cache: str | None = None
        self._log_fp = None
        self._file_lock = threading.Lock()   # 文件写入串行化（worker 与主线程都可能写）
        self._reach: dict[str, bool] = {}    # 各线路主机的连通性预检结果（每台主机只测一次）
        self._last_output: deque = deque(maxlen=40)   # 最近一条命令的输出尾部

        tk.Label(self, text=T["header"], fg=C_CYAN, bg=C_BG,
                 font=("Consolas", 13, "bold")).pack(anchor="w", padx=14, pady=(12, 6))

        # ── 视图切换 + 操作按钮 ──
        bar = tk.Frame(self, bg=C_BG)
        bar.pack(fill="x", padx=14, pady=(0, 6))
        self._view_btns = {}
        for key in ("update", "install", "report"):
            b = tk.Button(bar, text=T[f"view_{key}"], command=lambda k=key: self._show_view(k),
                          bg=C_PANEL, fg=C_DIM, activebackground=C_CYAN_D,
                          activeforeground="white", bd=0, padx=10, pady=3,
                          font=(FONT, 9))
            b.pack(side="left", padx=(0, 6))
            self._view_btns[key] = b
        for text, cmd in ((T["btn_close"], self._try_close),
                          (T["btn_open_dir"], self._open_log_dir),
                          (T["btn_export_pdf"], lambda: self._export("pdf")),
                          (T["btn_export_txt"], lambda: self._export("txt"))):
            tk.Button(bar, text=text, command=cmd, bg=C_CYAN_D, fg="white",
                      activebackground=C_CYAN, activeforeground=C_BG,
                      bd=0, padx=10, pady=3, font=(FONT, 9)).pack(side="right", padx=(6, 0))

        self.text = tk.Text(self, bg=C_TERM, fg=C_TEXT, font=("Consolas", 10),
                            state="disabled", wrap="none", bd=0)
        self.text.pack(expand=True, fill="both", padx=14)
        sy = tk.Scrollbar(self.text, orient="vertical", command=self.text.yview)
        sx = tk.Scrollbar(self.text, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")

        self.status_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.status_var, fg=C_DIM, bg=C_BG,
                 font=(FONT, 9)).pack(anchor="w", padx=14, pady=(4, 10))

        self.protocol("WM_DELETE_WINDOW", self._try_close)
        if view_only:
            self._show_view("update" if existing_log("update").exists() else "install")
            self.status_var.set(T["view_only_hint"])
        else:
            self.after(100, self._start_update)   # 先让窗口显示出来（可能要弹「请先关闭转换器」）

    # ---------------- 日志输出 ----------------
    def _open_log_file(self):
        """打开更新日志：超过 1MB 先截断保留尾部，再追加本次会话头。"""
        try:
            if UPDATE_LOG.exists() and UPDATE_LOG.stat().st_size > LOG_ROTATE_BYTES:
                # 先按字节截尾再无损解码，避免正好切断多字节字符导致整份日志被误读
                tail = UPDATE_LOG.read_bytes()[-LOG_ROTATE_BYTES // 2:].decode("utf-8", errors="ignore")
                UPDATE_LOG.write_bytes(b"\xef\xbb\xbf" + (T["log_truncated"] + "\n").encode("utf-8")
                                       + tail.encode("utf-8"))
            if not UPDATE_LOG.exists():
                UPDATE_LOG.write_bytes(b"\xef\xbb\xbf")   # UTF-8 BOM
            self._log_fp = open(UPDATE_LOG, "a", encoding="utf-8", errors="replace")
            self._file_log_line("")
            self._file_log_line("=" * 56)
            self._file_log_line(T["session_start"].format(t=f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}"))
            self._file_log_line("=" * 56)
        except OSError:
            self._log_fp = None

    def _file_log_line(self, s: str):
        if self._log_fp is None:
            return
        try:
            with self._file_lock:
                stamp = datetime.datetime.now().strftime("%H:%M:%S")
                self._log_fp.write(f"[{stamp}] {s}\n" if s else "\n")
                self._log_fp.flush()          # 逐行落盘，真正的实时日志
        except (OSError, ValueError):
            pass

    def log(self, s: str):
        """更新线程专用：写文件 + （若正在看更新视图）上屏。"""
        self._file_log_line(s)
        if self._view == "update":
            self._append_widget(s)

    def _append_widget(self, s: str):
        self.text.configure(state="normal")
        self.text.insert("end", s + "\n")
        if int(self.text.index("end-1c").split(".")[0]) > 4000:   # 防膨胀
            self.text.delete("1.0", "2001.0")
        self.text.see("end")
        self.text.configure(state="disabled")

    def _set_widget_text(self, content: str):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.see("end")
        self.text.configure(state="disabled")

    def _read_file(self, path: Path) -> str:
        return logtools._read_log(path, lang=LANG)

    # ---------------- 视图切换 ----------------
    def _show_view(self, key: str):
        if self._running:
            self.status_var.set(T["updating_no_switch"])
            return
        self._view = key
        for k, b in self._view_btns.items():
            b.configure(fg=C_CYAN if k == key else C_DIM)
        if key == "update":
            p = existing_log("update")
            self._set_widget_text(self._read_file(p))
            self.status_var.set(str(p))
        elif key == "install":
            p = existing_log("install")
            self._set_widget_text(self._read_file(p))
            self.status_var.set(str(p))
        else:
            # 诊断报告：先显示缓存（若有），同时后台总是重新收集，保证反映当前环境状态
            if self._report_cache is not None:
                self._set_widget_text(self._report_cache)
                self.status_var.set(T["report_ready"])
            else:
                self.status_var.set(T["collecting_report"])
            threading.Thread(target=self._build_report, daemon=True).start()

    def _build_report(self):
        report = logtools.collect_diagnostics(SCRIPT_DIR, lang=LANG)
        self._report_cache = report
        def show():
            if self._view == "report":
                self._set_widget_text(report)
                self.status_var.set(T["report_ready"])
        try:
            self.after(0, show)
        except (RuntimeError, tk.TclError):
            pass   # 窗口已关闭（用户看完日志直接关窗），丢弃本次回调

    # ---------------- 导出 ----------------
    def _current_content(self) -> str:
        return self.text.get("1.0", "end-1c")

    def _export(self, kind: str):
        content = self._current_content()
        if not content.strip():
            messagebox.showinfo(T["export_log"], T["export_empty"], parent=self)
            return
        base = T["export_base"].format(name=T[f"view_{self._view}"],
                                       t=f"{datetime.datetime.now():%Y%m%d_%H%M%S}")
        if kind == "txt":
            path = filedialog.asksaveasfilename(
                parent=self, title=T["export_txt_title"], initialfile=base + ".txt",
                defaultextension=".txt", filetypes=[(T["filetype_txt"], "*.txt")])
        else:
            path = filedialog.asksaveasfilename(
                parent=self, title=T["export_pdf_title"], initialfile=base + ".pdf",
                defaultextension=".pdf", filetypes=[(T["filetype_pdf"], "*.pdf")])
        if not path:
            return
        try:
            if kind == "txt":
                logtools.export_txt(content, path)
            else:
                logtools.export_pdf(content, path,
                                    title=f"MarkItDown Converter {T[f'view_{self._view}']}",
                                    lang=LANG)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(T["export_fail"], T["export_fail_msg"].format(e=e), parent=self)
            return
        self.status_var.set(T["exported"].format(path=path))
        if messagebox.askyesno(T["export_ok"], T["export_ok_msg"].format(path=path), parent=self):
            try:
                os.startfile(path)  # noqa: S606
            except OSError:
                pass

    def _open_log_dir(self):
        try:
            os.startfile(SCRIPT_DIR)  # noqa: S606
        except OSError:
            pass

    def _try_close(self):
        if self._running:
            self.status_var.set(T["updating_no_close"])
            return
        self.destroy()

    # ---------------- 更新流程 ----------------
    def _py(self) -> str:
        # venv 缺失时绝不能回退 sys.executable：那会把组件 pip 装进运行更新器的
        # 基础 Python（污染环境且应用仍不可用）；_update_worker 入口已拦截该情况
        return str(VENV_PY)

    def _run_cmd(self, args: list[str]) -> int:
        """流式执行命令：输出逐行进日志，返回退出码。"""
        self.after(0, self.log, "$ " + " ".join(args[1:]) if args and args[1] == "-m" else "$ " + " ".join(args))
        try:
            # 子进程按系统 ANSI 代码页输出（中文 Windows 为 GBK）：pip 报文是英文，
            # 但系统级错误（WinError 描述、中文路径）是 GBK，用 mbcs 才能正确解码。
            # 显式指定 PYTHONIOENCODING：用户环境若设了 PYTHONUTF8 / PYTHONIOENCODING=utf-8，
            # pip 会改输出 UTF-8，按 mbcs 解码后含中文的行全是乱码
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="mbcs", errors="replace",
                                    env=dict(os.environ, PYTHONIOENCODING="mbcs:replace"),
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as e:
            self.after(0, self.log, T["cmd_start_fail"].format(e=e))
            return -1
        assert proc.stdout is not None
        self._last_output.clear()
        for line in proc.stdout:
            line = line.rstrip()
            self._last_output.append(line)
            self.after(0, self.log, line)
        return proc.wait()

    def _reachable(self, url: str) -> bool:
        host = urlsplit(url).hostname or ""
        if host not in self._reach:
            self._reach[host] = tcp_reachable(host)
            if not self._reach[host]:
                self.after(0, self.log, T["net_skip"].format(host=host))
        return self._reach[host]

    def _pip(self, pkgs: list[str], index: str = MIRROR, offline: bool = False, fast: bool = False,
             extra: list[str] | None = None, probe: str | None = None) -> bool:
        """probe：线路实际下载的地址（GitHub 线路的包来自 spec 里的 URL 而非 index）。"""
        args = ([self._py(), "-m", "pip", "install", "--upgrade"]
                + (PIP_FLAGS_FAST if fast else PIP_FLAGS) + (extra or []))
        if offline:
            wheels = SCRIPT_DIR / "wheels"
            if not wheels.is_dir():
                # v1.0.6 起：在线安装成功后安装程序会删除离线备用组件以节省磁盘
                self.after(0, self.log, T["offline_no_wheels"])
                return False
            args += ["--no-index", "--find-links", str(wheels)]
        else:
            if not self._reachable(probe or index):
                return False
            args += ["-i", index]
        rc = self._run_cmd(args + pkgs)
        no_dist = any(m in ln for ln in self._last_output for m in NO_DIST_MARKERS)
        if rc != 0 and not fast and not no_dist:
            # 杀毒软件会临时锁定新写入的 DLL（如 onnxruntime.dll），稍候重试即可成功；
            # 「没有匹配的版本」是确定性失败，不重试
            self.after(0, self.log, T["wait_retry"])
            time.sleep(10)
            rc = self._run_cmd(args + pkgs)
        return rc == 0

    def _deploy_vcrt(self) -> None:
        """把安装包自带的 VC++ 运行库 DLL 部署到 onnxruntime 的 pyd 同目录。

        venv 的 Scripts\\python.exe 只是转发器，真实进程镜像是基础安装目录的
        python.exe（GetModuleFileNameW 实测），因此 .venv\\Scripts 不在 pyd
        依赖的搜索路径里；pyd 自身所在目录（onnxruntime\\capi）必被搜索。
        pip 升级会重写该目录，故每次自检前重新部署。部署失败不致命——
        自检会暴露真实错误。"""
        try:
            redist = SCRIPT_DIR / "redist-vcrt"
            capi = SCRIPT_DIR / ".venv" / "Lib" / "site-packages" / "onnxruntime" / "capi"
            if not (redist.is_dir() and capi.is_dir()):
                return
            n = 0
            for dll in redist.glob("*.dll"):
                shutil.copy2(dll, capi / dll.name)
                n += 1
            if n:
                self.after(0, self.log, T["vcrt_deployed"].format(n=n))
        except Exception as exc:
            self.after(0, self.log, T["vcrt_exc"].format(e=exc))

    def _dump_diag(self) -> None:
        """自检最终失败时自动收集诊断信息写入日志：真实进程镜像、逐 DLL 加载
        测试、onnxruntime 目录内容、onnxruntime 导入堆栈。拿到这段输出即可
        定位绝大多数「找不到指定的模块」类问题。"""
        script = (
            "import ctypes, os, platform, sys\n"
            "print('[diag] python =', sys.version.replace(chr(10), ' '))\n"
            "print('[diag] sys.executable =', sys.executable)\n"
            "print('[diag] platform =', platform.platform())\n"
            "buf = ctypes.create_unicode_buffer(512)\n"
            "ctypes.windll.kernel32.GetModuleFileNameW(None, buf, 512)\n"
            "print('[diag] process image =', buf.value)\n"
            "print('[diag] PATH =', os.environ.get('PATH', ''))\n"
            "k32 = ctypes.windll.kernel32\n"
            "for name in ['msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',\n"
            "             'vcruntime140.dll', 'vcruntime140_1.dll', 'concrt140.dll']:\n"
            "    h = k32.LoadLibraryExW(name, None, 0x1000)\n"
            "    if h:\n"
            "        print('[diag] LOAD OK  :', name)\n"
            "    else:\n"
            "        print('[diag] LOAD FAIL:', name, 'winerr =', k32.GetLastError())\n"
            "sp = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), 'Lib', 'site-packages')\n"
            "capi = os.path.join(sp, 'onnxruntime', 'capi')\n"
            "print('[diag] site-packages =', sp, 'exists =', os.path.isdir(sp))\n"
            "print('[diag] capi =', capi, 'exists =', os.path.isdir(capi))\n"
            "if os.path.isdir(capi):\n"
            "    print('[diag] capi files =', sorted(os.listdir(capi)))\n"
            "try:\n"
            "    import onnxruntime\n"
            "    print('[diag] onnxruntime import OK, version =', onnxruntime.__version__)\n"
            "except Exception as e:\n"
            "    print('[diag] onnxruntime import FAIL:', repr(e))\n"
        )
        try:
            diag = SCRIPT_DIR / ".venv" / "mid_diag.py"
            diag.write_text(script, encoding="ascii")
            self.after(0, self.log, T["diag_collecting"])
            self._run_cmd([self._py(), str(diag)])
        except Exception as exc:
            self.after(0, self.log, T["diag_fail"].format(e=exc))

    def _self_check(self) -> bool:
        self._deploy_vcrt()
        cmd = [self._py(), "-c", "from markitdown import MarkItDown; MarkItDown(); print('SELF-CHECK OK')"]
        self.after(0, self.log, T["selfcheck_loading"])
        if self._run_cmd(cmd) == 0:
            return True
        # 杀毒软件可能在扫描刚写入的 DLL（如 onnxruntime.dll），稍候重试即可通过
        self.after(0, self.log, T["selfcheck_retry"])
        time.sleep(20)
        if self._run_cmd(cmd) == 0:
            return True
        self._dump_diag()
        self.after(0, self.log, T["selfcheck_fail"])
        return False

    def _start_update(self):
        # 转换器开着时，它的常驻转换进程占用着 onnxruntime / numpy 等组件的 DLL：
        # 此时 pip 替换组件会失败，或留下新旧混杂的运行环境，必须先关闭
        while converter_running():
            if not messagebox.askretrycancel(T["app_running_title"], T["app_running_msg"], parent=self):
                self._show_view("update" if existing_log("update").exists() else "install")
                self.status_var.set(T["update_cancelled"])
                return
        self._running = True
        for b in self._view_btns.values():
            b.configure(state="disabled")
        self._view_btns["update"].configure(state="normal", fg=C_CYAN)
        self._open_log_file()
        self._view = "update"
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self):
        ok = True
        try:
            if not VENV_PY.exists():
                # 运行环境缺失：绝不能退而操作基础 Python，直接提示重跑安装包
                self.after(0, self.log, T["venv_missing"])
                self.after(0, self._finish_update, False)
                return
            self.after(0, self.log, T["pip_self_update"])
            if not self._reachable(MIRROR) or self._run_cmd(
                    [self._py(), "-m", "pip", "install", "--upgrade", "pip", "-i", MIRROR] + PIP_FLAGS) != 0:
                self.after(0, self.log, T["mirror1_fail"])
                if self._reachable(MIRROR2):
                    self._run_cmd([self._py(), "-m", "pip", "install", "--upgrade", "pip",
                                   "-i", MIRROR2] + PIP_FLAGS)

            self.after(0, self.log, T["gui_installing"])
            gui_ok = self._pip(OTHER_PKGS)
            if not gui_ok:
                self.after(0, self.log, T["mirror1_fail"])
                gui_ok = self._pip(OTHER_PKGS, index=MIRROR2)
            if not gui_ok:
                self.after(0, self.log, T["online_fail_offline"])
                gui_ok = self._pip(OTHER_PKGS, offline=True)
            # 核心组件与界面组件互不为前提：界面组件全线路失败时核心照样尝试，
            # 最后汇总两类结果（安装器 setup.iss 中两者同样是独立判定、各自有兜底）
            # 国内网络环境下 PyPI 镜像最稳定（实测清华镜像 34 秒装完全部依赖），
            # GitHub 线路只作后备并快速判定，避免在不通的线路上空等
            self.after(0, self.log, T["core_installing"])
            spec_ok = self._pip([PYPI_SPEC])
            if not spec_ok:
                self.after(0, self.log, T["core_mirror2"])
                spec_ok = self._pip([PYPI_SPEC], index=MIRROR2)
            if not spec_ok:
                self.after(0, self.log, T["core_github"])
                spec_ok = self._pip([GITHUB_SPEC], fast=True, probe="https://codeload.github.com/")
            if not spec_ok:
                self.after(0, self.log, T["core_proxy"])
                spec_ok = self._pip([GITHUB_PROXY_SPEC], fast=True, probe="https://gh-proxy.com/")
            if not spec_ok:
                self.after(0, self.log, T["all_online_fail"])
                spec_ok = self._pip([PYPI_SPEC] + OTHER_PKGS, offline=True)
            ok = gui_ok and spec_ok

            if ok:
                # 逐组安装可选组件：某一组装不上不能拖垮另一组
                for name, pkgs in OPTIONAL_GROUPS:
                    self.after(0, self.log, T["optional_installing"].format(pkg=name))
                    if not self._pip(pkgs, extra=OPTIONAL_FLAGS):
                        if not self._pip(pkgs, index=MIRROR2, extra=OPTIONAL_FLAGS):
                            self._pip(pkgs, offline=True, extra=OPTIONAL_FLAGS)

            if ok:
                ok = self._self_check()

            # 把组件版本清单追加进日志（经 after 队列投递，与其他日志保持严格先后顺序；
            # 在工作线程中执行 pip list 本身，避免卡住界面）
            try:
                proc = subprocess.run([self._py(), "-m", "pip", "list", "--disable-pip-version-check"],
                                      capture_output=True, text=True, encoding="utf-8",
                                      errors="replace", timeout=60,
                                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                self.after(0, self.log, "")
                self.after(0, self.log, T["pip_list_header"])
                for ln in (proc.stdout or "").splitlines():
                    self.after(0, self.log, ln)
            except Exception:  # noqa: BLE001
                pass

            self.after(0, self._finish_update, ok)
        except Exception as e:  # noqa: BLE001
            self.after(0, self.log, T["update_error"].format(e=e))
            self.after(0, self._finish_update, False)

    def _finish_update(self, ok: bool):
        # 先写结论（此时日志文件仍打开，结论会一并落盘），再关闭文件
        if ok:
            self.log(T["update_ok"])
            self.status_var.set(T["status_ok"])
        else:
            self.log(T["update_fail"])
            self.status_var.set(T["status_fail"])
        if self._log_fp is not None:
            try:
                self._log_fp.close()
            except OSError:
                pass
            self._log_fp = None
        self._running = False
        for b in self._view_btns.values():
            b.configure(state="normal")
        self._show_view("update")


if __name__ == "__main__":
    Updater(view_only="--view" in sys.argv).mainloop()
