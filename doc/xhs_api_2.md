# 小红书 Web 端 HTTP API 接口与签名机制

> 分析对象：`xhs-workbench` 项目的 `src/adapters/xhs/` 模块（源自 xhs-cli / xiaohongshu-cli），基于 HTTP API 直连 `edith.xiaohongshu.com`（Web 端主域）与 `creator.xiaohongshu.com`（创作者平台域）
> 签名承载：`xhshow` 库（`Xhshow` / `SignState` / `SessionManager`），macOS/Chrome 环境参数
> 覆盖范围：账号信息、笔记读写、搜索、评论、互动、关注、通知、二维码登录、文件上传、创作发布等 **40+ 个接口**
> 文档代码基于 `src/adapters/xhs/client.py`、`client_mixins.py`、`signing.py`、`creator_signing.py` 重构整理

---

## 1. 通用说明

### 1.1 域名与 Base URL

| 常量 | 值 | 用途 |
| --- | --- | --- |
| `EDITH_HOST` | `https://edith.xiaohongshu.com` | **主 API 域**（`/api/sns/**` 等绝大多数接口） |
| `CREATOR_HOST` | `https://creator.xiaohongshu.com` | 创作者平台域（`/web_api/**`、`/api/media/**`、`/api/galaxy/**`） |
| `UPLOAD_HOST` | `https://ros-upload.xiaohongshu.com` | COS 对象存储直传（`PUT /<file_id>`） |
| `HOME_URL` | `https://www.xiaohongshu.com` | 网页端主页 / 笔记 SSR 页面（`/explore/<note_id>`） |

路由规则（`_creator_host`）：URI 以 `/api/galaxy/` 开头 → `CREATOR_HOST`，否则 → `EDITH_HOST`。
创作者登录/发布接口虽以 `_main_api_post` 调用，但会通过 `header_overrides` 覆盖 `origin`、`referer` 为 `CREATOR_HOST`。

### 1.2 通用请求头（`_base_headers`）

| 请求头 | 值 | 说明 |
| --- | --- | --- |
| `user-agent` | `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36` | Chrome 145 / macOS UA |
| `content-type` | `application/json;charset=UTF-8` | POST 请求体为紧凑 JSON |
| `cookie` | `k1=v1; k2=v2; ...` | 登录态，必含 `a1`（签名输入）与 `web_session` |
| `origin` | `https://www.xiaohongshu.com` | 主域请求；创作域请求覆盖为 `CREATOR_HOST` |
| `referer` | `https://www.xiaohongshu.com/` | 同上 |
| `sec-ch-ua` | `"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"` | Client Hints |
| `sec-ch-ua-mobile` | `?0` | |
| `sec-ch-ua-platform` | `"macOS"` | |
| `sec-fetch-dest` / `sec-fetch-mode` / `sec-fetch-site` | `empty` / `cors` / `same-site` | |
| `accept` | `application/json, text/plain, */*` | |
| `accept-language` | `zh-CN,zh;q=0.9,en;q=0.8` | |
| `dnt` / `priority` | `1` / `u=1, i` | |

签名相关头（由 `sign_main_api` / `sign_creator` 注入）见下表：

| 请求头 | 说明 |
| --- | --- |
| `x-s` | 请求签名（主域 `XYS_`/`XYW_` 前缀；创作域 `XYW_` 前缀） |
| `x-s-common` | 公共签名（AES/RC4 加密的浏览器环境指纹 + cookie 摘要，仅主域 GET/POST 使用） |
| `x-t` | 毫秒时间戳（与签名内 `x4` 一致） |
| `x-b3-traceid` | 16 位十六进制追踪 ID |
| `x-xray-traceid` | 32 位十六进制追踪 ID（前 16 位 `时间戳<<23 | seq`，后 16 位随机） |
| `x-mns` | `unload` |
| `xy-direction` | 分片键（`user_id` 或随机决定，1–100） |
| `x-rap-param` | 部分接口（feed/搜索/发布）需要 |

### 1.3 响应包裹格式

所有主域与创作域接口返回统一的 JSON 包裹（`_handle_response` 解析后**只返回 `data`/`success` 字段本身**）：

```json
{
  "success": true,
  "code": 0,
  "msg": "",
  "data": { }
}
```

判定顺序（`_handle_response`）：
1. `success == true` → 返回 `data.get("success")`（一般取 `data`）。
2. `code == 300012` → 抛 `IpBlockedError`（IP 被风控）。
3. `code == 300015` → 抛 `SignatureError`（签名校验失败）。
4. `code == -100` → 抛 `SessionExpiredError`（会话过期，需重新登录）。
5. 其它 → 抛 `XhsApiError`（携带 `code` 与完整响应）。
6. HTTP 状态 461 / 471 → 触发验证码 `NeedVerifyError`，并指数退避（5s/10s/20s… 上限 30s）。

### 1.4 重试与限速

