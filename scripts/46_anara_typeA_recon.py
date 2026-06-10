# -*- coding: utf-8 -*-
"""TYPE A recon (ANARA): найти упоминания внешних актов ПО ИМЕНИ в predprinimatel
и zemelnyy и показать их статус (залинковано/нет), точную фразу и контекст.

READ-ONLY. Ничего не пишет в _structured/_ready. Только отчёт.

Списки актов:
  - ИМЕЮТ NGR у нас (можно линковать сразу).
  - НЕТ NGR у нас (надо искать залинкованное вхождение в корпусе или → остаток).
"""
import re, sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data" / "final"

# (метка, regex по видимому тексту, NGR или None)
# regex ловит фразу-имя акта в любой падежной форме.
ACTS = [
    # имеют NGR
    ("Налоговый кодекс",        r"Налогов\w*\s+кодекс\w*",                              "K2500000214"),
    ("КоАП",                    r"административн\w*\s+правонарушени\w*",                 "K1400000235"),
    ("УПК",                     r"[Уу]головно-процессуальн\w*\s+кодекс\w*",             "K1400000231"),
    ("АППК",                    r"[Аа]дминистративн\w*\s+процедурно-процессуальн\w*\s+кодекс\w*", "K2000000350"),
    ("О недрах",                r"[Оо]\s+недрах\s+и\s+недропользовани\w*",              "K1700000125"),
    ("Экологический кодекс",    r"Экологическ\w*\s+кодекс\w*",                          "K2100000400"),
    ("Предпринимательский кодекс", r"Предпринимательск\w*\s+кодекс\w*",                 "K1500000375"),
    ("Гражданский процесс. кодекс", r"Гражданск\w*\s+процессуальн\w*\s+кодекс\w*",      None),   # отдельно: НЕТ NGR
    ("Гражданский кодекс",      r"Гражданск\w*\s+кодекс\w*",                            "K940001000_"),
    # НЕТ NGR у нас (искать в корпусе / остаток)
    ("Водный кодекс",           r"Водн\w*\s+кодекс\w*",                                 None),
    ("О здоровье народа",       r"[Оо]\s+здоровье\s+народа",                            None),
    ("О внутр. водном транспорте", r"внутренн\w*\s+водн\w*\s+транспорт\w*",             None),
    ("О торговом мореплавании", r"торгов\w*\s+мореплавани\w*",                          None),
    ("Об инвестициях",          r"[Оо]б\s+инвестици\w*",                                None),
    ("О статусе столицы",       r"статус\w*\s+столиц\w*",                               None),
]

def in_link(node):
    """вернуть ближайший предок <a href> или None."""
    p = node.parent
    while p is not None and isinstance(p, Tag):
        if p.name == "a" and p.has_attr("href"):
            return p
        p = p.parent
    return None

def article_of(node):
    p = node.parent
    while p is not None and isinstance(p, Tag):
        if p.get("data-type") == "статья":
            return p.get("data-number", "?")
        p = p.parent
    return "?"

def in_heading_or_footnote(node):
    p = node.parent
    while p is not None and isinstance(p, Tag):
        if p.name in ("h1","h2","h3","h4","h5","h6"):
            return "heading"
        cls = " ".join(p.get("class", []))
        if "footnote" in cls or "snoska" in cls or p.get("data-type") in ("сноска","примечание"):
            return "footnote"
        p = p.parent
    return None

def recon(code):
    L = []
    p = FINAL / f"{code}_structured.html"
    soup = BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser")
    rows = []
    for label, pat, ngr in ACTS:
        rx = re.compile(pat)
        for ns in soup.find_all(string=rx):
            if not isinstance(ns, NavigableString):
                continue
            s = str(ns)
            for m in rx.finditer(s):
                a = in_link(ns)
                hf = in_heading_or_footnote(ns)
                art = article_of(ns)
                ctx_l = s[max(0, m.start()-22):m.start()]
                phrase = s[m.start():m.end()]
                ctx_r = s[m.end():m.end()+22]
                rows.append((label, ngr, "LINKED" if a else "—",
                             a["href"] if a else "", hf or "", art,
                             ctx_l, phrase, ctx_r))
    # агрегаты
    L.append(f"=== {code} ===")
    from collections import Counter
    by_label_unl = Counter()
    by_label_lnk = Counter()
    for r in rows:
        label, ngr, st = r[0], r[1], r[2]
        if st == "LINKED":
            by_label_lnk[label] += 1
        else:
            by_label_unl[label] += 1
    L.append(f"  {'акт':30}{'NGR':14}{'LINKED':>7}{'UNLINKED':>9}")
    for label, pat, ngr in ACTS:
        nl = by_label_lnk.get(label, 0); nu = by_label_unl.get(label, 0)
        if nl or nu:
            L.append(f"  {label:30}{(ngr or '—'):14}{nl:>7}{nu:>9}")
    L.append("")
    L.append("  UNLINKED вхождения (кандидаты на TYPE A; hf=heading/footnote — НЕ трогать):")
    for r in rows:
        label, ngr, st, hf_href, hf, art, cl, ph, cr = r
        if st == "LINKED":
            continue
        flag = f" [{hf}]" if hf else ""
        L.append(f"    ст.{art:<6} {label:26}{flag}  «…{cl}[{ph}]{cr}…»")
    L.append("")
    L.append("  LINKED вхождения (для сверки href-конвенции):")
    seen = set()
    for r in rows:
        label, ngr, st, href, hf, art, cl, ph, cr = r
        if st != "LINKED":
            continue
        key = (label, href)
        if key in seen:
            continue
        seen.add(key)
        L.append(f"    {label:26} href={href}  «{ph}»")
    return "\n".join(L)

def main():
    out = ["TYPE A — RECON: упоминания внешних актов по имени (predprinimatel, zemelnyy)",
           "=" * 90, ""]
    for c in ["predprinimatel", "zemelnyy"]:
        out.append(recon(c))
        out.append("")
    txt = "\n".join(out) + "\n"
    (ROOT / "data/reports/46_typeA_recon.txt").write_text(txt, encoding="utf-8")
    sys.stdout.write(txt.encode("ascii", "replace").decode("ascii"))

if __name__ == "__main__":
    main()
