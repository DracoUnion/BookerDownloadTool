# 知乎 Android 客户端 API 接口清单

> 分析对象：`zhihu.apk`（com.zhihu.android，v11.11.0 / versionCode 41106，targetSdk 34）
> 载体：jadx 1.5.0 反编译（19 个 classes*.dex，61851 个类，zhihu 包 46215 个类）
> 分析方式：全量扫描 `com.zhihu.*` 下 Retrofit 接口定义（`@retrofit2.http.*` 注解），提取方法、路径、请求参数
> 结果统计：共 **1600** 个去重后的 HTTP 接口（GET 905 / POST 484 / PUT 97 / DELETE 106 / PATCH 8）
> 说明：相对路径统一拼接 `https://api.zhihu.com/`，即根相对路径 `/<path>` 的完整地址为 `https://api.zhihu.com/<path>`。

---

## 1. 通用说明

### 1.1 Base URL / HOST

| 域名 | 用途 |
| --- | --- |
| `https://api.zhihu.com` | **主 API 域**（大多数接口） |
| `https://www.zhihu.com` | Web 端 / 部分回调 |
| `https://openapi.zhihu.com` | OAuth 认证（`/oauth`、`/access_token`） |
| `https://lens.zhihu.com` | 视频上传/直播/投票填报（lens 服务） |
| `https://walletpay.zhihu.com` | 钱包/支付 |
| `https://pay.zhihu.com` | 支付 |
| `https://sugar.zhihu.com` | 广告追踪/上报 |
| `https://appcloud.zhihu.com` / `appcloud2.zhihu.com` | 设备信息/配置/热修复/资源同步 |
| `https://m-cloud.zhihu.com` | 云资源/APM 采样 |
| `https://messaging.zhihu.com` | IM/群消息 |
| `https://world.zhihu.com` | 召回/预约游戏/Canvas 验证码 |
| `https://media.zhihu.com` | 媒体上传 |
| `https://simba.in.zhihu.com`、`ops.in.zhihu.com`、`home-svr.in.zhihu.com` | 内网/测试接口 |

### 1.2 Retrofit 注解（混淆后）

本 APK 中 Retrofit 注解类被混淆为单字母，映射如下：

| 混淆注解 | 原始注解 | 含义 |
| --- | --- | --- |
| `@retrofit2.http.f` | `@GET` | GET 请求 |
| `@retrofit2.http.o` | `@POST` | POST 请求 |
| `@retrofit2.http.b` | `@DELETE` | DELETE 请求 |
| `@retrofit2.http.n` | `@PATCH` | PATCH 请求 |
| `@retrofit2.http.p` | `@PUT` | PUT 请求 |
| `@retrofit2.http.h` | `@HTTP(method=..., path=...)` | 自定义方法请求 |
| `@retrofit2.http.e` | `@FormUrlEncoded` | 表单编码 |
| `@retrofit2.http.l` | `@Multipart` | 多媒体表单 |
| `@retrofit2.http.a` | `@Body` | 请求体 |
| `@retrofit2.http.c` | `@Field` | 表单字段 |
| `@retrofit2.http.d` | `@FieldMap` | 表单字段 Map |
| `@retrofit2.http.i` | `@Header` | 请求头 |
| `@retrofit2.http.j` | `@HeaderMap` | 请求头 Map |
| `@retrofit2.http.q` | `@Part` | 上传部件 |
| `@retrofit2.http.r` | `@PartMap` | 上传部件 Map |
| `@retrofit2.http.s` | `@Path` | URL 路径参数 |
| `@retrofit2.http.t` | `@Query` | 查询参数 |
| `@retrofit2.http.u` | `@QueryMap` | 查询参数 Map |
| `@retrofit2.http.x` | `@Url` | 动态完整 URL |

### 1.3 通用请求头

接口请求头由调用方（拦截器/服务接口注解）注入，常用项如下：

| 请求头 | 说明 |
| --- | --- |
| `Authorization` | Bearer token（登录态） |
| `Cookie` | Cookie 会话 |
| `X-APP-ID` | 客户端 ID |
| `X-APP-KEY` | 客户端密钥（appcloud 等） |
| `X-APP-BUILD` / `x-app-build` | 客户端构建号 |
| `X-UDID` | 设备唯一 ID |
| `X-REQ-TS` | 请求时间戳 |
| `X-REQ-SIGNATURE` | 请求签名（HmacSHA256 等） |
| `X-ARGUS-APP-KEY` / `X-USER-HASH` / `X-SYS-BIT` | Argus 风控/用户环境 |
| `x-env` | 环境标识 |
| `R-APP-FLAVOR` | 渠道 flavor |
| `za-spm` | 埋点 spm（统计） |
| `X-Account-Unlock` | 账号解锁校验 |
| `X-Zxt-Live-Token` | 直播/巡课 token |
| `x-ad-styles` / `x-ad-preview` / `need_debug` | 广告样式/调试 |
| `X-Upload-Conent-Type` | 上传内容类型 |
| `no-auth` / `auth-xxx-user` | 免鉴权/特殊鉴权开关 |

### 1.4 接口索引说明

- **方法**：HTTP 方法（GET/POST/PUT/DELETE/PATCH）。
- **路径**：相对 `https://api.zhihu.com`（除非注明了其它域名）。`{xxx}` 为路径占位符，`<key>: <name>` 说明参数。
- **请求参数**：`Path:` URL 路径占位符（Retrofit `@s`）；`Query:` URL 查询参数（Retrofit `@t`）；`Field:` 表单字段（`@c`，配合 FormUrlEncoded）；`Body:` JSON 请求体（`@a`）；`Header:` 请求头（`@i`）。
- **来源类**：反编译保留的原始文件名（`compiled from: XxxService.java`），用于交叉定位。

## 2. 接口清单

### 2.1 api.zhihu.com#account-privacy

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `PUT` | `/account-privacy/cnts` | Field: payload | ContactService |
| `GET` | `/account-privacy/cnts/knows_reason_setting` | — | RecommendKnowService |
| `PUT` | `/account-privacy/cnts/knows_reason_setting` | Field: status | RecommendKnowService |
| `GET` | `/account-privacy/cnts/setting` | — | ContactService |
| `PUT` | `/account-privacy/cnts/setting` | Field: status | ContactService |
| `POST` | `/account-privacy/cnts/status` | Field: payload | ContactService |

### 2.2 api.zhihu.com#account

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/account/attach_info` | Field: app_list, channel_id, client_ts, is_new_device | AccountService |
| `POST` | `/account/sub/register` | — | o1 |
| `POST` | `/account/switch` | — | o1 |
| `GET` | `/account/toggle` | — | AccountService |
| `GET` | `/account/unlock/request` | — | AccountService |
| `DELETE` | `/account/{social_type}/bind` | Path: social_type; Header: X-Account-Unlock | AccountService |
| `POST` | `/account/{social_type}/bind` | Path: social_type; Header: X-Account-Unlock | AccountService |

### 2.3 api.zhihu.com#active_mail

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/active_mail` | — | AccountService |

### 2.4 api.zhihu.com#ad-style-service

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/ad-style-service/request` | Header: x-ad-styles | MorphLayoutService |
| `GET` | `/ad-style-service/request?debug=1` | Header: x-ad-styles | MorphLayoutService |

### 2.5 api.zhihu.com#ai

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/ai/generate/content_polish/adopt` | — | DbService |
| `POST` | `/ai/generate/content_polish/completion` | — | DbService |
| `GET` | `/ai/generate/pin/permissions` | Query: content_id, content_type | DbService |
| `POST` | `/ai/generate/pin/task` | — | DbService |
| `GET` | `/ai/generate/pin/task/pre_generated_result` | Query: content_id, content_type | DbService |
| `GET` | `/ai/generate/pin/task/result` | Query: token | DbService |
| `GET` | `/ai/generate/word2pic` | Query: token | DbService |
| `POST` | `/ai/generate/word2pic` | — | DbService |
| `GET` | `/ai/task/result` | Query: business_type, task_id | DbService |
| `POST` | `/ai/task/submit` | — | DbService |
| `GET` | `/ai/task/terms` | Query: business_type | DbService |
| `POST` | `/ai/task/terms` | — | DbService |

### 2.6 api.zhihu.com#ai_news

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/ai_news/weather` | — | b |

### 2.7 api.zhihu.com#alliance

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/alliance/zcode/bad_case/report` | — | p |
| `POST` | `/alliance/zcode/url` | — | p |

### 2.8 api.zhihu.com#answer_later

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/answer_later` | Query: offset | QuestionService |
| `GET` | `/answer_later/count` | — | QuestionService, a |

### 2.9 api.zhihu.com#answers

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/answers` | Field: question_id | AnswerEditorService, DraftService |
| `GET` | `/answers/v2/{id}` | Path: id | d |
| `GET` | `/answers/v2/{token}/link_cards` | Path: token; Query: card_type | a |
| `DELETE` | `/answers/{answer_id}` | Path: answer_id | AnswerService, a, c |
| `GET` | `/answers/{answer_id}` | Path: answer_id; Query: with_pagination | a |
| `PUT` | `/answers/{answer_id}` | Path: answer_id | AnswerEditorService, AnswerRevisionService, AnswerService, DraftService, a, c |
| `GET` | `/answers/{answer_id}/collections_v2` | Path: answer_id | AnswerService |
| `PUT` | `/answers/{answer_id}/collections_v2` | Path: answer_id; Field: add_collections, remove_collections | AnswerService |
| `GET` | `/answers/{answer_id}/image_reactions` | Path: answer_id | ImageViewerService |
| `POST` | `/answers/{answer_id}/nothelpers` | Path: answer_id | AnswerService |
| `DELETE` | `/answers/{answer_id}/nothelpers/{member_id}` | Path: answer_id, member_id | AnswerService |
| `GET` | `/answers/{answer_id}/rewarddetails` | Path: answer_id; Query: offset | AnswerService |
| `GET` | `/answers/{answer_id}/rewarders` | Path: answer_id; Query: offset | AnswerService, ZhuanlanAnswerService |
| `POST` | `/answers/{answer_id}/rewarders` | Path: answer_id; Field: amount, type | ZhuanlanAnswerService |
| `GET` | `/answers/{answer_id}/segments` | Path: answer_id | AnswerEditorService, DbService |
| `GET` | `/answers/{answer_id}/settings` | Path: answer_id | AnswerEditorService, DbService |
| `POST` | `/answers/{answer_id}/voters` | Path: answer_id; Field: voteup_count, voting | AnswerBigCardInteractiveService, InteractiveService, TopicService |
| `GET` | `/answers/{id}/share` | Path: id | ShareService |
| `POST` | `/answers/{id}/voters` | Path: id; Field: voting | e |
| `DELETE` | `/answers/{urlToken}/thankers` | Path: urlToken | AnswerBigCardInteractiveService, TopicService |
| `POST` | `/answers/{urlToken}/thankers` | Path: urlToken | AnswerBigCardInteractiveService, TopicService |

### 2.10 api.zhihu.com#api

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/account/prod/account` | — | a |
| `POST` | `/api/account/prod/account/email` | Field: new_email; Header: X-Account-Unlock | AccountBindService |
| `PUT` | `/api/account/prod/account/email` | Field: digits, new_email; Header: X-Account-Unlock | AccountBindService |
| `POST` | `/api/account/prod/account/operator/info` | Field: access_token, appkey, expires_at, gw_auth, operator_type, refresh_token, social_id, source | AccountBindService |
| `PUT` | `/api/account/prod/account/operator_phone_no` | Field: access_token, appkey, gw_auth, operator_type, source; Header: X-Account-Unlock | AccountBindService |
| `PUT` | `/api/account/prod/account/password` | Field: new_password; Header: Authorization, X-Account-Unlock | AccountBindService |
| `POST` | `/api/account/prod/account/phone_no` | Field: new_phone_no, sms_type; Header: X-Account-Unlock | AccountBindService |
| `PUT` | `/api/account/prod/account/phone_no` | Field: digits, new_phone_no; Header: X-Account-Unlock | AccountBindService |
| `POST` | `/api/account/prod/account/phone_no/cover` | Header: X-Account-Unlock | AccountBindService |
| `GET` | `/api/account/prod/account/phone_no/social_info` | Query: phone_no | AccountBindService |
| `POST` | `/api/account/prod/account/unlock/digits` | Field: digits | a |
| `POST` | `/api/account/prod/account/unlock/password` | Field: password | a |
| `GET` | `/api/account/prod/account/unlock/request` | — | a |
| `POST` | `/api/account/prod/account/unlock/request/email` | — | a |
| `POST` | `/api/account/prod/account/unlock/request/sms` | — | a |
| `POST` | `/api/account/prod/account/unlock/request/voice` | — | a |
| `DELETE` | `/api/account/prod/account/{social_type}` | Path: social_type; Header: X-Account-Unlock | AccountBindService |
| `DELETE` | `/api/account/prod/account/{social_type}/bind` | Path: social_type; Header: X-Account-Unlock | AccountBindService |
| `POST` | `/api/account/prod/account/{social_type}/bind` | Path: social_type; Header: Authorization, X-Account-Unlock | AccountBindService |
| `POST` | `/api/account/prod/auth/digits` | Field: client_id, sms_type, username | a |
| `POST` | `/api/account/prod/client_logout` | Field: token, use_refresh_direct_sign | a |
| `POST` | `/api/account/prod/guests/token` | — | a |
| `GET` | `/api/account/prod/security_center/activity_count` | — | a |
| `GET` | `/api/account/prod/security_center/login_records` | — | a |
| `DELETE` | `/api/account/prod/security_center/login_records/{record_id}` | Path: record_id; Header: X-Account-Unlock | a |
| `GET` | `/api/account/prod/security_center/trust_devices` | — | a |
| `POST` | `/api/account/prod/security_center/trust_devices` | Header: X-Account-Unlock | a |
| `DELETE` | `/api/account/prod/security_center/trust_devices/{device_id}` | Path: device_id; Header: X-Account-Unlock | a |
| `POST` | `/api/account/prod/sign_in` | — | a |
| `POST` | `/api/account/prod/sign_in/environment` | Field: refresh_token | a |
| `POST` | `/api/account/prod/sms/digits` | Field: phone_no, sms_type | a |
| `GET` | `/api/account/prod/sms/supported_countries` | — | a |
| `POST` | `/api/account/prod/social/associate/steam/bind` | — | SocialService |
| `POST` | `/api/account/prod/social/associate/steam/un_bind` | — | SocialService |
| `POST` | `/api/account/prod/social/associate/{type}/bind` | Path: type | SocialService |
| `POST` | `/api/account/prod/social/associate/{type}/un_bind` | Path: type | SocialService |
| `POST` | `/api/account/prod/social/info` | Field: access_token, appkey, code, expires_at, refresh_token, social_id, social_type, source | AccountBindService |
| `POST` | `/api/account/prod/validate/digits` | Field: digits, phone_no | a |
| `POST` | `/api/colearning/courses/{course_id}/sections/{section_id}/progress/report` | Path: course_id, section_id | a |
| `POST` | `/api/colearning/notifications/action/read` | — | a |
| `GET` | `/api/colearning/setting` | Query: course_id, section_id | a |
| `GET` | `/api/colearning/wecom/setting` | Query: course_id | a |
| `POST` | `/api/edu_live/student/channel/auth` | Header: X-Zxt-Live-Token | a |
| `POST` | `/api/edu_live/student/chatroom/auth` | Header: X-Zxt-Live-Token | a |
| `GET` | `/api/edu_live/student/history_msgs` | Query: cursor, group_id; Header: X-Zxt-Live-Token | a |
| `POST` | `/api/edu_live/student/live_room/{room_id}/sign_auth` | Path: room_id | a |
| `GET` | `/api/edu_live/student/room_info` | Header: X-Zxt-Live-Token | a |
| `POST` | `/api/edu_live/student/whiteboard/auth` | Header: X-Zxt-Live-Token | a |
| `GET` | `/api/education/livestream/livestreams/{livestream_id}/announcement` | Path: livestream_id | a |
| `GET` | `/api/education/livestream/livestreams/{livestream_id}/chat_explain` | Path: livestream_id | a |
| `GET` | `/api/education/livestream/livestreams/{livestream_id}/common_msg` | Path: livestream_id | a |
| `GET` | `/api/education/livestream/livestreams/{livestream_id}/info` | Path: livestream_id; Query: group_id | a |
| `GET` | `/api/education/livestream/livestreams/{livestream_id}/lotteries/announcement` | Path: livestream_id | a |
| `GET` | `/api/education/livestream/livestreams/{livestream_id}/lotteries/{lottery_id}/attend_users` | Path: livestream_id, lottery_id | a |
| `POST` | `/api/education/livestream/livestreams/{livestream_id}/lotteries/{lottery_id}/fill_info` | Path: livestream_id, lottery_id | a |
| `GET` | `/api/education/livestream/livestreams/{livestream_id}/lotteries/{lottery_id}/images` | Path: livestream_id, lottery_id | a |
| `GET` | `/api/education/livestream/livestreams/{livestream_id}/lotteries/{lottery_id}/reward_users` | Path: livestream_id, lottery_id | a |
| `GET` | `/api/education/livestream/livestreams/{livestream_id}/pop_card` | Path: livestream_id | a |
| `GET` | `/api/education/livestream/livestreams/{livestream_id}/recommended` | Path: livestream_id | a |
| `GET` | `/api/education/livestream/livestreams/{livestream_id}/status` | Path: livestream_id | a, b |
| `GET` | `/api/education/livestream/livestreams/{livestream_id}/subscribe_list` | Path: livestream_id | a |
| `GET` | `/api/personal/log/hit/target` | Query: appKey, extra, userId | LogDogeService |
| `POST` | `/api/personal/log/upload` | Part: json | LogDogeService |
| `POST` | `/api/personal/log/upload/limit` | — | LogDogeService |
| `POST` | `/api/personal/log/upload/reason` | — | LogDogeService |
| `GET` | `/api/privacy/settings` | — | i |
| `POST` | `/api/privacy/settings` | — | i |
| `GET` | `/api/v1/blue_page/blue_box` | — | u |
| `POST` | `/api/v1/blue_page/blue_box/{activity_id}/report` | Path: activity_id; Field: type | u |
| `POST` | `/api/v1/blue_page/superquestion/report_info` | — | RedPacketService |
| `GET` | `/api/v4/brand/questions/{question_token}/activity/answers/red-packet` | Path: question_token | RedPacketService |
| `GET` | `/api/v4/collections/contents/{type}/{id}?all=false` | Path: id, type | AnswerBigCardInteractiveService |
| `POST` | `/api/v4/commercial/ecommerce/wechat/push` | — | WxServerMsgService |
| `GET` | `/api/v4/content/publish/notice_v2` | Query: action, isPublished, title | QuestionEditorService |
| `POST` | `/api/v4/crm/chat/plugin/clue_activities/{activity_token}/action/submit` | Path: activity_token | BusinessService |
| `POST` | `/api/v4/crm/chat/plugin/clue_activities/{token}/action/send` | Path: token | MenuService |
| `GET` | `/api/v4/crm/chat/plugin/clue_activities?template_type=2` | — | MenuService |
| `GET` | `/api/v4/crm/chat/plugin/coupons` | — | MenuService |
| `POST` | `/api/v4/crm/chat/plugin/coupons/{coupon_token}/action/receive` | Path: coupon_token | ChatService |
| `POST` | `/api/v4/crm/chat/plugin/coupons/{token}/action/send` | Path: token | MenuService |
| `GET` | `/api/v4/crm/chat/plugin/keywords/{sender_hash_id}` | Path: sender_hash_id | ChatService |
| `GET` | `/api/v4/crm/chat/plugin/profile/{sender_hash_id}` | Path: sender_hash_id | ChatService |
| `GET` | `/api/v4/draft-histories` | Query: limit, object_id, object_type, offset | CommunityEditorService2, DbService |
| `GET` | `/api/v4/draft-history` | Query: id, version_type | CommunityEditorService2, DbService |
| `POST` | `/api/v4/draft-history/revert` | — | CommunityEditorService2, DbService |
| `GET` | `/api/v4/ecom_data/config` | — | s |
| `GET` | `/api/v4/infinity/conversations/{conversation_id}` | Path: conversation_id | c |
| `PUT` | `/api/v4/infinity/conversations/{conversation_id}/finish` | Path: conversation_id | c |
| `POST` | `/api/v4/infinity/conversations/{conversation_id}/messages` | Path: conversation_id | c |
| `GET` | `/api/v4/infinity/message/self/card` | — | ChatService |
| `GET` | `/api/v4/infinity/message/self/card/enabled` | — | ChatService |
| `POST` | `/api/v4/infinity/order/conversation/prepay` | — | c |
| `PUT` | `/api/v4/infinity/order/conversation/prepay/{prepay_id}` | Path: prepay_id | c |
| `GET` | `/api/v4/infinity/{user_id}/calendar` | Path: user_id; Query: conversation_id, service_no | c |
| `GET` | `/api/v4/infinity/{user_id}/conversations/check` | Path: user_id; Query: service_no, type | c |
| `GET` | `/api/v4/mcn/linkcard/{id}` | Path: id; Query: scenes | a |
| `GET` | `/api/v4/mcn/linkcard/{id}/url` | Path: id; Query: deep_link, scenes, utm_campaign | a |
| `GET` | `/api/v4/mcn/midpage/collect_goods/list` | — | a |
| `POST` | `/api/v4/mcn/midpage/collect_goods/{sku_id}` | Path: sku_id | a |
| `GET` | `/api/v4/mcn/shop_cart?limit=0` | — | b |
| `GET` | `/api/v4/me/member/recommended-users` | Query: followee_token | ProfileService |
| `GET` | `/api/v4/me/topic/recommended-users` | Query: topic_token | TopicService |
| `GET` | `/api/v4/me/zero_follow/recommended-users` | — | FollowGuideService |
| `POST` | `/api/v4/member/login/record` | — | ProfileService |
| `GET` | `/api/v4/members/{urlToken}/recommendation_signalments` | Path: urlToken; Query: is_changed | ProfileService |
| `DELETE` | `/api/v4/members/{urlToken}/reviewing_signalments` | Path: urlToken | ProfileService |
| `GET` | `/api/v4/members/{urlToken}/reviewing_signalments` | Path: urlToken; Query: limit, offset | ProfileService |
| `GET` | `/api/v4/members/{urlToken}/signalments` | Path: urlToken | ProfileService |
| `POST` | `/api/v4/members/{urlToken}/signalments` | Path: urlToken | ProfileService |
| `POST` | `/api/v4/members/{urlToken}/signalments/actions/check` | Path: urlToken | ProfileService |
| `DELETE` | `/api/v4/members/{urlToken}/signalments/{signalmentId}` | Path: signalmentId, urlToken | ProfileService |
| `PUT` | `/api/v4/members/{urlToken}/signalments/{signalmentId}` | Path: signalmentId, urlToken | ProfileService |
| `DELETE` | `/api/v4/members/{urlToken}/signalments/{signalmentId}/voters` | Path: signalmentId, urlToken | ProfileService |
| `GET` | `/api/v4/members/{urlToken}/signalments/{signalmentId}/voters` | Path: signalmentId, urlToken; Query: offset | ProfileService |
| `POST` | `/api/v4/members/{urlToken}/signalments/{signalmentId}/voters` | Path: signalmentId, urlToken | ProfileService |
| `GET` | `/api/v4/members/{urlToken}/signalments/{signalmentId}/voters/new` | Path: signalmentId, urlToken; Query: offset | ProfileService |
| `PUT` | `/api/v4/share/info` | — | e |
| `GET` | `/api/v4/video_courses/review/{course_id}` | Path: course_id | VideoCourseService |
| `POST` | `/api/v4/video_courses/sections/{section_id}/last` | Path: section_id | VideoCourseService |
| `GET` | `/api/v4/video_courses/sections/{section_id}/play_duration` | Path: section_id | a |
| `POST` | `/api/v4/video_courses/sections/{section_id}/play_duration` | Path: section_id | a |
| `GET` | `/api/v4/video_courses/{course_id}` | Path: course_id | VideoCourseService |
| `GET` | `/api/v4/video_courses/{course_id}/sections/{section_id}/share` | Path: course_id, section_id | VideoCourseService |
| `GET` | `/api/v4/video_courses/{course_id}/sections_detail` | Path: course_id; Query: limit, offset | VideoCourseService |
| `GET` | `/api/v4/video_courses/{course_id}/sections_v2` | Path: course_id | VideoCourseService |
| `GET` | `/api/v4/zhihu-basic-prod/basic/settings` | Query: item_id, mode | SettingsService |
| `POST` | `/api/v4/zhihu-basic-prod/basic/settings` | Field: item_id, mode, value | SettingsService |
| `GET` | `/api/v4/zhihu-basic-prod/hotfix_config` | Query: hash_id | DataFixService |
| `GET` | `/api/v4/zhihu-basic-prod/realname/status` | Query: source | ZhiHuLabService, ZhihuPayService |
| `GET` | `/api/v4/zhihu-basic-prod/realname/tip` | Query: version | AccountService |
| `GET` | `/api/v4/zhihu-basic-prod/uniform/settings` | Query: setting_page | ZhiHuLabService, g |
| `PUT` | `/api/v4/zhihu-basic-prod/uniform/settings` | — | ZhiHuLabService, g |
| `POST` | `/api/v5/face/validate` | — | AccountService |
| `POST` | `/api/v5/megvii/biz_token` | — | AccountService |
| `POST` | `/api/v5/megvii/verify` | — | AccountService |
| `GET` | `/api/account/prod/default_avatar/random` | Header: Authorization | a |
| `POST` | `/api/account/prod/register/pre_process` | Field: access_token, appkey, expires_at, refresh_token, social_id, social_type, source | AccountRegisterService |
| `POST` | `/api/account/prod/register` | — | AccountRegisterService |
| `POST` | `/api/account/prod/validate/register_form` | Field: fullname, phone_no | AccountRegisterService |

### 2.11 api.zhihu.com#article_publish

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/article_publish/check/question` | Field: article_token | a |

