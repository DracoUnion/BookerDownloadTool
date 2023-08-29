import re
import json
from pyquery import PyQuery as pq
from urllib.parse import unquote_plus, quote_plus
from EpubCrawler.util import request_retry
from EpubCrawler.config import config

def get_article(html, url):
    # 获取文章 ID
    if url.endswith('/'): url = url[:-1]
    aid = url.split('/')[-1]
    # 获取书籍 ID
    m = re.search(r'book_id%22%3A(\d+)', html)
    if not m: raise Exception('未找到 book_id')
    bid = m.group(1)
    # 构造 API 链接并请求
    api_url = f'https://www.yuque.com/api/docs/{aid}?include_contributors=true&include_like=true&include_hits=true&merge_dynamic_data=false&book_id={bid}'
    j = request_retry(
        'GET', api_url, 
        headers=config['headers'],
        retry=config['retry'],
        timeout=(config['connTimeout'], config['readTimeout']),
    ).json()
    # 获取标题和正文
    title = j['data']['title']
    cont = j['data']['content']
    cont = re.sub(r'<!doctype[^>]*>', '', cont)
    # 处理正文中的 <card> 元素
    rt = pq(f'<div>{cont}></div>')
    el_imgs = rt('card[name=image]')
    for el in el_imgs:
        el = pq(el)
        props = json.loads(unquote_plus(el.attr('value'))[5:])
        el_new = pq('<img />')
        for k, v in props.items(): el_new.attr(k, str(v))
        if el_new.attr('src'):
            src = 'https://www.yuque.com/api/filetransfer/images?url=' + quote_plus(el_new.attr('src'))
            el_new.attr('src', src)
        el.replace_with(el_new)
    el_hrs = rt('card[name=hr]')
    for el in el_hrs:
        pq(el).replace_with('<hr />')
    el_cards = rt('card')
    if len(el_cards):
        names = {pq(el).attr('name') for el in el_cards}
        print(f'未知卡片类型：{names}')
    cont = f'''
        <blockquote>原文：<a href="{url}">{url}</a></blockquote>{str(rt)}
    '''
    return {'title': title, 'content': cont}