- 请求间最小间隔 `request_delay`（默认 1.0s），附高斯抖动，模拟真人浏览。
- 对 HTTP 429/500/502/503/504 及网络异常指数退避重试（最多 `max_retries` 次）。
- 每次响应会合并响应 Cookie 回内存会话。

---

## 2. 接口清单

路径相对 `EDITH_HOST`（`https://edith.xiaohongshu.com`），带 ★ 为相对 `CREATOR_HOST`（`https://creator.xiaohongshu.com`）。`Query:` = GET 查询参数；`Body:` = POST JSON 请求体。调用签名方式以 ①主域签名 `sign_main_api` ②创作域签名 `sign_creator` 标记。

### 2.1 账号与个人（Reading / Auth）

| 方法 | 路径 | 签名② | 请求参数 | 说明 |
| --- | --- | --- | --- | --- |
| `GET` | `/api/sns/web/v2/user/me` | ① | — | 当前登录用户信息（QR 登录后校验用，返回含 `login_info.user_id` / `basic_info`） |
| `GET` | `/api/sns/web/v1/user/otherinfo` | ① | Query: `target_user_id` | 指定用户主页信息 |
| `GET` | `/api/sns/web/v1/user_posted` | ① | Query: `num=30`, `cursor`, `user_id`, `image_scenes=FD_WM_WEBP` | 用户发布的笔记列表（分页，`data.notes`） |
| `GET` | `/api/sns/web/v2/note/collect/page` | ① | Query: `user_id`, `cursor`, `num=30` | 用户收藏的笔记 |
| `GET` | `/api/sns/web/v1/note/like/page` | ① | Query: `user_id`, `cursor`, `num=30` | 用户点赞的笔记 |
| `GET` | `/api/sns/web/unread_count` | ① | — | 未读消息数 |
| `GET` | `/api/sns/web/v1/you/mentions` | ① | Query: `num=20`, `cursor` | 通知-@我的 |
| `GET` | `/api/sns/web/v1/you/likes` | ① | Query: `num=20`, `cursor` | 通知-赞 |
| `GET` | `/api/sns/web/v1/you/connections` | ① | Query: `num=20`, `cursor` | 通知-关注/粉丝 |

### 2.2 笔记（Reading）

| 方法 | 路径 | 签名② | 请求参数 | 说明 |
| --- | --- | --- | --- | --- |
| `POST` | `/api/sns/web/v1/feed` | ① | Body: `source_note_id`, `image_formats=["jpg","webp","avif"]`, `extra={"need_body_topic":"1"}`, `xsec_source`, `xsec_token` | 按 ID 取笔记详情（需 `xsec_token`，否则 406；失败可降级 HTML 解析） |
| `POST` | `/api/sns/web/v1/homefeed` | ① | Body: `cursor_score`, `num=40`, `refresh_type=1`, `note_index=0`, `unread_begin_note_id`, `unread_end_note_id`, `unread_note_count=0`, `category`, `search_key`, `need_num=40`, `image_scenes=["FD_PRV_WEBP","FD_WM_WEBP"]` | 首页推荐 feed |
| `GET` | `https://www.xiaohongshu.com/explore/{note_id}` | — | 无签名（HTML 页面） | SSR 页面，`window.__INITIAL_STATE__` 内嵌笔记数据，无需 `xsec_token` 即可兜底拉取 |

> **取笔记策略（`get_note_detail`）**：有 `xsec_token` 优先走 `feed` API，失败（`NeedVerifyError`/`XhsApiError`）时降级解析 SSR HTML；无 token 则直接走 HTML。token 有效期为缓存 TTL（`NOTE_CONTEXT_TTL_SECONDS` = 86400s）。

### 2.3 搜索（Reading）

搜索为「预热 + 主查询」多请求流程（`search_notes`），会话由 `search_id` 绑定（base36 编码的 `时间戳ms<<64 | 随机数`），`search_id` 落在本地会话缓存（TTL 600s，上限 128）。

按 `(keyword, sort, note_type)` 首次命中（新建会话）时，先依次调用：
1. `POST /api/sns/web/v1/search/onebox` —— Body: `keyword`, `search_id`, `biz_type=web_search_user`, `request_id`（`"{随机}-{时间戳ms}"`）
2. `GET /api/sns/web/v1/search/filter` —— Query: `keyword`, `search_id`

主查询：

| 方法 | 路径 | 签名② | 请求参数 | 说明 |
| --- | --- | --- | --- | --- |
| `POST` | `/api/sns/web/v1/search/notes` | ① | Body: `keyword`, `page`, `page_size`, `search_id`, `sort`（`general/default` 等）, `note_type`, `ext_flags=[]`, `filters`（默认 5 组）, `geo=""`, `image_formats=["jpg","webp","avif"]` | 搜索结果，`data.items` |
| `GET` | `/api/sns/web/v1/search/recommend` | ① | Query: `keyword` | 搜索联想（首次会话的异步预取，失败忽略） |

