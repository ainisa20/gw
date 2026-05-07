# 表单填写助手 - 打包指南

## 打包成独立桌面应用

### macOS

```bash
# 1. 安装依赖
pip3 install pyinstaller wxPython

# 2. 运行打包脚本
./build_macos.sh
```

打包完成后，应用在 `dist/FormHelper.app`，双击即可运行。

### Windows

```cmd
# 1. 安装依赖
pip install pyinstaller wxPython

# 2. 运行打包脚本
build_windows.bat
```

打包完成后，应用在 `dist/FormHelper.exe`，双击即可运行。

## 应用图标

将图标文件放在 `assets/` 目录：
- macOS: `assets/icon.icns` (推荐 1024x1024)
- Windows: `assets/icon.ico` (推荐 256x256)

## macOS 权限说明

首次运行时，系统会请求**屏幕录制权限**，这是截图功能必需的，请点击「允许」。

## 常见问题

### Windows 打包后运行报错
确保安装了 Visual C++ Redistributable：https://aka.ms/vs/17/release/vc_redist.x64.exe

### macOS 打包后无法打开
```bash
# 移除隔离属性
xattr -cr dist/FormHelper.app
```
