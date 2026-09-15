from .util import *
from pyquery import PyQuery as pq
import re

def get_arxiv_ids(html):
    html = rm_xml_tags(html)
    rt = pq(html)
    return [pq(el).text().split('/')[-1] for el in rt('id')]

def arxiv_fetch(args):
    pg_size = min(args.page_size, 3000)
    query_list = []
    if args.cate:
        query_list.append(f'cat:{args.cate}')
    if args.start and args.end:
        query_list.append(f'submittedDate:[{args.start} TO {args.end}]')
    if args.kw:
        query_list.append(f'all:{args.kw}')
    query = ' AND '.join(query_list)

    ids = []
    start = 0
    while True:
        params = {
                'search_query': query,
                'start': start,
                'max_results': pg_size,  # API限制
                'sortBy': 'submittedDate',
                'sortOrder': 'descending'
        }

        url = f'http://export.arxiv.org/api/query'
        html = request_retry(
            'GET', url,
            params=params,
            headers=default_hdrs
        ).text
        ids_pt = get_arxiv_ids(html)
        if not ids_pt: break
        ids += ids_pt
        print(ids_pt)
        start += pg_size
    
    ofile = open(f'arxiv_{args.cate}_{args.start}_{args.end}.txt', 'w', encoding='utf8')
    ofile.write('\n'.join(ids) + '\n')    
    ofile.close()

def reg_subparser(subparsers):
    arxiv_fetch_parser = subparsers.add_parser("arxiv-fetch", help="fetch arxiv ids")
    arxiv_fetch_parser.add_argument("-c", "--cate", help="category code")
    arxiv_fetch_parser.add_argument("-s", "--start", help="starting yyyymmdd")
    arxiv_fetch_parser.add_argument("-e", "--end", help="ending yyyymmdd")
    arxiv_fetch_parser.add_argument("-s", "--page-size", type=int, default=2000, help="page size")
    arxiv_fetch_parser.add_argument("--kw", default="", help="key words")
    arxiv_fetch_parser.set_defaults(func=arxiv_fetch)
