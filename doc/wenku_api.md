# 百度文库 APK 文档预览逻辑与 HTTP 接口分析

> 分析对象：`百度文库_9.2.50_APKPure.apk`（com.baidu.wenku）
> 载体：IDA Pro IDB（`百度文库_9.2.50_APKPure.apk.i64`）+ 14 个 classes*.dex 字符串/字节码静态提取
> 目的：定位**文档预览逻辑**的代码位置，厘清预览/阅读/下载环节调用的 HTTP 接口

---

## 1. 预览逻辑代码位置（类路径）

文档预览可分为「在线阅读」与「本地/上传预览」两条链路，核心类如下。

### 1.1 在线文档预览（阅读器）

| 类路径（Descriptor） | 职责 |
| --- | --- |
| `com/baidu/wenku/bdreader/ui/activity/WKReaderContentPreviewActivity` | 内容预览页 Activity（预览主入口） |
| `com/baidu/wenku/bdreader/ui/activity/LongPicPreviewActivity` | 长图（图片版式）预览 |
| `com/baidu/wenku/bdreader/readcontrol/txt/manager/TxtReaderController` | TXT 文本阅读器控制 |
| `com/baidu/wenku/bdreader/readcontrol/txt/TxtOpenHelper` | TXT 打开辅助 |
| `com/baidu/wenku/bdreader/readcontrol/txt/model/WkTxtBook` | TXT 书模型 |
| `com/baidu/wenku/bdreader/plugin/ui/pdf/PDFActivity` | PDF 阅读 |
| `com/baidu/wenku/bdreader/helper/WenkuBookManager` | 书籍数据管理 |
| `com/baidu/wenku/bdreader/helper/ReaderUtils` | 阅读器工具 |
| `com/baidu/wenku/base/model/XReaderEntity` | 阅读实体模型 |
| `com/baidu/datalib/docedit/widget/DocEditTemplatePreviewDialog` | 文档编辑模板预览弹窗 |

> 位置参考：这些类主要位于 `classes10.dex`（`WKReaderContentPreviewActivity` 确认为 classes10.dex 3367406）。

### 1.2 网络请求 Action（预览/下载发起的 HTTP 请求）

| 类路径 | 接口/用途 |
| --- | --- |
| `com/baidu/wenku/base/net/reqaction/SourceDocInfoReqAction` | 源文档信息（预览/转换前的文档信息） |
| `com/baidu/wenku/base/net/download/DocContentReqAction` | **文档内容请求**（预览正文核心） |
| `com/baidu/wenku/base/net/download/TransferDownloadReqAction` | 转存下载 |
| `com/baidu/wenku/base/net/download/RequestActionBase` | 下载请求基类 |
| `com/baidu/wenku/bdreader/action/ExportLongPicReqAction` | 长图导出 |
| `com/baidu/wenku/bdreader/action/ExportLongPicStatusReqAction` | 长图导出状态 |
| `com/baidu/wenku/pptdownload/model/PPTPageReqAction` | PPT 页 |
| `com/baidu/wenku/bdreader/plugin/formats/pdf/CheckHeaderReqAction` | PDF 头检查 |
| `com/baidu/wenku/importmodule/ai/convert/model/action/SourceDocInfoReqAction` | AI 转写源文档信息 |

---

## 2. 域名 / HOST

| 域名 | 用途 |
| --- | --- |
| `http://appwk.baidu.com` | **BASE_URL**——naapi/appapi 主接口域 |
| `https://appwk.baidu.com` | 主接口域（HTTPS） |
| `https://wenku.baidu.com` | 网页版 / view 页面 |
| `http://wenku.baidu.com/view/` | 网页查看页 |
| `https://wapwenku.baidu.com` | WAP 查看页 |
| `wenku.bdimg.com` / `edu-wenku.bdimg.com` | 静态资源 / CDN |
| `.cdn.bcebos.com` | BOS 对象存储（文档附件/图片） |
| `converter.baidu.com` | 文档转换服务 |
| `wk.baidu.com` | 知识 / 音频 / 课程 |
| 内网 | `naonline04.appwk.wenku.baidu-int.com`、`fedev_zlk.tanbi.wenku.baidu-int.com`、`wenku.baidu-int.com` |

---

## 3. 预览核心信令（关键参数模板）

下载/预览请求中出现的签名参数模板，来自 DEX 常量池：

| 模板 | 含义 |
| --- | --- |
| `rt=dc&pw=0&pn=0&rn=0&awk=mydown&ver=2&doc_id=%1$s&dt=%2$s&sign=%3$s` | 文档内容下载（`rt=dc` = download content） |
| `type=2&sign=%s&rt=Retype&doc_id=%s&pn=%d&rn=%d&aimw=%d&%s` | 重新排版下载 |
| `channel=%1$s&doc_id=%2$s&sign=%3$s` | 渠道预览 |
| `doc_id=%1$s&sign=%2$s` | 基础签名 |
| `&doc_id=` / `?docId=` / `;docId=` | doc 标识参数 |

---

## 4. HTTP 接口清单（按前缀分类）

### 4.1 naapi 文档/预览/下载接口（`https://appwk.baidu.com/naapi/...`）

#### 文档预览 / 下载
| 接口 | 说明 |
| --- | --- |
| `naapi/doc/view?` | 文档预览视图信息 |
| `naapi/doc/viewlist` | 预览视图列表 |
| `naapi/doc/briefinfo?` | 文档简介信息 |
| `naapi/doc/classnew?` | 文档分类 |
| `naapi/doc/intercept` | 预览拦截判断 |
| `naapi/doc/feature` | 文档特性 |
| `/naapi/doc/getbatchdownloadinfo` | **批量下载信息** |
| `naapi/doc/getcopytext` | 复制文本 |
| `naapi/doc/getdoccommontag?` | 文档标签 |
| `naapi/doc/getdocvoucher?` | 文档下载凭证 |
| `naapi/doc/getnewdoctags` | 新文档标签 |
| `naapi/doc/freedownload?` | 免费下载 |
| `naapi/doc/downloadrtcs?` | 下载（rtcs） |
| `naapi/doc/getprivilege` | 下载权限 |
| `naapi/doc/getdocsbyentuuid?` | 按 entUuid 查文档 |
| `naapi/doc/getentitybyword?` | 按词查实体 |
| `naapi/doc/copyploy` | 复制策略 |
| `naapi/doc/getsalerrec?` | 卖家推荐 |
| `naapi/doc/getpackinfo?` | 打包信息 |
| `naapi/doc/getdocdownloadcopywriter?` | 下载文案 |
| `naapi/doc/viewrecom?` | 预览推荐 |

