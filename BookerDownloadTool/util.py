from playwright.sync_api import sync_playwright
import re
import requests
import os
import shutil
from os import path
import imgyaso
import subprocess as subp
import tempfile
import uuid
from contextlib import contextmanager
from camoufox.sync_api import Camoufox
from camoufox import DefaultAddons
from playwright.sync_api import sync_playwright
from functools import reduce
from http.cookies import SimpleCookie
import json
import hashlib
import yaml
from pydantic import BaseModel, parse_obj_as, ValidationError

RE_INFO = r'\[(.+?)\]([^\[]+)'

default_hdrs = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
}

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36'

# Chrome 124 的 Sec-CH-UA 客户端提示头 —— 与下方伪造的 Chrome/124 UA 对齐，
# 覆盖 Playwright headless 自带的 "HeadlessChrome" brand（BrowserScan/APIVoid 均会检测）。
BROWSER_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
CLIENT_HINTS = {
    'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not;A=Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-ch-ua-platform-version': '"10.0.0"',
    'sec-ch-ua-full-version-list': '"Chromium";v="124.0.6367.91", "Google Chrome";v="124.0.6367.91", "Not;A=Brand";v="24.0.0.0"',
    'sec-ch-ua-arch': '"x86"',
    'sec-ch-ua-bitness': '"64"',
    'sec-ch-ua-wow64': '?0',
}

DIR = path.dirname(path.abspath(__file__))

def read_js(name):
    """读取脚本文件内容（add_init_script 需要的是 JS 源码，不是路径）。"""
    with open(path.join(DIR, name), encoding='utf-8') as f:
        return f.read()

d = lambda name: path.join(path.dirname(__file__), name)


def rm_xml_tags(html):
    html = re.sub(r'<?xml[^>]*?>', '', html)
    html = re.sub(r'xmlns=".+?"', '', html)
    return html
    
def is_gbk(ch):
    try: 
        ch.encode('gbk')
        return True
    except:
        return False
    
def filter_gbk(fname):
    return ''.join([ch for ch in fname if is_gbk(ch)])

def opti_img(img, mode, colors):
    if mode == 'quant':
        return imgyaso.pngquant_bts(img, colors)
    elif mode == 'grid':
        return imgyaso.grid_bts(img)
    elif mode == 'trunc':
        return imgyaso.trunc_bts(img, colors)
    elif mode == 'thres':
        return imgyaso.adathres_bts(img)
    else:
        return img

def fname_escape(name):
    return name.replace('\\', '＼') \
               .replace('/', '／') \
               .replace(':', '：') \
               .replace('*', '＊') \
               .replace('?', '？') \
               .replace('"', '＂') \
               .replace('<', '＜') \
               .replace('>', '＞') \
               .replace('|', '｜')

def request_retry(method, url, retry=10, check_status=False, **kw):
    kw.setdefault('timeout', 10)
    for i in range(retry):
        try:
            r = requests.request(method, url, **kw)
            if check_status: r.raise_for_status()
            return r
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            print(f'{url} retry {i}')
            if i == retry - 1: raise e

def safe_mkdir(dir):
    try: os.makedirs(dir)
    except: pass
    
def safe_rmdir(dir):
    try: shutil.rmtree(dir)
    except: pass

def safe_remove(fname):
    try: os.unlink(fname)
    except: pass

def anime4k_auto(img):
    fname = path.join(tempfile.gettempdir(), uuid.uuid4().hex + '.png')
    open(fname, 'wb').write(img)
    subp.Popen(
        ['pdf-tool', 'anime4k-auto', fname, '-G'], 
        shell=True,
    ).communicate()
    img = open(fname, 'rb').read()
    safe_remove(fname)
    return img

def parse_cookie(cookie):
    # cookie.split('; ').map(x => x.split('='))
    #     .filter(x => x.length >= 2)
    #     .reduce((x, y) =>  {x[y[0]] = y[1]; return x}, {})
    kvs = [kv.split('=') for kv in cookie.split('; ')]
    res = {kv[0]:kv[1] for kv in kvs if len(kv) >= 2}
    return res

