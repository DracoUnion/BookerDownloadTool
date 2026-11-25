# 百度文库搜索接口逆向分析

> 分析对象：百度文库 PC 端搜索页 `https://wenku.baidu.com/search?word=<关键词>`
> 分析方式：Firefox 打开页面 → 给 `XMLHttpRequest` / `fetch` 打桩 → 触发搜索 → 抓取请求；
> 随后从前端打包产物 `pcUnionClient/js/views/view-ai-union-*.js` 中定位接口封装与参数构造逻辑。
> 目的：定位**文档检索列表**接口，供 `bdt wenku-fetch` 子命令直接调用。

---

## 1. 页面结构

- 搜索页 URL：`https://wenku.baidu.com/search?word=<关键词>&tabType=doc`
- 页面为 Vue 单页应用，入口 HTML 内联 `window.pageData`，其中与检索相关的字段为：

| 字段 | 示例 | 说明 |
| --- | --- | --- |
| `searchTabType` | `doc` | 当前标签页（`doc` 文档 / `composite` 综合 / `square` 广场） |
| `queryPath` | `/ndcore/browse/search?word=机器学习` | 检索路由 |
| `encodedWord` | `%E6%9C%BA%E5%99%A8%E5%AD%A6%E4%B9%A0` | URL 编码后的关键词 |
| `tabData.tabMap[5].trueUrl` | `//wenku.baidu.com/search?lm=0&od=0&word=_QUERY_` | 顶部“文库”竖排入口，`lm`/`od` 即下文的格式与排序参数 |

检索结果**不在** HTML 中（`docId` / `/view/` 链接均不在 HTML 里），而是页面加载后由 JS 发起 XHR 取得。

## 2. 接口定位

在前端打包产物中，`view-ai-union-43dd7041.062d4a10.js` 可见：

```js
f = function (e, t) { return r.L.post("/gsearch/search/newallsearch", e, { signal: t }) }
```

调用点（`view-ai-union-749a6420.32f137c7.js`）给出请求体构造逻辑：

```js
E = function () {
  var e = {
    word: S.value,                 // 关键词
    pn: C.value,                   // 页码，从 1 开始
    rn: k.value,                   // 每页条数（首页 12，其余页 10）
    fr: "wkSearch",
    lm: P.value[$.M_.Format],      // 格式筛选
    fd: P.value[$.M_.Resource] === $.kq.BOOK ? $.kq.BOOK : P.value[$.M_.Type],  // 类型筛选
    od: P.value[$.M_.Sort],        // 排序
    sceneParam: P.value[$.M_.SCENE_KEY]
  };
  return I.membershipCardWord !== S.value ? { ...e, noCacheMembershipCard: true } : e;
}
```

同目录下的其它检索相关接口：

| 接口 | 方法 | 用途 |
| --- | --- | --- |
| `/gsearch/search/newallsearch` | POST | **文档检索列表**（本项目使用） |
| `/gsearch/search/zscard` | POST | 关键词 AI 摘要卡片，body 为 `platform=pc&query=<词>`（表单编码） |
| `/gsearch/search/scenerecognition` | GET | 场景识别，query 参数为 `query=<词>&ext_platform=pc` |
| `/gsearch/search/genflowsearch` | POST | AI 生成流式检索 |
| `/gdoc/genflow/searchrecquery` | GET | 搜索推荐词，参数 `reqNum` |
| `/gdoc/square/squaresearch` | GET | “广场”卡片检索，参数 `query`、`pn`、`rn` |

## 3. 请求格式

```http
POST /gsearch/search/newallsearch HTTP/1.1
Host: wenku.baidu.com
Content-Type: application/json
Referer: https://wenku.baidu.com/search
User-Agent: Mozilla/5.0 ... Chrome/124.0.0.0 Safari/537.36

{"word":"人工智能","pn":1,"rn":12,"fr":"wkSearch","lm":0,"fd":0,"od":0}
```

> 注意：请求体必须是 **JSON**。用 `application/x-www-form-urlencoded` 提交会返回
> `{"status":{"code":200002,"msg":"empty word"}}`。

### 参数取值