> 默认 `filters`：
> ```json
> [{"tags": ["general"], "type": "sort_type"},
>  {"tags": ["不限"], "type": "filter_note_type"},
>  {"tags": ["不限"], "type": "filter_note_time"},
>  {"tags": ["不限"], "type": "filter_note_range"},
>  {"tags": ["不限"], "type": "filter_pos_distance"}]
> ```

### 2.4 评论（Reading / Interaction）

| 方法 | 路径 | 签名② | 请求参数 | 说明 |
| --- | --- | --- | --- | --- |
| `GET` | `/api/sns/web/v2/comment/page` | ① | Query: `note_id`, `cursor`, `top_comment_id`, `image_formats=jpg,webp,avif`, `xsec_token` | 一级评论分页（`data.comments` / `data.has_more` / `data.cursor`） |
| `GET` | `/api/sns/web/v2/comment/sub/page` | ① | Query: `note_id`, `root_comment_id`, `num=30`, `cursor` | 二级（楼中楼）评论 |
| `POST` | `/api/sns/web/v1/comment/post` | ① | Body: `note_id`, `content`, `target_comment_id`(回复时), `at_users=[]` | 发表评论 / 回复评论 |
| `POST` | `/api/sns/web/v1/comment/delete` | ① | Body: `note_id`, `comment_id` | 删除评论 |

> 评论接口需要 `xsec_token`。`xsec_token` 缺失时自动从缓存或笔记页面 meta 解析；失效时作废缓存并重新解析一次（`get_comments` 的缓存失效重试逻辑）。

### 2.5 笔记互动（Interaction）

| 方法 | 路径 | 签名② | 请求参数 | 说明 |
| --- | --- | --- | --- | --- |
| `POST` | `/api/sns/web/v1/note/like` | ① | Body: `note_oid` | 点赞笔记 |
| `POST` | `/api/sns/web/v1/note/dislike` | ① | Body: `note_oid` | 取消点赞 |
| `POST` | `/api/sns/web/v1/note/collect` | ① | Body: `note_id` | 收藏笔记 |
| `POST` | `/api/sns/web/v1/note/uncollect` | ① | Body: `note_ids` | 取消收藏 |

### 2.6 关注（Interaction）

| 方法 | 路径 | 签名② | 请求参数 | 说明 |
| --- | --- | --- | --- | --- |
| `POST` | `/api/sns/web/v1/user/follow` | ① | Body: `target_user_id` | 关注用户 |
| `POST` | `/api/sns/web/v1/user/unfollow` | ① | Body: `target_user_id` | 取消关注 |

### 2.7 二维码登录（Auth）

| 方法 | 路径 | 签名② | 请求参数 | 说明 |
| --- | --- | --- | --- | --- |
| `POST` | `/api/sns/web/v1/login/activate` | ① | Body: `{}` | 登录激活（可预先置 session cookie，失败可忽略） |
| `POST` | `/api/sns/web/v1/login/qrcode/create` | ① | Body: `qr_type=1` | 创建二维码，返回 `data.qr_id` / `data.code` / `data.url` |
| `POST` | `/api/qrcode/userinfo` | ① | Body: `qrId`, `code`；Header 覆盖: `service-tag=webcn` | 轮询扫码状态（`data.codeStatus`：1=已扫待确认，2=已确认；`data.userId`） |
| `GET` | `/api/sns/web/v1/login/qrcode/status` | ① | Query: `qr_id`, `code` | 确认后取回完整登录态（`completion_data`，含 `login_info.user_id`、`session` 等） |

> CSR 场景需要先注入自生成的 `a1` 与 `webId` cookie；登录成功后将返回的 `web_session` / `web_session_sec` 持久化。

### 2.8 创作者平台（Creator）★「仅签名 ②」

文件上传分三步：获取上传许可 → COS 直传 → 携 fileId 发布。

| 步骤 | 方法 | 路径 | 签名② | 请求参数 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 1 上传许可 | `GET` | `/api/media/v1/upload/web/permit` ★ | ② | Query: `biz_name=spectrum`, `scene=image`, `file_count=1`, `version=1`, `source=web` | 返回 `data.uploadTempPermits[0].fileIds[0]` 与 `token` |
| 2 COS 直传 | `PUT` | `https://ros-upload.xiaohongshu.com/{file_id}` | — | Headers: `X-Cos-Security-Token`(token), `Content-Type` | 直传二进制，4xx 即失败 |
| 3a 发布图笔记 | `POST` | `/web_api/sns/v2/note` | ①（覆盖 origin/referer 为 ★） | Body 见下 | 发布图文笔记 → `data.note_id` |
| 3b 话题搜索 | `POST` | `/web_api/sns/v1/search/topic` ★ | ② | Body: `suggest_topic_request={"title":"","desc":""}`, `page={"page_size":20,"page":1}`, `keyword` | 发布时选话题 |
| 发布用户搜索 | `POST` | `/web_api/sns/v1/search/user_info` ★ | ② | Body: `keyword`, `search_id`（时间戳ms字符串）, `page` | 发布时 @ 用户 |
| 删除笔记 | `POST` | `/api/galaxy/creator/note/delete` ★ | ② | Body: `note_id` | 删除笔记（Web 公开 API 可能返回 404，此时视为暂不支持） |
| 笔记列表 | `GET` | `/api/galaxy/v2/creator/note/user/posted` ★ | ② | Query: `tab=0`, `page=0` | 创作者后台已发布笔记列表 |

