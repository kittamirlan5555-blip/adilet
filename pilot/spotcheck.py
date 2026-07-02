# -*- coding: utf-8 -*-
"""
НЕЗАВИСИМЫЙ СПОТ-ЧЕК из СЫРОГО HTML (дисциплина CLAUDE.md §6) для 5 DONE-доков.
Раннер/гейт слепы к границам спанов и целям ссылок — здесь проверяем руками.

Для каждого slug (аргументы CLI), формы _ready и _structured:
  1) text-invariance : ''.join(get_text().split()) у _ready == у _structured
     (линковка двигает границы <a>, но НЕ меняет видимый текст; script/style срезаем)
  2) nested <a>      : a.find_parent('a') == 0
  3) empty href      : <a href> со значением '' или '#' == 0
  4) dangling #z     : каждый href='#zNNN' имеет цель id/name='zNNN' в файле
  5) links count     : сколько <a href> всего (живость линковки)
Печатает таблицу + итог PASS/FAIL по доку.
"""
import io
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "final"


def norm_text(soup):
    s = BeautifulSoup(str(soup), "html.parser")
    for t in s.find_all(["script", "style", "template"]):
        t.decompose()
    return "".join(s.get_text().split())


def check(slug):
    rp = FINAL / f"{slug}_ready.html"
    sp = FINAL / f"{slug}_structured.html"
    out = {"slug": slug}
    if not rp.exists():
        return {"slug": slug, "err": "нет _ready"}
    ready = BeautifulSoup(rp.read_text(encoding="utf-8", errors="replace"), "html.parser")
    # text-invariance vs structured
    if sp.exists():
        struct = BeautifulSoup(sp.read_text(encoding="utf-8", errors="replace"), "html.parser")
        tr, ts = norm_text(ready), norm_text(struct)
        out["ti"] = "OK" if tr == ts else f"DIFF Δ{len(tr)-len(ts)}"
    else:
        out["ti"] = "no _structured"
    # nested
    out["nested"] = sum(1 for a in ready.find_all("a") if a.find_parent("a"))
    # empty href — ТОЛЬКО href='' (реальный дефект). Голый href='#' = chrome-навигация
    # шаблона adilet (Избранное/Обратная связь/тел.), НЕ правовая ссылка -> отдельно.
    out["empty"] = sum(1 for a in ready.find_all("a", href=True) if a["href"].strip() == "")
    out["chrome#"] = sum(1 for a in ready.find_all("a", href=True) if a["href"].strip() == "#")
    # dangling #z
    ids = set()
    for t in ready.find_all(attrs={"id": True}):
        ids.add(t["id"])
    for t in ready.find_all(attrs={"name": True}):
        ids.add(t["name"])
    dang = 0
    for a in ready.find_all("a", href=True):
        h = a["href"].strip()
        if h.startswith("#") and len(h) > 1:
            if h[1:] not in ids:
                dang += 1
    out["dangling"] = dang
    out["links"] = len(ready.find_all("a", href=True))
    out["pass"] = (out["ti"] == "OK" and out["nested"] == 0
                   and out["empty"] == 0 and out["dangling"] == 0)
    return out


def main():
    slugs = sys.argv[1:]
    if not slugs:
        sys.exit("укажи slug'и")
    print(f"{'slug':16}{'text-inv':12}{'nested':7}{'empty':6}{'dangl':6}{'chrome#':8}{'links':7}{'ИТОГ':6}")
    print("-" * 68)
    allpass = True
    for s in slugs:
        r = check(s)
        if "err" in r:
            print(f"{s:16}{r['err']}")
            allpass = False
            continue
        verdict = "PASS" if r["pass"] else "FAIL"
        if not r["pass"]:
            allpass = False
        print(f"{s:16}{r['ti']:12}{r['nested']:<7}{r['empty']:<6}{r['dangling']:<6}"
              f"{r['chrome#']:<8}{r['links']:<7}{verdict:6}")
    print("-" * 60)
    print("ОБЩИЙ ИТОГ:", "ВСЕ PASS" if allpass else "ЕСТЬ FAIL")


if __name__ == "__main__":
    main()
