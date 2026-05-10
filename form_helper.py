import time
import os
import sys
import json
import socket
import threading
import uuid
import subprocess
import base64
import tempfile
import platform
import traceback
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request as UrllibRequest, urlopen
from urllib.error import URLError
from io import BytesIO
import wx
import wx.html2

import _resources

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8", mode="w"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("form_helper")

IS_MACOS = platform.system() == "Darwin"
SCRIPT_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

log.info(f"=== 表单填写助手启动 ===")
log.info(f"Python: {sys.version}")
log.info(f"Platform: {platform.platform()}")
log.info(f"SCRIPT_DIR: {SCRIPT_DIR}")
log.info(f"IS_MACOS: {IS_MACOS}")
log.info(f"wx version: {wx.__version__}")

_res_cache = {}


def load_resource_text(name):
    if name not in _res_cache:
        _res_cache[name] = _resources.get_text(name)
    return _res_cache[name]


def load_resource_bytes(name):
    if name not in _res_cache:
        _res_cache[name] = _resources.get_bytes(name)
    return _res_cache[name]


DEFAULT_CONFIG = {
    "difyApi": "http://47.239.24.30:8889",
    "difyToken": "app-I8L7ehbLS8iqCvFoa6w7nhhf",
    "formUrl": "https://amr.sz.gov.cn/xxgk/qt/ztlm/opcfwzq/index.html?f_link_type=f_linkinlinenote&flow_extra=eyJpbmxpbmVfZGlzcGxheV9wb3NpdGlvbiI6MCwiZG9jX3Bvc2l0aW9uIjowLCJkb2NfaWQiOiIxMDUyYmVmZWRkMTFiMjFiLTBiNWJhZjk4ZmYxZmFmMGEifQ%3D%3D"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return {
                    "difyApi": cfg.get("difyApi") or DEFAULT_CONFIG["difyApi"],
                    "difyToken": cfg.get("difyToken") or DEFAULT_CONFIG["difyToken"],
                    "formUrl": cfg.get("formUrl") or DEFAULT_CONFIG["formUrl"]
                }
        except Exception as e:
            log.error(f"[config] load error: {e}")
    return DEFAULT_CONFIG.copy()

_config = load_config()
DIFY_BASE_URL = _config["difyApi"]
DIFY_TOKEN = _config["difyToken"]
FORM_URL = _config["formUrl"]
USER_ID = str(uuid.uuid4())

log.info(f"DIFY_BASE_URL: {DIFY_BASE_URL}")
log.info(f"FORM_URL: {FORM_URL[:80]}...")

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ChatHandler(BaseHTTPRequestHandler):
    chat_html = ""

    def do_POST(self):
        if self.path == "/api/lookup-fragment":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            self._handle_lookup_fragment(body)
        elif self.path.startswith("/api/"):
            api_path = self.path[5:]
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            log.info(f"[proxy] POST /{api_path} ({content_length} bytes)")
            self._proxy_request("POST", api_path, body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        log.info(f"[http] GET {self.path}")
        if self.path == "/" or self.path == "/chat":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(self.chat_html.encode("utf-8"))
            log.info(f"[http] served chat.html ({len(self.chat_html)} bytes)")
        elif self.path == "/api/catalog":
            self._handle_get_catalog()
        elif self.path.startswith("/ref-image?path="):
            self._serve_ref_image()
        elif self.path.startswith("/page"):
            self._serve_page_file()
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
        log.info(f"[proxy] -> {method} {url}")
        ct = self.headers.get("Content-Type") or ""

        if "chat-messages" in path and "application/json" in ct:
            try:
                data = json.loads(body.decode('utf-8'))
                log.info(f"[proxy] query: {data.get('query', '')[:500]}")
                files = data.get('files', [])
                if files:
                    log.info(f"[proxy] files: {json.dumps(files)}")
                if data.get('conversation_id'):
                    log.info(f"[proxy] conversation_id: {data['conversation_id']}")
            except Exception:
                pass
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
            log.info(f"[proxy] <- {status} streaming={is_stream}")

            self.send_response(status)
            self._send_cors()
            if "content-type" in header_dict:
                self.send_header("Content-Type", header_dict["content-type"])
            self.end_headers()

            if is_stream:
                while True:
                    chunk = resp.read(4096)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
                log.info(f"[proxy] stream complete")
            else:
                resp_body = resp.read()
                log.info(f"[proxy] <- body ({len(resp_body)} bytes)")
                self.wfile.write(resp_body)
        except URLError as e:
            log.error(f"[proxy] ERROR: {e}")
            err_body = ""
            if hasattr(e, 'read'):
                try:
                    err_body = e.read().decode()
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

    def _handle_get_catalog(self):
        try:
            from fragment_matcher import get_matcher
            matcher = get_matcher()
            catalog = matcher.build_catalog_text()
            log.info(f"[catalog] 返回 {len(catalog)} chars")

            self.send_response(200)
            self._send_cors()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(catalog.encode('utf-8'))
        except Exception as e:
            log.error(f"[catalog] ERROR: {e}")
            traceback.print_exc()
            self.send_response(500)
            self._send_cors()
            self.end_headers()

    def _handle_lookup_fragment(self, body):
        try:
            data = json.loads(body.decode('utf-8'))
            fragment_id = data.get('id')
            fragment_title = data.get('title')
            log.info(f"[lookup] id={fragment_id}, title={fragment_title}")

            from fragment_matcher import get_matcher
            matcher = get_matcher()

            fragment = None
            if fragment_id:
                fragment = matcher.find_by_id(int(fragment_id))
            if not fragment and fragment_title:
                fragment = matcher.find_by_title(fragment_title)

            if fragment:
                log.info(f"[lookup] found: ID={fragment['id']}")
                self.send_response(200)
                self._send_cors()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(
                    {"success": True, "fragment": fragment},
                    ensure_ascii=False
                ).encode('utf-8'))
            else:
                log.info(f"[lookup] not found")
                self.send_response(200)
                self._send_cors()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(
                    {"success": False, "error": "未找到匹配片段"},
                    ensure_ascii=False
                ).encode('utf-8'))
        except Exception as e:
            log.error(f"[lookup] ERROR: {e}")
            traceback.print_exc()
            self.send_response(500)
            self._send_cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(
                {"success": False, "error": str(e)},
                ensure_ascii=False
            ).encode('utf-8'))

    def _serve_ref_image(self):
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        rel_path = params.get('path', [''])[0]

        if not rel_path or '..' in rel_path:
            self.send_response(400)
            self.end_headers()
            return

        data = load_resource_bytes(rel_path)
        if data is None:
            self.send_response(404)
            self.end_headers()
            return

        ct = "image/jpeg"
        if rel_path.endswith(".png"):
            ct = "image/png"
        elif rel_path.endswith(".gif"):
            ct = "image/gif"
        elif rel_path.endswith(".webp"):
            ct = "image/webp"

        self.send_response(200)
        self._send_cors()
        self.send_header("Content-Type", ct)
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(data)

    def _serve_page_file(self):
        from urllib.parse import urlparse, unquote
        parsed = urlparse(self.path)
        rel_path = unquote(parsed.path).lstrip("/")

        if '..' in rel_path:
            self.send_response(400)
            self.end_headers()
            return

        data = load_resource_bytes(rel_path)
        if data is None:
            self.send_response(404)
            self.end_headers()
            return

        ct = "application/octet-stream"
        if rel_path.endswith(".html"):
            ct = "text/html; charset=utf-8"
        elif rel_path.endswith(".css"):
            ct = "text/css; charset=utf-8"
        elif rel_path.endswith(".js"):
            ct = "application/javascript; charset=utf-8"
        elif rel_path.endswith(".jpg") or rel_path.endswith(".jpeg"):
            ct = "image/jpeg"
        elif rel_path.endswith(".png"):
            ct = "image/png"
        elif rel_path.endswith(".gif"):
            ct = "image/gif"
        elif rel_path.endswith(".webp"):
            ct = "image/webp"
        elif rel_path.endswith(".json"):
            ct = "application/json; charset=utf-8"
        elif rel_path.endswith(".md"):
            ct = "text/plain; charset=utf-8"

        self.send_response(200)
        self._send_cors()
        self.send_header("Content-Type", ct)
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass


