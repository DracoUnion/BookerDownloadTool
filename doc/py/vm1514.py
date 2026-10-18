# -*- coding: utf-8 -*-
"""
Zhihu x-zse-93/x-zse-96/x-zst-81 签名算法的核心加密器（模块 1514 VM）Python 移植。
"""
import json
import math
import random
import time
import os
from urllib.parse import quote

_VM_COUNT = None

_VM_DEBUG = None

# ---------------- JS 语义辅助 ----------------

_NAN = float('nan')


def _tonum(x):
    """JS ToNumber 近似：数值保留，布尔转 0/1，None/对象/无法解析串 -> NaN。"""
    if x is None:
        return _NAN
    if isinstance(x, bool):
        return 1 if x else 0
    if isinstance(x, (int, float)):
        return x
    if isinstance(x, str):
        try:
            if x == '':
                return _NAN
            return float(x)
        except ValueError:
            return _NAN
    return _NAN


def _is_numeric(x):
    return isinstance(x, (int, float)) and not (isinstance(x, float) and math.isnan(x))


def to_i32(x):
    """JS ToInt32: 取模 2^32 后转有符号。非数值 -> 0。"""
    x = _tonum(x)
    if isinstance(x, float) and math.isnan(x):
        return 0
    x = int(x)
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x >= 0x80000000 else x


def u32(x):
    return int(x) & 0xFFFFFFFF


def srl(a, b):
    """JS >>> 无符号右移。"""
    a = to_i32(a)
    b = to_i32(b) & 31
    return u32(a) >> b


def sra(a, b):
    """JS >> 有符号右移（算术）。"""
    a = to_i32(a)
    b = to_i32(b) & 31
    return a >> b


def sl(a, b):
    """JS << 左移。"""
    a = to_i32(a)
    b = to_i32(b) & 31
    return to_i32(u32(a) << b)


def js_div(a, b):
    """JS / 浮点除法。"""
    a = _tonum(a)
    b = _tonum(b)
    if b == 0:
        if isinstance(b, float) and math.isnan(b):
            return _NAN
        return float('inf') if (math.isnan(a) or a > 0) else float('-inf')
    return a / b


def js_mod(a, b):
    """JS % 截断余数（与被除数同号）；任一为 NaN 则 NaN。"""
    a = _tonum(a)
    b = _tonum(b)
    if isinstance(a, float) and math.isnan(a):
        return _NAN
    if isinstance(b, float) and math.isnan(b):
        return _NAN
    return math.fmod(a, b)


def js_lt(a, b):   return _tonum(a) < _tonum(b)
def js_le(a, b):   return _tonum(a) <= _tonum(b)
def js_gt(a, b):   return _tonum(a) > _tonum(b)
def js_ge(a, b):   return _tonum(a) >= _tonum(b)


def js_typeof(x):
    if x is None:
        return 'undefined'
    if isinstance(x, bool):
        return 'boolean'
    if isinstance(x, (int, float)):
        return 'number'
    if isinstance(x, str):
        return 'string'
    if isinstance(x, (list, dict)):
        return 'object'
    if isinstance(x, _Obj):
        return 'object'
    if isinstance(x, (JArray,)):
        return 'object'
    return 'object'


def js_not(x):
    return not x


def js_truthy(x):
    """JS truthiness. 注意：0、''、None、NaN 为 falsy。"""
    if x is None:
        return False
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return x != 0 and not (isinstance(x, float) and math.isnan(x))
    if isinstance(x, str):
        return len(x) > 0
    return True


# ---------------- 环境对象 ----------------

class _Obj:
    """模拟 JS 普通对象（含 .constructor 等属性）。"""
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def get(self, key, default=None):
        return getattr(self, key, default)


class JArray(list):
    """JS 数组（模拟一些方法）。"""
    def __init__(self, *a):
        super().__init__(*a)

    @property
    def length(self):
        return len(self)


class JString(str):
    """JS 字符串（模拟 length 与按索引访问）。"""
    @property
    def length(self):
        return len(self)


class _Date:
    @staticmethod
    def now():
        return int(time.time() * 1000)


class _Math:
    @staticmethod
    def random():
        return random.random()

    def __getattr__(self, name):
        # Math.round / floor 等
        import builtins
        mapping = {'round': round, 'floor': math.floor, 'ceil': math.ceil,
                   'abs': abs, 'pow': math.pow, 'sqrt': math.sqrt,
                   'max': max, 'min': min, 'PI': math.pi}
        if name in mapping:
            return mapping[name]
        raise AttributeError(name)


class _Window:
    pass


