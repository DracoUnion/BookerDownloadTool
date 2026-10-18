import json
import os
import re
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from os import path
from urllib.parse import parse_qsl, quote_plus

import img2pdf

from .util import default_hdrs, fname_escape, request_retry

INFO_URL = 'https://wenku.baidu.com/api/doc/getdocinfo'
ZOOM_URL = 'https://wkretype.bdimg.com/retype/zoom/{store_id}'


def parse_doc_id(value):
    """校验百度文库文档 ID。"""
    value = value.strip()
    if not re.fullmatch(r'[0-9a-fA-F]{16,64}', value):
        raise ValueError('doc_id 必须是 16 至 64 位十六进制字符串，请直接传入文档 ID')
    return value


def _parse_jsonp(text):
    """解析 getdocinfo 返回的 JSONP。"""
    start = text.find('(')
    end = text.rfind(')')
    if start < 0 or end <= start:
        raise ValueError('文库信息接口返回格式异常（不是有效 JSONP）')
    try:
        return json.loads(text[start + 1:end])
    except json.JSONDecodeError as ex:
        raise ValueError('文库信息接口返回了无效 JSON') from ex


def _parse_query_fragment(value):
    if not value:
        return {}
    return dict(parse_qsl(value.lstrip('&?'), keep_blank_values=True))


def fetch_doc_info(doc_id, headers=None, proxy=None, retry=10):
    headers = headers or default_hdrs.copy()
    headers.setdefault('Referer', f'https://wenku.baidu.com/view/{doc_id}.html')
    proxies = {'http': proxy, 'https': proxy} if proxy else None
    response = request_retry(
        'GET', INFO_URL,
        params={'callback': 'cb', 'doc_id': doc_id},
        headers=headers,
        proxies=proxies,
        retry=retry,
        check_status=True,
    )
    info = _parse_jsonp(response.text)
    doc_info = info.get('docInfo')
    if not isinstance(doc_info, dict):
        raise ValueError('文档不存在或当前不可预览')

    store_id = info.get('doc_id_update') or doc_info.get('doc_id_update')
    if not store_id:
        raise ValueError('接口未返回文档预览存储 ID')

    md5_params = _parse_query_fragment(info.get('md5sum') or doc_info.get('md5sum'))
    md5sum = md5_params.get('md5sum')
    if not md5sum:
        raise ValueError('接口未返回文档预览 md5sum')

    page_ranges = {}
    for entry in info.get('bcsParam') or doc_info.get('bcsParam') or []:
        try:
            page_num = int(entry['page'])
        except (KeyError, TypeError, ValueError):
            continue
        ranges = _parse_query_fragment(entry.get('zoom'))
        if 'jpg' in ranges and 'png' in ranges:
            page_ranges[page_num] = ranges

    if not page_ranges:
        raise ValueError('接口未返回可用的预览图片列表')

    try:
        total_pages = int(doc_info.get('totalPageNum') or info.get('page') or 0)
    except (TypeError, ValueError):
        total_pages = 0
    if total_pages <= 0:
        total_pages = max(page_ranges)

    title = doc_info.get('docTitle') or doc_info.get('title') or doc_id
    return {
        'doc_id': doc_id,
        'title': title,
        'store_id': store_id,
        'md5sum': md5sum,
        'sign': md5_params.get('sign', ''),
        'total_pages': total_pages,
        'page_ranges': page_ranges,
    }


def build_page_url(info, page):
    ranges = info['page_ranges'].get(page)
    if not ranges:
        raise ValueError(f'接口未提供第 {page} 页的预览图片范围')

    params = {
        'pn': page,
        'o': 'jpg_6',
        'md5sum': info['md5sum'],
        'sign': info['sign'],
        'png': ranges['png'],
        'jpg': ranges['jpg'],
        'highRes': 'true',
    }
    query = '&'.join(f'{key}={quote_plus(str(value))}' for key, value in params.items())
    return f"{ZOOM_URL.format(store_id=info['store_id'])}?{query}"


def _download_page(page, url, headers, proxy, retry):
    proxies = {'http': proxy, 'https': proxy} if proxy else None
    response = request_retry(
        'GET', url,
        headers=headers,
        proxies=proxies,
        retry=retry,
        check_status=True,
    )
    data = response.content
    if not data.startswith(b'\xff\xd8\xff'):
        raise ValueError(f'第 {page} 页接口响应不是有效 JPEG 图片')
    return data


