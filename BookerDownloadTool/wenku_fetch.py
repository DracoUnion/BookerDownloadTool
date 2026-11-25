"""wenku-fetch 子命令：搜索百度文库文档，把结果文档 ID 写入文件。

逆向自百度文库 PC 端搜索页前端接口 `POST /gsearch/search/newallsearch`（详见
doc/wenku_search_api.md）。全部实现为函数，无分层（无 agent/编排器）。
"""
import html
import json
import logging
import os
import re
import time
from os import path
from typing import List, Optional

import requests
from pydantic import BaseModel, Field

from .util import default_hdrs, fname_escape, gen_objs_md5, read_yaml_model, request_retry, write_yaml_model

logger = logging.getLogger(__name__)

SEARCH_URL = 'https://wenku.baidu.com/gsearch/search/newallsearch'
DOC_URL_TMPL = 'https://wenku.baidu.com/view/{doc_id}.html'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

# 筛选参数取值（与文库前端筛选面板一致）
FORMAT_ALL = 0
FORMAT_DOC = 1
FORMAT_PDF = 2
FORMAT_PPT = 3
FORMAT_XLS = 4
FORMAT_TXT = 5

TYPE_ALL = 0
TYPE_VIP = 1
TYPE_FREE = 3
TYPE_QUALITY = 4

SORT_RELEVANCE = 0
SORT_NEWEST = 1
SORT_MOST_DOWNLOAD = 2
SORT_HIGHEST_SCORE = 3

RESOURCE_BOOK = 11

CARD_TYPE_DOC = 'wk_doc'
DEFAULT_CACHE_DIR = '.wenku-fetch-cache'


# ── 数据模型 ──────────────────────────────────────────────

class WenkuDoc(BaseModel):
    """百度文库搜索结果中的一个文档"""
    doc_id: str = Field(..., description='文档唯一标识（十六进制字符串）')
    title: str = Field(..., description='文档标题（已去除 HTML 高亮标签）')
    url: str = Field(..., description='文档详情页链接')
    abstract: str = Field('', description='文档摘要（已去除 HTML 高亮标签）')
    file_type: int = Field(0, description='文档格式类型编号，如 4 为 docx、6 为 pptx')
    page_num: int = Field(0, description='文档页数')
    download_count: int = Field(0, description='下载次数')
    view_count: int = Field(0, description='阅读次数')
    author: str = Field('', description='文档作者名')
    create_time: int = Field(0, description='文档创建时间（Unix 时间戳）')
    quality_score: float = Field(0, description='文档质量评分')
    sell_type: int = Field(0, description='文档售卖类型编号')
    copyable: bool = Field(False, description='正文是否可复制')
    tag_list: List[str] = Field(default_factory=list, description='文档标签列表')


class WenkuSearchResult(BaseModel):
    """某个关键词的搜索结果"""
    keyword: str = Field(..., description='搜索关键词')
    page: int = Field(1, description='已抓取的页码数')
    total: int = Field(0, description='搜索结果总数')
    docs: List[WenkuDoc] = Field(default_factory=list, description='搜索结果文档列表')


# ── 工具函数 ──────────────────────────────────────────────

def strip_highlight(text: str) -> str:
    """去掉标题/摘要里的 <em> 高亮标签并反转义实体。"""
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', '', text)
    return html.unescape(text).strip()


def default_output_name(keyword: str) -> str:
    """默认输出文件名：{关键词}.txt（非法文件名字符会被转义）。"""
    return fname_escape(keyword.strip()) + '.txt'


# ── 接口调用 ──────────────────────────────────────────────

def _get_session() -> requests.Session:
    """获取会话（预热文库首页 Cookie，降低被风控拦截概率）。"""
    s = requests.Session()
    s.headers.update({
        'User-Agent': UA,
        'Referer': 'https://wenku.baidu.com/search',
        'Origin': 'https://wenku.baidu.com',
    })
    try:
        s.get('https://wenku.baidu.com/', timeout=15)
    except requests.RequestException as ex:
        logger.debug('文库首页预热失败：%s', ex)
    return s


