# MarkItDown 转换器 / MarkItDown Converter

一键将 PDF、Word、PowerPoint、Excel、图片（含 OCR）、音频等文件批量转换为 Markdown 的 Windows 桌面工具。
A Windows desktop tool that batch-converts PDF, Word, PowerPoint, Excel, images (with OCR), audio and more into Markdown.

> 基于微软开源项目 [MarkItDown](https://github.com/microsoft/markitdown)（MIT 协议）构建。
> Built on Microsoft's open-source [MarkItDown](https://github.com/microsoft/markitdown) under the MIT license.

## ✨ 功能特性 / Features

- 📄 支持 PDF / DOCX / PPTX / XLSX / 图片（含 OCR）/ 音频 / HTML / CSV 等多种格式 / PDF, DOCX, PPTX, XLSX, images (with OCR), audio, HTML, CSV and more
- 📁 支持批量转换整个文件夹 / Batch-convert entire folders
- 🖥️ 图形界面，免命令行操作 / GUI, no command line required
- 🌐 完全离线运行，无需联网（OCR 语言包除外）/ Fully offline (except OCR language packs)

## 📂 源码结构 / Source Code

本仓库包含完整源代码，基于 Python 3.12 + customtkinter 构建。
The complete source code is included. The app is built with Python 3.12 + customtkinter.

```
src/                    应用源代码 / Application source
├── markitdown_gui.py   主程序：图形界面 + --worker 后台转换进程 / Main GUI + worker process
├── update.pyw          更新器与日志中心（--view 仅打开日志中心）/ Updater & log center
├── logtools.py         日志导出工具（TXT/PDF，纯标准库）/ Log export utilities (stdlib-only)
└── app.ico             程序图标 / Application icon
installer/setup.iss     Inno Setup 安装包构建脚本 / Installer build script (Inno Setup)
launch.bat              开发用启动器（无控制台窗口）/ Dev launcher (no console)
requirements.txt        Python 依赖清单 / Python dependencies
```

## 🔧 自行构建 / Building from Source

1. 安装 Python 3.12（64 位）/ Install Python 3.12 (64-bit)
2. 安装依赖 / Install dependencies：

   ```bash
   pip install -r requirements.txt
   ```

3. 开发模式运行 / Run in dev mode：双击 `launch.bat`（或执行 `pythonw src/markitdown_gui.py`）
   Double-click `launch.bat` (or run `pythonw src/markitdown_gui.py`)

4. 打包安装包 / Build the installer：
   - 安装 [Inno Setup](https://jrsoftware.org/isdl.php) / Install [Inno Setup](https://jrsoftware.org/isdl.php)
   - 将 `src/` 下全部文件与使用说明书 PDF 放入 `installer/src/` / Copy everything under `src/` plus the user-manual PDF into `installer/src/`
   - 离线依赖（可选）：下载 Python 3.12 离线安装包及 `pip download -r requirements.txt` 得到的 wheels，放入 `installer/src/redist/` 与 `installer/src/wheels/`
     Offline deps (optional): fetch the Python 3.12 offline installer and wheels via `pip download -r requirements.txt` into `installer/src/redist/` and `installer/src/wheels/`
   - 用 Inno Setup 编译 `installer/setup.iss` / Compile `installer/setup.iss` with Inno Setup

## 📥 下载安装 / Download & Install

1. 前往 [Releases](https://github.com/yilaitd-web/markitdown-converter/releases) 页面 / Go to [Releases](https://github.com/yilaitd-web/markitdown-converter/releases)
2. 下载最新版本的安装包 / Download the latest installer (e.g. `MarkItDown-Converter-Setup-v1.1.4.exe`)
3. 双击运行安装程序，按向导完成安装 / Run the installer and follow the wizard

## 🔐 安装包完整性验证 / Integrity Verification

所有发布文件均附带 SHA-256 校验和与 GPG 签名，防止下载过程中被篡改。
All release files ship with SHA-256 checksums and a GPG signature to detect tampering.

### 方式一：SHA-256 校验 / Option 1: SHA-256

```powershell
Get-FileHash "MarkItDown-Converter-Setup-v1.1.4.exe" -Algorithm SHA256
```

将输出与 [`SHA256SUMS.txt`](./SHA256SUMS.txt) 中公布的哈希值对比，两者一致即表明文件完整。
Compare the output with the hash published in [`SHA256SUMS.txt`](./SHA256SUMS.txt).

### 方式二：GPG 签名验证（推荐）/ Option 2: GPG Verification (recommended)

发布者的 GPG 公钥已保存在本仓库 [`keys/release-signing-key.asc`](./keys/release-signing-key.asc)：
The publisher's GPG public key is committed at [`keys/release-signing-key.asc`](./keys/release-signing-key.asc):

```bash
gpg --import keys/release-signing-key.asc
gpg --verify SHA256SUMS.txt.asc SHA256SUMS.txt
sha256sum -c SHA256SUMS.txt
```

> 公钥指纹 / Fingerprint：`EB35 A51D BF23 C7C5 B64E 807A 3CA4 11B8 02EE FF79`

> ⚠️ 本安装包使用 GPG 签名保障完整性，未购买商业代码签名证书；Windows SmartScreen 首次运行时如显示"未知发布者"，请点击"更多信息 → 仍要运行"。商业代码签名证书需向 DigiCert、Sectigo 等 CA 付费申请并完成身份验证。
> ⚠️ The installer is integrity-protected via GPG but is not commercially code-signed; if SmartScreen shows "unknown publisher", click "More info → Run anyway". A commercial code-signing certificate requires paid application and identity verification with a CA such as DigiCert or Sectigo.

## 🔏 代码签名策略 / Code Signing Policy

本项目已申请 SignPath Foundation 免费代码签名（审核中），完整的签名策略（团队角色、构建流程、签名范围）见 [SIGNING.md](./SIGNING.md)。
This project has applied for free code signing from the SignPath Foundation (pending approval). The full signing policy (team roles, build process, signing scope) is documented in [SIGNING.md](./SIGNING.md).

**Free code signing provided by SignPath.io, certificate by SignPath Foundation.**

## 🔒 隐私说明 / Privacy

This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.

- 本软件完全离线运行，**不收集、不上传任何个人数据**，不包含任何遥测、分析或跟踪代码。
- 转换过程全部在本地完成，你的文件不会离开你的电脑。
- This software runs **entirely offline**. It collects and uploads **no personal data** and contains no telemetry, analytics or tracking code.
- All conversion happens locally — your files never leave your machine.

## 📖 使用说明 / Documentation

使用说明书随 Release 附件提供：`MarkItDown-Converter-UserManual-v1.1.4-zh.pdf`。
The user manual ships with each release: `MarkItDown-Converter-UserManual-v1.1.4-zh.pdf`.

## 📋 系统要求 / Requirements

- Windows 10 / 11（64 位）/ Windows 10 / 11 (64-bit)
- 无需预装 Python / No pre-installed Python

## 📜 开源协议与归属 / License & Attribution

本项目以 [MIT License](./LICENSE) 发布，基于微软 [MarkItDown](https://github.com/microsoft/markitdown)（MIT）构建，感谢原作者与社区。
This project is released under the [MIT License](./LICENSE) and is built on Microsoft's [MarkItDown](https://github.com/microsoft/markitdown) (MIT). Thanks to the original authors and community.

## ⚠️ 免责声明 / Disclaimer

本软件按"原样"提供，不附带任何明示或默示的担保；使用本软件所产生的风险由使用者自行承担。
This software is provided "as is", without warranty of any kind; users assume all risks arising from its use.
