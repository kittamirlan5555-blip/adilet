# -*- coding: utf-8 -*-
"""
Сбор пула НОВЫХ материальных Z-законов с adilet (пилот-2), честно, без выдумок.

BFS по /rus/docs/{НГР} (robots-разрешено). У КАЖДОЙ скачанной страницы берём её
СОБСТВЕННЫЙ <title> (он всё равно качается ради ссылок — заголовок бесплатно) и
классифицируем. Кандидат = материальный закон, которого НЕТ ни в готовом корпусе,
ни в прошлом пилоте, и чей <title> НЕ «О внесении изменени…».

Оптимизация вежливости: если source/{НГР}.html уже на диске (прошлый пилот / этот
обход) — читаем с диска, adilet не дёргаем. Материальных-новых кандидатов сохраняем
в source/{НГР}.html (ingest потом прочтёт с диска, без повторной закачки).

Выход:
    pilot/pool_new_meta.csv   — ngr, class(subst|amend|excluded), title
    pilot/pool_new.txt        — НГР кандидатов (материальные новые)
"""
import csv
import io
import json
import os
import re
import sys
import time
from collections import deque, OrderedDict
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
SOURCE.mkdir(exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (ADILETkz pilot ingester; contact: team)"}
DOC_RE = re.compile(r"/rus/docs/([A-Z][0-9A-Za-z_]{5,})")
SLEEP = 1.2
FETCH_CAP = 900          # жёсткий потолок запросов к adilet
TARGET = 115             # столько материальных-новых кандидатов достаточно (буфер к 100)

# ── amendment detect по <title> ──
def is_amendment(title: str) -> bool:
    t = (title or "").lower()
    return "внесени" in t and ("измен" in t or "дополнен" in t)

# ── корпус + прошлый пилот -> исключить ──
codes = json.loads((ROOT / "maps" / "codes.json").read_text(encoding="utf-8"))
EXCL = set()
for k, v in codes.items():
    if k.startswith("_"):
        continue
    EXCL.add(k.rstrip("_"))
    if isinstance(v, dict) and v.get("doc_id"):
        EXCL.add(v["doc_id"].rstrip("_"))
pf = ROOT / "pilot" / "prev_slugs.txt"
if pf.exists():
    for l in pf.read_text(encoding="utf-8").splitlines():
        if l.strip():
            EXCL.add(l.strip().rstrip("_"))

def excluded(ngr: str) -> bool:
    return ngr.rstrip("_") in EXCL

# известные материальные законы как СИДЫ (реальные НГР; их cross-refs ведут на
# другие материальные акты гуще, чем страницы кодексов)
SEEDS = [
    "Z980000339_", "Z970000127_", "Z020000299_", "Z950002710_", "Z1500000434",
    "Z950002464_", "Z950002155_", "Z1500000410", "Z1600000486", "Z090000191_",
    "Z030000423_", "Z2100000047", "Z1400000213", "Z950002733_",
]


def fetch_or_cache(ngr):
    """(html, from_cache). Читает source/{ngr}.html если есть, иначе GET."""
    p = SOURCE / f"{ngr}.html"
    if p.exists():
        return p.read_text(encoding="utf-8", errors="replace"), True
    for attempt in range(1, 3):
        try:
            r = requests.get(f"https://adilet.zan.kz/rus/docs/{ngr}", headers=H, timeout=40)
            if r.status_code == 200:
                return r.text, False
            return "", False
        except requests.RequestException:
            time.sleep(2 * attempt)
    return "", False


def get_title(soup):
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    return ""


def main():
    seen = set()
    frontier = deque(SEEDS)
    meta = OrderedDict()          # ngr -> (class, title)
    cand = []                     # материальные новые
    fetches = 0

    while frontier and fetches < FETCH_CAP and len(cand) < TARGET:
        ngr = frontier.popleft()
        if ngr in seen:
            continue
        seen.add(ngr)
        on_disk = (SOURCE / f"{ngr}.html").exists()
        html, from_cache = fetch_or_cache(ngr)
        if not from_cache:
            fetches += 1
        if not html:
            if not from_cache:
                time.sleep(SLEEP)
            continue
        soup = BeautifulSoup(html, "html.parser")
        title = get_title(soup)
        # классификация текущего дока
        if excluded(ngr):
            cls = "excluded"
        elif is_amendment(title):
            cls = "amend"
        else:
            cls = "subst"
            if ngr not in meta:
                cand.append(ngr)
                # сохранить материальный-новый в source/ (ingest прочтёт с диска)
                if not on_disk:
                    (SOURCE / f"{ngr}.html").write_text(html, encoding="utf-8")
        if ngr not in meta:
            meta[ngr] = (cls, title)
        # харвест ссылок -> фронтир
        for a in soup.find_all("a", href=True):
            m = DOC_RE.search(a["href"].strip())
            if m:
                nx = m.group(1)
                if nx.startswith("Z") and nx not in seen:
                    frontier.append(nx)
        if fetches % 25 == 0 or len(cand) % 20 == 0:
            print(f"  fetches={fetches} cache_hits={len(seen)-fetches} "
                  f"| subst_new={len(cand)} | frontier={len(frontier)}")
        if not from_cache:
            time.sleep(SLEEP)

    # выгрузка
    with (ROOT / "pilot" / "pool_new_meta.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ngr", "class", "title"])
        for ngr, (cls, title) in meta.items():
            w.writerow([ngr, cls, title])
    (ROOT / "pilot" / "pool_new.txt").write_text("\n".join(cand) + "\n", encoding="utf-8")

    from collections import Counter
    cc = Counter(c for c, _ in meta.values())
    print("\n" + "=" * 60)
    print(f"страниц обработано: {len(seen)} (запросов к adilet: {fetches}, с диска: {len(seen)-fetches})")
    print(f"классы: {dict(cc)}")
    print(f"МАТЕРИАЛЬНЫХ НОВЫХ кандидатов: {len(cand)} -> pilot/pool_new.txt")


if __name__ == "__main__":
    main()
