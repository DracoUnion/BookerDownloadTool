from .util import *
import json
from os import path

def download_uqer(args):
    tid = args.tid
    dir = args.dir
    safe_mkdir(dir)
    
    url = f'https://gw.datayes.com/mercury_community/w/thread/{tid}'
    j = request_retry('GET', url).json()
    if j['code'] != 200:
        print(f'[tid={tid}] 下载失败：{j}')
        return

    fmt = j['data']['content_format']
    if fmt == 'markdown':
        title = j['data']['title']
        cont = j['data']['content']
        ofname = path.join(dir, f'{tid}.md')
        if path.isfile(ofname):
            print(f'[tid={tid}] 已下载')
            return
        print(ofname)
        open(ofname, 'w', encoding='utf8').write(f'# {title}\n\n{cont}')
    else:
        print(f'格式为 {fmt}，不是 Markdown，无法处理')

    for it in j['data']['attachments']:
        fmt = it['content_format']
        if fmt != 'ipynb':
            print(f'附件格式为 {fmt}，不是 ipynb，无法处理')
            continue
        aid = it['attachment_id']
        notebook = it['content']
        name = it['notebook_name'][:-6]
        notebook['worksheets'][0]['cells'].insert(0, {
            "cell_type": "markdown", 
            "id": uuid.uuid4().hex.upper(), 
            "metadata": {}, 
            "source": f'# {name}',
        })
        ofname = path.join(dir, f'{tid} - {aid}.ipynb')
        if path.isfile(ofname):
            print(f'[aid={aid}] 已下载')
            continue
        print(ofname)
        open(ofname, 'w', encoding='utf8').write(json.dumps(notebook))
    
        
    