# 浏览器自动化检测对抗实战笔记

> 目标站：`cleantalk.org/am-i-a-bot` `bot.incolumitas.com` `browserscan.net/zh/bot-detection` `apivoid.com/tools/bot-detection-test`
>
> 核心产物：`BookerDownloadTool/patch_env_mock_wasm.js`（Playwright `add_init_script` 注入）+ `BookerDownloadTool/util.py` 中对应的 `CLIENT_HINTS` 请求头覆盖
>
> 日期：2026-10-21

---

## 0. 摘要 / 实测结果

以下为 Chromium (headless) + `--disable-blink-features=AutomationControlled` + 本 patch + `stealth.min.js` 的实际测试结果：

| 站点 | 结果 |
|---|---|
| CleanTalk am-i-a-bot | **100 分 / 0 flag（满分通过）** |
| incolumitas 新检测 & old tests | webdriverPresent/connectionRTT/pluginArray/refMatch/overrideTest/overflowTest 等**全部 OK** |
| BrowserScan | WebDriver / WebDriver Advance / Selenium / NightmareJS / PhantomJS / Headless Chrome 等**全部「正常」**；仅服务端 CDP 协议检测一项剩「机器人」 |
| APIVoid | 风险分仍高（服务端深层审计 + IP 信誉 + 跨域完整性检查，纯 JS 补丁天然可被其识别） |

**结论**：`patch_env_mock_wasm.js` 能 100% 通过「基于浏览器 JS 可见信号」的检测
（CleanTalk / incolumitas 全部通过，BrowserScan 除服务端 CDP 行外全部正常）。
无法仅靠 JS 补丁通过的是**协议层 / 服务端**检测：CDP 连接本身、
`Sec-CH-UA` HTTP 头（需 `extra_http_headers` 覆盖，见 util.py）、APIVoid 的原型完整性审计。

---

## 1. 四个站点的检测代码来源

| 站点 | 检测脚本 |
|---|---|
| CleanTalk | 内联 `ct-bot-run` 事件 + `fd.cleantalk.org/2.1.9/ct-bot-detector.min.js` |
| incolumitas | `fpCollect.min.js` `fpScanner.js` `newTests.js` `fp.min.js` |
| BrowserScan | `dist/BA3xi3GQ.js` 等 + 服务端分析（Nuxⁿ 应用） |
| APIVoid | 内联 `BotDetector` collector（约 78KB），服务端规则计分 |

---

## 2. CleanTalk — 16 项检测与 mock

检测代码位于页面内联脚本 `ct-bot-run`（`var btn = document.getElementById('ct-bot-run')`），
每次点击（以及加载后自动）跑一次 `buildSignals()`。

### 2.1 自动化框架

| 检测项 | 检测代码 | 判定 | mock |
|---|---|---|---|
| `navigator.webdriver` | `bad: navigator.webdriver === true, weight: 34` | 要为 false | 启动参数 `--disable-blink-features=AutomationControlled` + 兜底改 `Navigator.prototype.webdriver` getter |
| Selenium markers | `for (k in window) if(/cdc_\|selenium\|webdriver\|driver-evaluate\|fxdriver/i.test(k)) return true`；还有 `document.__selenium_unwrapped`、`$cdc_asdjflasutopfhvcZLmcfl_` 等 | 不得存在 | patch 第 7 节统一 `delete` 这些全局 |
| Playwright markers | `window.__playwright \|\| __pw_manual \|\| __PW_inspect` | 不得存在 | 同上，delete |
| PhantomJS | `window._phantom \|\| window.callPhantom` | 不得存在 | delete |
| Nightmare.js | `window.__nightmare` | 不得存在 | delete |

### 2.2 Headless 与浏览器环境

| 检测项 | 检测代码 | 判定 | mock |
|---|---|---|---|
| Headless UA | `/HeadlessChrome\|Electron\|slimerjs\|puppeteer/i.test(UA)` | UA 不能含 headless 字样 | context `user_agent` 已替换 |
| `window.chrome` 缺失 | `isChrome && !window.chrome` | Chrome UA 下必须有 chrome 对象 | patch 第 2 节提供 `{runtime, app, csi, loadTimes, webstore}` |
| WebGL 软件渲染 | `/SwiftShader\|llvmpipe\|Mesa OffScreen/i.test(RENDERER)` | 不能是软渲染 | 由 `stealth.min.js`（puppeteer-extra）覆盖 WebGL 渲染器名为真实 GPU；实测 "ANGLE (AMD, Radeon R9 200…)" |
| 零尺寸窗口 | `outerWidth===0 \|\| outerHeight===0` | 不能为 0 | patch 第 4 节 `outerWidth=inner+16, outerHeight=inner+120` |
| 默认 headless 分辨率 | `screen.width===800 && screen.height===600 && outerWidth===0` | 不满足即可 | 同上 |

