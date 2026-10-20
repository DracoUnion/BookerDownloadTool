#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
twitter.py — 使用 Scweet v5 从 Twitter/X 抓取指定关键词的推文并保存到本地。

移植自 D:\\src\\doctool\\twi_fetch.py，作为 BookerDownloadTool 的 `twitter` 子命令。

依赖:
    pip install scweet

Scweet v5 是 API-only 的重写版本（不再是早期的 Selenium/scrape() 旧 API）。
X 的搜索接口基本强制登录/Cookie，因此请先配置登录授权（见下方"用法"）。

用法示例
--------
    # 用 cookies.json 里的账号登录抓取关键词 openai
    bdt twitter -k openai -c cookies.json

    # 用 auth_token 登录（ct0 会自动向 x.com 引导获取）
    bdt twitter -k gpt -t YOUR_AUTH_TOKEN

    # 指定时间范围、语言、多个关键词、保存到指定目录
    bdt twitter -k openai gpt -l en --since 2024-06-01 --until 2024-06-30 -o ./data

    # 数值下限过滤 + 只抓前 500 条
    bdt twitter -k bitcoin --minlikes 100 --minretweets 20 --limit 500

权限说明
--------
Scweet 使用与浏览器不同的 API 客户端，偶发风控/限流。若 init 时报
"failed to authenticate" 或 "420 too many requests"，通常是该账号被风控或
ct0 已过期，请换账号或重新导出最新 cookie。
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------------------------
# 已登录浏览器 Cookie 导出小工具（可选）
# ---------------------------------------------------------------------------
# 自动提取时尝试的浏览器优先级（火狐 → Chrome → Edge）
BROWSER_PRIORITY = ["firefox", "chrome", "edge"]


def _browser_jar(browser: str):
    """获取 browser_cookie3 的 cookie jar；返回 None 表示不支持/导入失败。"""
    try:
        import browser_cookie3 as bc
    except ImportError:
        sys.exit("[错误] 需要 browser_cookie3: pip install browser_cookie3")

    getter = {
        "firefox": bc.firefox, "chrome": bc.chrome, "edge": bc.edge,
        "chromium": bc.chromium, "brave": bc.brave, "opera_gx": bc.opera_gx,
    }.get(browser)
    if getter is None:
        sys.exit(f"[错误] 暂不支持的浏览器: {browser!r}"
                 "（支持 firefox/chrome/edge/chromium/brave/opera_gx）")
    return getter()


def _get_browser_cookies(browser: str) -> dict:
    """从本机浏览器提取 x.com / twitter.com 的指定 cookie（映射对象格式）。

    最少需要 auth_token；ct0/twid/guest_id 一并带上更稳。
    """
    jar = _browser_jar(browser)
    wanted = {"auth_token", "ct0", "twid", "guest_id"}
    cookies = {}
    for c in jar:
        if c.domain and ("x.com" in c.domain or "twitter.com" in c.domain) and c.name in wanted:
            cookies[c.name] = c.value
    return cookies


