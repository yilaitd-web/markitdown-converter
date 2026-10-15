# -*- coding: utf-8 -*-
"""MarkItDown 转换器 —— 傻瓜式图形界面
把文件拖进来 / 从微信选择，选好输出文件夹，一键批量转换成 Markdown。

普通运行 = 图形界面；带 --worker 参数运行 = 后台转换工作进程
（转换在独立进程中进行，界面永不卡顿）。
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
ICON_FILE = SCRIPT_DIR / "app.ico"
MANUAL_FILE = SCRIPT_DIR / "MarkItDown转换器使用说明书.pdf"

WORKER_PARALLEL = min(4, os.cpu_count() or 4)   # 工作进程内并行转换数
SUPPORTED_HINT = "PDF · DOCX · XLSX · PPTX · HTML · CSV · JSON · XML · 图片(OCR) · 音频"

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

STATUS_STYLE = {  # 状态 -> (文字, 颜色)
    "waiting":  ("● 等待",  C_DIM),
    "running":  ("◉ 转换中", C_AMBER),
    "done":     ("✓ 完成",  C_GREEN),
    "failed":   ("✗ 失败",  C_RED),
    "empty":    ("⚠ 无文字", C_AMBER),
}

IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
# 转换时把内嵌图片一并导出的文档格式：图片落盘为 <文件名>.assets/ 下的文件，
# md 中以相对路径引用（PPTX 默认只输出指向不存在文件的失效引用；DOCX 默认
# 内嵌 base64 巨串，两者都统一改为文件引用）
EMBED_IMG_EXTS = {".pptx", ".docx"}

# 空内容的解释：markitdown 本地版对图片只提取元数据、对音频需语音识别
EMPTY_HINTS = {
    **{e: "OCR 未能从图中识别出文字" for e in IMG_EXTS},
    ".pdf": "PDF 无文字层且 OCR 未识别到文字（扫描件需正常安装 OCR 组件 winsdk，文档也可能已加密）",
    **{e: "音频转文字需要语音识别模型（本地版 markitdown 不具备）" for e in AUDIO_EXTS},
}
DEFAULT_EMPTY_HINT = "该文件中没有可提取的文字"

FONT = "Microsoft YaHei UI"
MONO = "Consolas"


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
    用 os.scandir：目录项自带类型/ stat 缓存，比 iterdir 省一半系统调用。"""
    items: list[tuple[Path, float, int]] = []
    for root in roots:
        try:
            with os.scandir(root) as it:
                months = sorted((e for e in it if e.is_dir()),
                                key=lambda e: e.name, reverse=True)
        except OSError:
            continue
        for m in months:
            try:
                with os.scandir(m.path) as it:
                    for e in it:
                        if not e.is_file():
                            continue
                        try:
                            st = e.stat()
                            items.append((Path(e.path), st.st_mtime, st.st_size))
                        except OSError:
                            pass
            except OSError:
                continue
            if len(items) >= limit * 2:   # 够用了就不再往下扫，省时
                break
    items.sort(key=lambda x: x[1], reverse=True)
    return items[:limit]


# ==================== 工作进程模式 ====================
_ocr_engine = None
_ocr_checked = False


def _get_ocr_engine():
    """惰性创建 Windows OCR 引擎（进程内单例）；不可用时返回 None。"""
    global _ocr_engine, _ocr_checked
    if not _ocr_checked:
        _ocr_checked = True
        try:
            from winsdk.windows.media.ocr import OcrEngine
            langs = list(OcrEngine.available_recognizer_languages)
            chosen = None
            for l in langs:                       # 优先中文
                if l.language_tag.lower().startswith("zh"):
                    chosen = l
                    break
            if chosen is None and langs:
                chosen = langs[0]
            if chosen is not None:
                _ocr_engine = OcrEngine.try_create_from_language(chosen)
        except Exception:
            _ocr_engine = None
    return _ocr_engine


