const fs = require('fs');

function loadModule(file, requireFn) {
  let src = fs.readFileSync(file, 'utf-8').trim();
  // strip "N:" numeric prefix
  src = src.replace(/^\d+:/, '');
  // body ends with "})" or "}" plus optional trailing comma separator
  if (src.endsWith(',') ) src = src.slice(0, -1);
  // src now looks like "function(ei,eo){BODY}" or "function(__unused_webpack_module,exports,__webpack_require__){BODY}"
  const m = { exports: {} };
  // call it with module, exports, require
  const callable = new Function('module','exports','require',
    'return (' + src + ')(module, exports, require);');
  callable(m, m.exports, requireFn);
  return m.exports;
}

const m74185 = loadModule('module_74185.js', () => {});

global.window = global;
let hCaptured = null;
Object.defineProperty(global, '__ZH__', {
  configurable: true,
  get() { return this._zh; },
  set(v) { this._zh = v; hCaptured = v; }
});

const requireFn = (id) => {
  if (id === 74185) return m74185;
  throw new Error('require(' + id + ') not available: ' + new Error().stack.split('\n')[2]);
};

const exports1514 = loadModule('module1514.js', requireFn);

console.log('exports keys:', Object.keys(exports1514));
console.log('XL version:', exports1514.XL);
console.log('ZP is function:', typeof exports1514.ZP);
console.log('hCaptured keys:', hCaptured ? Object.keys(hCaptured) : 'none');
if (hCaptured) {
  for (const k of Object.keys(hCaptured)) {
    const v = hCaptured[k];
    console.log('h.' + k, Array.isArray(v) ? 'array len ' + v.length + ' first5=' + v.slice(0,5).join(',') : typeof v);
  }
}

if (typeof exports1514.ZP === 'function') {
  console.log('encrypt("hello") =', exports1514.ZP('hello'));
  console.log('encrypt("abc") =', exports1514.ZP('abc'));
  console.log('encrypt("101_3_3.0") =', exports1514.ZP('101_3_3.0'));
}
