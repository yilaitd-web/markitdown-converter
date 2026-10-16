# -*- coding: utf-8 -*-
"""MarkItDown 转换器 —— 日志工具（安装程序与更新器共用）

- export_txt：导出 UTF-8（带 BOM）文本，记事本/微信直接打开不乱码
- export_pdf：纯标准库生成 PDF，使用 PDF 预定义中文字体 STSong-Light
  （UniGB-UCS2-H），无需安装任何第三方库，离线可用
- collect_diagnostics：汇总系统信息、组件版本、安装/更新日志，便于回传定位问题
"""
import datetime
import platform
import subprocess
import sys
from pathlib import Path

# ---------------- TXT ----------------

def export_txt(text: str, path) -> None:
    Path(path).write_bytes(b"\xef\xbb\xbf" + text.replace("\r\n", "\n").replace("\r", "\n")
                           .replace("\n", "\r\n").encode("utf-8", errors="replace"))


# ---------------- PDF ----------------
_PAGE_W, _PAGE_H = 595, 842      # A4，单位 pt
_MARGIN = 45
_FONT_SIZE = 9
_LINE_H = 13
_TITLE_SIZE = 12
_MAX_UNITS = 56.0                # 每行约 56 个全角单位（CJK=1，ASCII≈0.5）


def _char_units(ch: str) -> float:
    cp = ord(ch)
    if cp == 9:                  # 制表符按 4 空格宽
        return 2.0
    # CJK 及全角字符按全宽，其余按半宽估算
    if (0x1100 <= cp <= 0x115F or 0x2E80 <= cp <= 0x9FFF or 0xA000 <= cp <= 0xA4CF
            or 0xAC00 <= cp <= 0xD7A3 or 0xF900 <= cp <= 0xFAFF
            or 0xFF00 <= cp <= 0xFF60 or 0xFFE0 <= cp <= 0xFFE6
            or 0x20000 <= cp <= 0x2FA1F):
        return 1.0
    return 0.5


_ASCII_PER_LINE = int(_MAX_UNITS / 0.5)   # 纯 ASCII 行每行可放的字符数


def _wrap(line: str):
    """按估算宽度折行；控制字符替换为空格。"""
    line = "".join(ch if (ch == "\t" or ord(ch) >= 32) else " " for ch in line)
    line = line.expandtabs(4)
    if not line:
        return [""]
    if line.isascii():
        # 日志绝大多数是 pip 的英文输出：每字符等宽半格，直接按长度切，免去逐字符循环
        n = _ASCII_PER_LINE
        return [line[i:i + n] for i in range(0, len(line), n)]
    out, cur, units = [], "", 0.0
    for ch in line:
        u = _char_units(ch)
        if units + u > _MAX_UNITS and cur:
            out.append(cur)
            cur, units = "", 0.0
        cur += ch
        units += u
    out.append(cur)
    return out


def _hex(s: str) -> str:
    """转 UTF-16BE 十六进制串（PDF 十六进制字符串语法）。"""
    s = "".join(ch if ord(ch) <= 0xFFFF else "?" for ch in s)
    return s.encode("utf-16-be", errors="replace").hex().upper()


def _obj(body: bytes) -> bytes:
    return body if body.endswith(b"\n") else body + b"\n"


_PDF_TITLES = {"zh": "MarkItDown 转换器 运行日志", "en": "MarkItDown Converter Log"}


