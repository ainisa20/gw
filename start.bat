@echo off
REM 启动脚本 - Windows

cd /d "%~dp0"

REM 检查 Python3
python3 --version >nul 2>&1
if %errorlevel% neq 0 (
  python --version >nul 2>&1
  if %errorlevel% neq 0 (
    echo ❌ 未检测到 Python3，请先安装：https://www.python.org/downloads/
    echo    安装时勾选 "Add Python to PATH"
    pause
    exit /b 1
  )
  set PYTHON=python
) else (
  set PYTHON=python3
)

REM 检查 wxPython
%PYTHON% -c "import wx" >nul 2>&1
if %errorlevel% neq 0 (
  echo ⚠️  未检测到 wxPython，正在安装...
  %PYTHON% -m pip install wxPython
  if %errorlevel% neq 0 (
    echo ❌ wxPython 安装失败，请手动执行: pip install wxPython
    pause
    exit /b 1
  )
)

echo 🚀 启动表单填写助手...
%PYTHON% form_helper.py
pause
