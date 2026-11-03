#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
weibo.py — 抓取微博指定关键词的博文并保存到本地。

API 参考 weibo-cli:
    https://github.com/jackwener/weibo-cli/blob/main/weibo_cli/client.py

使用微博移动端搜索接口 ``m.weibo.cn/api/container/getIndex``，按页抓取关键词
搜索结果，去重后保存。输出格式与 ``twitter`` 子命令一致：一个 CSV 文件
（未安装 pandas 时退回 JSON），文件名为 ``weibos_{关键词}_{since}_{until}.csv``。

微博移动端搜索允许匿名访问，但登录后结果更完整、更稳定。可通过 ``-c/--cookie``
显式传入 Cookie，或从本机浏览器自动提取（需要事先登录 weibo.com）。

用法示例
--------
    # 抓取关键词为「人工智能」的所有博文
    bdt weibo -k 人工智能

    # 多个关键词、指定输出目录、限制条数
    bdt weibo -k 人工智能 大模型 -o ./data --limit 1000

    # 使用内联 Cookie（含 SUB/SUBP）提高抓取成功率
    bdt weibo -k 特斯拉 -c "SUB=xxx; SUBP=yyy"

    # 只保留指定日期区间（YYYY-MM-DD，按博文发布时间过滤）
    bdt weibo -k 新能源 --since 2024-01-01 --until 2024-06-30
