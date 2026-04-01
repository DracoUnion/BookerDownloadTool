import re
import hashlib
import requests
from os import path
import traceback
from imgyaso.quant import pngquant
from urllib.parse import urljoin

def process_img_md(md, imgs, base_url='', img_prefix='img/'):
    mts = list(re.finditer(r'!\[[^\]]*\]\(([^\)]+)\)', md))
    for m in mts:
        try:
            url = m.group(1)
            if not url.startswith('http'): 
                url = urljoin(base_url, url)
            if not url.startswith('http'): 
                continue
            print(url)
            hash_ = hashlib.md5(url.encode('utf8')).hexdigest()
            data = requests.get(url).content
            data = pngquant(data)
            imgs[f'{hash_}.png'] = data
            md = md.replace(url, f'{img_prefix}{hash_}.png')
        except:
            traceback.print_exc()

    return md