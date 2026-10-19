# -*- coding: utf-8 -*-
"""生成 doc/xhs_api.md：小红书 Android 客户端 API 与签名机制分析文档（apk 反编译）"""
import json, re
from collections import Counter

DOC = r"D:\src\BookerDownloadTool\doc\xhs_api.md"
API_LIST = r"D:\src\BookerDownloadTool\_xhs_data\api_list.md"
API_DATA = r"D:\src\BookerDownloadTool\_xhs_data\api_final.json"

with open(API_LIST, encoding='utf-8', errors='replace') as fh:
    api_list_md = fh.read()

with open(API_DATA, encoding='utf-8') as fh:
    _rows = json.load(fh)
_counts = Counter(r['http'] for r in _rows)
_total = len(_rows)
STATS_LINE = (f"**{_total}** 个去重后的 HTTP 接口（GET {_counts.get('GET', 0)} / "
              f"POST {_counts.get('POST', 0)} / PUT {_counts.get('PUT', 0)} / "
              f"DELETE {_counts.get('DELETE', 0)}）")
STATS_SHORT = (f"**GET {_counts.get('GET', 0)} / POST {_counts.get('POST', 0)} / "
               f"PUT {_counts.get('PUT', 0)} / DELETE {_counts.get('DELETE', 0)}**，共 {_total}")