### 2.3 浏览器指纹

| 检测项 | 检测代码 | 判定 | mock |
|---|---|---|---|
| Plugins | `navigator.plugins.length===0 && !isMobile` | 应有插件 | patch 第 3 节构造 3 个 `[object Plugin]` |
| Languages | `!navigator.languages \|\| length===0` | 非空 | `locale='zh-CN'` 已保证 |
| CPU 核心数 | `hardwareConcurrency===0 \|\| >32` | 1~32 | 不改（实测 4~16 正常） |
| 色深 | `screen.colorDepth===0` | 非 0 | 不改（24） |
| 屏幕尺寸 | `!screen.width \|\| !screen.height` | 非 0 | 不改 |

### 2.4 行为

| 检测项 | 检测代码 | 判定 | mock |
|---|---|---|---|
| Interaction | `(moves===0 && keys===0) && (Date.now()-firstTs>1500)` | 需有鼠标/键盘事件 | 运行 `runTest()` 前人为 `page.mouse.move()` 即可（弱信号） |

---

## 3. incolumitas — 检测项与 mock

### 3.1 新检测（`newTests.js?version=v0.6.4`）

| 检测项 | 检测代码 | 判定 | mock |
|---|---|---|---|
| `puppeteerEvaluationScript` | `new Error('test err').stack.includes('puppeteer')` | 栈中不能出现 puppeteer | 不产生，天然 OK |
| `webdriverPresent` | `navigator.webdriver ? 'FAIL' : 'OK'` | webdriver 为 false | 见 2.1 |
| `connectionRTT` | `connection.rtt === undefined ? UNKNOWN : rtt===0 ? FAIL : OK` | rtt>0 | **patch 第 8 节** mock `navigator.connection={effectiveType:'4g',rtt:50,downlink:10}` |
| `puppeteerExtraStealthUsed` | 检测 `Navigator.prototype` 上 `hardwareConcurrency`/`languages` getter 的 `toString` 是否非原生 + 权限状态 | getter 须保持原生或吻合 | 不主动 patch 这两个原型 getter |
| `inconsistentUserAgent` | `data['user-agent']` 与 UA 比较 | UA 一致 | context UA 已对齐 |
| `inconsistentLanguages` | `Accept-Language` 头 与 `navigator.languages` 互包含 | 头与 JS 一致 | `extra_http_headers` + locale 对齐 |

### 3.2 插件专项（`newTests.js`）—— 本 patch 修补的重点

| 检测项 | 检测代码 | 判定 | 需要什么 |
|---|---|---|---|
| `pluginArray` | `!(navigator.plugins instanceof PluginArray) \|\| plugins[0].toString()!=='[object Plugin]'` | 要是真 PluginArray、元素 `[object Plugin]` | patch：`Object.setPrototypeOf(plugins, PluginArray.prototype)` + 每个 plugin `Symbol.toStringTag='Plugin'` |
| `refMatch` | `plugins[0][0].enabledPlugin === plugins[0]` | mimeType 要回链 plugin | patch：每个 mimeType 子对象带 `enabledPlugin` 回指 |
| `overrideTest` | `plugins.refresh = 'test'; plugins.refresh === 'test'` | refresh 应可覆盖 | 原生 PluginArray 可写，patch 下 OK |
| `overflowTest` | `plugins.item(4294967296) === plugins[0]` | item 可调用、索引回绕 | patch：自实现 `item(i){return this[i%this.length]}`，避免原生 `PluginArray.prototype.item` 抛 Illegal invocation |
| `pluginsLength` | `navigator.plugins.length===0` | >0 | patch 提供 3 个插件 |

### 3.3 旧检测（fpCollect / fpScanner）

`fpCollect.min.js` 会遍历 `navigator` 原型链每个属性的 `get.toString()`，
因此**不能往 `navigator` 实例加 own 属性、不能用 JS 函数替换 getter 后再调用**，否则 `webDriverAdvanced`/`detailChrome` 会暴露。

| 检测项 | 判定 | mock |
|---|---|---|
| `webdriver` / `webDriverValue` | `'webdriver' in navigator`（真 Chrome 为 true）；值 false | 只改 `Navigator.prototype.webdriver`，**绝不在实例上 defineProperty** |
| `webDriverAdvanced` | `Object.getOwnPropertyDescriptor(Object.getPrototypeOf(navigator), prop)` 的 getter `toString` | getter 保持原生（AutomationControlled 已处理） |
| `hasChrome` / `detailChrome` | `!!window.chrome`；遍历 `webstore/runtime/app/csi/loadTimes` | patch 提供 chrome 对象，`csi/loadTimes/webstore` 的 `constructor.toString()` 为 `[native code]`（配 puppeteer-extra 更稳） |
| `phantomJS` / `selenium` / `nightmareJS` | in-window / in-document 键 | patch 第 7 节 delete |

