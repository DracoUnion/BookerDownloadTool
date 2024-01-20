from EpubCrawler.config import config
from pyquery import PyQuery as pq
import json

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
    
    