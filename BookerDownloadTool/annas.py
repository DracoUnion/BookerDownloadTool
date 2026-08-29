import traceback
from difflib import SequenceMatcher
import tqdm
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import shutil
import os
import argparse
import re
import json
import copy
import subprocess as subp
from pyquery import PyQuery as pq
import random
from urllib.parse import quote_plus
from .util import plrt_create_driver, request_retry, fname_escape, to_kebab

HOST = 'annas-archive.gl'

dft_hdr = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0',
    'Referer': f'https://{HOST}',
}

def plrt_get_html(page, url: str, el_chk: str = None) -> str:
    """
    使用 Playwright 启动浏览器，访问页面，等待验证通过后获取 Cookies。
    """  
    # 2. 访问目标网站，等待网络空闲，让验证有机会完成
    page.goto(url)
    page.wait_for_load_state("domcontentloaded")
    
    # 3. 尝试等待关键的 el_chk ，最多等待 20 秒
    #    这比单纯等待timeout更智能
    if el_chk:
        page.wait_for_selector(el_chk, timeout=50000)
    # 4. 获取HTML并关闭浏览器
    html = page.content()
    return html

def plrt_get_html_retry(page, url: str, el_chk: str = None, retry: int = 10) -> str:
    for i in range(retry):
        try:
            page.reload()
            return plrt_get_html(page, url, el_chk)
        except KeyboardInterrupt:
            raise
        except Exception:
            print(f'plrt_get_html retry #{i + 1}')
            traceback.print_exc()
            if i == retry - 1: raise

def tr_download_safe(args):
    try:
        download_annas(args)
    except:
        traceback.print_exc()


def annas_batch(args):
    if not args.flist.endswith('.jsonl'):
        print('请提供 JSONL 文件')
        return
    
    pool = ThreadPoolExecutor(args.threads)
    hdls = []
    lines = open(args.flist, encoding='utf8').read().split('\n')
    lines = [l for l in lines if l.strip()]
    for l in lines[args.start:]:
        j = json.loads(l)
        args = copy.deepcopy(args)
        args.hash = j['hash']
        h = pool.submit(tr_download_safe, args)
        hdls.append(h)
        if len(hdls) > args.threads:
            for h in hdls: h.result()
            hdls = []

    for h in hdls: 
        h.result()

def annas_fetch(args):
    # https://annas-archive.gl/search
    # ?index=&page=1&sort=newest&content=book_nonfiction
    # &content=book_unknown&ext=pdf&ext=epub&lang=en&display=&q=tarot
    with plrt_create_driver(args.no_headless) as (browser, context, page):    
        f = open(args.ofname, 'a', encoding='utf8')
        qry_ext = ''.join(f'&ext={e}' for e in args.ext)
        qry_cont = ''.join(f'&content={c}' for c in args.content)
        qry_lang = ''.join(f'&lang={l}' for l in args.lang)
        qry_yr = f'&termtype_1=year&termval_1={args.year}' if args.year else ''
        for i in range(args.start, args.end + 1):
            url = (
                f'https://{HOST}/search' + 
                f'?page={i}&sort={args.sort}&q={quote_plus(args.query)}' + 
                f'{qry_ext}{qry_cont}{qry_lang}{qry_yr}'
            )
            print(url)
            html = plrt_get_html_retry(page, url, '.header-inner-top')
            rt = pq(html)
            el_links = rt.find('a.text-lg[href^="/md5/"]')
            if not el_links: break
            for el in el_links:
                el = pq(el)
                hash_ = el.attr('href').replace('/md5/', '')
                title = el.text().strip()
                print(f'title: {title}, hash: {hash_}')
                f.write(json.dumps({
                    'title': title, 
                    'hash': hash_, 
                    'slug': to_kebab(title)
                }) + '\n')
                f.flush()
        f.close()
        browser.close()

def download_annas(args):
    with plrt_create_driver(args.no_headless) as (browser, context, page):    
        hash_ = args.hash
        url = f'https://{HOST}/md5/{hash_}'
        # html = request_retry('GET', url).text
        html = plrt_get_html_retry(page, url, '.text-gray-800')
        rt = pq(html)
        title = rt.find('div.font-semibold:nth-child(4)') \
            .text().strip().replace(' 🔍', '')
        ext = rt.find('.text-gray-800').text().split(' · ')[1].lower()
        fname = fname_escape(f'{title[:200]}.{ext}')
        fname_bak = fname_escape(f'{fname}.bak')
        if os.path.isfile(fname):
            print(f'{fname} 已存在')
            return
        print(f'fname: {fname}')


        el_links_li = rt('#md5-panel-downloads > div:nth-child(2) li.list-disc') \
            .filter(lambda i, el: 'no waitlist' in pq(el).text())
        if not el_links_li:
            print(f'{fname} 未找到下载链接')
            return 
        
        url = pq(random.choice(el_links_li)).children('a').attr('href')
        url = f'https://{HOST}{url}'
        # url = f'https://{HOST}/slow_download/{hash_}/0/{idx}'
        html = plrt_get_html_retry(page, url, '.bg-gray-200')
        rt = pq(html)
        link = rt.find('.bg-gray-200').text().strip()
        r = request_retry('GET', link, headers=dft_hdr, stream=True)
        r.raise_for_status()
        fsize = int(r.headers['Content-Length'])
        chunk_size = 8192
        num_chunks = (fsize + chunk_size - 1) // chunk_size 
        with open(fname_bak, 'wb') as f:
            for data in tqdm.tqdm(
                r.iter_content(chunk_size),
                total=num_chunks,
            ):
                f.write(data)
                f.flush()
        os.rename(fname_bak, fname)
        browser.close()

    

def annas_dedup(args):
    if not args.flist.endswith('.jsonl'):
        print('请提供 JSONL 文件')
        return
    li = open(args.flist, encoding='utf8').read().split('\n')
    li = [l for l in li if l.strip()]
    li = [json.loads(it) for it in li]
    
    norm = lambda s: s.split(':')[0].split('：')[0]
    calc_sim = lambda s1, s2: SequenceMatcher(None, s1, s2).ratio()
    kept_name = []
    kept = []
    for it in li:
        name = norm(it['title'])
        print(name)
        if any(calc_sim(name, k) >= args.sim for k in kept_name):
            continue
        kept_name.append(name)
        kept.append(it)

    li = [json.dumps(it) for it in kept]
    open(args.flist, 'w', encoding='utf8').write(li)
    print('done...')

def main():



    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__': main()