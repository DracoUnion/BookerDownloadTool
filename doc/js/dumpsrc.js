const fs = require('fs');
let src = fs.readFileSync('module1514.js', 'utf-8').trim();
src = src.replace(/^\d+:/, '');
if (src.endsWith(',')) src = src.slice(0, -1);
// instrument case 440: capture the decoded M array before parsing
src = src.replace('case 440:U=66,M=[],I=this.D[16383&this.e];for(var b=0;b<I.length;b++)M.push(String.fromCharCode(24^I.charCodeAt(b)^U)),U=24^I.charCodeAt(b)^U;M=M.join("").split("|"),O=parseInt(M.shift()),this.i.push(0===O?M.join("|"):1===O?-1!==M.join().indexOf(".")?parseInt(M.join()):parseFloat(M.join()):2===O?eval(M.join()):3===O?null:void 0),this.T-=88;break;',
  'case 440:U=66,M=[],I=this.D[16383&this.e];for(var b=0;b<I.length;b++)M.push(String.fromCharCode(24^I.charCodeAt(b)^U)),U=24^I.charCodeAt(b)^U;M=M.join("").split("|");if(window.__DMP&&M[0]==="2")window.__DMP.push(M.join("|"));O=parseInt(M.shift());this.i.push(0===O?M.join("|"):1===O?-1!==M.join().indexOf(".")?parseInt(M.join()):parseFloat(M.join()):2===O?eval(M.join()):3===O?null:void 0),this.T-=88;break;');
const m = { exports: {} };
global.window = global;
const requireFn = (id) => { if (id === 74185) return {_: (x) => typeof x}; throw new Error('missing '+id); };
const fn = new Function('module','exports','require','return (' + src + ')(module, exports, require);');
fn(m, m.exports, requireFn);
const ZP = m.exports.ZP;
window.__DMP = null; ZP('warmup'); ZP('warmup2');
window.__DMP = [];
const out = ZP('hello');
console.log('out:', out);
console.log('type-2 eval strings:');
const seen = new Set();
for (const s of window.__DMP) {
  if (!seen.has(s)) { seen.add(s); console.log(JSON.stringify(s.slice(0,150))); }
}
