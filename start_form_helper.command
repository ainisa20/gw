#!/bin/bash
cd "$(dirname "$0")"

if ! command -v python3 &> /dev/null; then
  echo "❌ 未检测到 Python3，请先安装: brew install python3"
  read -p "按回车键退出..."
  exit 1
fi

python3 -c "import wx" 2> /dev/null
if [ $? -ne 0 ]; then
  echo "⚠️  未检测到 wxPython，正在安装..."
  pip3 install wxPython
  if [ $? -ne 0 ]; then
    echo "❌ wxPython 安装失败，请手动执行: pip3 install wxPython"
    read -p "按回车键退出..."
    exit 1
  fi
fi

echo "🚀 启动表单填写助手..."
python3 form_helper.py
