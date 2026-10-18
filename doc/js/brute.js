const fs = require('fs');
function loadModule(file, requireFn) {
  let src = fs.readFileSync(file, 'utf-8').trim();
  src = src.replace(/^\d+:/, '');
  if (src.endsWith(',')) src = src.slice(0, -1);
  const m = { exports: {} };
  const callable = new Function('module','exports','require','return (' + src + ')(module, exports, require);');
  callable(m, m.exports, requireFn);
  return m.exports;
}
const m74185 = loadModule('module_74185.js', () => {});
const m10261 = loadModule('module_10261.js', () => {});
global.window = global;
const requireFn = (id) => { if (id === 74185) return m74185; throw new Error('missing ' + id); };
const exp1514 = loadModule('module1514.js', requireFn);
const ZP = exp1514.ZP;
const md5 = m10261;

function sig(src) { return ZP(md5(src)); }

// sample: url, expected x-zse-96
const samples = [
  ["https://www.zhihu.com/api/v4/me?include=is_realname",
   "qYwqJWSkXXsK=gyedDJNh7RI31hZVSsDDrBLIHSrfgwDC0iDTl3JTLnuhXOtaPx3"],
  ["https://www.zhihu.com/api/v4/me/switches?include=is_creator%2Coppose_right",
   "3k3AOK8cq7sAt7591NMntxOWQq4J6IssgXLdWXvoIIGadKSWR2t56V8RLNvIP5R4"],
];

const dc0_full = "23GUX1lpmhuPTnyZMrbH5UfZHvz-TQoLs7I=|1766998849";
const dc0_udid = "23GUX1lpmhuPTnyZMrbH5UfZHvz-TQoLs7I=";

function urls(u) {
  const x = new URL(u);
  const p = x.pathname;
  const q = x.search;    // "?include=..."
  const qraw = x.search.slice(1);
  const qs = x.searchParams.toString();
  return { p, q, qraw, qs };
}

let any = false;
for (const [url, expect] of samples) {
  const { p, q, qraw, qs } = urls(url);
  const cands = [];
  for (const dc of [dc0_full, dc0_udid]) {
    for (const path of [p, p+q]) {
      for (const vs of [
        ["101_3_3.0", path, dc],
        ["101_3_3.0", path, dc, ""],
        ["101_3_3.0", dc, path],
        [path, "101_3_3.0", dc],
        ["101_3_3.0", path, dc, qraw],
        ["101_3_3.0", path, qraw, dc],
        ["101_3_3.0", p, q, dc],
        ["101_3_3.0", path, "", dc],
      ]) {
        cands.push(vs.filter(Boolean).join("+"));
      }
    }
  }
  // dedupe
  const seen = new Set();
  for (const c of cands) {
    const key = c;
    if (seen.has(key)) continue;
    seen.add(key);
    const s = sig(c);
    if (s === expect) {
      console.log('!!! MATCH for', url);
      console.log('    source:', JSON.stringify(c));
      console.log('    md5:', md5(c));
      any = true;
    }
  }
  if (!any) {
    console.log('no match for', url);
  }
  any = false; // reset per sample? no—check all samples in loop
}
