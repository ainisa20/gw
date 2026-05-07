@echo off
REM Windows 打包脚本

echo 🔨 开始打包 Windows 应用...

REM 检查 PyInstaller
where pyinstaller >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 📦 安装 PyInstaller...
    pip install pyinstaller
)

REM 创建 assets 目录（如果不存在）
if not exist "assets" mkdir assets

REM 检查图标
if not exist "assets\icon.ico" (
    echo ⚠️  警告: assets\icon.ico 不存在，将使用默认图标
)

REM 清理之前的构建
echo 🧹 清理旧文件...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM 打包
echo 📦 打包中...
pyinstaller form_helper.spec --clean

REM 检查打包结果
if exist "dist\FormHelper.exe" (
    echo ✅ 打包成功!
    echo 📱 应用位置: dist\FormHelper.exe
    echo.
    echo 🚀 运行测试: dist\FormHelper.exe
) else (
    echo ❌ 打包失败
    exit /b 1
)