#### 文档/阅读统计与用户
| 接口 | 说明 |
| --- | --- |
| `naapi/user/getviewcnt` | 浏览量 |
| `naapi/user/getdoccount?` | 文档数 |
| `naapi/user/getimportcnt` | 导入数 |
| `naapi/user/getinfo?` | 用户信息 |
| `naapi/user/GetChannelAndType?` | 渠道类型 |
| `naapi/user/getgiftcontent?` | 礼包内容 |
| `naapi/user/getnewuservip` | 新用户 VIP |
| `naapi/user/getvipoff?` | VIP 优惠 |
| `naapi/user/navipmutex?` | VIP 互斥 |
| `naapi/user/checkviptrialcard` / `receiveviptrialcard` | 体验卡 |
| `/naapi/user/useFreeDoc?` | **使用免费文档** |
| `naapi/vip/readerrenewinfo?` | 阅读器续费信息 |
| `/naapi/wkpay/vipexpirecontrol?` | VIP 到期控制 |
| `naapi/wkpay/NaPayAuthCancel?` | 支付鉴权取消 |
| `naapi/wkpay/viewviplimit?` | 查看 VIP 限制 |
| `naapi/wkpay/vipactivitycontrol?` | VIP 活动控制 |
| `user/naapi/getsignature?` | 签名 |
| `user/naapi/getboughtnum?` / `getbrowsenum?` / `getcollectionnum?` | 已购/浏览/收藏数 |
| `user/naapi/boughtdoc` / `boughtdocpack` / `boughtcourses` | 已购内容 |

#### 编辑/转换/回答
| 接口 | 说明 |
| --- | --- |
| `naapi/api/totxt?` | **文档转 txt** |
| `naapi/api/urltodoc?` | URL 转文档 |
| `naapi/api/translate?` | 翻译 |
| `naapi/api/converterdocinfo?` | 转换文档信息 |
| `naapi/api/getofflinepkginfo?` | 离线包信息 |
| `naapi/api/getdistributioninfo?` | 分销信息 |
| `naapi/api/getmallinfo?` | 商城信息 |
| `naapi/api/getmsg?` | 消息 |
| `naapi/api/smallflow?` | 免流 |
| `naapi/api/sync?` | 同步 |
| `naapi/bigque/...` | 答题（bigque）系列 |
| `naapi/answer/...` | 回答系列 |

#### 其它（支付/任务/圈子/音频/课本）
- 支付：`naapi/pay/...`（MkTrade?、bddsmktrade?、canceltrade?、gototrade?、paycheck?、getvoucher?、miniviplist?、resultcallback、getdocavailablevoucher?、recallorder）
- 任务：`naapi/task/...`（centerlist?、checkshare?、fintask?、gettaskgoods?、inittask、localrece?、updatetask、taskvcode?...）
- 圈子：`naapi/wkcircle/...`（addreply、delreply、like、zanreply、mycollect、messagelist...）
- 音频：`naapi/audio/catalog?`、`info?`、`rec?`
- 文件夹：`naapi/folder/...`（folderlist、doclist?、addtolist、movedoctofolders...）
- 小说：`naapi/wknovel/readtask`、`taskstatus`、`getreadtaskgoods?`
- 文库币：`naapi/wkcoin/wkcoinlist?`、`wkcointrade?`
- 教材：`naapi/book/getbaikelemmacard?`、`naapi/jingpin/getcategory?`

#### 文档详情（外链 H5）
- `/pages/view/view?docid=` —— H5 端预览页路径（追星/分享/网页端查看）

### 4.2 appapi 应用接口（`https://appwk.baidu.com/appapi/...`）

#### 文档
| 接口 | 说明 |
| --- | --- |
| `appapi/doc/wpinfo` | **Word 预览信息** |
| `appapi/doc/playppt` | **PPT 播放** |
| `appapi/doc/pptcatalog` | **PPT 目录** |
| `appapi/doc/pptplayinfo` | **PPT 播放信息** |
| `appapi/doc/catalog` | 文档目录 |
| `appapi/doc/downcard` | 下载卡 |
| `appapi/doc/downloaddc` | 下载（dc） |
| `appapi/doc/rename` | 重命名 |
| `appapi/doc/batchdelete` | 批量删除 |
| `appapi/doc/infolder` | 是否在文件夹 |
| `appapi/doc/helpful` | 有用 |
| `appapi/doc/editorlimited` | 编辑限制 |
| `appapi/doc/getaicard` | AI 卡 |
| `appapi/doc/getrecommendtool` | 推荐工具 |
| `appapi/doc/gettool/synergy` | 协作工具 |
| `appapi/doc/aieditordocrec` / `ndocrec` | AI 编辑器文档推荐 |
| `appapi/doc/searchsorttype` | 搜索排序类型 |

#### AI / 编辑 / 生成
- `appapi/ai/...`（storymedia 系列、ppt 系列、multidoc/parse、sensitive、uploadimg、readpage、docassistant...）
- `appapi/aiv2/...`（getppttemplate、promptlist、tagandpromptlist、ctrl、researchreport...）
- `appapi/edit/...`（aieditconfig、getusereditdoclist、getusereditdoccnt、btn）
- `appapi/newupload/...`（listall、filechooseable）
- `appapi/packeddoc/...`（generate、info、mypacks、indexpacks）

#### 首页 / 我的 / 皮肤 / 网盘
- `appapi/index/...`（home、tab、homeicondata、getcid、getunitlist、queryclick、tabselected）
- `appapi/abg/...`（index、readerdoc）
- `appapi/mydoc/...`（newpersondata/...、recenteditdoclst、recentgenerated/list...）
- `appapi/skin/...`（list、choosed、popup、popuped）
- `appapi/wpan/...`（getpanfilelist、getuserauthstatus、getfiledlink、userauthpan、usercancelauthpan）
- `appapi/note/...`（add、list、remove）
- `appapi/share/...`（info、assistance）
- `appapi/user/...`（batchcollectdoc、getudocinfo、checktfuser、usercenterconfig、getfileuploadverify）
- `appapi/tool/...`、`appapi/task/...`、`appapi/push/...`、`appapi/vip/vipprompt`、`appapi/vipday/config`、`appapi/pay/sucpop`

