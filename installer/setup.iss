; ============================================================
; MarkItDown 转换器 安装脚本 (Inno Setup 6)
; 功能：Python 环境检测/安装、GitHub 在线组件 + PyPI 镜像 + 离线备用组件、
;       自定义安装位置、微信文件位置识别（程序内置）、检查更新、
;       实时滚动日志（同步写入「安装日志.txt」，系统 ANSI 编码，可在日志中心导出 PDF/TXT）、
;       VC++ 运行库随包应用本地部署（免管理员，适配全新系统/服务器）、
;       完整卸载、首次启动自动打开使用说明书。
; 适用系统：Windows 10 / 11（x64，不含 ARM）及同代 Windows Server。
; ============================================================
#define MyAppName "MarkItDown 转换器"
#define MyAppVersion "1.1.4"

[Setup]
AppId={{D4A7C2E1-3F5B-4E6A-9B8C-7D0E1F2A3B4C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=MarkItDown Converter
AppUpdatesURL=https://github.com/microsoft/markitdown
DefaultDirName={autopf}\MarkItDownConverter
DefaultGroupName=MarkItDown 转换器
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0
OutputDir=Output
OutputBaseFilename=MarkItDown转换器安装包_v{#MyAppVersion}
SetupIconFile=src\app.ico
UninstallDisplayIcon={app}\app.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany=MarkItDown Converter
VersionInfoDescription=MarkItDown 转换器 安装程序
VersionInfoProductName=MarkItDown 转换器
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "chinesesimp"; MessagesFile: "languages\ChineseSimplified.isl"

[Files]
Source: "src\markitdown_gui.py"; DestDir: "{app}"
Source: "src\update.pyw"; DestDir: "{app}"
Source: "src\logtools.py"; DestDir: "{app}"
Source: "src\app.ico"; DestDir: "{app}"
Source: "src\MarkItDown转换器使用说明书.pdf"; DestDir: "{app}"
Source: "src\VERSION"; DestDir: "{app}"
Source: "src\redist\python-3.12.8-amd64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "src\redist\vcrt\*"; DestDir: "{app}\redist-vcrt"
Source: "src\wheels\*"; DestDir: "{app}\wheels"

[Icons]
Name: "{autodesktop}\MarkItDown 转换器"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\markitdown_gui.py"""; WorkingDir: "{app}"; IconFilename: "{app}\app.ico"
Name: "{group}\MarkItDown 转换器"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\markitdown_gui.py"""; WorkingDir: "{app}"; IconFilename: "{app}\app.ico"
Name: "{group}\使用说明书"; Filename: "{app}\MarkItDown转换器使用说明书.pdf"; IconFilename: "{app}\app.ico"
Name: "{group}\检查更新 · 日志中心"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\update.pyw"""; WorkingDir: "{app}"; IconFilename: "{app}\app.ico"
Name: "{group}\卸载 MarkItDown 转换器"; Filename: "{uninstallexe}"; IconFilename: "{app}\app.ico"

[Run]
Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\markitdown_gui.py"""; WorkingDir: "{app}"; Description: "立即运行 MarkItDown 转换器（首次启动会自动打开使用说明书）"; Flags: postinstall nowait skipifsilent; Check: VenvReady

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files; Name: "{app}\markitdown_gui_config.json"
Type: files; Name: "{app}\安装日志.txt"
Type: files; Name: "{app}\更新日志.txt"

[Code]
procedure Sleep(dwMilliseconds: Cardinal); external 'Sleep@kernel32.dll stdcall';
function SendMessage(hWnd: LongInt; Msg: LongInt; wParam: LongInt; lParam: LongInt): LongInt; external 'SendMessageA@user32.dll stdcall';

var
  CbPython, CbGitHub: TNewCheckBox;
  LogMemo: TNewMemo;
  GPythonExe: String;
  GDepsOK: Boolean;
  GLogFile: String;
  GTailLine: Integer;

const
  PyInstallerName = 'python-3.12.8-amd64.exe';
  Mirror = 'https://pypi.tuna.tsinghua.edu.cn/simple';
  Mirror2 = 'https://mirrors.aliyun.com/pypi/simple/';
  GitHubSpec = 'markitdown[pptx,docx,xlsx,xls,pdf,outlook,audio-transcription] @ https://codeload.github.com/microsoft/markitdown/zip/refs/heads/main#subdirectory=packages/markitdown';
  GitHubSpecProxy = 'markitdown[pptx,docx,xlsx,xls,pdf,outlook,audio-transcription] @ https://gh-proxy.com/https://codeload.github.com/microsoft/markitdown/zip/refs/heads/main#subdirectory=packages/markitdown';
  ExtrasSpec = 'markitdown[pptx,docx,xlsx,xls,pdf,outlook,audio-transcription]';
  EM_VSCROLL = $00B5;
  SB_BOTTOM = 7;
  RUN_TIMEOUT_MS = 1800000;   { 单条命令最长 30 分钟，防死等 }

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

{ 安装页上的实时日志框：把日志文件新增的行滚动显示出来 }
procedure RefreshLogView();
var
  Lines: TArrayOfString;
  I: Integer;
begin
  if GLogFile = '' then Exit;
  if not FileExists(GLogFile) then Exit;
  if not LoadStringsFromFile(GLogFile, Lines) then Exit;   { 文件被占用时本轮跳过 }
  if GTailLine > GetArrayLength(Lines) then GTailLine := 0;
  for I := GTailLine to GetArrayLength(Lines) - 1 do
    LogMemo.Lines.Add(Lines[I]);
  GTailLine := GetArrayLength(Lines);
  while LogMemo.Lines.Count > 600 do
    LogMemo.Lines.Delete(0);
  SendMessage(LogMemo.Handle, EM_VSCROLL, SB_BOTTOM, 0);
  LogMemo.Update;
end;

procedure SetStatus(const S: String);
begin
  WizardForm.StatusLabel.Caption := S;
  StepLog('== ' + S);
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
    StepLog('  残留进程树清理退出码 = ' + IntToStr(Code))
  else
    StepLog('!! 无法启动 PowerShell 清理残留进程；若后续步骤异常，请重启电脑后重试安装');
end;

{ ---------------- 命令执行：输出实时写入日志并滚动上屏 ----------------
  通过 cmd /v:on 启动（延迟扩展取 !ERRORLEVEL! 到哨兵文件），
  子进程的 stdout/stderr 用 >> 实时追加进日志文件；本过程轮询刷新日志框。
  pip 在中文 Windows 上的输出为 GBK，与 StepLog 的 ANSI 写入一致。
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
    '/v:on /s /c "' + Command + ' >>"' + GLogFile + '" 2>&1&echo !ERRORLEVEL!>"' + CodeFile + '""',
    '', SW_HIDE, ewNoWait, Dummy) then
  begin
    StepLog('!! 命令启动失败');
    Result := -1;
    Exit;
  end;
  Waited := 0;
  while not FileExists(CodeFile) do
  begin
    Sleep(350);
    Waited := Waited + 350;
    RefreshLogView();
    if Waited > RUN_TIMEOUT_MS then
    begin
      StepLog('!! 命令超过 30 分钟未结束，正在强制终止该进程树（防残留进程干扰后续步骤）…');
      KillHungStep(CodeFile);
      Sleep(500);
      Break;
    end;
  end;
  Sleep(300);
  Result := -1;
  if LoadStringsFromFile(CodeFile, Lines) then
    if GetArrayLength(Lines) > 0 then
      Result := StrToIntDef(Trim(Lines[0]), -1);
  StepLog('  退出码 = ' + IntToStr(Result));
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
    StepLog('等待 15 秒后重试同一来源（应对杀毒软件临时锁定文件）…');
    WizardForm.StatusLabel.Caption := '遇到干扰，15 秒后自动重试（杀毒软件可能正在扫描文件）…';
    Sleep(15000);
    Result := RunStep(Title + '（自动重试）', Command);
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
        StepLog('!! VC++ 运行库复制失败: ' + FindRec.Name + ' -> ' + TargetDir);
    until not FindNext(FindRec);
  finally
    FindClose(FindRec);
  end;
  StepLog('VC++ 运行库部署（' + Note + '）: ' + IntToStr(Copied) + ' / ' + IntToStr(Total) + ' 个文件');
  if (Total = 0) or (Copied < Total) then
    StepLog('!! VC++ 运行库未完整部署到 ' + TargetDir + '；若自检提示 DLL load failed，请安装微软 VC++ 2015-2022 x64 运行库');
end;

{ 校验 markitdown 可导入。校验前先把 VC++ 运行库放到 onnxruntime 的 pyd 同目录：
  onnxruntime 需要 msvcp140*.dll / vcruntime140*.dll，全新服务器（如阿里云
  Windows Server）系统里没有这些组件；每次 pip 安装都可能重写该目录，故每次
  校验前重新部署。目标目录不存在（onnxruntime 未装上）时静默跳过，由导入
  校验本身暴露真实错误。 }
function CheckCoreImport(const VenvPy, AppDir: String): Boolean;
begin
  DeployVcrt(AppDir + '\.venv\Lib\site-packages\onnxruntime\capi', 'onnxruntime 组件目录');
  Result := RunStep('校验 markitdown 可导入 …', '"' + VenvPy + '" -c "import markitdown"') = 0;
end;

function OkStr(B: Boolean): String;
begin
  if B then Result := 'OK' else Result := '失败';
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
    RunStep('收集诊断信息（写入日志，便于排查）…', '"' + VenvPy + '" "' + ScriptFile + '"')
  else
    StepLog('!! 诊断脚本写入失败: ' + ScriptFile);
end;

{ 测试钩子：/SIMNOPYTHON=1 模拟「电脑没有 Python」的安装路径 }
function SimNoPython(): Boolean;
begin
  Result := ExpandConstant('{param:SIMNOPYTHON|0}') = '1';
end;

{ 运行某个 python 并验证版本：探测文件由 Python 自己以 UTF-8 写入
  （旧版用 cmd 重定向输出 sys.executable，中文用户名/中文路径下读回乱码，
   FileExists 判定失败 → 明明装好了 Python 却误报错误。此版根治该问题）。
  Strict=True 要求 3.12~3.14（与离线组件一致），False 放宽到 3.10+（仅在线模式）。 }
function VerifyPython(const ExeOrCmd: String; Strict: Boolean; var ExePath: String): Boolean;
var
  TmpFile: String;
  Lines: TArrayOfString;
  Maj, Min, Bits, MinMin, MaxMin, Code: Integer;
begin
  Result := False;
  TmpFile := ExpandConstant('{tmp}\pydetect.txt');
  DeleteFile(TmpFile);
  if not Exec(ExpandConstant('{cmd}'), '/s /c "' + ExeOrCmd +
      ' -c "import sys;open(sys.argv[1],''w'',encoding=''utf-8-sig'').write(sys.executable+''\n''+str(sys.version_info[0])+''\n''+str(sys.version_info[1])+''\n''+(''64'' if sys.maxsize>2**32 else ''32''))" "' +
      TmpFile + '""', '', SW_HIDE, ewWaitUntilTerminated, Code) then
    Exit;
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
    Result := True;
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
  StepLog('下载: ' + Url);
  { curl.exe 自 Win10 1803 起内置；更早的系统没有，直接判失败走兜底 }
  if not FileExists(ExpandConstant('{sys}\curl.exe')) then
  begin
    StepLog('  系统无内置 curl.exe（Windows 版本过旧），跳过在线下载');
    Result := False;
    Exit;
  end;
  Result := Exec(ExpandConstant('{sys}\curl.exe'),
    '-L --fail --silent --show-error --connect-timeout 20 --max-time 600 --speed-limit 1024 --speed-time 60 -o "' + Dest + '" "' + Url + '"',
    '', SW_HIDE, ewWaitUntilTerminated, Code) and (Code = 0) and FileExists(Dest);
  StepLog('  下载退出码 = ' + IntToStr(Code) + '（28=整体超时/低速超时，60 秒平均低于 1KB/s 即放弃）');
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
    SetStatus('正在下载 Python 安装程序（约 26MB，请耐心等待）…');
    if not DownloadFile('https://mirrors.huaweicloud.com/python/3.12.8/' + PyInstallerName, Inst) then
    if not DownloadFile('https://mirrors.aliyun.com/python-release/windows/' + PyInstallerName, Inst) then
    if not DownloadFile('https://www.python.org/ftp/python/3.12.8/' + PyInstallerName, Inst) then
    begin
      StepLog('!! 获取 Python 安装程序失败');
      MsgBox('获取 Python 安装程序失败。请手动安装 Python 3.12 ~ 3.14（64 位）后重新运行本安装程序。', mbError, MB_OK);
      Exit;
    end;
  end
  else
    StepLog('使用安装包内置的 Python 安装程序。');
  SetStatus('正在安装 Python 3.12（约需 1-2 分钟，期间无提示属正常）…');
  if not Exec(Inst, '/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 AssociateFiles=0 Include_launcher=1', '', SW_HIDE, ewWaitUntilTerminated, Code) then
    Code := -1;
  StepLog('Python 安装程序退出码 = ' + IntToStr(Code) + '（0/3010=成功；1638=已存在更新版本）');
  { 以检测结果为准，最多重试 15 轮（每轮 2 秒），覆盖注册表/PATH 刷新延迟 }
  for Attempt := 1 to 15 do
  begin
    if DetectPython(True, ExePath) then
    begin
      StepLog('第 ' + IntToStr(Attempt) + ' 轮检测找到 Python: ' + ExePath);
      Result := True;
      Exit;
    end;
    if Attempt < 15 then
    begin
      SetStatus('正在等待 Python 环境就绪（第 ' + IntToStr(Attempt) + ' / 15 轮检测）…');
      Sleep(2000);
    end;
  end;
  StepLog('!! Python 安装后多次检测仍未找到可用解释器');
end;

{ 文件复制完成后：检测/安装 Python → 建虚拟环境 → 分步装组件并逐步校验 }
procedure SetupEnvironment();
var
  AppDir, VenvPy: String;
  GuiOK, CoreOK: Boolean;
  UsedOffline: Boolean;
  NetOK, WinsdkDone, PdfiumDone: Boolean;
  WinVer: TWindowsVersion;
  OsName, AdminStr: String;
  FreeMB, TotalMB: Cardinal;
begin
  AppDir := ExpandConstant('{app}');
  GDepsOK := False;
  GuiOK := False;
  CoreOK := False;
  UsedOffline := False;
  GLogFile := AppDir + '\安装日志.txt';
  GTailLine := 0;
  DeleteFile(GLogFile);
  StepLog('==== MarkItDown 转换器 安装日志 v{#MyAppVersion} ====');
  StepLog('安装目录: ' + AppDir);
  { 记录系统信息，便于远程诊断（Win11 与 Win10 同为 Major=10，用 Build 区分） }
  GetWindowsVersionEx(WinVer);
  if (WinVer.Major = 10) and (WinVer.Build >= 22000) then
    OsName := 'Windows 11'
  else if WinVer.Major = 10 then
    OsName := 'Windows 10 / 同代 Server'
  else
    OsName := 'Windows ' + IntToStr(WinVer.Major) + '.' + IntToStr(WinVer.Minor);
  if IsAdmin then AdminStr := '是' else AdminStr := '否';
  StepLog('系统: ' + OsName + '  Build ' + IntToStr(WinVer.Build) + '  (x64, 管理员: ' + AdminStr + ')');
  StepLog('当前用户: ' + GetUserNameString);
  if GetSpaceOnDisk(ExtractFileDrive(AppDir) + '\', True, FreeMB, TotalMB) then
    StepLog(Format('磁盘: %s 盘剩余 %.1f GB / 共 %.1f GB', [
      ExtractFileDrive(AppDir), FreeMB / 1024.0, TotalMB / 1024.0]));
  WizardForm.ProgressGauge.Style := npbstMarquee;
  try
    { ---- 1) Python 运行环境 ---- }
    SetStatus('正在检测 Python 运行环境…');
    if SimNoPython() or not DetectPython(True, GPythonExe) then
    begin
      { 没有 3.12~3.14：勾选时自动安装内置 Python 3.12（离线）；否则接受 3.10+ 仅在线模式 }
      if CbPython.Checked then
      begin
        if not InstallPython(GPythonExe) then
          if not DetectPython(False, GPythonExe) then
          begin
            StepLog('!! 未能配置 Python 环境');
            MsgBox('未能配置 Python 环境。请手动安装 Python 3.12 ~ 3.14（64 位）后重新运行本安装程序。', mbError, MB_OK);
            Exit;
          end;
      end
      else if not DetectPython(False, GPythonExe) then
      begin
        MsgBox('未检测到 Python 3.10 及以上版本，且未勾选自动安装。转换器暂时无法运行。', mbInformation, MB_OK);
        Exit;
      end;
    end;
    StepLog('使用 Python: ' + GPythonExe);

    { ---- 2) 独立虚拟环境 ---- }
    RunStepRetry('正在创建独立运行环境（约 1 分钟）…',
      '"' + GPythonExe + '" -m venv "' + AppDir + '\.venv"');
    VenvPy := AppDir + '\.venv\Scripts\python.exe';
    if not FileExists(VenvPy) then
    begin
      StepLog('!! 创建运行环境失败');
      MsgBox('创建运行环境失败，请尝试更换安装位置后重新安装。', mbError, MB_OK);
      Exit;
    end;

    { ---- 2b) VC++ 运行库应用本地部署（约 1.4MB，免管理员、免联网）。
            真正的生效位置是 onnxruntime 的 pyd 同目录，在每次核心校验前由
            CheckCoreImport 部署；这里往启动目录也放一份作备用（成本可忽略）。 }
    DeployVcrt(AppDir + '\.venv\Scripts', 'python 启动目录·备用');

    { ---- 2c) 网络预检（约 3 秒）：不通则跳过全部在线线路，直接用离线组件 ---- }
    NetOK := NetProbe();
    if not NetOK then
      StepLog('!! 网络预检未通过（两条镜像 3 秒内均无响应）：跳过在线安装，直接使用内置离线组件。');

    { ---- 3) 升级 pip（失败不致命，换阿里云镜像再试一次） ---- }
    if NetOK then
      if RunStepRetry('正在升级 pip（清华镜像）…',
        '"' + VenvPy + '" -m pip install --upgrade pip -i ' + Mirror + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') <> 0 then
        RunStepRetry('清华镜像失败，正在用阿里云镜像重试升级 pip …',
          '"' + VenvPy + '" -m pip install --upgrade pip -i ' + Mirror2 + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir');

    { ---- 4) 在线安装（勾选且网络可用时）：界面组件与转换核心分开安装、分步校验 ---- }
    if NetOK and CbGitHub.Checked then
    begin
      { 4a) 界面组件：清华镜像 → 阿里云镜像 }
      GuiOK := RunStepRetry('正在安装界面组件 customtkinter / tkinterdnd2（清华镜像）…',
        '"' + VenvPy + '" -m pip install customtkinter tkinterdnd2 -i ' + Mirror + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0;
      if not GuiOK then
        GuiOK := RunStepRetry('界面组件清华镜像失败，正在用阿里云镜像重试 …',
          '"' + VenvPy + '" -m pip install customtkinter tkinterdnd2 -i ' + Mirror2 + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0;
      if GuiOK then
        GuiOK := RunStep('校验界面组件可导入 …',
          '"' + VenvPy + '" -c "import customtkinter, tkinterdnd2"') = 0;

      { 4b) 转换核心 markitdown：PyPI 清华镜像 → 阿里云镜像（中国大陆实测 34 秒装完全部依赖）→
            GitHub 直连（快速失败，最多约 30 秒）→ 加速代理（快速失败）→ 离线 wheels 兜底。
            国内用户绝大多数在第一条线路即完成，不再先撞 GitHub 墙；
            每条线路装完立即校验导入，失败才走下一条。 }
      CoreOK := False;
      if RunStepRetry('正在从清华镜像安装 MarkItDown 组件（约 1-3 分钟）…',
        '"' + VenvPy + '" -m pip install "' + ExtrasSpec + '" -i ' + Mirror + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0 then
        CoreOK := CheckCoreImport(VenvPy, AppDir);
      if not CoreOK then
        if RunStepRetry('清华镜像失败，正在改用阿里云镜像安装 …',
          '"' + VenvPy + '" -m pip install "' + ExtrasSpec + '" -i ' + Mirror2 + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0 then
          CoreOK := CheckCoreImport(VenvPy, AppDir);
      if not CoreOK then
        if RunStep('国内镜像均失败，正在尝试 GitHub 直连（快速判定，失败不超过 1 分钟）…',
          '"' + VenvPy + '" -m pip install "' + GitHubSpec + '" -i ' + Mirror + ' --disable-pip-version-check --no-input --retries 1 --timeout 15 --no-cache-dir') = 0 then
          CoreOK := CheckCoreImport(VenvPy, AppDir);
      if not CoreOK then
        if RunStep('GitHub 直连失败，正在通过加速代理下载（快速判定）…',
          '"' + VenvPy + '" -m pip install "' + GitHubSpecProxy + '" -i ' + Mirror + ' --disable-pip-version-check --no-input --retries 1 --timeout 15 --no-cache-dir') = 0 then
          CoreOK := CheckCoreImport(VenvPy, AppDir);
    end;

    { ---- 5) 任一环节失败：改用安装包内置的离线组件兜底 ---- }
    if (not GuiOK) or (not CoreOK) then
    begin
      UsedOffline := True;
      StepLog('在线安装未完全成功，切换到内置离线组件。');
      if RunStepRetry('正在使用安装包内置的离线组件（约 1-3 分钟）…',
        '"' + VenvPy + '" -m pip install --no-index --find-links="' + AppDir + '\wheels" "' + ExtrasSpec + '" customtkinter tkinterdnd2 --disable-pip-version-check --no-input') = 0 then
      begin
        GuiOK := RunStep('校验界面组件可导入 …', '"' + VenvPy + '" -c "import customtkinter, tkinterdnd2"') = 0;
        CoreOK := CheckCoreImport(VenvPy, AppDir);
      end;
    end;

    GDepsOK := GuiOK and CoreOK;
    if UsedOffline then AdminStr := '是' else AdminStr := '否';
    StepLog('分步结果: 界面组件=' + OkStr(GuiOK) + ', 转换核心=' + OkStr(CoreOK) +
      ', 动用离线包=' + AdminStr);
    if not GDepsOK then
    begin
      StepLog('!! 各条安装线路均未通过校验，正在收集诊断信息 …');
      RunPythonDiag(VenvPy, AppDir);
    end;

    { ---- 6) winsdk（Windows OCR）可选组件：失败仅影响图片 OCR。
            网络已证实不可用（预检失败或核心组件已走离线）时跳过在线尝试，
            直接用内置离线包，避免再空转两轮重试。 }
    if GDepsOK then
    begin
      WinsdkDone := False;
      if NetOK and not UsedOffline then
      begin
        if RunStepRetry('正在安装可选的图片 OCR 组件 winsdk（失败不影响使用）…',
          '"' + VenvPy + '" -m pip install winsdk -i ' + Mirror + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0 then
          WinsdkDone := True
        else if RunStepRetry('winsdk 清华镜像失败，正在用阿里云镜像重试 …',
          '"' + VenvPy + '" -m pip install winsdk -i ' + Mirror2 + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0 then
          WinsdkDone := True;
      end;
      if not WinsdkDone then
      begin
        UsedOffline := True;
        RunStepRetry('正在用内置离线包安装 OCR 组件 …',
          '"' + VenvPy + '" -m pip install --no-index --find-links="' + AppDir + '\wheels" winsdk --disable-pip-version-check --no-input');
      end;

      { pypdfium2（扫描件/图片型 PDF 渲染）可选组件：与 winsdk 配合完成图片型
        PDF 的 OCR 识别，失败仅影响扫描件识别，不影响其他格式。 }
      PdfiumDone := False;
      if NetOK and not UsedOffline then
      begin
        if RunStepRetry('正在安装扫描件识别组件 pypdfium2（失败不影响使用）…',
          '"' + VenvPy + '" -m pip install pypdfium2 -i ' + Mirror + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0 then
          PdfiumDone := True
        else if RunStepRetry('pypdfium2 清华镜像失败，正在用阿里云镜像重试 …',
          '"' + VenvPy + '" -m pip install pypdfium2 -i ' + Mirror2 + ' --disable-pip-version-check --no-input --retries 5 --timeout 30 --no-cache-dir') = 0 then
          PdfiumDone := True;
      end;
      if not PdfiumDone then
      begin
        UsedOffline := True;
        RunStepRetry('正在用内置离线包安装 pypdfium2 …',
          '"' + VenvPy + '" -m pip install --no-index --find-links="' + AppDir + '\wheels" pypdfium2 --disable-pip-version-check --no-input');
      end;
    end;

    { ---- 7) 自检：转换引擎能真正加载才算成功。
            失败先等 20 秒再重试一次：安全软件常在组件刚落盘时锁定 DLL，
            片刻后自动解锁；重试仍失败则自动收集诊断信息写入日志。 }
    if GDepsOK then
    begin
      GDepsOK := RunStep('正在自检转换引擎 …',
        '"' + VenvPy + '" -c "from markitdown import MarkItDown; MarkItDown(); print(''SELF-CHECK OK'')"') = 0;
      if not GDepsOK then
      begin
        StepLog('!! 首次自检失败（详见上方错误堆栈）。常见原因：安全软件临时锁定 DLL。等待 20 秒后重试 …');
        SetStatus('首次自检失败，等待 20 秒后重试 …');
        Sleep(20000);
        GDepsOK := RunStep('正在重新自检转换引擎 …',
          '"' + VenvPy + '" -c "from markitdown import MarkItDown; MarkItDown(); print(''SELF-CHECK OK'')"') = 0;
        if not GDepsOK then
        begin
          StepLog('!! 再次自检仍失败，正在收集诊断信息 …');
          RunPythonDiag(VenvPy, AppDir);
          StepLog('!! 请把本日志发给发送安装包的人，上方 [diag] 段落可直接定位问题。');
        end;
      end;
    end;

    { ---- 8) 组件版本清单写入日志，便于事后排查 ---- }
    RunStep('记录组件版本清单（pip list）…',
      '"' + VenvPy + '" -m pip list --disable-pip-version-check');
    if UsedOffline then AdminStr := '是' else AdminStr := '否';
    StepLog('==== 安装流程结束: 总体=' + OkStr(GDepsOK) + '（界面组件=' + OkStr(GuiOK) +
      ', 转换核心=' + OkStr(CoreOK) + ', 动用离线包=' + AdminStr + '） ====');

    if GDepsOK then
    begin
      { 磁盘空间优化：在线安装成功说明本机网络可用，内置离线备用组件（约 245MB）
        已完成使命，删除以节省空间；若安装过程动用过离线包（网络不佳的机器），
        则保留以备日后离线修复。 }
      if UsedOffline then
        StepLog('本次安装使用了内置离线组件，保留 wheels 目录以备日后离线修复。')
      else
        if DelTree(AppDir + '\wheels', True, True, True) then
          StepLog('在线安装成功，已删除内置离线备用组件（释放约 245MB 磁盘空间）。')
        else
          StepLog('!! 离线备用组件删除失败，不影响使用；可手动删除: ' + AppDir + '\wheels');
      SetStatus('组件安装完成，自检通过。');
      WizardForm.FinishedLabel.Caption :=
        '安装已完成，MarkItDown 转换器可以使用了。' + #13#10#13#10 +
        '安装日志已保存到：' + #13#10 + GLogFile + #13#10 +
        '（如以后遇到问题，可在开始菜单「检查更新 · 日志中心」中查看并导出 PDF/TXT 日志）';
    end
    else
    begin
      SetStatus('组件未能完整安装。');
      WizardForm.FinishedLabel.Caption :=
        '安装未完全成功：组件未能完整安装。' + #13#10#13#10 +
        '请联网后运行开始菜单「检查更新 · 日志中心」自动补全；' + #13#10 +
        '若多次失败，请把以下日志文件发给发送安装包的人：' + #13#10 + GLogFile;
      MsgBox('组件未能完整安装。请联网后运行开始菜单「检查更新」自动补全；若多次失败，请联系发送安装包的人。', mbError, MB_OK);
    end;
  finally
    WizardForm.ProgressGauge.Style := npbstNormal;
    RefreshLogView();
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    SetupEnvironment();
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
  Page := CreateCustomPage(wpWelcome, '安装选项', '本安装程序将执行以下两项操作（推荐保持勾选）');

  CbPython := TNewCheckBox.Create(Page);
  CbPython.Parent := Page.Surface;
  CbPython.Left := 8;
  CbPython.Top := 16;
  CbPython.Width := Page.SurfaceWidth - 16;
  CbPython.Caption := '① 检测并安装 Python 运行环境（必需）';
  CbPython.Checked := True;

  Desc1 := TNewStaticText.Create(Page);
  Desc1.Parent := Page.Surface;
  Desc1.Left := 32;
  Desc1.Top := 40;
  Desc1.Width := Page.SurfaceWidth - 40;
  Desc1.Caption := '若电脑没有 Python 或版本不符，将自动安装安装包内置的 Python 3.12（无需联网）；已安装则自动跳过。';

  CbGitHub := TNewCheckBox.Create(Page);
  CbGitHub.Parent := Page.Surface;
  CbGitHub.Left := 8;
  CbGitHub.Top := 84;
  CbGitHub.Width := Page.SurfaceWidth - 16;
  CbGitHub.Caption := '② 联网安装最新版 MarkItDown 组件（推荐，优先国内镜像）';
  CbGitHub.Checked := True;

  Desc2 := TNewStaticText.Create(Page);
  Desc2.Parent := Page.Surface;
  Desc2.Left := 32;
  Desc2.Top := 108;
  Desc2.Width := Page.SurfaceWidth - 40;
  Desc2.Caption := '下载失败、无网络或取消勾选时，自动改用安装包内置的离线组件，功能相同。';

  Lbl := TNewStaticText.Create(Page);
  Lbl.Parent := Page.Surface;
  Lbl.Left := 8;
  Lbl.Top := 156;
  Lbl.Width := Page.SurfaceWidth - 16;
  Lbl.Caption := '说明：安装全程实时日志见安装页下方；安装后可在「检查更新 · 日志中心」导出 PDF/TXT。';

  { 安装页：进度条下方增加实时滚动日志框 }
  LogHint := TNewStaticText.Create(WizardForm);
  LogHint.Parent := WizardForm.InstallingPage;
  LogHint.SetBounds(WizardForm.ProgressGauge.Left,
    WizardForm.ProgressGauge.Top + WizardForm.ProgressGauge.Height + ScaleY(6),
    WizardForm.ProgressGauge.Width, ScaleY(14));
  LogHint.Caption := '详细日志（实时滚动，完整内容见安装目录「安装日志.txt」）：';
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