`POST /web_api/sns/v2/note` 请求体（图笔记）：

```json
{
  "common": {
    "type": "normal",
    "title": "标题",
    "note_id": "",
    "desc": "正文",
    "source": "{\"type\":\"web\",\"ids\":\"\",\"extraInfo\":\"{\\\"subType\\\":\\\"official\\\"}\"}",
    "business_binds": "{\"version\":1,\"noteId\":0,\"noteOrderBind\":{},\"notePostTiming\":{\"postTime\":null},\"noteCollectionBind\":{\"id\":\"\"}}",
    "ats": [],
    "hash_tag": [{"name": "话题名"}],
    "post_loc": {},
    "privacy_info": {"op_type": 1, "type": 0}
  },
  "image_info": {"images": [{"file_id": "<COS fileId>", "metadata": {"source": -1}}]},
  "video_info": null
}
```

---

## 3. 主要返回结构（`normalize_note` 归一化结果）

API 返回的笔记对象字段多样（新版本 `items[].note_card`、老版本 `items[].note`、`noteId`/`note_id`、`imageList`/`image_list`、`interactInfo`/`interact_info` 混合），业务层统一归一化为：

```json
{
  "note_id": "64abc...",
  "keyword": "考研",
  "title": "标题",
  "body": "正文",
  "topics": ["话题1", "话题2"],
  "author": "作者名",
  "author_id": "用户ID",
  "interactions": {
    "likes": 1234, "collects": 567,
    "comments": 89, "shares": 12
  },
  "media_type": "image",
  "images": [{"url": "https://sns-img-xxx.xhscdn.com/...", "seq": 0}],
  "source": "xhs-cli"
}
```

字段提取优先级（`_first` 依次取第一个非空）：
- id：`noteId` / `note_id` / `id`
- 标题：`title` / `displayTitle` / `display_title`
- 正文：`desc` / `description` / `body`
- 作者：`user.nickname` / `user.name` / `user_id`
- 点赞：`interactInfo.likedCount` / `interact_info.liked_count` / `likes`
- 图 URL：`imageList[].url` / `urlDefault` / `url_default` / `originUrl` / `origin_url`（或直接字符串）

## 4. 签名计算逻辑

小红书 Web 端存在三套签名，各自独立：

| 签名 | 输出头 | 适用域 | 算法 |
| --- | --- | --- | --- |
| 主 API XYS | `x-s`（`XYS_` 前缀）、`x-s-common`、`x-t` | edith `/api/sns/**` 非取数接口 | 144 字节载荷 → XOR → 自定义 Base64 |
| 主 API XYW | `x-s`（`XYW_` 前缀） | edith 取数接口（`user_posted`、`otherinfo` 等，自 ~2026-03 起 XYS 形式被 406） | MD5 + AES-128-CBC |
| 创作域 | `x-s`（`XYW_` 前缀）、`x-t` | creator.xiaohongshu.com | MD5 + AES-128-CBC |

### 4.1 签名通用输入

**content string** = 待签名数据（`_build_content_string`）：

- POST：`uri + 紧凑JSON(payload)`，如 `/api/sns/web/v1/comment/post` + `{"note_id":"..","content":".."}`
- GET：`uri` 拼接排序保持原序的查询串，列表值用 `,` 连接，`=` 编码为 `%3D`（其余特殊字符不编码），无参数时仅为 `uri`

再计算 **d 值**：`d = md5(content).hexdigest()`（32 位小写）。

cookie 中 **`a1`** 值（通常 52 位）是签名输入之一；`xsec_appid` 固定为 `xhs-pc-web`。

### 4.2 主 API XYS 头（GET & POST）

以 `Xhshow.sign_headers_get / sign_headers_post` 生成 5+1 个头，核心流程 `sign_xs`:

1. `uri = extract_uri(uri)`（剥掉协议/域名/查询）。
2. `content_string = _build_content_string(...)`；`d = md5(content_string)`。
3. `m_digest = d`（GET）或 `md5(uri).hexdigest()`（POST）。
4. 组装 **144 字节载荷数组**（`build_payload_array`）：
   - 版本字节 `[121, 104, 96, 41]`
   - 随机 4 字节 seed
   - 请求时间戳（毫秒，8 字节 LE）
   - 会话状态四元组：`page_load_timestamp`、`sequence_value`、`window_props_length`、`uri_length`
   - `d` 的**前 8 字节**与 `seed & 0xFF` 异或
   - `a1` 字节（52 位，不足补 `\x00`）+ 长度字节
   - `xhs-pc-web`（10 字节补零）+ 长度字节
   - 环境表异或段
   - `[2,97,51,16]` 前缀 + `a3`（`custom_hash_v2(ts_8bytes + md5_bytes)` 与 seed 异或）