### 4.3 上传/提交接口（doc/submit/*）

| 接口 | 说明 |
| --- | --- |
| `doc/submit/nagetbostoken` | 获取 BOS 上传 token |
| `doc/submit/napreviewfile` | **提交预览文件** |
| `doc/submit/nacompletefile` | 完成上传 |
| `doc/submit/naupload?` | 上传 |
| `doc/submit/naconvcheck` | 转换检查 |
| `doc/submit/nagetstsbostoken` | 获取 TTS BOS token |

> 上传/预览文件流程：`nagetbostoken` → `napreviewfile` → `nacompletefile`。

### 4.4 转换服务（converter.baidu.com）

| 接口 | 说明 |
| --- | --- |
| `POST /api/uploadfile` | 上传文件 |
| `/api/fileconverter` | 发起转换 |
| `/api/fileconverterstatus` | 转换状态 |
| `/api/converterjob` | 转换任务 |
| `/api/converterjobdown` | 转换任务下载 |

### 4.5 其它辅接口

| 域名/路径 | 说明 |
| --- | --- |
| `https://wk.baidu.com/api/interface/getdocothercache?` | 文档相关缓存 |
| `https://mbd.baidu.com/fetchlog/getbostoken` | 获取 BOS token（短链） |
| `https://wenku.baidu.com/xpage/form/getform?id=wenku_android_magirain` | 表单 |
| `https://wenku.baidu.com/vcode?` | 验证码 |
| `https://wenku.baidu.com/wenji/` | 文集 |
| `https://wenku.baidu.com/daoru` | 导入 |

---
### 4.6 全量接口请求参数

> **请求公共参数（全部接口均附加）**：每个 naapi/appapi 请求都会在 query/body 中附加下方 `公共参数`（由 `NaapiRequestActionBase.buildCommonParamsMap(true)` 生成）以及 `time`、`sign`（见 §6 `naapi_common_sign`）。下表「参数」列仅列出**接口特有参数**；值为「仅公共参数」表示该接口额外参数未直接以 `.put("key",...)` 形式出现在反编译源码中（可能通过对象模型字段或字符串模板携带）。

| 公共参数 | 说明 |
| --- | --- |
| `uid` | `abd_000000000000000`（固定） |
| `pid` / `bid` | 1 / 1（固定） |
| `opid` | `wk_na`（固定） |
| `from` | `3_<channel>`，URL 编码 |
| `fr` | `3` |
| `ua` | 设备 UA，形如 `build/model_androidVersion`，下划线拼接，URL 编码 |
| `app_ua` | Build.MODEL，URL 编码 |
| `screen` | `<height>_<width>`，URL 编码 |
| `Bdi_bear` | 设备指纹（`t.d()`），URL 编码 |
| `nettype` | 网络类型（`t.c()`），URL 编码 |
| `app_version` 等 | 应用版本号（`versionName`） |
| `sys_ver` | Build.VERSION.RELEASE |
| `vendor` | Build.MANUFACTURER |
| `phone_model` | Uri.encode(Build.MODEL) |
| `api_level` | Build.VERSION.SDK_INT |
| `density` | 屏幕密度 |
| `channel` | 渠道 ID（`MarketChannelHelper.getChannelID()`） |
| `cuid` / `signCuid` | 设备标识；`signCuid = MD5("113"+cuid+"bpfc")` |
| `hw_oaid` / `oaid` / `c3_aid` | 设备 OAID 类标识（存在时） |
| `sampleId`/`PackageId`/`fourth_category` | 配置下发字段（存在时） |
| `time` | `System.currentTimeMillis()`（毫秒字符串） |
| `sign` | 见 §6 — `MD5("113"+app_version+bduss+"3_"+channel+cuid+time10+"rwdk70aqPu")` |
| Cookie | `BDUSS=<bduss>`（登录态，另含 `X-Sid`/`X-Sid-Type` 调试开关） |

**接口清单与特有参数：**