class _Navigator:
    userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36'


class _Location:
    href = 'https://www.zhihu.com/'
    protocol = 'https:'
    host = 'www.zhihu.com'
    hostname = 'www.zhihu.com'
    pathname = '/'
    search = ''


class _History:
    length = 0


class _Screen:
    width = 1920
    height = 1080


class _Document:
    cookie = ''


# eval 环境：eval("Date") / eval("window") 等
ENV = {
    'Date': _Date,
    'window': _Window,
    'document': _Document,
    'navigator': _Navigator,
    'location': _Location,
    'history': _History,
    'screen': _Screen,
    'Math': _Math,
    'Array': JArray,
    # '__g' 在 init 时注入
}


# ---------------- __g 块加密（模块 1514 中的 __g.x / __g.r） ----------------

class _ZSE:
    """对应 JS 模块中的 __g 对象。zb/zk 由 VM 生成后填充。"""
    def __init__(self):
        self.zb = []      # S 盒（256 字节）
        self.zk = []      # 32 个轮密钥（32 位有符号）
        self.zm = []      # IV（16 字节）
        self._encrypt = None
        self.tables_ready = False

    def r(self, inp):
        """__g.r：16 字节 -> 16 字节（Feistel/线性变换）。"""
        # B: 大端读 4 字节
        ec = [0] * 36
        ec[0] = (inp[0] << 24) | (inp[1] << 16) | (inp[2] << 8) | inp[3]
        ec[1] = (inp[4] << 24) | (inp[5] << 16) | (inp[6] << 8) | inp[7]
        ec[2] = (inp[8] << 24) | (inp[9] << 16) | (inp[10] << 8) | inp[11]
        ec[3] = (inp[12] << 24) | (inp[13] << 16) | (inp[14] << 8) | inp[15]
        for i in range(32):
            ef = self.G(ec[i + 1] ^ ec[i + 2] ^ ec[i + 3] ^ self.zk[i])
            ec[i + 4] = to_i32(ec[i] ^ ef)
        out = [0] * 16
        self._w4(ec[35], out, 0)
        self._w4(ec[34], out, 4)
        self._w4(ec[33], out, 8)
        self._w4(ec[32], out, 12)
        return out

    @staticmethod
    def _w4(v, arr, off):
        v = to_i32(v)
        arr[off] = 255 & (v >> 24)
        arr[off + 1] = 255 & (v >> 16)
        arr[off + 2] = 255 & (v >> 8)
        arr[off + 3] = 255 & v

    def G(self, x):
        """__g.G：S 盒 + 旋转线性变换。"""
        x = to_i32(x)
        b0 = self.zb[255 & (x >> 24)]
        b1 = self.zb[255 & (x >> 16)]
        b2 = self.zb[255 & (x >> 8)]
        b3 = self.zb[255 & x]
        eu = (b0 << 24) | (b1 << 16) | (b2 << 8) | b3
        # Q: 循环左移 n 位
        def Q(v, n):
            v = u32(v)
            n &= 31
            if n == 0:
                return v
            return u32((v << n) | (v >> (32 - n)))
        eu = u32(eu)
        r = eu ^ Q(eu, 2) ^ Q(eu, 10) ^ Q(eu, 18) ^ Q(eu, 24)
        return to_i32(r)

    def x(self, ei, eo):
        """__g.x：CBC 模式块加密（ei 为字节列表，eo 为 IV/前一块密文）。"""
        ec = []
        eu = len(ei)
        ef = 0
        while eu > 0:
            ed = ei[16 * ef:16 * (ef + 1)]
            eh = [0] * 16
            for ep in range(16):
                eh[ep] = ed[ep] ^ eo[ep]
            eo = self.r(eh)
            ec.extend(eo)
            ef += 1
            eu -= 16
        return ec


# ---------------- VM（l 类） ----------------

