from collections import deque
from urllib.parse import urljoin, urlparse
import requests
from pyquery import PyQuery as pq
import re
from .util import *
import traceback
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Thread
# from multiprocessing import Lock, Process as Thread
import time
from sqlalchemy import Text, Integer, Column, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

hdrs = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
}

Base = declarative_base()
Session = None
idle = None
lock_get = None
lock_add = None
ofile = None

class UrlRecord(Base):
    __tablename__ = 'url_record'
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, unique=True)
    # 是否已处理，1：已处理，0：未处理
    stat = Column(Integer, index=True, server_default="0")

def get_session_maker(db_fname):
    engine = create_engine(
        'sqlite:///' + db_fname, 
        echo=False,
        pool_size=0, 
        max_overflow=-1,
    )
    Session = sessionmaker(bind=engine)
    return Session

def get_html_checked(url, args):
    for i in range(args.retry):
        html = request_retry(
            'GET', url, 
            retry=args.retry,
            proxies=args.proxy,
            headers=hdrs,
        ).text
        if not args.nonblank: break
        check_text = pq(html).find(args.nonblank).text()
        if check_text.strip(): break
        if i == args.retry - 1:
            raise Exception(f'url: [{url}] element: [{args.nonblank}] checked blank')
    return html

def tr_get_next_safe(i, url, res, args):
    try:
        print(url)
        ns = get_next(url, args)
        res[i] = ns
    except:
        traceback.print_exc()

def get_next(url, args):
    html = get_html_checked(url, args)
    if not html: return []
    html = re.sub(r'<\?xml\x20[^>]*\?>', '', html)
    html = re.sub(r'xmnls=".+?"', '', html)
    rt = pq(html)
    el_links = rt('a')
    links = [
        urljoin(url, pq(el).attr('href').strip()) 
        for el in el_links
        if pq(el).attr('href')
    ]
    hostname = urlparse(url).hostname
    links = [
        l for l in links 
        if urlparse(l).hostname == hostname
    ]
    links = [
        re.sub(r'#.*', '', l)
        for l in links
    ]
    if not args.qs:
        links = [
            re.sub(r'\?.*', '', l)
            for l in links
        ]
    if args.re:
        links = [
            l for l in links
            if re.search(args.re, l)
        ]
    # print(f'url: {url}\nnext: {links}\n')
    return list(set(links))

def tr_whole_site(trid, args):
    sess = Session()
    while True:
        with lock_get:
            rec = sess.query(UrlRecord).filter(UrlRecord.stat == 0).first()
            if rec:
                sess.query(UrlRecord).filter(UrlRecord.id == rec.id) \
                    .update({'stat': 1})
                sess.commit()

        if rec is None:
            idle[trid] = 1
            print(f'[thread {trid}] idle, {sum(idle)}/{args.threads}')
            if sum(idle) == args.threads:
                break
            continue            
        
        url = rec.url
        print(f'[thread {trid}] proc: {url}')
        ofile.write(url + '\n')

        nexts = get_next(url, args)

        has_new = False
        for n in nexts:
            with lock_add:
                exi = sess.query(UrlRecord).filter(UrlRecord.url == n).count()
                if not exi:
                    sess.add(UrlRecord(url=n, stat=0))
                    sess.commit()
                    has_new = True

        if has_new:
            for i in range(len(idle)):
                idle[i] = 0




def whole_site(args):
    global Session
    global idle
    global lock_add
    global lock_get
    global ofile

    site = args.site
    pres = urlparse(site)
    hdrs['Referer'] = f'{pres.scheme}://{pres.hostname}'
    if args.proxy: 
        args.proxy = {'http': args.proxy, 'https': args.proxy}
    if args.cookie:
        hdrs['Cookie'] = args.cookie
    
    # 创建数据库
    pref = re.sub(r'[^\w\-\.]', '-', site)
    db_fname = f'{pref}.db' 
    Session = get_session_maker(db_fname)
    Base.metadata.create_all(Session.kw['bind'])

    # 创建结果文件
    res_fname = f'{pref}.txt'
    ofile = open(res_fname, 'a', encoding='utf8')

    # 初始化数据库
    sess = Session()
    cnt = sess.query(UrlRecord).count()
    if cnt == 0:
        ofile.write(site + '\n')
        sess.add(UrlRecord(url=site, stat=0))
        sess.commit()

    # pool = ThreadPoolExecutor(args.threads)
    trs = []
    lock_add = Lock()
    lock_get = Lock()
    idle = [0] * args.threads
    for i in range(args.threads):
        tr = Thread(
            target=tr_whole_site,
            args=(i, args),
        )
        tr.start()
        trs.append(tr)
    for tr in trs:
        tr.join()
    
    '''
    while q:
        # 取出指定数量的链接
        pop_cnt = min(len(q), args.threads)
        urls = [q.popleft() for _ in range(pop_cnt)]
        # urls = [u for u in urls if not u.endswith('.xml')]
        # 调用子线程获取引用
        nexts = [[] for _ in range(pop_cnt)]
        hdls = []
        for i, url in enumerate(urls):
            h = pool.submit(tr_get_next_safe, i, url, nexts, args)
            hdls.append(h)
        for h in hdls: h.result()
        # 合并、去重
        nexts = set(sum(nexts, []))
        for url in urls:
            ofile.write(url + '\n')
            rec_file.write('-1\n')
        for n in nexts:
            if n not in vis:
                vis.add(n)
                q.append(n)
                rec_file.write(n + '\n')
    '''

    ofile.close()
