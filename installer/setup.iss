; ============================================================
; MarkItDown 转换器 安装脚本 (Inno Setup 6) —— 中文 / English 双语版
; 启动后首先选择语言（Select Setup Language），之后所有界面、日志、
; 快捷方式均按所选语言生成；选择结果写入安装目录 language.txt，
; 主程序与更新器据此显示对应语言。
; 英文安装时日志文件为英文标题（Install Log.txt / Update Log.txt），方便查找。
; 功能：Python 环境检测/安装、GitHub 在线组件 + PyPI 镜像 + 离线备用组件、
;       自定义安装位置、微信文件位置识别（程序内置）、检查更新、
;       实时滚动日志（同步写入安装日志，系统 ANSI 编码，可在日志中心导出 PDF/TXT）、
;       VC++ 运行库随包应用本地部署（免管理员，适配全新系统/服务器）、
;       完整卸载、首次启动自动打开使用说明书。
; 适用系统：Windows 10 / 11（x64，不含 ARM）及同代 Windows Server。
; ============================================================
#define MyAppName "MarkItDown Converter"
#define MyAppVersion "1.2.2"

; 测试构建可用 iscc /dTestAppId="{{...}" /dTestSuffix="_Test" 覆盖 AppId 与输出名，
; 避免测试安装覆盖正式安装的卸载注册信息
#ifdef TestAppId
  #define AppIdValue TestAppId
#else
  #define AppIdValue "{{D4A7C2E1-3F5B-4E6A-9B8C-7D0E1F2A3B4C}"
#endif
#ifndef TestSuffix
  #define TestSuffix ""
#endif