### 2.12 api.zhihu.com#articles

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/articles/my_drafts` | — | DraftService |
| `GET` | `/articles/my_drafts` | Query: include, limit, offset | DraftService |
| `GET` | `/articles/v2/{id}` | Path: id | d |
| `GET` | `/articles/v2/{token}/link_cards` | Path: token; Query: card_type | a |
| `POST` | `/articles/write` | Field: content, copyright, title | ArticleRouterService |
| `POST` | `/articles/{articleId}/republish` | Path: articleId | ColumnService |
| `GET` | `/articles/{article_draft_id}/segments` | Path: article_draft_id | ArticleEditorService |
| `DELETE` | `/articles/{article_id}` | Path: article_id | ZhuanlanArticleService, a, c |
| `GET` | `/articles/{article_id}` | Path: article_id | ArticleEditorService, ZhuanlanArticleService, a |
| `PUT` | `/articles/{article_id}` | Path: article_id | c |
| `GET` | `/articles/{article_id}/collections` | Path: article_id; Query: offset | ZhuanlanArticleService |
| `PUT` | `/articles/{article_id}/collections` | Path: article_id; Field: add_collections, remove_collections | ZhuanlanArticleService |
| `GET` | `/articles/{article_id}/disclaimers` | Path: article_id | ArticleEditorService, DbService |
| `DELETE` | `/articles/{article_id}/draft` | Path: article_id | ArticleEditorService |
| `GET` | `/articles/{article_id}/draft` | Path: article_id | AnswerEditorService, ArticleEditorService, DbService, a |
| `POST` | `/articles/{article_id}/draft` | Path: article_id; Field: content, copyright, delta_time, title, topic_ids | ArticleEditorService |
| `PUT` | `/articles/{article_id}/draft` | Path: article_id; Field: content, title | ArticleEditorService |
| `GET` | `/articles/{article_id}/image_reactions` | Path: article_id | ImageViewerService |
| `GET` | `/articles/{article_id}/recommend_topics` | Path: article_id | ArticleEditorService, a |
| `DELETE` | `/articles/{article_id}/scheduled-publish` | Path: article_id | ArticleEditorService |
| `POST` | `/articles/{article_id}/scheduled-validate` | Path: article_id | ArticleEditorService, ArticleService |
| `GET` | `/articles/{article_id}/settings` | Path: article_id | ArticleEditorService, DbService |
| `GET` | `/articles/{article_id}/similar-questions` | Path: article_id | m |
| `GET` | `/articles/{article_id}/tipjar` | Path: article_id | ZhuanlanArticleService |
| `POST` | `/articles/{article_id}/tipjar_wallet` | Path: article_id; Field: price | ZhuanlanArticleService |
| `GET` | `/articles/{article_id}/tipjarors` | Path: article_id; Query: offset | ArticleService |
| `PUT` | `/articles/{article_id}/topics` | Path: article_id | ArticleEditorService |
| `POST` | `/articles/{article_id}/voters` | Path: article_id; Field: voteup_count, voting | AnswerBigCardInteractiveService, InteractiveService, ZhuanlanArticleService |
| `GET` | `/articles/{article_id}?include=contributions[*][column][articles_count,is_following]&include=activity_topping_info` | Path: article_id | a |
| `POST` | `/articles/{id}/republish` | Path: id | a |
| `GET` | `/articles/{id}/republish-requests` | Path: id | a |
| `GET` | `/articles/{id}/share` | Path: id | ShareService |

### 2.13 api.zhihu.com#auto-publish

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/auto-publish/{token}/{type}` | Path: token, type | DraftService, PublishContainerService |

### 2.14 api.zhihu.com#balance

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/balance/payment_methods` | Query: buyer_amount, service_id | WalletService |

### 2.15 api.zhihu.com#bazaar

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `PUT` | `/bazaar/activity/popup_callback/{activity_type}` | Path: activity_type | NewMarketService |
| `GET` | `/bazaar/activity/{type}` | Path: type | NewMarketService |
| `GET` | `/bazaar/float_window` | — | NewMarketService |
| `GET` | `/bazaar/learning_history` | Query: offset | KMarketService |
| `PATCH` | `/bazaar/learning_history` | — | KMarketService |
| `GET` | `/bazaar/mine/personal_v2` | — | a |
| `GET` | `/bazaar/people/{hash_id}/works` | Path: hash_id | MarketService |
| `GET` | `/bazaar/vip_tab/book_city/conditions` | — | NewMarketService |
| `GET` | `/bazaar/vip_tab/book_city/conditions/{tag_type}` | Path: tag_type; Query: in_hot_label; QueryMap: encoded = true | NewMarketService |
| `GET` | `/bazaar/vip_tab/book_city/section/{tag_type}` | Path: tag_type; Query: limit, offset; QueryMap: encoded = true | NewMarketService |
| `GET` | `/bazaar/vip_tab/book_city/sku_list/{tag_type}` | Path: tag_type; Query: limit, offset; QueryMap: encoded = true | NewMarketService |
| `GET` | `/bazaar/vip_tab/book_lists` | Query: limit, offset | KMarketService |
| `GET` | `/bazaar/vip_tab/educate_live` | — | NewMarketService |
| `GET` | `/bazaar/vip_tab/header` | Query: android_old, birthday_banner, downgradable, user_mode | NewMarketService |
| `GET` | `/bazaar/vip_tab/modules` | Query: category_tag, limit, module, offset, user_mode | NewMarketService |
| `GET` | `/bazaar/vip_tab/recommend` | — | NewMarketService |
| `DELETE` | `/bazaar/vip_tab/red_point` | Query: position_type, red_point_type | NewMarketService |
| `GET` | `/bazaar/vip_tab/shelf` | — | NewMarketService |
| `GET` | `/bazaar/vip_tab/tabs` | Query: is_experiment, user_mode | NewMarketService |
| `POST` | `/bazaar/vip_tab/window` | — | NewMarketService |
| `POST` | `/bazaar/vip_tab/window/mark` | — | NewMarketService |

### 2.16 api.zhihu.com#bind_ring_after_publish

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/bind_ring_after_publish` | — | m0 |

### 2.17 api.zhihu.com#book_reviews

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/book_reviews/{id}` | Path: id | EBookService |
| `PUT` | `/book_reviews/{id}` | Path: id; Field: content, score | EBookService |
| `DELETE` | `/book_reviews/{id}/actions/topic_like` | Path: id | TopicService |
| `POST` | `/book_reviews/{id}/actions/topic_like` | Path: id | TopicService |

### 2.18 api.zhihu.com#books

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/books/audio/{token}/all` | Path: token | AudioBookService |
| `GET` | `/books/categories/{token}` | Path: token; Query: limit, offset | EBookService |
| `GET` | `/books/collections` | Query: offset | EBookService |
| `DELETE` | `/books/collections/{collection_id}` | Path: collection_id | a |
| `GET` | `/books/collections/{collection_id}` | Path: collection_id; Query: limit, offset | EBookService |
| `POST` | `/books/collections/{collection_id}` | Path: collection_id | a |
| `GET` | `/books/default_font` | — | EBookService |
| `GET` | `/books/features/{token}` | Path: token; Query: limit, offset | EBookService |
| `GET` | `/books/fonts?font_list=android_font_2025` | — | EBookService |
| `POST` | `/books/orders` | Field: token, type | AudioBookService |
| `GET` | `/books/{book_id}` | Path: book_id; Query: include | EBookService |
| `GET` | `/books/{book_id}/chapters/word_counts` | Path: book_id; Query: is_all | EBookService |
| `GET` | `/books/{book_id}/last_read` | Path: book_id; Query: book_version | EBookService |
| `GET` | `/books/{book_id}/reviews` | Path: book_id; Query: limit, offset | EBookService |
| `POST` | `/books/{book_id}/reviews` | Path: book_id; Field: content, is_muted, score | EBookService |
| `GET` | `/books/{book_id}/simple` | Path: book_id | EBookService, a, b, c |
| `GET` | `/books/{book_id}/trial_terminal` | Path: book_id | EBookService |
| `GET` | `/books/{book_id}/v2/download` | Path: book_id; Query: is_trial | EBookService |
| `POST` | `/books/{book_id}/v2/download` | Path: book_id; Field: client_id, is_trial, key_hash, signature, timestamp, trans_key | EBookService |
| `GET` | `/books/{id}/chapters/page_list` | Path: id; Query: offset, order_by | q1 |

### 2.19 api.zhihu.com#brand

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/brand/question/{question_id}/card?include=brand` | Path: question_id | AnswerRevisionService |
| `GET` | `/brand/question/{question_id}/lottery?include=winners_answer_tokens` | Path: question_id | AnswerService |
| `GET` | `/brand/question/{question_token}/card?include=brand` | Path: question_token | l |

### 2.20 api.zhihu.com#buginfo

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `PUT` | `/buginfo/report_dirty_data` | Field: dirty_data, error_url | BugReportService |

### 2.21 api.zhihu.com#captcha

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/captcha` | Header: Authorization | CaptchaService |
| `POST` | `/captcha` | Field: input_text; Header: Authorization | CaptchaService |
| `PUT` | `/captcha` | Header: Authorization | CaptchaService |

### 2.22 api.zhihu.com#car_meta

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/car_meta/topics/{topicId}/actions/cancel_want` | Path: topicId | f |
| `POST` | `/car_meta/topics/{topicId}/actions/want` | Path: topicId | f |
| `GET` | `/car_meta/topics/{topicId}/header` | Path: topicId | f |
| `GET` | `/car_meta/topics/{topicId}/tags` | Path: topicId | f |
| `GET` | `/car_meta/topics/{topicId}/tags_feed` | Path: topicId; Query: tag_id | f |

### 2.23 api.zhihu.com#coin

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/coin/recharges` | Field: product_id, source, type, wechat_payment_type | CashierService |
| `GET` | `/coin/recharges/{tradeNumber}` | Path: tradeNumber | CashierService |

### 2.24 api.zhihu.com#collections

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/collections/contents/{content_type}/{content_id}` | Path: content_id, content_type; Header: za-spm | a |
| `PUT` | `/collections/contents/{content_type}/{content_id}` | Path: content_id, content_type; Field: add_collections, remove_collections; Header: za-spm | DbCollectionService, a, e, h |
| `DELETE` | `/collections/contents/{content_type}/{content_id}?failed_multi=1` | Path: content_id, content_type; Header: za-spm | a |
| `POST` | `/collections/contents/{content_type}/{content_url_token}` | Path: content_type, content_url_token | c, e |
| `GET` | `/collections/{collection_id}/contents?with_deleted=1` | Path: collection_id; Query: offset; Header: za-spm | a |
| `POST` | `/collections/{collection_id}/followers` | Path: collection_id | SearchComponentService |
| `DELETE` | `/collections/{collection_id}/followers/{member_id}` | Path: collection_id, member_id | SearchComponentService |
| `PUT` | `/collections/{collection_id}/unread` | Path: collection_id | a |
| `PUT` | `/collections/{collection_id}?censor=1` | Path: collection_id; Field: description, is_default, is_public, title | a |
| `GET` | `/collections/{id}/share` | Path: id | ShareService |

### 2.25 api.zhihu.com#column-feed

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/column-feed/read` | — | ProfileService |
| `POST` | `/column-feed/read` | Field: time | ProfileService |

### 2.26 api.zhihu.com#column

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/column/column_tab/banner` | — | a |
| `GET` | `/column/column_tab/feed` | — | a |
| `GET` | `/column/column_tab/subscribe_info` | — | a |

### 2.27 api.zhihu.com#columns

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/columns/v3/{column_id}` | Path: column_id | a |
| `GET` | `/columns/{column_id}/contribution-invitations/feedbacks` | Path: column_id | NotificationService |
| `POST` | `/columns/{column_id}/contribution-invitations/feedbacks` | Path: column_id; Field: feedbacks | NotificationService |
| `GET` | `/columns/{column_id}/followers` | Path: column_id; Query: offset | ColumnService |
| `POST` | `/columns/{column_id}/followers` | Path: column_id | SearchComponentService |
| `DELETE` | `/columns/{column_id}/followers/{member_id}` | Path: column_id, member_id | SearchComponentService |
| `PUT` | `/columns/{column_id}/{follow_state}` | Path: column_id, follow_state | a |

### 2.28 api.zhihu.com#comment_v5

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/comment_v5/comment/{comment_id}` | Path: comment_id | b, m |
| `GET` | `/comment_v5/comment/{comment_id}/anchor_comment` | Path: comment_id; Query: source | b |
| `GET` | `/comment_v5/comment/{comment_id}/child_comment` | Path: comment_id | b |
| `PUT` | `/comment_v5/comment/{comment_id}/operation/approve` | Path: comment_id | b |
| `DELETE` | `/comment_v5/comment/{comment_id}/operation/collapse` | Path: comment_id | b |
| `PUT` | `/comment_v5/comment/{comment_id}/operation/collapse` | Path: comment_id | b |
| `DELETE` | `/comment_v5/comment/{comment_id}/operation/hot` | Path: comment_id | b |
| `PUT` | `/comment_v5/comment/{comment_id}/operation/hot` | Path: comment_id | b |
| `DELETE` | `/comment_v5/comment/{comment_id}/operation/top` | Path: comment_id | b |
| `PUT` | `/comment_v5/comment/{comment_id}/operation/top` | Path: comment_id | b |
| `DELETE` | `/comment_v5/comment/{comment_id}/reaction/dislike` | Path: comment_id | b |
| `PUT` | `/comment_v5/comment/{comment_id}/reaction/dislike` | Path: comment_id | b |
| `PUT` | `/comment_v5/comment/{comment_id}/reaction/like` | Path: comment_id | m |
| `GET` | `/comment_v5/{object_type}/{object_id}/ai_comment` | Path: object_id, object_type | b |
| `GET` | `/comment_v5/{object_type}/{object_id}/author_say` | Path: object_id, object_type | b |
| `GET` | `/comment_v5/{object_type}/{object_id}/collapse_comments` | Path: object_id, object_type | b |
| `POST` | `/comment_v5/{object_type}/{object_id}/comment` | Path: object_id, object_type; Header: za-spm | b |
| `GET` | `/comment_v5/{object_type}/{object_id}/config` | Path: object_id, object_type; Query: reply_comment_id, source | b |
| `GET` | `/comment_v5/{object_type}/{object_id}/list-headers` | Path: object_id, object_type | b |
| `GET` | `/comment_v5/{object_type}/{object_id}/permission` | Path: object_id, object_type | a |
| `GET` | `/comment_v5/{object_type}/{object_id}/reviewing_comments` | Path: object_id, object_type | b |
| `GET` | `/comment_v5/{object_type}/{object_id}/root_comment` | Path: object_id, object_type; Query: order_by, source, type; Header: x-ad-styles | b |
| `POST` | `/comment_v5/{object_type}/{object_id}/segment/comment` | Path: object_id, object_type; Header: za-spm | b |
| `GET` | `/comment_v5/{object_type}/{object_id}/segment/config` | Path: object_id, object_type; Query: reply_comment_id, source | b |
| `GET` | `/comment_v5/{object_type}/{object_id}/share` | Path: object_id, object_type | b |

### 2.29 api.zhihu.com#comments

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/comments/{comment_id}/voters` | Path: comment_id | a |
| `DELETE` | `/comments/{comment_id}/voters/{member_id}` | Path: comment_id, member_id | a |

### 2.30 api.zhihu.com#commercial

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/commercial/banner/{questionId}` | Path: questionId | CommercialService |

### 2.31 api.zhihu.com#commercial_api

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/commercial_api/app_float_layer` | — | FeedFloatService |
| `GET` | `/commercial_api/back_brush` | Header: x-ad-styles | SrcollBackService |
| `GET` | `/commercial_api/banners_v3/app_float_corner` | Query: token, type; Header: x-ad-styles | DetailAdService |
| `GET` | `/commercial_api/banners_v3/app_topstory_banner` | — | AdCardNetService |
| `GET` | `/commercial_api/reward_video` | Query: content_id, content_type, sdk_scene_code, url_token | GetRewardInfoService |
| `GET` | `/commercial_api/sdk/prefetch` | — | CachePoolAdService |
| `GET` | `/commercial_api/sdk_launch` | — | GetThirdSDKInfoService |
| `GET` | `/commercial_api/search_eggs` | Query: query | SearchEggsManager |
| `GET` | `/commercial_api/{type}/{token}/bottom-v2` | Path: token, type; Header: x-ad-styles | l |

### 2.32 api.zhihu.com#community-prod

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/community-prod/appreciation/gifts/list?list_type=page_detail` | Query: content_token, content_type | c |
| `GET` | `/community-prod/hot/tabs` | — | ContinuousConsumptionService |
| `GET` | `/community-prod/publish_article/is-able-to` | Query: content_token | ArticleEditorService, a |
| `GET` | `/community-prod/{type}/{id}/media-detail` | Path: id, type | MediaDetailListService, a, r |

### 2.33 api.zhihu.com#community-share

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/community-share/unify/share/channel` | — | c |
| `GET` | `/community-share/unify/share/data` | Query: channel, content_id, content_type, utm_campaign, utm_medium, utm_oi, utm_source | ShareService |
| `GET` | `/community-share/unify/share/report` | Query: url_token | ShareService |
| `PUT` | `/community-share/unify/share/report` | Query: url_token | c |
| `GET` | `/community-share/union/share/channel` | — | c |

### 2.34 api.zhihu.com#community

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/community/recommend` | Query: limit, offset, scene | ProfileService |

### 2.35 api.zhihu.com#consumption_events

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/consumption_events/10001` | — | k0 |
| `POST` | `/consumption_events/10001/permission_reward_popup` | — | h |