def _ocr_image(path: str) -> str:
    """用 Windows 本地 OCR 识别图片文字，返回清理后的多行文本。失败返回 ''。"""
    import asyncio
    import re

    engine = _get_ocr_engine()
    if engine is None:
        return ""
    try:
        from winsdk.windows.graphics.imaging import BitmapDecoder
        from winsdk.windows.storage import FileAccessMode, StorageFile

        async def _run():
            f = await StorageFile.get_file_from_path_async(path)
            stream = await f.open_async(FileAccessMode.READ)
            dec = await BitmapDecoder.create_async(stream)
            bmp = await dec.get_software_bitmap_async()
            result = await engine.recognize_async(bmp)
            return [ln.text for ln in result.lines]

        lines = asyncio.run(_run())
    except Exception:
        return ""
    # Windows OCR 会在每个汉字之间塞空格，清掉非 ASCII 字符之间的空格
    cleaned = [re.sub(r"(?<=[^\x00-\x7F])\s+(?=[^\x00-\x7F])", "", ln) for ln in lines]
    return "\n".join(ln for ln in cleaned if ln.strip())


_pdfium_lock = threading.Lock()   # pdfium 非线程安全：所有渲染调用串行化


def _ocr_pdf(path: str, max_pages: int = 30) -> str:
    """图片型（扫描件）PDF 兜底：逐页渲染成图片，再用 Windows OCR 识别文字。
    无 OCR 引擎、未安装 pypdfium2 或识别不到文字时返回 ''。"""
    if _get_ocr_engine() is None:
        return ""
    try:
        import pypdfium2 as pdfium
    except Exception:
        return ""
    import shutil
    import tempfile

    tmp = tempfile.mkdtemp(prefix="mid_pdfocr_")
    try:
        with _pdfium_lock:        # 渲染段全程持锁；OCR 段在锁外可并行
            pdf = pdfium.PdfDocument(path)
            try:
                n_total = len(pdf)
                pngs = []
                for i in range(min(n_total, max_pages)):
                    png = os.path.join(tmp, f"p{i}.png")
                    pdf[i].render(scale=2.78).to_pil().save(png)   # ≈200 DPI
                    pngs.append(png)
            finally:
                pdf.close()
        parts = []
        for i, png in enumerate(pngs):
            t = _ocr_image(png)
            parts.append(t if t.strip() else f"（第 {i + 1} 页未识别到文字）")
        if n_total > max_pages:
            parts.append(f"（页数较多，仅识别前 {max_pages} 页）")
        return "\n\n".join(parts)
    except Exception:
        return ""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_IMG_DATA_URI_RE = re.compile(r"!\[([^\]]*)\]\(data:([^;\s]+);base64,([A-Za-z0-9+/=\s]+?)\)")
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
            alt = alt.replace("\\", "/").rsplit("/", 1)[-1].strip() or "图片"
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
            # CommonMark 链接目标，否则各 Markdown 阅读器解析失败、图片不显示
            seen[h] = quote(f"{assets_dir.name}/{fname}", safe="/()!$&'*+,;=:@~-._")
        return f"![{alt}]({seen[h]})"

    return _IMG_DATA_URI_RE.sub(_sub, text), counter


