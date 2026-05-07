import time
import os
import json
import socket
import threading
import uuid
import subprocess
import base64
import tempfile
import platform
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request as UrllibRequest, urlopen
from urllib.error import URLError
from io import BytesIO
import wx
import wx.html2

IS_MACOS = platform.system() == "Darwin"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

# 默认配置
DEFAULT_CONFIG = {
    "difyApi": "http://47.239.24.30:8889",
    "difyToken": "app-jplqCEqKkX9dQPH2AobwAXOu",
    "formUrl": "https://amr.sz.gov.cn/xxgk/qt/ztlm/opcfwzq/index.html?f_link_type=f_linkinlinenote&flow_extra=eyJpbmxpbmVfZGlzcGxheV9wb3NpdGlvbiI6MCwiZG9jX3Bvc2l0aW9uIjowLCJkb2NfaWQiOiIxMDUyYmVmZGRkMTFiMjFiLTBiNWJhZjk4ZmYxZmFmMGEifQ%3D%3D"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                # 只保留非空的配置
                return {
                    "difyApi": cfg.get("difyApi") or DEFAULT_CONFIG["difyApi"],
                    "difyToken": cfg.get("difyToken") or DEFAULT_CONFIG["difyToken"],
                    "formUrl": cfg.get("formUrl") or DEFAULT_CONFIG["formUrl"]
                }
        except Exception as e:
            print(f"[config] load error: {e}")
    return DEFAULT_CONFIG.copy()

_config = load_config()
DIFY_BASE_URL = _config["difyApi"]
DIFY_TOKEN = _config["difyToken"]
FORM_URL = _config["formUrl"]
USER_ID = str(uuid.uuid4())


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ChatHandler(BaseHTTPRequestHandler):
    chat_html = ""

    def do_POST(self):
        if self.path.startswith("/api/"):
            api_path = self.path[5:]
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            print(f"[proxy] POST /{api_path} ({content_length} bytes)")
            self._proxy_request("POST", api_path, body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == "/" or self.path == "/chat":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(self.chat_html.encode("utf-8"))
        elif self.path.startswith("/chat."):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"")
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def _proxy_request(self, method, path, body):
        url = DIFY_BASE_URL + "/" + path
        print(f"[proxy] -> {method} {url}")
        print(f"[proxy] request Content-Type: {self.headers.get('Content-Type')}")
        
        req = UrllibRequest(url, data=body, method=method)
        req.add_header("Authorization", "Bearer " + DIFY_TOKEN)
        
        ct = self.headers.get("Content-Type")
        if ct:
            req.add_header("Content-Type", ct)
        else:
            req.add_header("Content-Type", "application/json")
        
        try:
            resp = urlopen(req, timeout=300)
            status = resp.status
            is_stream = "event-stream" in resp.headers.get("Content-Type", "")
            resp_headers = resp.getheaders()
            header_dict = {k.lower(): v for k, v in resp_headers}
            print(f"[proxy] <- {status} streaming={is_stream}")

            self.send_response(status)
            self._send_cors()
            if "content-type" in header_dict:
                self.send_header("Content-Type", header_dict["content-type"])
            self.end_headers()

            if is_stream:
                # SSE: forward chunks immediately
                while True:
                    chunk = resp.read(4096)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
                    print(f"[proxy] stream chunk: {len(chunk)} bytes")
                print(f"[proxy] stream complete")
            else:
                resp_body = resp.read()
                print(f"[proxy] <- body ({len(resp_body)} bytes)")
                if resp_body:
                    print(f"[proxy] response: {resp_body.decode()[:500]}")
                self.wfile.write(resp_body)
        except URLError as e:
            print(f"[proxy] ERROR: {e}")
            err_body = ""
            if hasattr(e, 'read'):
                try:
                    err_body = e.read().decode()
                    print(f"[proxy] error body: {err_body[:500]}")
                except Exception:
                    pass
            body_err = json.dumps({"error": str(e.reason), "detail": err_body}).encode()
            self.send_response(502)
            self._send_cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body_err)

    def _send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def log_message(self, format, *args):
        pass


