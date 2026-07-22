# -*- coding: utf-8 -*-
"""Инжект синтетических якорей z{N}h в _structured НОВЫХ доков (консистентность с _ready
и старым корпусом-43). 01_build_article_map назначает z{N}h статьям с <b>Статья N.</b>
без родного якоря; батч-пайплайн инжектил их только в _ready, не в _structured →
665 chunk-якорей не резолвились в _structured и numbering-audit давал D3.

Правка: `<a id="zNh" name="zNh"></a>` в начало <b>-заголовка (пусто → text-invariant).
Как в _ready. ТОЛЬКО новые доки (старый корпус не трогаем — у него якоря уже есть)."""
import io, sys, json, os, re, hashlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(".")
june = Path(os.environ["TEMP"]) / "chunks_june_accepted_backup.jsonl"
oldset = set(json.loads(l)["code"] for l in june.read_text(encoding="utf-8").splitlines() if l.strip())
CODES = json.loads((ROOT / "maps" / "codes.json").read_text(encoding="utf-8"))
RE_TITLE = re.compile(r"^\s*Стать\w*\s+")
apply = "--apply" in sys.argv

tot_docs = tot_inj = 0
bad = []
for slug, v in CODES.items():
    if slug.startswith("_") or not isinstance(v, dict) or slug in oldset:
        continue
    stp = ROOT / "final" / f"{slug}_structured.html"
    amp = ROOT / "maps" / f"article_map_{slug}.json"
    if not (stp.exists() and amp.exists()):
        continue
    amap = json.loads(amp.read_text(encoding="utf-8"))
    synth = {str(n): a for n, a in amap.items() if str(a).endswith("h")}
    if not synth:
        continue
    html = stp.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    sha0 = hashlib.sha256("".join(soup.get_text().split()).encode()).hexdigest()
    inj = 0
    for d in soup.find_all("div", class_="article"):
        num = str(d.get("data-number"))
        anc = synth.get(num)
        if not anc:
            continue
        if soup.find(attrs={"id": anc}) or soup.find(attrs={"name": anc}):
            continue                          # уже есть
        # заголовок статьи — <h3>/<h4> (УК/ГК/…) ИЛИ <b> (налог/АППК/…); первый,
        # чей текст = «Статья N…». Инжектим якорь в НЕГО (как 07 для _ready).
        hdr = None
        for cand in d.find_all(["h3", "h4", "b"]):
            if RE_TITLE.match(cand.get_text(" ", strip=True)):
                hdr = cand
                break
        if hdr is None:
            continue
        a = soup.new_tag("a", id=anc)
        a["name"] = anc
        hdr.insert(0, a)                      # <h3|b><a id=zNh name=zNh></a>Статья N...
        inj += 1
    if inj:
        sha1 = hashlib.sha256("".join(soup.get_text().split()).encode()).hexdigest()
        nested = sum(1 for x in soup.find_all("a") if x.find_parent("a"))
        ok = sha0 == sha1 and nested == 0
        if not ok:
            bad.append((slug, sha0 == sha1, nested))
            continue
        tot_docs += 1
        tot_inj += inj
        if apply:
            stp.write_text(str(soup), encoding="utf-8")
print(f"инжектировано якорей: {tot_inj} в {tot_docs} новых доков  "
      f"({'ЗАПИСАНО' if apply else 'dry-run'})")
if bad:
    print(f"  ПРОБЛЕМЫ (text-inv/nested): {bad[:8]}")
