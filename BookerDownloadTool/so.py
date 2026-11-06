#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
so.py — 按问题编号区间抓取 Stack Overflow 问题与回答，输出 Markdown。

使用 Stack Exchange API（https://api.stackexchange.com/2.3）批量获取问题与回答，
再按 doc/so_tmpl.md 的模板渲染为 Markdown。编号不存在（已删除/非法）的问题会被
API 直接忽略，等价于跳过 404。API 匿名配额较小，可通过 --api-key 传入 Stack
Apps 的 key 提升配额。

用法示例
--------
    # 下载 11227800~11227900，输出到默认目录 so_11227800_11227900
    bdt so -s 11227800 -e 11227900

    # 指定输出目录与并发数
    bdt so -s 11227800 -e 11227900 -o ./stackoverflow -th 8

    # 使用 Stack Apps API key（可提升每日配额）
    bdt so -s 11227800 -e 11227900 --api-key YOUR_KEY
"""

import os
import re
import sys
import time
import html as html_lib
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser

import tqdm
import requests

from .util import fname_escape

API_BASE = 'https://api.stackexchange.com/2.3'
SITE = 'stackoverflow'
# 单次请求最多 100 个 id；答案单页最多 100 条
CHUNK_SIZE = 100
PAGE_SIZE = 100

DEFAULT_HEADERS = {
    'User-Agent': 'BookerDownloadTool-so/1.0',
    'Accept': 'application/json',
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


# ─────────────────────────── API ───────────────────────────

_tls = threading.local()
_quota = {'remaining': None}


def _get_session():
    if not hasattr(_tls, 'session'):
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        _tls.session = session
    return _tls.session


def api_get(path, params, api_key=None, retry=5):
    """调用 Stack Exchange API，处理 backoff / 配额 / 限流重试。"""
    session = _get_session()
    query = dict(params, site=SITE)
    if api_key:
        query['key'] = api_key

    for i in range(retry):
        try:
            r = session.get(f'{API_BASE}/{path}', params=query, timeout=(30, 60))
        except requests.RequestException as e:
            print(f'[重试] {path}: {type(e).__name__}')
            time.sleep(2 + i)
            continue

        if r.status_code == 200:
            data = r.json()
            if data.get('quota_remaining') is not None:
                _quota['remaining'] = data['quota_remaining']
            if data.get('backoff'):
                time.sleep(int(data['backoff']))
            if data.get('error_id'):
                msg = data.get('error_message', '')
                # 限流/拥挤时退避重试
                if data['error_id'] == 502 or 'throttle' in msg.lower():
                    time.sleep(5 * (i + 1))
                    continue
                raise RuntimeError(f"API 错误 {data['error_id']}: {msg}")
            return data

        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 + i)
            continue

        raise RuntimeError(f'API 请求失败 HTTP {r.status_code}: {r.text[:200]}')

    raise RuntimeError(f'API 重试耗尽: {path}')


def _chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def fetch_questions(qids, api_key=None):
    """批量获取问题；不存在的 id 会被 API 忽略。"""
    ids = ';'.join(str(q) for q in qids)
    data = api_get(f'questions/{ids}', {'filter': 'withbody'}, api_key)
    return data.get('items', [])


def fetch_answers(qids, api_key=None):
    """批量获取这些问题下的回答，按赞同数降序，自动翻页。"""
    ids = ';'.join(str(q) for q in qids)
    answers = []
    page = 1
    while True:
        data = api_get(
            f'questions/{ids}/answers',
            {
                'filter': 'withbody',
                'sort': 'votes',
                'order': 'desc',
                'pagesize': PAGE_SIZE,
                'page': page,
            },
            api_key,
        )
        answers.extend(data.get('items', []))
        if not data.get('has_more'):
            break
        page += 1
    return answers


# ─────────────────────────── 渲染 ───────────────────────────

def _fmt_epoch(value):
    if not value:
        return ''
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc) \
            .strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError, OSError):
        return str(value)


def build_item(question, answers):
    """把 API 返回的问题与回答组装成模板所需的结构。"""
    return {
        'id': str(question.get('question_id', '')),
        'title': html_lib.unescape(question.get('title', '')).strip(),
        'score': question.get('score', ''),
        'time': _fmt_epoch(question.get('creation_date')),
        'tags': [html_lib.unescape(t) for t in (question.get('tags') or [])],
        'body': html_to_md(question.get('body', '')),
        'answers': [
            {
                'id': str(a.get('answer_id', '')),
                'score': a.get('score', ''),
                'time': _fmt_epoch(a.get('creation_date')),
                'body': html_to_md(a.get('body', '')),
            }
            for a in answers
        ],
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


# ─────────────────────────── 下载 ───────────────────────────

def process_chunk(qids, outdir, api_key=None):
    """处理一批问题 id，返回 (成功数, 跳过数, 写出的文件列表)。"""
    questions = fetch_questions(qids, api_key)
    if not questions:
        return 0, len(qids), []

    found_ids = [q['question_id'] for q in questions]
    answers = fetch_answers(found_ids, api_key)

    grouped = defaultdict(list)
    for a in answers:
        grouped[a.get('question_id')].append(a)

    written = []
    for q in questions:
        item = build_item(q, grouped.get(q['question_id'], []))
        fname = os.path.join(outdir, fname_escape(item['id']) + '.md')
        tmp = f'{fname}.{os.getpid()}.{threading.get_ident()}.tmp'
        with open(tmp, 'w', encoding='utf8') as f:
            f.write(render_markdown(item))
        os.replace(tmp, fname)
        written.append(fname)

    return len(questions), len(qids) - len(questions), written


# ─────────────────────────── 主流程 ───────────────────────────

def so_download(args):
    if args.start > args.end:
        sys.exit('[错误] 起始编号不能大于终止编号')

    outdir = args.outdir or f'so_{args.start}_{args.end}'
    os.makedirs(outdir, exist_ok=True)

    qids = list(range(args.start, args.end + 1))
    chunks = list(_chunks(qids, CHUNK_SIZE))
    total = len(qids)

    print('=' * 60)
    print(f'[INFO] 问题区间 : {args.start} ~ {args.end}（共 {total} 个）')
    print(f'[INFO] 输出目录 : {outdir}')
    print(f'[INFO] 并发数   : {args.threads}')
    print(f'[INFO] API Key  : {"已设置" if args.api_key else "未设置（匿名配额较小）"}')
    print('=' * 60)

    stats = Counter()
    written = []

    with ThreadPoolExecutor(max_workers=args.threads) as pool, \
            tqdm.tqdm(total=len(chunks)) as bar:
        futures = {
            pool.submit(process_chunk, chunk, outdir, args.api_key): chunk
            for chunk in chunks
        }
        for fut in as_completed(futures):
            chunk = futures[fut]
            try:
                ok, skipped, files = fut.result()
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f'[WARN] 批次 {chunk[0]}~{chunk[-1]} 失败: {e}')
                stats['error'] += len(chunk)
            else:
                stats['ok'] += ok
                stats['skipped'] += skipped
                written.extend(files)
            bar.update(1)

    remaining = _quota['remaining']
    print('-' * 60)
    print(f"[完成] 成功 {stats['ok']}，跳过 {stats['skipped']}（不存在/已删除），"
          f"失败 {stats['error']}")
    if remaining is not None:
        print(f'[完成] API 剩余配额: {remaining}')
    print(f'[完成] 输出目录: {outdir}')
    if written:
        print(f'[完成] 示例文件: {written[0]}')


def reg_subparser(subparsers):
    p = subparsers.add_parser('so', help='按编号区间抓取 Stack Overflow 问题与回答')
    p.add_argument('-s', '--start', type=int, required=True, help='起始问题编号')
    p.add_argument('-e', '--end', type=int, required=True, help='终止问题编号')
    p.add_argument('-o', '--outdir', default=None,
                   help='输出目录，默认 so_{起始编号}_{终止编号}')
    p.add_argument('--api-key', default=None,
                   help='Stack Apps API key（可选，可提升每日配额）')
    p.add_argument('-th', '--threads', type=int, default=4, help='并发批次数')
    p.set_defaults(func=so_download)
