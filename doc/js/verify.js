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
const m10261 = loadModule('module_10261.js', () => {});  // md5
global.window = global;
const requireFn = (id) => {
  if (id === 74185) return m74185;
  throw new Error('missing ' + id);
};
const exp1514 = loadModule('module1514.js', requireFn);

const md5 = m10261;  // default export function
const ZP = exp1514.ZP;

function xzse96(url, dc0) {
  const u = new URL(url);
  const pathsearch = u.pathname + u.search;   // mR
  // source building per 88545: [zse93, mR, dc0, bodypart, xZst81].filter(Boolean).join("+")
  const source = ["101_3_3.0", pathsearch, dc0].filter(Boolean).join("+");
  const md5hex = md5(source);
  const sig = ZP(md5hex);
  return { source, md5hex, sig, header: "2.0_" + sig };
}

const cases = [
  ["https://www.zhihu.com/api/v4/me?include=is_realname",
   "2.0_qYwqJWSkXXsK=gyedDJNh7RI31hZVSsDDrBLIHSrfgwDC0iDTl3JTLnuhXOtaPx3"],
];

for (const [url, expected] of cases) {
  const r = xzse96(url, "23GUX1lpmhuPTnyZMrbH5UfZHvz-TQoLs7I=|1766998849");
  console.log('URL     :', url);
  console.log('source  :', r.source);
  console.log('md5     :', r.md5hex);
  console.log('sig     :', r.header);
  console.log('expected:', expected);
  console.log('MATCH   :', r.header === expected);
}
