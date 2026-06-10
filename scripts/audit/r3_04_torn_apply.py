# -*- coding: utf-8 -*-
"""R3 БЛОК 2, шаг 2: фикс разорванных спанов B/C. Дисциплина 71_fullspan:
двигаются ТОЛЬКО границы <a> (href и видимый текст неизменны).

python scripts/audit/r3_04_torn_apply.py [--apply]
-> reports/r3/torn_apply_report.md

A-семейство (8 шт.) НЕ правится автоматом — в ручную секцию отчёта.
laws3-r2 исключены. Гейты: §6.1 text-invariance, баланс <a>, G6=0 для
двухформенных документов.
"""
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import auditlib as al

sys.path.insert(0, str(HERE.parent))
import paths

_spec = importlib.util.spec_from_file_location("eng", HERE / "r3_02_g6_apply.py")
eng = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eng)

APPLY = "--apply" in sys.argv

QT = str.maketrans({"«": '"', "»": '"', "“": '"', "”": '"', "„": '"',
                    "–": "-", "—": "-", "−": "-"})
RE_NOTE = re.compile(r'<(span|p)\b[^>]*class="note"[^>]*>.*?</\1\s*>', re.I | re.S)
PATTERNS = [
    ("A", re.compile(r"законодательств\w*\s+Республики\s+Казахстан\s+"
                     r"(?:о|об|в\s+сфере|в\s+области)\s+[а-яё][^;.]{0,110}")),
    ("B", re.compile(r"(?:Конституционн\w+\s+)?[Зз]акон\w*\s+Республики\s+"
                     r"Казахстан\s+\"[^\"\n]{3,120}\"")),
    ("C", re.compile(r"[Кк]одекс\w*\s+Республики\s+Казахстан"
                     r"(?:\s+\"[^\"\n]{3,120}\")?")),
]
RE_SELF = re.compile(r"настоящ\w+\s*$")
SKIP = {"informatizacii", "notariat", "obrazovanie"}


def collect_cases(slug):
    """[(fam, H_canon, S_norm, F_norm)] по _structured (или ready)."""
    path = al.FINAL / f"{slug}_structured.html"
    if not path.exists():
        path = al.FINAL / f"{slug}_ready.html"
    raw = path.read_text(encoding="utf-8")
    own = None
    cj = json.loads(paths.CODES_JSON.read_text(encoding="utf-8"))
    v = cj.get(slug)
    own = v.get("doc_id") if isinstance(v, dict) else None
    tmap = al.TextMap(raw)
    hay = tmap.text.translate(QT)
    links = [(m.start(2), m.end(2), m.group(1),
              eng.norm(m.group(2))) for m in al.RE_A_PAIR.finditer(raw)]
    notes = [(m.start(), m.end()) for m in RE_NOTE.finditer(raw)]
    cases = []
    for fam, rx in PATTERNS:
        for m in rx.finditer(hay):
            s, e = m.start(), m.end()
            if RE_SELF.search(hay[max(0, s - 12):s]):
                continue
            rs, re_ = tmap.pos[s], tmap.pos[e - 1] + 1
            if any(a <= rs and re_ <= b for a, b in notes):
                continue
            head_end = tmap.pos[min(e - 1, s + 25)]
            if any(cs <= rs and head_end <= ce for cs, ce, h, t in links):
                continue
            core_end = re_ if fam in ("B", "C") else None
            if core_end is None:
                continue  # A-семейство — вручную
            inter = [x for x in links if x[0] < core_end and rs < x[1]]
            if not inter:
                continue
            # вложенные кавычки: захват оборвался внутри названия
            if e < len(hay) and hay[e:e + 1] not in ("", " ", ",", ".", ";",
                                                     ")", "\n"):
                nq = hay.find('"', e)
                if 0 < nq < e + 60:
                    e = nq + 1
                    re_ = tmap.pos[e - 1] + 1
            cs, ce, h, t = inter[0]
            lo, hi = min(cs, rs), max(ce, re_)
            F = eng.norm(re.sub(r"<[^>]+>", " ", raw[lo:hi]))
            H = eng.canon_href(h, own)
            if eng.norm(t) == F:
                continue  # уже полный
            cases.append((fam, H, eng.norm(t), F))
    return own, cases


def main():
    L = [f"# R3 БЛОК 2 — фикс разорванных спанов ({'APPLY' if APPLY else 'DRY-RUN'})",
         "", "Дисциплина 71_fullspan: только границы <a>; href и текст документа",
         "неизменны. Все документы ниже — ПРИНЯТЫЕ (laws3-r2 исключены).", ""]
    total = Counter()
    for slug in al.all_slugs():
        if slug in SKIP:
            continue
        own, cases = collect_cases(slug)
        if not cases:
            continue
        mult = Counter(cases)
        forms = {}
        for suf in ("structured", "ready"):
            p = al.FINAL / f"{slug}_{suf}.html"
            if p.exists():
                forms[suf] = [p, p.read_text(encoding="utf-8")]
        orig_text = {k: "".join(re.sub(r"<[^>]+>", " ", v[1]).split())
                     for k, v in forms.items()}
        L.append(f"## {slug} — кейсов {sum(mult.values())} "
                 f"(уникальных {len(mult)}), формы: {list(forms)}")
        L.append("")
        L.append("| было <a> | стало <a> | href | применено (по формам) |")
        L.append("|---|---|---|---|")
        for (fam, H, S, F), n in sorted(mult.items()):
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
                total["ext"] += done
            L.append(f"| «{S[:50]}» | «{F[:70]}» | {H[:60]} | {', '.join(res)} |")
        # гейты
        ok = True
        for suf, (p, raw2) in forms.items():
            now = "".join(re.sub(r"<[^>]+>", " ", raw2).split())
            if now != orig_text[suf]:
                ok = False
                L.append(f"!! TEXT-INVARIANCE FAIL {p.name}")
            depth = bad = 0
            for t in re.finditer(r"<a\b[^>]*>|</a\s*>", raw2, re.I):
                depth += 1 if t.group(0)[1] != "/" else -1
                if depth > 1 or depth < 0:
                    bad += 1
            if bad or depth != 0:
                ok = False
                L.append(f"!! NESTED FAIL {p.name}")
        if len(forms) == 2:
            os_, or_, _, _ = eng.divergences(forms["structured"][1],
                                             forms["ready"][1], own)
            if os_ or or_:
                ok = False
                L.append(f"!! G6 FAIL: {len(os_)}+{len(or_)} расхождений")
        L.append(f"гейты: {'OK' if ok else 'FAIL'}")
        L.append("")
        if APPLY and ok:
            for suf, (p, raw2) in forms.items():
                p.write_text(raw2, encoding="utf-8")
        total["docs"] += 1
        if not ok:
            total["fail_docs"] += 1
        print(f"{slug:18} кейсов={sum(mult.values()):>3} гейты={'OK' if ok else 'FAIL'}")

    L.append(f"ИТОГО: документов {total['docs']}, расширений {total['ext']}, "
             f"документов с FAIL-гейтом {total['fail_docs']}")
    out = paths.REPORTS / "r3" / "torn_apply_report.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"расширений={total['ext']} fail_docs={total['fail_docs']} -> {out}")


if __name__ == "__main__":
    main()
