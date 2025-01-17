import argparse
import sys
import os
from . import __version__
from .zhihu_sele import *
from .zhihu_api import *
from .lightnovel import *
from .dl_gh_book import *
from .bili import *
from .dmzj import *
from .discuz import *
from .zsxq import *
from .whole_site import *
from .medium import *
from .webarchive import *
from .links import *
from .wx import *
from .uqer import *
from .freembook import *
from .yuque import *
from .feishu import *
from .arxiv import *
from .gh import *
from .hkrnws import *
from .pic import *

def main():
    bili_cookie = os.environ.get('BILI_COOKIE', '')
    wk8_cookie = os.environ.get('WK8_COOKIE', '')

    parser = argparse.ArgumentParser(prog="BookerDownloadTool", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--version", action="version", version=f"PYBP version: {__version__}")
    parser.set_defaults(func=lambda x: parser.print_help())
    subparsers = parser.add_subparsers()
    
    gh_book_parser = subparsers.add_parser("gh-book", help="download books from github")
    gh_book_parser.add_argument("url", help="SUMMARY.md url")
    gh_book_parser.add_argument("-t", "--threads", type=int, default=5, help="num of threads")
    gh_book_parser.add_argument("-p", "--proxy", help="proxy")
    gh_book_parser.add_argument("-a", "--article", default='article', help="article selector")
    gh_book_parser.set_defaults(func=dl_gh_book)
    
    bili_parser = subparsers.add_parser("bili", help="download bilibili video")
    bili_parser.add_argument("id", help="av or bv")
    bili_parser.add_argument("-a", "--audio", action='store_true', help="whether to convert to audio")
    bili_parser.add_argument("-o", "--output_dir", default='.', help="output dir")
    bili_parser.add_argument("-c", "--cookie", default=bili_cookie, help="cookie")
    bili_parser.add_argument("--start_page", type=int, default=1, help="start page")
    bili_parser.add_argument("--end_page", type=int, default=1_000_000, help="end page")
    bili_parser.set_defaults(func=download_bili)

    bilisub_parser = subparsers.add_parser("bilisub", help="download bilibili subtitle")
    bilisub_parser.add_argument("id", help="av or bv")
    bilisub_parser.add_argument("-o", "--output_dir", default='.', help="output dir")
    bilisub_parser.add_argument("-c", "--cookie", default=bili_cookie, help="cookie")
    bilisub_parser.add_argument("--start_page", type=int, default=1, help="start page")
    bilisub_parser.add_argument("--end_page", type=int, default=1_000_000, help="end page")
    bilisub_parser.set_defaults(func=download_bilisub)


    bili_kw_parser = subparsers.add_parser("bili-kw", help="download bilibili video by kw")
    bili_kw_parser.add_argument("kw", help="keyword")
    bili_kw_parser.add_argument("-s", "--start", type=int, default=1, help="starting page for video list")
    bili_kw_parser.add_argument("-e", "--end", type=int, default=1_000_000, help="ending page for video list")
    bili_kw_parser.add_argument("-a", "--audio", action='store_true', help="whether to convert to audio")
    bili_kw_parser.add_argument("--start_page", type=int, default=1, help="start page for every video")
    bili_kw_parser.add_argument("--end_page", type=int, default=1_000_000, help="end page for every video")
    bili_kw_parser.add_argument("-o", "--output_dir", default='.', help="output dir")
    bili_kw_parser.add_argument("-c", "--cookie", default=bili_cookie, help="cookie")
    bili_kw_parser.set_defaults(func=batch_kw_bili)
  
    bilisub_kw_parser = subparsers.add_parser("bilisub-kw", help="download bilibili video by kw")
    bilisub_kw_parser.add_argument("kw", help="keyword")
    bilisub_kw_parser.add_argument("-s", "--start", type=int, default=1, help="starting page for video list")
    bilisub_kw_parser.add_argument("-e", "--end", type=int, default=1_000_000, help="ending page for video list")
    bilisub_kw_parser.add_argument("--start_page", type=int, default=1, help="start page for every video")
    bilisub_kw_parser.add_argument("--end_page", type=int, default=1_000_000, help="end page for every video")
    bilisub_kw_parser.add_argument("-o", "--output_dir", default='.', help="output dir")
    bilisub_kw_parser.add_argument("-c", "--cookie", default=bili_cookie, help="cookie")
    bilisub_kw_parser.set_defaults(func=batch_kw_bilisub)


    bili_home_parser = subparsers.add_parser("bili-home", help="download bilibili video by user")
    bili_home_parser.add_argument("mid", help="user id")
    bili_home_parser.add_argument("-s", "--start", type=int, default=1, help="starting page for video list")
    bili_home_parser.add_argument("-e", "--end", type=int, default=1_000_000, help="ending page for video list")
    bili_home_parser.add_argument("-a", "--audio", action='store_true', help="whether to convert to audio")
    bili_home_parser.add_argument("--start_page", type=int, default=1, help="start page for every video")
    bili_home_parser.add_argument("--end_page", type=int, default=1_000_000, help="end page for every video")
    bili_home_parser.add_argument("-o", "--output_dir", default='.', help="output dir")
    bili_home_parser.add_argument("-c", "--cookie", default=bili_cookie, help="cookie")
    bili_home_parser.set_defaults(func=batch_home_bili)
    
    bili_meta_parser = subparsers.add_parser("bili-meta", help="download bilibili meta")
    bili_meta_parser.add_argument("-s", "--start", type=int, default=1, help="starting page for video list")
    bili_meta_parser.add_argument("-e", "--end", type=int, default=1_000_000, help="ending page for video list")
    bili_meta_parser.add_argument("-t", "--threads", type=int, default=1, help="thread num")
    bili_meta_parser.add_argument("-r", "--retry", type=int, default=10, help="retry times")
    bili_meta_parser.add_argument("-w", "--wait", type=float, default=0, help="sec to wait")
    bili_meta_parser.add_argument("-p", "--proxy", default='', help="proxies splitted by ';'")
    bili_meta_parser.set_defaults(func=download_meta_bili)

    ln_parser = subparsers.add_parser("ln", help="download lightnovel")
    ln_parser.add_argument("id", help="id")
    ln_parser.add_argument("-s", "--save-path", default='out', help="path to save")
    ln_parser.add_argument("-c", "--cookie", default=wk8_cookie, help="wenku8.net cookie")
    ln_parser.add_argument("-r", "--retry", type=int, default=10, help="retry times")
    ln_parser.set_defaults(func=download_ln)

    ln_batch_parser = subparsers.add_parser("batch-ln", help="download lightnovel in batch")
    ln_batch_parser.add_argument("fname", help="file name of ids")
    ln_batch_parser.add_argument("-s", "--save-path", default='out', help="path to save")
    ln_batch_parser.add_argument("-c", "--cookie", default=wk8_cookie, help="wenku8.net cookie")
    ln_batch_parser.add_argument("-t", "--threads", type=int, default=5, help="thread count")
    ln_batch_parser.add_argument("-r", "--retry", type=int, default=1_000_000, help="retry times")
    ln_batch_parser.set_defaults(func=batch_ln)

    ln_fetch_parser = subparsers.add_parser("fetch-ln", help="fetch lightnovel ids")
    ln_fetch_parser.add_argument("fname", help="file fname")
    ln_fetch_parser.add_argument("-c", "--cookie", default=wk8_cookie, help="wenku8.net cookie")
    ln_fetch_parser.add_argument("-s", "--start", required=True, help="starting date (YYYYMMDD)")
    ln_fetch_parser.add_argument("-e", "--end", required=True, help="ending date (YYYYMMDD)")
    ln_fetch_parser.set_defaults(func=fetch_ln)
    
    zhihu_ques_parser = subparsers.add_parser("zhihu-ques", help="crawl zhihu answers of a question by **selenium**")
    zhihu_ques_parser.add_argument("qid", help="qid")
    zhihu_ques_parser.set_defaults(func=zhihu_ques_sele)
    
    zhihu_ques_batch_parser = subparsers.add_parser("zhihu-ques-batch", help="crawl zhihu answers of a question by **selenium**")
    zhihu_ques_batch_parser.add_argument("fname", help="fname of qids")
    zhihu_ques_batch_parser.set_defaults(func=zhihu_ques_batch_sele)
    
    zhihu_topic_parser = subparsers.add_parser("zhihu-topic", help="crawl zhihu questions of a topic by **selenium**")
    zhihu_topic_parser.add_argument("tid", help="tid")
    zhihu_topic_parser.set_defaults(func=zhihu_topic_sele)

    zhihu_topic_batch_parser = subparsers.add_parser("zhihu-topic-batch", help="crawl zhihu questions of a topic by **selenium**")
    zhihu_topic_batch_parser.add_argument("fname", help="fname of tids")
    zhihu_topic_batch_parser.set_defaults(func=zhihu_topic_batch_sele)

    zhihu_topics_parser = subparsers.add_parser("zhihu-topics", help="crawl zhihu sub topics  by **selenium**")
    zhihu_topics_parser.add_argument("root", help="root tid")
    zhihu_topics_parser.add_argument("-c", "--cookie", default='', help="zhihu cookie")
    zhihu_topics_parser.set_defaults(func=zhihu_all_topics_sele)

    dmzj_dl_parser = subparsers.add_parser("dmzj", help="download dmzj comic")
    dmzj_dl_parser.add_argument("id", help="id")
    dmzj_dl_parser.add_argument("-o", "--out", default="out", help="output dir")
    dmzj_dl_parser.add_argument("--img-threads", type=int, default=8, help="image threads")
    dmzj_dl_parser.add_argument("--ch-threads", type=int, default=8, help="chapter threads")
    dmzj_dl_parser.add_argument("-l", "--exi-list", default="dmzj_exi.json", help="fname for existed comic")
    dmzj_dl_parser.set_defaults(func=download_dmzj)

    dmzj_fetch_parser = subparsers.add_parser("fetch-dmzj", help="fetch dmzj comic ids")
    dmzj_fetch_parser.add_argument("fname", help="fname containing ids")
    dmzj_fetch_parser.add_argument("-s", "--start", help="starting date")
    dmzj_fetch_parser.add_argument("-e", "--end", help="ending date")
    dmzj_fetch_parser.set_defaults(func=fetch_dmzj)

    dmzj_batch_parser = subparsers.add_parser("batch-dmzj", help="download dmzj comic in batch")
    dmzj_batch_parser.add_argument("fname", help="fname containing ids")
    dmzj_batch_parser.add_argument("-o", "--out", default="out", help="output dir")
    dmzj_batch_parser.add_argument("--img-threads", type=int, default=8, help="image threads")
    dmzj_batch_parser.add_argument("--ch-threads", type=int, default=8, help="chapter threads")
    dmzj_batch_parser.add_argument("-l", "--exi-list", default="dmzj_exi.json", help="fname for existed comic")
    dmzj_batch_parser.set_defaults(func=batch_dmzj)

    dl_dz_parser = subparsers.add_parser("dz", help="download a page of dz")
    dl_dz_parser.add_argument("host", help="host: <domain>:<port>/<path>")
    dl_dz_parser.add_argument("tid", help="tid")
    dl_dz_parser.add_argument("-s", "--start", help="staring date")
    dl_dz_parser.add_argument("-e", "--end", help="ending date")
    dl_dz_parser.add_argument("-c", "--cookie", default="", help="dz cookie")
    dl_dz_parser.add_argument("-a", "--all", action='store_true', help="whether to crawl all replies")
    dl_dz_parser.add_argument("-l", "--exi-list", default='exi_dz.json', help="existed fnames JSON")
    dl_dz_parser.add_argument("-o", "--out", default='out', help="output dir")
    dl_dz_parser.set_defaults(func=download_dz)

    fetch_parser = subparsers.add_parser("fetch-dz", help="fetch dz tids")
    fetch_parser.add_argument("fname", help="fname containing tids")
    fetch_parser.add_argument("host",  help="host: <domain>:<port>/<path>")
    fetch_parser.add_argument("fid", help="fid")
    fetch_parser.add_argument("-s", "--start", type=int, default=1, help="staring page num")
    fetch_parser.add_argument("-e", "--end", type=int, default=10000000, help="ending page num")
    fetch_parser.add_argument("-c", "--cookie", default="", help="gn cookie")
    fetch_parser.set_defaults(func=fetch_dz)

    batch_parser = subparsers.add_parser("batch-dz", help="batch download")
    batch_parser.add_argument("fname", help="fname")
    batch_parser.add_argument("-s", "--start", help="staring date")
    batch_parser.add_argument("-e", "--end", help="ending date")
    batch_parser.add_argument("-c", "--cookie", default="", help="gn cookie")
    batch_parser.add_argument("-t", "--threads", type=int, default=8, help="num of threads")
    batch_parser.add_argument("-a", "--all", action='store_true', help="whether to crawl all replies")
    batch_parser.add_argument("-l", "--exi-list", default='exi_dz.json', help="existed fnames JSON")
    batch_parser.add_argument("-o", "--out", default='out', help="output dir")
    batch_parser.set_defaults(func=batch_dz)
    
    now = datetime.now()
    zsxq_parser = subparsers.add_parser("zsxq", help="download zsxq")
    zsxq_parser.add_argument('-s', '--start', default='00010101', help="starting date")
    zsxq_parser.add_argument('-e', '--end', default=f'{now.year}{now.month:02d}{now.day:02d}', help="ending date")
    zsxq_parser.add_argument('-c', '--cookie', default=os.environ.get('ZSXQ_COOKIE'), help="zsxq cookie, default as $ZSXQ_COOKIE")
    zsxq_parser.add_argument('id', help='zsxq group id')
    zsxq_parser.set_defaults(func=download_zsxq)

    whole_site_parser = subparsers.add_parser("whole-site", help="crawl whole site urls")
    whole_site_parser.add_argument("site", help="site url")
    whole_site_parser.add_argument("db", help="db fname")
    whole_site_parser.add_argument("-r", "--retry", type=int, default=10, help="times to retry")
    whole_site_parser.add_argument("-p", "--proxy", help="proxy")
    whole_site_parser.add_argument("-t", "--threads", type=int, default=8, help="num of threads")
    whole_site_parser.add_argument("-c", "--cookie", help="cookie")
    whole_site_parser.add_argument("-B", "--nonblank", help="selector for nonblank element. the check will fail if they are blank")
    whole_site_parser.add_argument("--re", help="pattern to match links")
    whole_site_parser.add_argument("--qs", action='store_true', help="whether to consider query string")
    whole_site_parser.set_defaults(func=whole_site)

    exp_whole_site_parser = subparsers.add_parser("exp-whole-site", help="export whole site urls")
    exp_whole_site_parser.add_argument("db", help="db fname")
    exp_whole_site_parser.add_argument("-s", "--batch-size", type=int, default=1000, help="db fname")
    exp_whole_site_parser.set_defaults(func=exp_whole_site)
    
    med_parser = subparsers.add_parser("medium", help="fetch medium toc")
    med_parser.add_argument("host", help="medium blog host: xxx.medium.com or medium.com/xxx")
    med_parser.add_argument('-s', '--start', default='20150101', help="starting date")
    med_parser.add_argument('-e', '--end', default='99991231', help="ending date")
    med_parser.add_argument('-p', '--proxy', help="proxy")
    med_parser.set_defaults(func=fetch_medium)

    war_parser = subparsers.add_parser("web-archive", help="fetch web archive")
    war_parser.add_argument("host", help="host")
    war_parser.add_argument("-s", "--start", type=int, default=1, help="starting page")
    war_parser.add_argument("-e", "--end", type=int, default=1_000_000_000, help="ending page")
    war_parser.add_argument("-r", "--regex", default='.', help="regex to match urls")
    war_parser.add_argument("-q", "--query", action='store_true', help="whether to deduplicate with query")
    war_parser.add_argument("-f", "--fragment", action='store_true', help="whether to deduplicate with fragment")
    war_parser.add_argument("-p", "--proxy", help="proxy")
    war_parser.set_defaults(vis=set())
    war_parser.set_defaults(func=fetch_webarchive)

    links_parser = subparsers.add_parser("links", help="fetch links in pages")
    links_parser.add_argument("url", help="url with {i} as page num")
    links_parser.add_argument("link", help="link selector")
    links_parser.add_argument("ofname", help="output file name")
    links_parser.add_argument("-s", "--start", type=int, default=1, help="starting page")
    links_parser.add_argument("-e", "--end", type=int, default=10000000, help="ending page")
    links_parser.add_argument("-t", "--time", help="time selector")
    links_parser.add_argument("-r", "--time-regex", default=r"\d+-\d+-\d+", help="time regex")
    links_parser.add_argument("-p", "--proxy", help="proxy")
    links_parser.add_argument("-H", "--headers", help="headers in JSON")
    links_parser.add_argument("-J", "--json", action='store_true', help="treat output as JSON not HTML")
    links_parser.set_defaults(func=fetch_links)

    sitemap_parser = subparsers.add_parser("sitemap", help="fetch links in sitemap")
    sitemap_parser.add_argument("url", help="sitemap url")
    sitemap_parser.add_argument("-r", "--regex", default="/blog/", help="link regex")
    sitemap_parser.add_argument("-o", "--ofname", help="output file name")
    sitemap_parser.add_argument("-p", "--proxy", help="proxy")
    sitemap_parser.set_defaults(func=fetch_sitemap_handle)

    links_epub_parser = subparsers.add_parser("links-epub", help="batch download links to epub")
    links_epub_parser.add_argument("links", help="name of file storing links")
    links_epub_parser.add_argument("--name", help="epub name")
    links_epub_parser.add_argument("-t", "--title", default="", help="title selector")
    links_epub_parser.add_argument("-c", "--content", default="", help="content selector")
    links_epub_parser.add_argument("-r", "--remove", default="", help="remove elems selector")
    links_epub_parser.add_argument("-n", "--num", default=500, type=int, help="num of articles in one epub")
    links_epub_parser.add_argument("-m", "--opti-mode", default='quant', help="img optimization mode")
    links_epub_parser.add_argument("-l", "--size-limit", default='100m', help="epub size limit")
    links_epub_parser.add_argument("-g", "--time-regex", default=r'(\d+)-(\d+)-(\d+)', help="time regex")
    links_epub_parser.add_argument("-E", "--exec", action='store_true', help="whether to execute EpubCrawler on config files")
    links_epub_parser.set_defaults(func=batch_links)

    wx_parser = subparsers.add_parser("wx", help="crawler weixin articles")
    wx_parser.add_argument("fname", help="XLSX fname")
    wx_parser.add_argument("-n", "--size", type=int, default=500, help="num of articles per ebook")
    wx_parser.add_argument("-o", "--opti-mode", default='thres', help="img optimization mode, default 'thres'")
    wx_parser.set_defaults(func=crawl_wx)
    
    uqer_parser = subparsers.add_parser("uqer", help="download uqer post")
    uqer_parser.add_argument("tid", help="uqer tid")
    uqer_parser.add_argument("-d", "--dir", default='.',  help="output dir")
    uqer_parser.set_defaults(func=download_uqer)

    uqer_batch_parser = subparsers.add_parser("batch-uqer", help="download uqer post in batch")
    uqer_batch_parser.add_argument("fname", help="file name of uqer tids")
    uqer_batch_parser.add_argument("-d", "--dir", default='.',  help="output dir")
    uqer_batch_parser.add_argument("-t", "--threads", type=int, default=8,  help="thread count")
    uqer_batch_parser.set_defaults(func=download_uqer_batch)

    fmb_parser = subparsers.add_parser("freembook", help="download freembook info")
    fmb_parser.add_argument("start", type=int, help="starting ssid")
    fmb_parser.add_argument("end", type=int, help="ending ssid")
    fmb_parser.add_argument("-t", "--threads", type=int, default=8,  help="thread count")
    fmb_parser.add_argument("-p", "--proxy", default='',  help="proxy splitted by ';'")
    fmb_parser.set_defaults(func=download_fmb)

    yuque_parser = subparsers.add_parser("yuque", help="crawler yuque articles")
    yuque_parser.add_argument("path", help="yuque \"{userName}/{bookName}\"")
    yuque_parser.add_argument("-t", "--text-threads", type=int, default=8, help="num of threads for text")
    yuque_parser.add_argument("-i", "--img-threads", type=int, default=24, help="num of threads for imgs")
    yuque_parser.add_argument("-c", "--cookie", default=os.environ.get('YUQUE_COOKIE', ''), help="yuque cookie")
    yuque_parser.add_argument("-o", "--opti-mode", default='thres', help="img optimization mode, default 'thres'")
    yuque_parser.add_argument("-s", "--start", help="starting date for articles")
    yuque_parser.add_argument("-e", "--end", help="ending date for articles")
    yuque_parser.add_argument("-n", "--name", help="book name")
    yuque_parser.set_defaults(func=crawl_yuque)

    yuque_parser = subparsers.add_parser("batch-yuque", help="crawler yuque articles")
    yuque_parser.add_argument("fname", help="fname of yuque article links")
    yuque_parser.add_argument("-t", "--text-threads", type=int, default=8, help="num of threads for text")
    yuque_parser.add_argument("-i", "--img-threads", type=int, default=24, help="num of threads for imgs")
    yuque_parser.add_argument("-c", "--cookie", default=os.environ.get('YUQUE_COOKIE', ''), help="yuque cookie")
    yuque_parser.add_argument("-o", "--opti-mode", default='thres', help="img optimization mode, default 'thres'")
    yuque_parser.set_defaults(func=batch_yuque)

    feishu_parser = subparsers.add_parser("feishu", help="crawler feishu articles")
    feishu_parser.add_argument("url", help="https://<uid>.feishu.cn/docx/<aid>")
    feishu_parser.add_argument("-c", "--cookie", default=os.environ.get('FEISHU_COOKIE', ''), help="feishu cookie")
    feishu_parser.add_argument("-o", "--opti-mode", default='thres', help="img optimization mode, default 'thres'")
    feishu_parser.set_defaults(func=download_feishu)

    zhihu_ques_api_parser = subparsers.add_parser("zhiapi-ques", help="crawl zhihu answers of a question by **API**")
    zhihu_ques_api_parser.add_argument("qid", help="qid")
    zhihu_ques_api_parser.add_argument("-p", "--proxy", help="proxy")
    zhihu_ques_api_parser.add_argument("-m", "--opti-mode", default="thres", help="img opti mode")
    zhihu_ques_api_parser.add_argument("-r", "--retry", type=int, default=10, help="retry count")
    zhihu_ques_api_parser.set_defaults(func=zhihu_ques_api)

    zhihu_ques_range_api_parser = subparsers.add_parser("zhiapi-ques-range", help="crawl zhihu answers of a question by **API**")
    zhihu_ques_range_api_parser.add_argument("start", type=int, help="starting qid")
    zhihu_ques_range_api_parser.add_argument("end", type=int, help="ending qid")
    zhihu_ques_range_api_parser.add_argument("-p", "--proxy", help="proxy")
    zhihu_ques_range_api_parser.add_argument("-m", "--opti-mode", default="thres", help="img opti mode")
    zhihu_ques_range_api_parser.add_argument("-t", "--threads", type=int, default=8, help="thread num")
    zhihu_ques_range_api_parser.add_argument("-r", "--retry", type=int, default=10, help="retry count")
    zhihu_ques_range_api_parser.set_defaults(func=zhihu_ques_range_api)

    arxiv_fetch_parser = subparsers.add_parser("arxiv-fetch", help="fetch arxiv ids")
    arxiv_fetch_parser.add_argument("subject", help="subject code")
    arxiv_fetch_parser.add_argument("year_month", help="year and month like yymm")
    arxiv_fetch_parser.add_argument("-s", "--page-size", type=int, default=2000, help="page size")
    arxiv_fetch_parser.set_defaults(func=arxiv_fetch)

    gh_repo_parser = subparsers.add_parser("gh-repo-fetch", help="fetch gh repos")
    gh_repo_parser.add_argument("-s", "--start", type=int, default=1, help="starting page ")
    gh_repo_parser.add_argument("-e", "--end", type=int, default=1_000_000, help="ending page ")
    gh_repo_parser.add_argument("-t", "--token", default=os.environ.get('GH_TOKEN', ''), help="github token")
    gh_repo_parser.add_argument("-r", "--retry", type=int, default=10, help="retry count")
    gh_repo_parser.add_argument("-p", "--proxy", help="proxy")
    gh_repo_parser.add_argument("query", help="query to search")
    gh_repo_parser.add_argument("ofname", help="output file name")
    gh_repo_parser.set_defaults(func=gh_repo_fetch)

    hkrnws_fetch_parser = subparsers.add_parser("hkrnws-fetch", help="fetch hkrnws posts")
    hkrnws_fetch_parser.add_argument("date", help="date YYYYMMDD")
    hkrnws_fetch_parser.add_argument("-p", "--proxy", help="proxy")
    hkrnws_fetch_parser.set_defaults(func=fetch_hkrnws)

    hkrnws_fetch_parser = subparsers.add_parser("hkrnws-range", help="fetch multiple hkrnws posts")
    hkrnws_fetch_parser.add_argument("start", help="starting date YYYYMMDD")
    hkrnws_fetch_parser.add_argument("end", help="ending date YYYYMMDD")
    hkrnws_fetch_parser.add_argument("-p", "--proxy", help="proxy")
    hkrnws_fetch_parser.add_argument("-t", "--threads", type=int, default=8, help="num of threads")
    hkrnws_fetch_parser.set_defaults(func=fetch_hkrnws_rng)

    pixabay_dl_parser = subparsers.add_parser("pixabay", help="download pics in pixabay")
    pixabay_dl_parser.add_argument("kw", help="keyword")
    pixabay_dl_parser.add_argument("-d", "--dir", default='.', help="output dir")
    pixabay_dl_parser.add_argument("-p", "--proxy", help="proxy")
    pixabay_dl_parser.add_argument("-t", "--threads", type=int, default=8, help="num of threads")
    pixabay_dl_parser.add_argument("-s", "--start", type=int, default=1, help="starting page ")
    pixabay_dl_parser.add_argument("-e", "--end", type=int, default=1_000_000, help="ending page ")
    pixabay_dl_parser.set_defaults(func=download_pixabay)


    args = parser.parse_args()
    args.func(args)
    
if __name__ == '__main__': main()