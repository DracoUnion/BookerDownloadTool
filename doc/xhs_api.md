# 小红书 Android 客户端 API 接口与签名机制

> 分析对象：`xiaohongshu.apk`（com.xingin.xhs，小红书 Android 客户端）
> 反编译工具：jadx 1.5.6，APK 共 124893 个类（classes*.dex 全部解出），主包 `com.xingin.*`
> 分析方式：扫描所有含 `@jce.*` HTTP 注解的 Service 接口定义，提取方法、路径、请求参数；并结合拦截器链与 `com.xingin.shield` / `com.xingin.tiny` 安全 SDK 源码重建签名机制
> 结果统计：**3040** 个去重后的 HTTP 接口（GET 1434 / POST 1522 / PUT 46 / DELETE 38），`/api/sns` 为核心业务域

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

### 域名 `ad-splash.xiaohongshu.com`

#### `api`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `https://ad-splash.xiaohongshu.com/api/v2/splash/debug` | Query: ads_id, preview_info | AdsDebugServers |

### 域名 `edith.xiaohongshu.com`

#### `CARD_UPDATE_STATUS_PATH`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `CARD_UPDATE_STATUS_PATH` | Body: java.util.Map<java.lang.String, java.lang.Object> map, kotlin.coroutines.Continuation<java.lang.Object> | SchemaCardUpdateService |

#### `ads`（9 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/ads/api/thirdparty/nature/collect` | Body: sw.f | GameCommonitorApiService |
| `POST` | `/api/ads/brand/liveinfo` | Field: ads_id, track_id, preview_live_state | SplashAdsItemServices |
| `POST` | `/api/ads/brand/splash_related_info` | Field: ads_id, track_id, preview_live_state, preview_info | SplashAdsNoteInfoServices |
| `POST` | `/api/ads/material/guide` | Query: ads_uuid, track_id, user_id, request_type | UserServices |
| `POST` | `ads/api/clue/collect/pre/fill/info` | Body: mx.b1 | LeadGenerationService |
| `POST` | `ads/api/clue/collect/pre/fill/info` | Body: mx.a1 | LeadGenerationService |
| `POST` | `ads/api/clue/service_card/send/code` | Body: mx.c1 | LeadGenerationService |
| `POST` | `ads/api/clue/service_card/submit` | Body: mx.l0 | LeadGenerationService |
| `POST` | `api/ads/v1/alliance/forward` |  | AdsOpenAppRedirectService |

#### `app`（4 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `api/app/live/commerce/v1/settings` | Query: host_id, room_id | AlphaGoodsLiveMallService |
| `POST` | `/api/app/buyer/wish/reply_msg` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS, brand_wish_id, brand_wish_recordId | IMService |
| `POST` | `/api/app/state/subsidies/qualification/operation` | Body: com.google.gson.l | PayApiService |
| `POST` | `api/app/live/commerce/v1/settings` | Body: pz0.f1 | AlphaGoodsLiveMallService |

#### `app_api`（8 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/app_api/edith/redapp/cs/ticket/detail/v2` | Query: ticketNumber, visualRange, sourceType | BCIMTicketService |
| `GET` | `/app_api/edith/redapp/cs/ticket/progress/reddot` | Query: sid; Header: authorization | ChatDetailApiService |
| `GET` | `/app_api/edith/wallet/redcoin/my_coins` |  | AlphaAmountServiceV2 |
| `GET` | `/app_api/edith/wallet/redcoin/top_up/create_top_up_order` | Query: item_id | AlphaAmountServiceV2 |
| `GET` | `/app_api/edith/wallet/redcoin/top_up/create_top_up_order` | Query: item_id, com.xingin.entities.BaseTagBean.TYPE_PRICE | AlphaAmountServiceV2 |
| `GET` | `/app_api/edith/wallet/redcoin/top_up/transaction/{transaction_id}` | Path: transaction_id | AlphaAmountServiceV2 |
| `GET` | `/app_api/edith/wallet/redcoin/top_up/transaction/{transaction_id}` | Path: transaction_id | AlphaAmountServiceV2 |
| `POST` | `/app_api/edith/ticket/urge` | Body: adc.m | BCIMTicketService |

#### `boost`（2 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/boost/note/publish/translate` | Body: okhttp3.RequestBody | NoteService |
| `POST` | `/api/boost/note/publish/translate` | Body: okhttp3.RequestBody | NoteDetailService |

#### `c2cbusiness`（11 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/c2cbusiness/product/delete_c2c_product` | Field: itemId | ProGoodsDetailService |
| `POST` | `/api/c2cbusiness/product/multi_goods/business_bind/prepare` | Body: b1b.u1 | C2CNoteBusinessBindProcessService |
| `POST` | `/api/c2cbusiness/product/used_note_item/create` | Body: b1b.o3 | C2CUsedNoteItemService |
| `POST` | `/api/c2cbusiness/product/used_note_item/render` | Body: b1b.d3 | C2CUsedNoteItemService |
| `POST` | `/api/c2cbusiness/product/used_note_item/update` | Body: b1b.p4 | C2CUsedNoteItemService |
| `POST` | `/api/c2cbusiness/seller/precheck_c2c_core_condition` |  | C2CSellerPrecheckService |
| `POST` | `/api/c2cbusiness/trade/cc` | Body: xz5.q2; Header: x-ratelimit-meta, rn-name, rn-version | IC2CPayApi |
| `POST` | `api/c2cbusiness/chat/consult` | Field: scene, note_id, item_id | C2CImService |
| `POST` | `api/c2cbusiness/imcard/common/send` | Field: request_param, type, channel_type, sender_id, receiver_id | C2CImService |
| `POST` | `api/c2cbusiness/live/room/item/list/clear` | Field: user_id, room_id | AlphaConfigEdithLiveGoService |
| `POST` | `api/c2cbusiness/portfolio/work/card/create/v2` | Field: portfolioId, portfolioWorkId, targetUserId, fromScene | C2CImService |

#### `capa`（4 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/capa/configlist` | Query: config | CapaConfigService |
| `GET` | `/api/capa/configlist` | Query: config | CapaApi |
| `GET` | `/api/capa/goods/ai_detect_picture` | Query: user_id, pic_file_ids | CapaAiImageService |
| `GET` | `/api/capa/goods/ai_detect_picture` | Query: user_id, pic_file_ids | CapaApi |

#### `cs`（79 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/api/cs/v3/chat/{chatId}/notes/{noteId}` | Path: chatId, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_NOTE_ID; Query: sid; Header: authorization | ChatDetailApiService |
| `DELETE` | `/api/cs/v3/chat/{chatId}/participants/{userId}` | Path: chatId, userId; Query: sid; Header: authorization | ChatDetailApiService |
| `DELETE` | `/api/cs/v3/message/{messageId}/package/v2` | Path: messageId; Query: package_id, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/chat/platform/agent_quick_intent/config` | Query: service_agent_id, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v2/faq/message` | Query: faq_id, seller_id, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v2/images/tokens` | Query: sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/active/chat/degrade` | Query: sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/cases/{caseId}/feedback` | Path: caseId; Query: sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/chat/degrade` | Query: sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/chat/templates` | Query: chat_type, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/chat/{chatId}/detail` | Path: chatId; Query: include_participants, include_statistics, include_settings, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/chat/{chatId}/info` | Path: chatId; Query: sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/chat/{chatId}/message/statistics` | Path: chatId; Query: start_time, end_time, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/chat/{chatId}/notes` | Path: chatId; Query: sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/chat/{chatId}/participants` | Path: chatId; Query: page, page_size, include_online_status, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/chat/{chatId}/permissions` | Path: chatId; Query: user_id, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/chat/{chatId}/search` | Path: chatId; Query: keyword, message_type, start_time, end_time, page, page_size, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/chat/{chatId}/statistics` | Path: chatId; Query: time_range_days, statistics_type, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/chat/{chatId}/tags` | Path: chatId; Query: sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/chat/{imChatId}/chat_info` | Path: imChatId; Query: sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/entry/basic-info` | Query: seller_id, entryId, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/export/task/{taskId}/status` | Path: taskId; Query: sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/feedback/config` | Query: skill_id, im_chat_id, version, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/generate_redirect_link` | Query: locationCode | OrderDetailService |
| `GET` | `/api/cs/v3/goods-v3/goods/message` | Query: new_sku_id, goods_recommend_channel, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/inquiry/question` | Query: entry_id, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/intent_feedback` | Query: message_ids, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/judge/active/seller` | Query: sellerId, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/judge/feedback` | Query: chatId, sourceOfQuestionnaire, version, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/merchant/degrade` | Query: sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/note-info` | Query: note_id, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/note-info` | Query: note_id | NotePreviewBarService |
| `GET` | `/api/cs/v3/quick-intent` | Query: seller_id, goods_id, entry, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/seller/consult/config` | Query: seller_id, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/seller/csa/status_desc` | Query: seller_id, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/seller/{sellerId}/messages` | Path: sellerId; Query: limit, before_message_id, _, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/serviceagent/{sellerId}/chat` | Path: sellerId; Query: sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/smart-hint` | Query: keyword, chatId, imToken, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/cs/v3/tools/package/{packageId}/detail` | Path: packageId; Query: sid; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/bcim/urge/aftersale/user/msg` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.String>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/biz_frequency/check` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/modifyaddress/failentry` | Body: com.xingin.trade_bcim.ui.page.service.ModifyAddressFailEntryRequest modifyAddressFailEntryRequest, kotlin.coroutines.Continuation<? super com.xingin.trade_bcim.ui.page.service.ModifyAddressFailEntryResponse> | ModifyAddressFailEntryService |
| `POST` | `/api/cs/send/spu/msg` | Body: com.xingin.trade_bcim.ui.page.service.SmartGuideSpuMessageRequest smartGuideSpuMessageRequest, kotlin.coroutines.Continuation<? super com.xingin.trade_bcim.ui.page.service.SmartGuideSpuMessageResponse> | SmartGuideSpuMessageService |
| `POST` | `/api/cs/template/message/refresh` | Body: java.util.Map<java.lang.String, java.lang.String> map, kotlin.coroutines.Continuation<java.lang.Object> | SchemaRefreshService |
| `POST` | `/api/cs/v2/chats` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v2/chats/{chatId}/messages` | Path: chatId; Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v2/seller/{sellerId}/assistant/messages` | Path: sellerId; Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/c/clear/red/dot` | Body: java.util.Map<java.lang.String, java.lang.Object> map, kotlin.coroutines.Continuation<? super retrofit2.a<java.lang.String>> | ChatEdithApiClient |
| `POST` | `/api/cs/v3/c/clear/red/dot` | Query: sid; Body: com.xingin.trade_bcim.model.ClearAllUnreadCountRequest; Header: authorization | XYBCIMSessionApiService |
| `POST` | `/api/cs/v3/chat/close` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/chat/message/hide` | Body: mcc.k0 | EvaluateFeedbackService |
| `POST` | `/api/cs/v3/chat/{chatId}/apply-template` | Path: chatId; Query: sid; Body: java.util.Map<java.lang.String, ? extends java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/chat/{chatId}/clear` | Path: chatId; Query: sid; Body: com.xingin.trade_bcim.model.ClearChatHistoryRequest; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/chat/{chatId}/export` | Path: chatId; Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/chat/{chatId}/notes` | Path: chatId; Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/chat/{chatId}/participants` | Path: chatId; Query: sid; Body: com.xingin.trade_bcim.model.AddChatParticipantRequest; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/chats/{chatId}/enqueue` | Path: chatId; Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/chats/{chatId}/transfer` | Path: chatId; Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/check_overseas` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/close-chat` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/feedback` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/feedback` | Body: mcc.i0 | EvaluateFeedbackService |
| `POST` | `/api/cs/v3/get/msg/feedback` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/intent_feedback` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/mcs/get_customer_im_chat_config` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/mcs/save_im_chat_black_list` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/message/feedback` | Body: icc.y | IsvMessageFeedbackService |
| `POST` | `/api/cs/v3/quick-intent/v2` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/save/msg/feedback` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/sku/list` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/cs/v3/tools/coupon/info` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `PUT` | `/api/cs/v3/cases/{caseId}/feedback` | Path: caseId; Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `PUT` | `/api/cs/v3/chat/{chatId}/archive` | Path: chatId; Query: sid; Header: authorization | ChatDetailApiService |
| `PUT` | `/api/cs/v3/chat/{chatId}/background` | Path: chatId; Query: sid; Body: com.xingin.trade_bcim.model.SetChatBackgroundRequest; Header: authorization | ChatDetailApiService |
| `PUT` | `/api/cs/v3/chat/{chatId}/notes/{noteId}` | Path: chatId, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_NOTE_ID; Query: sid; Body: java.util.Map<java.lang.String, ? extends java.lang.Object>; Header: authorization | ChatDetailApiService |
| `PUT` | `/api/cs/v3/chat/{chatId}/permissions/{userId}` | Path: chatId, userId; Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `PUT` | `/api/cs/v3/chat/{chatId}/restore` | Path: chatId; Query: sid; Header: authorization | ChatDetailApiService |
| `PUT` | `/api/cs/v3/chat/{chatId}/settings` | Path: chatId; Query: sid; Body: com.xingin.trade_bcim.model.UpdateChatSettingsRequest; Header: authorization | ChatDetailApiService |
| `PUT` | `/api/cs/v3/chat/{chatId}/tags` | Path: chatId; Query: sid; Body: java.util.Map<java.lang.String, ? extends java.lang.Object>; Header: authorization | ChatDetailApiService |

#### `curation`（6 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/curation/batch_add` | Body: com.google.gson.l | KingStoreService |
| `POST` | `/curation/batch_remove` | Body: com.google.gson.l | KingStoreService |
| `POST` | `/curation/category_list` | Body: dy1.c | KingStoreService |
| `POST` | `/curation/create_category` | Body: dy1.a | KingStoreService |
| `POST` | `/curation/edit_category` | Body: dy1.b | KingStoreService |
| `POST` | `/curation/update_custom_config` | Body: com.google.gson.l | KingStoreService |

#### `distribution`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/distribution/trace/ds_token/resolve/v2` | Field: com.xingin.capa.feature_model.session.EditableVideo2.VIDEO_ENTRANCE_DEEPLINK, event_trace_id, trigger_time, trigger_from | DistributionApi |

#### `edith`（78 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/edith/ads/social/business_card/list` |  | IMAcquisitionToolService |
| `GET` | `/api/edith/ads/social/jssdk/code-package` | Query: codePackageId, bUserId | AdsJssdkService |
| `GET` | `/api/edith/ads/social/jssdk/page` | Query: pageId, bUserId | AdsJssdkService |
| `GET` | `/api/edith/ads/social/jssdk/page/tool_info` | Query: pageId, bUserId | AdsJssdkService |
| `GET` | `/api/edith/ads/social/lead-card/ext/cascade` | Query: cardId, bUserId | PickerService |
| `GET` | `/api/edith/ads/social/lead-card/ext/city` | Query: cardId, bUserId | PickerService |
| `GET` | `/api/edith/ads/social/live/card/bind/list` | Query: roomId | AudienceLeadsService |
| `GET` | `/api/edith/ads/social/live/card/pop/info` | Query: roomId | AudienceLeadsService |
| `GET` | `/api/edith/ads/social/live/clue/submit/status` | Query: cardId, roomId | AudienceLeadsService |
| `GET` | `/api/edith/ads/social/live/ug/card/pop/info` | Query: roomId | AudienceUgService |
| `GET` | `/api/edith/ads/social/live/ug/card/pop/info` | Query: roomId | HostUgService |
| `GET` | `/api/edith/ads/social/page_card/list` | Query: page_num, page_size | IMAcquisitionToolService |
| `GET` | `/api/edith/ads/social/service_card/list` | Query: page_num, page_size | IMAcquisitionToolService |
| `GET` | `/api/edith/ads/social/trade/budget` |  | IMAcquisitionToolService |
| `GET` | `/api/edith/ads/social/trade_card/list` | Query: page_num, page_size | IMAcquisitionToolService |
| `GET` | `/api/edith/buyer_content_no_login` | Query: sku_id, address_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, anchor_id, trade_ext, com.alipay.ams.component.sdk.InternalConfigKeys.ADDRESS_ELEMENT_MODE, auto_refresh, ext_query | GoodsDetailVisionService |
| `GET` | `/api/edith/cs/chat/seller-info` | Query: seller_id, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/edith/cs/chats/user_info` | Query: sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/edith/cs/message/compensate/coupon/content` | Query: couponId, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/edith/cs/message/compensate/entry/content` | Query: packageId, messageId, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/edith/cs/pre-order/message-card/click` | Query: pre_order_id, link | MsgServices |
| `GET` | `/api/edith/cs/questionnaire/chat/feedback` | Query: chatId, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/edith/cs/seller-info/conditional` | Query: seller_id, entry, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/edith/cs/seller/online/status` | Query: sellerId, sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/edith/cs/sns/grey` | Query: currentUserId, viewUserId, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | MsgServices |
| `GET` | `/api/edith/live/commerce/app/check_host_is_gray` | Query: host_id, gray_enum | AlphaGoodsLiveMallService |
| `GET` | `/api/edith/live/commerce/app/get_act_type_list_by_tab_type` | Query: tab_type, host_id | AlphaGoodsLiveMallService |
| `GET` | `/api/edith/live/commerce/app/query_anchor_live_room_goods` | Query: host_id, page, page_size, with_goods | AlphaGoodsLiveMallService |
| `GET` | `/api/edith/live/commerce/app/query_live_room_goods_detail` | Query: host_id, room_id, category_id, current_room_id, act_type_list | AlphaGoodsLiveMallService |
| `GET` | `/api/edith/micro_extra` | Query: trade_ext | GoodsDetailService |
| `GET` | `/edith/api/store/aigc-publish/attribute` | Query: item_id, sku_id | AIGCNoteGeneratorService |
| `GET` | `/edith/api/store/bridge/goods-tab/popup` |  | GoodsNoteModel |
| `GET` | `/edith/api/store/bridge/note_related_goods` | Query: note_id, note_type | INnsRelatedNoteService |
| `GET` | `/edith/api/store/bridge/same-goods-note` | Query: goods_id, goods_seller_type, page_num, page_size, with_detail | SimilarNotesRepo |
| `GET` | `api/edith/ads/social/explore_card/rn_info` | Query: cardId, senderId, receiveId, messageId, isAuto | ExploreCardRnInfoService |
| `GET` | `api/edith/ads/social/live/card/pop/info` | Query: roomId | AdsLiveHostService |
| `GET` | `api/edith/ads/social/live/card/pop/info` | Query: roomId | AdsLiveHostService |
| `GET` | `api/edith/ads/social/live/card/tob/bind/list` | Query: roomId, cardType | AdsLiveHostService |
| `GET` | `api/edith/ads/social/live/clue/auth/check` |  | AdsLiveHostService |
| `POST` | `/api/edith/ads/social/im/appraise` | Field: appraiseId, receiver, score | EvaluateCardApiService |
| `POST` | `/api/edith/ads/social/invert/event` | Body: com.xingin.ads.jssdk.container.service.a.b | AdsJssdkService |
| `POST` | `/api/edith/ads/social/invert/event` | Body: dx.a | CardEventService |
| `POST` | `/api/edith/ads/social/jssdk/code-package/validate` | Body: com.xingin.ads.jssdk.container.service.c | AdsJssdkService |
| `POST` | `/api/edith/ads/social/live/report` | Body: m10.i | AudienceLeadsService |
| `POST` | `/api/edith/ads/social/live/ug/card/bind` | Body: l50.b | HostUgService |
| `POST` | `/api/edith/ads/social/live/ug/card/operate` | Body: l50.d | HostUgService |
| `POST` | `/api/edith/ads/social/live/ug/report` | Body: h50.g | AudienceUgService |
| `POST` | `/api/edith/ads/social/send_message` | Body: com.xingin.advert.adscard.ConsultMessageSend | ConsultApiService |
| `POST` | `/api/edith/ads/social/social_card/connect` | Body: com.xingin.advert.adscard.ConsultInfoRequest | ConsultApiService |
| `POST` | `/api/edith/ads/social/social_card/wecom_check_and_fallback` | Body: zu.l0 | WecomLinkService |
| `POST` | `/api/edith/ads/social/social_card/wecom_link_status_check` | Body: zu.l0 | WecomLinkService |
| `POST` | `/api/edith/ads/social/trade_card/get_card_link` | Body: gy.g | TradingCardLinkService |
| `POST` | `/api/edith/ads/social/xiaomi/ur/generate` | Field: app_id | XiaoMiDeeplinkHandler |
| `POST` | `/api/edith/cs/chats/enqueue` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/edith/cs/note/share` | Field: seller_id, note_id, text | MsgServices |
| `POST` | `/api/edith/cs/questionnaire/chat/submit` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/edith/cs/robot/chat/transfer` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/edith/cs/seller/no/order/anchor` | Body: java.util.Map<java.lang.String, java.lang.String> map, kotlin.coroutines.Continuation<java.lang.Object> | BCIMNoOrderAnchorService |
| `POST` | `/api/edith/live/commerce/app/live/plan/goods/expect/sale/amount/upsert` | Body: pz0.f2 | AlphaGoodsLiveMallService |
| `POST` | `/edith/api/store/aigc-publish/ai/content` | Body: tw5.a | AIGCNoteGeneratorService |
| `POST` | `/edith/api/store/aigc-publish/ai/regenerate_image` | Body: tw5.b | AIGCNoteGeneratorService |
| `POST` | `/edith/api/store/aigc-publish/regenerate_text` | Body: tw5.c | AIGCNoteGeneratorService |
| `POST` | `/edith/api/store/bridge/goods_list` | Field: keyword, page_num, page_size, tab_type, goods_option_type, order_column, order_asc, goods_id_for_memory | GoodsNoteModel |
| `POST` | `/edith/api/store/trigger_privilege` | Body: com.xingin.commercial.goodsdetail.entities.o1 | GoodsDetailService |
| `POST` | `api/edith/ads/social/lead-card/ext/rn/info` | Body: mx.g0 | LeadGenerationService |
| `POST` | `api/edith/ads/social/live/card/bind` | Body: u10.a | AdsLiveHostService |
| `POST` | `api/edith/ads/social/live/card/bind/manage` | Body: u10.k | AdsLiveHostService |
| `POST` | `api/edith/ads/social/live/card/bind/manage` | Body: u10.k | AdsLiveHostService |
| `POST` | `api/edith/ads/social/live/card/list` | Body: u10.c | AdsLiveHostService |
| `POST` | `api/edith/ads/social/live/card/operate` | Body: u10.e | AdsLiveHostService |
| `POST` | `api/edith/live/commerce/app/live/center/goods/pre/sale/release` | Field: host_id, item_id | AlphaGoodsLiveMallService |
| `PUT` | `/api/edith/cs/chat/sticky` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `PUT` | `/api/edith/cs/chat/sticky` | Body: java.util.Map<java.lang.String, java.lang.Object> map, kotlin.coroutines.Continuation<? super retrofit2.a<java.lang.String>> | ChatEdithApiClient |
| `PUT` | `/api/edith/cs/chat/sticky` | Query: sid; Body: com.xingin.trade_bcim.model.SetPlatformChatStickyRequest; Header: authorization | XYBCIMSessionApiService |
| `PUT` | `/api/edith/cs/impaas/chat/disturb` | Body: java.util.Map<java.lang.String, java.lang.Object> map, kotlin.coroutines.Continuation<? super retrofit2.a<java.lang.String>> | ChatEdithApiClient |
| `PUT` | `/api/edith/cs/impaas/chat/disturb` | Query: sid; Body: com.xingin.trade_bcim.model.SetMerchantChatDisturbRequest; Header: authorization | XYBCIMSessionApiService |
| `PUT` | `/api/edith/cs/impaas/chat/sticky` | Body: java.util.Map<java.lang.String, java.lang.Object> map, kotlin.coroutines.Continuation<? super retrofit2.a<java.lang.String>> | ChatEdithApiClient |
| `PUT` | `/api/edith/cs/impaas/chat/sticky` | Query: sid; Body: com.xingin.trade_bcim.model.SetMerchantChatStickyRequest; Header: authorization | XYBCIMSessionApiService |

#### `eva`（7 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/eva/cs/dim/box/grey` |  | ChatEdithApiClient |
| `GET` | `/api/eva/cs/v1/chat/seller/info` | Query: sellerId, sid; Header: authorization | ChatDetailApiService |
| `POST` | `/api/eva/csflow/keep_queue` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/eva/customer_close_chat` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/eva/get/cs/token` | Body: java.util.Map<java.lang.String, java.lang.Object> map, kotlin.coroutines.Continuation<? super java.lang.String> | ChatEdithApiClient |
| `POST` | `/api/eva/submit/leave/message` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/eva/submit/leave/message` | Body: com.xingin.trade_bcim.ui.page.service.QueueLeaveMessageRequest queueLeaveMessageRequest, kotlin.coroutines.Continuation<? super java.util.Map<java.lang.String, ? extends java.lang.Object>> | QueueLeaveMessageService |

#### `finance`（7 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/finance/redcoin/coin/cashier` | Query: pay_scene, channel | PayServices |
| `GET` | `/api/finance/redcoin/top_up/transaction` | Query: item_id, com.xingin.entities.BaseTagBean.TYPE_PRICE | SketchPayService |
| `GET` | `/api/finance/redcoin/top_up/transaction/{transaction_id}` | Path: transaction_id | SketchPayService |
| `GET` | `api/finance/redcoin/top_up/items` | Query: business | AlphaLiveClassService |
| `GET` | `api/finance/redcoin/top_up/transaction` | Query: item_id | AlphaLiveClassService |
| `GET` | `api/finance/redcoin/top_up/transaction` | Query: item_id, com.xingin.entities.BaseTagBean.TYPE_PRICE | ShoppingRedPacketJarvisService |
| `GET` | `api/finance/redcoin/top_up/transaction/{transaction_id}` | Path: transaction_id | AlphaLiveClassService |

#### `fls`（4 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/fls/red/merchant/require/questionnaire` | Query: imChatId, version, sid; Header: authorization | ChatDetailApiService |
| `POST` | `/api/fls/red/merchant/submit/questionnaire` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/fls/red/urge/shipment/push/mock/message` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/fls/v2/chat/{chatId}/questionnaire` | Path: chatId; Query: sid; Header: authorization | ChatDetailApiService |

#### `friends`（5 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/friends/friends_explore/top_entry` |  | FollowExploreRecommendService |
| `GET` | `/api/friends/friends_explore/top_entry` |  | FollowExploreRecommendService |
| `GET` | `/api/friends/v1/info/extra` | Query: user_id_list | UserServices |
| `GET` | `/api/friends/v1/info/self` | Query: cursor | UserServices |
| `GET` | `api/friends/friends_explore/banner` |  | UserServices |

#### `game`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/game/subscribe` | Body: sw.l | GameSubscribeApiService |

#### `growth`（26 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/growth/feeds/oppo/featured_note` |  | DonationService |
| `GET` | `/api/growth/mozart/config/query_list` | Query: type, customIds, param | RedBoxService |
| `GET` | `/api/growth/v1/widget/travel` |  | WidgetServices |
| `GET` | `/api/growth/v1/widget/zhuiguang` |  | WidgetServices |
| `GET` | `/growth/cny2026/access` |  | GrowthCnyServices |
| `GET` | `/growth/rpas/fairydasktop` |  | WidgetServices |
| `POST` | `/api/growth/activity/gift_for_new_user/do_action_v2` | Field: actionCode | RedBoxService |
| `POST` | `/api/growth/activity/gift_for_new_user/do_action_v2` | Field: actionCode, paramsMap | RedBoxService |
| `POST` | `/api/growth/activity/gift_for_new_user/no_login_do_action` | Field: actionCode | RedBoxService |
| `POST` | `/api/growth/activity/gift_for_new_user/no_login_do_action` | Field: actionCode | RedBoxService |
| `POST` | `/api/growth/beethoven/action` | Body: vf8.b | IncentiveApiService |
| `POST` | `/api/growth/beethoven/nuc_browse_report` | Body: vf8.b | IncentiveApiService |
| `POST` | `/api/growth/beethoven/nuc_reach_decide` | Body: vf8.e | IncentiveApiService |
| `POST` | `/api/growth/beethoven/query` | Body: td6.e | BeethovenApiService |
| `POST` | `/api/growth/schubert/board/config` | Field: userShareAction, businessNameSet, stage, locale | ShareService |
| `POST` | `/api/growth/schubert/protected/create` | Query: biz, url | DotsApi |
| `POST` | `/api/growth/schubert/protected/create` | Query: biz, url | SearchAgentPageApi |
| `POST` | `/api/growth/schubert/share/content` | Body: w97.i | ShareService |
| `POST` | `/api/growth/schubert/share/downgrade` | Field: bussinessName, shareCommonData, allShareInfoList | ShareService |
| `POST` | `/api/growth/schubert/share/dp_pull_report` | Body: kod.f | DeepLinkService |
| `POST` | `/api/growth/schubert/share_guide/info` | Body: t1c.l | ShareGuideService |
| `POST` | `/api/growth/schubert/share_guide/report` | Body: t1c.m | ShareGuideService |
| `POST` | `/api/growth/schubert/shorturl/get_long_url` | Body: k86.g | EventService |
| `POST` | `/api/growth/schubert/shorturl/get_long_url` | Body: lod.b | DeepLinkService |
| `POST` | `/api/growth/trace/context` | Field: traceId, context | ShareService |
| `POST` | `/api/growth/userevaluate/notemark` | Body: nh7.q | ContentRatingApiService |

#### `guts-xhs`（17 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/guts-xhs/api/v1/chat/message/delete` | Body: com.xingin.diandian.bean.RequestDeleteBean requestDeleteBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<java.lang.String>> | ChatService |
| `POST` | `/guts-xhs/api/v1/chat/message/source` | Body: com.xingin.diandian.bean.RequestMessageSource requestMessageSource, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<com.xingin.diandian.bean.MessageSourceBean>> | ChatService |
| `POST` | `/guts-xhs/api/v1/chat/topic/delete` | Body: com.xingin.diandian.bean.RequestDeleteTopic requestDeleteTopic, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<com.xingin.diandian.bean.DeleteTopicBean>> | ChatService |
| `POST` | `/guts-xhs/api/v1/chat/topic/list` | Body: com.xingin.diandian.bean.RequestTopicListBean requestTopicListBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<com.xingin.diandian.bean.TopicListBean>> | ChatService |
| `POST` | `/guts-xhs/api/v1/chat/topic/message` | Body: com.xingin.diandian.bean.RequestTopicMessageBean requestTopicMessageBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<com.xingin.diandian.bean.HistoryBean>> | ChatService |
| `POST` | `/guts-xhs/api/v1/file/decrypt` | Body: com.xingin.diandian.bean.RequestFileIdExchangeBean requestFileIdExchangeBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<java.util.Map<java.lang.String, com.xingin.diandian.bean.RealFillIdBean>>> | ChatService |
| `POST` | `/guts-xhs/api/v1/link/analysis` | Body: com.xingin.diandian.bean.RequestLinkAnalysisBean requestLinkAnalysisBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<com.xingin.diandian.bean.LinkAnalysisData>> | ChatService |
| `POST` | `/guts-xhs/api/v1/onboarding/welcome_query` | Body: com.xingin.diandian.bean.WelcomeQueryReqBean welcomeQueryReqBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<com.xingin.diandian.bean.WelcomeQueryBean>> | ChatService |
| `POST` | `/guts-xhs/api/v1/share/create` | Body: com.xingin.diandian.bean.RequestShareBean requestShareBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<com.xingin.diandian.bean.ShareUrlBean>> | ChatService |
| `POST` | `/guts-xhs/api/v1/share/picture` | Body: com.xingin.diandian.bean.RequestSharePictureBean requestSharePictureBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<com.xingin.diandian.bean.SharePictureBean>> | ChatService |
| `POST` | `/guts-xhs/api/v1/sug/create` | Body: com.xingin.diandian.bean.RequestSugWord requestSugWord, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<com.xingin.diandian.bean.SugBean>> | ChatService |
| `POST` | `/guts-xhs/api/v1/sug/create` | Body: com.xingin.dots.legacy.network.entities.recommend.DotsSugRequest | DotsApi |
| `POST` | `/guts-xhs/api/v1/user/ban/query` |  | ChatService |
| `POST` | `/guts-xhs/api/v1/user/profile/detail` |  | ChatService |
| `POST` | `/guts-xhs/api/v1/user/profile/update` | Body: com.xingin.diandian.bean.ModifyProfileBean modifyProfileBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<com.xingin.diandian.bean.ProfileBean>> | ChatService |
| `POST` | `guts-xhs/api/v1/chat/history/list` | Body: com.xingin.diandian.bean.RequestHistoryBean requestHistoryBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<com.xingin.diandian.bean.HistoryBean>> | ChatService |
| `POST` | `guts-xhs/api/v1/location/user` |  | ChatService |

#### `happy`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/happy/v1/get_cap` | Query: count | SecurityMetricsService |

#### `hawking`（2 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/hawking/leads/info` | Query: note_id | LeadsModel |
| `GET` | `api/hawking/native_land/info` | Query: page_id | CanvasApiService |

#### `im`（314 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/api/im/chat_widget` | Query: chat_user_id, type | ChatSettingService |
| `DELETE` | `/api/im/emoji/bg` | Query: chat_user_id | ChatEmojiBgService |
| `DELETE` | `/api/im/red/group/dismiss` | Query: group_id | MsgServices |
| `DELETE` | `/api/im/red/group/quit` | Query: group_id | MsgServices |
| `DELETE` | `/api/im/v1/group/dismiss` | Query: group_id | MsgServices |
| `DELETE` | `/api/im/v1/group/quit` | Query: group_id | MsgServices |
| `DELETE` | `/api/im/v1/users/blocked-users/{user_id}` | Path: user_id | MsgServices |
| `DELETE` | `api/im/v1/users/muted-users/{user_id}` | Path: user_id | MsgServices |
| `GET` | `/api/im/chat/dynamic/info` | Query: target_id, chat_type | MsgServices |
| `GET` | `/api/im/chat/get_unread` |  | MsgUnreadService |
| `GET` | `/api/im/chat_bottom/reply` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | MsgServices |
| `GET` | `/api/im/chat_medal/detail_page` | Query: target_user_id | MsgServices |
| `GET` | `/api/im/chat_medal/share_info` | Query: target_user_id, level | ShareService |
| `GET` | `/api/im/chat_medal/widget` | Query: target_user_id | ChatWidgetsGuideServices |
| `GET` | `/api/im/chat_widget/checkin/plan/entries` | Query: chat_type, target_id | CheckInService |
| `GET` | `/api/im/chat_widget/checkin/plan/entry` | Query: chat_type, target_id, plan_id | CheckInService |
| `GET` | `/api/im/chat_widget/checkin/plan/plus_check` | Query: chat_type, target_id | MsgServices |
| `GET` | `/api/im/chat_widget/list` | Query: chat_user_id | ChatSettingService |
| `GET` | `/api/im/chat_widget/sticky_note/detail` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | StickyNoteApi |
| `GET` | `/api/im/chat_widget/sticky_post/feeds` | Query: chat_user_id, size, last_id | StickyNoteApi |
| `GET` | `/api/im/chats/group` | Query: limit, page, complete, next_ts | MsgServices |
| `GET` | `/api/im/chats/group/info` | Query: group_ids | MsgServices |
| `GET` | `/api/im/chats/group/sticky_top/list` | Query: group_id, cursor, size, include_cursor, up | MsgServices |
| `GET` | `/api/im/cny/firework/2026` | Query: chat_user_id | FireworkService |
| `GET` | `/api/im/detect/switch/author` |  | MsgServices |
| `GET` | `/api/im/group/bubble/get_hint` | Query: group_id | MsgServices |
| `GET` | `/api/im/group/widget/list` | Query: group_id, checkin_plan_id | GroupSpaceService |
| `GET` | `/api/im/group/widget/wish/guide` | Query: group_id | GroupSpaceService |
| `GET` | `/api/im/group/widget/wish/list` | Query: group_id, type | GroupSpaceService |
| `GET` | `/api/im/message/settings` | Query: chat_user_id, checkin_plan_id | ChatSettingService |
| `GET` | `/api/im/message/voice/caption` | Query: file_id | FireworkService |
| `GET` | `/api/im/messages/around/history` | Query: chat_type, chat_id, store_id, limit | MsgServices |
| `GET` | `/api/im/messages/history` | Query: limit, chat_user_id, last_id, start_id | MsgServices |
| `GET` | `/api/im/messages/new/history` | Query: chat_type, chat_id, store_id, limit | MsgServices |
| `GET` | `/api/im/messages/old/history` | Query: chat_type, chat_id, store_id, limit | MsgServices |
| `GET` | `/api/im/messages/queryChats` | Query: targetIdList | MsgServices |
| `GET` | `/api/im/messages/range/history` | Query: chat_type, chat_id, from_store_id, to_store_id | MsgServices |
| `GET` | `/api/im/nns/group_list` |  | IMGroupBindServices |
| `GET` | `/api/im/note/interact` | Query: query_note_type, start_note_id, limit | NoteShareServices |
| `GET` | `/api/im/note/share/config` | Query: chat_user_id | NoteShareServices |
| `GET` | `/api/im/panel/search/gif` | Query: keyword, page, limit, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | EmojiSearchService |
| `GET` | `/api/im/qr_code/generate` | Query: scene, content | ShareService |
| `GET` | `/api/im/red/group/admininfo` | Query: group_id | MsgServices |
| `GET` | `/api/im/red/group/gen_invite_emoji_code` | Query: group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | MsgServices |
| `GET` | `/api/im/red/group/join_group_by_invite_card` | Query: group_id, msg_id | MsgServices |
| `GET` | `/api/im/red/group/messages/history` | Query: group_id, start_id, last_id, limit | MsgServices |
| `GET` | `/api/im/red/group/qr_code` | Query: biz_id, biz_type | MsgServices |
| `GET` | `/api/im/red/group/safe/check` | Query: group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | MsgServices |
| `GET` | `/api/im/red/group/user/note_list` | Query: group_id, cursor, size | BindNoteServices |
| `GET` | `/api/im/red/vote/getGroupVoteList` | Query: group_id, page, size | MsgServices |
| `GET` | `/api/im/red/vote/getVoteDetailById` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | MsgServices |
| `GET` | `/api/im/share_board/both_join_board` | Query: target_user_id | MsgServices |
| `GET` | `/api/im/share_board/create_auth_check` | Query: target_user_id | MsgServices |
| `GET` | `/api/im/share_board/gen_share_key` | Query: board_id, user_id | CommonBoardService |
| `GET` | `/api/im/share_panel/extra` |  | ShareService |
| `GET` | `/api/im/smiles` |  | PersonalEmoticonService |
| `GET` | `/api/im/smiles/get_file_id` |  | PersonalEmoticonService |
| `GET` | `/api/im/smiles/hot` |  | PersonalEmoticonService |
| `GET` | `/api/im/smiles/hot_smiles` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | EmojiSearchService |
| `GET` | `/api/im/smiles/note/add` | Query: note_id | FeedbackService |
| `GET` | `/api/im/socialrelation/trigger/coldstart` |  | MsgServices |
| `GET` | `/api/im/stickeralbum/sticker/list` | Query: album_id | StickerService |
| `GET` | `/api/im/trans_link` | Query: link | MsgServices |
| `GET` | `/api/im/user/decrypt` | Query: encrypt_user_id | CommentService |
| `GET` | `/api/im/users/following` | Query: page_size, start | MsgServices |
| `GET` | `/api/im/users/following/all` |  | MsgServices |
| `GET` | `/api/im/v1/file/url` | Query: sceneId, fileKey, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, groupId | DocumentServices |
| `GET` | `/api/im/v1/group/admin/page` | Query: group_id | MsgServices |
| `GET` | `/api/im/v1/group/ai/message/history` | Query: chatId, cursor | AiChatServices |
| `GET` | `/api/im/v1/group/ai/message/last` | Query: chatId | AiChatServices |
| `GET` | `/api/im/v1/group/approval` | Query: group_id, type, approval_status, cursor, page_size | GroupLabelServices |
| `GET` | `/api/im/v1/group/chain` | Query: groupChainId, groupId, groupChainUserPageSize | GroupChainService |
| `GET` | `/api/im/v1/group/chain/users` | Query: groupChainId, groupId, page, limit | GroupChainService |
| `GET` | `/api/im/v1/group/chains` | Query: groupId, limit, page | GroupChainService |
| `GET` | `/api/im/v1/group/checkin/full/share_info` | Query: group_id, check_in_id, full_type | CheckInServices |
| `GET` | `/api/im/v1/group/checkin/note/material` | Query: group_id, check_in_id | CheckInServices |
| `GET` | `/api/im/v1/group/create/config` | Query: create_source | CreateGroupServices |
| `GET` | `/api/im/v1/group/get_group_basic_info` | Query: group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, join_source_str, open_gid | MsgServices |
| `GET` | `/api/im/v1/group/get_jump_page_by_invite_code` | Query: emoji, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | MsgServices |
| `GET` | `/api/im/v1/group/invite/emoji_code` | Query: group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | MsgServices |
| `GET` | `/api/im/v1/group/label/detail` | Query: group_id, page_num, page_size | GroupLabelServices |
| `GET` | `/api/im/v1/group/message/sender` | Query: group_id, msg_id | MsgServices |
| `GET` | `/api/im/v1/group/personal_page/subject` | Query: user_id, cursor, scroll_type, get_type, size, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | MyGroupService |
| `GET` | `/api/im/v1/group/robot` | Query: group_id, robot_id | MsgServices |
| `GET` | `/api/im/v1/group/robot/join_group_list` | Query: group_id, type, cursor, size | MsgServices |
| `GET` | `/api/im/v1/group/robot/me` | Query: group_id, cursor, size | MsgServices |
| `GET` | `/api/im/v1/group/robot/recommend` | Query: group_id | MsgServices |
| `GET` | `/api/im/v1/group/robot/test/chat` | Query: robot_id, group_id, version_id | MsgServices |
| `GET` | `/api/im/v1/group/robot/test/pull_message` | Query: last_msg_id, chat_id, robot_id, version_id | MsgServices |
| `GET` | `/api/im/v1/group/robots` | Query: group_id | MsgServices |
| `GET` | `/api/im/v1/group/search` | Query: page_no, keyword, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, search_id, is_recommend | AliothServices |
| `GET` | `/api/im/v1/group/shortcut` | Query: group_id | MsgServices |
| `GET` | `/api/im/v1/group/square/card/tab` | Query: key_word | GroupSquareServices |
| `GET` | `/api/im/v1/group/square/config` | Query: longitude, latitude, tax_id, version | GroupSquareServices |
| `GET` | `/api/im/v1/group/square/list` | Query: tax_id, page_no, page_size | GroupSquareServices |
| `GET` | `/api/im/v1/group/square/search` | Query: page_no, keyword, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, search_id, extra | SearchGroupService |
| `GET` | `/api/im/v1/group/topic/share/info` | Query: group_id, topic_id, type | GroupTopicService |
| `GET` | `/api/im/v1/group/topics` | Query: groupId, needFilterInvolved, needUserCreatedPost | GroupTopicService |
| `GET` | `/api/im/v1/group/topics` | Query: groupId, needFilterInvolved, needUserCreatedPost, type | GroupTopicService |
| `GET` | `/api/im/v1/group/user/following` | Query: page_size, offset_user_id, group_id | MsgServices |
| `GET` | `/api/im/v1/group/user/following/search` | Query: keyword, from, page_size, group_id | MsgServices |
| `GET` | `/api/im/v1/group/vote/detail` | Query: group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | MsgServices |
| `GET` | `/api/im/v1/group/vote/page` | Query: group_id, page, size | MsgServices |
| `GET` | `/api/im/v1/group_mini_info` | Query: group_id | GroupInfoEditServices |
| `GET` | `/api/im/v1/message/extra/offline` | Query: chat_id_list, limit | MsgServices |
| `GET` | `/api/im/v1/message/location/list` | Query: chat_id | MsgServices |
| `GET` | `/api/im/v1/multi/config` | Query: field, groupId | CheckInService |
| `GET` | `/api/im/v1/multi/config` | Query: field, longitude, latitude, groupId, labelName | GroupLabelServices |
| `GET` | `/api/im/v1/plus/config` | Query: chat_id, chat_type, user_id, receiver_id, scene | ChatPlusServices |
| `GET` | `/api/im/v1/poi/around` | Query: longitude, latitude, keyword, page_no, page_size, scene | LocationSelectService |
| `GET` | `/api/im/v1/users/mutual/follow?` | Query: page_size, start | MsgServices |
| `GET` | `/api/im/v1/users/search/mutual/follow` | Query: keyword, from, page_size | MsgServices |
| `GET` | `/api/im/v2/group/get_group_jump_page_info` | Query: group_id, batch, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, join_source_str, open_gid, emoji, longitude, latitude, domain | GroupMiddleService |
| `GET` | `/api/im/v2/group/master_group` |  | MsgServices |
| `GET` | `/api/im/v2/group/members` | Query: group_id, limit, page | MsgServices |
| `GET` | `/api/im/v2/group/user` | Query: group_id, user_id_list | MsgServices |
| `GET` | `/api/im/v2/group_mini_info` | Query: group_id | GroupInfoEditServices |
| `GET` | `/api/im/v2/message/extra` | Query: chat_type, chat_id, min_store_id, max_store_id | MsgServices |
| `GET` | `/api/im/v2/messages/offline` | Query: next_ts, count, limit | MsgServices |
| `GET` | `/api/im/v2/voice_convert` | Query: msg_ids | MsgServices |
| `GET` | `/api/im/v3/chats/info` | Query: chat_user_ids | MsgServices |
| `GET` | `/api/im/voice_convert` | Query: msg_ids | MsgServices |
| `GET` | `api/im/emoji/config` | Query: curVersion, forceUpdate | MsgServices |
| `GET` | `api/im/get_intimacy_chat` |  | MsgServices |
| `GET` | `api/im/red/group/getFans` | Query: group_id, start | MsgServices |
| `GET` | `api/im/red/group/getRecentEngageUserInfo` | Query: group_id | MsgServices |
| `GET` | `api/im/search/gif` | Query: keyword, page, limit | MsgServices |
| `GET` | `api/im/speak/create_auth_check` | Query: target_user_id, type | MsgServices |
| `GET` | `api/im/stickerstore/album/list` | Query: cursor, biz_type | EmojiStoreService |
| `GET` | `api/im/stickerstore/album/list` | Query: cursor, biz_type | StickerService |
| `GET` | `api/im/stickerstore/user/album/list` | Query: biz_type | EmojiStoreService |
| `GET` | `api/im/stickerstore/user/album/list` | Query: biz_type | StickerService |
| `GET` | `api/im/user/auth` | Query: type | UserServices |
| `GET` | `api/im/v1/chats/record/overview` | Query: chat_id, is_group | MessageSearchServices |
| `GET` | `api/im/v1/chats/record/search` | Query: chat_id, is_group, filter_type, keyword, cursor, size | MessageSearchServices |
| `GET` | `api/im/v1/file/key` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_FILE_ID | MsgServices |
| `GET` | `api/im/v1/group/activity/card` | Query: group_id | MsgServices |
| `GET` | `api/im/v1/group/settings` | Query: groupId | GroupSettingServices |
| `GET` | `api/im/v1/statement/user/list` | Query: msg_id, emoji_name, chat_id, cursor, size | MsgServices |
| `GET` | `api/im/v2/get_banner_list` |  | MsgServices |
| `GET` | `api/im/v3/chats` | Query: limit, complete, next_ts | MsgServices |
| `POST` | `/api/im/activity_grouping/instance/report` | Body: vs7.b | CampaignNavigatorReportService |
| `POST` | `/api/im/activity_grouping/report_exposure` | Field: user_id, unread_activity, read_activity | LocalFeedService |
| `POST` | `/api/im/chat/dynamic/info/expose` | Body: vn4.y | MsgServices |
| `POST` | `/api/im/chat/set_unread` | Field: chat_target_id, chat_type, read_store_id, unread_count | MsgUnreadService |
| `POST` | `/api/im/chat_widget` | Field: chat_user_id, type | ChatSettingService |
| `POST` | `/api/im/chat_widget/checkin/plan/create` | Field: name, icon, chat_type, com.xingin.capa.feature_model.session.VideoBackgroundBean.TYPE_COLOR, target_id, introduction, format | CheckInService |
| `POST` | `/api/im/chat_widget/checkin/plan/update` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, name, icon, chat_type, com.xingin.capa.feature_model.session.VideoBackgroundBean.TYPE_COLOR, target_id, introduction, format | CheckInService |
| `POST` | `/api/im/chat_widget/checkin/post` | Query: chat_type, target_id; Field: plan_id, content, com.xingin.capa.feature_model.session.VideoBackgroundBean.TYPE_IMAGE, poi_id, image_type | CheckInService |
| `POST` | `/api/im/chat_widget/sticky_note/edit` | Body: zn4.t | StickyNoteApi |
| `POST` | `/api/im/chat_widget/sticky_note/post` | Body: zn4.u | MsgServices |
| `POST` | `/api/im/chat_widget/sticky_note/remove` | Query: sticky_note_id | StickyNoteApi |
| `POST` | `/api/im/chats/group` | Field: group_id, start_store_id, chat_status | MsgServices |
| `POST` | `/api/im/chats/group/remark` | Field: group_id, remark | MsgServices |
| `POST` | `/api/im/chats/group/sticky_top/insert` | Field: group_id, msg_id | MsgServices |
| `POST` | `/api/im/chats/group/sticky_top/remove` | Field: group_id, msg_id, all | MsgServices |
| `POST` | `/api/im/clean/report` | Field: chat_user_id, type, action | MsgServices |
| `POST` | `/api/im/data/authorization` | Field: data_outbound_has_authorized | MsgServices |
| `POST` | `/api/im/detect/switch/author` | Body: vn4.j | MsgServices |
| `POST` | `/api/im/egg_expose` | Query: emoji_str, target_user_id | MsgServices |
| `POST` | `/api/im/emoji/bg` | Field: chat_user_id, emoji, com.xingin.capa.feature_model.session.VideoBackgroundBean.TYPE_COLOR | ChatEmojiBgService |
| `POST` | `/api/im/golden_bubble/switch` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | ChatSettingService |
| `POST` | `/api/im/group/bubble/expose_hint` | Field: group_id, ts | MsgServices |
| `POST` | `/api/im/group/bubble/publish` | Field: group_id, bubble_emoji, bubble_content | BubbleService |
| `POST` | `/api/im/group/create/note` | Body: q48.a | CreateGroupServices |
| `POST` | `/api/im/group/ice_breaker` | Field: groupId, emojiKey, subType, com.xingin.capa.feature_model.session.VideoBackgroundBean.TYPE_IMAGE | MsgServices |
| `POST` | `/api/im/group/management` | Field: createSpeakOutLive, groupId | MsgServices |
| `POST` | `/api/im/group/management` | Field: groupId, createGroupLiveSwitch | MsgServices |
| `POST` | `/api/im/group/management` | Field: groupId, switchName, switchValue | MsgServices |
| `POST` | `/api/im/group/management` | Field: groupId, groupThresholdRequests | MsgServices |
| `POST` | `/api/im/group/query_online_status` | Field: groupIds, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | MsgServices |
| `POST` | `/api/im/group/text2image` | Body: wy7.w | GroupRecruitServices |
| `POST` | `/api/im/group/widget/invite` | Field: group_id, type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | GroupSpaceService |
| `POST` | `/api/im/group/widget/sort` | Field: group_id, widget_types | GroupSpaceService |
| `POST` | `/api/im/int/messages/typing/signal` | Body: zn4.g | MsgServices |
| `POST` | `/api/im/int/v3/messages/ads/consult` | Body: zn4.b | MsgServices |
| `POST` | `/api/im/message/bubble/update/switch` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | ChatSettingService |
| `POST` | `/api/im/message/group/exposed` | Field: group_id, max_store_id | MessagePreviewService |
| `POST` | `/api/im/message/video_note/history` | Body: zn4.x | MsgServices |
| `POST` | `/api/im/messages/revokeMessage` | Body: zn4.r | MsgServices |
| `POST` | `/api/im/messages/updateTop` | Body: zn4.f | MsgServices |
| `POST` | `/api/im/note/info/batch` | Body: mc8.f | NoteShareServices |
| `POST` | `/api/im/notify/thanks` | Body: zn4.p | MsgServices |
| `POST` | `/api/im/private/query_online_status` | Field: userIds, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | MsgServices |
| `POST` | `/api/im/private/rm_ice_break` | Field: chat_id | MsgServices |
| `POST` | `/api/im/red/group/add` | Body: zn4.l | MsgServices |
| `POST` | `/api/im/red/group/admin` | Body: zn4.l | MsgServices |
| `POST` | `/api/im/red/group/approveJoinGroupHistory` | Field: group_id, page, limit | MsgServices |
| `POST` | `/api/im/red/group/cancel_join_group` | Field: group_id | MsgServices |
| `POST` | `/api/im/red/group/create` | Body: zn4.l | MsgServices |
| `POST` | `/api/im/red/group/get_group_jump_page_info` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, is_batch_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, join_source_str, open_gid | MsgServices |
| `POST` | `/api/im/red/group/get_invite_emoji_code_info` | Body: zn4.k | MsgServices |
| `POST` | `/api/im/red/group/info` | Field: group_id, group_name | MsgServices |
| `POST` | `/api/im/red/group/join_group` | Field: group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, inviter, answer, join_source_str, extra | MsgServices |
| `POST` | `/api/im/red/group/messages/view` | Field: view_ids | MsgServices |
| `POST` | `/api/im/red/group/mute` | Field: group_id, mute | MsgServices |
| `POST` | `/api/im/red/group/note/binding` | Field: group_id, binding_note_list, unbinding_note_list, bindSource | BindNoteServices |
| `POST` | `/api/im/red/group/personal_page_group_show_info` | Field: user_id, sorted_by | MsgServices |
| `POST` | `/api/im/red/group/remove` | Body: zn4.l | MsgServices |
| `POST` | `/api/im/red/group/removeAdmin` | Body: zn4.l | MsgServices |
| `POST` | `/api/im/red/group/updateAnnouncement` | Body: zn4.w | MsgServices |
| `POST` | `/api/im/red/group/updateGroupAvatar` | Field: group_id, avatar | MsgServices |
| `POST` | `/api/im/red/group/username` | Field: group_id, user_id, nickname | MsgServices |
| `POST` | `/api/im/red/link/execute` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | MsgServices |
| `POST` | `/api/im/red/vote/postVote` | Body: zn4.n | MsgServices |
| `POST` | `/api/im/red/vote/userVote` | Body: zn4.o | MsgServices |
| `POST` | `/api/im/risk_popup` | Field: chat_user_id, risk_popup_type | MsgServices |
| `POST` | `/api/im/short_link/send_message` | Body: zn4.e | MsgServices |
| `POST` | `/api/im/smiles/add` | Field: file_id | PersonalEmoticonService |
| `POST` | `/api/im/smiles/add` | Field: file_id | PersonalEmoticonService |
| `POST` | `/api/im/smiles/add/direct` | Field: image_url, smiles_type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_WIDTH, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_HEIGHT | PersonalEmoticonService |
| `POST` | `/api/im/smiles/add/third_party` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | PersonalEmoticonService |
| `POST` | `/api/im/smiles/delete` | Field: file_ids | PersonalEmoticonService |
| `POST` | `/api/im/smiles/operate` | Query: top_smiles_ids, delete_smiles_ids | EmojiStoreService |
| `POST` | `/api/im/socialrelation/intervention/ack` | Field: msgId | MsgServices |
| `POST` | `/api/im/stickerstore/album/user/subscribe` | Query: album_id, biz_type | EmojiStoreService |
| `POST` | `/api/im/user_report` | Body: zn4.j | MsgServices |
| `POST` | `/api/im/users/filterUser/stranger` | Body: zn4.c | MsgServices |
| `POST` | `/api/im/v1/chats/remove/group` | Field: group_id, start_store_id, chat_status | MsgServices |
| `POST` | `/api/im/v1/chats/remove/stranger` | Field: batch_data | MsgServices |
| `POST` | `/api/im/v1/chats/top` | Body: zn4.f | MsgServices |
| `POST` | `/api/im/v1/enter_chat_trigger` | Field: chat_type, chat_id | MsgServices |
| `POST` | `/api/im/v1/group/admin/add` | Body: zn4.l | MsgServices |
| `POST` | `/api/im/v1/group/admin/remove` | Body: zn4.l | MsgServices |
| `POST` | `/api/im/v1/group/ai/chat/quit` | Field: chatId, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.OPERATION_SAVE | AiChatServices |
| `POST` | `/api/im/v1/group/alter/announcement` | Body: zn4.w | MsgServices |
| `POST` | `/api/im/v1/group/alter/public` | Field: group_id, type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | MsgServices |
| `POST` | `/api/im/v1/group/approval/change` | Field: group_id, type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, approval_status | GroupLabelServices |
| `POST` | `/api/im/v1/group/approval/read` | Field: group_id, approval_type | MsgServices |
| `POST` | `/api/im/v1/group/approval_all_group_robots` | Field: group_id | MsgServices |
| `POST` | `/api/im/v1/group/approve/approved_history` | Field: group_id, page, limit | MsgServices |
| `POST` | `/api/im/v1/group/approve/join_group` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, approved, group_id | MsgServices |
| `POST` | `/api/im/v1/group/approve/join_group_all` | Field: group_id, approved | MsgServices |
| `POST` | `/api/im/v1/group/chain` | Body: com.xingin.im.entities.CreateGroupChainPostBody | GroupChainService |
| `POST` | `/api/im/v1/group/chain/user` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS, remark, groupId, groupChainId | GroupChainService |
| `POST` | `/api/im/v1/group/checkin/create/note` | Body: e48.b | CheckInServices |
| `POST` | `/api/im/v1/group/checkin/detail/create` | Field: group_id, check_in_id, content, file_ids, use_capa_bucket | CheckInServices |
| `POST` | `/api/im/v1/group/checkin/detail/edit` | Field: group_id, check_in_id, check_in_detail_id, content, deleted_urls, added_file_ids, use_capa_bucket | CheckInServices |
| `POST` | `/api/im/v1/group/create` | Body: zn4.l | MsgServices |
| `POST` | `/api/im/v1/group/get_group_jump_page_info` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, is_batch_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, join_source_str, open_gid | MsgServices |
| `POST` | `/api/im/v1/group/invite/emoji_code` | Body: zn4.k | MsgServices |
| `POST` | `/api/im/v1/group/letter/report` | Field: letter_id, group_id, action, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | MsgServices |
| `POST` | `/api/im/v1/group/master/transfer` | Field: group_id, target_user_id | GroupTransferOwnerServices |
| `POST` | `/api/im/v1/group/member/add` | Body: zn4.l | MsgServices |
| `POST` | `/api/im/v1/group/member/remove` | Body: zn4.l | MsgServices |
| `POST` | `/api/im/v1/group/notification/settings` | Field: group_id, notification_status, importantNotifyOptions | MsgServices |
| `POST` | `/api/im/v1/group/remove_all_message` | Field: revoke_user_id, group_id | MsgServices |
| `POST` | `/api/im/v1/group/remove_inactive` | Field: group_id, remove_inactive_member | MsgServices |
| `POST` | `/api/im/v1/group/robot/bind` | Field: robot_id, group_id | MsgServices |
| `POST` | `/api/im/v1/group/robot/create` | Field: robot_id, group_id, version_id | MsgServices |
| `POST` | `/api/im/v1/group/robot/create_draft` | Field: nickname, com.xingin.capa.feature_model.session.VideoBackgroundBean.TYPE_IMAGE, character_description, character_introduction, group_id | MsgServices |
| `POST` | `/api/im/v1/group/robot/handle_join_group_robot` | Field: group_id, robot_id, result, request_id | MsgServices |
| `POST` | `/api/im/v1/group/robot/test/send_message` | Field: robot_id, version_id, chat_id, content | MsgServices |
| `POST` | `/api/im/v1/group/robot/update_join_switch` | Field: group_id, result | MsgServices |
| `POST` | `/api/im/v1/group/setting/modify` | Field: group_id, command, payload | GroupLabelServices |
| `POST` | `/api/im/v1/group/topic/posts` | Body: com.xingin.im.v2.group.topic.bean.GroupTopicPostRequestBean | GroupTopicService |
| `POST` | `/api/im/v1/group/topic/update_status` | Field: groupId, topicId, type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS, showPublic | GroupTopicService |
| `POST` | `/api/im/v1/group/update_join_group_approval` | Field: group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SETTING, question, answer | MsgServices |
| `POST` | `/api/im/v1/group/user/setting/modify` | Field: group_id, command, payload | GroupLabelServices |
| `POST` | `/api/im/v1/group/vote/create` | Body: zn4.n | MsgServices |
| `POST` | `/api/im/v1/group/vote/participate` | Body: zn4.o | MsgServices |
| `POST` | `/api/im/v1/link/execute` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, biz_type | MsgServices |
| `POST` | `/api/im/v1/message/location/read` | Field: chat_id | MsgServices |
| `POST` | `/api/im/v1/messages/stranger/read` |  | MsgServices |
| `POST` | `/api/im/v1/statement/post` | Field: msg_id, emoji_name, chat_id, source_content | MsgServices |
| `POST` | `/api/im/v1/top/sticky` | Body: o67.o0 | MsgServices |
| `POST` | `/api/im/v1/update_group_info` | Field: group_id, group_name, group_introduction, group_avatar, is_upload_avatar | MsgServices |
| `POST` | `/api/im/v1/user/batch` | Field: userIds | MsgServices |
| `POST` | `/api/im/v1/users/blocked-users/{user_id}` | Path: user_id; Field: testid | MsgServices |
| `POST` | `/api/im/v2/group/create` | Body: com.xingin.im.v2.group.create.bean.CreateGroupPostBody | CreateGroupServices |
| `POST` | `/api/im/v2/group/search` | Body: wi0.f | AliothServices |
| `POST` | `/api/im/v2/messages/ack` | Body: zn4.q | MsgServices |
| `POST` | `/api/im/v2/messages/batch_read` | Body: zn4.d | MsgServices |
| `POST` | `/api/im/v2/messages/read` | Body: zn4.d | MsgServices |
| `POST` | `/api/im/v2/messages/unread` | Body: zn4.d | MsgServices |
| `POST` | `/api/im/v2/red_dot/report` | Field: type, id_list | ChatPlusServices |
| `POST` | `/api/im/v2/update_group_info` | Body: com.xingin.im.edit.v2.bean.GroupEditableInfoPostBody | GroupInfoEditServices |
| `POST` | `/api/im/v3/chats` | Field: chat_user_id, start_store_id, chat_status | MsgServices |
| `POST` | `/api/im/v3/chats/check` | Body: zn4.a | MsgServices |
| `POST` | `/api/im/v3/chats/delete` |  | MsgServices |
| `POST` | `/api/im/v3/chats/stranger` | Field: batch_data | MsgServices |
| `POST` | `/api/im/v3/chats/stranger/box` |  | MsgServices |
| `POST` | `/api/im/v3/chats/update_status` | Field: target_id, chat_type, chat_status | MsgServices |
| `POST` | `/api/im/v3/messages/ads/consult` | Body: zn4.b | MsgServices |
| `POST` | `api/im/activity_grouping/personal` | Body: vs7.a | CampaignService |
| `POST` | `api/im/activity_grouping/sidebar_data` |  | CampaignSidebarService |
| `POST` | `api/im/file/cdn_url` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_FILE_ID, sourceType, bizCode, scene, uuid, senderId, receiverId, extraInfo, mediaType, videoId, needHDR, isSupportSound | MsgServices |
| `POST` | `api/im/file/cdn_url` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_FILE_ID, sourceType, bizCode, scene, uuid, senderId, receiverId, extraInfo, mediaType, videoId, needHDR, isSupportSound | ChatEdithApiClient |
| `POST` | `api/im/group/show_history` | Field: groupId, needShowHistory | MsgServices |
| `POST` | `api/im/group/show_welcome` | Field: groupId, needShowWelcome, welcomeType, welcomeText | MsgServices |
| `POST` | `api/im/push/update` | Field: type | MsgServices |
| `POST` | `api/im/red/group/approveJoinGroup` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, approved, group_id | MsgServices |
| `POST` | `api/im/red/group/approveJoinGroupAll` | Field: group_id, approved | MsgServices |
| `POST` | `api/im/red/group/joinGroupApproval` | Field: group_id, needGroupApproval | MsgServices |
| `POST` | `api/im/red/group/joinGroupThreshold` | Field: group_id, needThreshold | MsgServices |
| `POST` | `api/im/red/group/silence` | Field: group_id, silence | MsgServices |
| `POST` | `api/im/red_dot/report` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, type | MsgServices |
| `POST` | `api/im/smiles/operate` | Field: top_smiles_ids, delete_smiles_ids | StickerService |
| `POST` | `api/im/stickeralbum/unsubscribe` | Query: album_id, biz_type | EmojiStoreService |
| `POST` | `api/im/stickeralbum/unsubscribe` | Field: album_id, biz_type | StickerService |
| `POST` | `api/im/stickerstore/album/user/subscribe` | Field: album_id, biz_type | StickerService |
| `POST` | `api/im/stickerstore/user/album/update` | Query: album_id_list, biz_type | EmojiStoreService |
| `POST` | `api/im/stickerstore/user/album/update` | Field: album_id_list, biz_type | StickerService |
| `POST` | `api/im/user/auth` | Field: type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | UserServices |
| `POST` | `api/im/v1/group/ai/button/event` | Field: event, value, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, chatId | AiChatServices |
| `POST` | `api/im/v1/group/ai/chat` | Field: scene, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AiChatServices |
| `POST` | `api/im/v1/group/ai/chat/restart` | Field: chatId, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AiChatServices |
| `POST` | `api/im/v1/group/ai/message` | Field: content, event, extra, createTime, uuid, chatId | AiChatServices |
| `POST` | `api/im/v1/group/get_approve_join_group_infos` | Field: group_id, page, limit | MsgServices |
| `POST` | `api/im/v1/users/muted-users/{user_id}` | Path: user_id; Field: testid | MsgServices |
| `POST` | `api/im/v2/action/report` | Field: type, id_list | MsgServices |
| `POST` | `api/im/v2/delete_banner_list` | Field: banner_id | MsgServices |
| `PUT` | `/api/im/v1/group/robot/update` | Field: robot_id, group_id, version_id | MsgServices |
| `PUT` | `/api/im/v1/group/robot/update_draft` | Field: robot_id, nickname, com.xingin.capa.feature_model.session.VideoBackgroundBean.TYPE_IMAGE, character_description, character_introduction | MsgServices |

#### `impaas`（8 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/impaas/conv/single/create` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |
| `POST` | `/api/impaas/conv/user/list` | Body: java.util.Map<java.lang.String, java.lang.Object> map, kotlin.coroutines.Continuation<? super retrofit2.a<java.lang.String>> | ChatEdithApiClient |
| `POST` | `/api/impaas/conv/user/list` | Body: java.util.Map<java.lang.String, java.lang.Object> map, kotlin.coroutines.Continuation<? super retrofit2.a<java.lang.String>> | ChatEdithApiClient |
| `POST` | `/api/impaas/conv/user/list` | Body: java.util.Map<java.lang.String, java.lang.Object> map, kotlin.coroutines.Continuation<? super retrofit2.a<java.lang.String>> | ChatEdithApiClient |
| `POST` | `/api/impaas/conv/user/list` | Body: com.xingin.trade_bcim.model.GetMerchantChatListRequest; Header: authorization | XYBCIMSessionApiService |
| `POST` | `/api/impaas/conv/visible/set` | Body: java.util.Map<java.lang.String, java.lang.Object> map, kotlin.coroutines.Continuation<? super retrofit2.a<java.lang.String>> | ChatEdithApiClient |
| `POST` | `/api/impaas/conv/visible/set` | Body: com.xingin.trade_bcim.model.DeleteMerchantChatRequest; Header: authorization | XYBCIMSessionApiService |
| `POST` | `/api/impaas/message/user/list` | Query: sid; Body: java.util.Map<java.lang.String, java.lang.Object>; Header: authorization | ChatDetailApiService |

#### `infra`（2 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/infra/v1/translate` | Body: com.xingin.translate.RequestBody | TranslateService |
| `POST` | `api/infra/v1/system_service/kratosscripts` |  | AccountService |

#### `light`（2 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/light/app2c/v1/detail` | Field: app_id, app_type | RequestRepository |
| `POST` | `/api/light/app2c/v1/list` | Query: page_num, page_size | DownloadManagerRepository |

#### `link`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/link/security/validator` | Query: link, msg_id | MsgServices |

#### `lola`（9 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/lola/backend/api/chat/observation/list` | Body: com.xingin.diandian.bean.RequestObservationListBean requestObservationListBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<com.xingin.diandian.model.ObservationListModel>> | ChatService |
| `POST` | `/lola/backend/api/chat/picture_search` | Body: com.xingin.diandian.bean.RequestImageSearchBean requestImageSearchBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<com.xingin.diandian.bean.ImageSearchBean>> | ChatService |
| `POST` | `/lola/backend/api/chat/welcome_inquire` |  | ChatService |
| `POST` | `/lola/backend/api/search/suggestion` | Body: com.xingin.diandian.bean.RequestSuggestionBean requestSuggestionBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<com.xingin.diandian.bean.SuggestionResponseBean>> | ChatService |
| `POST` | `/lola/backend/api/user/report` | Body: com.xingin.diandian.bean.RequestReportBean requestReportBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<java.lang.String>> | ChatService |
| `POST` | `/lola/backend/api/welcome/topic` | Body: com.xingin.diandian.bean.RequestTopicBean requestTopicBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<com.xingin.diandian.bean.TopicResponseBean>> | ChatService |
| `POST` | `lola/api/agix/feedback` | Body: com.xingin.diandian.bean.RequestFeedBackBean requestFeedBackBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<java.lang.String>> | ChatService |
| `POST` | `lola/api/agix/feedback` |  | ChatService |
| `POST` | `lola/backend/api/chat/cancel` | Body: com.xingin.diandian.bean.RequestInterceptBean requestInterceptBean, kotlin.coroutines.Continuation<? super com.xingin.diandian.network.ApiResponse<java.lang.String>> | ChatService |

#### `madmen`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/madmen/ad/tracking/xhs-guide-v2/click` | Query: deviceId, xhsUserId | DiandianDownloadGuideTrackingApi |

#### `marketing`（12 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/marketing/box/trigger` | Body: com.xingin.commercial.goodsdetail.entities.r1; Header: x-ratelimit-meta | GoodsDetailService |
| `POST` | `/api/marketing/box_trigger/goods_search` | Field: bizScene, keyword, filter | CommercialSearchServicesV2 |
| `POST` | `/api/marketing/box_trigger/goods_search` | Body: xz5.g1 | PayApiService |
| `POST` | `/api/marketing/consult/video_autoplay` | Field: bizScene, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, videoType, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_NOTE_ID, skuId | NoteDetailService |
| `POST` | `/api/marketing/execution_strategy/acion/goods_search` | Field: executionId | CommercialSearchServicesV2 |
| `POST` | `/api/marketing/execution_strategy/action` | Query: executionId | SurpriseBoxService |
| `POST` | `/api/marketing/execution_strategy/action` | Field: executionId | StoreEdithCouponService |
| `POST` | `/api/marketing/front_pop_recall` | Field: executionId | SurpriseBoxService |
| `POST` | `/api/marketing/show/execution_strategy` | Body: xz5.x3 | PayApiService |
| `POST` | `/api/marketing/window_flipped` | Field: bizSource, has_flipped, execution_id | NoteDetailService |
| `POST` | `api/marketing/close_fixed_banner_of_benefits_claim` | Body: yx5.c | CouponBenefitsApi |
| `POST` | `api/marketing/get_fixed_banner_of_benefits_claim` | Body: yx5.a | CouponBenefitsApi |

#### `matrix`（3 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/matrix/dsl/templates/{name}` | Path: name; Query: template_version_code | TemplateService |
| `GET` | `/api/matrix/trading-scene/user/{user_id}/curations` | Path: user_id; Query: page, size | ProfileServices |
| `POST` | `/api/matrix/dsl/templates` | Body: okhttp3.RequestBody | TemplateService |

#### `media`（12 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/media/v1/imageinfo` | Query: fileKey, caller | ImageDetailInfoService |
| `GET` | `/api/media/v1/upload/capa/permit` | Query: bid, biz_name, scene, file_count, version | TokenService |
| `GET` | `/api/media/v1/upload/permit` | Query: bid, biz_name, scene, file_count, version | TokenService |
| `GET` | `/api/media/v1/upload/permit_no_login` | Query: bid, biz_name, scene, file_count, version | TokenService |
| `GET` | `/api/media/v1/upload/quick_upload_check` | Query: bid, bizName, scene, dedupIdentifier, dedupAlgorithm | TokenService |
| `GET` | `/api/media/v1/upload/quick_upload_check` | Query: bid, bizName, scene, dedupIdentifier, dedupAlgorithm, dedupChecksum | TokenService |
| `GET` | `/api/media/v1/video/meta_info` | Query: video_id, caller | VideoDetailInfoService |
| `POST` | `/api/media/v1/media/ai/mainobjectseg/mainobjectseg` | Body: com.xingin.capa.network.model.ai.MainObjectSegRequestBody | CapaAiImageService |
| `POST` | `/api/media/v1/media/ai/mainobjectseg/mainobjectseg` | Body: com.xingin.net.gen.model.Edith2ApiMediaV1MediaAiMainobjectsegMainobjectsegPostRequestBody | CapaApi |
| `POST` | `/api/media/v1/media/ai/moment` | Body: com.xingin.net.gen.model.Edith2ApiMediaV1MediaAiMomentPostRequestBody | CapaApi |
| `POST` | `/api/media/v1/media/ai/passerseg` | Body: com.xingin.capa.network.model.ai.PasserbySegRequestBody | CapaAiImageService |
| `POST` | `/api/media/v1/media/ai/passerseg` | Body: com.xingin.net.gen.model.Edith2ApiMediaV1MediaAiPassersegPostRequestBody | CapaApi |

#### `media_strategy`（2 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/media_strategy/batch_get_strategy` | Query: caller, strategy_types, prediction_date, is_oversea | ClientBandwidthUsageStrategy |
| `GET` | `/api/media_strategy/batch_get_strategy` | Query: caller, strategy_types, prediction_date, is_oversea | ServerPeakPeriodStrategy |

#### `medusa`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/medusa/api/app/community/source/new` | Body: v99.e | Api |

#### `model_portrait`（5 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/model_portrait/detect_items` | Query: cpu_name | NetworkReqService |
| `POST` | `/api/model_portrait/clear_model_portrait` | Body: com.xingin.modelprofile.network.ClearProfileParam | NetworkReqService |
| `POST` | `/api/model_portrait/model_score` | Body: com.xingin.modelprofile.network.DynamicAcquireReqParam | NetworkReqService |
| `POST` | `/api/model_portrait/portraits` |  | NetworkReqService |
| `POST` | `/api/model_portrait/report_model_capability` | Body: com.xingin.modelprofile.capability.CapabilityReportParam | NetworkReqService |

#### `mp`（3 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/mp/rmp/live/get_room_link` | Query: app_id, room_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | IMPLiveService |
| `GET` | `/api/mp/rmp/live/validate_trailer` | Query: app_id, trailer_id | IMPLiveService |
| `GET` | `/api/mp/rmp/search-tab` | Query: query, search_id, page, page_size, geo | AliothServices |

#### `nike`（5 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/nike/v1/package/latest` |  | DiandianUpdateApi |
| `GET` | `/api/nike/v3/update/check` |  | UpdateService |
| `GET` | `/api/nike/v3/update/popup` |  | UpdateService |
| `POST` | `/api/nike/v3/update/check/ship/success` | Body: com.xingin.xhs.robust.PatchTrackUtils.InUploadData | PatchServices |
| `POST` | `/api/nike/v4/update/check/andrshipinfo` | Body: com.xingin.robust.bean.PatchRequest | PatchServices |

#### `payment`（5 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/payment/iap/google/pay` | Field: order_id, order_channel, receipt_data, product_id, payment_type | PayServices |
| `POST` | `/payment/memeber/agreement/apply_sign` | Body: k36.c | AntomAgreementService |
| `POST` | `/payment/memeber/agreement/query_status` | Body: k36.i | AntomAgreementService |
| `POST` | `/payment/register/{bizType}/apply` | Path: bizType; Body: com.xingin.xhs.pay.lib.entities.MerchantOpeRequest | PayServices |
| `POST` | `/payment/register/{bizType}/deregister` | Path: bizType; Body: com.xingin.xhs.pay.lib.entities.MerchantOpeRequest | PayServices |

#### `pgym`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/pgym/trade_national/get_game_task` | Query: task_no, track_id, game_app_id | AdsGameTaskService |

#### `platform-server`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/platform-server/dsl/platform/templateDataMock/detail` | Query: dataId | DslAutoTestService |

#### `preorder`（12 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/preorder/click_event` | Query: biz_type, chat_user_id, menu_type, event_id | MsgServices |
| `GET` | `/api/preorder/coupon_list` | Query: promotion_channel, seller_uid_list | MsgServices |
| `GET` | `/api/preorder/goods_show_info` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, show_type, extra | GoodsDetailService |
| `GET` | `/api/preorder/goods_show_info` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, show_type, extra | ShareService |
| `POST` | `/api/preorder/card_click_event` | Query: cardType; Body: cj5.a | IMService |
| `POST` | `/api/preorder/chat_card_info` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, hostId, link, is_from_buyer | ShareService |
| `POST` | `/api/preorder/dynamic_event_click` | Query: baseActionRequest, bizParam | IMService |
| `POST` | `/api/preorder/image_search` | Field: source_type, chat_type, user_id, group_id, receiver_id, note_id, image_url, message_id, video_link | MsgServices |
| `POST` | `/api/preorder/is_match_preorder_condition` |  | MsgServices |
| `POST` | `/api/preorder/live_card_refresh` | Body: aj5.b | IMLiveCardApi |
| `POST` | `/api/preorder/update_threshold_detail` | Body: p98.r | RefinedThresholdService |
| `POST` | `/api/preorder/user_info` | Field: type, user_id, group_id, receiver_id | MsgServices |

#### `push`（40 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `api/push/delete_push_interest_tag` | Query: user_id, tag_id | UserServices |
| `GET` | `/api/push/check_interact_window_can_pop` | Query: user_id | PushGuideUserServices |
| `GET` | `/api/push/get_gesture_guidance_config` | Query: osVersion, phoneBrand | StrategyNetService |
| `GET` | `/api/push/get_push_valid_token` | Query: projectId | PushServices |
| `GET` | `/api/push/get_server_racing_result` | Query: flags | PushHoldoutService |
| `GET` | `/api/push/hit_badge_holdout` | Query: userId, deviceId | BadgeServices |
| `GET` | `/api/push/query_badge_exp` |  | MsgServices |
| `GET` | `/api/push/v1/widget/activity` |  | WidgetServices |
| `GET` | `/api/push/v1/widget/friend` | Query: target_user_id | WidgetServices |
| `GET` | `/api/push/v1/widget/trending` |  | WidgetServices |
| `GET` | `api/push/check_sub_channel_can_pop` | Query: user_id, sub_channel_id | ExploreService |
| `GET` | `api/push/get_interest_tag_list` | Query: user_id | UserServices |
| `GET` | `api/push/user_authority` | Query: userId, switchIds | UserServices |
| `GET` | `api/push/user_authority` | Query: userId, switchIds | PersonalizedService |
| `POST` | `/api/push/android/callback` | Field: eid, userId, deviceId, com.xingin.capa.edit.panel.sticker.model.watermarker.WaterMarker.TIME_STICKER_NAME, extra, type | PushServices |
| `POST` | `/api/push/app_client_push` | Body: oc6.g | AppClientPushService |
| `POST` | `/api/push/app_ensure_push` | Field: timestamp, action, scene, params, targetRows | HeraApiServices |
| `POST` | `/api/push/app_ensure_push` | Field: timestamp, action, scene, params | SimpleServices |
| `POST` | `/api/push/app_ensure_push_inactive` | Field: timestamp, action, scene, params, targetRows | HeraApiServices |
| `POST` | `/api/push/awareness/sid/register` | Field: donation_id, sid, timestamp | DonationService |
| `POST` | `/api/push/badge/clear` |  | PushServices |
| `POST` | `/api/push/badge/clear_v2` | Query: deviceId | PushServices |
| `POST` | `/api/push/close_user_switchs` | Body: cd6.a | PushServices |
| `POST` | `/api/push/device_bind_token` | Field: deviceId, devicePlatType, deviceInfo, build, timestamp, osInfo, reason, tokens, childSwitchJson, deviceParamsJson | PushServices |
| `POST` | `/api/push/device_revoke_token` | Field: deviceId, reason, timestamp | PushServices |
| `POST` | `/api/push/inapp-push` | Field: userId, com.xingin.capa.edit.panel.sticker.model.watermarker.WaterMarker.TIME_STICKER_NAME, action | MsgServices |
| `POST` | `/api/push/live-activity/token/regist` | Field: userId, deviceId, timestamp, role, devicePlatType, deviceInfo, serviceName, liveActivityTokens | AtomicNotificationServices |
| `POST` | `/api/push/live-activity/token/revoke` | Field: userId, deviceId, timestamp, role, devicePlatType, deviceInfo, serviceName, liveActivityTokens | AtomicNotificationServices |
| `POST` | `/api/push/subscribe_interact_push` | Field: user_id | PushGuideUserServices |
| `POST` | `/api/push/system_service/device/regist/v3` | Field: role, reason, osInfo, timestamp, pushSwitch, deviceInfo, tokens, devicePlatType, childSwitchJson, deviceParamsJson | PushServices |
| `POST` | `/api/push/user_bind_device` | Field: userId, deviceId, devicePlatType, timestamp, role | PushServices |
| `POST` | `/api/push/v1/fish_moment/clock_in` |  | WidgetServices |
| `POST` | `/api/push/v1/oppo/camera/deeplink/shoot_same` | Body: com.google.gson.l | OppoRedirectService |
| `POST` | `api/push/add_push_interest_tag` | Field: user_id, tag_id | UserServices |
| `POST` | `api/push/add_sub_channel_interest` | Field: user_id, sub_channel_id | ExploreService |
| `PUT` | `api/push/second_switch` | Field: userId, switchId, targetUserList | UserServices |
| `PUT` | `api/push/second_switch/update` | Field: userId, targetUserId, switchId, actionType | UserServices |
| `PUT` | `api/push/user_authority/update` | Field: userId, switchAuth | PushServices |
| `PUT` | `api/push/user_authority/update` | Field: userId, switchAuth | UserServices |
| `PUT` | `api/push/user_authority/update` | Field: userId, switchAuth | PersonalizedService |

#### `redcaptcha`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `api/redcaptcha/v2/feedback_for_app` |  | AntispamService |

#### `redcityip`（15 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/redcityip/query/oversea` |  | PetChatApi |
| `GET` | `/api/redcityip/v1/chat/config` |  | PetChatApi |
| `GET` | `/api/redcityip/v1/chat/onboarding` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, session_id | PetChatApi |
| `GET` | `/api/redcityip/v1/chats/pet` | Query: limit, page, complete, next_ts | MsgServices |
| `GET` | `/api/redcityip/v1/pet/emoji/tab` |  | PetChatApi |
| `GET` | `/api/redcityip/v1/recommend/pet/explore` |  | MsgServices |
| `GET` | `/api/redcityip/v1/welcome/chat/info` | Query: session_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, has_location_permission, is_first | PetChatApi |
| `GET` | `/api/redcityip/v3/homepage/pet/info` |  | PetChatApi |
| `GET` | `/api/redcityip/v4/chat/history` | Query: last_id, start_id, limit | PetChatApi |
| `POST` | `/api/redcityip/v1/chats/pet` | Field: receiver_id, start_store_id, chat_status | MsgServices |
| `POST` | `/api/redcityip/v1/recommend/pet/block` |  | MsgServices |
| `POST` | `/api/redcityip/v3/chat/end` | Field: pet_id, session_id | PetChatApi |
| `POST` | `/api/redcityip/v3/chat/start` | Body: ur7.b0 | PetChatApi |
| `POST` | `/api/redcityip/v3/share/note` | Field: type, content, text | MsgServices |
| `POST` | `/api/redcityip/v4/chat/reply` | Body: ur7.x | PetChatApi |

#### `redconfig`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/redconfig/dynamic/rule/execute/batch` | Body: com.xingin.i18n.dynamicconfig.data.ConfigRequest | RedConfigHubService |

#### `resource`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/resource/delivery/multi/match` | Query: sceneCode | HomeFeedGuideService |

#### `risk`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/risk/v1/natasha/checktextbykeywordwithclienttest` | Query: textList, optionParams, keywordScopeType | CapaCnySecurityAuditService |

#### `rmp`（14 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/rmp/share/query_share_ticket` | Query: share_ticket, app_id | IShareService |
| `GET` | `api/rmp/pkg/{appId}` | Path: appId; Query: sid, base_version; Header: mp-common-params | IMPVersionService |
| `POST` | `/api/rmp/share/acquire_share_ticket` | Body: tma.t0 | IShareService |
| `POST` | `/api/rmp/share/exchange_deeplink` | Body: tma.p | IShareService |
| `POST` | `/api/rmp/share/get_existed_ext_img_url` | Body: tma.r | IShareService |
| `POST` | `/api/rmp/share/get_rmp_info` | Body: tma.x | IShareService |
| `POST` | `/api/rmp/share/get_short_url` | Body: tma.w0 | IShareService |
| `POST` | `/api/rmp/share/group/get_info_list` | Body: tma.i | IChatService |
| `POST` | `/api/rmp/share/save_pic_4h5` | Body: tma.t | IShareService |
| `POST` | `/api/rmp/v1/front_end_action` | Body: tma.z0 | ICloseService |
| `POST` | `/api/rmp/v1/get_recently_used_config` | Body: tma.p0 | ICloseService |
| `POST` | `/api/rmp/v1/pay` | Body: okhttp3.RequestBody; Header: xy-common-params | IMPPayService |
| `POST` | `/api/rmp/v1/upsert_recently_used` | Body: tma.f | ICloseService |
| `POST` | `api/rmp/debug/access/check` | Body: okhttp3.RequestBody; Header: mp-common-params | IMPVersionService |

#### `rocking`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/rocking/resource/plan/batch/get` | Field: resource_query_list | GoodsNoteModel |

#### `sc`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/sc/tt` | Body: com.xingin.xhs.antispam.entities.TinyTokenApi.a | TinyTokenApi |

#### `search`（27 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/search/fls/ai/history/detail` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, conversation_id, message_id | ShopAiGuideHistoryService |
| `GET` | `/api/search/fls/ai/history/list` | Query: size, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pre_cursor, page_from | ShopAiGuideHistoryService |
| `GET` | `/api/search/fls/ai/stream/tokens` | Query: uuid, msg_id | ShopAiGuidePageApi |
| `GET` | `/api/search/fls/ai/stream/tokens` | Query: uuid, msg_id, from_index | ShopAiGuidePageApi |
| `GET` | `/api/search/fls/filters/v3` | Query: keyword, filters, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, allow_rewrite, with_undertake, extra_info | CommercialSearchServicesV2 |
| `GET` | `/api/search/fls/placeholder` |  | StoreService |
| `GET` | `/api/search/fls/placeholder` | Query: store_id, account_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | ShopSearchService |
| `GET` | `/api/search/fls/products/v3` | Query: keyword, filters, page, size, sort, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, search_id, page_pos, store_id, geo | CommercialSearchServices |
| `GET` | `/api/search/fls/products/v3` | Query: keyword, size, filters, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | CommercialSearchServices |
| `GET` | `/api/search/fls/products/v3` | Query: keyword, size, filters, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | CommercialSearchServicesV2 |
| `GET` | `/api/search/fls/products/v3` | Query: keyword, page, size, sort, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, search_id, store_id, link_source | ShopSearchService |
| `GET` | `/api/search/fls/products/v3` | Query: keyword, page, size, sort, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, search_id, store_id, link_source | ProfileSearchGoodsServices |
| `GET` | `/api/search/fls/products/v5` | Query: keyword, filters, page, size, sort, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, search_id, page_pos, store_id, geo, sku_list, note_list, allow_rewrite, extra_info | CosmosGoodService |
| `GET` | `/api/search/fls/recommend_info/v2` | Query: keyword, search_id, geo, preview_ad | CommercialSearchServicesV2 |
| `GET` | `/api/search/fls/trending/v3` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, placeholder, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SESSION_ID | AliothServices |
| `GET` | `/api/search/fls/trending/v3` | Query: store_id, account_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | ShopSearchService |
| `GET` | `/api/search/v11/common` | Query: keyword, filters_json_str, sort, page, page_size, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, app_search_id, search_session_id, api_extra, page_pos, pin_note_id, allow_rewrite, geo, scene, location_permission, device_level, is_full_request, ads_param, word_request_id, load_type, api_split, note_ids | AliothServices |
| `GET` | `/api/search/v11/dqa/guide/v2/words` | Query: business_type, entities, ext_params, attach_content, session_id, msg_id, biz, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, request_id | DotsApi |
| `GET` | `/api/search/v11/gaokao/filter/switch` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, share_id, table_filter | DotsApi |
| `GET` | `/api/search/v11/gaokao/filter/switch` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, share_id, table_filter | SearchAgentPageApi |
| `POST` | `/api/search/fls/ai/history/update` | Body: qq5.i iVar, kotlin.coroutines.Continuation<? super kotlin.Unit> | ShopAiGuideHistoryService |
| `POST` | `/api/search/fls/ai/query/rec` | Body: zq5.j | ShopAiGuidePageApi |
| `POST` | `/api/search/fls/ai/send/ai` | Body: zq5.n | ShopAiGuidePageApi |
| `POST` | `/api/search/fls/ai/signal` | Body: zq5.p | ShopAiGuidePageApi |
| `POST` | `/api/search/v10/common/filter/select/switch` | Body: txd.k | XYSparkChooseFilterApi |
| `POST` | `/api/search/v11/dqa/signal` | Body: com.xingin.dots.legacy.network.entities.signal.DotsReqDataForPostSignal | DotsApi |
| `POST` | `/api/search/v11/dqa/signal` | Body: iyb.e | SearchAgentPageApi |

#### `security`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/security/antispam/v1/restriction/self-resolve` |  | IRiskService |

#### `sns`（2016 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/api/sns/component/delete_user_checkin` | Query: check_in_id | InteractiveSquareService |
| `DELETE` | `/api/sns/v1/filter/collect` | Query: filter_id | FilterServices |
| `DELETE` | `/api/sns/v1/filter/collect` | Query: filter_id | INnsDetailService |
| `DELETE` | `/api/sns/v1/media/cancel_collect_soundtrack` | Query: soundtrack_id | SameParagraphService |
| `DELETE` | `/api/sns/v1/media/cancel_collect_soundtrack` | Query: soundtrack_id | INnsDetailService |
| `DELETE` | `/api/sns/v1/media/cancel_collect_soundtrack` | Query: soundtrack_id | UserCollectedModel |
| `DELETE` | `/api/sns/v1/media/{music_id}` | Path: music_id | MusicService |
| `DELETE` | `/api/sns/v1/media/{music_id}` | Path: music_id | MusicHeaderService |
| `DELETE` | `/api/sns/v1/media/{music_id}` | Path: music_id | INnsDetailService |
| `DELETE` | `/api/sns/v1/media/{music_id}` | Path: music_id | UserCollectedModel |
| `DELETE` | `/api/sns/v1/note/collection/uncollect` | Query: collection_id, tag_id, source_item_id | CollectionService |
| `DELETE` | `/api/sns/v1/note/collection/uncollect` | Query: collection_id | PortfolioService |
| `DELETE` | `/api/sns/v1/recommend` | Query: target_id, type, note_id, track_id, feedback_type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, homefeed_category | FeedbackService |
| `DELETE` | `/api/sns/v1/recommend` | Query: target_id, type, note_id | NoteDetailService |
| `DELETE` | `/api/sns/v1/user/remarkname/delete` | Query: user_id | CommonUserService |
| `DELETE` | `/api/sns/v2/board` | Query: board_id | CommonBoardService |
| `DELETE` | `/api/sns/v2/message/delete` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | CommonNoteService |
| `DELETE` | `/api/sns/v2/system_service/device/regist` | Query: user_id, code, device_plat_type | PushServices |
| `DELETE` | `/api/sns/v2/user/followings/{user_id}/pins` | Path: user_id; Query: scene, sub_scene | CommonUserService |
| `DELETE` | `/api/sns/v2/user/followings/{user_id}/pins` | Path: user_id | UserServices |
| `DELETE` | `api/sns/v1/recommend` | Query: target_id, type, note_id | ShareOperateService |
| `DELETE` | `api/sns/v1/tag/follow` | Query: oid | TagServices |
| `GET` | `/api/sns/agentspark/dot/chat/history` | Query: biz, session_id, cursor, size | DotsApi |
| `GET` | `/api/sns/agentspark/dot/chat/history` | Query: biz, session_id, cursor, size | DotsPageApi |
| `GET` | `/api/sns/agentspark/dot/guide/words` | Query: business_type, entities | ImageSearchAskGuideWordsApi |
| `GET` | `/api/sns/agentspark/dot/guide/words` | Query: business_type, entities, ext_params, attach_content, session_id, msg_id, biz, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, request_id | DotsApi |
| `GET` | `/api/sns/agentspark/dot/guide/words` | Query: business_type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, session_id, conversation_id, msg_id, ext_params, biz, onebox | DotsApi |
| `GET` | `/api/sns/agentspark/dot/message/status` | Query: biz, session_id, msg_id | DotsApi |
| `GET` | `/api/sns/agentspark/dot/messages/anchor` | Query: anchor_type, session_id, anchor_id, extra, tag, biz | DotsApi |
| `GET` | `/api/sns/agentspark/dot/messages/anchor` | Query: anchor_type, session_id, anchor_id, extra, biz | DotsPageApi |
| `GET` | `/api/sns/agentspark/dot/messages/append` | Query: anchor_type, session_id, anchor_id, extra, biz | DotsApi |
| `GET` | `/api/sns/agentspark/dot/messages/history` | Query: cursor, count, in_order, biz, session_id, tag, no_bubbles | DotsApi |
| `GET` | `/api/sns/agentspark/dot/messages/history` | Query: cursor, count, in_order, biz, session_id | DotsPageApi |
| `GET` | `/api/sns/agentspark/dot/messages/list` | Query: share_id, scene, cursor, count | DotsApi |
| `GET` | `/api/sns/agentspark/dot/messages/reply` | Query: biz, session_id, msg_id, version | DotsApi |
| `GET` | `/api/sns/agentspark/dot/messages/reply` | Query: biz, session_id, msg_id, version | DotsPageApi |
| `GET` | `/api/sns/agentspark/dot/subscription` | Query: cursor, page_size, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS, subscription_id | AgentDotsApi |
| `GET` | `/api/sns/agentspark/dot/subscription/notify/list` | Query: subscription_id, cursor, page_size, in_order, target_msg_id | DotsApi |
| `GET` | `/api/sns/agentspark/dot/summary` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, type | DotsApi |
| `GET` | `/api/sns/agentspark/rec/subscription` |  | DotsApi |
| `GET` | `/api/sns/agentspark/v1/feedback/get_reason_config` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_TASK_ID | DotsApi |
| `GET` | `/api/sns/agentspark/v1/subscription/summary` | Query: subscription_id, cursor, page_size | AgentDotsApi |
| `GET` | `/api/sns/badge/survive/info` | Query: user_id | SimpleServices |
| `GET` | `/api/sns/capa/crowd/exists` | Query: scenes | CrowdService |
| `GET` | `/api/sns/capa/postgw/note_brife_info` | Query: note_id | NoteService |
| `GET` | `/api/sns/capa/servicegw/album/batch_query` | Query: ids, request_count | TemplateRecService |
| `GET` | `/api/sns/capa/servicegw/chapter/result` | Query: video_id | ChapterService |
| `GET` | `/api/sns/capa/servicegw/comment_to_post/info` | Query: comment_id | CommentToPostService |
| `GET` | `/api/sns/capa/servicegw/new_user/retrieve` |  | CommonService |
| `GET` | `/api/sns/capa/servicegw/videoid` | Query: file_key, biz_name | ChapterService |
| `GET` | `/api/sns/capa/support/merge_image` |  | DynamicResourcesService |
| `GET` | `/api/sns/celestial/ai/messages` | Query: domain, biz, turn_id, request_id, start_index, end_index | DotsApi |
| `GET` | `/api/sns/celestial/ai/messages` | Query: domain, biz, turn_id, request_id, start_index, end_index | DotsPageApi |
| `GET` | `/api/sns/celestial/connect/config` | Query: domain, protocols, user_id, device_id | LongLinkDNS |
| `GET` | `/api/sns/celestial/v2/connect/config` | Query: domain, protocols | LongLinkDNS |
| `GET` | `/api/sns/challenge/info` | Query: challenge_id | ChallengeCardService |
| `GET` | `/api/sns/challenge/interaction_challenge_list` |  | InteractiveSquareService |
| `GET` | `/api/sns/challenge/search` | Query: name | ChallengeCardService |
| `GET` | `/api/sns/challenge/search` | Query: name | ChallengeCardService |
| `GET` | `/api/sns/component/checkin` | Query: check_in_id | InteractiveSquareService |
| `GET` | `/api/sns/component/checkin_icon_list` |  | InteractiveSquareService |
| `GET` | `/api/sns/component/customized_checkin_config` |  | InteractiveSquareService |
| `GET` | `/api/sns/component/interaction_checkin_list` |  | InteractiveSquareService |
| `GET` | `/api/sns/component/interaction_secondary_page` |  | InteractiveSquareService |
| `GET` | `/api/sns/component/top_picks` |  | InteractiveSquareService |
| `GET` | `/api/sns/inspiration/2tabconfig` |  | CapaApi |
| `GET` | `/api/sns/inspiration/ai/check` | Query: async_request_id | AIAsyncNetService |
| `GET` | `/api/sns/inspiration/ai/check` | Query: async_request_id | CapaApi |
| `GET` | `/api/sns/inspiration/ai_edit_image/asr_smooth` | Query: asr_text | VoiceInputService |
| `GET` | `/api/sns/inspiration/ai_edit_image/asr_smooth` |  | Capa51AiPhotoShopService |
| `GET` | `/api/sns/inspiration/ai_edit_image/asr_smooth` |  | CNYAiPhotoShopService |
| `GET` | `/api/sns/inspiration/ai_edit_image/asr_smooth` |  | CommentAiPhotoShopService |
| `GET` | `/api/sns/inspiration/ai_edit_image/asr_smooth` |  | ImageEditAiPhotoShopService |
| `GET` | `/api/sns/inspiration/ai_edit_image/asr_smooth` |  | ImAiPhotoShopService |
| `GET` | `/api/sns/inspiration/ai_edit_image/load_info` | Query: biz_type | Capa51AiPhotoShopService |
| `GET` | `/api/sns/inspiration/ai_edit_image/load_info` | Query: biz_type | CNYAiPhotoShopService |
| `GET` | `/api/sns/inspiration/ai_edit_image/load_info` | Query: biz_type | ImageEditAiPhotoShopService |
| `GET` | `/api/sns/inspiration/ai_edit_image/load_info` | Query: biz_type | ImAiPhotoShopService |
| `GET` | `/api/sns/inspiration/ai_edit_image/load_info/comment` | Query: biz_type | CommentAiPhotoShopService |
| `GET` | `/api/sns/inspiration/ai_edit_image/style/page_query` | Query: cursor, extra | Capa51AiPhotoShopService |
| `GET` | `/api/sns/inspiration/ai_edit_image/style/page_query` | Query: cursor, extra | CNYAiPhotoShopService |
| `GET` | `/api/sns/inspiration/ai_edit_image/style/page_query` | Query: cursor, extra | CommentAiPhotoShopService |
| `GET` | `/api/sns/inspiration/ai_edit_image/style/page_query` | Query: cursor, extra | ImageEditAiPhotoShopService |
| `GET` | `/api/sns/inspiration/ai_edit_image/style/page_query` | Query: cursor, extra | ImAiPhotoShopService |
| `GET` | `/api/sns/inspiration/ai_template/check_limit` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AIAsyncNetService |
| `GET` | `/api/sns/inspiration/ai_template/id` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | AiTemplateService |
| `GET` | `/api/sns/inspiration/ai_template/pages` | Query: ai_template_id, category_id, page_size, is_position, version, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AiTemplateService |
| `GET` | `/api/sns/inspiration/ai_template/pages` | Query: ai_template_id, category_id, page_size, is_position, version, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | CapaApi |
| `GET` | `/api/sns/inspiration/asides` |  | TemplateTtsService |
| `GET` | `/api/sns/inspiration/asides` |  | CapaApi |
| `GET` | `/api/sns/inspiration/cny/pre_load/resource` |  | CapaCnyPreloadService |
| `GET` | `/api/sns/inspiration/generate_invite_link` | Query: ai_template_id | AiPortraitGroupPhotoService |
| `GET` | `/api/sns/inspiration/get_online_ai_template_categories` |  | AiTemplateService |
| `GET` | `/api/sns/inspiration/get_user_friend_list` |  | AiPortraitGroupPhotoService |
| `GET` | `/api/sns/inspiration/graffiti_palettes` | Query: last_palette_id, page_size, target_palette_id | CapaApi |
| `GET` | `/api/sns/inspiration/graffiti_palettes_v2` | Query: last_palette_category_id, target_palette_id, page_size | GraffitiPlayListService |
| `GET` | `/api/sns/inspiration/image_template/is_recent_publish` | Query: user_id | CapaTemplateResourceService |
| `GET` | `/api/sns/inspiration/image_template/is_recent_publish` | Query: user_id | ImageTemplatePanelOpenService |
| `GET` | `/api/sns/inspiration/image_template/is_recent_publish` | Query: user_id | CapaApi |
| `GET` | `/api/sns/inspiration/long_text/layout_json` | Query: request_id, version_id | LongNoteService |
| `GET` | `/api/sns/inspiration/post_inspiration` |  | InteractiveEntranceService |
| `GET` | `/api/sns/inspiration/post_inspiration` |  | InteractiveEntranceService |
| `GET` | `/api/sns/inspiration/search/associated_word` | Query: keyword | ImageTemplateService |
| `GET` | `/api/sns/inspiration/search/word_entry` |  | ImageTemplateService |
| `GET` | `/api/sns/inspiration/storyline/asides` |  | TemplateTtsService |
| `GET` | `/api/sns/inspiration/storyline/check/daily_count` |  | StorylineApiService |
| `GET` | `/api/sns/inspiration/storyline/msg` | Query: request_id, index | StorylineApiService |
| `GET` | `/api/sns/inspiration/storyline/text_smooth` | Query: asr_text | StorylineApiService |
| `GET` | `/api/sns/inspiration/template/pop_window` |  | TemplateGuideService |
| `GET` | `/api/sns/inspiration/text2img/load/package` |  | TTiConfigV2Service |
| `GET` | `/api/sns/inspiration/user/virtual_image` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AIAsyncNetService |
| `GET` | `/api/sns/inspiration/user/virtual_image` | Query: ai_template_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AIAsyncNetService |
| `GET` | `/api/sns/inspiration/v2/transitions` |  | VideoTransitionService |
| `GET` | `/api/sns/inspiration/v2/transitions` |  | CapaApi |
| `GET` | `/api/sns/inspiration/voice_clone/get_voice_list` |  | VoiceCloneService |
| `GET` | `/api/sns/octopus/router/longlinkconfig` | Query: domain, field, userId | MsgServices |
| `GET` | `/api/sns/open/note/variants` | Query: goods_id, goods_seller_type | GoodsSettingRepo |
| `GET` | `/api/sns/prof/business_card/list` | Query: idList | IMAcquisitionToolService |
| `GET` | `/api/sns/prof/business_card/list` | Query: pageNum, pageSize | IMAcquisitionToolService |
| `GET` | `/api/sns/prof/chat_product/query_config` |  | IMAcquisitionToolService |
| `GET` | `/api/sns/reach/msg/query` |  | ReachMessageService |
| `GET` | `/api/sns/red/live/app/base/v1/before-stop-info` | Query: room_id | AlphaApiService |
| `GET` | `/api/sns/red/live/app/base/v1/host/room_config` | Query: room_id | AlphaConfigLiveRoomService |
| `GET` | `/api/sns/red/live/app/base/v1/query_gambit_by_roomid` | Query: room_id; Header: x-ratelimit-meta | AlphaAudienceTopicService |
| `GET` | `/api/sns/red/live/app/base/v1/room/aggregate_business_info` | Query: room_id, host_id; Header: x-ratelimit-meta | AlphaConfigLiveRoomService |
| `GET` | `/api/sns/red/live/app/fansgroup/v1/detail` | Query: room_id, host_id | ILiveFansGroupApiService |
| `GET` | `/api/sns/red/live/app/fansgroup/v1/list_fans` | Query: host_id | ILiveFansGroupApiService |
| `GET` | `/api/sns/red/live/app/fansgroup/v1/list_privilege` | Query: host_id | ILiveFansGroupApiService |
| `GET` | `/api/sns/red/live/app/fansgroup/v1/user_relation_info` | Query: room_id, host_id | ILiveFansGroupApiService |
| `GET` | `/api/sns/red/live/app/feed/v1/browsing_history` | Query: room_ids | BrowsingHistoryLiveService |
| `GET` | `/api/sns/red/live/app/feed/v1/doublefeed` | Query: cursor_score, size, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pre_source, extra_info | AlphaAudienceTopicService |
| `GET` | `/api/sns/red/live/app/gift/v1/worldcup/pk/info` | Query: room_id | WorldCupCallApiService |
| `GET` | `/api/sns/red/live/app/group_live/entrance` | Query: room_id | AlphaGroupLiveAPIService |
| `GET` | `/api/sns/red/live/app/group_pk/v1/current_pk` | Query: room_id | LiveGroupLivePKApiService |
| `GET` | `/api/sns/red/live/app/pay/v1/charge_panel` | Query: biz_scene, need_coins | AlphaAmountLiveGoService |
| `GET` | `/api/sns/red/live/app/room/v1/leave_popup` | Query: room_id | AlphaConfigLiveRoomService |
| `GET` | `/api/sns/red/live/app/v1/ecology/flow_card_panel` | Query: room_id, host_id, type, enabled, page, page_size | AlphaSettingLiveGoService |
| `GET` | `/api/sns/red/live/app/v1/livegoods/permission/user/list` | Query: host_id | AlphaGoodsProductService |
| `GET` | `/api/sns/red/live/app/v1/mall/live_goods_category/list` | Query: room_id, room_source; Header: x-ratelimit-meta | AlphaGoodsLiveMallService |
| `GET` | `/api/sns/red/live/app/v1/mall/prelive/pool_goods_list_by_id` | Query: host_id, category_id, type, page, page_size | LiveGoodsCategoryService |
| `GET` | `/api/sns/red/live/app/v1/mall/room/config` | Query: room_id | AlphaGoodsLiveMallService |
| `GET` | `/api/sns/red/live/app/v1/room/gambit_list` | Query: content_type, obs, game | AlphaApiService |
| `GET` | `/api/sns/red/live/app/v1/room/recent_poi_info` | Query: longitude, latitude | AlphaSettingLiveGoService |
| `GET` | `/api/sns/red/live/app/v1/room/resource/get` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID; Header: x-ratelimit-meta | LiveEffectAPIService |
| `GET` | `/api/sns/red/livemall/app/shopping_bag/v1/rolling_msg` | Query: host_id, room_id | AlphaGoodsBagService |
| `GET` | `/api/sns/red/livemall/manager/app/live_goods_category/v1/list` | Query: room_id, host_id, plan_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | LiveGoodsCategoryService |
| `GET` | `/api/sns/red/livemall/manager/app/pool_goods/v1/category/belong` | Query: room_id, host_id, plan_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | LiveGoodsCategoryService |
| `GET` | `/api/sns/search/v1/dqa/complex/detail` | Query: conversation_id, card_id, query, searchid, business_type, geo, anchor_id, anchor_type, is_dots | DotsApi |
| `GET` | `/api/sns/search/v1/dqa/complex/detail` | Query: conversation_id, card_id, query, searchid, business_type, geo | SearchAgentPageApi |
| `GET` | `/api/sns/search/v1/dqa/onebox/detail` | Query: conversation_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, page_from, size, search_id, type, query, version, result_version, message_id, share_id, chat_status, scene, anchor_id, anchor_type, is_dots | DotsApi |
| `GET` | `/api/sns/search/v1/dqa/onebox/detail` | Query: conversation_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, page_from, size, search_id, type, query, version, result_version, message_id, share_id, chat_status, scene | SearchAgentPageApi |
| `GET` | `/api/sns/search/v1/dqa/share/details` | Query: share_id | DotsApi |
| `GET` | `/api/sns/search/v1/dqa/share/details` | Query: share_id | SearchAgentPageApi |
| `GET` | `/api/sns/search/v1/dqa/share/link` | Query: file_id, share_link | DotsApi |
| `GET` | `/api/sns/search/v1/dqa/share/link` | Query: file_id, share_link | SearchAgentPageApi |
| `GET` | `/api/sns/search/v1/dqa/stream/tokens` | Query: conversation_id, message_id, index_in_conversation, is_dots | SearchAgentPageApi |
| `GET` | `/api/sns/search/v1/dqa/stream/tokens` | Query: conversation_id, message_id, index_in_conversation | SearchAgentPageApi |
| `GET` | `/api/sns/sport/sticker/user/info` |  | MaterialAPIService |
| `GET` | `/api/sns/user_cache/follow/cache` | Query: cursor, size, pull_type | LocalRelationServices |
| `GET` | `/api/sns/user_cache/follow/rotate` | Query: cursor, count, update_time | LocalRelationServices |
| `GET` | `/api/sns/user_cache/follow_cache_check` | Query: cursor, count, update_time | LocalRelationServices |
| `GET` | `/api/sns/user_cache/pull_offline` | Query: cursor_user_id | LocalRelationServices |
| `GET` | `/api/sns/v1/account/intervention` | Query: business_code, user_id | IRiskService |
| `GET` | `/api/sns/v1/account/phone-binding-dialog` |  | IRiskService |
| `GET` | `/api/sns/v1/board/follow` | Query: oid | CommonBoardService |
| `GET` | `/api/sns/v1/board/unfollow` | Query: oid | CommonBoardService |
| `GET` | `/api/sns/v1/board/user` | Query: user_id, page, num, with_participate_board | CommonBoardService |
| `GET` | `/api/sns/v1/circle/base` | Query: circle_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, is_first_request | RedCircleHomeService |
| `GET` | `/api/sns/v1/circle/comment/video/download` | Query: video_id, video_type | ICircleMediaSaveService |
| `GET` | `/api/sns/v1/circle/getpartition` | Query: circle_id, new_agreement | CirclePartitionApiService |
| `GET` | `/api/sns/v1/circle/notification_bar` | Query: circle_id | RedCircleHomeService |
| `GET` | `/api/sns/v1/circle/post/video/download` | Query: video_id, video_type | ICircleMediaSaveService |
| `GET` | `/api/sns/v1/circle/quote/post_option` | Query: circle_id, post_id | CircleApiService |
| `GET` | `/api/sns/v1/circle/refer/info` | Query: ref_type, ref_id | CircleRefContentApiService |
| `GET` | `/api/sns/v1/cny_new/get_user_avatar_icon` | Query: user_id | UserServices |
| `GET` | `/api/sns/v1/cny_new/get_user_avatar_icon_switch_status` | Query: user_id | UserServices |
| `GET` | `/api/sns/v1/comment/delete` | Query: discovery, oid | CommentService |
| `GET` | `/api/sns/v1/comment/delete` | Query: discovery, oid | CommonCommentService |
| `GET` | `/api/sns/v1/comment/dislike` | Query: comment_id | CommentService |
| `GET` | `/api/sns/v1/comment/dislike` | Query: comment_id | CommonCommentService |
| `GET` | `/api/sns/v1/comment/like` | Query: comment_id | CommonCommentService |
| `GET` | `/api/sns/v1/content/dislike/get_reason_config` | Query: object_type, object_id, page_instance | DotsApi |
| `GET` | `/api/sns/v1/content/frame_config` | Query: has_dot_permission | HomeNavigationService |
| `GET` | `/api/sns/v1/content/navigator` | Query: area_type, common_params | GuideService |
| `GET` | `/api/sns/v1/content/navigator` | Query: area_type, common_params | RedDotServices |
| `GET` | `/api/sns/v1/content/video/get_ads_info` | Query: note_id, ads_track_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, container_type, preview_ad, loaded_ad | InstreamAdApiService |
| `GET` | `/api/sns/v1/effect/image` |  | MaterialAPIService |
| `GET` | `/api/sns/v1/effect/image/list` |  | MaterialAPIService |
| `GET` | `/api/sns/v1/effect/video` | Query: fragment_count, com.xingin.capa.feature_model.session.UploadImageBean.KEY_IMAGE_MATERIAL, recommend_fragment_infos | MaterialAPIService |
| `GET` | `/api/sns/v1/effect/video` |  | MaterialAPIService |
| `GET` | `/api/sns/v1/file/faved` | Query: user_id, cursor, num | ProfileCollectDocumentApi |
| `GET` | `/api/sns/v1/filter/faved/filters` | Query: page, page_size, user_id | CollectedNnsServices |
| `GET` | `/api/sns/v1/filter/faved/filters` | Query: page, page_size, user_id | UserCollectedModel |
| `GET` | `/api/sns/v1/followfeed/recommend` | Query: cursor, num, use_contact | FollowFeedService |
| `GET` | `/api/sns/v1/followings/reddot` | Query: isStartUp | FollowFeedService |
| `GET` | `/api/sns/v1/followings/variousfeed` | Query: user_id, refresh_type, liveStatus, room_id, has_red_circle, track_id | NoteDetailService |
| `GET` | `/api/sns/v1/guide/home` |  | NoteGuideService |
| `GET` | `/api/sns/v1/guide/onboard` |  | CommonService |
| `GET` | `/api/sns/v1/homefeed/guide` | Query: type | HomeFeedGuideService |
| `GET` | `/api/sns/v1/im/get_recent_chats` |  | MsgServices |
| `GET` | `/api/sns/v1/im/get_recent_chats_v2` | Query: note_id, author_id | MsgServices |
| `GET` | `/api/sns/v1/interaction/backup/comment/page/l1` | Query: note_id, start, num, show_priority_sub_comments, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, top_comment_id, top_comment_id_v2, exclude_comment_ids, force_master, preload_scene, page_context, sort_strategy, request_comment_list_type | CommentService |
| `GET` | `/api/sns/v1/interaction/comment/detail` | Query: note_id, comment_id | CommentService |
| `GET` | `/api/sns/v1/interaction/comment/extension/note_layer/page` | Query: type, start, note_id | CommentService |
| `GET` | `/api/sns/v1/interaction/comment/extension/panel` | Query: note_id, target_comment_id | CommentServices |
| `GET` | `/api/sns/v1/interaction/comment/l1/sub/page` | Query: scene, note_id, root_comment_id, top_comment_id, start, num, filter_comment_ids, container | CommentService |
| `GET` | `/api/sns/v1/interaction/comment/merged/l1/page` | Query: note_id, type, start, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, page_context, container | CommentService |
| `GET` | `/api/sns/v1/interaction/comment/user/interact/page` | Query: interact_type, target_user_id, cursor, num | ProfileHistoryCommentService |
| `GET` | `/api/sns/v1/interaction/comment/user/interact/page` | Query: interact_type, target_user_id, cursor, num | CommentService |
| `GET` | `/api/sns/v1/interaction/comment/video/download` | Query: note_id, comment_id, media_type, video_id | CommentMediaBrowserService |
| `GET` | `/api/sns/v1/interaction/note/like_collect/list` | Query: note_id, top_relation_id, top_relation_type, cursor | AgreeOrFollowServices |
| `GET` | `/api/sns/v1/interaction/note/like_fav/list` | Query: note_id, top_relation_id, top_relation_type, cursor | AgreeOrFollowServices |
| `GET` | `/api/sns/v1/interaction/sing/chain/result` | Query: type, note_id, comment_id | VoicePlayBarService |
| `GET` | `/api/sns/v1/interaction/user/comment/posted` | Query: cursor, force_master | CommentService |
| `GET` | `/api/sns/v1/link/search` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, type, name, subname, note_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | HashTagLinkHandler |
| `GET` | `/api/sns/v1/link/search` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, type, name, subname, note_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | CommentService |
| `GET` | `/api/sns/v1/live/activity/people_push_link` | Query: push_id | AlphaConfigService |
| `GET` | `/api/sns/v1/live/course/{room_id}/join_check` | Path: room_id | AlphaUserService |
| `GET` | `/api/sns/v1/live/fans_group/fans_list` | Query: room_id, host_user_id, page, size | AlphaFansLiveMallService |
| `GET` | `/api/sns/v1/live/fans_group/info` | Query: is_host, host_user_id | AlphaFansLiveMallService |
| `GET` | `/api/sns/v1/live/fans_group/info` | Query: is_host, host_user_id | AlphaFansService |
| `GET` | `/api/sns/v1/live/fans_group/my_privileges` | Query: host_user_id | AlphaFansLiveMallService |
| `GET` | `/api/sns/v1/live/fans_group/my_privileges` | Query: host_user_id | AlphaFansService |
| `GET` | `/api/sns/v1/live/fans_group/my_privileges` | Query: host_user_id | AlphaGoodsFansService |
| `GET` | `/api/sns/v1/live/fans_group/{room_id}/list` | Path: room_id; Query: host_user_id, page, size | AlphaFansService |
| `GET` | `/api/sns/v1/live/feed/waterfall` | Query: room_id, page_source, pos, tag_source, new_flag, extra_info; Header: x-ratelimit-meta | AlphaConfigLiveRoomService |
| `GET` | `/api/sns/v1/live/gift/info` | Query: source_id | AlphaGiftService |
| `GET` | `/api/sns/v1/live/gift_panel` | Query: host_id, room_id | AlphaGiftMultiLiveService |
| `GET` | `/api/sns/v1/live/new/gift_panel` | Query: host_id, room_id | AlphaGiftMultiLiveService |
| `GET` | `/api/sns/v1/live/new/gift_panel` | Query: host_id, room_id | AlphaGiftMultiLiveService |
| `GET` | `/api/sns/v1/live/obs_code` | Query: room_id | AlphaConfigService |
| `GET` | `/api/sns/v1/live/room_auth` | Query: user_id | AlphaConfigService |
| `GET` | `/api/sns/v1/live/trailer/query/by_note_id` | Query: note_id | LiveRepository |
| `GET` | `/api/sns/v1/live/trailer/query/by_note_id` | Query: note_id | LiveTrailerRepository |
| `GET` | `/api/sns/v1/live/worldcup/gift_panel` | Query: host_id, room_id, scene | AlphaGiftMultiLiveService |
| `GET` | `/api/sns/v1/live/worldcup/gift_panel` | Query: host_id, room_id, scene | AlphaGiftMultiLiveService |
| `GET` | `/api/sns/v1/live/{room_id}/before_stop` | Path: room_id | AlphaConfigService |
| `GET` | `/api/sns/v1/live/{room_id}/obs_code` | Path: room_id | AlphaConfigService |
| `GET` | `/api/sns/v1/live/{room_id}/recommend` | Path: room_id; Query: recommend_count | AlphaUserService |
| `GET` | `/api/sns/v1/local/poi/bar` | Query: geo | LocalFeedService |
| `GET` | `/api/sns/v1/localfeed/liveshooting_bar` | Query: geo, note_id, enable_location_permission | LocalFeedService |
| `GET` | `/api/sns/v1/localfeed/tab_config` | Query: enable_location_permission, geo, city_name, country_name, coordinate_type | LocalFeedService |
| `GET` | `/api/sns/v1/mappoi/footprints/entry` | Query: user_id | VisitedServices |
| `GET` | `/api/sns/v1/mappoi/unimap/footprints/timeline` | Query: user_id, longitude, latitude, tag_id, page, page_size, cursor_id | VisitedServices |
| `GET` | `/api/sns/v1/media/cover_calculate` | Query: file_id, type | CapaApi |
| `GET` | `/api/sns/v1/media/faved/bgms` |  | MusicService |
| `GET` | `/api/sns/v1/media/faved/media` |  | MusicService |
| `GET` | `/api/sns/v1/media/faved/mediav2` | Query: target_user_id, page_num | UserCollectedModel |
| `GET` | `/api/sns/v1/media/filter_tag_list` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | FilterServices |
| `GET` | `/api/sns/v1/media/generate_watercolor` | Query: fileid, type | WaterColorService |
| `GET` | `/api/sns/v1/media/local_music` |  | MusicService |
| `GET` | `/api/sns/v1/media/music/{id}` | Path: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | CommonService |
| `GET` | `/api/sns/v1/media/poi/{id}` | Path: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | PoiService |
| `GET` | `/api/sns/v1/media/prop_colls` | Query: from, isNewProp, type | CommonService |
| `GET` | `/api/sns/v1/media/prop_colls_v2` | Query: from, isNewProp, type, cameraPosition | PropService |
| `GET` | `/api/sns/v1/media/prop_info` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | SameParagraphService |
| `GET` | `/api/sns/v1/media/soundtrack` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | CommonService |
| `GET` | `/api/sns/v1/media/soundtrack_info` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | SameParagraphService |
| `GET` | `/api/sns/v1/media/sticker/{id}` | Path: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | NeptuneService |
| `GET` | `/api/sns/v1/media/stickers` | Query: business, image_info, type, support_new_water_mark, activity_source, channel | MaterialAPIService |
| `GET` | `/api/sns/v1/media/stickers/sticker_index_feeds` | Query: business, type, tab_infos, channel | MaterialAPIService |
| `GET` | `/api/sns/v1/media/stickers/sticker_index_head` | Query: business, type, channel | MaterialAPIService |
| `GET` | `/api/sns/v1/media/tab_guide/list` |  | CapaApi |
| `GET` | `/api/sns/v1/media/tab_guide_list` |  | CapaConfigService |
| `GET` | `/api/sns/v1/media/use_prop` | Query: prop_id | CommonService |
| `GET` | `/api/sns/v1/media/use_prop` | Query: prop_id | NoteDetailService |
| `GET` | `/api/sns/v1/media/video_models` |  | StyleService |
| `GET` | `/api/sns/v1/media/{filterTypeId}/filter_list` | Path: filterTypeId; Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, page, page_size | FilterServices |
| `GET` | `/api/sns/v1/message/send_large_file_msg` |  | NoteService |
| `GET` | `/api/sns/v1/mp/red/apps/{appId}/follow_status` | Path: appId; Query: sid | IMPFollowService |
| `GET` | `/api/sns/v1/note/atme` | Query: user_id, cursor, page_size | AtServers |
| `GET` | `/api/sns/v1/note/atme/manage` | Query: cursor, page_size, filter_note_id | TaggedMeService |
| `GET` | `/api/sns/v1/note/atme/toggle` |  | TaggedMeService |
| `GET` | `/api/sns/v1/note/basic/homefeed` | Query: cursor_score, num, enable_update_note, refresh_type | ExploreService |
| `GET` | `/api/sns/v1/note/beautys` | Query: entrance_type | MaterialAPIService |
| `GET` | `/api/sns/v1/note/beautys` | Query: entrance_type | CommonService |
| `GET` | `/api/sns/v1/note/beautys_group/abgroup` | Query: capture_beauty_flag, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | MaterialAPIService |
| `GET` | `/api/sns/v1/note/co_creation/list` | Query: co_author_id, note_id | NoteDetailService |
| `GET` | `/api/sns/v1/note/collection/candidate_notes` | Query: cursor | CollectionService |
| `GET` | `/api/sns/v1/note/collection/candidate_notes` | Query: cursor | PortfolioService |
| `GET` | `/api/sns/v1/note/collection/fav/list` | Query: user_id, cursor, num | UserCollectedModel |
| `GET` | `/api/sns/v1/note/collection/info` | Query: collection_id, device_orientation, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | CollectionService |
| `GET` | `/api/sns/v1/note/collection/info` | Query: collection_id | PortfolioService |
| `GET` | `/api/sns/v1/note/collection/list` | Query: user_id, cursor, com.alipay.ams.component.sdk.InternalConfigKeys.ADDRESS_ELEMENT_MODE | ProfileServices |
| `GET` | `/api/sns/v1/note/collection/list` | Query: user_id, cursor, com.alipay.ams.component.sdk.InternalConfigKeys.ADDRESS_ELEMENT_MODE | ProfileServices |
| `GET` | `/api/sns/v1/note/collection/list_note` | Query: collection_id, cursor, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, order_type, inclusive, num | PortfolioService |
| `GET` | `/api/sns/v1/note/collection/list_note` | Query: collection_id, cursor, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | PortfolioService |
| `GET` | `/api/sns/v1/note/collection/list_note_v2` | Query: collection_id, cursor, inclusive, num, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, order_type, device_orientation | CollectionService |
| `GET` | `/api/sns/v1/note/collection/list_note_v2` | Query: collection_id, cursor, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | CollectionService |
| `GET` | `/api/sns/v1/note/collection/next_note` | Query: collection_id, cursor, source_param | CollectionNextNoteProvider |
| `GET` | `/api/sns/v1/note/collection/query_sketch_container_bottom_bar` | Query: collection_id | BottomBarService |
| `GET` | `/api/sns/v1/note/collection/query_sketch_order` | Query: order_id | OrderDetailService |
| `GET` | `/api/sns/v1/note/collection/query_sketch_payment_panel` | Query: note_id | CollectionService |
| `GET` | `/api/sns/v1/note/debug/{note_id}` | Path: note_id | VideoDebugInfo |
| `GET` | `/api/sns/v1/note/detailfeed/preload` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, data, ext | NoteDetailService |
| `GET` | `/api/sns/v1/note/dualfeed` |  | VideoTabService |
| `GET` | `/api/sns/v1/note/faved` | Query: user_id, cursor, num, type | UserCollectedModel |
| `GET` | `/api/sns/v1/note/faved` | Query: user_id, cursor, num | UserCollectedModel |
| `GET` | `/api/sns/v1/note/filters` | Query: v, activity_source | MaterialAPIService |
| `GET` | `/api/sns/v1/note/get_video_feedback_card` | Query: note_id, video_type, author_name | FeedbackService |
| `GET` | `/api/sns/v1/note/help_after_post/invite/list` | Query: note_id | InviteService |
| `GET` | `/api/sns/v1/note/here/list` | Query: note_id, cursor_id, page_size, top_user_ids | LiveShootingService |
| `GET` | `/api/sns/v1/note/here/scrolling_message_list` | Query: note_id | LiveShootingService |
| `GET` | `/api/sns/v1/note/history_records` | Query: note_items, need_err | BrowsingHistoryService |
| `GET` | `/api/sns/v1/note/imagefeed` | Query: note_id, page, has_ads_tag, num, fetch_mode, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, source_scene, ads_track_id, ads_track_url, from_rec_local, extra_params, biz_ext_json | NoteDetailService |
| `GET` | `/api/sns/v1/note/imagefeed` | Query: note_id, page, has_ads_tag, num, fetch_mode, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, source_scene, ads_track_id, ads_track_url, from_rec_local, extra_params, biz_ext_json | NoteDetailService |
| `GET` | `/api/sns/v1/note/imagefeed/get_remain_images` | Query: note_id, biz_type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, biz_id, screen_width, screen_height | NoteDetailService |
| `GET` | `/api/sns/v1/note/liked` | Query: user_id, cursor, num, type | UserNoteLikeModel |
| `GET` | `/api/sns/v1/note/liked` | Query: user_id, cursor, num | UserNoteLikeModel |
| `GET` | `/api/sns/v1/note/multifeed` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, content_scene, fetch_mode, refresh_type, cursor_score, num, source_params, device_params | PodcastListenLaterApiService |
| `GET` | `/api/sns/v1/note/multifeed` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, content_scene, source_item_id, refresh_type, cursor_score, num, source_params, device_params, unread_params, rec_extra_params, geo, fetch_mode | PodcastApiService |
| `GET` | `/api/sns/v1/note/next_step/activity` | Query: note_id | NoteCampaignService |
| `GET` | `/api/sns/v1/note/next_step/layer/feed` | Query: nns_id, nns_type, sort_type, cursor, num, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, note_id, include_note_ids | INnsDetailService |
| `GET` | `/api/sns/v1/note/next_step/layer/info` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, type, source_note_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, second_source, extra_params | INnsDetailV2Service |
| `GET` | `/api/sns/v1/note/nice/list_v2` | Query: note_id, top_user_ids, scene_id, cursor_id, page_size, cur_page, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, framework, biz_context | NiceVideoService |
| `GET` | `/api/sns/v1/note/post_note_notice` |  | CommonService |
| `GET` | `/api/sns/v1/note/product_review` | Query: note_id, context, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | MatrixApi |
| `GET` | `/api/sns/v1/note/product_review` | Query: note_id, context, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | NoteDetailService |
| `GET` | `/api/sns/v1/note/tabfeed` |  | VideoTabService |
| `GET` | `/api/sns/v1/note/transitions` |  | CapaTemplateResourceService |
| `GET` | `/api/sns/v1/note/transitions` |  | CapaApi |
| `GET` | `/api/sns/v1/note/transitions/id` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, type | TemplateResourceService |
| `GET` | `/api/sns/v1/note/transitions/id` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, type | CapaTemplateResourceService |
| `GET` | `/api/sns/v1/note/transitions/id` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, type | CapaApi |
| `GET` | `/api/sns/v1/note/user/page/search` | Query: user_id, type, cursor, keyword, search_id, page_size | ProfileSearchNotesServices |
| `GET` | `/api/sns/v1/note/variousfeed` | Query: note_id, fetch_mode, cursor_score, num, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, source_params, guide_params | VideoFeedNetService |
| `GET` | `/api/sns/v1/note/venuefeed` | Query: source_params, device_params, cursor_score | LiveShootingFeedNetService |
| `GET` | `/api/sns/v1/note/video/marks` | Query: note_id, geo | NoteService |
| `GET` | `/api/sns/v1/note/video/marks/dialog` | Query: note_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, is_out_of_china | MarkDialogService |
| `GET` | `/api/sns/v1/note/video_config_check` |  | ColdStartConfigService |
| `GET` | `/api/sns/v1/note/video_finished` | Query: note_id, note_attributes | NoteDetailService |
| `GET` | `/api/sns/v1/note/widget/query_interact` | Query: widget_id | InteractComponentService |
| `GET` | `/api/sns/v1/note/widget/query_interact` | Query: widget_id | InteractComponentService |
| `GET` | `/api/sns/v1/onboarding/widget/common` |  | WidgetServices |
| `GET` | `/api/sns/v1/onboarding/widget/dress` |  | WidgetServices |
| `GET` | `/api/sns/v1/onboarding/widget/fish_moment` |  | WidgetServices |
| `GET` | `/api/sns/v1/onboarding/widget/fish_moment` |  | WidgetServices |
| `GET` | `/api/sns/v1/onboarding/widget/photography` |  | WidgetServices |
| `GET` | `/api/sns/v1/onboarding/widget/red_calendar` |  | WidgetServices |
| `GET` | `/api/sns/v1/onboarding/widget/tool` |  | WidgetServices |
| `GET` | `/api/sns/v1/page/music/get_music_header` | Query: music_id | MusicHeaderService |
| `GET` | `/api/sns/v1/page/music/search_music_notes` | Query: music_id, page, sort, page_size | MusicNoteService |
| `GET` | `/api/sns/v1/podcast/notes/history` | Query: target_uid, view_uid, cursor, num, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | PodcastListenLaterApiService |
| `GET` | `/api/sns/v1/search/doc/preview` | Query: doc_id | DownloadService |
| `GET` | `/api/sns/v1/search/doc/preview` | Query: doc_id | DocumentPreviewPageApi |
| `GET` | `/api/sns/v1/search/hot_list` |  | AliothServices |
| `GET` | `/api/sns/v1/search/qa_trending` |  | QaTrendingNetService |
| `GET` | `/api/sns/v1/search/queryrec/note` | Query: type, query, note_id, search_id, source_from, entire_source_info, dwell_time, last_query_time, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_POSITION, last_position, last_related_pos | AliothServices |
| `GET` | `/api/sns/v1/search/queryrec/wyw/longpress` | Query: type, content, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_POSITION | DotsApi |
| `GET` | `/api/sns/v1/search/queryrec/wyw/longpress` | Query: type, content, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_POSITION | SearchAgentPageApi |
| `GET` | `/api/sns/v1/search/recommend_guess` | Query: query, word_request_situation, pin_word, last1_query, last1_query_time | AliothApi |
| `GET` | `/api/sns/v1/search/star_signal` | Query: keyword | AliothServices |
| `GET` | `/api/sns/v1/search/user/info` | Query: user_ids | CommonService |
| `GET` | `/api/sns/v1/shopping/ai_guide/history` | Query: conversation_id, page, size | ShopAiGuidePageApi |
| `GET` | `/api/sns/v1/system/cold_start_config` | Query: need_user_info, has_displayed_translation_guide, client_public_key_base64 | ColdStartConfigService |
| `GET` | `/api/sns/v1/system/device_type` | Query: device_model | DeviceInfoServices |
| `GET` | `/api/sns/v1/system/migration_config` |  | ColdStartConfigService |
| `GET` | `/api/sns/v1/system/service/ui/config` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | HomeNavigationService |
| `GET` | `/api/sns/v1/system_service/check_code` | Query: phone, zone, code, type | AccountApi |
| `GET` | `/api/sns/v1/system_service/check_code` | Query: phone, zone, code, type | IVerifyCodeService |
| `GET` | `/api/sns/v1/system_service/check_code` | Query: secure | IVerifyCodeService |
| `GET` | `/api/sns/v1/system_service/check_code` | Query: phone, zone, code, type | GrowthApi |
| `GET` | `/api/sns/v1/system_service/launch` |  | InfraApi |
| `GET` | `/api/sns/v1/system_service/popup_window` | Query: use_contact, pymk_appeared | DialogModel |
| `GET` | `/api/sns/v1/system_service/promotion_info` |  | AboutService |
| `GET` | `/api/sns/v1/system_service/push/switch/get_switch_id` | Query: user_id, platform, switch_id | MsgServices |
| `GET` | `/api/sns/v1/system_service/qcloud_filename` | Query: type, num | TokenService |
| `GET` | `/api/sns/v1/system_service/question/send_feedback` | Query: question_version_id | QuestionServices |
| `GET` | `/api/sns/v1/system_service/report/scene` | Query: scene_code | ReportService |
| `GET` | `/api/sns/v1/system_service/stickers/neptune` |  | NeptuneService |
| `GET` | `/api/sns/v1/system_service/track_flag` |  | GrowthApi |
| `GET` | `/api/sns/v1/system_service/vfc_code` | Query: phone, zone, type, app_type, verification_channel, whatsapp_installed | IVerifyCodeService |
| `GET` | `/api/sns/v1/system_service/vfc_code` | Query: secure, app_type, verification_channel, whatsapp_installed | IVerifyCodeService |
| `GET` | `/api/sns/v1/system_service/vfc_code` | Query: phone, zone, type | GrowthApi |
| `GET` | `/api/sns/v1/tag/reobpage` | Query: ug_role | LoginServices |
| `GET` | `/api/sns/v1/tag/user` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | PageService |
| `GET` | `/api/sns/v1/tag/user/{user_id}/collected` | Path: user_id; Query: page, page_size | UserCollectedModel |
| `GET` | `/api/sns/v1/tag/{type}` | Path: type; Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | PageService |
| `GET` | `/api/sns/v1/topic/search_tab` | Query: search_word, search_id, page, page_size | AliothServices |
| `GET` | `/api/sns/v1/topic/unfollow` | Query: topic_id, topic_name, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AliothServices |
| `GET` | `/api/sns/v1/topic/unfollow` | Query: topic_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | CommonUserService |
| `GET` | `/api/sns/v1/user/at/recent` | Query: oid, start | AtUserServices |
| `GET` | `/api/sns/v1/user/collect_filter` | Query: user_id, post_later_flag | UserCollectedModel |
| `GET` | `/api/sns/v1/user/collected/note/search` | Query: keyword, search_id, page, page_size | UserCollectedModel |
| `GET` | `/api/sns/v1/user/common_follows` | Query: user_id | RelationMergeModel |
| `GET` | `/api/sns/v1/user/faved/image/template` | Query: cursor, num, user_id | CollectedNnsServices |
| `GET` | `/api/sns/v1/user/faved/template` | Query: cursor, num, user_id | CollectedNnsServices |
| `GET` | `/api/sns/v1/user/followers` | Query: user_id, cursor | UserApi |
| `GET` | `/api/sns/v1/user/followings` | Query: user_id, cursor, order | UserApi |
| `GET` | `/api/sns/v1/user/getUserTaxonomy` |  | CapaApi |
| `GET` | `/api/sns/v1/user/identities` |  | UserServices |
| `GET` | `/api/sns/v1/user/info/sticker/list` | Query: sticker_config_id | StickerServices |
| `GET` | `/api/sns/v1/user/login/devices` |  | SettingLoginDeviceInfoServices |
| `GET` | `/api/sns/v1/user/login/onboardingextra` | Header: deviceId | GrowthApi |
| `GET` | `/api/sns/v1/user/page/collect_info` | Query: user_id, type, page_index, page_size, is_out_of_china, geo, cursor | UserCollectedModel |
| `GET` | `/api/sns/v1/user/privacy/daily/setting_config` | Query: user_id | DailyService |
| `GET` | `/api/sns/v1/user/profile_pre_edit` |  | UserServices |
| `GET` | `/api/sns/v1/user/release_inspiration` | Query: user_id | UserCollectedModel |
| `GET` | `/api/sns/v1/user/target_user_privacy` | Query: uid | RelationMergeModel |
| `GET` | `/api/sns/v1/user/unfollow` | Query: room_id, oid, scene, sub_scene, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | CommonUserService |
| `GET` | `/api/sns/v1/user/unfollow` | Query: oid, scene, sub_scene | CommonUserService |
| `GET` | `/api/sns/v1/user/unfollow` | Query: oid, scene, sub_scene | CommonUserService |
| `GET` | `/api/sns/v1/user/verify/avatar_holder/get_image` | Query: biz_id, biz_type | UserServices |
| `GET` | `/api/sns/v1/user/verify/avatar_holder/info` | Query: target_user_id | UserServices |
| `GET` | `/api/sns/v1/user/verify/verify_info` | Query: biz_id | IVerifyService |
| `GET` | `/api/sns/v1/user/verify/verify_info` | Query: biz_id | IMGVerifyService |
| `GET` | `/api/sns/v1/user/verify_identity` | Query: code, name | UserServices |
| `GET` | `/api/sns/v1/user/violation` | Query: scene | NoteService |
| `GET` | `/api/sns/v1/video_template/authoring_data` | Query: user_id | CapaTemplateResourceService |
| `GET` | `/api/sns/v1/video_template/authoring_data` | Query: user_id | CapaApi |
| `GET` | `/api/sns/v1/video_template/banner` |  | CapaTemplateResourceService |
| `GET` | `/api/sns/v1/video_template/banner` |  | CapaApi |
| `GET` | `/api/sns/v1/video_template/batch/adjusts` | Query: ids | TemplateResourceService |
| `GET` | `/api/sns/v1/video_template/batch/adjusts` | Query: ids | CapaTemplateResourceService |
| `GET` | `/api/sns/v1/video_template/batch/adjusts` | Query: ids | CapaApi |
| `GET` | `/api/sns/v1/video_template/batch/special_effect` | Query: ids | TemplateEffectService |
| `GET` | `/api/sns/v1/video_template/batch/special_effect` | Query: ids | CapaApi |
| `GET` | `/api/sns/v1/video_template/batch/text_animation` | Query: ids | CapaApi |
| `GET` | `/api/sns/v1/video_template/default_image_template` | Query: scene | ImageTemplateApiManagerImpl |
| `GET` | `/api/sns/v1/video_template/detect_footprinting` | Query: type, audio_address, audio_format, frame_rate, channel_num | CapaTemplateResourceService |
| `GET` | `/api/sns/v1/video_template/detect_footprinting` | Query: type, audio_address, audio_format, frame_rate, channel_num | CapaApi |
| `GET` | `/api/sns/v1/video_template/get_online_image_template_categories` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, scene, image_file_ids, activity_source | MaterialAPIService |
| `GET` | `/api/sns/v1/video_template/get_online_image_template_categories` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | VideoTemplateService |
| `GET` | `/api/sns/v1/video_template/get_online_image_template_categories` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, scene, image_file_ids, activity_source | CapaApi |
| `GET` | `/api/sns/v1/video_template/get_online_photo_album_categories` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, recommend_fragment_infos | MaterialAPIService |
| `GET` | `/api/sns/v1/video_template/get_online_photo_album_categories` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | VideoTemplateService |
| `GET` | `/api/sns/v1/video_template/guide_message` |  | CapaApi |
| `GET` | `/api/sns/v1/video_template/image_template_info` | Query: image_template_id | ImageTemplateApiManagerImpl |
| `GET` | `/api/sns/v1/video_template/image_template_info` | Query: image_template_id | ImageTemplateApiManagerImpl |
| `GET` | `/api/sns/v1/video_template/image_template_info` | Query: image_template_id | ImageTemplateService |
| `GET` | `/api/sns/v1/video_template/image_template_info` | Query: image_template_id | CapaApi |
| `GET` | `/api/sns/v1/video_template/online_adjusts` |  | MaterialAPIService |
| `GET` | `/api/sns/v1/video_template/online_adjusts` | Query: activity_source | CapaApi |
| `GET` | `/api/sns/v1/video_template/recommend_template` | Query: fragment_count, com.xingin.capa.feature_model.session.UploadImageBean.KEY_IMAGE_MATERIAL, image_file_ids | CapaApi |
| `GET` | `/api/sns/v1/video_template/review_success/newest` |  | ITemplateService |
| `GET` | `/api/sns/v1/video_template/review_success/newest` |  | CapaApi |
| `GET` | `/api/sns/v1/video_template/review_tabs` |  | ITemplateService |
| `GET` | `/api/sns/v1/video_template/review_tabs` |  | CapaApi |
| `GET` | `/api/sns/v1/video_template/single/special_effect` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | EffectServices |
| `GET` | `/api/sns/v1/video_template/single/special_effect` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | SpecialEffectApi |
| `GET` | `/api/sns/v1/video_template/single/special_effect` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | CapaApi |
| `GET` | `/api/sns/v1/video_template/single/video_animation` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | TemplateResourceService |
| `GET` | `/api/sns/v1/video_template/single/video_animation` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | CapaTemplateResourceService |
| `GET` | `/api/sns/v1/video_template/single/video_animation` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | CapaApi |
| `GET` | `/api/sns/v1/video_template/special_effect` | Query: range_type | MaterialAPIService |
| `GET` | `/api/sns/v1/video_template/special_effect` | Query: range_type | CapaApi |
| `GET` | `/api/sns/v1/video_template/sticker_animation` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | TemplateResourceService |
| `GET` | `/api/sns/v1/video_template/sticker_animation` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | CapaTemplateResourceService |
| `GET` | `/api/sns/v1/video_template/sticker_animation` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | CapaApi |
| `GET` | `/api/sns/v1/video_template/sticker_animations` |  | CapaTemplateResourceService |
| `GET` | `/api/sns/v1/video_template/sticker_animations` |  | CapaApi |
| `GET` | `/api/sns/v1/video_template/tags` |  | CapaTemplateResourceService |
| `GET` | `/api/sns/v1/video_template/tags` |  | CapaApi |
| `GET` | `/api/sns/v1/video_template/text_animation` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | TemplateResourceService |
| `GET` | `/api/sns/v1/video_template/text_animation` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | CapaTemplateResourceService |
| `GET` | `/api/sns/v1/video_template/text_animation` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | CapaApi |
| `GET` | `/api/sns/v1/video_template/text_animations` |  | CapaTemplateResourceService |
| `GET` | `/api/sns/v1/video_template/text_animations` |  | CapaApi |
| `GET` | `/api/sns/v1/video_template/user_template` | Query: user_id, need_video_type, page, pageSize | ITemplateService |
| `GET` | `/api/sns/v1/video_template/user_template` | Query: user_id, need_video_type, page, pageSize | CapaApi |
| `GET` | `/api/sns/v1/video_template/video_animation` |  | CapaTemplateResourceService |
| `GET` | `/api/sns/v1/video_template/video_animation` |  | CapaApi |
| `GET` | `/api/sns/v1/widget/outside/card` | Query: num, refresh_type, personalization | WidgetServices |
| `GET` | `/api/sns/v1/widget/outside/feed` | Query: cursor_score, num, geo, note_index, refresh_type, personalization, client_volume, pin_note_id | NoteDetailService |
| `GET` | `/api/sns/v10/note` | Query: note_id, edit_mode, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | NoteService |
| `GET` | `/api/sns/v10/note` | Query: note_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | NoteService |
| `GET` | `/api/sns/v10/note/video/save` | Query: note_id | NoteDetailService |
| `GET` | `/api/sns/v10/search/extract/text` | Query: note_id, file_id, note_from | ImageSearchService |
| `GET` | `/api/sns/v10/search/images` | Query: keyword, filters, sort, page, page_size, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, search_id, session_id, api_extra, page_pos, allow_rewrite, geo, scene, location_permission, is_out_of_china, device_level, refresh_type, unread_begin_note_id, unread_end_note_id, unread_note_count, search_tab, load_type, request_trigger_from, last_select_filter_from, word_request_id, note_ids, exp_infos, ext_params, feed_oaid, known_signal, request_from | AliothServices |
| `GET` | `/api/sns/v11/dqa/guide/words` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, conversation_id, message_id, complex_srp_cache_key, query, business_type, result_version, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, image_search_source, share_id, file_id, anchor_box, conversation_list, extension, scene | DotsApi |
| `GET` | `/api/sns/v11/dqa/guide/words` | Query: business_type, entities, ext_params | AgentDotsApi |
| `GET` | `/api/sns/v11/dqa/guide/words` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, conversation_id, message_id, complex_srp_cache_key, query, business_type, result_version, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, image_search_source, share_id, file_id, anchor_box, conversation_list | SearchAgentPageApi |
| `GET` | `/api/sns/v11/dqa/history/detail` | Query: conversation_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | DotsApi |
| `GET` | `/api/sns/v11/dqa/history/detail` | Query: conversation_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | SearchAgentPageApi |
| `GET` | `/api/sns/v11/dqa/history/list` | Query: keyword, pre_cursor, from, size, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | SearchAgentPageApi |
| `GET` | `/api/sns/v11/search/get_drawing_page_infod` | Query: req_id, file_id, note_id, image_search_source | ImageSearchService |
| `GET` | `/api/sns/v11/search/image_viewer_guides` | Query: req_id, file_id, note_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | NoteDetailService |
| `GET` | `/api/sns/v11/search/images` | Query: note_id, file_id, anchor_id, cursor, size, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, bbox, note_from, first_search, keyword, query, search_id, sort, request_id, first_conversation_id, first_message_id, is_trace_enable, trace_detail, trace_type, is_draw_page_user_input, ext_params, video_extra_infos | ImageSearchService |
| `GET` | `/api/sns/v11/search/images` | Query: note_id, file_id, anchor_id, cursor, size, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, bbox, note_from, search_id | ImageSearchNoteService |
| `GET` | `/api/sns/v11/search/images/active/guide` |  | ImageSearchService |
| `GET` | `/api/sns/v11/search/images/active/guide` |  | ImageSearchNoteService |
| `GET` | `/api/sns/v11/search/images/entrance/show` | Query: note_id, image_id_list | FeedbackService |
| `GET` | `/api/sns/v11/search/images/goods` | Query: note_id, file_id, item_id, cursor, size, anchor_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, sort, search_id, need_anchors, note_from, bbox, sku_list, enable_onebox, goods_tab_type | ImageSearchGoodsService |
| `GET` | `/api/sns/v11/search/images/goods` | Query: goods_id, file_id, item_id, cursor, size, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, search_id, need_anchors, enable_onebox, goods_tab_type | ImageSearchGoodsService |
| `GET` | `/api/sns/v11/search/longpress/guide` | Query: note_id, image_id_list | NoteDetailService |
| `GET` | `/api/sns/v11/search/video/pause/enable` | Query: req_id, video_id, note_id | ImageSearchService |
| `GET` | `/api/sns/v11/search/video/pause/guides` | Query: req_id, video_id, note_id, timestamp | ImageSearchService |
| `GET` | `/api/sns/v11/search/video_pause_guides` | Query: req_id, video_id | ImageSearchService |
| `GET` | `/api/sns/v2/board/lite` | Query: page, with_participate_board | CommonBoardService |
| `GET` | `/api/sns/v2/board/lite` | Query: page, num, forbid_generate, with_participate_board | CommonBoardService |
| `GET` | `/api/sns/v2/board/user/{userid}/followed` | Path: userid; Query: page | CommonBoardService |
| `GET` | `/api/sns/v2/board/{boardid}` | Path: boardid; Query: scene, page | CommonBoardService |
| `GET` | `/api/sns/v2/capa/edit/ref_info` | Query: ref_id, ref_type, extra | CommonService |
| `GET` | `/api/sns/v2/dot/user/dual/board_notes` | Query: board_id, cursor_score, num | AgentDotsApi |
| `GET` | `/api/sns/v2/dot/user/dual/boards` | Query: page, num | AgentDotsApi |
| `GET` | `/api/sns/v2/dot/user/dual/collect_notes` | Query: cursor_score, num | AgentDotsApi |
| `GET` | `/api/sns/v2/dot/user/dual/history_notes` | Query: cursor_score, num | AgentDotsApi |
| `GET` | `/api/sns/v2/dot/user/dual/like_notes` | Query: cursor_score, num | AgentDotsApi |
| `GET` | `/api/sns/v2/dot/user/dual/post_notes` | Query: cursor_score, num | AgentDotsApi |
| `GET` | `/api/sns/v2/dot/user/dual/preview_notes` | Query: cursor_score, scene, num, batch_id, tab_id, folder_id, page_board | AgentDotsApi |
| `GET` | `/api/sns/v2/guide/home_guide` | Query: has_location_permission | PopGuideService |
| `GET` | `/api/sns/v2/guide/template_banner` |  | CapaApi |
| `GET` | `/api/sns/v2/guide/user_banner` |  | NoteGuideService |
| `GET` | `/api/sns/v2/guide/user_guide` |  | PopGuideService |
| `GET` | `/api/sns/v2/media/collect_nns` | Query: nns_id, nns_type, option | INnsDetailService |
| `GET` | `/api/sns/v2/media/font` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | MaterialAPIService |
| `GET` | `/api/sns/v2/media/font` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | CapaApi |
| `GET` | `/api/sns/v2/media/font/styles` |  | CapaApi |
| `GET` | `/api/sns/v2/media/get_nnsInfo` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, type | INnsDetailService |
| `GET` | `/api/sns/v2/media/text/style/font_styles` | Query: business | MaterialAPIService |
| `GET` | `/api/sns/v2/media/text/style/font_styles` | Query: activity_source | CapaApi |
| `GET` | `/api/sns/v2/media/text/style/templates` | Query: type, activity_source, channel, business | MaterialAPIService |
| `GET` | `/api/sns/v2/media/text/style/templates` | Query: type | CapaApi |
| `GET` | `/api/sns/v2/media/text/text_template/category/text_templates` | Query: category_ids, business | MaterialAPIService |
| `GET` | `/api/sns/v2/media/text/text_template/categorys` |  | MaterialAPIService |
| `GET` | `/api/sns/v2/media/text_style` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | MaterialAPIService |
| `GET` | `/api/sns/v2/media/text_style` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | CapaApi |
| `GET` | `/api/sns/v2/media/{id}/use_photo_album` | Path: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | CommonService |
| `GET` | `/api/sns/v2/message/event/exposure/report` | Query: user_id, message_id, sender_id, type | MessageServiceV2 |
| `GET` | `/api/sns/v2/message/event/get_collected_list` | Query: user_id, page_no, num | MessageServices |
| `GET` | `/api/sns/v2/message/event/get_rejected_list` | Query: user_id, page_no, num | MessageServiceV2 |
| `GET` | `/api/sns/v2/message/event/get_subscription_list` | Query: user_id, page_no, num | MessageServiceV2 |
| `GET` | `/api/sns/v2/note/bgm_categories` | Query: file_id, required_beat | MusicService |
| `GET` | `/api/sns/v2/note/bgm_collection_detail` | Query: collection_id | MusicService |
| `GET` | `/api/sns/v2/note/bgm_collection_list` |  | MusicService |
| `GET` | `/api/sns/v2/note/business_bind` | Query: note_id | AdvanceService |
| `GET` | `/api/sns/v2/note/canvas` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | VideoPaintService |
| `GET` | `/api/sns/v2/note/get_danmaku` | Query: note_id, begin_mil_sec, size_per_sec, size | DanmakuApiService |
| `GET` | `/api/sns/v2/note/get_danmaku` | Query: note_id, begin_mil_sec, size_per_sec, size | DanmakuService |
| `GET` | `/api/sns/v2/note/get_danmaku_report_reason` |  | ReportService |
| `GET` | `/api/sns/v2/note/get_note_vote_user_detail` | Query: vote_id, vote_option_id, cursor, size | NoteDetailService |
| `GET` | `/api/sns/v2/note/liked` | Query: user_id, cursor, num | UserNoteLikeModel |
| `GET` | `/api/sns/v2/note/nice` | Query: user_id, cursor, num | UserNoteLikeModel |
| `GET` | `/api/sns/v2/page/lable/category` |  | LabelService |
| `GET` | `/api/sns/v2/page/lable/category` |  | CapaApi |
| `GET` | `/api/sns/v2/page/suggest` | Query: type, geo_info, page, page_size, region_type | LabelService |
| `GET` | `/api/sns/v2/page/suggest` | Query: type, geo_info, page, page_size, region_type | CapaApi |
| `GET` | `/api/sns/v2/pois/cities` | Query: locations | PageTagService |
| `GET` | `/api/sns/v2/recommend/user/social` | Query: type, use_contact | GrowthApi |
| `GET` | `/api/sns/v2/search/user/follow` | Query: keyword, page | AtUserServices |
| `GET` | `/api/sns/v2/search/user/follow` | Query: keyword, page, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | UserServices |
| `GET` | `/api/sns/v2/system_service/capa_business_config` |  | CapaConfigService |
| `GET` | `/api/sns/v2/system_service/capa_business_config` |  | CapaApi |
| `GET` | `/api/sns/v2/system_service/capa_common_config` | Query: scene, note_id, device_level | CapaConfigService |
| `GET` | `/api/sns/v2/system_service/capa_common_config` | Query: scene, note_id, device_level | CapaApi |
| `GET` | `/api/sns/v2/system_service/config` | Query: api_level, config_hash, cpu_name, gpu_renderer | InfraApi |
| `GET` | `/api/sns/v2/system_service/media_tool_config` |  | CapaApi |
| `GET` | `/api/sns/v2/system_service/mix_cloud_upload_info` | Query: operator, type, business, env, cross_upload, dynamic, version | TokenService |
| `GET` | `/api/sns/v2/system_service/octopus_dns` |  | InfraApi |
| `GET` | `/api/sns/v2/system_service/post_note_remind` |  | NoteGuideService |
| `GET` | `/api/sns/v2/system_service/qcloud_filename` | Query: md5s, type, num | TokenService |
| `GET` | `/api/sns/v2/user/account_info/anomalies` |  | IRiskService |
| `GET` | `/api/sns/v2/user/authority/common` |  | GeneralSettingServices |
| `GET` | `/api/sns/v2/user/desc/keywords` |  | UserServices |
| `GET` | `/api/sns/v2/user/followings/author_feed` | Query: author_id, cursor_score, num, ball_area_type, live_room_id, last_read_note_id | FollowFeedService |
| `GET` | `/api/sns/v2/user/followings/dualfeed` | Query: cursor_score, num, pin_user_id, client_volume, note_index, pin_note_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, geo, unread_begin_note_id, unread_end_note_id, unread_note_count, expo_unread_begin_note_id, expo_unread_end_note_id, expo_unread_note_count, last_card_position, red_dot_type, red_dot_num, red_dot_track_id, red_dot_link_id, user_post_note_id, enable_live_shooting, enable_location_permission, read_note_list, unread_note_list; Header: open-dp | FollowFeedService |
| `GET` | `/api/sns/v2/user/followings/live_reservation_bar` | Query: author_id | FollowFeedService |
| `GET` | `/api/sns/v2/user/identities` |  | UserServices |
| `GET` | `/api/sns/v2/user/info/function/me_guide` |  | FunctionCardServices |
| `GET` | `/api/sns/v2/user/keywords/list` | Query: target_id, keyword_id | KeywordImageListServices |
| `GET` | `/api/sns/v2/user/tab/second_filter` | Query: user_id, post_later_flag, first_tab_id | ProfileHistoryCommentService |
| `GET` | `/api/sns/v2/user/tab/second_filter` | Query: user_id, post_later_flag, first_tab_id | UserCollectedModel |
| `GET` | `/api/sns/v2/user/tab/second_filter` | Query: user_id, post_later_flag, first_tab_id | UserLikedModel |
| `GET` | `/api/sns/v2/user/tab/second_filter` | Query: user_id, post_later_flag, first_tab_id | WorksServers |
| `GET` | `/api/sns/v2/user/teenager/status` | Query: user_id | KidsModeService |
| `GET` | `/api/sns/v2/user/widget/update/entrance` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | WidgetService |
| `GET` | `/api/sns/v2/user/{userid}/followings` | Path: userid; Query: start, com.alipay.ams.component.sdk.InternalConfigKeys.ADDRESS_ELEMENT_MODE | AtUserServices |
| `GET` | `/api/sns/v3/guide/user_empty_state` |  | ProfileServices |
| `GET` | `/api/sns/v3/live/room_auth` | Query: user_id | AlphaConfigService |
| `GET` | `/api/sns/v3/message/you/fold` | Query: start, size, type | FoldCommentApi |
| `GET` | `/api/sns/v3/message/you/fold/specific` | Query: ids, scene, type | FoldCommentApi |
| `GET` | `/api/sns/v3/message/you/likes` | Query: start, size | MsgCenterServices |
| `GET` | `/api/sns/v3/message/you/likes/specific` | Query: ids | MsgCenterServices |
| `GET` | `/api/sns/v3/message/you/mentions` | Query: start, size, exit_box_types | MsgCenterServices |
| `GET` | `/api/sns/v3/message/you/mentions/specific` | Query: ids | MsgCenterServices |
| `GET` | `/api/sns/v3/note/comment/sub_comments` | Query: note_id, comment_id, start, num, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, filter_sub_comment_id, top_comment_id, top_comment_id_v2, page_context, scene, re_expand, container | CommentService |
| `GET` | `/api/sns/v3/note/comment/sub_comments` | Query: note_id, comment_id, start, num, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, filter_sub_comment_id, top_comment_id, shake_user | CommentApi |
| `GET` | `/api/sns/v3/note/guide` | Query: guide_keys | NoteDetailService |
| `GET` | `/api/sns/v3/note/guide/callback` | Query: guide_key | NoteDetailService |
| `GET` | `/api/sns/v3/search/user` | Query: keyword, page, page_size, search_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, filters, api_extra, exp_infos, ext_params | AliothServices |
| `GET` | `/api/sns/v3/tag/login_recommend` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, step, gender, age, generation | GrowthApi |
| `GET` | `/api/sns/v4/live/goods` | Query: room_id, offset, size, need_new_coupon | LiveGoodsCategoryService |
| `GET` | `/api/sns/v4/note/user/daily/posted` | Query: target_user_id, cursor, num, use_cursor | DailyService |
| `GET` | `/api/sns/v4/note/videofeed` | Query: note_id, fetch_mode, cursor_score, num, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, source_params, guide_params, preview_ad, search_extra_params, rec_params, unread_params, ace_params, biz_ext_json | VideoFeedNetService |
| `GET` | `/api/sns/v4/search/hint` | Query: word_request_situation, hint_word, note_id | SearchService |
| `GET` | `/api/sns/v4/search/notes/recommend_info` | Query: keyword, search_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, geo, api_extra, recommend_info_extra, preview_ad, exp_infos, ext_params | AliothServices |
| `GET` | `/api/sns/v4/user/me/refresh` |  | UserServices |
| `GET` | `/api/sns/v5/note/comment/list` | Query: note_id, start, num, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, exclude_comment_ids, preload_scene, page_context, sort_strategy, video_feed_type | CommentMediaBrowserService |
| `GET` | `/api/sns/v5/note/comment/list` | Query: note_id, start, num, show_priority_sub_comments, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, top_comment_id, top_comment_id_v2, exclude_comment_ids, force_master, page_context, preload_scene, sort_strategy, video_feed_type, request_comment_list_type, session_id, top_comment_operate_scene, container | CommentService |
| `GET` | `/api/sns/v5/note/comment/list` | Query: note_id, start, num, show_priority_sub_comments, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, top_comment_id, top_comment_id_v2, exclude_comment_ids, force_master, preload_scene, page_context, sort_strategy, video_feed_type, request_comment_list_type, top_comment_operate_scene | CommentService |
| `GET` | `/api/sns/v5/note/comment/list` | Query: note_id, start, num, show_priority_sub_comments, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, top_comment_id, shake_user, exclude_comment_ids | CommentApi |
| `GET` | `/api/sns/v5/recommend/user/explore` | Query: cursor_score, num, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, source_user_id, load_more, exp_flag, use_contact, pin_author_ids | MsgServices |
| `GET` | `/api/sns/v5/recommend/user/explore` | Query: cursor_score, num, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, source_user_id, load_more, exp_flag, use_contact, pin_author_ids | CommonUserService |
| `GET` | `/api/sns/v5/recommend/user/explore` | Query: cursor_score, num, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, exp_flag | FollowRecommendService |
| `GET` | `/api/sns/v5/recommend/user/explore` | Query: num, cursor_score, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, exp_flag | LoginServices |
| `GET` | `/api/sns/v5/recommend/user/explore` | Query: cursor_score, num, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, source_user_id, load_more, exp_flag, use_contact, pin_author_ids | RecommendUserModel |
| `GET` | `/api/sns/v5/recommend/user/explore` | Query: cursor_score, num, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, exp_flag | FollowFeedService |
| `GET` | `/api/sns/v5/recommend/user/follow_recommend` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, uid, num | CommonUserService |
| `GET` | `/api/sns/v6/homefeed` | Query: oid, cursor_score, geo, trace_id, note_index, real_note_index, refresh_type, last_refresh_type, client_volume, known_signal, unread_begin_note_id, unread_end_note_id, unread_note_count, preview_ad, preview_type, loaded_ad, home_ads_id, feed_oaid, user_action, personalization, is_break_down, orientation, launch_scenario, detach_splash_ad, last_card_position, last_live_position, last_live_id, cache_note_ids, enable_live_shooting, enable_location_permission, push_note_id, insert_note_type, selected_interests, playback_capability; Header: open-dp | ExploreService |
| `GET` | `/api/sns/v6/homefeed/categories` | Query: frame_type, force_show, video2tab | ExploreService |
| `GET` | `/api/sns/v6/homefeed/padtv` | Query: oid, cursor_score, geo, trace_id, note_index, refresh_type, client_volume, unread_begin_note_id, unread_end_note_id, unread_note_count, preview_ad, preview_type, loaded_ad, home_ads_id, user_action, personalization, is_break_down, orientation, launch_scenario, last_card_position, last_live_position, last_live_id; Header: open-dp | RedTvService |
| `GET` | `/api/sns/v6/message/delete_box` | Query: type, biz_type, biz_id | MsgServices |
| `GET` | `/api/sns/v6/message/delete_msg` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | MsgServices |
| `GET` | `/api/sns/v6/message/detect/switch` |  | MsgServices |
| `GET` | `/api/sns/v6/message/search/all` | Query: keyword | MessageSearchService |
| `GET` | `/api/sns/v6/message/search/one` | Query: keyword, num, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | MessageSearchService |
| `GET` | `/api/sns/v6/page/search` | Query: type, geo_info, keyword, page, page_size, region_type | LabelService |
| `GET` | `/api/sns/v6/page/search` | Query: keyword, page, page_size, geo_info, type, search_id, region_type | CapaApi |
| `GET` | `/api/sns/v6/relatedfeed` | Query: note_id, cursor_score, refresh_type, reco_type, note_source, source_params, rec_params, ace_params, search_extra_params, guide_params, preview_ad, unread_params | RelatedVideoService |
| `GET` | `/api/sns/v6/sketchfeed` | Query: session_id, cursor_score, num, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, refresh_type, filter_sketch_id | CollectionService |
| `GET` | `api/sns/capa/servicegw/poi/live_shooting_num` | Query: keyword, latitude, longitude, type | PoiService |
| `GET` | `api/sns/capa/servicegw/topic/batch_query` | Query: page_ids | TopicService |
| `GET` | `api/sns/inspiration/ai_edit_image/template_detail` | Query: template_id, style_id, extra_info | Capa51ConfigService |
| `GET` | `api/sns/open/comment/goods` | Query: note_id, user_id, keyword, page_num, page_size | CommentServices |
| `GET` | `api/sns/open/personal_page_tab/goods_list` | Query: userId | StoreServices |
| `GET` | `api/sns/red/live/app/activity/v1/world/cup26/guide/next_match/info` | Query: host_id | AlphaNextMatchGuideApi |
| `GET` | `api/sns/red/live/app/activity/v1/world/cup26/incidents` | Query: host_id, source_page | HighlightMsgService |
| `GET` | `api/sns/red/live/app/base/v1/get/cover/info` | Query: host_id, room_id | AlphaCoverTitleInfoService |
| `GET` | `api/sns/red/live/app/base/v1/room/member/count` | Query: room_id | AlphaGoodsLiveGoService |
| `GET` | `api/sns/red/live/app/base/v1/room/playback/info` | Query: room_id | AlphaPlaybackDispatchService |
| `GET` | `api/sns/red/live/app/base/v1/room/viewer_list` | Query: room_id | AlphaHeatService |
| `GET` | `api/sns/red/live/app/base/v1/room_frame` | Query: room_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE; Header: x-ratelimit-meta | AlphaDecorateService |
| `GET` | `api/sns/red/live/app/beauty/v1/style_makeup_resource` |  | AlphaStyleMakeupService |
| `GET` | `api/sns/red/live/app/comment/v1/user_violation` | Query: user_id | AlphaApiService |
| `GET` | `api/sns/red/live/app/core/v1/interaction_component` | Query: room_id | LiveRoomStatusService4LiveGo |
| `GET` | `api/sns/red/live/app/core/v1/live_status` | Query: scene, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, room_id_list, living_host_id | LiveStatusService |
| `GET` | `api/sns/red/live/app/core/v1/user_status` | Query: scene, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, user_id_list, living_host_id | LiveStatusService |
| `GET` | `api/sns/red/live/app/draw/lucky_draws` | Query: room_id; Header: x-ratelimit-meta | AlphaApiService |
| `GET` | `api/sns/red/live/app/family/v1/group/chat_list` | Query: room_id, host_id | LiveFamilyApiService |
| `GET` | `api/sns/red/live/app/feed/v1/gambit_feed` | Query: gambit_id, session_id, room_id, page_size, page_num | AlphaAudienceTopicService |
| `GET` | `api/sns/red/live/app/feed/v1/squarefeed` | Query: cursor_score, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, size, excludes, exclude_tag | LiveSquareLiveRoomNewService |
| `GET` | `api/sns/red/live/app/feed/v1/squarefeed` | Query: cursor_score, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, size, category, excludes, exclude_tag, pre_source, top_rooms | LiveSquareService |
| `GET` | `api/sns/red/live/app/line/v1/config_panel/linking_viewer` | Query: room_id | AlphaLinkLiveGoService |
| `GET` | `api/sns/red/live/app/line/v1/config_panel/talk_space` | Query: room_id | AlphaLinkLiveGoService |
| `GET` | `api/sns/red/live/app/line/v1/host/apply_list` | Query: app_id, room_id, apply_sort_type | AlphaLinkLiveGoService |
| `GET` | `api/sns/red/live/app/line/v1/host/invite_friend_list` | Query: room_id | AlphaLinkLiveGoService |
| `GET` | `api/sns/red/live/app/line/v1/host/viewer_list` | Query: room_id | AlphaLinkLiveGoService |
| `GET` | `api/sns/red/live/app/line/v1/viewer/apply_list` | Query: room_id | AlphaLinkLiveGoService |
| `GET` | `api/sns/red/live/app/line/v2/config_panel/linking_host` | Query: app_id, room_id | AlphaLinkLiveGoService |
| `GET` | `api/sns/red/live/app/line/v2/invite_host_list` | Query: app_id, room_id, type, sub_biz_type | AlphaLinkLiveGoService |
| `GET` | `api/sns/red/live/app/media/get_sdk_join_config` | Query: room_id, app_id | LiveSdkConfigService |
| `GET` | `api/sns/red/live/app/pay/v1/wallet/coins/balance` | Query: scene | AlphaGiftService |
| `GET` | `api/sns/red/live/app/red_packet/v4/detail` | Query: red_packet_id | LiveRedPacketApiService |
| `GET` | `api/sns/red/live/app/red_packet/v4/show_list` | Query: room_id, biz_types | LiveRedPacketApiService |
| `GET` | `api/sns/red/live/app/redpacket/v1/detail/get` | Query: red_packet_id; Header: x-ratelimit-meta | RedPacketNewApiService |
| `GET` | `api/sns/red/live/app/redpacket/v1/show_list/get` | Query: room_id, biz_types | RedPacketNewApiService |
| `GET` | `api/sns/red/live/app/reservation/v1/host_reservation_overview` | Query: host_id | AlphaReservationService |
| `GET` | `api/sns/red/live/app/resource_by_id/sender` | Query: source_id; Header: x-ratelimit-meta | AlphaGiftMultiLiveService |
| `GET` | `api/sns/red/live/app/room/live_box/config` | Query: box_type | AlphaTeleprompterService |
| `GET` | `api/sns/red/live/app/v1/atmosphere/config_list` | Query: room_id, host_id; Header: x-ratelimit-meta | AlphaAtmosphereConfigService4LiveGo |
| `GET` | `api/sns/red/live/app/v1/base/room_metric` | Query: room_id, host_id | LivePushDataDashboardService |
| `GET` | `api/sns/red/live/app/v1/center/room/get_stream_info` | Query: room_id | LiveCoreApiLiveRoomService |
| `GET` | `api/sns/red/live/app/v1/center/room/host/living_live_info` | Query: app_id | AlphaApiService |
| `GET` | `api/sns/red/live/app/v1/center/room/host/living_live_info` | Query: app_id, biz_id | AlphaApiService |
| `GET` | `api/sns/red/live/app/v1/center/room/host/living_live_info` | Query: app_id | AlphaPlayerLiveGoService |
| `GET` | `api/sns/red/live/app/v1/center/room/host/living_live_info` | Query: app_id, biz_id | LiveCoreApiLiveGoService |
| `GET` | `api/sns/red/live/app/v1/center/room/live_auth` | Query: host_id, room_id, need_buyer_matrix_account | AlphaHostAuthLiveRoomService |
| `GET` | `api/sns/red/live/app/v1/center/room/stop_info_2c` | Query: room_id, host_id, recommend_type, recommend_count, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE; Header: x-ratelimit-meta | AlphaApiService |
| `GET` | `api/sns/red/live/app/v1/common_share_pre` | Query: biz_type, biz_id | AlphaGoodsProductService |
| `GET` | `api/sns/red/live/app/v1/course/course_appendix_all_list` | Query: course_id | AlphaLiveClassService |
| `GET` | `api/sns/red/live/app/v1/course/course_appendix_list` | Query: course_id, page, page_size | AlphaLiveClassService |
| `GET` | `api/sns/red/live/app/v1/course/get_room_bound_lesson` | Query: app_id, room_id | AlphaConfigEdithService |
| `GET` | `api/sns/red/live/app/v1/course/host/unbound_appendix_list` | Query: page, page_size | AlphaLiveClassService |
| `GET` | `api/sns/red/live/app/v1/dynamic/review_info` | Query: host_id | AlphaMomentJarvisLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/backdrop/list` |  | AlphaGreenScreenLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/cover/info` | Query: host_id, room_id | AlphaConfigEdithLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/cover/info` | Query: host_id, room_id | AlphaConfigEdithLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/group/info` | Query: group_id | AlphaGroupLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/group/list` | Query: user_id | AlphaGroupLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/group/list` | Query: user_id, is_auto | AlphaGroupLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/inform_card/active_card` | Query: host_id, room_id; Header: x-ratelimit-meta | AlphaInfoCardLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/inform_card/active_group_chat/list` | Query: room_id, host_id, inform_card_id | AlphaGroupLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/inform_card/group_chat/list` | Query: room_id, host_id, inform_card_id | AlphaGroupLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/inform_card/query` | Query: host_id, room_id, statuses | AlphaInfoCardLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/interaction_count` | Query: room_id | AlphaConfigEdithLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/latest_chat_msg` | Query: app_id, room_id | AlphaConfigEdithLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/music/channel_list` | Query: host_id, room_id | AlphaBgmLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/music/channel_list` | Query: host_id, room_id | AlphaBgmService |
| `GET` | `api/sns/red/live/app/v1/ecology/music/detail_list` | Query: host_id, room_id, channel_id, page, page_size | AlphaBgmLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/room/get_living_room_link` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, extra_info | AlphaConfigLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/top_msg` | Query: room_id | AlphaSettingLiveGoService |
| `GET` | `api/sns/red/live/app/v1/ecology/watch_history/get` | Query: host_ids, user_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pre_source | AlphaCommonHistoryLiveGoService |
| `GET` | `api/sns/red/live/app/v1/goods/count` | Query: room_id | AlphaFlashBuyLiveMallService |
| `GET` | `api/sns/red/live/app/v1/goods/shopping_bag/check` | Query: room_id, contract_id | AlphaInfoCardLiveMallService |
| `GET` | `api/sns/red/live/app/v1/line/can_agree_invite` | Query: media_type, room_id, app_id | AlphaCommonLinkLiveGoService |
| `GET` | `api/sns/red/live/app/v1/line/can_apply` | Query: media_type, room_id, app_id | AlphaCommonLinkLiveGoService |
| `GET` | `api/sns/red/live/app/v1/line/can_enable_video` | Query: room_id, app_id | AlphaCommonLinkLiveGoService |
| `GET` | `api/sns/red/live/app/v1/line/host/apply_list` | Query: app_id, room_id | AlphaTalkBaseServiceLiveGo |
| `GET` | `api/sns/red/live/app/v1/line/host/linking_list` | Query: app_id, room_id | AlphaLinkLiveGoService |
| `GET` | `api/sns/red/live/app/v1/line/invite_friend_list` | Query: app_id, room_id | AlphaTalkLinkServiceLiveGo |
| `GET` | `api/sns/red/live/app/v1/line/invite_host_list` | Query: room_id | AlphaLinkLiveGoService |
| `GET` | `api/sns/red/live/app/v1/line/invite_viewer_list` | Query: app_id, room_id, page, size | AlphaTalkLinkServiceLiveGo |
| `GET` | `api/sns/red/live/app/v1/line/invite_window` | Query: invite_id | AlphaLinkLiveGoService |
| `GET` | `api/sns/red/live/app/v1/line/linkmic/seek` | Query: room_id, app_id | AlphaLinkLiveGoService |
| `GET` | `api/sns/red/live/app/v1/line/linkmic_apply_panel` | Query: room_id, app_id | AlphaLinkJarvisLiveGoService |
| `GET` | `api/sns/red/live/app/v1/line/quick_invitation_list` | Query: room_id, page, size, app_id | AlphaTalkBaseServiceLiveGo |
| `GET` | `api/sns/red/live/app/v1/line/search_invite_host_list` | Query: room_id, query | AlphaLinkLiveGoService |
| `GET` | `api/sns/red/live/app/v1/line/viewer/apply_list` | Query: app_id, room_id | AlphaLinkLiveGoService |
| `GET` | `api/sns/red/live/app/v1/live_tab/waterfall_feed` | Query: page_source, pos | AlphaConfigService |
| `GET` | `api/sns/red/live/app/v1/livegoods/choice_goods/c/goods/list` | Query: host_id, choice_goods_id, cursor, filter, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AlphaGoodsProductService |
| `GET` | `api/sns/red/live/app/v1/livegoods/choice_goods/category/list` | Query: host_id, choice_goods_id | AlphaGoodsProductLiveMallService |
| `GET` | `api/sns/red/live/app/v1/livegoods/choice_goods/category/list` | Query: host_id, choice_goods_id | AlphaGoodsProductService |
| `GET` | `api/sns/red/live/app/v1/livegoods/choice_goods/cps_goods_list` | Query: page, user_id, biz_id, limit, biz_type | AlphaGoodsEdithService |
| `GET` | `api/sns/red/live/app/v1/livegoods/choice_goods/cps_goods_search` | Query: query, page, biz_id, user_id, biz_type, limit | AlphaSearchGoodsService |
| `GET` | `api/sns/red/live/app/v1/livegoods/choice_goods/goods/list/from/categoryid` | Query: host_id, choice_goods_id, cursor, filter, category_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AlphaGoodsProductService |
| `GET` | `api/sns/red/live/app/v1/livegoods/choice_goods/goods/list/from/categoryid` | Query: host_id, choice_goods_id, cursor, filter, category_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AlphaGoodsProductService |
| `GET` | `api/sns/red/live/app/v1/livegoods/choice_goods/k/goods/list` | Query: host_id, choice_goods_id, cursor, filter, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AlphaGoodsProductService |
| `GET` | `api/sns/red/live/app/v1/livegoods/choice_goods/k/history/live` | Query: host_id | AlphaGoodsEdithService |
| `GET` | `api/sns/red/live/app/v1/livegoods/choice_goods/k/live/history/items` | Query: host_id, room_id, choice_goods_id | AlphaGoodsEdithService |
| `GET` | `api/sns/red/live/app/v1/livegoods/choice_goods/match/detail` | Query: host_id, match_id, owner_view | AlphaCollocationService |
| `GET` | `api/sns/red/live/app/v1/livegoods/choice_goods/match/list` | Query: user_id, cursor | AlphaCollocationService |
| `GET` | `api/sns/red/live/app/v1/livegoods/choice_goods/page` | Query: host_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, entrance_type | AlphaGoodsProductService |
| `GET` | `api/sns/red/live/app/v1/mall/business/goods_detail/list` | Query: business_id, business_type, page, page_size, host_id | AlphaGoodsEdithService |
| `GET` | `api/sns/red/live/app/v1/mall/business/goods_detail/list` | Query: business_id, business_type, page, page_size | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/cps/goods/list` | Query: room_id, page, page_size, act_type_list | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/cps/goods/search` | Query: query, room_id, page, page_size, act_type_list | AlphaSearchGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/explained_goods` | Query: room_id, page, page_size | AlphaMomentsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/flash_buy/list` | Query: room_id, type, page, page_size | AlphaFlashBuyLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/goods/pool/disable_goods` | Query: host_id, room_id, plan_id, pool_id, scene_id, request_user_id | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/goods/shopping_bag/disable_goods` | Query: room_id, plan_id | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/goods/shopping_bag/info` | Query: room_id, room_source, open_source; Header: x-ratelimit-meta | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/goods/shopping_bag/search` | Query: room_id, query, offset, size, search_id; Header: x-ratelimit-meta | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/goods_auth` | Query: host_id, room_id, need_buyer_matrix_account | AlphaGoodsProductLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/goods_auth` | Query: host_id, room_id, need_buyer_matrix_account | AlphaGoodsProductService |
| `GET` | `api/sns/red/live/app/v1/mall/goods_list` | Query: room_id, page, page_size | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/goods_panel` | Query: room_id, need_new_coupon | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/history_goods` | Query: room_id, page, page_size | AlphaMomentsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/lucky_draw/goods_lucky_draw_list` | Query: room_id, lucky_draw_id, page, page_size | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/marketing/group_chat_info` | Query: room_id, receive_id | AlphaPromoteLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/marketing/list_received_users` | Query: room_id, receive_id, receive_type, page, page_size | AlphaPromoteLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/plan/cps/goods/list` | Query: plan_id, host_id, page, page_size, act_type_list | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/plan/cps/goods/search` | Query: plan_id, query, host_id, page, page_size, act_type_list | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/plan/detail` | Query: plan_id | AlphaPlanLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/plan/detail/v2` | Query: plan_id | AlphaPlanLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/plan/goods/list` | Query: plan_id, room_id, page, page_size | LiveGoodsCategoryService |
| `GET` | `api/sns/red/live/app/v1/mall/plan/goods/list` | Query: plan_id, pool_id, room_id, page, page_size | AlphaPlanLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/plan/link/status` | Query: room_id, host_id | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/plan/list` | Query: host_id, page, page_size, room_id | AlphaPlanLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/plan/shop/goods/list` | Query: plan_id, host_id, page, page_size, act_type_list | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/plan/shop/goods/search` | Query: plan_id, query, host_id, page, page_size, act_type_list | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/prelive/pool_goods_list_by_id` | Query: host_id, type, page, page_size, category_id | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/rank/goods_rank_hour` | Query: room_id | AlphaRankingLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/seller/carriage_templates` | Query: host_id, cost_type_filter | AlphaFlashBuyLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/seller/categories` | Query: parent_category_id, host_id | AlphaFlashBuyLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/seller/category/brand/list` | Query: host_id, category_ids, keyword, page, page_size | AlphaFlashBuyLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/seller/category/max_delivery_time` | Query: category_id, host_id | AlphaFlashBuyLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/seller/logistics_templates` | Query: host_id | AlphaFlashBuyLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/shop/goods/list` | Query: room_id, page, page_size, act_type_list | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/shop/goods/search` | Query: query, room_id, page, page_size, act_type_list | AlphaSearchGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/user/cps/goods/list` | Query: room_id, page, page_size, host_id | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/mall/user/shop/goods/list` | Query: room_id, page, page_size, host_id | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v1/playgeme/auth/generate` | Query: user_id, anchor_id, game_id | AlphaBindGameApi |
| `GET` | `api/sns/red/live/app/v1/room/categories` | Query: host_id, room_id, content_type | AlphaApiService |
| `GET` | `api/sns/red/live/app/v1/room/categories` | Query: host_id, room_id, content_type | AlphaSettingLiveGoService |
| `GET` | `api/sns/red/live/app/v1/room/config` | Query: host_id, func_pos, func_type | AlphaApiService |
| `GET` | `api/sns/red/live/app/v1/room/config` | Query: host_id, func_pos, func_type | AlphaSettingLiveGoService |
| `GET` | `api/sns/red/live/app/v1/room/cover_iqa` | Query: host_id, cover, cover_file_info | AlphaApiService |
| `GET` | `api/sns/red/live/app/v1/room/current_room_info` | Query: host_id, room_id | AlphaApiService |
| `GET` | `api/sns/red/live/app/v1/room/host_last_category` | Query: content_type | AlphaSettingLiveGoService |
| `GET` | `api/sns/red/live/app/v1/room/join_business_base_info` | Query: room_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE; Header: x-ratelimit-meta | AlphaConfigEdithLiveRoomService |
| `GET` | `api/sns/red/live/app/v1/room/join_business_base_info` | Query: room_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE; Header: x-ratelimit-meta | AlphaConfigEdithService |
| `GET` | `api/sns/red/live/app/v1/room/join_comment_info` | Query: room_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pre_source, track_id; Header: x-ratelimit-meta | AlphaApiService |
| `GET` | `api/sns/red/live/app/v1/room/join_comment_info` | Query: room_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pre_source, track_id; Header: x-ratelimit-meta | AlphaChatService |
| `GET` | `api/sns/red/live/app/v1/room/last_room_info` | Query: host_id | AlphaApiService |
| `GET` | `api/sns/red/live/app/v1/room/last_room_info` | Query: host_id | AlphaConfigEdithLiveGoService |
| `GET` | `api/sns/red/live/app/v1/room/pre_config` | Query: host_id | AlphaApiService |
| `GET` | `api/sns/red/live/app/v1/room/pre_config` | Query: host_id | AlphaApiService |
| `GET` | `api/sns/red/live/app/v1/room/recent_poi_info` | Query: longitude, latitude | AlphaApiService |
| `GET` | `api/sns/red/live/app/v1/room/room_settings` | Query: room_id, host_id | AlphaConfigLiveGoService |
| `GET` | `api/sns/red/live/app/v1/share/template` | Query: biz_type, target_user_id | AlphaGoodsProductService |
| `GET` | `api/sns/red/live/app/v1/user/host_info` | Query: host_id | AlphaApiService |
| `GET` | `api/sns/red/live/app/v1/user/host_info` | Query: host_id | AlphaConfigService |
| `GET` | `api/sns/red/live/app/v1/user/label_info` | Query: room_id, host_id | AlphaUserEdithLiveGoService |
| `GET` | `api/sns/red/live/app/v1/user/trailer/detail` | Query: trailer_id, source_type | LiveServices4LiveGo |
| `GET` | `api/sns/red/live/app/v1/user/trailer/detail` | Query: trailer_id, source_type, source_host_id | AlphaLivePreviewEdithLiveGoService |
| `GET` | `api/sns/red/live/app/v1/user/trailer/detail` | Query: trailer_id, source_type | AlphaPlanLiveGoService |
| `GET` | `api/sns/red/live/app/v1/video/lookback/list_view` | Query: host_id | AlphaPlayBackService4LiveGo |
| `GET` | `api/sns/red/live/app/v1/video/lookback/task_detail` | Query: host_id, room_ids | AlphaPlayBackService4LiveGo |
| `GET` | `api/sns/red/live/app/v2/livegoods/choice_goods/match/goods/list` | Query: match_id, user_id | AlphaGoodsProductService |
| `GET` | `api/sns/red/live/app/v2/mall/flash_buy/detail` | Query: room_id, item_id, sku_id | AlphaFlashBuyLiveMallService |
| `GET` | `api/sns/red/live/app/v2/mall/goods_explain/goods_info` | Query: room_id, contract_id, user_ids | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/live/app/v2/product/seller/items` | Query: host_id, page, page_size, keyword | AlphaCouponLiveMallService |
| `GET` | `api/sns/red/live/app/vote/v1/detail` | Query: vote_id | LiveVoteApiService |
| `GET` | `api/sns/red/live/app/vote/v1/host/detail` | Query: vote_id, user_id, room_id | LiveVoteApiService |
| `GET` | `api/sns/red/live/coin/balance` |  | ShoppingRedPacketEdithService |
| `GET` | `api/sns/red/live/ecology/new_host_task/flow_prefer/detail` | Query: room_id | AlphaTaskLiveGoService |
| `GET` | `api/sns/red/live/ecology/shopping_red_packet/allow_received/list` | Query: room_id | AlphaStoreService |
| `GET` | `api/sns/red/live/ecology/shopping_red_packet/allow_received/list` | Query: room_id | ShoppingRedPacketLiveGoService |
| `GET` | `api/sns/red/live/rank/entrance/list` | Query: room_id; Header: x-ratelimit-meta | AlphaApiService |
| `GET` | `api/sns/red/live/rec/category` | Query: room_id, page | AlphaCommonConfigLiveGoService |
| `GET` | `api/sns/red/live/room/pre/more_settings_func` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, room_id, racing, filters | AlphaPrepareLiveGoService |
| `GET` | `api/sns/red/live/room/showing_trailer` | Query: room_id, source_host_id; Header: x-ratelimit-meta | AlphaApiService |
| `GET` | `api/sns/red/live/trailer/trailer_complex_plan/info/by_time` | Query: start_time, host_id | AlphaLivePreviewEdithLiveGoService |
| `GET` | `api/sns/red/live/trailer/trailer_info` | Query: trailer_id, source_host_id; Header: x-ratelimit-meta | AlphaApiService |
| `GET` | `api/sns/red/live/trailer/trailer_info` | Query: trailer_id | AlphaLivePreviewEdithLiveGoService |
| `GET` | `api/sns/red/live/v1/mall/flash_buy/pause/restriction/reason` | Query: room_id | AlphaFlashBuyLiveMallService |
| `GET` | `api/sns/red/live/v1/mall/shoppingbag/guide/info` | Query: room_id | AlphaGoodsLiveGoService |
| `GET` | `api/sns/red/livemall/app/ai/assistant/icon_status` | Query: host_id, room_id | AIAgentApi |
| `GET` | `api/sns/red/livemall/app/dynamic/host/info` | Query: host_id | AlphaMomentsLiveMallService |
| `GET` | `api/sns/red/livemall/app/dynamic/overview/list` | Query: host_id, page, page_size | AlphaMomentsLiveMallService |
| `GET` | `api/sns/red/livemall/app/explain/v1/explained_goods/list` | Query: room_id, page, page_size, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/livemall/app/goods_card/callback` | Query: room_id, contract_id, room_source, pass_through_log_param, pass_through_other_param; Header: x-ratelimit-meta | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/livemall/app/marketing/get_config` | Query: room_id; Header: x-ratelimit-meta | AlphaConfigListLiveMallService |
| `GET` | `api/sns/red/livemall/app/marketing/get_config` | Query: room_id; Header: x-ratelimit-meta | StoreConfigListLiveMallService |
| `GET` | `api/sns/red/livemall/app/red_dot_info` | Query: room_id | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/livemall/app/reservation/v1/info` | Query: reservation_id, host_id, query_subscribe_status | AlphaLivePreviewLiveMallService |
| `GET` | `api/sns/red/livemall/app/shopping_bag/v1/top_area_banner` | Query: room_id, request_source | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/livemall/app/trailer/v1/host_reservation_card` | Query: host_id, source_type | AlphaUserCardLiveMallService |
| `GET` | `api/sns/red/livemall/app/widgets/v1/all_widgets_info` | Query: room_id, extra_info; Header: x-ratelimit-meta | AlphaWidgetLiveMallService |
| `GET` | `api/sns/red/livemall/app/widgets/v1/config` | Query: room_id | AlphaConfigListLiveMallService |
| `GET` | `api/sns/red/livemall/manager/app/live_goods_category/v1/list` | Query: room_id, host_id, plan_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AlphaGoodsLiveMallService |
| `GET` | `api/sns/red/livemall/manager/app/pool_goods/v1/category_goods/by_pool` | Query: plan_id, category_id, host_id, page, page_size | AlphaPlanLiveMallService |
| `GET` | `api/sns/v1/account_recovery/search/user` | Query: keyword, page, page_size | RecoverServices |
| `GET` | `api/sns/v1/account_recovery/users/recently_logged_in` |  | RecoverServices |
| `GET` | `api/sns/v1/ads/resource` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, resource_type | AdsPreCacheService |
| `GET` | `api/sns/v1/comment/like` | Query: comment_id | CommentService |
| `GET` | `api/sns/v1/creator/get_creator_message` | Query: start, num | MsgAuthorHelperServices |
| `GET` | `api/sns/v1/creator/red_app/package/pull` | Query: appId, userId, clientVersion, env, deviceId, platform, committerId, version | IMiniToolService |
| `GET` | `api/sns/v1/hey/followfeed` | Query: reverse, live, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pin_user_id, refresh_type, follow_tab_red_dot_type | HeyServices |
| `GET` | `api/sns/v1/interaction/comment/ask/detail` | Query: note_id, comment_id | AiReplyService |
| `GET` | `api/sns/v1/intimacy/intimacy_list` | Query: biz_name, note_id | NoteMatrixUserServices |
| `GET` | `api/sns/v1/intimacy/intimacy_list` |  | NoteMatrixUserServices |
| `GET` | `api/sns/v1/intimacy/intimacy_list/search` | Query: keyword, page, rows, biz_name | NoteMatrixUserServices |
| `GET` | `api/sns/v1/live/activity/potato_park/{room_id}/get_potato_gift_info` | Path: room_id | AlphaGiftService |
| `GET` | `api/sns/v1/live/admins` | Query: room_id, page, page_size | AlphaUserService |
| `GET` | `api/sns/v1/live/adult_check` |  | AlphaApiService |
| `GET` | `api/sns/v1/live/before_live` | Query: recommend_count, user_id | AlphaConfigService |
| `GET` | `api/sns/v1/live/coupon/{room_id}/all_list` | Path: room_id | AlphaCouponService |
| `GET` | `api/sns/v1/live/course/category/menus` |  | AlphaLiveClassService |
| `GET` | `api/sns/v1/live/course/check/lesson/pre_start_time` | Query: pre_start_time | AlphaLiveClassService |
| `GET` | `api/sns/v1/live/course/host/record/list` | Query: page, page_size | AlphaLiveClassService |
| `GET` | `api/sns/v1/live/course/inside/detail` | Query: course_id | AlphaLiveClassService |
| `GET` | `api/sns/v1/live/course/teacher/lesson/info/nearest` |  | AlphaLiveClassService |
| `GET` | `api/sns/v1/live/course/video/play/played_duration` | Query: lesson_id, video_index | AlphaPlayBackService |
| `GET` | `api/sns/v1/live/course/{course_id}/check_order` | Path: course_id | AlphaLiveClassService |
| `GET` | `api/sns/v1/live/cover/history` |  | AlphaConfigService |
| `GET` | `api/sns/v1/live/draw/info/{lucky_draw_id}` | Path: lucky_draw_id; Header: x-ratelimit-meta | AlphaApiService |
| `GET` | `api/sns/v1/live/draw/info/{lucky_draw_id}` | Path: lucky_draw_id | AlphaLotteryLiveGoService |
| `GET` | `api/sns/v1/live/draw/{lucky_draw_id}/lucky_boys` | Path: lucky_draw_id; Header: x-ratelimit-meta | AlphaApiService |
| `GET` | `api/sns/v1/live/draw/{lucky_draw_id}/lucky_boys` | Path: lucky_draw_id | AlphaLotteryLiveGoService |
| `GET` | `api/sns/v1/live/dynamic/clip_detail` | Query: clip_id, host_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pre_source | AlphaPlayBackService4LiveGo |
| `GET` | `api/sns/v1/live/dynamic/month` | Query: host_id, timestamp | AlphaMomentsLiveGoService |
| `GET` | `api/sns/v1/live/dynamic/month` | Query: host_id, timestamp | AlphaMomentJarvisLiveGoService |
| `GET` | `api/sns/v1/live/dynamic/overview` | Query: host_id | AlphaMomentsLiveGoService |
| `GET` | `api/sns/v1/live/dynamic/overview` | Query: host_id | AlphaMomentJarvisLiveGoService |
| `GET` | `api/sns/v1/live/dynamic/switch_config` | Query: host_id | AlphaMomentsLiveGoService |
| `GET` | `api/sns/v1/live/dynamic/switch_config` | Query: host_id | AlphaMomentJarvisLiveGoService |
| `GET` | `api/sns/v1/live/feed` | Query: cursor_score, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, category, excludes, exclude_tag | AlphaCommonConfigLiveGoService |
| `GET` | `api/sns/v1/live/filters` |  | AlphaConfigService |
| `GET` | `api/sns/v1/live/filters` |  | AlphaConfigService |
| `GET` | `api/sns/v1/live/goods_detail` | Query: room_id, contract_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AlphaGoodsLiveMallService |
| `GET` | `api/sns/v1/live/goods_detail` | Query: room_id, contract_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AlphaGoodsLiveMallService |
| `GET` | `api/sns/v1/live/homefeed` | Query: cursor_score, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, size, excludes, exclude_tag | LiveSquareLiveRoomOldService |
| `GET` | `api/sns/v1/live/host_setup_info` | Query: room_id | AlphaUserService |
| `GET` | `api/sns/v1/live/letter/config` | Query: room_id | AlphaQuestionService |
| `GET` | `api/sns/v1/live/letter/list` | Query: room_id, page, page_size, target_letter_id | AlphaQuestionLiveGoService |
| `GET` | `api/sns/v1/live/letter/list` | Query: room_id, page, page_size, target_letter_id, sort_type, extra_info | AlphaQuestionService |
| `GET` | `api/sns/v1/live/pre/entrance/list` |  | AlphaLivePreviewService |
| `GET` | `api/sns/v1/live/pull_stream` | Query: host_id, room_id | AlphaApiService |
| `GET` | `api/sns/v1/live/pull_stream` | Query: host_id, room_id | LiveGoService |
| `GET` | `api/sns/v1/live/real_name_verify_check` |  | AlphaConfigService |
| `GET` | `api/sns/v1/live/received_gifts` | Query: room_id, page, page_size | AlphaGiftService |
| `GET` | `api/sns/v1/live/recommend/before_live` | Query: recommend_count, user_id | AlphaConfigService |
| `GET` | `api/sns/v1/live/red_packet/{red_packet_id}` | Path: red_packet_id | AlphaRedPacketLiveGoService |
| `GET` | `api/sns/v1/live/red_packet/{room_id}/room/all/red_packets` | Path: room_id | AlphaRedPacketLiveGoService |
| `GET` | `api/sns/v1/live/resources` | Query: host_id, room_id | AlphaGiftMultiLiveService |
| `GET` | `api/sns/v1/live/strategy/list` |  | AlphaLiveStrategyService |
| `GET` | `api/sns/v1/live/trailer/host/coming_trailer` | Query: host_id, source_type | AlphaUserLiveGoService |
| `GET` | `api/sns/v1/live/trailer/host/coming_trailer` | Query: host_id, source_type, trailer_id | AlphaCommonUserLiveGoService |
| `GET` | `api/sns/v1/live/trailer/trailer_list` | Query: host_id, source_type, room_id | AlphaLivePreviewLiveGoService |
| `GET` | `api/sns/v1/live/trailer/trailer_share_generate` | Query: trailer_id | ShareService |
| `GET` | `api/sns/v1/live/user_status` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, user_id_list | LiveServices4LiveGo |
| `GET` | `api/sns/v1/live/user_status` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, user_id_list | AlphaApiService |
| `GET` | `api/sns/v1/live/user_status` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, user_id_list | AlphaApiService |
| `GET` | `api/sns/v1/live/user_status` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, user_id_list | LiveRoomStatusService4LiveGo |
| `GET` | `api/sns/v1/live/user_status` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, user_id_list | LiveStatusLiveService |
| `GET` | `api/sns/v1/live/{room_id}/admins` | Path: room_id; Query: page, page_size | AlphaUserService |
| `GET` | `api/sns/v1/live/{room_id}/host_setup_info` | Path: room_id | AlphaUserService |
| `GET` | `api/sns/v1/live/{room_id}/lucky_draws` | Path: room_id | AlphaApiService |
| `GET` | `api/sns/v1/live/{room_id}/lucky_draws` | Path: room_id | AlphaLotteryLiveGoService |
| `GET` | `api/sns/v1/live/{room_id}/received_gifts` | Path: room_id; Query: page, page_size | AlphaGiftService |
| `GET` | `api/sns/v1/live/{room_id}/user_card` | Path: room_id; Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, user_id, force_host_view | AlphaUserLiveRoomService |
| `GET` | `api/sns/v1/live/{room_id}/viewers` | Path: room_id; Query: host_id, page, page_size | AlphaApiService |
| `GET` | `api/sns/v1/live/{source_id}/info` | Path: source_id | AlphaGiftService |
| `GET` | `api/sns/v1/live/{source_id}/resource_by_id` | Path: source_id; Header: x-ratelimit-meta | AlphaGiftMultiLiveService |
| `GET` | `api/sns/v1/local/poi/search/suggest` | Query: query, geo, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AliothServices |
| `GET` | `api/sns/v1/localfeed` | Query: location_permission_status, cursor_score, trace_id, refresh_type, geo, current_geo, other_city, liveshooting_note_id, enable_live_shooting, last_card_position, last_live_position, last_live_id, category_oid, search_params, ignore_location_data, unread_begin_note_id, unread_end_note_id, unread_note_count, channel_id, category_id, sub_category_id, distance_id, city_name, country_name, coordinate_type, loaded_ad, preview_ad, preview_type, personalization; Header: open-dp | LocalFeedService |
| `GET` | `api/sns/v1/localfeed/activity` | Query: location_permission_status, cursor_score, trace_id, refresh_type, geo, current_geo, other_city, liveshooting_note_id, enable_live_shooting, last_card_position, last_live_position, last_live_id, category_oid, search_params, ignore_location_data, unread_begin_note_id, unread_end_note_id, unread_note_count, channel_id, category_id, sub_category_id, distance_id, city_name, country_name, coordinate_type; Header: open-dp | LocalFeedService |
| `GET` | `api/sns/v1/localfeed/bar` | Query: geo, other_city, city_name | LocalFeedService |
| `GET` | `api/sns/v1/localfeed/city_list` | Query: geo, city_name, enable_location_permission, country_name | LocalFeedService |
| `GET` | `api/sns/v1/localfeed/header` | Query: geo_info, geo, coordinate_type, ignore_location_data | LocalFeedService |
| `GET` | `api/sns/v1/localfeed/map/hot_poi` |  | AliothServices |
| `GET` | `api/sns/v1/localfeed/map/search_poi` | Query: keyword, page_size, cursor | AliothServices |
| `GET` | `api/sns/v1/localfeed/map_entrance` | Query: ext_flag, geo, other_city, city_name | LocalFeedService |
| `GET` | `api/sns/v1/mappoi/footprints/privacy` |  | EdithUserServices |
| `GET` | `api/sns/v1/media/prop_colls/live` | Query: type | AlphaConfigService |
| `GET` | `api/sns/v1/media/user/sug` | Query: page, page_size, note_title, note_content, textimg_text | IUserService |
| `GET` | `api/sns/v1/message/sysmessage/push` | Query: start, num | MessageServices |
| `GET` | `api/sns/v1/message/sysmessage/subpage` | Query: type, start, num | MessageServices |
| `GET` | `api/sns/v1/message/sysmessage/sys` | Query: start, num | MessageServices |
| `GET` | `api/sns/v1/message/you/connections` | Query: start, num, msg_version | MessageServices |
| `GET` | `api/sns/v1/message/you/connections` | Query: start, num, msg_version | MessageServices |
| `GET` | `api/sns/v1/message/you/likes` | Query: start, num | MessageServices |
| `GET` | `api/sns/v1/message/you/mentions` | Query: start, num | MessageServices |
| `GET` | `api/sns/v1/mp/red/apps/{appId}/introduction` | Path: appId; Query: sid | IMPVersionService |
| `GET` | `api/sns/v1/mp/red/apps/{appId}/pkg` | Path: appId; Query: baseVersion, envVersion, producerId, sid, mpVersion; Header: mp-common-params | IMPVersionService |
| `GET` | `api/sns/v1/note/beautys_group` |  | AlphaConfigService |
| `GET` | `api/sns/v1/note/beautys_group` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | MaterialAPIService |
| `GET` | `api/sns/v1/note/beautys_group` |  | CommonService |
| `GET` | `api/sns/v1/note/board/info` | Query: board_id, cursor, num, candidate_share_board_id | NoteServices |
| `GET` | `api/sns/v1/note/dislike` | Query: oid | CommonNoteService |
| `GET` | `api/sns/v1/note/like` | Query: oid | CommonNoteService |
| `GET` | `api/sns/v1/note/like` | Query: oid | StoreService |
| `GET` | `api/sns/v1/note/nns/miniprogram/card` | Query: note_id | FollowNoteModel |
| `GET` | `api/sns/v1/note/share` | Query: share_platform, note_id, encouragement | ShareService |
| `GET` | `api/sns/v1/note/share/specific_user_list` | Query: note_id | ShareViewService |
| `GET` | `api/sns/v1/note/video/bgm_categories` |  | MusicService |
| `GET` | `api/sns/v1/note/video/categoried_bgms` | Query: category_id, page, page_size | MusicService |
| `GET` | `api/sns/v1/note/video_played` | Query: note_id, repeat | NoteDetailService |
| `GET` | `api/sns/v1/note/video_screenshot` | Query: note_id, type, play_ms | VideoScreenshotShareService |
| `GET` | `api/sns/v1/note/wxmp_qr_code/{noteid}` | Path: noteid; Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, xhsshare, uid, apptime | ShareService |
| `GET` | `api/sns/v1/note/{note_id}/meta` | Path: note_id | NoteServices |
| `GET` | `api/sns/v1/paddles/pull_shanks` |  | StrategyNetService |
| `GET` | `api/sns/v1/page/user_page/mp_tab` | Query: page_no, page_size, user_id | HotelOrderServices |
| `GET` | `api/sns/v1/page/{page_id}/topic` | Path: page_id | TopicService |
| `GET` | `api/sns/v1/pop_ups/show` | Query: opportunity, current_page | DialogModel |
| `GET` | `api/sns/v1/recommend/tag/explore` | Query: page, num | TagServices |
| `GET` | `api/sns/v1/recommend/user/contacts` | Query: page, keyword | UserServices |
| `GET` | `api/sns/v1/recommend/user/follow_all` | Query: type | UserServices |
| `GET` | `api/sns/v1/recommend/user/hint` |  | MsgServices |
| `GET` | `api/sns/v1/recommend/user/hint` |  | CommonUserService |
| `GET` | `api/sns/v1/recommend/user/hint` |  | MatrixUserServices |
| `GET` | `api/sns/v1/recommend/user/hint` |  | UserServices |
| `GET` | `api/sns/v1/recommend/user/hint` |  | UserServices |
| `GET` | `api/sns/v1/recommend/user/social` |  | LoginServices |
| `GET` | `api/sns/v1/recommend/user/status` |  | UserServices |
| `GET` | `api/sns/v1/recommend/user/weibo/sync` |  | UserServices |
| `GET` | `api/sns/v1/search/user/follow` | Query: keyword, page | MatrixUserServices |
| `GET` | `api/sns/v1/search/user/page` | Query: keyword, page, rows, scene, template_id | IUserService |
| `GET` | `api/sns/v1/search/user/page` | Query: keyword, page, rows | MatrixUserServices |
| `GET` | `api/sns/v1/share/code` | Query: code, codeOnly, entireText, copyFrom, type | CopyLinkService |
| `GET` | `api/sns/v1/system/switch_config` | Query: api_level, config_hash, cpu_name, gpu_renderer | XhsConfigService |
| `GET` | `api/sns/v1/system_service/captcha_link` |  | CommonServices |
| `GET` | `api/sns/v1/system_service/college_names` | Query: keyword, page, page_size | UserServices |
| `GET` | `api/sns/v1/system_service/config` | Query: launchtimes | ConfigServices |
| `GET` | `api/sns/v1/system_service/config/video_download_switch` |  | GeneralSettingServices |
| `GET` | `api/sns/v1/system_service/im_user_sign` | Query: app_id | LiveRtcSignService |
| `GET` | `api/sns/v1/system_service/launch` |  | ConfigServices |
| `GET` | `api/sns/v1/system_service/network_identify` | Query: network_type, imsi, private_ip, phone | UnicomFreeService |
| `GET` | `api/sns/v1/system_service/push/redswitch` |  | PersonalizedService |
| `GET` | `api/sns/v1/system_service/push/switch` |  | UserServices |
| `GET` | `api/sns/v1/system_service/push/switch` |  | NoteDetailService |
| `GET` | `api/sns/v1/system_service/push/switch/get_switch_id` | Query: user_id, platform, switch_id | LiveRemindSwitchHelper |
| `GET` | `api/sns/v1/system_service/push/switch/get_switch_id` | Query: user_id, platform, switch_id | EdithUserServices |
| `GET` | `api/sns/v1/system_service/push/switch_v2` | Query: user_id, platform | PushServices |
| `GET` | `api/sns/v1/system_service/push/switch_v2` | Query: user_id, platform | EdithUserServices |
| `GET` | `api/sns/v1/system_service/setting_event` |  | SettingServices |
| `GET` | `api/sns/v1/system_service/shield_sms_check/send_code` | Query: phone, zone | VerificationCodeServices |
| `GET` | `api/sns/v1/system_service/shield_sms_check/user_info` |  | VerificationCodeServices |
| `GET` | `api/sns/v1/user/at/recent` | Query: oid, start | UserServices |
| `GET` | `api/sns/v1/user/block/list` | Query: start, num | UserServices |
| `GET` | `api/sns/v1/user/extra_info` | Query: user_id | ProfileIPInfoModel |
| `GET` | `api/sns/v1/user/followers` | Query: user_id, cursor | UserServices |
| `GET` | `api/sns/v1/user/followings` | Query: user_id, cursor, order | UserServices |
| `GET` | `api/sns/v1/user/followings/all` |  | MatrixUserServices |
| `GET` | `api/sns/v1/user/followings/page` | Query: page, page_size, scene, template_id | IUserService |
| `GET` | `api/sns/v1/user/login-confirmation/status` | Query: state_token | AccountService |
| `GET` | `api/sns/v1/user/login/acct_group/delete` | Query: acct_group_id, target_user_id, rule_id | ChangeAccountService |
| `GET` | `api/sns/v1/user/login/acct_group/list` | Query: acct_group_id, rule_id | ChangeAccountService |
| `GET` | `api/sns/v1/user/login/onboardingextra` | Query: deviceId | LoginServices |
| `GET` | `api/sns/v1/user/logout` |  | AccountService |
| `GET` | `api/sns/v1/user/me/authority` | Query: scene | AccountService |
| `GET` | `api/sns/v1/user/me/authority` | Query: scene | AccountService |
| `GET` | `api/sns/v1/user/password/modify` | Query: origin_password, password | SecurityAccountService |
| `GET` | `api/sns/v1/user/password/reset` | Query: zone, phone, password, mobile_token | LoginServices |
| `GET` | `api/sns/v1/user/phone/bind/appeal/check` |  | SecurityAccountService |
| `GET` | `api/sns/v1/user/phone/pre-check` | Query: type, zone, phone | IBindService |
| `GET` | `api/sns/v1/user/privacy` |  | AdvanceService |
| `GET` | `api/sns/v1/user/privacy` |  | EdithUserServices |
| `GET` | `api/sns/v1/user/privacy/collection` | Query: post_later_flag | PrivacyServices |
| `GET` | `api/sns/v1/user/privacy/declare` |  | PrivacyServices |
| `GET` | `api/sns/v1/user/privacy/personalization` |  | PersonalizationService |
| `GET` | `api/sns/v1/user/privacy/visited` |  | PrivacyServices |
| `GET` | `api/sns/v1/user/signoff/flow` |  | AccountService |
| `GET` | `api/sns/v1/user/social_info` |  | AccountService |
| `GET` | `api/sns/v1/user/third/account_info` |  | IBindService |
| `GET` | `api/sns/v1/user/verify/flow_config` | Query: business_code | IIdentityService |
| `GET` | `api/sns/v1/user/verify/resources/pag` |  | CommonServices |
| `GET` | `api/sns/v1/user/verify/verify_info` | Query: biz_id | IIdentityService |
| `GET` | `api/sns/v1/user/verify/verify_info` | Query: biz_id | IMiniToolService |
| `GET` | `api/sns/v1/user/widget/info` | Query: target_user_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, ext_params | WidgetService |
| `GET` | `api/sns/v1/user/widget/me` | Query: ext_params, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | WidgetService |
| `GET` | `api/sns/v1/user/widget/update/entrance` | Query: ext_params | WidgetService |
| `GET` | `api/sns/v1/user/{userid}/followings` | Path: userid; Query: start, com.alipay.ams.component.sdk.InternalConfigKeys.ADDRESS_ELEMENT_MODE | UserServices |
| `GET` | `api/sns/v1/video/lookback/getItemWithId` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | AlphaConfigService |
| `GET` | `api/sns/v10/search/notes` |  | AliothServices |
| `GET` | `api/sns/v10/search/videos` | Query: keyword, search_id, session_id, tab_id, scene, load_type, geo, location_permission, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, ext_params, sort, filters, cursor | AliothServices |
| `GET` | `api/sns/v2/guide/tab_pop` | Query: tab | TabPropService |
| `GET` | `api/sns/v2/hey/qrcode` | Query: hey_id | ShareService |
| `GET` | `api/sns/v2/hey/{user_id}/hey_gallery` | Path: user_id | HeyServices |
| `GET` | `api/sns/v2/live/share` | Query: room_id, share_source, share_source_id, content_type | AlphaApiService |
| `GET` | `api/sns/v2/live/share` | Query: room_id, share_source, share_source_id, content_type | LiveShareLiveGoService |
| `GET` | `api/sns/v2/message/config` | Query: register_time | MsgServices |
| `GET` | `api/sns/v2/message/config` | Query: register_time | MsgServices |
| `GET` | `api/sns/v2/message/message_box` | Query: start, num, type | MessageServices |
| `GET` | `api/sns/v2/message/you/likes` | Query: start, num, msg_version | MessageServices |
| `GET` | `api/sns/v2/message/you/mentions` | Query: start, num, msg_version | MessageServices |
| `GET` | `api/sns/v2/note/image/stickers` | Query: note_id | StickerService |
| `GET` | `api/sns/v2/note/image/stickers` | Query: note_id, geo | FollowNoteModel |
| `GET` | `api/sns/v2/note/music/library/collection` |  | MusicService |
| `GET` | `api/sns/v2/note/music/library/collection_music` | Query: page, page_size, collection_id, required_beat | MusicService |
| `GET` | `api/sns/v2/note/music/library/recommend` | Query: required_beat | MusicService |
| `GET` | `api/sns/v2/page/topic/config` | Query: page_id, module_id | TopicService |
| `GET` | `api/sns/v2/recommend/user/weibo` | Query: keyword, page | UserServices |
| `GET` | `api/sns/v2/search/filter` | Query: word_request_id, search_id, tab_id, geo, location_permission, filters, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, api_extra, ext_params | AliothServices |
| `GET` | `api/sns/v2/system_service/splash_config` | Query: android_device_model | SplashConfigApiService |
| `GET` | `api/sns/v2/tag/user/{target_user_id}/followed` | Path: target_user_id; Query: start | TagServices |
| `GET` | `api/sns/v2/user/account_info` |  | AccountService |
| `GET` | `api/sns/v2/user/followings/ballarea` | Query: reverse, live, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pin_user_id | HeyServices |
| `GET` | `api/sns/v2/user/followings/extra` | Query: user_id_list, tab_type | UserServices |
| `GET` | `api/sns/v2/user/followings/self` | Query: cursor, order, tab_type | UserServices |
| `GET` | `api/sns/v2/user/phone/zones` |  | IVerifyCodeService |
| `GET` | `api/sns/v2/user/widget/info` | Query: target_user_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, ext_params | WidgetService |
| `GET` | `api/sns/v2/user/widget/me` | Query: type_2tab, move_hey_exp, ext_params | WidgetService |
| `GET` | `api/sns/v3/recommend/user/explore` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, page, num, memory_size | LoginServices |
| `GET` | `api/sns/v3/system_service/flag_exp` | Query: fetchSceneTag | XhsExperimentService |
| `GET` | `api/sns/v3/system_service/flag_exp` | Query: fetchSceneTag, deviceLevel | XhsExperimentService |
| `GET` | `api/sns/v3/tag/login_recommend` |  | LoginServices |
| `GET` | `api/sns/v3/user/info` | Query: user_id, profile_page_head_exp | AlphaUserEdithService |
| `GET` | `api/sns/v3/user/info` | Query: user_id, profile_page_head_exp | ShopDetailPendantUserService |
| `GET` | `api/sns/v3/user/info` |  | UserServices |
| `GET` | `api/sns/v3/user/me` |  | AccountService |
| `GET` | `api/sns/v4/note/user/posted` | Query: user_id, cursor, num, sub_tag_id, use_cursor, pin_note_id, pin_note_ids, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AlphaUserEdithService |
| `GET` | `api/sns/v4/note/user/posted` | Query: user_id, sub_tag_id, cursor, num, use_cursor, pin_note_id, pin_note_ids, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, just_viewed_note_id, privacy_type, empty_state_mode, page_strategy | NoteServices |
| `GET` | `api/sns/v4/search/banner` | Query: scene, click_time, impress_time | AliothServices |
| `GET` | `api/sns/v4/search/recommend` | Query: keyword, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, ai_mode, word_request_id, geo, word_request_situation, cursor_index, last_query, last_query_time, note_id, note_source, note_enter_time, exp_infos, guide_item_id, ext_params | AliothServices |
| `GET` | `api/sns/v4/search/recommend` | Query: keyword, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, word_request_id, geo | AliothServices |
| `GET` | `api/sns/v4/search/recommend` | Query: keyword, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, geo | CommentGoodsSearchApi |
| `GET` | `api/sns/v4/search/recommend` | Query: keyword, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, geo | CommentGoodsSearchApi |
| `GET` | `api/sns/v4/search/recommend_dqa` | Query: keyword, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, dqa_session_keywords, ext_info, image_guide_words | AliothServices |
| `GET` | `api/sns/v4/search/trending` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pin_word, preview_ad, word_request_situation, last_query, last_query_time, hint_word, hint_word_type, hint_word_request_id, note_id, note_type, note_view_duration, note_time, exp_infos, ext_params, geo, card_entry | AliothServices |
| `GET` | `api/sns/v5/page/notes` | Query: page_id, page_size, sort, cursor, inspiration_top_note_ids | TopicService |
| `GET` | `api/sns/v6/message/detect` |  | MessageServices |
| `GET` | `api/sns/v6/message/get_unread_count` |  | MsgServices |
| `POST` | `/api/sns/agentspark/dot/chat/delete` | Body: com.xingin.dots.legacy.network.entities.history.DotsChatDeleteRequest | DotsApi |
| `POST` | `/api/sns/agentspark/dot/content/dislike/report` | Body: com.xingin.dots.legacy.network.entities.feedback.DotsLikeReportRequest | DotsApi |
| `POST` | `/api/sns/agentspark/dot/content/like/report` | Body: com.xingin.dots.legacy.network.entities.feedback.DotsLikeReportRequest | DotsApi |
| `POST` | `/api/sns/agentspark/dot/download/deeplink` | Body: u27.c | DotsAgentSettingApi |
| `POST` | `/api/sns/agentspark/dot/guide/ack` | Body: com.xingin.dots.legacy.network.entities.recommend.DotsGuideWordAckRequest | DotsApi |
| `POST` | `/api/sns/agentspark/dot/messages/delete` | Body: com.xingin.dots.legacy.network.entities.share.DotsDeleteMessagesRequest | DotsApi |
| `POST` | `/api/sns/agentspark/dot/messages/share` | Body: com.xingin.dots.legacy.network.entities.share.DotsCreateShareInfoRequest | DotsApi |
| `POST` | `/api/sns/agentspark/dot/messages/share_image` | Body: com.xingin.dots.legacy.network.entities.share.DotsShareImageRequest | DotsApi |
| `POST` | `/api/sns/agentspark/dot/question/select` | Body: com.xingin.dots.legacy.network.entities.guidequestion.DotsQuestionSelectRequest | DotsApi |
| `POST` | `/api/sns/agentspark/dot/subscription/cancel` | Field: subscription_id | AgentDotsApi |
| `POST` | `/api/sns/agentspark/dot/subscription/delete` | Field: subscription_id | AgentDotsApi |
| `POST` | `/api/sns/agentspark/dot/subscription/restore` | Field: subscription_id | AgentDotsApi |
| `POST` | `/api/sns/agentspark/onebox/realtime-search` | Body: okhttp3.RequestBody | DotsRealtimeSearchHttpApi |
| `POST` | `/api/sns/agentspark/user/collect_target` | Query: type, target_id, collected | DotsApi |
| `POST` | `/api/sns/agentspark/user/collect_version` | Body: com.xingin.dots.legacy.network.entities.collect.DotsCollectRequest | DotsApi |
| `POST` | `/api/sns/agentspark/user/list_collects` | Body: com.xingin.dots.legacy.network.entities.collect.DotsListCollectsRequest dotsListCollectsRequest, kotlin.coroutines.Continuation<? super com.xingin.dots.legacy.network.entities.collect.DotsCollectListData> | DotsApi |
| `POST` | `/api/sns/agentspark/user_cancel_collect` | Body: com.xingin.dots.legacy.network.entities.collect.DotsCancelCollectRequest | DotsApi |
| `POST` | `/api/sns/agentspark/v1/feedback/report` | Body: com.xingin.dots.legacy.network.entities.feedback.DotsFeedbackReportRequest | DotsApi |
| `POST` | `/api/sns/agentspark/v1/vote_gsb_candidate` | Body: com.xingin.dots.legacy.network.entities.gsb.DotsVoteGsbCandidateRequest | DotsApi |
| `POST` | `/api/sns/badge/update_badge` | Body: fo4.b | MsgServices |
| `POST` | `/api/sns/capa/servicegw/chapter/generate` | Body: com.xingin.capa.network.model.chapter.ChapterGenerateRequest | ChapterService |
| `POST` | `/api/sns/capa/servicegw/device_model/calculate` | Body: com.xingin.capa.network.model.device.DeviceScoreParamModel | DeviceScoreService |
| `POST` | `/api/sns/capa/servicegw/getpoilistv2` | Field: latitude, longitude | PoiService |
| `POST` | `/api/sns/capa/servicegw/podcast/summary` | Body: com.xingin.capa.network.model.podcast.PodcastSummaryRequestBody | PodcastService |
| `POST` | `/api/sns/capa/servicegw/retrieve/report` | Field: type, ids | CommonService |
| `POST` | `/api/sns/capa/servicegw/rewrite/audio/text` | Field: content, extra_info | ASRVoiceInputService |
| `POST` | `/api/sns/capa/servicegw/rewrite/audio/text` | Field: content, extra_info | VoiceInputService |
| `POST` | `/api/sns/capa/servicegw/suggest/topics` | Body: com.xingin.capa.network.model.topic.TopicRecommendRequestBody | TopicService |
| `POST` | `/api/sns/capa/servicegw/title_recommend` | Body: com.xingin.capa.network.model.TitleRecommendRequestBody | TitleService |
| `POST` | `/api/sns/capa/servicegw/title_recommend` | Body: com.xingin.net.gen.model.Edith2ApiSnsCapaServicegwTitleRecommendPostRequestBody | CapaApi |
| `POST` | `/api/sns/capa/servicegw/v1/guide/report_action` | Field: guide_type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, action, ext_info | HalfProfileInspirePostService |
| `POST` | `/api/sns/capa/servicegw/v1/guide_event` | Field: event_type | PopGuideService |
| `POST` | `/api/sns/capa/support/comment/guide_action` | Field: comment_id, stage, action | CommonCommentService |
| `POST` | `/api/sns/challenge/recomend` | Query: type | ChallengeService |
| `POST` | `/api/sns/challenge/recommend_guide` | Body: com.capa.challenge_card.model.ChallengeRecommendRequestBody challengeRecommendRequestBody, kotlin.coroutines.Continuation<? super com.capa.challenge_card.model.ChallengeRecommendResult> | ChallengeCardService |
| `POST` | `/api/sns/component/spam_check` | Body: gu2.a | CapaCcrSecurityAuditService |
| `POST` | `/api/sns/inspiration/ai/async/cancel` | Body: com.xingin.capa.ai.async.net.CancelBody | AIAsyncNetService |
| `POST` | `/api/sns/inspiration/ai/async/cancel` | Body: com.xingin.net.gen.model.Edith2ApiSnsInspirationAiAsyncCancelPostRequestBody | CapaApi |
| `POST` | `/api/sns/inspiration/ai/async/commit` | Body: dm2.a | AIAsyncNetService |
| `POST` | `/api/sns/inspiration/ai/async/commit` | Body: com.xingin.net.gen.model.Edith2ApiSnsInspirationAiAsyncCommitPostRequestBody | CapaApi |
| `POST` | `/api/sns/inspiration/ai_edit_image/batch_get_results` | Body: f34.c | Capa51AiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/batch_get_results` | Body: f34.c | CNYAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/batch_get_results` | Body: f34.c | ImageEditAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/batch_get_results` | Body: f34.c | ImAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/batch_get_results/comment` | Body: f34.c | CommentAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/commit` | Body: f34.a | ImageEditAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/commit/cny` | Body: f34.a | CNYAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/commit/comment` | Body: f34.a | CommentAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/commit/im` | Body: f34.a | ImAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/commit/tmp` | Body: f34.a | Capa51AiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/sugs/batch_recommend` | Body: com.xingin.capa.v2.feature.aiphotoshop.model.AiPhotoShopSugRecommendParams | Capa51AiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/sugs/batch_recommend` | Body: com.xingin.capa.v2.feature.aiphotoshop.model.AiPhotoShopSugRecommendParams | CNYAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/sugs/batch_recommend` | Body: com.xingin.capa.v2.feature.aiphotoshop.model.AiPhotoShopSugRecommendParams | CommentAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/sugs/batch_recommend` | Body: com.xingin.capa.v2.feature.aiphotoshop.model.AiPhotoShopSugRecommendParams | ImageEditAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/sugs/batch_recommend` | Body: com.xingin.capa.v2.feature.aiphotoshop.model.AiPhotoShopSugRecommendParams | ImAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/task` | Field: request_id, type, biz_type | Capa51AiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/task` | Field: request_id, type, biz_type | CNYAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/task` | Field: request_id, type, biz_type | ImageEditAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/task` | Field: request_id, type, biz_type | ImAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_edit_image/task/comment` | Field: request_id, type, biz_type | CommentAiPhotoShopService |
| `POST` | `/api/sns/inspiration/ai_sync_task` | Body: dm2.b | AIAsyncNetService |
| `POST` | `/api/sns/inspiration/content/operate` | Field: type, content_id, source_type | VideoTemplateBattleReportService |
| `POST` | `/api/sns/inspiration/content/user/info` | Field: source_type | VideoTemplateBattleReportService |
| `POST` | `/api/sns/inspiration/delete/virtual_image` |  | AIAsyncNetService |
| `POST` | `/api/sns/inspiration/effect/cv` | Body: com.xingin.capa.network.model.EffectCvPostRequestBody | CapaAiImageService |
| `POST` | `/api/sns/inspiration/effect/cv` | Body: com.xingin.net.gen.model.Edith2ApiSnsInspirationEffectCvPostRequestBody | CapaApi |
| `POST` | `/api/sns/inspiration/emoji/tabs` |  | CapaEmojiConfigService |
| `POST` | `/api/sns/inspiration/generate/cv` | Body: com.xingin.capa.feature_model.tag.TagCvRequestBody | MaterialAPIService |
| `POST` | `/api/sns/inspiration/generate/cv` | Body: com.xingin.capa.network.model.GenerateCvPostRequestBody | CapaAiImageService |
| `POST` | `/api/sns/inspiration/gepoi` | Field: latitude, longitude | PoiService |
| `POST` | `/api/sns/inspiration/graffiti_pens` | Query: category_id, graffiti_pen_id, page_size | GraffitiMaterialPenService |
| `POST` | `/api/sns/inspiration/long_text/page_operate` | Body: com.xingin.capa.network.model.longnote.LongNotePageOperatorRequestBody | LongNoteService |
| `POST` | `/api/sns/inspiration/long_text_structure` | Field: origin_text | LongNoteService |
| `POST` | `/api/sns/inspiration/longtext2img` | Body: com.xingin.capa.network.model.longnote.LongNoteRequestBody | LongNoteService |
| `POST` | `/api/sns/inspiration/operate_user_authorize` | Field: target_user_id, type, ai_template_id | AiPortraitGroupPhotoService |
| `POST` | `/api/sns/inspiration/operatev2` | Body: com.xingin.capa.network.model.ttiv3.replay.Text2ImageReplaceRequestBodyV3 | TTiV3Service |
| `POST` | `/api/sns/inspiration/prompt_info` | Body: rq2.d | AiPhotoShopService |
| `POST` | `/api/sns/inspiration/review` | Body: com.xingin.capa.network.model.longnote.SecurityCheckRequestBody | LongNoteService |
| `POST` | `/api/sns/inspiration/rsynctts` | Field: ttsParams | TemplateTtsService |
| `POST` | `/api/sns/inspiration/scrawl2mg` | Body: com.xingin.net.gen.model.Edith2ApiSnsInspirationScrawl2mgPostRequestBody | CapaApi |
| `POST` | `/api/sns/inspiration/search/template` | Field: search_type, keyword, cursor, page_size | ImageTemplateService |
| `POST` | `/api/sns/inspiration/select/default/virtual_image` | Body: em2.j | AIAsyncNetService |
| `POST` | `/api/sns/inspiration/storyline/dialog_agent` | Body: nv3.h hVar, kotlin.coroutines.Continuation<java.lang.Object> | StorylineApiService |
| `POST` | `/api/sns/inspiration/storyline/frame_info_commit` | Body: nv3.j jVar, kotlin.coroutines.Continuation<java.lang.Object> | StorylineApiService |
| `POST` | `/api/sns/inspiration/storyline/highlight` | Body: nv3.k kVar, kotlin.coroutines.Continuation<? super rv3.k> | StorylineApiService |
| `POST` | `/api/sns/inspiration/storyline/prompt` | Body: nv3.l lVar, kotlin.coroutines.Continuation<? super rv3.k> | StorylineApiService |
| `POST` | `/api/sns/inspiration/storyline/task` | Body: nv3.m mVar, kotlin.coroutines.Continuation<? super rv3.k> | StorylineApiService |
| `POST` | `/api/sns/inspiration/storyline/translate` | Field: texts, language | MultiLanguageService |
| `POST` | `/api/sns/inspiration/text2img/common` | Query: text, business | DotsApi |
| `POST` | `/api/sns/inspiration/text2img/common` | Query: text, business | SearchAgentPageApi |
| `POST` | `/api/sns/inspiration/text2imgv3` | Body: com.xingin.capa.network.model.ttiv3.Text2ImageRequestBodyV3 | TTiV3Service |
| `POST` | `/api/sns/inspiration/text2mg2ab` | Body: com.xingin.capa.network.model.tti.Text2ImageRequestBody | TTiService |
| `POST` | `/api/sns/inspiration/text2mg2ab` | Body: com.xingin.capa.network.model.ttiv2.Text2ImageRequestBodyV2 | TTiV2Service |
| `POST` | `/api/sns/inspiration/text2mg2ab` | Body: com.xingin.net.gen.model.Edith2ApiSnsInspirationText2mg2abPostRequestBody | CapaApi |
| `POST` | `/api/sns/inspiration/text_template` |  | TextTemplateService |
| `POST` | `/api/sns/inspiration/textimg/operate` | Body: com.xingin.capa.network.model.ttiv2.replay.Text2ImageReplaceRequestBody | TTiV2Service |
| `POST` | `/api/sns/inspiration/videotemplate/effect/upload` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_TASK_ID, video_file_id | VideoTemplateVerifyService |
| `POST` | `/api/sns/inspiration/voice_clone/commit` | Field: text_id, audio_file_id | VoiceCloneService |
| `POST` | `/api/sns/inspiration/voice_clone/delete_voice` | Field: voice_id, voice_type | VoiceCloneService |
| `POST` | `/api/sns/inspiration/voice_clone/get_cloning_text` | Field: text_id | VoiceCloneService |
| `POST` | `/api/sns/inspiration/voice_clone/update_voice` | Field: voice_id, new_voice_name, voice_type, default_voice, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS, voice_version_code | VoiceCloneService |
| `POST` | `/api/sns/prof/common_phrase/page/render/get` |  | CommonPhraseService |
| `POST` | `/api/sns/prof/tool/consume` | Field: receiverId, productServiceCode | MsgServices |
| `POST` | `/api/sns/reach/msg/ack` | Body: eh2.c | ReachMessageService |
| `POST` | `/api/sns/red/live/app/cross_year/msg/switch` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | LiveCrossYearActivityApiService |
| `POST` | `/api/sns/red/live/app/family/v1/join_compensate` | Query: room_id, host_id | LiveFamilyApiService |
| `POST` | `/api/sns/red/live/app/fansgroup/v1/activate` | Field: room_id, host_id | ILiveFansGroupApiService |
| `POST` | `/api/sns/red/live/app/fansgroup/v1/join` | Field: room_id, host_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | ILiveFansGroupApiService |
| `POST` | `/api/sns/red/live/app/fansgroup/v1/update/group_name` | Field: name | ILiveFansGroupApiService |
| `POST` | `/api/sns/red/live/app/feed/v1/linking_feed_for_dev` | Field: room_id, page_source, pos, tag_source, new_flag, extra_info | AlphaConfigLiveRoomService |
| `POST` | `/api/sns/red/live/app/reservation/v1/cancel_subscribe` | Query: reservation_id, source_id, source_type | AlphaReservationService |
| `POST` | `/api/sns/red/live/app/reservation/v1/cancel_subscribe` | Query: reservation_id, source_id, source_type | LiveRepository |
| `POST` | `/api/sns/red/live/app/reservation/v1/subscribe` | Query: reservation_id, source_id, source_type | AlphaReservationService |
| `POST` | `/api/sns/red/live/app/reservation/v1/subscribe` | Query: reservation_id, source_id, source_type | LiveRepository |
| `POST` | `/api/sns/red/live/app/v1/ecology/use_bag_property` | Field: room_id, source_id, source_type, bag_property_id | AlphaGiftLiveGoService |
| `POST` | `/api/sns/red/live/app/v1/livegoods/choice_goods/k/cancel/playback` | Field: host_id, contract_id, playback_end_time, choice_goods_id | AlphaGoodsProductService |
| `POST` | `/api/sns/red/live/app/v1/livegoods/choice_goods/k/operate/sync/switch` | Field: host_id, room_id, open_status | AlphaGoodsEdithService |
| `POST` | `/api/sns/red/live/app/v1/livegoods/choice_goods/k/sort/goods` | Field: host_id, contract_ids, choice_goods_id, categoryId, scene | AlphaGoodsProductService |
| `POST` | `/api/sns/red/live/app/v1/livegoods/choice_goods/operate/permission` | Field: host_id, sa_user_id, permission_status | AlphaGoodsProductService |
| `POST` | `/api/sns/red/live/app/v1/mall/batch_sort_pool_goods` | Field: plan_id, sort_contract_list | AlphaPlanLiveMallService |
| `POST` | `/api/sns/red/live/app/v1/mall/contract/extra/subtitle` | Body: pz0.e2 | AlphaGoodsEdithService |
| `POST` | `/api/sns/red/live/app/v1/mall/goods_card/popup` | Field: operate_source, room_id, contract_id | AlphaGoodsLiveMallService |
| `POST` | `/api/sns/red/live/app/v1/mall/goods_explain/cancle_request_explain_goods` | Field: room_id, contract_id | AlphaGoodsLiveMallService |
| `POST` | `/api/sns/red/live/app/v1/room/join_room_intercept` | Query: room_id, host_id | LiveFamilyApiService |
| `POST` | `/api/sns/red/live/app/v1/room/start/check` | Field: room_id, content_type, distribute, join_limit | LiveCoreApiLiveRoomService |
| `POST` | `/api/sns/red/live/app/v2/mall/goods/contract/create` | Body: pz0.p | AlphaGoodsLiveMallService |
| `POST` | `/api/sns/red/live/media/debug_info` | Field: room_id | AlphaDebugInfoService |
| `POST` | `/api/sns/red/livemall/app/explain_clip/red_dot_read` | Body: com.xingin.commercial.transactionnote.commodity.repo.GoodsNoteModel.a | GoodsNoteModel |
| `POST` | `/api/sns/red/livemall/app/join_room/get_biz_info` | Field: room_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AlphaConfigListLiveMallService |
| `POST` | `/api/sns/red/livemall/app/live/comment/container/exposure/report` | Field: room_id, container_ids | LiveCommentContainerApi |
| `POST` | `/api/sns/red/livemall/app/live/comment/container/list` | Field: room_id, biz_types, query_scopes | LiveCommentContainerApi |
| `POST` | `/api/sns/red/livemall/app/shop/member_info` | Field: room_id | AlphaMemberService |
| `POST` | `/api/sns/red/livemall/app/trailer/check_auth` | Field: host_id | AlphaLivePreviewLiveMallService |
| `POST` | `/api/sns/red/livemall/app/trailer/v1/cancel_subscribe_good` | Field: user_id, trailer_id, item_id | AlphaGoodsLiveMallService |
| `POST` | `/api/sns/red/livemall/app/trailer/v1/subscribe_good` | Field: user_id, trailer_id, item_id, source_type, sku_id, contract_id, need_add_cart | AlphaGoodsLiveMallService |
| `POST` | `/api/sns/red/livemall/app/trailer/v1/subscribe_good` | Field: user_id, trailer_id, item_id, source_type, sku_id, contract_id, add_cart_num | GoodsDetailService |
| `POST` | `/api/sns/red/livemall/manager/app/live_goods_category/v1/add` | Body: com.xingin.alpha.goods.prepare.category.bean.GoodsCategoryReqData | LiveGoodsCategoryService |
| `POST` | `/api/sns/red/livemall/manager/app/live_goods_category/v1/delete` | Body: com.xingin.alpha.goods.prepare.category.bean.GoodsDeleterReqData | LiveGoodsCategoryService |
| `POST` | `/api/sns/red/livemall/manager/app/live_goods_category/v1/edith` | Body: com.xingin.alpha.goods.prepare.category.bean.GoodsDeleterReqData | LiveGoodsCategoryService |
| `POST` | `/api/sns/red/livemall/manager/app/live_goods_category/v1/live_goods_bind` | Body: com.xingin.alpha.goods.prepare.category.bean.GoodsAddReqData | LiveGoodsCategoryService |
| `POST` | `/api/sns/red/livemall/manager/app/live_goods_category/v1/pool_goods_bind` | Body: com.xingin.alpha.goods.prepare.category.bean.GoodsAddReqData | LiveGoodsCategoryService |
| `POST` | `/api/sns/red/livemall/manager/app/pool_goods/v1/list_detail/by_contract` | Body: com.xingin.alpha.goods.prepare.category.bean.GoodsAddReqData | LiveGoodsCategoryService |
| `POST` | `/api/sns/thoth/decision/result` |  | ColdStartConfigService |
| `POST` | `/api/sns/user/v1/urge_update/list` | Field: type, cursor | UserServices |
| `POST` | `/api/sns/user/v1/urge_update/read_all` |  | UserServices |
| `POST` | `/api/sns/user/v1/urge_update/update_bother_status` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | UserServices |
| `POST` | `/api/sns/user/v1/urge_update/urge` | Field: target_id | UserServices |
| `POST` | `/api/sns/user_cache/offline/ack` | Field: user_ids | LocalRelationServices |
| `POST` | `/api/sns/user_cache/report_tracking` | Body: com.xingin.local.relation.bean.ReportAllLocalRelationUserBody | LocalRelationServices |
| `POST` | `/api/sns/v1/activity_platform/customized_task_report` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_TASK_ID | CNYMarketTaskWidgetApi |
| `POST` | `/api/sns/v1/ads/midvideo/strategy` | Body: brc.i | SketchAdNetService |
| `POST` | `/api/sns/v1/attribution/conversion/data` | Field: data | LoginServices |
| `POST` | `/api/sns/v1/basemode/report` | Field: platform, versionName, channel, deviceId, baseModeId, projectId, appId, build, cpuName, overseasChannel, eventName, extraMap, timestamp, sign | BaseModeServices |
| `POST` | `/api/sns/v1/basemode/sendmsg` | Field: baseModeId, timestamp | MsgServices |
| `POST` | `/api/sns/v1/board` | Field: share_mode, invite_user_ids | CommonBoardService |
| `POST` | `/api/sns/v1/board/share_board/accept_invite` | Field: share_board_id, share_key | CommonBoardService |
| `POST` | `/api/sns/v1/board/share_board/quit` | Field: share_board_id | CommonBoardService |
| `POST` | `/api/sns/v1/board/share_board/remove_user` | Field: share_board_id, target_user_id | CommonBoardService |
| `POST` | `/api/sns/v1/circle/add_pin` | Field: circle_id, post_id | CircleApiService |
| `POST` | `/api/sns/v1/circle/add_selection` | Field: circle_id, post_id | CircleApiService |
| `POST` | `/api/sns/v1/circle/apply_join` | Field: circle_id | RedCircleHomeService |
| `POST` | `/api/sns/v1/circle/cancel_pin` | Field: circle_id, post_id | CircleApiService |
| `POST` | `/api/sns/v1/circle/cancel_selection` | Field: circle_id, post_id | CircleApiService |
| `POST` | `/api/sns/v1/circle/comment/dislike` | Field: comment_id | CircleService |
| `POST` | `/api/sns/v1/circle/comment/like` | Field: comment_id | CircleService |
| `POST` | `/api/sns/v1/circle/post` | Body: com.xingin.capa.network.model.circle.CirclePostParamModel | CirclePostApiService |
| `POST` | `/api/sns/v1/circle/post` | Body: com.xingin.capa.network.model.circle.CirclePostVideoParamModel | CirclePostApiService |
| `POST` | `/api/sns/v1/circle/post/delete` | Field: circle_id, post_id | CircleApiService |
| `POST` | `/api/sns/v1/circle/post/dislike` | Query: post_id, post_user_id, circle_id | RedCircleTabFeedService |
| `POST` | `/api/sns/v1/circle/post/like` | Query: post_id, post_user_id, circle_id | RedCircleTabFeedService |
| `POST` | `/api/sns/v1/circle/prepost` | Query: circle_id, content, type, partition, ref_type, ref_id | CirclePostApiService |
| `POST` | `/api/sns/v1/circle/prepost` | Body: com.xingin.capa.network.model.circle.CirclePrePostParamModel | CirclePostApiService |
| `POST` | `/api/sns/v1/circle/quit` | Field: circle_id | CircleApiService |
| `POST` | `/api/sns/v1/circle/remove` | Field: circle_id, user_id | CircleApiService |
| `POST` | `/api/sns/v1/circle/{sayId}/comment` | Path: sayId; Field: content, target_comment_id | CircleService |
| `POST` | `/api/sns/v1/cny/2025/sticker/update_user_decorated_sticker` | Body: com.xingin.matrix.sticker.entities.SaveStickerRequestBody | StickerServices |
| `POST` | `/api/sns/v1/cny_new/open_user_avatar_icon_switch` | Field: open_status | UserServices |
| `POST` | `/api/sns/v1/content/dislike/report` | Query: object_id, object_type, page_instance, operate_type | ShopAiGuideDislikeApiService |
| `POST` | `/api/sns/v1/content/dislike/report` | Body: com.xingin.dots.legacy.network.entities.feedback.DotsDislikeReportRequest | DotsApi |
| `POST` | `/api/sns/v1/content/dislike/report` | Query: object_id, object_type, note_id, note_author_id, page_instance, operate_type, track_id, extra_info | FeedbackService |
| `POST` | `/api/sns/v1/content/navigator_report` | Field: instance_id, target_id | GuideService |
| `POST` | `/api/sns/v1/content/navigator_report` | Query: instance_id, note_id, event_type | PodcastApiService |
| `POST` | `/api/sns/v1/content/navigator_report` | Query: instance_id, note_id, event_type | NoteDetailService |
| `POST` | `/api/sns/v1/content/navigator_report` | Field: instance_id, target_id, event_type | RedDotServices |
| `POST` | `/api/sns/v1/content/navigator_report` | Field: instance_id, target_id | RedDotServices |
| `POST` | `/api/sns/v1/creator/red_app/batch_get_cdn_url` | Field: file_ids | MiniToolShareService |
| `POST` | `/api/sns/v1/creator/skills/list` | Body: mda.j | WorksServers |
| `POST` | `/api/sns/v1/creator/subscribe_helper` | Query: type | MsgAuthorHelperServices |
| `POST` | `/api/sns/v1/effect/video/recommend` | Body: eq2.b | MaterialAPIService |
| `POST` | `/api/sns/v1/eoi/media/medialist` | Body: com.xingin.multi.entity.MediaRequestBody | MultiMediaService |
| `POST` | `/api/sns/v1/eoi/media/recommend` | Body: com.xingin.capa.network.model.poi.EoiRequestBody | PoiService |
| `POST` | `/api/sns/v1/ext/agora/task/userhandle` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_TASK_ID, signature, timestamp, entity_id | VolleyService |
| `POST` | `/api/sns/v1/ext/share/data` | Field: app_key, data_code | VolleyService |
| `POST` | `/api/sns/v1/file/faved/collect` | Field: document_id | DocumentPreviewPageApi |
| `POST` | `/api/sns/v1/file/faved/uncollect` | Field: document_id | ProfileCollectDocumentApi |
| `POST` | `/api/sns/v1/file/faved/uncollect` | Field: document_id | DocumentPreviewPageApi |
| `POST` | `/api/sns/v1/filter/collect` | Field: filter_id, space | FilterServices |
| `POST` | `/api/sns/v1/filter/collect` | Field: filter_id, space | INnsDetailService |
| `POST` | `/api/sns/v1/followings/various/report` | Body: d87.c | NoteDetailService |
| `POST` | `/api/sns/v1/history/report` | Body: hra.n | BrowseHistoryApiService |
| `POST` | `/api/sns/v1/homefeed/guide/callback` | Field: guide_type, ui_type | HomeFeedGuideService |
| `POST` | `/api/sns/v1/interaction/comment/collect` | Body: r09.b | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/collect/cancel` | Body: r09.b | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/component/report` | Query: component_type | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/delete` | Body: r09.d | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/delete` | Body: com.xingin.models.services.CommonCommentService.a | CommonCommentService |
| `POST` | `/api/sns/v1/interaction/comment/dislike` | Body: r09.h | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/dislike` | Body: com.xingin.models.services.CommonCommentService.b | CommonCommentService |
| `POST` | `/api/sns/v1/interaction/comment/downvoted/cancel` | Body: r09.f | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/downvoted/post` | Body: r09.f | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/downvoted/reason` | Query: note_id, comment_id, selected_reasons | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/downvoted/reason` | Body: t67.l | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/fold` | Field: comment_id, note_id | ReportService |
| `POST` | `/api/sns/v1/interaction/comment/post` | Body: com.xingin.entities.n | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/post` | Body: com.xingin.entities.r | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/post` | Body: com.xingin.entities.p | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/post` | Body: com.xingin.entities.a0 | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/prepost` | Body: com.xingin.entities.u | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/prepost` | Body: com.xingin.entities.o | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/prepost` | Body: com.xingin.entities.t | CommentService |
| `POST` | `/api/sns/v1/interaction/comment/public_status/cancel` | Query: comment_id | ProfileHistoryCommentService |
| `POST` | `/api/sns/v1/interaction/comment/public_status/set` | Query: comment_id | ProfileHistoryCommentService |
| `POST` | `/api/sns/v1/interaction/comment/user/confirm_guide` | Body: r09.j | CommentService |
| `POST` | `/api/sns/v1/live/fans_group/join` | Field: room_id, host_user_id | AlphaFansLiveMallService |
| `POST` | `/api/sns/v1/live/fans_group/sign_in` | Field: user_id, room_id, host_id | AlphaGoodsFansLiveMallService |
| `POST` | `/api/sns/v1/live/fans_group/update_name` | Query: new_name | AlphaFansService |
| `POST` | `/api/sns/v1/live/fans_group/{room_id}/join` | Path: room_id; Field: host_user_id, group_type | AlphaFansService |
| `POST` | `/api/sns/v1/live/feed/waterfall` | Field: room_id, page_source, pos, tag_source, new_flag, extra_info, common_info; Header: x-ratelimit-meta | AlphaConfigLiveRoomService |
| `POST` | `/api/sns/v1/live/trailer/cancel_subscribe` | Query: trailer_id | LiveRepository |
| `POST` | `/api/sns/v1/live/trailer/cancel_subscribe` | Query: trailer_id | LiveServices4LiveGo |
| `POST` | `/api/sns/v1/live/trailer/cancel_subscribe` | Query: trailer_id | SplashAdsLiveServicesLiveGo |
| `POST` | `/api/sns/v1/live/trailer/cancel_subscribe` | Query: trailer_id | LiveTrailerRepository |
| `POST` | `/api/sns/v1/live/trailer/cancel_subscribe` | Query: trailer_id | IMService |
| `POST` | `/api/sns/v1/live/trailer/subscribe` | Query: trailer_id, source_type | LiveRepository |
| `POST` | `/api/sns/v1/live/trailer/subscribe` | Query: trailer_id, source_type | LiveServices4LiveGo |
| `POST` | `/api/sns/v1/live/trailer/subscribe` | Query: trailer_id, source_type | SplashAdsLiveServicesLiveGo |
| `POST` | `/api/sns/v1/live/trailer/subscribe` | Query: trailer_id, source_type | LiveTrailerRepository |
| `POST` | `/api/sns/v1/live/trailer/subscribe` | Query: trailer_id, source_type | IMService |
| `POST` | `/api/sns/v1/local/city/get_top_bar_entry` | Field: geo, city_name | LocalFeedService |
| `POST` | `/api/sns/v1/local/poi/citytabs` | Field: longitude, latitude | PoiService |
| `POST` | `/api/sns/v1/local/poi/collect` | Field: poi_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | UnderBarPoiPresenter |
| `POST` | `/api/sns/v1/local/poi/collect` | Field: poi_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AdsUnderBarPoiPresenter |
| `POST` | `/api/sns/v1/local/poi/collect` | Field: poi_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | PoiCardDslSpiPresenter |
| `POST` | `/api/sns/v1/local/poi/collect` | Field: poi_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | CollectService |
| `POST` | `/api/sns/v1/local/poi/marklocationlist` | Body: com.xingin.capa.network.model.poi.PoiMarkLocationBody | PoiService |
| `POST` | `/api/sns/v1/local/poi/search/tab` | Field: query, search_id, page, page_size, query_filters, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, list_type, geo, query_extra | AliothServices |
| `POST` | `/api/sns/v1/local/poi/trigger_ai_intent` | Body: ndd.f | UserIntentGenerationService |
| `POST` | `/api/sns/v1/location/gps` | Body: com.xingin.net.gen.model.Edith2ApiSnsV1LocationGpsPostRequestBody | CapaApi |
| `POST` | `/api/sns/v1/location/residence` |  | CapaApi |
| `POST` | `/api/sns/v1/mappoi/footprints/batch/update` | Body: a9a.p | VisitedServices |
| `POST` | `/api/sns/v1/mappoi/personal/collect/list` | Field: target_user_id, cursor_id, page_size | UserCollectedModel |
| `POST` | `/api/sns/v1/mappoi/upload/map/track/point` | Body: hdb.d | TrackService |
| `POST` | `/api/sns/v1/mappoi/upload/map/track/point` | Body: com.xingin.redmap.service.RedMapTrackUploadService.d | RedMapTrackUploadService |
| `POST` | `/api/sns/v1/media/ai/mainobjectseg/mainobjectseg` | Body: com.xingin.net.gen.model.Edith2ApiSnsV1MediaAiMainobjectsegMainobjectsegPostRequestBody | CapaApi |
| `POST` | `/api/sns/v1/media/ai/photo3d` | Body: com.xingin.capa.network.model.Photo3dRequestBody | CapaAiImageService |
| `POST` | `/api/sns/v1/media/ai/photo3d` | Body: com.xingin.net.gen.model.Edith2ApiSnsV1MediaAiPhoto3dPostRequestBody | CapaApi |
| `POST` | `/api/sns/v1/media/collect_soundtrack` | Field: soundtrack_id | SameParagraphService |
| `POST` | `/api/sns/v1/media/collect_soundtrack` | Field: soundtrack_id | INnsDetailService |
| `POST` | `/api/sns/v1/media/collect_soundtrack` | Field: soundtrack_id | UserCollectedModel |
| `POST` | `/api/sns/v1/media/generate_album` | Body: com.xingin.capa.network.model.BodyAlbumRequestBean | BodyAlbumService |
| `POST` | `/api/sns/v1/media/pre_download_image` | Body: com.xingin.capa.network.model.NotifyMsgRequestBody | CommonService |
| `POST` | `/api/sns/v1/media/template/device_grade` |  | CapaApi |
| `POST` | `/api/sns/v1/media/template/moment` | Body: com.xingin.net.gen.model.Edith2ApiSnsV1MediaTemplateMomentPostRequestBody | CapaApi |
| `POST` | `/api/sns/v1/media/template/publish_reason` | Body: com.xingin.net.gen.model.Edith2ApiSnsV1MediaTemplatePublishReasonPostRequestBody | CapaApi |
| `POST` | `/api/sns/v1/media/template/recommend` | Body: com.xingin.net.gen.model.Edith2ApiSnsV1MediaTemplateRecommendPostRequestBody | CapaApi |
| `POST` | `/api/sns/v1/media/{filter_id}/use_filter` | Path: filter_id; Field: space | MaterialAPIService |
| `POST` | `/api/sns/v1/media/{filter_id}/use_filter` | Path: filter_id; Field: space | FilterServices |
| `POST` | `/api/sns/v1/media/{music_id}/collect` | Path: music_id; Field: category_id | MusicService |
| `POST` | `/api/sns/v1/media/{music_id}/collect` | Path: music_id; Field: category_id | MusicHeaderService |
| `POST` | `/api/sns/v1/media/{music_id}/collect` | Path: music_id; Field: category_id | INnsDetailService |
| `POST` | `/api/sns/v1/media/{music_id}/collect` | Path: music_id; Field: category_id | UserCollectedModel |
| `POST` | `/api/sns/v1/mp/red/apps/{appId}/follow` | Path: appId; Query: sid | IMPFollowService |
| `POST` | `/api/sns/v1/mp/red/authorize` | Query: sid; Body: okhttp3.RequestBody; Header: xy-common-params | IOpenService |
| `POST` | `/api/sns/v1/mp/red/get_mid_link` | Body: okhttp3.RequestBody; Header: xy-common-params | IOpenService |
| `POST` | `/api/sns/v1/mp/red/get_phone` | Query: sid; Body: okhttp3.RequestBody; Header: xy-common-params | IOpenService |
| `POST` | `/api/sns/v1/mp/red/get_setting` | Query: sid; Body: okhttp3.RequestBody; Header: xy-common-params | IOpenService |
| `POST` | `/api/sns/v1/mp/red/get_userinfo` | Query: sid; Body: okhttp3.RequestBody; Header: xy-common-params | IOpenService |
| `POST` | `/api/sns/v1/note/atme/show` | Field: note_id, show_status | CommonNoteService |
| `POST` | `/api/sns/v1/note/atme/show` | Query: note_id, show_status | TaggedMeService |
| `POST` | `/api/sns/v1/note/atme/toggle` | Query: toggle_status | TaggedMeService |
| `POST` | `/api/sns/v1/note/audio` |  | AudioService |
| `POST` | `/api/sns/v1/note/collect` | Field: note_id, board_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | CommonBoardService |
| `POST` | `/api/sns/v1/note/collection/add_note` | Field: collection_id, note_ids | CollectionService |
| `POST` | `/api/sns/v1/note/collection/add_note` | Field: collection_id, note_ids | PortfolioService |
| `POST` | `/api/sns/v1/note/collection/create` | Field: name, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_DESC | CollectionService |
| `POST` | `/api/sns/v1/note/collection/create` | Field: name, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_DESC | PortfolioService |
| `POST` | `/api/sns/v1/note/collection/create_sketch_order_and_pay` | Field: note_id, product_id, com.xingin.entities.BaseTagBean.TYPE_PRICE, sale_price, transaction_id | CollectionService |
| `POST` | `/api/sns/v1/note/collection/delete` | Field: collection_id | CollectionService |
| `POST` | `/api/sns/v1/note/collection/delete` | Field: collection_id | PortfolioService |
| `POST` | `/api/sns/v1/note/collection/remove_note` | Field: collection_id, note_ids | CollectionService |
| `POST` | `/api/sns/v1/note/collection/remove_note` | Field: collection_id, note_ids | PortfolioService |
| `POST` | `/api/sns/v1/note/collection/sorting_note` | Field: collection_id, note_ids | CollectionService |
| `POST` | `/api/sns/v1/note/collection/update` | Field: collection_id, name, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_DESC | CollectionService |
| `POST` | `/api/sns/v1/note/collection/update` | Field: collection_id, name, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_DESC | PortfolioService |
| `POST` | `/api/sns/v1/note/detailfeed/preload` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, data, ext | NoteDetailService |
| `POST` | `/api/sns/v1/note/file/download` | Field: document_id, note_id | DownloadService |
| `POST` | `/api/sns/v1/note/help_after_post/invite` | Query: note_id, invite_user_ids | InviteService |
| `POST` | `/api/sns/v1/note/here` | Query: note_id, here_action_type | LiveShootingService |
| `POST` | `/api/sns/v1/note/here/cancel` | Query: note_id | LiveShootingService |
| `POST` | `/api/sns/v1/note/later/add` | Body: in9.a aVar, kotlin.coroutines.Continuation<? super in9.b> | PodcastListenLaterApiService |
| `POST` | `/api/sns/v1/note/later/add` | Body: ota.b | WatchLaterApiService |
| `POST` | `/api/sns/v1/note/listen_later/move` | Body: in9.h hVar, kotlin.coroutines.Continuation<? super in9.i> | PodcastListenLaterApiService |
| `POST` | `/api/sns/v1/note/listen_later/remove` | Body: in9.j jVar, kotlin.coroutines.Continuation<? super in9.k> | PodcastListenLaterApiService |
| `POST` | `/api/sns/v1/note/live_photo/save` | Field: note_id, is_hdr | NoteDetailService |
| `POST` | `/api/sns/v1/note/longpress` | Body: okhttp3.RequestBody | FeedbackService |
| `POST` | `/api/sns/v1/note/longpress` | Body: okhttp3.RequestBody | NoteDetailService |
| `POST` | `/api/sns/v1/note/metrics_report` | Body: okhttp3.RequestBody | NoteActionService |
| `POST` | `/api/sns/v1/note/metrics_report/sketch_report` | Field: sketch_id, note_id, view_progress_ms | VideoFeedNetService |
| `POST` | `/api/sns/v1/note/move` | Field: notes_id, target_board_id, source_board_id | CommonBoardService |
| `POST` | `/api/sns/v1/note/multi_uncollect` | Field: note_ids | CommonBoardService |
| `POST` | `/api/sns/v1/note/nice` | Field: note_id | NiceVideoService |
| `POST` | `/api/sns/v1/note/notnice` | Field: note_id | NiceVideoService |
| `POST` | `/api/sns/v1/note/out/share/car/entry` | Field: note_id | ShareService |
| `POST` | `/api/sns/v1/note/out/share/car/sync` | Field: note_id, share_time, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, request_id | ShareService |
| `POST` | `/api/sns/v1/note/paid_image/save` | Field: note_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, need_hdr | NoteDetailService |
| `POST` | `/api/sns/v1/note/privacy` | Field: note_id, privacy, user_ids, privacy_json | NoteDetailService |
| `POST` | `/api/sns/v1/note/seed` | Query: note_id | CommonNoteService |
| `POST` | `/api/sns/v1/note/share/bubble_report` | Field: note_id, type, count | NoteDetailService |
| `POST` | `/api/sns/v1/note/submit_video_feedback` | Body: qb9.f | FeedbackService |
| `POST` | `/api/sns/v1/note/uncollect` | Query: notes_id | CommonNoteService |
| `POST` | `/api/sns/v1/note/unseed` | Query: note_id | CommonNoteService |
| `POST` | `/api/sns/v1/note/upload/resource/info` | Field: note_id, res_list, image_list, video_list | CommonService |
| `POST` | `/api/sns/v1/note/video_play_feedback` | Body: com.xingin.entities.notedetail.VideoFeedbackRequestBody | NoteDetailService |
| `POST` | `/api/sns/v1/note/videofeed/exit` | Body: com.xingin.entities.notedetail.o0 | NoteDetailService |
| `POST` | `/api/sns/v1/note/watch_later/remove` | Body: ota.f | WatchLaterApiService |
| `POST` | `/api/sns/v1/note/widget/cancel_interact` | Query: note_id, widget_id, option_id | InteractComponentService |
| `POST` | `/api/sns/v1/note/widget/create_interact` | Body: z93.e | InteractComponentService |
| `POST` | `/api/sns/v1/note/widget/make_interact` | Query: note_id, widget_id, option_id | InteractComponentService |
| `POST` | `/api/sns/v1/onboarding/push` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | LoginServices |
| `POST` | `/api/sns/v1/paddles/event` | Field: event_type, event_data | HeraApiServices |
| `POST` | `/api/sns/v1/paddles/fences` |  | SimpleServices |
| `POST` | `/api/sns/v1/paddles/fetch_lite_config` |  | HeraApiServices |
| `POST` | `/api/sns/v1/paddles/get_context_awareness_tags` |  | SimpleServices |
| `POST` | `/api/sns/v1/paddles/hit_push_holdout` |  | HeraApiServices |
| `POST` | `/api/sns/v1/paddles/jpush-filter` | Body: com.xingin.xhs.push.simple.bean.JPushRefreshRequest | SimpleServices |
| `POST` | `/api/sns/v1/paddles/reddot` |  | HeraApiServices |
| `POST` | `/api/sns/v1/paddles/reddot` |  | SimpleServices |
| `POST` | `/api/sns/v1/questionnaire/report` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, track_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_TASK_ID, option_id, sec_ques_id, sec_ques_opt_titles, sec_ques_text | QuestionnaireService |
| `POST` | `/api/sns/v1/recommend/dislike/record` | Query: target_id, target_type, object_type, object_id, track_id, page_instance, operate_type, extra_info | FeedbackService |
| `POST` | `/api/sns/v1/redhouse/received_notify_msg` | Body: d87.v | RedHouseService |
| `POST` | `/api/sns/v1/search/feedback/common` | Field: type, message, target_id, search_id, business_type, extra_info | SearchFeedbackService |
| `POST` | `/api/sns/v1/search/feedback/common` | Body: iyb.h | SearchAgentPageApi |
| `POST` | `/api/sns/v1/search/notes/recommend_info/feedback` | Body: vf0.n | AliothServices |
| `POST` | `/api/sns/v1/search/onebox/dqa` | Field: type, message, answer_id, search_id | AliothServices |
| `POST` | `/api/sns/v1/shopping/ai_guide/quiz/submit` | Body: zq5.k | ShopAiGuidePageApi |
| `POST` | `/api/sns/v1/surprisebox/coupon_action` | Query: biz_type, biz_id | NoteCouponService |
| `POST` | `/api/sns/v1/surprisebox/feedback` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, type | SurpriseBoxService |
| `POST` | `/api/sns/v1/surprisebox/open` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | SurpriseBoxService |
| `POST` | `/api/sns/v1/surprisebox/submit_action` | Field: rule_id, page_instance, action, biz_params, rn_name, rn_version, requestSource | SurpriseBoxService |
| `POST` | `/api/sns/v1/system/ares/device/violation/query` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | IRiskService |
| `POST` | `/api/sns/v1/system/ares/report/reason` | Field: target_type | ReportService |
| `POST` | `/api/sns/v1/system/ares/submit` | Body: zsb.c | ReportService |
| `POST` | `/api/sns/v1/system_service/config/common` | Field: key, value | GeneralSettingServices |
| `POST` | `/api/sns/v1/system_service/config/common` | Field: key, value | MatrixApi |
| `POST` | `/api/sns/v1/system_service/permission/report` | Field: contact_permission | PermissionModel |
| `POST` | `/api/sns/v1/system_service/screen_notice` | Query: trigger_type | InfraApi |
| `POST` | `/api/sns/v1/system_service/signal_report` | Body: jd6.m | DeviceContextApiService |
| `POST` | `/api/sns/v1/system_service/umi_sonoda` | Field: data | PrivacyTrackerServices |
| `POST` | `/api/sns/v1/system_service/update_track_flag` | Query: flag | GrowthApi |
| `POST` | `/api/sns/v1/tag/batch_goods` | Body: com.xingin.capa.network.model.BatchGetGoodsInfoRequest | CapaPostTagService |
| `POST` | `/api/sns/v1/tag/batch_goods` | Body: com.xingin.net.gen.model.JarvisBatchGetGoodsInfoRequest | CapaApi |
| `POST` | `/api/sns/v1/tag/batch_label` | Body: com.xingin.capa.network.model.BatchGetLabelInfoRequest | CapaPostTagService |
| `POST` | `/api/sns/v1/tag/batch_label` | Body: com.xingin.net.gen.model.JarvisBatchGetLabelInfoRequest | CapaApi |
| `POST` | `/api/sns/v1/tag/image/template/collect` | Field: user_id, template_ids, data | TemplateService |
| `POST` | `/api/sns/v1/tag/image/template/uncollect` | Field: user_id, template_ids | TemplateService |
| `POST` | `/api/sns/v1/tag/template/collect` | Field: user_id, template_ids, data | TemplateService |
| `POST` | `/api/sns/v1/tag/template/uncollect` | Field: user_id, template_ids | TemplateService |
| `POST` | `/api/sns/v1/topic/follow` | Query: topic_id, topic_name, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AliothServices |
| `POST` | `/api/sns/v1/user/activate` | Field: idfa, idfv, android_id, channel, pasteboard, category, oaid, android_version, mac, gaid, attribution_id, imei_encrypted, install_time, install_first_open, open_url, after_register, last_login_user_id, extra_data, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, did_cur_value, did_last_value, did_cur_source, client_public_key_base64 | ILoginService |
| `POST` | `/api/sns/v1/user/activate` | Field: idfa, idfv, android_id, channel, pasteboard, category, oaid, android_version, mac, gaid, attribution_id, imei_encrypted, install_time, install_first_open, open_url, after_register, last_login_user_id, extra_data | GrowthApi |
| `POST` | `/api/sns/v1/user/agegate/get_page` |  | LoginServices |
| `POST` | `/api/sns/v1/user/agegate/validate` | Field: birthday | LoginServices |
| `POST` | `/api/sns/v1/user/data/sync` | Field: biz_id, type | CommonBoardService |
| `POST` | `/api/sns/v1/user/data/sync` | Query: type | MatrixApi |
| `POST` | `/api/sns/v1/user/follow` | Field: userids, refer_note_id, parent_source, scene, sub_scene | CommonUserService |
| `POST` | `/api/sns/v1/user/follow` | Field: userids, refer_note_id, parent_source, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, scene, sub_scene | CommonUserService |
| `POST` | `/api/sns/v1/user/follow` | Field: room_id, userids, live_source, scene, sub_scene, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | CommonUserService |
| `POST` | `/api/sns/v1/user/interact/callback` | Field: flag | ProfileCnyService |
| `POST` | `/api/sns/v1/user/interact/info` | Field: target_user_id, biz_type | ProfileCnyService |
| `POST` | `/api/sns/v1/user/interact/received` | Field: cursor, count, interaction_id | ProfileCnyService |
| `POST` | `/api/sns/v1/user/interact/send` | Field: target_user_id, biz_type, interaction_type, reply_interaction_id | ProfileCnyService |
| `POST` | `/api/sns/v1/user/login/aurora` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, idfa, idfv, android_id, channel, gw_auth, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, imei, imei_encrypted, pasteboard, category, oaid, android_version, mac, attribution_id, gaid | GrowthApi |
| `POST` | `/api/sns/v1/user/login/cmcc` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, phone | ILoginService |
| `POST` | `/api/sns/v1/user/login/cucc` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, phone | ILoginService |
| `POST` | `/api/sns/v1/user/login/getui` | Body: com.xingin.net.gen.model.Edith2ApiSnsV1UserLoginGetuiPostRequestBody | ILoginService |
| `POST` | `/api/sns/v1/user/login/getui` | Body: com.xingin.net.gen.model.Edith2ApiSnsV1UserLoginGetuiPostRequestBody | GrowthApi |
| `POST` | `/api/sns/v1/user/login/message` |  | ILoginService |
| `POST` | `/api/sns/v1/user/login/mob_tech` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, op_token, operator, phone_operator, md5, idfa, idfv, android_id, channel, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, phone | AccountApi |
| `POST` | `/api/sns/v1/user/login/mob_tech` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, op_token, operator, phone_operator, md5, idfa, idfv, android_id, channel, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | GrowthApi |
| `POST` | `/api/sns/v1/user/login/oversea/social` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, openid, code, type, last_login, idfa, idfv, android_id, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | ILoginService |
| `POST` | `/api/sns/v1/user/login/oversea/social` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, openid, code, type, last_login, idfa, idfv, android_id, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | GrowthApi |
| `POST` | `/api/sns/v1/user/login/risk/status` |  | UserServices |
| `POST` | `/api/sns/v1/user/login/uninstall` | Field: user_id, device_password, carrier_provider, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, gw_auth | ILoginService |
| `POST` | `/api/sns/v1/user/login/validate/device-password` | Field: user_id, device_password | ILoginService |
| `POST` | `/api/sns/v1/user/phone/bind/ctcc` |  | LoginServices |
| `POST` | `/api/sns/v1/user/phone/bind/mob_tech` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, op_token, operator, phone_operator, md5, unbind_other_account | GrowthApi |
| `POST` | `/api/sns/v1/user/privacy/auto_translate/info` |  | GeneralSettingServices |
| `POST` | `/api/sns/v1/user/privacy/auto_translate/set` | Field: flag | GeneralSettingServices |
| `POST` | `/api/sns/v1/user/privacy/daily/setting` | Query: userId, permissionType, action, value | DailyService |
| `POST` | `/api/sns/v1/user/privacy/lang_setting` | Field: timestamp | GeneralSettingServices |
| `POST` | `/api/sns/v1/user/privacy/language_translation/info` |  | I18NV2SettingService |
| `POST` | `/api/sns/v1/user/privacy/language_translation/set` | Body: pu9.b | I18NV2SettingService |
| `POST` | `/api/sns/v1/user/profile/guide/config` | Field: scene, ext_params | HalfProfileInspirePostService |
| `POST` | `/api/sns/v1/user/profile/guide/report_action` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, action | HalfProfileInspirePostService |
| `POST` | `/api/sns/v1/user/refresh_session` | Field: ruleId | GrowthApi |
| `POST` | `/api/sns/v1/user/remarkname/add` | Field: user_id, remark_name | CommonUserService |
| `POST` | `/api/sns/v1/user/upload_head_image` | Part: upfile\ | CommonServices |
| `POST` | `/api/sns/v1/user/upload_head_image` | Part: upfile\ | CommonServices |
| `POST` | `/api/sns/v1/user/verify/avatar_holder/update` | Field: biz_id, biz_type | UserServices |
| `POST` | `/api/sns/v1/user/verify/national_identity_auth_result` | Query: biz_seq, id_card_auth_data, cert_pwd_data, com.alipay.ams.component.sdk.InternalConfigKeys.ADDRESS_ELEMENT_MODE | WAuthApiService |
| `POST` | `/api/sns/v1/video_template` | Body: com.xingin.capa.feature_model.session.ReportParamModel | NoteService |
| `POST` | `/api/sns/v1/video_template/image_templates` | Field: image_template_id, category_id, page_size, is_position, version, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, activity_source | MaterialAPIService |
| `POST` | `/api/sns/v1/video_template/image_templates` | Field: image_template_id, category_id, page_size, is_position, version | VideoTemplateService |
| `POST` | `/api/sns/v1/video_template/image_templates` | Body: com.xingin.net.gen.model.Edith2ApiSnsV1VideoTemplateImageTemplatesPostRequestBody | CapaApi |
| `POST` | `/api/sns/v1/video_template/photo_albums` | Field: photo_album_id, weight, category_id, page_size, is_position, version, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, recommend_album_id, recommend_fragment_infos | MaterialAPIService |
| `POST` | `/api/sns/v1/video_template/photo_albums` | Field: photo_album_id, weight, category_id, page_size, is_position, version, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, recommend_album_id, recommend_fragment_infos | VideoTemplateService |
| `POST` | `/api/sns/v1/video_template/photo_albums` | Body: com.xingin.net.gen.model.Edith2ApiSnsV1VideoTemplatePhotoAlbumsPostRequestBody | CapaApi |
| `POST` | `/api/sns/v1/video_template/recommend/home_page/image_template` | Field: last_image_template_id, page_size | ImageTemplateService |
| `POST` | `/api/sns/v1/video_template/recommend/home_page/video_template` | Field: last_video_template_id, page_size | VideoTemplateService |
| `POST` | `/api/sns/v1/video_template/recommend/home_page/video_template` | Body: com.xingin.net.gen.model.Edith2ApiSnsV1VideoTemplateRecommendHomePageVideoTemplatePostRequestBody | CapaApi |
| `POST` | `/api/sns/v1/video_template/recommend/image_template` | Body: com.xingin.capa.feature_model.template.image.AiRecommendRequestBody | MaterialAPIService |
| `POST` | `/api/sns/v1/video_template/recommend/image_template` | Body: com.xingin.net.gen.model.Edith2ApiSnsV1VideoTemplateRecommendImageTemplatePostRequestBody | CapaApi |
| `POST` | `/api/sns/v1/video_template/recommend_template_v2` | Body: z53.c | MaterialAPIService |
| `POST` | `/api/sns/v1/video_template/recommend_template_v2` | Body: z53.c | VideoTemplateService |
| `POST` | `/api/sns/v1/video_template/recommend_template_v2` | Body: com.xingin.net.gen.model.Edith2ApiSnsV1VideoTemplateRecommendTemplateV2PostRequestBody | CapaApi |
| `POST` | `/api/sns/v1/video_template/user/resume` | Body: com.xingin.capa.network.model.UserResumeRequestBody | CapaTemplateResourceService |
| `POST` | `/api/sns/v1/video_template/user/resume` | Body: com.xingin.net.gen.model.Edith2ApiSnsV1VideoTemplateUserResumePostRequestBody | CapaApi |
| `POST` | `/api/sns/v1/video_template/user_image_template` | Body: com.xingin.capa.network.model.UserImageTemplateRequestBody | CapaTemplateResourceService |
| `POST` | `/api/sns/v1/video_template/user_image_template` | Body: com.xingin.net.gen.model.Edith2ApiSnsV1VideoTemplateUserImageTemplatePostRequestBody | CapaApi |
| `POST` | `/api/sns/v10/search/history/sync` | Body: jc0.n | AliothServices |
| `POST` | `/api/sns/v11/dqa/history/update` | Body: com.xingin.dots.legacy.network.entities.history.DotsHistoryDeleteRequest dotsHistoryDeleteRequest, kotlin.coroutines.Continuation<? super kotlin.Unit> | DotsApi |
| `POST` | `/api/sns/v11/dqa/history/update` | Body: rxb.n nVar, kotlin.coroutines.Continuation<? super kotlin.Unit> | SearchAgentPageApi |
| `POST` | `/api/sns/v11/dqa/send/ai` | Body: iyb.f; Header: service-tag | SearchAgentPageApi |
| `POST` | `/api/sns/v2/capa/edit/search/music` | Field: keyword, offset, page_size, search_type, viewed_music_ids, extra | MusicService |
| `POST` | `/api/sns/v2/dot/input/card` | Field: select_notes_infos | AgentDotsApi |
| `POST` | `/api/sns/v2/guide/feedback` | Body: ju2.a | CapaGuideFeedBackService |
| `POST` | `/api/sns/v2/guide/feedback` | Body: ns9.y1 | ProfileServices |
| `POST` | `/api/sns/v2/guide/user_banner_feedback` | Field: action, banner_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | NoteGuideService |
| `POST` | `/api/sns/v2/list_profile_vibe_apps` | Body: mda.i | WorksServers |
| `POST` | `/api/sns/v2/media/video_models` | Body: com.xingin.net.gen.model.JarvisCapaGenerateOneKeyStyleRequest | CapaApi |
| `POST` | `/api/sns/v2/message/mute` | Field: msg_id, mute | MsgCenterServices |
| `POST` | `/api/sns/v2/note` | Body: com.xingin.capa.feature_model.session.ReportParamModel | NoteService |
| `POST` | `/api/sns/v2/note/bgm_recommend_musics` | Field: tags, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_FILE_ID, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_TITLE, city, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, filter_name | CommonService |
| `POST` | `/api/sns/v2/note/bgm_recommend_musics` | Field: embedding_datas, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, algo_type, required_beat, extras | MusicService |
| `POST` | `/api/sns/v2/note/bgm_recommend_musics_v2` | Field: request_id, scene, embedding_datas, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, algo_type, required_beat, extras, cursor | MusicService |
| `POST` | `/api/sns/v2/note/bgm_tags` | Field: file_ids, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | CommonService |
| `POST` | `/api/sns/v2/note/browsing_history/clear` | Field: type | GeneralSettingServices |
| `POST` | `/api/sns/v2/note/feedback/audio_play_feedback` | Body: ln9.j | PodcastApiService |
| `POST` | `/api/sns/v2/note/handle_bullet` | Query: note_id, op_type, bullet_screen_id | DanmakuService |
| `POST` | `/api/sns/v2/note/music/report_recommend_music` | Field: music_id_list | MusicService |
| `POST` | `/api/sns/v2/note/recommend_musics_v2` | Field: request_id, scene, file_ids, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, required_beat, extras | MusicService |
| `POST` | `/api/sns/v2/note/recommend_musics_v2` | Field: request_id, scene, file_ids, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, required_beat, extras, cursor | MusicService |
| `POST` | `/api/sns/v2/note/widgets` | Body: com.xingin.entities.notedetail.h hVar, kotlin.coroutines.Continuation<? super gsa.a> | PodcastApiService |
| `POST` | `/api/sns/v2/note/widgets` | Body: com.xingin.entities.notedetail.h | NoteDetailBaseService |
| `POST` | `/api/sns/v2/note/widgets` | Body: com.xingin.entities.notedetail.h | NoteDetailService |
| `POST` | `/api/sns/v2/note/widgets/album/callback` | Query: user_id, note_id, album_id, recommend_score, satisfy_score | NoteDetailService |
| `POST` | `/api/sns/v2/note/widgets/get_test_link` | Query: recordIdListStr, vSellerId, debugType | PreviewService |
| `POST` | `/api/sns/v2/note/widgets/report` | Body: com.xingin.entities.notedetail.k | NoteDetailService |
| `POST` | `/api/sns/v2/questionnaire/exposure` | Body: com.google.gson.l | QuestionnaireSurveyNetworkService |
| `POST` | `/api/sns/v2/questionnaire/exposure` | Body: com.google.gson.l | CommentService |
| `POST` | `/api/sns/v2/questionnaire/exposure` | Body: com.google.gson.l | NoteQuestionNetworkService |
| `POST` | `/api/sns/v2/questionnaire/report` | Body: com.google.gson.l | QuestionnaireSurveyNetworkService |
| `POST` | `/api/sns/v2/questionnaire/report` | Body: r09.t | CommentService |
| `POST` | `/api/sns/v2/questionnaire/report` | Body: com.google.gson.l | NoteQuestionNetworkService |
| `POST` | `/api/sns/v2/recommend/overt/topics` | Body: com.xingin.capa.network.model.topic.TopicsRecommendDisplayRequestBody | TopicService |
| `POST` | `/api/sns/v2/recommend/overt/topics` | Body: com.xingin.net.gen.model.Edith2SuggestOvertTopicRequest | CapaApi |
| `POST` | `/api/sns/v2/recommend/suggest/topics` | Body: com.xingin.capa.network.model.topic.TopicsRecommendPostRequestBody | TopicService |
| `POST` | `/api/sns/v2/recommend/suggest/topics` | Body: com.xingin.net.gen.model.Edith2ApiSnsV2RecommendSuggestTopicsPostRequestBody | CapaApi |
| `POST` | `/api/sns/v2/system_service/device/regist` | Field: userId, tokens, device_plat_type, vivo_strategies, vivo_strategies_v2, code, manufacturer, timestamp, device_info | PushServices |
| `POST` | `/api/sns/v2/urge_v2` | Field: request | NoteDetailService |
| `POST` | `/api/sns/v2/user/account_info/anomalies/confirm` |  | IRiskService |
| `POST` | `/api/sns/v2/user/authority/common/update` | Query: permission_key, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | GeneralSettingServices |
| `POST` | `/api/sns/v2/user/followings/{user_id}/pins` | Path: user_id; Field: scene, sub_scene | CommonUserService |
| `POST` | `/api/sns/v2/user/followings/{user_id}/pins` | Path: user_id | UserServices |
| `POST` | `/api/sns/v2/user/info/function/feedback` | Body: ns9.c0 | FunctionCardServices |
| `POST` | `/api/sns/v2/user/keyword/dislike` | Field: keyword_id, target_id | KeywordImageListServices |
| `POST` | `/api/sns/v2/user/keyword/like` | Field: keyword_id, target_id | KeywordImageListServices |
| `POST` | `/api/sns/v2/user/widget/update` | Body: com.xingin.account.entities.n | WidgetEditService |
| `POST` | `/api/sns/v3/message/share` | Field: receiver_id, shared_message_ids, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | PetChatApi |
| `POST` | `/api/sns/v3/page/topic` | Body: jw9.d | TopicService |
| `POST` | `/api/sns/v3/pois` | Field: geo_info, page, page_size, lite | PoiService |
| `POST` | `/api/sns/v3/pois/search` | Field: keyword, geo_info, page, page_size | PoiService |
| `POST` | `/api/sns/v4/live/goods` | Field: room_id, offset, size, need_new_coupon | AlphaGoodsLiveMallService |
| `POST` | `/api/sns/v4/note/comment` | Field: note_id, content, comment_id, at_users, hash_tags, is_note_first_comment, is_sink, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, scene, hash_tag_list, sign_ai_privacy, page_session_id, widget_id, widget_type, widget_option_id, copy_content, edit_time, voice_to_text | CommentService |
| `POST` | `/api/sns/v4/note/comment` | Body: com.xingin.entities.s | CommentService |
| `POST` | `/api/sns/v4/note/comment` | Field: note_id, content, comment_id, at_users, hash_tags, is_note_first_comment, is_sink | CommentApi |
| `POST` | `/api/sns/v4/tag/login_recommend` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, step, gender, age, generation, imei_encrypted, oaid | LoginServices |
| `POST` | `/api/sns/v4/user/login/cmcc` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, idfa, idfv, android_id, channel, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | ILoginService |
| `POST` | `/api/sns/v4/user/login/cmcc` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, idfa, idfv, android_id, channel, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | GrowthApi |
| `POST` | `/api/sns/v4/user/login/code` | Field: mobile_token, zone, phone, idfa, idfv, android_id, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | ILoginService |
| `POST` | `/api/sns/v4/user/login/code` | Field: mobile_token, zone, phone | ILoginService |
| `POST` | `/api/sns/v4/user/login/code` | Field: mobile_token, zone, phone, idfa, idfv, android_id, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | GrowthApi |
| `POST` | `/api/sns/v4/user/login/cucc` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, idfa, idfv, android_id, channel, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | ILoginService |
| `POST` | `/api/sns/v4/user/login/cucc` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, idfa, idfv, android_id, channel, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | GrowthApi |
| `POST` | `/api/sns/v4/user/login/device_password` | Field: user_id, device_password | ILoginService |
| `POST` | `/api/sns/v4/user/login/device_password` | Field: user_id, device_password, idfa, idfv, android_id, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | GrowthApi |
| `POST` | `/api/sns/v4/user/login/password` | Field: password, zone, phone, idfa, idfv, android_id, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | ILoginService |
| `POST` | `/api/sns/v4/user/login/password` | Field: password, zone, phone | ILoginService |
| `POST` | `/api/sns/v4/user/login/password` | Field: password, zone, phone, idfa, idfv, android_id, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | GrowthApi |
| `POST` | `/api/sns/v4/user/login/social` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, nickname, type, idfa, idfv, android_id, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | GrowthApi |
| `POST` | `/api/sns/v4/user/register` | Field: mobile_token, zone, phone, idfa, idfv, android_id, channel, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | ILoginService |
| `POST` | `/api/sns/v4/user/register` | Field: mobile_token, zone, phone | ILoginService |
| `POST` | `/api/sns/v4/user/register` | Field: mobile_token, zone, phone, idfa, idfv, android_id, channel, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | GrowthApi |
| `POST` | `/api/sns/v5/message/message_unread` | Field: type | MsgServices |
| `POST` | `/api/sns/v5/recommend/block` | Body: pb7.i | CommonUserService |
| `POST` | `/api/sns/v5/user/login/ctcc` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, idfa, idfv, android_id, gw_auth, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, phone | AccountApi |
| `POST` | `/api/sns/v5/user/login/ctcc` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, idfa, idfv, android_id, gw_auth, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, phone, client_public_key_base64 | ILoginService |
| `POST` | `/api/sns/v5/user/login/ctcc` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, idfa, idfv, android_id, gw_auth, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | GrowthApi |
| `POST` | `/api/sns/v5/user/login/social` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, openid, code, type, last_login, idfa, idfv, android_id, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | ILoginService |
| `POST` | `/api/sns/v5/user/login/social` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, openid, code, type, last_login, idfa, idfv, android_id, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | GrowthApi |
| `POST` | `/api/sns/v6/message/detect/switch` | Body: vn4.o4 | MsgServices |
| `POST` | `/api/sns/v6/message/mute` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS, target_id, notify_type | CommonNoteService |
| `POST` | `/api/sns/v6/message/mute` | Field: type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS, target_id | CommonNoteService |
| `POST` | `/api/sns/v6/message/mute_stranger` | Query: mute | MsgServices |
| `POST` | `/api/sns/v6/message/push/expose` | Field: buzTag, msgId, category | MsgServices |
| `POST` | `/api/sns/v6/message/sticky_top` | Body: zn4.f | MsgServices |
| `POST` | `api/sns/capa/cny/config` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, template_id | CnyConfigService |
| `POST` | `api/sns/capa/postgw/note/delete` | Body: com.xingin.entities.n1 | NoteServices |
| `POST` | `api/sns/capa/postgw/permission/validate` | Field: note_id, function_type | EditOperateService |
| `POST` | `api/sns/capa/postgw/permission/validate` | Field: note_id, function_type | ShareOperateService |
| `POST` | `api/sns/capa/servicegw/component_strong_guide` | Body: com.xingin.capa.network.model.secondhandgoods.StrongGuideRequestBody | GlobalPostNoteComponentRepo |
| `POST` | `api/sns/capa/servicegw/component_strong_guide` | Body: com.xingin.capa.network.model.secondhandgoods.StrongGuideRequestBody | PostNoteComponentRepo |
| `POST` | `api/sns/capa/servicegw/getpoilist` | Field: latitude, longitude, page, size, type | PoiService |
| `POST` | `api/sns/capa/servicegw/getpoilist` | Field: keyword, latitude, longitude, page, size, type | PoiService |
| `POST` | `api/sns/capa/servicegw/getpoilist` | Field: keyword, latitude, longitude, page, size, type | PoiService |
| `POST` | `api/sns/capa/servicegw/v2/search/topics` | Field: keyword, topic_round_start_time, content | TopicService |
| `POST` | `api/sns/inspiration/simple_text2img` | Body: wf0.f | SimpleText2ImgService |
| `POST` | `api/sns/red/live/app/activity/v1/liverank/popularity_rank` | Field: room_id, time_flag, subtract | AlphaRankApiService |
| `POST` | `api/sns/red/live/app/activity/v1/world/cup26/guide/next_match/book` | Body: zu0.a | AlphaNextMatchGuideApi |
| `POST` | `api/sns/red/live/app/activity/v1/world/cup26/guide/next_match/book` | Body: zu0.a | AlphaNextMatchGuideApi |
| `POST` | `api/sns/red/live/app/base/v1/cover/update` | Field: host_id, room_id, cover_url, room_title, file_info, last_cover_id, cover_update_reason_type | AlphaCoverTitleInfoService |
| `POST` | `api/sns/red/live/app/base/v1/report_received_msg` | Body: uy0.f | LiveImReportService |
| `POST` | `api/sns/red/live/app/comment/v1/hit_keywords` | Field: room_id, matched_keywords | AlphaStoreService |
| `POST` | `api/sns/red/live/app/comment/v1/send` | Field: room_id, comment, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pre_source, view_session_id, role, nickname, avatar | AlphaApiService |
| `POST` | `api/sns/red/live/app/family/v1/expression/query` | Field: host_id | AlphaInputFamilyEmojiApi |
| `POST` | `api/sns/red/live/app/fansgroup/v1/switch` | Query: room_id, host_id, group_type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AlphaFansGroupApiServiceV2 |
| `POST` | `api/sns/red/live/app/feed/v1/replace_live_card` | Query: scene, live_list | LiveStatusService |
| `POST` | `api/sns/red/live/app/gift/v1/batch_send_gift` | Body: e91.d | AlphaGiftService |
| `POST` | `api/sns/red/live/app/gift/v1/batch_send_gift` | Body: e91.d | AlphaGiftService |
| `POST` | `api/sns/red/live/app/gift/v1/batch_send_gift_finish` | Body: e91.c | AlphaGiftService |
| `POST` | `api/sns/red/live/app/gift/v1/give/gift` | Body: e91.g; Header: x-ratelimit-meta | AlphaGiftService |
| `POST` | `api/sns/red/live/app/gift/v1/give/gift` | Body: e91.g; Header: x-ratelimit-meta | AlphaGiftService |
| `POST` | `api/sns/red/live/app/gift/v1/give/gift/finish` | Body: e91.e; Header: x-ratelimit-meta | AlphaGiftService |
| `POST` | `api/sns/red/live/app/interaction/after_combo_praise` | Field: room_id, praise_count, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pre_source, view_session_id | AlphaApiService |
| `POST` | `api/sns/red/live/app/line/v1/config_panel/linking_host/update` | Field: app_id, room_id, layout_type, linkmic_switch, linkmic_invited_scope, emphasize | AlphaLinkLiveGoService |
| `POST` | `api/sns/red/live/app/line/v1/config_panel/linking_viewer/update` | Field: room_id, layout_type, linkmic_switch, viewer_apply_restrict_type, viewer_apply_coins, viewer_enable_send_gift, viewer_enable_incr_rank, viewer_paid_apply_duration_sec, viewer_paid_apply_coins | AlphaLinkLiveGoService |
| `POST` | `api/sns/red/live/app/line/v1/config_panel/talk_space/update` | Field: room_id, viewer_apply_free_approval_switch, viewer_enable_send_gift, viewer_apply_restrict_type, viewer_apply_coins, viewer_enable_incr_rank, viewer_paid_apply_duration_sec, viewer_paid_apply_coins | AlphaLinkLiveGoService |
| `POST` | `api/sns/red/live/app/line/v1/mute_other_speaker` | Field: app_id, room_id, mute, target_user_id | AlphaLinkService |
| `POST` | `api/sns/red/live/app/line/v1/search_invite_host_list` | Field: app_id, room_id, query | AlphaLinkLiveGoService |
| `POST` | `api/sns/red/live/app/paid_live/preview_report` | Field: room_id | AlphaConfigEdithLiveRoomService |
| `POST` | `api/sns/red/live/app/paid_live/preview_report` | Field: room_id | LiveRoomStatusService4LiveGo |
| `POST` | `api/sns/red/live/app/pk/v2/config_panel/update` | Field: app_id, room_id, pk_switch, pk_invited_scope | AlphaLinkLiveGoService |
| `POST` | `api/sns/red/live/app/popular/send/gift` | Body: q81.h | AlphaGiftLiveGoService |
| `POST` | `api/sns/red/live/app/red_packet/v4/join` | Body: lo1.a | LiveRedPacketApiService |
| `POST` | `api/sns/red/live/app/red_packet/v4/join` | Body: lo1.a; Header: x-ratelimit-meta | LiveRedPacketApiService |
| `POST` | `api/sns/red/live/app/redpacket/v1/create` | Field: room_id, biz_type, grab_condition, waiting_seconds, total_coins, split_nums, split_strategy | RedPacketNewApiService |
| `POST` | `api/sns/red/live/app/redpacket/v1/grap/report` | Field: red_packet_id, room_id, biz_type | RedPacketNewApiService |
| `POST` | `api/sns/red/live/app/redpacket/v1/join` | Field: red_packet_id | RedPacketNewApiService |
| `POST` | `api/sns/red/live/app/room/live_box/config/update` | Field: box_type, button_switch | AlphaTeleprompterService |
| `POST` | `api/sns/red/live/app/room/live_box/message/report` | Field: box_type, action, live_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | AlphaTeleprompterService |
| `POST` | `api/sns/red/live/app/v1/center/room/before/start` | Field: room_id, app_id | LiveCoreApiLiveRoomService |
| `POST` | `api/sns/red/live/app/v1/center/room/join/host` | Field: app_id, host_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pre_source, view_session_id | LiveCoreApiLiveRoomService |
| `POST` | `api/sns/red/live/app/v1/center/room/join/room` | Field: app_id, room_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pre_source, view_session_id; Header: x-ratelimit-meta | LiveCoreApiLiveRoomService |
| `POST` | `api/sns/red/live/app/v1/center/room/lock/release` | Field: room_id, app_id | LiveCoreApiLiveRoomService |
| `POST` | `api/sns/red/live/app/v1/center/room/pre` | Field: app_id, biz_id | LiveCoreApiLiveRoomService |
| `POST` | `api/sns/red/live/app/v1/center/room/recovery` | Field: app_id, room_id, distribute, style, obs, content_type, push_type, on_push_info, join_limit | LiveCoreApiLiveRoomService |
| `POST` | `api/sns/red/live/app/v1/center/room/report_push_info` | Field: app_id, biz_id, host_id, room_id, push_result | LiveCoreApiLiveGoService |
| `POST` | `api/sns/red/live/app/v1/center/room/start` | Field: app_id, room_id, distribute, style, obs, content_type, push_type, on_push_info, join_limit | LiveCoreApiLiveRoomService |
| `POST` | `api/sns/red/live/app/v1/center/room/stop` | Field: app_id, room_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS, reason | LiveCoreApiLiveRoomService |
| `POST` | `api/sns/red/live/app/v1/center/room/stop_info` | Field: room_id | AlphaApiService |
| `POST` | `api/sns/red/live/app/v1/center/room/stop_info` | Field: room_id | AlphaHostEndApiService4LiveGoV2 |
| `POST` | `api/sns/red/live/app/v1/course/bind_lesson_room` | Field: room_id, lesson_id | AlphaConfigEdithService |
| `POST` | `api/sns/red/live/app/v1/course/report_bullet_screen_action` | Field: room_id, course_id, action_type | AlphaLiveClassService |
| `POST` | `api/sns/red/live/app/v1/ecology/backdrop/replace` | Field: old_id, new_md5, new_file_id, type, file_info | AlphaGreenScreenLiveGoService |
| `POST` | `api/sns/red/live/app/v1/ecology/backdrop/upload` | Field: file_id, md5, type, file_info | AlphaGreenScreenLiveGoService |
| `POST` | `api/sns/red/live/app/v1/ecology/cover/update` | Field: host_id, room_id, cover_url, room_title, file_info | AlphaConfigEdithLiveGoService |
| `POST` | `api/sns/red/live/app/v1/ecology/gift/send` | Body: q81.h | AlphaGiftMultiLiveService |
| `POST` | `api/sns/red/live/app/v1/ecology/group/push` | Field: room_id, group_id | AlphaGroupLiveGoService |
| `POST` | `api/sns/red/live/app/v1/ecology/inform_card/create` | Field: host_id, room_id, com.xingin.capa.feature_model.interactive.model.InteractiveTabModel.TEMPLATE, content, related_type, related_id | AlphaInfoCardLiveGoService |
| `POST` | `api/sns/red/live/app/v1/ecology/inform_card/delete` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, host_id, room_id | AlphaInfoCardLiveGoService |
| `POST` | `api/sns/red/live/app/v1/ecology/inform_card/manage` | Field: room_id, active_ids, inactive_ids | AlphaInfoCardLiveGoService |
| `POST` | `api/sns/red/live/app/v1/ecology/inform_card/modify` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, host_id, room_id, com.xingin.capa.feature_model.interactive.model.InteractiveTabModel.TEMPLATE, content, related_type, related_id | AlphaInfoCardLiveGoService |
| `POST` | `api/sns/red/live/app/v1/ecology/multi/user/sync` | Body: e51.a | AlphaUserLiveGoService |
| `POST` | `api/sns/red/live/app/v1/ecology/operate_group/join` | Field: batch_id | AlphaGroupLiveGoService |
| `POST` | `api/sns/red/live/app/v1/ecology/operate_group/join` | Field: batch_id | AlphaHostEndApiService4LiveGo |
| `POST` | `api/sns/red/live/app/v1/ecology/send_comment_message` | Field: user_id, room_id, type, sub_type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_DESC | AlphaSendCommentLiveGoService |
| `POST` | `api/sns/red/live/app/v1/ecology/top_msg/change_msg` | Field: room_id, msg, scope | AlphaSettingLiveGoService |
| `POST` | `api/sns/red/live/app/v1/ecology/top_msg/switch` | Field: room_id, enable | AlphaSettingLiveGoService |
| `POST` | `api/sns/red/live/app/v1/fans_group/sign_in` | Field: user_id, room_id, host_id | AlphaGoodsFansLiveGoService |
| `POST` | `api/sns/red/live/app/v1/line/apply_sort_type/change` | Field: app_id, room_id, apply_sort_type | AlphaLinkEdithLiveGoService |
| `POST` | `api/sns/red/live/app/v1/line/center/pre_on_mic` | Field: app_id, room_id, layout_type, max_user_limit, media_type, sub_layout_type, background | AlphaTalkPreviewService |
| `POST` | `api/sns/red/live/app/v1/line/extend_duration` | Field: app_id, room_id, target_user_id, duration_sec | AlphaLinkLiveGoService |
| `POST` | `api/sns/red/live/app/v1/line/linkmic/seek/cancel` | Field: app_id, room_id | AlphaLinkEdithLiveGoService |
| `POST` | `api/sns/red/live/app/v1/line/linkmic/seek/create` | Field: app_id, room_id, type, sub_biz_type, session_id | AlphaLinkEdithLiveGoService |
| `POST` | `api/sns/red/live/app/v1/line/mic_relations` | Field: app_id, room_id, user_ids, linkmic_id, sequence | AlphaCommonLinkLiveGoService |
| `POST` | `api/sns/red/live/app/v1/line/mic_relations` | Field: app_id, room_id, user_ids, linkmic_id, sequence | AlphaLinkService |
| `POST` | `api/sns/red/live/app/v1/line/pk/settle` | Field: app_id, room_id | AlphaEmceePkApiService4LiveGo |
| `POST` | `api/sns/red/live/app/v1/line/push_sdk_type_switch` | Field: room_id, push_sdk_type, app_id | AlphaLinkEdithLiveGoService |
| `POST` | `api/sns/red/live/app/v1/line/switch_emphasize_user` | Field: app_id, room_id, emphasize_user_id, emphasize, type, operate_type | AlphaCommonLinkLiveGoService |
| `POST` | `api/sns/red/live/app/v1/livegoods/choice_goods/batch_delete` | Query: host_id; Field: choice_goods_id, choice_goods_detail_ids | AlphaGoodsProductService |
| `POST` | `api/sns/red/live/app/v1/livegoods/choice_goods/bind_notes` | Body: wx1.a | AlphaGoodsProductService |
| `POST` | `api/sns/red/live/app/v1/livegoods/choice_goods/category/batch/add/item` | Field: host_id, category_id, contract_ids | AlphaGoodsProductService |
| `POST` | `api/sns/red/live/app/v1/livegoods/choice_goods/category/create` | Field: host_id, com.xingin.capa.template_show.api.videotemplate.entity.VideoTemplateModel.CATEGORY_NAME | AlphaGoodsProductService |
| `POST` | `api/sns/red/live/app/v1/livegoods/choice_goods/category/delete` | Query: host_id; Field: category_id | AlphaGoodsProductService |
| `POST` | `api/sns/red/live/app/v1/livegoods/choice_goods/category/edit` | Field: host_id, com.xingin.capa.template_show.api.videotemplate.entity.VideoTemplateModel.CATEGORY_NAME, category_id | AlphaGoodsProductService |
| `POST` | `api/sns/red/live/app/v1/livegoods/choice_goods/category/remove/item` | Query: host_id; Field: category_id, contract_ids | AlphaGoodsProductService |
| `POST` | `api/sns/red/live/app/v1/livegoods/choice_goods/category/single/add/item` | Query: host_id; Field: contract_id, category_ids | AlphaGoodsProductService |
| `POST` | `api/sns/red/live/app/v1/livegoods/choice_goods/edit_recommend` | Body: wx1.p | AlphaGoodsProductService |
| `POST` | `api/sns/red/live/app/v1/livegoods/choice_goods/match/bind_note` | Body: wx1.b | AlphaCollocationService |
| `POST` | `api/sns/red/live/app/v1/livegoods/choice_goods/match/create` | Body: wx1.e | AlphaCollocationService |
| `POST` | `api/sns/red/live/app/v1/livegoods/choice_goods/match/delete` | Field: user_id, match_id | AlphaCollocationService |
| `POST` | `api/sns/red/live/app/v1/livegoods/choice_goods/match/edit` | Body: wx1.e | AlphaCollocationService |
| `POST` | `api/sns/red/live/app/v1/livegoods/choice_goods/top` | Body: wx1.q | AlphaGoodsProductService |
| `POST` | `api/sns/red/live/app/v1/livegoods/choice_goods/update_switch` | Field: host_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS, operator_id, switch_type, reason | AlphaGoodsProductService |
| `POST` | `api/sns/red/live/app/v1/mall/contract/extra/subtitle` | Body: pz0.e2 | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/drop_goods` | Body: com.xingin.alpha.common.store.goods.bean.DropGoodsBody | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/flash_buy/create` | Body: au1.c | AlphaFlashBuyLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/go/buy` | Field: room_id | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/goods/add_cart` | Query: contract_id, item_id, added_price, biz_id, source_type, scene; Header: x-ratelimit-meta | AlphaCollocationLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/goods/add_cart` | Query: room_id, contract_id, item_id, added_price, pass_through_param; Header: x-ratelimit-meta | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/goods/make_top_goods` | Field: room_id, operate_type, contract_id | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/goods_explain/end_explain` | Field: room_id, contract_id | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/goods_explain/make_request_explain_goods_switch` | Field: room_id, request_explain_goods_switch | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/goods_explain/request_explain_goods` | Field: room_id, contract_id | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/goods_explain/start_explain` | Field: operate_source, room_id, contract_id | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/marketing/claim` | Query: room_id, receive_id, receive_type, room_source; Header: x-ratelimit-meta | AlphaPromoteLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/marketing/claimable_info` | Query: room_source; Body: st1.n | AlphaPromoteLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/marketing/join_room_info` | Query: room_source; Body: st1.o | AlphaPromoteLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/plan/goods/update` | Body: nx1.m0 | AlphaPlanLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/plan/link` | Field: plan_id, room_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/plan/pool/goods/batch_delete` | Body: nx1.z | AlphaPlanLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/plan/pool/goods/sort` | Body: nx1.l0 | AlphaPlanLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/pool_goods/shelf_all` | Field: room_id | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/prelive/item/operate` | Body: pz0.d1 | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/prelive/plan/link` | Field: host_id, plan_id | AlphaPlanLiveMallService |
| `POST` | `api/sns/red/live/app/v1/mall/prelive/plan/unlink` | Field: host_id, plan_id | AlphaPlanLiveMallService |
| `POST` | `api/sns/red/live/app/v1/room/bind_gambit` | Field: room_id, host_id, activity_id, gambit_id, content_type, obs | AlphaApiService |
| `POST` | `api/sns/red/live/app/v1/room/biz_relation/bind` | Field: room_id, biz_id, type | AlphaSettingLiveGoService |
| `POST` | `api/sns/red/live/app/v1/room/cancel_pause` | Field: room_id, host_id | AlphaPauseServiceV2 |
| `POST` | `api/sns/red/live/app/v1/room/config/update` | Body: com.google.gson.l | AlphaSettingLiveGoService |
| `POST` | `api/sns/red/live/app/v1/room/get_paid_live_info` | Field: room_id | LiveRoomStatusService4LiveGo |
| `POST` | `api/sns/red/live/app/v1/room/pause` | Field: room_id, host_id | AlphaPauseServiceV2 |
| `POST` | `api/sns/red/live/app/v1/room/report_room_status` | Field: room_id, is_camera_on, is_mic_on, is_screen_record, is_filter_on, goods_no_filter_on, geo | AlphaApiService |
| `POST` | `api/sns/red/live/app/v1/room/report_room_status` | Field: room_id, is_camera_on, is_mic_on, is_screen_record, is_filter_on, goods_no_filter_on | AlphaConfigEdithLiveGoService |
| `POST` | `api/sns/red/live/app/v1/room/share` | Field: room_id, share_to, com.xingin.capa.feature_model.session.EditableVideo2.VIDEO_ENTRANCE_DEEPLINK | AlphaApiService |
| `POST` | `api/sns/red/live/app/v1/room/share` | Field: room_id, share_to, com.xingin.capa.feature_model.session.EditableVideo2.VIDEO_ENTRANCE_DEEPLINK | LiveShareLiveGoService |
| `POST` | `api/sns/red/live/app/v1/room/submit_category` | Field: host_id, room_id, category_ids | AlphaConfigEdithLiveGoService |
| `POST` | `api/sns/red/live/app/v1/room/submit_room_info` | Field: room_id, host_id, content_type, name, cover, multi_cover, multi_cover_list_json, notice, file_info, category_ids, category_custom_names, official_activity_ids, poi_context, activity_id, gambit_id, obs, geo | AlphaApiService |
| `POST` | `api/sns/red/live/app/v1/room/submit_room_info` | Field: room_id, host_id, content_type, name, cover, notice, file_info, category_ids, category_custom_names, official_activity_ids, poi_context, activity_id, gambit_id | AlphaConfigEdithLiveGoService |
| `POST` | `api/sns/red/live/app/v1/room/submit_sticker_info` | Field: hostId, roomId, operateType, stickerInfo, originStickerInfo | AlphaStickerLiveGoService |
| `POST` | `api/sns/red/live/app/v1/room/word_audit` | Field: word, room_id | AlphaConfigEdithLiveGoService |
| `POST` | `api/sns/red/live/app/v1/room_func/update` | Field: room_id, func_type, button_switch | AlphaSettingLiveGoService |
| `POST` | `api/sns/red/live/app/v1/start_check` | Field: room_id, content_type, distribute, join_limit | AlphaConfigEdithLiveRoomService |
| `POST` | `api/sns/red/live/app/v1/trailer/create` | Field: plan_id, host_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_TITLE, start_time, goods | AlphaPlanLiveGoService |
| `POST` | `api/sns/red/live/app/v1/trailer/update` | Field: trailer_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_TITLE, start_time, goods, source_type, note_id_list, display_in_room, coupon_template_id | AlphaLivePreviewLiveGoService |
| `POST` | `api/sns/red/live/app/v1/video/lookback/submit_task` | Field: host_id, room_id | AlphaPlayBackService4LiveGo |
| `POST` | `api/sns/red/live/app/v2/center/room/start` | Field: app_id, room_id, distribute, style, obs, content_type, push_type, on_push_info, join_limit | LiveCoreApiLiveRoomService |
| `POST` | `api/sns/red/live/app/v2/line/adjust_seat` | Field: app_id, user_id, room_id, target_seat, host_id | AlphaLinkLiveGoService |
| `POST` | `api/sns/red/live/app/v2/line/apply` | Field: app_id, room_id, media_type, sub_type, extra_map, type | LiveRtcLiveGoApiService |
| `POST` | `api/sns/red/live/app/v2/line/handle_invite` | Field: app_id, room_id, from_user_id, from_room_id, operate_type, type, sub_biz_type | LiveRtcApiLiveGoServiceV2 |
| `POST` | `api/sns/red/live/app/v2/line/invite` | Field: app_id, room_id, to_user_id, to_room_id, media_type, scene_type, type, sub_biz_type | LiveRtcApiLiveGoServiceV2 |
| `POST` | `api/sns/red/live/app/v2/line/mic_relation` | Field: user_ids, room_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, sequence, app_id | AlphaCommonLinkLiveGoService |
| `POST` | `api/sns/red/live/app/v2/line/mic_relation` | Field: user_ids, room_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, sequence, app_id | AlphaLinkService |
| `POST` | `api/sns/red/live/app/v2/mall/flash_buy/update` | Body: au1.c | AlphaFlashBuyLiveMallService |
| `POST` | `api/sns/red/live/app/v2/mall/plan/pool/goods/batch_add` | Body: ta1.a | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/app/v2/mall/select_goods` | Body: pz0.k1 | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/app/vote/v1/choose` | Field: vote_id, vote_option | LiveVoteApiService |
| `POST` | `api/sns/red/live/app/vote/v1/end` | Field: vote_id | LiveVoteApiService |
| `POST` | `api/sns/red/live/app/vote/v2/create` | Field: room_id, vote_title, auto_end, auto_end_delay_time, options | LiveVoteApiService |
| `POST` | `api/sns/red/live/ecology/new_host_task/flow_prefer/choose` | Query: room_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | AlphaTaskLiveGoService |
| `POST` | `api/sns/red/live/ecology/shopping_red_packet/detail` | Field: red_packet_id, biz_type | AlphaStoreService |
| `POST` | `api/sns/red/live/ecology/shopping_red_packet/detail` | Field: red_packet_id, biz_type | ShoppingRedPacketLiveGoService |
| `POST` | `api/sns/red/live/ecology/shopping_red_packet/receive` | Field: red_packet_id | AlphaStoreService |
| `POST` | `api/sns/red/live/ecology/shopping_red_packet/receive` | Field: red_packet_id | ShoppingRedPacketLiveGoService |
| `POST` | `api/sns/red/live/manager/app/pre_live/v1/pool_goods/sort` | Body: nx1.r0 | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/media/generate_frame_extraction_index` | Body: com.xingin.alpha.render.frame.Room | AlphaFrameExtractorEdithService |
| `POST` | `api/sns/red/live/media/report_frame_extraction` | Body: com.xingin.alpha.render.frame.FrameDetail | AlphaFrameExtractorEdithService |
| `POST` | `api/sns/red/live/trailer/trailer_status_update` | Field: trailer_id, room_id, show_status | AlphaLivePreviewEdithLiveGoService |
| `POST` | `api/sns/red/live/v1/block_user` | Field: user_id, block_user_id, room_id | AlphaUserLiveGoService |
| `POST` | `api/sns/red/live/v1/mall/contract_list/detail` | Field: room_id, contract_ids, atmosphere_source | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/live/v1/room_user/audience_leave` | Field: room_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pre_source, view_session_id; Header: x-ratelimit-meta | AlphaRoomService |
| `POST` | `api/sns/red/live/v1/room_user/viewer_heart` | Field: room_id, heart_duration, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pre_source, view_session_id, host_id; Header: x-ratelimit-meta | AlphaRoomService |
| `POST` | `api/sns/red/livemall/app/contract_list/get_detail` | Field: room_id, contract_ids, com.xingin.capa.feature_model.session.EditableVideo2.VIDEO_ENTRANCE_DEEPLINK, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, atmosphere_source, need_top_area; Header: x-ratelimit-meta | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/livemall/app/dynamic/overview/switch` | Field: host_id, room_id, show_status | AlphaMomentsLiveMallService |
| `POST` | `api/sns/red/livemall/app/goods/explain/comments` | Field: room_id, new_item_id, page, size | AlphaMomentsLiveMallService |
| `POST` | `api/sns/red/livemall/app/goods/shopping_bag/marketing/usable_goods` | Field: room_id, receive_id, receive_type, coupon_template_ids, param_json, offset, size | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/livemall/app/goods_card/v1/join_room_goods_card_info` | Query: room_source; Field: room_id, need_all_goods_card, com.xingin.capa.feature_model.session.EditableVideo2.VIDEO_ENTRANCE_DEEPLINK, need_show_explain_goods_card; Header: x-ratelimit-meta | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/livemall/app/live/touchpoint/report` | Body: sx5.g | UserFlowRetrofitApi |
| `POST` | `api/sns/red/livemall/app/live_classified_goods/v1/list` | Query: room_source; Field: room_id, category_id, page, page_size, com.xingin.capa.feature_model.session.EditableVideo2.VIDEO_ENTRANCE_DEEPLINK; Header: x-ratelimit-meta | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/livemall/app/liveplan/settingconfig/query` | Field: host_id | AlphaApiService |
| `POST` | `api/sns/red/livemall/app/reservation/v1/switch/operate` | Field: host_id, operate_type | AlphaLivePreviewLiveMallService |
| `POST` | `api/sns/red/livemall/app/shopping_bag/v1/top_area_goods` | Field: room_id, category_id, com.xingin.capa.feature_model.session.EditableVideo2.VIDEO_ENTRANCE_DEEPLINK | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/livemall/app/shopping_bag/v1/usable_coupon_top_entrance` | Field: room_id; Header: x-ratelimit-meta | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/livemall/app/shopping_bag/v2/coupon_entrance_info` | Field: room_id; Header: x-ratelimit-meta | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/livemall/app/shopping_bag/v2/coupon_entrance_v2` | Body: bw1.g; Header: x-ratelimit-meta | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/livemall/app/shopping_bag/v2/get_user_usable_coupons_v2` | Field: room_id, page, size, param_json | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/livemall/app/shopping_map/pendant/task/finish` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_TASK_ID, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | StayTaskWidgetApi |
| `POST` | `api/sns/red/livemall/app/shopping_map/pendant/task/info` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_TASK_ID, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | StayTaskWidgetApi |
| `POST` | `api/sns/red/livemall/app/trailer/create` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_TITLE, start_time, goods, source_type, note_id_list, plan_id, host_id, room_id, display_in_room, pre_trailer_id, coupon_template_id | AlphaLivePreviewLiveMallService |
| `POST` | `api/sns/red/livemall/app/trailer/future_trailer` | Field: host_id, source_type | AlphaMomentsLiveMallService |
| `POST` | `api/sns/red/livemall/app/trailer/host_status` | Field: host_id | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/livemall/app/trailer/v1/delete_coupon` | Field: trailer_id | AlphaLivePreviewLiveMallService |
| `POST` | `api/sns/red/livemall/app/trailer/v1/goods/list` | Field: business_id, business_type, page, page_size | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/livemall/app/trailer/v1/pre_trailer_id` |  | AlphaLivePreviewLiveMallService |
| `POST` | `api/sns/red/livemall/app/v1/mall/goods/shopping_bag/list` | Field: room_id, offset, limit, com.xingin.capa.feature_model.session.EditableVideo2.VIDEO_ENTRANCE_DEEPLINK, need_top_area, need_all_goods_list, request_source; Header: x-ratelimit-meta | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/livemall/app/v1/mall/presale/cancel_subscribe` | Body: pz0.y1 | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/livemall/app/v1/mall/presale/subscribe` | Body: pz0.y1 | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/livemall/manager/app/ai_explain/v1/cancel` | Field: room_id | AlphaGoodsLiveMallService |
| `POST` | `api/sns/red/livemall/manager/app/live_goods_category/v1/sort` | Body: com.xingin.alpha.goods.prepare.category.bean.GoodsCategorySortReqData | LiveGoodsCategoryService |
| `POST` | `api/sns/v1/account_recovery/account_info` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, face_token, state_token | RecoverServices |
| `POST` | `api/sns/v1/account_recovery/bind` |  | RecoverServices |
| `POST` | `api/sns/v1/account_recovery/bind` |  | RecoverServices |
| `POST` | `api/sns/v1/account_recovery/bind_phone` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, mobile_token, phone, zone, unbind_other_account, state_token, face_token | RecoverServices |
| `POST` | `api/sns/v1/account_recovery/detail_info` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, used_name, usual_place, phone_brand, birthday, used_phone_number, reason | RecoverServices |
| `POST` | `api/sns/v1/account_recovery/login` |  | AccountService |
| `POST` | `api/sns/v1/account_recovery/notify` | Field: face_token, secure | RecoverServices |
| `POST` | `api/sns/v1/account_recovery/reset_password` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, password | RecoverServices |
| `POST` | `api/sns/v1/account_recovery/verify_phone` | Field: secure, face_token, sim_token, sim_type | RecoverServices |
| `POST` | `api/sns/v1/account_recovery/verify_real_name` | Field: user_id, secure | RecoverServices |
| `POST` | `api/sns/v1/ads/general` | Body: su.j | AdsGeneralRepository |
| `POST` | `api/sns/v1/attribution/appsflyer` | Field: af_result, appsflyer_id | AppsFlyerService |
| `POST` | `api/sns/v1/attribution/self/event` | Field: event_type, referrer_raw, gaid | AttributionService |
| `POST` | `api/sns/v1/board/share_board/invite` | Field: share_board_id, invite_user_ids | MsgServices |
| `POST` | `api/sns/v1/creator/red_app/authorization` | Body: bja.a | IMiniToolService |
| `POST` | `api/sns/v1/creator/red_app/recent_use` | Body: bja.e | IMiniToolService |
| `POST` | `api/sns/v1/homefeed/client_downgrade/assemble` | Body: l6d.d | DemotionModel |
| `POST` | `api/sns/v1/homefeed/client_downgrade/report` | Body: l6d.b | DemotionModel |
| `POST` | `api/sns/v1/homefeed/client_downgrade/sync_fetch_noteids` | Body: l6d.b | DemotionModel |
| `POST` | `api/sns/v1/im/delete_recent_chat` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, is_group, type | ShareOperateService |
| `POST` | `api/sns/v1/interaction/comment/like` | Body: r09.h | CommentService |
| `POST` | `api/sns/v1/interaction/comment/like` | Body: com.xingin.models.services.CommonCommentService.b | CommonCommentService |
| `POST` | `api/sns/v1/interaction/intimacy/atsearch` | Body: cx4.a | CommentService |
| `POST` | `api/sns/v1/live/activity/{room_id}/{activity}/{sub_activity}` | Path: room_id, activity, sub_activity | AlphaConfigService |
| `POST` | `api/sns/v1/live/block_send` | Field: room_id, target | AlphaUserService |
| `POST` | `api/sns/v1/live/cancel_block_send` | Field: room_id, target | AlphaUserService |
| `POST` | `api/sns/v1/live/cancel_make_admin` | Field: room_id, target, role | AlphaUserService |
| `POST` | `api/sns/v1/live/course/cancel_pre_order` | Field: live_order_id | AlphaLiveClassService |
| `POST` | `api/sns/v1/live/course/change` | Field: course_info | AlphaLiveClassService |
| `POST` | `api/sns/v1/live/course/create/new` | Field: course_info | AlphaLiveClassService |
| `POST` | `api/sns/v1/live/course/invitation_code/use` | Field: course_id, code | AlphaLiveClassService |
| `POST` | `api/sns/v1/live/course/report` | Field: type, content, target | AlphaUserService |
| `POST` | `api/sns/v1/live/course/video/play/played_duration` | Field: lesson_id, played_duration, video_index | AlphaPlayBackService |
| `POST` | `api/sns/v1/live/course/{course_id}/buy` | Path: course_id | AlphaLiveClassService |
| `POST` | `api/sns/v1/live/course/{course_id}/pre_buy` | Path: course_id; Field: wallet_order_id | AlphaLiveClassService |
| `POST` | `api/sns/v1/live/draw/{lucky_draw_id}` | Path: lucky_draw_id; Field: space; Header: x-ratelimit-meta | AlphaApiService |
| `POST` | `api/sns/v1/live/draw/{lucky_draw_id}` | Path: lucky_draw_id; Field: space; Header: x-ratelimit-meta | AlphaLotteryLiveGoService |
| `POST` | `api/sns/v1/live/dynamic/clip_show_switch/close` | Field: host_id, clip_id | AlphaMomentsLiveGoService |
| `POST` | `api/sns/v1/live/dynamic/clip_show_switch/close` | Field: host_id, clip_id | AlphaMomentJarvisLiveGoService |
| `POST` | `api/sns/v1/live/dynamic/clip_show_switch/open` | Field: host_id, clip_id | AlphaMomentsLiveGoService |
| `POST` | `api/sns/v1/live/dynamic/clip_show_switch/open` | Field: host_id, clip_id | AlphaMomentJarvisLiveGoService |
| `POST` | `api/sns/v1/live/dynamic/entrance_show_switch/close` | Field: host_id | AlphaMomentsLiveGoService |
| `POST` | `api/sns/v1/live/dynamic/entrance_show_switch/close` | Field: host_id | AlphaMomentJarvisLiveGoService |
| `POST` | `api/sns/v1/live/dynamic/entrance_show_switch/open` | Field: host_id | AlphaMomentsLiveGoService |
| `POST` | `api/sns/v1/live/dynamic/entrance_show_switch/open` | Field: host_id | AlphaMomentJarvisLiveGoService |
| `POST` | `api/sns/v1/live/dynamic/operate_entrance` | Field: host_id, target_status | AlphaMomentsLiveGoService |
| `POST` | `api/sns/v1/live/dynamic/operate_entrance` | Field: host_id, target_status | AlphaMomentJarvisLiveGoService |
| `POST` | `api/sns/v1/live/feed/submit_feed_card_unexposed` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, room_ids | AlphaLiveFeedService |
| `POST` | `api/sns/v1/live/feed/submit_feed_card_unexposed` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, room_ids | LiveFeedService |
| `POST` | `api/sns/v1/live/interaction/send_comment` | Field: room_id, comment, comment_type, comment_extra_param, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pre_source, view_session_id, role, nickname, avatar, at_users, count; Header: x-ratelimit-meta | AlphaApiService |
| `POST` | `api/sns/v1/live/interaction/send_comment` | Field: room_id, comment, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, pre_source, view_session_id, role, nickname, avatar | AlphaChatService |
| `POST` | `api/sns/v1/live/interaction/send_praise` | Body: lw0.c4; Header: x-ratelimit-meta | AlphaApiService |
| `POST` | `api/sns/v1/live/kickout` | Field: room_id, target | AlphaUserService |
| `POST` | `api/sns/v1/live/letter/delete` | Field: letter_id | AlphaQuestionService |
| `POST` | `api/sns/v1/live/letter/end_answer` | Field: letter_id | AlphaQuestionService |
| `POST` | `api/sns/v1/live/letter/post` | Field: letter_info | AlphaQuestionService |
| `POST` | `api/sns/v1/live/letter/set_config` | Field: gift_id, count, conditions, room_id | AlphaQuestionService |
| `POST` | `api/sns/v1/live/letter/start_answer` | Field: letter_id | AlphaQuestionService |
| `POST` | `api/sns/v1/live/letter/switch` | Field: open, room_id | AlphaQuestionService |
| `POST` | `api/sns/v1/live/make_admin` | Field: room_id, target, role | AlphaUserService |
| `POST` | `api/sns/v1/live/make_camera_direction` | Field: room_id, direction_type | AlphaUserService |
| `POST` | `api/sns/v1/live/make_hide_viewers` | Field: room_id, hide_viewers | AlphaConfigService |
| `POST` | `api/sns/v1/live/make_shield_word` | Field: room_id, shield_word | AlphaUserService |
| `POST` | `api/sns/v1/live/pre/set_host_profile` |  | AlphaConfigService |
| `POST` | `api/sns/v1/live/red_packet/{red_packet_id}/receive` | Path: red_packet_id; Field: space | AlphaRedPacketLiveGoService |
| `POST` | `api/sns/v1/live/report/share/in_room/data` | Field: sid, share_uid, room_id, ext, com.xingin.capa.feature_model.session.EditableVideo2.VIDEO_ENTRANCE_DEEPLINK | AlphaReportService |
| `POST` | `api/sns/v1/live/trailer/cancel_subscribe` | Field: trailer_id | AliothServices |
| `POST` | `api/sns/v1/live/trailer/cancel_subscribe` | Field: trailer_id | AlphaApiService |
| `POST` | `api/sns/v1/live/trailer/cancel_subscribe` | Field: trailer_id | AlphaLivePreviewLiveGoService |
| `POST` | `api/sns/v1/live/trailer/cancel_subscribe` | Field: trailer_id | AlphaGoodsLiveGoService |
| `POST` | `api/sns/v1/live/trailer/cancel_subscribe` | Field: trailer_id | AlphaReservationService |
| `POST` | `api/sns/v1/live/trailer/cancel_subscribe` | Field: trailer_id | LiveCoreApiService |
| `POST` | `api/sns/v1/live/trailer/cancel_subscribe` | Field: trailer_id | LiveSubscribeApi |
| `POST` | `api/sns/v1/live/trailer/create` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_TITLE, start_time, goods, source_type, note_id_list, plan_id, parent_user_id | AlphaLivePreviewLiveGoService |
| `POST` | `api/sns/v1/live/trailer/subscribe` | Field: trailer_id, source_type | AliothServices |
| `POST` | `api/sns/v1/live/trailer/subscribe` | Field: trailer_id, source_type; Header: x-ratelimit-meta | AlphaApiService |
| `POST` | `api/sns/v1/live/trailer/subscribe` | Field: trailer_id, source_type | AlphaLivePreviewLiveGoService |
| `POST` | `api/sns/v1/live/trailer/subscribe` | Field: trailer_id, source_type | AlphaMomentJarvisLiveGoService |
| `POST` | `api/sns/v1/live/trailer/subscribe` | Field: trailer_id, source_type | AlphaReservationService |
| `POST` | `api/sns/v1/live/trailer/subscribe` | Field: trailer_id, source_type; Header: x-ratelimit-meta | LiveCoreApiService |
| `POST` | `api/sns/v1/live/trailer/subscribe` | Field: trailer_id, source_type | LiveSubscribeApi |
| `POST` | `api/sns/v1/live/trailer/{trailer_id}/delete` | Path: trailer_id; Field: plan_id | AlphaLivePreviewService |
| `POST` | `api/sns/v1/live/{room_id}/block_send` | Path: room_id; Field: target | AlphaUserService |
| `POST` | `api/sns/v1/live/{room_id}/cancel_block_send` | Path: room_id; Field: target | AlphaUserService |
| `POST` | `api/sns/v1/live/{room_id}/cancel_make_admin` | Path: room_id; Field: target, role | AlphaUserService |
| `POST` | `api/sns/v1/live/{room_id}/follow` | Path: room_id; Field: user_id, scene, sub_scene | CommonUserService |
| `POST` | `api/sns/v1/live/{room_id}/follow` | Path: room_id; Field: user_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, scene, sub_scene | CommonUserService |
| `POST` | `api/sns/v1/live/{room_id}/hit_coupon/done` | Path: room_id; Field: com.xingin.capa.edit.panel.sticker.model.watermarker.WaterMarker.TIME_STICKER_NAME | AlphaConfigService |
| `POST` | `api/sns/v1/live/{room_id}/issue_trailer` | Path: room_id; Field: trailer_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_TITLE, start_time, goods, note_id_list | AlphaLivePreviewService |
| `POST` | `api/sns/v1/live/{room_id}/kickout` | Path: room_id; Field: target | AlphaUserService |
| `POST` | `api/sns/v1/live/{room_id}/make_admin` | Path: room_id; Field: target, role | AlphaUserService |
| `POST` | `api/sns/v1/live/{room_id}/make_camera_direction` | Path: room_id; Field: direction_type | AlphaUserService |
| `POST` | `api/sns/v1/live/{room_id}/make_hide_viewers` | Path: room_id; Field: hide_viewers | AlphaConfigService |
| `POST` | `api/sns/v1/live/{room_id}/make_notice` | Path: room_id; Field: notice | AlphaConfigService |
| `POST` | `api/sns/v1/live/{room_id}/make_shield_word` | Path: room_id; Field: shield_word | AlphaUserService |
| `POST` | `api/sns/v1/live/{room_id}/report` | Path: room_id; Field: type, content, target | AlphaUserService |
| `POST` | `api/sns/v1/live/{room_id}/unfollow` | Path: room_id; Field: user_id, scene, sub_scene | CommonUserService |
| `POST` | `api/sns/v1/live/{room_id}/use_exposure_card` | Path: room_id; Field: source_id | AlphaGiftService |
| `POST` | `api/sns/v1/local/poi/creator/search` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, keyword, latitude, longitude, page, size, type | PoiService |
| `POST` | `api/sns/v1/local/poi/getpoilist` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, keyword, latitude, longitude, page, size, type, note_content, user_latitude, user_longitude | PoiService |
| `POST` | `api/sns/v1/local/poi/getpoilist` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, keyword, latitude, longitude, page, size, type | PoiSearchApi |
| `POST` | `api/sns/v1/local/poi/getpoilist` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, keyword, latitude, longitude, page, size, type, search_context | PoiSearchApi |
| `POST` | `api/sns/v1/local/poi/getpoilist` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, keyword, latitude, longitude, user_latitude, user_longitude, page, size, type, poi_id_list, radius, note_content | PoiSearchApi |
| `POST` | `api/sns/v1/mappoi/re/geo/v1` | Field: latitude, longitude | ILocationService |
| `POST` | `api/sns/v1/media/local_music/delete` | Field: soundtrack_id | MusicService |
| `POST` | `api/sns/v1/media/local_music/upload` | Field: music_file_id, cover_file_id, duration_ms, md5 | MusicService |
| `POST` | `api/sns/v1/message/you/connections/greet/update` | Field: greet_score | MessageServices |
| `POST` | `api/sns/v1/mp/red/check_session` | Query: sid; Body: okhttp3.RequestBody; Header: xy-common-params | IOpenService |
| `POST` | `api/sns/v1/mp/red/login` | Query: sid; Body: okhttp3.RequestBody; Header: xy-common-params | IOpenService |
| `POST` | `api/sns/v1/mp/red/pay` | Query: sid; Body: okhttp3.RequestBody; Header: xy-common-params | IMPPayService |
| `POST` | `api/sns/v1/note/dislike` | Query: oid | CommonNoteService |
| `POST` | `api/sns/v1/note/dislike` | Query: oid | StoreService |
| `POST` | `api/sns/v1/note/dislike` | Query: oid | CosmosNoteLikeService |
| `POST` | `api/sns/v1/note/like` | Query: oid | CommonNoteService |
| `POST` | `api/sns/v1/note/like` | Query: oid | StoreService |
| `POST` | `api/sns/v1/note/like` | Query: oid | CosmosNoteLikeService |
| `POST` | `api/sns/v1/note/top` | Field: note_id, sticky | EditOperateService |
| `POST` | `api/sns/v1/note/top` | Field: note_id, sticky | ShareOperateService |
| `POST` | `api/sns/v1/note/video/upload_bgm` | Field: upload_bgm_list | MusicService |
| `POST` | `api/sns/v1/oauth2/auth_info` |  | IOAuthService |
| `POST` | `api/sns/v1/oauth2/authorize` |  | IOAuthService |
| `POST` | `api/sns/v1/onboarding/interest/report` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | ExploreService |
| `POST` | `api/sns/v1/onboarding/uginfo` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | GrowthService |
| `POST` | `api/sns/v1/paddles/pull_configs` | Field: pull_configs_request | StrategyNetService |
| `POST` | `api/sns/v1/page/collect_tag` | Field: tag_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | TopicService |
| `POST` | `api/sns/v1/page/collect_tag` | Field: tag_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | UserCollectedModel |
| `POST` | `api/sns/v1/pop_ups/report` | Field: selected_button_value, pop_ups_type | DialogModel |
| `POST` | `api/sns/v1/questionnaire/report` |  | NoteDetailService |
| `POST` | `api/sns/v1/questionnaire/report` |  | QuestionnaireService |
| `POST` | `api/sns/v1/recommend/dislike/record` | Field: target_id, target_type, object_type, object_id, track_id, page_instance, extra_info | AliothServices |
| `POST` | `api/sns/v1/recommend/user/mask` | Body: vn4.k5 | MsgServices |
| `POST` | `api/sns/v1/recommend/user/mask` | Body: com.xingin.follow.pymk.bean.RecommendUserRemove | CommonUserService |
| `POST` | `api/sns/v1/recommend/user/mask` | Body: com.xingin.follow.videopage.recommend.bean.RecommendUserRemove | FollowRecommendService |
| `POST` | `api/sns/v1/recommend/user/mask` | Body: com.xingin.matrix.v2.profile.recommendv2.utils.entities.RecommendUserRemove | MatrixUserServices |
| `POST` | `api/sns/v1/recommend/user/mask` | Body: com.xingin.matrix.v2.profile.recommendv2.utils.entities.RecommendUserRemove | UserServices |
| `POST` | `api/sns/v1/search/topics` | Field: keyword, topic_round_start_time, content | TopicService |
| `POST` | `api/sns/v1/share/code` | Field: type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, origin_url, extraInfo | ShareOperateService |
| `POST` | `api/sns/v1/system/ares/config` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID | AlphaCommentReportService |
| `POST` | `api/sns/v1/system/ares/submit` | Body: ep1.h | AlphaCommentReportService |
| `POST` | `api/sns/v1/system_service/device_params_info` | Field: device_info_json, upload_count, did_cur_value, did_cur_source, did_last_value, did_cur_update_time, did_history_list_json | DeviceParamsUploadService |
| `POST` | `api/sns/v1/system_service/p_report` |  | AntiService |
| `POST` | `api/sns/v1/system_service/pre_activate_bind` |  | AccountService |
| `POST` | `api/sns/v1/system_service/report` | Field: target_id, target_type, reason_type, reason_desc, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_IMAGES, target_content, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | ReportService |
| `POST` | `api/sns/v1/system_service/shield_sms_check/check_code` | Field: phone, zone, code | VerificationCodeServices |
| `POST` | `api/sns/v1/system_service/short_url` | Field: origin_url | ShareService |
| `POST` | `api/sns/v1/system_service/update_device` |  | AccountService |
| `POST` | `api/sns/v1/system_service/upload_contacts` |  | LoginServices |
| `POST` | `api/sns/v1/system_service/upload_contacts` | Field: data, page_total, page_index | UserServices |
| `POST` | `api/sns/v1/system_service/upload_weibo_token` | Field: data | UserServices |
| `POST` | `api/sns/v1/system_service/uploadlocation` | Field: latitude, longitude | LocalFeedService |
| `POST` | `api/sns/v1/tag/ads_engage` |  | AccountService |
| `POST` | `api/sns/v1/tag/follow` | Field: oid | TagServices |
| `POST` | `api/sns/v1/topic/batch_customized` | Body: com.xingin.capa.network.model.topic.TopicCreatePostBody | TopicService |
| `POST` | `api/sns/v1/underage/minor_protection_status` |  | RedAgeProtectionApi |
| `POST` | `api/sns/v1/user/block` | Field: user_id | ShareOperateService |
| `POST` | `api/sns/v1/user/face_recognition_approve` | Field: order_id, face_recognition_verified, biz_source, source_photo_id | IIdentityService |
| `POST` | `api/sns/v1/user/info/bind/cmcc` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, unbind_other_account | IBindService |
| `POST` | `api/sns/v1/user/interact/resource` |  | ProfileAnimService |
| `POST` | `api/sns/v1/user/login/account-selected` | Field: state_token, target_user_id | ILoginService |
| `POST` | `api/sns/v1/user/login/account_info/unbind` | Field: type, mobile_token, code, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, openid | AccountService |
| `POST` | `api/sns/v1/user/login/account_info/unbind` | Field: type | IBindService |
| `POST` | `api/sns/v1/user/login/acct_group/exec` | Field: acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, rule_id, target_user_id | AccountService |
| `POST` | `api/sns/v1/user/login/acct_group/exec` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, target_user_id, rule_id, acct_group_id, client_public_key_base64 | ILoginService |
| `POST` | `api/sns/v1/user/login/auxiliary-account/bind` | Field: corp_id, target_id, order_id, state_token | IAuxiliaryAccountService |
| `POST` | `api/sns/v1/user/login/auxiliary-account/create` | Field: mobile_token, zone, phone | ILoginService |
| `POST` | `api/sns/v1/user/login/auxiliary-account/init` | Field: corp_id, order_id, state_token | IAuxiliaryAccountService |
| `POST` | `api/sns/v1/user/login/auxiliary-account/pre-check` |  | IAuxiliaryAccountService |
| `POST` | `api/sns/v1/user/login/check_last` |  | LoginServices |
| `POST` | `api/sns/v1/user/login/confirm` | Field: r_id, state_token, operation_type | AccountService |
| `POST` | `api/sns/v1/user/login/devices/history` |  | IDeviceService |
| `POST` | `api/sns/v1/user/login/devices/remove/history` | Field: device_id, biz_id, template_id | IDeviceService |
| `POST` | `api/sns/v1/user/login/devices/remove/history` | Field: biz_id, template_id | IDeviceService |
| `POST` | `api/sns/v1/user/login/kos/invitation/valid` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, corpId, targetUserId | IAuxiliaryAccountService |
| `POST` | `api/sns/v1/user/login/password/modify` | Field: origin_password, password | SecurityAccountService |
| `POST` | `api/sns/v1/user/login/password/reset` | Field: zone, phone, password, mobile_token | LoginServices |
| `POST` | `api/sns/v1/user/login/password/set` | Query: password | SecurityAccountService |
| `POST` | `api/sns/v1/user/login/real-name` | Field: login_state_token | ILoginService |
| `POST` | `api/sns/v1/user/login/recovery_account` | Field: state_token, face_token, idfa, idfv, android_id, channel, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | AccountApi |
| `POST` | `api/sns/v1/user/login/recovery_account` | Field: state_token, face_token, idfa, idfv, android_id, channel, gaid, oaid, pasteboard, category, android_version, mac, attribution_id, imei_encrypted, ruleId, after_register, acct_group_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | ILoginService |
| `POST` | `api/sns/v1/user/login/recovery_account` | Field: state_token, face_token | ILoginService |
| `POST` | `api/sns/v1/user/login/sid_reason` |  | IDeviceService |
| `POST` | `api/sns/v1/user/login/social-bind-phone` | Field: zone, phone, mobile_token, tmp_social_token, type | IBindService |
| `POST` | `api/sns/v1/user/login/social-bind-phone-quick` | Field: phone_card_type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, gw_auth, tmp_social_token, type | IBindService |
| `POST` | `api/sns/v1/user/login/tmp-token` | Field: tmp_token, target_user_id | ILoginService |
| `POST` | `api/sns/v1/user/phone/bind/appeal/submit` | Query: mobile_token, new_phone, new_zone, register_phone, register_phone_zone, user_credential | SecurityAccountService |
| `POST` | `api/sns/v1/user/phone/bind/cucc` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, unbind_other_account | IBindService |
| `POST` | `api/sns/v1/user/privacy/collection/update` | Field: type, is_public | PrivacyServices |
| `POST` | `api/sns/v1/user/privacy/declare/update` | Field: type, is_public | PrivacyServices |
| `POST` | `api/sns/v1/user/privacy/personalization/update` | Query: type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | PersonalizationService |
| `POST` | `api/sns/v1/user/privacy/visited/update` | Field: type, is_public | PrivacyServices |
| `POST` | `api/sns/v1/user/register_basic_info` | Field: key, value, allow_random | LoginServices |
| `POST` | `api/sns/v1/user/register_basic_info` |  | LoginServices |
| `POST` | `api/sns/v1/user/signoff/cancel` | Field: flow_id | AccountService |
| `POST` | `api/sns/v1/user/status` |  | AccountService |
| `POST` | `api/sns/v1/user/teenager/lock` | Body: eh8.c | KidsModeService |
| `POST` | `api/sns/v1/user/teenager/unlock` | Body: eh8.c | KidsModeService |
| `POST` | `api/sns/v1/user/unblock` | Field: user_id | UserServices |
| `POST` | `api/sns/v1/user/unblock` | Field: user_id | ShareOperateService |
| `POST` | `api/sns/v1/user/upload_head_image` | Part: upfile\ | LoginServices |
| `POST` | `api/sns/v1/user/upload_pm_image` | Query: type; Body: okhttp3.RequestBody | ReportService |
| `POST` | `api/sns/v1/user/verify/verify_carrier` | Field: secure, face_token | RecoverServices |
| `POST` | `api/sns/v1/user/widget/update` | Body: java.util.HashMap<java.lang.String, java.util.ArrayList<com.xingin.account.entities.m>> | WidgetService |
| `POST` | `api/sns/v2/capa/edit/ref_link` | Field: ref_id, ref_type, extra | ShareOperateService |
| `POST` | `api/sns/v2/live/course/buy` | Field: live_order_id | AlphaLiveClassService |
| `POST` | `api/sns/v2/live/interaction/get_simple_interaction` | Field: room_id, start_timestamp, size, user_id, need_comment, host_id | AlphaChatService |
| `POST` | `api/sns/v2/live/interaction/get_simple_interaction` | Field: room_id, start_timestamp, size, user_id, need_comment, host_id | AlphaChatService |
| `POST` | `api/sns/v2/note/business_bind/draft_check` | Field: business_binds | GlobalPostNoteComponentRepo |
| `POST` | `api/sns/v2/note/business_bind/draft_check` | Field: business_binds | PostNoteComponentRepo |
| `POST` | `api/sns/v2/system_service/splash_async_optimization` | Body: zy.d | SplashConfigApiService |
| `POST` | `api/sns/v2/system_service/splash_online_decision` | Body: com.xingin.advert.intersitial.realtime.requestv2.RealTimeRequestParams | SplashConfigApiService |
| `POST` | `api/sns/v2/tag/follow` | Field: data | LoginServices |
| `POST` | `api/sns/v2/tag/follow` |  | LoginServices |
| `POST` | `api/sns/v2/tag/follow` |  | LoginServices |
| `POST` | `api/sns/v2/tag/follow` |  | LoginServices |
| `POST` | `api/sns/v2/user/block_view` | Field: target_user_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | UserServices |
| `POST` | `api/sns/v2/user/follow` |  | LoginServices |
| `POST` | `api/sns/v2/user/followings/dual_rec_user/block` | Body: com.xingin.matrix.v2.profile.recommendv2.utils.entities.RecommendUserRemoveInBiSerial | MatrixUserServices |
| `POST` | `api/sns/v2/user/info` | Body: g51.a | AlphaUserService |
| `POST` | `api/sns/v2/user/info` |  | LoginServices |
| `POST` | `api/sns/v2/user/info` | Field: key, value | UserServices |
| `POST` | `api/sns/v2/user/info` | Field: key, value | UserServices |
| `POST` | `api/sns/v2/user/info` | Body: m1a.k | UserServices |
| `POST` | `api/sns/v2/user/info/pre_save` | Field: key, value | UserServices |
| `POST` | `api/sns/v2/user/info/pre_save` | Body: m1a.k | UserServices |
| `POST` | `api/sns/v2/user/info/preview` | Field: modify_contents, new_page_exp, load_widgets_opt_exp, ext_params | UserServices |
| `POST` | `api/sns/v2/user/login/sid_reason` |  | IDeviceService |
| `POST` | `api/sns/v2/user/mute_view` | Field: target_user_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | UserServices |
| `POST` | `api/sns/v2/user/phone/bind` |  | LoginServices |
| `POST` | `api/sns/v2/user/phone/bind-revert` | Field: mobile_token, zone, phone | IBindService |
| `POST` | `api/sns/v2/user/phone/change` | Field: mobile_token, zone, phone, unbind_other_account, rebind_auxiliary_account, validate_phone_token, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | IBindService |
| `POST` | `api/sns/v2/user/unfollow` | Field: data | LoginServices |
| `POST` | `api/sns/v3/account_recovery/start` | Field: phone, red_id, face_token, is_device, selected_candidate_index | RecoverServices |
| `POST` | `api/sns/v3/user/account_info/bind` |  | IBindService |
| `POST` | `api/sns/v3/user/account_info/bind` |  | LoginServices |
| `POST` | `api/sns/v3/user/login` |  | AccountService |
| `POST` | `api/sns/v4/note/comment` | Field: content, note_id, comment_id, at_users, hash_tags, is_note_first_comment | CommentService |
| `POST` | `api/sns/v4/user/login/code` |  | AccountService |
| `POST` | `api/sns/v4/user/register` |  | AccountService |
| `POST` | `api/sns/v4/user/register` | Field: tmp_token | ILoginService |
| `POST` | `api/sns/v6/homefeed/upload_categories` |  | ExploreService |
| `PUT` | `/api/sns/v1/board` | Field: share_mode, invite_user_ids | CommonBoardService |
| `PUT` | `/api/sns/v1/comment/top` | Field: comment_id, action | CommentService |
| `PUT` | `/api/sns/v1/dailystatus` | Field: note_id, daily_note, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | NoteDetailService |
| `PUT` | `/api/sns/v1/note/collection/collect` | Field: collection_id, tag_id, source_item_id | CollectionService |
| `PUT` | `/api/sns/v1/note/collection/collect` | Field: collection_id | PortfolioService |
| `PUT` | `/api/sns/v1/system_service/push/switch` | Field: switch_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | MsgServices |
| `PUT` | `/api/sns/v1/video_template/review_tab/show_status` | Body: com.xingin.net.gen.model.JarvisApiSnsV1VideoTemplateReviewTabShowStatusPutRequestBody | CapaApi |
| `PUT` | `/api/sns/v1/video_template/review_tab_show_status` | Body: com.xingin.capa.network.model.ReviewTabShowStatusRequestBody | CapaTemplateResourceService |
| `PUT` | `/api/sns/v2/note` | Body: com.xingin.capa.feature_model.session.ReportParamModel | NoteService |
| `PUT` | `/api/sns/v2/note/delete_danmaku` | Query: note_id, danmaku_id | DanmakuService |
| `PUT` | `/api/sns/v2/note/do_vote` |  | NoteDetailService |
| `PUT` | `/api/sns/v2/note/post_danmaku` | Field: note_id, content, begin_edit_mil_sec, begin_edit_player_id, post_mil_sec, post_player_id | DanmakuService |
| `PUT` | `/api/sns/v3/message/you/fold/read` | Field: scene, type | FoldCommentApi |
| `PUT` | `api/sns/v1/board/manage` | Field: pub_board_ids, pri_board_ids, all_boards_action | PrivacyServices |
| `PUT` | `api/sns/v1/system_service/config/video_download_switch` | Field: enable | GeneralSettingServices |
| `PUT` | `api/sns/v1/system_service/push/switch` | Field: switch_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | LiveRemindSwitchHelper |
| `PUT` | `api/sns/v1/system_service/push/switch` | Field: switch_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | PushServices |
| `PUT` | `api/sns/v1/system_service/push/switch` | Field: switch_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | EdithUserServices |
| `PUT` | `api/sns/v1/user/privacy` | Field: only_followings_can_comment, only_receive_followings_at_info, disable_search_from_phone, disable_search_from_weibo, remove_notes_from_localfeed, only_followings_send_danmaku, hide_followers, hide_followings, disable_all_reminder, privacy_chat_config, online_status_config, disable_pymk, disable_in_others_follow_fans_list, disable_pymk_search, show_share_account, show_chat_medal, disable_cmt_from_co_friends, picture_search_switch | EdithUserServices |
| `PUT` | `api/sns/v1/user/privacy` | Field: only_followings_can_comment, only_receive_followings_at_info, disable_search_from_phone, disable_search_from_weibo, remove_notes_from_localfeed, only_followings_send_danmaku, hide_followers, hide_followings, disable_all_reminder, privacy_chat_config, online_status_config, disable_pymk, disable_in_others_follow_fans_list, disable_pymk_search, show_share_account, show_chat_medal, disable_cmt_from_co_friends, picture_search_switch, user_video_download_switch | EdithUserServices |
| `PUT` | `api/sns/v2/user/privacy` | Field: only_followings_can_comment, only_receive_followings_at_info, disable_search_from_phone, disable_search_from_weibo, remove_notes_from_localfeed, only_followings_send_danmaku, picture_search_switch | UserServices |
| `PUT` | `api/sns/v5/message` | Field: type, biz_type, biz_id, ext_type | MsgServices |
| `PUT` | `api/sns/v5/message` | Field: type | MessageServices |

#### `socialinteract`（7 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/socialinteract/guide_follow` | Query: target_user_id | NoteDetailService |
| `GET` | `/api/socialinteract/videofeed/pymk` | Query: card_type, cursor | MsgServices |
| `POST` | `/api/socialinteract/banner_image/like` | Field: target_user_id | UserServices |
| `POST` | `/api/socialinteract/banner_image/unlike` | Field: target_user_id | UserServices |
| `POST` | `/api/socialinteract/user_avatar/like` | Field: target_user_id | UserServices |
| `POST` | `/api/socialinteract/user_avatar/unlike` | Field: target_user_id | UserServices |
| `POST` | `/api/socialinteract/videofeed/block` | Field: card_type | MsgServices |

#### `speechai`（6 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/speechai/ai_sing/rsync/get_audios` | Body: com.xingin.capa.network.model.ai.SingParamsWrapper | TemplateAISingRequestService |
| `POST` | `/api/speechai/caption/rsync/get_caption` | Body: com.xingin.capa.network.model.GetCaptionRequestBody | CapaCaptionService |
| `POST` | `/api/speechai/caption/rsync/get_caption` | Body: com.xingin.net.gen.model.Edith2ApiSpeechaiCaptionRsyncGetCaptionPostRequestBody | CapaApi |
| `POST` | `/api/speechai/nonstreamingasr` | Query: domain, biz_name, file_id | AsrService |
| `POST` | `/api/speechai/tts4capaplus/rsynctts` | Field: ttsParams | TemplateTtsService |
| `POST` | `/api/speechai/tts4capatemplate/rsynctts` | Field: ttsParams | TemplateTtsService |

#### `speedtest`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/speedtest` |  | AliothServices |

#### `store`（146 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/api/store/v1/vendor/collection` | Query: vendor_id | CommonVendorService |
| `GET` | `/api/store/distribution/note/cards` | Query: note_id | NoteDetailService |
| `GET` | `/api/store/edith/logistics/package/tracking` | Query: package_id, need_logistics_route | RLMapViewService |
| `GET` | `/api/store/edith/oc/cashier` | Query: order_id, support_pay_apps; Header: rn-name, rn-version | RetentionService |
| `GET` | `/api/store/edith/review/action/trigger_result` | Query: biz_type, biz_id, rn_version | SurpriseBoxService |
| `GET` | `/api/store/edith/review/v3/product_detail/product_review` | Query: sku_id, module_names | GoodsDetailService |
| `GET` | `/api/store/edith/review/v3/product_detail/product_review` | Query: sku_id, module_names | GoodsPreviewService |
| `GET` | `/api/store/edith/review/variant` | Query: sku_id, trade_ext | GoodsDetailService |
| `GET` | `/api/store/edith/sc/recommend/multi` | Query: sku_id, biz_scene, cursor | GoodsDetailService |
| `GET` | `/api/store/edith/sc/refresh` | Query: pre_page, extra_info | CartPreloadApi |
| `GET` | `/api/store/guide/components/shop_entrance` | Query: seller_user_id, ext_params; Header: x-ratelimit-meta | StoreServices |
| `GET` | `/api/store/hf/mall_home/bottom_bar` | Query: view_from, extra | StoreService |
| `GET` | `/api/store/jpd/edith/detail/composition` | Query: item_id | IChartService |
| `GET` | `/api/store/jpd/edith/detail/goods_note_info` | Query: sku_id | GoodsDetailService |
| `GET` | `/api/store/jpd/edith/detail/live/floatwindow` | Query: sku_id, app_type; Header: x-ratelimit-meta | GoodsDetailService |
| `GET` | `/api/store/jpd/edith/detail/placeholder` | Query: sku_id | GoodsDetailService |
| `GET` | `/api/store/jpd/edith/detail/share_code` | Query: sku_id, trade_ext, original_link_url, nav_bar_type | GoodsDetailService |
| `GET` | `/api/store/jpd/edith/detail/sizechart` | Query: item_id | IChartService |
| `GET` | `/api/store/jpd/edith/detail/sizechart` | Query: item_id, address_id, size_chart_type | IChartService |
| `GET` | `/api/store/jpd/edith/detail/variant` | Query: sku_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, xhs_g_s, anchor_id, real_contract_id, live_page_id, trade_ext, anti_crawler, variant_click_type, app_type, is_native; Header: x-ratelimit-meta, rn-name, rn-version | IGoodsVpApi |
| `GET` | `/api/store/jpd/edith/detail/variant/live` | Query: item_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, xhs_g_s, anchor_id, real_contract_id, live_page_id, anti_crawler, variant_click_type, trade_ext, app_type, is_native; Header: x-ratelimit-meta, rn-name, rn-version | ILiveVpApi |
| `GET` | `/api/store/jpd/edith/detail/vision/buyable_note` | Query: sku_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, address_id, move_ahead_pic_id, trade_ext, auto_refresh, ext_query | GoodsDetailVisionService |
| `GET` | `/api/store/jpd/edith/detail/vision/c2c/display` | Query: sku_id, user_id, item_id, offer_id, style, b_user_id, business_type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, extra_info, trade_ext, track | ProGoodsDetailService |
| `GET` | `/api/store/jpd/edith/detail/vision/c2c/preview` | Query: sku_id, user_id, item_id, offer_id, style, b_user_id, business_type, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, extra_info, trade_ext | ProGoodsDetailService |
| `GET` | `/api/store/jpd/edith/detail/vision/community` | Query: sku_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, address_id, cart_key, pre_page, move_ahead_pic_id, trade_ext, auto_refresh, ext_query | GoodsDetailVisionService |
| `GET` | `/api/store/jpd/edith/detail/vision/community` | Query: sku_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, address_id, pre_page, move_ahead_pic_id, trade_ext, live_forecast_id, detail_channel_type, auto_refresh, ext_query | GoodsDetailVisionService |
| `GET` | `/api/store/jpd/edith/detail/vision/curation` | Query: sku_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, address_id, anchor_id, cart_key, pre_page, trade_ext, move_ahead_pic_id, com.alipay.ams.component.sdk.InternalConfigKeys.ADDRESS_ELEMENT_MODE, auto_refresh, ext_query | GoodsDetailVisionService |
| `GET` | `/api/store/jpd/edith/detail/vision/live` | Query: sku_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, real_contract_id, live_page_id, anchor_id, live_coupon_claim_status, address_id, pre_page, move_ahead_pic_id, trade_ext, auto_refresh, ext_query | GoodsDetailVisionService |
| `GET` | `/api/store/jpd/edith/detail/vision/primary` | Query: sku_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, address_id, cart_key, pre_page, trade_ext, move_ahead_pic_id, auto_refresh, ext_query | GoodsDetailVisionService |
| `GET` | `/api/store/mall/mall_home/static_area` |  | StoreServiceV3 |
| `GET` | `/api/store/mall/mall_home/tab/feeds` | Query: tab_id, cursor_score, page_source, is_pull_down, purchase_sku_id, user_operator_param, view_from | StoreServiceV3 |
| `GET` | `/api/store/mall/mall_home/tab/feeds` | Query: tab_id, cursor_score, page_source, is_pull_down, purchase_sku_id, user_operator_param, view_from | StoreServiceV3 |
| `GET` | `/api/store/nb/lottery/v2/info` | Query: note_id | NoteDetailService |
| `GET` | `/api/store/oc/order_paid_query` | Query: oid | PayApiService |
| `GET` | `/api/store/personal/curation/search_by_c` | Query: keyword, anchor_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | ProfileSearchGoodsServices |
| `GET` | `/api/store/personal/curation/search_by_k` | Query: keyword, cursor, real_time, after_add_goods | AlphaGoodsProductService |
| `GET` | `/api/store/personal/curation/sort` |  | StoreServices |
| `GET` | `/api/store/personal/curation/sort` | Query: anchor_id, type, keyword, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | ProfileSearchGoodsServices |
| `GET` | `/api/store/personal/get_tab_component` | Query: user_id, seller_id, new_arrival_range, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, sort_version, goods_extra_param, last_top_coupons | StoreServices |
| `GET` | `/api/store/personal/get_trade_seller_info` |  | UserServices |
| `GET` | `/api/store/ps/discovery/hot_list` |  | AliothServices |
| `GET` | `/api/store/ps/in_store_trending/v1` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, store_id | CommercialSearchServices |
| `GET` | `/api/store/ps/products/v3` | Query: keyword, filters, page, size, sort, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, search_id, page_pos, store_id, geo | CommercialSearchServices |
| `GET` | `/api/store/ps/products/v3` | Query: keyword, size, filters, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | CommercialSearchServices |
| `GET` | `/api/store/ps/products/v3` | Query: keyword, size, filters, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | CommercialSearchServicesV2 |
| `GET` | `/api/store/ps/products/v3` | Query: keyword, page, size, sort, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, search_id, store_id, link_source | ShopSearchService |
| `GET` | `/api/store/ps/products/v3` | Query: keyword, page, size, sort, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, search_id, store_id, link_source | ProfileSearchGoodsServices |
| `GET` | `/api/store/ps/recommend_info/v2` | Query: keyword, search_id, geo, preview_ad | CommercialSearchServicesV2 |
| `GET` | `/api/store/ps/tabdot/cancel` | Query: type | AliothServices |
| `GET` | `/api/store/ps/trending/v3` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, placeholder | AliothServices |
| `GET` | `/api/store/review/v2/{skuId}/product_detail/product_review` | Path: skuId; Query: from | GoodsDetailService |
| `GET` | `/api/store/review/{item_id}/show_note` | Path: item_id; Query: tab, page, page_size | GoodsDetailService |
| `GET` | `/api/store/rf/multi_feeds` | Query: cursor_score, is_pull_down, biz_name, sku_id_list | GoodsDetailService |
| `GET` | `/api/store/shop/recommend` | Query: sku_id, app_type | GoodsDetailService |
| `GET` | `/api/store/shop/recommend/v2` | Query: sku_id, app_type | GoodsDetailService |
| `GET` | `/api/store/ts/consult/open/pay/channel` | Query: user_id, order_id, channel, client_source | IMPPayService |
| `GET` | `/api/store/v2/link/search` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID, type, name, subname, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | HashTagLinkHandler |
| `GET` | `/api/store/vs/{seller_id}/info` | Path: seller_id; Query: sid; Header: authorization | ChatDetailApiService |
| `GET` | `/api/store/vs/{store_id}/fans_coupon/obtain` | Path: store_id; Query: target_user_id, template_id, claim_ciphertext | GoodsDetailService |
| `GET` | `api/store/distribution/selection-center/buyer/info` | Query: host_id | AlphaPlanEdithService |
| `GET` | `api/store/distribution/selection-center/distributor/info` |  | AlphaChatServices |
| `GET` | `api/store/jpd/{goodsId}` | Path: goodsId; Query: mocked, note_id | FollowNoteModel |
| `GET` | `api/store/jpd/{goodsId}/static` | Path: goodsId | FollowNoteModel |
| `GET` | `api/store/mall/mall_home/wind_vane` | Query: sku_id | StoreService |
| `GET` | `api/store/nb/bridge/cards` | Query: target_id, target_type, is_default, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, ads_track_id | FollowNoteModel |
| `GET` | `api/store/oc/order_paid_query` | Query: oid; Header: xy-common-params | IMPPayService |
| `GET` | `api/store/personal/get_sync_curation_switch_status` | Query: room_id | AlphaGoodsEdithService |
| `GET` | `api/store/sc/items_count` |  | FollowNoteModel |
| `GET` | `api/store/trade_note/query/put_goods_permission` | Query: user_id | CommentPostGoodsApi |
| `GET` | `api/store/ts/pay_method` | Query: channel, client_source, oid; Header: xy-common-params | IMPPayService |
| `POST` | `/api/store/address/default/set` | Body: com.google.gson.l | PayApiService |
| `POST` | `/api/store/ai_guide/send` | Body: fq5.b | ShopAiGuideApiService |
| `POST` | `/api/store/bridge/half_layout_goods_list` | Field: note_id | GoodsDialogService |
| `POST` | `/api/store/bridge/half_layout_goods_list` | Body: pw5.r | TransactionNoteRepo |
| `POST` | `/api/store/bridge/trade_note/permission` | Body: pw5.v | TransactionNoteRepo |
| `POST` | `/api/store/cs/acqn/{template_id}` | Path: template_id; Field: claim_ciphertext, claim_channel | MsgServices |
| `POST` | `/api/store/cs/acqn/{template_id}` | Path: template_id; Field: claim_ciphertext, claim_channel | GoodsDetailService |
| `POST` | `/api/store/cs/acqn/{template_id}` | Path: template_id; Field: claim_ciphertext, claim_channel | StoreJarvisCouponService |
| `POST` | `/api/store/cs/acqn/{template_id}` | Path: template_id; Field: claim_channel, claim_ciphertext | PayApiService |
| `POST` | `/api/store/cs/promo/acqn/{id}` | Path: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_ID; Field: str | FeedModel |
| `POST` | `/api/store/distribution/creator/apply` | Body: lw0.m4 | AlphaRecommendSelectionService |
| `POST` | `/api/store/distribution/tscenter/contract_list` | Body: pw5.h | TransactionNoteRepo |
| `POST` | `/api/store/edith/cc` | Body: xz5.o2; Header: x-ratelimit-meta, rn-name, rn-version | ICartPayApi |
| `POST` | `/api/store/edith/cc` | Body: xz5.p2; Header: x-ratelimit-meta, rn-name, rn-version | IConsolidationPayApi |
| `POST` | `/api/store/edith/cc` | Body: xz5.o2; Header: x-ratelimit-meta, rn-name, rn-version | IMultiplePayApi |
| `POST` | `/api/store/edith/cc` | Body: xz5.q2; Header: x-ratelimit-meta, rn-name, rn-version | ISingleSkuPayApi |
| `POST` | `/api/store/edith/cc/check_content` | Body: xz5.s2 | PayApiService |
| `POST` | `/api/store/edith/cc/live` | Body: xz5.q2; Header: x-ratelimit-meta, rn-name, rn-version | ISingleLiveSkuPayApi |
| `POST` | `/api/store/edith/cc/popup/window` | Body: yk5.d | PayApiService |
| `POST` | `/api/store/edith/cc/popup/window/metric/submit` | Body: yk5.f | RetentionApiService |
| `POST` | `/api/store/edith/cc/variant` | Body: xz5.q2; Header: x-ratelimit-meta, rn-name, rn-version | IGoodsVpApi |
| `POST` | `/api/store/edith/cc/variant/live` | Body: xz5.q2; Header: x-ratelimit-meta, rn-name, rn-version | ILiveVpApi |
| `POST` | `/api/store/edith/logistics/session/evaluate` | Body: ucc.q | LogisticEvaluateService |
| `POST` | `/api/store/edith/sc` | Body: com.xingin.commercial.goodsdetail.entities.b | GoodsDetailService |
| `POST` | `/api/store/edith/sc/report` | Body: com.google.gson.l | PayApiService |
| `POST` | `/api/store/edith/sc/report` | Body: com.google.gson.l | PayApiService |
| `POST` | `/api/store/edith/trade_utility/batch_record_behavior` | Body: z46.c | PayExitService |
| `POST` | `/api/store/fav/wishlist/v3` | Body: wx1.n | AlphaGoodsJarvisService |
| `POST` | `/api/store/fav/wishlist/v3` | Body: com.xingin.commercial.goodsdetail.entities.c3 | GoodsDetailService |
| `POST` | `/api/store/fav/wishlist/v3` | Body: com.xingin.commercial.goodsdetail.entities.c3 | PayApiService |
| `POST` | `/api/store/guide/components` | Body: com.xingin.commercial.goodsdetail.entities.t; Header: x-ratelimit-meta | GoodsDetailService |
| `POST` | `/api/store/guide/components/curation_personal_tab` | Body: p7a.s; Header: x-ratelimit-meta | StoreServices |
| `POST` | `/api/store/guide/components/dynamic_event_click` | Field: baseActionRequest, bizParam | EventService |
| `POST` | `/api/store/guide/components/general` | Body: defpackage.StoreGeneralReq | StoreClassificationService |
| `POST` | `/api/store/guide/components/shop_category` | Body: defpackage.StoreGeneralReq; Header: x-ratelimit-meta | StoreClassificationService |
| `POST` | `/api/store/guide/components/shop_extend` | Body: defpackage.StoreGeneralReq | StoreClassificationService |
| `POST` | `/api/store/guide/components/vision/core/shop/v2` | Field: res; Header: x-ratelimit-meta | ShopService |
| `POST` | `/api/store/guide/components/vision/core/shop/v2/preload` | Field: res; Header: x-ratelimit-meta | ShopService |
| `POST` | `/api/store/guide/components/vision/core/shop/v2/top/preload` | Field: res; Header: x-ratelimit-meta | ShopService |
| `POST` | `/api/store/guide/components/vision/core/shop_personal_tab` | Field: res; Header: x-ratelimit-meta | ShopService |
| `POST` | `/api/store/guide/components/vision/v1` | Body: com.xingin.commercial.goodsdetail.entities.t; Header: x-ratelimit-meta | GoodsDetailService |
| `POST` | `/api/store/hf/mall_home/click/guide/bubble` | Query: view_from, extra; Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE | StoreService |
| `POST` | `/api/store/jpd/cancel_subscribe` | Body: com.xingin.commercial.goodsdetail.entities.z2 | GoodsDetailService |
| `POST` | `/api/store/jpd/edith/detail/claim` | Body: com.xingin.commercial.goodsdetail.entities.q1; Header: x-ratelimit-meta | GoodsDetailService |
| `POST` | `/api/store/jpd/edith/detail/seedling` | Field: note_id, spu_id, sku_id, filter_note_id | GoodsDetailService |
| `POST` | `/api/store/jpd/edith/detail/seedling/more` | Field: note_id, spu_id, sku_id, filter_note_id | GoodsDetailService |
| `POST` | `/api/store/jpd/edith/detail/seedling/unbind` | Field: note_id, item_id | GoodsDetailService |
| `POST` | `/api/store/jpd/edith/native/payment_marketing` | Body: com.xingin.commercial.goodsdetail.entities.r | GoodsDetailService |
| `POST` | `/api/store/jpd/subscribe` | Body: com.xingin.commercial.goodsdetail.entities.z2 | GoodsDetailService |
| `POST` | `/api/store/jupiter/uc/purchaser` | Body: xz5.w2 | PayApiService |
| `POST` | `/api/store/mall/mall_home/sku_items` | Body: com.google.gson.l lVar, kotlin.coroutines.Continuation<? super e86.b> | PriceCalculationApi |
| `POST` | `/api/store/mall/mall_home/upload_event` | Field: event_type, event_id, event_code, version, extra | StoreService |
| `POST` | `/api/store/mall/mall_home/vision/feed` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, extra_params, geo | IndexShopVisionApi |
| `POST` | `/api/store/mall/mall_home/vision/feed` | Query: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, geo | IndexShopVisionApi |
| `POST` | `/api/store/mall/mall_home/vision/feed/category` | Query: com.xingin.capa.feature_model.session.EditableVideo2.VIDEO_ENTRANCE_DEEPLINK | ShopCategoryVisionApi |
| `POST` | `/api/store/mall/mall_home/vision/feed/category` | Query: com.xingin.capa.feature_model.session.EditableVideo2.VIDEO_ENTRANCE_DEEPLINK | ShopCategoryVisionApi |
| `POST` | `/api/store/mall/mall_home/vision/mall_2tab_config` |  | IndexShopVisionApi |
| `POST` | `/api/store/nb/lottery/join` | Query: lottery_id | NoteDetailService |
| `POST` | `/api/store/personal/claim_coupon` | Field: user_id, seller_id, coupon_type, template_id | UserServices |
| `POST` | `/api/store/personal/clear_red_dot` | Field: biz_id, event_type | GoodsDetailService |
| `POST` | `/api/store/personal/rest_ope_live_window` | Field: operate, sub_id | UserServices |
| `POST` | `/api/store/tools/preview` | Field: action, timestamp | PreviewService |
| `POST` | `/api/store/ts/notify/iap` | Field: order_id, order_channel, receipt_data, product_id, payment_type | PayServices |
| `POST` | `/api/store/ts/order/pay` | Body: xz5.f2 | PayApiService |
| `POST` | `/api/store/ts/query/pay/marketing` | Body: com.google.gson.l | PayApiService |
| `POST` | `/api/store/user_personal/red_dot_msg/{red_dot_msg_code}` | Path: red_dot_msg_code | UserServices |
| `POST` | `/api/store/v1/vendor/collection` | Field: vendor_id | CommonVendorService |
| `POST` | `api/store/bridge/goods_note/half_layout_goods_list/v2` | Body: y66.c cVar, kotlin.coroutines.Continuation<? super nuc.w> | VisionNoteApi |
| `POST` | `api/store/cs/coupon/acqn` | Field: coupon_ids, claim_channel | FollowNoteModel |
| `POST` | `api/store/curation/category/order` | Body: wx1.o | AlphaGoodsProductService |
| `POST` | `api/store/distribution/invite/update_invitation_status` | Query: invitation_id, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS | AlphaChatServices |
| `POST` | `api/store/personal/curation/live_sync_curation` | Field: room_id | AlphaGoodsEdithService |
| `POST` | `api/store/sc/v1` | Field: item_id, quantity, added_price | FollowNoteModel |
| `POST` | `api/store/trade_note/goods_list` | Body: k76.c | CommentPostGoodsApi |
| `POST` | `api/store/trade_note/trans_goods_link` | Body: k76.i | CommentPostGoodsApi |
| `PUT` | `api/store/distribution/selection-center/invite/invitations/{invite_id}` | Path: invite_id; Field: invite_id, has_accepted, reason, kol_tel, kol_message, we_chat | AlphaChatServices |

#### `themet`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/themet/ar3d/biz-type/1/biz-id/{biz-id}` | Path: biz-id | ModelService |

#### `translation`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/translation/data/multi/get` | Body: com.xingin.android.redutils.translate.TranslatorRequestBody | TranslateService |

#### `uploader`（2 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/uploader/cloudobjectexist` | Body: com.xingin.capa.network.model.CloudObjectExistRequestBody | CapaPostTagService |
| `POST` | `/api/uploader/cloudobjectexist` | Body: com.xingin.net.gen.model.Edith2ApiUploaderCloudobjectexistPostRequestBody | CapaApi |

#### `usergrowth`（15 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/usergrowth/compass/submit_data` | Field: event_list | AugurUploadService |
| `POST` | `/api/usergrowth/mallbanner` | Field: scene | MartTipsService |
| `POST` | `/api/usergrowth/mallbanner/claim` |  | MartTipsService |
| `POST` | `/api/usergrowth/mallbanner/negativefeedback` | Field: bannerType, scene | MartTipsService |
| `POST` | `/api/usergrowth/malltab/animatio/freq` | Field: showMallEntry, showMallBubble, showMallLottie | StoreEntryServices |
| `POST` | `/api/usergrowth/malltab/animation` |  | StoreEntryServices |
| `POST` | `/api/usergrowth/reach/slot/report` | Body: com.google.gson.l | PayApiService |
| `POST` | `/api/usergrowth/sns/strategy/query` | Field: execution_id, rule_id | SurpriseBoxService |
| `POST` | `/api/usergrowth/task/recordtaskprogress` | Body: sr0.b | TaskService |
| `POST` | `api/usergrowth/activity/feedback/negative/report` | Body: xt5.h1 | StarMarketTaskApi |
| `POST` | `api/usergrowth/behavior/getflowlist` | Body: sx5.m | UserFlowRetrofitApi |
| `POST` | `api/usergrowth/behavior/report` | Body: sx5.l | UserFlowRetrofitApi |
| `POST` | `api/usergrowth/task/claimreward` | Body: xt5.n1 | StarMarketTaskApi |
| `POST` | `api/usergrowth/task/query` | Body: xt5.m1 | StarMarketTaskApi |
| `POST` | `api/usergrowth/task/recordtaskprogress` | Body: xt5.k1 | StarMarketTaskApi |

#### `v2`（4 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/v2/outdoor/store/filter_list` | Query: seller_id, location | LifeServices |
| `GET` | `/api/v2/outdoor/store/product_list` | Query: seller_id, location, page_num, page_size, poi_id, city, district | LifeServices |
| `GET` | `/api/v2/outdoor/store/product_list_new` | Query: seller_id, location, page_num, page_size, poi_id, city, district | LifeServices |
| `GET` | `/api/v2/outdoor/store/product_list_new` | Query: seller_id, location, page_num, page_size, poi_id, city, district, key_word | ProfileSearchGoodsServices |

#### `vision`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/vision/toc/preload/dsl/all` |  | VisionGlobalNetworkApi |

#### `wario`（8 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/api/wario/sdk/chats/{imChatId}/active` | Path: imChatId | ChatWarioApiClient |
| `DELETE` | `/api/wario/sdk/chats/{imChatId}/active` | Path: imChatId | ChatWarioApiClient |
| `DELETE` | `/api/wario/sdk/chats/{imChatId}/active` | Path: imChatId; Query: im_token, sid; Header: authorization | XYBCIMSessionApiService |
| `GET` | `/api/wario/chat/platform` | Query: im_token | ChatWarioApiClient |
| `GET` | `/api/wario/chat/platform` | Query: im_token, sid; Header: authorization | XYBCIMSessionApiService |
| `GET` | `/api/wario/sdk/chats/{imChatId}/history_messages` | Path: imChatId; Query: limit, direction, im_token, ref_msg_id, sid; Header: authorization | ChatDetailApiService |
| `POST` | `/api/wario/sdk/chats/{imChatId}/queue_cancel` | Path: imChatId; Query: im_token | ChatDetailApiService |
| `POST` | `/api/wario/sdk/chats/{imChatId}/queue_continue` | Path: imChatId; Query: im_token | ChatDetailApiService |

#### `web_api`（15 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/web_api/sns/v1/creator/quick_reply` |  | MsgServices |
| `GET` | `/web_api/sns/v2/enterprise/oauth2/config` | Query: app_key | OpenWebViewService |
| `GET` | `/web_api/sns/v2/enterprise/oauth2/sendCode` | Query: app_key | OpenWebViewService |
| `GET` | `web_api/sns/capa/servicegw/permission` | Query: cocreator_ids | CoCreationService |
| `GET` | `web_api/sns/v1/user/check_advanced_options_exclusive` | Query: note_id, business_binds, scene_id | TransactionNoteRepo |
| `GET` | `web_api/sns/v2/page/topic/config` | Query: page_id, source_url | StarViewPrefetchService |
| `POST` | `/web_api/sns/v2/enterprise/external-channels/track` | Body: fga.a | ILaunchTrackService |
| `POST` | `/web_api/sns/v2/enterprise/leads/connect` | Field: note_id | LeadsModel |
| `POST` | `/web_api/sns/v2/enterprise/leads/connect` | Field: note_id | NoteDetailService |
| `POST` | `/web_api/sns/v2/enterprise/oauth2/user_auth` | Body: zzd.a | OpenWebViewService |
| `POST` | `/web_api/sns/v5/creator/inspiration_favor` | Field: opt_type, inspiration_id | TemplateService |
| `POST` | `web_api/sns/v1/user/advanced_component/tip` | Field: component_binds | GlobalPostNoteComponentRepo |
| `POST` | `web_api/sns/v1/user/advanced_component/tip` | Field: component_binds | PostNoteComponentRepo |
| `POST` | `web_api/sns/v1/user/check_advanced_options_exclusive` | Body: com.xingin.commercial.transactionnote.TransactionNoteRepo.a | TransactionNoteRepo |
| `POST` | `web_api/sns/v3/page/topic` | Body: com.xingin.advert.intersitial.ui2.utils.StarViewPrefetchService.a | StarViewPrefetchService |

#### `{dynamicPath}`（2 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `{dynamicPath}` | Path: dynamicPath | AlphaMomentsLiveMallService |
| `POST` | `{dynamicPath}` | Path: dynamicPath | AlphaMomentsLiveMallService |

#### `{path_url}`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `{path_url}` | Path: path_url; Field: type | CommentService |

### 域名 `fe-resource-app.rnote.com`

#### `fe`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `https://fe-resource-app.rnote.com/fe/resource/distribute/app` | Body: qo7.a | HybridResPrefetchApi |

### 域名 `fe-resource-app.xiaohongshu.com`

#### `api`（3 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `https://fe-resource-app.xiaohongshu.com/api/fe/rn/chunk` |  | RnChunkPrePushApi |
| `POST` | `https://fe-resource-app.xiaohongshu.com/api/fe/scarlet/distribute` | Body: ol5.a | ScarletBundleApi |
| `POST` | `https://fe-resource-app.xiaohongshu.com/api/fe/scarlet/simpleGet` | Body: ol5.o | ScarletBundleApi |

#### `fe`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `https://fe-resource-app.xiaohongshu.com/fe/resource/distribute/app` | Body: qo7.a | HybridResPrefetchApi |

#### `prerequests`（2 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `https://fe-resource-app.xiaohongshu.com/prerequests/h5/distribute/app` |  | H5PreRequestService |
| `GET` | `https://fe-resource-app.xiaohongshu.com/prerequests/rn/distribute/app` |  | RnPreRequestService |

#### `resource`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `https://fe-resource-app.xiaohongshu.com/resource/h5/distribute/app` | Body: f0e.a | H5DistributeApi |

### 域名 `fe.rnote.com`

#### `api`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `https://fe.rnote.com/api/feresource/v1/web` | Body: nxc.b | WebResourceService |

### 域名 `fe.xiaohongshu.com`

#### `api`（2 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `https://fe.xiaohongshu.com/api/feresource/v1/preload?trigger=auto` | Query: version, platform | PullSdkApi |
| `POST` | `https://fe.xiaohongshu.com/api/feresource/v1/web` | Body: nxc.b | WebResourceService |

### 域名 `feresource.xiaohongshu.com`

#### `api`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `https://feresource.xiaohongshu.com/api/v6/record/simpleGet` | Body: ngb.o | ReactService |

#### `fe`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `https://feresource.xiaohongshu.com/fe/resource/distribute/app` | Body: qo7.a | HybridResPrefetchApi |

### 域名 `imstream.xiaohongshu.com`

#### `api`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `https://imstream.xiaohongshu.com/api/im/stream/tts` | Query: msg_id | ImTtsApi |

### 域名 `mediacloud.xiaohongshu.com`

#### `api`（2 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `https://mediacloud.xiaohongshu.com/api/httpdns/dns` | Query: host | NetcacheHTTPDnsApi |
| `GET` | `https://mediacloud.xiaohongshu.com/api/zeus/get_user_low_latency_score` |  | PlayerLowLatencyScoreApi |

### 域名 `qa.sit.xiaohongshu.com`

#### `api`（2 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `https://qa.sit.xiaohongshu.com/api/infra/log/ackCompleted` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN | UploadLogSitService |
| `POST` | `https://qa.sit.xiaohongshu.com/api/infra/log/upload` | Field: cdnUrl, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, appVersion, apmSid, userId, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, platform | UploadLogSitService |

### 域名 `qa.xiaohongshu.com`

#### `api`（4 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `https://qa.xiaohongshu.com/api/infra/bug_report/file/upload` |  | Api |
| `POST` | `https://qa.xiaohongshu.com/api/infra/bug_report/issue` | Body: c2d.b | Api |
| `POST` | `https://qa.xiaohongshu.com/api/infra/log/ackCompleted` | Field: com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN | UploadLogService |
| `POST` | `https://qa.xiaohongshu.com/api/infra/log/upload` | Field: cdnUrl, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_RECOMMENDATION_TOKEN, appVersion, apmSid, userId, com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_SOURCE, platform | UploadLogService |

### 域名 `referee.xiaohongshu.com`

#### `api`（2 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `https://referee.xiaohongshu.com/api/ec_ads/ad_effect/ug/invoke_result` | Body: okhttp3.RequestBody | PreviewService |
| `POST` | `https://referee.xiaohongshu.com/api/sns/v2/note/widgets/get_test_link` | Body: okhttp3.RequestBody | PreviewService |

#### `v1`（2 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `https://referee.xiaohongshu.com/v1/stateReport` | Body: okhttp3.RequestBody | MonitorApiService |
| `POST` | `https://referee.xiaohongshu.com/v1/third/collect` | Body: okhttp3.RequestBody | MonitorApiService |

### 域名 `rn-resource-app.xiaohongshu.com`

#### `api`（6 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `https://rn-resource-app.xiaohongshu.com/api/deeplink/resource` | Query: bundleName, bundleVersion | ReactService |
| `POST` | `https://rn-resource-app.xiaohongshu.com/api/bridge/api_info/app` | Body: com.xingin.xybridge.tracker.BridgeConfigRequestBody | JSBService |
| `POST` | `https://rn-resource-app.xiaohongshu.com/api/v5/record/simpleGet` | Body: ngb.o | ReactService |
| `POST` | `https://rn-resource-app.xiaohongshu.com/api/v6/record/simpleGet` | Body: ngb.o | ReactService |
| `POST` | `https://rn-resource-app.xiaohongshu.com/api/v8/records/diff` | Body: ngb.p | ReactService |
| `POST` | `https://rn-resource-app.xiaohongshu.com/api/v9/records/diff` | Body: ngb.q | ReactService |

### 域名 `rn-resource.rnote.com`

#### `api`（5 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `https://rn-resource.rnote.com/api/bridge/api_info/app` | Body: com.xingin.xybridge.tracker.BridgeConfigRequestBody | JSBService |
| `POST` | `https://rn-resource.rnote.com/api/v5/record/simpleGet` | Body: ngb.o | ReactService |
| `POST` | `https://rn-resource.rnote.com/api/v6/record/simpleGet` | Body: ngb.o | ReactService |
| `POST` | `https://rn-resource.rnote.com/api/v8/records/diff` | Body: ngb.p | ReactService |
| `POST` | `https://rn-resource.rnote.com/api/v9/records/diff` | Body: ngb.q | ReactService |

### 域名 `srap.devops.xiaohongshu.com`

#### `api`（1 个接口）
| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `https://srap.devops.xiaohongshu.com/api/ask/data/component/detail` | Query: query | SearchAgentPageApi |


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
- Java 侧字符串全部混淆：`q7.a()` / `daemon.d.c1.a()` 用「循环 XOR + 位旋转」解码，例如 `"TQÑÚ"` 与 `"I_"` 解码后 = `"tinyd"`，`"Ù«..."` 与 `"ë,"` = `"libtinyd.so"`。

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

实测（与 `daemon/d.java` 一致）：`xor_repeat("TQÑÚ\x02", "I_")` 后按位调整得 `tinyd`；`xor_repeat("Ù\x1b«...", "ë,")` 后按位调整得 `libtinyd.so`。

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

- 接口数量与方法分布：**GET 1434 / POST 1522 / PUT 46 / DELETE 38**，共 3040。
- `@jce.h` 自定义方法（如 DELETE）与部分 `@jce.*` 组合的旧接口仍在使用。
- Body 参数多数为 Kotlin data class（`com.xingin.*.entities.*` / `com.xingin.capa.feature_model.session.*`），文档列出类型名以便反查字段定义。
- 本分析基于 2026-10 线上版本，签名算法（`libtiny.so` / `libxyass.so`）与 token 接口可能随版本迭代变化，请以最新 APK 为准。