| 接口路径（相对 `http://appwk.baidu.com/`） | 特有参数 |
| --- | --- |
| `/appapi/index/getunitlist` | 仅公共参数 |
| `/appapi/index/tabselected` | cid,  flag_id |
| `/naapi/doc/getbatchdownloadinfo` | docIds |
| `/naapi/folder/getedustrucinfo` | docId |
| `/naapi/task/userdailyinfo` | 仅公共参数 |
| `/naapi/task/userdailyinfo?` | 仅公共参数 |
| `/naapi/user/useFreeDoc?` | 仅公共参数 |
| `/naapi/wkpay/vipexpirecontrol?` | 仅公共参数 |
| `/user/naapi/getsignature?` | 仅公共参数 |
| `appapi/abg/index` | 仅公共参数 |
| `appapi/abg/readerdoc` | docId |
| `appapi/activity/code` | code,  os |
| `appapi/ai/aichart/export` | docId,  height,  taskId,  title,  width |
| `appapi/ai/aichart/exportstatus` | docId,  height,  taskId,  title,  width |
| `appapi/ai/cameramenu` | source |
| `appapi/ai/chart/intention` | content |
| `appapi/ai/docassistant?cuid=` | action,  docId,  from,  query,  tfViewAI,  title |
| `appapi/ai/editor` | 仅公共参数 |
| `appapi/ai/entrycard` | query,  source |
| `appapi/ai/introduction` | docId,  source |
| `appapi/ai/librarydoclist` | pn,  rn |
| `appapi/ai/menu` | tab |
| `appapi/ai/multidoc/parse` | docId |
| `appapi/ai/multidoc/status` | docIds |
| `appapi/ai/ppt/bostoken` | mFileEXT,  mFilename,  type |
| `appapi/ai/ppt/conv` | docId |
| `appapi/ai/ppt/gc` | pptjson,  style_id,  themeId,  title,  tpl_id |
| `appapi/ai/ppt/gettplbdjson` | docId,  docSourceDir,  uploadDocBucket,  uploadDocFilePath,  uploadDocTitle |
| `appapi/ai/ppt/pptjson` | mdoutline,  rebuildNum,  rebuild_idx,  style_id,  title,  tpl_id |
| `appapi/ai/ppt/pptjsonv2` | mdoutline,  rebuildNum,  rebuild_idx,  style_id,  title,  tpl_id |
| `appapi/ai/ppt/topiclist` | content,  source,  title |
| `appapi/ai/pptoptimize/create` | docName,  type,  uploadSource |
| `appapi/ai/pptoptimize/status` | taskID |
| `appapi/ai/readpage` | key_recommedn_ids |
| `appapi/ai/sensitive` | answerId,  blackUsed,  inputScene,  inputSource,  message,  query |
| `appapi/ai/storymedia/addprivacyauth` | imageObject,  roleName,  x1,  y1 |
| `appapi/ai/storymedia/addrole` | imageObject,  roleName,  x1,  y1 |
| `appapi/ai/storymedia/cancelnotification` | docId |
| `appapi/ai/storymedia/caseshareinfo` | docId |
| `appapi/ai/storymedia/casesharetext` | docId |
| `appapi/ai/storymedia/delhotpoint` | docId |
| `appapi/ai/storymedia/detail` | docId |
| `appapi/ai/storymedia/gethotpoint` | 仅公共参数 |
| `appapi/ai/storymedia/getimagebostoken` | fileExt,  object |
| `appapi/ai/storymedia/getnotification` | docId |
| `appapi/ai/storymedia/getprivacyauth` | imageObject,  roleName,  x1,  y1 |
| `appapi/ai/storymedia/getshareinfo` | docId |
| `appapi/ai/storymedia/getttsbostoken` | fileExt,  fileList,  object |
| `appapi/ai/storymedia/getvideo` | docId |
| `appapi/ai/storymedia/goodexample` | docId,  source |
| `appapi/ai/storymedia/imagesubmit` | fileExt,  object |
| `appapi/ai/storymedia/sharetext` | docId |
| `appapi/ai/storymedia/startsynctask` | docId,  from,  indexList,  isRetry,  opType |
| `appapi/ai/storymedia/substatus` | docId,  from,  indexList,  isRetry,  opType |
| `appapi/ai/storymedia/ttssubmit` | fileExt,  fileList,  object |
| `appapi/ai/uploadimg` | content,  source |
| `appapi/aiv2/ctrl` | ability,  action |
| `appapi/aiv2/editor/prompt/search` | query |
| `appapi/aiv2/editor/recommend` | doc_id |
| `appapi/aiv2/editor/tagandpromptlist` | 仅公共参数 |
| `appapi/aiv2/getassistantlist` | docId,  source,  toollist |
| `appapi/aiv2/getppttemplate` | 仅公共参数 |
| `appapi/aiv2/homepageaibar` | 仅公共参数 |
| `appapi/aiv2/ppt/topiclist` | content,  source,  title |
| `appapi/aiv2/prompt/search` | query |
| `appapi/aiv2/promptcfg` | 仅公共参数 |
| `appapi/aiv2/promptlist` | tagId |
| `appapi/aiv2/prompttaglist` | 仅公共参数 |
| `appapi/aiv2/researchreport/content` | 仅公共参数 |
| `appapi/aiv2/researchreport/tpl` | 仅公共参数 |
| `appapi/aiv2/tagandpromptlist` | 仅公共参数 |
| `appapi/api/getimagebostoken` | fileExt,  object |
| `appapi/api/growthaccept?na_uncheck=1` | android_id,  app_from,  app_name,  app_type,  os_version,  soft_version |
| `appapi/api/imagesubmit` | fileExt,  object |
| `appapi/api/naerise` | 仅公共参数 |
| `appapi/api/sharetailcopy` | docId |
| `appapi/api/skin` | 仅公共参数 |
| `appapi/api/tradeinfo?` | tradeid |
| `appapi/api/updatesubinfo` | subType |
| `appapi/doc/aieditordocrec` | docContent,  docId,  docName |
| `appapi/doc/batchdelete` | docIds |
| `appapi/doc/catalog` | docId |
| `appapi/doc/downcard` | docId |
| `appapi/doc/downloaddc` | docId |
| `appapi/doc/editorlimited` | 仅公共参数 |
| `appapi/doc/getaicard` | docId |
| `appapi/doc/getrecommendtool` | docId |
| `appapi/doc/gettool/synergy` | docId |
| `appapi/doc/helpful` | docId,  status |
| `appapi/doc/infolder` | docId |
| `appapi/doc/ndocrec` | goodsId |
| `appapi/doc/playppt` | docId |
| `appapi/doc/pptcatalog` | docId |
| `appapi/doc/pptplayinfo` | docId |
| `appapi/doc/rename` | docId,  docName |
| `appapi/doc/searchsorttype` | 仅公共参数 |
| `appapi/doc/wpinfo` | docId,  needShareUrl |
| `appapi/donate/detail` | 仅公共参数 |
| `appapi/edit/aieditconfig` | 仅公共参数 |
| `appapi/edit/btn` | docid |
| `appapi/edit/getusereditdoccnt` | 仅公共参数 |
| `appapi/edit/getusereditdoclist` | dataVersion,  fileOperationType,  pn,  rn,  tagName |
| `appapi/folder/homepageentry` | 仅公共参数 |
| `appapi/holiday/card` | query,  source |
| `appapi/index/getcid` | docid |
| `appapi/index/home` | doccid1,  type |
| `appapi/index/homeicondata` | 仅公共参数 |
| `appapi/index/queryclick` | type |
| `appapi/index/tab` | edoc_page_num,  edoc_page_size,  tabCid |
| `appapi/invite/bind` | code |
| `appapi/invite/code` | code |
| `appapi/mydoc/newpersondata/adddoctofolder` | docIdList,  folderId,  inRoot |
| `appapi/mydoc/newpersondata/addfolder` | folderId,  folderName |
| `appapi/mydoc/newpersondata/delfolderanddoc` | docIds |
| `appapi/mydoc/newpersondata/editfolderlist` | docId |
| `appapi/mydoc/newpersondata/folderdoclist` | folderId,  pn,  rn,  selectType |
| `appapi/mydoc/newpersondata/renamefolder` | folderId,  folderName |
| `appapi/mydoc/newpersondata/renamefolderdoc` | docId,  docName |
| `appapi/mydoc/recenteditdel?` | 仅公共参数 |
| `appapi/mydoc/recenteditdoclst` | pn,  rn |
| `appapi/mydoc/recentgenerated/del?` | 仅公共参数 |
| `appapi/mydoc/recentgenerated/list` | last_timestamp,  pn,  rn |
| `appapi/newupload/filechooseable` | fileOperationType |
| `appapi/newupload/listall` | dPn,  fPn,  fileOperationType,  rn |
| `appapi/note/add` | noteIds,  pn,  rn |
| `appapi/note/list` | noteIds,  pn,  rn |
| `appapi/note/remove` | noteIds,  pn,  rn |
| `appapi/olympic2024/alipayuser` | auth_code |
| `appapi/packeddoc/generate` | docId |
| `appapi/packeddoc/indexpacks` | 仅公共参数 |
| `appapi/packeddoc/info` | clearType,  packId |
| `appapi/packeddoc/mypacks` | pn,  rn |
| `appapi/pay/sucpop` | cashType |
| `appapi/push/cate` | cateIds,  docId |
| `appapi/push/focus` | cateIds,  docId |
| `appapi/search/hot` | 仅公共参数 |
| `appapi/search/zlksearch` | pn,  position,  query,  rn,  timeType |
| `appapi/share/assistance` | code |
| `appapi/share/info` | 仅公共参数 |
| `appapi/skin/choosed` | skin_id |
| `appapi/skin/list` | 仅公共参数 |
| `appapi/skin/popup` | 仅公共参数 |
| `appapi/skin/popuped` | 仅公共参数 |
| `appapi/task/getpushsublist` | 仅公共参数 |
| `appapi/task/homepop` | taskaction |
| `appapi/task/subviptask` | subType |
| `appapi/task/toast` | taskaction |
| `appapi/task/updateviptask` | extra,  taskId |
| `appapi/task/viptask` | taskaction |
| `appapi/task/viptasklist` | taskaction |
| `appapi/tool/2024box` | 仅公共参数 |
| `appapi/tool/indexbar` | 仅公共参数 |
| `appapi/traffic/clipboard` | refer,  version |
| `appapi/tripartite/source/channel` | 仅公共参数 |
| `appapi/user/batchcollectdoc` | createTimes,  docIds |
| `appapi/user/checktfuser` | refer,  version |
| `appapi/user/getfileuploadverify` | action,  docIDs |
| `appapi/user/getudocinfo` | docIds,  folderId,  folderIds,  folderName,  pn,  rn,  shareId |
| `appapi/user/usercenterconfig` | 仅公共参数 |
| `appapi/vip/vipprompt` | visitPage |
| `appapi/vipday/config` | 仅公共参数 |
| `appapi/wkcircle/messageremind` | 仅公共参数 |
| `appapi/wpan/getfiledlink` | 仅公共参数 |
| `appapi/wpan/getpanfilelist` | fileOperationType,  limit,  path,  start |
| `appapi/wpan/getuserauthstatus` | 仅公共参数 |
| `appapi/wpan/userauthpan` | 仅公共参数 |
| `appapi/wpan/usercancelauthpan` | 仅公共参数 |
| `naapi/activity/daylearning` | 仅公共参数 |
| `naapi/activity/daylearningwindow` | 仅公共参数 |
| `naapi/activity/limitdownload` | docId |
| `naapi/activity/popwindow?` | 仅公共参数 |
| `naapi/answer/answerindex?` | 仅公共参数 |
| `naapi/answer/answersearch?` | 仅公共参数 |
| `naapi/answer/answeruseful?` | 仅公共参数 |
| `naapi/answer/class?` | 仅公共参数 |
| `naapi/answer/downloadanswer?` | 仅公共参数 |
| `naapi/answer/getanswercollectinfo?` | 仅公共参数 |
| `naapi/answer/getanswerinfo?` | 仅公共参数 |
| `naapi/answer/getnewhotlist?` | 仅公共参数 |
| `naapi/answer/ugcanswerinfo` | imagefile,  indexid,  indexids,  na_uncheck,  sign,  title,  type,  upid |
| `naapi/answer/ugcanswerupload` | imagefile,  indexid,  indexids,  na_uncheck,  sign,  title,  type,  upid |
| `naapi/answer/useranswercollect?` | 仅公共参数 |
| `naapi/answer/useranswerfeedback?` | 仅公共参数 |
| `naapi/answer/view?` | 仅公共参数 |
| `naapi/api/automatching` | doc_id,  title |
| `naapi/api/converterdocinfo?` | 仅公共参数 |
| `naapi/api/coursecollect?` | 仅公共参数 |
| `naapi/api/getdistributioninfo?` | 仅公共参数 |
| `naapi/api/getmallinfo?` | 仅公共参数 |
| `naapi/api/getmsg?` | 仅公共参数 |
| `naapi/api/getofflinepkginfo?` | 仅公共参数 |
| `naapi/api/getusertag?` | 仅公共参数 |
| `naapi/api/smallflow?` | 仅公共参数 |
| `naapi/api/sync?` | 仅公共参数 |
| `naapi/api/totxt?` | 仅公共参数 |
| `naapi/api/translate?` | 仅公共参数 |
| `naapi/api/urltodoc?` | 仅公共参数 |
| `naapi/api/vipvoucher?` | version |
| `naapi/api/wkadoptv2?` | 仅公共参数 |
| `naapi/api/wmadopt?` | 仅公共参数 |
| `naapi/api/wmzypaystatus?` | 仅公共参数 |
| `naapi/audio/catalog?` | 仅公共参数 |
| `naapi/audio/info?` | 仅公共参数 |
| `naapi/audio/rec?` | 仅公共参数 |
| `naapi/bigque/bigquebigpicsearch?` | 仅公共参数 |
| `naapi/bigque/bigqueextractpic?` | 仅公共参数 |
| `naapi/bigque/bigquequerysearch?` | 仅公共参数 |
| `naapi/bigque/getquedetail?` | 仅公共参数 |
| `naapi/bigque/photoconvertword?` | 仅公共参数 |
| `naapi/bigque/userphsearchfeedback?` | 仅公共参数 |
| `naapi/book/getbaikelemmacard?` | kw |
| `naapi/doc/briefinfo?` | 仅公共参数 |
| `naapi/doc/classnew?` | 仅公共参数 |
| `naapi/doc/copyploy` | docId,  flowRefer |
| `naapi/doc/downloadrtcs?` | 仅公共参数 |
| `naapi/doc/feature` | docId |
| `naapi/doc/freedownload?` | 仅公共参数 |
| `naapi/doc/getcopytext` | docId,  rn,  start |
| `naapi/doc/getdoccommontag?` | 仅公共参数 |
| `naapi/doc/getdocdownloadcopywriter?` | 仅公共参数 |
| `naapi/doc/getdocsbyentuuid?` | ent_uuid,  name,  pn,  rn |
| `naapi/doc/getdocvoucher?` | 仅公共参数 |
| `naapi/doc/getentitybyword?` | 仅公共参数 |
| `naapi/doc/getnewdoctags` | docId |
| `naapi/doc/getpackinfo?` | 仅公共参数 |
| `naapi/doc/getprivilege` | tsStyle |
| `naapi/doc/getsalerrec?` | 仅公共参数 |
| `naapi/doc/intercept` | clickSrc,  dailyFirstTimeLaunch,  docId,  extinfo,  intercepted,  isCallUpUser,  isNewDownloadUser,  readerFrom,  readerQuery,  refer,  referDocId,  source |
| `naapi/doc/view?` | 仅公共参数 |
| `naapi/doc/viewlist` | docId,  pn,  query,  rn,  source |
| `naapi/doc/viewrecom?` | 仅公共参数 |
| `naapi/feed/subscribeauthor?` | 仅公共参数 |
| `naapi/feed/usersubscribelist?` | 仅公共参数 |
| `naapi/folder/adddoctofolders` | delFolderIds,  docId,  folderIds |
| `naapi/folder/addfolder` | docIds,  folderId,  folderIds,  folderName,  pn,  rn,  shareId |
| `naapi/folder/addtolist` | docIds,  folderId,  folderIds,  folderName,  pn,  rn,  shareId |
| `naapi/folder/collectfolderlist` | docId,  pn,  rn |
| `naapi/folder/deletedoc?` | docIds,  folderId |
| `naapi/folder/delfolder` | docIds,  folderId,  folderIds,  folderName,  pn,  rn,  shareId |
| `naapi/folder/doclist?` | fileOperationType,  folderId,  pn,  rn |
| `naapi/folder/folderinfo` | docIds,  folderId,  folderIds,  folderName,  pn,  rn,  shareId |
| `naapi/folder/folderlist` | docIds,  folderId,  folderIds,  folderName,  pn,  rn,  shareId |
| `naapi/folder/jiaoyutab` | docCid1,  shareId,  type |
| `naapi/folder/library` | libraryfr |
| `naapi/folder/movedocstofolder` | delfolderIds,  desfolderId,  desfolderIds,  docId,  docIds,  srcfolderId |
| `naapi/folder/movedoctofolders` | delfolderIds,  desfolderId,  desfolderIds,  docId,  docIds,  srcfolderId |
| `naapi/folder/renamefolder` | docIds,  folderId,  folderIds,  folderName,  pn,  rn,  shareId |
| `naapi/jingpin/getcategory?` | 仅公共参数 |
| `naapi/layer/cashierlayer` | from_page |
| `naapi/layer/dailycard` | source |
| `naapi/layer/getshoubaivoucher` | 仅公共参数 |
| `naapi/multi/basicinfo` | docId |
| `naapi/multi/info?` | 仅公共参数 |
| `naapi/multi/report?` | 仅公共参数 |
| `naapi/pay/MkTrade?` | bduss,  orderInfoDescArray |
| `naapi/pay/bddsmktrade?` | bduss,  orderInfoDescArray |
| `naapi/pay/canceltrade?` | 仅公共参数 |
| `naapi/pay/getdocavailablevoucher?` | doc_id |
| `naapi/pay/getvoucher?` | goods_id,  goods_price |
| `naapi/pay/gototrade?` | orderInfoDescArray |
| `naapi/pay/miniviplist?` | 仅公共参数 |
| `naapi/pay/paycheck?` | 仅公共参数 |
| `naapi/pay/recallorder` | 仅公共参数 |
| `naapi/pay/resultcallback` | src,  tradeId |
| `naapi/privacy/personalization` | 仅公共参数 |
| `naapi/privacy/updatepersonalization` | status |
| `naapi/push/storelogintoken?` | app_name,  device,  op,  third_id,  third_type |
| `naapi/push/storenologintoken?` | app_name,  device,  op,  third_id,  third_type |
| `naapi/recommend/recommenddoc` | dataIds,  docId,  docTitle,  rn,  source |
| `naapi/recommend/vipdoccard` | query,  rn,  source |
| `naapi/recommend/vipdoccard?` | docId,  query,  rn,  source |
| `naapi/search/wkhotwords` | 仅公共参数 |
| `naapi/task/centerlist?` | 仅公共参数 |
| `naapi/task/checkshare?` | 仅公共参数 |
| `naapi/task/fintask?` | 仅公共参数 |
| `naapi/task/gettaskgoods?` | 仅公共参数 |
| `naapi/task/inittask` | 仅公共参数 |
| `naapi/task/localrece?` | 仅公共参数 |
| `naapi/task/newshare?` | 仅公共参数 |
| `naapi/task/taskstat` | 仅公共参数 |
| `naapi/task/tasksucst?` | 仅公共参数 |
| `naapi/task/taskvcode?` | 仅公共参数 |
| `naapi/task/updatetask` | extra,  taskId |
| `naapi/task/updatetaskpush` | isOpen |
| `naapi/user/GetChannelAndType?` | 仅公共参数 |
| `naapi/user/checkviptrialcard` | actId,  docId |
| `naapi/user/getdoccount?` | 仅公共参数 |
| `naapi/user/getgiftcontent?` | 仅公共参数 |
| `naapi/user/getimportcnt` | 仅公共参数 |
| `naapi/user/getinfo?` | 仅公共参数 |
| `naapi/user/getnewuservip` | 仅公共参数 |
| `naapi/user/getviewcnt` | 仅公共参数 |
| `naapi/user/getvipoff?` | 仅公共参数 |
| `naapi/user/navipmutex?` | 仅公共参数 |
| `naapi/user/newuservippopup` | docId,  source |
| `naapi/user/receiveaudio?` | 仅公共参数 |
| `naapi/user/receiveflowusergift?` | 仅公共参数 |
| `naapi/user/receiveviptrialcard` | 仅公共参数 |
| `naapi/user/receivewelfareusergift?` | 仅公共参数 |
| `naapi/vip/readerrenewinfo?` | docId |
| `naapi/wkbean/lottery?` | action,  na_uncheck,  signVer,  token |
| `naapi/wkcircle/addreply` | content,  dynamicId,  parentReplyId |
| `naapi/wkcircle/delreply` | replyId |
| `naapi/wkcircle/dynamicdetail` | dynamicId |
| `naapi/wkcircle/join?` | circleId |
| `naapi/wkcircle/like` | dynamicId |
| `naapi/wkcircle/messagelist` | msgTime,  option,  pn,  rn,  type |
| `naapi/wkcircle/messagenewlist` | msgTime,  option,  pn,  rn,  type |
| `naapi/wkcircle/messagetab` | conds,  likeTime,  replyTime,  startTime |
| `naapi/wkcircle/mycollect` | pn,  rn |
| `naapi/wkcircle/newusermessage` | crefer |
| `naapi/wkcircle/package` | circleId,  pn,  rn |
| `naapi/wkcircle/replydetail` | pn,  replyId,  rn |
| `naapi/wkcircle/replylist` | dynamicId,  pn,  rn |
| `naapi/wkcircle/retaincircle` | ids |
| `naapi/wkcircle/zanreply` | replyId,  type |
| `naapi/wkcoin/wkcoinlist?` | 仅公共参数 |
| `naapi/wkcoin/wkcointrade?` | trade_id |
| `naapi/wknovel/getreadtaskgoods?` | vcode_in,  vcode_str |
| `naapi/wknovel/readtask` | 仅公共参数 |
| `naapi/wknovel/taskstatus` | 仅公共参数 |
| `naapi/wkpay/NaPayAuthCancel?` | 仅公共参数 |
| `naapi/wkpay/viewviplimit?` | 仅公共参数 |
| `naapi/wkpay/vipactivitycontrol?` | 仅公共参数 |
| `user/naapi/boughtcourses` | 仅公共参数 |
| `user/naapi/boughtdoc` | 仅公共参数 |
| `user/naapi/boughtdocpack` | 仅公共参数 |
| `user/naapi/getboughtnum?` | 仅公共参数 |
| `user/naapi/getbrowsenum?` | 仅公共参数 |
| `user/naapi/getcollectionnum` | 仅公共参数 |
| `user/naapi/getcollectionnum?` | 仅公共参数 |


