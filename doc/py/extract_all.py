# -*- coding: utf-8 -*-
import re, json

data = open('3964.app.cb10463d9c412aa84d0c.js', encoding='utf-8').read()
BOUND = r'(?<![0-9A-Za-z_$])'

def extract_mod(data, mid):
    m = re.search(BOUND + r'%d:function\([^)]*\)' % mid, data)
    if not m:
        return None
    s = m.start()
    header_end = m.end()
    nxt = re.search(BOUND + r'\d+:function\(', data[header_end:])
    e = header_end + nxt.start() if nxt else len(data)
    seg = data[s:e]
    seg = re.sub(r'^\d+:', '', seg)
    if seg.endswith(','):
        seg = seg[:-1]
    return seg

# Start with 88545's deps (the signer)
root = ['88545','55164','57477','71728','94009','93823','18543','62845','10261','54058','22347','1514','74185']
mods = {}
pending = list(root)
while pending:
    mid = pending.pop(0)
    if mid in mods:
        continue
    seg = extract_mod(data, int(mid))
    if seg is None:
        print('MISSING module', mid)
        continue
    mods[mid] = seg
    # find ec(NN) dependencies
    for dep in re.findall(r'\bec\((\d+)\)', seg):
        if dep not in mods and dep not in pending:
            pending.append(dep)

print('extracted', len(mods), 'modules:', sorted(mods.keys()))
json.dump(mods, open('mods.json','w',encoding='utf-8'), ensure_ascii=False)
# Log which are missing
for dep in re.findall(r'\bec\((\d+)\)', json.dumps(mods)):
    pass
