const fs = require('fs');
const mods = JSON.parse(fs.readFileSync('mods.json', 'utf-8'));
global.window = global;
global.document = { cookie: "" };
const cache = {};
function requireFn(id) {
  const s = String(id);
  if (cache[s]) return cache[s].exports;
  if (!mods[s]) throw new Error('module not extracted: ' + s);
  const m = (cache[s] = { exports: {} });
  const fn = new Function('module','exports','require','return (' + mods[s] + ')(module, exports, require);');
  fn(m, m.exports, requireFn);
  return m.exports;
}
requireFn.n = function(module) { return module && module.__esModule ? function(){ return module['default']; } : function() { return module; }; };
requireFn.d = function(exports, definition) { for (const k in definition) Object.defineProperty(exports, k, { enumerable: true, get: definition[k] }); };

const signerFactory = requireFn('88545').Z;

module.exports = function sign(url, { dc0, xZst81, method='GET', body }) {
  global.document.cookie = 'd_c0=' + dc0 + ';';
  return new Promise((resolve, reject) => {
    const captured = [];
    const fakeFetch = (u, o) => {
      const hdrs = {};
      (o.headers instanceof Headers ? o.headers : new Headers(o.headers || {})).forEach((v,k)=>hdrs[k]=v);
      captured.push({ url: u, headers: hdrs });
      return Promise.resolve({ ok: true, status: 200 });
    };
    const eZ = signerFactory({ headerRefs: { xZst81: xZst81 || undefined } }, {});
    const signedFetch = eZ(fakeFetch);
    signedFetch(url, { method, body }).then(() => {
      const c = captured[0];
      resolve(c ? {
        url: url,
        'x-zse-93': c.headers['x-zse-93'],
        'x-zse-96': c.headers['x-zse-96'],
        'x-zst-81': c.headers['x-zst-81'] || null,
      } : null);
    }).catch(reject);
  });
};
