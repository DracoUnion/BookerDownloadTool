# 知乎 x-zse-93 / x-zse-96 / x-zst-81 签名算法（Python 实现）

> 逆向目标：知乎 Web 端 API 请求头 `x-zse-93`、`x-zse-96`、`x-zst-81` 的计算逻辑。
> 验证：用本实现生成的签名请求 `https://www.zhihu.com/api/v5.1/topics/19588503/feeds/timeline_activity/v2?desktop=true&page=1&limit=7`，**服务端返回 HTTP 200**（话题动态 45481 条）。
> 逆向日期：2026-10-18/19。算法基于当时线上 heifetz 分块 `3964.app.cb10463d9c412aa84d0c.js`。

---

## 一、算法总览

知乎 Web 端对绝大多数 `/api/*` 请求自动附加三个反爬签名头：

| 请求头 | 值格式 | 含义 |
|---|---|---|
| `x-zse-93` | `101_3_3.0` | 版本串：`{appId}_{平台}_{加密器版本}`，Web 端固定 |
| `x-zse-96` | `2.0_{签名}` | 真正签名：`{版本前缀}_{ZP(md5(source))}` |
| `x-zst-81` | `3_2.0{密文}` | 服务端下发的会话指纹 token（部分接口需要） |

**签名计算流程**（对应前端模块 88545 的 `eA`/`eZ`）：

```
source = [ "101_3_3.0", url_path+search, d_c0, body?, x_zst_81 ].filter(Boolean).join("+")
md5hex = MD5(source)                        # 32 位小写 hex
sig    = ZP(md5hex)                          # 模块 1514 加密器
x-zse-96 = "2.0_" + sig
x-zse-93 = "101_3_3.0"
```

各字段来源：

- `url_path+search`：请求 URL 的 `pathname + "?" + query`（`new URL(url)` 的 pathname + search）。
- `d_c0`：Cookie `d_c0` 的值（形如 `xxxxx=|时间戳`）。
- `body`：请求体（GET 无 body 则省略）；对象会被 `JSON.stringify`。
- `x_zst_81`：`x-zst-81` 请求头值（服务端下发），有则拼在 source 末尾。
- 拼接分隔符是 `+`，空项通过 `filter(Boolean)` 剔除。

**ZP 加密器**（模块 1514）是知乎自研的混淆加密：
- 自定义块加密 `__g.r`（S 盒 + 32 轮 Feistel 线性变换）+ CBC 链 `__g.x`；
- 明文块 = `[随机盐, 0x0A, 输入字节..., 0x09 填充]`；
- 结果用自定义 base64（`=` 也是普通字符）编码。
- 整体包裹在一个 JS 虚拟机（VM，`l.prototype.O` 解释器）里，字节码在运行时通过 `eval` 生成，极难静态还原 —— 本实现选择**在 Python 中用 quickjs 引擎直接执行模块 1514 原始 JS**，保证与浏览器算法逐字节一致。

---

## 二、环境依赖

- Python 3.8+
- `pip install quickjs requests`（quickjs 是 Python 绑定的 QuickJS JS 引擎）

模块 1514 的原始 JS 代码需一并放置（见下文"提取 module1514.js"）。

---

## 三、完整代码 `zhihu_sign.py`