---

## 4. BrowserScan — 检测项与 mock

BrowserScan 是 Nuxⁿ SPA，客户端收集数据 + 服务端判分。客户端可见判定：

| 检测项 | 判定 | 处理 |
|---|---|---|
| WebDriver | `navigator['webdriver'] \|\| Ke(navigator,'webdriver')`（own 属性检查） | **关键：不能在 navigator 上加 own webdriver 属性** → 已修，实测 WebDriver 行从「机器人」→「正常」 |
| WebDriver Advance | 同上 GetOwnPropertyDescriptor | getter 保持原生 |
| Selenium / NightmareJS / PhantomJS / Awesomium / Cef / CefSharp / Coachjs / FMiner / Geb / Phantomas / Rhino / Webdriverio / Headless Chrome | 各种 window/document 键 | patch 第 7 节 delete |
| CDP | `'emit' in window`、代理注入的 `xxx_Array` 类 window 键（`/^([a-z]){3}_.*_(Array\|Promise\|Symbol\|Proxy\|JSON\|Object)$/`）、`__nw_*` 等 | 客户端全部为 false；**但服务端 CDP 协议检测仍判机器人**（协议层，JS 无法隐藏） |
| Navigator 完整性 | 展示 `webdriver/plugins/mimeTypes/userAgentData/hardwareConcurrency/connection` 等值 | patch 后均为合理值；`userAgentData.brands` 为 Chrome/124，`connection.rtt=50` |
| HeadlessChrome brand | `userAgentData.brands` 含 `HeadlessChrome`/版本 ≠ 伪造 UA | **patch 第 6 节**整体替换 `Navigator.prototype.userAgentData` 为 Chrome/124 的 mock；`Sec-CH-UA` HTTP 头用 `util.py` 的 `CLIENT_HINTS` 覆盖 |

---

## 5. APIVoid — 为何纯 JS 无法通过

APIVoid 的 `BotDetector` collector 做了**服务端深层审计**，对我们的 JS 补丁几乎必然报警：

| 信号 | 为什么躲不掉 |
|---|---|
| `collectPrototypeIntegrity` | 遍历 `navigator` 上 `webdriver/plugins/mimeTypes/connection/userAgentData` 等 accessor 与 `Function.prototype.toString`、`webgl.getParameter` 等方法的 `toString`，**凡是被 JS 替换/包装的都会进 `patchedAccessors/patchedMethods`** |
| `Sec-CH-UA` HTTP 头 | 由浏览器在请求层生成（headless 报 `HeadlessChrome/128`），JS 改不了，只能靠 `extra_http_headers` 覆盖或让浏览器真实版本匹配 |
| 跨 realm 一致性 | 比较主页面 / `<iframe>` / worker 里的 `navigator` 值是否一致，JS 补丁很难同步到所有 realm |
| IP / TLS / TCP 指纹 | 完全在浏览器外，与本 patch 无关 |

**实践意义**：APIVoid 这类工具适合作为「补丁有效性」的参考上限，而不是必须 0 分的标准。

---

## 6. 关键实现细节（本 patch 踩过的坑）

1. **不能用 `window.__APPLIED__` 全局守卫**。
   Playwright `add_init_script` 每个 document/frame 只执行一次；若加了守卫，
   会在 `about:blank` 这个首文档里执行一次后永久跳过后续真实页面，
   而 `about:blank` 里 `navigator.userAgentData` 是 `undefined` → 后续页面 client hints 没被覆盖。
2. **webdriver 只能放 `Navigator.prototype`，不能放 `navigator` 实例**。
   真实 Chrome 无 own 属性。BrowserScan 判 `Object.getOwnPropertyDescriptor(navigator,'webdriver')`，
   incolumitas fpCollect 遍历 own+proto 所有属性 toString。放实例 = 直接暴露。
   兜底写法：仅当 `navigator.webdriver === true` 才替换原型 getter；否则保持原生（AutomationControlled 已给 false）。
3. **`userAgentData` 的 `brands` getter 不可单独 patch**（`NavigatorUAData` 实例是 lazy、原型 getter 非 configurable）。
   必须整体替换 `Navigator.prototype.userAgentData`，返回一个 `brands/getHighEntropyValues/toJSON` 都自洽的 mock。
