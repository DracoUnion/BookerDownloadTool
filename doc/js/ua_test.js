const fs = require('fs');
let src = fs.readFileSync('module1514.js', 'utf-8').trim();
src = src.replace(/^\d+:/, '');
if (src.endsWith(',')) src = src.slice(0, -1);
// expose __g and h
src = src.replace('var __g={x:', 'var __g={x:');
src = src.replace('};l.prototype.O=', '};if(typeof window!="undefined"){window.__gREF=__g;}l.prototype.O=');
const m = { exports: {} };
global.window = global;
const requireFn = (id) => { if (id === 74185) return {_: (x) => typeof x}; throw new Error('missing '+id); };
const fn = new Function('module','exports','require','return (' + src + ')(module, exports, require);');
fn(m, m.exports, requireFn);
const ZP = m.exports.ZP;
// Fix Math.random to a fixed value to see determinism
ZP('warmup1'); ZP('warmup2');
// Test A: fixed Math.random
const oldR = Math.random;
Math.random = function(){ return 0.123456789; };
const a1 = ZP('hello');
const a2 = ZP('hello');
Math.random = oldR;
console.log('fixed random:', a1, a2, 'same?', a1===a2);
// Test B: change navigator.userAgent
const oldUA = Object.getOwnPropertyDescriptor(Navigator.prototype, 'userAgent');
if (oldUA) {
  Object.defineProperty(Navigator.prototype, 'userAgent', { get: () => 'CHANGED_UA_XYZ' });
  Math.random = function(){ return 0.123456789; };
  const b1 = ZP('hello');
  Math.random = oldR;
  console.log('UA changed :', b1);
  console.log('UA affects output?', b1 !== a1);
  // restore
  Object.defineProperty(Navigator.prototype, 'userAgent', oldUA);
}
