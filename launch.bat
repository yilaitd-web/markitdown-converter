@echo off
rem MarkItDown 转换器启动器（无控制台窗口）/ Launcher (no console window)
rem 使用 PATH 中的 pythonw；如需指定解释器，请先设置 PYTHONW 环境变量。
rem Uses pythonw from PATH; set the PYTHONW env var to use a specific interpreter.
if defined PYTHONW (set "PYW=%PYTHONW%") else (set "PYW=pythonw")
start "" "%PYW%" "%~dp0src\markitdown_gui.py"
