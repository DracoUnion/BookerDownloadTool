import re
import sys
import time
import traceback
import copy
from os import path
from pyquery import PyQuery as pq
from EpubCrawler.util import request_retry
from EpubCrawler.img import process_img
from EpubCrawler.config import config as cralwer_config
from datetime import datetime
from GenEpub import gen_epub
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from .util import *

# 滚动到底
def scroll_to_bottom(driver):
    driver.execute_script('''
        document.documentElement.scrollTop -= 50
        document.documentElement.scrollTop = 100000000
    ''')
    
# 判断是否到底
def if_reach_bottom(driver):
    return driver.execute_script('''
        return document.querySelector('.QuestionAnswers-answerButton') != null
    ''')    
    
# 获取最后一个 AID
def get_last_aid(driver):
    return driver.execute_script('''
        var ansLi = document.querySelectorAll('.AnswerItem')
        return (ansLi.length == 0)? '': ansLi[ansLi.length - 1].getAttribute('name')
    ''')   

# 获取 AID 数量
def get_ans_count(driver):
    return driver.execute_script('''
        var ansLi = document.querySelectorAll('.AnswerItem')
        return ansLi.length
    ''')  
    
# 获取回答数量
def get_ans_total(driver):
    return driver.execute_script('''
        var el = document.querySelector('h4.List-headerText')
        if (!el) return 0
        var text = el.innerText.replace(',', '')
        var m = /\d+/.exec(text)
        if (!m) return 0
        return Number.parseInt(m[0])
    ''')  

def get_ques_count(driver):
    return driver.execute_script('''
        var els = document.querySelectorAll('h2.ContentItem-title')
        return els.length
    ''')  

# 获取整个页面 HTML
def get_html(driver):
    return driver.execute_script('''
        return document.documentElement.outerHTML
    ''')    

def close_login_dialog(driver):
    driver.execute_script('''
        var cls_btn = document.querySelector('.Modal-closeButton')
        if (cls_btn) cls_btn.click()
    ''')
    
def get_qids(html):
    rt = pq(html)
    el_links = rt('h2.ContentItem-title meta[itemprop="url"]')
    qids = [
        pq(el).attr('content').split('/')[-1]
        for el in el_links
    ]
    return qids

def get_sub_tids(html):
    rt = pq(html)
    el_topics = rt('.TopicRelativeBoard-item').eq(-1).find('a')
    tids = [
        pq(el).attr('href').split('/')[-1]
        for el in el_topics
    ]
    return tids

# 获取文章列表
def get_articles(html, qid):
    rt = pq(html)
    rt.remove('noscript, .GifPlayer-icon, a svg')
    title = '知乎问答：' + fname_escape(rt('h1.QuestionHeader-title').eq(0).text())
    co = f'''
        <blockquote>来源：<a href='https://www.zhihu.com/question/{qid}'>https://www.zhihu.com/question/{qid}</a></blockquote>
    '''
    articles = [{'title': title, 'content': co}]
    el_ansLi = rt('.AnswerItem')
    for i in range(len(el_ansLi)):
        el = el_ansLi.eq(i)
        el_au = el.find('.UserLink-link')
        au_name = (el_au.text() or '匿名用户').strip()
        au_url = el_au.attr('href') or ''
        el_time = el.find('.ContentItem-time>a')
        co_url = el_time.attr('href')
        vote = el.find('.VoteButton--up').attr('aria-label').strip()[3:]
        upd_time = el_time.text().strip()[4:]
        co = el.find('.RichText').html()
        co = f'''
            <blockquote>
                <p>作者：<a href='{au_url}'>{au_name}</a></p>
                <p>赞同数：{vote}</p>
                <p>编辑于：<a href='{co_url}'>{upd_time}</a></p>
            </blockquote>
            {co}
        '''
        articles.append({'title': au_name, 'content': co})
    return articles

