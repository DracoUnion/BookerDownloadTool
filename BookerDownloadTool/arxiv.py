from .util import *
from pyquery import PyQuery as pq
import re
import arxiv

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

    search = arxiv.Search(
        query = query,
        max_results = None,
        sort_by = arxiv.SortCriterion.SubmittedDate,
        sort_order = arxiv.SortOrder.Descending,
    )
    cl = arxiv.Client(
        page_size=pg_size, 
        delay_seconds=1, 
        num_retries=100_000
    )
    
    results = list(cl.results(search))
    ids = [r.entry_id.split('/')[-1] for r in results]
    
    ofile = open(f'arxiv_{args.kw}_{args.cate}_{args.start}_{args.end}.txt', 'w', encoding='utf8')
    ofile.write('\n'.join(ids) + '\n')    
    ofile.close()

def reg_subparser(subparsers):
    arxiv_fetch_parser = subparsers.add_parser("arxiv-fetch", help="抓取 arXiv id")
    arxiv_fetch_parser.add_argument("-c", "--cate", default="", help="分类代码")
    arxiv_fetch_parser.add_argument("-s", "--start", default="", help="起始日期 yyyymmdd")
    arxiv_fetch_parser.add_argument("-e", "--end", default="", help="结束日期 yyyymmdd")
    arxiv_fetch_parser.add_argument("-ps", "--page-size", type=int, default=2000, help="每页数量")
    arxiv_fetch_parser.add_argument("--kw", default="", help="关键词")
    arxiv_fetch_parser.set_defaults(func=arxiv_fetch)
