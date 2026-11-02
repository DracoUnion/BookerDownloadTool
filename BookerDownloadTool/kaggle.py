# -*- coding: utf-8 -*-
"""Kaggle 比赛笔记本抓取与 EPUB 生成。

流程：
  1. 访问 https://www.kaggle.com/competitions/<slug>/code 对应的官方接口，
     列出比赛下的全部公开笔记本（需要 Kaggle API 凭据）。
  2. 用 kernels/pull 接口逐个拉取笔记本源码（.ipynb）。
  3. 把 markdown / 代码 / 输出（含图片）渲染成 HTML 章节。
  4. 抓取正文图片，调用 GenEpub 生成 EPUB。

说明：Kaggle 网页接口对匿名请求会返回 reCAPTCHA 挑战，列表接口必须带
Kaggle API 凭据（https://www.kaggle.com/settings -> API -> Create New Token，
把 kaggle.json 放到 ~/.kaggle/ 或设置 KAGGLE_USERNAME/KAGGLE_KEY）。
kernels/pull 本身公开可用，因此也可用 -f/--file 或 --url 直接指定笔记本。
"""
import os
import re
import json
import html
import time
import base64
import traceback
from os import path

from EpubCrawler.img import process_img
from EpubCrawler.config import config as crawler_config
from GenEpub import gen_epub

from .util import fname_escape

KAGGLE_API = 'https://www.kaggle.com/api/v1'
KERNELS_LIST_URL = KAGGLE_API + '/kernels/list'
KERNELS_PULL_URL = KAGGLE_API + '/kernels/pull'
KAGGLE_WEB = 'https://www.kaggle.com'
# 官方 API 客户端的 UA。注意不要用完整的 Chrome UA：Kaggle 的 WAF 会把它当成
# 未完成 reCAPTCHA 的浏览器请求并返回挑战页，而 API UA 可以正常拿到 JSON。
UA = 'kaggle-api/1.6.17'
PAGE_SIZE = 100
RE_KERNEL_URL = re.compile(r'kaggle\.com/code/([^/?#]+)/([^/?#]+)')


# ---------------------------------------------------------------------------
# 凭据 / 请求
# ---------------------------------------------------------------------------

def read_kaggle_auth(args):
    """读取 Kaggle API 凭据：命令行 > 环境变量 > ~/.kaggle/kaggle.json。

    返回 (username, key)，没有配置时返回 None。
    """
    username = (getattr(args, 'kg_user', '') or
                os.environ.get('KAGGLE_USERNAME') or
                os.environ.get('KAGGLE_USER') or '')
    key = (getattr(args, 'kg_key', '') or
           os.environ.get('KAGGLE_KEY') or '')
    if username and key:
        return username, key

    cfg = path.expanduser(path.join('~', '.kaggle', 'kaggle.json'))
    if path.isfile(cfg):
        try:
            data = json.load(open(cfg, encoding='utf8'))
            if data.get('username') and data.get('key'):
                return data['username'], data['key']
        except Exception:
            traceback.print_exc()
    return None


def kaggle_request(method, url, auth=None, params=None, retry=5,
                   timeout=30, proxy=None):
    """带 Kaggle API 认证的请求（自动重试）。

    即使没有凭据也发送一个占位的 Basic 认证头：Kaggle 对匿名 API 请求会返回
    reCAPTCHA 页面，而带认证头的请求会返回正常的 JSON（kernels/pull 不校验凭据）。
    """
    import requests

    username, key = auth if auth else ('anonymous', 'none')
    token = base64.b64encode(f'{username}:{key}'.encode('utf8')).decode('ascii')
    hdrs = {
        'User-Agent': UA,
        'Accept': 'application/json',
        'Authorization': 'Basic ' + token,
    }
    proxies = {'http': proxy, 'https': proxy} if proxy else None
    last_ex = None
    for i in range(retry):
        try:
            r = requests.request(
                method, url, params=params, headers=hdrs,
                timeout=timeout, proxies=proxies,
            )
            if r.status_code == 200 and 'json' in r.headers.get('content-type', ''):
                return r.json()
            if r.status_code == 200 and 'recaptcha' in r.text[:3000]:
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


def list_competition_kernels(slug, auth, retry=5, proxy=None):
    """分页列出比赛下的全部公开笔记本，返回 [{'ref': 'user/slug', 'title': ...}]。"""
    if not auth:
        raise SystemExit(
            '列出比赛笔记本需要 Kaggle API 凭据。请设置 KAGGLE_USERNAME/KAGGLE_KEY，'
            f'或把 kaggle.json 放到 {path.expanduser("~/.kaggle/kaggle.json")}；'
            '也可以先用 -f refs.txt / --url 指定笔记本。')

    refs, seen = [], set()
    page = 1
    while True:
        data = kaggle_request(
            'GET', KERNELS_LIST_URL, auth=auth,
            params={
                'competition': slug,
                'page': page,
                'pageSize': PAGE_SIZE,
                'sortBy': 'voteCount',
            },
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
                author, kslug = it.get('author'), it.get('slug')
                if author and kslug:
                    ref = f'{author}/{kslug}'
            if ref and ref not in seen:
                seen.add(ref)
                refs.append({'ref': ref, 'title': it.get('title', '')})
        print(f'已获取 {len(refs)} 个笔记本（page {page}）')
        if len(data) < PAGE_SIZE:
            break
        page += 1
    return refs


def resolve_kernel_refs(args):
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
        auth = read_kaggle_auth(args)
        refs = list_competition_kernels(
            args.slug, auth, retry=args.retry, proxy=args.proxy)
    return refs


def pull_kernel(user, slug, auth=None, retry=5, proxy=None):
    """拉取单个笔记本，返回 (metadata, blob)。"""
    return kaggle_request(
        'GET', KERNELS_PULL_URL, auth=auth,
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

    auth = read_kaggle_auth(args)
    refs = resolve_kernel_refs(args)
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
                user, slug, auth=auth,
                retry=args.retry, proxy=args.proxy)
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
        "--kg-user", default='', help="Kaggle 用户名（默认读环境变量/kaggle.json）")
    parser.add_argument(
        "--kg-key", default='', help="Kaggle API Key（默认读环境变量/kaggle.json）")
    parser.add_argument(
        "-f", "--file", help="笔记本 ref 列表文件（每行 owner/slug 或 Kaggle URL）")
    parser.add_argument(
        "--url", action='append', default=[],
        help="额外指定笔记本 URL/ref，可重复")
    parser.add_argument("-p", "--proxy", help="代理")
    parser.add_argument("-r", "--retry", type=int, default=5, help="重试次数")
    parser.set_defaults(func=fetch_kaggle)
