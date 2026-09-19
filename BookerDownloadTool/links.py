import sys
from urllib.parse import urljoin, urlparse
from pyquery import PyQuery as pq
import json
import re
import subprocess as subp
from .util import *

config = {
    'url': '',
    'link': '',
    'time': '',
    'proxy': None,
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
    },
}

def get_toc_json(jstr, re_tm):
    j = json.loads(jstr)
    links = dict_get_recur(j, config['link'])
    times = None
    if config['time']:
        times = dict_get_recur(j, config['time'])
        assert len(links) == len(times)
        for i, t in enumerate(times):
            m = re.search(re_tm, t)
            times[i] = m.group() if m else t
        links = [f'{l}#{t}' for l, t in zip(links,times)]
    return links
    

def get_toc(html, base, re_tm):
    root = pq(html)
    el_links = root(config['link'])
    el_times = None
    if config['time']:
        el_times = root(config['time'])
        assert len(el_links) == len(el_times)
    links = []
    for i in range(len(el_links)):
        url = el_links.eq(i).attr('href')
        if not url:
            links.append(el_links.eq(i).text().strip())
            continue
        url = urljoin(base, url)
        if el_times:
            tm = el_times.eq(i).text().strip()
            m = re.search(re_tm, tm)
            url += '#' + (m.group() if m else tm)
        links.append(url)
    return links

def fetch_links(args):
    config['url'] = args.url
    config['link'] = args.link
    config['time'] = args.time
    ofname = args.ofname
    st = args.start
    ed = args.end
    
    if args.proxy:
        config['proxy'] = {
            'http': args.proxy,
            'https': args.proxy,
        }
    if args.headers:
        config['headers'] = json.loads(args.headers)
    
    ofile = open(ofname, 'a', encoding='utf-8')
    
    for i in range(st, ed + 1):
        url = config['url'].replace('{i}', str(i))
        print(url)
        html = request_retry(
            'GET', url, 
            proxies=config['proxy'],
            headers=config['headers'],
        ).text
        if args.json:
            toc = get_toc_json(html, args.time_regex)
        else:
            toc = get_toc(html, url, args.time_regex)
        if len(toc) == 0: break
        for it in toc:
            print(it)
            ofile.write(str(it) + '\n')
    
    ofile.close()

def get_date_from_url(url, rgx):
    m = re.search('#' + rgx, url)
    if not m: return '000101'
    yr = m.group(1)
    mon = m.group(2)
    if len(mon) == 1: mon = '0' + mon
    return yr + mon

def batch_links(args):
    num = args.num
    if not args.name:
        args.name = re.sub(r'\.\w+$', '', path.basename(args.links))
    links = open(args.links, encoding='utf8').read().split('\n')
    links = list(filter(None, links))
    
    dates = [get_date_from_url(l, args.time_regex) for l in links]
    
    for i in range(0, len(links), args.num):
        st = dates[i]
        ed = dates[i:i+args.num][-1]
        if st > ed: st, ed = ed, st
        
        cfg = {
            'name': f'{args.name}_{st}_{ed}',
            'url': links[i],
            'title': args.title,
            'content': args.content,
            'remove': args.remove,
            'optiMode': args.opti_mode,
            'list': links[i:i+args.num],
            'sizeLimit': args.size_limit,
        }

        cfg_fname = f'config_{fname_escape(args.name)}_{st}_{ed}.json'
        open(cfg_fname, 'w', encoding='utf8').write(json.dumps(cfg))
        print(cfg_fname)
        if args.exec:
            subp.Popen(['crawl-epub', cfg_fname], shell=True).communicate()
        
        
def fetch_sitemap_handle(args):
    if not args.ofname:
        args.ofname = re.sub(r'\W', '_', args.url) + '.txt'
    url, regex, ofname = args.url, args.regex, args.ofname
    urls = fetch_sitemap(url, regex, args.proxy)
    f = open(ofname, 'w', encoding='utf8')
    for u in urls:
        f.write(u + '\n')
        print(u)
    f.close()

        
def fetch_sitemap(url, rgx=None, pr=None):
    xml = request_retry(
        'GET', url, 
        headers=config['headers'],
        proxies={'http': pr, 'https': pr},
    ).text
    urls = re.findall(r'<loc>(.+?)</loc>', xml)
    urls = [u.strip() for u in urls]
    subs = [
        u for u in urls
        if u.endswith('.xml')
    ]
    res = []
    for s in subs:
        res += fetch_sitemap(s, rgx, pr)
    res += [
        f'{u}#0001-01-01' for u in urls
        if not u.endswith('.xml') 
           and re.search(rgx, u)
    ]
    return res

    

def reg_subparser(subparsers):
    links_parser = subparsers.add_parser("links", help="抓取分页链接")
    links_parser.add_argument("url", help="URL，{i} 为页码占位符")
    links_parser.add_argument("link", help="链接选择器")
    links_parser.add_argument("ofname", help="输出文件名")
    links_parser.add_argument("-s", "--start", type=int, default=1, help="起始页")
    links_parser.add_argument("-e", "--end", type=int, default=10000000, help="结束页码")
    links_parser.add_argument("-t", "--time", help="时间选择器")
    links_parser.add_argument("-r", "--time-regex", default=r"\d+-\d+-\d+", help="时间正则")
    links_parser.add_argument("-p", "--proxy", help="代理")
    links_parser.add_argument("-H", "--headers", help="请求头 JSON")
    links_parser.add_argument("-J", "--json", action='store_true', help="将输出视为 JSON 而非 HTML")
    links_parser.set_defaults(func=fetch_links)

    sitemap_parser = subparsers.add_parser("sitemap", help="抓取站点地图链接")
    sitemap_parser.add_argument("url", help="站点地图 URL")
    sitemap_parser.add_argument("-r", "--regex", default="/blog/", help="链接正则")
    sitemap_parser.add_argument("-o", "--ofname", help="输出文件名")
    sitemap_parser.add_argument("-p", "--proxy", help="代理")
    sitemap_parser.set_defaults(func=fetch_sitemap_handle)

    links_epub_parser = subparsers.add_parser("links-epub", help="批量下载链接生成 EPUB")
    links_epub_parser.add_argument("links", help="存储链接的文件名")
    links_epub_parser.add_argument("--name", help="EPUB 名称")
    links_epub_parser.add_argument("-t", "--title", default="", help="标题选择器")
    links_epub_parser.add_argument("-c", "--content", default="", help="内容选择器")
    links_epub_parser.add_argument("-r", "--remove", default="", help="移除元素选择器")
    links_epub_parser.add_argument("-n", "--num", default=500, type=int, help="每卷 EPUB 文章数")
    links_epub_parser.add_argument("-m", "--opti-mode", default='quant', help="图片优化模式")
    links_epub_parser.add_argument("-l", "--size-limit", default='100m', help="EPUB 大小限制")
    links_epub_parser.add_argument("-g", "--time-regex", default=r'(\d+)-(\d+)-(\d+)', help="时间正则")
    links_epub_parser.add_argument("-E", "--exec", action='store_true', help="是否执行 EpubCrawler 处理配置文件")
    links_epub_parser.set_defaults(func=batch_links)
