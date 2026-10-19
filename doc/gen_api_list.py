# -*- coding: utf-8 -*-
"""
生成小红书 Android API 接口清单 markdown（按域名 + 模块分组）。
"""
import json
import re
from collections import OrderedDict, defaultdict

DATA = r"D:\src\BookerDownloadTool\_xhs_data\api_final.json"

# 域名归属规则（基于反编译 host 枚举 xa6/a.java 与域名映射 w2d/b.java）
DEFAULT_HOST = "edith.xiaohongshu.com"

def host_for(r):
    p = (r['path'] or '').strip()
    if p.startswith('http'):
        return p.split('/')[2]
    return DEFAULT_HOST

def mod_for(r):
    p = (r['path'] or '').strip().lstrip('/')
    if p.startswith('http'):
        parts = p.split('/')[3:]
        seg = parts[0] if parts else ''
    else:
        parts = p.split('/')
        # api/sns/... -> module = "sns"
        if parts and parts[0] == 'api' and len(parts) > 1:
            seg = parts[1]
        elif parts:
            seg = parts[0]
        else:
            seg = '(empty)'
    return seg

def param_str(r):
    """format request params: Query: a,b  Field: c  Body: Type; Path: x"""
    groups = OrderedDict()
    for p in r['params']:
        anno = p['anno']
        if anno == 'Body':
            groups.setdefault('Body', []).append(p['type'])
        elif anno in ('Tag',):
            continue
        else:
            key = p['key']
            if not key:
                continue
            groups.setdefault(anno, []).append(key)
    parts = []
    order = ['Path', 'Query', 'Field', 'Body', 'Header', 'FieldMap', 'QueryMap', 'HeaderMap', 'Part', 'PartMap']
    for k in order:
        if k in groups:
            v = groups[k]
            # unique preserve order
            seen = set(); uniq = []
            for x in v:
                if x not in seen:
                    seen.add(x); uniq.append(x)
            parts.append(f"{k}: " + ", ".join(uniq))
    return "; ".join(parts)

def main():
    data = json.load(open(DATA, encoding='utf-8'))
    # group by host then module
    hosts = defaultdict(lambda: defaultdict(list))
    for r in data:
        h = host_for(r)
        m = mod_for(r)
        hosts[h][m].append(r)
    out = []
    out.append("## 接口清单")
    for host in sorted(hosts.keys()):
        mods = hosts[host]
        out.append(f"\n### 域名 `{host}`")
        for mod in sorted(mods.keys()):
            items = mods[mod]
            out.append(f"\n#### `{mod}`（{len(items)} 个接口）")
            out.append("| 方法 | 路径 | 请求参数 | 来源类 |")
            out.append("| --- | --- | --- | --- |")
            for r in sorted(items, key=lambda x: (x['http'], x['path'] or '')):
                path = (r['path'] or '').strip()
                if path.startswith('http'):
                    # absolute url — show full
                    pass
                src = f"{r['class']}" if r['class'] else ""
                out.append(f"| `{r['http']}` | `{path}` | {param_str(r)} | {src} |")
    return "\n".join(out)

if __name__ == '__main__':
    text = main()
    with open(r"D:\src\BookerDownloadTool\_xhs_data\api_list.md", "w", encoding='utf-8') as fh:
        fh.write(text)
    print("written, len:", len(text))