5. 载荷逐字节与固定 144 字节 `HEX_KEY` 异或（`xor_transform_array`），截断前 144 字节。
6. `x3 = encode_x3(bytes)`，`encode_x3` = 标准 Base64 → 字母表替换为 `X3_BASE64_ALPHABET`（`MfgqrsbcyzPQRStuvC7mn501HIJBo2DEFTKdeNOwxWXYZap89+/A4UVLhijkl63G`）。
7. `x3 = "mns0301_" + x3_signature`（`X3_PREFIX`）。
8. 填充 `SIGNATURE_DATA_TEMPLATE`：`{"x0":"4.3.5","x1":"xhs-pc-web","x2":"macOS","x3":<上述x3>,"x4":""}`，紧凑 JSON 后 `encode()`（标准 Base64 → 字母表替换为 `CUSTOM_BASE64_ALPHABET`）。
9. `x-s = "XYS_" + <上一步结果>`。

`x-t` = 毫秒时间戳（`int(time.time()*1000)`）。

**x-s-common**（`sign_xs_common`）：
- 指纹 `fingerprint` = `FingerprintGenerator.generate(cookies, PUBLIC_USERAGENT)`（RC4 加密等）
- `b1` = 指纹子集 `x33…x52,x82` 紧凑 JSON → `ARC4(key="xhswebmplfbt")` 加密 → 自定义 Base64
- `x9 = CRC32(b1)`（JS 语义）
- 填充 `SIGNATURE_XSCOMMON_TEMPLATE`（`s0=5, x1="4.3.5", x2="macOS", x3="xhs-pc-web", x4="4.86.0", x9=<crc>, x11="normal"`），`x5=a1`，`x8=b1`
- 紧凑 JSON → 自定义 Base64（`CUSTOM_BASE64_ALPHABET`），即为 `x-s-common`。

> workbench 的 `signing.py` 覆盖了模板常量为 **macOS**：`x0="4.3.5"`（SDK_VERSION）、`x1="xhs-pc-web"`（APP_ID）、`x2="macOS"`（PLATFORM）；`SIGNATURE_XSCOMMON_TEMPLATE` 中 `xad` 等按默认。

**会话模拟（SessionManager）**：`page_load_timestamp` 在会话初始化时固定（毫秒）；每次签名前 `update_state()`，`sequence_value` 递增 0–1，`window_props_length` 递增 1–10，使连续请求的指纹演化更接近真实浏览器。

### 4.3 主 API XYW 头（取数接口）

`Xhshow.sign_xyw`：

1. `content_string` 同 4.1（GET 拼查询串 / POST 拼 body）。
2. `x1 = md5("url=" + content_string).hexdigest()`。
3. `x2 = "0|0|0|1|0|0|1|0|0|0|1|0|0|0|0|1|0|0|1"`（`XYW_ENV_FLAGS_DEFAULT`）。
4. `x4 = 毫秒时间戳`。
5. `message = "x1={x1};x2={x2};x3={a1};x4={x4};"`。
6. `plaintext = PKCS7_pad(base64(message))`。
7. AES-128-CBC 加密（`key="7cc4adla5ay0701v"`，`iv="4uzjr7mbsibcaldp"`），输出 hex。
8. 组装 `{"signSvn":"56","signType":"x2","appId":"xhs-pc-web","signVersion":"1","payload":<hex>}` 紧凑 JSON。
9. `x-s = "XYW_" + base64(json)`。

### 4.4 创作域 XYW 头（creator.xiaohongshu.com）

`sign_creator`（workbench 自有实现，非 `xhshow`）：

1. 输入串 `content`：
   - GET：`api`（如 `url=/api/galaxy/v2/creator/note/user/posted`）
   - POST：`api` + 紧凑 JSON body（如 `url=/web_api/sns/v2/note` + `{...}`）
2. `x1 = md5(content).hexdigest()`。
3. `x2 = "0|0|0|1|0|0|1|0|0|0|1|0|0|0|0|1|0|0|0"`（18 段）。
4. `x3 = a1` cookie 值；`x4 = 毫秒时间戳`。
5. `plaintext = "x1={x1};x2={x2};x3={x3};x4={x4};"` → base64 编码。
6. **AES-128-CBC** 加密（`key="7cc4adla5ay0701v"`，`iv="4uzjr7mbsibcaldp"`，PKCS7 pad），输出 **hex**。
7. 组装 `{"signSvn":"56","signType":"x2","appId":"ugc","signVersion":"1","payload":<hex>}` 紧凑 JSON。
8. `x-s = "XYW_" + base64(json)`；`x-t = str(x4)`。