def init_fragment_matcher():
    try:
        json_data = load_resource_text("fragments_structured.json")
        if not json_data:
            log.error("[init] fragments_structured.json decrypt failed")
            return

        import fragment_matcher
        fragments = json.loads(json_data)
        matcher = fragment_matcher.FragmentMatcher.__new__(fragment_matcher.FragmentMatcher)
        matcher.fragments = fragments
        matcher.title_index = {}
        for frag in fragments:
            matcher.title_index[frag['title']] = frag
        fragment_matcher._matcher_instance = matcher

        log.info(f"[init] fragment_matcher loaded ({len(fragments)} fragments)")
    except Exception as e:
        log.error(f"[init] fragment_matcher load error: {e}")
        traceback.print_exc()


def start_server(port):
    try:
        chat_html = load_resource_text("chat.html")
        ChatHandler.chat_html = chat_html.replace("__DIFY_API_PROXY__", "")
        log.info(f"[server] chat.html loaded ({len(ChatHandler.chat_html)} bytes)")
    except Exception as e:
        log.error(f"[server] Failed to load chat.html: {e}")
        ChatHandler.chat_html = f"<html><body><h1>Error: {e}</h1></body></html>"

    log.info(f"[server] Starting HTTP on http://127.0.0.1:{port}")
    server = HTTPServer(("127.0.0.1", port), ChatHandler)
    server.serve_forever()


