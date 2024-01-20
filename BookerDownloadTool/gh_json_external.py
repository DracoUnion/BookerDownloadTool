from EpubCrawler.config import config
from pyquery import PyQuery as pq
import json
import re
from urllib.parse import urljoin

def get_toc(jstr, base):
    j = json.loads(jstr)
    html = j['payload']['blob']['richText']
    rt = pq(html)
    if config['remove']:
        rt.remove(config['remove'])
    el_links = rt(config['link'])
    vis = set()
    res = []
    for i in range(len(el_links)):
        el_link = el_links.eq(i)
        url = el_link.attr('href')
        if not url:
            text = el_link.text().strip()
            res.append(text)
            continue
            
        url = re.sub(r'#.*$', '', url)
        if base:
            url = urljoin(base, url)
        if not url.startswith('http'):
            continue
        if url in vis: continue
        vis.add(url)
        res.append(url)
        
    return res

def get_article(jstr, base):
    j = json.loads(jstr)
    html = j['payload']['blob']['richText']
    rt = pq(html)
    if config['remove']:
        rt.remove(config['remove'])
    el_title = rt(config['title']).eq(0)
    title = el_title.text().strip()
    el_title.remove()
    content = '\n'.join([
        pq(el).html()
        for el in rt(config['content'])
    ])
    if config['credit']:
        credit = f'<blockquote>来源：<a href="{base}">{base}</a></blockquote>'
        content = credit + '\n' + content
    return {
        'title': title,
        'content': content
    }
    
    