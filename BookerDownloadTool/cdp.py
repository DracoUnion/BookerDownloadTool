import requests
import itertools
import json
import os
import shutil
import subprocess as subp
import tempfile
import threading
import time
import traceback
from contextlib import contextmanager
import websocket


class CdpError(RuntimeError):
    pass

class CdpConnection:
    """一个同步的 CDP WebSocket 连接（请求/响应按 id 配对）。"""

    def __init__(self, ws, timeout_ms=60_000):
        self.ws = ws
        self.timeout_ms = timeout_ms
        self._id_gen = itertools.count(1)
        self._lock = threading.Lock()

    @classmethod
    def connect(cls, url, timeout_ms=30_000):
        # timeout 同时作用于握手与 recv：recv 每 N 秒返回一次，便于外层按
        # 自己的 deadline 判断超时，而不是被一条永远等不到的消息卡死。
        ws = websocket.create_connection(url, timeout=15, origin=None)
        return cls(ws, timeout_ms=timeout_ms)

    def send(self, method, params=None, session_id=None, timeout_ms=None):
        msg_id = next(self._id_gen)
        payload = {'id': msg_id, 'method': method}
        if params is not None:
            payload['params'] = params
        if session_id:
            payload['sessionId'] = session_id
        timeout_ms = timeout_ms or self.timeout_ms
        with self._lock:
            self.ws.send(json.dumps(payload))
        deadline = time.time() + timeout_ms / 1000.0
        while True:
            if time.time() > deadline:
                raise TimeoutError(f'CDP 超时：{method}')
            try:
                data = json.loads(self.ws.recv())
            except KeyboardInterrupt:
                raise
            except websocket.WebSocketTimeoutException:
                continue  # recv 定时返回，检查 deadline
            except websocket.WebSocketConnectionClosedException as e:
                raise CdpError(f'CDP 连接已关闭：{e}')
            if data.get('id') == msg_id:
                if data.get('error'):
                    raise CdpError(
                        f'{method}: {data["error"].get("message", data["error"])}')
                return data.get('result', {})
            # id 不匹配的是事件通知，这里不订阅事件，直接丢弃

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


class CdpPage:
    """绑定到单个 Chrome tab 的 CDP 会话，等价于原 annas.py 的 page 对象。"""

    def __init__(self, cdp: CdpConnection, session_id, target_id, proc=None, profile=None):
        self.cdp = cdp
        self.session_id = session_id
        self.target_id = target_id
        self.proc = proc          # Chrome 主进程（用于清理）
        self.profile = profile    # 临时 user-data-dir（用于清理）

    def send(self, method, params=None, timeout_ms=None):
        return self.cdp.send(method, params,
                             session_id=self.session_id, timeout_ms=timeout_ms)

    # ── 页面操作 ──

    def evaluate(self, expression, timeout_ms=15_000):
        try:
            res = self.send('Runtime.evaluate', {
                'expression': expression,
                'returnByValue': True,
            }, timeout_ms=timeout_ms)
            if res.get('exceptionDetails'):
                raise CdpError(f'Runtime.evaluate 异常：'
                            f'{json.dumps(res["exceptionDetails"], ensure_ascii=False)[:500]}')
            return res.get('result', {}).get('value')
        except:
            traceback.print_exc()
            return None

    def html(self) -> str:
        """等价于 page.content()。"""
        return self.evaluate('document.documentElement.outerHTML')

    def goto(self, url, timeout_ms=60_000):
        self.send('Page.navigate', {'url': url})
        self.wait_ready(timeout_ms)

    def reload(self, timeout_ms=60_000):
        try:
            self.send('Page.reload', {'ignoreCache': True})
            self.wait_ready(timeout_ms)
        except CdpError:
            # 页面导航中/上下文销毁时 reload 会失败，交给后续 goto 兜底
            pass

    def wait_ready(self, timeout_ms=60_000):
        """等价于 wait_for_load_state('domcontentloaded')。"""
        deadline = time.time() + timeout_ms / 1000.0
        while time.time() < deadline:
            rs = self.evaluate('document.readyState')
            if rs in ('interactive', 'complete'):
                return True
            time.sleep(0.2)
        return False

    def wait_for_iframe_selector(self, iframe_sel, el_sel, timeout_ms=50_000):
        """轮询直到元素出现（如验证通过后页面关键选择器），等价于
        page.wait_for_selector(selector, timeout=50000)。"""
        expr = f'''
            (() => {{
            const iframe = document.querySelector('{iframe_sel}');
            if (!iframe) return false;
            const innerDoc = iframe.contentDocument || iframe.contentWindow.document;
            return !!innerDoc.querySelector('{el_sel}')
            }})()
        '''
        deadline = time.time() + timeout_ms / 1000.0
        while time.time() < deadline:
            if self.evaluate(expr):
                return True
            time.sleep(0.5)
        raise TimeoutError(f'等待选择器超时（{timeout_ms}ms）：{el_sel}')

    def wait_for_selector(self, selector, timeout_ms=50_000):
        """轮询直到元素出现（如验证通过后页面关键选择器），等价于
        page.wait_for_selector(selector, timeout=50000)。"""
        expr = f'!!document.querySelector({json.dumps(selector)})'
        deadline = time.time() + timeout_ms / 1000.0
        while time.time() < deadline:
            if self.evaluate(expr):
                return True
            time.sleep(0.5)
        raise TimeoutError(f'等待选择器超时（{timeout_ms}ms）：{selector}')

