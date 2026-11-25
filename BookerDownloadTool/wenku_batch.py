"""wenku-batch 子命令：读取 wenku-fetch 产出的 doc_id 列表，多线程批量下载 PDF。

复用 wenku 子命令的接口调用与页面下载逻辑（BookerDownloadTool/wenku.py），
全部实现为模块级函数，单文件即可运行。

用法示例
--------
    # 下载 ids.txt 中的全部文档（每个文档仅取前 3 页，便于快速验证）
    bdt wenku-batch ids.txt -d out -s 1 -e 3

    # 4 个文档并发、每个文档 8 页并发
    bdt wenku-batch ids.txt -d out --threads 4 --page-threads 8
"""
import os
import re
import tempfile
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from os import path
from typing import List

import img2pdf

from .util import default_hdrs
from .wenku import (
    _download_page,
    _output_title,
    build_page_url,
    fetch_doc_info,
    parse_doc_id,
)

# 输入文件里每行既可以是纯 doc_id，也可以是包含 /view/<doc_id>.html 的完整链接
DOC_ID_RE = re.compile(r'/view/([0-9a-fA-F]{16,64})')
PRINT_LOCK = threading.Lock()


def print_locked(msg: str) -> None:
    """多线程下串行打印，避免日志串行错乱。"""
    with PRINT_LOCK:
        print(msg, flush=True)


def read_doc_ids(fname: str) -> List[str]:
    """从文本文件读取 doc_id 列表（跳过空行、注释与非法行，自动去重）。

    每行可以是纯 doc_id，也可以是完整链接（含 `/view/<doc_id>.html`）。
    """
    doc_ids: List[str] = []
    seen = set()
    with open(fname, encoding='utf8') as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            matched = DOC_ID_RE.search(line)
            candidate = matched.group(1) if matched else line
            try:
                doc_id = parse_doc_id(candidate)
            except ValueError as ex:
                print_locked(f'跳过第 {lineno} 行（非法 doc_id）：{line}')
                continue
            if doc_id in seen:
                continue
            seen.add(doc_id)
            doc_ids.append(doc_id)
    return doc_ids


def pick_page_range(info: dict, start: int, end) -> tuple:
    """根据文档信息与用户指定的页码范围，确定实际可下载的页码列表。

    返回 (页码列表, 提示信息)；页码范围非法时抛出 ValueError。
    """
    available_end = max(info['page_ranges'])
    total_pages = info['total_pages']
    if end is None:
        last = min(total_pages, available_end)
        note = ''
    else:
        if end > total_pages:
            last = available_end
            note = f'结束页 {end} 超出文档总页数 {total_pages}，按预览上限截断到第 {last} 页'
        else:
            last = min(end, available_end)
            note = '' if last == end else f'预览仅到第 {available_end} 页，截断到第 {last} 页'
    if start < 1 or last < start:
        raise ValueError(f'页码范围无效（预览可用页 1~{available_end}，文档共 {total_pages} 页）')

    pages = list(range(start, last + 1))
    missing = [page for page in pages if page not in info['page_ranges']]
    if missing:
        raise ValueError(
            f'第 {missing[0]} 页没有预览图片（预览可用页 1~{available_end}）'
        )
    return pages, note