"""

import argparse
import html
import json
import random
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from .util import cookie_str_to_dict, posts_to_md, md_body
from .ext_cookie import extract_cookies_multi_browsers

# ---------------------------------------------------------------------------
# 移动端搜索接口常量（与 weibo-cli constants.py 保持一致）
# ---------------------------------------------------------------------------
MOBILE_BASE_URL = "https://m.weibo.cn"
MOBILE_SEARCH_URL = "/api/container/getIndex"
MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                  "Mobile/15E148 Safari/604.1",
    "Accept": "application/json, text/plain, */*",
    "Referer": f"{MOBILE_BASE_URL}/",
    "X-Requested-With": "XMLHttpRequest",
}

_TAG_RE = re.compile(r"<[^>]+>")


# ---------------------------------------------------------------------------
# Cookie / 登录态解析
# ---------------------------------------------------------------------------
def _validate_date(value, name):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        sys.exit(f"[错误] {name} 日期格式不正确: {value!r}，应为 YYYY-MM-DD")


def _load_cookies(args):
    """解析微博 Cookie。

    优先级: 内联 ``--cookie`` > 本机浏览器（weibo.com / weibo.cn）。
    未找到 Cookie 时返回空字典，以匿名方式继续抓取。
    """
    if args.cookie:
        cookies = cookie_str_to_dict(args.cookie)
        if not cookies:
            sys.exit("[错误] 无法解析 --cookie，请提供形如 'SUB=xxx; SUBP=yyy' 的字符串")
        if not ({"SUB", "SUBP"} & set(cookies)):
            print("[警告] Cookie 中不包含 SUB/SUBP，登录态可能无效")
        return cookies

    cookies = {}
    for domain in ("weibo.com", "weibo.cn"):
        try:
            cookies.update(extract_cookies_multi_browsers(domain) or {})
        except Exception:
            pass
    if not cookies:
        print("[警告] 未在浏览器中找到微博登录 Cookie，将匿名抓取（结果可能不完整）")
        return {}
    print(f"[INFO] 已从本机浏览器提取登录 Cookie: {sorted(cookies)}")
    return cookies


# ---------------------------------------------------------------------------
# 解析工具
# ---------------------------------------------------------------------------
def _clean_text(mblog):
    """把微博富文本转成纯文本（去标签、反转义）。"""
    raw = mblog.get("text_raw") or mblog.get("text") or ""
    return html.unescape(_TAG_RE.sub("", raw)).strip()


def _mblog_key(mblog):
    """返回博文的稳定去重键。"""
    for key in ("mblogid", "bid", "idstr", "id", "mid"):
        value = mblog.get(key)
        if value:
            return str(value)
    return None


def _extract_mblogs(cards):
    """从搜索结果 cards 中递归提取博文（card_type == 9）。"""
    out = []

    def walk(card):
        if not isinstance(card, dict):
            return
        if card.get("card_type") == 9 and card.get("mblog"):
            out.append(card["mblog"])
        for sub in card.get("card_group") or []:
            walk(sub)

    for card in cards or []:
        walk(card)
    return out


def _mblog_date(mblog):
    """尽力解析博文发布时间，失败返回 None。"""
    for key in ("created_timestamp", "timestamp", "created_at_timestamp"):
        value = mblog.get(key)
        if isinstance(value, (int, float)) and value > 0:
            try:
                return datetime.fromtimestamp(value)
            except (ValueError, OSError):
                pass

    raw = (mblog.get("created_at") or "").strip()
    if not raw:
        return None

    # 微博常见格式: "Tue Nov 03 08:00:54 +0800 2026"
    for fmt in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass

    now = datetime.now()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:\s+(\d{1,2}):(\d{2}))?$", raw)
    if m:
        y, mo, d, hh, mm = m.groups()
        try:
            return datetime(int(y), int(mo), int(d), int(hh or 0), int(mm or 0))
        except ValueError:
            return None

    m = re.match(r"^(\d{2})-(\d{2})(?:\s+(\d{1,2}):(\d{2}))?$", raw)
    if m:
        mo, d, hh, mm = m.groups()
        try:
            dt = datetime(now.year, int(mo), int(d), int(hh or 0), int(mm or 0))
        except ValueError:
            return None
        if dt > now + timedelta(days=1):
            dt = dt.replace(year=now.year - 1)
        return dt

    if raw in ("刚刚", "今天") or "分钟前" in raw or "小时前" in raw or raw.startswith("今天"):
        return now
    if raw.startswith("昨天"):
        return now - timedelta(days=1)
    return None


def _mblog_md_section(mblog, idx):
    """把一条博文渲染为 Markdown 段落（以 "## " 二级标题开头）。"""
    user = mblog.get("user") or {}
    screen = user.get("screen_name") or "未知用户"
    lines = [f"## {idx}. @{screen}", ""]

    meta = []
    ts = _mblog_date(mblog)
    meta.append("发布：" + (ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "未知"))
    mid = mblog.get("mblogid") or mblog.get("bid")
    if mid:
        meta.append(f"链接：https://m.weibo.cn/detail/{mid}")

    counts = []
    for label, key in (("转发", "reposts_count"), ("评论", "comments_count"),
                       ("点赞", "attitudes_count")):
        value = mblog.get(key)
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
            counts.append(f"{label}：{value}")
    if counts:
        meta.append(" ｜ ".join(counts))
    lines.extend(f"- {m}" for m in meta)
    lines.append("")

    text = _clean_text(mblog)
    if text:
        lines.append(md_body(text))
        lines.append("")

    if isinstance(mblog.get("retweeted_status"), dict):
        rt = mblog["retweeted_status"]
        rt_user = ((rt.get("user") or {}).get("screen_name") or "未知用户")
        rt_text = md_body(_clean_text(rt))
        quote = f"> 转发自 @{rt_user}"
        if rt_text:
            quote += "：\n> " + "\n> ".join(rt_text.splitlines())
        lines.append(quote)
        lines.append("")
        if not mblog.get("pics"):
            mblog = rt

    for pic in mblog.get("pics") or []:
        if not isinstance(pic, dict):
            continue
        large = pic.get("large")
        if isinstance(large, dict):
            url = large.get("url") or pic.get("url")
        else:
            url = large or pic.get("url")
        if url:
            lines.append(f"![图]({url})")
            lines.append("")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# 网络请求
# ---------------------------------------------------------------------------
def _sleep_jitter(base_delay):
    """模拟人工操作的高斯抖动延迟。"""
    if base_delay <= 0:
        return
    jitter = max(0.0, random.gauss(0.3, 0.15))
    if random.random() < 0.05:
        jitter += random.uniform(2.0, 5.0)
    time.sleep(base_delay + jitter)


def _search_page(client, keyword, page, retries=3):
    """请求指定关键词的一页搜索结果。"""
    params = {
        "containerid": f"100103type=1&q={keyword}",
        "page_type": "searchall",
        "page": str(page),
    }
    last_exc = None
    for attempt in range(max(1, retries)):
        try:
            resp = client.get(MOBILE_SEARCH_URL, params=params)
            if resp.status_code in (429, 500, 502, 503, 504):
                wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"[警告] HTTP {resp.status_code}，{wait:.1f}s 后重试 "
                      f"({attempt + 1}/{retries})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            text = resp.text
            if text.startswith("<"):
                raise ValueError("接口返回 HTML 而非 JSON，可能被风控或需要登录")
            return resp.json()
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_exc = exc
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
    if last_exc:
        raise RuntimeError(f"请求失败（重试 {retries} 次）: {last_exc}")
    raise RuntimeError(f"请求失败（重试 {retries} 次）")


def _crawl_keyword(client, keyword, args, limit_remaining=None):
    """翻页抓取单个关键词的全部博文。"""
    collected = []
    seen = set()
    page = 1
    empty_pages = 0
    max_pages = args.max_pages or 200
    max_empty_pages = args.max_empty_pages or 2

    while page <= max_pages:
        if page > 1:
            _sleep_jitter(args.delay)

        try:
            data = _search_page(client, keyword, page, retries=args.retries)
        except Exception as exc:
            print(f"[警告] 「{keyword}」第 {page} 页请求失败，停止翻页: {exc}")
            break

        if data.get("ok") != 1:
            msg = data.get("msg") or data.get("message") or "未知错误"
            print(f"[警告] 「{keyword}」搜索返回异常: ok={data.get('ok')} msg={msg}")
            break

        payload = data.get("data") or {}
        cards = payload.get("cards") or []
        mblogs = _extract_mblogs(cards)

        new_count = 0
        for mblog in mblogs:
            key = _mblog_key(mblog)
            if key is None or key in seen:
                continue
            seen.add(key)
            collected.append(mblog)
            new_count += 1
            if limit_remaining is not None and len(collected) >= limit_remaining:
                print(f"[INFO] 「{keyword}」达到上限 {limit_remaining} 条，停止翻页")
                return collected

        print(f"[INFO] 「{keyword}」第 {page} 页: 新增 {new_count} 条，"
              f"累计 {len(collected)} 条")

        empty_pages = empty_pages + 1 if (not cards or new_count == 0) else 0
        if empty_pages >= max_empty_pages:
            break
        if payload.get("page_has_next") is False:
            break

        page += 1

    return collected


# ---------------------------------------------------------------------------
# 抓取主流程
# ---------------------------------------------------------------------------
def weibo_fetch(args):
    since_date = _validate_date(args.since, "since") if args.since else None
    until_date = _validate_date(args.until, "until") if args.until else None

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("[INFO] 关键词    :", args.keywords)
    print("[INFO] 时间范围  :", args.since or "不限", "~", args.until or "不限")
    print("[INFO] 输出目录  :", outdir)
    print("[INFO] 代理      :", args.proxy or "无")
    if args.limit:
        print("[INFO] 上限条数  :", args.limit)
    print("=" * 60)

    cookies = _load_cookies(args)

    client_kwargs = dict(
        base_url=MOBILE_BASE_URL,
        headers=dict(MOBILE_HEADERS),
        cookies=cookies,
        follow_redirects=True,
        timeout=httpx.Timeout(args.timeout),
    )
    try:
        if args.proxy:
            try:
                client = httpx.Client(proxy=args.proxy, **client_kwargs)
            except TypeError:  # 兼容旧版 httpx
                client = httpx.Client(proxies=args.proxy, **client_kwargs)
        else:
            client = httpx.Client(**client_kwargs)
    except Exception as exc:
        sys.exit(f"[错误] 初始化 HTTP 客户端失败: {exc}")

    all_mblogs = []
    seen = set()
    try:
        with client:
            for keyword in args.keywords:
                print(f"\n[INFO] 开始抓取关键词: {keyword}")
                remaining = (args.limit - len(all_mblogs)) if args.limit else None
                if remaining is not None and remaining <= 0:
                    break
                collected = _crawl_keyword(client, keyword, args, remaining)
                for mblog in collected:
                    key = _mblog_key(mblog)
                    if key is None or key in seen:
                        continue
                    seen.add(key)
                    all_mblogs.append(mblog)
                print(f"[INFO] 「{keyword}」完成，累计去重后 {len(all_mblogs)} 条")
                if args.limit and len(all_mblogs) >= args.limit:
                    break
    except KeyboardInterrupt:
        print("\n[WARN] 已中断，保存已抓取的数据……")
    except Exception as exc:
        sys.exit(f"[错误] 抓取失败: {exc}")

    if not all_mblogs:
        print("[警告] 未抓取到任何博文。可能原因: 关键词过冷、需要登录、被风控限流。")
        return

    # 日期过滤（仅在提供 --since/--until 时生效；无法解析时间的博文保留）
    if since_date or until_date:
        filtered = []
        for mblog in all_mblogs:
            dt = _mblog_date(mblog)
            if dt is not None:
                if since_date and dt.date() < since_date:
                    continue
                if until_date and dt.date() > until_date:
                    continue
            filtered.append(mblog)
        if len(filtered) != len(all_mblogs):
            print(f"[INFO] 日期过滤: {len(all_mblogs)} -> {len(filtered)} 条")
        all_mblogs = filtered
        if not all_mblogs:
            print("[警告] 日期过滤后无剩余博文。")
            return

    # 落盘（格式与 twitter 子命令一致）
    key_part = "_".join(args.keywords)
    safe_key = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in key_part)
    since_part = args.since or "all"
    until_part = args.until or "all"
    base_name = f"weibos_{safe_key}_{since_part}_{until_part}"

    try:
        import pandas as pd
        df = pd.DataFrame(all_mblogs)
        filename = base_name + ".csv"
        df.to_csv(outdir / filename, index=False, encoding="utf-8-sig")
        print(f"[OK] 共抓取 {len(all_mblogs)} 条博文，已保存: {outdir / filename}")
    except ImportError:
        filename = base_name + ".json"
        (outdir / filename).write_text(
            json.dumps(all_mblogs, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[OK] 共抓取 {len(all_mblogs)} 条博文（未装 pandas，改用 json）: "
              f"{outdir / filename}")

    # 额外输出一份 Markdown，便于人读
    sections = [_mblog_md_section(m, i + 1) for i, m in enumerate(all_mblogs)]
    meta_lines = [
        f"关键词：{'、'.join(args.keywords)}",
        f"时间范围：{args.since or '不限'} ~ {args.until or '不限'}",
        f"条数：{len(all_mblogs)}",
    ]
    md_name = base_name + ".md"
    (outdir / md_name).write_text(
        posts_to_md(f"微博博文：{args.keywords[0]}", meta_lines, sections),
        encoding="utf-8",
    )
    print(f"[OK] 已同时保存 Markdown: {outdir / md_name}")

    # 预览前几条
    print("\n[预览] 前 5 条：")
    for mblog in all_mblogs[:5]:
        user = (mblog.get("user") or {}).get("screen_name", "?")
        ts = mblog.get("created_at", "?")
        text = _clean_text(mblog).replace("\n", " ")[:80]
        print(f"  [{ts}] @{user}: {text}")


def reg_subparser(subparsers):
    p = subparsers.add_parser("weibo", help="抓取微博关键词博文")
    p.add_argument("-k", "--keywords", nargs="+", required=True, help="关键词，可多个")
    p.add_argument("-c", "--cookie", default=None,
                   help="内联 Cookie 字符串，如 'SUB=xxx; SUBP=yyy'")
    p.add_argument("--since", default=None, help="起始日期 YYYY-MM-DD（按发布时间过滤），默认不限")
    p.add_argument("--until", default=None, help="结束日期 YYYY-MM-DD（按发布时间过滤），默认不限")
    p.add_argument("--limit", type=int, default=None, help="最多抓取条数")
    p.add_argument("--max-pages", type=int, default=200, help="每个关键词最多翻页数，默认 200")
    p.add_argument("--max-empty-pages", type=int, default=2, help="连续空页停止阈值，默认 2")
    p.add_argument("--delay", type=float, default=1.0, help="请求间隔秒数，默认 1.0")
    p.add_argument("--retries", type=int, default=3, help="单页请求重试次数，默认 3")
    p.add_argument("--timeout", type=float, default=30.0, help="请求超时秒数，默认 30")
    p.add_argument("-o", "--outdir", default="./weibo", help="结果保存目录，默认 ./weibo")
    p.add_argument("--proxy", default=None, help="代理地址")
    p.set_defaults(func=weibo_fetch)
