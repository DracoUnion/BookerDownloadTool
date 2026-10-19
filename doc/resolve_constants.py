# -*- coding: utf-8 -*-
"""
增强：解析 API 提取结果中的常量引用为字面值，输出干净的 doc 源数据。
"""
import json, re, os

DATA = r"D:\src\BookerDownloadTool\_xhs_data\api_raw.json"
SOURCES = r"D:\src\BookerDownloadTool\_xhs_decompile\sources"
OUT = r"D:\src\BookerDownloadTool\_xhs_data\api_final.json"

# Build constant lookup: "com.pkg.Class.CONST" -> value
CONST_RE = re.compile(r'public\s+static\s+final\s+(?:java\.lang\.)?String\s+(\w+)\s*=\s*"([^"]*)"')
const_cache = {}
def resolve_constant(token):
    if not token or '.' not in token:
        return token
    if token in const_cache:
        return const_cache[token]
    # try find source file for the class
    parts = token.split('.')
    classname = parts[-2]
    constname = parts[-1]
    pkg = '.'.join(parts[:-2])
    pkg_path = pkg.replace('.', '/')
    fpath = os.path.join(SOURCES, pkg_path, classname + '.java')
    if os.path.exists(fpath):
        try:
            with open(fpath, encoding='utf-8', errors='replace') as fh:
                text = fh.read()
            m = CONST_RE.search(text, re.MULTILINE)
            if m and m.group(1) == constname:
                const_cache[token] = m.group(2)
                return m.group(2)
        except Exception:
            pass
    const_cache[token] = token
    return token

def main():
    data = json.load(open(DATA, encoding='utf-8'))
    for r in data:
        for p in r['params']:
            if p['anno'] in ('Field', 'Query', 'Path', 'Header'):
                resolved = resolve_constant(p['key'])
                p['key'] = resolved
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print("resolved constants, total:", len(data))
    # stats by path prefix
    from collections import Counter
    c = Counter(r['http'] for r in data)
    print(c)

if __name__ == '__main__':
    main()