def export_pdf(text: str, path, title: str | None = None, lang: str = "zh") -> None:
    if title is None:
        title = _PDF_TITLES.get(lang, _PDF_TITLES["zh"])
    page_fmt = "第 {a} / {b} 页" if lang == "zh" else "Page {a} / {b}"
    norm = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for raw in norm.split("\n"):
        lines.extend(_wrap(raw))
    if not lines:
        lines = [""]

    head_room = 34               # 标题区高度
    per_page = max(1, (_PAGE_H - _MARGIN * 2 - head_room) // _LINE_H)
    pages = [lines[i:i + per_page] for i in range(0, len(lines), per_page)]

    n_pages = len(pages)
    font_obj = 3 + n_pages * 2           # 页面对象与内容对象之后是字体三件套
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(n_pages))

    objs: dict[int, bytes] = {}
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[2] = f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode()
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    for pi, chunk in enumerate(pages):
        page_no = 3 + pi * 2
        cont_no = page_no + 1
        stream = [b"BT /F1 %d Tf %d %d Td <%s> Tj ET"
                  % (_TITLE_SIZE, _MARGIN, _PAGE_H - _MARGIN + 6, _hex(f"{title}    {stamp}").encode())]
        stream.append(b"BT /F1 8 Tf %d %d Td <%s> Tj ET"
                      % (_MARGIN, _MARGIN - 16,
                         _hex(page_fmt.format(a=pi + 1, b=n_pages)).encode()))
        body = [f"BT /F1 {_FONT_SIZE} Tf {_LINE_H} TL {_MARGIN} "
                f"{_PAGE_H - _MARGIN - head_room} Td".encode()]
        for ln in chunk:
            body.append(b"<" + _hex(ln).encode() + b"> Tj T*")
        body.append(b"ET")
        data = b"\n".join(stream + body)
        objs[cont_no] = (b"<< /Length %d >>\nstream\n" % len(data)) + data + b"\nendstream"
        objs[page_no] = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_PAGE_W} {_PAGE_H}] "
                         f"/Resources << /Font << /F1 {font_obj} 0 R >> >> "
                         f"/Contents {cont_no} 0 R >>").encode()

    # 注意：不要加 /ToUnicode。UniGB-UCS2-H 编码下内容流即 UCS-2 码点，
    # 阅读器（pdfium/Adobe）无需 ToUnicode 即可正确复制搜索；pdfminer 自带
    # Adobe-GB1 CID→Unicode 映射也能正确提取。若强行加 identity ToUnicode，
    # pdfminer 会把它错误地套在 CID 上，反而提取出乱码（实测验证 2026-10-15）。
    objs[font_obj] = (f"<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light "
                      f"/Encoding /UniGB-UCS2-H /DescendantFonts [{font_obj + 1} 0 R] >>").encode()
    # /W [1 95 500]：ASCII（UniGB-UCS2-H 下映射到 CID 1~95）按半角宽度排版。
    # 缺了它所有字形都按默认全角 1000 排，英文字母间距拉大一倍，pip 报错这类
    # 长英文行的后半截直接跑出页面右边界被截掉（实测验证 2026-10-16）
    objs[font_obj + 1] = (f"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light "
                          f"/CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 5 >> "
                          f"/DW 1000 /W [1 95 500] "
                          f"/FontDescriptor {font_obj + 2} 0 R >>").encode()
    objs[font_obj + 2] = (b"<< /Type /FontDescriptor /FontName /STSong-Light /Flags 4 "
                          b"/FontBBox [0 -200 1000 900] /ItalicAngle 0 /Ascent 880 "
                          b"/Descent -120 /CapHeight 700 /StemV 80 >>")

    out = bytearray(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode() + _obj(objs[num]) + b"endobj\n"
    xref_pos = len(out)
    size = max(objs) + 1
    out += f"xref\n0 {size}\n".encode()
    out += b"0000000000 65535 f \n"
    for num in range(1, size):
        out += f"{offsets[num]:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n").encode()
    Path(path).write_bytes(bytes(out))


# ---------------- 诊断报告 ----------------

def _decode_tail(data: bytes) -> str:
    """解码从文件尾部切下的字节切片。切割点可能落在多字节字符中间：
    严格解码失败时从头部最多再丢 3 字节对齐重试（UTF-8 字符最长 4 字节），
    全部失败才换下一编码——这样 UTF-8 日志不会因切点残缺而落到 GBK
    被静默错解成乱码；cp1252 兜住英文 Windows 上的安装日志（ANSI=西欧码页，
    含重音字符的用户名等）。GBK 为双字节编码，切点残缺最多再丢 1 字节即可对齐。"""
    for enc in ("utf-8-sig", "gbk", "cp1252"):
        for skip in range(4):
            try:
                return data[skip:].decode(enc)
            except (UnicodeDecodeError, ValueError):
                continue
    return data.decode("utf-8", errors="replace")


