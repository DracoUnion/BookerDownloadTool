from .util import request_retry
import re
import hashlib
import requests
from os import path
import traceback
from imgyaso.quant import pngquant
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor

config = {
    'headers': {},
    'threads': 8,
    'retry': 10,
}

def tr_download_img_safe(url, imgs):
    try:
        tr_download_img(url, imgs)
    except:
        traceback.print_exc()

def tr_download_img(url, imgs):
    print(url)
    hash_ = hashlib.md5(url.encode('utf8')).hexdigest()
    data = request_retry(
        'GET', url,
        headers=config.get('headers', {}),
        retry=config['retry'],
    ).content
    data = pngquant(data)
    imgs[f'{hash_}.png'] = data

def process_img_md(md, imgs, base_url='', img_prefix='img/'):
    mts = list(re.finditer(r'!\[[^\]]*\]\(([^\)]+)\)', md))
    pool = ThreadPoolExecutor(config['threads'])
    hdls = []
    for m in mts:
        url = m.group(1)
        if not url.startswith('http'): 
            url = urljoin(base_url, url)
        if not url.startswith('http'): 
            continue
        h = pool.submit(tr_download_img_safe, url, imgs)
        hdls.append(h)
        if len(hdls) > config['threads']:
            for h in hdls: h.result()
            hdls = []
        hash_ = hashlib.md5(url.encode('utf8')).hexdigest()
        md = md.replace(url, f'{img_prefix}{hash_}.png')
    for h in hdls: 
        h.result()
    return md