class VM:
    def __init__(self):
        self.C = [0, 0, 0, 0]
        self.s = 0
        self.t = []      # 保存的 s（子程序调用栈）
        self.S = []      # 内存/寄存器存储数组
        self.h = []      # 保存的 S
        self.i = []      # 值栈
        self.B = []      # 保存的 i
        self.Q = False
        self.G = []      # 字节码数组
        self.D = []      # 字符串池
        self.w = 1024
        self.g = None
        self.a = int(time.time() * 1000)
        self.e = 0
        self.T = 255
        self.V = None
        self.U = lambda: int(time.time() * 1000)
        self.M = [0] * 32
        # 指令字段
        self.k = 0
        self.J = 0
        self.c = 0
        self.I = 0
        self.F = 0
        self.W = 0
        self.b = 0

    # C 寄存器数组（JS 稀疏数组）
    def _getC(self, idx):
        if idx < 0:
            return None
        if idx < len(self.C):
            return self.C[idx]
        return None

    def _setC(self, idx, val):
        while idx >= len(self.C):
            self.C.append(None)
        self.C[idx] = val

    def _getS(self, idx):
        if idx < len(self.S):
            return self.S[idx]
        return None

    def _setS(self, idx, val):
        while idx >= len(self.S):
            self.S.append(None)
        self.S[idx] = val

    def O(self, A, C, s):
        """解释器。A=字节码/程序, C=参数, s=参数。"""
        # 函数作用域局部变量（JS var 声明，跨循环迭代持久）
        loc_t = None
        loc_S = None
        loc_h = None
        loc_i = None
        loc_B = None
        loc_Q = None
        loc_G = None
        loc_D = None
        loc_w = None
        loc_g = None
        loc_a = None
        loc_e = None
        loc_E = None
        loc_T = None
        loc_r = None
        loc_V = None
        loc_U = None
        loc_M = None
        loc_O = None
        loc_c = None
        loc_I = None

        if _VM_COUNT is not None:
            self._cnt = _VM_COUNT
            self._tseq = []
            self._tseq_s = []
            self._tseq_e = []
        while self.T < self.w:
            if getattr(self, '_cnt', None) is not None:
                self._cnt[self.T] = self._cnt.get(self.T, 0) + 1
                self._tseq.append(self.T)
                self._tseq_s.append(self.s)
                self._tseq_e.append(self.e)
            try:
                T = self.T
                if T == 27:
                    self._setC(self.c, sra(self._getC(self.I), self._getC(self.F)))
                    self.M[12] = 35
                    self.T = self.T * (len(self.C) + (3 if self.M[13] else 9)) + 1
                elif T == 34:
                    self._setC(self.c, to_i32(to_i32(self._getC(self.I)) & to_i32(self._getC(self.F))))
                    self.M[12] = 35
                    self.T = self.T * (self.M[15] - 6) + 12
                elif T == 41:
                    self._setC(self.c, self._getC(self.I) <= self._getC(self.F))
                    self.T = 8 * self.T + 27
                elif T == 48:
                    self._setC(self.c, not js_truthy(self._getC(self.I)))
                    self.T = 7 * self.T + 16
                elif T == 50:
                    self._setC(self.c, to_i32(to_i32(self._getC(self.I)) | to_i32(self._getC(self.F))))
                    self.T = 6 * self.T + 52
                elif T == 57:
                    self._setC(self.c, srl(self._getC(self.I), self._getC(self.F)))
                    self.T = 7 * self.T - 47
                elif T == 64:
                    self._setC(self.c, sl(self._getC(self.I), self._getC(self.F)))
                    self.T = 5 * self.T + 32
                elif T == 71:
                    self._setC(self.c, to_i32(to_i32(self._getC(self.I)) ^ to_i32(self._getC(self.F))))
                    self.T = 6 * self.T - 74
                elif T == 78:
                    self._setC(self.c, to_i32(to_i32(self._getC(self.I)) & to_i32(self._getC(self.F))))
                    self.T = 4 * self.T + 40
                elif T == 80:
                    self._setC(self.c, self._getC(self.I) < self._getC(self.F))
                    self.T = 5 * self.T - 48
                elif T == 87:
                    self._setC(self.c, -self._getC(self.I))
                    self.T = 3 * self.T + 91
                elif T == 94:
                    self._setC(self.c, self._getC(self.I) > self._getC(self.F))
                    self.T = 4 * self.T - 24
                elif T == 101:
                    # JS in 运算符
                    k = self._getC(self.I)
                    o = self._getC(self.F)
                    self._setC(self.c, _js_in(k, o))
                    self.T = 3 * self.T + 49
                elif T == 108:
                    self._setC(self.c, js_typeof(self._getC(self.I)))
                    self.T = 2 * self.T + 136
                elif T == 110:
                    self._setC(self.c, self._getC(self.I) is not self._getC(self.F))
                    self.T += 242
                elif T == 117:
                    a = self._getC(self.I)
                    b = self._getC(self.F)
                    self._setC(self.c, a if not js_truthy(a) else b)
                    self.T = 3 * self.T + 1
                elif T == 124:
                    a = self._getC(self.I)
                    b = self._getC(self.F)
                    self._setC(self.c, a if js_truthy(a) else b)
                    self.T += 228
                elif T == 131:
                    self._setC(self.c, self._getC(self.I) >= self._getC(self.F))
                    self.T = 3 * self.T - 41
                elif T == 138:
                    self._setC(self.c, _js_loose_eq(self._getC(self.I), self._getC(self.F)))
                    self.T = 2 * self.T + 76
                elif T == 140:
                    self._setC(self.c, js_mod(self._getC(self.I), self._getC(self.F)))
                    self.T += 212
                elif T == 147:
                    self._setC(self.c, js_div(self._getC(self.I), self._getC(self.F)))
                    self.T += 205
                elif T == 154:
                    self._setC(self.c, self._getC(self.I) * self._getC(self.F))
                    self.T += 198
                elif T == 161:
                    self._setC(self.c, self._getC(self.I) - self._getC(self.F))
                    self.T += 191
                elif T == 168:
                    self._setC(self.c, _js_add(self._getC(self.I), self._getC(self.F)))
                    self.T = 2 * self.T + 16
                elif T == 254:
                    self._setC(self.c, _js_eval(loc_i))
                    self.T += 98 if 20 < self.M[11] else 89
                elif T == 255:
                    self.s = C or 0
                    self.M[26] = 52
                    self.T += 8 if self.M[13] else 6
                elif T == 258:
                    loc_g = {}
                    for F in range(self.k):
                        e = self.i.pop()
                        a = self.i.pop()
                        loc_g[a] = e
                    self._setC(self.W, loc_g)
                    self.T += 94
                elif T == 261:
                    self.D = s or []
                    self.M[11] = 68
                    self.T += 3 if self.M[26] else 5
                elif T == 264:
                    self.M[15] = 16
                    self.T = 331 if isinstance(A, str) else 336
                elif T == 266:
                    _js_set_index(self._getC(self.I), loc_i, self.i.pop())
                    self.T += 86
                elif T == 278:
                    self._setC(self.c, _js_get_index(self._getC(self.I), loc_i))
                    self.T += 63 if self.M[22] else 74
                elif T == 283:
                    self._setC(self.c, _js_eval(chr(int(self._getC(self.I)))))
                elif T == 300:
                    loc_S = self.U()
                    self.M[0] = 66
                    self.T += self.M[11]
                elif T == 331:
                    # 初始程序 base64 解码（仅 init 用；_encrypt 直接给 G/D）
                    D_ = _atob(A)
                    w = (ord(D_[0]) << 16) | (ord(D_[1]) << 8) | ord(D_[2])
                    k = 3
                    while k < w + 3:
                        self.G.append((ord(D_[k]) << 16) | (ord(D_[k + 1]) << 8) | ord(D_[k + 2]))
                        k += 3
                    loc_V = w + 3
                    while loc_V < len(D_):
                        E = (ord(D_[loc_V]) << 8) | ord(D_[loc_V + 1])
                        loc_T = D_[loc_V + 2:loc_V + 2 + E]
                        self.D.append(loc_T)
                        loc_V += E + 2
                    self.M[21] = 8
                    self.T += 21 if 1000 < loc_V else 35
                elif T == 336:
                    self.G = A
                    self.D = s
                    self.M[18] = 134
                    self.T += self.M[15]
                elif T == 344:
                    self.T = 3 * self.T - 8
                elif T == 350:
                    loc_U = 66
                    loc_M = []
                    loc_I = self.D[self.k]
                    for W in range(len(loc_I)):
                        loc_M.append(chr(24 ^ ord(loc_I[W]) ^ loc_U))
                        loc_U = 24 ^ ord(loc_I[W]) ^ loc_U
                    joined = ''.join(loc_M)
                    loc_r = int(joined.split('|')[1])
                    self._setC(self.W, self.i[len(self.i) - loc_r:])
                    self.i = self.i[:len(self.i) - loc_r]
                    self.T += 2
                elif T == 352:
                    self.e = self.G[self.s]
                    self.s += 1
                    self.T -= self.M[26]
                elif T == 360:
                    self.a = loc_S
                    self.T += self.M[0]
                elif T == 368:
                    self.T -= 24 if 500 < loc_S - self.a else 8
                elif T == 380:
                    self.i.append(16383 & self.e)
                    self.T -= 28
                elif T == 400:
                    self.i.append(self._getS(16383 & self.e))
                    self.T -= 48
                elif T == 408:
                    self.T -= 64
                elif T == 413:
                    self._setC(self.e >> 15 & 7,
                               (32767 & self.e) if ((self.e >> 18 & 1) == 0) else self._getS(32767 & self.e))
                    self.T -= 61
                elif T == 418:
                    self._setS(65535 & self.e, self._getC(self.e >> 16 & 7))
                    self.T -= 66 if (self.e >> 16) < 20 else 80
                elif T == 423:
                    self.c = self.e >> 16 & 7
                    self.I = self.e >> 13 & 7
                    self.F = self.e >> 10 & 7
                    self.J = 1023 & self.e
                    self.T -= 255 + 6 * self.J + self.J % 5
                elif T == 426:
                    self.T += 5 * (self.e >> 19) - 18
                elif T == 428:
                    self.W = self.e >> 16 & 7
                    self.k = 65535 & self.e
                    self.t.append(self.s)
                    self.h.append(self.S)
                    self.s = self._getC(self.W)
                    self.S = []
                    for J_ in range(self.k):
                        self.S.insert(0, self.i.pop())
                    self.B.append(self.i)
                    self.i = []
                    self.T -= 76
                elif T == 433:
                    self.s = self.t.pop()
                    self.S = self.h.pop()
                    self.i = self.B.pop()
                    self.T -= 81
                elif T == 438:
                    self.Q = self._getC(self.e >> 16 & 7)
                    self.T -= 86
                elif T == 440:
                    loc_U = 66
                    loc_M = []
                    loc_I = self.D[16383 & self.e]
                    for b in range(len(loc_I)):
                        loc_M.append(chr(24 ^ ord(loc_I[b]) ^ loc_U))
                        loc_U = 24 ^ ord(loc_I[b]) ^ loc_U
                    joined = ''.join(loc_M)
                    parts = joined.split('|')
                    loc_O = int(parts[0])
                    loc_M = parts[1:]
                    joined2 = '|'.join(loc_M)
                    if loc_O == 0:
                        self.i.append(joined2)
                    elif loc_O == 1:
                        self.i.append(int(joined2) if joined2.find('.') == -1 else float(joined2))
                    elif loc_O == 2:
                        self.i.append(_js_eval(joined2))
                    elif loc_O == 3:
                        self.i.append(None)
                    else:
                        self.i.append(None)
                    self.T -= 88
                elif T == 443:
                    self.b = self.e >> 2 & 65535
                    self.J = 3 & self.e
                    # JS: 0===J ? s=b : 1===J ? (Q && (s=b)) : (2===J && Q) || (s=b)
                    if self.J == 0:
                        self.s = self.b
                    elif self.J == 1:
                        if self.Q:
                            self.s = self.b
                        # else: s 保持不变
                    else:
                        # J==2：若 Q 为 true，(2===J && Q) 成立，|| 短路，s 不变
                        # 否则执行 s = this.b
                        if not (self.J == 2 and self.Q):
                            self.s = self.b
                    self.g = None
                    self.T -= 91
                elif T == 445:
                    self.i.append(self._getC(self.e >> 14 & 7))
                    self.T -= 93
                elif T == 448:
                    if self.s == 1374 and _VM_DEBUG:
                        _VM_DEBUG.append(('C448', self.s, [str(x)[:20] for x in self.C[:8]], 'isl', len(self.i)))
                    self.W = self.e >> 16 & 7
                    self.k = self.e >> 2 & 4095
                    self.J = 3 & self.e
                    loc_Q = (self.i.pop() if self.J == 1 else False)
                    loc_G = self.i[len(self.i) - self.k:len(self.i)]
                    self.i = self.i[:len(self.i) - self.k]
                    loc_c = 3 if 2 < len(loc_G) else len(loc_G)
                    self.T += 6 * self.J + 1 + 10 * loc_c
                elif T == 449:
                    self._setC(3, _js_fn(self._getC(self.W), []))
                    self.T -= 97 - len(loc_G)
                elif T == 455:
                    self._setC(3, _js_method(self._getC(self.W), loc_Q, []))
                    self.T -= 103 + len(loc_G)
                elif T == 453:
                    loc_B = self.e >> 17 & 3
                    self.T = 445 if loc_B == 0 else 380 if loc_B == 1 else 400 if loc_B == 2 else 440
                elif T == 458:
                    self.J = self.e >> 17 & 3
                    self.c = self.e >> 14 & 7
                    self.I = self.e >> 11 & 7
                    loc_i = self.i.pop()
                    self.T -= 12 * self.J + 180
                elif T == 459:
                    self._setC(3, _js_fn(self._getC(self.W), [loc_G[0]]))
                    self.T -= 100 + 7 * len(loc_G)
                elif T == 461:
                    self._setC(3, _js_new0(self._getC(self.W)))
                    self.T -= 109 - len(loc_G)
                elif T == 463:
                    loc_U = 66
                    loc_M = []
                    loc_I = self.D[65535 & self.e]
                    for n in range(len(loc_I)):
                        loc_M.append(chr(24 ^ ord(loc_I[n]) ^ loc_U))
                        loc_U = 24 ^ ord(loc_I[n]) ^ loc_U
                    joined = ''.join(loc_M)
                    parts = joined.split('|')
                    loc_O = int(parts[0])
                    loc_M = parts[1:]
                    self.T += 10 * loc_O + 3
                elif T == 465:
                    self._setC(3, _js_method(self._getC(self.W), loc_Q, [loc_G[0]]))
                    self.T -= 13 * len(loc_G) + 100
                elif T == 466:
                    self._setC(self.e >> 16 & 7, '|'.join(loc_M))
                    self.T -= 114 * len(loc_M)
                elif T == 468:
                    self.g = 65535 & self.e
                    self.T -= 116
                elif T == 469:
                    self._setC(3, _js_fn(self._getC(self.W), [loc_G[0], loc_G[1]]))
                    self.T -= 119 - len(loc_G)
                elif T == 471:
                    self._setC(3, _js_new1(self._getC(self.W), loc_G[0]))
                    self.T -= 118 + len(loc_G)
                elif T == 473:
                    raise _VMThrow(self._getC(self.e >> 16 & 7))
                elif T == 475:
                    self._setC(3, _js_method(self._getC(self.W), loc_Q, [loc_G[0], loc_G[1]]))
                    self.T -= 123
                elif T == 476:
                    joined = '|'.join(loc_M)
                    val = int(joined) if joined.find('.') == -1 else float(joined)
                    self._setC(self.e >> 16 & 7, val)
                    self.T -= 124 if self.M[21] < 10 else 126
                elif T == 478:
                    # init 专用：构造 _encrypt 闭包（本移植中由外部注入，不走此处）
                    loc_t = [0] + list(self.S)
                    self.V = 65535 & self.e
                    loc_h = self
                    self._setC(3, _encrypt_factory(loc_t, loc_h))
                    self.T -= 120 if 50 < self.M[3] else 126
                elif T == 479:
                    self._setC(3, _js_fn(self._getC(self.W), list(loc_G)))
                    self.M[3] = 168
                    self.T -= 127 if self.M[9] else 128
                elif T == 481:
                    self._setC(3, _js_new2(self._getC(self.W), loc_G[0], loc_G[1]))
                    self.T -= 10 * len(loc_G) + 109
                elif T == 483:
                    self.J = self.e >> 15 & 15
                    self.W = self.e >> 12 & 7
                    self.k = 4095 & self.e
                    self.T = 258 if self.J == 0 else 350
                elif T == 485:
                    self._setC(3, _js_method(self._getC(self.W), loc_Q, list(loc_G)))
                    self.T -= 143 if self.M[15] % 2 == 1 else 133
                elif T == 486:
                    self._setC(self.e >> 16 & 7, _js_eval('|'.join(loc_M)))
                    self.T -= self.M[18]
                elif T == 491:
                    self._setC(3, _js_new_apply(self._getC(self.W), loc_G))
                    self.T -= 139 if self.M[8] / self.M[1] < 10 else 130
                elif T == 496:
                    self._setC(self.e >> 16 & 7, None)
                    self.T -= 160 if 10 < self.M[5] - self.M[3] else 144
                elif T == 506:
                    self._setC(self.e >> 16 & 7, None)
                    self.T -= 154 if self.M[18] % self.M[12] == 1 else 145
                else:
                    self.T = self.w
            except _VMThrow:
                if self.g:
                    self.s = self.g
                self.T -= 114
            except Exception:
                if self.g:
                    self.s = self.g
                self.T -= 114
        return self.C