def zhihu_topic_sele(args):
    tid = args.tid
    # 检查是否存在
    url = f'https://www.zhihu.com/topic/{tid}'
    html = request_retry('GET', url).text
    rt = pq(html)
    if '你似乎来到了没有知识存在的荒原' in rt('title').text():
        print(f'话题 [tid={tid}] 不存在')
        return
    title = rt('.TopicMetaCard-title').text()
    driver = create_driver()
    driver.get(url)
    close_login_dialog(driver)
    last_count = 0
    cntr = 0
    while True:
        try:
            scroll_to_bottom(driver)
            time.sleep(0.5)
            count = get_ques_count(driver)
            print(f'count: {count}')
            if count == last_count:
                cntr += 1
                if cntr == 10: break
            else:
                cntr = 0
            last_count = count
        except:
            traceback.print_exc()
    html = get_html(driver)
    qids = get_qids(html)
    driver.close()
    fname = f'zhihu_ques_{tid}_{title}.txt'
    open(fname, 'w').write('\n'.join(qids) + '\n')

def zhihu_ques_sele(args):
    cralwer_config['optiMode'] = 'thres'
    cralwer_config['imgSrc'] = ['data-original', 'src']
    qid = args.qid
    
    # 检查是否存在
    url = f'https://www.zhihu.com/question/{qid}'
    html = request_retry('GET', url).text
    rt = pq(html)
    if '你似乎来到了没有知识存在的荒原' in rt('title').text():
        print(f'问题 [qid={qid}] 不存在')
        return
    if len(rt('h4.List-headerText')) == 0:
        print(f'问题 [qid={qid}] 无回答')
        return
    fname = '知乎问答：' + fname_escape(rt('h1.QuestionHeader-title').eq(0).text()) + '.epub'
    if path.isfile(fname):
        print('问题 [qid={qid}] 已抓取')
        return
    driver = create_driver()
    driver.get(url)
    # 关闭登录对话框
    close_login_dialog(driver)
    total = get_ans_total(driver)
    if total == 0:
        print(f'问题 [qid={qid}] 无回答')
        driver.close()
        return
    # 如果没有到底就一直滚动
    while not if_reach_bottom(driver):
        try:
            cnt = get_ans_count(driver)
            print(f'reach bottom: false, count: {cnt}/{total}')
            scroll_to_bottom(driver)
            # time.sleep(1)
        except:
            traceback.print_exc()
    
    html = get_html(driver)
    # time.sleep(3600)
    driver.close()
    articles = get_articles(html, qid)
    imgs = {}
    
    for art in articles:
        art['content'] = process_img(
            art['content'], imgs, 
            img_prefix='../Images/',
            page_url=url,
        )
        
    gen_epub(articles, imgs)

def zhihu_all_topics_sele(args):
    root_tid = args.root
    res_fname = f'zhihu_all_topics_{root_tid}.txt'
    rec_fname = f'zhihu_all_topics_{root_tid}_rec.txt'

    ofile = open(res_fname, 'a', encoding='utf8')
    if path.isfile(rec_fname):
        rec = open(rec_fname, encoding='utf8').read().split('\n')
        rec = [l for l in rec if l]
        if rec and rec[-1] == '-1': rec = rec[:-1]
        vis = set(rec)
        pop_count = rec.count('-1')
        rec = [tid for tid in rec if tid != '-1'][pop_count:]
        q = deque(rec)
    else:
        vis = set()
        q = deque([root_tid])
    rec_file = open(rec_fname, 'a', encoding='utf8')
    driver = create_driver()
    while q:
        tid = q.popleft()
        print(f'tid: {tid}')
        rec_file.write('-1\n')
        ofile.write(tid + '\n')
        url = f'https://www.zhihu.com/topic/{tid}'
        driver.get(url)
        subs = get_sub_tids(get_html(driver))
        for s in subs:
            if s not in vis:
                vis.add(s)
                q.append(s)
                rec_file.write(s + '\n')
    ofile.close()
    rec_file.close()

    