def set_driver_cookie(
    driver, cookie, domain,
    path='/', expires=-1, secure=False,
    http_only=False, same_site='Lax'
):
    if isinstance(cookie, str):
        cookie = cookie_str_to_dict(cookie)
    cookies = [
        {
            'name': k, 
            'value': v, 
            'domain': '.' + domain,
            'path': path,
            "expires": expires,
            "secure": secure,
            "httpOnly": http_only,
            "sameSite": same_site,
        }
        for k, v in cookie.items()
    ]
    driver.add_cookies(cookies)


@contextmanager
def camou_create_driver(headless=True, timeout=30_000):
    """Yield a native Camoufox page and its context."""
    opts = {
        "headless": headless,
        "humanize": True,
        "locale": "en-US",
        "os": ("windows",),
        "exclude_addons": [DefaultAddons.UBO],
    }
    with Camoufox(**opts) as browser:
        context = browser.new_context(
            user_agent=BROWSER_UA,
            viewport={"width":1200,"height":640},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            extra_http_headers=CLIENT_HINTS,
        )
        context.add_init_script(read_js('patch_env_mock_wasm.js'))
        context.add_init_script(read_js('stealth.min.js'))
        page = context.new_page()
        page.set_default_timeout(timeout)
        page.set_default_navigation_timeout(timeout)
        try:
            yield browser, context, page
        finally:
            page.close()
            context.close()


def dict_get_recur(obj, keys):
    res = [obj]
    for k in keys.split('.'):
        k = k.strip()
        if k == '*':
            res = reduce(lambda x, y: x + y,res, [])
        else:
            res = [o.get(k) for o in res if k in o]
    return res

def merge_video_audio(video, audio, video_fmt='mp4', audio_fmt='mp4'):
    tmpdir = path.join(tempfile.gettempdir(), uuid.uuid4().hex)
    safe_mkdir(tmpdir)
    vfname = path.join(tmpdir, f'video.{video_fmt}')
    v0fname = path.join(tmpdir, f'video0.{video_fmt}')
    open(vfname, 'wb').write(video)
    afname = path.join(tmpdir, f'audio.{audio_fmt}')
    a0fname = path.join(tmpdir, f'audio0.{audio_fmt}')
    open(afname, 'wb').write(audio)
    res_fname = path.join(tmpdir, f'merged.{video_fmt}')
    cmds = [
        ['ffmpeg', '-i', vfname, '-vcodec', 'copy', '-an', v0fname, '-y'],
        ['ffmpeg', '-i', afname, '-acodec', 'copy', '-vn', a0fname, '-y'],
        ['ffmpeg', '-i', a0fname, '-i', v0fname, '-c', 'copy', res_fname, '-y'],
    ]
    for cmd in cmds:
        print(f'cmd: {cmd}')
        subp.Popen(cmd, shell=True).communicate()
    res = open(res_fname, 'rb').read()
    safe_rmdir(tmpdir)
    return res


def float2hhmmss(num):
    int_ = int(num)
    frac = int((num - int_) * 1000)
    hr, min_, sec = int_ // 3600, int_ % 3600 // 60, int_ % 60
    return f'{hr}:{min_:02d}:{sec:02d}.{frac:03d}'

def plrt_new_context(browser):
    context =  browser.new_context(
            user_agent=BROWSER_UA,
            viewport={"width":1200,"height":640},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            extra_http_headers=CLIENT_HINTS,
        )
    context.add_init_script(read_js('patch_env_mock_wasm.js'))
    context.add_init_script(read_js('stealth.min.js'))
    return context

def plrt_new_browser(plrt, headless=True):
    return plrt.chromium.launch(
        headless=headless,
        args=[
            # 禁用AutomationControlled自动化标记（Chrome94+核心参数）
            "--disable-blink-features=AutomationControlled", 
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            # 模拟真人最大化打开浏览器
            "--start-maximized",
        ],
    )

@contextmanager
def plrt_create_driver(headless=True, timeout=30_000):
    """Yield a native Playwright page and its context."""
    with sync_playwright() as p:
        browser = plrt_new_browser(p, headless)
        context = plrt_new_context(browser)
        page = context.new_page()
        page.set_default_timeout(timeout)
        page.set_default_navigation_timeout(timeout)
        try:
            yield browser, context, page
        finally:
            page.close()
            context.close()
            browser.close()

