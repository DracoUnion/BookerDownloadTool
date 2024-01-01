import os
import sys
import shutil
import copy
import subprocess as subp
from os import path
import re
import tempfile
import uuid
import json
from concurrent.futures import ThreadPoolExecutor
import requests
from pyquery import PyQuery as pq
from GenEpub import gen_epub
from .util import *
    
def format_text(text):
    # 多个换行变为一个
    text = re.sub(r'(\r\n)+', '\r\n', text)
    # 去掉前两行
    text = re.sub(r'^.+?\r\n.+?\r\n', '', text)
    # 去掉后两行
    text = re.sub(r'\r\n.+?\r\n.+?$', '', text)
    # 划分标题和段落
    def rep_func(m):
        s = m.group(1)
        return '<p>' + s[4:] + '</p>' \
            if s.startswith('    ') else \
            '<!--split--><h1>' + s + '</h1>'
    text = re.sub(r'^(.+?)$', rep_func, text, flags=re.M)
    # 拆分章节，过滤空白章节
    chs = filter(None, text.split('<!--split-->'))
    # 将章节拆分为标题和内容
    map_func = lambda x: {
        'title': re.search(r'<h1>(.+?)</h1>', x).group(1),
        'content': re.sub(r'<h1>.+?<\/h1>', '', x),
    }
    return list(map(map_func, chs))
    
def get_info(html):
    root = pq(html)
    dt = root('#content > div:nth-child(1) > table:nth-child(1) tr:nth-child(2) > td:nth-child(4)').text()[5:].replace('-', '') or 'UNKNOWN'
    url = root('#content > div:nth-child(1) > div:nth-child(6) > div > span:nth-child(1) > fieldset > div > a').attr('href')
    title = root('#content > div:nth-child(1) > table:nth-child(1) tr:nth-child(1) > td > table tr > td:nth-child(1) > span > b').text()
    author = root('#content > div:nth-child(1) > table:nth-child(1) tr:nth-child(2) > td:nth-child(2)').text()[5:]
    return {'dt': dt, 'url': url, 'title': fname_escape(title), 'author': fname_escape(author)}
    
def download_ln(args):
    id = args.id
    save_path = args.save_path
    headers = default_hdrs.copy()
    headers['Cookie'] = args.cookie
    
    url = f'https://www.wenku8.net/book/{id}.htm'
    html = request_retry('GET', url, headers=headers).content.decode('gbk')
    info = get_info(html)
    print(info['title'], info['author'], info['dt'])
    
    ofname = f"{save_path}/{info['title']} - {info['author']} - {info['dt']}.epub"
    if path.exists(ofname):
        print('已存在')
        return
    safe_mkdir(save_path)
    
    articles = [{
        'title': info['title'], 
        'content': f"<p>作者：{info['author']}</p>",
    }]
    url = f'http://dl.wenku8.com/down.php?type=utf8&id={id}'
    text = request_retry('GET', url, headers=headers).content.decode('utf-8')
    chs = format_text(text)
    articles += chs
    gen_epub(articles, {}, None, ofname)
    
def download_safe(args):
    try: download_ln(args)
    except Exception as ex: print(ex)
    
def batch_ln(args):
    fname = args.fname
    
    lines = open(fname, encoding='utf-8').read().split('\n')
    lines = filter(None, map(lambda x: x.strip(), lines))
    pool = ThreadPoolExecutor(args.threads)
    hdls = []
    for id in lines:
        args = copy.deepcopy(args)
        args.id = id
        hdl = pool.submit(download_safe, args)
        hdls.append(hdl)
    for h in hdls: h.result()
    
def get_toc(html):
    root = pq(html)
    el_links = root('table.grid b a')
    el_dts = root('table.grid div > div:nth-child(2) > p:nth-child(3)')
    res = []
    for i in range(len(el_links)):
        id = re.search(r'/(\d+)\.htm', el_links.eq(i).attr('href')).group(1)
        dt = el_dts.eq(i).text().split('/')[0][3:].replace('-', '')
        res.append({'id': id, 'dt': dt})
    for i in range(1, len(res)):
        res[i]['dt'] = res[i]['dt'] or res[i - 1]['dt']
    for i in range(len(res) - 2, -1, -1):
        res[i]['dt'] = res[i]['dt'] or res[i + 1]['dt']
    res = [r for r in res if r['dt']]
    return res
        
    
def fetch_ln(args):
    fname = args.fname
    st = args.start
    ed = args.end
    headers = default_hdrs.copy()
    headers['Cookie'] = args.cookie

    ofile = open(fname, 'a', encoding='utf-8')
    
    stop = False
    i = 1
    while True:
        if stop: break
        print(f'page: {i}')
        url = f'https://www.wenku8.net/modules/article/index.php?page={i}'
        html = request_retry('GET', url, headers=headers).content.decode('gbk')
        toc = get_toc(html)
        if len(toc) == 0: break
        for bk in toc:
            if ed and bk['dt'] > ed:
                continue
            if st and bk['dt'] < st:
                stop = True
                break
            print(bk['id'], bk['dt'])
            ofile.write(bk['id'] + '\n')
        i += 1
        
    ofile.close()
    
    
if __name__ == '__main__': main()  
