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
        return f'<h1>{cont}</h1>'
    elif tp in ['text', 'image']:
        return f'<p>{cont}</p>'
    elif tp.startswith('heading'):
        tag = 'h' + tp[-1]
        return f'<{tag}>{cont}</{tag}>'
    else:
        raise ValueError()

def get_docx_html(url, cookie=''):
    if not re.search(r'^https://\w+\.feishu.cn/docx/\w+$', url):
        raise ValueError('URL 格式错误：https://<user>.feishu.cn/docx/<art>')
    hdrs = default_hdrs | {'Cookie': cookie}
    html = request_retry('GET', url, headers=hdrs).text
    rt = pq(html)
    el_data_sc = pq([
        el for el in rt('script')
        if pq(el).text().strip().startswith('window.DATA =')
    ])
    if len(el_data_sc) == 0:
        raise ValueError('找不到内容元素！')
    jscode = 'var window = {};' + el_data_sc.text()
    data = execjs.compile(jscode).eval('window.DATA')
    blk_ids = data['clientVars']['data']['block_sequence']
    blk_map = data['clientVars']['data']['block_map']
    blks = [blk_map[bid] for bid in blk_ids]
    blks = [b for b in blks if b['data']['type'] in ALLOW_TYPES]
    html = '\n'.join([blk2html(b) for b in blks])
    return html

def download_feishu(args):
    crconf['optiMode'] = args.opti_mode
    crconf['headers']['Cookie'] = args.cookie
    url = args.url
    html = get_docx_html(url, args.cookie)
    imgs = {}
    html = process_img(html, imgs, img_prefix='img/')
    html_fname = url.split('/')[-1] + '.html'
    open(html_fname, 'w', encoding='utf8').write(html)
    if not path.isdir('img'):
        os.makedirs('img')
    for name, img in imgs.items():
        img_fname = path.join('img', name)
        open(img_fname, 'wb').write(img)