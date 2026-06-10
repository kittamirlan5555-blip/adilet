# -*- coding: utf-8 -*-
"""ANARA R2 Фаза 4в: подсчёт plain-вхождений 6 новых ключей маппинга
в ПРИНЯТОМ корпусе (5 законов + 13 кодексов). READ-ONLY, без правок —
по решению владельца новые ключи в этом раунде к принятым документам
НЕ применяются, только считаем потенциал.

python scripts/audit/r2_05_corpus_counts.py
-> data/reports/anara_r2/05_corpus_counts.md
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auditlib as al

R2 = al.ROOT / "data" / "reports" / "anara_r2"
R2_SLUGS = {"informatizacii", "notariat", "obrazovanie"}

QT = str.maketrans({"«": '"', "»": '"', "“": '"', "”": '"', "„": '"',
                    "–": "-", "—": "-", "−": "-"})
RE_NOTE = re.compile(r'<(span|p)\b[^>]*class="note"[^>]*>.*?</\1\s*>',
                     re.I | re.S)

# 6 новых ключей Фазы 2 (r2_02_mapping.ADD); голову склоняем regex'ом,
# чтобы поймать все падежи одной правовой фразы
PHRASES = [
    ("о гос. регулировании фин. рынка", "Z030000474_",
     "о государственном регулировании, контроле и надзоре финансового "
     "рынка и финансовых организаций"),
    ("о персональных данных и их защите", "Z1300000094",
     "о персональных данных и их защите"),
    ("о Национальном архивном фонде и архивах", "Z980000326_",
     "о Национальном архивном фонде и архивах"),
    ("об исполнительном производстве", "Z100000261_",
     "об исполнительном производстве"),
    ("о языках", "Z970000151_",
     "о языках"),
    ("о статусе педагога", "Z1900000293",
     "о статусе педагога"),
]


def build_rx(tail):
    words = tail.split()
    body = r"\s+".join(re.escape(w) for w in words)
    return re.compile(r"законодательств\w*\s+Республики\s+Казахстан\s+"
                      + body + r"(?![\w-])")


def main():
    slugs = [s for s in al.all_slugs() if s not in R2_SLUGS]
    rxs = [(label, ngr, build_rx(tail)) for label, ngr, tail in PHRASES]

    rows = []                       # (label, slug, plain, linked, part, note)
    totals = {label: [0, 0, 0, 0] for label, _, _ in PHRASES}
    for slug in slugs:
        path = al.FINAL / f"{slug}_structured.html"
        raw = path.read_text(encoding="utf-8")
        tmap = al.TextMap(raw)
        hay = tmap.text.translate(QT)
        contents = [(m.start(2), m.end(2)) for m in al.RE_A_PAIR.finditer(raw)]
        notes = [(m.start(), m.end()) for m in RE_NOTE.finditer(raw)]
        for label, ngr, rx in rxs:
            plain = linked = part = in_note = 0
            for m in rx.finditer(hay):
                s, e = m.start(), m.end()
                rs, re_ = tmap.pos[s], tmap.pos[e - 1] + 1
                if any(a <= rs and re_ <= b for a, b in notes):
                    in_note += 1
                elif any(cs <= rs and re_ <= ce for cs, ce in contents):
                    linked += 1
                elif any(cs < re_ and rs < ce for cs, ce in contents):
                    part += 1
                else:
                    plain += 1
            if plain or linked or part or in_note:
                rows.append((label, slug, plain, linked, part, in_note))
            t = totals[label]
            t[0] += plain; t[1] += linked; t[2] += part; t[3] += in_note

    L = ["# ANARA R2 — Фаза 4в: новые ключи маппинга в принятом корпусе", "",
         f"Корпус: {len(slugs)} принятых документов (без 3 законов R2). "
         "READ-ONLY: по решению владельца ключи в этом раунде к принятым "
         "документам НЕ применяются — только подсчёт потенциала.", "",
         "## Итог по фразам", "",
         "| фраза («законодательств… РК …») | НГР | plain | уже ссылка "
         "| разорван | в сносках |", "|---|---|---|---|---|---|"]
    for label, ngr, _ in PHRASES:
        p, l, pa, n = totals[label]
        L.append(f"| {label} | {ngr} | **{p}** | {l} | {pa} | {n} |")
    gp = sum(t[0] for t in totals.values())
    L += ["", f"**Всего plain-вхождений (потенциал линковки): {gp}**", "",
          "## Разбивка по документам (только ненулевые)", "",
          "| фраза | документ | plain | уже ссылка | разорван | в сносках |",
          "|---|---|---|---|---|---|"]
    for label, slug, p, l, pa, n in rows:
        L.append(f"| {label} | {slug} | {p} | {l} | {pa} | {n} |")

    out = R2 / "05_corpus_counts.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:20]))
    print(f"...\n-> {out}")


if __name__ == "__main__":
    main()