class _VMThrow(Exception):
    def __init__(self, val):
        super().__init__('vm throw')
        self.val = val


# ---------------- JS 运算符/方法辅助 ----------------

def _js_add(a, b):
    """JS +（字符串拼接或数值相加）。"""
    if isinstance(a, str) or isinstance(b, str):
        return _js_str(a) + _js_str(b)
    return a + b


def _js_str(x):
    if x is None:
        return 'undefined'
    if isinstance(x, bool):
        return 'true' if x else 'false'
    if isinstance(x, (int, float)):
        return str(x)
    if isinstance(x, str):
        return x
    return str(x)


def _js_loose_eq(a, b):
    # JS == 近似：数值比较 / 布尔转数值 / None==None
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if isinstance(a, bool):
        a = 1 if a else 0
    if isinstance(b, bool):
        b = 1 if b else 0
    return a == b


def _js_in(key, obj):
    """JS in：key 是 obj 的属性/索引。"""
    if isinstance(obj, (list, JArray)):
        try:
            return int(key) < len(obj)
        except Exception:
            return False
    if isinstance(obj, dict):
        return key in obj
    if isinstance(obj, str):
        return key in obj
    return False


def _js_get_index(obj, idx):
    """JS obj[i] 读取。"""
    if obj is None:
        return None
    if isinstance(obj, str):
        if isinstance(idx, (int, float)) and 0 <= int(idx) < len(obj):
            return obj[int(idx)]
        return None
    if isinstance(obj, (list, JArray)):
        if isinstance(idx, (int, float)) and 0 <= int(idx) < len(obj):
            return obj[int(idx)]
        return None
    if isinstance(obj, dict):
        return obj.get(idx)
    return getattr(obj, str(idx), None)


