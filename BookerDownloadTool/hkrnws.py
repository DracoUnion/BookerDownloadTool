from .util import *
from datetime import datetime, timedelta
import copy
from concurrent.futures import ThreadPoolExecutor

def fetch_hkrnws(args):
    url = f'https://hckrnews.com/data/{args.date}.js'
    r = request_retry(
        'GET', url, 
        headers=default_hdrs,
        proxies={'http': args.proxy, 'https': args.proxy},
    )
    if r.status_code == 404:
        print(f'未找到 {args.date}')
        return
    j = r.json()
    links = [it['link'] for it in j]
    ofname = f'hkrnws_{args.date}.txt'
    print(ofname)
    open(ofname, 'w', encoding='utf8').write('\n'.join(links))

def fetch_hkrnws_rng(args):
    st, ed = args.start, args.end
    stdt = datetime(int(st[:4]), int(st[4:6]), int(st[6:8]))
    eddt = datetime(int(ed[:4]), int(ed[4:6]), int(ed[6:8]))
    now = datetime.now()
    dt = stdt
    pool = ThreadPoolExecutor(args.threads)
    hdls = []
    while dt <= eddt and dt <= now:
        args = copy.deepcopy(args)
        args.date = f'{dt.year:04d}{dt.month:02d}{dt.day:02d}'
        h = pool.submit(fetch_hkrnws, args)
        hdls.append(h)
        dt += timedelta(days=1)
    for h in hdls:
        h.result()



def reg_subparser(subparsers):
    hkrnws_fetch_parser = subparsers.add_parser("hkrnws-fetch", help="抓取 hckrnews 链接")
    hkrnws_fetch_parser.add_argument("date", help="日期 YYYYMMDD")
    hkrnws_fetch_parser.add_argument("-p", "--proxy", help="代理")
    hkrnws_fetch_parser.set_defaults(func=fetch_hkrnws)

    hkrnws_fetch_parser = subparsers.add_parser("hkrnws-range", help="批量抓取 hckrnews 链接")
    hkrnws_fetch_parser.add_argument("start", help="起始日期 YYYYMMDD")
    hkrnws_fetch_parser.add_argument("end", help="结束日期 YYYYMMDD")
    hkrnws_fetch_parser.add_argument("-p", "--proxy", help="代理")
    hkrnws_fetch_parser.add_argument("-t", "--threads", type=int, default=8, help="线程数")
    hkrnws_fetch_parser.set_defaults(func=fetch_hkrnws_rng)
