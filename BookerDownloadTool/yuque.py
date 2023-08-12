import re
from os import path
from .util import *
import json
import subprocess as subp


def download_yuque(args):
    fname = args.fname
    name = re.sub(r'\.\w+$', '', path.basename(fname))
    ids = open(fname, encoding='utf8').read().split()
    pref = 'https://www.yuque.com/'
    ids = [
        (id if id.startswith(pref) else pref + id)
        for id in ids if id
    ]
    cfg = {
        "name": name,
        "url": "https://www.yuque.com",
        "link": "",
        "title": "h1#article-title",
        "content": ".ne-viewer-body",
        "selenium": true,
        "waitContent": args.wait,
        "textThreads": args.text_threads,
        "imgThreads": args.img_threads,
        "optiMode": "thres",
        "remove": "button",
        "headers": {
            "Cookie": args.cookie,
            "Referer": "https://www.yuque.com/"
        },
        "list": ids,
    }
    cfg_fname = 'config_' + fname_escape(name) + '.json'
    open(cfg_fname, 'w', encoding='utf8').write(json.dumps(cfg_fname))
    subp.Popen(['crawl-epub', cfg_fname], shell=True).communicate()