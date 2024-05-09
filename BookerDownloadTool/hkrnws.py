from .util import *

def fetch_hkrnws(args):
    url = f'https://hckrnews.com/data/{args.date}.js'
    r = request_retry(
        'GET', url, 
        headers=default_hdrs
    )
    if r.status_code == 404:
        print(f'未找到 {args.date}')
        return
    j = r.json()
    links = [it['link'] for it in j]
    open(f'hkrnws_{args.date}.txt', 'w', encoding='utf8').write('\n'.join(links))