from pyquery import PyQuery as pq
import re
import os
from os import path
import json
import sys
import shutil
import argparse
import subprocess as subp
import copy
import traceback
from concurrent.futures import ThreadPoolExecutor
import tempfile
import uuid
import hashlib
from imgyaso import pngquant_bts
from GenEpub import gen_epub
from EpubCrawler.img import process_img
from EpubCrawler.config import config
from .util import *
 
exi_list = set()
 
default_hdrs = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36',
}
 
selectors = {
    'title': '#thread_subject',
    'content': 'td[id^=postmessage], .pattl',
    'author': 'a.xw1',
    'pages': 'div.pgt label span',
    'time': 'em[id^=authorposton]',
    'remove': '.jammer, [style="display:none"]',
    'uid': 'dd a.xi2',
    'link': '[id^=normalthread] a.xst',
}
 
def load_exi_list(args):
    global exi_list
    if not exi_list and path.exists(args.exi_list):
        exi_list = set(json.loads(open(args.exi_list).read()))
                
 
def get_info(html):
    root = pq(html)
    title = root(selectors['title']).eq(0).text().strip()
    author = root(selectors['author']).eq(0).text().strip()
    el_page = root(selectors['pages'])
    if len(el_page) == 0:
        pages = 1
    else:
        pages = el_page.attr('title')
        pages = int(pages.split(' ')[1])
    return {
        'title': fname_escape(title),
        'pages': pages,
        'author': fname_escape(author),
    }
     
def get_uid(html):
    root = pq(html)
    uid = root(selectors['uid']).eq(0).text().strip()
    return uid
 
def get_last_time(html):
    root = pq(html)
    time_str = root(selectors['time']).eq(-1).html() or ''
    m = re.search(r'\d+\-\d+\-\d+', time_str)
    if not m: return 'UNKNOWN'
    time_str = m.group()
    time_str = ''.join([
        s.zfill(2)
        for s in time_str.split('-')
    ])
    return time_str
 
def get_contents(html):
    root = pq(html)
    root(selectors['remove']).remove()
    el_contents = root(selectors['content'])
    contents = [
        '<div>' + pq(c).html() + '</div>'
        for c in el_contents
    ]
    return contents

def md5(s):
    return hashlib \
        .md5(s.encode('utf-8')) \
        .hexdigest()
     
def download_art(url, articles, imgs, cookie):
    hdrs = default_hdrs.copy()
    hdrs['Cookie'] = cookie
    html = request_retry('GET', url, headers=hdrs).text
    contents = get_contents(html)
    for c in contents:
        c = process_img(
            c, imgs, 
            img_prefix='../Images/',
            page_url=url,
        )
        articles.append({
            'title': str(len(articles)),
            'content': c
        })
     
def get_info_by_tid(host, tid, is_all, cookie):
    hdrs = default_hdrs.copy()
    hdrs['Cookie'] = cookie
    if is_all:
        uid = "0"
    else:
        url = f'https://{host}/forum.php?mod=viewthread&tid={tid}'
        html = request_retry('GET', url, headers=hdrs).text
        uid = get_uid(html)
        if not uid: return
    url = f'https://{host}/forum.php?mod=viewthread&tid={tid}&page=1000000&authorid={uid}'
    html = request_retry('GET', url, headers=hdrs).text
    info = get_info(html)
    info['uid'] = uid
    info['time'] = get_last_time(html)
    return info

def download_dz_safe(args):
    try: download_dz(args)
    except: traceback.print_exc()
     