def extract_cookies(browser: str, outfile: str) -> None:
    """把浏览器中已登录 x.com 的 cookie 导出到 outfile (映射对象格式)。

    仅支持 Chromium 系浏览器（Chrome/Edge/Brave 等）。
    要求: pip install browser_cookie3
    """
    cookies = _get_browser_cookies(browser)

    if "auth_token" not in cookies:
        sys.exit("[错误] 未在浏览器中找到 x.com 的 auth_token。请先在该浏览器登录 x.com 后再试。")

    Path(outfile).write_text(
        json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[OK] 已导出 cookie 到 {outfile}: {sorted(cookies)}")


# ---------------------------------------------------------------------------
# Cookie / 登录态解析
# ---------------------------------------------------------------------------
def _validate_date(value, name):
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        sys.exit(f"[错误] {name} 日期格式不正确: {value!r}，应为 YYYY-MM-DD")


def _load_cookies(args):
    """根据参数解析出传给 Scweet 的 cookies 承载方式（返回 kwargs 片段）。

    优先级: cookies_file > auth_token > inline_cookies > 浏览器 cookie
    浏览器 cookie 默认按 firefox → chrome → edge 顺序尝试，成功即止；
    显式指定 --browser 时只尝试该浏览器。
    """
    sources = [bool(args.cookies_file), bool(args.auth_token), bool(args.inline_cookies)]
    if sum(sources) > 1:
        sys.exit("[错误] -c / -t / --inline-cookies 三者最多选一个。")

    if args.cookies_file:
        p = Path(args.cookies_file)
        if not p.is_file():
            sys.exit(f"[错误] cookies 文件不存在: {p}")
        return {"cookies_file": str(p)}

    if args.auth_token:
        return {"auth_token": args.auth_token}

    if args.inline_cookies:
        raw = args.inline_cookies.strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return {"cookies": payload}

    # 均未显式提供：从本机浏览器（browser_cookie3）提取 x.com 登录态
    browsers = [args.browser] if args.browser else BROWSER_PRIORITY
    for browser in browsers:
        try:
            browser_cookies = _get_browser_cookies(browser)
        except SystemExit:
            raise
        except Exception as exc:
            print(f"[警告] {browser} 浏览器 Cookie 提取失败: {exc}")
            continue

        if "auth_token" not in browser_cookies:
            print(f"[警告] {browser} 浏览器中未找到 x.com 的 auth_token，尝试下一个")
            continue

        print(f"[INFO] 已从本机 {browser} 浏览器提取登录 Cookie: "
              f"{sorted(browser_cookies)}")
        return {"cookies": browser_cookies}

    print("[警告] 未在任何浏览器中找到 x.com 的 auth_token，将以匿名方式尝试。"
          "X 通常强制登录，匿名大概率抓不到。")
    return {}


# ---------------------------------------------------------------------------
# 抓取主流程
# ---------------------------------------------------------------------------
def twitter_fetch(args):
    # 辅助模式：导出浏览器 cookie 后直接退出
    if args.extract_cookies:
        extract_cookies(args.browser or "chrome", args.extract_cookies)
        return

    # 校验并补全日期
    if args.since:
        _validate_date(args.since, "since")
    if args.until:
        _validate_date(args.until, "until")
    since = args.since or (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    until = args.until or datetime.now().strftime("%Y-%m-%d")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("[INFO] 关键词    :", args.keywords)
    print("[INFO] 时间范围  :", since, "~", until)
    print("[INFO] 语言      :", args.lang or "不限")
    print("[INFO] 排序      :", args.display_type)
    print("[INFO] 输出目录  :", outdir)
    print("[INFO] 代理      :", args.proxy or "无")
    if args.limit:
        print("[INFO] 上限条数  :", args.limit)
    print("=" * 60)

    # 惰性导入
    try:
        from Scweet import Scweet
    except ImportError as exc:
        sys.exit(f"[错误] 缺少 scweet: {exc}\n请先执行: pip install scweet")

    kwargs = _load_cookies(args)
    if args.db:
        kwargs["db_path"] = args.db
    if args.proxy:
        kwargs["proxy"] = args.proxy

    print("[INFO] 初始化 Scweet 客户端……")
    try:
        client = Scweet(**kwargs)
    except Exception as exc:
        sys.exit(f"[错误] 初始化失败: {exc}\n"
                 f"       多数为登录态无效/被风控所致。请换账号，或重新提取最新 cookie。")

    # 构建搜索条件
    search_kwargs = dict(
        since=since,
        until=until,
        all_words=args.keywords,
        lang=args.lang,
        min_likes=args.minlikes,
        min_replies=args.minreplies,
        min_retweets=args.minretweets,
        display_type=args.display_type,
        limit=args.limit,
    )
    if args.max_empty_pages is not None:
        search_kwargs["max_empty_pages"] = args.max_empty_pages
    if args.from_account:
        search_kwargs["from_users"] = [args.from_account]
    if args.hashtag:
        search_kwargs["hashtags_any"] = [args.hashtag]
    if args.save:
        search_kwargs["save"] = True
        search_kwargs["save_format"] = args.save_format

    print("[INFO] 开始抓取，可能需要几分钟……")
    try:
        tweets = client.search(query="", **search_kwargs)
    except Exception as exc:
        sys.exit(f"[错误] 抓取失败: {exc}")

    if not tweets:
        print("[警告] 未抓取到任何推文。可能原因: 账号被风控/限流、关键词过冷、时间范围无数据。")
        return

    # 去重（按 tweet_id）
    seen = set()
    unique = []
    for t in tweets:
        tid = t.get("tweet_id") or t.get("id")
        if tid is None or tid not in seen:
            seen.add(tid)
            unique.append(t)
    if len(unique) != len(tweets):
        print(f"[INFO] 去重: {len(tweets)} -> {len(unique)} 条")

    # 落盘到自定目录（Scweet 默认存到 cwd，这里统一写一份到 outdir）
    key_part = "_".join(args.keywords)
    safe_key = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in key_part)
    lang_part = args.lang or "all"

    try:
        import pandas as pd
        df = pd.DataFrame(unique)
        filename = f"tweets_{safe_key}_{since}_{until}_{lang_part}.csv"
        df.to_csv(outdir / filename, index=False, encoding="utf-8-sig")
        print(f"[OK] 共抓取 {len(unique)} 条推文，已保存: {outdir / filename}")
    except ImportError:
        filename = f"tweets_{safe_key}_{since}_{until}_{lang_part}.json"
        (outdir / filename).write_text(
            json.dumps(unique, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[OK] 共抓取 {len(unique)} 条推文（未装 pandas，改用 json）: {outdir / filename}")

    # 预览前几条
    print("\n[预览] 前 5 条：")
    for t in unique[:5]:
        user = (t.get("user") or {}).get("screen_name", "?")
        ts = t.get("timestamp", "?")
        text = (t.get("text") or "").replace("\n", " ")[:80]
        print(f"  [{ts}] @{user}: {text}")


# ---------------------------------------------------------------------------
# 参数解析（供 `python twitter.py` 独立运行）
# ---------------------------------------------------------------------------
def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="使用 Scweet v5 抓取 Twitter/X 指定关键词的推文并保存到本地。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    auth = parser.add_argument_group("登录授权（三选一，推荐 cookies-file 或 auth-token）")
    auth.add_argument("--cookies-file", "-c", default=None, help="cookies.json 文件路径")
    auth.add_argument("--auth-token", "-t", default=None, help="直接给定 auth_token 值，ct0 自动引导")
    auth.add_argument("--inline-cookies", default=None, help="内联 JSON cookie 字符串")

    parser.add_argument("--keywords", "-k", nargs="+", required=True, help="关键词，可多个")
    parser.add_argument("--since", default=None, help="起始日期 YYYY-MM-DD，默认最近 30 天")
    parser.add_argument("--until", default=None, help="结束日期 YYYY-MM-DD，默认今天")

    parser.add_argument("--lang", "-l", default=None, help="语言过滤，如 zh / en")
    parser.add_argument("--minlikes", type=int, default=None, help="点赞数下限")
    parser.add_argument("--minreplies", type=int, default=None, help="回复数下限")
    parser.add_argument("--minretweets", type=int, default=None, help="转推数下限")
    parser.add_argument("--from-account", default=None, help="只看某账号发出的推文")
    parser.add_argument("--hashtag", default=None, help="仅含某话题标签")
    parser.add_argument("--display-type", default="Top", choices=["Top", "Latest"], help="结果排序")
    parser.add_argument("--limit", type=int, default=None, help="最多抓取条数")

    parser.add_argument("--max-empty-pages", type=int, default=None, help="连续空页停止阈值")
    parser.add_argument("--db", default=None, help="Scweet 状态数据库路径")
    parser.add_argument("--outdir", "-o", default="./tweets", help="结果保存目录，默认 ./tweets")
    parser.add_argument("--proxy", default=None, help="代理地址")
    parser.add_argument("--save", action="store_true", help="同时让 Scweet 自己把结果落盘")
    parser.add_argument("--save-format", default="csv", choices=["csv", "json", "both"], help="--save 时的落盘格式")

    parser.add_argument("--extract-cookies", "-E", metavar="FILE", default=None,
                        help="把浏览器中已登录 x.com 的 cookie 导出到指定文件并退出")
    parser.add_argument("--browser", default=None,
                        choices=["firefox", "chrome", "edge", "chromium", "brave", "opera_gx"],
                        help="提取 cookie 的浏览器；缺省按 firefox→chrome→edge 自动尝试，"
                             "与 -E 共用时默认 chrome")
    return parser.parse_args(argv)


def reg_subparser(subparsers):
    p = subparsers.add_parser("twitter", help="抓取 Twitter/X 关键词推文")
    p.add_argument("-k", "--keywords", nargs="+", required=True, help="关键词，可多个")
    p.add_argument("-c", "--cookies-file", default=None, help="cookies.json 文件路径")
    p.add_argument("-t", "--auth-token", default=None, help="auth_token 值，ct0 自动引导")
    p.add_argument("--inline-cookies", default=None, help="内联 JSON cookie 字符串")
    p.add_argument("--since", default=None, help="起始日期 YYYY-MM-DD，默认最近 30 天")
    p.add_argument("--until", default=None, help="结束日期 YYYY-MM-DD，默认今天")
    p.add_argument("-l", "--lang", default=None, help="语言过滤")
    p.add_argument("--minlikes", type=int, default=None, help="点赞数下限")
    p.add_argument("--minreplies", type=int, default=None, help="回复数下限")
    p.add_argument("--minretweets", type=int, default=None, help="转推数下限")
    p.add_argument("--from-account", default=None, help="只看某账号发出的推文")
    p.add_argument("--hashtag", default=None, help="仅含某话题标签")
    p.add_argument("--display-type", default="Top", choices=["Top", "Latest"], help="结果排序")
    p.add_argument("--limit", type=int, default=None, help="最多抓取条数")
    p.add_argument("--max-empty-pages", type=int, default=None, help="连续空页停止阈值")
    p.add_argument("--db", default=None, help="Scweet 状态数据库路径")
    p.add_argument("-o", "--outdir", default="./tweets", help="结果保存目录，默认 ./tweets")
    p.add_argument("--proxy", default=None, help="代理地址")
    p.add_argument("--save", action="store_true", help="同时让 Scweet 自己把结果落盘")
    p.add_argument("--save-format", default="csv", choices=["csv", "json", "both"], help="--save 时的落盘格式")
    p.add_argument("-E", "--extract-cookies", metavar="FILE", default=None,
                   help="把浏览器中已登录 x.com 的 cookie 导出到指定文件并退出")
    p.add_argument("--browser", default=None,
                   choices=["firefox", "chrome", "edge", "chromium", "brave", "opera_gx"],
                   help="提取 cookie 的浏览器；缺省按 firefox→chrome→edge 自动尝试，"
                        "与 -E 共用时默认 chrome")
    p.set_defaults(func=twitter_fetch)


def main(argv=None):
    twitter_fetch(parse_args(argv))


if __name__ == "__main__":
    main()