# -*- coding: utf-8 -*-
"""Этап 3: влить подтверждённые name->НГР в maps/npa_mapping.json.

Ключ = ТОЧНАЯ цитируемая подстрока «Название» как в тексте _ready (03 оборачивает
ключ дословно). Для одного акта может быть несколько текст-форм (склонения слова
«Закон» снаружи, суффикс «Республики Казахстан») → несколько ключей на один НГР.

Источники подтверждённых: npa_candidates.json (реестр = adilet <title>, уже сверено)
+ npa_verified.json (fetch + <title>==имя + НЕ отменён). Перед вливанием — ещё раз
repeal-check по кэшу source/{НГР}.html (если есть): отменённый НГР НЕ вливаем (§5).
"""
import csv
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "final"
SOURCE = ROOT / "source"
REP = ROOT / "reports" / "pilot"
QUOTES = "«»\"“”„'"
RE_QUOTED = re.compile(r"[«\"][Оо][бБ]?\s[^»\"]{4,150}[»\"]")   # ловим ВЕСЬ «…» (с кавычками)


def norm_name(s):
    s = re.sub(r"\s*[-–]\s*ИПС.*$", "", s or "")
    s = re.sub(r"\s*\(([^)]*кодекс[^)]*)\)\s*$", "", s, flags=re.I)
    s = s.strip().strip(QUOTES).strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+Республики\s+Казахстан$", "", s)
    return s


def is_repealed_cached(ngr):
    p = SOURCE / f"{ngr}.html"
    if not p.exists():
        return False  # не проверить -> не блокируем (кандидаты из codes.json — активные)
    soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
    for t in soup.find_all(["script", "style"]):
        t.decompose()
    art = soup.find("article") or soup
    atext = art.get_text(" ", strip=True)
    am = re.search(r"Стать[яиею]\s+\d", atext)
    header = atext[:am.start()] if am else atext[:2000]
    return bool(re.search(r"[Уу]тратил[аио]?\s+силу", header))


def main():
    apply = "--apply" in sys.argv
    # подтверждённые name(norm) -> НГР
    ver = {}
    for fn in ("npa_candidates.json", "npa_verified.json"):
        d = json.loads((REP / fn).read_text(encoding="utf-8"))
        for name, v in d.items():
            ver.setdefault(name, v["ngr"])
    print(f"подтверждённых имён (реестр+fetch): {len(ver)}")

    # repeal-check по кэшу
    dropped = [n for n, ngr in ver.items() if is_repealed_cached(ngr)]
    for n in dropped:
        del ver[n]
    if dropped:
        print(f"отброшено repeal-check по кэшу: {len(dropped)} -> {dropped[:6]}")

    slugs = [r["slug"] for r in csv.DictReader((ROOT / "pilot" / "pilot_audit.csv").open(encoding="utf-8"))]
    new_keys = {}     # exact «…» substring -> НГР
    keyfreq = Counter()
    for s in slugs:
        p = FINAL / f"{s}_ready.html"
        if not p.exists():
            continue
        soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
        for t in soup.find_all(["script", "style"]):
            t.decompose()
        for tn in soup.find_all(string=True):
            if tn.find_parent("a"):
                continue
            for m in RE_QUOTED.finditer(str(tn)):
                exact = m.group(0)               # «Название» как в тексте (с кавычками)
                nm = norm_name(exact)
                if nm in ver:
                    new_keys[exact] = ver[nm]
                    keyfreq[exact] += 1

    print(f"ТОЧНЫХ ключей-подстрок для вливания: {len(new_keys)} "
          f"(покрывают {sum(keyfreq.values())} вхождений в 82 _ready)")

    mapping = json.loads((ROOT / "maps" / "npa_mapping.json").read_text(encoding="utf-8"))
    before = len(mapping)
    added, conflict = 0, []
    for key, ngr in new_keys.items():
        if key in mapping:
            if mapping[key].rstrip("_") != ngr.rstrip("_"):
                conflict.append((key, mapping[key], ngr))
            continue
        if apply:
            mapping[key] = ngr
        added += 1
    print(f"npa_mapping: было {before}, новых ключей {added}, конфликтов со старым {len(conflict)}")
    for k, old, new in conflict[:8]:
        print(f"  CONFLICT {k[:40]!r}: старое={old} новое={new} (НЕ трогаем старое)")
    if apply:
        (ROOT / "maps" / "npa_mapping.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"ВЛИТО -> maps/npa_mapping.json (теперь {len(mapping)} ключей)")
    else:
        print("(dry-run; --apply чтобы влить)")


if __name__ == "__main__":
    main()
