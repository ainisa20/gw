# 政府网站导航优化说明

## 日志中的错误解析

### 1. NSURLErrorDomain error -999

```
[right] 加载错误: The operation couldn't be completed. (NSURLErrorDomain error -999.)
```

**这是什么？**
- macOS WKWebView的已知问题
- 错误名称：`NSURLErrorCancelled`
- 含义：请求被客户端取消

**为什么会发生？**
1. **页面快速跳转**：政府网站有很多自动跳转
2. **重复点击**：用户快速点击同一个链接
3. **反爬虫机制**：网站检测到自动化访问
4. **网络波动**：请求被中断

**影响程度：**
- ⚠️ 轻微：通常页面可以正常使用
- ✅ 不影响：截图求助功能正常
- ✅ 不影响：导航按钮功能正常

**如何处理？**
- 无需特别处理，这是macOS平台的特性
- 如果页面真的无法加载，点击"↻ 刷新"按钮
- 或者点击"🌐 浏览器"按钮在Safari中打开

---

### 2. PDF文件链接

```
[right] 导航到: https://amr.sz.gov.cn/attachment/1/1695/1695968/12691837.pdf
```

**问题：**
- WebView不支持内嵌显示PDF
- 页面会显示空白或加载失败

**解决方案：**
已添加自动检测，PDF文件会自动在系统浏览器中打开

---

## 新增功能

### 🌐 浏览器按钮

```
[◀ 后退][前进 ▶][↻ 刷新][⌂ 主页][🌐 浏览器][URL输入框........][加载]
```

**功能：**
- 在系统默认浏览器中打开当前页面
- macOS: Safari
- Windows: Edge 或 Chrome

**何时使用：**
1. **PDF文件** - 自动在浏览器中打开
2. **页面显示异常** - 切换到浏览器查看
3. **需要打印/保存** - 浏览器功能更完整
4. **WebView加载失败** - 作为备选方案

**使用方法：**
1. 在右侧加载任意页面
2. 点击"🌐 浏览器"按钮
3. 当前页面会在Safari/Edge中打开

---

## 智能特性

### 1. PDF自动检测

```python
if url.lower().endswith('.pdf'):
    webbrowser.open(url)  # 在浏览器中打开
```

**效果：**
- 点击PDF链接 → 自动在Safari中打开
- 无需手动操作
- 支持下载、打印、保存

### 2. 错误友好提示

```python
if "NSURLErrorDomain error -999" in error_str:
    print("[right] 提示: 这是macOS WebView的已知问题")
```

**效果：**
- 终端显示更友好的错误提示
- 不影响应用运行
- 用户知道这是正常现象

### 3. 浏览器快捷打开

**方法1：点击按钮**
- 点击"🌐 浏览器"按钮

**方法2：手动输入PDF URL**
- 在URL输入框粘贴PDF链接
- 点击"加载"
- 自动在浏览器中打开

---

## 使用场景示例

### 场景1：查看政府PDF文档

```
1. 政府网站有"操作指南.pdf"链接
2. 点击该链接
3. 系统自动在Safari中打开PDF
4. 可以打印、保存、查看
```

### 场景2：WebView加载失败

```
1. 页面一直加载，显示错误
2. 点击"🌐 浏览器"按钮
3. 在Safari中正常打开
4. 完成操作后回到应用
```

### 场景3：需要保存页面

```
1. 在右侧看到有用的表单页面
2. 想要保存为PDF
3. 点击"🌐 浏览器"按钮
4. 在Safari中"文件 → 导出为PDF"
```

---

## 技术细节

### PDF检测实现

```python
def on_right_navigating(self, evt):
    url = evt.GetURL()

    # 检测PDF文件
    if url.lower().endswith('.pdf'):
        print(f"[right] 检测到PDF文件: {url}")
        import webbrowser
        webbrowser.open(url)
        evt.Veto()  # 阻止WebView加载
        return

    evt.Skip()  # 正常页面继续加载
```

### 浏览器打开实现

```python
def on_open_external(self, event):
    current_url = self.right.GetCurrentURL()
    if current_url and current_url != "about:blank":
        import webbrowser
        webbrowser.open(current_url)
```

### 错误处理优化

```python
def on_right_error(self, evt):
    error_str = evt.GetString()

    # 友好提示
    if "NSURLErrorDomain error -999" in error_str:
        print("[right] 提示: macOS WebView已知问题")
    elif "blocked" in error_str.lower():
        print("[right] 提示: 可能被阻止，尝试'🌐 浏览器'按钮")
```

---

## 日志说明

### 正常日志
```
[right] 导航到: https://amr.sz.gov.cn/...
```
✅ 页面正在导航

### PDF日志
```
[right] 检测到PDF文件: https://.../guide.pdf
[external] PDF文件在浏览器中打开: https://.../guide.pdf
```
✅ PDF自动处理

### 错误日志
```
[right] 加载错误: NSURLErrorDomain error -999
[right] 提示: 这是macOS WebView的已知问题，通常不影响使用
```
✅ 友好提示

### 浏览器打开日志
```
[external] 在浏览器中打开: https://amr.sz.gov.cn/...
```
✅ 已在Safari中打开

---

## 已知限制

### 1. WebView功能限制
- 不支持PDF内嵌显示
- 某些现代Web特性可能不支持
- 部分网站可能阻止WebView访问

### 2. 解决方案
- 使用"🌐 浏览器"按钮作为补充
- 对于复杂页面，推荐在浏览器中操作

### 3. 平台差异
- **macOS**: 使用Safari打开
- **Windows**: 使用默认浏览器
- **Linux**: 使用xdg-open打开

---

## 最佳实践

### 用户侧

1. **遇到NSURLErrorDomain error -999**
   - 不用担心，这是正常的
   - 页面通常可以正常使用
   - 如果真不行，点击"刷新"或"浏览器"

2. **查看PDF文档**
   - 直接点击，会自动打开Safari
   - 或点击"🌐 浏览器"按钮

3. **页面显示异常**
   - 尝试"↻ 刷新"按钮
   - 或点击"🌐 浏览器"在Safari中查看

### 开发侧

1. **监控错误日志**
   - 查看是否有新的错误模式
   - 优化错误提示信息

2. **用户反馈**
   - 收集哪些页面容易出错
   - 考虑添加白名单机制

3. **未来优化**
   - 考虑使用更强大的WebView引擎
   - 添加自定义PDF渲染器
   - 支持更多文件类型（Word、Excel等）

---

## 更新日志

### v1.1 (当前版本)
- ✅ 添加"🌐 浏览器"按钮
- ✅ PDF自动检测并打开
- ✅ 错误日志友好提示
- ✅ NSURLErrorDomain error -999说明

### v1.0 (之前版本)
- ✅ 基础导航功能
- ✅ 后退/前进/刷新/主页
- ✅ URL自动同步

---

## 总结

**你现在看到的错误是正常的：**
- `NSURLErrorDomain error -999` → macOS WebView特性，不影响使用
- `PDF链接` → 自动在Safari中打开

**新增功能：**
- `🌐 浏览器`按钮 → 一键在浏览器中打开当前页面

**建议：**
- 优先使用WebView（速度快，支持截图求助）
- 遇到问题时使用"🌐 浏览器"按钮
- PDF文档会自动在Safari中打开

**重启应用后生效：**
```bash
./start.sh
```
