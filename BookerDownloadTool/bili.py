import requests
import json
import os
import sys
from os import path
from moviepy.editor import VideoFileClip
from io import BytesIO
import traceback
import tempfile
import uuid
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from .util import *
import time

def tr_download_meta_bili(aid, write_back, args):
    print(f'aid: {aid}')
    url = f'https://api.bilibili.com/x/web-interface/view?aid={aid}'
    for i in range(args.retry):
        text = requests.get(url, headers=bili_hdrs).text \
                .replace('\r', '') \
                .replace('\n', ' ')
        time.sleep(args.wait)
        if '"message":"请求被拦截"' not in text: 
            break
    write_back(idx, text)
        
    
def tr_download_meta_bili_safe(*args, **kw):
    try: tr_download_meta_bili(*args, **kw)
    except: traceback.print_exc()

def download_meta_bili(args):
    st = int(args.start)
    ed = int(args.end)
    ofile = open(f'bili_meta_{st}_{ed}.jsonl', 'w', encoding='utf8')
    lk = Lock()
    res = [''] * (ed - st + 1)
    cur = 0
    def write_back(idx, text):
        res[idx] = text
        with lk: 
            while res[cur] and cur < len(res):
                ofile.write(res[cur] + '\n')
                cur += 1
    pool = ThreadPoolExecutor(args.threads)
    hdls = []
    for i, aid in enumerate(range(st, ed + 1)):
        h = pool.submit(tr_download_meta_bili_safe, aid, write_back, args)
        hdls.append(h)
    for h in hdls: h.result()
    ofile.close()

def batch_home_bili(args):
    mid = args.mid
    st = args.start
    ed = args.end
    to_audio = args.audio
    for i in range(st, ed + 1):
        url = f'https://api.bilibili.com/x/space/arc/search?search_type=video&mid={mid}&pn={i}&order=pubdate'
        j = requests.get(url, headers=bili_hdrs).json()
        if j['code'] != 0:
            print('解析失败：' + j['message'])
            return
        for it in j['data']['list']['vlist']:
            bv = it['bvid']
            args.id = bv
            download_bili_safe(args)

def batch_kw_bili(args):
    kw = args.kw
    st = args.start
    ed = args.end
    to_audio = args.audio
    kw_enco = quote_plus(kw)
    for i in range(st, ed + 1):
        url = f'https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={kw_enco}&page={i}&order=pubdate'
        j = requests.get(url, headers=bili_hdrs).json()
        if j['code'] != 0:
            print('解析失败：' + j['message'])
            return
        for it in j['data']['result']:
            bv = it['bvid']
            args.id = bv
            download_bili_safe(args)

def download_bili_safe(args):
    try: download_bili(args)
    except Exception as ex: print(ex)

def download_bili_single(id, args):
    to_audio = args.audio
    sp = args.start_page
    ep = args.end_page
    opath = args.output_dir
    safe_mkdir(opath)
    av = ''
    bv = ''
    if id.lower().startswith('av'):
        av = id[2:]
    else:
        bv = id
        
    url = f'https://api.bilibili.com/x/web-interface/view?bvid={bv}&aid={av}'
    j = requests.get(url, headers=bili_hdrs).json()
    if j['code'] != 0:
        print('获取 CID 失败：' + j['message'])
        return
    av = j['data']['aid']
    bv = j['data']['bvid']
    author = fname_escape(j['data']['owner']['name'])
    title1 = fname_escape(j['data']['title'])
    for it in j['data']['pages'][sp-1:ep]:
        cid = it['cid']
        pg = it['page']
        title2 = fname_escape(it['part'])
        title = f'{title1} - P{pg}' if title1 == title2 \
            else f'{title1} - P{pg}：{title2}'
        print(title, author)
        name = f'{title} - {author} - {bv}'
        ext = 'mp3' if to_audio else 'flv'
        fname = path.join(opath, name + '.' + ext)
        if path.isfile(fname):
            print(f'{fname} 已存在')
            continue
        url = f'https://api.bilibili.com/x/player/playurl?cid={cid}&otype=json&bvid={bv}&aid={av}'
        j = requests.get(url, headers=bili_hdrs).json()
        if j['code'] != 0:
            print('解析失败：' + j['message'])
            continue
        video_url = j['data']['durl'][0]['url']
        video = requests.get(video_url, headers=bili_hdrs).content
        if not to_audio:
            open(fname, 'wb').write(video)
            continue
        tmp_fname = path.join(tempfile.gettempdir(), uuid.uuid4().hex + '.flv')
        open(tmp_fname, 'wb').write(video)
        vc = VideoFileClip(tmp_fname)
        vc.audio.write_audiofile(fname)
        vc.reader.close()
        os.unlink(tmp_fname)

def download_bili(args):
    ids = args.id.split(',')
    for id in ids: download_bili_single(id, args)
