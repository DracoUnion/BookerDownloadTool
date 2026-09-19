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
    "title": "{article}>h1, {article}>h2, {article}>h3",
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
    config['headers'] = default_hdrs.copy()
    config['headers']['Accept'] = 'application/json'
    open('config.json', 'w', encoding='utf8') \
        .write(json.dumps(config))
    subp.Popen('crawl-epub', shell=True).communicate()
    os.remove('config.json')
            

def reg_subparser(subparsers):
    gh_book_parser = subparsers.add_parser("gh-book", help="从 GitHub 下载书籍")
    gh_book_parser.add_argument("url", help="SUMMARY.md 链接")
    gh_book_parser.add_argument("-t", "--threads", type=int, default=5, help="线程数")
    gh_book_parser.add_argument("-p", "--proxy", help="代理")
    gh_book_parser.add_argument("-a", "--article", default='article', help="article 选择器")
    gh_book_parser.set_defaults(func=dl_gh_book)
