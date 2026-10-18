const fs = require('fs');
let src = fs.readFileSync('module1514.js', 'utf-8').trim();
src = src.replace(/^\d+:/, '');
if (src.endsWith(',')) src = src.slice(0, -1);
src = src.replace(')try{switch(this.T){',
  ')try{if(typeof window!="undefined"&&window.__CS){window.__CS[this.T]=(window.__CS[this.T]||0)+1;}switch(this.T){');
const m = { exports: {} };
global.window = global;
const requireFn = (id) => { if (id === 74185) return {_: (x) => typeof x}; throw new Error('missing '+id); };
const fn = new Function('module','exports','require','return (' + src + ')(module, exports, require);');
fn(m, m.exports, requireFn);
const ZP = m.exports.ZP;
window.__CS = null;
ZP('warmup1'); ZP('warmup2');
window.__CS = {};
const out = ZP('hello');
const cases = Object.keys(window.__CS).map(Number).sort((a,b)=>a-b);
console.log('ZP(hello)=', out);
console.log('unique cases:', cases.length, cases.join(','));
// print counts sorted by case
const counts = Object.entries(window.__CS).map(([c,n])=>[+c,n]).sort((a,b)=>a[0]-b[0]);
console.log('counts:', counts.map(([c,n])=>c+':'+n).join(' '));
