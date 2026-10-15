# -*- coding: utf-8 -*-
"""MarkItDown 转换器 —— 检查更新 · 日志中心

- 实时显示更新过程，并同步逐行写入「更新日志.txt」（UTF-8，含时间戳）
- 可切换查看：更新日志 / 安装日志 / 诊断报告
- 一键导出 TXT 或 PDF（PDF 为纯标准库生成，支持中文，见 logtools.py）
- 多线路安装：GitHub 直连 → 两个加速代理 → PyPI 镜像；每步装完即校验

从开始菜单「MarkItDown 转换器 > 检查更新」启动；
加 --view 参数启动则只打开日志中心，不执行更新。
"""
import datetime
import os
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

SCRIPT_DIR = Path(__file__).resolve().parent
VENV_PY = SCRIPT_DIR / ".venv" / "Scripts" / "python.exe"
UPDATE_LOG = SCRIPT_DIR / "更新日志.txt"
INSTALL_LOG = SCRIPT_DIR / "安装日志.txt"
sys.path.insert(0, str(SCRIPT_DIR))
import logtools  # noqa: E402

PYPI_SPEC = "markitdown[pptx,docx,xlsx,xls,pdf,outlook,audio-transcription]"
GITHUB_SPEC = ("markitdown[pptx,docx,xlsx,xls,pdf,outlook,audio-transcription] @ "
               "https://codeload.github.com/microsoft/markitdown/zip/refs/heads/main#subdirectory=packages/markitdown")
GITHUB_PROXY_SPEC = ("markitdown[pptx,docx,xlsx,xls,pdf,outlook,audio-transcription] @ "
                     "https://gh-proxy.com/https://codeload.github.com/microsoft/markitdown/zip/refs/heads/main#subdirectory=packages/markitdown")
OTHER_PKGS = ["customtkinter", "tkinterdnd2"]
# winsdk（Windows OCR）只发布到 cp313 的预编译包，3.14+ 装不上属正常，仅影响图片 OCR；
# pypdfium2 把扫描件/图片型 PDF 渲染成图片供 OCR（wheel 内置 pdfium 二进制，全版本可装）
OPTIONAL_PKGS = ["winsdk", "pypdfium2"]
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


