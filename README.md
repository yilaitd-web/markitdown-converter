# MarkItDown 转换器 (MarkItDown Converter)

一键将 PDF、Word、PowerPoint、Excel、图片、音频等文件批量转换为 Markdown 的 Windows 桌面工具。

本软件基于微软开源项目 [MarkItDown](https://github.com/microsoft/markitdown)（MIT 协议）构建。

## ✨ 功能特性

- 📄 支持 PDF / DOCX / PPTX / XLSX / 图片（含 OCR）/ 音频 / HTML / CSV 等多种格式
- 📁 支持批量转换整个文件夹
- 🖥️ 图形界面，免命令行操作
- 🌐 完全离线运行，无需联网（OCR 语言包除外）

## 📥 下载安装

1. 前往 [Releases](https://github.com/yilaitd-web/markitdown-converter/releases) 页面
2. 下载最新版本的 `MarkItDown转换器安装包_vX.X.X.exe`
3. 双击运行安装程序，按向导完成安装

## 🔐 安装包完整性验证（安全证书）

所有发布文件均附带 SHA-256 校验和与 GPG 签名，防止下载过程中被篡改。

### 方式一：SHA-256 校验

```powershell
# Windows PowerShell
Get-FileHash "MarkItDown转换器安装包_v1.1.4.exe" -Algorithm SHA256
```

将输出与 [`SHA256SUMS.txt`](./SHA256SUMS.txt) 中公布的哈希值对比，两者一致即表明文件完整。

### 方式二：GPG 签名验证（推荐）

发布者的 GPG 公钥已保存在本仓库 [`keys/release-signing-key.asc`](./keys/release-signing-key.asc)：

```bash
# 1. 导入发布者公钥
gpg --import keys/release-signing-key.asc

# 2. 验证校验文件的签名
gpg --verify SHA256SUMS.txt.sig SHA256SUMS.txt

# 3. 确认安装包哈希与校验文件一致
sha256sum -c SHA256SUMS.txt
```

> 公钥指纹（Fingerprint）：
> `EB35 A51D BF23 C7C5 B64E 807A 3CA4 11B8 02EE FF79`

> ⚠️ 注意：本安装包未购买商业代码签名证书，Windows SmartScreen 首次运行时可能显示"未知发布者"提示，点击"更多信息 → 仍要运行"即可。商业代码签名证书需要向证书颁发机构（如 DigiCert、Sectigo）付费申请并完成企业身份验证。

## 📖 使用说明

详见 [`MarkItDown转换器使用说明书.pdf`](./MarkItDown转换器使用说明书.pdf)。

## 📋 系统要求

- Windows 10 / 11（64 位）
- 无需预装 Python

## 📜 开源协议

本项目基于 MarkItDown（MIT），以 [MIT License](./LICENSE) 发布。

## ⚠️ 免责声明

本软件按"原样"提供，不附带任何明示或默示的担保。使用本软件所产生的任何风险由使用者自行承担。
