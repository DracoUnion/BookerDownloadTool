# -*- coding: utf-8 -*-
"""Kaggle 比赛笔记本抓取与 EPUB 生成。

流程：
  1. 复用浏览器（抓包得到）的网页内部接口，列出比赛下的全部公开笔记本。
     列表接口即浏览器「Code」页实际调用的
     https://www.kaggle.com/api/i/kernels.KernelsService/ListKernels。
  2. 用 kernels/pull 接口逐个拉取笔记本源码（.ipynb）。
  3. 把 markdown / 代码 / 输出（含图片）渲染成 HTML 章节。
  4. 抓取正文图片，调用 GenEpub 生成 EPUB。

说明：本子命令不要求 Kaggle API 凭据（username/key）。网页内部接口只需要一套
会话 Cookie（ka_sessionid / XSRF-TOKEN / CLIENT-TOKEN），按下面的优先级获取：
  1. -c/--cookie 显式传入从浏览器抓包得到的 Cookie 字符串；
  2. 从本机浏览器（已登录或已访问过 kaggle.com）自动提取；
  3. 都没有时自动访问一次比赛页面，领取一套匿名会话（公开比赛无需登录）。
kernels/pull 本身公开可用，因此也可用 -f/--file 或 --url 直接指定笔记本。
"""
import re
import json
import html
import time
import base64
import traceback

import requests

from EpubCrawler.img import process_img
from EpubCrawler.config import config as crawler_config
from GenEpub import gen_epub

from .util import fname_escape, cookie_str_to_dict
from .ext_cookie import extract_cookies_multi_browsers

KAGGLE_WEB = 'https://www.kaggle.com'
KAGGLE_API = KAGGLE_WEB + '/api/v1'   # 公开 REST 接口（kernels/pull 无需凭据）
KAGGLE_I = KAGGLE_WEB + '/api/i'      # 网页内部接口（浏览器抓包得到的那套）
KERNELS_LIST_PATH = '/kernels.KernelsService/ListKernels'
GET_COMPETITION_PATH = '/competitions.CompetitionService/GetCompetition'
KERNELS_PULL_URL = KAGGLE_API + '/kernels/pull'
# 内部接口用浏览器 UA；公开 REST 接口用官方客户端 UA（避免 WAF 判定为浏览器请求）。
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36')
API_UA = 'kaggle-api/1.6.17'
PAGE_SIZE = 100
RE_KERNEL_URL = re.compile(r'kaggle\.com/code/([^/?#]+)/([^/?#]+)')


# ---------------------------------------------------------------------------
# 会话 / 请求
# ---------------------------------------------------------------------------

def _proxies(proxy):
    return {'http': proxy, 'https': proxy} if proxy else None


