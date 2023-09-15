from EpubCrawler.config import config
from pyquery import PyQuery as pq
import json

def get_article(jstr, base):
    j = json.loads(jstr)
    if j['code'] != 0:
        raise RuntimeError(j['msg'])
    html = j['data']['ssr_content']
    rt = pq(html)
    title = rt('.page-block-content').eq(0).text().strip()
    cont = rt('.page-block-children').html()
    cont = f'<blockquote>来源：<a href="{base}">{base}</a></blockquote>' + cont
    return {'title': title, 'content': cont}