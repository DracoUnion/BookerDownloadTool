const fs = require('fs');
let src = fs.readFileSync('module1514.js', 'utf-8').trim();
src = src.replace(/^\d+:/, '');
if (src.endsWith(',')) src = src.slice(0, -1);
const m = { exports: {} };
global.window = global;
const requireFn = (id) => { if (id === 74185) return {_: (x) => typeof x}; throw new Error('missing '+id); };
// proxy Date.now, and common globals used by VM: instrument via __g? 
// Instead, wrap eval'd strings: replace module's eval? We can't easily.
// Approach: patch the O method's eval cases to resolve via a registry and log property access.
// Simpler: patch Date.now to log, and patch Math/Array access via wrapping.
const origNow = Date.now;
const origMathRandom = Math.random;
Date.now = function() { if (global.__TIMELOG) global.__TIMELOG.push(Date.now_impl()); return Date.now_impl(); };
Date.now_impl = origNow;
// log window/document/navigator property access via Proxy on their common methods
function prox(name, obj) {
  return new Proxy(obj, {
    get(t, k) {
      if (global.__PROBE && typeof k === 'string') global.__PROBE.push(name+'.'+k);
      const v = Reflect.get(t, k);
      if (typeof v === 'function') {
        return function(...a) {
          if (global.__PROBE && typeof k === 'string') global.__PROBE.push(name+'.'+k+'()');
          return v.apply(t, a);
        };
      }
      return v;
    }
  });
}
global.window = global;
// replace the module globals via eval strings by patching O: we need the eval to return proxies.
// Patch the module source: in case 254 eval(i), map known names to proxies first.
src = src.replace(
  'case 254:this.C[this.c]=eval(i),',
  'case 254:this.C[this.c]=({"Date":window.__PRDate,"window":window,"document":window.__PRDoc,"navigator":window.__PRNav,"location":window.__PRLoc,"history":window.__PRHist,"screen":window.__PRScr,"Math":window.__PRMath,"Array":Array,"__g":window.__PRg}[i]!==undefined?{"Date":window.__PRDate,"window":window,"document":window.__PRDoc,"navigator":window.__PRNav,"location":window.__PRLoc,"history":window.__PRHist,"screen":window.__PRScr,"Math":window.__PRMath,"Array":Array,"__g":window.__PRg}[i]:eval(i)),'
);
const fn = new Function('module','exports','require','return (' + src + ')(module, exports, require);');
fn(m, m.exports, requireFn);
const ZP = m.exports.ZP;
// set up proxies AFTER load (eval'd references captured at runtime)
window.__PROBE = [];
window.__TIMELOG = [];
window.__PRDate = { now: function(){ window.__TIMELOG.push('Date.now'); return Date.now_impl(); } };
window.__PRDoc = prox('document', global);
window.__PRNav = prox('navigator', global);
window.__PRLoc = prox('location', global);
window.__PRHist = prox('history', global);
window.__PRScr = prox('screen', global);
window.__PRMath = prox('Math', global);
window.__PRg = global.__gDump2;  // actual __g? we don't have ref... 
// __g is module-internal. Provide our own stub that wraps real r/x if accessible.
window.__PRg = { x: function(){}, r: function(){}, _encrypt: function(){} };
ZP('warmup1'); ZP('warmup2');
window.__PROBE = []; window.__TIMELOG = [];
const out = ZP('hello');
console.log('out:', out);
console.log('PROBE accesses:', window.__PROBE.slice(0,60).join(', '));
console.log('Date.now calls:', window.__TIMELOG.length);
