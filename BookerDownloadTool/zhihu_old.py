import re
import sys
from EpubCrawler.util import request_retry
from EpubCrawler.img import process_img
from EpubCrawler.config import config as cralwer_config
from datetime import datetime
from GenEpub import gen_epub

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
}

def get_content(art):
    au_name = art['author']['name']
    au_url = 'https://www.zhihu.com/people/' + \
        art['author']['url_token']
    vote = art['voteup_count']
    url = art['url'].replace('api/v4/answers', 'answer')
    upd_time = datetime.utcfromtimestamp(art['updated_time']).strftime('%Y-%m-%d')
    co = re.sub(r'<noscript>.+?</noscript>', '', art['content'])
    co = re.sub(r' src=".+?"', '', co) \
        .replace('data-actualsrc', 'src')
    co = f'''
        <blockquote>
            <p>作者：<a href='{au_url}'>{au_name}</a></p>
            <p>赞同数：{vote}</p>
            <p>编辑于：<a href='{url}'>{upd_time}</a></p>
        </blockquote>
        {co}
    '''
    return {'title': au_name, 'content': co}
    
def ext_cookies(cookie_str):
    # _xsrf=...; KLBRSID=...
    kvs = re.findall(r'(?:_xsrf|KLBRSID)=[^;]+', cookie_str)
    kvs = [kv.split('=') for kv in kvs]
    return {kv[0]:kv[1] for kv in kvs}
    
def zhihu_ques(args):
    qid = args.qid
    cralwer_config['optiMode'] = args.opti_mode
    cralwer_config['imgSrc'] = ['data-original', 'src']

    url = f'https://www.zhihu.com/api/v4/questions/{qid}/feeds?cursor=&include=content,voteup_count'
    r = request_retry(
        'GET', url, 
        headers=headers,
        proxies={'http': args.proxy, 'https': args.proxy},
    )
    cookies = ext_cookies(r.headers.get('Set-Cookie', ''))
    j = r.json()
    if len(j['data']) == 0:
        print(f'问题 {qid} 没有回答')
        return
    title = '知乎问答：' + j['data'][0]['question']['title']
    co = f'''
        <blockquote>来源：<a href='https://www.zhihu.com/question/{qid}'>https://www.zhihu.com/question/{qid}</a></blockquote>
    '''
    articles = [{'title': title, 'content': co}]
    imgs = {}
    
    while True:
        print(url)
        r = request_retry(
            'GET', url, 
            headers=headers, 
            cookies=cookies,
            proxies={'http': args.proxy, 'https': args.proxy},
        )
        cookies |= ext_cookies(r.headers.get('Set-Cookie', ''))
        j = r.json()
        for art in j['data']:
            art = get_content(art)
            art['content'] = process_img(
                art['content'], imgs, 
                img_prefix='../Images/'
            )
            articles.append(art)
        if j['paging']['is_end']: break
        url = j['paging']['next']
        
    gen_epub(articles, imgs)