## 5. 预览/下载请求关键参数

| 参数 | 说明 |
| --- | --- |
| `doc_id` / `docId` / `docid` | 文档唯一标识 |
| `sign` | 签名（由 doc_id 等计算） |
| `rt=dc` | rt=Retype（重新排版）/ dc（下载内容） |
| `pn` / `rn` | 页码 / 每页行数 |
| `aimw` | 目标宽度（图片版式） |
| `pw=0` | 是否付费 |
| `awk=mydown` | 我的下载 |
| `ver=2` | 版本 |
| `channel` | 渠道 |
| `dt` | 文档类型 |

---

## 6. `sign` 参数逆向结果（当前证据）

### 6.1 `DocContentReqAction` 中已还原的算法

通过 JADX 对 `classes10.dex` 中的 `com.baidu.wenku.base.net.download.DocContentReqAction` 进行反编译，`getSign` 的 MagiRain 桩仍保留了实际 Java 逻辑。两个重载分别为：

```java
private String getSign() {
    String reversedDocId = StringUtil.strrev(this.mDocId);
    return FileMD5.md5(reversedDocId + "rwdk70aqPu");
}

private String getSign(int pn, int rn) {
    return FileMD5.md5(String.format(
        "%s_%d_%d_%s",
        StringUtil.strrev(this.mDocId), pn, rn, "rwdk70aqPu"));
}
```