```python
# -*- coding: utf-8 -*-
"""
知乎 x-zse-93 / x-zse-96 / x-zst-81 请求头签名计算（Python 版）。

算法来源：知乎 heifetz 前端包 3964.app.*.js
  - 模块 93823 : header 名与版本常量
  - 模块 88545 : Web 端签名 source 拼接 + 调用 encryptor
  - 模块 10261 : MD5
  - 模块 1514  : 真正的加密器 ZP（VM 混淆块加密 + 自定义 base64）
  - 模块 62845 : F="2.0"（x-zse-96 前缀）、Web="3_2.0"（x-zst-81 前缀）

模块 1514 是 JS 混淆 VM，难以 1:1 移植为纯 Python；
这里用 quickjs（Python 绑定 QuickJS JS 引擎）执行模块 1514 的原始 JS，
与浏览器端算法完全一致。source 拼接与 MD5 用纯 Python 实现。
"""
import hashlib
import json
import os
import re
from urllib.parse import quote, urlparse

try:
    import quickjs
except ImportError:
    quickjs = None

# ---------------------------------------------------------------------------
# 常量（模块 93823 / 62845 / 88545）
# ---------------------------------------------------------------------------
ZSE93 = "101_3_3.0"       # x-zse-93 值：appId(Zhihu=101) + "_" + 平台(3=Web) + "_" + 版本(3.0)
SIG_VERSION = "2.0"       # 模块 62845 F 常量，x-zse-96 前缀
ZST81_PREFIX = "3_2.0"    # 模块 62845 Web 平台版本，x-zst-81 前缀


# ---------------------------------------------------------------------------
# 在 quickjs 中加载模块 1514，获得 ZP 加密函数
# ---------------------------------------------------------------------------
_JS_TEMPLATE = r"""
// ---- atob shim（模块 1514 case 331 用 base64 解码初始字节码）----
var atob = function(b64){
  var B='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  var out='', i=0, len=b64.length, chr1,chr2,chr3,enc1,enc2,enc3,enc4;
  while(i<len){
    enc1=B.indexOf(b64.charAt(i++)); enc2=B.indexOf(b64.charAt(i++));
    enc3=B.indexOf(b64.charAt(i++)); enc4=B.indexOf(b64.charAt(i++));
    chr1=(enc1<<2)|(enc2>>4); chr2=((enc2&15)<<4)|(enc3>>2); chr3=((enc3&3)<<6)|enc4;
    out+=String.fromCharCode(chr1);
    if(enc3!=64) out+=String.fromCharCode(chr2);
    if(enc4!=64) out+=String.fromCharCode(chr3);
  }
  return out;
};
var window = {};
// ---- webpack 模块 shim ----
var __mod = {}; var __exp = {};
function __req(id){
  if(id===74185) return {_: function(x){ return typeof x; }};
  throw new Error('missing module '+id);
}
// ---- 知乎签名模块 1514（webpack 工厂函数，原代码）----
// __MODULE_1514_BODY__

;(__MODULE_1514_BODY__)(__mod, __exp, __req);
;window.__ZP = __exp.ZP;
"""

_CTX = None


def _ensure_ctx():
    """初始化 quickjs 上下文并加载模块 1514。"""
    global _CTX
    if _CTX is not None:
        return _CTX
    if quickjs is None:
        raise RuntimeError("需要安装 quickjs 库：pip install quickjs")
    mod_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "module1514.js")
    if not os.path.exists(mod_file):
        raise FileNotFoundError("缺少 module1514.js（知乎加密模块原代码）")
    body = open(mod_file, encoding="utf-8").read().strip()
    body = re.sub(r"^\d+:", "", body)      # 去掉 webpack 模块头 "1514:function(...)"
    if body.endswith(","):
        body = body[:-1]
    js = _JS_TEMPLATE.replace("__MODULE_1514_BODY__", body)
    ctx = quickjs.Context()
    ctx.eval(js)
    _CTX = ctx
    return ctx


def zhihu_encrypt(s):
    """对应模块 1514 导出的 ZP：ZP(e) = __g._encrypt(encodeURIComponent(e))。"""
    ctx = _ensure_ctx()
    return ctx.eval("__exp.ZP(" + json.dumps(s) + ")")


def md5hex(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# source 构造（模块 88545 的 eA 函数）
# ---------------------------------------------------------------------------
def build_source(url, dc0, xzst81=None, body=None):
    """Web 端 source：eA = [zse93, path+search, dc0, body?, xZst81].filter(Boolean).join("+")。"""
    u = urlparse(url)
    path_search = (u.path if u.path else "") + (("?" + u.query) if u.query else "")
    parts = [ZSE93, path_search, dc0]
    if body is not None:
        if isinstance(body, (dict, list)):
            body = json.dumps(body, separators=(",", ":"))
        parts.append(body)
    if xzst81:
        parts.append(xzst81)
    return "+".join(p for p in parts if p)


def compute_signature(url, dc0, xzst81=None, body=None):
    """签名 = ZP(md5(source))。返回 (source, md5hex, sig)。"""
    source = build_source(url, dc0, xzst81, body)
    md5_hex = md5hex(source)
    sig = zhihu_encrypt(md5_hex)      # ZP 内部会做 encodeURIComponent
    return source, md5_hex, sig


def make_headers(url, dc0, xzst81=None, body=None):
    """返回 {x-zse-93, x-zse-96, (x-zst-81)} 请求头。"""
    _, _, sig = compute_signature(url, dc0, xzst81, body)
    headers = {
        "x-zse-93": ZSE93,
        "x-zse-96": SIG_VERSION + "_" + sig,
    }
    if xzst81:
        headers["x-zst-81"] = xzst81
    return headers


def get_dc0_from_cookie(cookie_header):
    """从 Cookie 头中提取 d_c0 值。"""
    m = re.search(r"d_c0=([^;]+)", cookie_header or "")
    return m.group(1) if m else None


if __name__ == "__main__":
    url = ("https://www.zhihu.com/api/v5.1/topics/19588503/feeds/timeline_activity/v2"
           "?desktop=true&page=1&limit=7")
    dc0 = "你的d_c0值"            # 从浏览器 Cookie 取
    h = make_headers(url, dc0)
    print(h)
```