header = r'''# 小红书 Android 客户端 API 接口与签名机制

> 分析对象：`xiaohongshu.apk`（com.xingin.xhs，小红书 Android 客户端）
> 反编译工具：jadx 1.5.6，APK 共 124893 个类（classes*.dex 全部解出），主包 `com.xingin.*`
> 分析方式：扫描所有含 `@jce.*` HTTP 注解的 Service 接口定义，提取方法、路径、请求参数；并结合拦截器链与 `com.xingin.shield` / `com.xingin.tiny` 安全 SDK 源码重建签名机制
> 结果统计：__STATS_LINE__，`/api/sns` 为核心业务域

---

## 1. 通用说明

### 1.1 HTTP 框架

小红书不使用标准 Retrofit，而是基于 **Retrofit 内核改造**的自研框架 `com.xingin.net`（混淆名 `fce.*`）。接口用 `@jce.*` 注解描述，注解到 HTTP 语义的映射见 `fce/z.java`（`b(method, path, hasBody)` 分发处）：

| 注解 | HTTP 语义 | 说明 |
| --- | --- | --- |
| `@jce.f("/path")` | **GET** | `aVar2.b("GET", ...)` |
| `@jce.o("/path")` | **POST** | `aVar2.b("POST", ..., true)` |
| `@jce.p("/path")` | **PUT** | `aVar2.b("PUT", ..., true)` |
| `@jce.b("/path")` | **DELETE** | `aVar2.b("DELETE", ...)` |
| `@jce.g` / `@jce.n` / `@jce.m` | HEAD / PATCH / OPTIONS | 见 `fce/z.java` |
| `@jce.h(method="X", path="...", hasBody=...)` | 自定义方法 | 如 DELETE `/api/store/...` |
| `@jce.t("name")` 参数 | 查询参数 | ≈ Retrofit `@Query` |
| `@jce.c("name")` 参数 | 表单字段 | ≈ `@Field`，配合 `@jce.e` |
| `@jce.s("name")` 参数 | 路径占位符 | ≈ `@Path`，如 `{invite_id}` |
| `@jce.a` 参数 | 请求体 | ≈ `@Body`（JSON 序列化） |
| `@jce.i("name")` 参数 | 请求头 | ≈ `@Header` |
| `@jce.d` / `@jce.u` / `@jce.j` | FieldMap / QueryMap / HeaderMap | Map 批量参数 |
| `@jce.q` / `@jce.r` | Part / PartMap | ≈ `@Part`（上传） |
| `@jce.y` 参数 | 动态 URL | ≈ `@Url` |
| `@jce.e` 方法 | FormUrlEncoded | 表单编码 |
| `@jce.l` 方法 | Multipart | 多媒体上传 |
| `@jce.k` 方法 | Headers | 批量请求头 |

> 说明：本 APK 的 `@jce` 各注解类名与 `fce` 框架类名均为 ProGuard 混淆后的短名，语义由 `fce/z.java` 的解析分支唯一确定。

### 1.2 Base URL / HOST

主 API 的 Base URL 由配置动态下发（见 `a0b/d.java`：`esd.h.h("").n("edith.xiaohongshu.com", "https://edith.xiaohongshu.com")`）。HOST 枚举 `xa6/a.java` 定义四类：

| 枚举 | key | 默认域名 |
| --- | --- | --- |
| `EDITH` | edith | `https://edith.xiaohongshu.com` |
| `JARVIS` | main | `https://www.xiaohongshu.com` |
| `SEARCH` | search | `https://search.xiaohongshu.com` |
| `SO` | so | `https://so.xiaohongshu.com` |

**实际域集合**（含海外映射，见 `w2d/b.java` 域名映射表）：

| 域名 | 用途 |
| --- | --- |
| `edith.xiaohongshu.com` | **主 API 域**（`/api/sns`、`/api/store`、`/api/edith`、`/api/im` 等绝大多数业务接口） |
| `www.xiaohongshu.com` | Web/H5、JARVIS 主站 API |
| `search.xiaohongshu.com` / `so.xiaohongshu.com` | 搜索 |
| `live-room.xiaohongshu.com` / `mojito.xiaohongshu.com` / `wario.xiaohongshu.com` | 直播 / 电商 / 营销 |
| `referee.xiaohongshu.com` | 评价/社区治理 |
| `mediacloud.xiaohongshu.com` | 媒体云 |
| `fe-resource-app.*.xiaohongshu.com` | RN/前端资源下发 |
| `rn-resource.rnote.com` 等 | 海外 CDN 域名（rednote 系） |
| `ci.xiaohongshu.com` / `sns-*.xhscdn.com` | 图片 CDN / 元数据 |
| `imstream.xiaohongshu.com` | IM 长连接流 |
| `apm-fe.xiaohongshu.com` / `t2/t3.xiaohongshu.com` | 监控/埋点 |
| `.cos.ap-shanghai.myqcloud.com` | COS 对象存储上传 |

### 1.3 通用请求头（由网络库拦截器自动注入）

| 请求头 | 值 / 来源 | 说明 |
| --- | --- | --- |
| `xy-common-params` | URL-编码的 `k=v&k=v` 串 | **公共参数头**，主网络层自动附加（片段见下） |
| `x-legacy-did` | `xec.r.e()` | 旧版设备 ID（did，UUID v3） |
| `x-legacy-fid` | `djd.o1.f186257a.e()` | 设备指纹（Shield FingerPrintJni） |
| `x-legacy-sid` | `g1d.b.f220928a.d()` | 会话 ID |
| `x-xray-traceid` / `x-b3-traceid` | 随机 UUID | 链路追踪 / OpenTracing |
| `xhs-request-time` | 毫秒时间戳 | 请求时间 |
| `mp-common-params` | `gla.u0.f228464a.d(...)` | 小程序（非主 APP）公共参数 |
| `User-Agent` | `xhsminiapp/x.x.x` … | 客户端 UA（含版本） |
| `shield` | libxyass.so 生成 | **Shield 风控签名头**（被拦截器放行的受保护头） |
| `x-s` / `x-t` | 推断由 native（libtiny.so / libxyass.so）生成；**DEX 字符串表中不存在该字面量** | 小红书 Web 端同名签名头；Android 端实际头名需动态抓包确认（见第 3 节） |
| `xy-tt` | `/api/sc/tt` 下发 | Tiny token（带过期时间） |

`xy-common-params` 的字段（来自 `a0b/b.java` 与 `fjd/e.java` 的 k=v 提供者）：

```
platform=android & deviceId=<did> & versionName=<版本> & channel=<渠道>&
baseModeId=<> & project_id=<ECFAAF01> & app_id=<ECFAAF> &
build=<build号> & tz=<时区> & cpu_name=<> & overseas_channel=<>&
sid=<会话id> & fid=<指纹> & lang=<语言> & uis=<>&
id_token=<登录token>
```

---

## 2. 全部接口清单

以下接口均以相对 `https://edith.xiaohongshu.com`（除非路径为绝对 URL），`{xxx}` 为路径占位符。请求参数字段：`Query:` URL 查询、`Field:` 表单字段（FormUrlEncoded）、`Body:` JSON 请求体类型、`Path:` 路径占位符、`Header:` 请求头（`@jce.i`）。
'''

