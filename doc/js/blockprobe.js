const fs = require('fs');
let src = fs.readFileSync('module1514.js', 'utf-8').trim();
src = src.replace(/^\d+:/, '');
if (src.endsWith(',')) src = src.slice(0, -1);
src = src.replace('return ec},r:function(ei){',
  'return ec},r:function(ei){if(window.__BP){window.__BP.push(Array.from(ei));}');
const m = { exports: {} };
global.window = global;
const requireFn = (id) => { if (id === 74185) return {_: (x) => typeof x}; throw new Error('missing '+id); };
const fn = new Function('module','exports','require','return (' + src + ')(module, exports, require);');
fn(m, m.exports, requireFn);
const ZP = m.exports.ZP;
ZP('warmup'); ZP('warmup2');
const oldR = Math.random;
Math.random = function(){ return 0.123456789; };
const inputs = ['', 'a', 'ab', 'abc', 'hello', 'hello world', '0123456789abcdef', '0123456789abcdef0123456789abcdef'];
for (const inp of inputs) {
  window.__BP = [];
  const out = ZP(inp);
  console.log(JSON.stringify(inp), '->', out, ' blocks=', JSON.stringify(window.__BP));
}
Math.random = oldR;
