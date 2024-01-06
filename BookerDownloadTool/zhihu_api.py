import re
import sys
from EpubCrawler.util import request_retry
from EpubCrawler.img import process_img
from EpubCrawler.config import config as cralwer_config
from datetime import datetime
from GenEpub import gen_epub
import traceback
from concurrent.futures import ThreadPoolExecutor
import copy
from os import path

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
    
def request_retry_no403(*args, **kw):
    kw.setdefault('retry', 10)
    for i in range(kw['retry']):
        r = request_retry(*args, **kw)
        if r.status_code != 403: break
    if r.status_code == 403: raise Exception('HTTP 403')
    return r
    
def zhihu_ques_api(args):
    qid = args.qid
    cralwer_config['optiMode'] = args.opti_mode
    cralwer_config['imgSrc'] = ['data-original', 'src']
    
    print(f'qid: {qid}')
    url = f'https://www.zhihu.com/api/v4/questions/{qid}/feeds?cursor=&include=content,voteup_count'
    r = request_retry_no403(
        'GET', url, 
        retry=args.retry,
        headers=headers,
        proxies={'http': args.proxy, 'https': args.proxy},
    )
    cookies = ext_cookies(r.headers.get('Set-Cookie', ''))
    j = r.json()
    if 'data' not in j:
        print(f'问题 {qid} 不存在')
        return
    if len(j['data']) == 0:
        print(f'问题 {qid} 没有回答')
        return
    answers = [
        it['target'] for it in j['data'] 
        if it['target_type'] == 'answer'
    ]
    title = '知乎问答：' + answers[0]['question']['title']
    if path.isfile(f'{title}.epub') or \
       path.isfile(f'{title} - PT1.epub'):
       print(f'问题 {qid} 已经抓取完毕：{title}')
       return
    co = f'''
        <blockquote>来源：<a href='https://www.zhihu.com/question/{qid}'>https://www.zhihu.com/question/{qid}</a></blockquote>
    '''
    articles = [{'title': title, 'content': co}]
    imgs = {}
    
    while True:
        print(url)
        r = request_retry_no403(
            'GET', url, 
            retry=args.retry,
            headers=headers, 
            cookies=cookies,
            proxies={'http': args.proxy, 'https': args.proxy},
        )
        cookies.update(ext_cookies(r.headers.get('Set-Cookie', '')))
        j = r.json()
        answers = [
            it['target'] for it in j['data'] 
            if it['target_type'] == 'answer'
        ]
        for ans in answers:
            art = get_content(ans)
            art['content'] = process_img(
                art['content'], imgs, 
                img_prefix='../Images/'
            )
            articles.append(art)
        if j['paging']['is_end']: break
        url = j['paging']['next']
        
    gen_epub(articles, imgs)

def zhihu_ques_api_safe(args):
    try:
        zhihu_ques_api(args)
    except:
        traceback.print_exc()
        
def zhihu_ques_range_api(args):
    pool = ThreadPoolExecutor(args.threads)
    hdls = []
    
    for i in range(args.start, args.end + 1):
        args = copy.deepcopy(args)
        args.qid = i
        h = pool.submit(zhihu_ques_api_safe, args)
        hdls.append(h)
        # 及时释放内存
        if len(hdls) >= args.threads:
            for h in hdls: h.result()
            hdls = []
    
    for h in hdls: h.result()