> 注意：创作域与主域 XYW **key/iv/算法相同**，差异仅在 `appId`（创作域 `ugc` vs 主域 `xhs-pc-web`）与 `x2` 环境标记。

### 4.5 GET 查询串编码规则（签名与请求必须一致）

`build_get_uri` / `build_url`：
- 列表值 → `,` 连接（如 `image_scenes=FD_PRV_WEBP,FD_WM_WEBP`）。
- **只把 `=` 编码为 `%3D`**，其它字符（含 `,`）原样保留 —— 这是签名可复验的关键，禁用 `urllib.parse.urlencode`。
- `None` → 空字符串。

### 4.6 追踪 ID

- `x-b3-traceid`：16 位随机十六进制。
- `x-xray-traceid`：32 位十六进制，`part1 = ('%016x' % (ts_ms << 23 | seq))`，`seq` 随机 0~2²³-1；part2 随机。
- `x-mns = "unload"`。
- `xy-direction`：`user_id` 给定走 MurmurHash 式散列映射 1–100，否则随机 10–100。

---

## 5. Python 参考代码

### 5.1 主 API 签名包装（等价 `src/adapters/xhs/signing.py`）

```python
"""主 API 签名：直接调用 xhshow 库，保持 SessionManager 会话模拟。"""
from xhshow import CryptoConfig, SessionManager, Xhshow

SDK_VERSION = "4.3.5"
APP_ID = "xhs-pc-web"
PLATFORM = "macOS"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)

_config = CryptoConfig().with_overrides(
    PUBLIC_USERAGENT=USER_AGENT,
    SIGNATURE_DATA_TEMPLATE={
        "x0": SDK_VERSION, "x1": APP_ID, "x2": PLATFORM, "x3": "", "x4": "",
    },
    SIGNATURE_XSCOMMON_TEMPLATE={
        "s0": 5, "s1": "", "x0": "1", "x1": SDK_VERSION, "x2": PLATFORM,
        "x3": APP_ID, "x4": "4.86.0", "x5": "", "x6": "", "x7": "",
        "x8": "", "x9": -596800761, "x10": 0, "x11": "normal",
    },
)

_xhshow = Xhshow(_config)
_session = SessionManager(_config)


def sign_main_api(method, uri, cookies, params=None, payload=None, timestamp=None):
    """生成主 API 全部签名头：x-s / x-s-common / x-t / x-b3-traceid / x-xray-traceid。"""
    if method.upper() == "GET":
        return _xhshow.sign_headers_get(uri, cookies, params=params,
                                        timestamp=timestamp, session=_session)
    return _xhshow.sign_headers_post(uri, cookies, payload=payload,
                                     timestamp=timestamp, session=_session)


def build_get_uri(uri, params=None):
    """构造 GET 完整 URI（含查询串，平台专属编码）。"""
    return _xhshow.build_url(uri, params) if params else uri
```

### 5.2 创作域签名（等价 `creator_signing.py`）

```python
"""创作域签名：MD5 + AES-128-CBC，XYW_ 前缀。"""
import base64, hashlib, json, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

AES_KEY = b"7cc4adla5ay0701v"
AES_IV = b"4uzjr7mbsibcaldp"


def _aes_encrypt_hex(data: str) -> str:
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    pyld = pad(data.encode("utf-8"), AES.block_size)
    return cipher.encrypt(pyld).hex()


def sign_creator(api: str, data: dict | None, a1: str) -> dict[str, str]:
    """生成创作域签名头。api 需带 url= 前缀；data 为 POST body，GET 传 None。"""
    content = api
    if data is not None:
        content += json.dumps(data, separators=(",", ":"), ensure_ascii=False)

    x1 = hashlib.md5(content.encode("utf-8")).hexdigest()
    x2 = "0|0|0|1|0|0|1|0|0|0|1|0|0|0|0|1|0|0|0"
    x3 = a1
    x4 = int(time.time() * 1000)

    plaintext = f"x1={x1};x2={x2};x3={x3};x4={x4};"
    payload_hex = _aes_encrypt_hex(base64.b64encode(plaintext.encode("utf-8")).decode("utf-8"))

    envelope = {"signSvn": "56", "signType": "x2", "appId": "ugc",
                "signVersion": "1", "payload": payload_hex}
    xs = "XYW_" + base64.b64encode(
        json.dumps(envelope, separators=(",", ":")).encode("utf-8")).decode("utf-8")
    return {"x-s": xs, "x-t": str(x4)}
```

### 5.3 HTTP 客户端骨架（URI 请求 + 加签 + 重试，等价 `client.py`）

