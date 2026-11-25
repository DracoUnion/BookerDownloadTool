"""wenku-fetch 子命令：搜索百度文库文档，把结果文档链接写入文件。

用法示例
--------
    # 搜索“人工智能”，结果链接写入 人工智能.txt
    bdt wenku-fetch 人工智能

    # 抓取 3 页（每页 10 条），写入指定文件
    bdt wenku-fetch 人工智能 -n 3 -o links.txt

    # 只看 pdf 格式、免费文档
    bdt wenku-fetch 人工智能 --format 2 --type 3
"""
import logging
import os
from os import path
from typing import List

from .util import fname_escape
from .wenku_fetch_agent import WenkuFetchAgent
from .wenku_fetch_models import WenkuSearchResult

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = '.wenku-fetch-cache'


def default_output_name(keyword: str) -> str:
    """默认输出文件名：{关键词}.txt（非法文件名字符会被转义）。"""
    return fname_escape(keyword.strip()) + '.txt'


class WenkuFetchOrchestrator:
    """编排器：调用文库搜索接口 → 汇总文档 → 写入链接文件。"""

    def __init__(self, args):
        self.args = args
        self.agent = WenkuFetchAgent(args)

    # ── 步骤 1：搜索 ─────────────────────────────────────────

    def step_search(self) -> WenkuSearchResult:
        """按关键词搜索文档。"""
        keyword = self.args.keyword.strip()
        if not keyword:
            raise ValueError('关键词不能为空')
        logger.info('开始搜索：%s（共 %d 页，每页 %d 条）',
                    keyword, self.args.pages, self.args.page_size)
        res = self.agent.search_docs(
            keyword, self.args.pages, self.args.page_size, self.args.sleep)
        logger.info('搜索完成：%d 条文档（接口报告总数 %d）', len(res.docs), res.total)
        return res

    # ── 步骤 2：输出 ─────────────────────────────────────────

    def step_output(self, res: WenkuSearchResult) -> str:
        """把文档链接写入输出文件（一行一个链接）。"""
        ofname = self.args.output or default_output_name(res.keyword)
        outdir = path.dirname(path.abspath(ofname))
        os.makedirs(outdir, exist_ok=True)
        links: List[str] = [doc.url for doc in res.docs if doc.url]
        with open(ofname, 'w', encoding='utf8') as f:
            f.write('\n'.join(links) + ('\n' if links else ''))
        logger.info('已写入 %d 条链接：%s', len(links), ofname)
        print(f'已保存 {len(links)} 条文档链接：{ofname}')
        return ofname

    # ── 主流程 ──────────────────────────────────────────────

    def run(self) -> str:
        res = self.step_search()
        if not res.docs:
            logger.warning('未搜索到任何文档')
        return self.step_output(res)


def wenku_fetch_handle(args):
    """入口函数：创建编排器并运行。"""
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, 'debug', False) else logging.INFO,
        format='[%(asctime)s][%(name)s][%(levelname)s] %(message)s',
    )
    if not getattr(args, 'cache_dir', ''):
        args.cache_dir = DEFAULT_CACHE_DIR
    return WenkuFetchOrchestrator(args).run()


def reg_subparser(subparsers):
    wenku_fetch_parser = subparsers.add_parser(
        'wenku-fetch', help='搜索百度文库文档，把结果文档链接保存到文件')
    wenku_fetch_parser.add_argument('keyword', help='搜索关键词')
    wenku_fetch_parser.add_argument('-o', '--output', default='',
                                    help='输出文件名，默认 {关键词}.txt')
    wenku_fetch_parser.add_argument('-n', '--pages', type=int, default=1,
                                    help='抓取页数，默认 1')
    wenku_fetch_parser.add_argument('-s', '--page-size', type=int, default=10,
                                    help='每页条数，默认 10')
    wenku_fetch_parser.add_argument('--format', type=int, default=0,
                                    help='格式筛选：0 不限 / 1 doc / 2 pdf / 3 ppt / 4 xls / 5 txt')
    wenku_fetch_parser.add_argument('--type', type=int, default=0,
                                    help='类型筛选：0 不限 / 1 VIP专享 / 3 免费 / 4 精品')
    wenku_fetch_parser.add_argument('--sort', type=int, default=0,
                                    help='排序：0 最高相关 / 1 最新上线 / 2 最多下载 / 3 最高评分')
    wenku_fetch_parser.add_argument('--book', action='store_true',
                                    help='搜索图书而非文档')
    wenku_fetch_parser.add_argument('--proxy', default='', help='HTTP/HTTPS 代理地址')
    wenku_fetch_parser.add_argument('--retries', type=int, default=10,
                                    help='请求重试次数，默认 10')
    wenku_fetch_parser.add_argument('--sleep', type=float, default=0.5,
                                    help='相邻页请求间隔秒数，默认 0.5')
    wenku_fetch_parser.add_argument('--cache-dir', default='',
                                    help=f'缓存目录，默认 {DEFAULT_CACHE_DIR}')
    wenku_fetch_parser.add_argument('--no-cache', action='store_true', help='不使用缓存')
    wenku_fetch_parser.add_argument('--refresh', action='store_true', help='忽略已有缓存并重新抓取')
    wenku_fetch_parser.set_defaults(func=wenku_fetch_handle)
