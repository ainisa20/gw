#!/bin/bash
# 启动脚本 - macOS / Linux

cd "$(dirname "$0")"

# 检查 Python3
if ! command -v python3 &> /dev/null; then
  echo "❌ 未检测到 Python3，请先安装："
  echo "   macOS:  brew install python3"
  echo "   Linux:  sudo apt install python3"
  exit 1
fi

# 检查 wxPython
python3 -c "import wx" 2> /dev/null
if [ $? -ne 0 ]; then
  echo "⚠️  未检测到 wxPython，正在安装..."
  pip3 install wxPython
  if [ $? -ne 0 ]; then
    echo "❌ wxPython 安装失败，请手动执行: pip3 install wxPython"
    exit 1
  fi
fi

echo "🚀 启动表单填写助手..."
python3 form_helper.py
