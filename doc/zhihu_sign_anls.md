# 知乎 x-zse-93 / x-zse-96 请求头逆向实战分析

> 本文记录通过 Chrome 抓包 + 前端 JS 源码逆向，完整还原知乎 Web 端反爬签名请求头 `x-zse-93`、`x-zse-96`、`x-zst-81` 计算逻辑的完整过程：访问的链接、搜索关键词、关键代码位置、关键分析与判断。
> 逆向完成于 2026-10-18，算法版本 `101_3_3.0`。

---

## 一、背景与目标

知乎 Web 端几乎所有 `/api/*` 请求都带三个反爬请求头：

```
x-zse-93: 101_3_3.0
x-zse-96: 2.0_qYwqJWSkXXsK=gyedDJNh7RI31hZVSsDDrBLIHSrfgwDC0iDTl3JTLnuhXOtaPx3
x-zst-81: 3_2.0VhnTj77m-qofgh3...（可选，服务端下发的会话指纹）
```

目标是弄清这三个头各自怎么算、依赖哪些输入，并给出可复现的 Python 实现。最终实现生成的签名请求返回 **HTTP 200**，服务端校验通过。

---

## 二、访问的链接

| 用途 | URL |
|---|---|
| 知乎页面（抓包入口） | `https://www.zhihu.com/question/2045055313053843631/answer/2095218403346749183` |
| 目标测试接口（话题动态） | `https://www.zhihu.com/api/v5.1/topics/19588503/feeds/timeline_activity/v2?desktop=true&page=1&limit=7` |
| 签名模块所在分块（核心） | `https://static.zhihu.com/heifetz/3964.app.cb10463d9c412aa84d0c.js` |
| 主应用分块 | `https://static.zhihu.com/heifetz/main.app.e98962fde881ea71c456.js` |
| runtime / vendor | `https://static.zhihu.com/heifetz/runtime.app.518d54fd3167125557e5.js`、`vendor.92ed966b299812d66d9f.js` |

抓包时页面共发出 70+ 个带签名的 API 请求，覆盖 `/api/v4/me`、`/api/v4/questions/*/feeds`、`/api/v5.1/topics/*/relation/v2` 等。

---

## 三、搜索关键词（可复现线索）

- `x-zse-96`、`x-zse-93`、`x-zst-81`、`d_c0`
- 知乎签名逆向 / 知乎 zse 逆向 / heifetz
- `2.0_` 前缀签名 / `101_3_3.0` 版本号
- `__ZH__.zse` / `__g._encrypt` / Zhihu VM 加密

---

## 四、逆向过程

### 第 1 步：抓包确认头与常量

用 Chrome 网络抓包（webRequest 后端）刷新知乎问题页，拿到一批带 `x-zse-93`/`x-zse-96` 的请求。关键观察：

```
GET /api/v4/me?include=is_realname
  x-zse-93: 101_3_3.0
  x-zse-96: 2.0_qYwqJWSkXXsK=gyedDJNh7RI31hZVSsDDrBLIHSrfgwDC0iDTl3JTLnuhXOtaPx3
```

- `x-zse-93` 恒定 `101_3_3.0` —— 像是版本串而非签名；
- `x-zse-96` 每次随 URL 变化，且长度随请求复杂度变化（≈53~64 字符）—— 是真正的签名。

### 第 2 步：定位签名模块（grep 关键字符串）

下载全部 heifetz JS 分块（30+ 个），逐个 grep：

```bash
for f in *.js; do grep -l "x-zse-96" $f; done
```

命中唯一分块 **`3964.app.cb10463d9c412aa84d0c.js`**（约 3.5MB，含 1514 等多个模块）。继续在该分块内分析。

### 第 3 步：还原 source 拼接（模块 93823 / 88545 / 62845 / 18543 / 10261）

`3964.app` 是独立的 webpack 实例（模块用 `ei,eo,ec` 参数名），各模块可读。核心模块：

**模块 93823 —— header 名与版本**：
```js
// 93823:function(ei,eo,ec){ ... ed=ec(1514);
var eh = function(ei){ return ei&&ei.version&&"function"==typeof ei.encrypt
    ? ei : {encrypt: ed.ZP, version: ed.XL}; };      // 加密器封装（默认用模块1514的ZP/XL）
var ep = function(ei, eo, ec){ var eu = "".concat(ei,"_").concat(eo);
    return ec ? ["".concat(ec,"_").concat(eu), "x-zse-93", "x-zse-96"]
              : [eu, "x-zse-83", "x-zse-86"]; };
```
- `ep(HN.Web=3, "3.0", appId="101")` → `["101_3_3.0", "x-zse-93", "x-zse-96"]` → 解释了 `x-zse-93=101_3_3.0`。

