# BookerDownloadTool

一个面向中文互联网内容的命令行下载工具，支持从 GitHub 电子书、轻小说站（wenku8）、知乎、Discuz 论坛、知识星球、语雀、飞书、微信公众号、Anna's Archive、Medium、arXiv 等多个来源批量抓取内容并生成本地文件（EPUB / Markdown / 文本 / JSONL）。

- 语言：Python 3.9+，依赖见 [`pyproject.toml`](pyproject.toml)
- 默认以无头浏览器运行，部分命令基于 [Camoufox](https://github.com/daijro/camoufox) 反爬浏览器

---

## 安装

```bash
pip install .
```

安装后会生成三个等价的命令入口，任选其一使用（下文以 `bdt` 为例）：

```bash
bdt <命令> [参数]
# 或
BookerDownloadTool <命令> [参数]
dl-tool <命令> [参数]
python -m BookerDownloadTool <命令> [参数]
```

查看全部命令和帮助：

```bash
bdt -h          # 总帮助（列出全部子命令）
bdt <命令> -h   # 查看某个子命令的帮助
```

## 全局选项

| 选项 | 说明 |
| --- | --- |
| `-v, --version` | 显示版本号 |
| `-H, --no-headless` | 关闭无头模式，**显示**浏览器窗口（便于调试；默认是无头运行） |

> 注意：`annas` 子命令内部的 `-H, --headless` 含义相反（打开无头模式），不要混淆。

## Cookie 环境变量

需要登录的站点通过 Cookie 访问。以下环境变量会被对应命令用作 Cookie 的默认值，也可在命令行用 `-c/--cookie` 覆盖（用 [`ext-cookies`](#辅助工具) 可以从本机浏览器一键导出）：

| 环境变量 | 对应站点 / 命令 |
| --- | --- |
| `WK8_COOKIE` | wenku8 轻小说（`ln`/`batch-ln`/`fetch-ln`）、知乎（`zhihu-*`） |
| `ZSXQ_COOKIE` | 知识星球（`zsxq`） |
| `YUQUE_COOKIE` | 语雀（`yuque`/`batch-yuque`） |
| `FEISHU_COOKIE` | 飞书（`feishu`/`feishu-all`） |
| `GH_TOKEN` | GitHub（`gh-repo-fetch`） |
| `XHS_COOKIE` | 小红书（`xhs`，可选；缺省自动从本机浏览器 Cookie 提取） |

> 爬知乎乎、语雀、飞书、飞书等站点时，Cookie 里通常必须带上登录态的 Cookie 才能抓取完整内容。

---

## 命令速查

| 命令 | 功能 | 输出 |
| --- | --- | --- |
| `gh-book` | 抓取 GitHub 仓库的书籍（SUMMARY.md） | EPUB |
| `ln` / `batch-ln` / `fetch-ln` | 下载 / 批量下载 / 按日期抓取 wenku8 轻小说 | EPUB / id 列表 |
| `wenku` | 下载百度文库预览文档 | PDF |
| `zhihu-ques` / `zhihu-ques-batch` | 抓取知乎问题下的回答 | EPUB |
| `zhihu-topic` / `zhihu-topic-batch` / `zhihu-topics` | 抓取知乎话题下的问题、递归抓取子话题 | id 列表 |
| `dz` / `fetch-dz` / `batch-dz` | 下载 Discuz 论坛帖子 / 抓取 tid / 批量下载 | EPUB / id 列表 |
| `zsxq` | 下载知识星球某个圈子某个时间段的内容 | EPUB |
| `whole-site` / `exp-whole-site` | 爬取整站 URL 并入库 / 导出 URL | SQLite / txt |
| `medium` | 抓取 Medium 博客按日期发布的文章链接 | txt |
| `web-archive` | 从 Wayback Machine CDX 抓取某域名存档 URL | txt |
| `links` / `sitemap` | 按分页抓取页面链接 / 抓取站点地图链接 | txt |
| `links-epub` | 把链接列表批量生成 EPUB | EPUB |
| `wx` | 从公众号文章 Excel 导出批量生成 EPUB | EPUB |
| `uqer` / `batch-uqer` | 下载优矿（uqer）帖子（Markdown/IPython 笔记） | md / ipynb |
| `freembook` | 按 ssid 区间抓取 freembook 图书信息 | JSONL |
| `yuque` / `batch-yuque` | 抓取语雀知识库文章 / 批量抓取 | EPUB |
| `feishu` / `feishu-all` | 抓取飞书文档 / 抓取 wiki 整棵节点树 | md |
| `arxiv-fetch` | 按分类和日期区间抓取 arXiv 论文 id | txt |
| `gh-repo-fetch` | 用 GitHub API 搜索仓库（分页拉取全量） | txt |
| `hkrnws-fetch` / `hkrnws-range` | 抓取 hckrnews 某天 / 某日期区间链接 | txt |
| `pixabay` | 按关键词批量下载 Pixabay 图片 | 图片文件 |
| `annas` / `annas-batch` / `annas-fetch` / `annas-dedup` | Anna's Archive 单本下载 / 批量 / 搜索 / 去重 | 文件 / JSONL |
| `xhs` | 搜索小红书笔记，保存全量文本与图片 | md / 图片 |
| `twitter` | 用 Scweet 抓取 Twitter/X 关键词推文 | csv / json |
| `ext-cookies` | 从本机浏览器导出指定域名的 Cookie | 标准输出 |

---

## 命令详解

### GitHub 电子书

#### `bdt gh-book` — 抓取 GitHub 仓库书籍

```bash
bdt gh-book <url> [-t 线程数] [-p 代理] [-a article选择器]
```

`url` 为仓库的 `SUMMARY.md` 链接（开发建议使用 `blob/master/...` 形式），工具会读取目录并从同一仓库拉取每个章节生成 EPUB。`-a` 默认 `article`，对应 GitHub 内容页的 article 元素。

```bash
bdt gh-book https://github.com/user/repo/blob/master/SUMMARY.md
```

### 轻小说（wenku8）

需要 `WK8_COOKIE` 环境变量或 `-c` 指定 Cookie。

```bash
# 按更新时间抓取某时间区间更新的小说 id 列表
bdt fetch-ln ids.txt -s 20240101 -e 20240301

# 批量下载（ids.txt 每行一个 id），可指定线程数
bdt batch-ln ids.txt -s out -t 8

# 下载单本
bdt ln 123456 -s out
```

### 知乎

`zhihu-ques` / `zhihu-ques-batch` 通过官方 API（`api/v4/questions/{qid}/answers`）抓取问题下全部回答并生成 EPUB；`zhihu-topic` / `zhihu-topic-batch` 通过官方 API（`api/v5.1/topics/{tid}/feeds/new_question/v2`）抓取话题下的问题 id 列表；`zhihu-topics` 通过官方 API（`api/v3/topics/{tid}/children`）递归抓取子话题。三者都需要签名请求头（`x-zse-93` / `x-zse-96`，算法见 `doc/zhihu_sign.md`），Cookie 缺省用 `browser_cookie3` 从 Firefox/Chrome 浏览器提取，也可用 `-c` 显式传入。

```bash
# 抓取单个问题下全部回答，生成 EPUB（自动从浏览器取 Cookie）
bdt zhihu-ques 295617378

# 批量抓取（文件每行一个 qid）
bdt zhihu-ques-batch qids.txt

# 抓取单个话题下的问题，输出 qid 列表文件
bdt zhihu-topic 19550235

# 批量抓取话题（文件每行一个 tid）
bdt zhihu-topic-batch tids.txt

# 从根话题开始递归抓取所有子话题的 tid 列表
bdt zhihu-topics 19550235 -c "<zhihu cookie>"
```

典型流程：`zhihu-topics` 得到全部 tid → `zhihu-topic-batch` 得到全部 qid → `zhihu-ques-batch` 逐个生成 EPUB。

### 百度文库

通过文档预览图片生成 PDF，仅适用于当前账号/文档允许预览的页面。参数直接传入文档 `doc_id`：

```bash
# 下载全部可用预览页，并发数默认为 8
bdt wenku <doc_id> -d out

# 只下载前 5 页，并发下载
bdt wenku <doc_id> -s 1 -e 5 -t 8 -d out
```

也可以使用 `-o/--output` 指定 PDF 文件名；页面下载失败时不会生成不完整的 PDF。

### Discuz 论坛

```bash
# 抓取某个版块（fid）的帖子标题列表，fname 用于记录
bdt fetch-dz tids.txt example.com 2 -s 1 -e 50

# 批量下载（tids.txt 每行 "<host>\t<tid>"）
bdt batch-dz tids.txt -t 8 -o out

# 下载单个帖子（tid），可限制日期或抓全部楼层
bdt dz example.com 12345 -a -o out
```

- `bz batch-dz` / `dz` 生成 EPUB；超过 100MB 自动分卷为 `- pt1`、`- pt2` 等。
- `-l/--exi-list`（默认 `exi_dz.json`）记录已生成的 EPUB 名字，用于断点续传。

### 知识星球

```bash
# 下载圈子 id 在某时间段的全部内容，Cookie 默认取 $ZSXQ_COOKIE
bdt zsxq <group_id> -s 20240101 -e 20240801 -c "<cookie>"
```

### 整站抓取

```bash
# 爬取整个站点可达的 URL，存入 SQLite 数据库
bdt whole-site https://example.com example.db --re '/blog/' -t 8

# 从数据库导出全部 URL
bdt exp-whole-site example.db
```

- `--re` 用正则过滤要收录的链接；`--qs` 把 query string 也计入去重；`-B/--nonblank` 指定“必须非空”的选择器作为校验条件。

### 链接抓取与成书

```bash
# 分页抓取页面里的链接（{i} 为页码占位符），link 为 CSS 选择器
bdt links "https://blog.example.com/page/{i}" "article h2 a" links.txt -s 1 -e 20

# 抓取站点地图中的链接
bdt sitemap https://example.com/sitemap.xml -r "/blog/" -o links.txt

# 抓取 Wayback Machine 存档 URL
bdt web-archive example.com -s 1 -e 1000 -r "/blog/"

# 抓取 Medium 博客按日期发布列表
bdt medium xxx.medium.com -s 20150101 -e 20240801

# 把链接列表按 500 篇一卷批量转成 EPUB
bdt links-epub links.txt --name myblog -n 500
```

### 微信公众号

```bash
# fname 为公众号文章导出的 Excel（需包含：公众号、文章链接、发布时间 三列）
bdt wx articles.xlsx -n 500
```

按公众号分组、按月切片，每个切片生成一个 `config_<公众号>_<月份>.json` 并调用 EpubCrawler 生成 EPUB。

### 知识库 / 文档平台

```bash
# 语雀：整体知识库
bdt yuque user/book -c "<cookie>" -n "我的知识库"

# 语雀：批量（文件每行一个文章链接）
bdt batch-yuque links.txt -c "<cookie>"

# 飞书：单篇文档
bdt feishu https://xxx.feishu.cn/docx/xxxx -c "<cookie>"

# 飞书：wiki 下整棵节点树
bdt feishu-all https://xxx.feishu.cn/wiki/xxxx -c "<cookie>" -t 8

# 优矿：下载帖子（Markdown 或 IPython 笔记）
bdt uqer 123456
bdt batch-uqer tids.txt -t 8
```

- `feishu` / `feishu-all` 输出 Markdown（含图片目录 `img/`）；`feishu` 需要登录态 Cookie，否则会报错。
- `uqer` 输出为 `.md` 或 `.ipynb`。

### 学术

```bash
# 抓取指定分类、日期区间的 arXiv 论文 id（日期格式 yyyymmdd）
bdt arxiv-fetch cs.AI 20240101 20240301
```

### GitHub 搜索

```bash
# 用 GitHub API 搜索仓库，分页拉取全量并写入文件
bdt gh-repo-fetch "topic:book language:zh" repos.txt -t "$GH_TOKEN" -p "http://127.0.0.1:7890"
```

### 新闻聚合

```bash
bdt hkrnws-fetch 20240801                # 某一天的 hckrnews 链接
bdt hkrnws-range 20240801 20240831 -t 8  # 日期区间
```

### 图片

```bash
# 按关键词分页下载 Pixabay 图片
bdt pixabay sunset -d pics -s 1 -e 5 -t 8
```

### Anna's Archive

```bash
# 搜索，把结果写入 JSONL 列表
bdt annas-fetch "三体 clone" books.jsonl -s 1 -e 50 -l zh -x epub

# 下载单个文件（hash 为 annas-fetch 结果里的 md5）
bdt annas <hash>

# 批量下载 JSONL 列表，-s 指定镜像站（slow/bt/lgli）
bdt annas-batch books.jsonl -t 8 -s annas

# 按标题相似度就地去重 JSONL 列表（默认阈值 0.8）
bdt annas-dedup books.jsonl -s 0.8
```

### 辅助工具

```bash
# 从本机浏览器导出某域名的 Cookie（直接打印到标准输出）
bdt ext-cookies chrome zhihu.com
```

支持浏览器：`chrome, chromium, opera, opera_gx, brave, edge, vivaldi, firefox, librewolf, safari, lynx, w3m, arc`。导出的 Cookie 可作为其他命令的 `-c` 参数或环境变量使用。

### 小红书

```bash
# 搜索关键词，抓 1 页（每页 20 条），保存到 ./xhs/<关键词>/（自动含全量文字与图片）
bdt xhs 考研

# 抓 5 页、每页 50 条，保存到指定目录
bdt xhs 考研 -p 5 -n 50 -o xhs_data

# 不下载图片；显式提供 Cookie（含 a1 / web_session）
bdt xhs 考研 -p 2 --no-img -c "a1=...; web_session=..."
```

Cookie 默认自动从本机浏览器提取 `xiaohongshu.com` 的会话（`-b` 指定浏览器，默认 `chrome`）；也可用 `-c/--cookie` 或 `XHS_COOKIE` 环境变量显式提供。每篇笔记保存为 `<note_id>.md`（YAML 元信息 + 正文）与 `imgs/` 下的图片。

### Twitter

```bash
# 用 cookies.json 里的账号登录抓取关键词 openai
bdt twitter -k openai -c cookies.json

# 用 auth_token 登录，指定时间范围与语言，最多 500 条
bdt twitter -k gpt -l en --since 2024-06-01 --until 2024-06-30 --limit 500

# 把浏览器里已登录 x.com 的 cookie 导出为 cookies.json
bdt twitter -E cookies.json --browser chrome
```

`twitter` 基于 Scweet v5（`pip install scweet`）。需先配置登录态（`-c/--cookies-file`、`-t/--auth-token` 或 `--inline-cookies` 三选一），X 通常强制登录。结果保存为 CSV（默认）或 JSON。

---

## 常用工作流示例

**知乎：从话题到 EPUB 一条龙**

```bash
export WK8_COOKIE="$(bdt ext-cookies chrome zhihu.com)"
bdt zhihu-topics 19550235 -c "$WK8_COOKIE"          # 话题 tid 列表
bdt zhihu-topic-batch zhihu_all_topics_19550235.txt  # 问题 qid 列表
bdt zhihu-ques-batch zhihu_ques_*.txt                 # 每个问题生成 EPUB
```

**Discuz 论坛批量归档**

```bash
bdt fetch-dz tids.txt example.com 2 -s 1 -e 200
bdt batch-dz tids.txt -t 8 -a -o out
```

**整站链接入库**

```bash
bdt whole-site https://example.com example.db --re '/docs/' --qs
bdt exp-whole-site example.db > urls.txt
```

---

## 说明

- 绝大多数下载命令输出到**当前工作目录**（EPUB、txt、md、JSONL、`out/` 等），可用 `-o/--out`、`-d/--dir`、`-s/--save-path` 等参数指定输出位置。
- 使用代理的公共参数 `-p/--proxy`，如 `http://127.0.0.1:7890`；`freembook` 的 `-p` 支持用 `;` 分隔多个代理轮换。
- 需要浏览器环境的命令（Pixabay、Anna's Archive 单本下载）基于 Camoufox，首次运行会自动下载浏览器内核；知乎 `zhihu-ques` / `zhihu-topic` / `zhihu-topics` 系列已全部改用官方 API + 签名，不依赖浏览器。抓取时可用全局 `-H` 打开可见窗口观察行为。