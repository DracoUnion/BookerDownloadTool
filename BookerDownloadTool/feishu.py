import json
import re
from EpubCrawler.util import request_retry
import argparse
from os import path
import subprocess as subp
from .util import *

def get_children(space_id, domain, wiki, cookie):
    url = f'https://{domain}.feishu.cn/space/api/wiki/v2/tree/get_node_child/?space_id={space_id}&wiki_token={wiki}'
    j = request_retry(
        'GET', url, 
        headers={'Cookie': cookie},
    ).json()
    if j['code'] != 0:
        raise RuntimeError(j['msg'])
    return [ch['wiki_token'] for ch in j['data'][wiki]]

def get_root_wikis(space_id, domain, cookie):
    url = f'https://{domain}.feishu.cn/space/api/wiki/v2/tree/get_info/?need_shared=true&space_id={space_id}'
    j = request_retry(
        'GET', url, 
        headers={'Cookie': cookie},
    ).json()
    if j['code'] != 0:
        raise RuntimeError(j['msg'])
    return j['data']['tree']['root_list']

def get_space_toc(space_id, domain, cookie):
    roots = get_root_wikis(space_id, domain, cookie)[::-1]
    res = []
    while len(roots):
        cur = roots.pop()
        res.append(cur)
        children = get_children(space_id, domain, cur, cookie)
        roots.extend(children[::-1])
    return res

def crawl_feishu(args):
    # 请求页面获取空间 ID
    wiki = args.wiki
    cookie = args.cookie
    url = f'https://feishu.cn/wiki/{wiki}'
    # 解决重定向不带 Cookie 的问题
    while True:
        r = request_retry(
            'GET', url, 
            headers={'Cookie': cookie}, 
            allow_redirects=False
        )
        if 'Location' not in r.headers: break
        url = r.headers['Location']
    m = re.search(r'([\w\-]+)\.feishu\.cn', url)
    if not m: 
        print(f'空间域名获取失败')
        return
    domain = m.group(1)
    html = r.text
    m = re.search(r'"space_id":"(\d+)"', html)
    if not m:
        print("空间 ID 获取失败")
        return
    space_id = m.group(1)
    # 如果没有Cookie，设置临时Cookie
    if not cookie:
        cookie = r.headers.get('Set-Cookie', '')
    toc = get_space_toc(space_id, domain, cookie)
    links = [
        f'https://{domain}.feishu.cn/space/api/ssr/wiki/{wiki}' 
        for wiki in toc
    ]
    name = args.name or f'飞书文档集_{domain}_{space_id}'
    cfg = {
        "name": name,
        "url": f"https://{domain}.feishu.cn",
        "link": "",
        "title": ".",
        "content": ".ne-viewer-body",
        "textThreads": args.text_threads,
        "imgThreads": args.img_threads,
        "optiMode": args.opti_mode,
        "remove": "button",
        "headers": {
            "Cookie": cookie,
            # "Referer": "https://www.yuque.com/"
        },
        "list": links,
        "external": path.join(DIR, 'feishu_external.py'),
    }
    cfg_fname = 'config_' + fname_escape(name) + '.json'
    open(cfg_fname, 'w', encoding='utf8').write(json.dumps(cfg))
    subp.Popen(['crawl-epub', cfg_fname], shell=True).communicate()
    
