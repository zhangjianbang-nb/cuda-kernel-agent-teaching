#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal CDP client (port-parameterized) for GitHub repo creation.

Reused shape from ai_workspace/ducklint/create_repo.py, but the port is a
parameter so a dedicated headful Chromium (saved GitHub-logged-in profile,
proxy 9981) can live on 9223 while other CDP browsers keep 9222.
"""
import base64
import json
import os
import socket
import struct
import time
import urllib.request


def http_json(url, timeout=10):
    req = urllib.request.Request(url)
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


class WS:
    def __init__(self, host, port, path):
        self.sock = socket.create_connection((host, port), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
               f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.sock.send(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            resp += self.sock.recv(4096)
        assert b"101" in resp.split(b"\r\n")[0], resp[:200]

    def send(self, payload):
        data = payload.encode()
        header = bytearray([0x81])
        n = len(data)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        mask = os.urandom(4)
        header += mask
        self.sock.send(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self, timeout=60):
        self.sock.settimeout(timeout)
        buf = b""
        while True:
            hdr = self._read(2)
            opcode = hdr[0] & 0x0F
            ln = hdr[1] & 0x7F
            if ln == 126:
                ln = struct.unpack(">H", self._read(2))[0]
            elif ln == 127:
                ln = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(ln)
            if opcode == 0x1:
                return (buf + payload).decode("utf-8", "replace")
            if opcode == 0x8:
                raise ConnectionError("ws closed")
            if opcode == 0x0:
                buf += payload

    def _read(self, n):
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("eof")
            data += chunk
        return data


class Page:
    def __init__(self, target, port):
        self.port = port
        ws_url = target["webSocketDebuggerUrl"]
        path = ws_url.split(str(port), 1)[1]
        self.ws = WS("127.0.0.1", port, path)
        self.mid = 0

    def call(self, method, **params):
        self.mid += 1
        msg = {"id": self.mid, "method": method}
        if params:
            msg["params"] = params
        self.ws.send(json.dumps(msg))
        deadline = time.time() + 60
        while time.time() < deadline:
            resp = json.loads(self.ws.recv())
            if resp.get("id") == self.mid:
                if "error" in resp:
                    raise RuntimeError(resp["error"])
                return resp.get("result", {})
        raise TimeoutError(method)

    def js(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, returnByValue=True,
                      awaitPromise=True)
        return r.get("result", {}).get("value")

    def nav(self, url):
        self.call("Page.navigate", url=url)

    def wait_load(self, want_sub, timeout=40):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                cur = self.js("location.href")
                if want_sub in (cur or ""):
                    time.sleep(2.0)
                    return True
            except Exception:
                pass
            time.sleep(1)
        return False
