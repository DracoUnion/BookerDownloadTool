import json
import re
from EpubCrawler.util import request_retry
import argparse
from os import path
import subprocess as subp
from .util import *
from pyquery import PyQuery as pq
import execjs
from EpubCrawler.img import process_img
from EpubCrawler.config import config as crconf

ALLOW_TYPES = {
    'page',
    'text',
    'image',
    'heading1',
    'heading2',
    'heading3',
    'heading4',
    'heading5',
    'heading6',
}


def blk2html(blk):
    tp = blk['data']['type']
    tok2_img_tag = lambda tok: f'<img src="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/v2/cover/{tok}/" />'
    cont = (
        blk['data']['text']['initialAttributedTexts']['text']['0']
        if 'text' in blk['data'] else 
        tok2_img_tag(blk['data']['image']['token'])
        if 'image' in blk['data'] else ''
    )
    if tp == 'page':
        cont = cont.replace('\n', ' ')
        return f'<h1>{cont}</h1>'
    elif tp in ['text', 'image']:
        lines = [l.strip() for l in cont.split('\n')]
        return '\n'.join([f'<p>{l}</p>' for l in lines if l])
    elif tp.startswith('heading'):
        cont = cont.replace('\n', ' ')
        tag = 'h' + tp[-1]
        return f'<{tag}>{cont}</{tag}>'
    else:
        raise ValueError()

def get_aid_by_wid(wid, cookie=''):
    url = f'https://jviztcgxxfy.feishu.cn/space/api/wiki/v2/tree/get_info/?wiki_token={wid}'
    hdrs = default_hdrs | {'Cookie': cookie}
    data = request_retry('GET', url, headers=hdrs).json()
    return data['data']['tree']['nodes'][wid]['obj_token']

def get_docx_html(uid, aid, cookie=''):
    url = f'https://{uid}.feishu.cn/space/api/docx/pages/client_vars?id={aid}&limit=1000000000'
    hdrs = default_hdrs | {'Cookie': cookie}
    data = request_retry('GET', url, headers=hdrs).json()
    '''
    rt = pq(html)
    el_data_sc = pq([
        el for el in rt('script')
        if pq(el).text().strip().startswith('window.DATA =')
    ])
    if len(el_data_sc) == 0:
        raise ValueError('找不到内容元素！')
    jscode = 'var window = {};' + el_data_sc.text()
    
    data = execjs.compile(jscode).eval('window.DATA')
    '''
    blk_ids = data['data']['block_sequence']
    blk_map = data['data']['block_map']
    blks = [blk_map[bid] for bid in blk_ids]
    blks = [b for b in blks if b['data']['type'] in ALLOW_TYPES]
    htmls = [blk2html(b) for b in blks]
    url = f'https://{uid}.feishu.cn/docx/{aid}'
    htmls.insert(1, f'<blockquote>来源：<a href="{url}">{url}</a></blockquote>')
    return '\n'.join(htmls)

def download_feishu(args):
    if not args.cookie:
        raise ValueError('请设置 Cookie')
    crconf['optiMode'] = args.opti_mode
    crconf['headers']['Cookie'] = args.cookie
    m = re.search(r'(\w+).feishu.cn/(docx|wiki)/(\w+)', args.url)
    if not m:
        raise ValueError('URL 格式错误：https://<uid>.feishu.cn/<docx|wiki>/<aid>')
    uid, tp, aid = m.group(1), m.group(2), m.group(3)
    if tp == 'wiki':
        aid = get_aid_by_wid(aid, args.cookie)
    html = get_docx_html(uid, aid, args.cookie)
    imgs = {}
    html = process_img(html, imgs, img_prefix='img/')
    html_fname = args.url.split('/')[-1] + '.html'
    open(html_fname, 'w', encoding='utf8').write(html)
    if not path.isdir('img'):
        os.makedirs('img')
    for name, img in imgs.items():
        img_fname = path.join('img', name)
        open(img_fname, 'wb').write(img)