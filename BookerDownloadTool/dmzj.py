import os
from os import path
import shutil
import requests
from pyquery import PyQuery as pq
from imgyaso import pngquant_bts, \
    adathres_bts, grid_bts, noise_bts, trunc_bts, noisebw_bts
import execjs
import traceback
import sys
import cv2
import numpy as np
import re
import tempfile
import json
import uuid
import img2pdf
import subprocess as subp
from concurrent.futures import ThreadPoolExecutor
from GenEpub import gen_epub
from BookerWikiTool.util import fname_escape, safe_mkdir, safe_rmdir
from EpubCrawler.util import request_retry, safe_remove

ch_pool = None
img_pool = None

headers = {
    'Referer': 'http://manhua.dmzj.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
}

d = lambda name: path.join(path.dirname(__file__, name))
    
def load_existed(fname):
    exi = []
    if path.exists(fname):
        exi = json.loads(open(fname, encoding='utf-8').read())
    return set(exi)

def get_info(html):
    root = pq(html)
    title = root('.anim_title_text h1').text()
    author = root('div.anim-main_list tr:nth-child(3) a').text().strip()
    el_links = root('.cartoon_online_border li a')
    toc = []
    for i in range(len(el_links)):
        toc.append('http://manhua.dmzj.com' + el_links.eq(i).attr('href'))
    return {'title': fname_escape(title), 'author': fname_escape(author), 'toc': toc}
    
def get_article(html):
    root = pq(html)
    title = root('.hotrmtexth1 a').text().strip()
    ch = root('.display_middle span').text().strip()
    sc = root('script:not([src])').eq(0).html()
    if sc:
        pics = execjs.compile(sc).eval('arr_pages') 
        pics = list(map(lambda s: 'http://images.dmzj.com/' + s, pics))
    else: pics = None
    return {'title': fname_escape(title), 'ch': fname_escape(ch), 'pics': pics}
    
        
def process_img(img):
    return noisebw_bts(trunc_bts(anime4k_auto(img), 4))

def anime4k_auto(img):
    fname = path.join(tempfile.gettempdir(), uuid.uuid4().hex + '.png')
    open(fname, 'wb').write(img)
    subp.Popen(
        ['wiki-tool', 'anime4k-auto', fname, '-G'], 
        shell=True,
    ).communicate()
    img = open(fname, 'rb').read()
    safe_remove(fname)
    return img
    
def tr_download_dmzj_img(url, imgs, k):
    print(f'pic: {url}')
    img = request_retry('GET', url, headers=headers).content
    img = process_img(img)
    imgs[k] = img
    
def download_dmzj_ch_safe(url, info, odir):
    try: download_dmzj_ch(url, info, odir)
    except Exception as ex: traceback.print_exc()
    
def download_dmzj_ch(url, info, odir):
    print(f'ch: {url}')
    html = request_retry('GET', url, headers=headers).text
    art = get_article(html)
    if not art['pics']:
        print('找不到页面')
        return
        
    name = f"{art['title']} - {info['author']} - {art['ch']}"
    ofname = f'{odir}/{name}.pdf'
    if name in existed or path.exists(ofname):
        print('文件已存在')
        return
    safe_mkdir(odir)
    
    imgs = {}
    hdls = []
    for i, img_url in enumerate(art['pics']):
        hdl = img_pool.submit(tr_download_dmzj_img, img_url, imgs, f'{i}.png')
        hdls.append(hdl)
    for h in hdls:
        h.result()
       
    img_list = [
        imgs.get(f'{i}.png', b'')
        for i in range(len(imgs))
    ]
    pdf = img2pdf.convert(img_list)
    open(ofname, 'wb').write(pdf)
    
def init_pools(args):
    global ch_pool
    global img_pool
    if ch_pool is None:
        ch_pool = ThreadPoolExecutor(args.ch_threads)
    if img_pool is None:
        img_pool = ThreadPoolExecutor(args.img_threads)
    
def download_dmzj(args, block=True):
    id = args.id
    init_pools(args) 
    url = f'http://manhua.dmzj.com/{id}/'
    html = request_retry('GET', url, headers=headers).text
    info = get_info(html)
    print(info['title'], info['author'])
    
    if len(info['toc']) == 0:
        print('已下架')
        return []
        
    hdls = []
    for url in info['toc']:
        hdl = ch_pool.submit(download_dmzj_ch_safe, url, info, args.out)
        hdls.append(hdl)
    if block:
        for h in hdls: h.result()
        hdls = []
    return hdls
    
        
def download_dmzj_safe(id, block=True):
    try: 
        return download_dmzj(id, block)
    except Exception as ex: 
        traceback.print_exc()
        return []
        
def batch_dmzj(args):
    fname = args.fname
    init_pools(args)
    lines = open(fname, encoding='utf-8').read().split('\n')
    lines = filter(None, map(lambda x: x.strip(), lines))
    hdls = []
    for id in lines:
        part = download_safe(id, False)
        hdls += part
    for h in hdls: h.result()
        
def fetch_dmzj(args):
    fname, st, ed = args.fname, args.start, args.end
    f = open(fname, 'a')
    
    stop = False
    i = 1
    while True:
        if stop: break
        print(f'page: {i}')
        url = f'http://sacg.dmzj.com/mh/index.php?c=category&m=doSearch&status=0&reader_group=0&zone=2304&initial=all&type=0&_order=t&p={i}&callback=c'
        res = request_retry('GET', url, headers=headers).text
        j = json.loads(res[2:-2])
        if not j.get('result'): break
        for bk in j['result']:
            id = bk['comic_url'][1:-1]
            dt = bk['last_update_date'].replace('-', '')
            if ed and dt > ed: 
                continue
            if st and dt < st: 
                stop = True
                break
            print(id, dt)
            f.write(id + '\n')
        i += 1
        
    f.close()
        