def _js_set_index(obj, idx, val):
    """JS obj[i] = val。"""
    if isinstance(obj, (list, JArray)):
        idx = int(idx)
        while len(obj) <= idx:
            obj.append(None)
        obj[idx] = val
    elif isinstance(obj, dict):
        obj[idx] = val
    else:
        setattr(obj, str(idx), val)


def _js_call0(fn, q=None):
    return _js_call(fn, [], q)


def _js_call1(fn, a0, q=None):
    return _js_call(fn, [a0], q)


def _js_call2(fn, a0, a1, q=None):
    return _js_call(fn, [a0, a1], q)


def _js_apply0(fn, args):
    return _js_call(fn, args)


def _js_apply1(fn, q, args):
    return _js_call(fn, args, q)


def _js_new0(cls):
    return _js_new(cls, [])


def _js_new1(cls, a0):
    return _js_new(cls, [a0])


def _js_new2(cls, a0, a1):
    return _js_new(cls, [a0, a1])


def _js_new_apply(cls, args):
    return _js_new(cls, args)


def _js_fn(fn, args):
    """JS 函数调用 fn(args)：fn 是 Python callable / _JSFn / 带 call 的对象。"""
    if fn is None:
        return None
    if isinstance(fn, _JSFn):
        return fn.call(list(args))
    if callable(fn):
        try:
            return fn(*list(args))
        except Exception:
            return None
    if hasattr(fn, 'call'):
        return fn.call(list(args))
    return None