---

## 四、提取 `module1514.js`（加密模块原代码）

模块 1514 是算法核心，被混淆 VM 包裹，直接移植几乎不可能，因此我们保存其**原始 JS 代码**供 quickjs 执行。提取方法：

```bash
# 1. 下载线上 heifetz 分块（包含签名模块）
curl -o 3964.app.js "https://static.zhihu.com/heifetz/3964.app.cb10463d9c412aa84d0c.js"

# 2. 用下面的 Python 提取模块 1514（按 webpack 模块边界切割）
python extract_module1514.py
```

```python
# extract_module1514.py —— 从 heifetz 分块提取模块 1514
import re

data = open("3964.app.js", encoding="utf-8").read()
BOUND = r"(?<![0-9A-Za-z_$])"

def extract_mod(mid):
    m = re.search(BOUND + r"%d:function\([^)]*\)" % mid, data)
    s = m.start()
    header_end = m.end()
    nxt = re.search(BOUND + r"\d+:function\(", data[header_end:])
    e = header_end + nxt.start() if nxt else len(data)
    seg = data[s:e]
    seg = re.sub(r"^\d+:", "", seg)
    if seg.endswith(","):
        seg = seg[:-1]
    return seg

open("module1514.js", "w", encoding="utf-8").write(extract_mod(1514))
```

> 若线上分块 hash 变化，只需重新下载并调整文件名；`extract_mod(1514)` 提取的即是加密器模块。

---

## 五、使用示例（requests）

```python
import requests
import zhihu_sign

# 从浏览器 Cookie 拿 d_c0
cookie = requests.utils.dict_from_cookiejar(requests.get(
    "https://www.zhihu.com", timeout=10).cookies)
dc0 = cookie.get("d_c0")

url = "https://www.zhihu.com/api/v5.1/topics/19588503/feeds/timeline_activity/v2?desktop=true&page=1&limit=7"
headers = zhihu_sign.make_headers(url, dc0)
headers.update({
    "Referer": "https://www.zhihu.com/topic/19588503",
    "x-requested-with": "fetch",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
})

r = requests.get(url, headers=headers)
print(r.status_code, r.json()["paging"]["totals"])
```

---

## 六、验证结果

| 测试项 | 结果 |
|---|---|
| 目标接口 `.../feeds/timeline_activity/v2?desktop=true&page=1&limit=7` | **HTTP 200**，返回话题动态 45481 条 |
| x-zse-93 | `101_3_3.0`（固定） |
| x-zse-96 | `2.0_` + ZP(md5(source))，Python 生成被服务端接受 |
| x-zst-81 | 该接口非必需；带值接口把它拼进 source |

服务端对签名的校验方式：解密 `x-zse-96` 得到 `md5(source)` 并比对。随机盐（来自 `Math.random()`）被服务端忽略，因此每次签名不同但都有效。

---

## 七、注意事项

1. `d_c0` 是登录态 Cookie，随会话变化；签名必须用与请求同会话的 `d_c0`。
2. 模块 1514 会通过 `eval` 探测 `document/window/navigator` 等环境做随机盐与指纹；quickjs 环境里它们未定义，行为与 Node 一致（已验证可过）。
3. 知乎可能随时更新加密模块（版本号 `101_3_3.0` 会变）。失效时需重新下载 heifetz 分块并重提模块 1514，同时检查 `ZSE93`、`SIG_VERSION` 常量。
4. 本实现仅用于学习与个人自动化测试，请遵守知乎平台规则与相关法律法规。
