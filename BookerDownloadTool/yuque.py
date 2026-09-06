import os
import re
from os import path
from .util import *
import json
import subprocess as subp
from pyquery import PyQuery as pq
from datetime import datetime

def get_name(html, args):
    name = pq(html).find('title') \
               .eq(0).text()[:-5] \
               .replace(' ', '')
    st = args.start or '00000101'
    now = datetime.now()
    ed = args.end or f'{now.year:04d}{now.month:02d}{now.day:02d}'
    return f'{name}_{st}_{ed}'
        

def crawl_yuque(args):
    path_ = args.path
    url = f'https://www.yuque.com/{path_}'
    hdrs = {'Cookie': args.cookie}
    html = request_retry('GET', url, headers=hdrs).text
    name = args.name or get_name(html, args)
    print(name)
    m = re.search(r'book%22%3A%7B%22id%22%3A(\d+)', html)
    if not m: 
        print('找不到书籍 ID')
        return
    bid = m.group(1)
    url = f'https://www.yuque.com/api/docs?book_id={bid}'
    j = request_retry('GET', url, headers=hdrs).json()
    arts = [{
        'slug': a['slug'],
        'update_time': a['content_updated_at'].split('T')[0].replace('-', ''),
    } for a in j['data']]
    if args.start:
        arts = [a for a in arts if a['update_time'] >= args.start]
    if args.end:
        arts = [a for a in arts if a['update_time'] <= args.end]
    links = [f'https://www.yuque.com/{path_}/' + a['slug'] for a in arts]
    cfg = {
        "name": name,
        "url": "https://www.yuque.com",
        "link": "",
        "title": "h1#article-title",
        "content": ".ne-viewer-body",
        "textThreads": args.text_threads,
        "imgThreads": args.img_threads,
        "optiMode": args.opti_mode,
        "remove": "button",
        "headers": {
            "Cookie": args.cookie,
            # "Referer": "https://www.yuque.com/"
        },
        "list": links,
        "external": path.join(DIR, 'yuque_external.py'),
    }
    cfg_fname = 'config_' + fname_escape(name) + '.json'
    open(cfg_fname, 'w', encoding='utf8').write(json.dumps(cfg))
    subp.Popen(['crawl-epub', cfg_fname], shell=True).communicate()
    
def batch_yuque(args):
    fname = args.fname
    name = re.sub(r'\.\w+$', '', path.basename(fname))
    ids = open(fname, encoding='utf8').read().split()
    ids = [id for id in ids if id]
    cfg = {
        "name": name,
        "url": "https://www.yuque.com",
        "link": "",
        "title": "h1#article-title",
        "content": ".ne-viewer-body",
        "textThreads": args.text_threads,
        "imgThreads": args.img_threads,
        "optiMode": args.opti_mode,
        "remove": "button",
        "headers": {
            "Cookie": args.cookie,
            # "Referer": "https://www.yuque.com/"
        },
        "list": ids,
        "external": path.join(DIR, 'yuque_external.py'),
    }
    cfg_fname = 'config_' + fname_escape(name) + '.json'
    open(cfg_fname, 'w', encoding='utf8').write(json.dumps(cfg))
    subp.Popen(['crawl-epub', cfg_fname], shell=True).communicate()

def reg_subparser(subparsers):
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
