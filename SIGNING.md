# 代码签名策略 / Code Signing Policy

本项目签署并发布 Windows 安装包，签名方式如下说明。
This project signs and distributes Windows installer packages as described below.

**状态 / Status**：已申请 SignPath Foundation 免费代码签名（申请中 / application submitted, pending approval）。
**Free code signing provided by SignPath.io, certificate by SignPath Foundation.**

## 将签名的内容 / What Will Be Signed

- 发布在 [GitHub Releases](https://github.com/yilaitd-web/markitdown-converter/releases) 上的 Windows 安装包（.exe）。
- Windows installers (.exe) published on [GitHub Releases](https://github.com/yilaitd-web/markitdown-converter/releases).

## 构建与签名流程 / Build and Signing Process

- 安装包由 [GitHub Actions](.github/workflows/build-installer.yml) 从本仓库的源代码自动构建。
- Installers are built from this repository's source code by [GitHub Actions](.github/workflows/build-installer.yml).
- 仅 CI 构建产物会提交给 SignPath 签名；签名私钥由 SignPath 保存在硬件安全模块（HSM）中，本项目不持有私钥。
- Only CI-built artifacts are submitted to SignPath for signing. The private key is held by SignPath on a Hardware Security Module (HSM); this project never possesses the key.

## 团队角色 / Team Roles

单人维护项目 / Single-maintainer project：

- **提交者与审查者 / Committers and Reviewers**：[yilaitd-web](https://github.com/yilaitd-web)
- **批准者 / Approvers**：[yilaitd-web](https://github.com/yilaitd-web) — 每次签名请求须经维护者本人明确批准。/ Every signing request requires explicit approval by the maintainer.
- 所有外部 Pull Request 须经维护者审查后方可合并。/ All external pull requests are reviewed by the maintainer before merging.

## 隐私政策 / Privacy Policy

This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.

本软件完全离线运行，不收集、不上传任何个人数据；详见 [README 隐私说明](./README.md#-隐私说明--privacy)。

## 分发渠道 / Distribution

- 官方下载渠道仅为 [GitHub Releases](https://github.com/yilaitd-web/markitdown-converter/releases)。
- The only official distribution channel is [GitHub Releases](https://github.com/yilaitd-web/markitdown-converter/releases).