对应的混淆类/方法名如下：

| JADX 还原名 | APK 中混淆名 | 作用 |
| --- | --- | --- |
| `StringUtil.strrev` | `com.baidu.wenku.uniformcomponent.utils.f0.z` | 反转字符串；逐字符交换后返回 |
| `FileMD5.md5` | `com.baidu.wenku.uniformcomponent.utils.k.d` | `MessageDigest.getInstance("MD5")`，输出小写十六进制 |
| `FileMD5.bufferToHex` | `com.baidu.wenku.uniformcomponent.utils.k.b/c` | 每个字节转两个小写十六进制字符 |
| `DocContentReqAction.getSign()` | `DocContentReqAction.getSign()` | 无页码参数的文档信息签名 |
| `DocContentReqAction.getSign(int,int)` | `DocContentReqAction.getSign(int,int)` | 重新排版分页签名 |

因此，无页码签名的可复现表达式是：

```text
sign0 = lower_hex(MD5(reverse(doc_id) + "rwdk70aqPu"))
```

分页签名的可复现表达式是：

```text
sign_page = lower_hex(MD5(reverse(doc_id) + "_" + str(pn) + "_" + str(rn) + "_rwdk70aqPu"))
```

这里的 `reverse` 是 Java 字符串按 UTF-16 `char` 反转；通常文档 ID 为 ASCII，因此 Python 的 `doc_id[::-1]` 等价。`k.d` 使用平台默认字符集调用 `str.getBytes()`；在 Android 常规环境下为 UTF-8，但实现本身没有显式传入字符集。

