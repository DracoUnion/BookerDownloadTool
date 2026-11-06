#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
so.py — 按问题编号区间并发抓取 Stack Overflow 问题页，输出 Markdown。

直接使用 requests 抓取 https://stackoverflow.com/questions/{编号} 的网页 HTML，
用 pyquery 解析标题 / 赞同数 / 时间 / 标签 / 正文与回答，并按 doc/so_tmpl.md
的模板渲染为 Markdown。编号不存在（404）的页面自动跳过。

Stack Overflow 前面有 Cloudflare，匿名直连通常会被拦截，因此推荐传入 Cookie
（``-ck``，即浏览器里 stackoverflow.com 的 Cookie 字符串，含 cf_clearance），
或直接把本机浏览器里的 Cookie 读出来使用。

用法示例
--------
    # 下载 11227800~11227900，输出到默认目录 so_11227800_11227900
    bdt so -s 11227800 -e 11227900

    # 指定输出目录与线程数
    bdt so -s 11227800 -e 11227900 -o ./stackoverflow -th 8

    # 传入 Cookie
    bdt so -s 11227800 -e 11227900 -ck "cf_clearance=...; __cf_bm=..."

    # 指定从 firefox 读取 Cookie（不指定时按 firefox→chrome→edge 尝试）
    bdt so -s 11227800 -e 11227900 -b firefox