**模块 88545 —— Web 端签名入口（最关键）**：
```js
function eA(ei, eo, ec, eu){          // ei=url, eo=body, ec={zse93,dc0,xZst81}, eu=encryptor
  var ef = ec.zse93, ed = ec.dc0, eh = ec.xZst81;
  var eg = mR(ei);                    // URL 的 pathname+search
  var ey = Wn(eo);                    // body 序列化
  var eA = [ef, eg, ed, kA(ey)&&ey, eh].filter(Boolean).join("+");   // ← source
  return {source: eA, signature: encrypt(md5(eA))};
}
// eZ() 包装器：读 d_c0（cookie），算签名，set 头
//   e_.set("x-zse-93", "101_3_3.0")
//   e_.set("x-zse-96", "2.0_" + signature)
```
- `source = [zse93, path+search, d_c0, body?, xZst81].join("+")`；
- `signature = encrypt(md5(source))`；
- `x-zse-96 = "2.0_" + signature`。

**模块 62845 —— 前缀常量**：
```js
// 62845:function(...) var eu, ef = "2.0";
// eu.iOS="5_2.0", eu.Android="4_2.0", eu.Web="3_2.0"
```
- `F="2.0"` 就是 `x-zse-96` 的前缀；`Web="3_2.0"` 是 `x-zst-81` 的前缀（`x-zst-81 = "3_2.0" + 加密内容`）。

**模块 18543 —— URL/工具**：
```js
// em = function(ei){ var eo = new URL(ei,"https://www.zhihu.com");
//       return "".concat(eo.pathname).concat(eo.search); };   // pathname+search
// eE = function(){ var ei = /d_c0=([^;]+)/.exec(document.cookie); return ei&&ei[1]; }
```

**模块 10261 —— MD5**：
- 标准 blueimp-md5，默认导出 `md5(s)` 返回小写 hex。

### 第 4 步：x-zst-81 的来源

在 `3964.app` 内 grep `x-zst-81` 出现在两处：一是模块 88545 里作为 source 末项 / header 透传；二是约 143672 字节处的配置加载：

```js
// e6() 通过 getHybridConfig / account/me 拿到
ef = eo["x-zst-81"]; ...
return { xAppVersion:ec, xUDId:eu, xZst81:ef, ... };
```

判断：`x-zst-81` 是**服务端下发的会话指纹 token**（来自 account/me 等配置接口），客户端原样透传进 source 并作为请求头回传。它本身前缀 `3_2.0` 由模块 62845 的 `Web="3_2.0"` 生成。

### 第 5 步：加密器 ZP = 模块 1514 —— 一个被 VM 包裹的自研加密

模块 1514 尾部导出：

```js
// 1514:function(...){ ... A="3.0" ...
var D = function(ei){ return __g._encrypt(encodeURIComponent(ei)); };
exports.XL = A, exports.ZP = D;
```

即 `ZP(e) = __g._encrypt(encodeURIComponent(e))`。但 `__g._encrypt` 不是明文函数 —— 它由一段 **字节码 VM** 在运行时构造：

```js
// l.prototype.O 是一个 ~77 case 的字节码解释器（T 状态机跳转）
// 模块加载时执行： (new l).O("ABt7CAAUSAAAC...")   // base64 字节码
// 解释执行中 case 478 构造 _encrypt 闭包：
//   this.C[3] = function(ei){ var eo = new l; eo.S=t; eo.S[0]=ei;
//                eo.O(h.G, h.V, h.D); return eo.C[3]; }
```

该 VM：
- 通过 `eval("Date"/"window"/"document"/"Math"/"Array"/"__g"...)` 获取真实环境引用；
- `document`/`navigator`/`location`/`history`/`screen` 在 Node 环境 `eval` 抛 `ReferenceError`，被 VM `catch`（`T -= 114`）吸收；
- 用 `Math.random()` 生成随机盐（首字节，服务端忽略）；
- 明文块形如 `[盐, 0x0A, 输入字节..., 0x09 填充]`；
- 调用 `__g.r`（S 盒 + 32 轮 Feistel 线性变换）块加密 + CBC 链；
- 结果用**自定义 base64** 编码（`=` 也是普通字符）。

