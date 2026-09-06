import argparse
from . import __version__
from . import (
    annas, arxiv, discuz, dl_gh_book, ext_cookie, feishu, freembook,
    gh, hkrnws, lightnovel, links, medium, pic, uqer, webarchive,
    whole_site, wx, yuque, zhihu, zsxq,
)


def main():
    parser = argparse.ArgumentParser(prog="BookerDownloadTool", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--version", action="version", version=f"PYBP version: {__version__}")
    parser.add_argument("-H", "--no-headless", action="store_false")
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
    annas.reg_subparser(subparsers)
    ext_cookie.reg_subparser(subparsers)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()