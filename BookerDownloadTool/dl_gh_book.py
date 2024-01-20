import requests
import json
import subprocess as subp
from pyquery import PyQuery as pq
import sys
from .util import *
import re
import os

tmpl = {
    "link": "{article} li a",
    "title": "{article}>h1",
    "content": "{article}",
    "remove": "a.anchor",
    "optiMode": "none",
}

def dl_gh_book(args):
    url = args.url
    proxy = None
    if args.proxy:
        proxy = {
            'http': args.proxy,
            'https': args.proxy,
        }
    
    if not url.endswith('SUMMARY.md'):
        print('请提供目录链接！')
        return
    print(url)
    readme_url = url.replace('SUMMARY.md', 'README.md')
    html = request_retry('GET', readme_url, proxies=proxy).text
    title = pq(html).find(f'{args.article}>h1').eq(0).text().strip()
    
    config = tmpl.copy()
    for k, v in config.items():
        config[k] = v.replace("{article}", args.article)
    config['name'] = title
    config['url'] = url
    config['imgThreads'] = args.threads
    config['textThreads'] = args.threads
    config['proxy'] = args.proxy
    config['external'] = path.join(DIR, 'gh_json_external.py')
    open('config.json', 'w', encoding='utf8') \
        .write(json.dumps(config))
    subp.Popen('crawl-epub', shell=True).communicate()
    os.remove('config.json')
            