def download_dz(args):
    config['colors'] = 256
    config['imgSrc'] = ['zoomfile', 'src']
    tid, cookie = args.tid, args.cookie
    host = args.host
    odir = args.out
    load_exi_list(args)
    try: os.mkdir(odir)
    except: pass
 
    info = get_info_by_tid(host, tid, args.all, cookie)
    if not info:
        print(f'{tid} 不存在')
        return
    uid = info['uid']
    tm = info['time']
    if args.start and tm < args.start:
        print(f'日期 {tm} 小于起始日期 {args.start}')
        return
    if args.end and tm > args.end:
        print(f'日期 {tm} 大于终止日期 {args.end}')
        return
    print(f"tid: {tid}, title: {info['title']}, time: {info['time']}")
     
    name = ' - '.join([
        fname_escape(host),
        info['title'],
        info['author'],
        info['time'],
    ])
    if name in exi_list or \
       f"{name} - pt1" in exi_list:
        print('已存在')
        return
    p = f"{odir}/{name}.epub"
    if path.exists(p) or \
       path.exists(f"{odir}/{name} - pt1.epub"):
        print('已存在')
        return
     
    articles = [{
        'title': info['title'],
        'content': f'<p>作者：{info["author"]}</p><p>TID：{tid}</p>'
    }]
    imgs ={}
    for i in range(1, info['pages'] + 1):
        print(f'page: {i}')
        url = f'https://{host}/forum.php?mod=viewthread&tid={tid}&page={i}&authorid={uid}'
        download_art(url, articles, imgs, cookie)
     
    total = sum(len(v) for _, v in imgs.items())
    hecto_mb = 100 * 1024 * 1024
    if total >= hecto_mb:
        gen_epub_paging(articles[1:], imgs, tid, info, name)
    else:
        gen_epub(articles, imgs, None, p)
 
def gen_epub_paging(articles, imgs, tid, info, name):
    hecto_mb = 100 * 1024 * 1024
    art_part = []
    img_part = {}
    total = 0
    ipt = 1
    for a in articles:
        art_imgs = re.findall(r'src="\.\./Images/(\w{32}\.png)"', a['content'])
        size = sum(
            len(imgs.get(iname, b'')) 
            for iname in art_imgs
        )
        if total + size >= hecto_mb:
            name_part = f'{name} - pt{ipt}'
            p = f'out/{name_part}.epub'
            art_part.insert(0, {
                'title': info['title'] + f' - pt{ipt}',
                'content': f'<p>作者：{info["author"]}</p><p>TID：{tid}</p>'
            })
            gen_epub(art_part, img_part, None, p)
            art_part = []
            img_part = {}
            total = 0
            ipt += 1
        art_part.append(a)
        img_part.update({
            iname:imgs.get(iname, b'') 
            for iname in art_imgs
        })
        total += size
    if art_part:
        name_part = f'{name} - pt{ipt}'
        p = f'out/{name_part}.epub'
        art_part.insert(0, {
            'title': info['title'] + f' - pt{ipt}',
            'content': f'<p>作者：{info["author"]}</p><p>TID：{tid}</p>'
        })
        gen_epub(art_part, img_part, None, p)
    
 
def get_tids(html):
    root = pq(html)
    el_links = root(selectors['link'])
    links = [pq(l).attr('href') for l in el_links]
    links = [re.search(r'tid=(\d+)', l).group(1) for l in links]
    return links
     
def batch_dz(args):
    fname = args.fname
    load_exi_list(args)
    with open(fname, encoding='utf-8') as f:
        tids = f.read().split('\n')
    lines = filter(None, [t.strip() for t in tids])
    pool = ThreadPoolExecutor(args.threads)
    hdls = []
    for l in lines:
        host, t, *_ = l.split('\t')
        args = copy.deepcopy(args)
        args.tid = t
        args.host = host
        h = pool.submit(download_dz_safe, args)
        hdls.append(h)
    for h in hdls: h.result()
    
     
def fetch_dz(args):
    fname, fid, st, ed = args.fname, args.fid, args.start, args.end
    host = args.host
    f = open(fname, 'a', encoding='utf-8')
    hdrs = default_hdrs.copy()
    hdrs['Cookie'] = args.cookie
    for i in range(st, ed + 1):
        print(f'page: {i}')
        url = f'https://{host}/forum.php?mod=forumdisplay&fid={fid}&page={i}'
        html = request_retry('GET', url, headers=hdrs).text
        tids = get_tids(html)
        if len(tids) == 0: break
        for t in tids:
            print(t)
            f.write(f'{host}\t{t}\n')
            f.flush()
         
    f.close()
