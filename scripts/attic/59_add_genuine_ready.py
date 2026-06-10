# -*- coding: utf-8 -*-
"""Добавить в _ready 3 ЧИСТЫЕ канон-ссылки (only_struct), которых там нет.

Только nalog, только 3 внешних именованных акта (TYPE A): текст уникален в _ready
(подстрок=1), оборачиваем ровно один текст-узел в inner_main тем же href, что и
канон. Видимый текст не меняется (gate get_text vs backup). DRY-RUN по умолчанию.
"""
import re
import sys
import importlib.util
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
BK = ROOT / "data" / "final_backup_ANARA_FINISH"
APPLY = "--apply" in sys.argv

_spec = importlib.util.spec_from_file_location("audit_mod", ROOT / "scripts" / "audit_links_coverage.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
SELF_DOC = A.SELF_DOC

K = "https://adilet.zan.kz/rus/docs/"

# (sig в каноне, href для _ready) — текст возьмём из канон-<a>
NALOG_ADD = [
    ("/docs/K1700000125#z36", K + "K1700000125#z36"),
    ("/docs/Z040000588_#z13-1", K + "Z040000588_#z13-1"),
    ("/docs/Z1500000438#z6", K + "Z1500000438#z6"),
]


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


def inner(soup):
    return soup.find("div", class_="inner_main") or soup.body or soup


def wrap_one(soup, exact, href):
    """Обернуть ПЕРВЫЙ текст-узел в inner_main, содержащий exact (не внутри <a>)."""
    root = inner(soup)
    for node in root.find_all(string=True):
        if node.find_parent("a") is not None:
            continue
        s = str(node)
        idx = s.find(exact)
        if idx < 0:
            continue
        before, after = s[:idx], s[idx + len(exact):]
        new_a = soup.new_tag("a", href=href)
        new_a.string = exact
        parent = node.parent
        i = parent.index(node)
        node.extract()
        parent.insert(i, NavigableString(after))
        parent.insert(i, new_a)
        parent.insert(i, NavigableString(before))
        return True
    return False


def main():
    code = "nalog"
    self_doc = SELF_DOC[code]
    L = ["ДОБАВЛЕНИЕ 3 канон-ссылок в nalog_ready (only_struct, TYPE A)",
         f"режим: {'APPLY' if APPLY else 'DRY-RUN'}", "=" * 80]
    soup_s = BeautifulSoup((FINAL / f"{code}_structured.html").read_text(encoding="utf-8"), "html.parser")
    soup_r = BeautifulSoup((FINAL / f"{code}_ready.html").read_text(encoding="utf-8"), "html.parser")
    # точные тексты из канона
    canon_text = {}
    for a in soup_s.find_all("a", href=True):
        sig = norm_href(a["href"], self_doc)
        if sig in dict(NALOG_ADD):
            canon_text.setdefault(sig, a.get_text())
    ok = True
    done = 0
    for sig, href in NALOG_ADD:
        exact = canon_text.get(sig)
        if exact is None:
            L.append(f"  !! канон-текст для {sig} не найден")
            ok = False
            continue
        wrapped = wrap_one(soup_r, exact, href)
        L.append(f"  {sig:30} -> обёрнуто={wrapped}  text=«{exact[:55]}…»")
        if wrapped:
            done += 1
        else:
            ok = False
    # GATE get_text vs backup
    vis_new = BeautifulSoup(str(soup_r), "html.parser").get_text()
    vis_bk = BeautifulSoup((BK / f"{code}_ready.html").read_text(encoding="utf-8"), "html.parser").get_text()
    g1 = vis_new == vis_bk
    L.append(f"  G1 видимый текст vs бэкап: {'OK' if g1 else 'FAIL %d->%d' % (len(vis_bk), len(vis_new))}")
    if APPLY and ok and g1:
        (FINAL / f"{code}_ready.html").write_text(str(soup_r), encoding="utf-8")
        L.append(f"  записано: {code}_ready.html (добавлено {done})")
    elif APPLY:
        L.append("  НЕ записано (ok/G1 FAIL)")
    out = "\n".join(L) + "\n"
    (ROOT / "data/reports/59_add_genuine_ready.txt").write_text(out, encoding="utf-8")
    print(f"written; APPLY={APPLY}; ok={ok}; g1={g1}; done={done}")


if __name__ == "__main__":
    main()
