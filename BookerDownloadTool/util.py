import requests
import os
import shutil
from os import path
import imgyaso
import subprocess as subp
import tempfile
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from functools import reduce

RE_INFO = r'\[(.+?)\]([^\[]+)'

bili_hdrs = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Referer': 'https://www.bilibili.com/',
}

dmzj_hdrs = {
    'Referer': 'http://manhua.dmzj.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
}

default_hdrs = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
}

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36'

DIR = path.dirname(path.abspath(__file__))

d = lambda name: path.join(path.dirname(__file__), name)

    
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
        ['wiki-tool', 'anime4k-auto', fname, '-G'], 
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
        
def set_driver_cookie(driver, cookie):
    if isinstance(cookie, str):
        cookie = parse_cookie(cookie)
    for k, v in cookie.items():
        driver.add_cookie({'name': k, 'value': v})

def create_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--log-level=3')
    options.add_argument(f'--user-agent={UA}')
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)
    driver.set_script_timeout(1000)
    # StealthJS
    stealth = open(d('stealth.min.js')).read()
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": stealth
    })
    return driver

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

