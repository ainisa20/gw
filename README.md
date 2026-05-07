# 表单填写助手 - 使用指南

## 快速开始

### 方式一：运行打包好的应用（推荐）

**macOS:**
```bash
open dist/FormHelper.app
```

**Windows:**
```cmd
dist\FormHelper.exe
```

### 方式二：源码运行

```bash
python3 form_helper.py
```

## 功能说明

### 左侧：AI 助手
- **文字对话**：输入框输入问题，点击发送
- **图片上传**：点击 📎 按钮上传截图
- **语音输入**：点击 🎤 按钮录音（自动转文字）
- **截图求助**：点击右侧悬浮的「📸 截图求助」按钮

### 右侧：表单页面
- 显示政府或各类表单网站
- 可手动修改 URL

## 截图求助功能

1. 右侧加载表单页面
2. 点击左侧右侧的红色悬浮按钮「📸 截图求助」
3. 系统自动截取右侧页面并发送给 AI
4. AI 分析截图，返回填写建议

**注意**：首次使用会请求屏幕录制权限，需要允许。

## 打包指南

### macOS
```bash
./build_macos.sh
```
生成：`dist/FormHelper.app`

### Windows
```cmd
build_windows.bat
```
生成：`dist\FormHelper.exe`

## 自定义图标

将图标文件放入 `assets/` 目录：
- macOS: `icon.icns`
- Windows: `icon.ico`

详细说明见 `assets/README.md`

## 技术栈

- **界面框架**：wxPython（跨平台）
- **WebView**：macOS 用 WKWebView，Windows 用 Edge WebView
- **AI 后端**：Dify API
- **本地服务**：Python HTTP 服务器（处理 CORS）

## 常见问题

### macOS：应用无法打开
```bash
xattr -cr dist/FormHelper.app
```

### Windows：缺少 DLL
安装 [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### 截图失败
- 确保已授予屏幕录制权限
- 确保窗口未被遮挡