### 2.36 api.zhihu.com#content-distribution-core

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/content-distribution-core/bubble/common/settings` | — | m0 |
| `GET` | `/content-distribution-core/bubble/common/settings/v2` | — | m0 |
| `GET` | `/content-distribution-core/bubble/common/show` | — | m0 |
| `GET` | `/content-distribution-core/plus_panel_setting` | — | m0 |
| `GET` | `/content-distribution-core/sections/{channel_id}` | Path: channel_id | FeedKmCardService |
| `POST` | `/content-distribution-core/sections/{channel_id}/baby/add` | Path: channel_id | FeedKmCardService |
| `GET` | `/content-distribution-core/sections/{channel_id}/baby/get_one` | Path: channel_id; Query: id | FeedKmCardService |
| `POST` | `/content-distribution-core/sections/{channel_id}/baby/update` | Path: channel_id | FeedKmCardService |
| `GET` | `/content-distribution-core/sections/{channel_id}/categories/{category_id}` | Path: category_id, channel_id | FeedKmCardService |
| `GET` | `/content-distribution-core/sections/{channel_id}/close_tab` | Path: channel_id | FeedKmCardService |

### 2.37 api.zhihu.com#content-promotion

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/content-promotion/super-coupon/remind` | Query: scene_code | a |
| `POST` | `/content-promotion/super-coupon/remind/disappear` | — | a |

### 2.38 api.zhihu.com#content

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/content/drafts` | Query: action, limit, offset | DraftService |
| `POST` | `/content/drafts` | — | PublishContainerService |
| `POST` | `/content/drafts/latest/abandon` | — | PublishContainerService |
| `GET` | `/content/drafts/{draft_id}` | Path: draft_id; Query: action | PublishContainerService |
| `POST` | `/content/drafts_delete` | — | DraftService, OriginalCardService, PublishContainerService |
| `GET` | `/content/plugin/{content_id}` | Path: content_id; Query: action, activity_id, activity_provider, extra_id | PublishContainerService |
| `POST` | `/content/publish` | — | DraftService |
| `POST` | `/content/publish/ai_title/infos` | — | ExploreAutoTitleService |
| `GET` | `/content/publish/config/shoot_guide` | Query: beauty_version, filter_version, idea_version, sticker_version | MediaStudioService |
| `GET` | `/content/publish/configs` | Query: content, pin_id, pin_ring_id, ring_list_count, scene, title | DbService, ExploreAutoTitleService, m0 |
| `POST` | `/content/publish/configs` | — | ExploreAutoTitleService |
| `POST` | `/content/publish/configs/v2` | — | DbService |
| `GET` | `/content/publish/content_material/emojis` | Query: material_id | DbService |
| `GET` | `/content/publish/control` | Query: question_token, scene | a |
| `GET` | `/content/publish/guide/segment_record/inspiration` | — | MediaStudioService |
| `GET` | `/content/publish/guide/segment_record/tip` | — | MediaStudioService |
| `GET` | `/content/publish/guide/segment_record/tutorial` | — | MediaStudioService |
| `GET` | `/content/publish/link_card_infos` | Query: max, scene, urls | DbService |
| `GET` | `/content/publish/parse_url` | Query: scene, url | b |
| `GET` | `/content/publish/ring/infos` | Query: ring_ids | DbService |
| `GET` | `/content/publish/ring/style_data` | Query: ring_id | m0 |
| `POST` | `/content/publish/topics/create` | — | m |
| `GET` | `/content/publish/topics/materials_related` | Query: material_ids | a |
| `GET` | `/content/publish/topics/permission` | — | m |
| `POST` | `/content/publish/topics/recommend` | Query: key_word, recommend_type, topic_ids | m |
| `GET` | `/content/publish/topics/search` | Query: key_word, recommend_type, topic_ids | m |
| `POST` | `/content/staging/publish/register` | — | DbService |

### 2.39 api.zhihu.com#content_follow

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/content_follow/{content_type}/{content_token}/follow` | Path: content_token, content_type | c |
| `POST` | `/content_follow/{content_type}/{content_token}/not_interest` | Path: content_token, content_type | c |
| `POST` | `/content_follow/{content_type}/{content_token}/unfollow` | Path: content_token, content_type | c |

### 2.40 api.zhihu.com#contents

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/contents/{content_id}/reactions` | Path: content_id | InteractiveService, a |
| `POST` | `/contents/{content_id}/reactions` | Path: content_id | InteractiveService, a |

### 2.41 api.zhihu.com#contributable_zvideo_campaigns

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/contributable_zvideo_campaigns` | — | a |

### 2.42 api.zhihu.com#creation-relationship

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `PUT` | `/creation-relationship/authorize` | — | a |
| `PUT` | `/creation-relationship/cancel` | Query: content_id, content_type | AnswerService, a |

### 2.43 api.zhihu.com#creator

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/creator/notification/content/{content_type}s/{content_id}?notification_type=answer_admire_could_open` | Path: content_id, content_type | m0 |
| `GET` | `/creator/popup/info/{content_type}s/{content_id}` | Path: content_id, content_type | m0 |
| `GET` | `/creator/publish/creation_tip` | Query: scene | PublishContainerService |
| `GET` | `/creator/publish/feedback` | Query: content_id, content_type | DbService |
| `GET` | `/creator/publish/feedback/v2` | Query: content_id, content_type | m0 |
| `PATCH` | `/creator/rights/1513324000` | — | m0 |

### 2.44 api.zhihu.com#creator_board

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/creator_board` | Query: mode | a |

### 2.45 api.zhihu.com#creators

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/creators/achievements/window` | — | e, g3 |
| `GET` | `/creators/domain` | — | m0 |
| `PUT` | `/creators/domain` | — | m0 |
| `DELETE` | `/creators/navigator/upvote` | Query: content_token, content_type | InteractiveService |
| `POST` | `/creators/navigator/upvote` | — | InteractiveService |
| `GET` | `/creators/personalized-question-tabs?page_source=invite` | — | a |
| `GET` | `/creators/personalized-questions/recommended` | Query: offset, page_source | QuestionService |
| `GET` | `/creators/personalized-questions/wait_answer/{topic_id}` | Path: topic_id; Query: offset | m0 |
| `GET` | `/creators/plus_panel/topic/recommend` | — | m0 |
| `GET` | `/creators/question_route/common_module` | Query: page_source | a |
| `GET` | `/creators/question_route/creation_interest_tab` | — | QuestionService |
| `GET` | `/creators/question_route/creation_preference/ciw` | — | QuestionService |
| `POST` | `/creators/question_route/creation_preference/ciw` | — | QuestionService |
| `GET` | `/creators/question_route/creation_preference/ciw_search` | Query: key_words | QuestionService |
| `POST` | `/creators/question_route/empty_answer_draft` | — | QuestionService |
| `GET` | `/creators/question_route/member_related/recommend?limit=4&page_source=panel` | Query: offset, recom_domain_score_ab | m0 |
| `GET` | `/creators/question_route/mine_related/topic?page_source=mine` | Query: offset, topic_id | QuestionService |
| `GET` | `/creators/rank/hot?period=day` | Query: domain, offset | m0 |
| `GET` | `/creators/rank/potential?sort_type=all` | Query: domain, offset | m0 |
| `GET` | `/creators/recent/domain` | Query: rank_type | m0 |
| `POST` | `/creators/task/circle/rewards/confirm` | — | ProfileService |
| `GET` | `/creators/topic-plaza/recommend` | Query: current, page_size, scene | m0 |

### 2.46 api.zhihu.com#cs

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/cs/api/v4/help_card/get` | Query: request_source, user_id | ChatService |
| `POST` | `/cs/api/v4/help_card/submit` | — | ChatService |

### 2.47 api.zhihu.com#customer_service

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/customer_service/choose_question_tag` | — | ChatService |
| `GET` | `/customer_service/question_tag` | — | ChatService |

### 2.48 api.zhihu.com#darwin

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/darwin/reviews` | — | a |
| `GET` | `/darwin/reviews/{review_id}` | Path: review_id; Query: sku_id | a |
| `PUT` | `/darwin/reviews/{review_id}` | Path: review_id | a |
| `GET` | `/darwin/sku_grading/{sku_id}` | Path: sku_id | a |
| `GET` | `/darwin/superstar/images` | Query: sku_id | f |

### 2.49 api.zhihu.com#details

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/details/recommend/{business_type}/{business_id}/list` | Path: business_id, business_type; Query: limit | a |

### 2.50 api.zhihu.com#drafts

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/drafts` | Query: limit, offset, publish_state | DraftService |

### 2.51 api.zhihu.com#drama-recommend

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/drama-recommend/drama/card-next` | Query: request_id, source, theater_id | DramaService |
| `GET` | `/drama-recommend/drama/home/choice` | Query: limit, offset, request_id, source | HomeLiveFeedService |

### 2.52 api.zhihu.com#drama

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/drama/account` | — | DramaService |
| `GET` | `/drama/actor/status` | — | DramaService, a |
| `GET` | `/drama/all-gifts` | — | DramaService |
| `GET` | `/drama/all-stickers` | — | b |
| `POST` | `/drama/auto-connect` | Field: connect_type, media_type, target_drama_id | a |
| `GET` | `/drama/category-tree` | — | DramaService |
| `GET` | `/drama/clips/{clip_id}` | Path: clip_id | DramaService |
| `POST` | `/drama/combos/{combo_id}/end` | Path: combo_id | DramaService |
| `POST` | `/drama/connections` | Field: camp_type, connect_type, media_type, position, self_drama_id, target_drama_id, target_member_id, theme | b |
| `PUT` | `/drama/connections/heartbeat` | Field: connection_ids, drama_id, is_first_time, is_open_camera, is_open_microphone | a, b |
| `DELETE` | `/drama/connections/{connection_id}/cancel` | Path: connection_id | b |
| `PUT` | `/drama/connections/{connection_id}/close` | Path: connection_id | a, b |
| `PUT` | `/drama/connections/{connection_id}/confirm` | Path: connection_id; Query: is_open_camera, is_open_microphone | b |
| `GET` | `/drama/connections/{connection_id}/message` | Path: connection_id | a, b |
| `PUT` | `/drama/connections/{connection_id}/permit` | Path: connection_id | b |
| `PUT` | `/drama/connections/{connection_id}/refuse` | Path: connection_id | b |
| `POST` | `/drama/create-drama` | Field: config_id, copy, drama_id, source | a |
| `GET` | `/drama/drama-tools` | Query: drama_id | DramaService |
| `POST` | `/drama/dramas` | Field: access_type, camps, category_id, cover_image, description, drama_activity_id, force, hotspot_id, live_id, orientation, show_infinity, showcase, stream_origin, theme, type, using_prepare_created_resource | b |
| `POST` | `/drama/dramas/{drama_id}/acquired-gifts` | Path: drama_id; Field: combo_id, gift_count, gift_id, nonce, receiver_id | DramaService |
| `GET` | `/drama/dramas/{drama_id}/actor-connections` | Path: drama_id; Query: limit, offset | b |
| `POST` | `/drama/dramas/{drama_id}/close` | Path: drama_id | a, b |
| `PUT` | `/drama/dramas/{drama_id}/connection-users` | Path: drama_id; Field: users | a |
| `PUT` | `/drama/dramas/{drama_id}/continue` | Path: drama_id; Field: source | a, b |
| `PUT` | `/drama/dramas/{drama_id}/eject/{hash_id}` | Path: drama_id, hash_id | DramaService |
| `GET` | `/drama/dramas/{drama_id}/explaining-commodity` | Path: drama_id | DramaService |
| `GET` | `/drama/dramas/{drama_id}/fast` | Path: drama_id | a |
| `GET` | `/drama/dramas/{drama_id}/follow-push-panel` | Path: drama_id | DramaService |
| `GET` | `/drama/dramas/{drama_id}/gift-records` | Path: drama_id; Query: limit, offset | b |
| `POST` | `/drama/dramas/{drama_id}/gifts` | Path: drama_id; Field: combo_id, gift_count, gift_id, nonce, receiver_id | DramaService |
| `POST` | `/drama/dramas/{drama_id}/heartbeat` | Path: drama_id | a, b |
| `GET` | `/drama/dramas/{drama_id}/heat-ranks` | Path: drama_id | DramaService |
| `POST` | `/drama/dramas/{drama_id}/interact/v2` | Path: drama_id; Field: is_end, like_count, like_total_count | DramaService |
| `GET` | `/drama/dramas/{drama_id}/lite` | Path: drama_id | a, b, f |
| `POST` | `/drama/dramas/{drama_id}/log` | Path: drama_id; Field: type | DramaService, a |
| `POST` | `/drama/dramas/{drama_id}/member_heartbeat` | Path: drama_id | a, b |
| `GET` | `/drama/dramas/{drama_id}/obs` | Path: drama_id | c |
| `POST` | `/drama/dramas/{drama_id}/polls` | Path: drama_id; Field: options, title | g |
| `GET` | `/drama/dramas/{drama_id}/polls/{poll_id}` | Path: drama_id, poll_id | g |
| `POST` | `/drama/dramas/{drama_id}/polls/{poll_id}/end` | Path: drama_id, poll_id | g |
| `POST` | `/drama/dramas/{drama_id}/polls/{poll_id}/vote` | Path: drama_id, poll_id; Field: option_ids | g |
| `PUT` | `/drama/dramas/{drama_id}/quiet/{hash_id}` | Path: drama_id, hash_id; Field: type | DramaService |
| `POST` | `/drama/dramas/{drama_id}/record-clip` | Path: drama_id; Field: delayed_duration, duration, type | DramaService |
| `POST` | `/drama/dramas/{drama_id}/red_packets/{red_packet_id}` | Path: drama_id, red_packet_id | d |
| `POST` | `/drama/dramas/{drama_id}/report-buy-commodity` | Path: drama_id; Field: commodity | DramaService |
| `POST` | `/drama/dramas/{drama_id}/send-follow-push` | Path: drama_id | DramaService |
| `POST` | `/drama/dramas/{drama_id}/share-callback` | Path: drama_id; Field: theater_id | DramaService |
| `POST` | `/drama/dramas/{drama_id}/start` | Path: drama_id | c |
| `PUT` | `/drama/dramas/{drama_id}/validate-connection` | Path: drama_id; Field: user_id | a |
| `GET` | `/drama/dramas/{drama_id}/visitor-connections` | Path: drama_id | b |
| `GET` | `/drama/dramas/{drama_id}/word-guide` | Path: drama_id | a, b |
| `GET` | `/drama/dramas/{drama_id}/{hash_id}/status` | Path: drama_id, hash_id | DramaService |
| `GET` | `/drama/duration-treasure-box/list` | — | DramaService |
| `POST` | `/drama/duration-treasure-boxs/{box_id}/open` | Path: box_id | DramaService |
| `POST` | `/drama/forecasts/apply/create` | Field: cover_image, start_at, theme | DramaService |
| `DELETE` | `/drama/forecasts/{forecast_id}` | Path: forecast_id | ForecastService |
| `GET` | `/drama/forecasts/{forecast_id}` | Path: forecast_id | ForecastService |
| `DELETE` | `/drama/forecasts/{forecast_id}/remind` | Path: forecast_id | ForecastService, a |
| `POST` | `/drama/forecasts/{forecast_id}/remind` | Path: forecast_id | ForecastService, a |
| `GET` | `/drama/gifts` | Query: drama_id | DramaService |
| `GET` | `/drama/global/config` | — | DramaService |
| `DELETE` | `/drama/global/{hash_id}` | Path: hash_id; Query: drama_id, type | DramaService |
| `PUT` | `/drama/global/{hash_id}` | Path: hash_id; Field: drama_id, type | DramaService |
| `GET` | `/drama/home/follow` | — | b |
| `GET` | `/drama/hot-drama-list` | — | TopStoryService |
| `GET` | `/drama/infinity-show?show_infinity=1` | — | b |
| `POST` | `/drama/log/errors` | Field: data | DramaService |
| `POST` | `/drama/log/stats` | Field: data, type | DramaService |
| `POST` | `/drama/member/batch-follow` | Field: drama_id, hash_ids, scene | DramaService |
| `GET` | `/drama/member/batch-get-connectors-info` | Query: drama_id, hash_ids | DramaService |
| `GET` | `/drama/member/config` | — | DramaService |
| `GET` | `/drama/member/follow-panel` | Query: drama_id | DramaService |
| `POST` | `/drama/members/{hash_id}/follow` | Path: hash_id; Field: theater_id | DramaService, f |
| `POST` | `/drama/mqtt/ping` | Field: foreground, mqtt_status, theater_id | DramaService, a |
| `POST` | `/drama/mqtt/pong` | Field: event_id, theater_id | DramaService, a |
| `POST` | `/drama/notification` | Field: drama_id, theater_id, type | e |
| `GET` | `/drama/people/{hash_id}` | Path: hash_id; Query: theater_id | b |
| `POST` | `/drama/prepare` | Query: cover_image, include, source, theme | b, f |
| `GET` | `/drama/preset-emojis` | — | a, b |
| `GET` | `/drama/receive-records` | — | b |
| `GET` | `/drama/recruit-activities` | — | DramaService |
| `GET` | `/drama/red_packets/{red_packet_id}` | Path: red_packet_id | d |
| `GET` | `/drama/resource/{resource_id}` | Path: resource_id; Query: extra_param | VideoXSquareService |
| `GET` | `/drama/send-records` | — | b |
| `GET` | `/drama/share-info` | Query: id, state | DramaService, e, f |
| `POST` | `/drama/slide-up` | Field: current_drama_id, next_drama_id | DramaService |
| `GET` | `/drama/statements/v2` | Query: drama_id | DramaService |
| `POST` | `/drama/statements/v2` | Field: content, drama_id | DramaService |
| `GET` | `/drama/theater/block-words` | — | DramaService |
| `POST` | `/drama/theater/block-words` | Field: text | DramaService |
| `DELETE` | `/drama/theater/block-words/{word_id}` | Path: word_id | DramaService |
| `GET` | `/drama/theater/{theater_id}/settings` | Path: theater_id | b |
| `PUT` | `/drama/theater/{theater_id}/settings` | Path: theater_id; Field: disable_auto_permit_conn, new_conn_apply | b |
| `POST` | `/drama/theaters` | Query: cover_image, include, source, theme | a |
| `GET` | `/drama/theaters/{theater_id}` | Path: theater_id; Query: drama_id | a, b |
| `GET` | `/drama/theaters/{theater_id}/actor-messages` | Path: theater_id | DramaService, a |
| `POST` | `/drama/theaters/{theater_id}/bullets` | Path: theater_id; Field: content, content_type, drama_id | DramaService, a |
| `GET` | `/drama/theaters/{theater_id}/config` | Path: theater_id | DramaService |
| `GET` | `/drama/theaters/{theater_id}/crucial-info` | Path: theater_id; Query: is_next, pre_stay_duration, source | DramaService |
| `GET` | `/drama/theaters/{theater_id}/forecast/list` | Path: theater_id | DramaService |
| `GET` | `/drama/theaters/{theater_id}/init-messages` | Path: theater_id; Query: limit | DramaService, a |
| `POST` | `/drama/theaters/{theater_id}/leave` | Path: theater_id; Query: on_drama_end | b |
| `GET` | `/drama/theaters/{theater_id}/lottery/info` | Path: theater_id | DramaService |
| `POST` | `/drama/theaters/{theater_id}/lottery/participant` | Path: theater_id | DramaService |
| `GET` | `/drama/theaters/{theater_id}/lottery/result` | Path: theater_id | DramaService |
| `POST` | `/drama/theaters/{theater_id}/lottery/save` | Path: theater_id; Field: award_count, award_name, strategy_id, task_id | DramaService |
| `POST` | `/drama/theaters/{theater_id}/lottery/start` | Path: theater_id; Field: award_count, award_name, strategy_id, task_id | DramaService |
| `GET` | `/drama/theaters/{theater_id}/lottery/starting_info` | Path: theater_id | DramaService |
| `GET` | `/drama/theaters/{theater_id}/lottery/winner` | Path: theater_id; Query: limit, offset | DramaService |
| `GET` | `/drama/theaters/{theater_id}/privilege` | Path: theater_id | DramaService |
| `GET` | `/drama/theaters/{theater_id}/recent-messages` | Path: theater_id; Query: limit | DramaService, a, f |
| `DELETE` | `/drama/theaters/{theater_id}/sticker` | Path: theater_id; Query: drama_id, id | b |
| `POST` | `/drama/theaters/{theater_id}/sticker` | Path: theater_id; Field: drama_id, position_x, position_y, sticker_id, text | b |
| `POST` | `/drama/theaters/{theater_id}/visit` | Path: theater_id; Query: source; Field: force | a, b |
| `GET` | `/drama/withdraw` | Query: channel_type, withdraw_amount | b |
| `POST` | `/drama/withdraw` | Field: channel_type, withdraw_amount | b |
| `GET` | `/drama/withdraw/page` | — | b |

