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
global.window = global;
const requireFn = (id) => { if (id === 74185) return m74185; throw new Error('missing ' + id); };
const exports1514 = loadModule('module1514.js', requireFn);
const zse = global.__ZH__.zse;
const fs2 = require('fs');
// Dump full tables as JSON
const out = {
  zb: Array.from(zse.zb),
  zk: Array.from(zse.zk),
  zm: Array.from(zse.zm)
};
fs2.writeFileSync('zse_tables.json', JSON.stringify(out));
console.log('tables dumped:', out.zb.length, out.zk.length, out.zm.length);

// Test various inputs
const enc = exports1514.ZP;
for (const t of ['', 'a', 'ab', 'abc', 'abcdef', 'x2becbwdgkcwacno', '101_3_3.0+/api/v4/me', 'A'.repeat(16), 'A'.repeat(32)]) {
  console.log(JSON.stringify(t.length>20?t.slice(0,20)+'...':t), '->', enc(t));
}
// chars needing encodeURIComponent
console.log('url+space:', enc('a+b'));
console.log('percent:', enc('100%2B'));
console.log('chinese:', enc('中文'));