class FormHelper(wx.Frame):
    def __init__(self):
        display = wx.ScreenDC()
        sw, sh = display.Size
        super().__init__(None, title="表单填写助手 - 左参考 · 右填写", size=(int(sw * 0.9), int(sh * 0.9)))

        self.Bind(wx.EVT_SIZE, self.on_frame_size)

        port = find_free_port()
        log.info(f"[init] HTTP port: {port}")
        t = threading.Thread(target=start_server, args=(port,), daemon=True)
        t.start()
        time.sleep(0.5)

        chat_url = "http://127.0.0.1:" + str(port)
        log.info(f"[init] chat_url: {chat_url}")

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        nav_bar = wx.BoxSizer(wx.HORIZONTAL)
        btn_back = wx.Button(self, label="←", size=(36, -1))
        btn_forward = wx.Button(self, label="→", size=(36, -1))
        btn_refresh = wx.Button(self, label="⟳", size=(36, -1))
        btn_home = wx.Button(self, label="🏠", size=(36, -1))
        btn_back.Bind(wx.EVT_BUTTON, self.on_back)
        btn_forward.Bind(wx.EVT_BUTTON, self.on_forward)
        btn_refresh.Bind(wx.EVT_BUTTON, self.on_refresh)
        btn_home.Bind(wx.EVT_BUTTON, self.on_home)
        self.url_input = wx.TextCtrl(self, value=FORM_URL, style=wx.TE_PROCESS_ENTER)
        load_btn = wx.Button(self, label="加载")
        load_btn.Bind(wx.EVT_BUTTON, self.on_load)
        self.url_input.Bind(wx.EVT_TEXT_ENTER, lambda e: self.on_load())
        nav_bar.Add(btn_back, 0, wx.ALL, 2)
        nav_bar.Add(btn_forward, 0, wx.ALL, 2)
        nav_bar.Add(btn_refresh, 0, wx.ALL, 2)
        nav_bar.Add(btn_home, 0, wx.ALL, 2)
        nav_bar.Add(self.url_input, 1, wx.ALL | wx.EXPAND, 4)
        nav_bar.Add(load_btn, 0, wx.ALL, 4)
        main_sizer.Add(nav_bar, 0, wx.EXPAND)

        content_sizer = wx.BoxSizer(wx.HORIZONTAL)

        backend = wx.html2.WebViewBackendEdge
        log.info(f"[init] Creating left WebView with backend={backend}")
        try:
            self.left = wx.html2.WebView.New(self, backend=backend)
            log.info(f"[init] Left WebView created OK")
        except Exception as e:
            log.error(f"[init] Edge backend failed: {e}, falling back to default")
            self.left = wx.html2.WebView.New(self)

        self.left.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.on_left_loaded)
        self.left.Bind(wx.html2.EVT_WEBVIEW_ERROR, self.on_left_error)
        self.left.Bind(wx.html2.EVT_WEBVIEW_NAVIGATING, self.on_left_navigating)
        log.info(f"[init] Loading chat_url: {chat_url}")
        self.left.LoadURL(chat_url)

        resizer = wx.Panel(self, size=(6, -1))
        resizer.SetBackgroundColour("#0f3460")
        resizer.Bind(wx.EVT_LEFT_DOWN, self.on_resizer_down)
        resizer.Bind(wx.EVT_LEFT_UP, self.on_resizer_up)
        resizer.Bind(wx.EVT_MOTION, self.on_resizer_move)
        self.resizer = resizer

        log.info(f"[init] Creating right WebView")
        try:
            self.right = wx.html2.WebView.New(self, backend=backend)
            log.info(f"[init] Right WebView created OK")
        except Exception as e:
            log.error(f"[init] Edge backend failed: {e}, falling back to default")
            self.right = wx.html2.WebView.New(self)

        self.right.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.on_right_loaded)
        self.right.Bind(wx.html2.EVT_WEBVIEW_ERROR, self.on_right_error)
        log.info(f"[init] Loading FORM_URL")
        self.right.LoadURL(FORM_URL)

        content_sizer.Add(self.left, proportion=36, flag=wx.EXPAND)
        content_sizer.Add(resizer, 0, flag=wx.EXPAND)
        content_sizer.Add(self.right, proportion=64, flag=wx.EXPAND)
        main_sizer.Add(content_sizer, 1, wx.EXPAND)

        self.SetSizer(main_sizer)
        self.Centre()

        self.resizing = False
        self.resizer_start_x = 0
        log.info(f"[init] Frame init complete")

    def on_frame_size(self, evt):
        self.Layout()
        evt.Skip()

    def on_left_loaded(self, evt):
        url = evt.GetURL()
        log.info(f"[left] LOADED: {url}")
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
        try:
            self.left.RunScript(inject_js)
            log.info(f"[left] RunScript inject OK")
        except Exception as e:
            log.warning(f"[left] RunScript inject failed: {e}")
        evt.Skip()

    def on_left_error(self, evt):
        url = evt.GetURL() if hasattr(evt, 'GetURL') else 'unknown'
        log.error(f"[left] WEBVIEW_ERROR on: {url}")

    def on_right_loaded(self, evt):
        url = evt.GetURL()
        log.info(f"[right] LOADED: {url}")

    def on_right_error(self, evt):
        url = evt.GetURL() if hasattr(evt, 'GetURL') else 'unknown'
        log.error(f"[right] WEBVIEW_ERROR on: {url}")

    def on_left_navigating(self, evt):
        url = evt.GetURL()
        log.info(f"[left] NAVIGATING: {url}")
        if url.startswith("screenshot://"):
            evt.Veto()
            if "trigger" in url:
                wx.CallAfter(self.on_screenshot_help, None)
        else:
            evt.Skip()

    def on_load(self):
        url = self.url_input.GetValue().strip()
        if url and not url.startswith("http"):
            url = "http://" + url
        if url:
            self.right.LoadURL(url)

    def on_back(self, evt):
        self.right.GoBack()

    def on_forward(self, evt):
        self.right.GoForward()

    def on_refresh(self, evt):
        self.right.Reload()

    def on_home(self, evt):
        self.url_input.SetValue(FORM_URL)
        self.right.LoadURL(FORM_URL)

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
            log.info(f"[screenshot] captured {len(img_data)} bytes")
            file_id = self._upload_to_dify(img_data)
            log.info(f"[screenshot] uploaded, file_id={file_id}")
            data_url = "data:image/jpeg;base64," + base64.b64encode(img_data).decode()
            js = f"sendScreenshotHelp('{file_id}', '{data_url}')"
            log.info(f"[screenshot] injecting JS ({len(js)} chars)")
            self.left.RunScript(js)
        except Exception as e:
            log.error(f"[screenshot] ERROR: {e}")
            try:
                self.left.RunScript(
                    "addMessage('ai','<span style=\"color:#e94560\">截图失败: "
                    + str(e).replace("'", "\\'").replace('"', '\\"')
                    + "</span>', true)"
                )
            except Exception:
                pass
        finally:
            try:
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
            except Exception:
                pass

    def _capture_right_panel(self):
        tmp = os.path.join(tempfile.gettempdir(), "form_helper_shot.jpg")
        if IS_MACOS:
            rect = self.right.GetScreenRect()
            subprocess.run(
                ["screencapture", "-R",
                 f"{rect.x},{rect.y},{rect.width},{rect.height}", "-t", "jpg", tmp],
                check=True, capture_output=True, timeout=5
            )
        else:
            import ctypes
            import ctypes.wintypes
            hwnd = int(self.right.GetHandle())
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            pw = rect.right - rect.left
            ph = rect.bottom - rect.top
            log.info(f"[screenshot] hwnd={hwnd} rect=({rect.left},{rect.top},{pw},{ph})")
            screen_dc = ctypes.windll.user32.GetDC(0)
            mem_dc = ctypes.windll.gdi32.CreateCompatibleDC(screen_dc)
            hbmp = ctypes.windll.gdi32.CreateCompatibleBitmap(screen_dc, pw, ph)
            ctypes.windll.gdi32.SelectObject(mem_dc, hbmp)
            ret = ctypes.windll.user32.PrintWindow(hwnd, mem_dc, 2)
            log.info(f"[screenshot] PrintWindow ret={ret}")
            ctypes.windll.gdi32.DeleteDC(mem_dc)
            ctypes.windll.user32.ReleaseDC(0, screen_dc)
            bmp = wx.Bitmap()
            bmp.SetHandle(hbmp)
            bmp.SetSize(wx.Size(pw, ph))
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
        log.info(f"[upload] {result}")
        if not result.get("id"):
            raise Exception(result.get("message", "upload failed"))
        return result["id"]


if __name__ == "__main__":
    try:
        log.info("Creating wx.App")
        app = wx.App()
        log.info("Initializing encrypted resources")
        init_fragment_matcher()
        log.info("Creating FormHelper frame")
        frame = FormHelper()
        frame.Show()
        log.info("Entering MainLoop")
        app.MainLoop()
    except Exception as e:
        log.critical(f"Fatal error: {e}")
        traceback.print_exc()
