#!/bin/bash
# 启动脚本 - macOS

cd "$(dirname "$0")"
echo "🚀 启动表单填写助手..."
python3 form_helper.py &