### 2.53 api.zhihu.com#ecom

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/ecom/api/v1/city/{topicId}/header` | Path: topicId | h |
| `GET` | `/ecom/api/v1/city/{topicId}/hot_feed` | Path: topicId | h |
| `GET` | `/ecom/api/v1/city/{topicId}/qa_feed` | Path: topicId | h |
| `GET` | `/ecom/api/v1/city/{topicId}/tabs_feed` | Path: topicId; Query: tab_id | h |
| `GET` | `/ecom/api/v1/topic/{topicId}/content_feed` | Path: topicId; Query: sku_id, source | m |
| `GET` | `/ecom/api/v1/topic/{topicId}/header` | Path: topicId | DigitalProductService |
| `GET` | `/ecom/api/v1/topic/{topicId}/promotions` | Path: topicId | DigitalProductService |
| `GET` | `/ecom/api/v1/topic/{topicId}/sku_feed` | Path: topicId | m |
| `GET` | `/ecom/api/v1/topic/{topicId}/tags` | Path: topicId | DigitalProductService |
| `GET` | `/ecom/api/v1/topic/{topicId}/tags_feed` | Path: topicId; Query: tag_id | DigitalProductService |

### 2.54 api.zhihu.com#editor

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/editor/default-settings` | — | AnswerEditorService, DbService |
| `GET` | `/editor/material/sticker` | Query: type | a |
| `GET` | `/editor/material/sticker/search` | Query: keyword | a |
| `GET` | `/editor/material/sticker/tabs` | — | a |
| `GET` | `/editor/material/wordart` | — | a |

### 2.55 api.zhihu.com#education

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/education/audio/info` | — | b |
| `GET` | `/education/bottom/{sku_id}` | Path: sku_id | d |
| `GET` | `/education/calendar_remind/course/{course_id}/all_section` | Path: course_id | i |
| `GET` | `/education/calendar_remind/course/{course_id}/future_section` | Path: course_id | i |
| `GET` | `/education/checkout/prepay` | Query: sku_id | i |
| `GET` | `/education/course/{business_id}/playing_section` | Path: business_id | a |
| `POST` | `/education/course/{business_id}/playing_section/{section_id}` | Path: business_id, section_id | a |
| `GET` | `/education/course/{course_id}/rights` | Path: course_id | a |
| `GET` | `/education/detail_page/{training_id}/catalog` | Path: training_id; Query: limit, offset | a |
| `GET` | `/education/detail_page/{training_id}/header` | Path: training_id | a |
| `GET` | `/education/file/{file_id}` | Path: file_id | a |
| `POST` | `/education/form_filling` | — | a, d |
| `GET` | `/education/form_info` | Query: sku_id, style | d |
| `GET` | `/education/manuscript/{business_type}/{business_id}/section/{section_id}` | Path: business_id, business_type, section_id | b |
| `POST` | `/education/monitor` | — | b |
| `GET` | `/education/nps_questionnaire/join` | Query: course_id | a |
| `POST` | `/education/progress` | — | a |
| `POST` | `/education/promotion_activities/subscribemsg` | — | c |
| `GET` | `/education/section_detail_page/{section_id}/base_info` | Path: section_id; Query: group_id | a |
| `GET` | `/education/sku_detail_page/{sku_id}/bottom` | Path: sku_id | b, d |
| `GET` | `/education/sku_detail_page/{sku_id}/header` | Path: sku_id | a |
| `GET` | `/education/sku_detail_page/{sku_id}/series` | Path: sku_id | b |
| `GET` | `/education/sku_detail_page/{sku_id}/share` | Path: sku_id | a |
| `GET` | `/education/training/course/video_page/{course_id}/recommended_card` | Path: course_id | a |
| `GET` | `/education/training/courses/{course_id}/sections/{section_id}/safety_check` | Path: course_id, section_id | a |
| `GET` | `/education/training/live_room/{section_id}/announcement` | Path: section_id | a |
| `GET` | `/education/training/live_room/{section_id}/common_msg` | Path: section_id | a |
| `POST` | `/education/training/live_room/{section_id}/heat` | Path: section_id | a |
| `GET` | `/education/training/live_room/{section_id}/relation` | Path: section_id | a |
| `POST` | `/education/training/live_room/{section_id}/report` | Path: section_id; Query: type | a |
| `POST` | `/education/training/live_room/{section_id}/subscribe` | Path: section_id | NewMarketService, a |
| `POST` | `/education/training/live_room/{section_id}/unsubscribe` | Path: section_id | a |
| `POST` | `/education/training/safety/safety_sms_check` | — | a |
| `PUT` | `/education/training/safety/safety_sms_check` | — | a |
| `GET` | `/education/training/{business_id}/share` | Path: business_id | a |
| `GET` | `/education/training/{business_id}/training/share` | Path: business_id; Query: section_id | d |
| `GET` | `/education/training/{business_id}/{business_type}/share` | Path: business_id, business_type; Query: section_id | a, b |
| `GET` | `/education/training/{courseId}/share` | Path: courseId | a |
| `GET` | `/education/training/{course_id}/detail_page` | Path: course_id | a |
| `GET` | `/education/training/{course_id}/detail_page/catalog/chapter_list` | Path: course_id | a |
| `GET` | `/education/training/{course_id}/detail_page/catalog/section_list` | Path: course_id; Query: chapter_id, need_learn_progress, section_id | a |
| `GET` | `/education/training/{course_id}/detail_page/catalog/section_type` | Path: course_id | a |
| `GET` | `/education/training/{id}/video_page/catalog?resource_type=video` | Path: id; Query: after_id, before_id, include, limit | a |
| `GET` | `/education/training/{id}/video_page/detail` | Path: id | a |
| `GET` | `/education/training/{sku_id}/wechat_info` | Path: sku_id | a, c |
| `POST` | `/education/training/{sku_id}/wechat_info` | Path: sku_id | c |
| `POST` | `/education/training/{training_id}/sections/{section_id}/decr_audition` | Path: section_id, training_id | a |
| `GET` | `/education/training/{training_id}/sections/{section_id}/liveinfo` | Path: section_id, training_id; Query: team | a |
| `POST` | `/education/video/monitor` | — | a |
| `POST` | `/education/videos/info` | — | a |

### 2.56 api.zhihu.com#emoji

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/emoji/collect` | — | m |
| `GET` | `/emoji/info/{id}` | Path: id | m |
| `GET` | `/emoji/library/list` | Query: limit, offset | m |
| `POST` | `/emoji/upload` | — | EmoticonUploadService, m |
| `GET` | `/emoji/user/list` | Query: limit, offset | m |
| `POST` | `/emoji/user/remove` | — | m |

### 2.57 api.zhihu.com#entry

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/entry/mark` | — | a |
| `GET` | `/entry/tips` | — | a |

### 2.58 api.zhihu.com#episode

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/episode/panel` | Query: curr_content_id, curr_content_type | a |

### 2.59 api.zhihu.com#event-center

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/event-center/data` | Query: data_key | ReportService |
| `GET` | `/event-center/guide/pin` | — | k0 |
| `GET` | `/event-center/profile/icon` | — | ProfileService |

### 2.60 api.zhihu.com#event7d

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/event7d/status` | — | ActivityService |
| `POST` | `/event7d/upload` | — | ActivityService, SevenDayPunchCardService |

### 2.61 api.zhihu.com#feed-render

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/feed-render/recommend/teenage` | Query: limit, offset | HomeServices |

### 2.62 api.zhihu.com#feed-root

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/feed-root/block` | Query: keyword, scene_code | BlockKeywordsService, CreatorBlockKeywordsService |
| `GET` | `/feed-root/block` | Query: scene_code | BlockKeywordsService, CreatorBlockKeywordsService |
| `POST` | `/feed-root/block` | Field: content_token, content_type, keyword, scene_code | BlockKeywordsService, CreatorBlockKeywordsService |
| `GET` | `/feed-root/sections/cityList` | — | TopStoryService |
| `POST` | `/feed-root/sections/saveUserCity` | — | TopStoryService |
| `POST` | `/feed-root/sections/submit/v2` | Query: city | TopStoryService, m0 |
| `POST` | `/feed-root/submit` | Field: type, value | TopStoryService |

### 2.63 api.zhihu.com#feed

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/feed/render/recommend_interest/check` | Query: trigger_scene | q |
| `POST` | `/feed/render/recommend_interest/report` | — | q |
| `GET` | `/feed/render/revisit/tag_config` | — | g |
| `GET` | `/feed/render/tab/config` | Query: city | TopStoryService |

### 2.64 api.zhihu.com#feed_fringe

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/feed_fringe` | Query: content_token, need_fringe, source | TopStoryService |

### 2.65 api.zhihu.com#fringe

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/fringe` | — | TopStoryService |
| `GET` | `/fringe/ad` | — | PushAdService |
| `POST` | `/fringe/report` | — | TopStoryService |

### 2.66 api.zhihu.com#general

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/general/video/publish` | — | d |

### 2.67 api.zhihu.com#gift

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/gift/v1/gift` | Query: sku_id | StarService |
| `GET` | `/gift/v1/gift/{gift_id}/share_info` | Path: gift_id | StarService |

### 2.68 api.zhihu.com#growth

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/growth/log_print` | Query: link | KKReportService |

### 2.69 api.zhihu.com#growth_signal

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/growth_signal/guide/hobby` | — | k0 |
| `GET` | `/growth_signal/guide/reading` | — | b |
| `GET` | `/growth_signal/new_user/guides` | Query: guide_page | k0 |

### 2.70 api.zhihu.com#guest

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/guest/self` | — | ProfileService |

### 2.71 api.zhihu.com#guide_center

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/guide_center/strategy` | — | q |
| `POST` | `/guide_center/strategy/action_record` | — | q |
| `POST` | `/guide_center/strategy/record` | — | q |

### 2.72 api.zhihu.com#hot

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/hot/topics` | — | TopStoryService |

### 2.73 api.zhihu.com#image

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/image/private_url` | Query: scene, token, url | ImageService |
| `POST` | `/image/transmission/task` | — | a |
| `GET` | `/image/transmission/task/status` | Query: task_id | a |
| `POST` | `/image/transmission/task/status` | — | a |

### 2.74 api.zhihu.com#image_share

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/image_share/qrcode` | Query: back_color, content, fill_color, size | c |
| `GET` | `/image_share/status` | Query: content_type, url_token | LongImgShareService |

### 2.75 api.zhihu.com#image_viewer

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/image_viewer/extra` | — | ImageViewerService |

### 2.76 api.zhihu.com#images

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `PUT` | `/images/{image_id}/uploading_status` | Path: image_id | ImageService, a |

### 2.77 api.zhihu.com#invite

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `PUT` | `/invite/like-topics` | — | NotificationTopicService |
| `GET` | `/invite/like-topics/recommend` | — | NotificationTopicService |
| `GET` | `/invite/recent_invited` | Query: limit | a |

### 2.78 api.zhihu.com#km-indep-home-comm

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/km-indep-home-comm/audio/{well_id}/{section_id}/{scene_type}/danm` | Path: scene_type, section_id, well_id; Query: offset, tts_id | m |
| `POST` | `/km-indep-home-comm/audio/{well_id}/{section_id}/{scene_type}/danm` | Path: scene_type, section_id, well_id | m |
| `GET` | `/km-indep-home-comm/catalog/{well_id}` | Path: well_id; Query: after_id, before_id, formal_content, include_search_id, limit, need_boundary, scene | a, m |
| `GET` | `/km-indep-home-comm/convert/zcode` | Query: url | c, i |
| `DELETE` | `/km-indep-home-comm/member/book_shelf` | Query: book_list_id, property_type | ManuscriptCatalogService |
| `POST` | `/km-indep-home-comm/member/book_shelf` | — | ManuscriptCatalogService |
| `PATCH` | `/km-indep-home-comm/member/history` | — | NewMarketService |
| `DELETE` | `/km-indep-home-comm/member/like` | Query: id, type | m |
| `POST` | `/km-indep-home-comm/member/like` | — | m |
| `POST` | `/km-indep-home-comm/products/{business_id}/{business_type}/section/{section_id}/resource/v2` | Path: business_id, business_type, section_id | m |
| `GET` | `/km-indep-home-comm/products/{well_id}/{business_type}/section/{section_id}/fold_menu` | Path: business_type, section_id, well_id | m |
| `GET` | `/km-indep-home-comm/progress/{well_id}` | Path: well_id; Query: scene | a, m |
| `GET` | `/km-indep-home-comm/recommend/audio` | Query: section_id | m |
| `POST` | `/km-indep-home-comm/record/attach_info` | — | c, i |
| `GET` | `/km-indep-home-comm/remain-popup/detail` | Query: section_id | a |
| `GET` | `/km-indep-home-comm/truncate/download/info` | — | c |
| `GET` | `/km-indep-home-comm/vip_purchase/{well_id}/section/{section_id}/popup` | Path: section_id, well_id | m |
| `GET` | `/km-indep-home-comm/work/{work_id}/section_list` | Path: work_id | a |

### 2.79 api.zhihu.com#km-indep-home

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/km-indep-home/catalog/guide` | Query: transmission | ManuscriptCatalogService |
| `GET` | `/km-indep-home/catalog/{well_id}` | Path: well_id; Query: after_id, before_id, include_search_id, limit, need_boundary, scene | ManuscriptCatalogService |
| `GET` | `/km-indep-home/catalog/{well_id}/v2` | Path: well_id; Query: after_id, before_id, include_search_id, limit, need_boundary, source, transmission | ManuscriptCatalogService |
| `GET` | `/km-indep-home/free_limit_time/list` | Query: limit, section_id | ManuscriptCatalogService |
| `DELETE` | `/km-indep-home/member/like` | Query: id, type | a |
| `POST` | `/km-indep-home/member/like` | — | a |
| `GET` | `/km-indep-home/message/un_read` | — | k |
| `GET` | `/km-indep-home/products/{well_id}/{business_type}/section/{section_id}/ad` | Path: business_type, section_id, well_id | m |
| `POST` | `/km-indep-home/recommend/catalog` | — | ManuscriptCatalogService |
| `GET` | `/km-indep-home/recommend/tts/{well_id}/{section_id}/v1` | Path: section_id, well_id | m |
| `PATCH` | `/km-indep-home/resource/pre_load` | — | m |
| `GET` | `/km-indep-home/share/section/{well_id}/{section_id}` | Path: section_id, well_id; Query: product_type | m |
| `GET` | `/km-indep-home/vip_pin/details/{pinId}` | Path: pinId | a |
| `POST` | `/km-indep-home/zhihu_guide_action` | — | e |

### 2.80 api.zhihu.com#km-live-room

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/km-live-room/dressed/decoration/list` | — | a |

### 2.81 api.zhihu.com#km-ravenclaw

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/km-ravenclaw/act/{actId}/task` | Path: actId | c |
| `GET` | `/km-ravenclaw/jisuban_incentive_act/entrance` | — | c |
| `GET` | `/km-ravenclaw/report_issue` | Query: error_code, issue_type | a |
| `POST` | `/km-ravenclaw/task/finish` | — | c |
| `POST` | `/km-ravenclaw/task_platform/task_finish` | — | q, x |
| `GET` | `/km-ravenclaw/vip_purchase_buy_success/popup` | — | a |

### 2.82 api.zhihu.com#km-vip-zhihu-web

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/km-vip-zhihu-web/member/like_list` | Query: limit, offset | KMarketService |
| `POST` | `/km-vip-zhihu-web/vip_tab/material/use_frequency` | — | NewMarketService |
| `GET` | `/km-vip-zhihu-web/vip_tab/member/history_list` | Query: ids, type | NewMarketService |
| `DELETE` | `/km-vip-zhihu-web/vip_tab/member/like` | Query: id, type | NewMarketService |
| `POST` | `/km-vip-zhihu-web/vip_tab/member/like` | — | NewMarketService |
| `GET` | `/km-vip-zhihu-web/vip_tab/member/like_list` | Query: limit, offset, type | NewMarketService |
| `GET` | `/km-vip-zhihu-web/vip_tab/member/list_blank` | Query: limit, offset, refresh_type, tab | NewMarketService |
| `GET` | `/km-vip-zhihu-web/vip_tab/people/{hash_id}/merge_works` | Path: hash_id; Query: limit, offset, sort_type | a |
| `GET` | `/km-vip-zhihu-web/vip_tab/vip_pin/discover` | Query: clicked_pin, flow_type, limit, offset, refresh_type, sub_tab_ab_val | NewMarketService |
| `GET` | `/km-vip-zhihu-web/vip_tab/vip_pin/pop` | Query: token | NewMarketService |

### 2.83 api.zhihu.com#km_ad

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/km_ad/ad_order/create` | — | RewardOrderApi |
| `POST` | `/km_ad/ad_order/{ad_order_id}/commit` | Path: ad_order_id | RewardOrderApi |
| `POST` | `/km_ad/ad_order/{ad_order_id}/report` | Path: ad_order_id | RewardOrderApi |
| `GET` | `/km_ad/ad_order/{ad_order_id}/status` | Path: ad_order_id | RewardOrderApi |

### 2.84 api.zhihu.com#km_filter

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/km_filter/last_read/vip_tab` | — | NewMarketService |

### 2.85 api.zhihu.com#km_story

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/km_story/feed/section/touch` | — | a, u, w6 |
| `POST` | `/km_story/km_feed/feed_back_tip` | — | a |
| `POST` | `/km_story/km_feed/feed_back_v2` | — | a |
| `POST` | `/km_story/km_feed/last_read` | — | a |

### 2.86 api.zhihu.com#kmap

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/kmap/share_restore` | — | KmService |
| `GET` | `/kmap/vsj` | — | a |

### 2.87 api.zhihu.com#kmqa

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/kmqa/zvideo/{video_entity_id}/player` | Path: video_entity_id | d |

### 2.88 api.zhihu.com#knowledge_school

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/knowledge_school/courses/{course_id}/note_count` | Path: course_id; Query: course_type | a |
| `POST` | `/knowledge_school/courses/{course_id}/sections/{section_id}/notes` | Path: course_id, section_id | a |
| `GET` | `/knowledge_school/flow/card` | Query: course_id, entry_type, section_id | a |
| `GET` | `/knowledge_school/guide_download_config/activity/{course_id}` | Path: course_id | b |
| `GET` | `/knowledge_school/section/{business_id}/training/share` | Path: business_id; Query: edu_share_type, section_id | a |
| `GET` | `/knowledge_school/section/{business_id}/{business_type}/share` | Path: business_id, business_type; Query: edu_share_type, section_id | a |
| `GET` | `/knowledge_school/zh_tab/ai/categories` | — | a |
| `GET` | `/knowledge_school/zh_tab/ai/categories/{category_id}/feeds` | Path: category_id | a |

### 2.89 api.zhihu.com#kpb

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/kpb/virtual_order/{virtual_order_id}/status` | Path: virtual_order_id; Header: auth-xxx-user, no-auth | MockPayService |
| `POST` | `/kpb/wallet/proxy` | Header: auth-xxx-user, no-auth | MockPayService |

### 2.90 api.zhihu.com#kvip

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/kvip/content/videos/info` | — | a |
| `POST` | `/kvip/content/audio/info` | — | a |
| `GET` | `/kvip/content/common_simple/{business_type}/{business_id}/header` | Path: business_id, business_type | d |
| `GET` | `/kvip/content/products/ebook/{id}/section` | Path: id; Query: offset, order_by | a |
| `GET` | `/kvip/content/products/{business_type}/{businessId}/detail?resource_type=video` | Path: businessId, business_type | a |
| `GET` | `/kvip/content/products/{business_type}/{business_Id}/section` | Path: business_Id, business_type; Query: ab_default_value, after_id, before_id, fields, include, include_after_id, is_new_column, limit, mode, offset, order_by, public_status, resource_type, type, with_ab_param | a, b |
| `GET` | `/kvip/content/products/{business_type}/{business_id}/detail` | Path: business_id, business_type | a |
| `GET` | `/kvip/content/products/{business_type}/{business_id}/header` | Path: business_id, business_type | SkuHeaderApiV2 |
| `POST` | `/kvip/content/products/{business_type}/{business_id}/manuscript` | Path: business_id, business_type | KVipPdfService |
| `POST` | `/kvip/content/products/{business_type}/{business_id}/manuscript/download` | Path: business_id, business_type | KVipPdfService |
| `GET` | `/kvip/content/products/{business_type}/{business_id}/section/{section_id}/header` | Path: business_id, business_type, section_id; Query: catalog_id, catalog_type | a |
| `GET` | `/kvip/content/products/{business_type}/{business_id}/section?resource_type=audio` | Path: business_id, business_type; Query: ab_default_value, after_id, before_id, include, limit, with_ab_param | a |
| `POST` | `/kvip/content/videos/info` | — | a |
| `GET` | `/kvip/content/videos/plugin/{video_id}` | Path: video_id; Query: answer_token, business_id, business_type, section_id | a |
| `GET` | `/kvip/right/my_card` | — | MineKVipCardService |
| `GET` | `/kvip/right/sku/reversion_sku_ext` | Query: ad_extra, sku_id | a, b |
| `GET` | `/kvip/right/sku/reversion_sku_ext?scene=ebook_manuscript` | Query: sku_id | EBookService |

### 2.91 api.zhihu.com#lastread

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/lastread/touch` | Field: targets | LastReadServiceV2, c |
| `POST` | `/lastread/touch/v2` | Field: targets | LastReadServiceV2 |

### 2.92 api.zhihu.com#latest_contacts

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/latest_contacts` | — | ChatServiceCopy |

### 2.93 api.zhihu.com#lives

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/lives/alipay_params` | — | AlipayAuthService |
| `POST` | `/lives/people/self/deposit_balance` | Query: action | DepositService |
| `GET` | `/lives/people/{member_hash}/statistics` | Path: member_hash | LiveService |
| `GET` | `/lives/self/speaker_info` | — | AlipayAuthService |
| `POST` | `/lives/shares` | Field: message_id | LiveService4DetailPage |
| `POST` | `/lives/sms_code/send` | Field: phone_no | AlipayAuthService |
| `POST` | `/lives/sms_code/validate` | Field: auth_code, phone_no | AlipayAuthService |
| `POST` | `/lives/speakers/self/bind-alipay` | Field: alipay_auth_code, alipay_user_id | AlipayAuthService |
| `POST` | `/lives/speakers/self/unbind-alipay` | — | AlipayAuthService |
| `POST` | `/lives/speakers/self/validate` | Field: cert_no, display_name | AlipayAuthService |
| `GET` | `/lives/{id}` | Path: id | LiveService4DetailPage, a |
| `POST` | `/lives/{id}/like` | Path: id | PushOtherService |
| `GET` | `/lives/{live_id}` | Path: live_id | b0 |
| `GET` | `/lives/{live_id}/reactions` | Path: live_id | a |

### 2.94 api.zhihu.com#log_collect

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/log_collect/analysis` | — | AdAnalysisService |

