import argparse
import re
from urllib.parse import urlparse
from .util import *

PAGE_SIZE = 10000

def get_url_key(url, args):
    info = urlparse(url)
    k = info.path
    if args.query: k += '?' + info.query
    if args.fragment: k += '#' + info.fragment
    return k

def url_dedup(li, args):
    res = []
    for url in li:
        k = get_url_key(url, args)
        if not re.search(args.regex, k): continue
        if k in args.vis: continue
        res.append(url)
        args.vis.add(k)
    return res

def fetch_webarchive(args):
    proxy = {'https': args.proxy, 'http': args.proxy}
    ofname = re.sub('\W', '_', args.host) + '_' + str(args.start) + '_' + str(args.end) + '.txt'
    ofile = open(ofname, 'w', encoding='utf8')
    
    for i in range(args.start, args.end):
        print(f'page: {i}')
        offset = (i - 1) * PAGE_SIZE
        url = (
            'https://web.archive.org/cdx/search/cdx' +
            f'?url={args.host}/*&output=json' +
            '&filter=statuscode:200&filter=mimetype:text/html' +
            f'&limit={PAGE_SIZE}&offset={offset}' +
            '&collapse=urlkey&fl=original'
        )
        j = request_retry('GET', url, proxies=proxy).json()
        if not j: break
        li = [l[0] for l in j[1:]]
        li = url_dedup(li, args)
        for url in li:
            ofile.write(f'https://web.archive.org/web/{url}\n')
            print(f'https://web.archive.org/web/{url}')
        
    ofile.close()
