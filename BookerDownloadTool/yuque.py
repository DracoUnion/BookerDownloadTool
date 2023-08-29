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
    url = r'https://www.yuque.com/{path_}'
    hdrs = {'Cookie': args.cookie}
    html = request_retry('GET', url, headers=hdrs).text
    name = args.name or get_name(html, args)
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
        "waitContent": args.wait,
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