from collections import deque
from urllib.parse import urljoin, urlparse
import requests
from pyquery import PyQuery as pq
import re
from .util import *
import traceback
from concurrent.futures import ThreadPoolExecutor

hdrs = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
}

def get_html_checked(url, args):
    for i in range(args.retry):
        html = request_retry(
            'GET', url, 
            retry=args.retry,
            proxies=args.proxy,
            headers=hdrs,
        ).text
        if not args.check_nonblank: break
        check_text = pq(html).find(args.check_nonblank)
        if check_text.strip(): break
        if i == args.retry - 1:
            raise Exception(f'url [{url}] element {args.check_nonblank} checked blank')

def tr_get_next_safe(i, url, res, args):
    try:
        print(url)
        html = get_html_checked(url, args)
        ns = get_next(url, args)
        res[i] = ns
    except:
        traceback.print_exc()

def get_next(url, args):
    
    if not html: return []
    html = re.sub(r'<\?xml\x20[^>]*\?>', '', html)
    html = re.sub(r'xmnls=".+?"', '', html)
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
    links = [
        re.sub(r'#.*', '', l)
        for l in links
    ]
    if not args.qs:
        links = [
            re.sub(r'\?.*', '', l)
            for l in links
        ]
    if args.re:
        links = [
            l for l in links
            if re.search(args.re, l)
        ]
    # print(f'url: {url}\nnext: {links}\n')
    return links



def whole_site(args):
    site = args.site
    pres = urlparse(site)
    hdrs['Referer'] = f'{pres.scheme}://{pres.hostname}'
    if args.proxy: 
        args.proxy = {'http': args.proxy, 'https': args.proxy}
    if args.cookie:
        hdrs['Cookie'] = args.cookie
    
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
        rec_file.write(site + '\n')
    pool = ThreadPoolExecutor(args.threads)

    while q:
        # 取出指定数量的链接
        pop_cnt = min(len(q), args.threads)
        urls = [q.popleft() for _ in range(pop_cnt)]
        # urls = [u for u in urls if not u.endswith('.xml')]
        # 调用子线程获取引用
        nexts = [[] for _ in range(pop_cnt)]
        hdls = []
        for i, url in enumerate(urls):
            h = pool.submit(tr_get_next_safe, i, url, nexts, args)
            hdls.append(h)
        for h in hdls: h.result()
        # 合并、去重
        nexts = set(sum(nexts, []))
        for url in urls:
            ofile.write(url + '\n')
            rec_file.write('-1\n')
        for n in nexts:
            if n not in vis:
                vis.add(n)
                q.append(n)
                rec_file.write(n + '\n')
    
    ofile.close()
    rec_file.close()