### 6.2 签名如何进入 HTTP 参数

`DocContentReqAction.buildRequestParams()` 的还原代码为：

```java
String reversedDocId = f0.z(mDocId);
String params = String.format(
    "rt=dc&pw=0&pn=0&rn=0&awk=mydown&ver=2&doc_id=%1$s&dt=%2$s&sign=%3$s",
    s.g(mDocId),
    mDocType,
    s.g(k.d(reversedDocId + "rwdk70aqPu")));
```

其中 `s.g` 是 `MiscUtil.urlEncode`，实现为：

```java
URLEncoder.encode(value, "utf-8")
```

所以实际下载参数可写成：

```text
GET/POST https://appwk.baidu.com/<download-path>
  ?rt=dc
  &pw=0&pn=0&rn=0&awk=mydown&ver=2
  &doc_id=URLEncode(doc_id)
  &dt=mDocType
  &sign=URLEncode(MD5(reverse(doc_id) + "rwdk70aqPu"))
  &<common-params>
```

若 `mDownloadType & 4 == 4`，还会追加：

```text
&pdt=2&fr=android     # mDocExt == "pdf"
&pdt=1&fr=android     # 其它扩展名
```

`source`、`doc_title`、`doc_ext`、`mtkey=uid` 会加入 `buildCommonParamsString`；当 `source == "search"` 时还会加入 `si=<searchIndex>`。