### 2.95 api.zhihu.com#market

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/market/activity/1221/consumption/header` | — | ActivitiesService |
| `GET` | `/market/activity/1221/consumption/list` | Query: limit, offset | ActivitiesService |
| `GET` | `/market/annotations/{annotation_id}/notes` | Path: annotation_id | EBookService |
| `PUT` | `/market/associator/learn_time` | — | KMLearnTimeService |
| `POST` | `/market/audio/played/notify` | — | MarketService |
| `GET` | `/market/certificates` | — | KMPersonalService, b |
| `GET` | `/market/comments/rights` | Query: resource_id, resource_type, section_id | KmService |
| `POST` | `/market/content/{sku_id}/section/{chapter_id}/annotations` | Path: chapter_id, sku_id | EBookService |
| `POST` | `/market/learning_list/delete` | — | KMarketService |
| `GET` | `/market/paid_answers/paid_video` | Query: resource_id, section_id | d |
| `GET` | `/market/people/self?with_fields=is_new` | — | MarketService, a |
| `GET` | `/market/people/{hash_id}/intro` | Path: hash_id | KMarketService |
| `GET` | `/market/people/{hash_id}/statistics` | Path: hash_id | KmService |
| `GET` | `/market/playlist?player=audio` | Query: biz_id, biz_type | b0 |
| `GET` | `/market/popovers_v2` | — | KMarketService |
| `POST` | `/market/popovers_v2/{id}` | Path: id | KMarketService |
| `GET` | `/market/public_annotation/{public_id}/notes` | Path: public_id | EBookService |
| `GET` | `/market/share/templates` | Query: type | EBookService |
| `POST` | `/market/share/templates` | — | EBookService |
| `GET` | `/market/sp_magazine/{combine_id}/header` | Path: combine_id | f |
| `GET` | `/market/svip_note/{type}/{id}` | Path: id, type | KmCommonService, KmService |
| `GET` | `/market/switch/vip_release_subscriber` | — | KMPersonalService |
| `POST` | `/market/switch/vip_release_subscriber` | Field: is_on, switch_name | KMPersonalService |
| `GET` | `/market/updating_header` | — | KMarketService |
| `GET` | `/market/vip_popover/release_notification` | Query: sku_id | KMPersonalService |
| `POST` | `/market/vip_popover/release_notification` | — | KMPersonalService |

### 2.96 api.zhihu.com#materials

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/materials/{scene}/folders` | Path: scene; Query: material_type, type | CommunityEditorService2 |
| `GET` | `/materials/{scene}/folders/{folder_id}/search` | Path: folder_id, scene; Query: keyword, limit, source_id, source_type | CommunityEditorService2 |
| `POST` | `/materials/{scene}/recently-materials` | Path: scene | CommunityEditorService2 |
| `GET` | `/materials/{scene}/search` | Path: scene; Query: keyword, limit, offset | CommunityEditorService2 |

### 2.97 api.zhihu.com#me

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/me/guides` | — | GrowTipService |
| `GET` | `/me/guides/extra/creator_share` | Query: token, type | ContentGuideService |
| `GET` | `/me/guides/extra/push_info` | — | PushGuideService |
| `GET` | `/me/guides/extra/push_old_info` | — | PushGuideService |
| `GET` | `/me/operation_guides/v3/extra` | Query: scenes | PushYearPostDBService, o, p |
| `DELETE` | `/me/operation_guides/v3/{session_id}` | Path: session_id | PushYearPostDBService, o, p |
| `DELETE` | `/me/operation_guides/{OperationGuideId}` | Path: OperationGuideId; Query: attach_info | GrowTipService |

### 2.98 api.zhihu.com#member

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/member/guides/v5/tag` | Query: ab_value, select_type | k0 |
| `DELETE` | `/member/medal/exposed` | — | ProfileService |
| `PUT` | `/member/medal/exposed` | — | ProfileService |
| `POST` | `/member/medal/switch` | Field: key, value | ProfileService |

### 2.99 api.zhihu.com#members

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/members/{hash_id_or_token}/medal_windows` | Path: hash_id_or_token; Query: medalId, source | ProfileService |
| `POST` | `/members/{hash_id_or_token}/medal_windows_callback` | Path: hash_id_or_token; Field: medalId, source | ProfileService |
| `GET` | `/members/{id}/zvideos` | Path: id; Query: include, similar_aggregation | VEProfileService |
| `GET` | `/members/{member_id}/topics/{topic_id}/creations` | Path: member_id, topic_id; Query: sort_by | MembersService |
| `GET` | `/members/{urlToken}/marked-answers` | Path: urlToken; Query: offset, order_by, per_page | AnswerService, ProfileService |
| `GET` | `/members/{urlToken}/owned-columns` | Path: urlToken; Query: id, type | AnswerEditorService, CommunityEditorService2, DbService, PublishContainerService, d |
| `GET` | `/members/{urlToken}/relations/common_mutuals` | Path: urlToken; Query: offset, per_page | ProfileService |
| `GET` | `/members/{urlToken}/relations/mutuals` | Path: urlToken; Query: offset, per_page | ProfileService |

### 2.100 api.zhihu.com#message-push

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/message-push/event` | — | PushGuideService |

### 2.101 api.zhihu.com#messages

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/messages` | Field: content, content_type, image, receiver_id, reply_source, source_id, source_type, sticker | ChatService |
| `POST` | `/messages/actions/cancel` | Field: message_id | ChatService |
| `POST` | `/messages/actions/mark-as-read` | — | ChatService |
| `POST` | `/messages/batch_delete` | Field: message_tokens | ChatService |
| `GET` | `/messages/user/{hash_id}` | Path: hash_id | ChatService |
| `DELETE` | `/messages/{message_id}` | Path: message_id | ChatService |
| `POST` | `/messages/{message_id}/evaluation` | Path: message_id | ChatService |

### 2.102 api.zhihu.com#messages?limit=20

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/messages?limit=20` | Query: after_id, before_id, client_scene, sender_id | ChatService |

### 2.103 api.zhihu.com#misc

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/misc/business` | — | ProfileService |

### 2.104 api.zhihu.com#modular

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/modular/metrics/report` | — | a |

### 2.105 api.zhihu.com#moments

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/moments/activity` | Query: item_brief | OriginalCardService |
| `GET` | `/moments/follow_widget` | Query: auto_refresh | f |
| `POST` | `/moments/lastread` | Field: targets | FollowLastReadServiceV2, LastReadServiceV2 |
| `POST` | `/moments/recent/display` | — | FollowTopService |
| `DELETE` | `/moments/recent/people/{member_id}/top` | Path: member_id | RecentTopService |
| `POST` | `/moments/recent/people/{member_id}/top` | Path: member_id | RecentTopService |
| `GET` | `/moments/recent/people/{url_token}/top` | Path: url_token | FollowTopService, RecentTopService |
| `POST` | `/moments/recent/read` | Query: brief | FollowTopService |
| `GET` | `/moments/recent/{type}/{member_id}/activities` | Path: member_id, type | FollowTopService |
| `DELETE` | `/moments/recent/{type}/{member_id}/top` | Path: member_id, type | FollowTopService |
| `POST` | `/moments/recent/{type}/{member_id}/top` | Path: member_id, type | FollowTopService |
| `GET` | `/moments/recent?type=raw` | — | FollowTopService |
| `GET` | `/moments/tab_v2` | Query: ab_param, feed_type, update_time | FollowService, MomentsService |
| `POST` | `/moments/uninterest` | Field: item_brief | OriginalCardService |
| `POST` | `/moments/uninterest_user` | Field: member_id | FollowRecommendUserService, OriginalCardService, ProfileService |
| `GET` | `/moments/{member_id}/origin` | Path: member_id; Query: limit, sort, source_content_id, source_content_type; Header: need_debug | ProfileService |
| `GET` | `/moments/{member_id}/vote` | Path: member_id; Query: limit; Header: need_debug | ProfileService |

### 2.106 api.zhihu.com#moments_v3

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/moments_v3` | Query: feed_type; Header: X-Moments-Ab-Param, need_debug | FollowService |

### 2.107 api.zhihu.com#mpush-go

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/mpush-go/click` | Field: url | PushPlatformService |
| `PUT` | `/mpush-go/provider` | Field: device_udid, is_valid, op, provider_name, provider_token | f |
| `PUT` | `/mpush-go/switch` | Field: is_valid | f |

### 2.108 api.zhihu.com#mqtt

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/mqtt/auth` | — | MqttAuthService |

### 2.109 api.zhihu.com#negative-feedback

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/negative-feedback/panel` | Query: content_token, content_type, scene_code | m |

### 2.110 api.zhihu.com#news_specials

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/news_specials/{id}/followers` | Path: id | FeedKmCardService |
| `POST` | `/news_specials/{id}/followers` | Path: id | FeedKmCardService |

### 2.111 api.zhihu.com#next

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/next` | Query: collection_id, collection_type, id, scenes, type | a |

### 2.112 api.zhihu.com#next-render

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/next-render` | Header: x-ad-styles | a, d |

### 2.113 api.zhihu.com#nlives

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/nlives/lives/{live_id}/typing` | Path: live_id | a |
| `POST` | `/nlives/lives/attachments` | — | a |
| `POST` | `/nlives/lives/{live_id}/ban_slide/{slide_id}` | Path: live_id, slide_id | a |
| `POST` | `/nlives/lives/{live_id}/chapters` | Path: live_id | a |
| `PUT` | `/nlives/lives/{live_id}/chapters/orders` | Path: live_id | a |
| `PUT` | `/nlives/lives/{live_id}/chapters/{chapter_id}` | Path: chapter_id, live_id | a |
| `GET` | `/nlives/lives/{live_id}/chapters/{chapter_id}/slides` | Path: chapter_id, live_id; Query: check_audio | a |
| `POST` | `/nlives/lives/{live_id}/chapters/{chapter_id}/slides` | Path: chapter_id, live_id | a |
| `PUT` | `/nlives/lives/{live_id}/chapters/{chapter_id}/slides/orders` | Path: chapter_id, live_id | a |
| `PUT` | `/nlives/lives/{live_id}/chapters/{chapter_id}/slides/{slide_id}` | Path: chapter_id, live_id, slide_id | a |
| `POST` | `/nlives/lives/{live_id}/chapters/{chapter_id}/slides/{slide_id}/messages` | Path: chapter_id, live_id, slide_id | a |
| `POST` | `/nlives/lives/{live_id}/chapters/{chapter_id}/slides/{slide_id}/prerecord_messages` | Path: chapter_id, live_id, slide_id | a |
| `GET` | `/nlives/lives/{live_id}/chapters_info` | Path: live_id; Query: type | a |
| `GET` | `/nlives/lives/{live_id}/chatroom_pipe` | Path: live_id; Query: conv_type | a |
| `POST` | `/nlives/lives/{live_id}/clap` | Path: live_id | a |
| `POST` | `/nlives/lives/{live_id}/enter_chatroom` | Path: live_id | a |
| `GET` | `/nlives/lives/{live_id}/messages` | Path: live_id; Query: after_id, before_id, limit, message_type, mode | a |
| `POST` | `/nlives/lives/{live_id}/messages` | Path: live_id | a |
| `POST` | `/nlives/lives/{live_id}/messages/{message_id}` | Path: live_id, message_id; Query: action | a |
| `POST` | `/nlives/lives/{live_id}/messages/{message_id}/agree` | Path: live_id, message_id | a |
| `POST` | `/nlives/lives/{live_id}/messages/{message_id}/played` | Path: live_id, message_id | a |
| `POST` | `/nlives/lives/{live_id}/messages/{message_id}/reply` | Path: live_id, message_id | a |
| `GET` | `/nlives/lives/{live_id}/prerecord_messages` | Path: live_id; Query: after_id, before_id, limit | a |
| `DELETE` | `/nlives/lives/{live_id}/prerecord_messages/{message_id}` | Path: live_id, message_id | a |
| `PUT` | `/nlives/lives/{live_id}/prerecord_messages/{message_id}` | Path: live_id, message_id | a |
| `GET` | `/nlives/lives/{live_id}/qa_messages` | Path: live_id; Query: after_id, before_id, limit, message_type, mode | a |
| `GET` | `/nlives/lives/{live_id}/room` | Path: live_id | a |
| `PUT` | `/nlives/lives/{live_id}/room_status` | Path: live_id | a |
| `GET` | `/nlives/lives/{live_id}/simple` | Path: live_id | LiveService4DetailPage |
| `GET` | `/nlives/lives/{live_id}/slides/{slide_id}/prerecord_messages` | Path: live_id, slide_id; Query: after_id, before_id, limit | a |
| `POST` | `/nlives/lives/{live_id}/switch_slide` | Path: live_id | a |

### 2.114 api.zhihu.com#notifications

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/notifications/mark` | Field: action, notification_id, send_at, timestamp, type | NotificationService, PushPlatformService |
| `GET` | `/notifications/timeline/{urlToken}/actors` | Path: urlToken; Query: limit, offset | NotificationService |
| `GET` | `/notifications/types` | — | g |
| `GET` | `/notifications/v2/timeline/{urlToken}/actors` | Path: urlToken; Query: limit, offset | NotificationService |
| `GET` | `/notifications/v3/count/v3` | — | g |
| `POST` | `/notifications/v3/message/draft/{myId_oppositeId}` | Path: myId_oppositeId | NotificationService |
| `POST` | `/notifications/v3/message/mute/{admin_token}` | Path: admin_token | NotificationServiceV3 |
| `POST` | `/notifications/v3/message/readall` | — | NotificationServiceV3 |
| `DELETE` | `/notifications/v3/object/{id}` | Path: id | NotificationServiceV3 |
| `POST` | `/notifications/v3/object/{id}` | Path: id; Query: value | NotificationServiceV3 |
| `PUT` | `/notifications/v3/object/{id}/top` | Path: id; Field: on_top | NotificationServiceV3 |
| `DELETE` | `/notifications/v3/object/{urlToken}` | Path: urlToken | EntryNotificationService |
| `GET` | `/notifications/v3/timeline/entry/invite` | Query: enable_modular, invite_with_time_slice, limit | NotificationServiceV3 |
| `POST` | `/notifications/v3/timeline/entry/{entryName}/actions/readall` | Path: entryName | EntryNotificationService |
| `GET` | `/notifications/v3/timeline/entry/{entry_name}?limit=20&adr_com=5` | Path: entry_name; Query: filter_type | EntryNotificationService |
| `GET` | `/notifications/v3/timeline/{urlToken}/actors` | Path: urlToken; Query: limit, offset | NotificationServiceV3 |
| `GET` | `/notifications/v3/timeline/{urlToken}/actors_v2` | Path: urlToken | EntryNotificationService |
| `GET` | `/notifications/{notification_id}/people` | Path: notification_id; Query: offset | NotificationService |

### 2.115 api.zhihu.com#ogv

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/ogv/zvideo/{id}` | Path: id | a |

### 2.116 api.zhihu.com#open_chat_box

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/open_chat_box` | — | ChatService |

### 2.117 api.zhihu.com#order

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/order/purchase` | — | CashierService |
| `GET` | `/order/recharge/products` | Query: required_amount, source | CashierService |
| `GET` | `/order/shopping` | Query: sku_id, source, start_point | CashierService |
| `POST` | `/order/v1/auto-purchase/config` | — | a |
| `POST` | `/order/v1/checkout` | — | a, l |
| `GET` | `/order/v1/checkout/{deal_id}` | Path: deal_id | a, l |
| `POST` | `/order/v1/deal` | — | TradeService |
| `GET` | `/order/v1/delivery/status` | Query: deal_id | SkuOrderService, a |
| `POST` | `/order/v1/playlet/coin/recharge/panel` | — | m |
| `POST` | `/order/v1/purchase` | — | SkuOrderService |
| `POST` | `/order/v1/purchase/{deal_id}` | Path: deal_id | SkuOrderService, a |
| `GET` | `/order/v1/recharge/products` | Query: product_type, required_amount, source, wallet_id | CashierService, CoinService |
| `GET` | `/order/v1/settlement/{settlement_id}` | Path: settlement_id | g |
| `POST` | `/order/v1/settlement/{settlement_id}` | Path: settlement_id | g |
| `POST` | `/order/v1/trade/deal` | — | TradeService |
| `GET` | `/order/v2/gift/total-income` | Query: platform, revenue_account_type, version, wallet_id | WalletService |

### 2.118 api.zhihu.com#people

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/people/account/list` | — | o1 |
| `POST` | `/people/follow_and_join` | — | ProfileService |
| `PUT` | `/people/homepage_entry/bubble` | — | ProfileService |
| `GET` | `/people/homepage_entry_v2` | — | ProfileService |
| `GET` | `/people/homepage_mine_icon` | — | ProfileService |
| `GET` | `/people/profile/recommend` | Query: limit, offset, scene | ProfileService |
| `GET` | `/people/self` | Header: Authorization, x-app-id | AccountService, ProfileService, ZhiHuLabService, a, o1 |
| `PUT` | `/people/self` | Field: cover_hash, verify_ids | ProfileService, ZhiHuLabService, u0 |
| `GET` | `/people/self/activity_blocked_followees` | Query: limit, offset | ProfileService |
| `POST` | `/people/self/activity_blocked_followees` | — | OriginalCardService, ProfileService |
| `DELETE` | `/people/self/activity_blocked_followees/{follow_id}` | Path: follow_id | ProfileService |
| `DELETE` | `/people/self/activity_blocked_followees/{url_token}` | Path: url_token | OriginalCardService |
| `POST` | `/people/self/avatar` | Query: avatar_url; Field: avatar_url; Header: Authorization | a, u0 |
| `GET` | `/people/self/drafts_count` | — | DbService, ProfileService, QuestionService, m0 |
| `GET` | `/people/self/followees/batch` | Query: limit | a |
| `PUT` | `/people/self/goodat_topics` | — | QuestionService |
| `GET` | `/people/self/goodat_topics/recommended` | — | QuestionService |
| `GET` | `/people/self/goodat_topics/recommended?limit=60` | — | a |
| `GET` | `/people/self/goodat_topics/recommended?with_top_topics=1` | — | QuestionService |
| `POST` | `/people/self/goodat_topics/{topic_id}` | Path: topic_id | QuestionService |
| `PUT` | `/people/self/profile_v2` | Field: educations, employments, locations | ProfileService, a |
| `GET` | `/people/self/qrcode/background` | — | ShareQrService |
| `GET` | `/people/self/question_invitations` | Query: limit, offset | QuestionService |
| `GET` | `/people/self/rename_status` | — | ProfileService |
| `PUT` | `/people/self/settings` | Field: type, value | ProfileService |
| `GET` | `/people/self/sticker-groups` | — | StickerService |
| `GET` | `/people/self/sticker-groups/v2` | — | StickerService |
| `GET` | `/people/self/switches` | Query: include | ProfileService, ZhuanlanProfileService |
| `GET` | `/people/self/user_status` | Query: keys | ZhiHuLabService |
| `POST` | `/people/self/user_status` | Field: key, value | ZhiHuLabService |
| `DELETE` | `/people/toppings` | Query: action_type, content_token, content_type | OriginalCardService, ProfileService, ZhuanlanProfileService, c |
| `POST` | `/people/toppings` | — | OriginalCardService, ProfileService, ZhuanlanProfileService, c |
| `DELETE` | `/people/{follow_member_id}/followers/{member_id}` | Path: follow_member_id, member_id | NewProfileService, ProfileService, ProfileServiceCopy, TopicService, q0 |
| `POST` | `/people/{hash_id}/congratulator` | Path: hash_id | ProfileService |
| `GET` | `/people/{hash_id}/guidance_task/detail` | Path: hash_id | ProfileService |
| `GET` | `/people/{hash_id}/profile` | Path: hash_id; Query: has_contacts_permission, is_preview, profile_new_version, profile_v4, recommend_ab, scene | ProfileService |
| `GET` | `/people/{hash_id}/profile/detail` | Path: hash_id; Query: profile_new_version | ProfileService |
| `GET` | `/people/{hash_id}/profile/tab/more` | Path: hash_id; Query: tab_type | ProfileService |
| `GET` | `/people/{id}/followees` | Path: id | SearchPeopleService |
| `GET` | `/people/{id}/share` | Path: id | ShareService |
| `GET` | `/people/{member_id}` | Path: member_id | NewProfileService, ProfileService |
| `GET` | `/people/{member_id}/answers` | Path: member_id; Query: limit, offset, order_by | ProfileService |
| `GET` | `/people/{member_id}/articles` | Path: member_id; Query: limit, offset, sort_by | ProfileService, ZhuanlanProfileService, k |
| `GET` | `/people/{member_id}/collection_contents` | Path: member_id; Query: limit, offset; Header: za-spm | a |
| `GET` | `/people/{member_id}/collections_v2` | Path: member_id; Query: limit, offset | ProfileService, e, h |
| `GET` | `/people/{member_id}/columns` | Path: member_id; Query: limit, offset | ProfileService, ZhuanlanProfileService |
| `GET` | `/people/{member_id}/followees` | Path: member_id; Query: offset | ProfileService, ProfileServiceCopy2 |
| `GET` | `/people/{member_id}/followers` | Path: member_id; Query: offset | ProfileService |
| `POST` | `/people/{member_id}/followers` | Path: member_id | NewProfileService, ProfileService, ProfileServiceCopy, TopicService, q0 |
| `GET` | `/people/{member_id}/following_collections` | Path: member_id; Query: offset | ProfileService |
| `GET` | `/people/{member_id}/following_columns` | Path: member_id; Query: limit, offset | ProfileService, ZhuanlanProfileService |
| `GET` | `/people/{member_id}/following_news_specials` | Path: member_id; Query: offset | ProfileService |
| `GET` | `/people/{member_id}/following_questions` | Path: member_id; Query: offset | ProfileService |
| `GET` | `/people/{member_id}/following_roundtables` | Path: member_id; Query: offset | ProfileService |
| `GET` | `/people/{member_id}/following_topics` | Path: member_id; Query: offset | ProfileService |
| `GET` | `/people/{member_id}/included-articles` | Path: member_id; Query: limit, offset, sort_by | ZhuanlanArticleService |
| `GET` | `/people/{member_id}/is_following` | Path: member_id | NewProfileService, ProfileService, e |
| `GET` | `/people/{member_id}/lives` | Path: member_id; Query: offset | LiveService |
| `GET` | `/people/{member_id}/questions` | Path: member_id; Query: limit, offset | ProfileService |
| `GET` | `/people/{member_id}/relation/{type}` | Path: member_id, type; Query: action | ProfileSocialService |
| `GET` | `/people/{member_id}/similarity` | Path: member_id; Query: profile_new_version, profile_v4, recommend_ab, source | ProfileService |
| `GET` | `/people/{member_id}/topic/{topic_id}/answers` | Path: member_id, topic_id; Query: offset, order_by | ProfileService |
| `POST` | `/people/{people_id}/followers` | Path: people_id; Header: za-spm | InteractiveService |
| `DELETE` | `/people/{people_id}/followers/{cur_people_id}` | Path: cur_people_id, people_id; Header: za-spm | InteractiveService |
| `GET` | `/people/{people_id}/is_blocked` | Path: people_id | ProfileService |
| `GET` | `/people/{people_id}/profile/tab` | Path: people_id; Query: scene, source_id, source_type | a |
| `GET` | `/people/{urlToken}/profile/creations/feed?type=article&limit=10` | Path: urlToken; Query: offset | ColumnService |

