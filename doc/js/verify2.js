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

// Sample from capture
const url = "https://zhihu-web-analytics.zhihu.com/api/v3inv2/za/logs/batch";
const expected = "2.0_QrB=A/d25/DbFd6uz59O8yeRqGA7M9CwGnAjD8UvqR3MD16MarKuqRS+1wFBNj+U";
const dc0 = "23GUX1lpmhuPTnyZMrbH5UfZHvz-TQoLs7I=|1766998849";
const zst81 = "3_2.0aR_sn77yn6O92wOB8hPZnQr0EMYxc4f18wNBUgpTQ6nxERFZsLY0-4Lm-h3_tufIwJS8gcxTgJS_AuPZNcXCTwxI78YxEM20s4PGDwN8gGcYAupMWufIeQuK7AFpS6O1vukyQ_R0rRnsyukMGvxBEqeCiRnxEL2ZZrxmDucmqhPXnXFMTAoTF6RhRuLPFLCY_Jx06b99eCOfYBL87hVCLrOCPho8TG3BnBxfUwLfbLC99GHBZDSGTuSTv_YxJGgBfDH8FGSVcCV_Q_wLNwcMjuLCpbOBfh397JLOeQOCOCtKtuwOprH_66X0kiXKbqgOvhxMNuV_SQxVyuY9qUc1UDU8fcfKwcf_2GYYQDr_9wXmCqfzGUc1Ugu1hDgxqU21MLX01C3MYuVpXGcfjCOLQbgfIqCOACgB7UV_Zre9Ibesywt0PhwKB9N0nDxVc0eVKuwLeHcGVcSLQHg8mgV9QewqciH_Cwe8wBgC";

function trySources(urlStr, dc, zst) {
  const u = new URL(urlStr);
  const p = u.pathname;          // "/api/v3inv2/za/logs/batch"
  const q = u.search;            // "" for this one
  const combos = [
    ["101_3_3.0", p+q, dc].filter(Boolean).join("+"),
    ["101_3_3.0", p+q, dc, zst].filter(Boolean).join("+"),
    ["101_3_3.0", p, dc, zst].filter(Boolean).join("+"),
    ["101_3_3.0", p, dc].filter(Boolean).join("+"),
    ["101_3_3.0", p, q, dc, zst].filter(Boolean).join("+"),
  ];
  for (const src of combos) {
    const sig = ZP(md5(src));
    const hdr = "2.0_" + sig;
    const ok = hdr === expected;
    console.log(ok ? '!!! MATCH' : '  no', JSON.stringify(src));
    console.log('    hdr:', hdr.slice(0, 60));
    if (ok) return src;
  }
  return null;
}

const m = trySources(url, dc0, zst81);
console.log('matched source:', m ? JSON.stringify(m) : 'NONE');
