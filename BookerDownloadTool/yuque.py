import re
from os import path
from .util import *
import json
import subprocess as subp


def crawl_yuque(args):
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
        "waitContent": args.wait,
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