from .util import *
from pyquery import PyQuery as pq
import re

def get_arxiv_ids(html):
    html = rm_xml_tags(html)
    rt = pq(html)
    return [pq(el).text().split('/')[-1] for el in rt('id')]

def arxiv_fetch(args):
    pg_size = min(args.page_size, 3000)
    query = f'cat:{args.cate} AND submittedDate:[{args.start} TO {args.end}]'

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