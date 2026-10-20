#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xhs.py — 小红书 Web 端搜索 + 笔记详情抓取

调用小红书 Web 端 HTTP API（edith.xiaohongshu.com）：
  1. 搜索给定关键词的分页笔记列表（POST /api/sns/web/v1/search/notes）
  2. 对每条笔记调用详情接口取全量文字与图片
     （POST /api/sns/web/v1/feed，需 xsec_token；失败降级解析 SSR HTML）
  3. 把每篇笔记的文本（Markdown）与图片保存到指定目录（默认 ./xhs）

签名参考 doc/xhs_api_2.md 第 5 节：主域签名走 xhshow 库。
Cookie 默认取本机浏览器（browser_cookie3）的 xiaohongshu.com 会话，
也可用 -c/--cookie 直接提供（含 a1 与 web_session）。

依赖:
    pip install xhshow httpx browser_cookie3
"""

import json
import os
import random
import time
from pathlib import Path

import httpx

from .ext_cookie import extract_cookies_multi_browsers
from .util import cookie_str_to_dict, fname_escape

# ---------------------------------------------------------------------------
# 常量（doc/xhs_api_2.md §1.1 / §2.2）
# ---------------------------------------------------------------------------
EDITH_HOST = "https://edith.xiaohongshu.com"
HOME_URL = "https://www.xiaohongshu.com"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)
SDK_VERSION = "4.3.5"
APP_ID = "xhs-pc-web"
PLATFORM = "macOS"

SEARCH_URI = "/api/sns/web/v1/search/notes"
ONEOBOX_URI = "/api/sns/web/v1/search/onebox"
FILTER_URI = "/api/sns/web/v1/search/filter"
FEED_URI = "/api/sns/web/v1/feed"

# 搜索接口默认 filters（doc §2.3）
DEFAULT_FILTERS = [
    {"tags": ["general"], "type": "sort_type"},
    {"tags": ["不限"], "type": "filter_note_type"},
    {"tags": ["不限"], "type": "filter_note_time"},
    {"tags": ["不限"], "type": "filter_note_range"},
    {"tags": ["不限"], "type": "filter_pos_distance"},
]

IMAGE_FORMATS = ["jpg", "webp", "avif"]

# ---------------------------------------------------------------------------
# 主域签名（doc §5.1）
# ---------------------------------------------------------------------------
try:
    from xhshow import CryptoConfig, SessionManager, Xhshow

    _config = CryptoConfig().with_overrides(
        PUBLIC_USERAGENT=USER_AGENT,
        SIGNATURE_DATA_TEMPLATE={
            "x0": SDK_VERSION, "x1": APP_ID, "x2": PLATFORM, "x3": "", "x4": "",
        },
        SIGNATURE_XSCOMMON_TEMPLATE={
            "s0": 5, "s1": "", "x0": "1", "x1": SDK_VERSION, "x2": PLATFORM,
            "x3": APP_ID, "x4": "4.86.0", "x5": "", "x6": "", "x7": "",
            "x8": "", "x9": -596800761, "x10": 0, "x11": "normal",
        },
    )
    _xhshow = Xhshow(_config)
    _session = SessionManager(_config)
except ImportError:
    _xhshow = None
    _session = None


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def _base36(n: int) -> str:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "0"
    out = []
    while n:
        n, r = divmod(n, 36)
        out.append(chars[r])
    return "".join(reversed(out))


def _first(d, keys, default=None):
    """按优先级取字典字段（兼容 note/note_card、interactInfo/interact_info 混用）。"""
    if not isinstance(d, dict):
        return default
    for k in keys:
        v = d.get(k)
        if v is not None and v != "":
            return v
    return default


def _pick_images(note):
    """从笔记对象中提取图片 URL 列表。

    优先级: image_list / imageList / images -> cover.info_list -> cover.url_default。
    """
    if not isinstance(note, dict):
        return []
    imgs = _first(note, ["image_list", "imageList", "images"])
    if isinstance(imgs, list):
        urls = []
        for it in imgs:
            if isinstance(it, str):
                urls.append(it)
            elif isinstance(it, dict):
                url = _first(it, ["urlDefault", "url_default", "originUrl", "origin_url", "url"])
                if url:
                    urls.append(url)
        if urls:
            return urls
    # cover 兜底
    cover = note.get("cover")
    if isinstance(cover, dict):
        info_list = cover.get("info_list") or cover.get("infoList")
        if isinstance(info_list, list):
            return [_first(it, ["urlDefault", "url_default", "url"], "") for it in info_list if it]
        url = _first(cover, ["urlDefault", "url_default", "originUrl", "origin_url", "url"])
        if url:
            return [url]
    return []


# ---------------------------------------------------------------------------
# HTTP 客户端（doc §5.3 精简版）
# ---------------------------------------------------------------------------
class XhsApiError(Exception):
    pass


class XhsClient:
    def __init__(self, cookies: dict, timeout=30.0, request_delay=1.0, max_retries=3):
        self.cookies = cookies or {}
        self._http = httpx.Client(timeout=timeout, follow_redirects=True)
        self._request_delay = request_delay
        self._max_retries = max_retries
        self._last_request_time = 0.0
        self._verify_count = 0
        self._search_sessions = {}  # keyword -> search_id

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # -- 基础请求 ----------------------------------------------------------
    def _rate_limit_delay(self):
        if self._request_delay <= 0:
            return
        elapsed = time.time() - self._last_request_time
        if elapsed < self._request_delay:
            jitter = max(0, random.gauss(0.3, 0.15))
            time.sleep(self._request_delay - elapsed + jitter)

    def _base_headers(self):
        from .util import cookie_dict_to_str
        return {
            "user-agent": USER_AGENT,
            "content-type": "application/json;charset=UTF-8",
            "cookie": cookie_dict_to_str(self.cookies),
            "origin": HOME_URL,
            "referer": f"{HOME_URL}/",
            "sec-ch-ua": f'"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "dnt": "1",
            "priority": "u=1, i",
        }

    def _handle_response(self, resp):
        if resp.status_code in (461, 471):
            self._verify_count += 1
            cooldown = min(30, 5 * (2 ** (self._verify_count - 1)))
            time.sleep(cooldown)
            raise XhsApiError(
                f"HTTP {resp.status_code} 触发验证码 (verify_uuid={resp.headers.get('verifyuuid', '?')})")
        self._verify_count = 0
        text = resp.text
        if not text:
            return None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            raise XhsApiError(f"非 JSON 响应: {text[:200]}")
        if data.get("success"):
            return data.get("data", data.get("success"))
        code = data.get("code")
        msg = f"XHS API 错误: code={code} msg={data.get('msg','')}"
        if code == 300012:
            raise XhsApiError(msg + "（IP 被风控）")
        if code == 300015:
            raise XhsApiError(msg + "（签名校验失败）")
        if code == -100:
            raise XhsApiError(msg + "（会话过期，请刷新 Cookie）")
        raise XhsApiError(msg)

    def _request_with_retry(self, method, url, **kwargs):
        self._rate_limit_delay()
        last_exc = None
        for attempt in range(self._max_retries):
            try:
                resp = self._http.request(method, url, **kwargs)
                if resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep((2 ** attempt) + random.uniform(0, 1))
                    continue
                return resp
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                time.sleep((2 ** attempt) + random.uniform(0, 1))
        raise XhsApiError(f"请求失败(重试{self._max_retries}次): {last_exc}")

    # -- 主域 GET / POST ----------------------------------------------------
    def _main_api_get(self, uri, params=None):
        if _xhshow is None:
            raise XhsApiError("缺少 xhshow 库，请执行: pip install xhshow")
        sign_headers = _xhshow.sign_headers_get(
            uri, self.cookies, params=params, session=_session)
        url = f"{EDITH_HOST}{_xhshow.build_url(uri, params)}" if params else f"{EDITH_HOST}{uri}"
        resp = self._request_with_retry(
            "GET", url, headers={**self._base_headers(), **sign_headers})
        return self._handle_response(resp)

    def _main_api_post(self, uri, data, x_rap=False):
        if _xhshow is None:
            raise XhsApiError("缺少 xhshow 库，请执行: pip install xhshow")
        sign_headers = _xhshow.sign_headers_post(
            uri, self.cookies, payload=data, session=_session, x_rap=x_rap)
        body = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        resp = self._request_with_retry(
            "POST", f"{EDITH_HOST}{uri}",
            headers={**self._base_headers(), **sign_headers}, content=body)
        return self._handle_response(resp)

    # -- 搜索 ---------------------------------------------------------------
    def search_notes(self, keyword, page, page_size=20, sort="general", note_type=0):
        """搜索笔记（含会话 warmup），返回归一条目列表。"""
        session_key = (keyword, sort, note_type)
        if session_key not in self._search_sessions:
            ts_ms = int(time.time() * 1000)
            search_id = _base36((ts_ms << 64) | random.getrandbits(64))
            self._search_sessions[session_key] = search_id
            self._warmup(keyword, search_id)

        search_id = self._search_sessions[session_key]
        body = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_id": search_id,
            "sort": sort,
            "note_type": note_type,
            "ext_flags": [],
            "filters": DEFAULT_FILTERS,
            "geo": "",
            "image_formats": IMAGE_FORMATS,
            "need_filter_state": 1,
        }
        data = self._main_api_post(SEARCH_URI, body, x_rap=True)
        items = data.get("items", []) if isinstance(data, dict) else []
        return [self._normalize_note(it) for it in items]

    def _warmup(self, keyword, search_id):
        """首次搜索时的 onebox + filter 预热，失败忽略。"""
        try:
            self._main_api_post(ONEOBOX_URI, {
                "keyword": keyword,
                "search_id": search_id,
                "biz_type": "web_search_user",
                "request_id": f"{random.randint(0, 10**6)}-{int(time.time()*1000)}",
            })
            self._main_api_get(FILTER_URI, {"keyword": keyword, "search_id": search_id})
        except XhsApiError as exc:
            print(f"[警告] 搜索预热失败(忽略): {exc}")

    # -- 笔记详情 -----------------------------------------------------------
    def get_note_detail(self, note):
        """取笔记全量详情。

        有 xsec_token 优先 POST /feed；失败或缺失 token 降级解析 SSR HTML。
        "image_formats":... 返回含完整 desc 与 image_list。
        """
        note_id = note.get("note_id")
        if not note_id:
            return note
        token = note.get("xsec_token")
        if token:
            try:
                feed = self._main_api_post(FEED_URI, {
                    "source_note_id": note_id,
                    "image_formats": IMAGE_FORMATS,
                    "extra": {"need_body_topic": "1"},
                    "xsec_source": note.get("xsec_source") or "pc_feed",
                    "xsec_token": token,
                })
                if isinstance(feed, dict) and "items" in feed:
                    for it in feed["items"]:
                        it_note = it.get("note_card") or it.get("note") or it
                        if _first(it_note, ["note_id", "noteId", "id"]) == note_id:
                            note = self._normalize_note(it)
                            return note
                return note
            except XhsApiError as exc:
                print(f"[警告] feed 详情失败({note_id})，降级 SSR: {exc}")
        return self._get_note_by_html(note_id, note)

    # -- SSR HTML 兜底 -------------------------------------------------------
    def _get_note_by_html(self, note_id, fallback_note):
        url = f"{HOME_URL}/explore/{note_id}"
        headers = {
            "user-agent": USER_AGENT,
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        try:
            resp = self._http.get(url, headers=headers)
            resp.raise_for_status()
            text = resp.text
            marker = "window.__INITIAL_STATE__="
            i = text.find(marker)
            if i < 0:
                raise XhsApiError("SSR 页面未找到 __INITIAL_STATE__")
            j = text.find("</script>", i)
            payload = text[i + len(marker):j].strip()
            if payload.endswith(";"):
                payload = payload[:-1]
            state = json.loads(payload)
            # 从 note.detailMap / noteDetail... 中取该 note_id 的笔记
            note_obj = self._extract_from_state(state, note_id)
            if note_obj:
                return self._normalize_note(note_obj)
            raise XhsApiError("SSR state 中未找到笔记数据")
        except Exception as exc:
            print(f"[警告] SSR 解析失败({note_id}): {exc}")
            return fallback_note

    @staticmethod
    def _extract_from_state(state, note_id):
        """递归在 SSR state 中寻找与 note_id 匹配的笔记对象。"""
        candidates = []
        stack = [state]
        while stack:
            v = stack.pop()
            if isinstance(v, dict):
                nid = _first(v, ["note_id", "noteId", "id"])
                if nid == note_id and "desc" in v:
                    candidates.append(v)
                elif nid == note_id and ("title" in v or "image_list" in v):
                    candidates.append(v)
                stack.extend(v.values())
            elif isinstance(v, list):
                stack.extend(v)
        if candidates:
            return max(candidates, key=lambda c: len(str(c)))
        return None

    # -- 归一化 ---------------------------------------------------------------
    def _normalize_note(self, item):
        note = item.get("note_card") or item.get("note") or item
        note_id = str(_first(note, ["note_id", "noteId", "id"], ""))
        user = note.get("user") or {}
        follow = note.get("interact_info") or note.get("interactInfo") or {}
        images = _pick_images(note)
        return {
            "note_id": note_id,
            "title": _first(note, ["title", "display_title", "displayTitle"], ""),
            "desc": _first(note, ["desc", "description", "body"], ""),
            "author": _first(user, ["nickname", "name", "user_id"], ""),
            "likes": _first(follow, ["liked_count", "likedCount", "likes"], 0),
            "collects": _first(follow, ["collected_count", "collectedCount", "collects"], 0),
            "comments": _first(follow, ["comment_count", "commentCount", "comments"], 0),
            "media_type": _first(note, ["type", "media_type"], "image"),
            "images": images,
            "xsec_token": _first(note, ["xsec_token", ""], None) or None,
            "xsec_source": _first(note, ["xsec_source", ""], None),
        }


# ---------------------------------------------------------------------------
# Cookie 获取
# ---------------------------------------------------------------------------
def load_xhs_cookies(args):
    """优先 browser_cookie3 取本浏览器 xiaohongshu.com cookie；
    失败或显式给 -c/--cookie 时用明文 Cookie 串。
    """
    if args.cookie:
        return cookie_str_to_dict(args.cookie)
    print(f"[警告] 无法解析 -c Cookie 串，回退到浏览器提取")

    cookies = extract_cookies_multi_browsers("xiaohongshu.com")
    if not cookies:
        raise SystemExit(
            "[错误] 未获取到 xiaohongshu.com 的 Cookie。\n"
            "       请在 Chrome 登录小红书后重试，或手动提供 -c \"a1=..; web_session=..\"")
    print(f"[INFO] 已从本机浏览器提取登录 Cookie: "
          f"{sorted(cookies)}")
    return cookies


# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------
def download_image(client, url, outpath):
    headers = {
        "user-agent": USER_AGENT,
        "referer": f"{HOME_URL}/",
        "accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    resp = client._http.get(url, headers=headers, follow_redirects=True)
    resp.raise_for_status()
    outpath.write_bytes(resp.content)


def ext_from_url(url, default="jpg"):
    p = url.rsplit("?", 1)[0] if "?" in url else url
    ext = p.rsplit(".", 1)[-1] if "." in p.split("/")[-1] else ""
    return ext[:5].lower() if ext and ext.isalnum() else default


def save_notes(client, notes, outdir, keyword, no_img=False):
    kw_dir = Path(outdir) / fname_escape(keyword)
    img_dir = kw_dir / "imgs"
    kw_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    for n in notes:
        nid = n["note_id"] or f"note_{abs(hash(json.dumps(n, ensure_ascii=False)))}"
        safe_id = fname_escape(nid)
        # 下载图片
        img_refs = []
        if not no_img:
            for i, url in enumerate(n["images"]):
                ext = ext_from_url(url)
                fname = f"{safe_id}_{i}.{ext}"
                try:
                    download_image(client, url, img_dir / fname)
                    img_refs.append(f"imgs/{fname}")
                except Exception as exc:
                    print(f"[警告] 图片下载失败 {url}: {exc}")
        # 写 Markdown
        lines = ["---"]
        for k, v in (
            ("note_id", nid), ("title", n["title"]), ("author", n["author"]),
            ("likes", n["likes"]), ("collects", n["collects"]),
            ("comments", n["comments"]), ("media_type", n["media_type"]),
        ):
            lines.append(f"{k}: '{str(v)}'")
        lines.append("---")
        lines.append("")
        lines.append(f"# {n['title']}")
        lines.append("")
        lines.append(n["desc"] or "")
        lines.append("")
        for ref in img_refs:
            lines.append(f"![{nid}]({ref})")
        lines.append("")
        (kw_dir / f"{safe_id}.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"[OK] {nid}  {n['title'][:40]}")

    print(f"\n[完成] 共 {len(notes)} 篇笔记，已保存到: {kw_dir}")


# ---------------------------------------------------------------------------
# CLI handler & 注册
# ---------------------------------------------------------------------------
def xhs_search(args):
    outdir = args.outdir
    Path(outdir).mkdir(parents=True, exist_ok=True)

    cookies = load_xhs_cookies(args)
    if not cookies.get("a1"):
        print("[警告] Cookie 缺少 a1（签名输入），签名可能失败")
    if not cookies.get("web_session"):
        print("[警告] Cookie 缺少 web_session（登录态），可能被限流/拒绝")

    with XhsClient(cookies, request_delay=args.delay) as client:
        for page in range(1, args.pages + 1):
            print(f"[INFO] 搜索第 {page}/{args.pages} 页: {args.keyword}")
            notes = client.search_notes(
                args.keyword, page, page_size=args.page_size,
                sort=args.sort, note_type=args.note_type)
            if not notes:
                print("[警告] 本页无结果，停止翻页")
                break

            detailed = []
            for n in notes:
                detail = client.get_note_detail(n)
                detailed.append(detail)

            save_notes(client, detailed, outdir, args.keyword, no_img=args.no_img)


def reg_subparser(subparsers):
    xhs_parser = subparsers.add_parser(
        "xhs", help="搜索小红书笔记并保存全量文本与图片（Cookie 默认取自本机浏览器）")
    xhs_parser.add_argument("keyword", help="搜索关键词")
    xhs_parser.add_argument("-p", "--pages", type=int, default=1, help="抓取页数，默认 1")
    xhs_parser.add_argument("-n", "--page-size", type=int, default=20, help="每页条数，默认 20")
    xhs_parser.add_argument("-o", "--outdir", default="xhs", help="保存目录，默认 ./xhs")
    xhs_parser.add_argument("-c", "--cookie",
                            help="小红书 Cookie 串（含 a1 / web_session）；缺省则用浏览器 Cookie")
    xhs_parser.add_argument("--sort", default="general", choices=["general", "default"],
                            help="搜索结果排序，默认 general")
    xhs_parser.add_argument("--note-type", type=int, default=0,
                            help="笔记类型 0=不限 1=图文 2=视频，默认 0")
    xhs_parser.add_argument("--no-img", action="store_true", help="不下载图片")
    xhs_parser.add_argument("--delay", type=float, default=1.0, help="请求间隔秒数，默认 1.0")
    xhs_parser.set_defaults(func=xhs_search)


if __name__ == "__main__":
    parser = __import__("argparse").ArgumentParser(description=__doc__)
    parser.add_argument("keyword")
    parser.add_argument("-p", "--pages", type=int, default=1)
    parser.add_argument("-n", "--page-size", type=int, default=20)
    parser.add_argument("-o", "--outdir", default="xhs")
    parser.add_argument("-c", "--cookie", default=os.environ.get("XHS_COOKIE"))
    ns = parser.parse_args()
    xhs_search(ns)