# 拼接接口清单（去掉开头的 "## 接口清单" 大标题，直接接在文档主标题之后）
api_body = api_list_md
# api_list.md 以 "## 接口清单" 开头，替换为二级/三级层次
# 我们把它放在 header 之后作为 "## 接口清单" 已经存在，直接移除重复大标题
# api_list.md 自带 "## 接口清单"，移除大标题（header 中已有 "## 2. 全部接口清单" 及说明）
api_body2 = re.sub(r'^## 接口清单\s*\n', '', api_list_md, count=1)

footer = '''

---

## 3. 签名 / 加签机制分析

小红书 Android 端对所有 API 请求实施了**双签名防护**：`Shield`（风控签名头对接，见 `com.xingin.shield.http`）与 `Tiny`（自研 native 签名 SDK，见 `com.xingin.tiny`），并在网络层通过 **OkHttp 拦截器**统一注入。整体请求头栈（按 OkHttp 执行顺序）：

```
Application Interceptor 链（多次添加）:
  #1 a0b.c   : 添加 xy-common-params 请求头（BaseMode 网络）
  #2 djd.o1.q: Shield 初始化（libxyass.so 加载）
  #3 gzc.p   : Tiny 签名拦截器（libtinyd.so / libtiny.so）
  #4 uja.g   : 小程序网络栈补充（mp-common-params 等）
```

### 3.1 Tiny 签名 SDK（核心 · libtinyd.so / libtiny.so）

**入口**：`gzc.p`（TinyInterceptor）拦截所有 `*.xiaohongshu.com / *.rnote.com` 请求（`djd.o1.r()` 判断 host 白名单，multipart 或指定路径跳过）。

对每个请求调用 `y8c.f.i(method, url, body)`：

```java
static Map<String,String> i(String method, String url, byte[] body) {
    URL u = new URL(url);
    String host = u.getHost(), path = u.getPath(), query = u.getQuery() != null ? u.getQuery() : "";
    // 若干字符串混淆还原：path 缺失时拼 "…"+host
    if (TinySDK.isInit)                       // f456115e
        return k3.b(100529502, method, host, path, query, body);   // → native
    return null;
}
```

`k3.b(id, args...)` → `com.xingin.tiny.internal.t.a(id, args...)` → **JNI native**。`t.a` 的第 1 个 int 是方法 ID，由 native 分发。签名 id `100529502` 进入 `libtiny.so` 的 `JNI_OnLoad` 所注册的原生方法（三库均动态注册，无 `Java_*` 导出符号），返回 `HashMap<String,String>`，即**签名头集合**——头名由 native 决定；DEX 中可确认的同族头只有 `xy-tt`（token），`x-s`/`x-t` 等名称不在 DEX 字符串表中。

**native 库**：
- `libtinyd.so`（134KB，daemon 守护，负责加载真实 so + 字符串解密桥接）
- `libtiny.so`（8.7MB，**签名算法主体**）
- Java 侧字符串全部混淆：`q7.a()` / `daemon.d.c1.a()` 用「循环 XOR + 位旋转」解码，例如 `"TQÑÚ\u0002"` 与 `"I_"` 解码后 = `"tinyd"`，`"Ù\u001b«..."` 与 `"ë,"` = `"libtinyd.so"`。

**token 刷新**：`com.xingin.xhs.antispam.entities.TinyTokenHelper` 定期从 **`POST /api/sc/tt`** 拉取签名 token（`refresh_token_time` 默认 8h，`force_refresh_token_time` 默认 23h），响应为一个 map，其中键 **`xy-tt`** 的值为 `xx,<过期时间戳>`（逗号分隔，末段为秒级时间戳，`extractExpireTime`）。拉到的整个 map 存入 `tiny_token_sign` 缓存、按请求头注入（`setCacheSign` / `getCacheSignMap`）。命中 462 状态码（`requestFailedByCacheSign`）会强制重置并重新拉取。

### 3.2 Shield 风控 SDK（com.xingin.shield · libxyass.so）

**入口**：`com.xingin.shield.http.XhsHttpInterceptor`（OkHttp Interceptor），`newInstance(token)` 其中 token = **设备 ID** `fjd.n.f214643a.a()`（`xec.r.f` 生成的 `device_id`）。

```java
Native.initializeNative();            // 加载 libxyass.so
cPtr = Native.initialize(token);      // 用 device_id 初始化，返回 cPtr
Native.intercept(chain, cPtr);        // 每次请求 → native 注入 shield 签名头
```

- native 库 `libxyass.so`（`c.f161714d = {120,121,97,115,115}` = "xyass"）。
- 初始化时还做「设备指纹」采集：`com.xingin.a.a.f.FingerPrintJni`（native），供 `djd.o1.e()` → `x-legacy-fid` 使用。
- 配套 **SSK 密钥交换**（`com.xingin.shield.ssk`）：`X25519KeyExchange.decryptSsk(...)`，用 X25519 曲线协商出 32 字节 `_sid_ssk_v3`（账户安全密钥），存于 `SharedPreferences("ssk")`。请求带 `x-errno` / `x-url` 等用于调试与路由。

### 3.3 签名头字段与整体流程

以一次 `GET /api/sns/v6/homefeed` 为例，完成加签后请求头大致为：

```
Host: edith.xiaohongshu.com
User-Agent: xhsminiapp/<ver>...
xy-common-params: platform=android&deviceId=…&versionName=…&append=…
x-legacy-did: 3a6f2c...        (android_id 的 UUID)
x-legacy-fid: <FingerPrintJni 指纹>
x-legacy-sid: <会话id>
x-xray-traceid: <随机uuid>
x-t: <native 签名值（名称需抓包确认）>
x-s: <native 签名值（名称需抓包确认）>
xy-tt: <token>,1700000000-8h
shield: <libxyass.so 计算的风控头>
```

**算法要点**（native 侧，Java 层仅传递输入并注入输出）：
1. **输入拼接**：`method`、`host`、`path`、`query`、`body`（字节）连同设备/时钟上下文一并传入 native。
2. **Tiny 核心**：native 以「请求方法 + host + path + query + body + token + 设备/时钟上下文」为输入，输出签名头集合。常见命名中 `x-t` 为时间戳、`x-s` 为签名，但本 APK 的 DEX 中不存在这两个字面量，实际头名需在真机抓包或 hook 时确认；算法在 `libtiny.so` 中实现，且被 VMP 保护。
3. native 以 `HashMap` 返回签名头，由拦截器 `builder.header(k, v)` 注入。
4. token 过期或服务端 462 → 重新 `POST /api/sc/tt` 获取（`xy-tt`）。

> **WebView / H5 / 小程序**使用另一套头（`tia/w.java` 放行名单）：`x-mini-sig`、`x-mini-mua`、`x-mini-gid`、`shield`、`xy-platform-info`、`xy-common-params`。`x-mini-*` 为小程序签名族（`uja`/`gla` 网络栈），`shield` 与 APP 同源。

### 3.4 加密方式小结（诚实声明）

**DEX 字符串表实证**（直接检索 `classes*.dex` 的 MUTF-8 字符串条目，长度前缀 + NUL 精确匹配）：

| 头名 | 是否存在于 DEX | 说明 |
| --- | --- | --- |
| `xy-common-params` | ✅ 8 个 dex | Java 层拼接，精确可复现 |
| `x-legacy-did` / `x-legacy-fid` / `x-legacy-sid` | ✅ | TinyInterceptor 直接 `header(...)` |
| `x-xray-traceid` / `x-b3-traceid` | ✅ | 链路追踪 |
| `xy-tt` | ✅ 1 个 dex | token（`/api/sc/tt` 下发） |
| `shield` | ✅ 1 个 dex | Shield 头（native 写入） |
| `x-mini-sig` / `x-mini-mua` / `x-mini-gid` | ✅ 1 个 dex | 小程序/H5 签名族 |
| `mp-common-params` | ✅ | 小程序公共参数 |
| `x-s` / `x-t` / `x-s-common` / `x-t-common` | ❌ **均不存在** | 若存在则由 native 生成，头名需动态确认 |

**能精确还原的部分（纯 Python 可实现）**：

| 组件 | 算法 / 机制 | 位置 |
| --- | --- | --- |
| did（`x-legacy-did` / `deviceId`） | `UUID.nameUUIDFromBytes(android_id)`（MD5 + RFC4122 位掩码） | `xec/r.java` |
| `xy-common-params` | `k=v&k=v` URL-encode 拼接 | `q4c/a.java` |
| 混淆字符串解密 | 循环 XOR + 位旋转（8 位循环移位） | `tiny/internal/q7|r7|d1.java` |
| `xy-tt` 过期解析 | 逗号分隔、末段秒级时间戳 | `TinyTokenHelper.extractExpireTime` |
| `/api/sc/tt` token 刷新 | POST 表单 + JSON 返回 `{ts:{xy-tt:...}}` | `TinyTokenApi.java` |
| 签名输入装配 | `(method, host, path, query, body)` 5 元组传 native | `y8c/f.java#i` |

**无法用纯 Python 复现的部分（必须动态执行）**：

- native 签名头（`x-s` / `x-t` 这类命名）的具体生成算法：位于 `libtiny.so`（8.7MB）中，且该库使用 **VMP 虚拟机保护**（`.rodata` 存在 `vmp.a.s` / `vmp.b` / `vmp.c` / `vmp.m` 模块标记、`error_6001/6010/6022/6051/6054/6008` 反调试计数），字节码运行时动态展开，静态逆向等价算法工作量极大。
- `shield` 头：位于 `libxyass.so`，同样为 native + JNI `RegisterNatives`（三个库均只有 `JNI_OnLoad` 导出，无 `Java_*` 符号），算法经 `Native.intercept(chain, cPtr)` 就地改写请求。
- 因此 **任何声称用几行 Python 哈希就能算出 native 签名头的实现，在技术上不可行**。正确做法是：真机/模拟器跑 APP → Frida hook `y8c.f.i` / `Native.intercept` 拿真实签名头 → 或 unidbg 模拟执行 `libtiny.so` 的 `JNI_OnLoad` 注册入口。

---

## 4. Python 加密逻辑实现

> 已确认可运行的实现见 `doc/py/xhs_sign.py`（与下文代码一致）。该文件完整实现上表「能精确还原的部分」；native 签名调用给出**接口骨架**（`NativeSignatureRequest` / `bridge_args`），实际执行需接入 Frida 或 unidbg。

### 4.1 did / device_id（对应 `xec.r.f`）

```python
import hashlib, uuid

def device_id_from_android_id(android_id: str) -> str:
    """Java UUID.nameUUIDFromBytes 的 Python 实现。
    取 android_id 的 UTF-8 字节做 MD5，按 RFC 4122 设置 version(3)/variant 位。"""
    raw = android_id.encode("utf-8")
    digest = bytearray(hashlib.md5(raw).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30          # version = 3
    digest[8] = (digest[8] & 0x3F) | 0x80          # RFC 4122 variant
    return str(uuid.UUID(bytes=bytes(digest)))
```

### 4.2 混淆字符串解密（对应 `tiny daemon d1/c1`）

```python
def xor_repeat(data: bytes, key: bytes, rounds: int = 3) -> bytes:
    """d1.a: data[i] ^= key[i % len(key)]，c1.a 外层重复 rounds 次（构造后 = 3）。"""
    out = bytearray(data)
    for _ in range(rounds):
        for i in range(len(out)):
            out[i] ^= key[i % len(key)]
    return bytes(out)

def rol8(v: int, n: int) -> int:  # 8 位循环左移
    n %= 8
    return ((v << n) | (v >> (8 - n))) & 0xFF

def ror8(v: int, n: int) -> int:  # 8 位循环右移
    n %= 8
    return ((v >> n) | (v << (8 - n))) & 0xFF
```

实测（与 `daemon/d.java` 一致）：`xor_repeat("TQÑÚ\\x02", "I_")` 后按位调整得 `tinyd`；`xor_repeat("Ù\\x1b«...", "ë,")` 后按位调整得 `libtinyd.so`。

### 4.3 xy-common-params（对应 `q4c/a.java`）

```python
from urllib.parse import quote

def common_params(values: dict) -> str:
    """q4c.a.b: k=v&k=v，值按 java.net.URLEncoder 规则（空格→+）。"""
    return "&".join(
        k + "=" + quote(str(v), safe="-_.!*'()") for k, v in values.items()
    )
```

### 4.4 xy-tt token 过期（对应 `TinyTokenHelper.extractExpireTime`）

```python
import time

def parse_xy_tt(value: str) -> int:
    """xy-tt = 'xx,<秒时间戳>'；返回过期秒时间戳。"""
    return int(value.rstrip(",").split(",")[-1])

def token_valid(xy_tt: str, now: int | None = None) -> bool:
    return parse_xy_tt(xy_tt) > (int(time.time()) if now is None else now)
```

### 4.5 native 签名桥接口（非伪造）

```python
@dataclass(frozen=True)
class NativeSignatureRequest:
    method: str
    host: str
    path: str
    query: str = ""
    body: bytes = b""

    def bridge_args(self):
        """对应 y8c.f.i(method, url, body) 传入 native 的 5 元组。"""
        return (self.method, self.host,
                self.path or ("/" + self.host), self.query or "", self.body)
```

真实签名需让 `libtiny.so` / `libxyass.so` 在目标设备执行上述 5 元组输入后才会生成；不可在纯 Python 中复算。

---

## 5. 相关反编译类速查
| 类（混淆名） | 职责 |
| --- | --- |
| `fce/z.java` | Retrofit 内核注解分发（HTTP 方法映射） |
| `fce/y.java` / `fce/x.java` | 注解解析 |
| `gzc/p.java` | **TinyInterceptor**（Tiny 签名注入） |
| `y8c/f.java` | Tiny Java 桥 + `i(method,url,body)` 签名入口 |
| `com/xingin/tiny/internal/t.java` | native 方法 `a(int id, Object...)` 分发（JNI） |
| `com/xingin/tiny/internal/k3.java` | Tiny 静态封装（部分方法 ID 走 native） |
| `com/xingin/tiny/internal/q7/r7.java` | 字符串 XOR/位旋转解密器 |
| `com/xingin/shield/http/XhsHttpInterceptor.java` | **Shield 签名拦截器** |
| `com/xingin/shield/http/Native.java` | Shield native 方法（libxyass.so） |
| `com/xingin/shield/ssk/X25519KeyExchange.java` | X25519 会话密钥 |
| `com/xingin/xhs/antispam/entities/TinyTokenHelper.java` | token 拉取/缓存（`/api/sc/tt`） |
| `com/xingin/xhs/antispam/entities/TinyTokenApi.java` | `POST /api/sc/tt` 定义 |
| `a0b/c.java` + `a0b/b.java` | BaseMode 网络 + `xy-common-params` 注入 |
| `fjd/e.java` / `q4c/a.java` | 公共参数提供者 / 序列化 |
| `xec/r.java` | did 生成（UUID v3 基于 android_id） |
| `fjd/n.java` | device_id 缓存（Shield token 源） |
| `djd/o1.java` | Shield + Tiny 初始化与设备指纹 |
| `tia/w.java` | H5/小程序请求头放行名单 |
| `w2d/b.java` | 域名映射表（国内/海外） |
| `xa6/a.java` | HOST 枚举（EDITH/JARVIS/SEARCH/SO） |

---

## 6. 备注

- 接口数量与方法分布：__STATS_SHORT__。
- `@jce.h` 自定义方法（如 DELETE）与部分 `@jce.*` 组合的旧接口仍在使用。
- Body 参数多数为 Kotlin data class（`com.xingin.*.entities.*` / `com.xingin.capa.feature_model.session.*`），文档列出类型名以便反查字段定义。
- 本分析基于 2026-10 线上版本，签名算法（`libtiny.so` / `libxyass.so`）与 token 接口可能随版本迭代变化，请以最新 APK 为准。
'''

final = header + '\n' + api_body2.strip() + '\n' + footer
final = final.replace('__STATS_LINE__', STATS_LINE).replace('__STATS_SHORT__', STATS_SHORT)

with open(DOC, 'w', encoding='utf-8') as fh:
    fh.write(final)
print("written:", DOC, "chars:", len(final))