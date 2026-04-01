import json
import re
from EpubCrawler.util import request_retry
import argparse
from os import path
import subprocess as subp
import urllib.parse
from .util import *
from pyquery import PyQuery as pq
import execjs
from html import escape as htmlesc
from EpubCrawler.img import process_img
from EpubCrawler.config import config as crconf
from typing import List, Tuple, Dict, Any
from .process_img_md import process_img_md

def parse_attribs(attribs_str: str) -> List[Tuple[List[int], int]]:
    """
    解析属性字符串，返回区间列表，每个区间包含属性索引列表和长度。
    示例: "*0*1+3*2+5" -> [([0,1], 3), ([2], 5)]
    """
    if not attribs_str:
        return []
    pattern = re.compile(r'(\*(?:\d+\*)*\d+)\+([0-9a-f]+)')
    matches = pattern.findall(attribs_str)
    result = []
    for match in matches:
        indices_str, length_str = match
        indices = [int(idx) for idx in indices_str.split('*')[1:] if idx]  # 去掉开头的空字符串
        length = int(length_str, 16)
        result.append((indices, length))
    return result

def apply_styles(text: str, style_indices: List[int], apool: Dict) -> str:
    """
    根据属性索引列表，对文本应用 Markdown 样式（链接优先，然后粗体）。
    """
    # 优先处理链接和内嵌文档组件
    for idx in style_indices:
        attr = apool.get('numToAttrib', {}).get(str(idx))
        if not attr:
            continue
        if attr[0] == 'link':
            url = urllib.parse.unquote(attr[1])
            # 递归处理其他样式（去掉当前链接属性）
            inner = apply_styles(text, [i for i in style_indices if i != idx], apool)
            return f"[{inner}]({url})"
        if attr[0] == 'inline-component':
            try:
                comp = json.loads(attr[1])
                if comp.get('type') == 'mention_doc':
                    data = comp.get('data', {})
                    title = data.get('title', '文档')
                    url = data.get('raw_url', '')
                    return f"[{title}]({url})"
            except json.JSONDecodeError:
                pass
    # 处理粗体
    for idx in style_indices:
        attr = apool.get('numToAttrib', {}).get(str(idx))
        if attr and attr[0] == 'bold' and attr[1] == 'true':
            inner = apply_styles(text, [i for i in style_indices if i != idx], apool)
            return f"**{inner}**"
    # 无样式
    return text

def parse_text_block(text_data: Dict) -> str:
    """
    解析带有属性池的文本块，返回 Markdown 字符串。
    """
    apool = text_data.get('apool', {})
    initial = text_data.get('initialAttributedTexts', {})
    # 这俩不是数组，是键为数字字符串的字典
    text_parts = initial.get('text', {})
    attribs_parts = initial.get('attribs', {})
    if not text_parts:
        return ""

    result = []
    for idx in range(min(len(text_parts), len(attribs_parts))):
        text_str = text_parts.get(str(idx), "")
        attribs_str = attribs_parts.get(str(idx), "")
        if not text_str:
            continue
        intervals = parse_attribs(attribs_str)
        if not intervals:
            # 无样式，直接添加
            result.append(text_str)
            continue

        pos = 0
        for indices, length in intervals:
            # 截取当前区间的文本
            segment = text_str[pos:pos+length]
            if segment:
                styled = apply_styles(segment, indices, apool)
                result.append(styled)
            pos += length
        # 处理剩余文本（可能由于解析不完整，但通常区间覆盖全部）
        if pos < len(text_str):
            result.append(text_str[pos:])
    return ''.join(result)

