#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Універсальний парсер HTML -> JSON зі списком камер.

Виклик:
  python3 parse_html_to_cameras.py source.html > cameras.json
"""

import sys, json, re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

if len(sys.argv) < 2:
    sys.stderr.write("Usage: python3 parse_html_to_cameras.py source.html > cameras.json\n")
    sys.exit(1)

with open(sys.argv[1], "r", encoding="utf-8", errors="ignore") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

def infer_type(u: str) -> str:
    u = (u or "").lower()
    if ".m3u8" in u: return "hls"
    if ".mp4" in u: return "mp4"
    if "mjpg" in u or "multipart/x-mixed-replace" in u: return "mjpeg"
    if any(k in u for k in ["snapshot", "jpgmulreq", "faststream", "viewer/video.jpg"]) or re.search(r"\.(jpg|jpeg|png)(\?|$)", u):
        return "jpeg_poll"
    return "mjpeg"

def clean(txt: str) -> str:
    return re.sub(r"\s+", " ", (txt or "").strip())

base = ""  # за потреби можна встановити базовий URL сторінки

candidates = []

# 1) <video> + <source>
for v in soup.find_all("video"):
    title = clean(v.get("title") or v.get("aria-label") or v.get("id") or "Camera")
    # <video src=...>
    if v.get("src"):
        url = urljoin(base, v["src"])
        candidates.append({"title": title, "url": url, "type": infer_type(url)})
    # <source src=...> всередині <video>
    for s in v.find_all("source"):
        if s.get("src"):
            url = urljoin(base, s["src"])
            candidates.append({"title": title, "url": url, "type": infer_type(url)})

# 2) <img> з потоками MJPEG / snapshot
for img in soup.find_all("img"):
    src = img.get("src")
    if not src: 
        continue
    url = urljoin(base, src)
    low = url.lower()
    if any(k in low for k in ["mjpg", "faststream", "snapshot", "jpgmulreq", "viewer/video.jpg"]) or re.search(r"\.(jpg|jpeg|png)(\?|$)", low):
        # назву беремо з alt/title або з контексту посилання
        title = clean(img.get("alt") or img.get("title"))
        if not title:
            parent_a = img.find_parent("a")
            if parent_a and parent_a.get("title"):
                title = clean(parent_a["title"])
        if not title:
            title = "Camera"
        candidates.append({"title": title, "url": url, "type": infer_type(url)})

# 3) Плитки/картки (генерично): шукаємо <img> усередині будь-яких блоків, що виглядають як прев’ю
for box in soup.find_all(True, class_=re.compile(r"(thumb|card|preview|item)", re.I)):
    img = box.find("img")
    if img and img.get("src"):
        url = urljoin(base, img["src"])
        title = "Camera"
        # шукаємо підпис усередині блока
        cap = box.find(True, class_=re.compile(r"(caption|title|label|name)", re.I))
        if cap:
            title = clean(cap.get_text())
        else:
            title = clean(img.get("alt") or img.get("title") or title)
        candidates.append({"title": title or "Camera", "url": url, "type": infer_type(url)})

# унікалізація за URL
unique = {}
for item in candidates:
    u = item["url"]
    if not u: 
        continue
    if u not in unique:
        unique[u] = item

items = list(unique.values())

# Вивід
json.dump(items, sys.stdout, ensure_ascii=False, indent=2)
