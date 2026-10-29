import argparse
import os
import sys
from . import __version__
from . import (
    annas, arxiv, bili_ai_proj, discuz, dl_gh_book, ext_cookie, feishu,
    freembook, gh, hkrnws, lightnovel, links, medium, pic, uqer,
    webarchive, whole_site, wenku, wx, wx_summary, yuque, zhihu,
    zhihu_radar, zsxq, twitter, xhs,
)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    openai_key = os.environ.get('OPENAI_API_KEY')
    openai_url = os.environ.get('OPENAI_BASE_URL')
    openai_model = os.environ.get('OPENAI_CHAT_MODEL', 'gpt-3.5-turbo')
    openai_vmodel = os.environ.get('OPENAI_VIS_MODEL', '')
    openai_tti_model = os.environ.get('OPENAI_TTI_MODEL', '')

    parser = argparse.ArgumentParser(prog="BookerDownloadTool", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--version", action="version", version=f"PYBP version: {__version__}")
    parser.add_argument("-H", "--no-headless", action="store_false")
    parser.add_argument("-m", "--model", default=openai_model, help="模型名称")
    parser.add_argument("-k", "--key", default=openai_key, help="OpenAI API Key")
    parser.add_argument("-r", "--retry", type=int, default=1_000_000, help="重试次数")
    parser.add_argument("-tm", "--temp", type=float, default=1, help="温度")
    parser.add_argument("-tp", "--top-p", type=float, help="top-p")
    parser.add_argument("-fp", "--frequency-penalty", type=float, help="频率惩罚")
    parser.add_argument("-pp", "--presence-penalty", type=float, help="存在惩罚")
    parser.add_argument("-mt", "--max-tokens", type=int, default=None, help="最大 token 数")
    parser.add_argument("--host", default=openai_url, help="API 地址")
    parser.add_argument("--emb", default=os.environ.get('EMB_MODEL_PATH', 'moka-ai/m3e-base'), help="Embedding 模型路径")
    parser.add_argument("-vm", "--vmodel", default=openai_vmodel, help="视觉模型名称")
    parser.add_argument("-im", "--tti-model", default=openai_tti_model, help="文生图模型名称")
    parser.add_argument("-ua", "--user-agent", default='claude-cli/2.1.41 (external, cli)', help="HTTP User-Agent 请求头")
    parser.add_argument("-st", "--stream", action='store_true' , help="流式输出模式")
    parser.add_argument("-eb", "--extra-body", help="额外请求体")
    parser.add_argument("-ct", "--conn-timeout", type=int, default=60, help="连接超时秒数")
    parser.add_argument("-rt", "--read-timeout", type=int, default=120, help="读取超时秒数")
    parser.add_argument("-rr", "--repetition-regex", default='', help="重复检测正则")
    parser.add_argument("-nt", "--no-think", action='store_true', help="关闭思考模式")
    parser.set_defaults(func=lambda x: parser.print_help())
    subparsers = parser.add_subparsers()

    dl_gh_book.reg_subparser(subparsers)
    lightnovel.reg_subparser(subparsers)
    zhihu.reg_subparser(subparsers)
    discuz.reg_subparser(subparsers)
    zsxq.reg_subparser(subparsers)
    whole_site.reg_subparser(subparsers)
    medium.reg_subparser(subparsers)
    webarchive.reg_subparser(subparsers)
    links.reg_subparser(subparsers)
    wx.reg_subparser(subparsers)
    uqer.reg_subparser(subparsers)
    freembook.reg_subparser(subparsers)
    yuque.reg_subparser(subparsers)
    feishu.reg_subparser(subparsers)
    arxiv.reg_subparser(subparsers)
    gh.reg_subparser(subparsers)
    hkrnws.reg_subparser(subparsers)
    pic.reg_subparser(subparsers)
    wenku.reg_subparser(subparsers)
    annas.reg_subparser(subparsers)
    ext_cookie.reg_subparser(subparsers)
    twitter.reg_subparser(subparsers)
    xhs.reg_subparser(subparsers)

    bili_ai_proj.reg_subparser(subparsers)
    zhihu_radar.reg_subparser(subparsers)
    wx_summary.reg_subparser(subparsers)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()