def parse_table(blk, blk_map):
    assert blk['data']['type'] == 'table'
    cont = []
    cells = blk['data']['cell_set']
    for r in blk['data']['rows_id']:
        cont.append([])
        for c in blk['data']['columns_id']:
            k = r + c
            if k not in cells:
                cont[-1].append("")
                continue
            cid = cells[k]['block_id']
            cell = blk_map[cid]
            tid = cell['data']['children'][0]
            text = get_text_blk_text(blk_map[tid]).replace('\n', ' ')
            cont[-1].append(text)

    md = ''
    for i, r in enumerate(cont):
        md += '| '
        for v in r:
            md += f'{htmlesc(v)} |\n'
        if i == 0:
            md += '| ' + ' --- |' * len(r) + '\n'
    md = md.strip()
    return md


def get_text_blk_text(blk):
    assert 'text' in blk['data']
    return parse_text_block(blk['data']['text'])

def get_img_blk_text(blk):
    assert 'image' in blk['data']
    tok = blk['data']['image']['token']
    return f'![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/v2/cover/{tok}/)'

def blk2md(blk, blk_map):
    tp = blk['data']['type']
    if tp == 'page':
        cont = get_text_blk_text(blk).replace('\n', ' ')
        return f'# {cont}'
    elif tp == 'text':
        lines = [
            l.strip() 
            for l in get_text_blk_text(blk).split('\n')
        ]
        return '\n\n'.join([l for l in lines if l])
    elif tp == 'image':
        return f'{get_img_blk_text(blk)}'
    elif tp.startswith('heading'):
        cont = get_text_blk_text(blk).replace('\n', ' ')
        head = '#' * int(tp[-1])
        return f'{head} {cont}'
    elif tp == 'code':
        return f'```\n{htmlesc(get_text_blk_text(blk))}\n```'
    elif tp == 'divider':
        return '---'
    elif tp == 'ordered':
        return f'1.  {get_text_blk_text(blk)}'
    elif tp == 'bullet':
        return f'+   {get_text_blk_text(blk)}'
    elif tp == 'table':
        return parse_table(blk, blk_map)
    else:
        print(f'未知类型： {tp}')
        return ''

def get_aid_by_wid(uid, wid, cookie):
    url = f'https://{uid}.feishu.cn/space/api/wiki/v2/tree/get_info/?wiki_token={wid}'
    hdrs = default_hdrs | {'Cookie': cookie}
    data = request_retry('GET', url, headers=hdrs).json()
    return data['data']['tree']['nodes'][wid]['obj_token']

def get_docx_md(uid, aid, cookie):
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
    allow_blks = blks
    # 过滤 table_cell 的 children text
    cells = [b for b in blks if b['data']['type'] == 'table_cell']
    chtext = [c['data']['children'] for c in cells]
    chtextids = set(sum(chtext, []))
    allow_blks = [b for b in allow_blks if b['id'] not in chtextids]
    mds = [blk2md(b, blk_map) for b in allow_blks]
    url = f'https://{uid}.feishu.cn/docx/{aid}'
    mds.insert(1, f'> 来源：![{url}]({url})')
    return '\n\n'.join(mds)

def download_feishu(args):
    if not args.cookie:
        raise ValueError('请设置 Cookie')
    crconf['optiMode'] = args.opti_mode
    crconf['headers']['Cookie'] = args.cookie
    m = re.search(r'(\w+).feishu.cn/(docx|docs|wiki)/(\w+)', args.url)
    if not m:
        raise ValueError('URL 格式错误：https://<uid>.feishu.cn/<docx|wiki>/<aid>')
    uid, tp, aid = m.group(1), m.group(2), m.group(3)
    if tp == 'wiki':
        aid = get_aid_by_wid(uid, aid, args.cookie)
    md = get_docx_md(uid, aid, args.cookie)
    imgs = {}
    md = process_img_md(md, imgs, img_prefix='img/')
    md_fname = args.url.split('/')[-1] + '.md'
    open(md_fname, 'w', encoding='utf8').write(md)
    if not path.isdir('img'):
        os.makedirs('img')
    for name, img in imgs.items():
        img_fname = path.join('img', name)
        open(img_fname, 'wb').write(img)