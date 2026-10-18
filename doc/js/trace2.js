const fs = require('fs');
let src = fs.readFileSync('module1514.js', 'utf-8').trim();
src = src.replace(/^\d+:/, '');
if (src.endsWith(',')) src = src.slice(0, -1);
// trace with more detail on x
src = src.replace('x:function(ei,eo){', 'x:function(ei,eo){if(typeof window!="undefined"&&window.__TRACE){window.__TRACE.push({op:"x",in:(typeof ei==="string"?Array.from(ei).map(c=>c.charCodeAt(0)):Array.from(ei||[])),key:Array.from(eo)});}');
src = src.replace('r:function(ei){', 'r:function(ei){if(typeof window!="undefined"&&window.__TRACE){window.__TRACE.push({op:"r",in:Array.from(ei)});}');
const m = { exports: {} };
global.window = global;
const requireFn = (id) => { if (id === 74185) return {_: (x) => typeof x}; throw new Error('missing '+id); };
const fn = new Function('module','exports','require','return (' + src + ')(module, exports, require);');
fn(m, m.exports, requireFn);
const ZP = m.exports.ZP;
// warm up without trace
window.__TRACE = null; ZP('warmup');
window.__TRACE = [];
const out = ZP('hello');
console.log('ZP(hello) =', out);
for (const t of window.__TRACE) {
  console.log(t.op, 'in=', JSON.stringify(t.in), 'key=', t.key ? JSON.stringify(t.key) : '');
}
