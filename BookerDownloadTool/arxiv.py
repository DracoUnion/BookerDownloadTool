from .util import *


def get_total(html):
    rt = pq(html)
    txt = rt('h2+small').text()
    m = re.search(r'(\d+)\x20entries', txt)
    if not m: return 0
    return int(m.group(1))
    
def get_ids(html):
    rt = pq(html)
    el_links = rt('.list-identifier>a:first-of-type')
    ids = [
        pq(el).attr('href').split('/')[-1]
        for el in el_links
    ]
    return ids
    
def arxiv_fetch(args):
    pgsz = min(args.page_size, 2000)
    sub = args.subject
    yrmon = args.year_month
    
    url = f'https://arxiv.org/list/{sub}/{yrmon}'
    html = request_retry('GET', url).text
    total = get_total(html)
    ofile = open(f'arxiv_{sub}_{yrmon}_{total}.txt', 'w', encoding='utf8')
    
    for i in range(0, total, pgsz):
        print(f'{sub}, {yrmon}, {i+1}-{i+pgsz}')
        url = f'https://arxiv.org/list/{sub}/{yrmon}?skip={i}&show={pgsz}'
        html = request_retry('GET', url).text
        ids = get_ids(html)
        print('\n'.join(ids))
        ofile.write('\n'.join(ids) + '\n')
        
    ofile.close()