def _js_method(obj, method, args):
    """JS 方法调用 obj[method](args)。method 为方法名字符串。"""
    if obj is None:
        return None
    mname = str(method)
    # 尝试对象属性方法（_ZSE.r / _Math.random / _Date.now 等）
    try:
        m = getattr(obj, mname)
        if callable(m):
            return m(*list(args))
    except (AttributeError, TypeError):
        pass
    # 内建类型方法（数组/字符串）走 _call_named
    if isinstance(obj, (list, JArray, str, bool, int, float, _Math, _Date)):
        return _call_named(mname, [obj] + list(args))
    return None


def _js_new(cls, args):
    if isinstance(cls, _JSFn):
        return cls.new(args)
    if cls is JArray or cls is list:
        return JArray(args)
    try:
        return cls(*args)
    except Exception:
        return None


class _JSFn:
    """JS 函数引用。name 为可调用名（在 _FUNCS 或 ENV 里解析）。"""
    def __init__(self, name):
        self.name = name

    def call(self, args, q=None):
        if self.name in _FUNCS:
            return _FUNCS[self.name](args, q)
        if self.name in ENV:
            return ENV[self.name]
        # 方法名如 'slice' 'concat' 等通过 _METHODS 处理
        return _call_named(self.name, args, q)

    def new(self, args):
        return _new_named(self.name, args)