### 2.119 api.zhihu.com#personalized-questions

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/personalized-questions/latest` | Query: offset | QuestionService |
| `DELETE` | `/personalized-questions/{question_token}` | Path: question_token | QuestionService, a, m0 |

### 2.120 api.zhihu.com#personalized_question

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/personalized_question/goodat_topics/{topic_id}` | Path: topic_id | ComposeAnswerService, SearchComponentService |
| `POST` | `/personalized_question/goodat_topics/{topic_id}` | Path: topic_id | ComposeAnswerService, SearchComponentService |

### 2.121 api.zhihu.com#pins

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/pins/{pin_id}/reactions` | Path: pin_id | InteractiveService, g |
| `POST` | `/pins/{pin_id}/reactions` | Path: pin_id; Field: type | InteractiveService, g |

### 2.122 api.zhihu.com#pluton

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/pluton/annotation/{business_type}/{business_id}/{section_id}` | Path: business_id, business_type, section_id | EBookService |
| `GET` | `/pluton/annotation_summary/annotation/timeline` | — | EBookService |
| `GET` | `/pluton/annotation_summary/note/timeline` | — | EBookService |
| `GET` | `/pluton/annotation_summary/product` | — | EBookService |
| `POST` | `/pluton/audio/info` | — | b0 |
| `POST` | `/pluton/book_list/0/info` | — | KMarketService |
| `GET` | `/pluton/book_list/list` | Query: limit, offset, type | KMarketService |
| `DELETE` | `/pluton/book_list/{book_list_id}/collect` | Path: book_list_id | a |
| `POST` | `/pluton/book_list/{book_list_id}/collect` | Path: book_list_id | a |
| `DELETE` | `/pluton/book_list/{book_list_id}/info` | Path: book_list_id | KMarketService |
| `GET` | `/pluton/book_list/{book_list_id}/info` | Path: book_list_id | KMarketService |
| `PUT` | `/pluton/book_list/{book_list_id}/info` | Path: book_list_id | KMarketService |
| `GET` | `/pluton/book_list/{book_list_id}/search_book` | Path: book_list_id; Query: limit, offset, title | KMarketService |
| `GET` | `/pluton/bookmark` | Query: last_updated, sku_id | EBookService |
| `POST` | `/pluton/bookmark` | — | EBookService |
| `GET` | `/pluton/category/story/header` | — | a |
| `GET` | `/pluton/comment_type` | Query: section_id, sku_id | b |
| `GET` | `/pluton/member_config` | — | a |
| `GET` | `/pluton/member_config/favor_labels` | — | NewMarketService |
| `PUT` | `/pluton/member_config/favor_labels` | — | NewMarketService |
| `GET` | `/pluton/products/{book_id}/ebook/share` | Path: book_id | EBookService, c |
| `GET` | `/pluton/products/{business_id}/{business_type}/header` | Path: business_id, business_type | f |
| `GET` | `/pluton/products/{business_id}/{business_type}/photos_and_videos` | Path: business_id, business_type | a |
| `GET` | `/pluton/products/{business_id}/{business_type}/section/{section_id}/header` | Path: business_id, business_type, section_id; Query: catalog_id, catalog_type, request_source | a, c |
| `GET` | `/pluton/products/{business_id}/{business_type}/share` | Path: business_id, business_type; Query: activity_key, marketing_token, section_id, task_id | KmService, a, b0, o |
| `GET` | `/pluton/products/{business_type}/{business_id}/header` | Path: business_id, business_type | SkuHeaderApiV2 |
| `GET` | `/pluton/products/{id}/{type}/detail` | Path: id, type; Query: resource_type | KmService, a, b0 |
| `GET` | `/pluton/products/{id}/{type}/detail?resource_type=video` | Path: id, type | a |
| `GET` | `/pluton/products/{id}/{type}/section` | Path: id, type; Query: ab_default_value, after_id, before_id, include, limit, mode, order_by, public_status, resource_type, with_ab_param | a, b, q1 |
| `GET` | `/pluton/products/{id}/{type}/section?resource_type=audio` | Path: id, type; Query: ab_default_value, after_id, before_id, include, limit, with_ab_param | b0 |
| `GET` | `/pluton/products/{id}/{type}/section?resource_type=video&public_status=public,svip_public` | Path: id, type; Query: after_id, before_id, include, limit | a |
| `POST` | `/pluton/section/resource` | — | b |
| `POST` | `/pluton/shelf/batch` | — | NewMarketService |
| `GET` | `/pluton/shelf/toast` | — | KMarketService |
| `DELETE` | `/pluton/shelves` | — | KMarketService, a, f, q5 |
| `GET` | `/pluton/shelves` | Query: learn_progress, offset, order_by, property_type, sku_name | KMarketService |
| `POST` | `/pluton/shelves` | — | a, f, q5 |
| `PUT` | `/pluton/shelves` | — | KMarketService, b |
| `POST` | `/pluton/shelves/reservation` | — | a |
| `PUT` | `/pluton/shelves/top` | — | KMarketService |
| `POST` | `/pluton/shelves/update_status` | — | KMarketService |
| `GET` | `/pluton/sku/{sku_id}/{business_type}/{business_id}/annotation` | Path: business_id, business_type, sku_id | EBookService |
| `GET` | `/pluton/sku/{sku_id}/{business_type}/{business_id}/note` | Path: business_id, business_type, sku_id | EBookService |
| `GET` | `/pluton/skus/{sku_id}/header` | Path: sku_id | f |
| `POST` | `/pluton/skus/{sku_id}/set_on_shelf_remind` | Path: sku_id | a |
| `GET` | `/pluton/topics/{topic_id}/binding_sku` | Path: topic_id | TopicService |
| `POST` | `/pluton/videos/info` | — | a, b |
| `GET` | `/pluton/videos/plugin/{video_id}` | Path: video_id; Query: business_id, business_type, section_id | d |

### 2.123 api.zhihu.com#podcast

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/podcast/player/play/{content_type}/{content_token}` | Path: content_token, content_type | a |
| `GET` | `/podcast/player/recommend` | Query: limit | a |
| `GET` | `/podcast/player/{content_type}/{content_token}` | Path: content_token, content_type; Query: entrance, listened_cnt | a |

### 2.124 api.zhihu.com#podcasts

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/podcasts/player/progress/{content_type}/{content_token}` | Path: content_token, content_type | a |
| `POST` | `/podcasts/subscribe/{content_type}/{content_token}` | Path: content_token, content_type | a |

### 2.125 api.zhihu.com#poisson-marketing

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/poisson-marketing/buy_and_give/buy/{sku_id}` | Path: sku_id | KmService |

### 2.126 api.zhihu.com#poisson

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/poisson/event/record` | — | EBookService, KmCommonService, KmService, TaskWebService |

### 2.127 api.zhihu.com#polls

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/polls/{id}` | Path: id | TopStoryService, b |
| `GET` | `/polls/{poll_id}` | Path: poll_id | e |
| `POST` | `/polls/{poll_id}` | Path: poll_id | d, e |

### 2.128 api.zhihu.com#product

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/product/member/config` | Query: type | KMPersonalService |
| `POST` | `/product/member/config` | — | KMPersonalService |
| `POST` | `/product/member/relationship` | — | KmCommonService, a, c |

### 2.129 api.zhihu.com#promotions

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/promotions/{article_id}` | Path: article_id | PromoteArticleService |
| `GET` | `/promotions/{article_id}/is_voted` | Path: article_id | PromoteArticleService |
| `POST` | `/promotions/{article_id}/voters` | Path: article_id; Field: voteup_count, voting | PromoteArticleService |
| `GET` | `/promotions/{id}/share` | Path: id | ShareService |

### 2.130 api.zhihu.com#promus

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/promus/assessment/{sku_id}/reports` | Path: sku_id; Query: offset | f |
| `POST` | `/promus/audios/info` | — | a, c |
| `POST` | `/promus/progress` | — | a, m |
| `POST` | `/promus/progress/group_progress` | — | a |
| `POST` | `/promus/progress/unit_progress` | — | a |
| `GET` | `/promus/tts/{tts_id}` | Path: tts_id | m |

### 2.131 api.zhihu.com#questions

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/questions` | — | QuestionEditorService |
| `GET` | `/questions/ai-message` | Query: question_token | AnswerRevisionService |
| `DELETE` | `/questions/drafts` | — | DraftService |
| `GET` | `/questions/{id}/share` | Path: id | ShareService |
| `POST` | `/questions/{questionId}/followers` | Path: questionId | e |
| `DELETE` | `/questions/{question_id}` | Path: question_id | QuestionService, a |
| `GET` | `/questions/{question_id}` | Path: question_id | AnswerEditorService, DbService, QuestionService, a |
| `PUT` | `/questions/{question_id}` | Path: question_id | QuestionEditorService |
| `GET` | `/questions/{question_id}/anonymous` | Path: question_id | DraftService, QuestionService |
| `PUT` | `/questions/{question_id}/anonymous` | Path: question_id; Field: is_anonymous | AnswerEditorService, QuestionService, a |
| `GET` | `/questions/{question_id}/answer-settings` | Path: question_id | AnswerEditorService, DbService |
| `DELETE` | `/questions/{question_id}/answer_later` | Path: question_id | QuestionService |
| `POST` | `/questions/{question_id}/answer_later` | Path: question_id | QuestionService, a |
| `DELETE` | `/questions/{question_id}/auto_invite` | Path: question_id | InviteeService |
| `GET` | `/questions/{question_id}/auto_invite` | Path: question_id | InviteeService |
| `POST` | `/questions/{question_id}/auto_invite` | Path: question_id | InviteeService |
| `GET` | `/questions/{question_id}/candidate-info` | Path: question_id | j |
| `GET` | `/questions/{question_id}/collapsed_answers` | Path: question_id; Query: offset | AnswerService |
| `DELETE` | `/questions/{question_id}/draft` | Path: question_id | AnswerEditorService |
| `GET` | `/questions/{question_id}/draft` | Path: question_id | AnswerEditorService, DraftService |
| `PUT` | `/questions/{question_id}/draft` | Path: question_id | AnswerEditorService |
| `GET` | `/questions/{question_id}/follow-answers` | Path: question_id | d |
| `GET` | `/questions/{question_id}/followers` | Path: question_id; Query: offset | QuestionService |
| `POST` | `/questions/{question_id}/followers` | Path: question_id | PushOtherService, QuestionService, SearchComponentService, TopicQuestionService, a |
| `DELETE` | `/questions/{question_id}/followers/{member_id}` | Path: member_id, question_id | QuestionService, SearchComponentService, TopicQuestionService, a |
| `POST` | `/questions/{question_id}/invitations/batch` | Path: question_id | InviteeService |
| `POST` | `/questions/{question_id}/invitees` | Path: question_id; Field: people_ids, src | InviteeService |
| `DELETE` | `/questions/{question_id}/invitees/{member_id}` | Path: member_id, question_id | InviteeService |
| `GET` | `/questions/{question_id}/inviters` | Path: question_id; Query: with_admin, with_answered, with_ignored | AnswerEditorService, DbService |
| `GET` | `/questions/{question_id}/poll_settings` | Path: question_id | QuestionService |
| `GET` | `/questions/{question_id}/recommendation_invitees` | Path: question_id | InviteeService |
| `GET` | `/questions/{question_id}/related-objects` | Path: question_id; Query: is_search | QuestionService |
| `GET` | `/questions/{question_id}/related-objects-v2?include=reactions` | Path: question_id; Query: enable_modular | AnswerListService, QuestionService |
| `GET` | `/questions/{question_id}/relationship` | Path: question_id | e |
| `DELETE` | `/questions/{question_id}/scheduled-answer` | Path: question_id | AnswerEditorService |
| `POST` | `/questions/{question_id}/validate-scheduled-answer` | Path: question_id | AnswerEditorService, DbService |
| `DELETE` | `/questions/{question_id}/voters/up` | Path: question_id | QuestionService |
| `POST` | `/questions/{question_id}/voters/up` | Path: question_id | QuestionService |
| `GET` | `/questions/{question_id}?include=read_count,query_info,voteup_count,voting,can_vote` | Path: question_id | QuestionService |
| `POST` | `/questions/{question_token}/invitations/ignore` | Path: question_token | QuestionService |
| `DELETE` | `/questions/{urlToken}/feeds/{sessionID}` | Path: sessionID, urlToken | AnswerRevisionService |
| `DELETE` | `/questions/{urlToken}/followers` | Path: urlToken | InteractiveService |
| `POST` | `/questions/{urlToken}/followers` | Path: urlToken | InteractiveService |
| `PUT` | `/questions/{urlToken}/guides` | Path: urlToken | AnswerService |

### 2.132 api.zhihu.com#reaction

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/reaction/comments/{comment_id}/like` | Path: comment_id | a, b |
| `POST` | `/reaction/comments/{comment_id}/like` | Path: comment_id | a, b |
| `DELETE` | `/reaction/images/{image_token}/like` | Path: image_token; Query: parent_id, parent_type; Header: za-spm | InteractiveService |
| `POST` | `/reaction/images/{image_token}/like` | Path: image_token; Header: za-spm | InteractiveService |
| `GET` | `/reaction/member/settings` | — | SynTrendsService |
| `POST` | `/reaction/member/settings` | — | SynTrendsService |
| `DELETE` | `/reaction/{content_type}/{content_token}/like` | Path: content_token, content_type; Query: is_real_pin_like; Header: za-spm | InteractiveService |
| `POST` | `/reaction/{content_type}/{content_token}/like` | Path: content_token, content_type; Header: za-spm | InteractiveService |
| `DELETE` | `/reaction/{content_type}/{content_token}/segment_reaction` | Path: content_token, content_type; Header: za-spm | InteractiveService |
| `POST` | `/reaction/{content_type}/{content_token}/segment_reaction` | Path: content_token, content_type; Header: za-spm | InteractiveService |
| `DELETE` | `/reaction/{content_type}/{content_token}/subscribe` | Path: content_token, content_type; Header: za-spm | InteractiveService |
| `POST` | `/reaction/{content_type}/{content_token}/subscribe` | Path: content_token, content_type; Header: za-spm | InteractiveService |
| `POST` | `/reaction/{content_type}/{content_token}/vote/up` | Path: content_token, content_type; Header: za-spm | InteractiveService |
| `DELETE` | `/reaction/{content_type}/{content_token}/vote/{action_value}` | Path: action_value, content_token, content_type; Header: za-spm | InteractiveService |
| `POST` | `/reaction/{content_type}/{content_token}/vote/{action_value}` | Path: action_value, content_token, content_type; Header: za-spm | InteractiveService |

### 2.133 api.zhihu.com#read_history

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/read_history/add` | — | n0 |
| `POST` | `/read_history/batch_add` | — | n0 |
| `GET` | `/read_history/total` | — | n0 |

### 2.134 api.zhihu.com#realname

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/realname/expose/contract` | — | ProfileService |
| `GET` | `/realname/gov` | — | AccountService |

### 2.135 api.zhihu.com#recommend

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/recommend/config` | Query: is_first_launch | a, s |

### 2.136 api.zhihu.com#reduction_v4

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/reduction_v4` | Query: app_ticket, atoken, ulink, ulink_params, umid | NetSwitchService |

### 2.137 api.zhihu.com#related_recommend

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/related_recommend/feed` | — | d |

### 2.138 api.zhihu.com#remix-web

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/remix-web/book_list/{catalog_id}/catalog` | Path: catalog_id; Query: after_id, include_search_id | a |
| `GET` | `/remix-web/common_simple/{business_id}/{business_type}/header` | Path: business_id, business_type | f |
| `GET` | `/remix-web/recommend/catalog` | Query: include_current_id, is_koc_search, limit, offset, section_id, well_id | a |
| `GET` | `/remix-web/{well_id}/indep_router/state` | Path: well_id; Query: section_id, type | i |

### 2.139 api.zhihu.com#remix

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/remix/common/{sku_id}/share` | Path: sku_id | d, f |
| `GET` | `/remix/common_v2/{business_id}/{business_type}/header` | Path: business_id, business_type | f |
| `POST` | `/remix/instabooks/daily_books/subscribe` | — | InstaBookService |
| `GET` | `/remix/instabooks/popover/subscribe` | — | b0 |
| `GET` | `/remix/instabooks/{instabook_id}/share` | Path: instabook_id | InstaBookService, s |
| `GET` | `/remix/progress/{business_id}/{business_type}` | Path: business_id, business_type; Query: with_fields | KmService, a, f |
| `POST` | `/remix/resource/{business_type}/{business_id}` | Path: business_id, business_type; Field: encrypted_key, sign, timestamp | PDFService |
| `POST` | `/remix/share/record` | — | a, f |
| `GET` | `/remix/video_lives/{live_id}/related_paid_column_id` | Path: live_id | LiveService |
| `GET` | `/remix/well/{id}/catalog` | Path: id; Query: after_id, all, before_id, fields, include_after_id, is_new_column, limit, mode | a |
| `GET` | `/remix/well/{id}/sections/{section_id}/dialogs` | Path: id, section_id; Query: limit, offset, progress | a |
| `GET` | `/remix/well/{well_id}/catalog` | Path: well_id; Query: ab_default_value, after_id, before_id, fields, include_after_id, is_new_column, limit, mode, offset, order_by, type, with_ab_param | f, q1 |
| `GET` | `/remix/well/{well_id}/catalog/slice` | Path: well_id | f |

### 2.140 api.zhihu.com#rings

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/rings/v1/constant` | — | m |
| `GET` | `/rings/v1/my/share` | — | b |
| `GET` | `/rings/v1/ring/{ring_id}/guide_popup` | Path: ring_id | b |
| `GET` | `/rings/v1/root_tab` | — | b |
| `GET` | `/rings/v1/root_tab/recommend` | Query: page, pin_id, scene | b |
| `GET` | `/rings/v1/{id}/feeds/essence` | Path: id; Query: scene | b |
| `GET` | `/rings/v1/{id}/feeds/hot` | Path: id; Query: pin_id, scene | b |
| `GET` | `/rings/v1/{id}/feeds/new` | Path: id; Query: pin_id, scene | b |
| `GET` | `/rings/v1/{id}/feeds/related` | Path: id | b |
| `DELETE` | `/rings/v1/{ringId}/admin/banned` | Path: ringId; Query: hash_id | m |
| `DELETE` | `/rings/v1/{ringId}/admin/pins/{pinId}` | Path: pinId, ringId; Query: desc | m |
| `GET` | `/rings/v1/{ring_id}` | Path: ring_id | b |
| `DELETE` | `/rings/v1/{ring_id}/bottom` | Path: ring_id; Query: pin_token | b |
| `POST` | `/rings/v1/{ring_id}/bottom` | Path: ring_id | b |
| `DELETE` | `/rings/v1/{ring_id}/choiceness` | Path: ring_id; Query: pin_token | b |
| `POST` | `/rings/v1/{ring_id}/choiceness` | Path: ring_id | b |
| `GET` | `/rings/v1/{ring_id}/gated` | Path: ring_id | b |
| `DELETE` | `/rings/v1/{ring_id}/membership` | Path: ring_id | b |
| `POST` | `/rings/v1/{ring_id}/membership` | Path: ring_id | ProfileService, b |
| `GET` | `/rings/v1/{ring_id}/profile_guide` | Path: ring_id; Query: scene | b |
| `POST` | `/rings/v1/{ring_id}/profile_guide/consume` | Path: ring_id; Query: guide_type, scene | b |
| `DELETE` | `/rings/v1/{ring_id}/top` | Path: ring_id; Query: pin_token | b |
| `POST` | `/rings/v1/{ring_id}/top` | Path: ring_id | b |
| `GET` | `/rings/v1/{ring_id}/topics` | Path: ring_id | b |

