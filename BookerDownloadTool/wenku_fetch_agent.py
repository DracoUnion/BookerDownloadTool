"""wenku-fetch 子命令的智能体：调用百度文库搜索接口获取文档列表。

接口来源：百度文库 PC 端搜索页（https://wenku.baidu.com/search?word=...）的前端
代码调用 `POST /gsearch/search/newallsearch`，请求体为 JSON，详见
doc/wenku_search_api.md。
"""
import html
import json
import logging
import re
import time
from os import path
from typing import List, Optional

import requests

from .util import (
    default_hdrs,
    gen_objs_md5,
    read_yaml_model,
    request_retry,
    write_yaml_model,
)
from .wenku_fetch_models import WenkuDoc, WenkuSearchResult

logger = logging.getLogger(__name__)

SEARCH_URL = 'https://wenku.baidu.com/gsearch/search/newallsearch'
DOC_URL_TMPL = 'https://wenku.baidu.com/view/{doc_id}.html'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

# 接口筛选参数取值（与文库前端筛选面板一一对应）
FORMAT_ALL = 0
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


def strip_highlight(text: str) -> str:
    """去掉标题/摘要里的 <em> 高亮标签并反转义实体。"""
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', '', text)
    return html.unescape(text).strip()


class WenkuFetchAgent:
    """封装百度文库搜索接口调用与结果缓存。"""

    def __init__(self, args):
        self.args = args
        self.proxy = getattr(args, 'proxy', '') or ''
        self.retry = int(getattr(args, 'retries', 10) or 1)
        self.cache_dir = getattr(args, 'cache_dir', '') or ''
        self.use_cache = not getattr(args, 'no_cache', False)
        self.refresh = getattr(args, 'refresh', False)
        self._session: Optional[requests.Session] = None

    # ── HTTP ────────────────────────────────────────────────

    def _get_session(self) -> requests.Session:
        """获取会话（携带文库首页 Cookie，降低被风控拦截的概率）。"""
        if self._session is None:
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
            self._session = s
        return self._session

    def _proxies(self) -> Optional[dict]:
        if not self.proxy:
            return None
        return {'http': self.proxy, 'https': self.proxy}

    def search_page(self, keyword: str, page: int, page_size: int) -> dict:
        """请求一页搜索结果，返回接口的 result 字段。"""
        body = {
            'word': keyword,
            'pn': page,
            'rn': page_size,
            'fr': 'wkSearch',
            'lm': getattr(self.args, 'format', FORMAT_ALL),
            'fd': getattr(self.args, 'type', TYPE_ALL),
            'od': getattr(self.args, 'sort', SORT_RELEVANCE),
        }
        if getattr(self.args, 'book', False):
            body['fd'] = RESOURCE_BOOK

        session = self._get_session()
        headers = dict(default_hdrs)
        headers['User-Agent'] = UA
        headers['Content-Type'] = 'application/json'
        headers['Referer'] = 'https://wenku.baidu.com/search'

        response = request_retry(
            'POST', SEARCH_URL,
            data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
            headers=headers,
            proxies=self._proxies(),
            retry=self.retry,
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

    # ── 解析 ────────────────────────────────────────────────

    @staticmethod
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

    # ── 搜索 ────────────────────────────────────────────────

    def _cache_fname(self, keyword: str, pages: int, page_size: int) -> str:
        key = gen_objs_md5(keyword, pages, page_size,
                           getattr(self.args, 'format', FORMAT_ALL),
                           getattr(self.args, 'type', TYPE_ALL),
                           getattr(self.args, 'sort', SORT_RELEVANCE),
                           bool(getattr(self.args, 'book', False)))
        return path.join(self.cache_dir, f'search_{key}.yaml')

    def search_docs(
        self, keyword: str, pages: int = 1, page_size: int = 10, sleep: float = 0.5,
    ) -> WenkuSearchResult:
        """按关键词搜索文档（最多 pages 页），跨页去重，带文件缓存。"""
        cache_fname = self._cache_fname(keyword, pages, page_size)
        if self.use_cache and not self.refresh:
            cached = read_yaml_model(cache_fname, WenkuSearchResult)
            if cached:
                logger.info('命中缓存：%s', cache_fname)
                return cached

        docs: List[WenkuDoc] = []
        seen = set()
        total = 0
        for page in range(1, pages + 1):
            logger.info('搜索第 %d/%d 页：%s', page, pages, keyword)
            result = self.search_page(keyword, page, page_size)
            items = result.get('items') or []
            extra = result.get('extra') or {}
            total = extra.get('total') or total
            for item in items:
                doc = self.parse_doc(item)
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
        if self.use_cache and self.cache_dir:
            write_yaml_model(cache_fname, res)
        return res
