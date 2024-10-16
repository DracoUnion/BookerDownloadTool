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

bili_payload = "{\"3064\":1,\"5062\":\"1704873471951\",\"03bf\":\"https%3A%2F%2Fwww.bilibili.com%2F\",\"39c8\":\"333.1007.fp.risk\",\"34f1\":\"\",\"d402\":\"\",\"654a\":\"\",\"6e7c\":\"839x959\",\"3c43\":{\"2673\":1,\"5766\":24,\"6527\":0,\"7003\":1,\"807e\":1,\"b8ce\":\"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\",\"641c\":0,\"07a4\":\"zh-CN\",\"1c57\":8,\"0bd0\":16,\"748e\":[2560,1080],\"d61f\":[2467,1091],\"fc9d\":480,\"6aa9\":\"Asia/Hong_Kong\",\"75b8\":1,\"3b21\":1,\"8a1c\":0,\"d52f\":\"not available\",\"adca\":\"Win32\",\"80c9\":[[\"PDF Viewer\",\"Portable Document Format\",[[\"application/pdf\",\"pdf\"],[\"text/pdf\",\"pdf\"]]],[\"Chrome PDF Viewer\",\"Portable Document Format\",[[\"application/pdf\",\"pdf\"],[\"text/pdf\",\"pdf\"]]],[\"Chromium PDF Viewer\",\"Portable Document Format\",[[\"application/pdf\",\"pdf\"],[\"text/pdf\",\"pdf\"]]],[\"Microsoft Edge PDF Viewer\",\"Portable Document Format\",[[\"application/pdf\",\"pdf\"],[\"text/pdf\",\"pdf\"]]],[\"WebKit built-in PDF\",\"Portable Document Format\",[[\"application/pdf\",\"pdf\"],[\"text/pdf\",\"pdf\"]]]],\"13ab\":\"mTUAAAAASUVORK5CYII=\",\"bfe9\":\"aTot0S1jJ7Ws0JC6QkvAL/A4H1PbV+/QA3AAAAAElFTkSuQmCC\",\"a3c1\":[\"extensions:ANGLE_instanced_arrays;EXT_blend_minmax;EXT_color_buffer_half_float;EXT_disjoint_timer_query;EXT_float_blend;EXT_frag_depth;EXT_shader_texture_lod;EXT_texture_compression_bptc;EXT_texture_compression_rgtc;EXT_texture_filter_anisotropic;EXT_sRGB;KHR_parallel_shader_compile;OES_element_index_uint;OES_fbo_render_mipmap;OES_standard_derivatives;OES_texture_float;OES_texture_float_linear;OES_texture_half_float;OES_texture_half_float_linear;OES_vertex_array_object;WEBGL_color_buffer_float;WEBGL_compressed_texture_s3tc;WEBGL_compressed_texture_s3tc_srgb;WEBGL_debug_renderer_info;WEBGL_debug_shaders;WEBGL_depth_texture;WEBGL_draw_buffers;WEBGL_lose_context;WEBGL_multi_draw\",\"webgl aliased line width range:[1, 1]\",\"webgl aliased point size range:[1, 1024]\",\"webgl alpha bits:8\",\"webgl antialiasing:yes\",\"webgl blue bits:8\",\"webgl depth bits:24\",\"webgl green bits:8\",\"webgl max anisotropy:16\",\"webgl max combined texture image units:32\",\"webgl max cube map texture size:16384\",\"webgl max fragment uniform vectors:1024\",\"webgl max render buffer size:16384\",\"webgl max texture image units:16\",\"webgl max texture size:16384\",\"webgl max varying vectors:30\",\"webgl max vertex attribs:16\",\"webgl max vertex texture image units:16\",\"webgl max vertex uniform vectors:4095\",\"webgl max viewport dims:[32767, 32767]\",\"webgl red bits:8\",\"webgl renderer:WebKit WebGL\",\"webgl shading language version:WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)\",\"webgl stencil bits:0\",\"webgl vendor:WebKit\",\"webgl version:WebGL 1.0 (OpenGL ES 2.0 Chromium)\",\"webgl unmasked vendor:Google Inc. (NVIDIA) #X3fQVPgERx\",\"webgl unmasked renderer:ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Laptop GPU (0x00002560) Direct3D11 vs_5_0 ps_5_0, D3D11) #X3fQVPgERx\",\"webgl vertex shader high float precision:23\",\"webgl vertex shader high float precision rangeMin:127\",\"webgl vertex shader high float precision rangeMax:127\",\"webgl vertex shader medium float precision:23\",\"webgl vertex shader medium float precision rangeMin:127\",\"webgl vertex shader medium float precision rangeMax:127\",\"webgl vertex shader low float precision:23\",\"webgl vertex shader low float precision rangeMin:127\",\"webgl vertex shader low float precision rangeMax:127\",\"webgl fragment shader high float precision:23\",\"webgl fragment shader high float precision rangeMin:127\",\"webgl fragment shader high float precision rangeMax:127\",\"webgl fragment shader medium float precision:23\",\"webgl fragment shader medium float precision rangeMin:127\",\"webgl fragment shader medium float precision rangeMax:127\",\"webgl fragment shader low float precision:23\",\"webgl fragment shader low float precision rangeMin:127\",\"webgl fragment shader low float precision rangeMax:127\",\"webgl vertex shader high int precision:0\",\"webgl vertex shader high int precision rangeMin:31\",\"webgl vertex shader high int precision rangeMax:30\",\"webgl vertex shader medium int precision:0\",\"webgl vertex shader medium int precision rangeMin:31\",\"webgl vertex shader medium int precision rangeMax:30\",\"webgl vertex shader low int precision:0\",\"webgl vertex shader low int precision rangeMin:31\",\"webgl vertex shader low int precision rangeMax:30\",\"webgl fragment shader high int precision:0\",\"webgl fragment shader high int precision rangeMin:31\",\"webgl fragment shader high int precision rangeMax:30\",\"webgl fragment shader medium int precision:0\",\"webgl fragment shader medium int precision rangeMin:31\",\"webgl fragment shader medium int precision rangeMax:30\",\"webgl fragment shader low int precision:0\",\"webgl fragment shader low int precision rangeMin:31\",\"webgl fragment shader low int precision rangeMax:30\"],\"6bc5\":\"Google Inc. (NVIDIA) #X3fQVPgERx~ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Laptop GPU (0x00002560) Direct3D11 vs_5_0 ps_5_0, D3D11) #X3fQVPgERx\",\"ed31\":0,\"72bd\":0,\"097b\":0,\"52cd\":[0,0,0],\"a658\":[\"Arial\",\"Arial Black\",\"Arial Narrow\",\"Book Antiqua\",\"Bookman Old Style\",\"Calibri\",\"Cambria\",\"Cambria Math\",\"Century\",\"Century Gothic\",\"Century Schoolbook\",\"Comic Sans MS\",\"Consolas\",\"Courier\",\"Courier New\",\"Georgia\",\"Helvetica\",\"Helvetica Neue\",\"Impact\",\"Lucida Bright\",\"Lucida Calligraphy\",\"Lucida Console\",\"Lucida Fax\",\"Lucida Handwriting\",\"Lucida Sans\",\"Lucida Sans Typewriter\",\"Lucida Sans Unicode\",\"Microsoft Sans Serif\",\"Monotype Corsiva\",\"MS Gothic\",\"MS PGothic\",\"MS Reference Sans Serif\",\"MS Sans Serif\",\"MS Serif\",\"Palatino Linotype\",\"Segoe Print\",\"Segoe Script\",\"Segoe UI\",\"Segoe UI Light\",\"Segoe UI Semibold\",\"Segoe UI Symbol\",\"Tahoma\",\"Times\",\"Times New Roman\",\"Trebuchet MS\",\"Verdana\",\"Wingdings\",\"Wingdings 2\",\"Wingdings 3\"],\"d02f\":\"124.04347527516074\"},\"54ef\":\"{\\\"b_ut\\\":\\\"7\\\",\\\"home_version\\\":\\\"V8\\\",\\\"i-wanna-go-back\\\":\\\"-1\\\",\\\"in_new_ab\\\":true,\\\"ab_version\\\":{\\\"for_ai_home_version\\\":\\\"V8\\\",\\\"tianma_banner_inline\\\":\\\"CONTROL\\\",\\\"enable_web_push\\\":\\\"DISABLE\\\"},\\\"ab_split_num\\\":{\\\"for_ai_home_version\\\":54,\\\"tianma_banner_inline\\\":54,\\\"enable_web_push\\\":10}}\",\"8b94\":\"\",\"df35\":\"312C2F31-1D48-E108C-4232-D7E96B104A8D1070864infoc\",\"07a4\":\"zh-CN\",\"5f45\":null,\"db46\":0}"
'''
bili_payload = {
    "3064":1, #  ptype, mobile => 2, others => 1
    "5062":"1704873471951", #  timestamp
    "03bf":"https%3A%2F%2Fwww.bilibili.com%2F", #  url accessed
    "39c8":"333.1007.fp.risk", #  spm_id,
    "34f1":"", #  target_url, default empty now
    "d402":"", #  screenx, default empty
    "654a":"", #  screeny, default empty
    "6e7c":"839x959", #  browser_resolution, window.innerWidth || document.body && document.body.clientWidth + "x" + window.innerHeight || document.body && document.body.clientHeight
    "3c43":{ #  3c43 => msg
        "2673":1, #  hasLiedResolution, window.screen.width < window.screen.availWidth || window.screen.height < window.screen.availHeight
        "5766":24, #  colorDepth, window.screen.colorDepth
        "6527":0, #  addBehavior, !!window.HTMLElement.prototype.addBehavior, html5 api
        "7003":1, #  indexedDb, !!window.indexedDB, html5 api
        "807e":1, #  cookieEnabled, navigator.cookieEnabled
        "b8ce":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", #  ua
        "641c":0, #  webdriver, navigator.webdriver, like Selenium
        "07a4":"zh-CN", #  language
        "1c57":8, #  deviceMemory in GB, navigator.deviceMemory
        "0bd0":16, #  hardwareConcurrency, navigator.hardwareConcurrency
        "748e":[
            2560, #  window.screen.width
            1080  #  window.screen.height
        ], #  screenResolution
        "d61f":[
            2467, #  window.screen.availWidth
            1091  #  window.screen.availHeight
        ], #  availableScreenResolution
        "fc9d":480, #  timezoneOffset, (new Date).getTimezoneOffset()
        "6aa9":"Asia/Hong_Kong", #  timezone, (new window.Intl.DateTimeFormat).resolvedOptions().timeZone
        "75b8":1, #  sessionStorage, window.sessionStorage, html5 api
        "3b21":1, #  localStorage, window.localStorage, html5 api
        "8a1c":0, #  openDatabase, window.openDatabase, html5 api
        "d52f":"not available", #  cpuClass, navigator.cpuClass
        "adca":"Win32", #  platform, navigator.platform
        "80c9":[
            [
                "PDF Viewer",
                "Portable Document Format",
                [
                    [
                        "application/pdf",
                        "pdf"
                    ],
                    [
                        "text/pdf",
                        "pdf"
                    ]
                ]
            ],
            [
                "Chrome PDF Viewer",
                "Portable Document Format",
                [
                    [
                        "application/pdf",
                        "pdf"
                    ],
                    [
                        "text/pdf",
                        "pdf"
                    ]
                ]
            ],
            [
                "Chromium PDF Viewer",
                "Portable Document Format",
                [
                    [
                        "application/pdf",
                        "pdf"
                    ],
                    [
                        "text/pdf",
                        "pdf"
                    ]
                ]
            ],
            [
                "Microsoft Edge PDF Viewer",
                "Portable Document Format",
                [
                    [
                        "application/pdf",
                        "pdf"
                    ],
                    [
                        "text/pdf",
                        "pdf"
                    ]
                ]
            ],
            [
                "WebKit built-in PDF",
                "Portable Document Format",
                [
                    [
                        "application/pdf",
                        "pdf"
                    ],
                    [
                        "text/pdf",
                        "pdf"
                    ]
                ]
            ]
        ], # plugins
        "13ab":"mTUAAAAASUVORK5CYII=", # canvas fingerprint
        "bfe9":"aTot0S1jJ7Ws0JC6QkvAL/A4H1PbV+/QA3AAAAAElFTkSuQmCC", # webgl_str
        "a3c1":[
            "extensions:ANGLE_instanced_arrays;EXT_blend_minmax;EXT_color_buffer_half_float;EXT_disjoint_timer_query;EXT_float_blend;EXT_frag_depth;EXT_shader_texture_lod;EXT_texture_compression_bptc;EXT_texture_compression_rgtc;EXT_texture_filter_anisotropic;EXT_sRGB;KHR_parallel_shader_compile;OES_element_index_uint;OES_fbo_render_mipmap;OES_standard_derivatives;OES_texture_float;OES_texture_float_linear;OES_texture_half_float;OES_texture_half_float_linear;OES_vertex_array_object;WEBGL_color_buffer_float;WEBGL_compressed_texture_s3tc;WEBGL_compressed_texture_s3tc_srgb;WEBGL_debug_renderer_info;WEBGL_debug_shaders;WEBGL_depth_texture;WEBGL_draw_buffers;WEBGL_lose_context;WEBGL_multi_draw",
            "webgl aliased line width range:[1, 1]",
            "webgl aliased point size range:[1, 1024]",
            "webgl alpha bits:8",
            "webgl antialiasing:yes",
            "webgl blue bits:8",
            "webgl depth bits:24",
            "webgl green bits:8",
            "webgl max anisotropy:16",
            "webgl max combined texture image units:32",
            "webgl max cube map texture size:16384",
            "webgl max fragment uniform vectors:1024",
            "webgl max render buffer size:16384",
            "webgl max texture image units:16",
            "webgl max texture size:16384",
            "webgl max varying vectors:30",
            "webgl max vertex attribs:16",
            "webgl max vertex texture image units:16",
            "webgl max vertex uniform vectors:4095",
            "webgl max viewport dims:[32767, 32767]",
            "webgl red bits:8",
            "webgl renderer:WebKit WebGL",
            "webgl shading language version:WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)",
            "webgl stencil bits:0",
            "webgl vendor:WebKit",
            "webgl version:WebGL 1.0 (OpenGL ES 2.0 Chromium)",
            "webgl unmasked vendor:Google Inc. (NVIDIA) #X3fQVPgERx",
            "webgl unmasked renderer:ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Laptop GPU (0x00002560) Direct3D11 vs_5_0 ps_5_0, D3D11) #X3fQVPgERx",
            "webgl vertex shader high float precision:23",
            "webgl vertex shader high float precision rangeMin:127",
            "webgl vertex shader high float precision rangeMax:127",
            "webgl vertex shader medium float precision:23",
            "webgl vertex shader medium float precision rangeMin:127",
            "webgl vertex shader medium float precision rangeMax:127",
            "webgl vertex shader low float precision:23",
            "webgl vertex shader low float precision rangeMin:127",
            "webgl vertex shader low float precision rangeMax:127",
            "webgl fragment shader high float precision:23",
            "webgl fragment shader high float precision rangeMin:127",
            "webgl fragment shader high float precision rangeMax:127",
            "webgl fragment shader medium float precision:23",
            "webgl fragment shader medium float precision rangeMin:127",
            "webgl fragment shader medium float precision rangeMax:127",
            "webgl fragment shader low float precision:23",
            "webgl fragment shader low float precision rangeMin:127",
            "webgl fragment shader low float precision rangeMax:127",
            "webgl vertex shader high int precision:0",
            "webgl vertex shader high int precision rangeMin:31",
            "webgl vertex shader high int precision rangeMax:30",
            "webgl vertex shader medium int precision:0",
            "webgl vertex shader medium int precision rangeMin:31",
            "webgl vertex shader medium int precision rangeMax:30",
            "webgl vertex shader low int precision:0",
            "webgl vertex shader low int precision rangeMin:31",
            "webgl vertex shader low int precision rangeMax:30",
            "webgl fragment shader high int precision:0",
            "webgl fragment shader high int precision rangeMin:31",
            "webgl fragment shader high int precision rangeMax:30",
            "webgl fragment shader medium int precision:0",
            "webgl fragment shader medium int precision rangeMin:31",
            "webgl fragment shader medium int precision rangeMax:30",
            "webgl fragment shader low int precision:0",
            "webgl fragment shader low int precision rangeMin:31",
            "webgl fragment shader low int precision rangeMax:30"
        ], # webgl_params, cab be set to [] if webgl is not supported
        "6bc5":"Google Inc. (NVIDIA) #X3fQVPgERx~ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Laptop GPU (0x00002560) Direct3D11 vs_5_0 ps_5_0, D3D11) #X3fQVPgERx", # webglVendorAndRenderer
        "ed31":0, # hasLiedLanguages
        "72bd":0, # hasLiedOs
        "097b":0, # hasLiedBrowser
        "52cd":[
            0, # void 0 !== navigator.maxTouchPoints ? t = navigator.maxTouchPoints : void 0 !== navigator.msMaxTouchPoints && (t = navigator.msMaxTouchPoints);
            0, # document.createEvent("TouchEvent"), if succeed 1 else 0
            0 # "ontouchstart" in window ? 1 : 0
        ], # touch support
        "a658":[
            "Arial",
            "Arial Black",
            "Arial Narrow",
            "Book Antiqua",
            "Bookman Old Style",
            "Calibri",
            "Cambria",
            "Cambria Math",
            "Century",
            "Century Gothic",
            "Century Schoolbook",
            "Comic Sans MS",
            "Consolas",
            "Courier",
            "Courier New",
            "Georgia",
            "Helvetica",
            "Helvetica Neue",
            "Impact",
            "Lucida Bright",
            "Lucida Calligraphy",
            "Lucida Console",
            "Lucida Fax",
            "Lucida Handwriting",
            "Lucida Sans",
            "Lucida Sans Typewriter",
            "Lucida Sans Unicode",
            "Microsoft Sans Serif",
            "Monotype Corsiva",
            "MS Gothic",
            "MS PGothic",
            "MS Reference Sans Serif",
            "MS Sans Serif",
            "MS Serif",
            "Palatino Linotype",
            "Segoe Print",
            "Segoe Script",
            "Segoe UI",
            "Segoe UI Light",
            "Segoe UI Semibold",
            "Segoe UI Symbol",
            "Tahoma",
            "Times",
            "Times New Roman",
            "Trebuchet MS",
            "Verdana",
            "Wingdings",
            "Wingdings 2",
            "Wingdings 3"
        ], # font details. see https://github.com/fingerprintjs/fingerprintjs for implementation details
        "d02f":"124.04347527516074" # audio fingerprint. see https://github.com/fingerprintjs/fingerprintjs for implementation details
    },
    "54ef":"{\"b_ut\":\"7\",\"home_version\":\"V8\",\"i-wanna-go-back\":\"-1\",\"in_new_ab\":true,\"ab_version\":{\"for_ai_home_version\":\"V8\",\"tianma_banner_inline\":\"CONTROL\",\"enable_web_push\":\"DISABLE\"},\"ab_split_num\":{\"for_ai_home_version\":54,\"tianma_banner_inline\":54,\"enable_web_push\":10}}", #  abtest info, embedded in html
    "8b94":"", #  refer_url, document.referrer ? encodeURIComponent(document.referrer).substr(0, 1e3) : ""
    "df35":"312C2F31-1D48-E108C-4232-D7E96B104A8D1070864infoc", #  _uuid, set from cookie, generated by client side(algorithm remains unknown)
    "07a4":"zh-CN", #  language
    "5f45":None, #  laboratory, set from cookie, null if empty, source remains unknown
    "db46":0 #  is_selfdef, default 0
}
'''

bili_hdrs = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com/',
    "Origin": "https://www.bilibili.com/",
    "Authority": "api.bilibili.com",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Content-Type": "application/json;charset=UTF-8",
    "sec-ch-ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Microsoft Edge";v="114"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
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

