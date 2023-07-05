from collections import deque
from urllib.parse import urljoin, urlparse
import requests
from pyquery import PyQuery as pq
import re
from .util import *


def get_next(url):
    html = request_retry('GET', url).text
    if not html: return []
    rt = pq(html)
    el_links = rt('a')
    links = [
        urljoin(url, pq(el).attr('href').strip()) 
        for el in el_links
        if pq(el).attr('href')
    ]
    hostname = urlparse(url).hostname
    links = [
        l for l in links 
        if urlparse(l).hostname == hostname
    ]
    # print(f'url: {url}\nnext: {links}\n')
    return links



def whole_site(args):
    site = args.site
    pref = re.sub(r'[^\w\-\.]', '-', site)
    res_fname = f'{pref}.txt'
    rec_fname = f'{pref}_rec.txt'
    
    ofile = open(res_fname, 'a', encoding='utf8')
    rec_file = open(rec_fname, 'a+', encoding='utf8')
    
    if rec_file.tell() != 0:
        rec_file.seek(0, 0)
        rec = rec_file.read().split('\n')
        rec = [l for l in rec if l.strip()]
        pop_count = rec.count('-1')
        q = deque([l for l in rec if l != "-1"][pop_count:])
        vis = set(rec)
    else:
        q = deque([site])
        vis = set([site])

    while q:
        url = q.pop()
        print(url)
        if url.endswith('.xml'): continue
        nexts = get_next(url)
        ofile.write(url + '\n')
        rec_file.write('-1\n')
        for n in nexts:
            if n not in vis:
                vis.add(n)
                q.append(n)
                rec_file.write(n + '\n')
    
    ofile.close()
    rec_file.close()