### 2.141 api.zhihu.com#root

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/root/guide/relation` | — | m0 |
| `GET` | `/root/tab` | — | m0 |
| `GET` | `/root/tab/v2` | Query: altitude, city, latitude, longitude, pd_city_geo_auth, source | m0 |

### 2.142 api.zhihu.com#roundtables

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/roundtables/{id}/share` | Path: id | ShareService |
| `POST` | `/roundtables/{roundtable_url_token}/followers` | Path: roundtable_url_token | RoundTableService, SearchComponentService |
| `DELETE` | `/roundtables/{roundtable_url_token}/followers/{member_id}` | Path: member_id, roundtable_url_token | RoundTableService, SearchComponentService |

### 2.143 api.zhihu.com#same_and_similar_question

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/same_and_similar_question` | Query: question_title | QuestionEditorService |

### 2.144 api.zhihu.com#schools

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/schools/{topic_token}/feeds/timeline_activity` | Path: topic_token; Query: limit | TopicService |

### 2.145 api.zhihu.com#scraper

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/scraper` | Query: url | a |

### 2.146 api.zhihu.com#search

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/search/customize` | — | MobileSearchService |
| `GET` | `/search/helper/profile` | Query: excerpt_len, q, restricted_field, restricted_scene, restricted_value, t | a |
| `GET` | `/search/helper/profile?excerpt_len=75&restricted_field=profile_type&restricted_scene=profile&t=profile` | Query: q, restricted_value | ProfileService |
| `GET` | `/search/history/pull` | Query: limit | j0 |
| `POST` | `/search/history/report` | — | SearchService2 |
| `GET` | `/search/hot_search` | Query: limit | j0 |
| `GET` | `/search/preset_words` | — | SearchService |
| `POST` | `/search/preset_words` | Query: clicked_zhihu_classics_top, is_cold_boot, is_first, sh_preset; Header: x-ad-preview | a0, h |
| `GET` | `/search/preset_words_report` | Query: is_click, is_disappear, query | a0, h |
| `GET` | `/search/recommend_query/v2` | Query: content_token, content_type, limit, new_main_page, offset, se_guess, search_hash_id; Header: x-ad-preview | j0 |
| `PUT` | `/search/recommend_query/v2` | — | j0 |
| `GET` | `/search/related_queries/{contentType}/{contentID}` | Path: contentID, contentType | j0 |
| `GET` | `/search/suggest` | Query: q | SearchSuggestService |
| `GET` | `/search/suggested_query` | Query: q | SearchSuggestService |
| `GET` | `/search/tabs` | Query: enable_recent | MobileSearchService |
| `GET` | `/search/widget/hot_search` | Query: limit, utm_source | f |

### 2.147 api.zhihu.com#search?t=people

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/search?t=people` | Query: offset, q | SearchService |

### 2.148 api.zhihu.com#search_question_highlight

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/search_question_highlight` | Query: limit, offset, q, t | QuestionEditorService |

### 2.149 api.zhihu.com#search_v3?t=people

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/search_v3?t=people` | Query: correction, q | SearchPeopleService |

### 2.150 api.zhihu.com#sections

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/sections/{content_type}/{content_id}/aggregation` | Path: content_id, content_type | EBookService |
| `POST` | `/sections/{object_type}/{object_id}/comment` | Path: object_id, object_type | EBookService, c |

### 2.151 api.zhihu.com#settings

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/settings/blocked_users` | Query: filter, offset | SettingsService |
| `POST` | `/settings/blocked_users` | Field: people_id | NewProfileService, ProfileService, q0 |
| `DELETE` | `/settings/blocked_users/{people_id}` | Path: people_id | NewProfileService, ProfileService, q0 |
| `GET` | `/settings/new/email` | — | NotificationSettingsService |
| `PUT` | `/settings/new/email` | Query: inboxmsg, member_follow, new_activity, question_invite, weekly_omnibus | NotificationSettingsService |
| `GET` | `/settings/new/notification` | — | NotificationServiceV3, NotificationSettingsService |
| `PUT` | `/settings/new/notification` | — | NotificationSettingsService |
| `GET` | `/settings/push_notification` | — | PushSettingsService |
| `PUT` | `/settings/push_notification` | — | PushSettingsService |
| `GET` | `/settings/social` | — | SocialService |
| `PUT` | `/settings/social` | Field: enable_weibo | SocialService |
| `PUT` | `/settings/vip` | — | VipSettingsService |

### 2.152 api.zhihu.com#short_url

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/short_url` | — | ShortUrlService |

### 2.153 api.zhihu.com#signals

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/signals/bayesian_interests/check` | Query: hash_id, source | k0 |
| `GET` | `/signals/business` | — | k0 |
| `GET` | `/signals/recommend_tags` | Query: age_group, education, gender, industry | k0 |
| `GET` | `/signals/schools` | Query: keyword, limit | a, k0 |

### 2.154 api.zhihu.com#simple-next-render

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/simple-next-render` | Header: x-ad-styles | d |

### 2.155 api.zhihu.com#sku

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/sku/km_resource` | Query: token | k |
| `GET` | `/sku/popup/{sku_id}` | Path: sku_id | a, b, c |
| `POST` | `/sku/reversion_sku_ext` | Query: ad_extra, sku_id | a, q |
| `POST` | `/sku/sku_ext` | Query: ad_extra, sku_id | a, b |
| `GET` | `/sku/svip_buy_popup` | Query: sku_id | a |

### 2.156 api.zhihu.com#slytherin

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/slytherin/activity` | Query: activity_key, pop_mode_id, section_id, site | k |
| `GET` | `/slytherin/activity/code` | Query: section_id, site | k |
| `POST` | `/slytherin/activity/report` | — | c |
| `POST` | `/slytherin/activity/{activity_code}/close` | Path: activity_code; Query: section_id, site | k |
| `POST` | `/slytherin/ad/reward/verify` | — | StatusCheckService |
| `GET` | `/slytherin/app/channel_activate` | — | i |
| `GET` | `/slytherin/cmcc/activities` | — | j |
| `POST` | `/slytherin/cmcc/activities` | — | j |
| `GET` | `/slytherin/fallback/{source}` | Path: source | DbService, NPSService |
| `POST` | `/slytherin/fallback/{source}` | Path: source | NPSService |
| `POST` | `/slytherin/marketing/outside/report` | — | s |
| `POST` | `/slytherin/marketing/set_simple_tag` | — | s |
| `POST` | `/slytherin/marketing/{token}` | Path: token | a |
| `GET` | `/slytherin/marketing/{token}/info` | Path: token | a |
| `GET` | `/slytherin/marketing/{token}/participate` | Path: token | a |
| `POST` | `/slytherin/paid_answer_pop_reward` | — | e |
| `GET` | `/slytherin/scene/article_end_card/material` | — | e |
| `GET` | `/slytherin/scene/coupon_countdown` | — | f |
| `POST` | `/slytherin/scene/coupon_countdown/close` | — | f |
| `POST` | `/slytherin/scene/coupon_countdown/trigger` | — | f |
| `GET` | `/slytherin/scene/detail/participate` | — | SkuHeaderApiV2 |
| `GET` | `/slytherin/scene/manuscript_pop_v3/material` | — | a |
| `POST` | `/slytherin/scene/manuscript_pop_v3/material` | — | a |
| `GET` | `/slytherin/scene/manuscript_retrieve_android/material` | — | a |
| `POST` | `/slytherin/scene/manuscript_retrieve_android/material` | — | a |
| `POST` | `/slytherin/scene/material/use_frequency` | — | a, b, e |
| `GET` | `/slytherin/scene/{token}/participate` | Path: token; Query: section_id | a |
| `GET` | `/slytherin/scenes/material` | Query: content_id, tokens | a, b |
| `GET` | `/slytherin/yanyan/scene/yanyan_manuscript_popup/material` | — | a |
| `POST` | `/slytherin/yanyan/scene/yanyan_manuscript_popup/material` | — | a |
| `GET` | `/slytherin/yanyan/scene/{scenes}/material` | Path: scenes | a |
| `POST` | `/slytherin/yanyan/scene/{scenes}/material` | Path: scenes | a |

### 2.157 api.zhihu.com#social

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/social/associate/yun139/accesstoken` | — | a |
| `GET` | `/social/associate/yun139/member_phone_no_cipher` | Query: uuid | a |
| `POST` | `/social/associate/{type}/update` | Path: type | SocialService |
| `GET` | `/social/bind` | — | SocialService |
| `POST` | `/social/config/steam` | — | SocialService |

### 2.158 api.zhihu.com#staging_contents

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/staging_contents` | Query: ids | a |
| `POST` | `/staging_contents` | Field: action, object_type, staging_content | StagingContentService |

### 2.159 api.zhihu.com#sticker-groups

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/sticker-groups/{group_id}?business=message` | Path: group_id | StickerService |

### 2.160 api.zhihu.com#sticker

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/sticker/list/{group_id}?business=message` | Path: group_id | StickerService |

### 2.161 api.zhihu.com#subscriptions

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/subscriptions/{id}` | Path: id | PushOtherService |

### 2.162 api.zhihu.com#tagore

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/tagore/categories` | — | DbService |
| `GET` | `/tagore/categories/tree` | — | d |

### 2.163 api.zhihu.com#topic_square

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/topic_square/categories` | — | BaseTopicService, QuestionService |
| `GET` | `/topic_square/categories/{category_id}/topics` | Path: category_id | BaseTopicService, QuestionService |

### 2.164 api.zhihu.com#topics

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/topics/lastread/receipts` | — | TopicService |
| `GET` | `/topics/{topicId}/basic?include=meta_header,meta.pub_info` | Path: topicId | DigitalProductService, k |
| `POST` | `/topics/{topicId}/followers` | Path: topicId | k |
| `DELETE` | `/topics/{topicId}/followers/{member_id}` | Path: member_id, topicId | k |
| `GET` | `/topics/{topicId}/vote` | Path: topicId | DigitalProductService, f, k |
| `GET` | `/topics/{topicUrlTokenInPath}/feeds/delicious_foods` | Path: topicUrlTokenInPath; Query: limit, offset | TopicService |
| `GET` | `/topics/{topicUrlTokenInPath}/feeds/life` | Path: topicUrlTokenInPath; Query: limit, offset | TopicService |
| `GET` | `/topics/{topicUrlTokenInPath}/feeds/tourist_attractions` | Path: topicUrlTokenInPath; Query: limit, offset | TopicService |
| `GET` | `/topics/{topic_id}` | Path: topic_id | TopicService |
| `GET` | `/topics/{topic_id}/basic` | Path: topic_id | BaseTopicService, d |
| `GET` | `/topics/{topic_id}/basic?include=meta.pub_info` | Path: topic_id | f |
| `GET` | `/topics/{topic_id}/basic?include=meta_header,meta.pub_info` | Path: topic_id; Query: brand_page_preview, source | TopicService |
| `GET` | `/topics/{topic_id}/best_answerers` | Path: topic_id; Query: limit, offset | TopicService |
| `GET` | `/topics/{topic_id}/essence_feeds` | Path: topic_id; Query: limit, offset | TopicService |
| `GET` | `/topics/{topic_id}/feeds/top_activity` | Path: topic_id; Query: after_id, brand_page_preview, limit, source | TopicService |
| `GET` | `/topics/{topic_id}/followers` | Path: topic_id; Query: offset | BaseTopicService |
| `POST` | `/topics/{topic_id}/followers` | Path: topic_id | BaseTopicService, SearchComponentService, TopicService |
| `DELETE` | `/topics/{topic_id}/followers/{member_id}` | Path: member_id, topic_id | BaseTopicService, SearchComponentService, TopicService |
| `GET` | `/topics/{topic_id}/is_following` | Path: topic_id | TopicService |
| `GET` | `/topics/{topic_id}/meta` | Path: topic_id; Query: include | TopicService |
| `GET` | `/topics/{topic_id}/sticky_feeds` | Path: topic_id; Query: offset | TopicService |
| `GET` | `/topics/{topic_id}/tags` | Path: topic_id | CampusService |
| `GET` | `/topics/{topic_id}/tags/{tag_id}` | Path: tag_id, topic_id | CampusService |
| `GET` | `/topics/{topic_id}/topic_index` | Path: topic_id | TopicService |
| `GET` | `/topics/{topic_id}/unanswered_questions` | Path: topic_id; Query: limit, offset | TopicService |
| `GET` | `/topics/{topic_token}` | Path: topic_token | ArticleEditorService, CommunityEditorService2, DbService, a |
| `GET` | `/topics/{topic_token}/awards` | Path: topic_token | TopicService |
| `GET` | `/topics/{topic_token}/creator` | Path: topic_token | b |
| `GET` | `/topics/{topic_token}/dynamic` | Path: topic_token; Query: after_id | b |
| `GET` | `/topics/{topic_token}/videos` | Path: topic_token | TopicService |
| `GET` | `/topics/{topic_token}/vote` | Path: topic_token | TopicService |
| `DELETE` | `/topics/{topic_token}/vote/{topic_attitude}` | Path: topic_attitude, topic_token | TopicService, n |
| `POST` | `/topics/{topic_token}/vote/{topic_attitude}` | Path: topic_attitude, topic_token | TopicService, n |
| `GET` | `/topics/{urlToken}/browsing_history` | Path: urlToken | TopicService |
| `GET` | `/topics/{urlToken}/feeds/home_page` | Path: urlToken; Query: is_recommend, limit, offset | TopicService |

### 2.165 api.zhihu.com#topstory

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/topstory/hot-list/missed` | — | v |
| `GET` | `/topstory/hot-list/question-recommend` | Query: excluded_question_ids | TransitionHotListService |
| `GET` | `/topstory/hot-list/weekly` | Query: weekly_date | v |
| `GET` | `/topstory/hot-list/weekly-option` | — | v |
| `GET` | `/topstory/recommend` | — | g0 |

### 2.166 api.zhihu.com#trade

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/trade/gift/{gift_id}/share_info` | Path: gift_id | a |
| `GET` | `/trade/v2/deals/{deal_id}/status` | Path: deal_id | CashierService |
| `GET` | `/trade/v2/deals/{deal_id}/support_payments` | Path: deal_id | TradeService |

### 2.167 api.zhihu.com#twin

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/twin/user-config` | — | NumPeopleService |
| `PATCH` | `/twin/user-config` | — | NumPeopleService |

### 2.168 api.zhihu.com#unify-consumption

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/unify-consumption/tabs/{hash_id}/articles` | Path: hash_id; Query: limit; Header: need_debug | ProfileService |
| `GET` | `/unify-consumption/tabs/{hash_id}/pins` | Path: hash_id; Header: need_debug | ProfileService |
| `GET` | `/unify-consumption/tabs/{hash_id}/zvideos` | Path: hash_id; Header: need_debug | ProfileService |

### 2.169 api.zhihu.com#unipay

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/unipay/account_money` | Query: types | CoinService, WalletService |
| `GET` | `/unipay/account_query_v2` | Query: types | CoinService |
| `GET` | `/unipay/account_query_v2?types=` | — | a |
| `POST` | `/unipay/coupons` | — | CouponService |
| `POST` | `/unipay/old/payments/{tradeNo}` | Path: tradeNo; Header: X-Account-Unlock | WalletService |
| `GET` | `/unipay/prepay/{prepay_no}` | Path: prepay_no | CashPrepayService |
| `POST` | `/unipay/prepay/{prepay_no}/trade` | Path: prepay_no | CashOrderService |
| `GET` | `/unipay/prepay/{prepay_no}/trade/{trade_number}` | Path: prepay_no, trade_number | CashOrderService |
| `GET` | `/unipay/settings` | Query: type | WalletService |
| `POST` | `/unipay/wallet/education/currency/withdraw/ZXT_BALANCE` | — | ZhihuPayService |

### 2.170 api.zhihu.com#unlimited

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/unlimited/go/my_card/all` | — | a |
| `GET` | `/unlimited/go/my_card/v2` | — | b |
| `GET` | `/unlimited/go/pay_after_use` | Query: sku_id | r0 |
| `GET` | `/unlimited/go/svip_purchase` | Query: activity_key, channel_key; Header: x-sim-operator | a |
| `GET` | `/unlimited/go/svip_purchase/pay_retrieve` | Query: sku_id | a |
| `GET` | `/unlimited/go/vip_purchase/recommendation` | — | a |
| `GET` | `/unlimited/people/self/subscriptions` | — | f |
| `GET` | `/unlimited/vip_purchase_simple` | — | a |
| `GET` | `/unlimited/vip_rights/popup` | Query: token | a |

### 2.171 api.zhihu.com#upload_audio

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/upload_audio` | — | c |

### 2.172 api.zhihu.com#upload_image

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/upload_image` | — | UploadService |

### 2.173 api.zhihu.com#user-credit

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/user-credit/basis` | — | ProfileService, ZhuanlanProfileService |

### 2.174 api.zhihu.com#user-permission

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/user-permission` | — | QuestionService |

### 2.175 api.zhihu.com#user-re

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/user-re/guides` | — | k0 |

### 2.176 api.zhihu.com#user-regulate-core

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/user-regulate-core/regulate_info` | Query: error_name | a0 |

### 2.177 api.zhihu.com#usertask-core

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/usertask-core/action/read_content` | — | UserActionService |
| `POST` | `/usertask-core/action/use_app` | — | UserActionService |
| `POST` | `/usertask-core/action/{action_type}` | Path: action_type | BoardingService, a, e, o |

### 2.178 api.zhihu.com#usertask_core

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/usertask_core/app_tasks` | Query: content_id, content_type, page_type, scenes | o |
| `GET` | `/usertask_core/task/reach/data` | Query: task_id | ReportService |
| `POST` | `/usertask_core/task/{task_id}/observe_right` | Path: task_id | BoardingService |
| `GET` | `/usertask_core/task_group_status/{group_id}` | Path: group_id; Query: content_id, content_type, page_type | BoardingService |

### 2.179 api.zhihu.com#v2

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `PUT` | `/v2/collections/contents/{content_type}/{content_id}` | Path: content_id, content_type; Field: add_collections, remove_collections; Header: za-spm | a |
| `DELETE` | `/v2/pins/{id}` | Path: id | a |
| `GET` | `/v2/pins/{people_id}/moments` | Path: people_id; Header: need_debug | ProfileSubPinService |
| `GET` | `/v2/topstory/hot-lists/everyone-seeing?offset=0&limit=20` | — | TopStoryService |
| `PUT` | `/v2/{object_type}/{object_id}/comment_permission` | Path: object_id, object_type; Field: comment_permission | a |

### 2.180 api.zhihu.com#v5.1

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/v5.1/topics/entries/{entry-id}` | Path: entry-id | TopicService |
| `GET` | `/v5.1/topics/permissions` | — | TopicService |
| `GET` | `/v5.1/topics/recommends` | Query: keywords | TopicService |
| `GET` | `/v5.1/topics/{topic-token}/entries` | Path: topic-token; Query: limit, offset | TopicService |
| `POST` | `/v5.1/topics/{topic-token}/entries` | Path: topic-token | TopicService |
| `GET` | `/v5.1/topics/{topic-token}/feeds/{topic-type}` | Path: topic-token, topic-type; Query: limit, offset | TopicService |
| `GET` | `/v5.1/topics/{topic-token}/pin-related` | Path: topic-token | TopicService |
| `GET` | `/v5.1/topics/{topic_id}` | Path: topic_id; Query: enable_modular, include | a |
| `GET` | `/v5.1/topics/{topic_id}/timeliness` | Path: topic_id | a |
| `GET` | `/v5.1/topics/{topic_id}?type=pin&include=stats.pin-count,stats.pin-uv,stats.pin-feeds-pv` | Path: topic_id | TopicService |
| `GET` | `/v5.1/topics/{topic_token}/celebrities` | Path: topic_token | TopicService |

### 2.181 api.zhihu.com#v5

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/v5/images/client-sdk-config` | — | ImageService |
| `POST` | `/v5/topics` | — | TopicService |
| `GET` | `/v5/topics/{topic_id}/topic_index?use_new=true` | Path: topic_id | a |
| `GET` | `/v5/topics/{topic_token}/bind_recommendations?use_new=true` | Path: topic_token | CommunityEditorService2, DbService |
| `POST` | `/v5/voices/url-refresh` | — | a |

### 2.182 api.zhihu.com#validate

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/validate/phone_prefix_suffix` | Field: phone_mask | b, h |

### 2.183 api.zhihu.com#versioning

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/versioning/{app_name}/latest` | Path: app_name; Query: version | OfflineService |
| `GET` | `/versioning/{app_name}/{version}/{app_id}` | Path: app_id, app_name, version | OfflineService |

### 2.184 api.zhihu.com#vessay

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/vessay/music/collect` | — | f |
| `GET` | `/vessay/music/music_album` | — | f |
| `GET` | `/vessay/music/recommend` | Query: limit, music_id, offset, type | f |
| `GET` | `/vessay/music/resource/{music_id}` | Path: music_id | a |
| `POST` | `/vessay/music/use/{music_id}` | Path: music_id | f |

### 2.185 api.zhihu.com#video-consume

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/video-consume/lower-ground-floor-config` | — | e |
| `GET` | `/video-consume/play-config` | — | VideoAutoPlaySpiltService |
| `GET` | `/video-consume/play-config?config_type=voice,auto_play,floating_window` | — | VideoAutoPlaySpiltService |

