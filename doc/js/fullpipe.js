const fs = require('fs');
const mods = JSON.parse(fs.readFileSync('mods.json', 'utf-8'));

// ---- global setup ----
global.window = global;
global.document = { cookie: "" };
// Node 22 has Headers, atob, URL

// ---- webpack-like registry ----
const cache = {};
function requireFn(id) {
  const s = String(id);
  if (cache[s]) return cache[s].exports;
  if (!mods[s]) throw new Error('module not extracted: ' + s);
  const m = (cache[s] = { exports: {} });
  const fn = new Function('module', 'exports', 'require', 'return (' + mods[s] + ')(module, exports, require);');
  fn(m, m.exports, requireFn);
  return m.exports;
}
// webpack helper n: default export accessor
requireFn.n = function(module) {
  const getter = module && module.__esModule ? function() { return module['default']; } : function() { return module; };
  getter.a = module;
  return getter;
};
// webpack helper d: define getter exports (not strictly needed since we call fn directly)
requireFn.d = function(exports, definition) {
  for (const key in definition) {
    Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
  }
};

// ---- load the signer module 88545 ----
const signerFactory = requireFn('88545').Z;   // eZ

// Test harness: fake fetch that captures headers
function createSigner(opts) {
  const { dc0, xZst81 } = opts;
  global.document.cookie = 'd_c0=' + dc0 + ';';
  const captured = [];
  const fakeFetch = (url, options) => {
    const hdrs = {};
    const h = options.headers;
    if (h instanceof Headers) {
      h.forEach((v, k) => hdrs[k] = v);
    } else if (h && typeof h === 'object') {
      Object.assign(hdrs, h);
    }
    captured.push({ url, method: options.method || 'GET', headers: hdrs, body: options.body });
    return Promise.resolve({ ok: true, status: 200 });
  };
  const eZ = signerFactory({ appId: undefined, headerRefs: { xZst81: xZst81 || undefined } }, {});
  const signed = eZ(fakeFetch);
  return { signed, captured };
}

function compute(url, opts) {
  const { signed, captured } = createSigner(opts);
  signed(url, { method: 'GET', body: undefined }).then(() => {
    const c = captured[0];
    console.log('URL      :', url);
    console.log('x-zse-93 :', c.headers['x-zse-93']);
    console.log('x-zse-96 :', c.headers['x-zse-96']);
    console.log('x-zst-81 :', c.headers['x-zst-81'] || '(none)');
    return c;
  }).catch(e => console.log('ERR', e));
}

const dc0 = "23GUX1lpmhuPTnyZMrbH5UfZHvz-TQoLs7I=|1766998849";
const zst81 = "3_2.0aR_sn77yn6O92wOB8hPZnQr0EMYxc4f18wNBUgpTQ6nxERFZsLY0-4Lm-h3_tufIwJS8gcxTgJS_AuPZNcXCTwxI78YxEM20s4PGDwN8gGcYAupMWufIeQuK7AFpS6O1vukyQ_R0rRnsyukMGvxBEqeCiRnxEL2ZZrxmDucmqhPXnXFMTAoTF6RhRuLPFLCY_Jx06b99eCOfYBL87hVCLrOCPho8TG3BnBxfUwLfbLC99GHBZDSGTuSTv_YxJGgBfDH8FGSVcCV_Q_wLNwcMjuLCpbOBfh397JLOeQOCOCtKtuwOprH_66X0kiXKbqgOvhxMNuV_SQxVyuY9qUc1UDU8fcfKwcf_2GYYQDr_9wXmCqfzGUc1Ugu1hDgxqU21MLX01C3MYuVpXGcfjCOLQbgfIqCOACgB7UV_Zre9Ibesywt0PhwKB9N0nDxVc0eVKuwLeHcGVcSLQHg8mgV9QewqciH_Cwe8wBgC";

// Test 1: analytics batch (known captured sample)
compute('https://zhihu-web-analytics.zhihu.com/api/v3inv2/za/logs/batch', { dc0, xZst81: zst81 });
