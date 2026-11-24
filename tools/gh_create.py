#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a GitHub repo through github.com/new using the logged-in CDP browser.

Usage: python3 -I gh_create.py <repo> <description> [port]
Prints CREATED / REPO_EXISTS / NOT_LOGGED_IN / UNKNOWN_STATE.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gh_cdp import Page, http_json


def main():
    repo = sys.argv[1]
    desc = sys.argv[2] if len(sys.argv) > 2 else ""
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 9223

    targets = [t for t in http_json(f"http://127.0.0.1:{port}/json") if t.get("type") == "page"]
    page = Page(targets[0], port)

    page.nav("https://github.com/new")
    page.wait_load("/new", 40)
    time.sleep(3)

    if "Create a new repository" not in (page.js("document.body.innerText") or ""):
        print("NOT_LOGGED_IN:", page.js("location.href"))
        print((page.js("document.body.innerText") or "")[:300])
        sys.exit(2)

    # repository name (React input needs native setter + input event)
    page.js("""
const el = document.getElementById('repository-name-input');
if (!el) throw new Error('no name input');
const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
setter.call(el, %s);
el.dispatchEvent(new Event('input', {bubbles: true}));
'ok'
""" % json.dumps(repo))
    time.sleep(1.5)

    if desc:
        page.js("""
const el = document.getElementById('description');
if (el) {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(el, %s);
  el.dispatchEvent(new Event('input', {bubbles: true}));
}
'ok'
""" % json.dumps(desc))
        time.sleep(1)

    # force public visibility if radio present
    page.js("""
const r = document.querySelector('input[value="public"]');
if (r && !r.checked) r.click();
'ok'
""")
    time.sleep(1)

    dup = page.js("""
const el = document.getElementById('repository-name-input');
const fg = el && el.closest('.form-group, div');
fg ? fg.innerText : ''
""")
    if "already exists" in (dup or ""):
        print("REPO_EXISTS")
        sys.exit(3)

    clicked = page.js("""
const btns = [...document.querySelectorAll('button')];
const btn = btns.find(b => b.textContent.trim().startsWith('Create repository'));
if (btn) { btn.scrollIntoView({block: 'center'}); setTimeout(() => btn.click(), 300); 'clicked' } else 'nofound'
""")
    print("click:", clicked)
    time.sleep(8)
    url = page.js("location.href")
    print("after-create-url:", url)
    print("CREATED" if repo in url else "UNKNOWN_STATE")
    if repo not in url:
        print((page.js("document.body.innerText") or "")[:500])


if __name__ == "__main__":
    main()
