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


def _wrap(line: str):
    """按估算宽度折行；控制字符替换为空格。"""
    line = "".join(ch if (ch == "\t" or ord(ch) >= 32) else " " for ch in line)
    line = line.expandtabs(4)
    if not line:
        return [""]
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


def export_pdf(text: str, path, title: str = "MarkItDown 转换器 运行日志") -> None:
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
                         _hex(f"第 {pi + 1} / {n_pages} 页").encode()))
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
    objs[font_obj + 1] = (f"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light "
                          f"/CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 5 >> "
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

def _read_log(path: Path, limit_chars: int = 400_000) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return f"（未找到 {path.name}）"
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = data.decode("utf-8", errors="replace")
    if len(text) > limit_chars:
        text = f"……（日志过长，仅保留最后 {limit_chars} 字符）……\n" + text[-limit_chars:]
    return text


def collect_diagnostics(app_dir, extra_note: str = "") -> str:
    """汇总诊断信息：系统环境、组件版本、安装/更新日志全文。"""
    app_dir = Path(app_dir)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ver = "未知"
    try:
        ver = (app_dir / "VERSION").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        pass
    parts = [
        "=" * 60,
        "  MarkItDown 转换器 诊断报告",
        f"  生成时间: {now}",
        "=" * 60,
        f"应用版本   : {ver}",
        f"安装目录   : {app_dir}",
        f"操作系统   : {platform.platform()}",
        f"当前 Python: {sys.version.split()[0]}  ({sys.executable})",
    ]
    if extra_note:
        parts.append(f"备注       : {extra_note}")

    venv_py = app_dir / ".venv" / "Scripts" / "python.exe"
    parts += ["", "-" * 60, "组件版本（pip list）", "-" * 60]
    if venv_py.exists():
        try:
            proc = subprocess.run(
                [str(venv_py), "-m", "pip", "list", "--disable-pip-version-check"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            parts.append(proc.stdout.strip() or proc.stderr.strip() or "（pip list 无输出）")
        except Exception as e:  # noqa: BLE001
            parts.append(f"（获取组件版本失败：{e}）")
    else:
        parts.append("（未找到虚拟环境，可能尚未完成安装）")

    for name in ("安装日志.txt", "更新日志.txt"):
        parts += ["", "-" * 60, name, "-" * 60, _read_log(app_dir / name)]
    return "\n".join(parts)
