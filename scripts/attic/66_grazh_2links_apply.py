# -*- coding: utf-8 -*-
"""ДОБИВКА 2 genuine self-рефов grazhdanskiy (обе формы) — идемпотентно.

Только +<a> вокруг существующего текста (raw-string replace, mid-paragraph,
байт-чисто). Якоря СВЕРЕНЫ через build_id_to_art:
  1) ст.150 «(статья 150 настоящего Кодекса)»  -> #z1178  (первый <p> ст.150;
     резолв body=150; у <h3> ст.150 НЕТ id, #z150 вёл бы на ст.10/11 — НЕЛЬЗЯ).
  2) ст.2   «…в ее статье 2.» («ее»=настоящая глава ГК, ст.6 Толкование) -> #z855
     (<h3 id="z855">Статья 2; #z2 вёл бы на ст.128-1 — НЕЛЬЗЯ).

Гейты: get_text(before)==get_text(after) per form; ровно 1 wrap/фикс/форму;
баланс structured==ready. Бэкап в data/final_backup_grazh_2links/.
"""
import shutil
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
BK = ROOT / "data" / "final_backup_grazh_2links"
CODE = "grazhdanskiy"

FIXES = [
    ("ст.150 -> #z1178",
     "(статья 150 настоящего Кодекса)",
     '(<a href="#z1178">статья 150</a> настоящего Кодекса)'),
    ("ст.2 -> #z855",
     "в ее статье 2.",
     'в ее <a href="#z855">статье 2</a>.'),
]


def gettext(html):
    return BeautifulSoup(html, "html.parser").get_text()


def main():
    BK.mkdir(exist_ok=True)
    L = []
    P = L.append
    P("=" * 96)
    P("ДОБИВКА 2 self-рефов grazhdanskiy — обе формы, идемпотентно, только +<a>")
    P("=" * 96)
    ok_all = True
    per_fix_counts = {lab: {} for lab, _, _ in FIXES}
    for form in ("structured", "ready"):
        fp = FINAL / f"{CODE}_{form}.html"
        before = fp.read_text(encoding="utf-8")
        # бэкап (срез ДО), не перезаписываем если уже есть
        bpath = BK / f"{CODE}_{form}.html"
        if not bpath.exists():
            shutil.copy2(fp, bpath)
        html = before
        P(f"\n[{form}]")
        for lab, old, new in FIXES:
            if new in html:
                cnt = 0
                P(f"  {lab}: уже применён (идемпотентно пропущен)")
            else:
                occ = html.count(old)
                assert occ == 1, f"{form}/{lab}: ожидалось 1 вхождение old, найдено {occ}"
                html = html.replace(old, new, 1)
                cnt = 1
                # before->after окно
                i = html.find(new)
                P(f"  {lab}: applied x1")
                P(f"     ДО : …{before[before.find(old)-30:before.find(old)+len(old)+8]}…")
                P(f"     ПОСЛЕ: …{html[i-30:i+len(new)+8]}…")
            per_fix_counts[lab][form] = cnt
        # ГЕЙТ get_text
        gt_ok = gettext(before) == gettext(html)
        ok_all = ok_all and gt_ok
        P(f"  get_text(before)==get_text(after): {'OK' if gt_ok else 'FAIL!!!'}")
        if html != before:
            fp.write_text(html, encoding="utf-8")
            P(f"  записан: {fp.name}")
        else:
            P(f"  без изменений (идемпотентно)")

    P("\n" + "-" * 96)
    P("БАЛАНС structured==ready по каждому фиксу (0=already-applied допустим, но симметрично):")
    bal_ok = True
    for lab in per_fix_counts:
        cs = per_fix_counts[lab].get("structured")
        cr = per_fix_counts[lab].get("ready")
        same = (cs == cr)
        bal_ok = bal_ok and same
        P(f"  {lab:22} structured={cs} ready={cr}  {'OK' if same else 'РАСХОЖДЕНИЕ!'}")

    P("\n" + "=" * 96)
    P(f"ИТОГ: get_text-гейт={'OK' if ok_all else 'FAIL'} | баланс-форм={'OK' if bal_ok else 'FAIL'}")
    P("=" * 96)
    out = ROOT / "data" / "reports" / "66_grazh_2links_apply.txt"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"written: {out}  gettext={ok_all}  balance={bal_ok}")


if __name__ == "__main__":
    main()
