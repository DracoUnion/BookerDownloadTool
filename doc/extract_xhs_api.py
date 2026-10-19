# -*- coding: utf-8 -*-
"""
提取小红书 APK 反编译代码中的所有 HTTP 接口定义（@jce.* 注解的 Service 接口）。
行级精确解析。输出 doc 用结构化 JSON。

已知映射（来自 fce/z.java 接口处理代码）：
  jce.f=GET, jce.o=POST, jce.p=PUT, jce.b=DELETE, jce.g=HEAD,
  jce.n=PATCH, jce.m=OPTIONS, jce.h=custom(method,path,hasBody)
  jce.t=@Query jce.c=@Field jce.s=@Path jce.i=@Header jce.a=@Body
  jce.d=@FieldMap jce.u=@QueryMap jce.q=@Part r=@PartMap
  jce.y=@Url jce.x=@Tag v=@QueryName j=@HeaderMap
  jce.e=@FormUrlEncoded jce.l=@Multipart k=@Headers
"""
import os
import re
import json
import sys
from collections import Counter

SOURCES = r"D:\src\BookerDownloadTool\_xhs_decompile\sources"
OUT = r"D:\src\BookerDownloadTool\_xhs_data"

METHOD_ANN = {"f": "GET", "o": "POST", "p": "PUT", "b": "DELETE",
              "g": "HEAD", "n": "PATCH", "m": "OPTIONS"}
PARAM_ANN = {"t": "Query", "c": "Field", "s": "Path", "i": "Header",
             "a": "Body", "d": "FieldMap", "u": "QueryMap", "q": "Part",
             "r": "PartMap", "y": "Url", "x": "Tag", "v": "QueryName",
             "j": "HeaderMap"}

# A line like:    @jce.o("/api/sns/v6/homefeed")
LN_METHOD_RE = re.compile(r'^\s*@jce\.([fopbgnm])\s*\(\s*(?:value\s*=\s*)?["\']([^"\']*)["\']\s*\)')
# custom line:    @jce.h(method = "DELETE", path = "/api/store/edith/sc", hasBody = x)
LN_H_RE = re.compile(r'^\s*@jce\.h\s*\(\s*method\s*=\s*"([^"]+)"\s*,\s*path\s*=\s*"([^"]*)"\s*[,)]')
# method entry that references a constant path: @jce.f(k9b.a) or @jce.h(hasBody=..., method=.., path=CONST)
LN_CONST_RE = re.compile(r'^\s*@jce\.([fopbgnm])\s*\(\s*([\w.]+)\s*\)')
# param annotation: @jce.t("oid")  or  @jce.t(com.xingin.SomeConst.KEY)  or @jce.a (body, no arg)
PARAM_RE = re.compile(r'@jce\.([a-z])\s*(?:\(([^)]*)\))?')
# method name:  io.reactivex.Observable<...> methodName(...)
METH_NAME_RE = re.compile(r'([\w<>.,?\[\] ]+?)\s+(\w+)\s*\(')

CONST_KEY_VALUE_RE = re.compile(
    r'(?:public\s+static\s+final\s+|static\s+final\s+)?String\s+(\w+)\s*=\s*["\']([^"\']*)["\']')

# Stop at either interface method end ( ");" ) or implementation method end ( ") {" ).
STOP_SEMI_RE = re.compile(r'\)\s*;\s*(?://.*)?$')
STOP_BODY_RE = re.compile(r'\)\s*\{')


def resolve_const(consts, token):
    """token like com.xingin.capa.idle.CapaStandaloneImagePublisherImpl.KEY_STATUS"""
    parts = token.split('.')
    return consts.get(parts[-1], token)


def parse_params(params_raw, consts):
    """params_raw is the source text between (...) of a single method (may span lines)."""
    if not params_raw.strip():
        return []
    out = []
    # capture each @jce.X(...) occurrence in order with preceding type text
    for m in PARAM_RE.finditer(params_raw):
        ann_letter = m.group(1)
        ann_arg = m.group(2)
        key = ""
        if ann_arg:
            km = re.search(r'["\']([^"\']*)["\']', ann_arg)
            if km:
                key = km.group(1)
            else:
                key = resolve_const(consts, ann_arg.strip())
        # find type+name: text between previous annotation end and this one
        end = m.end()
        next_pos = params_raw.find('@', end)
        seg = params_raw[end:next_pos] if next_pos != -1 else params_raw[end:]
        # seg looks like ' java.lang.String str2,' or ' int i92,' ; but between js could contain
        seg = seg.strip().rstrip(',').strip()
        tm = re.match(r'(.+?)\s+(\w+)$', seg)
        ptype = tm.group(1).strip() if tm else seg
        pname = tm.group(2) if tm else ""
        # collapse whitespace in type
        ptype = re.sub(r'\s+', ' ', ptype)
        out.append({'anno': PARAM_ANN.get(ann_letter, ann_letter),
                    'key': key, 'type': ptype, 'name': pname})
    # Body without annotation? @jce.a has no key; verify Body params are @jce.a
    return out