4. **plugins 要真 PluginArray + `[object Plugin]` + mimeType 回链 + item() 索引回绕**，
   否则 incolumitas 的 `pluginArray/refMatch/overflowTest` 全挂；`item()` 必须自实现，否则原生方法在普通数组上抛 `Illegal invocation`。
5. **WASM stub 必须是合法二进制**。原文件里 `new WebAssembly.Module` 用的是残缺字节（直接抛错），
   且 `exports._calculate_hash = ...` 用了非 async 箭头函数里的 `await` —— 顶层语法错误，整个脚本注入即失败。
   已改为手写合法的最小 wasm（`{magic, version, type, func, memory, export`("memory","_calculate_hash")`, code}`），
   让四站对 `WebAssembly.validate/Module/Memory/getHighEntropyValues` 的探测都能通过，并且任何页面都不抛错。
6. **`Sec-CH-UA` 请求头必须和 UA 一起伪造**。headless Chromium 网络层会自动带 `sec-ch-ua: "HeadlessChrome";v="128"`，
   与 JS 侧伪造的 Chrome/124 不一致 → BrowserScan/APIVoid 双杀。
   在 `util.py` 用 `extra_http_headers` 显式覆盖（见下）。

---

## 7. 补丁结构（`patch_env_mock_wasm.js`，9 节）

1. `navigator.webdriver` —— 仅当为 true 时替换 `Navigator.prototype.webdriver` getter
2. `window.chrome` —— 兜底提供 `runtime/app/csi/loadTimes/webstore`
3. `navigator.plugins / mimeTypes / pdfViewerEnabled` —— 3 个 `[object Plugin]`，带 enabledPlugin 回链 + 自实现 item()/namedItem()
4. `outerWidth / outerHeight` —— `inner+16 / inner+120`
5. `document.documentMode` —— `undefined`（IE 遗留检查）
6. `navigator.userAgentData` —— 整体 mock 成 Chrome/124（brands + getHighEntropyValues + toJSON）
7. 清理 Selenium/Playwright/PhantomJS/Nightmare 等全局标记
8. `navigator.connection` —— `{effectiveType:'4g', rtt:50, downlink:10, saveData:false}`（修 incolumitas connectionRTT）
9. WASM 兼容层 —— 合法最小 wasm，导出 `memory` 与 `_calculate_hash`

---

## 8. util.py 配套改动

```python
BROWSER_UA = 'Mozilla/5.0 ... Chrome/124.0.0.0 Safari/537.36'
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
# 注入点
context = browser.new_context(user_agent=BROWSER_UA, ..., extra_http_headers=CLIENT_HINTS)
context.add_init_script(d('patch_env_mock_wasm.js'))
context.add_init_script(d('stealth.min.js'))
```

为什么需要：headless Chromium 网络层会自行生成 `sec-ch-ua: "HeadlessChrome";v="128"`，
与 JS 侧伪造不一致。用 `extra_http_headers` 覆盖后，四站的「Client Hints/请求头」模块看到的
与 UA 完全一致。**这是 JS 补丁无法做到、必须由驱动层完成的环节。**

### 附带修复：`add_init_script` 传路径 bug（重要）

原 `util.py` 写的是：

```python
context.add_init_script(d('patch_env_mock_wasm.js'))   # d(...) 返回路径字符串
```

Playwright 的 `add_init_script(script=...)` 接受的是 **JS 源码**，不是路径。
把一个路径字符串当 `script` 传进去 = 注入一个字符串字面量（no-op），
**补丁从未真正运行**。这也是此前 CleanTalk 在真实调用路径下只有 61/3 分的原因。

修复：新增 `read_js(name)` 读取文件内容，4 处调用全部改为 `read_js(...)`：

```python
def read_js(name):
    """读取脚本文件内容（add_init_script 需要的是 JS 源码，不是路径）。"""
    with open(path.join(DIR, name), encoding='utf-8') as f:
        return f.read()

context.add_init_script(read_js('patch_env_mock_wasm.js'))
context.add_init_script(read_js('stealth.min.js'))
```

修复后实测同一代码路径：CleanTalk **100/0**，`userAgentData.brands = Chrome/124`。

---

## 9. 如何自测

`test_detect.py`（仓库根目录）已封装，直接：

```bash
python test_detect.py                      # 默认 cleantalk
python -c "...sync_playwright..."          # 或参考上文 4 站脚本
```

关键断言：

- cleantalk：`score == 100` 且 `flagged == 0`
- incolumitas：`webdriverPresent/connectionRTT/pluginArray/refMatch/overrideTest/overflowTest == OK`
- browserscan：`webdriver 行 == 正常`
- 无 `await is only valid in async` 之类的注入错误