class Updater(tk.Tk):
    def __init__(self, view_only: bool):
        super().__init__()
        self.title("MarkItDown 转换器 — 检查更新 · 日志中心")
        self.geometry("780x560")
        self.minsize(660, 460)
        self.configure(bg=C_BG)
        self._running = False
        self._view = "update"
        self._report_cache: str | None = None
        self._log_fp = None

        tk.Label(self, text="◢ 检查更新 · 日志中心 UPDATE & LOGS", fg=C_CYAN, bg=C_BG,
                 font=("Consolas", 13, "bold")).pack(anchor="w", padx=14, pady=(12, 6))

        # ── 视图切换 + 操作按钮 ──
        bar = tk.Frame(self, bg=C_BG)
        bar.pack(fill="x", padx=14, pady=(0, 6))
        self._view_btns = {}
        for key, label in (("update", "更新日志"), ("install", "安装日志"), ("report", "诊断报告")):
            b = tk.Button(bar, text=label, command=lambda k=key: self._show_view(k),
                          bg=C_PANEL, fg=C_DIM, activebackground=C_CYAN_D,
                          activeforeground="white", bd=0, padx=10, pady=3,
                          font=(FONT, 9))
            b.pack(side="left", padx=(0, 6))
            self._view_btns[key] = b
        for text, cmd in (("关闭", self._try_close),
                          ("打开日志文件夹", self._open_log_dir),
                          ("导出 PDF", lambda: self._export("pdf")),
                          ("导出 TXT", lambda: self._export("txt"))):
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
            self._show_view("update" if UPDATE_LOG.exists() else "install")
            self.status_var.set("日志查看模式（如需更新请从开始菜单启动「检查更新」）")
        else:
            self._start_update()

    # ---------------- 日志输出 ----------------
    def _open_log_file(self):
        """打开更新日志：超过 1MB 先截断保留尾部，再追加本次会话头。"""
        try:
            if UPDATE_LOG.exists() and UPDATE_LOG.stat().st_size > LOG_ROTATE_BYTES:
                # 先按字节截尾再无损解码，避免正好切断多字节字符导致整份日志被误读
                tail = UPDATE_LOG.read_bytes()[-LOG_ROTATE_BYTES // 2:].decode("utf-8", errors="ignore")
                UPDATE_LOG.write_bytes(b"\xef\xbb\xbf" + "……(早期日志已截断)……\n".encode("utf-8")
                                       + tail.encode("utf-8"))
            if not UPDATE_LOG.exists():
                UPDATE_LOG.write_bytes(b"\xef\xbb\xbf")   # UTF-8 BOM
            self._log_fp = open(UPDATE_LOG, "a", encoding="utf-8", errors="replace")
            self._file_log_line("")
            self._file_log_line("=" * 56)
            self._file_log_line(f"本次更新开始于 {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
            self._file_log_line("=" * 56)
        except OSError:
            self._log_fp = None

    def _file_log_line(self, s: str):
        if self._log_fp is None:
            return
        try:
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
        return logtools._read_log(path)

    # ---------------- 视图切换 ----------------
    def _show_view(self, key: str):
        if self._running:
            self.status_var.set("更新进行中，完成后可切换查看其他日志…")
            return
        self._view = key
        for k, b in self._view_btns.items():
            b.configure(fg=C_CYAN if k == key else C_DIM)
        if key == "update":
            self._set_widget_text(self._read_file(UPDATE_LOG))
            self.status_var.set(str(UPDATE_LOG))
        elif key == "install":
            self._set_widget_text(self._read_file(INSTALL_LOG))
            self.status_var.set(str(INSTALL_LOG))
        else:
            self.status_var.set("正在收集诊断信息（含组件版本清单，约几秒钟）…")
            if self._report_cache is not None:
                self._set_widget_text(self._report_cache)
                self.status_var.set("诊断报告（可直接导出，发给技术支持定位问题）")
            else:
                threading.Thread(target=self._build_report, daemon=True).start()

    def _build_report(self):
        report = logtools.collect_diagnostics(SCRIPT_DIR)
        self._report_cache = report
        def show():
            if self._view == "report":
                self._set_widget_text(report)
                self.status_var.set("诊断报告（可直接导出，发给技术支持定位问题）")
        self.after(0, show)

    # ---------------- 导出 ----------------
    def _current_content(self) -> str:
        return self.text.get("1.0", "end-1c")

    def _export(self, kind: str):
        content = self._current_content()
        if not content.strip():
            messagebox.showinfo("导出日志", "当前没有可导出的日志内容。", parent=self)
            return
        names = {"update": "更新日志", "install": "安装日志", "report": "诊断报告"}
        base = f"MarkItDown{names.get(self._view, '日志')}_{datetime.datetime.now():%Y%m%d_%H%M%S}"
        if kind == "txt":
            path = filedialog.asksaveasfilename(
                parent=self, title="导出 TXT 日志", initialfile=base + ".txt",
                defaultextension=".txt", filetypes=[("文本文件", "*.txt")])
        else:
            path = filedialog.asksaveasfilename(
                parent=self, title="导出 PDF 日志", initialfile=base + ".pdf",
                defaultextension=".pdf", filetypes=[("PDF 文件", "*.pdf")])
        if not path:
            return
        try:
            if kind == "txt":
                logtools.export_txt(content, path)
            else:
                logtools.export_pdf(content, path, title=f"MarkItDown 转换器 {names.get(self._view, '日志')}")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("导出失败", f"导出日志时出错：\n{e}", parent=self)
            return
        self.status_var.set(f"已导出：{path}")
        if messagebox.askyesno("导出成功", f"日志已保存到：\n{path}\n\n是否现在打开？", parent=self):
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
            self.status_var.set("更新进行中，完成后才能关闭窗口…")
            return
        self.destroy()

    # ---------------- 更新流程 ----------------
    def _py(self) -> str:
        return str(VENV_PY) if VENV_PY.exists() else sys.executable

    def _run_cmd(self, args: list[str]) -> int:
        """流式执行命令：输出逐行进日志，返回退出码。"""
        self.after(0, self.log, "$ " + " ".join(args[1:]) if args and args[1] == "-m" else "$ " + " ".join(args))
        try:
            # 子进程按系统 ANSI 代码页输出（中文 Windows 为 GBK）：pip 报文是英文，
            # 但系统级错误（WinError 描述、中文路径）是 GBK，用 mbcs 才能正确解码
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="mbcs", errors="replace",
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as e:
            self.after(0, self.log, f"无法启动命令：{e}")
            return -1
        assert proc.stdout is not None
        for line in proc.stdout:
            self.after(0, self.log, line.rstrip())
        return proc.wait()

    def _pip(self, pkgs: list[str], index: str = MIRROR, offline: bool = False, fast: bool = False) -> bool:
        args = [self._py(), "-m", "pip", "install", "--upgrade"] + (PIP_FLAGS_FAST if fast else PIP_FLAGS)
        if offline:
            wheels = SCRIPT_DIR / "wheels"
            if not wheels.is_dir():
                # v1.0.6 起：在线安装成功后安装程序会删除离线备用组件以节省磁盘
                self.after(0, self.log, "（本机已删除内置离线组件目录以节省磁盘，离线修复不可用；请联网后重试）")
                return False
            args += ["--no-index", "--find-links", str(wheels)]
        else:
            args += ["-i", index]
        rc = self._run_cmd(args + pkgs)
        if rc != 0 and not fast:
            # 杀毒软件会临时锁定新写入的 DLL（如 onnxruntime.dll），稍候重试即可成功
            self.after(0, self.log, "等待 10 秒后重试（杀毒软件可能正在扫描文件）…")
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
                self.after(0, self.log, f"已部署 {n} 个 VC++ 运行库到 onnxruntime 组件目录")
        except Exception as exc:
            self.after(0, self.log, f"VC++ 运行库部署异常（忽略，继续自检）: {exc}")

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
            self.after(0, self.log, "收集诊断信息（写入日志，便于排查）…")
            self._run_cmd([self._py(), str(diag)])
        except Exception as exc:
            self.after(0, self.log, f"诊断信息收集失败（忽略）: {exc}")

    def _self_check(self) -> bool:
        self._deploy_vcrt()
        cmd = [self._py(), "-c", "from markitdown import MarkItDown; MarkItDown(); print('SELF-CHECK OK')"]
        self.after(0, self.log, "自检：加载转换引擎 …")
        if self._run_cmd(cmd) == 0:
            return True
        # 杀毒软件可能在扫描刚写入的 DLL（如 onnxruntime.dll），稍候重试即可通过
        self.after(0, self.log, "首次自检失败，等待 20 秒后重试（杀毒软件可能正在扫描文件）…")
        time.sleep(20)
        if self._run_cmd(cmd) == 0:
            return True
        self._dump_diag()
        self.after(0, self.log, "自检未通过：请把本日志发给发送安装包的人，上方 [diag] 段落可直接定位问题。")
        return False

    def _start_update(self):
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
            self.after(0, self.log, "正在更新 pip 自身 …")
            if self._run_cmd([self._py(), "-m", "pip", "install", "--upgrade", "pip",
                              "-i", MIRROR] + PIP_FLAGS) != 0:
                self.after(0, self.log, "清华镜像失败，改用阿里云镜像重试 …")
                self._run_cmd([self._py(), "-m", "pip", "install", "--upgrade", "pip",
                               "-i", MIRROR2] + PIP_FLAGS)

            self.after(0, self.log, "\n正在安装/更新界面组件 customtkinter、tkinterdnd2 …")
            gui_ok = self._pip(OTHER_PKGS)
            if not gui_ok:
                self.after(0, self.log, "清华镜像失败，改用阿里云镜像重试 …")
                gui_ok = self._pip(OTHER_PKGS, index=MIRROR2)
            if not gui_ok:
                self.after(0, self.log, "在线安装失败，改用内置离线组件 …")
                gui_ok = self._pip(OTHER_PKGS, offline=True)
            ok = gui_ok

            if ok:
                # 国内网络环境下 PyPI 镜像最稳定（实测清华镜像 34 秒装完全部依赖），
                # GitHub 线路只作后备并快速判定，避免在不通的线路上空等
                self.after(0, self.log, "\n正在从清华镜像安装/更新 markitdown …")
                spec_ok = self._pip([PYPI_SPEC])
                if not spec_ok:
                    self.after(0, self.log, "清华镜像失败，改用阿里云镜像 …")
                    spec_ok = self._pip([PYPI_SPEC], index=MIRROR2)
                if not spec_ok:
                    self.after(0, self.log, "国内镜像均失败，尝试 GitHub 直连（快速判定）…")
                    spec_ok = self._pip([GITHUB_SPEC], fast=True)
                if not spec_ok:
                    self.after(0, self.log, "GitHub 直连失败，通过加速代理下载（快速判定）…")
                    spec_ok = self._pip([GITHUB_PROXY_SPEC], fast=True)
                if not spec_ok:
                    self.after(0, self.log, "\n在线线路全部失败，改用内置离线组件修复 …")
                    spec_ok = self._pip([PYPI_SPEC] + OTHER_PKGS, offline=True)
                ok = spec_ok

            if ok:
                self.after(0, self.log, "\n尝试安装可选 OCR 组件 winsdk / pypdfium2（失败不影响使用）…")
                if not self._pip(OPTIONAL_PKGS):
                    if not self._pip(OPTIONAL_PKGS, index=MIRROR2):
                        self._pip(OPTIONAL_PKGS, offline=True)

            if ok:
                ok = self._self_check()

            # 把组件版本清单追加进日志文件（在工作线程中执行，避免卡住界面）
            try:
                proc = subprocess.run([self._py(), "-m", "pip", "list", "--disable-pip-version-check"],
                                      capture_output=True, text=True, encoding="utf-8",
                                      errors="replace", timeout=60,
                                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                self._file_log_line("")
                self._file_log_line("---- 更新后组件版本（pip list）----")
                for ln in (proc.stdout or "").splitlines():
                    self._file_log_line(ln)
            except Exception:  # noqa: BLE001
                pass

            self.after(0, self._finish_update, ok)
        except Exception as e:  # noqa: BLE001
            self.after(0, self.log, f"\n✗ 更新出错：{e}")
            self.after(0, self._finish_update, False)

    def _finish_update(self, ok: bool):
        # 先写结论（此时日志文件仍打开，结论会一并落盘），再关闭文件
        if ok:
            self.log("\n✓ 更新完成！重新启动转换器即可使用最新版本。")
            self.status_var.set("更新成功。可用上方按钮导出日志（TXT / PDF）。")
        else:
            self.log("\n✗ 更新未完成：请检查网络后重试；也可导出「诊断报告」发给技术支持。")
            self.status_var.set("更新未完成。建议：导出诊断报告 → 发送给技术支持。")
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