| 参数 | 含义 | 取值 |
| --- | --- | --- |
| `word` | 关键词 | 任意字符串 |
| `pn` | 页码 | 从 1 开始 |
| `rn` | 每页条数 | 网页端首页 12、其余页 10 |
| `fr` | 来源标识 | 固定 `wkSearch` |
| `lm` | 格式筛选 | 0 不限 / 1 doc / 2 pdf / 3 ppt / 4 xls / 5 txt |
| `fd` | 类型筛选 | 0 全部 / 1 VIP专享 / 3 免费 / 4 精品；搜索图书时为 11 |
| `od` | 排序 | 0 最高相关 / 1 最新上线 / 2 最多下载 / 3 最高评分 |
| `sceneParam` | 场景参数 | 一般为空 |
| `noCacheMembershipCard` | 会员卡缓存开关 | 可选，布尔值 |

筛选面板与参数的对应关系来自前端常量：

```js
{ fdResource: "fdResource", format: "lm", type: "fd", relate: "od", more: "more", overall: "overall" }
```

## 4. 响应格式

```json
{
  "status": { "code": 0, "msg": "success", "sLogid": "0959417195" },
  "data": {
    "result": {
      "items": [
        {
          "card_type": "wk_doc",
          "docId": "e9c2c40d3f3567ec102de2bd960590c69ec3d888",
          "title": "<em><em>人工智能</em></em>简介.pptx",
          "abstract": "……",
          "data": {
            "url": "https://wenku.baidu.com/view/e9c2c40d3f3567ec102de2bd960590c69ec3d888.html?fr=income{{.itemPosition}}-doc-search",
            "docID": "e9c2c40d3f3567ec102de2bd960590c69ec3d888",
            "title": "<em><em>人工智能</em></em>简介.pptx",
            "content": "……",
            "fileType": 6,
            "pageNum": 31,
            "createTime": 1782623065,
            "qualityScore": 3.7,
            "sellType": 2,
            "downloadCount": 1,
            "viewCount": 106,
            "tagList": [],
            "authorInfo": { "name": "", "url": "" },
            "authorVerify": { "username": "店铺新人1f9wy", "homeUrl": "..." },
            "copyable": true,
            "covers": ["https://wkimg.bdimg.com/img/..."]
          },
          "ctjParams": { "sulaResourceID": "e9c2c4...", "sulaSearchID": "1028596516" }
        }
      ],
      "extra": {
        "word": "人工智能",
        "total": 44906,
        "isFilterWord": false,
        "membershipCards": [],
        "sampleId": "116406_2"
      },
      "strategy": {}
    }
  }
}
```

要点：

- `data.result.items` 混合多种卡片，`card_type` 为 `wk_doc` 才是文档；另有 `note_video`（视频）、`rec_query`（相关搜索词）。
- 标题、摘要中的 `<em>` 是关键词高亮标签，输出前需要剥离。
- `data.url` 中的 `?fr=income{{.itemPosition}}-doc-search` 是前端模板残留，实际使用应按 `docID` 拼出
  `https://wenku.baidu.com/view/<docID>.html`。
- `data.result.extra.total` 为结果总数，可用于判断是否还有后续页。
- `card_type=rec_query` 的卡片位于列表中间，属于“相关搜索”，不是文档。

## 5. 稳定性与风控

- 接口无需登录态即可返回结果，但频繁请求会触发风控；请求间隔建议 ≥ 0.5 秒。
- 首次请求前访问一次文库首页（种 Cookie）可降低被拦截概率。
- 直接用 `curl` 请求文档详情页 `/view/<docID>.html` 常返回 403，属详情页自身风控；
  判断文档是否存在可用 `https://wenku.baidu.com/api/doc/getdocinfo?callback=cb&doc_id=<docID>`。

## 6. 本项目实现

- `BookerDownloadTool/wenku_fetch_agent.py`：调用接口、解析 `wk_doc` 卡片、按 `doc_id` 去重、本地 YAML 缓存。
- `BookerDownloadTool/wenku_fetch_models.py`：`WenkuDoc` / `WenkuSearchResult` 模型。
- `BookerDownloadTool/wenku_fetch.py`：编排器与命令行参数，输出文档链接（一行一个）到 `{关键词}.txt`。

```bash
bdt wenku-fetch 人工智能                    # 写入 人工智能.txt
bdt wenku-fetch 人工智能 -n 3 -o links.txt  # 抓 3 页
bdt wenku-fetch 人工智能 --format 2 --type 3   # 只要 pdf 且免费
```
