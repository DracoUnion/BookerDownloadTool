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
from playwright.sync_api import sync_playwright
from functools import reduce
from http.cookies import SimpleCookie

RE_INFO = r'\[(.+?)\]([^\[]+)'

default_hdrs = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
}

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36'

DIR = path.dirname(path.abspath(__file__))

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

def set_driver_cookie(driver, cookie, url):
    if isinstance(cookie, str):
        cookie = cookie_str_to_dict(cookie)
    cookies = [
        {'name': k, 'value': v, 'url': url}
        for k, v in cookie.items()
    ]
    if hasattr(driver, 'add_cookies'):
        driver.add_cookies(cookies)
    else:
        for item in cookies:
            driver.add_cookie(item)


@contextmanager
def camou_create_driver(headless=True, timeout=30_000):
    """Yield a native Camoufox page and its context."""
    with Camoufox(headless=headless) as browser:
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width":1920,"height":1080},
            locale="zh-CN",
            timezone_id="Asia/Shanghai"
        )
        context.add_init_script(d('patch_env_mock_wasm.js'))
        context.add_init_script(d('stealth.min.js'))
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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width":1920,"height":1080},
            locale="zh-CN",
            timezone_id="Asia/Shanghai"
        )
    context.add_init_script(d('patch_env_mock_wasm.js'))
    context.add_init_script(d('stealth.min.js'))
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