"""

import os
import re
import sys
import time
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, wait, as_completed, FIRST_COMPLETED
from datetime import datetime
from html.parser import HTMLParser

import tqdm
import requests
from pyquery import PyQuery as pq

from .util import cookie_str_to_dict, fname_escape
from .ext_cookie import extract_cookies

SO_HOST = 'https://stackoverflow.com'

DEFAULT_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
)

DEFAULT_HEADERS = {
    'User-Agent': DEFAULT_UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
              'image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


# ─────────────────────────── HTML → Markdown ───────────────────────────

class _HtmlToMarkdown(HTMLParser):
    """轻量的 HTML→Markdown 转换器，覆盖 SO 正文常见标签。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0
        self.pre = 0
        self.href = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'button', 'svg', 'noscript', 'template'):
            self.skip += 1
            return
        if self.skip:
            return
        d = dict(attrs)
        if tag == 'br':
            self.out.append('\n')
        elif tag in ('p', 'div', 'section', 'article'):
            self.out.append('\n\n')
        elif tag == 'pre':
            self.out.append('\n```\n')
            self.pre += 1
        elif tag == 'code':
            if not self.pre:
                self.out.append('`')
        elif tag in ('strong', 'b'):
            self.out.append('**')
        elif tag in ('em', 'i'):
            self.out.append('*')
        elif tag == 'a':
            href = d.get('href')
            self.href.append(href)
            if href:
                self.out.append('[')
        elif tag == 'img':
            self.out.append(f"![{d.get('alt', '')}]({d.get('src', '')})")
        elif tag == 'li':
            self.out.append('\n- ')
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.out.append('\n\n' + '#' * int(tag[1]) + ' ')
        elif tag == 'blockquote':
            self.out.append('\n> ')
        elif tag == 'hr':
            self.out.append('\n\n---\n\n')
        elif tag == 'tr':
            self.out.append('\n')
        elif tag in ('td', 'th'):
            self.out.append(' | ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'button', 'svg', 'noscript', 'template'):
            if self.skip:
                self.skip -= 1
            return
        if self.skip:
            return
        if tag == 'pre':
            self.out.append('\n```\n')
            self.pre = max(0, self.pre - 1)
        elif tag == 'code':
            if not self.pre:
                self.out.append('`')
        elif tag in ('strong', 'b'):
            self.out.append('**')
        elif tag in ('em', 'i'):
            self.out.append('*')
        elif tag == 'a':
            href = self.href.pop() if self.href else None
            if href:
                self.out.append(f']({href})')
        elif tag in ('p', 'div', 'section', 'article', 'li', 'tr',
                     'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.out.append('\n')

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)

    def get_markdown(self):
        text = ''.join(self.out)
        # 去掉代码围栏内容首尾多余的空行，保留围栏与正文之间的空行
        text = re.sub(
            r'```\n(.*?)\n```',
            lambda m: '```\n' + m.group(1).strip('\n') + '\n```',
            text,
            flags=re.S,
        )
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = '\n'.join(line.rstrip() for line in text.split('\n'))
        return text.strip()


def html_to_md(html):
    if not html:
        return ''
    parser = _HtmlToMarkdown()
    try:
        parser.feed(html)
    except Exception:
        return re.sub(r'<[^>]+>', '', html).strip()
    return parser.get_markdown()


# ─────────────────────────── 解析 ───────────────────────────

def _fmt_time(value):
    """把 SO 的 '2012-06-27 13:51:36Z' 规范成可读时间。"""
    if not value:
        return ''
    value = str(value).strip()
    for fmt in ('%Y-%m-%d %H:%M:%SZ', '%Y-%m-%dT%H:%M:%SZ'):
        try:
            return datetime.strptime(value, fmt).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass
    return value


def _action_time(scope, keyword):
    """从 .user-action-time 中取出包含 keyword 的时间（title 属性）。"""
    for el in scope.find('.user-action-time'):
        el = pq(el)
        if keyword in el.text():
            rel = el.find('.relativetime').eq(0)
            if rel:
                return rel.attr('title') or rel.text().strip()
    return ''


def parse_question(html, qid):
    doc = pq(html)
    q = doc('#question')
    if not q:
        return None

    title_el = doc('#question-header h1 a.question-hyperlink')
    if not title_el:
        title_el = doc('h1 a.question-hyperlink')
    title = title_el.eq(0).text().strip()
    if not title:
        return None

    qid2 = q.attr('data-questionid') or str(qid)
    score = q.attr('data-score')
    if score is None:
        score = doc('#question .js-vote-count').eq(0).text().strip()

    q_time = _action_time(q, 'asked')
    if not q_time:
        rel = doc('#question .relativetime').eq(0)
        q_time = (rel.attr('title') or rel.text().strip()) if rel else ''

    tags = [pq(t).text().strip() for t in doc('#question a.post-tag')]
    body = html_to_md(doc('#question .js-post-body').eq(0).html() or '')

    answers = []
    for el in doc('div.answer[id^="answer-"]'):
        a = pq(el)
        aid = (a.attr('id') or '').replace('answer-', '')
        a_score = a.find('.js-vote-count').eq(0).text().strip()
        t = a.find('time').eq(0)
        a_time = (t.attr('datetime') or t.text().strip()) if t else ''
        if not a_time:
            a_time = _action_time(a, 'answered')
        a_body = html_to_md(a.find('.js-post-body').eq(0).html() or '')
        answers.append({
            'id': aid,
            'score': a_score,
            'time': _fmt_time(a_time),
            'body': a_body,
        })

    return {
        'id': qid2,
        'title': title,
        'score': score,
        'time': _fmt_time(q_time),
        'tags': tags,
        'body': body,
        'answers': answers,
    }


def render_markdown(item):
    """按 doc/so_tmpl.md 的模板渲染。"""
    lines = [f"# {item['title']}", '']
    lines += [
        f"> ID：{item['id']}",
        '> ',
        f"> 赞同：{item['score']}",
        '> ',
        f"> 时间：{item['time']}",
        '> ',
        f"> 标签：{', '.join(item['tags'])}",
        '',
    ]
    if item['body']:
        lines += [item['body'], '']
    lines += ['* * *', '']
    for i, ans in enumerate(item['answers'], 1):
        lines += [
            f"## 回答 #{i}",
            '',
            f"> 赞同：{ans['score']}",
            '> ',
            f"> 时间：{ans['time']}",
            '',
        ]
        if ans['body']:
            lines += [ans['body'], '']
    return '\n'.join(lines).rstrip() + '\n'


# ─────────────────────────── 抓取 ───────────────────────────

def _is_cf_challenge(text):
    low = (text or '').lower()
    return (
        'just a moment' in low
        or 'cf_chl' in low
        or 'enable javascript and cookies to continue' in low
    )


def _load_cookies(args):
    if args.cookie:
        cookies = cookie_str_to_dict(args.cookie)
        if not cookies:
            sys.exit('[错误] 无法解析 -ck/--cookie，请提供形如 "k1=v1; k2=v2" 的字符串')
        print(f'[INFO] 使用命令行 Cookie: {sorted(cookies)}')
        return cookies

    browsers = [args.browser] if args.browser else ['firefox', 'chrome', 'edge']
    for br in browsers:
        try:
            cookies = extract_cookies(br, 'stackoverflow.com')
        except Exception:
            cookies = {}
        if cookies:
            print(f'[INFO] 已从浏览器 {br} 提取 Cookie: {sorted(cookies)}')
            return cookies

    print('[警告] 未获取到 Cookie，将以匿名方式请求（可能被 Cloudflare 拦截）')
    return {}


_tls = threading.local()


def _get_session(cookies):
    if not hasattr(_tls, 'session'):
        session = requests.Session()
        session.cookies.update(cookies)
        session.headers.update(DEFAULT_HEADERS)
        _tls.session = session
    return _tls.session


def _fetch_curl_cffi(url, cookies):
    """requests 被 Cloudflare 拦截时，用 curl_cffi 再做一次 TLS 模拟请求。"""
    try:
        from curl_cffi import requests as cr
    except Exception:
        return None, None
    for imp in ('firefox', 'chrome'):
        try:
            session = cr.Session(impersonate=imp)
            session.cookies.update(cookies)
            # 不覆盖 User-Agent，让 impersonate 使用与 TLS 指纹匹配的 UA
            r = session.get(url, headers={'Accept-Language': 'en-US,en;q=0.9'}, timeout=60)
            if r.status_code == 200 and not _is_cf_challenge(r.text):
                return 200, r.text
        except Exception:
            pass
    return None, None


def fetch_html(url, cookies, retry=3):
    """返回 (状态, HTML)。状态: 200 / 404 / 403(Cloudflare) / 其他。"""
    session = _get_session(cookies)
    last_status = 0
    for i in range(retry):
        try:
            r = session.get(url, timeout=(30, 60))
        except Exception as e:
            print(f'[重试] {url} {type(e).__name__}')
            time.sleep(1 + i)
            continue

        last_status = r.status_code
        if r.status_code == 404:
            return 404, ''

        if r.status_code == 200 and not _is_cf_challenge(r.text):
            return 200, r.text

        if _is_cf_challenge(r.text):
            status, html = _fetch_curl_cffi(url, cookies)
            if status == 200:
                return 200, html
            return 403, r.text

        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 + i)
            continue

        return r.status_code, r.text

    return last_status, ''


