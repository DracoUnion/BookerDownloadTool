import traceback
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor
from .util   import *
from pyquery import PyQuery as pq

def tr_download_pic(url, fname, args):
    print(f'{fname}: {url}')
    data = request_retry(
        'GET', url, 
        headers=default_hdrs,
        proxies={'http': args.proxy, 'https': args.proxy},
    ).content
    ofname = path.join(args.dir, fname)
    open(ofname, 'wb').write(data)

def tr_download_pic_safe(*args, **kw):
    try:
        tr_download_pic(*args, **kw)
    except:
        traceback.print_exc()

def download_pixabay(args):
    kw = quote_plus(args.kw)
    safe_mkdir(args.dir)

    driver = create_driver()
    pool = ThreadPoolExecutor(args.threads)
    hdls = []
    for i in range(args.start, args.end + 1):
        print(f'page: {i}')
        url = f'https://pixabay.com/images/search/{kw}/?pagi={i}'
        driver.get(url)
        driver.implicitly_wait(5)
        '''
        html = request_retry(
            'GET', url, 
            headers=default_hdrs,
            proxies={'http': args.proxy, 'https': args.proxy},
        ).text
        '''
        html = driver.page_source
        el_pics = pq(html).find('div[class^=container]>a[class^=link]')
        for el in el_pics:
            el = pq(el)
            img_url = el.children('img').attr('srcset').split(',\x20')[-1].split('\x20')[0]
            img_fname = path.basename(el.attr('alt')[:-1]) + '.png'
            h = pool.submit(tr_download_pic_safe, img_url, img_fname, args)
            hdls.append(h)
            if len(hdls) >= args.threads:
                for h in hdls: h.result()

        for h in hdls: h.result()
