import pandas as pd
from os import path
import re
import subprocess as subp
import json

POST_TIME = '发布时间'
ART_LINK = '文章链接'
GZH_NAME = '公众号'
DIR = path.dirname(path.abspath(__file__))

config_tmpl = {
    "name": "{name}",
    "url": "http://mp.weixin.qq.com",
    "link": ".summary .link, .summary li a",
    "title": "#activity-name",
    "content": "#js_content",
    "remove": "",
    "optiMode": "thres",
	"external": path.join(DIR, 'wx_external.py'),
	"retry": 3,
	"list":[],
}

def crawl_wx(args):
    fname = args.fname
    size = args.size
    if not fname.endswith('.xls') and \
        not fname.endswith('.xlsx'):
        print('请提供 EXCEL 文件')
        return
    df_all = pd.read_excel(fname)
    if  POST_TIME not in df_all.columns or \
        ART_LINK not in df_all.columns or \
        GZH_NAME not in df_all.columns:
        print(f'未找到【{GZH_NAME}】、【{POST_TIME}】和【{ART_LINK}】')
        return
    df_all = df_all[df_all[ART_LINK].str.startswith('http')]
    gzh_names = df_all[GZH_NAME].unique()
    for gzh_name in gzh_names:
        df = df_all[df_all[GZH_NAME] == gzh_name]
        df.sort_values(by=POST_TIME, inplace=True, ascending=False)
        for i in range(0, len(df), size):
            df_part = df.iloc[i:i+size]
            st = df_part[POST_TIME].iloc[-1].replace('-', '')[:6]
            ed = df_part[POST_TIME].iloc[0].replace('-', '')[:6]
            name = f'{gzh_name} {st}-{ed}'
            config = config_tmpl.copy()
            config['name'] = name
            config['list'] = df_part[ART_LINK].tolist()
            config['optiMode'] = args.opti_mode
            config_fname = f'config_{gzh_name}_{st}_{ed}.json'
            open(config_fname, 'w', encoding='utf8').write(json.dumps(config))
            subp.Popen(['crawl-epub', config_fname], shell=True).communicate()