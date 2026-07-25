# -*- coding: utf-8 -*-
"""anara2 BLOCK 4 регресс: дата ВНУТРИ фразы «Закон* РК от <дата> "Имя"» — один спан.
Прогоняем coalesce_split_act + absorb_prefix из 72 на копиях задетых файлов, проверяем:
  - дата теперь ВНУТРИ спана (спан начинается с «Закон/Кодекс», содержит «от <дата>»);
  - text-invariant (get_text без разделителя байт-в-байт);
  - нет вложенных <a>.
Read-only (in-memory), диск не трогаем — применение идёт пайплайном в BLOCK 6.
"""
import io, sys, importlib.util, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "m72", ROOT / "scripts/pipeline/72_external_root_link.py")
m72 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m72)
MON = r"(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)\w*"
DATE = re.compile(r"от\s+\d{1,2}\s+" + MON + r"\s+\d{4}\s*года", re.I)


def main():
    files = sorted(ROOT.glob("final/*_ready.html"))
    tot_co = tot_ab = bad_inv = bad_nested = span_with_date = 0
    touched = 0
    for p in files:
        soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
        t0 = "".join(soup.get_text().split())
        co = m72.coalesce_split_act(soup)
        ab = m72.absorb_prefix(soup)
        if co == 0 and ab == 0:
            continue
        touched += 1
        t1 = "".join(soup.get_text().split())
        if t0 != t1:
            bad_inv += 1; print(f"  ✗ TEXT CHANGED {p.name}")
        nested = sum(1 for a in soup.find_all("a") if a.find("a"))
        if nested:
            bad_nested += 1; print(f"  ✗ NESTED <a>={nested} {p.name}")
        for a in soup.find_all("a", href=True):
            at = a.get_text()
            if DATE.search(at) and at.lstrip()[:1] in "ЗзКк":
                span_with_date += 1
        tot_co += co; tot_ab += ab
    print(f"файлов затронуто: {touched}  | coalesce={tot_co}  absorb={tot_ab}")
    print(f"спанов с датой внутри (после): {span_with_date}")
    ok = (bad_inv == 0 and bad_nested == 0)
    print("  ✅ text-invariant, nested=0" if ok else
          f"  ✗ inv-fail={bad_inv} nested-fail={bad_nested}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
