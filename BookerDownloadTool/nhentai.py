import requests
from pyquery import PyQuery as pq
import os
import sys
from os import path
import shutil
import json
import subprocess as subp
import uuid
import tempfile
import img2pdf
import re
from imgyaso import noisebw_bts
from .util import *

exi_list = None

def load_exi_list(args):
    global exi_list
    if not exi_list and path.exists(args.exi_list):
        exi_list = json.loads(open(args.exi_list, encoding='utf8').read())
        exi_list = [tuple(e) for e in exi_list]

def check_exist(existed, name):
    return tuple(extract_info(name)) in existed

        
def get_info(html):
    root = pq(html)
    title = root('h2.title').eq(0).text().strip() or \
            root('h1.title').eq(0).text().strip()
    tags = root('.tag>.name')
    tags = set((pq(t).text() for t in tags))
    imgs = root('.gallerythumb > img')
    imgs = [
        pq(i).attr('data-src')
            .replace('t.jpg', '.jpg')
            .replace('t.png', '.png')
            .replace('t.nhentai', 'i.nhentai')
        for i in imgs
    ]
    return {'title': filter_gbk(fname_escape(title)), 'imgs': imgs, 'tags': tags}

def process_img(img):
    return noisebw_bts(trunc_bts(anime4k_auto(img), 4))

def download_nh(args):
    id = args.id
    odir = args.out
    load_exi_list(args)
    
    url = f'https://nhentai.net/g/{id}/'
    html = get_retry(url).text
    info = get_info(html)
    print(f"id: {id}, title: {info['title']}")
    
    if check_exist(existed, info['title']):
        print('已存在')
        return 
        
    ofname = f"{odir}/{info['title']}.epub"
    if path.exists(ofname):
        print('已存在')
        return
    safe_mkdir(odir)
    
    imgs = {}
    for i, img_url in enumerate(info['imgs']):
        print(f'{img_url} => {i}.png')
        img = request_retry('GET', img_url, headers=config['hdrs']).content
        img = process_img(img)
        imgs[f'{i}.png'] = img
            
    img_list = [
        imgs.get(f'{i}.png', b'')
        for i in range(len(info['imgs']))
    ]
    pdf = img2pdf.convert(img_list)
    open(ofname, 'wb').write(pdf)

    
def get_ids(html):
    root = pq(html)
    links = root('a.cover')
    ids = [
        pq(l).attr('href')[3:-1]
        for l in links
    ]
    return ids
    
def fetch_nh(args):
    fname, cate, st, ed = args.fname, args.cate, args.start, args.end
    ofile = open(fname, 'w')
    
    for i in range(st, ed + 1):
        print(f'page: {i}')
        url = f'https://nhentai.net/{cate}/?page={i}'
        html = get_retry(url).text
        ids = get_ids(html)
        if len(ids) == 0: break
        for id in ids:
            ofile.write(id + '\n')
            
    ofile.close()
    
def batch_nh(args):
    fname = args.fname
    ids = filter(None, open(fname).read().split('\n'))
    for id in ids:
        try: download(id)
        except Exception as ex: print(ex) 
        
def extract_info(name):
    rms = re.findall(RE_INFO, name)
    if len(rms) == 0: return ['', name]
    return (rms[0][0], rms[0][1].strip())
        
def gen_exi_list(args):
    dir = args.dir
    res = [
        extract_info(f.replace('.epub', ''))
        for f in os.listdir(dir)
        if f.endswith('.epub')
    ]
    ofname = (dir[:-1] \
        if dir.endswith('/') or dir.endswith('\\') \
        else dir) + '.json'
    open(ofname, 'w', encoding='utf-8') \
        .write(json.dumps(res))
    
def fix_fnames(args):
    dir = args.dir
    files = os.listdir(dir)
    
    for f in files:
        nf = filter_gbk(f)
        if f == nf: continue
        print(f'{f} => {nf}')
        f = path.join(dir, f)
        nf = path.join(dir, nf)
        if path.exists(nf):
            os.unlink(f)
        else:
            os.rename(f, nf)
        
