# -*- coding: utf-8 -*-
"""ФИНАЛ-ГЕЙТ: видимый текст (get_text) обеих форм vs бэкап ANARA_FINISH.
Если _structured get_text не изменился — чанки (строятся из _structured) валидны,
пересборка НЕ нужна. _ready get_text тоже проверяем (правки только href/границы)."""
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
BK = ROOT / "data" / "final_backup_ANARA_FINISH"

CODES = ["nalog", "trudovoy", "grazhdanskiy", "grazhdanskiy_osob", "predprinimatel",
         "socialnyy", "ekologicheskiy", "zemelnyy", "upk", "koap", "appk",
         "byudzhet", "ugolovniy"]


def gt(p):
    return BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser").get_text()


def main():
    L = ["ФИНАЛ-ГЕЙТ get_text vs backup_ANARA_FINISH", "=" * 70,
         f"  {'код':20}{'_structured':>14}{'_ready':>10}"]
    all_ok = True
    for code in CODES:
        s_ok = gt(FINAL / f"{code}_structured.html") == gt(BK / f"{code}_structured.html")
        rp = FINAL / f"{code}_ready.html"
        rb = BK / f"{code}_ready.html"
        if rp.exists() and rb.exists():
            r_ok = gt(rp) == gt(rb)
            r = "OK" if r_ok else "FAIL"
        else:
            r_ok = True
            r = "-"
        all_ok = all_ok and s_ok and r_ok
        L.append(f"  {code:20}{('OK' if s_ok else 'FAIL'):>14}{r:>10}")
    L.append("-" * 70)
    L.append(f"  ИТОГ: {'ВСЕ OK — чанки валидны, пересборка не нужна' if all_ok else 'ЕСТЬ FAIL'}")
    out = "\n".join(L) + "\n"
    (ROOT / "data/reports/60_final_gettext_gate.txt").write_text(out, encoding="utf-8")
    print(f"all_ok={all_ok}")


if __name__ == "__main__":
    main()
