# -*- coding: utf-8 -*-
"""R3 БЛОК 2, шаг 3: добивка 10 хвостовых разорванных спанов (A-семейство и
два сложных B) явной таблицей кейсов. Только границы <a>.

python scripts/audit/r3_05_torn_tail.py [--apply]
-> дополняет reports/r3/torn_apply_report.md
"""
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import paths

_spec = importlib.util.spec_from_file_location("eng", HERE / "r3_02_g6_apply.py")
eng = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eng)

APPLY = "--apply" in sys.argv

A = "https://adilet.zan.kz/rus/docs/"
# (slug, n, H, S, F)
CASES = [
    ("koap", 1, A + "Z970000151_#z1", "о языках",
     "законодательства Республики Казахстан о языках"),
    ("nalog", 1, A + "Z950002464_#z1", "Конституционным законом",
     'Конституционным законом Республики Казахстан "О выборах в Республике Казахстан"'),
    ("nalog", 1, A + "Z950002444_#z1",
     "О банках и банковской деятельности в Республике Казахстан",
     'законами Республики Казахстан "О банках и банковской деятельности в Республике Казахстан'),
    ("upk", 2, A + "Z100000261_#z301", "законодательством",
     "законодательством Республики Казахстан об исполнительном производстве "
     "и статусе судебных исполнителей"),
    ("upk", 1, A + "V2000021747#z16", "законодательством",
     "законодательством Республики Казахстан о здравоохранении"),
    ("zemelnyy", 1, A + "K1400000235#z430", "законодательством",
     "законодательством Республики Казахстан об административных правонарушениях"),
    ("zemelnyy", 3, A + "K1400000235", "об административных правонарушениях",
     "законодательством Республики Казахстан об административных правонарушениях"),
]


def main():
    L = ["", "## Добивка хвостов (r3_05): A-семейство + 2 сложных B", "",
         "| док | было <a> | стало <a> | href | применено |", "|---|---|---|---|---|"]
    fail = 0
    by_slug = {}
    for slug, n, H, S, F in CASES:
        by_slug.setdefault(slug, []).append((n, H, S, F))
    for slug, cases in by_slug.items():
        forms = {}
        for suf in ("structured", "ready"):
            p = paths.FINAL / f"{slug}_{suf}.html"
            if p.exists():
                forms[suf] = [p, p.read_text(encoding="utf-8")]
        orig = {k: "".join(re.sub(r"<[^>]+>", " ", v[1]).split())
                for k, v in forms.items()}
        own = None  # H здесь всегда внешний полный URL
        for n, H, S, F in cases:
            res = []
            for suf in forms:
                done = 0
                for _ in range(n):
                    r2 = eng.extend_one(forms[suf][1], own, H, S, F)
                    if not r2:
                        break
                    forms[suf][1] = r2[0]
                    done += 1
                res.append(f"{suf}:{done}/{n}")
                if done != n:
                    fail += 1
            L.append(f"| {slug} | «{S[:40]}» | «{F[:60]}» | {H[len(A):]} "
                     f"| {', '.join(res)} |")
        ok = True
        for suf, (p, raw2) in forms.items():
            if "".join(re.sub(r"<[^>]+>", " ", raw2).split()) != orig[suf]:
                ok = False
                L.append(f"!! TEXT-INVARIANCE FAIL {p.name}")
        if len(forms) == 2:
            cj = __import__("json").loads(
                paths.CODES_JSON.read_text(encoding="utf-8"))
            v = cj.get(slug)
            own_id = v.get("doc_id") if isinstance(v, dict) else None
            os_, or_, _, _ = eng.divergences(forms["structured"][1],
                                             forms["ready"][1], own_id)
            if os_ or or_:
                ok = False
                L.append(f"!! G6 FAIL {slug}: {len(os_)}+{len(or_)}")
        if APPLY and ok:
            for suf, (p, raw2) in forms.items():
                p.write_text(raw2, encoding="utf-8")
        print(f"{slug}: гейты={'OK' if ok else 'FAIL'}")
    L.append("")
    out = paths.REPORTS / "r3" / "torn_apply_report.md"
    prev = out.read_text(encoding="utf-8") if out.exists() else ""
    if APPLY:
        out.write_text(prev + "\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"fail={fail}")


if __name__ == "__main__":
    main()
