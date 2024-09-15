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

def tr_download_meta_bili(idx, aid, pr, write_back, args):
    print(f'aid: {aid}')
    url = f'https://api.bilibili.com/x/web-interface/view?aid={aid}'
    for i in range(args.retry):
        text = request_retry(
            'GET', url, 
            headers=bili_hdrs,
            retry=args.retry,
            proxies = {'http': pr, 'https': pr},
        ).text \
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
    proxy = args.proxy.split(';')
    proxy = [p.strip() for p in proxy]
    ofile = open(f'bili_meta_{st}_{ed}.jsonl', 'a+', encoding='utf8')
    if ofile.tell() != 0:
        ofile.seek(0, 0)
        cont = ofile.read()
        offset = cont.count('\n')
        st += offset
    lk = Lock()
    res = [''] * (ed - st + 1)
    cur = 0
    def write_back(idx, text):
        nonlocal cur
        res[idx] = text
        with lk: 
            while cur < len(res) and res[cur]:
                ofile.write(res[cur] + '\n')
                cur += 1
    pool = ThreadPoolExecutor(args.threads)
    hdls = []
    for i, aid in enumerate(range(st, ed + 1)):
        pr = proxy[i % len(proxy)]
        h = pool.submit(tr_download_meta_bili_safe, i, aid, pr, write_back, args)
        hdls.append(h)
    for h in hdls: h.result()
    ofile.close()

def batch_home_bili(args):
    mid = args.mid
    st = args.start
    ed = args.end
    hdrs = bili_hdrs.copy()
    hdrs['Cookie'] = args.cookie
    for i in range(st, ed + 1):
        url = f'https://api.bilibili.com/x/space/wbi/arc/search?mid={mid}&tid=0&pn={i}&order=pubdate&platform=web'
        j = requests.get(url, headers=hdrs).json()
        if j['code'] != 0:
            print('解析失败：' + j['message'])
            return
        res = j['data']['list']['vlist']
        if len(res) == 0: break
        for it in res:
            bv = it['bvid']
            args.id = bv
            download_bili_safe(args)

def batch_kw_bili(args):
    kw = args.kw
    st = args.start
    ed = args.end
    kw_enco = quote_plus(kw)
    hdrs = bili_hdrs.copy()
    hdrs['Cookie'] = args.cookie
    for i in range(st, ed + 1):
        url = f'https://api.bilibili.com/x/web-interface/wbi/search/type?__refresh__=true&page={i}&page_size=50&platform=pc&highlight=1&single_column=0&keyword={kw_enco}&source_tag=3&search_type=video&order=pubdate'
        j = requests.get(url, headers=hdrs).json()
        if j['code'] != 0:
            print('解析失败：' + j['message'])
            return
        res = j['data']['result']
        if len(res) == 0: break
        for it in res:
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
    hdrs = bili_hdrs.copy()
    hdrs['Cookie'] = args.cookie

    url = f'https://api.bilibili.com/x/web-interface/view?bvid={bv}&aid={av}'
    j = requests.get(url, headers=hdrs).json()
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
        title = (
            f'{title1} - P{pg}' 
            if title1 == title2
            else f'{title1} - P{pg}：{title2}'
        )
        print(title, author)
        name = f'{title} - {author} - {bv}.mp4'
        fname = path.join(opath, name)
        if path.isfile(fname):
            print(f'{fname} 已存在')
            continue
        url = f'https://api.bilibili.com/x/player/playurl?fnval=80&cid={cid}&otype=json&bvid={bv}&aid={av}'
        j = requests.get(url, headers=hdrs).json()
        if j['code'] != 0:
            print('解析失败：' + j['message'])
            continue
        
        videos = j['data']['dash']['video']
        audios = j['data']['dash']['audio']
        if len(videos) == 0 or len(audios) == 0:
            print('解析失败，视频列表为空')
            continue
        audio_url = audios[0]['base_url']
        print(f'audio: {audio_url}')
        audio = requests.get(audio_url, headers=hdrs, timeout=(8, None)).content
        if args.audio:
            open(fname, 'wb').write(audio)
            continue
        video_url = videos[0]['base_url']
        print(f'video: {video_url}')
        video = requests.get(video_url, headers=hdrs, timeout=(8, None)).content
        video = merge_video_audio(video, audio)
        open(fname, 'wb').write(video)

def download_bili(args):
    ids = args.id.split(',')
    for id in ids: download_bili_single(id, args)

def download_bilisub(args):
    ids = args.id.split(',')
    for id in ids: download_bilisub_single(id, args)

def download_bilisub_single(id, args):
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
    hdrs = bili_hdrs.copy()
    hdrs['Cookie'] = args.cookie

    url = f'https://api.bilibili.com/x/web-interface/view?bvid={bv}&aid={av}'
    j = requests.get(url, headers=hdrs).json()
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
        title = (
            f'{title1} - P{pg}' 
            if title1 == title2
            else f'{title1} - P{pg}：{title2}'
        )
        print(title, author)
        name = f'{title} - {author} - {bv}.srt'
        fname = path.join(opath, name)
        if path.isfile(fname):
            print(f'{fname} 已存在')
            continue
        url = f'https://api.bilibili.com/x/player/wbi/v2?aid={av}&cid={cid}'
        j = requests.get(url, headers=hdrs).json()
        subtitles = j['data']['subtitle']['subtitles']
        prefs = [s for s in subtitles if s['lan'] in ['ai-zh', 'zh']]
        if not prefs:
            print(f'{fname} 无可用字幕')
            continue
        url = 'https:' + prefs[0]['subtitle_url']
        sub =  requests.get(url, headers=hdrs).json()
        open(fname, 'w', encoding='utf8').write(bilisub2srt(sub))

def bilisub2srt(j):
    subs = j['body']

    srts = []
    for i, sub in enumerate(subs, start=1):
        st = float2hhmmss(sub['from'])
        ed = float2hhmmss(sub['to'])
        txt = sub['content']
        srtpt = f'{i}\n{st} ---> {ed}\n{txt}'
        srts.append(srtpt)

    srt = '\n\n'.join(srts)
    return srt