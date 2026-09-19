import os
from .util import *
from urllib.parse import quote_plus

def gh_repo_fetch(args):
    ofile = open(args.ofname, 'a', encoding='utf8')

    q_enco = quote_plus(args.query)
    headers = default_hdrs.copy()
    if args.token:
        headers['Authorization'] = 'token ' + args.token
    for pg_num in range(args.start, args.end + 1):
        print(f'page: {pg_num}')
        url = f'https://api.github.com/search/repositories' + \
              f'?q={q_enco}&per_page=100&page={pg_num}'
        j = request_retry(
            'GET', url, 
            retry=args.retry,
            proxies={'http': args.proxy, 'https': args.proxy},
            headers=headers,
            check_status=True,
        ).json()
        if not j['items']: break
        for repo in j['items']:
            print(repo['full_name'])
            ofile.write(repo['full_name'] + '\n')

    ofile.close()

def reg_subparser(subparsers):
    gh_repo_parser = subparsers.add_parser("gh-repo-fetch", help="抓取 GitHub 仓库")
    gh_repo_parser.add_argument("-s", "--start", type=int, default=1, help="起始页")
    gh_repo_parser.add_argument("-e", "--end", type=int, default=1_000_000, help="结束页码")
    gh_repo_parser.add_argument("-t", "--token", default=os.environ.get('GH_TOKEN', ''), help="GitHub 令牌")
    gh_repo_parser.add_argument("-r", "--retry", type=int, default=10, help="重试次数")
    gh_repo_parser.add_argument("-p", "--proxy", help="代理")
    gh_repo_parser.add_argument("query", help="搜索关键词")
    gh_repo_parser.add_argument("ofname", help="输出文件名")
    gh_repo_parser.set_defaults(func=gh_repo_fetch)
