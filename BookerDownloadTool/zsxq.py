import requests
from pyquery import PyQuery as pq
from urllib.parse import unquote_plus
import json
import re
import os
from os import path
from EpubCrawler.util import request_retry
from EpubCrawler.img import process_img
from EpubCrawler.config import config
import argparse
from GenEpub import gen_epub
from urllib.parse import quote_plus
from datetime import datetime, timedelta


config['optiMode'] = 'thres'
config['imgThreads'] = 16
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36',
}

        
def process_text(text):
    text = text.replace('\n', '<br />')
    root = pq(f'<div>{text}</div>')
    el_tags = root('e[type=hashtag]')
    for t in el_tags:
        t = pq(t)
        title = unquote_plus(t.attr('title'))
        hid = t.attr('hid')
        t.replace_with(f'<span data-hid="{hid}">{title}</span>')
    el_links = root('e[type=web]')
    for l in el_links:
        l = pq(l)
        title = unquote_plus(l.attr('title') or '')
        href = unquote_plus(l.attr('href'))
        l.replace_with(f'<a href="{href}">{title}</a>')
    return str(root)
    
def get_article(j):
    res = []
    if 'resp_data' not in j:
        return res
    
    for it in j['resp_data']['topics']:
        if 'type' not in it:
            continue
        tp = it['type']
        if tp not in it:
            continue
        # un & time
        un = it[tp]['owner']['name']
        tm = conv_time_str(it['create_time'])
        
        # text
        text = process_text(it[tp].get('text', ''))
        # images
        imgs = '\n'.join([
            '<p><img src="{}" /></p>'.format(img['large']['url'])
            for img in it[tp].get('images', [])
        ])
        #likes
        likes = [
            like['owner']['name']
            for like in it.get('latest_likes', [])
        ]
        like_text = '，'.join(likes[:10])
        if it['likes_count'] > 10:
            like_text += ' 等{}人'.format(it['likes_count'])
        if like_text == "":
            like_text = "无"
        like_text = f'<p>👍 {like_text}</p>'
        # rewards
        rewards = [
            r['owner']['name']
            for r in it.get('rewards', [])
        ]
        r_text = '，'.join(rewards[:10])
        if it['rewards_count'] > 10:
            r_text += ' 等{}人'.format(it['rewards_count'])
        if r_text == "":
            r_text = "无"
        r_text = f'<p>🏅 {r_text}</p>'
        # reply
        replys = [
            '<p>{}：{}</p>'.format(c['owner']['name'], c['text'])
            for c in it.get('show_comments', [])       
        ]
        reply_text = '\n'.join(replys)
        
        co = f'<p>{un}</p>\n<p>{tm}</p>\n{text}\n{imgs}\n{r_text}\n{like_text}\n{reply_text}'
        # 标题是除去标签的前N个字
        title = it[tp]['title'] \
            if 'title' in it[tp] \
            else gen_title_from_cont(text)
        if 'article' in it[tp]:
            title = '📄 ' + title
        if it['digested']:
            title = '💎 ' + title
        res.append({
            'title': title, 
            'content': co,
        })
    return res
        
def req_zsxq_retry(url, retry=1000):
    for i in range(retry):
        j = request_retry(
            'GET', url, headers=headers,
        ).json()
       #  print(j)
        if j['succeeded']: break
    return j
        
def gen_title_from_cont(cont):
    return re.sub(r'</?\w+[^>]*>', '', cont) \
            .replace('\n', ' ')[:20]
    
def conv_time_str(tm):
    match = re.search(r'(\d+-\d+-\d+).(\d+:\d+:\d+)', tm)
    return  match.group(1) + ' ' + match.group(2)
           
def next_ed(ed):
    tm = datetime(
        int(ed[0:4]), int(ed[5:7]), int(ed[8:10]),
        int(ed[11:13]), int(ed[14:16]), int(ed[17:19]), int(ed[20:23]) * 1000
    )
    tm -= timedelta(milliseconds=1)
    return f'{tm.year}-{tm.month:02d}-{tm.day:02d}T{tm.hour:02d}:{tm.minute:02d}:{tm.second:02d}.{tm.microsecond//1000:03d}+0800'
           
def download_zsxq(args):
    ori_st = args.start
    ori_ed = args.end
    headers['Cookie'] = args.cookie
    gid = args.id
    st = f'{ori_st[:-4]}-{ori_st[-4:-2]}-{ori_st[-2:]}T00:00:00.000+0800'
    ed = f'{ori_ed[:-4]}-{ori_ed[-4:-2]}-{ori_ed[-2:]}T23:59:59.999+0800'
    st_fmt2 = f'{ori_st[:-4]}-{ori_st[-4:-2]}-{ori_st[-2:]}T00:00:00'
    
    url = f'https://api.zsxq.com/v2/groups/{gid}'
    j = req_zsxq_retry(url)
    name = j['resp_data']['group']['name']
    
    title = f'{name} {ori_st}-{ori_ed}'
    articles = [{
        'title': title, 
        'content': '',
    }]
    imgs = {}
    
    while True:
        print(f'st: {st}, ed: {ed}')
        # print(headers)
        url = f'https://api.zsxq.com/v2/groups/{gid}/topics?scope=all&count=20&end_time={quote_plus(ed)}'
        # print(url)
        j = req_zsxq_retry(url)
        j.setdefault('resp_data', {'topics': []})
        j['resp_data']['topics'] = [
            it for it in j['resp_data']['topics']
            if conv_time_str(it['create_time']) >= st_fmt2
        ]
        if len(j['resp_data']['topics']) == 0:
            break
        print(j['resp_data']['topics'])
        part = get_article(j)        
        # 图片
        for art in part:
            art['content'] = process_img(art['content'], imgs, img_prefix='../Images/')
        articles += part
        ed = next_ed(j['resp_data']['topics'][-1]['create_time'])
    
    gen_epub(articles, imgs)
    
if __name__ == '__main__': main()