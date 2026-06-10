# -*- coding: utf-8 -*-
"""ДЕКЛАРАТИВНЫЙ РЕКОНСАЙЛ _ready -> канон _structured (правим ТОЛЬКО _ready).

Основано на авторитетной per-sig дивергенции (скрипт «53_sigdiff»): хром
сокращается (есть в обеих формах одинаково), остаётся 53 знаковых-избытка =
43 difflib-правки. Канон (_structured) НЕ трогаем — его аудит чист.

Операции (только в пределах div.inner_main — тело документа, без хром-хедера/
футер-виджета adilet):
  RETARGET old_sig -> new_href : у первых `count` ссылок _ready с norm==old_sig
      меняем href на КАНОН-href (видимый текст не меняется). Для Налог.-ссылок,
      где канон указывает на «правильный» якорь и оборачивает + имя акта.
  UNWRAP   sig, count          : у ПОСЛЕДНИХ `count` ссылок _ready с norm==sig
      снимаем тег <a> (a.unwrap()) — текст сохраняется. Это избыточные повторы/
      пункт-якоря, которых канон НЕ держит (канон линкует первое вхождение).

Гейт: видимый текст (get_text всего документа) _ready БАЙТ-В-БАЙТ == бэкап
(final_backup_ANARA_FINISH); число затронутых ссылок совпало с планом.
DRY-RUN по умолчанию; --apply — записать.
"""
import re
import sys
import importlib.util
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
BK = ROOT / "data" / "final_backup_ANARA_FINISH"
APPLY = "--apply" in sys.argv

_spec = importlib.util.spec_from_file_location("audit_mod", ROOT / "scripts" / "audit_links_coverage.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

K = "https://adilet.zan.kz/rus/docs/"

PLAN = {
    "nalog": {
        "unwrap": {"#z7413": 1, "#z7429": 1, "#z10397": 1},
        "retarget": {},
    },
    "predprinimatel": {
        "unwrap": {"#z82": 1, "#z156": 1},
        "retarget": {},
    },
    "socialnyy": {
        "unwrap": {"#z644": 1, "#z189": 1, "#z190": 1, "#z186": 1, "#z187": 1,
                   "#z2803": 1, "#z2816": 1, "#z256_p1": 1, "#z3364": 1, "#z3366": 1},
        "retarget": {
            "/docs/K2500000214#z1941": (K + "K2500000214#z1939", 1),
            "/docs/K2500000214#z12999": (K + "K2500000214#z12998", 1),
            "/docs/K2500000214#z6907": (K + "K2500000214#z6906", 2),
            "/docs/K2500000214#z13013": (K + "K2500000214#z13008", 2),
            "#z1861": ("#z1845", 1),
        },
    },
    "upk": {
        "unwrap": {"#z192": 3, "#z5241": 1, "#z5088": 1, "#z1890": 4},
        "retarget": {},
    },
    "koap": {
        "unwrap": {"#z242": 1},
        "retarget": {},
    },
    "byudzhet": {
        "unwrap": {},
        "retarget": {"/docs/Z1500000438": (K + "Z1500000438#z1", 1)},
    },
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


def inner(soup):
    return soup.find("div", class_="inner_main") or soup.body or soup


def content_links(soup, self_doc):
    """ссылки _ready в порядке документа в пределах inner_main: (norm, a)."""
    root = inner(soup)
    out = []
    for a in root.find_all("a", href=True):
        s = norm_href(a["href"], self_doc)
        if s is None:
            continue
        out.append((s, a))
    return out


def main():
    L = ["РЕКОНСАЙЛ _ready -> канон (правим только _ready; inner_main)",
         f"режим: {'APPLY' if APPLY else 'DRY-RUN'}", "=" * 90]
    allok = True
    for code, plan in PLAN.items():
        self_doc = A.SELF_DOC.get(code, "")
        soup = BeautifulSoup((FINAL / f"{code}_ready.html").read_text(encoding="utf-8"), "html.parser")
        links = content_links(soup, self_doc)
        bysig = {}
        for s, a in links:
            bysig.setdefault(s, []).append(a)
        L.append("")
        L.append(f"### {code}")
        ok = True
        # RETARGET (первые count)
        for old, (new, cnt) in plan["retarget"].items():
            got = bysig.get(old, [])
            L.append(f"  RETARGET {old} -> {new}  план={cnt} найдено={len(got)}")
            if len(got) < cnt:
                ok = False
                L.append(f"     !! найдено меньше плана")
            if APPLY:
                for a in got[:cnt]:
                    a["href"] = new
        # UNWRAP (последние count)
        for sig, cnt in plan["unwrap"].items():
            got = bysig.get(sig, [])
            L.append(f"  UNWRAP   {sig}  план={cnt} найдено={len(got)} (снимаем последние {cnt})")
            if len(got) < cnt:
                ok = False
                L.append(f"     !! найдено меньше плана")
            if APPLY:
                for a in got[len(got) - cnt:]:
                    a.unwrap()
        # GATE видимый текст vs бэкап
        if APPLY:
            new_html = str(soup)
            vis_new = BeautifulSoup(new_html, "html.parser").get_text()
            vis_bk = BeautifulSoup((BK / f"{code}_ready.html").read_text(encoding="utf-8"), "html.parser").get_text()
            g1 = (vis_new == vis_bk)
            L.append(f"  G1 видимый текст vs бэкап: {'OK' if g1 else 'FAIL len %d->%d' % (len(vis_bk), len(vis_new))}")
            ok = ok and g1
            if g1:
                (FINAL / f"{code}_ready.html").write_text(new_html, encoding="utf-8")
                L.append(f"  записано: {code}_ready.html")
            else:
                L.append(f"  НЕ записано (G1 FAIL)")
        allok = allok and ok
    L.append("")
    L.append("ИТОГ: " + ("ОК" if allok else "ЕСТЬ ПРОБЛЕМА"))
    out = "\n".join(L) + "\n"
    (ROOT / "data/reports/54_reconcile_ready.txt").write_text(out, encoding="utf-8")
    sys.stdout.write(f"written; APPLY={APPLY}; allok={allok}\n")


if __name__ == "__main__":
    main()
