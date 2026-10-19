# -*- coding: utf-8 -*-
"""小红书 Android 签名体系中可从 Java 层精确复现的部分。

注意：x-s/x-t 的核心计算位于 APK 内 VMP 保护的 libtiny.so/libxyass.so，
不是本文件中的 Python 哈希函数。要得到真实签名，必须调用原生 SDK（真机/
模拟器、Frida 或 unidbg），或继续对 native 虚拟机进行动态逆向。
"""
from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass
from typing import Mapping, Optional
from urllib.parse import quote


def device_id_from_android_id(android_id: str) -> str:
    """对应 xec.r.f(): UUID.nameUUIDFromBytes(android_id UTF-8 bytes)。

    Java 的 UUID.nameUUIDFromBytes 使用 MD5（UUID v3），并设置 RFC 4122
    version/variant 位；Python uuid.uuid3(namespace, name) 不能直接表达
    arbitrary bytes，因此这里按 Java 源码逐步实现。
    """
    raw = android_id.encode("utf-8")
    digest = bytearray(hashlib.md5(raw).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30  # version 3
    digest[8] = (digest[8] & 0x3F) | 0x80  # RFC 4122 variant
    return str(uuid.UUID(bytes=bytes(digest)))


def xor_repeat(data: bytes, key: bytes, rounds: int = 3) -> bytes:
    """对应 tiny daemon d1/c1 的循环 XOR 解密。"""
    if not key:
        raise ValueError("key must not be empty")
    out = bytearray(data)
    for _ in range(rounds):
        for i in range(len(out)):
            out[i] ^= key[i % len(key)]
    return bytes(out)


def rol8(value: int, bits: int) -> int:
    bits %= 8
    return ((value << bits) | (value >> (8 - bits))) & 0xFF


def ror8(value: int, bits: int) -> int:
    bits %= 8
    return ((value >> bits) | (value << (8 - bits))) & 0xFF


def common_params(values: Mapping[str, object]) -> str:
    """对应 q4c.a.b(): key=value&key=value，值用 Java URLEncoder 规则编码。

    调用方应按 a0b.b/fjd.e 提供实际字段；不要把这里的输出误认为 x-s。
    """
    parts = []
    for key, value in values.items():
        # quote_plus 的空格编码为 '+'，与 java.net.URLEncoder 一致。
        encoded = quote(str(value), safe="-_.!*'()", encoding="utf-8")
        parts.append(f"{key}={encoded}")
    return "&".join(parts)


def tiny_signature_input(method: str, url_host: str, path: str,
                         query: Optional[str], body: bytes = b"") -> tuple:
    """对应 y8c.f.i() 传入 native 的五个业务参数。

    这只是 native bridge 的输入装配，不是签名结果。native 方法实际形态为：
      t.a(100529502, method, host, path, query, body)
    """
    return method, url_host, path or ("/" + url_host), query or "", body


def parse_xy_tt(value: str) -> int:
    """对应 TinyTokenHelper.extractExpireTime(): 取逗号分隔值最后一段秒时间戳。"""
    return int(value.rstrip(",").split(",")[-1])


def token_valid(xy_tt: str, now: Optional[int] = None) -> bool:
    now = int(time.time()) if now is None else now
    return parse_xy_tt(xy_tt) > now


@dataclass(frozen=True)
class NativeSignatureRequest:
    method: str
    host: str
    path: str
    query: str = ""
    body: bytes = b""

    def bridge_args(self) -> tuple:
        return tiny_signature_input(self.method, self.host, self.path,
                                    self.query, self.body)


def native_signature_unavailable(_: NativeSignatureRequest) -> dict[str, str]:
    """明确拒绝伪造签名：核心算法不在可移植的 Java/Python 层。"""
    raise NotImplementedError(
        "x-s/x-t are computed by the VMP-protected native Tiny/Shield SDK; "
        "call libtiny.so/libxyass.so through a runtime hook or unidbg."
    )


if __name__ == "__main__":
    did = device_id_from_android_id("example-android-id")
    print("did:", did)
    print("common:", common_params({"platform": "android", "deviceId": did,
                                    "versionName": "0.0.0", "build": 0}))
    req = NativeSignatureRequest("GET", "edith.xiaohongshu.com",
                                "/api/sns/v6/homefeed", "cursor_score=x")
    print("native bridge args:", req.bridge_args()[:-1], "<body bytes>")
