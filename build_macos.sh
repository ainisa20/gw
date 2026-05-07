#!/bin/bash
# macOS 打包脚本

set -e

echo "🔨 开始打包 macOS 应用..."

# 检查 PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "📦 安装 PyInstaller..."
    pip3 install pyinstaller
fi

# 创建 assets 目录（如果不存在）
mkdir -p assets

# 检查图标
if [ ! -f "assets/icon.icns" ]; then
    echo "⚠️  警告: assets/icon.icns 不存在，将使用默认图标"
    # 可以在这里添加自动生成图标的逻辑
fi

# 清理之前的构建
echo "🧹 清理旧文件..."
rm -rf build dist

# 打包
echo "📦 打包中..."
pyinstaller form_helper.spec --clean

# 检查打包结果
if [ -d "dist/FormHelper.app" ]; then
    echo "✅ 打包成功!"
    echo "📱 应用位置: dist/FormHelper.app"
    echo ""
    echo "🚀 运行测试: open dist/FormHelper.app"
else
    echo "❌ 打包失败"
    exit 1
fi
