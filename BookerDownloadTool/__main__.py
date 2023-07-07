import argparse
import sys
from . import __version__
from .zhihu_sele import *
from .lightnovel import *
from .dl_gh_book import *
from .bili import *
from .dmzj import *
from .discuz import *
from .zsxq import *
from .whole_site import *

def main():
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
    bili_parser.add_argument("-a", "--audio", type=bool, default=False, help="whether to convert to audio")
    bili_parser.add_argument("-o", "--output_dir", default='.', help="output dir")
    bili_parser.add_argument("--start_page", type=int, default=1, help="start page")
    bili_parser.add_argument("--end_page", type=int, default=1_000_000, help="end page")
    bili_parser.set_defaults(func=download_bili)

    bili_kw_parser = subparsers.add_parser("bili-kw", help="download bilibili video by kw")
    bili_kw_parser.add_argument("kw", help="keyword")
    bili_kw_parser.add_argument("-s", "--start", type=int, default=1, help="starting page for video list")
    bili_kw_parser.add_argument("-e", "--end", type=int, default=1_000_000, help="ending page for video list")
    bili_kw_parser.add_argument("-a", "--audio", type=bool, default=False, help="whether to convert to audio")
    bili_kw_parser.add_argument("--start_page", type=int, default=1, help="start page for every video")
    bili_kw_parser.add_argument("--end_page", type=int, default=1_000_000, help="end page for every video")
    bili_kw_parser.add_argument("-o", "--output_dir", default='.', help="output dir")
    bili_kw_parser.set_defaults(func=batch_kw_bili)
  
    bili_home_parser = subparsers.add_parser("bili-home", help="download bilibili video by user")
    bili_home_parser.add_argument("mid", help="user id")
    bili_home_parser.add_argument("-s", "--start", type=int, default=1, help="starting page for video list")
    bili_home_parser.add_argument("-e", "--end", type=int, default=1_000_000, help="ending page for video list")
    bili_home_parser.add_argument("-a", "--audio", type=bool, default=False, help="whether to convert to audio")
    bili_home_parser.add_argument("--start_page", type=int, default=1, help="start page for every video")
    bili_home_parser.add_argument("--end_page", type=int, default=1_000_000, help="end page for every video")
    bili_home_parser.add_argument("-o", "--output_dir", default='.', help="output dir")
    bili_home_parser.set_defaults(func=batch_home_bili)
    
    bili_meta_parser = subparsers.add_parser("bili-meta", help="download bilibili meta")
    bili_meta_parser.add_argument("-s", "--start", type=int, default=1, help="starting page for video list")
    bili_meta_parser.add_argument("-e", "--end", type=int, default=1_000_000, help="ending page for video list")
    bili_meta_parser.add_argument("-t", "--threads", type=int, default=1, help="thread num")
    bili_meta_parser.add_argument("-r", "--retry", type=int, default=10, help="retry times")
    bili_meta_parser.add_argument("-w", "--wait", type=float, default=0, help="sec to wait")
    bili_meta_parser.set_defaults(func=download_meta_bili)

    ln_parser = subparsers.add_parser("ln", help="download lightnovel")
    ln_parser.add_argument("id", help="id")
    ln_parser.add_argument("-s", "--save-path", default='out', help="path to save")
    ln_parser.add_argument("-c", "--cookie", default=os.environ.get('WK8_COOKIE', ''), help="wenku8.net cookie")
    ln_parser.set_defaults(func=download_ln)

    ln_batch_parser = subparsers.add_parser("batch-ln", help="download lightnovel in batch")
    ln_batch_parser.add_argument("fname", help="file name of ids")
    ln_batch_parser.add_argument("-s", "--save-path", default='out', help="path to save")
    ln_batch_parser.add_argument("-c", "--cookie", default=os.environ.get('WK8_COOKIE', ''), help="wenku8.net cookie")
    ln_batch_parser.set_defaults(func=batch_ln)

    ln_fetch_parser = subparsers.add_parser("fetch-ln", help="fetch lightnovel ids")
    ln_fetch_parser.add_argument("fname", help="file fname")
    ln_fetch_parser.add_argument("-c", "--cookie", default=os.environ.get('WK8_COOKIE', ''), help="wenku8.net cookie")
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
    whole_site_parser.set_defaults(func=whole_site)

    args = parser.parse_args()
    args.func(args)
    
if __name__ == '__main__': main()