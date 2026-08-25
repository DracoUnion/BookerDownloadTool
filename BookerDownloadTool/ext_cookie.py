import browser_cookie3 as bc
from .util import  cookie_dict_to_str

def extract_cookies(browser, domain):
    assert browser in [f.__name__ for f in bc.all_browsers]
    jar = getattr(bc, browser)()
    cookies = {
        c.name:c.value
        for c in jar
        if domain in c.domain
    }
    return cookies

def ext_cookies_hdl(args):
    cookies = cookie_dict_to_str(extract_cookies(args.browser, args.domain))
    print(f'获取结果：\n{cookies}')