_FUNCS = {}


def _call_named(name, args, q):
    if _VM_DEBUG and name in ('push','unshift','slice','charCodeAt','r','x','toString','indexOf'):
        obj0 = args[0] if args else None
        _VM_DEBUG.append(('CALL', name, type(obj0).__name__ if obj0 is not None else 'None', str(obj0)[:40]))

    """调用命名方法（数组/字符串方法等）。"""
    if name == 'slice' and len(args) >= 3:
        obj = args[0]
        start = int(args[1] or 0)
        end = args[2]
        if isinstance(obj, (list, JArray)):
            if end is None:
                return obj[start:]
            return obj[start:int(end)]
        if isinstance(obj, str):
            if end is None:
                return obj[start:]
            return obj[start:int(end)]
    if name == 'concat' and len(args) >= 2:
        base = args[0]
        for extra in args[1:]:
            if isinstance(base, (list, JArray)):
                base = list(base) + list(extra)
            elif isinstance(base, str):
                base = base + extra
        return base
    if name == 'charCodeAt' and len(args) >= 2:
        s = args[0]
        i = int(args[1] or 0)
        if isinstance(s, str) and 0 <= i < len(s):
            return ord(s[i])
        return float('nan')
    if name == 'fromCharCode':
        return ''.join(chr(int(x)) for x in args)
    if name == 'push':
        arr = args[0]
        for v in args[1:]:
            arr.append(v)
        return len(arr)
    if name == 'pop':
        arr = args[0]
        return arr.pop()
    if name == 'toString':
        return _js_str(args[0]) if args else 'undefined'
    if name == 'join':
        arr = args[0]
        sep = args[1] if len(args) > 1 and args[1] is not None else ','
        return sep.join(_js_str(x) for x in arr)
    if name == 'indexOf':
        arr = args[0]
        target = args[1]
        if isinstance(arr, (list, JArray)):
            for i, v in enumerate(arr):
                if v == target:
                    return i
            return -1
        if isinstance(arr, str):
            return arr.find(str(target))
        return -1
    if name == 'split':
        s = args[0]
        sep = args[1] if len(args) > 1 else ','
        return list(s.split(sep)) if sep else list(s)
    if name == 'shift':
        arr = args[0]
        return arr.pop(0) if arr else None
    if name == 'unshift':
        arr = args[0]
        arr.insert(0, args[1])
        return len(arr)
    if name == 'apply':
        fn = args[0]
        arglist = args[2] if len(args) > 2 else []
        return _js_call(fn, list(arglist))
    if name == 'call':
        fn = args[0]
        return _js_call(fn, args[2:])
    # 默认
    return None