def process_file(rel):
    fp = os.path.join(SOURCES, rel)
    with open(fp, encoding='utf-8', errors='replace') as fh:
        text = fh.read()
    pack_m = re.search(r'package\s+([\w.]+);', text)
    cls_m = re.search(r'(?:public\s+)?(?:interface|class)\s+(\w+)', text)
    package = pack_m.group(1) if pack_m else ""
    classname = cls_m.group(1) if cls_m else ""
    # collect constants: static final String x = "path"   (path constants)
    consts = {}
    for cm in CONST_KEY_VALUE_RE.finditer(text):
        consts[cm.group(1)] = cm.group(2)

    lines = text.split('\n')
    methods = []
    i = 0
    n = len(lines)
    pending_form = False
    pending_multipart = False
    while i < n:
        line = lines[i]
        if '@jce.e' in line and not LN_METHOD_RE.match(line) and not LN_CONST_RE.match(line):
            pending_form = True
        if '@jce.l' in line and not LN_METHOD_RE.match(line):
            pending_multipart = True
        m_meth = LN_METHOD_RE.match(line)
        m_h = LN_H_RE.match(line)
        m_const = LN_CONST_RE.match(line)
        cur_path = None
        cur_meth = None
        cur_letter = None
        if m_h:
            cur_letter = 'h'
            cur_meth = m_h.group(1)
            cur_path = m_h.group(2)
        elif m_meth:
            cur_letter = m_meth.group(1)
            cur_meth = METHOD_ANN.get(cur_letter)
            cur_path = m_meth.group(2)
        elif m_const:
            # path from constant
            cur_letter = m_const.group(1)
            cur_meth = METHOD_ANN.get(cur_letter)
            tok = m_const.group(2)
            cur_path = consts.get(tok.split('.')[-1], '')
        if cur_path is None and cur_meth is None:
            i += 1
            continue
        # Accumulate signature until interface-method end ");" or impl-method body ") {".
        j = i
        sig_parts = []
        is_impl = False
        while j < n:
            sig_parts.append(lines[j])
            if STOP_SEMI_RE.search(lines[j]):
                break
            if STOP_BODY_RE.search(lines[j]):
                is_impl = True  # implementation class method: mirror of an interface method
                break
            j += 1
        # Skip implementation-class method bodies (they duplicate @jce interface defs
        # and have multi-line bodies that would corrupt parameter parsing).
        if is_impl:
            pending_form = False
            pending_multipart = False
            i = j + 1
            continue
        body = '\n'.join(sig_parts)
        # is form/multipart flagged (annotation on line before the method annotation)
        is_form = pending_form or ('@jce.e' in body)
        is_multipart = pending_multipart or ('@jce.l' in body)
        pending_form = False
        pending_multipart = False
        # method name + return type from the sig
        nm = METH_NAME_RE.search(body)
        mname = nm.group(2) if nm else '?'
        ret_type = re.sub(r'\s+', ' ', nm.group(1)).strip() if nm else ''
        if mname == '?' or mname.startswith('static'):
            i = j + 1
            continue
        # parameters: from the method-name '(' to the signature's last ')'
        if nm:
            params_start = nm.end()          # position right after method's '('
        else:
            params_start = body.find('(') + 1
        last_paren = body.rfind(')')
        params_raw = body[params_start:last_paren] if last_paren >= params_start else ""
        params = parse_params(params_raw, consts)
        # handle absolute URL @jce.x / Url
        if cur_path == '':
            has_url = any(p['anno'] == 'Url' for p in params)
            if not has_url:
                cur_path = None
        methods.append({
            'package': package, 'class': classname,
            'method': mname, 'http': cur_meth, 'path': cur_path,
            'form': is_form, 'multipart': is_multipart,
            'return_type': ret_type,
            'params': params,
        })
        i = j + 1
    return methods


def main():
    results = []
    checked = 0
    for root, dirs, files in os.walk(SOURCES):
        for fn in files:
            if not fn.endswith('.java'):
                continue
            fp = os.path.join(root, fn)
            try:
                with open(fp, encoding='utf-8', errors='replace') as fh:
                    head = fh.read(6000)
            except Exception:
                continue
            if '@jce.' not in head:
                continue
            # only files with method-level annotations
            if not re.search(r'@jce\.[fopbgnmh]\(', head):
                continue
            checked += 1
            rel = os.path.relpath(fp, SOURCES).replace('\\', '/')
            try:
                results.extend(process_file(rel))
            except Exception as e:
                sys.stderr.write(f"ERR {rel}: {e}\n")
    # dedupe by (path, http, class, method)
    seen = set()
    uniq = []
    for r in results:
        key = (r['path'], r['http'], r['class'], r['method'])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    c = Counter(r['http'] for r in uniq)
    print("checked files:", checked)
    print("TOTAL:", len(uniq))
    print("BY METHOD:", dict(c))
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'api_raw.json'), 'w', encoding='utf-8') as fh:
        json.dump(uniq, fh, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()