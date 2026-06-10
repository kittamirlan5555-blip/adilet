# -*- coding: utf-8 -*-
"""РЕКОН для ANARA RE-CHECK: для каждого ПРОБА (regex) в _structured показать,
ЗАЛИНКОВАНО ли вхождение (внутри <a>) и каким href, + сниппет.

Метод: строим карту символ-смещений по text-узлам inner_main, помечая для
каждого узла inside_a/href. Regex по склейке; для каждого матча — пересекающиеся
сегменты и их href. Так «уже залинковано» определяется точно, не на глаз.

CLI: python scripts/61_recheck_recon.py <code> [<code2> ...]
"""
import re
import sys
import importlib.util
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"

S = r"[\s ]+"  # пробелы вкл. nbsp

# ОБЩАЯ БАТАРЕЯ — внешние акты по имени + структурные секции
COMMON = [
    ("МФЦ Астана", r"международном" + S + r"финансовом" + S + r"центре"),
    ("ГПК", r"Гражданск[а-я]+" + S + r"процессуальн[а-я]+" + S + r"кодекс"),
    ("Водный кодекс", r"Водн[а-я]+" + S + r"кодекс"),
    ("О недрах", r"о" + S + r"недрах" + S + r"и" + S + r"недропользовании"),
    ("Уголовного кодекса", r"Уголовн[а-я]+" + S + r"кодекс"),
    ("УПК (по имени)", r"Уголовно-процессуальн[а-я]+" + S + r"кодекс"),
    ("Предприним. кодекс", r"Предпринимательск[а-я]+" + S + r"кодекс"),
    ("Особенной части (структ)", r"Особенн[а-я]+" + S + r"част[а-я]+"),
    ("раздела N (структ)", r"раздел[а-я]*" + S + r"\d"),
    ("параграф N (структ)", r"параграф[а-я]*" + S + r"\d"),
]

EXTRA = {
    "upk": [
        ("УК ст.3 (ПРИОРИТЕТ)", r"стат[а-я]+" + S + r"3" + S + r"Уголовного" + S + r"кодекса"),
    ],
}
PROBES = {c: COMMON + EXTRA.get(c, []) for c in
          ["koap", "upk", "predprinimatel", "byudzhet", "nalog", "grazhdanskiy"]}


def inner(soup):
    return soup.find("div", class_="inner_main") or soup.body or soup


def build_map(root):
    segs = []  # (start, end, inside_a, href)
    buf = []
    pos = 0
    for node in root.find_all(string=True):
        s = str(node)
        if not s:
            continue
        a = node.find_parent("a")
        href = a.get("href") if a is not None else None
        segs.append((pos, pos + len(s), a is not None, href))
        buf.append(s)
        pos += len(s)
    return "".join(buf), segs


def hrefs_at(segs, lo, hi):
    """href-ы сегментов, пересекающих [lo,hi)."""
    inside = set()
    hh = set()
    for (s, e, ina, href) in segs:
        if e <= lo or s >= hi:
            continue
        inside.add(ina)
        if href:
            hh.add(href)
    return inside, hh


def main():
    codes = sys.argv[1:] or ["upk"]
    L = ["РЕКОН ANARA RE-CHECK — состояние флагов в _structured", "=" * 90]
    for code in codes:
        soup = BeautifulSoup((FINAL / f"{code}_structured.html").read_text(encoding="utf-8"), "html.parser")
        root = inner(soup)
        text, segs = build_map(root)
        L.append("")
        L.append(f"################### {code} ###################")
        for label, rx in PROBES.get(code, []):
            pat = re.compile(rx)
            ms = list(pat.finditer(text))
            wrapped = plain = partial = 0
            samples = []
            for m in ms:
                inside, hh = hrefs_at(segs, m.start(), m.end())
                if inside == {True}:
                    wrapped += 1
                    state = f"WRAPPED {sorted(hh)}"
                elif inside == {False}:
                    plain += 1
                    state = "PLAIN"
                else:
                    partial += 1
                    state = f"PARTIAL {sorted(hh)}"
                ctx = re.sub(r"\s+", " ", text[max(0, m.start() - 35):m.end() + 20])
                if len(samples) < 18 and not state.startswith("WRAPPED"):
                    samples.append((state, ctx))
            L.append("")
            L.append(f"  -- [{label}]  всего={len(ms)}  WRAPPED={wrapped} PLAIN={plain} PARTIAL={partial}")
            for state, ctx in samples:
                L.append(f"       {state}")
                L.append(f"         …{ctx}…")
    out = "\n".join(L) + "\n"
    rep = ROOT / "data/reports/61_recheck_recon.txt"
    rep.write_text(out, encoding="utf-8")
    print(f"written {rep.name}")


if __name__ == "__main__":
    main()