### 2.186 api.zhihu.com#video-feed

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/video-feed/broadcast` | Query: type | e |
| `GET` | `/video-feed/choice/follow/white-feed` | Query: include, limit | a |
| `POST` | `/video-feed/choice/recommend/white-feed` | Query: include | a |
| `POST` | `/video-feed/cocreation?&limit=5` | — | a |
| `GET` | `/video-feed/immersion` | Query: behavior_records, is_click_recommend_request, object_id, object_type, page, scene, template_id, topic_id, topic_sort_type | a |
| `GET` | `/video-feed/immersion_click` | Query: behavior_records, object_id, object_type, scene, template_id, topic_id, topic_sort_type | a |
| `GET` | `/video-feed/pins` | Query: object_id, object_type, scene, topic_id, topic_sort_type | a |
| `POST` | `/video-feed/reference?&limit=5` | — | a |

### 2.187 api.zhihu.com#video

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/video/play/play_info/dynamic_config` | — | VideoService |
| `POST` | `/video/play/watermark` | — | VideoService |
| `POST` | `/video/player/extra` | — | VideoService |

### 2.188 api.zhihu.com#video_maker

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/video_maker/fallback_info` | Query: app_version, architecture, fallback | EffectService |

### 2.189 api.zhihu.com#video_material

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/video_material/guide/list` | — | a |
| `GET` | `/video_material/list?type=8&tab=0` | — | a |
| `GET` | `/video_material/tabs?type=10&with_materials=1` | Query: is_test | DbService |
| `GET` | `/video_material/tabs?type=2&with_materials=1` | Query: is_test | a |
| `GET` | `/video_material/tabs?type=9&with_materials=1` | Query: is_published, is_test, scene, topic_id | a |

### 2.190 api.zhihu.com#videos

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/videos/{videoID}/plugin/interactive` | Path: videoID | d, u |
| `POST` | `/videos/{videoID}/plugin/interactive` | Path: videoID | d, u |
| `DELETE` | `/videos/{videoID}/plugin/interactive/{pluginID}` | Path: pluginID, videoID | d, u |
| `PATCH` | `/videos/{videoID}/plugin/interactive/{pluginID}` | Path: pluginID, videoID | d, u |

### 2.191 api.zhihu.com#wallet-halley

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/wallet-halley/reply/{review_id}` | Path: review_id | a |
| `GET` | `/wallet-halley/sku/{sku_id}/review_tags` | Path: sku_id | a |
| `POST` | `/wallet-halley/sku/{sku_id}/reviews` | Path: sku_id | a |
| `GET` | `/wallet-halley/sku/{sku_id}/reviews/navbar` | Path: sku_id | a, b |
| `GET` | `/wallet-halley/sku/{sku_id}/reviews/{review_id}` | Path: review_id, sku_id | a |
| `PUT` | `/wallet-halley/sku/{sku_id}/reviews/{review_id}` | Path: review_id, sku_id | a |
| `POST` | `/wallet-halley/sku/{sku_id}/reviews/{review_id}/reply` | Path: review_id, sku_id | a |

### 2.192 api.zhihu.com#wallet-next

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `PUT` | `/wallet-next/red-packet/active` | — | ZhihuPayService |
| `POST` | `/wallet-next/red-packet/create` | — | ZhihuPayService |

### 2.193 api.zhihu.com#wallet-promotion

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/wallet-promotion/coupon_info/query_all_available/{skuId}` | Path: skuId; Query: total_amount | a |

### 2.194 api.zhihu.com#wallet

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/wallet/account/balance` | Query: channel, platform, version, wallet_id | WalletService |

### 2.195 api.zhihu.com#walletapp

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/walletapp/password` | Field: current_password, new_password, tran_type; Header: X-Account-Unlock | WalletService |

### 2.196 api.zhihu.com#wx-minapp-push

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/wx-minapp-push/share-card` | Query: app_type, content_token, content_type | ShareService, a |

### 2.197 api.zhihu.com#wx-service

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/wx-service/disaster-recovery/zhihuzhixuetang/effective` | — | n |
| `POST` | `/wx-service/generate/jump/app/{app}` | Path: app | n |

### 2.198 api.zhihu.com#z_cloud_disk

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/z_cloud_disk/file/uploads` | — | b |

### 2.199 api.zhihu.com#zhihu-account-prod

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/zhihu-account-prod/realname/info/v2` | Query: source | AccountService |
| `GET` | `/zhihu-account-prod/v1/account/popup_login/init` | Query: initScence | i |

### 2.200 api.zhihu.com#zhihu

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/zhihu/km_feed/feed_back` | — | NewMarketService |
| `POST` | `/zhihu/km_feed/last_read` | — | NewMarketService |
| `POST` | `/zhihu/km_pin/read` | — | NewMarketService |

### 2.201 api.zhihu.com#zhitrack_android

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/zhitrack_android` | — | a |

### 2.202 api.zhihu.com#zinvite

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/zinvite/negative-feedback/panel` | Query: content_token, content_type, scene_code | m |

### 2.203 api.zhihu.com#zos

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `PUT` | `/zos/object/{id}/uploading_status` | Path: id | UploadFileAPI |

### 2.204 api.zhihu.com#zreaction

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/zreaction` | Query: action_type, action_value, content_id, content_type | AnswerBigCardInteractiveService, InteractiveService, a |
| `POST` | `/zreaction` | — | AnswerBigCardInteractiveService, InteractiveService, a |
| `GET` | `/zreaction/count` | Query: action_type, action_value, content_id, content_type | a |
| `GET` | `/zreaction/count?action_type=like&action_value=like` | Query: content_id, content_type | a |

### 2.205 api.zhihu.com#zreaction?action_type=like&action_value=like

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/zreaction?action_type=like&action_value=like` | Query: content_id, content_type | a |

### 2.206 api.zhihu.com#zrec-feedback

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `DELETE` | `/zrec-feedback/block-keyword` | Query: keyword, scene_code | QuestionService |
| `GET` | `/zrec-feedback/block-keyword` | Query: scene_code | QuestionService |
| `PUT` | `/zrec-feedback/block-keyword` | Query: keywords, scene_code | QuestionService |
| `DELETE` | `/zrec-feedback/content-tag` | — | BlockKeywordsService, CreatorBlockKeywordsService |
| `GET` | `/zrec-feedback/content-tags` | Query: content_token, content_type, feed_deliver_type, feedback_type, scene_code | BlockKeywordsService, CreatorBlockKeywordsService |
| `POST` | `/zrec-feedback/content-tags` | — | BlockKeywordsService, CreatorBlockKeywordsService |
| `POST` | `/zrec-feedback/recommend-satisfaction` | — | a, b |

### 2.207 api.zhihu.com#zst

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/zst/events/p` | — | FraudReportService |

### 2.208 api.zhihu.com#zvideo-collections

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/zvideo-collections/collections/add` | — | b |
| `DELETE` | `/zvideo-collections/collections/{collection_id}` | Path: collection_id | b |
| `PATCH` | `/zvideo-collections/collections/{collection_id}` | Path: collection_id | b |
| `GET` | `/zvideo-collections/collections/{collection_id}/include` | Path: collection_id; Query: include, limit, offset | b |
| `POST` | `/zvideo-collections/collections/{collection_id}/include` | Path: collection_id | b |
| `POST` | `/zvideo-collections/collections/{collection_id}/uninclude` | Path: collection_id | b |
| `GET` | `/zvideo-collections/collections/{id}/share` | Path: id; Query: object_id, object_type | q |
| `POST` | `/zvideo-collections/content/included` | Query: object_id, object_type | AnswerEditorService, b |
| `GET` | `/zvideo-collections/members/{member_id}/collections` | Path: member_id; Query: limit, object_id, object_type, offset | b |
| `GET` | `/zvideo-collections/zvideos/can_include` | Query: collection_id, include, limit, offset | b |

### 2.209 api.zhihu.com#zvideo-contribute

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/zvideo-contribute/contribute` | — | a |
| `POST` | `/zvideo-contribute/contribute/publish` | — | a |
| `GET` | `/zvideo-contribute/contribute/question/recommend` | Query: title, zvideo_id | a |
| `GET` | `/zvideo-contribute/contribute/question/search` | Query: query | a |
| `DELETE` | `/zvideo-contribute/contribute/{contribute_id}` | Path: contribute_id | a |
| `GET` | `/zvideo-contribute/contribute/{contribute_id}` | Path: contribute_id | a |
| `PUT` | `/zvideo-contribute/contribute/{contribute_id}` | Path: contribute_id | a |
| `GET` | `/zvideo-contribute/theme/cover` | — | a |
| `GET` | `/zvideo-contribute/zvideos/{zvideo_id}/contributions` | Path: zvideo_id; Query: scene | a, c, d |
| `GET` | `/zvideo-contribute/zvideos/{zvideo_id}/status` | Path: zvideo_id; Query: full_duration_millis, target | a, c, d |

### 2.210 api.zhihu.com#zvideo-tabs

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/zvideo-tabs/tabs/choice/feeds/recommend?include=answer,vessay,creation_reference,drama,reactions&source=lower_ground_floor` | — | a |
| `GET` | `/zvideo-tabs/tabs/choice/rank` | — | a |
| `GET` | `/zvideo-tabs/tabs/follow/feeds` | Query: limit | a |

### 2.211 api.zhihu.com#zvideo_banners

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/zvideo_banners/v2?type=choice` | — | a |

### 2.212 api.zhihu.com#zvideos

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/zvideos/answers/{answer_id}/share` | Path: answer_id; Query: video_id | q |
| `GET` | `/zvideos/drafts` | Query: limit, offset | DraftService |
| `POST` | `/zvideos/drafts` | — | d |
| `GET` | `/zvideos/drafts/recommend-fill` | Query: category_id, content, title | d |
| `DELETE` | `/zvideos/drafts/{id}` | Path: id | DraftService, d |
| `GET` | `/zvideos/drafts/{id}` | Path: id | d |
| `PATCH` | `/zvideos/drafts/{id}` | Path: id | d |
| `GET` | `/zvideos/insertable` | — | a |
| `GET` | `/zvideos/notice-aggregation` | — | a |
| `GET` | `/zvideos/publish/content/{content_id}/{content_type}` | Path: content_id, content_type | d |
| `GET` | `/zvideos/switch/config` | Query: key | d |
| `DELETE` | `/zvideos/{id}` | Path: id | a, c |
| `GET` | `/zvideos/{id}` | Path: id; Query: type | a |
| `GET` | `/zvideos/{id}/creation-references` | Path: id | q |
| `GET` | `/zvideos/{id}/delete-prompt` | Path: id | c |
| `PUT` | `/zvideos/{id}/is_visible` | Path: id | a |
| `POST` | `/zvideos/{id}/likers` | Path: id | e |
| `GET` | `/zvideos/{id}/share` | Path: id | m, q |
| `GET` | `/zvideos/{id}/similar` | Path: id | VEProfileService |
| `POST` | `/zvideos/{id}/voters` | Path: id | InteractiveService, e |
| `GET` | `/zvideos/{id}?include=contribute,interactive_plugin,creation_relationship` | Path: id | a, c |
| `GET` | `/zvideos/{zvideo_id}/publish/permissions` | Path: zvideo_id; Query: full_duration_millis | d |

### 2.213 api.zhihu.com#{}

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `PUT` | `/{contentType}/{contentId}/included-column` | Path: contentId, contentType | AnswerEditorService, CommunityEditorService2, DraftService |
| `POST` | `/{content_type}/{content_id}/voters` | Path: content_id, content_type; Field: heavy_up, heavy_up_content, voting | a |
| `GET` | `/{host}/manuscript/annotations` | Path: host; Query: section_id | a |
| `POST` | `/{host}/manuscript/code` | Path: host | a |
| `GET` | `/{host}/manuscript/native/recommend` | Path: host; Query: include_current_id, section_id, well_id, window_width | a |
| `GET` | `/{host}/manuscript/{businessId}/{sectionId}/manu_core` | Path: businessId, host, sectionId; Query: transmission, window_width, zs_page_turn | b |
| `POST` | `/{host}/manuscript/{well_id}/{section_id}/content` | Path: host, section_id, well_id; Query: window_width | a |
| `GET` | `/{host}/manuscript/{well_id}/{section_id}/manu_cache` | Path: host, section_id, well_id | a |
| `GET` | `/{host}/paid_columns/native_neighbors` | Path: host; Query: direction, include_current_id, section_id, well_id, window_width | a |
| `GET` | `/{host}/template/list` | Path: host; Query: content_types, scene_code | a |
| `PUT` | `/{object_type}/{object_id}/comment_permission` | Path: object_id, object_type; Field: comment_permission | ContentCommentPermissionService, a |
| `POST` | `/{service_name}/manuscript/score` | Path: service_name | a |
| `GET` | `/{service_name}/manuscript/{business_id}/{section_id}/manu_pop?scene=score` | Path: business_id, section_id, service_name | a |

### 2.214 www.zhihu.com#api

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/v4/commercial/ecommerce` | — | EditorService, ZhihuEditorService |
| `GET` | `/api/v4/mcn/linkcard/{id}` | Path: id | ZhihuEditorService |
| `GET` | `/api/v4/mcn/linkcard/{linkcard_id}` | Path: linkcard_id | d |
| `GET` | `/api/v4/mcn/permission/profit` | — | DbService, ZhihuEditorService |
| `GET` | `/api/v4/moments/recommend_follow_people` | Query: item_id, rec_type | a |
| `GET` | `/api/v4/pu/verify/member/verifications` | — | VerifyService |
| `GET` | `/api/v4/zvideos/{id}/card` | Path: id | ZhihuEditorService |

### 2.215 www.zhihu.com#content

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/content/drafts?action=pin&offset=0&limit=1` | — | DbService, m0 |

### 2.216 www.zhihu.com#logout

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/logout` | Field: use_refresh_direct_sign | LogoutService |

### 2.217 www.zhihu.com#sc-profiler

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/sc-profiler` | — | ScProfilerService, e1 |

### 2.218 openapi.zhihu.com#access_token

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/access_token` | Field: app_id, app_key, code, grant_type, redirect_uri | OauthService |

### 2.219 openapi.zhihu.com#oauth

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/oauth` | Field: app_id, confirm, optional_privileges, redirect_uri, response_type | OauthService |

### 2.220 openapi.zhihu.com#oauth_info

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/oauth_info` | Query: app_id | OauthService |

### 2.221 adaudit.zhihu.com#api

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/ad_audit` | — | GetThirdSDKInfoService |

### 2.222 appcloud.zhihu.com#v1

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/v1/device/extension` | — | DeviceExtensionService |
| `GET` | `/v1/push_channels` | Header: X-APP-ID, X-REQ-SIGNATURE, X-REQ-TS, X-UDID | PushPlatformService |
| `POST` | `/v1/push_channels/subscribe` | Field: channels; Header: X-APP-ID, X-REQ-SIGNATURE, X-REQ-TS, X-UDID, x-app-build | PushPlatformService |
| `POST` | `/v1/push_report` | Field: ack_info; Header: X-APP-ID, X-REQ-SIGNATURE, X-REQ-TS, X-UDID, x-app-build | PushPlatformService |

### 2.223 appcloud2.zhihu.com#v3

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/v3/config` | Header: X-APP-BUILD, X-APP-ID, X-APP-KEY, X-REQ-SIGNATURE, X-REQ-TS, X-UDID, x-env | ConfigServiceAPI |
| `GET` | `/v3/package` | Query: active, launch_type; Header: X-APP-BUILD, X-APP-ID, X-APP-KEY, X-ARGUS-APP-KEY, X-REQ-SIGNATURE, X-REQ-TS, X-SYS-BIT, X-UDID, X-USER-HASH, x-env | SyncUpdateService |
| `GET` | `/v3/resource` | Query: group_name, name, version; Header: R-APP-FLAVOR, X-APP-BUILD, X-APP-ID, X-APP-KEY, X-REQ-SIGNATURE, X-REQ-TS, X-UDID, x-env | SyncService |
| `POST` | `/v3/resource` | Query: group_name; Header: R-APP-FLAVOR, X-APP-BUILD, X-APP-ID, X-APP-KEY, X-REQ-SIGNATURE, X-REQ-TS, X-UDID, x-env | SyncService |

### 2.224 growth.zhihu.com#api

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/coordinator/getActiveContent` | Query: link | NetSwitchService |

### 2.225 home-svr.in.zhihu.com#api

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/getUserBind/{uid}` | Path: uid; Header: appid, token | SyncUpdateService |

### 2.226 lens.zhihu.com#api

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/lives/heartbeat` | — | INetService, MLBService |
| `POST` | `/api/lives/play/heartbeat` | — | VideoService |
| `POST` | `/api/lives/rtc/vendor` | — | q |
| `GET` | `/api/lives/{live_id}` | Path: live_id | VideoService |
| `POST` | `/api/lives/{live_id}/access` | Path: live_id | INetService, MLBService, q |
| `PUT` | `/api/lives/{live_id}/actions/join` | Path: live_id | q |
| `POST` | `/api/lives/{live_id}/actions/switch_vendor` | Path: live_id | q |
| `PUT` | `/api/lives/{live_id}/actions/switch_vendor` | Path: live_id | q |
| `POST` | `/api/lives/{live_id}/actions/{action}` | Path: action, live_id | MLBService, q |
| `PUT` | `/api/lives/{live_id}/actions/{action}` | Path: action, live_id | INetService, MLBService, q |
| `GET` | `/api/lives/{live_id}/config` | Path: live_id | INetService, q |
| `GET` | `/api/v2/videos/upload_token` | Query: object_key, upload_id, video_id | VideoService |
| `PUT` | `/api/v2/videos/{video_id}/uploading_status` | Path: video_id | VideoService |
| `POST` | `/api/v4/videos` | Header: X-Upload-Conent-Type | VideoService |
| `GET` | `/api/v4/videos/upload_token` | Query: object_key, upload_id, video_id | VideoService |
| `GET` | `/api/v4/videos/{video_id}` | Path: video_id | VideoService |
| `GET` | `/api/v4/videos/{video_id}/uploading_status` | Path: video_id | PublishContainerService, VideoService |
| `PUT` | `/api/v4/videos/{video_id}/uploading_status` | Path: video_id | VideoService |
| `GET` | `/api/videos/{id}/bullet-config` | Path: id | c |
| `GET` | `/api/videos/{id}/quick-bullets` | Path: id | c |
| `GET` | `/api/videos/{video_id}` | Path: video_id | VideoService |
| `GET` | `/api/videos/{video_id}/bullets` | Path: video_id; Query: limit_fired_time, offset_fired_time | VideoService |
| `POST` | `/api/videos/{video_id}/bullets` | Path: video_id | VideoService |
| `GET` | `/api/videos/{video_id}/uploading_status` | Path: video_id | VideoService |

### 2.227 m-cloud.zhihu.com#api

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/apm/sampling/get` | Query: appKey, memberHash | SampleConfigApi |
| `GET` | `/api/app/monitor/sampling/sync` | Query: appKey, eTag | SampleConfigApi |
| `GET` | `/api/cloud/hotfix/filter` | — | PatchApi |
| `GET` | `/api/cloud/resource/read` | — | CloudResourceRead |

### 2.228 messaging.zhihu.com#zhihu

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/zhihu/group` | Field: deviceType, udid | NewZcmService |
| `DELETE` | `/zhihu/group/{udid}` | Path: udid | NewZcmService |

### 2.229 mqtt-internal-public.zhihu.com#mqtt

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/mqtt/probe/ping` | Query: clientId, msg_id, online, os, uid, version | a |
| `GET` | `/mqtt/probe/pong` | Query: clientId, msg_id, os, uid, version | a |

### 2.230 ops.in.zhihu.com#api

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/api/push_test` | Header: Cookie | a |
| `GET` | `/api/push_test/device_provider?project_id=1355` | Query: device_udid; Header: Cookie | a |

### 2.231 pay.zhihu.com#edu

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/edu/order/fast-purchase` | — | a |

### 2.232 qt.dev.zhihu.com#mag-server

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/mag-server/performance/record` | — | i |

### 2.233 simba.in.zhihu.com#api

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/style/ad_mock` | Query: ad_id, ad_style | GetMorphStyleTestInfoService |
| `GET` | `/api/style/ad_style` | — | GetMorphStyleTestInfoService |

### 2.234 sugar.zhihu.com#ad-track

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/ad-track/report/applist` | — | AdAppListService |

### 2.235 sugar.zhihu.com#plutus_adreaper

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/plutus_adreaper/install_success` | Query: pn, rf, ts | AdDownloadService |

### 2.236 walletpay.zhihu.com#wallet-next

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/wallet-next/coupons/usable/list` | — | ZhihuPayService |
| `POST` | `/wallet-next/currency/withdraw` | Header: X-Account-Unlock | ZhihuPayService |
| `GET` | `/wallet-next/query/order` | Query: last_new_id, offset, type, wallet_id | ZhihuPayService |

### 2.237 walletpay.zhihu.com#walletapp

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/walletapp/payment/order` | — | ZhihuPayService |
| `GET` | `/walletapp/query/coupon/all` | Query: member_id, page, query_type, service_id, size, wallet_id | ZhihuPayService |
| `POST` | `/walletapp/query/order` | Field: trade_no, trade_type, wallet_id | ZhihuPayService |
| `GET` | `/walletapp/query/orderOldlist` | Query: member_id, page, service_id, size, version, wallet_id | ZhihuPayService |
| `POST` | `/walletapp/query/paymethod` | Field: acct_type, member_id, service_id, version, wallet_id | ZhihuPayService |
| `POST` | `/walletapp/withdraw` | — | ZhihuPayService |

### 2.238 world.zhihu.com#api

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `GET` | `/api/client/v1/get_appoint_game` | — | AppointmentDownloadService |
| `GET` | `/api/client/v1/get_canvas_info` | Query: campaignId, token | CanvasService |

### 2.239 world.zhihu.com#submit

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/submit/canvas/verify-code` | Field: info | CanvasService |

### 2.240 zhida.zhihu.com#ai_ingress

| 方法 | 路径 | 请求参数 | 来源类 |
| --- | --- | --- | --- |
| `POST` | `/ai_ingress/buddy/general/cold_start/load` | — | q1 |

