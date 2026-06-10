# -*- coding: utf-8 -*-
"""Контекст для 10 GENUINE only_struct: где канон линкует и есть ли в _ready
такой же НЕобёрнутый спан (чтобы решить — можно ли безопасно обернуть в _ready)."""
import re
import importlib.util
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
_spec = importlib.util.spec_from_file_location("audit_mod", ROOT / "scripts" / "audit_links_coverage.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
SELF_DOC = A.SELF_DOC

# (code, canon-sig, canon-text) — из 57
TARGETS = {
    "nalog": [("#z7412", "статьи 439"),
              ("/docs/K1700000125#z36", "пункта 2-1 статьи 36"),
              ("/docs/Z040000588_#z13-1", "статьи 13-1"),
              ("/docs/Z1500000438#z6", "статьи 6")],
    "socialnyy": [("#z2278", "4)"), ("#z3263", "статьей 256"), ("#z3485", "статье 102-1")],
    "appk": [("/docs/K1500000377", "Гражданского процессуального кодекса")],
}


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


def main():
    L = ["КОНТЕКСТ 10 GENUINE only_struct (канон vs _ready)", "=" * 90]
    for code, items in TARGETS.items():
        self_doc = SELF_DOC.get(code, "")
        soup_s = BeautifulSoup((FINAL / f"{code}_structured.html").read_text(encoding="utf-8"), "html.parser")
        ready_html = (FINAL / f"{code}_ready.html").read_text(encoding="utf-8")
        ready_text = BeautifulSoup(ready_html, "html.parser").get_text()
        L.append("")
        L.append(f"### {code}")
        # все <a> канона по sig
        bysig = {}
        for a in soup_s.find_all("a", href=True):
            s = norm_href(a["href"], self_doc)
            bysig.setdefault(s, []).append(a)
        for sig, _txt in items:
            alist = bysig.get(sig, [])
            L.append(f"  -- sig={sig!r}  канон-вхождений={len(alist)}")
            for a in alist:
                atext = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
                # контекст из канона: текст родителя
                par = a.find_parent(["p", "div", "td", "li"]) or a.parent
                ctx = re.sub(r"\s+", " ", par.get_text(" ", strip=True))
                pos = ctx.find(atext)
                seg = ctx[max(0, pos - 45):pos + len(atext) + 25] if pos >= 0 else ctx[:90]
                # сколько раз этот видимый текст встречается в _ready (как подстрока)
                cnt_ready = ready_text.count(atext)
                L.append(f"       a.text=«{atext}»  в _ready-тексте подстрок={cnt_ready}")
                L.append(f"       канон-контекст: …{seg}…")
    out = "\n".join(L) + "\n"
    (ROOT / "data/reports/58_genuine_context.txt").write_text(out, encoding="utf-8")
    print("written 58_genuine_context.txt")


if __name__ == "__main__":
    main()