def new_session(args, slug):
    """创建带 Kaggle 会话 Cookie 的 requests.Session。

    Cookie 优先级：-c/--cookie > 本机浏览器 > 自动领取匿名会话。整个流程不需要
    Kaggle API 凭据，等价于浏览器抓包后原样复用内部接口。
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': UA,
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': KAGGLE_WEB,
    })

    cookies = cookie_str_to_dict(getattr(args, 'cookie', '') or '') \
        if getattr(args, 'cookie', '') else {}
    if cookies:
        print('[INFO] 使用 --cookie 提供的 Kaggle Cookie')
    else:
        try:
            cookies = extract_cookies_multi_browsers('kaggle.com') or {}
        except Exception:
            traceback.print_exc()
            cookies = {}
        if cookies:
            print(f'[INFO] 已从本机浏览器提取 Kaggle Cookie: {sorted(cookies)}')

    for name, value in cookies.items():
        session.cookies.set(name, value, domain='.kaggle.com')

    # 缺会话/防伪 Cookie 时访问一次比赛页面，让服务端下发一套匿名会话。
    if not cookies or 'XSRF-TOKEN' not in session.cookies:
        page_url = f'{KAGGLE_WEB}/competitions/{slug}/code'
        try:
            session.get(page_url, timeout=30, proxies=_proxies(args.proxy))
            print('[INFO] 已访问比赛页面获取/刷新 Kaggle 会话 Cookie')
        except Exception:
            traceback.print_exc()

    if 'XSRF-TOKEN' not in session.cookies:
        raise SystemExit(
            '无法获取 Kaggle 会话 Cookie。请先在浏览器打开 https://www.kaggle.com '
            '（并登录），或用 -c/--cookie 传入抓包得到的 Cookie 字符串。')
    return session


def kaggle_i_post(session, api_path, payload, retry=5, timeout=30, proxy=None):
    """调用网页内部 API（与浏览器抓包到的 ListKernels 等请求一致）。

    使用 JSON 编码，携带会话 Cookie 与 X-XSRF-TOKEN 请求头；自动重试。
    """
    url = KAGGLE_I + api_path
    last_ex = None
    for i in range(retry):
        try:
            hdrs = {'X-XSRF-TOKEN': session.cookies.get('XSRF-TOKEN', '')}
            r = session.post(
                url, json=payload, headers=hdrs,
                timeout=timeout, proxies=_proxies(proxy),
            )
            if r.status_code == 200 and 'json' in r.headers.get('content-type', ''):
                return r.json()
            if r.status_code == 200 and 'recaptcha' in r.text[:3000].lower():
                last_ex = RuntimeError('被 Kaggle reCAPTCHA 拦截')
            else:
                last_ex = RuntimeError(
                    f'HTTP {r.status_code}: {r.text[:300]}')
            print(f'{api_path} retry {i}: {last_ex}')
        except KeyboardInterrupt:
            raise
        except Exception as ex:
            last_ex = ex
            print(f'{api_path} retry {i}: {ex}')
        time.sleep(2 + i * 2)
    raise last_ex


def kaggle_request(method, url, params=None, retry=5, timeout=30, proxy=None):
    """调用公开 REST 接口（自动重试）。

    即使没有凭据也发送一个占位的 Basic 认证头：Kaggle 对匿名 API 请求可能返回
    reCAPTCHA 页面，而带认证头的请求会返回正常 JSON（kernels/pull 不校验凭据）。
    """
    token = base64.b64encode(b'anonymous:none').decode('ascii')
    hdrs = {
        'User-Agent': API_UA,
        'Accept': 'application/json',
        'Authorization': 'Basic ' + token,
    }
    last_ex = None
    for i in range(retry):
        try:
            r = requests.request(
                method, url, params=params, headers=hdrs,
                timeout=timeout, proxies=_proxies(proxy),
            )
            if r.status_code == 200 and 'json' in r.headers.get('content-type', ''):
                return r.json()
            if r.status_code == 200 and 'recaptcha' in r.text[:3000].lower():
                last_ex = RuntimeError('被 Kaggle reCAPTCHA 拦截')
            else:
                last_ex = RuntimeError(
                    f'HTTP {r.status_code}: {r.text[:200]}')
            print(f'{url} retry {i}: {last_ex}')
        except KeyboardInterrupt:
            raise
        except Exception as ex:
            last_ex = ex
            print(f'{url} retry {i}: {ex}')
        time.sleep(2 + i * 2)
    raise last_ex


# ---------------------------------------------------------------------------
# 笔记本列表 / 拉取
# ---------------------------------------------------------------------------

def parse_kernel_ref(text):
    """把 owner/slug 或 Kaggle 笔记本 URL 转成 (user, slug)。"""
    text = (text or '').strip()
    m = RE_KERNEL_URL.search(text)
    if m:
        return m.group(1), m.group(2)
    if '/' in text:
        user, slug = text.split('/', 1)
        return user.strip(), slug.split('?')[0].strip()
    return None


def _list_request_body(competition_id, page, page_size, sort_by):
    """构建 ListKernels 内部接口的请求体（与浏览器抓包得到的结构一致）。"""
    return {
        'kernelFilterCriteria': {
            'search': '',
            'listRequest': {
                'competitionId': competition_id,
                'sortBy': sort_by,
                'pageSize': page_size,
                'group': 'EVERYONE',
                'page': page,
                'modelIds': [],
                'modelInstanceIds': [],
                'excludeKernelIds': [],
                'tagIds': '',
                'excludeResultsFilesOutputs': False,
                'wantOutputFiles': False,
                'excludeNonAccessedDatasources': True,
            },
        },
        'detailFilterCriteria': {
            'deletedAccessBehavior': 'RETURN_NOTHING',
            'unauthorizedAccessBehavior': 'RETURN_NOTHING',
            'excludeResultsFilesOutputs': False,
            'wantOutputFiles': False,
            'kernelIds': [],
            'outputFileTypes': [],
            'includeInvalidDataSources': False,
        },
    }


def get_competition_id(slug, session, retry=5, proxy=None):
    """把比赛 slug 转成内部的数字 id。"""
    data = kaggle_i_post(
        session, GET_COMPETITION_PATH, {'competitionName': slug},
        retry=retry, proxy=proxy,
    )
    if isinstance(data, dict) and isinstance(data.get('id'), (int, str)):
        return data['id']
    raise RuntimeError(f'无法解析比赛 id: {data!r}')


def list_competition_kernels(slug, session, sort_by='HOTNESS', retry=5,
                             proxy=None, page_size=PAGE_SIZE, limit=None):
    """分页列出比赛下的全部公开笔记本，返回 [{'ref': 'user/slug', 'title': ...}]。

    走网页内部接口 ListKernels，只需要会话 Cookie，不需要 Kaggle API 凭据。
    limit 给定后，获取到足够的 ref 就提前停止。
    """
    competition_id = get_competition_id(slug, session, retry=retry, proxy=proxy)
    print(f'比赛 {slug} 的内部 id 为 {competition_id}')

    refs, seen = [], set()
    page = 1
    while True:
        data = kaggle_i_post(
            session, KERNELS_LIST_PATH,
            _list_request_body(competition_id, page, page_size, sort_by),
            retry=retry, proxy=proxy,
        )
        if isinstance(data, dict):
            data = data.get('kernels', [])
        if not isinstance(data, list):
            raise RuntimeError(f'无法解析笔记本列表响应: {data!r}')
        if not data:
            break
        for it in data:
            ref = it.get('ref') or ''
            if not ref:
                author = it.get('author') or {}
                kslug = it.get('currentUrlSlug') or it.get('slug') or ''
                user = author.get('userName') if isinstance(author, dict) else author
                if user and kslug:
                    ref = f'{user}/{kslug}'
            if ref and ref not in seen:
                seen.add(ref)
                refs.append({'ref': ref, 'title': it.get('title', '')})
        print(f'已获取 {len(refs)} 个笔记本（page {page}）')
        if len(data) < page_size:
            break
        if limit and len(refs) >= limit:
            break
        page += 1
    return refs


def resolve_kernel_refs(args, session=None):
    """按 --file / --url / 比赛 slug 的顺序解析笔记本 ref。"""
    refs, seen = [], set()

    def add(user, slug):
        ref = f'{user}/{slug}'
        if user and slug and ref not in seen:
            seen.add(ref)
            refs.append({'ref': ref, 'title': ''})

    if args.file:
        for line in open(args.file, encoding='utf8'):
            line = line.split('#')[0].strip()
            if not line:
                continue
            parsed = parse_kernel_ref(line)
            if parsed:
                add(*parsed)
            else:
                print(f'忽略无法解析的行: {line}')

    for item in args.url or []:
        parsed = parse_kernel_ref(item)
        if parsed:
            add(*parsed)
        else:
            print(f'忽略无法解析的 URL: {item}')

    if not refs:
        if session is None:
            session = new_session(args, args.slug)
        refs = list_competition_kernels(
            args.slug, session, sort_by=args.sort,
            retry=args.retry, proxy=args.proxy, limit=args.num)
    return refs


def pull_kernel(user, slug, retry=5, proxy=None):
    """拉取单个笔记本，返回 (metadata, blob)。"""
    return kaggle_request(
        'GET', KERNELS_PULL_URL,
        params={'userName': user, 'kernelSlug': slug},
        retry=retry, proxy=proxy,
    )


# ---------------------------------------------------------------------------
# .ipynb -> HTML
# ---------------------------------------------------------------------------

def nb_source(val):
    """notebook 的 source/text 字段可能是字符串或行列表。"""
    if isinstance(val, list):
        return ''.join(str(x) for x in val)
    return '' if val is None else str(val)


def markdown_to_html(text):
    try:
        import markdown
        return markdown.markdown(text, extensions=['extra', 'sane_lists'])
    except Exception:
        return '<pre>' + html.escape(text) + '</pre>'


def md_cell_html(cell):
    """渲染 markdown 单元，并把 attachment:<name> 换成 data URL。"""
    src = nb_source(cell.get('source'))
    for name, mimes in (cell.get('attachments') or {}).items():
        for mime, data in mimes.items():
            src = src.replace('attachment:' + name, f'data:{mime};base64,{data}')
            break
    # 附件缺失时不要留下 attachment: 假 URL，否则会被当成远程图片下载
    src = re.sub(r'attachment:[^\s)\'"]+', '', src)
    return markdown_to_html(src)


def sanitize_html(text):
    """去掉输出 HTML 里的脚本/事件处理器，避免 EPUB 中执行或引用外部资源。"""
    text = re.sub(
        r'<(script|style|iframe|object|embed|form)\b[\s\S]*?</\1>',
        '', text, flags=re.I)
    text = re.sub(r'\son\w+\s*=\s*"[^"]*"', '', text, flags=re.I)
    text = re.sub(r"\son\w+\s*=\s*'[^']*'", '', text, flags=re.I)
    return text


def output_html(output):
    otype = output.get('output_type')
    if otype == 'stream':
        return '<pre>' + html.escape(nb_source(output.get('text'))) + '</pre>'
    if otype == 'error':
        tb = '\n'.join(output.get('traceback') or [])
        return '<pre class="error">' + html.escape(tb) + '</pre>'

    data = output.get('data') or {}
    for mime in ('image/png', 'image/jpeg', 'image/gif'):
        if mime in data:
            return (f'<p><img src="data:{mime};base64,'
                    f'{nb_source(data[mime])}"></p>')
    if 'text/html' in data:
        return sanitize_html(nb_source(data['text/html']))
    if 'text/plain' in data:
        return '<pre>' + html.escape(nb_source(data['text/plain'])) + '</pre>'
    if 'application/json' in data:
        try:
            val = json.dumps(data['application/json'],
                             ensure_ascii=False, indent=2)
        except Exception:
            val = str(data['application/json'])
        return '<pre>' + html.escape(val) + '</pre>'
    return ''


def notebook_to_html(nb):
    parts = []
    for cell in nb.get('cells') or []:
        ctype = cell.get('cell_type')
        if ctype == 'markdown':
            parts.append(md_cell_html(cell))
        elif ctype == 'code':
            code = nb_source(cell.get('source'))
            # 图片输出通常是 base64 data URL，交给 process_img 统一处理
            parts.append('<pre><code class="language-python">' +
                         html.escape(code) + '</code></pre>')
            for out in cell.get('outputs') or []:
                parts.append(output_html(out))
        elif ctype == 'raw':
            parts.append('<pre>' + html.escape(nb_source(cell.get('source'))) +
                         '</pre>')
    return '\n'.join(p for p in parts if p)


def kernel_to_article(meta, blob):
    """把 kernels/pull 的响应转成 GenEpub 的 article 结构。"""
    meta = meta or {}
    blob = blob or {}
    slug = blob.get('slug') or meta.get('slug') or ''
    author = (meta.get('ref') or '').split('/')[0]
    title = meta.get('title') or slug or 'Untitled'

    source = blob.get('source') or ''
    is_notebook = blob.get('kernelType') == 'notebook' or \
        source.lstrip().startswith('{')
    if is_notebook:
        try:
            body = notebook_to_html(json.loads(source))
        except Exception:
            traceback.print_exc()
            body = '<pre>' + html.escape(source) + '</pre>'
    else:
        body = '<pre><code>' + html.escape(source) + '</code></pre>'

    url = f'{KAGGLE_WEB}/code/{author}/{slug}' if author and slug else KAGGLE_WEB
    content = (f'<blockquote>来源：<a href="{url}">{url}</a></blockquote>\n'
               + body)
    return {'title': title, 'content': content}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def fetch_kaggle(args):
    crawler_config['optiMode'] = 'none'
    crawler_config['imgSrc'] = ['data-src', 'src']

    # 只有需要按比赛列出笔记本时才建立会话；-f/--url 直接指定时无需 Cookie。
    refs = resolve_kernel_refs(args, session=None)
    if not refs:
        print('没有找到任何笔记本')
        return

    refs = refs[:args.num]
    articles, imgs = [], {}
    for i, item in enumerate(refs, 1):
        ref = item['ref']
        user, slug = ref.split('/', 1)
        print(f'[{i}/{len(refs)}] 拉取 {ref}')
        try:
            data = pull_kernel(
                user, slug, retry=args.retry, proxy=args.proxy)
            article = kernel_to_article(
                data.get('metadata'), data.get('blob'))
        except KeyboardInterrupt:
            raise
        except Exception:
            traceback.print_exc()
            continue

        page_url = f'{KAGGLE_WEB}/code/{ref}'
        try:
            article['content'] = process_img(
                article['content'], imgs,
                img_prefix='../Images/',
                page_url=page_url,
            )
        except Exception:
            traceback.print_exc()
        articles.append(article)

    if not articles:
        print('没有成功获取任何笔记本')
        return

    name = f'Kaggle {args.slug}'
    out = args.out or fname_escape(name) + '.epub'
    gen_epub(articles, imgs, name=name, path=out)
    print(f'已生成 {out}，共 {len(articles)} 章')


def reg_subparser(subparsers):
    parser = subparsers.add_parser(
        "kaggle", help="抓取 Kaggle 比赛笔记本并生成 EPUB")
    parser.add_argument("slug", help="比赛 slug，如 titanic")
    parser.add_argument(
        "-o", "--out", help="输出 EPUB 路径（默认 Kaggle <slug>.epub）")
    parser.add_argument(
        "-n", "--num", type=int, default=20, help="最多导出的笔记本数量 (默认 20)")
    parser.add_argument(
        "-c", "--cookie", default='',
        help="浏览器抓包得到的 Cookie 字符串（默认自动读取本机浏览器/匿名会话）")
    parser.add_argument(
        "--sort", default='HOTNESS',
        help="网页笔记本排序方式（默认 HOTNESS，如 DATE_CREATED/VOTE_COUNT）")
    parser.add_argument(
        "-f", "--file", help="笔记本 ref 列表文件（每行 owner/slug 或 Kaggle URL）")
    parser.add_argument(
        "--url", action='append', default=[],
        help="额外指定笔记本 URL/ref，可重复")
    parser.add_argument("-p", "--proxy", help="代理")
    parser.add_argument("-r", "--retry", type=int, default=5, help="重试次数")
    parser.set_defaults(func=fetch_kaggle)