def start_server(port):
    chat_path = os.path.join(SCRIPT_DIR, "chat.html")
    with open(chat_path, "r", encoding="utf-8") as f:
        ChatHandler.chat_html = f.read().replace("__DIFY_API_PROXY__", "")
    print(f"[server] Starting on http://127.0.0.1:{port}")
    server = HTTPServer(("127.0.0.1", port), ChatHandler)
    server.serve_forever()


class FormHelper(wx.Frame):
    def __init__(self):
        display = wx.ScreenDC()
        sw, sh = display.Size
        super().__init__(None, title="表单填写助手 - 左参考 · 右填写", size=(int(sw * 0.9), int(sh * 0.9)))

        self.Bind(wx.EVT_SIZE, self.on_frame_size)

        port = find_free_port()
        t = threading.Thread(target=start_server, args=(port,), daemon=True)
        t.start()
        time.sleep(0.3)
        chat_url = "http://127.0.0.1:" + str(port)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        url_bar = wx.BoxSizer(wx.HORIZONTAL)
        self.url_input = wx.TextCtrl(self, value=FORM_URL, style=wx.TE_PROCESS_ENTER)
        load_btn = wx.Button(self, label="加载")
        load_btn.Bind(wx.EVT_BUTTON, self.on_load)
        self.url_input.Bind(wx.EVT_TEXT_ENTER, lambda e: self.on_load())
        url_bar.Add(self.url_input, 1, wx.ALL | wx.EXPAND, 4)
        url_bar.Add(load_btn, 0, wx.ALL, 4)
        main_sizer.Add(url_bar, 0, wx.EXPAND)

        content_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.left = wx.html2.WebView.New(self)
        self.left.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.on_left_loaded)
        self.left.Bind(wx.html2.EVT_WEBVIEW_NAVIGATING, self.on_left_navigating)
        self.left.LoadURL(chat_url)

        resizer = wx.Panel(self, size=(6, -1))
        resizer.SetBackgroundColour("#0f3460")
        resizer.Bind(wx.EVT_LEFT_DOWN, self.on_resizer_down)
        resizer.Bind(wx.EVT_LEFT_UP, self.on_resizer_up)
        resizer.Bind(wx.EVT_MOTION, self.on_resizer_move)
        self.resizer = resizer

        self.right = wx.html2.WebView.New(self)
        self.right.LoadURL(FORM_URL)

        content_sizer.Add(self.left, proportion=36, flag=wx.EXPAND)
        content_sizer.Add(resizer, 0, flag=wx.EXPAND)
        content_sizer.Add(self.right, proportion=64, flag=wx.EXPAND)
        main_sizer.Add(content_sizer, 1, wx.EXPAND)

        self.SetSizer(main_sizer)
        self.Centre()

        self.resizing = False
        self.resizer_start_x = 0

    def on_frame_size(self, evt):
        self.Layout()
        evt.Skip()

    def on_load(self):
        url = self.url_input.GetValue().strip()
        if url and not url.startswith("http"):
            url = "http://" + url
        if url:
            self.right.LoadURL(url)

    def on_left_loaded(self, evt):
        inject_js = """
        (function() {
            window.triggerScreenshot = function() {
                var btn = document.getElementById('screenshot-btn');
                if(btn) {
                    btn.disabled = true;
                    btn.style.opacity = '0.5';
                    btn.style.cursor = 'not-allowed';
                }
                window.location.href = 'screenshot://trigger';
            };
        })();
        """
        self.left.RunScript(inject_js)
        evt.Skip()

    def on_left_navigating(self, evt):
        url = evt.GetURL()
        if url.startswith("screenshot://"):
            evt.Veto()
            if "trigger" in url:
                wx.CallAfter(self.on_screenshot_help, None)
        else:
            evt.Skip()

    def on_resizer_down(self, evt):
        self.resizing = True
        self.resizer.CaptureMouse()
        self.resizer_start_x = evt.GetX()

    def on_resizer_up(self, evt):
        if self.resizing:
            self.resizing = False
            if self.resizer.HasCapture():
                self.resizer.ReleaseMouse()

    def on_resizer_move(self, evt):
        if not self.resizing:
            return
        dx = evt.GetX() - self.resizer_start_x
        current_left = self.left.GetSize().width
        new_left = current_left + dx
        total = self.GetSize().width
        if 200 < new_left < total - 200:
            self.left.SetSize((new_left, -1))
            self.right.SetSize((total - new_left - 6, -1))
            self.Layout()
        evt.Skip()

    def on_screenshot_help(self, evt):
        try:
            img_data = self._capture_right_panel()
            print(f"[screenshot] captured {len(img_data)} bytes")
            file_id = self._upload_to_dify(img_data)
            print(f"[screenshot] uploaded, file_id={file_id}")
            data_url = "data:image/jpeg;base64," + base64.b64encode(img_data).decode()
            js = f"sendScreenshotHelp('{file_id}', '{data_url}')"
            print(f"[screenshot] injecting JS ({len(js)} chars)")
            self.left.RunScript(js)
        except Exception as e:
            print(f"[screenshot] ERROR: {e}")
            try:
                self.left.RunScript(
                    "addMessage('ai','<span style=\"color:#e94560\">截图失败: "
                    + str(e).replace("'", "\\'").replace('"', '\\"')
                    + "</span>', true)"
                )
            except Exception:
                pass
        finally:
            self.left.RunScript("""
                (function() {
                    var btn = document.getElementById('screenshot-btn');
                    if(btn) {
                        btn.disabled = false;
                        btn.style.opacity = '';
                        btn.style.cursor = '';
                    }
                })();
            """)

    def _capture_right_panel(self):
        rect = self.right.GetScreenRect()
        tmp = os.path.join(tempfile.gettempdir(), "form_helper_shot.jpg")
        if IS_MACOS:
            subprocess.run(
                ["screencapture", "-R",
                 f"{rect.x},{rect.y},{rect.width},{rect.height}", "-t", "jpg", tmp],
                check=True, capture_output=True, timeout=5
            )
        else:
            dc = wx.ScreenDC()
            bmp = wx.Bitmap(rect.width, rect.height)
            mem_dc = wx.MemoryDC(bmp)
            mem_dc.Blit(0, 0, rect.width, rect.height, dc, rect.x, rect.y)
            mem_dc.SelectObject(wx.NullBitmap)
            img = bmp.ConvertToImage()
            img.SetOption("quality", 70)
            img.SaveFile(tmp, wx.BITMAP_TYPE_JPEG)
        with open(tmp, "rb") as f:
            data = f.read()
        os.unlink(tmp)
        return data

    def _upload_to_dify(self, image_data):
        boundary = "----FormHelperBoundary" + uuid.uuid4().hex[:8]
        body = BytesIO()
        body.write(f"--{boundary}\r\n".encode())
        body.write(
            b'Content-Disposition: form-data; name="file"; filename="screenshot.jpg"\r\n'
            b"Content-Type: image/jpeg\r\n\r\n"
        )
        body.write(image_data)
        body.write(f"\r\n--{boundary}\r\n".encode())
        body.write(
            b'Content-Disposition: form-data; name="user"\r\n\r\n'
            + USER_ID.encode()
            + f"\r\n--{boundary}--\r\n".encode()
        )
        url = DIFY_BASE_URL + "/v1/files/upload"
        req = UrllibRequest(url, data=body.getvalue(), method="POST")
        req.add_header("Authorization", "Bearer " + DIFY_TOKEN)
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        resp = urlopen(req, timeout=15)
        result = json.loads(resp.read().decode())
        print(f"[upload] {result}")
        if not result.get("id"):
            raise Exception(result.get("message", "upload failed"))
        return result["id"]


if __name__ == "__main__":
    app = wx.App()
    frame = FormHelper()
    frame.Show()
    app.MainLoop()