def find_chrome_executable():
    override = os.environ.get('DL_ANNAS_CHROME', '').strip()
    if override and os.path.exists(override):
        return override
    candidates = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    for cmd in ('chrome', 'chromium', 'msedge'):
        p = shutil.which(cmd)
        if p:
            return p
    raise FileNotFoundError('未找到 Chrome/Edge，请设置 DL_ANNAS_CHROME 环境变量')


def _wait_for_port_file(profile, proc, timeout_ms):
    """--remote-debugging-port=0 时 Chrome 会把实际端口写入
    <user-data-dir>/DevToolsActivePort，读取第一行即为端口号。"""
    pf = os.path.join(profile, 'DevToolsActivePort')
    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        if proc.poll() is not None:
            raise CdpError(f'Chrome 意外退出，code={proc.returncode}')
        if os.path.exists(pf):
            try:
                with open(pf) as f:
                    return int(f.read().splitlines()[0].strip())
            except (ValueError, IndexError):
                pass
        time.sleep(0.15)
    raise TimeoutError(f'Chrome 调试端口未就绪（{timeout_ms}ms）')


def _wait_for_ws_url(port, timeout_ms):
    url = f'http://127.0.0.1:{port}/json/version'
    deadline = time.time() + timeout_ms / 1000.0
    last_err = None
    while time.time() < deadline:
        try:
            # 强制不走代理，localhost 无需代理
            r = requests.get(url, timeout=2, proxies={'http': None, 'https': None})
            data = r.json()
            if data.get('webSocketDebuggerUrl'):
                return data['webSocketDebuggerUrl']
        except Exception as e:
            last_err = e
        time.sleep(0.15)
    raise TimeoutError(f'Chrome CDP 端点未就绪：{last_err}')


def _kill_chrome_tree(proc):
    if proc is None or proc.poll() is not None:
        return
    try:
        if os.name == 'nt':
            subp.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                     stdout=subp.DEVNULL, stderr=subp.DEVNULL)
        else:
            proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _launch_chrome(headless, timeout_ms=60_000):
    chrome = find_chrome_executable()
    profile = tempfile.mkdtemp(prefix='dl-annas-cdp-')
    args = [
        chrome,
        '--remote-debugging-port=0',          # 自动分配空闲端口，多实例不冲突
        f'--user-data-dir={profile}',          # 独立 profile，避免与已开的 Chrome 冲突
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--window-size=1920,1080',
    ]
    if headless:
        args += ['--headless=new', '--disable-gpu']
    proc = subp.Popen(args, stdout=subp.DEVNULL, stderr=subp.DEVNULL)
    try:
        port = _wait_for_port_file(profile, proc, timeout_ms)
        ws_url = _wait_for_ws_url(port, timeout_ms)
        cdp = CdpConnection.connect(ws_url, timeout_ms=timeout_ms)
        page = _attach_page(cdp, proc, profile)
    except Exception:
        _kill_chrome_tree(proc)
        shutil.rmtree(profile, ignore_errors=True)
        raise
    return page


def _attach_page(cdp, proc, profile):
    target_id = cdp.send('Target.createTarget', {'url': 'about:blank'})['targetId']
    res = cdp.send('Target.attachToTarget', {'targetId': target_id, 'flatten': True})
    page = CdpPage(cdp, session_id=res['sessionId'], target_id=target_id,
                   proc=proc, profile=profile)
    page.send('Page.enable', timeout_ms=10_000)
    page.send('Runtime.enable', timeout_ms=10_000)
    page.send('DOM.enable', timeout_ms=10_000)
    page.send('Page.bringToFront', timeout_ms=10_000)
    return page


@contextmanager
def cdp_create_driver(headless=True, timeout_ms=60_000):
    """等价于 plrt_create_driver()，yield 一个 CdpPage，退出时杀掉 Chrome。"""
    page = _launch_chrome(headless, timeout_ms)
    try:
        yield page
    finally:
        page.cdp.close()
        _kill_chrome_tree(page.proc)
        # Chrome 释放 profile 文件是异步的，稍等片刻再清，清不掉也无妨
        for _ in range(10):
            try:
                shutil.rmtree(page.profile)
                break
            except Exception:
                time.sleep(0.3)