def _new_named(name, args):
    if name == 'Array':
        return JArray(args)
    if name == 'Object':
        return _Obj()
    return None


def _js_eval(expr):
    """eval：解析环境对象引用。Node 环境下 document/location/history/screen 未定义会抛 ReferenceError，
    与模块 VM 的 eval(i) 行为一致（O 方法 catch 捕获后 T -= 114）。"""
    if expr in ('document', 'location', 'history', 'screen'):
        raise ReferenceError(expr + ' is not defined')
    if expr in ENV:
        return ENV[expr]
    if expr == '__g':
        return _G
    # 单字符 / 简单标识符：返回 None（若未定义）
    return None


def _atob(s):
    import base64
    return base64.b64decode(s).decode('latin-1')


# 全局 __g 对象（由 init 填充表）
_G = _ZSE()


def _encrypt_factory(t, h):
    """构造 _encrypt 闭包（init 用）。"""
    def enc(ei):
        eo = VM()
        eo.S = list(t)
        eo.S[0] = ei
        eo.O(h.G, h.V, h.D)
        return eo.C[3]
    return _JSFn_enc(enc)


class _JSFn_enc:
    def __init__(self, fn):
        self.fn = fn
    def call(self, args, q=None):
        return self.fn(args[0] if args else None)


def _base64_encode_urlsafe_or_std():
    import base64
    return base64.b64encode


# ---------------- 模块初始化（运行初始字节码，生成 zb/zk/zm） ----------------

_INIT_BYTECODE = None

def _load_init_bytecode():
    global _INIT_BYTECODE
    if _INIT_BYTECODE is not None:
        return _INIT_BYTECODE
    d = os.path.join(os.path.dirname(__file__), 'vm_state.json')
    state = json.load(open(d, encoding='utf-8'))
    _INIT_BYTECODE = state
    return state


def init_module():
    """从 vm_state.json 加载 G/V/D/S/t，并填充 __g 表。"""
    state = _load_init_bytecode()
    G = state['G']
    V = state['V']
    D = state['D']
    S = state['S']   # [zb, zm, key, zk]
    _G.zb = list(S[0])
    _G.zm = list(S[1])
    _G.zk = list(S[3])
    # key = S[2]（d3d2e726f50d4101）
    _G.key = list(S[2])
    ENV['__g'] = _G
    return G, V, D, S


def encrypt(ei):
    """对应模块 1514 的 ZP：_encrypt(encodeURIComponent(e))。"""
    state = _load_init_bytecode()
    G = state['G']
    V = state['V']
    D = state['D']
    t = state['t']
    eo = VM()
    eo.S = list(t)
    eo.S[0] = ei
    eo.O(G, V, D)
    return eo.C[3]


def zhihu_encrypt(s):
    """ZP 入口：encodeURIComponent(s) 后加密。"""
    return encrypt(quote(s, safe=''))
