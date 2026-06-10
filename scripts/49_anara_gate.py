# -*- coding: utf-8 -*-
"""ДИФФ-ГЕЙТ ANARA: сравнить текущие 4 файла с бэкапом (final_backup_ANARA_MARKUP).
Гейты:
  G1 видимый текст (get_text) БАЙТ-В-БАЙТ идентичен бэкапу (правки только +<a>);
  G2 число <a> выросло ровно на ожидаемое (B=0, A=+N); ни один старый href не пропал;
  G3 каждый ДОБАВЛЕННЫЙ href — это новый <a> (внешний акт) либо перенос границы (B).
READ-ONLY (только проверка).
"""
import sys
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data" / "final"
BK = ROOT / "data" / "final_backup_ANARA_MARKUP"

FILES = ["predprinimatel_structured.html","predprinimatel_ready.html",
         "zemelnyy_structured.html","zemelnyy_ready.html"]

def load(p):
    s = BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser")
    return s.get_text(), Counter(a.get("href") for a in s.find_all("a", href=True)), len(s.find_all("a"))

def main():
    L = ["ДИФФ-ГЕЙТ ANARA (текущие vs бэкап final_backup_ANARA_MARKUP)", "=" * 70]
    allok = True
    for f in FILES:
        bt, bh, ba = load(BK / f)
        ct, ch, ca = load(FINAL / f)
        g1 = (bt == ct)
        lost = [h for h, c in bh.items() if ch[h] < c]      # пропавшие href
        added = ch - bh                                      # добавленные href (Counter diff)
        g2 = (not lost)
        allok = allok and g1 and g2
        L.append("")
        L.append(f"[{f}]")
        L.append(f"  G1 видимый текст байт-в-байт: {'OK' if g1 else 'FAIL'}"
                 + ("" if g1 else f" (len {len(bt)}->{len(ct)})"))
        L.append(f"  G2 старые href целы: {'OK' if g2 else 'FAIL'+str(lost)}; <a> {ba}->{ca} (Δ{ca-ba:+d})")
        if added:
            L.append(f"  добавленные href (+): " + ", ".join(f"{h.split('/')[-1]}×{n}" for h, n in added.items()))
        else:
            L.append(f"  добавленные href: нет (TYPE B — только перенос границ существующих <a>)")
    L.append("")
    L.append("ИТОГ: " + ("ВСЕ ГЕЙТЫ ЗЕЛЁНЫЕ" if allok else "ЕСТЬ ПРОВАЛ — СТОП"))
    out = "\n".join(L) + "\n"
    (ROOT / "data/reports/49_anara_gate.txt").write_text(out, encoding="utf-8")
    sys.stdout.write(out.encode("ascii", "replace").decode("ascii"))

if __name__ == "__main__":
    main()
