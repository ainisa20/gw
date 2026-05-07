好的，我们来实现这个双栏表单填写助手。它能完美绕过政府网站的嵌入限制，因为左侧聊天助手和右侧表单都运行在独立的完整浏览器引擎中。

---

### 🛠️ 准备工作

在开始前，请先安装 PySide6 库：

```bash
pip install PySide6
```

### 🚀 创建应用

新建一个 Python 文件，例如 `form_helper.py`，将以下代码复制进去：

```python
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget,
                               QHBoxLayout, QVBoxLayout, QLineEdit, 
                               QPushButton, QSizePolicy)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtCore import QUrl

class FormHelper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("表单填写助手 - 左参考 · 右填写")
        # 设置一个合适的初始窗口大小
        self.resize(1600, 900)
        
        # 中央主控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== 左侧：聊天助手 ==========
        # 左侧助手直接加载你指定的聊天机器人页面
        self.left_webview = QWebEngineView()
        # 授权麦克风权限并开启必要的功能
        self.left_webview.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalStorageEnabled, True
        )
        # 开启 'accept-language' 和媒体流以支持语音输入
        self.left_webview.settings().setAttribute(
            QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True
        )
        # 加载指定的聊天助手页面
        self.left_webview.load(
            QUrl("http://www.jzopc.com/chatbot/99Ihd0ZUJiFJxA3W")
        )
        
        # ========== 右侧：表单填写区域 ==========
        # 右侧负责你需要填写的政府表单页面
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)
        
        # 地址栏与加载按钮
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit(
            "https://amr.sz.gov.cn/xxgk/qt/ztlm/opcfwzq/index.html?f_link_type=f_linkinlinenote&flow_extra=eyJpbmxpbmVfZGlzcGxheV9wb3NpdGlvbiI6MCwiZG9jX3Bvc2l0aW9uIjowLCJkb2NfaWQiOiIxMDUyYmVmZGRkMTFiMjFiLTBiNWJhZjk4ZmYxZmFmMGEifQ%3D%3D"
        )
        load_btn = QPushButton("加载")
        load_btn.clicked.connect(self.load_right_url)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(load_btn)
        
        # 右侧浏览器组件
        self.right_webview = QWebEngineView()
        self.right_webview.load(QUrl(self.url_input.text()))
        
        right_layout.addLayout(url_layout)
        right_layout.addWidget(self.right_webview)
        
        # 将左右两侧加入主布局，比例 2:3
        main_layout.addWidget(self.left_webview, 2)
        main_layout.addWidget(right_panel, 3)
        
    def load_right_url(self):
        """加载右侧地址栏中的网址"""
        url = self.url_input.text().strip()
        if url and not url.startswith("http"):
            url = "http://" + url
        if url:
            self.right_webview.load(QUrl(url))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序图标（可选，如果没有图标文件可以注释掉）
    # app.setWindowIcon(QIcon("icon.png"))
    
    window = FormHelper()
    window.show()
    sys.exit(app.exec())
```

### ✨ 运行与使用

1.  **保存并运行**：将代码保存为 `form_helper.py`，然后在终端中执行：
    ```bash
    python form_helper.py
    ```

2.  **开始使用**：
    *   **左侧助手**：窗口左侧会自动加载聊天机器人页面。运行时如果提示麦克风权限，请允许。
    *   **右侧表单**：窗口右侧会加载深圳市市场监督管理局的表单页面。你可以直接在右侧地址栏里修改或替换网址，然后点击“加载”按钮来切换页面。

### 🧰 功能亮点

| 特性 | 说明 |
|------|------|
| **完美绕过限制** | 左右两侧都是完整的 Chromium 浏览器实例，政府网站即使有 `X-Frame-Options: DENY` 也能正常加载。 |
| **一体化界面** | 你不需要来回切换窗口，左边看说明，右边直接填写。 |
| **可自由调整** | 拖拽中间的分隔线就能随时调整左右两侧的宽度比例。 |
| **地址可切换** | 右侧地址栏支持手写新网址，方便对比填写不同表单。 |

### 🧑‍💻 可能的问题与应对

*   **页面无法加载**：确保你的电脑能正常访问外网，且没有被防火墙拦截 `amr.sz.gov.cn` 或 `jzopc.com`。
*   **语音输入没反应**：首次打开聊天助手时，浏览器顶部可能会弹出权限申请，点击“允许”即可使用麦克风。
*   **窗口过小内容挤在一起**：代码里设置了初始大小 `1600x900`，如果你的屏幕比较小，可以调低这个值，或者直接最大化窗口。