# -*- coding: utf-8 -*-
"""R3 БЛОК 2, шаг 1: диагностика «РАЗОРВАННЫХ СПАНОВ» из 76-отчётов. READ-ONLY.

python scripts/audit/r3_03_torn_diag.py
-> reports/r3/torn_diag.md

Для каждого partial-кейса 76 (пересечение кандидатной фразы с <a>) показывает
пересекающиеся линки (текст+href) и вердикт-кандидат:
  TRUE-TORN — линк покрывает ЧАСТЬ минимальной правовой фразы (двигать границы);
  OVERRUN   — голова фразы уже полным спаном, захват зацепил следующий линк (ложняк);
  INSIDE    — фраза целиком внутри большего линка (ложняк);
laws3-r2 (informatizacii/notariat/obrazovanie) исключены — на ревью у Анары.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "audit"))
import auditlib as al

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

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


def main():
    L = ["# R3 БЛОК 2 — диагностика разорванных спанов", ""]
    counts = {}
    for slug in al.all_slugs():
        if slug in SKIP:
            continue
        path = al.FINAL / f"{slug}_structured.html"
        if not path.exists():
            path = al.FINAL / f"{slug}_ready.html"
        raw = path.read_text(encoding="utf-8")
        tmap = al.TextMap(raw)
        hay = tmap.text.translate(QT)
        links = [(m.start(2), m.end(2), m.group(1),
                  re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(2))).strip())
                 for m in al.RE_A_PAIR.finditer(raw)]
        notes = [(m.start(), m.end()) for m in RE_NOTE.finditer(raw)]
        doc_rows = []
        for fam, rx in PATTERNS:
            for m in rx.finditer(hay):
                s, e = m.start(), m.end()
                rs, re_ = tmap.pos[s], tmap.pos[e - 1] + 1
                if RE_SELF.search(hay[max(0, s - 12):s]):
                    continue
                if any(a <= rs and re_ <= b for a, b in notes):
                    continue
                # точно как в 76: голова фразы внутри <a> -> уже залинковано
                head_end = tmap.pos[min(e - 1, s + 25)]
                if any(cs <= rs and head_end <= ce for cs, ce, h, t in links):
                    continue
                inter = [(cs, ce, h, t) for cs, ce, h, t in links
                         if cs < re_ and rs < ce]
                if not inter:
                    continue
                frag = m.group(0)
                # ядро фразы: B/C минимальны (до закрывающей кавычки);
                # у A захват с запасом — ядро первые ~45 символов
                core_end = re_ if fam in ("B", "C") else tmap.pos[min(e - 1, s + 45)]
                inter_core = [x for x in inter if x[0] < core_end]
                verdict = "TRUE-TORN" if inter_core else "OVERRUN"
                doc_rows.append((fam, verdict, frag[:90],
                                 [(t[:60], h[:80]) for _, _, h, t in inter[:3]]))
        if doc_rows:
            counts[slug] = len(doc_rows)
            L.append(f"## {slug} — {len(doc_rows)}")
            for fam, verdict, frag, inter in doc_rows:
                L.append(f"- [{fam}] {verdict}: «{frag}»")
                for t, h in inter:
                    L.append(f"    - <a>{t}</a> -> {h}")
            L.append("")
    tt = sum(counts.values())
    L.insert(1, f"Всего partial-кейсов (без laws3): {tt}; "
                + ", ".join(f"{k}={v}" for k, v in counts.items()))
    out = paths.REPORTS / "r3" / "torn_diag.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    nt = sum(1 for line in L if "TRUE-TORN" in line and line.startswith("- "))
    print(f"partial={tt} true-torn={nt} -> {out}")


if __name__ == "__main__":
    main()
