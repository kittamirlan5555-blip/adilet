# -*- coding: utf-8 -*-
"""TYPE B scale: «стать*<пробел><a href="#z..">N</a>» — слово 'статья' ВНЕ ссылки,
залинкована только цифра. Считаем по всем 13 кодам в _structured и _ready (read-only).

Это ДЕТЕРМИНИРОВАННОЕ расширение существующих ссылок (href не меняется), не добивка.
"""
import re, sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data" / "final"
CODES = ["nalog","trudovoy","grazhdanskiy","grazhdanskiy_osob","predprinimatel",
         "socialnyy","ekologicheskiy","zemelnyy","upk","koap","appk","byudzhet","ugolovniy"]

BARENUM = re.compile(r"^\d+(?:-\d+)?$")
# слово 'статья' в любой форме на самом конце предшествующего текста + пробел(ы)
STAT_END = re.compile(r"(стат[ьеи][а-яё]{0,6})\s+$")

def count_code(path):
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    n = 0
    forms = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("#z"):
            continue
        if not BARENUM.match(a.get_text().strip()):
            continue
        prev = a.previous_sibling
        if not isinstance(prev, NavigableString):
            continue
        m = STAT_END.search(str(prev))
        if m:
            n += 1
            w = m.group(1).lower()
            forms[w] = forms.get(w, 0) + 1
    return n, forms

def main():
    L = []
    L.append("TYPE B — слово 'статья' вне ссылки, залинкована только цифра")
    L.append("(детерминированное расширение <a> назад на слово; href не меняется)")
    L.append("=" * 78)
    L.append(f"  {'код':20}{'_structured':>14}{'_ready':>10}")
    tot_s = tot_r = 0
    allforms = {}
    for c in CODES:
        ns, fs = count_code(FINAL / f"{c}_structured.html")
        rp = FINAL / f"{c}_ready.html"
        nr, fr = count_code(rp) if rp.exists() else (0, {})
        tot_s += ns; tot_r += nr
        for k, v in fs.items():
            allforms[k] = allforms.get(k, 0) + v
        L.append(f"  {c:20}{ns:>14}{nr:>10}")
    L.append("-" * 78)
    L.append(f"  {'ИТОГО':20}{tot_s:>14}{tot_r:>10}")
    L.append("")
    L.append("Разбивка по форме слова (по _structured):")
    for k in sorted(allforms, key=lambda x: -allforms[x]):
        L.append(f"  {k:14}{allforms[k]:>7}")
    out = "\n".join(L) + "\n"
    (ROOT / "data/reports/44_typeB_scale.txt").write_text(out, encoding="utf-8")
    sys.stdout.write(out.encode("ascii", "replace").decode("ascii"))

if __name__ == "__main__":
    main()