def _download_one(qid, outdir, cookies):
    url = f'{SO_HOST}/questions/{qid}'
    status, html = fetch_html(url, cookies)

    if status == 404:
        return '404', qid, ''
    if status == 403:
        return 'blocked', qid, ''
    if status != 200 or not html:
        return 'error', qid, f'HTTP {status}'

    low = html.lower()
    if not pq(html)('#question'):
        if 'page not found' in low or "couldn't find" in low or 'no longer available' in low:
            return '404', qid, ''
        return 'error', qid, '页面中找不到 #question'

    item = parse_question(html, qid)
    if item is None:
        return '404', qid, ''

    fname = os.path.join(outdir, fname_escape(item['id']) + '.md')
    tmp = f'{fname}.{qid}.tmp'
    with open(tmp, 'w', encoding='utf8') as f:
        f.write(render_markdown(item))
    os.replace(tmp, fname)
    return 'ok', qid, fname


# ─────────────────────────── 主流程 ───────────────────────────

def so_download(args):
    if args.start > args.end:
        sys.exit('[错误] 起始编号不能大于终止编号')

    outdir = args.outdir or f'so_{args.start}_{args.end}'
    os.makedirs(outdir, exist_ok=True)
    cookies = _load_cookies(args)

    total = args.end - args.start + 1
    print('=' * 60)
    print(f'[INFO] 问题区间 : {args.start} ~ {args.end}（共 {total} 个）')
    print(f'[INFO] 输出目录 : {outdir}')
    print(f'[INFO] 线程数   : {args.threads}')
    print('=' * 60)

    stats = Counter()
    written = []

    def handle(fut):
        try:
            status, qid, info = fut.result()
        except Exception as e:
            status, qid, info = 'error', None, f'{type(e).__name__}: {e}'
        stats[status] += 1
        if status == 'ok':
            written.append(info)
        elif status == 'blocked':
            print(f'[WARN] {qid} 被 Cloudflare 拦截，跳过（请提供有效 Cookie）')
        elif status == 'error':
            print(f'[WARN] {qid} 抓取失败: {info}')

    max_pending = max(1, args.threads) * 4
    with ThreadPoolExecutor(max_workers=args.threads) as pool, \
            tqdm.tqdm(total=total) as bar:
        pending = {}
        for qid in range(args.start, args.end + 1):
            pending[pool.submit(_download_one, qid, outdir, cookies)] = qid
            if len(pending) >= max_pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for fut in done:
                    handle(fut)
                    pending.pop(fut, None)
                    bar.update(1)
        for fut in as_completed(pending):
            handle(fut)
            bar.update(1)

    print('-' * 60)
    print(f"[完成] 成功 {stats['ok']}，404 跳过 {stats['404']}，"
          f"被拦截 {stats['blocked']}，失败 {stats['error']}")
    print(f'[完成] 输出目录: {outdir}')
    if written:
        print(f'[完成] 示例文件: {written[0]}')


def reg_subparser(subparsers):
    p = subparsers.add_parser('so', help='按编号区间抓取 Stack Overflow 问题页')
    p.add_argument('-s', '--start', type=int, required=True, help='起始问题编号')
    p.add_argument('-e', '--end', type=int, required=True, help='终止问题编号')
    p.add_argument('-o', '--outdir', default=None,
                   help='输出目录，默认 so_{起始编号}_{终止编号}')
    p.add_argument('-ck', '--cookie', default=None,
                   help='Cookie 字符串，如 "cf_clearance=...; __cf_bm=..."')
    p.add_argument('-b', '--browser', default=None,
                   choices=['firefox', 'chrome', 'chromium', 'edge', 'opera', 'opera_gx',
                            'brave', 'vivaldi', 'librewolf', 'safari', 'arc'],
                   help='从指定浏览器读取 Cookie（默认依次尝试 firefox→chrome→edge）')
    p.add_argument('-th', '--threads', type=int, default=8, help='并发线程数')
    p.set_defaults(func=so_download)
