import os
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
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from .util import *
from .ext_cookie import extract_cookies

# 滚动到底
def scroll_to_bottom(page):
    page.evaluate('''
        () => {
            document.documentElement.scrollTop -= 50
            document.documentElement.scrollTop = 100000000
        }
    ''')

# 获取回答数量
def get_ans_total(page):
    return page.evaluate('''
        () => {
            var el = document.querySelector('h4.List-headerText')
            if (!el) return 0
            var text = el.innerText.replace(',', '')
            var m = /\\d+/.exec(text)
            if (!m) return 0
            return Number.parseInt(m[0])
        }
    ''')  

def get_ques_count(page):
    return page.evaluate('''
        () => {
            var els = document.querySelectorAll('h2.ContentItem-title')
            return els.length
        }
    ''')  

# 获取整个页面 HTML
def get_html(page):
    return page.content()    

def close_login_dialog(page):
    page.evaluate('''
        () => {
            var cls_btn = document.querySelector('.Modal-closeButton')
            if (cls_btn) cls_btn.click()
        }
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

# 获取文章列表（由 zh_articles 替代，见 API 抓取逻辑）
def zhihu_topic_batch_sele(args):
    fname = args.fname
    tids = open(fname, encoding='utf8').read().split('\n')
    tids = [t for t in tids if t]
    for t in tids:
        args.tid = t
        try: zhihu_topic_sele(args)
        except KeyboardInterrupt:
            raise
        except: traceback.print_exc()

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
    with camou_create_driver(args.no_headless) as (browser, context, page):
        set_driver_cookie(context, args.cookie, 'zhihu.com')
        page.goto(url, wait_until='domcontentloaded', timeout=30_000)
        close_login_dialog(page)
        last_count = 0
        cntr = 0
        while True:
            try:
                scroll_to_bottom(page)
                page.wait_for_timeout(500)
                count = get_ques_count(page)
                print(f'count: {count}')
                if count == last_count:
                    cntr += 1
                    if cntr == 10: break
                else:
                    cntr = 0
                last_count = count
            except KeyboardInterrupt:
                raise
            except:
                traceback.print_exc()
        html = get_html(page)
    qids = get_qids(html)
    fname = f'zhihu_ques_{tid}_{fname_escape(title)}.txt'
    open(fname, 'w').write('\n'.join(qids) + '\n')

def zhihu_ques_batch_sele(args):
    fname = args.fname
    qids = open(fname, encoding='utf8').read().split('\n')
    qids = [q for q in qids if q]
    for q in qids:
        args.qid = q
        try: zhihu_ques_sele(args)
        except KeyboardInterrupt:
            raise
        except: traceback.print_exc()

# 知乎回答 API 基础 URL 与请求头
ZH_ANS_API = 'https://www.zhihu.com/api/v4/questions/{qid}/answers'
ZH_INCLUDE = 'data[*].content,data[*].voteup_count,data[*].comment_count,data[*].created_time,data[*].updated_time,data[*].question'
ZH_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'


def get_zh_cookie(args):
    """获取知乎 Cookie：优先 -c 参数，其次从 Firefox/Chrome 浏览器提取。"""
    if args.cookie:
        return args.cookie
    # 从浏览器提取（Chrome 解密失败时降级到 Firefox）
    for br in ['firefox', 'chrome']:
        try:
            ck = cookie_dict_to_str(extract_cookies(br, 'zhihu.com'))
            if ck:
                print(f'从 {br} 提取到知乎 Cookie')
                return ck
        except Exception as e:
            print(f'{br} Cookie 提取失败: {e!r}')
    return ''


def zh_ans_headers(cookie, qid):
    return {
        'User-Agent': ZH_UA,
        'Referer': f'https://www.zhihu.com/question/{qid}',
        'Accept': 'application/json, text/plain, */*',
        'Cookie': cookie,
    }


def zh_fetch_answers(qid, cookie):
    """分页抓取某问题下的全部回答，返回 (答案列表, 问题标题)。"""
    hdrs = zh_ans_headers(cookie, qid)
    answers = []
    title = None
    offset = 0
    limit = 20
    while True:
        url = f'{ZH_ANS_API.format(qid=qid)}?include={ZH_INCLUDE}&limit={limit}&offset={offset}'
        r = request_retry('GET', url, headers=hdrs, check_status=False, retry=10, timeout=15)
        if r.status_code == 403:
            # 未登录 / 风控：尝试用问题页判断是否存在
            raise RuntimeError(f'API 返回 403（可能需要登录 Cookie），qid={qid}')
        if r.status_code == 404:
            raise FileNotFoundError(f'问题 [qid={qid}] 不存在')
        r.raise_for_status()
        d = r.json()
        if title is None and d['data']:
            title = d['data'][0]['question']['title']
        answers.extend(d['data'])
        paging = d.get('paging', {})
        if paging.get('is_end'):
            break
        offset = paging.get('next', '').rsplit('offset=', 1)[-1]
        try:
            offset = int(offset)
        except Exception:
            break
    return answers, title


def zh_answer_content(ans, cookie):
    """回答正文；content_need_truncated 时单独拉取完整回答。"""
    content = ans.get('content', '')
    if ans.get('content_need_truncated'):
        aid = ans['id']
        url = f'https://www.zhihu.com/api/v4/answers/{aid}?include=content'
        r = request_retry('GET', url, headers=zh_ans_headers(cookie, ans.get('question', {}).get('id', '')), retry=10, timeout=15)
        if r.status_code == 200:
            content = r.json().get('content', content)
    return content


def zh_articles(answers, cookie, qid, title):
    """把 API 回答列表转为 get_articles 同款文章结构。"""
    articles = [{
        'title': '知乎问答：' + fname_escape(title),
        'content': f'''
            <blockquote>来源：<a href='https://www.zhihu.com/question/{qid}'>https://www.zhihu.com/question/{qid}</a></blockquote>
        ''',
    }]
    for ans in answers:
        au = ans.get('author', {}) or {}
        au_name = au.get('name') or '匿名用户'
        au_url = 'https://www.zhihu.com/people/' + (au.get('url_token') or '')
        ans_url = f'https://www.zhihu.com/question/{ans.get("question", {}).get("id", "")}/answer/{ans["id"]}'
        vote = ans.get('voteup_count', 0)
        upd = datetime.fromtimestamp(ans.get('updated_time', 0)).strftime('%Y-%m-%d %H:%M:%S')
        content = zh_answer_content(ans, cookie)
        if not content:
            continue
        co = f'''
            <blockquote>
                <p>作者：<a href='{au_url}'>{au_name}</a></p>
                <p>赞同数：{vote}</p>
                <p>编辑于：<a href='{ans_url}'>{upd}</a></p>
            </blockquote>
            {content}
        '''
        articles.append({'title': au_name, 'content': co})
    return articles


def zhihu_ques_sele(args):
    cralwer_config['optiMode'] = 'thres'
    cralwer_config['imgSrc'] = ['data-original', 'src']
    qid = args.qid
    cookie = get_zh_cookie(args)

    try:
        answers, title = zh_fetch_answers(qid, cookie)
    except FileNotFoundError:
        print(f'问题 [qid={qid}] 不存在')
        return
    except RuntimeError as e:
        print(e)
        return
    if not answers:
        print(f'问题 [qid={qid}] 无回答')
        return
    fname = '知乎问答：' + fname_escape(title) + '.epub'
    if path.isfile(fname):
        print(f'问题 [qid={qid}] 已抓取')
        return

    articles = zh_articles(answers, cookie, qid, title)
    imgs = {}
    url = f'https://www.zhihu.com/question/{qid}'
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
    rec_file = open(rec_fname, 'a+', encoding='utf8')
    if rec_file.tell() != 0:
        rec_file.seek(0, 0)
        rec = rec_file.read().split('\n')
        rec = [l for l in rec if l]
        # if rec and rec[-1] == '-1': 
        #     rec = rec[:-1]
        #     rec_file.seek(1, -3)
        vis = set(rec)
        pop_count = rec.count('-1')
        rec = [tid for tid in rec if tid != '-1'][pop_count:]
        q = deque(rec)
    else:
        vis = set()
        q = deque([root_tid])
        rec_file.write(root_tid + '\n')
    with camou_create_driver(args.no_headless) as (browser, context, page):
        set_driver_cookie(context, args.cookie, 'zhihu.com')
        page.goto(f'https://www.zhihu.com/topic/{root_tid}', wait_until='domcontentloaded', timeout=30_000)
        while q:
            tid = q.popleft()
            print(f'tid: {tid}')
            ofile.write(tid + '\n')
            url = f'https://www.zhihu.com/topic/{tid}'
            page.goto(url, wait_until='domcontentloaded', timeout=30_000)
            subs = get_sub_tids(get_html(page))
            rec_file.write('-1\n')
            for s in subs:
                if s not in vis:
                    vis.add(s)
                    q.append(s)
                    rec_file.write(s + '\n')
            page.wait_for_timeout(500)
    ofile.close()
    rec_file.close()

    


def reg_subparser(subparsers):
    wk8_cookie = os.environ.get('WK8_COOKIE', '')

    zhihu_ques_parser = subparsers.add_parser("zhihu-ques", help="通过官方 API 爬取知乎问题下的回答")
    zhihu_ques_parser.add_argument("qid", help="问题 id")
    zhihu_ques_parser.add_argument("-c", "--cookie", default='', help="知乎 Cookie（默认从 Firefox/Chrome 浏览器提取）")
    zhihu_ques_parser.set_defaults(func=zhihu_ques_sele)

    zhihu_ques_batch_parser = subparsers.add_parser("zhihu-ques-batch", help="通过官方 API 爬取知乎问题下的回答")
    zhihu_ques_batch_parser.add_argument("fname", help="qid 列表文件名")
    zhihu_ques_batch_parser.add_argument("-c", "--cookie", default='', help="知乎 Cookie（默认从 Firefox/Chrome 浏览器提取）")
    zhihu_ques_batch_parser.set_defaults(func=zhihu_ques_batch_sele)

    zhihu_topic_parser = subparsers.add_parser("zhihu-topic", help="通过 **Camoufox** 爬取知乎话题下的问题")
    zhihu_topic_parser.add_argument("tid", help="话题 tid")
    zhihu_topic_parser.add_argument("-c", "--cookie", default=wk8_cookie, help="wenku8 论坛 Cookie")
    zhihu_topic_parser.set_defaults(func=zhihu_topic_sele)

    zhihu_topic_batch_parser = subparsers.add_parser("zhihu-topic-batch", help="通过 **Camoufox** 爬取知乎话题下的问题")
    zhihu_topic_batch_parser.add_argument("fname", help="tid 列表文件名")
    zhihu_topic_batch_parser.add_argument("-c", "--cookie", default=wk8_cookie, help="wenku8 论坛 Cookie")
    zhihu_topic_batch_parser.set_defaults(func=zhihu_topic_batch_sele)

    zhihu_topics_parser = subparsers.add_parser("zhihu-topics", help="通过 **Camoufox** 爬取知乎子话题")
    zhihu_topics_parser.add_argument("root", help="根话题 tid")
    zhihu_topics_parser.add_argument("-c", "--cookie", default='', help="知乎 Cookie")
    zhihu_topics_parser.set_defaults(func=zhihu_all_topics_sele)