def _output_title(title, doc_id):
    title = fname_escape(str(title or '').strip()).strip().rstrip('. ')
    return title or doc_id


def download_wenku(args):
    try:
        doc_id = parse_doc_id(args.doc_id)
        headers = default_hdrs.copy()
        headers['Referer'] = f'https://wenku.baidu.com/view/{doc_id}.html'
        info = fetch_doc_info(doc_id, headers=headers, proxy=args.proxy, retry=args.retry)

        start = args.start
        available_end = max(info['page_ranges'])
        end = args.end if args.end is not None else min(info['total_pages'], available_end)
        if start < 1 or end < start:
            raise ValueError('页码范围无效，请确保 1 <= 起始页 <= 结束页')
        if end > info['total_pages']:
            raise ValueError(f'结束页 {end} 超出文档总页数 {info["total_pages"]}')
        if args.end is None and available_end < info['total_pages']:
            print(f'提示：预览接口当前提供到第 {available_end} 页（文档共 {info["total_pages"]} 页）')

        pages = list(range(start, end + 1))
        missing = [page for page in pages if page not in info['page_ranges']]
        if missing:
            preview_max = max(info['page_ranges'])
            raise ValueError(
                f'预览接口未提供第 {missing[0]} 页的图片范围（当前返回到第 {preview_max} 页）；'
                '请缩小页码范围或确认该文档是否允许预览这些页面'
            )

        output_dir = args.dir
        os.makedirs(output_dir, exist_ok=True)
        if args.output:
            output_path = args.output
            if not path.isabs(output_path):
                output_path = path.join(output_dir, output_path)
            if not output_path.lower().endswith('.pdf'):
                output_path += '.pdf'
        else:
            output_path = path.join(output_dir, _output_title(info['title'], doc_id) + '.pdf')

        if path.exists(output_path) and not args.overwrite:
            raise FileExistsError(f'输出文件已存在：{output_path}（使用 --overwrite 覆盖）')

        image_data = {}
        failures = []
        with ThreadPoolExecutor(max_workers=args.threads) as pool:
            futures = {
                pool.submit(
                    _download_page, page, build_page_url(info, page),
                    headers, args.proxy, args.retry,
                ): page
                for page in pages
            }
            for future in as_completed(futures):
                page = futures[future]
                try:
                    image_data[page] = future.result()
                    print(f'已下载第 {page}/{end} 页')
                except KeyboardInterrupt:
                    raise
                except Exception as ex:
                    failures.append((page, ex))

        if failures:
            detail = '; '.join(f'第 {page} 页: {ex}' for page, ex in sorted(failures))
            raise RuntimeError(f'页面下载失败，未生成 PDF：{detail}')

        pdf_data = img2pdf.convert([image_data[page] for page in pages])
        output_dirname = path.dirname(path.abspath(output_path))
        os.makedirs(output_dirname, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile('wb', dir=output_dirname, suffix='.pdf', delete=False) as temp:
                temp.write(pdf_data)
                temp_path = temp.name
            os.replace(temp_path, output_path)
        finally:
            if temp_path and path.exists(temp_path):
                os.unlink(temp_path)

        print(f'已保存 PDF：{output_path}')
    except KeyboardInterrupt:
        raise
    except Exception as ex:
        print(f'文库下载失败：{ex}')


def reg_subparser(subparsers):
    wenku_parser = subparsers.add_parser('wenku', help='下载百度文库预览文档为 PDF')
    wenku_parser.add_argument('doc_id', help='百度文库文档 ID（十六进制字符串）')
    wenku_parser.add_argument('-o', '--output', default='', help='输出 PDF 文件名或路径')
    wenku_parser.add_argument('-d', '--dir', default='.', help='输出目录')
    wenku_parser.add_argument('-s', '--start', type=int, default=1, help='起始页（从 1 开始）')
    wenku_parser.add_argument('-e', '--end', type=int, help='结束页（默认至文档末页）')
    wenku_parser.add_argument('-t', '--threads', type=int, default=8, help='并发线程数')
    wenku_parser.add_argument('-r', '--retry', type=int, default=10, help='每页重试次数')
    wenku_parser.add_argument('-p', '--proxy', default='', help='HTTP/HTTPS 代理地址')
    wenku_parser.add_argument('--overwrite', action='store_true', help='覆盖已有 PDF 文件')
    wenku_parser.set_defaults(func=download_wenku)
