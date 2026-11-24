#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compose QA screenshots into contact sheets for visual acceptance.

14 pages -> 2 sheets, so the whole site can be judged with 2 image reads
(media budget: <=3 per batch, <=4 cumulative).
"""
import os
import sys
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QA = os.path.join(ROOT, "site", "qa")

A = ["landing", "home", "map", "papers", "paper-detail", "algo-detail", "theory-detail"]
B = ["story-detail", "deepdive", "book", "appendix", "exam", "evolution", "summary"]


def sheet(names, out, cols=2, w=760):
    imgs = []
    for n in names:
        p = os.path.join(QA, n + ".png")
        im = Image.open(p).convert("RGB")
        h = int(im.height * w / im.width)
        imgs.append((n, im.resize((w, h), Image.LANCZOS)))
    rows = (len(imgs) + cols - 1) // cols
    cell_h = max(im.height for _, im in imgs) + 26
    canvas = Image.new("RGB", (cols * w, rows * cell_h), (250, 250, 248))
    d = ImageDraw.Draw(canvas)
    for i, (n, im) in enumerate(imgs):
        x = (i % cols) * w
        y = (i // cols) * cell_h
        canvas.paste(im, (x, y + 26))
        d.rectangle([x, y, x + w, y + 26], fill=(24, 26, 30))
        d.text((x + 8, y + 7), n, fill=(255, 255, 255))
    canvas.save(os.path.join(QA, out), quality=88)
    print(out, canvas.size, os.path.getsize(os.path.join(QA, out)) // 1024, "KB")


if __name__ == "__main__":
    sheet(A, "contact-a.jpg")
    sheet(B, "contact-b.jpg")
