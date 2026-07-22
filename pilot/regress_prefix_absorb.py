# -*- coding: utf-8 -*-
"""Регресс поглощения префикса (BLOCK 1): применяем absorb_prefix из 72 к КОПИЯМ в
памяти (final/ не трогаем). Пруф: text-invariant (get_text sha), nested=0, дефект->0
на пилоте; на КУРИРУЕМОМ корпусе absorbed==0 (не переобёртываем корректное)."""
import io, sys, re, csv, hashlib, importlib.util
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(".")
spec = importlib.util.spec_from_file_location("m72", "scripts/pipeline/72_external_root_link.py")
m72 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m72)

PREFIX = re.compile(
    r"(?:[Зз]акон(?:ами|ам|ах|ов|ом|а|е|у|ы)?|[Кк]одекс(?:ами|ам|ах|ов|ом|а|е|у|ы)?|"
    r"[Кк]онституционны[йм]\s+закон(?:ом|а|е)?)"
    r"(?:\s+Республики\s+Казахстан|\s+РК)?\s*$")
NASTOYASH = re.compile(r"настоящ\w*\s*$", re.I)


def defects(soup):
    n = 0
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if "/rus/docs/" not in h or "#" in h:
            continue
        t = a.get_text(" ", strip=True)
        if t[:1] in '"«':
            prev = a.previous_sibling
            pv = prev if isinstance(prev, str) else (prev.get_text(" ") if prev else "")
            m = PREFIX.search((pv or "").rstrip())
            if m and not NASTOYASH.search((pv or "").rstrip()[:m.start()]):
                n += 1
    return n


def check(paths, label, expect_zero_absorb=False):
    tot_before = tot_after = tot_absorbed = 0
    bad = []
    for p in paths:
        if not p.exists():
            continue
        soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
        sha0 = hashlib.sha256(soup.get_text().encode()).hexdigest()
        before = defects(soup)
        absorbed = m72.absorb_prefix(soup)
        sha1 = hashlib.sha256(soup.get_text().encode()).hexdigest()
        nested = sum(1 for a in soup.find_all("a") if a.find_parent("a"))
        after = defects(soup)
        tot_before += before; tot_after += after; tot_absorbed += absorbed
        if sha1 != sha0 or nested or (expect_zero_absorb and absorbed):
            bad.append((p.stem[:-6], before, absorbed, after, sha1 == sha0, nested))
    print(f"{label}: файлов={len(paths)}  дефектов ДО={tot_before}  поглощено={tot_absorbed}  "
          f"дефектов ПОСЛЕ={tot_after}")
    if bad:
        print("  ПРОБЛЕМЫ (slug, before, absorbed, after, sha_ok, nested):")
        for r in bad[:12]:
            print("   ", r)
    else:
        print("  ✅ text-invariant, nested=0" + (", absorbed==0 (корпус чист)" if expect_zero_absorb else ""))


slugs = [r["slug"] for r in csv.DictReader(open("pilot/pilot_audit.csv", encoding="utf-8"))]
check([ROOT / "final" / f"{s}_ready.html" for s in slugs], "ПИЛОТ (82)")
# курируемый корпус: стандарт уже верный -> absorbed должно быть 0
corpus = ["upk", "koap", "grazhdanskiy", "nalog", "trudovoy", "ugolovniy"]
check([ROOT / "final" / f"{c}_ready.html" for c in corpus], "КОРПУС (sample)", expect_zero_absorb=True)
