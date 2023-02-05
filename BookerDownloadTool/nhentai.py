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
import re
from imgyaso import noisebw_bts

# npm install -g gen-epub

RE_INFO = r'\[(.+?)\]([^\[]+)'
RE_TITLE = r'上传: (.+?) \([\d\.]+ \w+\)\n'
RE_META = r'META URL -> (\S+)'

config = {
    'hdrs': {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
    },
}

def request_retry(method, url, retry=10, **kw):
    kw.setdefault('timeout', 10)
    for i in range(retry):
        try:
            return requests.request(method, url, **kw)
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            print(f'{url} retry {i}')
            if i == retry - 1: raise e

get_retry = lambda *args, **kwargs: \
    request_retry('GET', *args, **kwargs)

def load_existed():
    existed = []
    fname = 'nh_existed.json'
    if path.exists(fname):
        existed = json.loads(open(fname).read())
    return {tuple(e) for e in existed}
    
existed = load_existed()

def check_exist(existed, name):
    return tuple(extract_info(name)) in existed

def fname_escape(name):
    
    return name.replace('\\', '＼') \
               .replace('/', '／') \
               .replace(':', '：') \
               .replace('*', '＊') \
               .replace('?', '？') \
               .replace('"', '＂') \
               .replace('<', '＜') \
               .replace('>', '＞') \
               .replace('|', '｜')

def safe_mkdir(dir):
    try:
        os.mkdir(dir)
    except:
        pass

def safe_rmdir(dir):
    try:
        shutil.rmtree(dir)
    except:
        pass
        
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

def gen_epub(articles, imgs, p):   
    imgs = imgs or {}

    dir = path.join(tempfile.gettempdir(), uuid.uuid4().hex) 
    safe_mkdir(dir)
    img_dir = path.join(dir, 'img')
    safe_mkdir(img_dir)
    
    for fname, img in imgs.items():
        fname = path.join(img_dir, fname)
        with open(fname, 'wb') as f:
            f.write(img)
    
    fname = path.join(dir, 'articles.json')
    with open(fname, 'w') as f:
        f.write(json.dumps(articles))
    
    args = f'gen-epub "{fname}" -i "{img_dir}" -p "{p}"'
    subp.Popen(args, shell=True).communicate()
    safe_rmdir(dir)

def download(id):
    url = f'https://nhentai.net/g/{id}/'
    html = get_retry(url).text
    info = get_info(html)
    print(f"id: {id}, title: {info['title']}")
    
    if 'webtoon' in info['tags']:
        print('跳过长条漫画')
        return
        
    if len(info['imgs']) > 600:
        print('漫画过长，已忽略')
        return
    
    if check_exist(existed, info['title']):
        print('已存在')
        return 
        
    ofname = f"out/{info['title']}.epub"
    if path.exists(ofname):
        print('已存在')
        return
    safe_mkdir('out')
    
    imgs = {}
    l = len(str(len(info['imgs'])))
    for i, img_url in enumerate(info['imgs']):
        fname = str(i).zfill(l) + '.png'
        print(f'{img_url} => {fname}')
        img = get_retry(img_url, headers=config['hdrs']).content
        img = process_img(img)
        imgs[fname] = img
            
    co = [
        f'<p><img src="../Images/{str(i).zfill(l)}.png" /></p>' 
        for i in range(len(info['imgs']))
    ]
    co = '\n'.join(co)
    articles = [{'title': info['title'], 'content': co}]
    gen_epub(articles, imgs, ofname)
    
def get_ids(html):
    root = pq(html)
    links = root('a.cover')
    ids = [
        pq(l).attr('href')[3:-1]
        for l in links
    ]
    return ids
    
def fetch(fname, cate="", st=1, ed=1_000_000):
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
    
def batch(fname):
    ids = filter(None, open(fname).read().split('\n'))
    for id in ids:
        try: download(id)
        except Exception as ex: print(ex) 
        
def extract_info(name):
    rms = re.findall(RE_INFO, name)
    if len(rms) == 0: return ['', name]
    return (rms[0][0], rms[0][1].strip())
        
def extract(dir):
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
    
def is_gbk(ch):
    try: 
        ch.encode('gbk')
        return True
    except:
        return False
    
def filter_gbk(fname):
    return ''.join([ch for ch in fname if is_gbk(ch)])
    
    
def fix_fnames(dir):
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
        
def convert_log(fname):
    co = open(fname, encoding='utf8').read()
    cos = co.split(' 上传: ')
    res = ['| 文件 | 链接 |\n| --- | --- |\n']
    for info in cos:
        info = ' 上传: ' + info
        title = re.search(RE_TITLE, info)
        meta = re.search(RE_META, info)
        if not title or not meta:
            continue
        res.append(f'| {title.group(1)} | {meta.group(1)} |\n')
        
    res = ''.join(res)
    open(fname + '.md', 'w', encoding='utf8').write(res)
    
    
def main():
    op = sys.argv[1]
    if op in ['dl', 'download']:
        download(sys.argv[2])
    elif op == 'batch':
        batch(sys.argv[2])
    elif op == 'fetch':
        fetch(
            sys.argv[2], 
            sys.argv[3] if len(sys.argv) > 3 else "", 
            int(sys.argv[4]) if len(sys.argv) > 4 else 1,
            int(sys.argv[5]) if len(sys.argv) > 5 else 1_000_000,
        )
    elif op in ['extract', 'ext']:
        extract(sys.argv[2])
    elif op == 'fix':
        fix_fnames(sys.argv[2])
    elif op == 'log':
        convert_log(sys.argv[2])
    elif op == 'search':
        print(check_exist(existed, sys.argv[2]))

if __name__ == '__main__': main()