def search_page(keyword: str, page: int, page_size: int,
                fmt: int = FORMAT_ALL, ftype: int = TYPE_ALL,
                sort: int = SORT_RELEVANCE, book: bool = False,
                retry: int = 10, proxy: str = '') -> dict:
    """请求一页搜索结果，返回接口的 result 字段。"""
    body = {
        'word': keyword,
        'pn': page,
        'rn': page_size,
        'fr': 'wkSearch',
        'lm': fmt,
        'fd': RESOURCE_BOOK if book else ftype,
        'od': sort,
    }

    headers = dict(default_hdrs)
    headers['User-Agent'] = UA
    headers['Content-Type'] = 'application/json'
    headers['Referer'] = 'https://wenku.baidu.com/search'

    proxies = {'http': proxy, 'https': proxy} if proxy else None

    s = _get_session()
    response = request_retry(
        'POST', SEARCH_URL,
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers=headers,
        proxies=proxies,
        retry=retry,
        check_status=True,
    )
    try:
        payload = response.json()
    except ValueError as ex:
        raise ValueError('文库搜索接口返回了非 JSON 内容') from ex

    status = payload.get('status') or {}
    if status.get('code') != 0:
        raise ValueError(
            f'文库搜索接口返回错误：code={status.get("code")} msg={status.get("msg")}'
        )
    data = payload.get('data') or {}
    return data.get('result') or {}


def parse_doc(item: dict) -> Optional[WenkuDoc]:
    """把一个结果卡片转换为 WenkuDoc；非文档卡片返回 None。"""
    if not isinstance(item, dict) or item.get('card_type') != CARD_TYPE_DOC:
        return None
    data = item.get('data') or {}
    doc_id = (data.get('docID') or item.get('docId') or '').strip()
    if not doc_id:
        return None

    author_info = data.get('authorInfo') or {}
    author_verify = data.get('authorVerify') or {}
    author = (author_info.get('name') or author_verify.get('username') or '').strip()

    def _int(value) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _float(value) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    return WenkuDoc(
        doc_id=doc_id,
        title=strip_highlight(data.get('title') or item.get('title') or ''),
        url=DOC_URL_TMPL.format(doc_id=doc_id),
        abstract=strip_highlight(data.get('content') or item.get('abstract') or ''),
        file_type=_int(data.get('fileType')),
        page_num=_int(data.get('pageNum')),
        download_count=_int(data.get('downloadCount')),
        view_count=_int(data.get('viewCount')),
        author=author,
        create_time=_int(data.get('createTime')),
        quality_score=_float(data.get('qualityScore')),
        sell_type=_int(data.get('sellType')),
        copyable=bool(data.get('copyable')),
        tag_list=[str(tag) for tag in (data.get('tagList') or [])],
    )


# ── 搜索 ──────────────────────────────────────────────────

def _cache_fname(cache_dir: str, keyword: str, pages: int, page_size: int,
                 fmt: int, ftype: int, sort: int, book: bool) -> str:
    key = gen_objs_md5(keyword, pages, page_size, fmt, ftype, sort, book)
    return path.join(cache_dir, f'search_{key}.yaml')


def search_docs(keyword: str, pages: int = 1, page_size: int = 10,
                fmt: int = FORMAT_ALL, ftype: int = TYPE_ALL,
                sort: int = SORT_RELEVANCE, book: bool = False,
                sleep: float = 0.5, retry: int = 10, proxy: str = '',
                cache_dir: str = '', use_cache: bool = True,
                refresh: bool = False) -> WenkuSearchResult:
    """按关键词搜索文档（最多 pages 页），跨页去重，带文件缓存。"""
    use_cache = use_cache and bool(cache_dir)
    cache_fname = _cache_fname(cache_dir, keyword, pages, page_size,
                               fmt, ftype, sort, book) if cache_dir else ''

    if use_cache and not refresh:
        cached = read_yaml_model(cache_fname, WenkuSearchResult)
        if cached:
            logger.info('命中缓存：%s', cache_fname)
            return cached

    docs: List[WenkuDoc] = []
    seen = set()
    total = 0
    for page in range(1, pages + 1):
        logger.info('搜索第 %d/%d 页：%s', page, pages, keyword)
        result = search_page(keyword, page, page_size,
                             fmt=fmt, ftype=ftype, sort=sort,
                             book=book, retry=retry, proxy=proxy)
        items = result.get('items') or []
        extra = result.get('extra') or {}
        total = extra.get('total') or total
        for item in items:
            doc = parse_doc(item)
            if doc is None or doc.doc_id in seen:
                continue
            seen.add(doc.doc_id)
            docs.append(doc)
        if not items:
            logger.info('第 %d 页无结果，提前结束', page)
            break
        if page < pages:
            time.sleep(sleep)

    res = WenkuSearchResult(keyword=keyword, page=pages, total=total, docs=docs)
    if use_cache and cache_dir:
        write_yaml_model(cache_fname, res)
    return res


# ── 输出 ────────────────────────────────────────────────