def _read_log(path: Path, limit_chars: int = 400_000, lang: str = "zh") -> str:
    # 只从文件尾部读够用的字节（UTF-8 单字符最长 4 字节），大日志不必全量读入解码
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - limit_chars * 4))
            data = f.read()
    except OSError:
        return f"（未找到 {path.name}）" if lang == "zh" else f"({path.name} not found)"
    truncated = size > limit_chars * 4
    text = _decode_tail(data)
    if truncated:
        # 丢弃首个可能从多字节字符中间截断的残行
        nl = text.find("\n")
        text = text[nl + 1:] if nl != -1 else ""
    if len(text) > limit_chars:
        note = (f"……（日志过长，仅保留最后 {limit_chars} 字符）……\n" if lang == "zh"
                else f"......(the log is too long; only the last {limit_chars} characters were kept)......\n")
        text = note + text[-limit_chars:]
    return text


def collect_diagnostics(app_dir, extra_note: str = "", lang: str = "zh") -> str:
    """汇总诊断信息：系统环境、组件版本、安装/更新日志全文（按语言出报告）。"""
    app_dir = Path(app_dir)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    zh = (lang == "zh")
    ver = "未知" if zh else "unknown"
    try:
        ver = (app_dir / "VERSION").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        pass
    if zh:
        head = ["  MarkItDown 转换器 诊断报告", f"  生成时间: {now}"]
        fields = [("应用版本", ver), ("安装目录", app_dir), ("操作系统", platform.platform()),
                  ("当前 Python", f"{sys.version.split()[0]}  ({sys.executable})")]
        note_label = "备注"
        pip_header = "组件版本（pip list）"
        pip_fail = "（获取组件版本失败：{e}）"
        pip_empty = "（pip list 无输出）"
        no_venv = "（未找到虚拟环境，可能尚未完成安装）"
        log_names = ["安装日志.txt", "更新日志.txt", "Install Log.txt", "Update Log.txt"]
    else:
        head = ["  MarkItDown Converter Diagnostic Report", f"  Generated: {now}"]
        fields = [("App version", ver), ("Install folder", app_dir), ("OS", platform.platform()),
                  ("Python", f"{sys.version.split()[0]}  ({sys.executable})")]
        note_label = "Note"
        pip_header = "Component versions (pip list)"
        pip_fail = "(Failed to get component versions: {e})"
        pip_empty = "(pip list produced no output)"
        no_venv = "(Virtual environment not found; the installation may be incomplete)"
        log_names = ["Install Log.txt", "Update Log.txt", "安装日志.txt", "更新日志.txt"]
    parts = ["=" * 60, *head, "=" * 60]
    parts += [f"{label:<6}: {value}" for label, value in fields]
    if extra_note:
        parts.append(f"{note_label:<6}: {extra_note}")

    venv_py = app_dir / ".venv" / "Scripts" / "python.exe"
    parts += ["", "-" * 60, pip_header, "-" * 60]
    if venv_py.exists():
        try:
            proc = subprocess.run(
                [str(venv_py), "-m", "pip", "list", "--disable-pip-version-check"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            parts.append(proc.stdout.strip() or proc.stderr.strip() or pip_empty)
        except Exception as e:  # noqa: BLE001
            parts.append(pip_fail.format(e=e))
    else:
        parts.append(no_venv)

    # 只收录实际存在的日志文件；语言切换/升级安装后两种文件名都找得到
    seen = set()
    for name in log_names:
        if name in seen or not (app_dir / name).exists():
            continue
        seen.add(name)
        parts += ["", "-" * 60, name, "-" * 60, _read_log(app_dir / name, lang=lang)]
    if not seen:
        parts += ["", "-" * 60, log_names[0], "-" * 60, _read_log(app_dir / log_names[0], lang=lang)]
    return "\n".join(parts)