def download_doc(doc_id: str, args) -> dict:
    """下载单个文档的预览页并合成 PDF。

    返回 {'doc_id', 'status': 'ok'/'skipped', 'path', 'title', 'pages'}。
    """
    headers = default_hdrs.copy()
    headers['Referer'] = f'https://wenku.baidu.com/view/{doc_id}.html'

    info = fetch_doc_info(doc_id, headers=headers, proxy=args.proxy, retry=args.retries)
    pages, note = pick_page_range(info, args.start, args.end)
    if note:
        print_locked(f'提示：{doc_id} {note}')

    title = _output_title(info['title'], doc_id)
    output_path = path.join(args.dir, title + '.pdf')
    if path.exists(output_path) and not args.overwrite:
        return {'doc_id': doc_id, 'status': 'skipped', 'path': output_path,
                'title': title, 'pages': len(pages)}

    image_data = {}
    failures = []
    print_locked(f'[开始] {doc_id}：{title}（共 {len(pages)} 页）')
    with ThreadPoolExecutor(max_workers=args.page_threads) as pool:
        futures = {
            pool.submit(
                _download_page, page, build_page_url(info, page),
                headers, args.proxy, args.retries,
            ): page
            for page in pages
        }
        for future in as_completed(futures):
            page = futures[future]
            try:
                image_data[page] = future.result()
            except KeyboardInterrupt:
                raise
            except Exception as ex:
                failures.append((page, ex))

    if failures:
        detail = '; '.join(f'第 {page} 页: {ex}' for page, ex in sorted(failures))
        raise RuntimeError(f'页面下载失败，未生成 PDF：{detail}')

    pdf_data = img2pdf.convert([image_data[page] for page in pages])
    output_dir = path.dirname(path.abspath(output_path))
    os.makedirs(output_dir, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=output_dir, suffix='.pdf', delete=False) as temp:
            temp.write(pdf_data)
            temp_path = temp.name
        os.replace(temp_path, output_path)
    finally:
        if temp_path and path.exists(temp_path):
            os.unlink(temp_path)

    return {'doc_id': doc_id, 'status': 'ok', 'path': output_path,
            'title': title, 'pages': len(pages)}


def wenku_batch(args) -> dict:
    """主流程：读取 doc_id 列表 → 并发下载 → 汇总结果。"""
    if not path.isfile(args.file):
        raise FileNotFoundError(f'找不到输入文件：{args.file}')

    doc_ids = read_doc_ids(args.file)
    print_locked(f'共读取 {len(doc_ids)} 个文档 ID（来自 {args.file}）')
    if not doc_ids:
        print_locked('没有可下载的文档 ID')
        return {'ok': 0, 'skipped': 0, 'failed': 0}

    os.makedirs(args.dir, exist_ok=True)
    stats = Counter()
    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        futures = {pool.submit(download_doc, doc_id, args): doc_id for doc_id in doc_ids}
        for future in as_completed(futures):
            doc_id = futures[future]
            try:
                res = future.result()
            except KeyboardInterrupt:
                raise
            except Exception as ex:
                stats['failed'] += 1
                print_locked(f'[失败] {doc_id}：{ex}')
            else:
                if res['status'] == 'skipped':
                    stats['skipped'] += 1
                    print_locked(f'[跳过] {doc_id}：文件已存在 {res["path"]}')
                else:
                    stats['ok'] += 1
                    print_locked(f'[完成] {doc_id} → {res["path"]}（{res["pages"]} 页）')

    print_locked(f'汇总：成功 {stats["ok"]}，跳过 {stats["skipped"]}，失败 {stats["failed"]}')
    return {'ok': stats['ok'], 'skipped': stats['skipped'], 'failed': stats['failed']}


def wenku_batch_handle(args):
    """argparse 入口函数。"""
    return wenku_batch(args)


def reg_subparser(subparsers):
    """在子解析器中注册 wenku-batch 子命令。"""
    p = subparsers.add_parser(
        'wenku-batch', help='按 wenku-fetch 输出的 doc_id 列表批量下载百度文库文档 PDF')
    p.add_argument('file', help='doc_id 列表文件（wenku-fetch 的输出）')
    p.add_argument('-d', '--dir', default='.', help='输出目录，默认当前目录')
    p.add_argument('-s', '--start', type=int, default=1, help='起始页（从 1 开始），默认 1')
    p.add_argument('-e', '--end', type=int, help='结束页，默认至文档可预览的末页')
    p.add_argument('--threads', type=int, default=4, help='并发下载的文档数，默认 4')
    p.add_argument('--page-threads', type=int, default=4,
                   help='单个文档内并发下载的页数，默认 4（总并发数约为两者之积）')
    p.add_argument('--proxy', default='', help='HTTP/HTTPS 代理地址')
    p.add_argument('--retries', type=int, default=10, help='每页重试次数，默认 10')
    p.add_argument('--overwrite', action='store_true', help='覆盖已存在的 PDF（默认跳过）')
    p.set_defaults(func=wenku_batch_handle)
