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
    except KeyboardInterrupt:
        raise
    except:
        traceback.print_exc()

def download_pixabay(args):
    kw = quote_plus(args.kw)
    safe_mkdir(args.dir)

    with camou_create_driver() as (browser, context, page):
        pool = ThreadPoolExecutor(args.threads)
        hdls = []
        for i in range(args.start, args.end + 1):
            print(f'page: {i}')
            url = f'https://pixabay.com/images/search/{kw}/?pagi={i}'
            page.goto(url, wait_until='domcontentloaded', timeout=30_000)
            page.evaluate('''
                document.body.style.zoom = '1%';
                window.scrollTo(0, document.body.scrollHeight);
            ''')
            page.wait_for_timeout(5_000)
            '''
            html = request_retry(
                'GET', url,
                headers=default_hdrs,
                proxies={'http': args.proxy, 'https': args.proxy},
            ).text
            '''
            html = page.content()
            el_pics = pq(html).find('div[class^=container]>a[class^=link]')
            for el in el_pics:
                el = pq(el)
                el_img = el.children('img').eq(0)
                if el_img.attr('srcset'):
                    img_url = el_img.attr('srcset').split(',\\x20')[-1].split('\\x20')[0]
                else:
                    img_url = el_img.attr('src')
                img_fname = path.basename(el.attr('href')[:-1]) + '.png'
                if path.isfile(path.join(args.dir, img_fname)):
                    continue
                h = pool.submit(tr_download_pic_safe, img_url, img_fname, args)
                hdls.append(h)

            for h in hdls:
                h.result()
        pool.shutdown()
