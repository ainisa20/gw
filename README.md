# 表单填写助手 - 使用指南

## 快速开始

### macOS
```bash
./start.sh
```
或双击 `start_form_helper.command`

### Windows
双击 `start.bat`

### 依赖安装
```bash
pip3 install wxPython
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

## 配置

编辑 `form_helper.py` 顶部的配置项：
- `DIFY_API_BASE`：Dify API 地址
- `DIFY_API_KEY`：API 密钥
- `DEFAULT_URL`：右侧默认加载的网页地址

修改后重新启动应用即可生效。

## 技术栈

- **界面框架**：wxPython（跨平台）
- **WebView**：macOS 用 WKWebView，Windows 用 Edge WebView
- **AI 后端**：Dify API
- **本地服务**：Python HTTP 服务器（处理 CORS）

## 常见问题

### 截图失败
- 确保已授予屏幕录制权限
- 确保窗口未被遮挡

### Windows：缺少 DLL
安装 [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