[Setup]
AppId={#AppIdValue}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=MarkItDown Converter
AppUpdatesURL=https://github.com/microsoft/markitdown
DefaultDirName={autopf}\MarkItDownConverter
DefaultGroupName={cm:StartMenuGroup}{#TestSuffix}
PrivilegesRequired=lowest
; 转换器运行期间持有同名互斥体（markitdown_gui.py 的 APP_MUTEX_NAME）：覆盖安装/卸载前
; 提示用户先关闭转换器——否则常驻转换进程占用着 .venv 里的 pythonw.exe 与组件 DLL，
; 重建 venv、pip 替换组件都会失败，安装被判失败后还会删掉原本可用的快捷方式
AppMutex=MarkItDownConverterGUI
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0
ShowLanguageDialog=yes
OutputDir=Output
OutputBaseFilename=MarkItDownConverter{#TestSuffix}_Setup_v{#MyAppVersion}
SetupIconFile=src\app.ico
UninstallDisplayIcon={app}\app.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany=MarkItDown Converter
VersionInfoDescription=MarkItDown Converter Setup
VersionInfoProductName=MarkItDown Converter
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimp"; MessagesFile: "languages\ChineseSimplified.isl"

[CustomMessages]
; ---------- 开始菜单 / 快捷方式 ----------
english.StartMenuGroup=MarkItDown Converter
chinesesimp.StartMenuGroup=MarkItDown 转换器
english.IconApp=MarkItDown Converter
chinesesimp.IconApp=MarkItDown 转换器
english.IconManual=User Guide
chinesesimp.IconManual=使用说明书
english.ManualFile=MarkItDown Converter User Guide.pdf
chinesesimp.ManualFile=MarkItDown转换器使用说明书.pdf
english.IconUpdater=Check for Updates · Log Center
chinesesimp.IconUpdater=检查更新 · 日志中心
english.IconUninstall=Uninstall MarkItDown Converter
chinesesimp.IconUninstall=卸载 MarkItDown 转换器
english.RunNowDesc=Run MarkItDown Converter now (the User Guide opens automatically on first launch)
chinesesimp.RunNowDesc=立即运行 MarkItDown 转换器（首次启动会自动打开使用说明书）
; ---------- 安装选项页 ----------
english.OptionsTitle=Installation Options
chinesesimp.OptionsTitle=安装选项
english.OptionsSub=The installer will perform the following two actions (keeping both checked is recommended)
chinesesimp.OptionsSub=本安装程序将执行以下两项操作（推荐保持勾选）
english.OptPython=1. Detect and install the Python runtime (required)
chinesesimp.OptPython=① 检测并安装 Python 运行环境（必需）
english.OptPythonDesc=If Python is missing or the version is unsupported, the bundled Python 3.12 is installed automatically (no Internet required); otherwise this step is skipped.
chinesesimp.OptPythonDesc=若电脑没有 Python 或版本不符，将自动安装安装包内置的 Python 3.12（无需联网）；已安装则自动跳过。
english.OptOnline=2. Download and install the latest MarkItDown components (recommended)
chinesesimp.OptOnline=② 联网安装最新版 MarkItDown 组件（推荐，优先国内镜像）
english.OptOnlineDesc=If the download fails, there is no Internet connection, or you uncheck this option, the bundled offline components are used instead; the features are identical.
chinesesimp.OptOnlineDesc=下载失败、无网络或取消勾选时，自动改用安装包内置的离线组件，功能相同。
english.OptionsNote=Note: the live log is shown at the bottom of the installation page; after installation you can export it as PDF/TXT in "Check for Updates · Log Center".
chinesesimp.OptionsNote=说明：安装全程实时日志见安装页下方；安装后可在「检查更新 · 日志中心」导出 PDF/TXT。
english.LogHint=Detailed log (scrolls live; the full log is saved as "Install Log.txt" in the installation folder):
chinesesimp.LogHint=详细日志（实时滚动，完整内容见安装目录「安装日志.txt」）：
; ---------- 日志文件名 ----------
english.InstallLogName=Install Log.txt
chinesesimp.InstallLogName=安装日志.txt
; ---------- 通用 ----------
english.StrOk=OK
chinesesimp.StrOk=OK
english.StrFail=FAILED
chinesesimp.StrFail=失败
english.StrYes=yes
chinesesimp.StrYes=是
english.StrNo=no
chinesesimp.StrNo=否
english.AutoRetry= (auto-retry)
chinesesimp.AutoRetry=（自动重试）
; ---------- 环境安装流程 ----------
english.LogHeader===== MarkItDown Converter Install Log v%1 ====
chinesesimp.LogHeader===== MarkItDown 转换器 安装日志 v%1 ====
english.InstallDirLog=Install folder: 
chinesesimp.InstallDirLog=安装目录: 
english.OsLine=OS: %1  Build %2  (x64, administrator: %3)
chinesesimp.OsLine=系统: %1  Build %2  (x64, 管理员: %3)
english.OsWin10=Windows 10 / same-generation Server
chinesesimp.OsWin10=Windows 10 / 同代 Server
english.CurrentUser=Current user: 
chinesesimp.CurrentUser=当前用户: 
english.DiskInfo=Disk: drive %1 has %2 GB free of %3 GB total
chinesesimp.DiskInfo=磁盘: %1 盘剩余 %2 GB / 共 %3 GB
english.CleanupExitCode=  Leftover process-tree cleanup exit code = 
chinesesimp.CleanupExitCode=  残留进程树清理退出码 = 
english.CleanupNoPs=!! Could not start PowerShell to clean up leftover processes; if later steps behave abnormally, restart the PC and run the installer again
chinesesimp.CleanupNoPs=!! 无法启动 PowerShell 清理残留进程；若后续步骤异常，请重启电脑后重试安装
english.CmdStartFail=!! Failed to start the command
chinesesimp.CmdStartFail=!! 命令启动失败
english.CmdTimeout=!! The command did not finish within 30 minutes; force-terminating its process tree (to prevent leftover processes from interfering with later steps)…
chinesesimp.CmdTimeout=!! 命令超过 30 分钟未结束，正在强制终止该进程树（防残留进程干扰后续步骤）…
english.ExitCodeLog=  Exit code = 
chinesesimp.ExitCodeLog=  退出码 = 
english.RetryWaitLog=Retrying the same source in 15 seconds (antivirus software may have temporarily locked files)…
chinesesimp.RetryWaitLog=等待 15 秒后重试同一来源（应对杀毒软件临时锁定文件）…
english.RetryWaitStatus=Interference detected; automatically retrying in 15 seconds (antivirus software may be scanning files)…
chinesesimp.RetryWaitStatus=遇到干扰，15 秒后自动重试（杀毒软件可能正在扫描文件）…
english.VcrtCopyFail=!! Failed to copy the VC++ runtime: 
chinesesimp.VcrtCopyFail=!! VC++ 运行库复制失败: 
english.VcrtDeployed=VC++ runtime deployment (%1): %2 / %3 files
chinesesimp.VcrtDeployed=VC++ 运行库部署（%1）: %2 / %3 个文件
english.VcrtIncomplete=!! The VC++ runtime was not fully deployed to %1; if the self-check reports "DLL load failed", install the Microsoft VC++ 2015-2022 x64 Redistributable
chinesesimp.VcrtIncomplete=!! VC++ 运行库未完整部署到 %1；若自检提示 DLL load failed，请安装微软 VC++ 2015-2022 x64 运行库
english.CheckImport=Verifying that markitdown can be imported …
chinesesimp.CheckImport=校验 markitdown 可导入 …
english.DiagCollect=Collecting diagnostic information (written to the log for troubleshooting)…
chinesesimp.DiagCollect=收集诊断信息（写入日志，便于排查）…
english.DiagWriteFail=!! Failed to write the diagnostic script: 
chinesesimp.DiagWriteFail=!! 诊断脚本写入失败: 
english.PyDownloading=Downloading the Python installer (about 26 MB; please wait)…
chinesesimp.PyDownloading=正在下载 Python 安装程序（约 26MB，请耐心等待）…
english.PyFetchFail=!! Failed to obtain the Python installer
chinesesimp.PyFetchFail=!! 获取 Python 安装程序失败
english.PyFetchFailMsg=Failed to obtain the Python installer. Install Python 3.12 - 3.14 (64-bit) manually, then run this installer again.
chinesesimp.PyFetchFailMsg=获取 Python 安装程序失败。请手动安装 Python 3.12 ~ 3.14（64 位）后重新运行本安装程序。
english.PyBundled=Using the Python installer bundled in this package.
chinesesimp.PyBundled=使用安装包内置的 Python 安装程序。
english.PyInstalling=Installing Python 3.12 (about 1-2 minutes; no on-screen activity during this time is normal)…
chinesesimp.PyInstalling=正在安装 Python 3.12（约需 1-2 分钟，期间无提示属正常）…
english.PyExitCode=Python installer exit code = %1 (0/3010 = success; 1638 = a newer version already exists)
chinesesimp.PyExitCode=Python 安装程序退出码 = %1（0/3010=成功；1638=已存在更新版本）
english.PyFoundRound=Python found on detection round %1: 
chinesesimp.PyFoundRound=第 %1 轮检测找到 Python: 
english.PyWaitRound=Waiting for the Python environment to become ready (detection round %1 / 15)…
chinesesimp.PyWaitRound=正在等待 Python 环境就绪（第 %1 / 15 轮检测）…
english.PyNotFoundAfterInstall=!! No usable Python interpreter was found after installation despite repeated detection
chinesesimp.PyNotFoundAfterInstall=!! Python 安装后多次检测仍未找到可用解释器
english.PyChecking=Checking the Python runtime environment…
chinesesimp.PyChecking=正在检测 Python 运行环境…
english.PySetupFail=!! Failed to set up the Python environment
chinesesimp.PySetupFail=!! 未能配置 Python 环境
english.PySetupFailMsg=Failed to set up the Python environment. Install Python 3.12 - 3.14 (64-bit) manually, then run this installer again.
chinesesimp.PySetupFailMsg=未能配置 Python 环境。请手动安装 Python 3.12 ~ 3.14（64 位）后重新运行本安装程序。
english.PyMissingMsg=Python 3.10 or later was not found, and automatic installation was not selected. The converter cannot run for now.
chinesesimp.PyMissingMsg=未检测到 Python 3.10 及以上版本，且未勾选自动安装。转换器暂时无法运行。
english.PyUsing=Using Python: 
chinesesimp.PyUsing=使用 Python: 
english.VenvCreating=Creating an isolated runtime environment (about 1 minute)…
chinesesimp.VenvCreating=正在创建独立运行环境（约 1 分钟）…
english.VenvReuse=Reusing the Python that the existing runtime environment was built with:
chinesesimp.VenvReuse=沿用现有运行环境所基于的 Python:
english.VenvRebuild=The existing runtime environment was built with Python %1 but Python %2 will be used now: rebuilding it (components built for the old version cannot be loaded by the new one)…
chinesesimp.VenvRebuild=现有运行环境基于 Python %1，本次使用 Python %2：重建运行环境（旧版本编译的组件无法被新版本加载）…
english.VenvFail=!! Failed to create the runtime environment
chinesesimp.VenvFail=!! 创建运行环境失败
english.VenvFailMsg=Failed to create the runtime environment. Try a different installation folder and reinstall.
chinesesimp.VenvFailMsg=创建运行环境失败，请尝试更换安装位置后重新安装。
english.VcrtNoteCapi=onnxruntime component folder
chinesesimp.VcrtNoteCapi=onnxruntime 组件目录
english.VcrtNoteBackup=Python launcher folder (backup)
chinesesimp.VcrtNoteBackup=python 启动目录·备用
english.NetProbeFail=!! Network pre-check failed (neither mirror responded within 3 seconds): skipping online installation and using the bundled offline components.
chinesesimp.NetProbeFail=!! 网络预检未通过（两条镜像 3 秒内均无响应）：跳过在线安装，直接使用内置离线组件。
english.NetProbeSkip=The option "2. Download and install the latest MarkItDown components" was not selected: skipping the network pre-check; the bundled offline components will be used.
chinesesimp.NetProbeSkip=未勾选「② 联网安装最新版 MarkItDown 组件」：跳过网络预检，直接使用内置离线组件。
english.PyDetectTimeout=!! This Python did not respond within 12 seconds; treating it as unavailable and cleaning up leftover processes: 
chinesesimp.PyDetectTimeout=!! 探测该 Python 超过 12 秒无响应，按不可用处理并清理残留进程: 
english.PipUpgrading=Upgrading pip (Tsinghua mirror)…
chinesesimp.PipUpgrading=正在升级 pip（清华镜像）…
english.PipUpgradeRetry=Tsinghua mirror failed; retrying the pip upgrade with the Aliyun mirror …
chinesesimp.PipUpgradeRetry=清华镜像失败，正在用阿里云镜像重试升级 pip …
english.GuiInstalling=Installing the GUI components customtkinter / tkinterdnd2 (Tsinghua mirror)…
chinesesimp.GuiInstalling=正在安装界面组件 customtkinter / tkinterdnd2（清华镜像）…
english.GuiRetry=Tsinghua mirror failed for the GUI components; retrying with the Aliyun mirror …
chinesesimp.GuiRetry=界面组件清华镜像失败，正在用阿里云镜像重试 …
english.GuiCheck=Verifying that the GUI components can be imported …
chinesesimp.GuiCheck=校验界面组件可导入 …
english.CoreInstalling=Installing the MarkItDown components from the Tsinghua mirror (about 1-3 minutes)…
chinesesimp.CoreInstalling=正在从清华镜像安装 MarkItDown 组件（约 1-3 分钟）…
english.CoreRetry=Tsinghua mirror failed; installing with the Aliyun mirror instead …
chinesesimp.CoreRetry=清华镜像失败，正在改用阿里云镜像安装 …
english.CoreGitHub=Both mirrors failed; trying a direct GitHub connection (quick check, fails within 1 minute)…
chinesesimp.CoreGitHub=国内镜像均失败，正在尝试 GitHub 直连（快速判定，失败不超过 1 分钟）…
english.CoreProxy=Direct GitHub connection failed; downloading through an acceleration proxy (quick check)…
chinesesimp.CoreProxy=GitHub 直连失败，正在通过加速代理下载（快速判定）…
english.OfflineSwitch=Online installation did not fully succeed; switching to the bundled offline components.
chinesesimp.OfflineSwitch=在线安装未完全成功，切换到内置离线组件。
english.OfflineInstalling=Installing the bundled offline components (about 1-3 minutes)…
chinesesimp.OfflineInstalling=正在使用安装包内置的离线组件（约 1-3 分钟）…
english.StepResults=Step results: GUI components=%1, conversion core=%2, offline bundle used=%3
chinesesimp.StepResults=分步结果: 界面组件=%1, 转换核心=%2, 动用离线包=%3
english.AllLinesFail=!! All installation sources failed verification; collecting diagnostic information …
chinesesimp.AllLinesFail=!! 各条安装线路均未通过校验，正在收集诊断信息 …
english.OcrInstalling=Installing the optional image OCR component (Windows OCR via winrt; failure does not affect normal use)…
chinesesimp.OcrInstalling=正在安装可选的图片 OCR 组件（Windows 本地 OCR，winrt；失败不影响使用）…
english.OcrRetry=Tsinghua mirror failed for the OCR component; retrying with the Aliyun mirror …
chinesesimp.OcrRetry=OCR 组件清华镜像失败，正在用阿里云镜像重试 …
english.OcrOffline=Installing the OCR component from the bundled offline packages …
chinesesimp.OcrOffline=正在用内置离线包安装 OCR 组件 …
english.OcrCheck=Checking image OCR (recognition languages installed in Windows; for troubleshooting only) …
chinesesimp.OcrCheck=检查图片 OCR 是否可用（Windows 已安装的识别语言，仅供排查）…
english.PdfiumInstalling=Installing the scanned-document recognition component pypdfium2 (failure does not affect normal use)…
chinesesimp.PdfiumInstalling=正在安装扫描件识别组件 pypdfium2（失败不影响使用）…
english.PdfiumRetry=Tsinghua mirror failed for pypdfium2; retrying with the Aliyun mirror …
chinesesimp.PdfiumRetry=pypdfium2 清华镜像失败，正在用阿里云镜像重试 …
english.PdfiumOffline=Installing pypdfium2 from the bundled offline packages …
chinesesimp.PdfiumOffline=正在用内置离线包安装 pypdfium2 …
english.SelfCheck=Self-check: testing the conversion engine …
chinesesimp.SelfCheck=正在自检转换引擎 …
english.SelfCheckFail1=!! The first self-check failed (see the error trace above). Common cause: security software temporarily locking DLL files. Retrying in 20 seconds …
chinesesimp.SelfCheckFail1=!! 首次自检失败（详见上方错误堆栈）。常见原因：安全软件临时锁定 DLL。等待 20 秒后重试 …
english.SelfCheckWaitStatus=The first self-check failed; retrying in 20 seconds …
chinesesimp.SelfCheckWaitStatus=首次自检失败，等待 20 秒后重试 …
english.SelfCheckRetry=Re-running the conversion engine self-check …
chinesesimp.SelfCheckRetry=正在重新自检转换引擎 …
english.SelfCheckFail2=!! The self-check failed again; collecting diagnostic information …
chinesesimp.SelfCheckFail2=!! 再次自检仍失败，正在收集诊断信息 …
english.SelfCheckAdvice=!! Send this log to the person who gave you the installer; the [diag] section above pinpoints the problem.
chinesesimp.SelfCheckAdvice=!! 请把本日志发给发送安装包的人，上方 [diag] 段落可直接定位问题。
english.PipListLog=Recording the component version list (pip list)…
chinesesimp.PipListLog=记录组件版本清单（pip list）…
english.LogFooter===== Installation finished: overall=%1 (GUI components=%2, conversion core=%3, offline bundle used=%4) ====
chinesesimp.LogFooter===== 安装流程结束: 总体=%1（界面组件=%2, 转换核心=%3, 动用离线包=%4） ====
english.WheelsKept=The bundled offline components were used during this installation; keeping the wheels folder for future offline repairs.
chinesesimp.WheelsKept=本次安装使用了内置离线组件，保留 wheels 目录以备日后离线修复。
english.WheelsDeleted=Online installation succeeded; the bundled offline components (about 180 MB) were deleted to save disk space.
chinesesimp.WheelsDeleted=在线安装成功，已删除内置离线备用组件（释放约 180MB 磁盘空间）。
english.WheelsDelFail=!! Failed to delete the bundled offline components; this does not affect use. You can delete them manually: 
chinesesimp.WheelsDelFail=!! 离线备用组件删除失败，不影响使用；可手动删除: 
english.DepsOkStatus=Components installed successfully; self-check passed.
chinesesimp.DepsOkStatus=组件安装完成，自检通过。
english.DepsFailStatus=The components were not fully installed.
chinesesimp.DepsFailStatus=组件未能完整安装。
; ---------- 完成页 / 弹窗 ----------
english.FinishedOk1=Installation is complete. MarkItDown Converter is ready to use.
chinesesimp.FinishedOk1=安装已完成，MarkItDown 转换器可以使用了。
english.FinishedOk2=The install log was saved to:
chinesesimp.FinishedOk2=安装日志已保存到：
english.FinishedOk3=(If problems occur later, open "Check for Updates · Log Center" from the Start Menu to view the log and export it as PDF/TXT.)
chinesesimp.FinishedOk3=（如以后遇到问题，可在开始菜单「检查更新 · 日志中心」中查看并导出 PDF/TXT 日志）
english.FinishedFail1=The installation did not fully succeed: the components were not fully installed.
chinesesimp.FinishedFail1=安装未完全成功：组件未能完整安装。
english.FinishedFail2=Connect to the Internet and run "Check for Updates · Log Center" from the Start Menu to complete the installation automatically. If it fails repeatedly, send this log file to the person who gave you the installer:
chinesesimp.FinishedFail2=请联网后运行开始菜单「检查更新 · 日志中心」自动补全；若多次失败，请把以下日志文件发给发送安装包的人：
english.DepsFailMsg=The components were not fully installed. Connect to the Internet and run "Check for Updates" from the Start Menu to complete the installation automatically; if it fails repeatedly, contact the person who gave you the installer.
chinesesimp.DepsFailMsg=组件未能完整安装。请联网后运行开始菜单「检查更新」自动补全；若多次失败，请联系发送安装包的人。
english.DownloadLog=Downloading: 
chinesesimp.DownloadLog=下载: 
english.NoCurl=  The system has no built-in curl.exe (Windows is too old); skipping the online download
chinesesimp.NoCurl=  系统无内置 curl.exe（Windows 版本过旧），跳过在线下载
english.DownloadExit=  Download exit code = %1 (28 = overall/low-speed timeout: abandoned when the 60-second average speed falls below 1 KB/s)
chinesesimp.DownloadExit=  下载退出码 = %1（28=整体超时/低速超时，60 秒平均低于 1KB/s 即放弃）

[Files]
Source: "src\markitdown_gui.py"; DestDir: "{app}"
Source: "src\update.pyw"; DestDir: "{app}"
Source: "src\logtools.py"; DestDir: "{app}"
Source: "src\app.ico"; DestDir: "{app}"
Source: "src\MarkItDown转换器使用说明书.pdf"; DestDir: "{app}"
Source: "src\MarkItDown Converter User Guide.pdf"; DestDir: "{app}"
Source: "src\VERSION"; DestDir: "{app}"
Source: "src\redist\python-3.12.8-amd64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "src\redist\vcrt\*"; DestDir: "{app}\redist-vcrt"
Source: "src\wheels\*"; DestDir: "{app}\wheels"

[Icons]
Name: "{autodesktop}\{cm:IconApp}{#TestSuffix}"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\markitdown_gui.py"""; WorkingDir: "{app}"; IconFilename: "{app}\app.ico"
Name: "{group}\{cm:IconApp}{#TestSuffix}"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\markitdown_gui.py"""; WorkingDir: "{app}"; IconFilename: "{app}\app.ico"
Name: "{group}\{cm:IconManual}"; Filename: "{app}\{cm:ManualFile}"; IconFilename: "{app}\app.ico"
Name: "{group}\{cm:IconUpdater}"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\update.pyw"""; WorkingDir: "{app}"; IconFilename: "{app}\app.ico"
Name: "{group}\{cm:IconUninstall}"; Filename: "{uninstallexe}"; IconFilename: "{app}\app.ico"

[Run]
Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\markitdown_gui.py"""; WorkingDir: "{app}"; Description: "{cm:RunNowDesc}"; Flags: postinstall nowait skipifsilent; Check: VenvReady

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files; Name: "{app}\markitdown_gui_config.json"
Type: files; Name: "{app}\language.txt"
Type: files; Name: "{app}\安装日志.txt"
Type: files; Name: "{app}\更新日志.txt"
Type: files; Name: "{app}\Install Log.txt"
Type: files; Name: "{app}\Update Log.txt"

[Code]
procedure Sleep(dwMilliseconds: Cardinal); external 'Sleep@kernel32.dll stdcall';
function SendMessage(hWnd: LongInt; Msg: LongInt; wParam: LongInt; lParam: LongInt): LongInt; external 'SendMessageA@user32.dll stdcall';

type
  { 消息泵用的 Windows MSG 结构（x86 安装程序，句柄/参数均 32 位） }
  TSetupMsg = record
    hwnd: LongInt;
    message: LongWord;
    wParam: LongInt;
    lParam: LongInt;
    time: LongWord;
    ptX, ptY: LongInt;
  end;

function PeekMessage(var lpMsg: TSetupMsg; hWnd: LongInt; wMsgFilterMin, wMsgFilterMax, wRemoveMsg: LongWord): Boolean; external 'PeekMessageA@user32.dll stdcall';
function TranslateMessage(const lpMsg: TSetupMsg): Boolean; external 'TranslateMessage@user32.dll stdcall';
function DispatchMessage(const lpMsg: TSetupMsg): LongInt; external 'DispatchMessageA@user32.dll stdcall';

var
  CbPython, CbGitHub: TNewCheckBox;
  LogMemo: TNewMemo;
  GPythonExe: String;
  GPyVer: String;      { 最近一次验证通过的 Python 主次版本号，如 3.12 }
  GDepsOK: Boolean;
  GLogFile: String;
  GTailBytes: Int64;

const
  PyInstallerName = 'python-3.12.8-amd64.exe';
  Mirror = 'https://pypi.tuna.tsinghua.edu.cn/simple';
  Mirror2 = 'https://mirrors.aliyun.com/pypi/simple/';
  GitHubSpec = 'markitdown[pptx,docx,xlsx,xls,pdf,outlook] @ https://codeload.github.com/microsoft/markitdown/zip/refs/heads/main#subdirectory=packages/markitdown';
  GitHubSpecProxy = 'markitdown[pptx,docx,xlsx,xls,pdf,outlook] @ https://gh-proxy.com/https://codeload.github.com/microsoft/markitdown/zip/refs/heads/main#subdirectory=packages/markitdown';
  { 不含 audio-transcription：该组件的 wav 识别会把音频上传到 Google（界面承诺
    「全部本地完成」），mp3/m4a 又依赖安装包没有的 ffmpeg；不装它，音频文件
    统一走「无文字」提示路径，与界面文案一致。 }
  ExtrasSpec = 'markitdown[pptx,docx,xlsx,xls,pdf,outlook]';
  EM_VSCROLL = $00B5;
  SB_BOTTOM = 7;
  RUN_TIMEOUT_MS = 1800000;   { 单条命令最长 30 分钟，防死等 }
  { 图片 OCR 组件：pywinrt 的 winrt-* 系列包（仍在维护，Python 3.12~3.14 均有预编译包），
    取代已停止维护、只有 3.12 包的 winsdk。各包版本必须一致，锁在 3.x 防大版本改 API。
    每项都要加引号：< > 在 cmd 里是重定向符 }
  OcrSpecs = '"winrt-runtime>=3.2.1,<4" "winrt-Windows.Foundation>=3.2.1,<4" ' +
    '"winrt-Windows.Foundation.Collections>=3.2.1,<4" "winrt-Windows.Globalization>=3.2.1,<4" ' +
    '"winrt-Windows.Graphics.Imaging>=3.2.1,<4" "winrt-Windows.Media.Ocr>=3.2.1,<4" ' +
    '"winrt-Windows.Storage>=3.2.1,<4" "winrt-Windows.Storage.Streams>=3.2.1,<4"';

{ 取当前语言的一条自定义文案（[CustomMessages]） }
function M(const Key: String): String;
begin
  Result := ExpandConstant('{cm:' + Key + '}');
end;

function YesNo(B: Boolean): String;
begin
  if B then Result := M('StrYes') else Result := M('StrNo');
end;

function OkStr(B: Boolean): String;
begin
  if B then Result := M('StrOk') else Result := M('StrFail');
end;

{ ---------------- 日志：实时落盘 ----------------
  日志文件统一使用系统 ANSI 编码（中文 Windows 即 GBK）：
  Inno 的 SaveStringToFile 写 ANSI，pip 在中文 Windows 上的输出同样是 GBK，
  二者天然一致，记事本/微信均可直接打开查看，日志中心导出 PDF 时自动识别。 }
procedure StepLog(const S: String);
begin
  Log(S);
  if GLogFile <> '' then
  try
    SaveStringToFile(GLogFile, GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':') + '  ' + S + #13#10, True);
  except
  end;
end;

{ 边等待边抽发消息：进度条 marquee（小绿条往返动画）、日志框滚动都靠消息循环
  驱动，裸 Sleep 会把界面整个冻住（绿条卡住、窗口假死）。安装期间一律用它代替
  Sleep——每 50ms 醒来一次把积压在队列里的消息派发掉，动画始终流畅。 }
procedure PumpSleep(Ms: Integer);
var
  Waited: Integer;
  Msg: TSetupMsg;
begin
  Waited := 0;
  while Waited < Ms do
  begin
    Sleep(50);
    while PeekMessage(Msg, 0, 0, 0, 1) do   { 1 = PM_REMOVE }
    begin
      TranslateMessage(Msg);
      DispatchMessage(Msg);
    end;
    Waited := Waited + 50;
  end;
end;

{ 环境搭建失败时删掉指向 pythonw.exe 的死快捷方式（venv 没建成，点了也打不开）。
  快捷方式由 [Icons] 在 SetupEnvironment 运行前创建，失败分支负责清理。 }
procedure DeleteDeadShortcuts();
begin
  DeleteFile(ExpandConstant('{autodesktop}\') + M('IconApp') + '{#TestSuffix}.lnk');
  DeleteFile(ExpandConstant('{group}\') + M('IconApp') + '{#TestSuffix}.lnk');
  DeleteFile(ExpandConstant('{group}\') + M('IconUpdater') + '.lnk');
end;

{ 安装页上的实时日志框：增量读取日志文件新增的字节并滚动显示。
  旧版每轮都整文件重新加载，安装日志可达 1-3MB，一场安装累计重读数百 MB（O(n²)），
  界面明显卡顿；现记录字节偏移只读新增部分，且只消费到最后一个换行符（残行留下一轮）。
  日志为系统 ANSI 字节流，按字节切行后逐行交给日志框（AnsiString→String 按系统码页转换，与落盘编码一致）。 }
procedure RefreshLogView();
var
  FS: TFileStream;
  Chunk: AnsiString;
  Avail: Int64;
  Cut, P, Q: Integer;
begin
  if GLogFile = '' then Exit;
  if not FileExists(GLogFile) then Exit;
  try
    FS := TFileStream.Create(GLogFile, fmOpenRead or fmShareDenyNone);
  except
    Exit;   { 文件被占用时本轮跳过 }
  end;
  try
    if FS.Size < GTailBytes then GTailBytes := 0;   { 日志被重建（理论上不会），归零重读 }
    FS.Position := GTailBytes;
    Avail := FS.Size - GTailBytes;
    if Avail <= 0 then Exit;
    SetLength(Chunk, Integer(Avail));
    FS.ReadBuffer(Chunk, Integer(Avail));
    Cut := 0;
    for P := Integer(Avail) downto 1 do
      if Chunk[P] = #10 then
      begin
        Cut := P;
        Break;
      end;
    if Cut = 0 then Exit;   { 还没有完整行，偏移不动，留到下一轮 }
    GTailBytes := GTailBytes + Cut;
    P := 1;
    while P <= Cut do
    begin
      Q := P;
      while (Q <= Cut) and (Chunk[Q] <> #13) and (Chunk[Q] <> #10) do
        Q := Q + 1;
      LogMemo.Lines.Add(Copy(Chunk, P, Q - P));
      if (Q < Cut) and (Chunk[Q] = #13) and (Chunk[Q + 1] = #10) then
        P := Q + 2
      else
        P := Q + 1;
    end;
    while LogMemo.Lines.Count > 600 do
      LogMemo.Lines.Delete(0);
    SendMessage(LogMemo.Handle, EM_VSCROLL, SB_BOTTOM, 0);
    LogMemo.Update;
  finally
    FS.Free;
  end;
end;

procedure SetStatus(const S: String);
begin
  WizardForm.StatusLabel.Caption := S;
  StepLog('== ' + S);
end;

{ 环境搭建中途失败（Python 缺失/venv 创建失败等提前 Exit 的分支）时的收尾：
  把完成页改为明确的失败文案 + 日志路径。旧版这些分支完成页仍显示默认
  「安装成功」文案，用户装好打不开却以为安装成功。 }
procedure MarkInstallFailed(const Detail: String);
begin
  SetStatus(M('DepsFailStatus'));
  DeleteDeadShortcuts();
  WizardForm.FinishedLabel.Caption :=
    M('FinishedFail1') + #13#10#13#10 + Detail + #13#10 + GLogFile;
end;

{ 命令超时后按哨兵文件路径找到孤儿 cmd 并整棵树杀掉：
  哨兵文件路径（含本实例独有的 is-XXXXX 临时目录名）只出现在那条卡死命令的
  命令行里，不会误杀安装程序自身或用户的其他进程；taskkill /T 连带其下的
  python/pip 子进程一并结束。 }
procedure KillHungStep(const Marker: String);
var
  PsFile, PsCode: String;
  Code: Integer;
begin
  PsFile := ExpandConstant('{tmp}\killtree.ps1');
  PsCode :=
    'param([string]$Marker)' + #13#10 +
    'Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -and $_.CommandLine.Contains($Marker) } | ForEach-Object {' + #13#10 +
    '  & "$env:WINDIR\System32\taskkill.exe" /PID $_.ProcessId /T /F | Out-Null' + #13#10 +
    '}' + #13#10;
  try
    SaveStringToFile(PsFile, PsCode, False);
  except
    Exit;
  end;
  if Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    '-NoProfile -ExecutionPolicy Bypass -File "' + PsFile + '" "' + Marker + '"',
    '', SW_HIDE, ewWaitUntilTerminated, Code) then
    StepLog(M('CleanupExitCode') + IntToStr(Code))
  else
    StepLog(M('CleanupNoPs'));
end;

{ ---------------- 命令执行：输出实时写入日志并滚动上屏 ----------------
  通过 cmd /v:on 启动（延迟扩展取 !ERRORLEVEL! 到哨兵文件），
  子进程的 stdout/stderr 用 >> 实时追加进日志文件；本过程轮询刷新日志框。
  pip 在中文 Windows 上的输出为 GBK，与 StepLog 的 ANSI 写入一致。
  先 set PYTHONIOENCODING=mbcs:replace：用户环境里若设了 PYTHONUTF8 /
  PYTHONIOENCODING=utf-8（开发者电脑常见），pip 会改写 UTF-8，与 ANSI 日志
  混在一个文件里，路径含中文（如中文用户名）的行在日志中心全变乱码。
  注意必须用 /s /c "…" 整体包裹：否则 cmd 会剥掉行首/行尾引号，
  导致带空格的 Python 路径（如 C:\Program Files\…）被错误拆分。 }
function RunStep(const Title, Command: String): Integer;
var
  CodeFile: String;
  Lines: TArrayOfString;
  Waited, Dummy: Integer;
begin
  SetStatus(Title);
  StepLog('$ ' + Command);
  CodeFile := ExpandConstant('{tmp}\runstep_code.txt');
  DeleteFile(CodeFile);
  if not Exec(ExpandConstant('{cmd}'),
    '/v:on /s /c "set PYTHONIOENCODING=mbcs:replace&& ' + Command + ' >>"' + GLogFile + '" 2>&1&echo !ERRORLEVEL!>"' + CodeFile + '""',
    '', SW_HIDE, ewNoWait, Dummy) then
  begin
    StepLog(M('CmdStartFail'));
    Result := -1;
    Exit;
  end;
  Waited := 0;
  while not FileExists(CodeFile) do
  begin
    PumpSleep(350);
    Waited := Waited + 350;
    RefreshLogView();
    if Waited > RUN_TIMEOUT_MS then
    begin
      StepLog(M('CmdTimeout'));
      KillHungStep(CodeFile);
      PumpSleep(500);
      Break;
    end;
  end;
  PumpSleep(300);
  Result := -1;
  if LoadStringsFromFile(CodeFile, Lines) then
    if GetArrayLength(Lines) > 0 then
      Result := StrToIntDef(Trim(Lines[0]), -1);
  StepLog(M('ExitCodeLog') + IntToStr(Result));
  RefreshLogView();
end;

{ pip 安装类命令：失败后等待 15 秒原路重试一次。
  杀毒软件（360/电脑管家/Defender）会临时锁定新写入的 DLL（实测 onnxruntime.dll
  连续四次被锁导致全部来源失败），稍候重试即可成功——这是「组件安装不稳定」
  的主要根源之一。 }
function RunStepRetry(const Title, Command: String): Integer;
begin
  Result := RunStep(Title, Command);
  if Result <> 0 then
  begin
    StepLog(M('RetryWaitLog'));
    WizardForm.StatusLabel.Caption := M('RetryWaitStatus');
    PumpSleep(15000);
    Result := RunStep(Title + M('AutoRetry'), Command);
  end;
end;

{ 把随包 VC++ 运行库 DLL 部署到指定目录（应用本地部署，免管理员、免联网）。
  注意：venv 的 Scripts\python.exe 只是转发器，真实进程镜像是基础安装目录的
  python.exe，因此 .venv\Scripts 不在 pyd 依赖的搜索路径里——已用
  GetModuleFileNameW(NULL) 实测证实。决定性有效的位置是
  site-packages\onnxruntime\capi（与被加载的 onnxruntime_pybind11_state.pyd
  同目录，Windows 加载 pyd 时必搜该目录）。 }
procedure DeployVcrt(const TargetDir, Note: String);
var
  FindRec: TFindRec;
  SrcDir: String;
  Copied, Total: Integer;
begin
  if not DirExists(TargetDir) then Exit;
  SrcDir := ExpandConstant('{app}') + '\redist-vcrt';
  Copied := 0; Total := 0;
  if FindFirst(SrcDir + '\*.dll', FindRec) then
  try
    repeat
      Total := Total + 1;
      if CopyFile(SrcDir + '\' + FindRec.Name, TargetDir + '\' + FindRec.Name, False) then
        Copied := Copied + 1
      else
        StepLog(M('VcrtCopyFail') + FindRec.Name + ' -> ' + TargetDir);
    until not FindNext(FindRec);
  finally
    FindClose(FindRec);
  end;
  StepLog(FmtMessage(M('VcrtDeployed'), [Note, IntToStr(Copied), IntToStr(Total)]));
  if (Total = 0) or (Copied < Total) then
    StepLog(FmtMessage(M('VcrtIncomplete'), [TargetDir]));
end;

{ 校验 markitdown 可导入。校验前先把 VC++ 运行库放到 onnxruntime 的 pyd 同目录：
  onnxruntime 需要 msvcp140*.dll / vcruntime140*.dll，全新服务器（如阿里云
  Windows Server）系统里没有这些组件；每次 pip 安装都可能重写该目录，故每次
  校验前重新部署。目标目录不存在（onnxruntime 未装上）时静默跳过，由导入
  校验本身暴露真实错误。 }
function CheckCoreImport(const VenvPy, AppDir: String): Boolean;
begin
  DeployVcrt(AppDir + '\.venv\Lib\site-packages\onnxruntime\capi', M('VcrtNoteCapi'));
  Result := RunStep(M('CheckImport'), '"' + VenvPy + '" -c "import markitdown"') = 0;
end;

{ 引擎校验失败时自动收集诊断信息写入日志：真实进程镜像（venv 转发器问题排查）、
  逐 DLL 加载测试（哪个缺一目了然）、onnxruntime 目录内容、onnxruntime 导入堆栈。
  有了这一段，绝大多数「找不到指定的模块」类问题仅凭日志即可定位。 }
procedure RunPythonDiag(const VenvPy, AppDir: String);
var
  ScriptFile, Script: String;
begin
  ScriptFile := ExpandConstant('{tmp}') + '\mid_diag.py';
  Script :=
    'import ctypes, os, platform, sys' + #13#10 +
    'print("[diag] python =", sys.version.replace(chr(10), " "))' + #13#10 +
    'print("[diag] sys.executable =", sys.executable)' + #13#10 +
    'print("[diag] platform =", platform.platform())' + #13#10 +
    'buf = ctypes.create_unicode_buffer(512)' + #13#10 +
    'ctypes.windll.kernel32.GetModuleFileNameW(None, buf, 512)' + #13#10 +
    'print("[diag] process image =", buf.value)' + #13#10 +
    'print("[diag] PATH =", os.environ.get("PATH", ""))' + #13#10 +
    'k32 = ctypes.windll.kernel32' + #13#10 +
    'for name in ["msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll",' + #13#10 +
    '             "vcruntime140.dll", "vcruntime140_1.dll", "concrt140.dll"]:' + #13#10 +
    '    h = k32.LoadLibraryExW(name, None, 0x1000)' + #13#10 +
    '    if h:' + #13#10 +
    '        print("[diag] LOAD OK  :", name)' + #13#10 +
    '    else:' + #13#10 +
    '        print("[diag] LOAD FAIL:", name, "winerr =", k32.GetLastError())' + #13#10 +
    'sp = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), "Lib", "site-packages")' + #13#10 +
    'capi = os.path.join(sp, "onnxruntime", "capi")' + #13#10 +
    'print("[diag] site-packages =", sp, "exists =", os.path.isdir(sp))' + #13#10 +
    'print("[diag] capi =", capi, "exists =", os.path.isdir(capi))' + #13#10 +
    'if os.path.isdir(capi):' + #13#10 +
    '    print("[diag] capi files =", sorted(os.listdir(capi)))' + #13#10 +
    'try:' + #13#10 +
    '    import onnxruntime' + #13#10 +
    '    print("[diag] onnxruntime import OK, version =", onnxruntime.__version__)' + #13#10 +
    'except Exception as e:' + #13#10 +
    '    print("[diag] onnxruntime import FAIL:", repr(e))' + #13#10;
  if SaveStringToFile(ScriptFile, Script, False) then
    RunStep(M('DiagCollect'), '"' + VenvPy + '" "' + ScriptFile + '"')
  else
    StepLog(M('DiagWriteFail') + ScriptFile);
end;

{ 测试钩子：/SIMOFFLINE=1 模拟取消勾选「联网安装」（静默安装时点不到自定义复选框），
  用于验证离线组件包是否完整 }
function SimOffline(): Boolean;
begin
  Result := ExpandConstant('{param:SIMOFFLINE|0}') = '1';
end;

{ 测试钩子：/SIMNOPYTHON=1 模拟「电脑没有 Python」的安装路径 }
function SimNoPython(): Boolean;
begin
  Result := ExpandConstant('{param:SIMNOPYTHON|0}') = '1';
end;

{ 运行某个 python 并验证版本：探测文件由 Python 自己以 UTF-8 写入
  （旧版用 cmd 重定向输出 sys.executable，中文用户名/中文路径下读回乱码，
   FileExists 判定失败 → 明明装好了 Python 却误报错误。此版根治该问题）。
  Strict=True 要求 3.12~3.14（与离线组件一致），False 放宽到 3.10+（仅在线模式）。
  采用与 RunStep 相同的 ewNoWait + 哨兵文件轮询，并设 12 秒超时：
  旧版 ewWaitUntilTerminated 遇到损坏/被杀软拦截的解释器（如微软商店占位 stub）
  会永久卡死安装界面；超时后按不可用处理并按哨兵路径整树清理残留进程。 }
function VerifyPython(const ExeOrCmd: String; Strict: Boolean; var ExePath: String): Boolean;
var
  TmpFile, CodeFile: String;
  Lines: TArrayOfString;
  Maj, Min, Bits, MinMin, MaxMin, Code, Waited, Dummy: Integer;
begin
  Result := False;
  TmpFile := ExpandConstant('{tmp}\pydetect.txt');
  CodeFile := ExpandConstant('{tmp}\pydetect_code.txt');
  DeleteFile(TmpFile);
  DeleteFile(CodeFile);
  if not Exec(ExpandConstant('{cmd}'), '/v:on /s /c "' + ExeOrCmd +
      ' -c "import sys;open(sys.argv[1],''w'',encoding=''utf-8-sig'').write(sys.executable+''\n''+str(sys.version_info[0])+''\n''+str(sys.version_info[1])+''\n''+(''64'' if sys.maxsize>2**32 else ''32'))" "' +
      TmpFile + '"&echo !ERRORLEVEL!>"' + CodeFile + '""', '', SW_HIDE, ewNoWait, Dummy) then
    Exit;
  Waited := 0;
  while not FileExists(CodeFile) do
  begin
    PumpSleep(200);
    Waited := Waited + 200;
    RefreshLogView();
    if Waited >= 12000 then
    begin
      StepLog(M('PyDetectTimeout') + ExeOrCmd);
      KillHungStep(TmpFile);
      PumpSleep(300);
      Exit;
    end;
  end;
  PumpSleep(100);   { 等 cmd 把退出码文件写完并释放句柄 }
  Code := -1;
  if LoadStringsFromFile(CodeFile, Lines) then
    if GetArrayLength(Lines) > 0 then
      Code := StrToIntDef(Trim(Lines[0]), -1);
  if Code <> 0 then Exit;
  if not LoadStringsFromFile(TmpFile, Lines) then Exit;
  if GetArrayLength(Lines) < 4 then Exit;
  ExePath := Trim(Lines[0]);
  Maj := StrToIntDef(Trim(Lines[1]), 0);
  Min := StrToIntDef(Trim(Lines[2]), 0);
  Bits := StrToIntDef(Trim(Lines[3]), 0);
  if Strict then
  begin
    MinMin := 12; MaxMin := 14;
  end
  else
  begin
    MinMin := 10; MaxMin := 99;
  end;
  if (Maj = 3) and (Min >= MinMin) and (Min <= MaxMin) and (Bits = 64) and FileExists(ExePath) then
  begin
    GPyVer := IntToStr(Maj) + '.' + IntToStr(Min);
    Result := True;
  end;
end;

{ 读取已有 .venv\pyvenv.cfg 中某个键的值（文件或键不存在返回空串）。
  文件是 UTF-8，这里按 ANSI 读：路径含中文时读出乱码，后续校验失败会自然
  退回常规检测，不影响正确性 }
function VenvCfgValue(const AppDir, Key: String): String;
var
  Lines: TArrayOfString;
  I, P: Integer;
begin
  Result := '';
  if not LoadStringsFromFile(AppDir + '\.venv\pyvenv.cfg', Lines) then Exit;
  for I := 0 to GetArrayLength(Lines) - 1 do
  begin
    P := Pos('=', Lines[I]);
    if (P > 0) and (CompareText(Trim(Copy(Lines[I], 1, P - 1)), Key) = 0) then
    begin
      Result := Trim(Copy(Lines[I], P + 1, Length(Lines[I])));
      Exit;
    end;
  end;
end;

{ 依次尝试：py 启动器 → PATH 中的 python → 注册表(HKCU/HKLM) →
  用户目录/Program Files 常见安装位置 → 每用户 py 启动器 →
  Anaconda/Miniconda → 应用商店版 }
function DetectPython(Strict: Boolean; var ExePath: String): Boolean;
var
  Versions: TArrayOfString;
  I: Integer;
  Dir: String;
begin
  Result := True;
  if VerifyPython('py -3', Strict, ExePath) then Exit;
  if VerifyPython('python', Strict, ExePath) then Exit;
  if RegGetSubkeyNames(HKCU, 'SOFTWARE\Python\PythonCore', Versions) then
    for I := 0 to GetArrayLength(Versions) - 1 do
      if RegQueryStringValue(HKCU, 'SOFTWARE\Python\PythonCore\' + Versions[I] + '\InstallPath', '', Dir) then
        if VerifyPython('"' + RemoveBackslashUnlessRoot(Trim(Dir)) + '\python.exe"', Strict, ExePath) then Exit;
  if RegGetSubkeyNames(HKLM, 'SOFTWARE\Python\PythonCore', Versions) then
    for I := 0 to GetArrayLength(Versions) - 1 do
      if RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\' + Versions[I] + '\InstallPath', '', Dir) then
        if VerifyPython('"' + RemoveBackslashUnlessRoot(Trim(Dir)) + '\python.exe"', Strict, ExePath) then Exit;
  for I := 10 to 17 do
    if VerifyPython('"' + ExpandConstant('{localappdata}\Programs\Python\Python3' + IntToStr(I) + '\python.exe') + '"', Strict, ExePath) then Exit;
  for I := 10 to 17 do
    if VerifyPython('"' + ExpandConstant('{commonpf}\Python3' + IntToStr(I) + '\python.exe') + '"', Strict, ExePath) then Exit;
  { 每用户安装的 py 启动器 }
  if VerifyPython('"' + ExpandConstant('{localappdata}\Programs\Python\Launcher\py.exe') + '" -3', Strict, ExePath) then Exit;
  { Anaconda / Miniconda 常见安装位置（这类 Python 不写 PythonCore 注册表） }
  Dir := GetEnv('USERPROFILE');
  if Dir <> '' then
  begin
    if VerifyPython('"' + RemoveBackslashUnlessRoot(Dir) + '\Anaconda3\python.exe"', Strict, ExePath) then Exit;
    if VerifyPython('"' + RemoveBackslashUnlessRoot(Dir) + '\Miniconda3\python.exe"', Strict, ExePath) then Exit;
  end;
  if VerifyPython('"' + ExpandConstant('{commonappdata}\Anaconda3\python.exe') + '"', Strict, ExePath) then Exit;
  if VerifyPython('"' + ExpandConstant('{commonappdata}\Miniconda3\python.exe') + '"', Strict, ExePath) then Exit;
  { 微软商店版 Python 的实际入口 }
  if VerifyPython('"' + ExpandConstant('{localappdata}\Microsoft\WindowsApps\python.exe') + '"', Strict, ExePath) then Exit;
  Result := False;
end;

function DownloadFile(const Url, Dest: String): Boolean;
var
  Code: Integer;
begin
  DeleteFile(Dest);
  StepLog(M('DownloadLog') + Url);
  { curl.exe 自 Win10 1803 起内置；更早的系统没有，直接判失败走兜底 }
  if not FileExists(ExpandConstant('{sys}\curl.exe')) then
  begin
    StepLog(M('NoCurl'));
    Result := False;
    Exit;
  end;
  Result := Exec(ExpandConstant('{sys}\curl.exe'),
    '-L --fail --silent --show-error --connect-timeout 20 --max-time 600 --speed-limit 1024 --speed-time 60 -o "' + Dest + '" "' + Url + '"',
    '', SW_HIDE, ewWaitUntilTerminated, Code) and (Code = 0) and FileExists(Dest);
  StepLog(FmtMessage(M('DownloadExit'), [IntToStr(Code)]));
end;

{ 3 秒连通性预检：两条镜像有一条响应即认为网络可用（HEAD 请求，流量可忽略）。
  对「丢包不拒绝」的网络（企业防火墙静默丢 SYN），若不预检，每条 pip 线路会
  各自空转 retries×timeout，全程最坏累计 45 分钟以上，体验等同卡死；
  预检失败时直接改用内置离线组件，2-3 分钟装完。 }
function NetProbe(): Boolean;
var
  Code: Integer;
  Probe: String;
begin
  Result := True;
  if not FileExists(ExpandConstant('{sys}\curl.exe')) then Exit;
  Probe := ExpandConstant('{tmp}') + '\netprobe.txt';
  DeleteFile(Probe);
  if Exec(ExpandConstant('{sys}\curl.exe'),
    '-I -L --fail --silent --connect-timeout 3 --max-time 5 -o "' + Probe + '" "' + Mirror + '/pip/"',
    '', SW_HIDE, ewWaitUntilTerminated, Code) and (Code = 0) then Exit;
  if Exec(ExpandConstant('{sys}\curl.exe'),
    '-I -L --fail --silent --connect-timeout 3 --max-time 5 -o "' + Probe + '" "' + Mirror2 + 'pip/"',
    '', SW_HIDE, ewWaitUntilTerminated, Code) and (Code = 0) then Exit;
  Result := False;
end;

{ 安装 Python 3.12：优先用安装包内置的安装程序（完全离线），失效时才联网下载。
  装完后做多轮重试检测：注册表/PATH 刷新有延迟，且部分机器上安装器退出码
  非 0 但 Python 实际可用（如 1638=已存在更新版本），因此以检测结果为准。 }
function InstallPython(var ExePath: String): Boolean;
var
  Inst: String;
  Code, Attempt: Integer;
begin
  Result := False;
  Inst := ExpandConstant('{tmp}\' + PyInstallerName);
  if not FileExists(Inst) then
  begin
    SetStatus(M('PyDownloading'));
    if not DownloadFile('https://mirrors.huaweicloud.com/python/3.12.8/' + PyInstallerName, Inst) then
    if not DownloadFile('https://mirrors.aliyun.com/python-release/windows/' + PyInstallerName, Inst) then
    if not DownloadFile('https://www.python.org/ftp/python/3.12.8/' + PyInstallerName, Inst) then
    begin
      StepLog(M('PyFetchFail'));
      MsgBox(M('PyFetchFailMsg'), mbError, MB_OK);
      Exit;
    end;
  end
  else
    StepLog(M('PyBundled'));
  SetStatus(M('PyInstalling'));
  if not Exec(Inst, '/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 AssociateFiles=0 Include_launcher=1', '', SW_HIDE, ewWaitUntilTerminated, Code) then
    Code := -1;
  StepLog(FmtMessage(M('PyExitCode'), [IntToStr(Code)]));
  { 以检测结果为准，最多重试 15 轮（每轮 2 秒），覆盖注册表/PATH 刷新延迟 }
  for Attempt := 1 to 15 do
  begin
    if DetectPython(True, ExePath) then
    begin
      StepLog(FmtMessage(M('PyFoundRound'), [IntToStr(Attempt)]) + ExePath);
      Result := True;
      Exit;
    end;
    if Attempt < 15 then
    begin
      SetStatus(FmtMessage(M('PyWaitRound'), [IntToStr(Attempt)]));
      PumpSleep(2000);
    end;
  end;
  StepLog(M('PyNotFoundAfterInstall'));
end;

{ 文件复制完成后：检测/安装 Python → 建虚拟环境 → 分步装组件并逐步校验 }
procedure SetupEnvironment();
var
  AppDir, VenvPy: String;
  OldHome, OldVer, VenvArgs: String;
  PyFound: Boolean;
  GuiOK, CoreOK: Boolean;
  CoreUsedOffline: Boolean;
  NetOK, OcrDone, PdfiumDone: Boolean;
  WinVer: TWindowsVersion;
  OsName: String;
  FreeMB, TotalMB: Cardinal;
begin
  AppDir := ExpandConstant('{app}');
  GDepsOK := False;
  GuiOK := False;
  CoreOK := False;
  CoreUsedOffline := False;
  GLogFile := AppDir + '\' + M('InstallLogName');
  GTailBytes := 0;
  DeleteFile(GLogFile);
  StepLog(FmtMessage(M('LogHeader'), ['{#MyAppVersion}']));
  StepLog(M('InstallDirLog') + AppDir);
  { 记录系统信息，便于远程诊断（Win11 与 Win10 同为 Major=10，用 Build 区分） }
  GetWindowsVersionEx(WinVer);
  if (WinVer.Major = 10) and (WinVer.Build >= 22000) then
    OsName := 'Windows 11'
  else if WinVer.Major = 10 then
    OsName := M('OsWin10')
  else
    OsName := 'Windows ' + IntToStr(WinVer.Major) + '.' + IntToStr(WinVer.Minor);
  StepLog(FmtMessage(M('OsLine'), [OsName, IntToStr(WinVer.Build), YesNo(IsAdmin)]));
  StepLog(M('CurrentUser') + GetUserNameString);
  if GetSpaceOnDisk(ExtractFileDrive(AppDir) + '\', True, FreeMB, TotalMB) then
    StepLog(FmtMessage(M('DiskInfo'), [
      ExtractFileDrive(AppDir), Format('%.1f', [FreeMB / 1024.0]), Format('%.1f', [TotalMB / 1024.0])]));
  WizardForm.ProgressGauge.Style := npbstMarquee;
  try
    { ---- 1) Python 运行环境 ----
      覆盖安装/升级时优先沿用现有 .venv 所基于的解释器：换成别的版本（例如用户
      后来又装了 3.14，py -3 会选它）会让旧 venv 里为原版本编译的 numpy /
      onnxruntime 等全部失效，而 pip 认为它们「已安装」不会重装，导致自检失败、
      安装被判失败；沿用原解释器时已装好的组件还能直接复用，升级快得多 }
    SetStatus(M('PyChecking'));
    PyFound := False;
    OldHome := VenvCfgValue(AppDir, 'home');
    if (OldHome <> '') and not SimNoPython() then
    begin
      PyFound := VerifyPython('"' + RemoveBackslashUnlessRoot(OldHome) + '\python.exe"', True, GPythonExe);
      if PyFound then
        StepLog(M('VenvReuse') + GPythonExe);
    end;
    if not PyFound then
    if SimNoPython() or not DetectPython(True, GPythonExe) then
    begin
      { 没有 3.12~3.14：勾选时自动安装内置 Python 3.12（离线）；否则接受 3.10+ 仅在线模式 }
      if CbPython.Checked then
      begin
        if not InstallPython(GPythonExe) then
          if not DetectPython(False, GPythonExe) then
          begin
            StepLog(M('PySetupFail'));
            MarkInstallFailed(M('PySetupFailMsg'));
            MsgBox(M('PySetupFailMsg'), mbError, MB_OK);
            Exit;
          end;
      end
      else if not DetectPython(False, GPythonExe) then
      begin
        MarkInstallFailed(M('PyMissingMsg'));
        MsgBox(M('PyMissingMsg'), mbInformation, MB_OK);
        Exit;
      end;
    end;
    StepLog(M('PyUsing') + GPythonExe);

    { ---- 2) 独立虚拟环境（已有 venv 的 Python 主次版本不同则 --clear 重建） ---- }
    VenvArgs := '';
    OldVer := VenvCfgValue(AppDir, 'version');
    if (OldVer <> '') and (GPyVer <> '') and (Pos(GPyVer + '.', OldVer + '.') <> 1) then
    begin
      StepLog(FmtMessage(M('VenvRebuild'), [OldVer, GPyVer]));
      VenvArgs := ' --clear';
    end;
    RunStepRetry(M('VenvCreating'),
      '"' + GPythonExe + '" -m venv' + VenvArgs + ' "' + AppDir + '\.venv"');
    VenvPy := AppDir + '\.venv\Scripts\python.exe';
    if not FileExists(VenvPy) then
    begin
      StepLog(M('VenvFail'));
      MarkInstallFailed(M('VenvFailMsg'));
      MsgBox(M('VenvFailMsg'), mbError, MB_OK);
      Exit;
    end;

    { ---- 2b) VC++ 运行库应用本地部署（约 1.4MB，免管理员、免联网）。
            真正的生效位置是 onnxruntime 的 pyd 同目录，在每次核心校验前由
            CheckCoreImport 部署；这里往启动目录也放一份作备用（成本可忽略）。 }
    DeployVcrt(AppDir + '\.venv\Scripts', M('VcrtNoteBackup'));

    { ---- 2c) 网络预检（约 3 秒）：不通则跳过全部在线线路，直接用离线组件。
            未勾选「联网安装」时跳过预检：无网机器上两个镜像各等 3 秒超时纯属浪费，
            且预检结果也不会被使用 ---- }
    if CbGitHub.Checked and not SimOffline() then
    begin
      NetOK := NetProbe();
      if not NetOK then
        StepLog(M('NetProbeFail'));
    end
    else
    begin
      NetOK := False;
      StepLog(M('NetProbeSkip'));
    end;

    { ---- 3) 升级 pip（失败不致命，换阿里云镜像再试一次） ---- }
    if NetOK then
      if RunStepRetry(M('PipUpgrading'),
        '"' + VenvPy + '" -m pip install --upgrade pip -i ' + Mirror + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') <> 0 then
        RunStepRetry(M('PipUpgradeRetry'),
          '"' + VenvPy + '" -m pip install --upgrade pip -i ' + Mirror2 + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir');

    { ---- 4) 在线安装（勾选且网络可用时）：界面组件与转换核心分开安装、分步校验 ---- }
    if NetOK and CbGitHub.Checked then
    begin
      { 4a) 界面组件：清华镜像 → 阿里云镜像 }
      GuiOK := RunStepRetry(M('GuiInstalling'),
        '"' + VenvPy + '" -m pip install customtkinter tkinterdnd2 -i ' + Mirror + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0;
      if not GuiOK then
        GuiOK := RunStepRetry(M('GuiRetry'),
          '"' + VenvPy + '" -m pip install customtkinter tkinterdnd2 -i ' + Mirror2 + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0;
      if GuiOK then
        GuiOK := RunStep(M('GuiCheck'),
          '"' + VenvPy + '" -c "import customtkinter, tkinterdnd2"') = 0;

      { 4b) 转换核心 markitdown：PyPI 清华镜像 → 阿里云镜像（中国大陆实测 34 秒装完全部依赖）→
            GitHub 直连（快速失败，最多约 30 秒）→ 加速代理（快速失败）→ 离线 wheels 兜底。
            国内用户绝大多数在第一条线路即完成，不再先撞 GitHub 墙；
            每条线路装完立即校验导入，失败才走下一条。 }
      CoreOK := False;
      if RunStepRetry(M('CoreInstalling'),
        '"' + VenvPy + '" -m pip install "' + ExtrasSpec + '" -i ' + Mirror + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0 then
        CoreOK := CheckCoreImport(VenvPy, AppDir);
      if not CoreOK then
        if RunStepRetry(M('CoreRetry'),
          '"' + VenvPy + '" -m pip install "' + ExtrasSpec + '" -i ' + Mirror2 + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0 then
          CoreOK := CheckCoreImport(VenvPy, AppDir);
      if not CoreOK then
        if RunStep(M('CoreGitHub'),
          '"' + VenvPy + '" -m pip install "' + GitHubSpec + '" -i ' + Mirror + ' --disable-pip-version-check --no-input --retries 1 --timeout 15 --no-cache-dir') = 0 then
          CoreOK := CheckCoreImport(VenvPy, AppDir);
      if not CoreOK then
        if RunStep(M('CoreProxy'),
          '"' + VenvPy + '" -m pip install "' + GitHubSpecProxy + '" -i ' + Mirror + ' --disable-pip-version-check --no-input --retries 1 --timeout 15 --no-cache-dir') = 0 then
          CoreOK := CheckCoreImport(VenvPy, AppDir);
    end;

    { ---- 5) 任一环节失败：改用安装包内置的离线组件兜底 ---- }
    if (not GuiOK) or (not CoreOK) then
    begin
      CoreUsedOffline := True;
      StepLog(M('OfflineSwitch'));
      if RunStepRetry(M('OfflineInstalling'),
        '"' + VenvPy + '" -m pip install --no-index --find-links="' + AppDir + '\wheels" "' + ExtrasSpec + '" customtkinter tkinterdnd2 --disable-pip-version-check --no-input') = 0 then
      begin
        GuiOK := RunStep(M('GuiCheck'), '"' + VenvPy + '" -c "import customtkinter, tkinterdnd2"') = 0;
        CoreOK := CheckCoreImport(VenvPy, AppDir);
      end;
    end;

    GDepsOK := GuiOK and CoreOK;
    StepLog(FmtMessage(M('StepResults'), [OkStr(GuiOK), OkStr(CoreOK), YesNo(CoreUsedOffline)]));
    if not GDepsOK then
    begin
      StepLog(M('AllLinesFail'));
      RunPythonDiag(VenvPy, AppDir);
    end;

    { ---- 6) 图片 OCR 可选组件（winrt-*，见 OcrSpecs）：失败仅影响图片/扫描件 OCR。
            网络已证实不可用（预检失败或核心组件已走离线）时跳过在线尝试，
            直接用内置离线包，避免再空转两轮重试。
            注意：可选组件的离线兜底不置 CoreUsedOffline——它与核心组件解耦，
            不应因此连累 pypdfium2 失去在线线路，更不应因此保留离线包。 }
    { 可选组件一律 --only-binary=:all:：没有预编译包时 pip 会下载源码包、装 CMake
      编译环境再编译失败（旧版 winsdk 在 3.14 上实测每次约 25 秒，6 次尝试共白耗
      2 分 41 秒）；只装 wheel 时 1~2 秒即判定。在线两条镜像互为重试，不再额外等
      15 秒；离线兜底保留一次自动重试（应对杀软锁 DLL）。 }
    if GDepsOK then
    begin
      OcrDone := False;
      if NetOK and not CoreUsedOffline then
      begin
        if RunStep(M('OcrInstalling'),
          '"' + VenvPy + '" -m pip install ' + OcrSpecs + ' --only-binary=:all: -i ' + Mirror + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0 then
          OcrDone := True
        else if RunStep(M('OcrRetry'),
          '"' + VenvPy + '" -m pip install ' + OcrSpecs + ' --only-binary=:all: -i ' + Mirror2 + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0 then
          OcrDone := True;
      end;
      if not OcrDone then
        RunStepRetry(M('OcrOffline'),
          '"' + VenvPy + '" -m pip install --no-index --find-links="' + AppDir + '\wheels" ' + OcrSpecs + ' --only-binary=:all: --disable-pip-version-check --no-input');
      { 把 OCR 是否可用、系统装了哪些识别语言写进日志（失败不影响安装结果，便于远程排查） }
      RunStep(M('OcrCheck'),
        '"' + VenvPy + '" -c "from winrt.windows.media.ocr import OcrEngine as E; print(''OCR languages:'', [x.language_tag for x in E.available_recognizer_languages])"');

      { pypdfium2（扫描件/图片型 PDF 渲染）可选组件：与 OCR 组件配合完成图片型
        PDF 的识别，失败仅影响扫描件识别，不影响其他格式。
        与 OCR 组件独立判定，互不连累。 }
      PdfiumDone := False;
      if NetOK and not CoreUsedOffline then
      begin
        if RunStep(M('PdfiumInstalling'),
          '"' + VenvPy + '" -m pip install pypdfium2 --only-binary=:all: -i ' + Mirror + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0 then
          PdfiumDone := True
        else if RunStep(M('PdfiumRetry'),
          '"' + VenvPy + '" -m pip install pypdfium2 --only-binary=:all: -i ' + Mirror2 + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0 then
          PdfiumDone := True;
      end;
      if not PdfiumDone then
        RunStepRetry(M('PdfiumOffline'),
          '"' + VenvPy + '" -m pip install --no-index --find-links="' + AppDir + '\wheels" pypdfium2 --only-binary=:all: --disable-pip-version-check --no-input');
    end;

    { ---- 7) 自检：转换引擎能真正加载才算成功。
            失败先等 20 秒再重试一次：安全软件常在组件刚落盘时锁定 DLL，
            片刻后自动解锁；重试仍失败则自动收集诊断信息写入日志。 }
    if GDepsOK then
    begin
      GDepsOK := RunStep(M('SelfCheck'),
        '"' + VenvPy + '" -c "from markitdown import MarkItDown; MarkItDown(); print(''SELF-CHECK OK'')"') = 0;
      if not GDepsOK then
      begin
        StepLog(M('SelfCheckFail1'));
        SetStatus(M('SelfCheckWaitStatus'));
        PumpSleep(20000);
        GDepsOK := RunStep(M('SelfCheckRetry'),
          '"' + VenvPy + '" -c "from markitdown import MarkItDown; MarkItDown(); print(''SELF-CHECK OK'')"') = 0;
        if not GDepsOK then
        begin
          StepLog(M('SelfCheckFail2'));
          RunPythonDiag(VenvPy, AppDir);
          StepLog(M('SelfCheckAdvice'));
        end;
      end;
    end;

    { ---- 8) 组件版本清单写入日志，便于事后排查 ---- }
    RunStep(M('PipListLog'),
      '"' + VenvPy + '" -m pip list --disable-pip-version-check');
    StepLog(FmtMessage(M('LogFooter'), [OkStr(GDepsOK), OkStr(GuiOK), OkStr(CoreOK), YesNo(CoreUsedOffline)]));

    if GDepsOK then
    begin
      { 磁盘空间优化：在线安装成功说明本机网络可用，内置离线备用组件（约 180MB）
        已完成使命，删除以节省空间；仅当核心/界面组件动用过离线包
        （CoreUsedOffline，网络不佳的机器）才保留以备日后离线修复——
        可选组件（OCR/pypdfium2）走离线兜底不影响此决策。 }
      if CoreUsedOffline then
        StepLog(M('WheelsKept'))
      else
        if DelTree(AppDir + '\wheels', True, True, True) then
          StepLog(M('WheelsDeleted'))
        else
          StepLog(M('WheelsDelFail') + AppDir + '\wheels');
      SetStatus(M('DepsOkStatus'));
      WizardForm.FinishedLabel.Caption :=
        M('FinishedOk1') + #13#10#13#10 +
        M('FinishedOk2') + #13#10 + GLogFile + #13#10 +
        M('FinishedOk3');
    end
    else
    begin
      SetStatus(M('DepsFailStatus'));
      WizardForm.FinishedLabel.Caption :=
        M('FinishedFail1') + #13#10#13#10 +
        M('FinishedFail2') + #13#10 + GLogFile;
      MsgBox(M('DepsFailMsg'), mbError, MB_OK);
    end;
  finally
    WizardForm.ProgressGauge.Style := npbstNormal;
    RefreshLogView();
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  LangCode: String;
begin
  if CurStep = ssPostInstall then
  begin
    { 把安装时选择的语言写入 language.txt：主程序与更新器据此显示对应语言。
      先写语言文件再装环境，即使组件安装失败语言设置也不丢失。 }
    if ActiveLanguage = 'english' then LangCode := 'en' else LangCode := 'zh';
    try
      SaveStringToFile(ExpandConstant('{app}') + '\language.txt', LangCode, False);
    except
    end;
    SetupEnvironment();
  end;
end;

function VenvReady(): Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\.venv\Scripts\pythonw.exe'));
end;

procedure InitializeWizard();
var
  Page: TWizardPage;
  Lbl, Desc1, Desc2, LogHint: TNewStaticText;
begin
  { 开头的两个勾选项（紧随欢迎页，位于选择安装位置之前） }
  Page := CreateCustomPage(wpWelcome, M('OptionsTitle'), M('OptionsSub'));

  CbPython := TNewCheckBox.Create(Page);
  CbPython.Parent := Page.Surface;
  CbPython.Left := 8;
  CbPython.Top := 16;
  CbPython.Width := Page.SurfaceWidth - 16;
  CbPython.Caption := M('OptPython');
  CbPython.Checked := True;

  Desc1 := TNewStaticText.Create(Page);
  Desc1.Parent := Page.Surface;
  Desc1.Left := 32;
  Desc1.Top := 40;
  Desc1.Width := Page.SurfaceWidth - 40;
  Desc1.Caption := M('OptPythonDesc');

  CbGitHub := TNewCheckBox.Create(Page);
  CbGitHub.Parent := Page.Surface;
  CbGitHub.Left := 8;
  CbGitHub.Top := 84;
  CbGitHub.Width := Page.SurfaceWidth - 16;
  CbGitHub.Caption := M('OptOnline');
  CbGitHub.Checked := True;

  Desc2 := TNewStaticText.Create(Page);
  Desc2.Parent := Page.Surface;
  Desc2.Left := 32;
  Desc2.Top := 108;
  Desc2.Width := Page.SurfaceWidth - 40;
  Desc2.Caption := M('OptOnlineDesc');

  Lbl := TNewStaticText.Create(Page);
  Lbl.Parent := Page.Surface;
  Lbl.Left := 8;
  Lbl.Top := 156;
  Lbl.Width := Page.SurfaceWidth - 16;
  Lbl.Caption := M('OptionsNote');

  { 安装页：进度条下方增加实时滚动日志框 }
  LogHint := TNewStaticText.Create(WizardForm);
  LogHint.Parent := WizardForm.InstallingPage;
  LogHint.SetBounds(WizardForm.ProgressGauge.Left,
    WizardForm.ProgressGauge.Top + WizardForm.ProgressGauge.Height + ScaleY(6),
    WizardForm.ProgressGauge.Width, ScaleY(14));
  LogHint.Caption := M('LogHint');
  LogHint.Font.Size := 8;

  LogMemo := TNewMemo.Create(WizardForm);
  LogMemo.Parent := WizardForm.InstallingPage;
  LogMemo.SetBounds(WizardForm.ProgressGauge.Left,
    WizardForm.ProgressGauge.Top + WizardForm.ProgressGauge.Height + ScaleY(22),
    WizardForm.ProgressGauge.Width,
    WizardForm.InstallingPage.ClientHeight - WizardForm.ProgressGauge.Top - WizardForm.ProgressGauge.Height - ScaleY(34));
  LogMemo.Anchors := [akLeft, akTop, akRight, akBottom];
  LogMemo.ScrollBars := ssBoth;
  LogMemo.WordWrap := False;
  LogMemo.ReadOnly := True;
  LogMemo.Font.Name := 'Consolas';
  LogMemo.Font.Size := 8;
end;
