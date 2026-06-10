# -*- coding: utf-8 -*-
"""МУЛЬТИМНОЖЕСТВО-ДИФФ _ready vs _structured (order-insensitive, read-only).

Скрипт 29 (difflib, ORDER-sensitive) даёт 34 — но часть из них это «парные»
одинаковые-sig элементы (один и тот же href присутствует в ОБЕИХ формах, но на
разных словах/позициях). difflib видит их как delete+insert; по существу это
не расхождение ссылок-таргетов.

Здесь считаем РАЗНИЦУ МУЛЬТИМНОЖЕСТВ sig (Counter(R)-Counter(S) и наоборот) —
хром само-сокращается, порядок не важен. Это «истинная» дивергенция таргетов.
Каждый остаток классифицируем:
  CHROME/SELF  — sig == /docs/{self_doc} (переключатель языков ҚАЗ/РУС/ENG и пр.)
  GENUINE      — канон-ссылка, которой нет в _ready (или наоборот).
"""
import re
import importlib.util
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"

_spec = importlib.util.spec_from_file_location("audit_mod", ROOT / "scripts" / "audit_links_coverage.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
SELF_DOC = A.SELF_DOC

CODES = ["nalog", "trudovoy", "grazhdanskiy", "predprinimatel", "socialnyy",
         "ekologicheskiy", "zemelnyy", "upk", "koap", "appk", "byudzhet", "ugolovniy"]


def norm_href(href, self_doc):
    h = href.strip()
    if h.startswith("#z"):
        return h
    if h.startswith("javascript") or h.startswith("mailto"):
        return None
    m = re.search(r"/docs/([A-Z]\d{6,}_?)(#z[\w-]+)?", h)
    if m:
        doc, frag = m.group(1), m.group(2) or ""
        if doc == self_doc and frag:
            return frag
        return f"/docs/{doc}{frag}"
    return None


def link_list(soup, self_doc):
    out = []
    for a in soup.find_all("a", href=True):
        sig = norm_href(a["href"], self_doc)
        if sig is None:
            continue
        txt = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        out.append((sig, txt))
    return out


def classify(sig, self_doc):
    if sig == f"/docs/{self_doc}":
        return "CHROME/SELF"
    return "GENUINE"


def main():
    L = ["МУЛЬТИМНОЖЕСТВО-ДИФФ _ready vs _structured (order-insensitive)",
         "=" * 90,
         f"  {'код':18}{'ready':>7}{'struct':>7}{'only_ready':>12}{'only_struct':>13}"
         f"{'genuine':>9}{'chrome':>8}"]
    tot_or = tot_os = tot_gen = tot_chr = 0
    detail = []
    for code in CODES:
        self_doc = SELF_DOC.get(code, "")
        soup_r = BeautifulSoup((FINAL / f"{code}_ready.html").read_text(encoding="utf-8"), "html.parser")
        soup_s = BeautifulSoup((FINAL / f"{code}_structured.html").read_text(encoding="utf-8"), "html.parser")
        R = link_list(soup_r, self_doc)
        S = link_list(soup_s, self_doc)
        cR = Counter(s for s, _ in R)
        cS = Counter(s for s, _ in S)
        only_r = cR - cS   # sig-избыток в _ready
        only_s = cS - cR   # sig-избыток в _structured (канон)
        nr = sum(only_r.values())
        ns = sum(only_s.values())
        # текст-примеры
        txtR = {}
        for s, t in R:
            txtR.setdefault(s, t)
        txtS = {}
        for s, t in S:
            txtS.setdefault(s, t)
        gen = chr_ = 0
        items = []
        for sig, n in sorted(only_r.items()):
            kind = classify(sig, self_doc)
            if kind == "GENUINE":
                gen += n
            else:
                chr_ += n
            items.append(("ONLY_READY ", sig, n, kind, txtR.get(sig, "")))
        for sig, n in sorted(only_s.items()):
            kind = classify(sig, self_doc)
            if kind == "GENUINE":
                gen += n
            else:
                chr_ += n
            items.append(("ONLY_STRUCT", sig, n, kind, txtS.get(sig, "")))
        L.append(f"  {code:18}{len(R):>7}{len(S):>7}{nr:>12}{ns:>13}{gen:>9}{chr_:>8}")
        tot_or += nr
        tot_os += ns
        tot_gen += gen
        tot_chr += chr_
        if items:
            detail.append((code, items))
    L.append("-" * 90)
    L.append(f"  {'ИТОГО':18}{'':>7}{'':>7}{tot_or:>12}{tot_os:>13}{tot_gen:>9}{tot_chr:>8}")
    L.append("")
    L.append(f"ИСТИННАЯ дивергенция (мультимножество sig): only_ready={tot_or} only_struct={tot_os}"
             f"  | GENUINE={tot_gen} CHROME/SELF={tot_chr}")
    L.append("")
    L.append("ДЕТАЛИ остатка (по мультимножеству):")
    for code, items in detail:
        L.append(f"  ### {code}")
        for side, sig, n, kind, txt in items:
            t = (txt[:60] + "…") if len(txt) > 60 else txt
            L.append(f"      {side} x{n}  {kind:11} {sig!r}  «{t}»")
    out = "\n".join(L) + "\n"
    (ROOT / "data/reports/57_multiset_residual.txt").write_text(out, encoding="utf-8")
    print("written 57_multiset_residual.txt")


if __name__ == "__main__":
    main()
