from .util import *
from urllib.parse import quote_plus

def gh_repo_fetch(args):
    ofile = open(args.ofname, 'w', encoding='utf8')

    q_enco = quote_plus(args.query)
    headers = default_hdrs.copy()
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