```python
import json, logging, random, time
from typing import Any
import httpx

from .constants import CREATOR_HOST, EDITH_HOST, HOME_URL, USER_AGENT
from .creator_signing import sign_creator
from .exceptions import (IpBlockedError, NeedVerifyError,
                         SessionExpiredError, SignatureError, XhsApiError)
from .signing import build_get_uri, sign_main_api

logger = logging.getLogger(__name__)


def cookies_to_string(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


class XhsClient:
    def __init__(self, cookies, timeout=30.0, request_delay=1.0, max_retries=3):
        self.cookies = cookies
        self._http = httpx.Client(timeout=timeout, follow_redirects=True)
        self._request_delay = request_delay
        self._base_request_delay = request_delay
        self._max_retries = max_retries
        self._last_request_time = 0.0
        self._verify_count = 0

    def close(self): self._http.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()

    def _rate_limit_delay(self):
        if self._request_delay <= 0:
            return
        elapsed = time.time() - self._last_request_time
        if elapsed < self._request_delay:
            jitter = max(0, random.gauss(0.3, 0.15))
            if random.random() < 0.05:
                jitter += random.uniform(2.0, 5.0)
            time.sleep(self._request_delay - elapsed + jitter)

    def _base_headers(self):
        return {
            "user-agent": USER_AGENT,
            "content-type": "application/json;charset=UTF-8",
            "cookie": cookies_to_string(self.cookies),
            "origin": HOME_URL,
            "referer": f"{HOME_URL}/",
            "sec-ch-ua": f'"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "dnt": "1",
            "priority": "u=1, i",
        }

    def _handle_response(self, resp: httpx.Response) -> Any:
        if resp.status_code in (461, 471):
            self._verify_count += 1
            cooldown = min(30, 5 * (2 ** (self._verify_count - 1)))
            time.sleep(cooldown)
            raise NeedVerifyError(
                verify_type=resp.headers.get("verifytype", "unknown"),
                verify_uuid=resp.headers.get("verifyuuid", "unknown"))
        self._verify_count = 0
        text = resp.text
        if not text:
            return None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            raise XhsApiError(f"Non-JSON response: {text[:200]}") from None
        if data.get("success"):
            return data.get("data", data.get("success"))
        code = data.get("code")
        if code == 300012: raise IpBlockedError()
        if code == 300015: raise SignatureError()
        if code == -100: raise SessionExpiredError()
        raise XhsApiError(f"API error: {json.dumps(data)[:300]}", code=code, response=data)

    def _request_with_retry(self, method, url, **kwargs) -> httpx.Response:
        self._rate_limit_delay()
        last_exc = None
        for attempt in range(self._max_retries):
            try:
                resp = self._http.request(method, url, **kwargs)
                if resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep((2 ** attempt) + random.uniform(0, 1)); continue
                return resp
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                time.sleep((2 ** attempt) + random.uniform(0, 1))
        if last_exc:
            raise XhsApiError(f"Request failed after retries: {last_exc}")
        raise XhsApiError("Request failed after retries")

    # ---- 主域 GET / POST（XYS/XYW 签名）----
    def _main_api_get(self, uri, params=None):
        sign_headers = sign_main_api("GET", uri, self.cookies, params=params)
        url = f"{EDITH_HOST}{build_get_uri(uri, params)}"
        resp = self._request_with_retry("GET", url, headers={**self._base_headers(), **sign_headers})
        return self._handle_response(resp)

    def _main_api_post(self, uri, data, header_overrides=None):
        sign_headers = sign_main_api("POST", uri, self.cookies, payload=data)
        url = f"{EDITH_HOST}{uri}"
        headers = {**self._base_headers(), **sign_headers}
        if header_overrides:
            headers.update(header_overrides)
        body = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        resp = self._request_with_retry("POST", url, headers=headers, content=body)
        return self._handle_response(resp)

    def _creator_host(self, uri):
        return CREATOR_HOST if uri.startswith("/api/galaxy/") else EDITH_HOST

    # ---- 创作域 GET / POST（XYW 签名）----
    def _creator_get(self, uri, params=None):
        full_uri = build_get_uri(uri, params)
        sign = sign_creator(f"url={full_uri}", None, self.cookies["a1"])
        host = self._creator_host(uri)
        headers = {**self._base_headers(),
                   "x-s": sign["x-s"], "x-t": sign["x-t"],
                   "origin": CREATOR_HOST, "referer": f"{CREATOR_HOST}/"}
        resp = self._request_with_retry("GET", f"{host}{full_uri}", headers=headers)
        return self._handle_response(resp)

    def _creator_post(self, uri, data):
        sign = sign_creator(f"url={uri}", data, self.cookies["a1"])
        host = self._creator_host(uri)
        headers = {**self._base_headers(),
                   "x-s": sign["x-s"], "x-t": sign["x-t"],
                   "origin": CREATOR_HOST, "referer": f"{CREATOR_HOST}/"}
        body = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        resp = self._request_with_retry("POST", f"{host}{uri}", headers=headers, content=body)
        return self._handle_response(resp)
```

### 5.4 主要端点示例