**分析与判断**：这里刻意用"字节码 VM + eval + 环境探测"把真正算法藏起来，纯静态还原成本极高（我在移植时逐一核对 50 个 case 的 JS 语义，仍卡在方法分派等边角）。因此改走"保留原始 JS，用 JS 引擎执行"的路线。

### 第 6 步：用 quickjs 在 Python 中执行模块 1514

试过两条路：
1. **纯 Python 移植 VM 解释器** —— 写了 `vm1514.py`，块加密 `__g.r` 已与 Node 输出完全一致（[203,27,213,...] 逐字节相同），但整体 VM 仍有 JS 语义差异（`eval` 环境、稀疏数组、`NaN`、方法分派），难以收尾。
2. **Python 内嵌 JS 引擎执行原模块** —— `js2py` 语义不全（缺 `atob`/`Array.from`，且 VM 内 `eval` 分配 `_encrypt` 失败）；**`quickjs`（真实 QuickJS 引擎）一次成功**：

```python
import quickjs
ctx = quickjs.Context()
ctx.eval(js_with_module1514_and_shims)      # 需要 atob shim + window={} + webpack shim
sig = ctx.eval('__exp.ZP("...")')           # 与浏览器完全一致
```

- quickjs 环境里 `document` 等未定义，`eval("document")` 抛 ReferenceError，与 Node 行为一致（验证过该路径产出的签名可过服务端）。

### 第 7 步：服务端验证（权威判定）

用 Python 生成的完整请求头发送：

```
GET /api/v5.1/topics/19588503/feeds/timeline_activity/v2?desktop=true&page=1&limit=7
x-zse-93: 101_3_3.0
x-zse-96: 2.0_<Python计算的签名>
```

→ **HTTP 200**，返回话题动态 `totals: 45481`。三种头全部验证通过。

---

## 五、关键代码位置汇总

| 分块 | 模块 ID | 作用 |
|---|---|---|
| `3964.app.*.js` | 1514 | 加密器 ZP（VM 混淆，`ZP=e=>__g._encrypt(encodeURIComponent(e))`） |
| `3964.app.*.js` | 93823 | header 名与版本（`101_3_3.0` / x-zse-93 / x-zse-96） |
| `3964.app.*.js` | 88545 | Web 签名入口：`source` 拼接 + `x-zse-96="2.0_"+ZP(md5(source))` |
| `3964.app.*.js` | 10261 | MD5（hex） |
| `3964.app.*.js` | 62845 | `F="2.0"`、`Web="3_2.0"` 前缀常量 |
| `3964.app.*.js` | 18543 | `mR`=pathname+search、`rA`=d_c0 cookie 读取 |
| `3964.app.*.js` | ~143672 处 | `x-zst-81` 来自服务端配置接口（account/me 等） |

---

## 六、分析与判断

1. **`x-zse-93` 不是签名**，是版本号：`{appId(101)}_{平台(3=Web)}_{加密器版本(3.0)}`。`x-zse-96` 才是签名。
2. **签名输入（source）与请求本身强绑定**：`[版本, path+search, d_c0, body, xZst81].join("+")`。`d_c0` 是登录 Cookie，`xZst81` 是服务端下发的会话指纹 → 服务端能用自己掌握的 `d_c0`/`xZst81` 复算比对。
3. **加密是"解密可验证"而非"确定输出"**：`ZP` 内部用 `Math.random()` 生成随机盐，同一 source 每次输出不同，但服务端解密后比对 `md5(source)` 即可验证 → 随机盐被忽略。
4. **防御手段**：核心加密器用自研字节码 VM + `eval` 环境探测 + 稀疏数组/NaN 等 JS 语义，大幅抬高静态还原门槛；每次发版还会改表（S 盒/轮密钥）与版本号。
5. **破解路线选择**：静态还原 VM 成本高、易错；"保留原 JS + 真实 JS 引擎执行" 是可靠且可维护的方案（知乎改版时只需重提模块 1514）。纯 Python 的 source 构造 + MD5 + 常量层保持不变，易维护。

---

## 七、可复现材料

- 完整 Python 实现与使用说明：`doc/zhihu_sign.md`
- 加密模块提取脚本：`doc/zhihu_sign.md` 第四节 `extract_module1514.py`
- 环境：Python 3.10 + quickjs + requests

> 仅供学习研究，请遵守知乎用户协议与法律法规。
