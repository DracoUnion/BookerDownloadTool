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

## 附：提取来源说明

- 接口路径、参数模板、域名均来自 `classes*.dex` 字符串池（共 486,276 条字符串）静态提取，按 `naapi/`、`appapi/`、`doc/submit/`、`/pages/`、`h5-*` 前缀归类。
- 预览逻辑 UI 层定位到 `com.baidu.wenku.bdreader.ui.activity.WKReaderContentPreviewActivity`（classes10.dex），HTTP 层定位到 `com.baidu.wenku.base.net.download.DocContentReqAction` 等 ReqAction 类。
- 首要接口域名：`https://appwk.baidu.com`（BASE_URL）。