```python
# 取当前用户信息
me = client._main_api_get("/api/sns/web/v2/user/me")

# 取用户主页
info = client._main_api_get("/api/sns/web/v1/user/otherinfo",
                            {"target_user_id": "5d9..."})

# 取用户发布的笔记（分页）
notes = client._main_api_get("/api/sns/web/v1/user_posted",
                             {"num": 30, "cursor": "", "user_id": "5d9...",
                              "image_scenes": "FD_WM_WEBP"})
# notes["notes"] 为列表

# 搜索笔记（自动完成 search_id 会话）
result = client.search_notes("考研", page=1, page_size=20,
                             sort="general", note_type=0)
# result["items"] 为列表

# 按 ID 取笔记详情（需 xsec_token）
note = client._main_api_post("/api/sns/web/v1/feed", {
    "source_note_id": "64abc...",
    "image_formats": ["jpg", "webp", "avif"],
    "extra": {"need_body_topic": "1"},
    "xsec_source": "pc_feed",
    "xsec_token": token,
})

# 首页 feed
feed = client._main_api_post("/api/sns/web/v1/homefeed", {
    "cursor_score": "", "num": 40, "refresh_type": 1, "note_index": 0,
    "unread_begin_note_id": "", "unread_end_note_id": "",
    "unread_note_count": 0, "category": "homefeed_recommend",
    "search_key": "", "need_num": 40,
    "image_scenes": ["FD_PRV_WEBP", "FD_WM_WEBP"],
})

# 一级评论分页（需 xsec_token）
comments = client._main_api_get("/api/sns/web/v2/comment/page", {
    "note_id": "64abc...", "cursor": "", "top_comment_id": "",
    "image_formats": "jpg,webp,avif", "xsec_token": token,
})
# comments["comments"] / comments["has_more"] / comments["cursor"]

# 点赞 / 收藏 / 评论 / 关注
client._main_api_post("/api/sns/web/v1/note/like", {"note_oid": "64abc..."})
client._main_api_post("/api/sns/web/v1/note/collect", {"note_id": "64abc..."})
client._main_api_post("/api/sns/web/v1/comment/post",
                      {"note_id": "64abc...", "content": "好文", "at_users": []})
client._main_api_post("/api/sns/web/v1/user/follow", {"target_user_id": "5d9..."})

# 发布图文笔记（三步骤）
permit = client._creator_get("/api/media/v1/upload/web/permit", {
    "biz_name": "spectrum", "scene": "image", "file_count": 1,
    "version": 1, "source": "web"})
file_id, token = permit["uploadTempPermits"][0]["fileIds"][0], permit["uploadTempPermits"][0]["token"]
# PUT https://ros-upload.xiaohongshu.com/{file_id}  (Header: X-Cos-Security-Token)
new_note = client._main_api_post("/web_api/sns/v2/note", {
    "common": {"type": "normal", "title": "标题", "note_id": "",
               "desc": "正文", "source": "{}", "business_binds": "{}",
               "ats": [], "hash_tag": [], "post_loc": {},
               "privacy_info": {"op_type": 1, "type": 0}},
    "image_info": {"images": [{"file_id": file_id, "metadata": {"source": -1}}]},
    "video_info": None,
}, {"origin": CREATOR_HOST, "referer": f"{CREATOR_HOST}/"})
```

---

## 6. 常见错误码

| code | 含义 | 异常 |
| --- | --- | --- |
| `-100` | 会话过期（需重新登录） | `SessionExpiredError` |
| `300012` | IP 被风控/封禁 | `IpBlockedError` |
| `300015` | 签名校验失败（签名环境不一致/参数篡改） | `SignatureError` |
| 461 / 471（HTTP） | 触发验证码 | `NeedVerifyError`（含 `verify_type`、`verify_uuid`） |
| HTTP 406 | 接受 `XYS_` 格式签名被拒（取数接口需 `XYW_`） | `XhsApiError` |
| `unsupported_operation` | Web 公开 API 不再支持的操作 | `UnsupportedOperationError` |
| 缺 cookie | 缺少 `a1` / `web_session` | `NoCookieError` / `CookieError` |

---

## 7. Cookie 与登录态

- **必需 cookie**：`a1`（签名输入）、`web_session`（稳定登录态）。完整导入集合还含 `webId`、`web_session_sec`、`id_token`、`websectiga`、`sec_poison_id`、`xsecappid`、`gid`、`abRequestId`、`webBuild`、`loadts`。
- **TTL**：cookie 超过 7 天自动尝试从本机浏览器刷新。
- **`a1` 生成**：`ts_hex + 30位随机(a-z0-9) + "5" + "0" + "000" + crc32`，截取 52 位。
- **`webId` 生成**：`md5(a1)`，32 位 hex。
- **note-xsec 缓存**：`TOKEN_CACHE_FILE` 保存 `note_id → {xsec_token, source, ts}`，LRU 上限 500、TTL 86400s。