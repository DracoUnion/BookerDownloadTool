from .util import *
import traceback
from concurrent.futures import ThreadPoolExecutor
import json

def tr_download_fmb(i, ssid, pr, writeback):
    print(f'ssid: {ssid}')
    url = f'https://api.freembook.com/search?category=duxiu&q={ssid}'
    j = request_retry(
        'GET', url, 
        retry=10000, 
        check_status=True,
        proxies={'http': pr, 'https': pr},
    ).json()
    books = [
        {
            'id': b[0],
            'ssid': b[1],
            'fileName': b[2],
            'size': b[3],
            'dxid': b[4],
            'bookName': b[5],
            'year': b[6],
            'pageSize': b[7],
            'bookNum': b[8],
        }
        for b in j.get('books', [])
    ]
    for b in books:
        bid = b['id']
        url = f'https://api.freembook.com/acquire?book_id={bid}'
        j = request_retry(
            'GET', url, 
            retry=10000, 
            check_status=True,
            proxies={'http': pr, 'https': pr},
        ).json()
        b['miaochuan'] = j.get('book_baidu', [])

    writeback(i, json.dumps(books).replace('\n', ''))
    
def tr_download_fmb_safe(*args, **kw):
    try: tr_download_fmb(*args, **kw)
    except: traceback.print_exc()

def download_fmb(args):
    st = args.start
    ed = args.end
    proxy = args.proxy.split(';')
    
    ofname = f'freembook_{st}_{ed}.jsonl'
    f = open(ofname, 'w', encoding='utf8')
    
    pool = ThreadPoolExecutor(args.threads)
    hdls = []
    res = [None] * (ed - st + 1)
    cur = 0
    def writeback(i, text):
        nonlocal cur
        res[i] = text
        while cur < len(res) and res[cur]:
            f.write(res[cur] + '\n')
            cur += 1
    for i, ssid in enumerate(range(st, ed + 1)):
        pr = proxy[i % len(proxy)]
        h = pool.submit(tr_download_fmb_safe, i, ssid, pr, writeback)
        hdls.append(h)
    for h in hdls: h.result()
    f.close()