### 6.3 两个实际接口路径

`p20.b` 中的静态初始化明确给出：

```java
BASE = "http://appwk.baidu.com/";
MULTI_INFO = "naapi/multi/info?";
DOC_VIEW = "naapi/doc/view?";
```

因此：

1. `getDocInfoUrl()`：

```text
http://appwk.baidu.com/naapi/multi/info?
extct=0&extsale=1&doc_id=<doc_id>&sign=<sign0>&<common-params>
```

2. `getBdeFPackUrl(pn, rn, aimw)`：

```text
http://appwk.baidu.com/naapi/doc/view?
type=2&sign=<sign_page>&rt=Retype&doc_id=<doc_id>
&pn=<pn>&rn=<rn>&aimw=<aimw>&<common-params>
```

注意：APK 中同时保留 HTTP BASE_URL；实际运行环境可能由网络层升级为 HTTPS，复制请求时应优先使用抓包得到的最终 scheme。

### 6.4 Python 实现

下面的代码实现了 APK 中已经确认的两类签名。`doc_content_sign()` 对应 `DocContentReqAction.getSign()`；`page_sign()` 对应 `getSign(pn, rn)`。

```python
from __future__ import annotations

import hashlib
import time
from urllib.parse import quote_plus

SIGN_SALT = "rwdk70aqPu"


def md5_hex(value: str) -> str:
    """等价于 FileMD5.md5：平台默认编码在 Android 常规环境中为 UTF-8。"""
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def reverse_doc_id(doc_id: str) -> str:
    """Java StringUtil.strrev；文档 ID 通常是 ASCII。"""
    return doc_id[::-1]


def doc_content_sign(doc_id: str) -> str:
    """DocContentReqAction.getSign()。"""
    return md5_hex(reverse_doc_id(doc_id) + SIGN_SALT)


def page_sign(doc_id: str, pn: int, rn: int) -> str:
    """DocContentReqAction.getSign(pn, rn)。"""
    source = f"{reverse_doc_id(doc_id)}_{pn}_{rn}_{SIGN_SALT}"
    return md5_hex(source)


def download_params(doc_id: str, doc_type: int = 1) -> str:
    """生成 rt=dc 文档内容请求参数（不含 buildCommonParamsString 的字段）。"""
    sign = doc_content_sign(doc_id)
    return (
        "rt=dc&pw=0&pn=0&rn=0&awk=mydown&ver=2"
        f"&doc_id={quote_plus(doc_id)}"
        f"&dt={doc_type}"
        f"&sign={quote_plus(sign)}"
    )


def naapi_common_sign(
    app_version: str,
    cuid: str,
    channel: str,
    bduss: str = "",
    timestamp_ms: int | None = None,
) -> tuple[str, str, str]:
    """NaapiRequestActionBase.putSignTMap 的签名。

    返回 (time 参数, sign 原文, sign hex)。调用方还需补齐 APK 生成的
    其它公共参数（ua、screen、nettype、Bdi_bear 等）。
    """
    if timestamp_ms is None:
        timestamp_ms = int(time.time() * 1000)
    time_value = str(timestamp_ms)
    # g0.e()：字符串长度超过 10 时截取末尾 10 个字符。
    time10 = time_value[-10:] if len(time_value) > 10 else time_value
    channel_part = "3_" + channel
    sign_source = (
        "113" + app_version + (bduss or "") + channel_part
        + cuid + time10 + SIGN_SALT
    )
    return time_value, sign_source, md5_hex(sign_source)


if __name__ == "__main__":
    doc_id = "example-doc-id"
    print("doc sign:", doc_content_sign(doc_id))
    print("page sign:", page_sign(doc_id, pn=0, rn=100))
    print("download:", download_params(doc_id, doc_type=1))
    print("naapi:", naapi_common_sign(
        app_version="9.2.50",
        cuid="<cuid>",
        channel="<channel>",
        bduss="<BDUSS>",
    ))
```

对应的 Python 计算式：

```text
sign0 = md5_hex(reverse(doc_id) + "rwdk70aqPu")
sign_page = md5_hex(reverse(doc_id) + "_" + str(pn) + "_" + str(rn) + "_rwdk70aqPu")
sign_naapi = md5_hex(
    "113" + app_version + bduss + "3_" + channel
    + cuid + time10 + "rwdk70aqPu"
)
```

`naapi_common_sign()` 中的 `cuid` 来自 `hx.b.a(Context)`（优先设备 CUID，回退设备 ID），`channel` 来自 `MarketChannelHelper.getChannelID()`，`app_version` 来自包管理器的 `versionName`，`bduss` 来自登录态。不同设备、渠道和登录状态会产生不同的公共参数与签名。

### 6.5 证据边界

- **已确认**：此 APK 版本中 `DocContentReqAction` 的两种 `sign` 算法、固定字符串 `rwdk70aqPu`、反转操作、MD5 算法、URL 编码方式和两个接口路径。
- **尚未确认**：`buildCommonParamsString` 生成的设备/登录公共参数，以及服务端是否还会校验 Cookie、CUID、时间戳或请求头。
- `nativeSignCuid`、`rsaSign` 等字符串属于其它本地签名/设备安全模块，不能与上述文档内容 `sign` 混为同一算法。

## 附：提取来源说明

- 接口路径、参数模板、域名均来自 `classes*.dex` 字符串池（共 486,276 条字符串）静态提取，按 `naapi/`、`appapi/`、`doc/submit/`、`/pages/`、`h5-*` 前缀归类。
- 预览逻辑 UI 层定位到 `com.baidu.wenku.bdreader.ui.activity.WKReaderContentPreviewActivity`（classes10.dex），HTTP 层定位到 `com.baidu.wenku.base.net.download.DocContentReqAction` 等 ReqAction 类。
- 首要接口域名：`https://appwk.baidu.com`（BASE_URL）。