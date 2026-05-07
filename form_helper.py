import time
import os
import json
import socket
import threading
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request as UrllibRequest, urlopen
from urllib.error import URLError
import wx
import wx.html2

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DIFY_BASE_URL = "http://47.239.24.30:8889"
DIFY_TOKEN = "app-jplqCEqKkX9dQPH2AobwAXOu"
USER_ID = str(uuid.uuid4())
FORM_URL = "https://amr.sz.gov.cn/xxgk/qt/ztlm/opcfwzq/index.html?f_link_type=f_linkinlinenote&flow_extra=eyJpbmxpbmVfZGlzcGxheV9wb3NpdGlvbiI6MCwiZG9jX3Bvc2l0aW9uIjowLCJkb2NfaWQiOiIxMDUyYmVmZGRkMTFiMjFiLTBiNWJhZjk4ZmYxZmFmMGEifQ%3D%3D"


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ChatHandler(BaseHTTPRequestHandler):
    chat_html = ""

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

    def do_POST(self):
        if self.path.startswith("/api/"):
            api_path = self.path[5:]
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            print(f"[proxy] POST /{api_path} ({content_length} bytes)")
            if "audio" in api_path:
                dbg_path = os.path.join(SCRIPT_DIR, "debug_audio.bin")
                with open(dbg_path, "wb") as f:
                    f.write(body)
                print(f"[proxy] saved audio to {dbg_path}")
            self._proxy_request("POST", api_path, body)
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
        print(f"[proxy] headers: Content-Type={self.headers.get('Content-Type')}")
        req = UrllibRequest(url, data=body, method=method)
        req.add_header("Authorization", "Bearer " + DIFY_TOKEN)
        ct = self.headers.get("Content-Type")
        if ct:
            req.add_header("Content-Type", ct)
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


if __name__ == "__main__":
    app = wx.App()
    frame = FormHelper()
    frame.Show()
    app.MainLoop()