def _run_worker() -> int:
    """常驻子进程：循环从 stdin 读一批任务（JSON 行），转换并把进度以 JSON 行写回 stdout。
    转换在独立进程中进行，即使大文件占满 CPU，界面进程也丝毫不受影响。"""
    from concurrent.futures import ThreadPoolExecutor

    try:
        from markitdown import MarkItDown   # 先加载引擎（预热的关键），再等任务
    except Exception as e:  # noqa: BLE001
        # 引擎加载失败（如缺少 VC++ 运行库 / 组件损坏）：把真实原因上报给界面再退出
        sys.stdout.write(json.dumps({"event": "engine_error", "msg": str(e)[:300]}) + "\n")
        sys.stdout.flush()
        return 1

    tls = threading.local()
    lock = threading.Lock()

    def report(d: dict):
        with lock:
            sys.stdout.write(json.dumps(d) + "\n")   # 纯 ASCII，无编码问题
            sys.stdout.flush()

    def work(i: int, src: str, dst: str):
        report({"i": i, "event": "start"})
        t0 = time.time()
        try:
            if not hasattr(tls, "engine"):
                tls.engine = MarkItDown()
            ext_lower = os.path.splitext(src)[1].lower()
            if ext_lower in EMBED_IMG_EXTS:
                # PPT 等文档里的图片：让 markitdown 以 data URI 带出，
                # 再落盘为 <文件名>.assets/ 图片文件并在 md 中相对引用
                result = tls.engine.convert(src, keep_data_uris=True)
            else:
                result = tls.engine.convert(src)
            text = result.text_content or ""
            used_ocr = False
            n_imgs = 0
            if text.strip() and ext_lower in EMBED_IMG_EXTS:
                text, n_imgs = _extract_embedded_images(text, Path(dst))
            if not text.strip() and ext_lower in IMG_EXTS:
                # markitdown 对图片只能提取元数据 → 用 Windows OCR 兜底识别图中文字
                ocr_text = _ocr_image(src)
                if ocr_text.strip():
                    text = (f"# {os.path.basename(src)} — 图片文字识别\n\n"
                            f"> 以下内容由 Windows OCR 本地识别\n\n" + ocr_text + "\n")
                    used_ocr = True
            elif not text.strip() and ext_lower == ".pdf":
                # 图片型/扫描件 PDF 没有文字层 → 逐页渲染后走 Windows OCR
                ocr_text = _ocr_pdf(src)
                if ocr_text.strip():
                    text = (f"# {os.path.basename(src)} — 扫描件文字识别\n\n"
                            f"> 该 PDF 无文字层，以下内容由 Windows OCR 本地识别\n\n"
                            + ocr_text + "\n")
                    used_ocr = True
            if not text.strip():
                # 提取结果为空：不落盘 0 字节文件，单独上报
                report({"i": i, "event": "empty", "secs": round(time.time() - t0, 2)})
            else:
                Path(dst).write_text(text, encoding="utf-8")
                report({"i": i, "event": "done", "secs": round(time.time() - t0, 2),
                        "ocr": used_ocr, "imgs": n_imgs})
        except Exception as e:  # noqa: BLE001
            report({"i": i, "event": "fail", "msg": str(e)[:200]})

    while True:   # 常驻：一批接一批，不用每批重新加载引擎
        line = sys.stdin.readline()
        if not line:
            return 0
        line = line.strip()
        if not line:
            continue
        try:
            jobs = json.loads(line)
        except json.JSONDecodeError:
            continue
        with ThreadPoolExecutor(max_workers=WORKER_PARALLEL) as pool:
            for i, (src, dst) in enumerate(jobs):
                pool.submit(work, i, src, dst)
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
            [sys.executable, str(Path(__file__).resolve()), "--worker"],
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
    """任务队列一行：轻量 tk 控件（比 CTk 控件创建快一个量级）。"""

    def __init__(self, master, path: Path, on_remove):
        super().__init__(master, bg=C_CARD, highlightbackground=C_BORDER,
                         highlightthickness=1, bd=0)
        self.path = path
        self.on_remove = on_remove

        tk.Label(self, text="▸", bg=C_CARD, fg=C_CYAN,
                 font=(MONO, 11)).pack(side="left", padx=(10, 2))
        self.name_label = tk.Label(self, text=path.name, anchor="w", bg=C_CARD,
                                   fg=C_TEXT, font=(FONT, 10))
        self.name_label.pack(side="left", fill="x", expand=True)

        self.remove_btn = tk.Label(self, text="✕", bg=C_CARD, fg=C_DIM,
                                   font=(FONT, 11), cursor="hand2", padx=8)
        self.remove_btn.pack(side="right", padx=(2, 6), pady=7)
        self.remove_btn.bind("<Button-1>", lambda e: self.on_remove(self))
        self.remove_btn.bind("<Enter>", lambda e: self.remove_btn.configure(fg=C_RED))
        self.remove_btn.bind("<Leave>", lambda e: self.remove_btn.configure(fg=C_DIM))

        self.status_label = tk.Label(self, text=STATUS_STYLE["waiting"][0], width=9,
                                     bg=C_CARD, fg=STATUS_STYLE["waiting"][1],
                                     font=(FONT, 10))
        self.status_label.pack(side="right", padx=6)

    def set_status(self, status: str):
        text, color = STATUS_STYLE[status]
        self.status_label.configure(text=text, fg=color)


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

        self.title("从微信选择文件")
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
        ctk.CTkLabel(head, text="◢ 微信文件", text_color=C_CYAN,
                     font=ctk.CTkFont(family=MONO, size=17, weight="bold")).pack(side="left")
        ctk.CTkLabel(head, text=" WECHAT INBOX", text_color=C_DIM,
                     font=ctk.CTkFont(family=MONO, size=11)).pack(side="left", pady=(4, 0))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=18, pady=(4, 6))
        bar.grid_columnconfigure(0, weight=1)
        self.filter_var = ctk.StringVar()
        self.filter_var.trace_add("write", self._schedule_render)   # 防抖，打字不卡
        ctk.CTkEntry(bar, textvariable=self.filter_var, placeholder_text="🔍 搜索文件名…",
                     font=ctk.CTkFont(family=FONT, size=12),
                     fg_color=C_TERM, border_color=C_BORDER, text_color=C_TEXT,
                     ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._small_btn(bar, "全选", self._select_all).grid(row=0, column=1, padx=(0, 6))
        self._small_btn(bar, "清空选择", self._select_none).grid(row=0, column=2)

        self.list_frame = ctk.CTkScrollableFrame(
            self, fg_color=C_PANEL, corner_radius=10,
            scrollbar_button_color=C_BORDER, scrollbar_button_hover_color=C_CYAN_D,
        )
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 6))
        self.list_frame.grid_columnconfigure(0, weight=1)
        self.hint_label = ctk.CTkLabel(
            self.list_frame, text="正在扫描微信文件目录…",
            font=ctk.CTkFont(family=MONO, size=12), text_color=C_DIM,
        )
        self.hint_label.grid(row=0, column=0, pady=30)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew", padx=18, pady=(4, 14))
        bottom.grid_columnconfigure(0, weight=1)
        self.count_var = ctk.StringVar(value="已选 0 个")
        ctk.CTkLabel(bottom, textvariable=self.count_var,
                     font=ctk.CTkFont(family=MONO, size=12), text_color=C_DIM
                     ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(bottom, text="＋ 添加到队列", height=36, corner_radius=6,
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
        # 优先用上次缓存的目录，秒开；缓存失效才全盘探测
        cached = [Path(p) for p in self.app.config.get("wechat_roots", [])]
        roots = [p for p in cached if p.is_dir()]
        if not roots:
            roots = find_wechat_roots()
            if roots:
                self.app.config["wechat_roots"] = [str(p) for p in roots]
                self.app._save_config()
        items = scan_wechat_files(roots)
        self.app.ui_queue.put(("wechat_items", self, items))

    def populate(self, items):
        self.items = items
        self.render_limit = self.PAGE
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
        for w in self.row_widgets:
            w.destroy()
        self.row_widgets.clear()
        if not self.items:
            self.hint_label.configure(text="未找到微信接收的文件\n（请确认微信已登录并收到过文件）")
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
                    text=f"▼ 加载更多（还有 {remain} 条）",
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
            lbl = tk.Label(self.list_frame, text=f'没有匹配「{self.filter_var.get()}」的文件',
                           bg=C_PANEL, fg=C_DIM, font=(FONT, 10))
            lbl.grid(row=0, column=0, pady=20)
            self.row_widgets.append(lbl)
        self._update_count()

    def _load_more(self):
        self.render_limit += self.PAGE
        self._render()

    def _update_count(self):
        n = sum(1 for v in self.vars.values() if v.get())
        self.count_var.set(f"已选 {n} 个")

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
            self.app._log(f"微信：已加入 {len(selected)} 个文件", "sys")
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

        ctk.CTkLabel(self, text="◢ 提示 NOTICE", text_color=C_CYAN,
                     font=ctk.CTkFont(family=MONO, size=15, weight="bold"),
                     ).pack(anchor="w", padx=20, pady=(18, 8))
        ctk.CTkLabel(self, text=message, justify="left", anchor="w",
                     font=ctk.CTkFont(family=FONT, size=13), text_color=C_TEXT,
                     wraplength=420,
                     ).pack(anchor="w", padx=20, fill="x")

        self.dont_show_var = ctk.BooleanVar(value=False)
        if dont_show_key:
            ctk.CTkCheckBox(self, text="不再提示", variable=self.dont_show_var,
                            font=ctk.CTkFont(family=FONT, size=12), text_color=C_DIM,
                            fg_color=C_CYAN, hover_color=C_CYAN_H, border_color=C_BORDER,
                            ).pack(anchor="w", padx=20, pady=(12, 0))

        ctk.CTkButton(self, text="知道了", height=36, corner_radius=6, width=140,
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
            self.app.config[self.dont_show_key] = True
            self.app._save_config()
        self.destroy()


class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.config = self._load_config()
        self.files: list[Path] = []
        self.rows: dict[Path, FileRow] = {}
        self.ui_queue: queue.Queue = queue.Queue()
        self.converting = False
        self.picker: WeChatPicker | None = None
        self.worker_man = WorkerManager()
        self._active_procs: set = set()

        self.title("MarkItDown 转换器")
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
        threading.Timer(0.6, self.worker_man.prewarm).start()
        self._log("SYSTEM READY — 等待任务输入", "sys")
        self._maybe_open_manual()
        if not lib_available():
            self._fatal("未找到 markitdown 库，请确认已安装。")

    def _maybe_open_manual(self):
        """首次运行时自动打开使用说明书（只此一次，之后可在安装目录手动查看）。"""
        if self.config.get("manual_shown") or not MANUAL_FILE.exists():
            return
        self.config["manual_shown"] = True
        self._save_config()
        try:
            os.startfile(MANUAL_FILE)  # noqa: S606
        except OSError:
            pass

    # ---------- 配置读写 ----------
    def _load_config(self) -> dict:
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_config(self):
        try:
            CONFIG_FILE.write_text(
                json.dumps(self.config, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _on_close(self):
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
        ctk.CTkLabel(title_row, text=" 转换器", text_color=C_PURPLE,
                     font=ctk.CTkFont(family=FONT, size=20, weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text=f"支持格式  [ {SUPPORTED_HINT} ]",
                     font=ctk.CTkFont(family=FONT, size=11), text_color=C_DIM
                     ).pack(anchor="w", pady=(3, 0))

        # ── 拖拽区 ──
        self.drop_frame = ctk.CTkFrame(self, fg_color=C_PANEL, corner_radius=10,
                                       border_width=2, border_color=C_CYAN_D)
        self.drop_frame.grid(row=1, column=0, sticky="ew", padx=22, pady=8)
        self.drop_label = ctk.CTkLabel(
            self.drop_frame, text="⇩  拖 入 文 件\nDRAG & DROP FILES HERE",
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
        self._section("任务队列 TASK QUEUE", 2)
        self.list_frame = ctk.CTkScrollableFrame(
            self, fg_color=C_PANEL, corner_radius=10,
            scrollbar_button_color=C_BORDER, scrollbar_button_hover_color=C_CYAN_D,
        )
        self.list_frame.grid(row=3, column=0, sticky="nsew", padx=22, pady=(0, 6))
        self.list_frame.grid_columnconfigure(0, weight=1)
        self.empty_label = ctk.CTkLabel(
            self.list_frame, text="[ 队列为空 ]",
            font=ctk.CTkFont(family=MONO, size=12), text_color=C_DIM,
        )
        self.empty_label.grid(row=0, column=0, pady=26)

        # ── 按钮行 ──
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=4, column=0, sticky="ew", padx=22)
        self._btn(btns, "＋ 添加文件", self._pick_files, accent=True).pack(side="left")
        self._btn(btns, "💬 微信文件", self._open_wechat, accent=True).pack(side="left", padx=8)
        self._btn(btns, "清空列表", self._clear_files).pack(side="left")

        # ── 输出目录 ──
        self._section("输出目录 OUTPUT DIR", 5)
        out_row = ctk.CTkFrame(self, fg_color="transparent")
        out_row.grid(row=6, column=0, sticky="ew", padx=22)
        out_row.grid_columnconfigure(0, weight=1)
        default_out = self.config.get("output_dir") or str(SCRIPT_DIR / "输出")
        self.out_var = ctk.StringVar(value=default_out)
        self.out_entry = ctk.CTkEntry(
            out_row, textvariable=self.out_var,
            font=ctk.CTkFont(family=MONO, size=12),
            fg_color=C_TERM, border_color=C_BORDER, text_color=C_CYAN,
        )
        self.out_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._btn(out_row, "浏览…", self._pick_output_dir).grid(row=0, column=1)

        # ── 执行终端 ──
        self._section("执行终端 TERMINAL", 7)
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

        self.status_var = ctk.StringVar(value="[ READY ] 准备就绪")
        ctk.CTkLabel(self, textvariable=self.status_var,
                     font=ctk.CTkFont(family=MONO, size=12), text_color=C_DIM
                     ).grid(row=10, column=0, sticky="w", padx=24, pady=(4, 0))

        # ── 转换按钮 ──
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=11, column=0, sticky="ew", padx=22, pady=(8, 16))
        bottom.grid_columnconfigure(0, weight=1)
        self.convert_btn = ctk.CTkButton(
            bottom, text="▶ 开始转换 EXECUTE", height=44,
            font=ctk.CTkFont(family=FONT, size=15, weight="bold"),
            fg_color=C_CYAN, hover_color=C_CYAN_H, text_color=C_BG,
            corner_radius=8, command=self._start_convert,
        )
        self.convert_btn.grid(row=0, column=0, sticky="ew")
        self._btn(bottom, "📂 打开输出目录", self._open_output).grid(row=0, column=1, padx=(8, 0))
        self._btn(bottom, "📄 日志中心", self._open_logs).grid(row=0, column=2, padx=(8, 0))

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
        tb = self.term._textbox
        self.term.configure(state="normal")
        tb.insert("end", text + "\n", tag)
        if int(tb.index("end-1c").split(".")[0]) > 500:   # 日志上限，防膨胀
            tb.delete("1.0", "201.0")
        tb.see("end")
        self.term.configure(state="disabled")

    # ---------- 文件管理 ----------
    def _parse_drop(self, data: str) -> list[Path]:
        parts, cur, in_brace = [], "", False
        for ch in data:
            if ch == "{":
                in_brace = True
            elif ch == "}":
                in_brace = False
                parts.append(cur)
                cur = ""
            elif ch == " " and not in_brace:
                if cur:
                    parts.append(cur)
                    cur = ""
            else:
                cur += ch
        if cur:
            parts.append(cur)
        return [Path(p) for p in parts]

    def _on_drop(self, event):
        self._drop_hover(False)
        self.add_files(self._parse_drop(event.data))

    def _pick_files(self):
        from tkinter import filedialog
        paths = filedialog.askopenfilenames(title="选择要转换的文件")
        if paths:
            self.add_files([Path(p) for p in paths])

    def add_files(self, paths: list[Path]):
        new: list[Path] = []
        for p in paths:
            if not p.is_file():
                continue
            p = p.resolve()
            if p in self.rows or p in self.files:
                continue
            self.files.append(p)
            new.append(p)
        if not new:
            return
        self.empty_label.grid_remove()
        self.status_var.set(f"[ QUEUE ] 已加入 {len(self.files)} 个任务")
        self._render_rows(new)          # 分批渲染，大批量添加不卡界面
        self._maybe_media_notice(new)

    def _render_rows(self, new: list[Path], idx: int = 0):
        """每次最多创建 60 行控件，剩余的交给事件循环下一拍，保持界面流畅。"""
        for p in new[idx:idx + 60]:
            if p not in self.files:      # 渲染期间被用户移除了
                continue
            if p in self.rows:           # 已渲染（异常情况兜底）
                continue
            self.rows[p] = FileRow(self.list_frame, p, self._remove_row)
        self._reflow_rows()
        if idx + 60 < len(new):
            self.after(10, lambda: self._render_rows(new, idx + 60))

    def _reflow_rows(self):
        """按文件顺序紧凑重排所有行：消除删除留下的空隙，杜绝行号重叠。"""
        for i, p in enumerate(self.files):
            row = self.rows.get(p)
            if row is not None:
                row.grid_configure(row=i, column=0, sticky="ew", pady=3, padx=2)

    def _maybe_media_notice(self, added: list[Path]):
        """添加图片/音频类文件时弹窗告知处理方式（每次运行只弹一次，可勾选永久关闭）。"""
        if self.config.get("media_notice_shown") or getattr(self, "_media_notice_done", False):
            return
        n_img = sum(1 for p in added if p.suffix.lower() in IMG_EXTS)
        n_aud = sum(1 for p in added if p.suffix.lower() in AUDIO_EXTS)
        if not n_img and not n_aud:
            return
        self._media_notice_done = True
        ocr_ok = find_spec("winsdk") is not None
        lines = []
        if n_img:
            if ocr_ok:
                lines.append(f"• 图片 × {n_img}：将自动调用 Windows OCR 在本地识别图中文字，"
                             "识别结果会保存为 .md 文件")
            else:
                lines.append(f"• 图片 × {n_img}：未检测到 OCR 组件，可能无法提取图中文字")
        if n_aud:
            lines.append(f"• 音频 × {n_aud}：暂不支持语音转写，将标记为「无文字」")
        if ocr_ok:
            lines.append("")
            lines.append("全部识别均在本地完成，不会上传任何内容。")
        NoticeDialog(self, "媒体文件提示", "\n".join(lines), "media_notice_shown")

    def _remove_row(self, row: FileRow):
        if self.converting:
            return
        row.destroy()
        self.files.remove(row.path)
        del self.rows[row.path]
        self._reflow_rows()
        if not self.rows:
            self.empty_label.grid()

    def _clear_files(self):
        if self.converting:
            return
        for row in list(self.rows.values()):
            row.destroy()
        self.files.clear()
        self.rows.clear()
        self.empty_label.grid()
        self.progress.set(0)
        self.status_var.set("[ READY ] 准备就绪")

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
        d = filedialog.askdirectory(title="选择输出文件夹", initialdir=self.out_var.get())
        if d:
            self.out_var.set(d)
            self.config["output_dir"] = d
            self._save_config()

    def _open_output(self):
        d = Path(self.out_var.get())
        d.mkdir(parents=True, exist_ok=True)
        os.startfile(d)  # noqa: S606

    def _open_logs(self):
        """打开日志中心：查看/导出安装日志与更新日志（只读模式，不执行更新）。"""
        updater = SCRIPT_DIR / "update.pyw"
        if not updater.exists():
            self._log("未找到日志中心（update.pyw），当前为便携模式运行", "warn")
            return
        try:
            subprocess.Popen([sys.executable, str(updater), "--view"],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as e:
            self._log(f"无法打开日志中心：{e}", "err")

    # ---------- 转换流程 ----------
    def _start_convert(self):
        if self.converting:
            return
        if not self.files:
            self.status_var.set("[ WAIT ] 请先添加要转换的文件")
            return
        out_dir = Path(self.out_var.get().strip())
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.status_var.set(f"[ ERROR ] 输出文件夹无效：{e}")
            return
        if not out_dir.is_dir():
            self.status_var.set("[ ERROR ] 输出路径不是一个文件夹")
            return
        self.config["output_dir"] = str(out_dir)
        self._save_config()

        self.converting = True
        self.convert_btn.configure(state="disabled", text="◉ 转换中 RUNNING…")
        self.progress.set(0)
        total = len(self.files)
        self.status_var.set(f"[ RUN ] 正在转换 0 / {total} …")
        self._log(f"── 任务开始，共 {total} 个文件 ──", "sys")

        threading.Thread(target=self._worker, args=(out_dir,), daemon=True).start()

    def _worker(self, out_dir: Path):
        """把整批任务交给预热好的子进程执行，读取它的进度输出。界面进程零负担。"""
        files = list(self.files)
        total = len(files)
        done = ok = empty = 0
        t0 = time.time()

        jobs, reserved = [], set()
        for p in files:
            dst = unique_output_path(out_dir, p.stem, reserved)
            reserved.add(dst)
            jobs.append([str(p), str(dst)])
            self.ui_queue.put(("log", f'$ markitdown "{p.name}" -o "{dst.name}"', "cmd"))

        proc = self.worker_man.get()
        self._active_procs.add(proc)
        reported: set = set()
        try:
            proc.stdin.write(json.dumps(jobs) + "\n")   # 常驻进程：不能 close stdin
            proc.stdin.flush()
        except (ValueError, BrokenPipeError, OSError):
            # 写入失败说明子进程已坏：杀掉换新，整批标记失败
            self.worker_man.kill()
            for i in range(total):
                self.ui_queue.put(("status", files[i], "failed"))
                self.ui_queue.put(("log", "  ✗ 失败  工作进程异常", "err"))
                self.ui_queue.put(("progress", i + 1, total))
            self._active_procs.discard(proc)
            self.ui_queue.put(("finished", 0, 0, total, time.time() - t0))
            return
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ev, i = msg.get("event"), msg.get("i")
                if ev == "engine_error":
                    # 子进程启动即失败（引擎没加载起来）：真实原因 + 修复指引，整批标记失败
                    self.ui_queue.put(("log", f"  ✗ 转换引擎加载失败：{msg.get('msg', '')}", "err"))
                    self.ui_queue.put(("log", "  ➜ 请运行开始菜单「检查更新 · 日志中心」自动修复；若仍失败，请重新运行安装包", "err"))
                    for j in range(total):
                        if j not in reported:
                            reported.add(j)
                            done += 1
                            self.ui_queue.put(("status", files[j], "failed"))
                            self.ui_queue.put(("progress", done, total))
                    break
                if ev == "start" and i is not None:
                    self.ui_queue.put(("status", files[i], "running"))
                elif ev in ("done", "fail", "empty") and i is not None:
                    reported.add(i)
                    done += 1
                    if ev == "done":
                        ok += 1
                        self.ui_queue.put(("status", files[i], "done"))
                        tag = "（OCR 识别）" if msg.get("ocr") else ""
                        if msg.get("imgs"):
                            tag += f"（图片×{msg['imgs']}）"
                        self.ui_queue.put(("log", f"  ✓ 完成{tag}  {msg.get('secs', 0):.2f}s", "ok"))
                    elif ev == "empty":
                        empty += 1
                        self.ui_queue.put(("status", files[i], "empty"))
                        hint = EMPTY_HINTS.get(files[i].suffix.lower(), DEFAULT_EMPTY_HINT)
                        self.ui_queue.put(("log", f"  ⚠ 无文字内容，未生成文件（{hint}）", "warn"))
                    else:
                        self.ui_queue.put(("status", files[i], "failed"))
                        self.ui_queue.put(("log", f"  ✗ 失败  {msg.get('msg', '')}", "err"))
                    self.ui_queue.put(("progress", done, total))
                elif ev == "all_done":
                    break
        except (BrokenPipeError, OSError):
            pass
        finally:
            self._active_procs.discard(proc)   # 常驻进程：不关闭不杀死，留给下一批复用

        # 子进程异常退出时，把没收到结果的文件标记为失败
        for i in range(total):
            if i not in reported:
                done += 1
                self.ui_queue.put(("status", files[i], "failed"))
                self.ui_queue.put(("log", "  ✗ 失败  工作进程异常", "err"))
                self.ui_queue.put(("progress", done, total))
        self.ui_queue.put(("finished", ok, empty, total, time.time() - t0))
        # 为下一批再预热一个备用进程
        threading.Thread(target=self.worker_man.prewarm, daemon=True).start()

    def _poll_queue(self):
        try:
            while True:
                item = self.ui_queue.get_nowait()
                kind = item[0]
                if kind == "status":
                    _, p, st = item
                    if p in self.rows:
                        self.rows[p].set_status(st)
                elif kind == "log":
                    _, text, tag = item
                    self._log(text, tag)
                elif kind == "wechat_items":
                    _, picker, items = item
                    try:
                        if picker.winfo_exists():
                            picker.populate(items)
                    except Exception:
                        pass
                elif kind == "progress":
                    _, done, total = item
                    self.progress.set(done / total)
                    self.status_var.set(f"[ RUN ] 正在转换 {done} / {total} …")
                elif kind == "finished":
                    _, ok, empty, total, secs = item
                    self.converting = False
                    self.convert_btn.configure(state="normal", text="▶ 开始转换 EXECUTE")
                    fail = total - ok - empty
                    parts = [f"完成 {ok}"]
                    if empty:
                        parts.append(f"无内容 {empty}")
                    if fail:
                        parts.append(f"失败 {fail}")
                    summary = "，".join(parts)
                    if ok == total:
                        self.status_var.set(f"[ DONE ] 全部完成 {total}/{total}，用时 {secs:.1f}s")
                        self._log(f"── 任务完成：{total}/{total}，总耗时 {secs:.1f}s ──", "sys")
                    else:
                        self.status_var.set(f"[ WARN ] {summary}，用时 {secs:.1f}s")
                        self._log(f"── 任务结束：{summary} ──", "warn")
        except queue.Empty:
            pass
        self.after(80, self._poll_queue)


if __name__ == "__main__":
    app = App()
    app.mainloop()