def cookie_dict_to_str(cookie_dict: dict) -> str:
    """
    将 Cookie 字典转为合法的 HTTP Cookie 头字符串。
    若值包含逗号、分号、空格等特殊字符，自动用双引号包裹。
    """
    if not cookie_dict:
        return ""
    
    cookie = SimpleCookie()
    for key, val in cookie_dict.items():
        # 确保值是字符串，避免数字/布尔值报错
        cookie[key] = str(val)
    
    # attrs=[] 去掉多余属性, header='' 去掉 Set-Cookie 前缀
    return cookie.output(attrs=[], header='', sep='; ').strip()

def cookie_str_to_dict(cookie_str: str) -> dict:
    """
    将 Cookie 字符串解析为字典。
    自动兼容 '; ' (浏览器)分隔符，
    并能正确还原被双引号包裹的特殊字符值。
    """
    cookie_str = cookie_str.strip()
    if not cookie_str:
        return {}
    
    # 标准 ; 或 ; 分隔，用 SimpleCookie 解析（自动去引号）
    cookie = SimpleCookie(cookie_str)
    return {key: val.value for key, val in cookie.items()}

def to_kebab(name: str) -> str:
    """将技能名转为 kebab-case slug"""
    s = re.sub(r"[^\w\s\u4e00-\u9fff\-]", "", name)
    s = re.sub(r"[\s_]+", "-", s).strip("-").lower()
    return s[:60] or "unnamed"


def md5(text: str):
    return hashlib.md5(text.encode('utf8')).hexdigest()

def gen_objs_md5(*args):
    args = [
        o if isinstance(o, str) else
            json_dump_model(o)
        for o in args
    ]
    return '_'.join(md5(o) for o in args)

def render_prompt(prompt: str, **kw):
    return re.sub(r"{(\w+)}", lambda g: kw.get(g.group(1), g.group(0)), prompt)

ext_code_block = lambda s: re.search(r'```\w*([\s\S]+)```', s).group(1)
ext_cont_block = lambda s: re.search(r'\[content\]([\s\S]+)\[/content\]', s).group(1)

def json_dump_model(obj) -> str:
    """将对象（含 pydantic 模型/列表）序列化为 JSON 字符串。"""
    if isinstance(obj, BaseModel):
        obj = obj.model_dump()
    elif isinstance(obj, list):
        obj = [
            it.dict() if isinstance(it, BaseModel) else it
            for it in obj
        ]
    return json.dumps(obj, ensure_ascii=False)

def json_load_model(text: str, model_type):
    """将 JSON 文本解析为指定 pydantic 模型。"""
    try:
        return parse_obj_as(model_type, json.loads(text))
    except json.JSONDecodeError:
        return None
    except ValidationError:
        return None


def write_text(fname: str, text: str, append: bool = False) -> None:
    """将 text 以 UTF-8 写入 fname（自动创建父目录）。"""
    os.makedirs(path.dirname(fname), exist_ok=True)
    open(fname, 'a' if append else 'w', encoding='utf8').write(text)

def read_text(fname: str) -> str:
    """以 UTF-8 读取 fname 的文本内容。"""
    if not path.isfile(fname):
        return None
    text = open(fname, encoding='utf8').read()
    chs = set(text)
    # 避免读取损坏的数据
    if len(chs) == 1 and '\x00' in chs:
        text = ""
    return text

def write_yaml_model(fname: str, obj) -> None:
    """将对象（含 pydantic 模型/列表）以 YAML 形式写入 fname。"""
    if isinstance(obj, BaseModel):
        obj = obj.dict()
    elif isinstance(obj, list):
        obj = [
            it.dict() if isinstance(it, BaseModel) else it
            for it in obj
        ]
    os.makedirs(path.dirname(fname), exist_ok=True)
    with open(fname, 'w', encoding='utf8') as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False)

def read_yaml_model(fname: str, model_type):
    """从 fname 读取 YAML 并解析为指定 pydantic 模型；文件缺失或损坏时返回 None。"""
    if not path.isfile(fname) or not path.getsize(fname):
        return None
    try:
        data = yaml.safe_load(open(fname, encoding='utf8').read())
        return parse_obj_as(model_type, data) if model_type else data
    except yaml.error.YAMLError:
        return None
    except ValidationError:
        return None
