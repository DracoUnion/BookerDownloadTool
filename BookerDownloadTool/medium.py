import sys
import re
from datetime import datetime, timedelta
from pyquery import PyQuery as pq
from .util import *

def get_links(html, dt):
    dt_str = dt.strftime('%Y-%m-%d')
    rt = pq(html)
    links = [pq(el).attr('href') for el in rt('.postArticle-readMore>a')]
    tms = [pq(el).attr('datetime')[:10] for el in rt('time')]
    links = [
        l + '#' + t
        for l, t in zip(links, tms)
        if t == dt_str
    ]
    return links

def fetch_medium(args):
    host, st, ed = args.host, args.start, args.end
    proxy = {'https': args.proxy, 'http': args.proxy}
    ofname = re.sub(r'\W', '_', host) + '_' + st + '_' + ed + '.txt'
    stdt = datetime(int(st[:4]), int(st[4:6]), int(st[6:8]))
    eddt = datetime(int(ed[:4]), int(ed[4:6]), int(ed[6:8]))
    ofile = open(ofname, 'w', encoding='utf8')
    dt = stdt
    now = datetime.now()
    while dt <= eddt and dt <= now:
        url = f'https://{host}/archive/{dt.year}/{dt.month:02d}/{dt.day:02d}/'
        print(url)
        html = request_retry('GET', url, proxies=proxy).text
        links = get_links(html, dt)
        if links:
            print('\n'.join(links))
            ofile.write('\n'.join(links) + '\n')
        dt = dt + timedelta(days=1)
    ofile.close()
    


def reg_subparser(subparsers):
    med_parser = subparsers.add_parser("medium", help="抓取 Medium 文章列表")
    med_parser.add_argument("host", help="Medium 博客主机: xxx.medium.com 或 medium.com/xxx")
    med_parser.add_argument('-s', '--start', default='20150101', help="起始日期")
    med_parser.add_argument('-e', '--end', default='99991231', help="结束日期")
    med_parser.add_argument('-p', '--proxy', help="代理")
    med_parser.set_defaults(func=fetch_medium)