def write_links(res: WenkuSearchResult, output: str) -> str:
    """把文档 ID 写入输出文件（一行一个 doc_id）。"""
    ofname = output or default_output_name(res.keyword)
    outdir = path.dirname(path.abspath(ofname))
    os.makedirs(outdir, exist_ok=True)
    ids = [doc.doc_id for doc in res.docs if doc.doc_id]
    with open(ofname, 'w', encoding='utf8') as f:
        f.write('\n'.join(ids) + ('\n' if ids else ''))
    logger.info('已写入 %d 条 doc_id：%s', len(ids), ofname)
    print(f'已保存 {len(ids)} 条文档 ID：{ofname}')
    return ofname


# ── 主流程 ──────────────────────────────────────────────

def wenku_fetch(keyword: str, output: str = '', pages: int = 1,
                page_size: int = 10, fmt: int = FORMAT_ALL,
                ftype: int = TYPE_ALL, sort: int = SORT_RELEVANCE,
                book: bool = False, proxy: str = '', retry: int = 10,
                sleep: float = 0.5, cache_dir: str = '',
                use_cache: bool = True, refresh: bool = False) -> str:
    """完整流程：搜索文档 → 写入链接文件。返回输出文件名。"""
    keyword = keyword.strip()
    if not keyword:
        raise ValueError('关键词不能为空')
    if not cache_dir:
        cache_dir = DEFAULT_CACHE_DIR

    logger.info('开始搜索：%s（共 %d 页，每页 %d 条）', keyword, pages, page_size)
    res = search_docs(keyword, pages, page_size,
                      fmt=fmt, ftype=ftype, sort=sort, book=book,
                      sleep=sleep, retry=retry, proxy=proxy,
                      cache_dir=cache_dir, use_cache=use_cache,
                      refresh=refresh)
    logger.info('搜索完成：%d 条文档（接口报告总数 %d）', len(res.docs), res.total)
    if not res.docs:
        logger.warning('未搜索到任何文档')
    return write_links(res, output)


# ── 命令行入口 ────────────────────────────────────────────

def wenku_fetch_handle(args):
    """argparse 入口函数：创建日志并运行主流程。"""
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, 'debug', False) else logging.INFO,
        format='[%(asctime)s][%(name)s][%(levelname)s] %(message)s',
    )
    return wenku_fetch(
        keyword=args.keyword,
        output=getattr(args, 'output', '') or '',
        pages=getattr(args, 'pages', 1),
        page_size=getattr(args, 'page_size', 10),
        fmt=getattr(args, 'format', FORMAT_ALL),
        ftype=getattr(args, 'type', TYPE_ALL),
        sort=getattr(args, 'sort', SORT_RELEVANCE),
        book=getattr(args, 'book', False),
        proxy=getattr(args, 'proxy', '') or '',
        retry=getattr(args, 'retries', 10),
        sleep=getattr(args, 'sleep', 0.5),
        cache_dir=getattr(args, 'cache_dir', '') or '',
        use_cache=not getattr(args, 'no_cache', False),
        refresh=getattr(args, 'refresh', False),
    )


def reg_subparser(subparsers):
    """在子解析器中注册 wenku-fetch 子命令。"""
    p = subparsers.add_parser(
        'wenku-fetch', help='搜索百度文库文档，把结果文档 ID 保存到文件')
    p.add_argument('keyword', help='搜索关键词')
    p.add_argument('-o', '--output', default='',
                   help='输出文件名，默认 {关键词}.txt')
    p.add_argument('-n', '--pages', type=int, default=1,
                   help='抓取页数，默认 1')
    p.add_argument('-s', '--page-size', type=int, default=10,
                   help='每页条数，默认 10')
    p.add_argument('--format', type=int, default=FORMAT_ALL,
                   help='格式筛选：0 不限 / 1 doc / 2 pdf / 3 ppt / 4 xls / 5 txt')
    p.add_argument('--type', type=int, default=TYPE_ALL,
                   help='类型筛选：0 不限 / 1 VIP专享 / 3 免费 / 4 精品')
    p.add_argument('--sort', type=int, default=SORT_RELEVANCE,
                   help='排序：0 最高相关 / 1 最新上线 / 2 最多下载 / 3 最高评分')
    p.add_argument('--book', action='store_true', help='搜索图书而非文档')
    p.add_argument('--proxy', default='', help='HTTP/HTTPS 代理地址')
    p.add_argument('--retries', type=int, default=10, help='请求重试次数，默认 10')
    p.add_argument('--sleep', type=float, default=0.5,
                   help='相邻页请求间隔秒数，默认 0.5')
    p.add_argument('--cache-dir', default='',
                   help=f'缓存目录，默认 {DEFAULT_CACHE_DIR}')
    p.add_argument('--no-cache', action='store_true', help='不使用缓存')
    p.add_argument('--refresh', action='store_true', help='忽略已有缓存并重新抓取')
    p.set_defaults(func=wenku_fetch_handle)
