# -*- coding: utf-8 -*-
"""BLOCK 4 — независимый аудит батча (из сырого HTML, мимо гейтов). Аргумент: tag
(reports/pilot/{tag}.csv). Проверяет НА СВЕЖЕМ выходе пайплайна:
  • merges «\\d+стать» (фикс A2) — должно 0;
  • prefix-defect «Закон* РК <a>"Имя"» ВНЕ спана (фикс B1/72) — должно 0;
  • nested <a>, битые #z якоря (полный фрагмент), двойной href;
  • text-invariance _ready vs _structured (ws) — DIFF = артефакт structured (см. A4);
  • счётчики: внешние root, #z внутр.
"""
import csv, io, re, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "final"
RE_MERGE = re.compile(r"\d+стать")
PREFIX = re.compile(
    r"(?:[Зз]акон(?:ом|а|е|у|ов|ами)?|[Кк]одекс(?:ом|а|е|у|ов|ами)?|"
    r"[Кк]онституционны[йм]\s+закон(?:ом|а|е)?)(?:\s+Республики\s+Казахстан|\s+РК)?\s*$")
tag = sys.argv[1] if len(sys.argv) > 1 else "batch_001"
rows = list(csv.DictReader((ROOT / "reports" / "pilot" / f"{tag}.csv").open(encoding="utf-8")))
slugs = [r["slug"] for r in rows if r["status"] in ("DONE", "UNDER_CHUNK")]


def nows(s):
    return "".join(s.get_text().split())


tot = dict(files=0, merge=0, prefix=0, nested=0, dead=0, dbl=0, ext=0, zint=0, tdiff=0)
bad = []
for s in slugs:
    p = FINAL / f"{s}_ready.html"
    if not p.exists():
        continue
    soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
    for t in soup.find_all(["script", "style"]):
        t.decompose()
    ids = {t.get("id") for t in soup.find_all(attrs={"id": True})} | \
          {t.get("name") for t in soup.find_all(attrs={"name": True})}
    merge = len(RE_MERGE.findall(soup.get_text()))
    prefix = nested = dead = ext = zint = 0
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if a.find("a"):
            nested += 1
        if h.startswith("#"):
            if h[1:] and h[1:] not in ids:
                dead += 1
        elif "/rus/docs/" in h and "#" not in h:
            ext += 1
            t = a.get_text(" ", strip=True)
            if t[:1] in '"«':
                prev = a.previous_sibling
                pv = prev if isinstance(prev, str) else (prev.get_text(" ") if prev else "")
                if PREFIX.search((pv or "").rstrip()):
                    prefix += 1
        if h.startswith("#z"):
            zint += 1
    dbl = len(re.findall(r"<a\b[^>]*\bhref=[^>]*\bhref=", str(soup)))
    sp = FINAL / f"{s}_structured.html"
    tdiff = 0
    if sp.exists():
        ss = BeautifulSoup(sp.read_text(encoding="utf-8", errors="replace"), "html.parser")
        for t in ss.find_all(["script", "style"]):
            t.decompose()
        tdiff = 0 if nows(soup) == nows(ss) else 1
    for k, v in dict(merge=merge, prefix=prefix, nested=nested, dead=dead, dbl=dbl,
                     ext=ext, zint=zint, tdiff=tdiff).items():
        tot[k] += v
    tot["files"] += 1
    if merge or prefix or nested or dead or dbl:
        bad.append((s, merge, prefix, nested, dead, dbl))

print(f"АУДИТ {tag}: {tot['files']} доков (DONE/UNDER_CHUNK)")
print(f"  merges \\d+стать (A2):        {tot['merge']}   (цель 0)")
print(f"  prefix «Закон*РК» вне спана (B1): {tot['prefix']}   (цель 0)")
print(f"  вложенных <a>:               {tot['nested']}   (цель 0)")
print(f"  битых #z якорей:             {tot['dead']}   (цель 0)")
print(f"  двойной href:                {tot['dbl']}   (цель 0)")
print(f"  внешних root-ссылок:         {tot['ext']}")
print(f"  #z внутренних:               {tot['zint']}")
print(f"  text-invariance _ready≠_structured: {tot['tdiff']} доков (артефакт structured, см. A4)")
clean = all(tot[k] == 0 for k in ("merge", "prefix", "nested", "dead", "dbl"))
print("ВЕРДИКТ:", "ЧИСТО ✅" if clean else "ЕСТЬ ЧТО РАЗОБРАТЬ ⚠")
for r in bad[:12]:
    print("   ", r)
