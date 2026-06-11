# -*- coding: utf-8 -*-
"""76: gap-отчёт маппинга — ОБЯЗАТЕЛЬНЫЙ шаг перед сдачей документа.

python scripts/76_mapping_gap_report.py --doc {slug} [--doc ...] [--all] [--strict]
-> data/reports/mapping_gap_{slug}.md

Ищет в тексте (вне <a>) кандидатные правовые фразы трёх семейств:
  A. «законодательств… Республики Казахстан о/об/в сфере/в области …»
  B. «Закон… Республики Казахстан "Название"»
  C. «…кодекс… Республики Казахстан» (адъективные и с кавычечным титулом)
и для каждой показывает, есть ли точный ключ в npa_mapping.json.
Самоотсылки «настоящим Законом/Кодексом» исключены. Кандидаты в сносках
(class="note") считаются отдельно (сноски не линкуем — правило Анары 13.05),
в гейт не входят. --strict: exit 1, если вне сносок остались кандидаты.

Это РЕПОРТЕР (read-only), не линкер: хвост фразы захватывается до конца
предложения с запасом — решение о спане принимает человек/линкер.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "audit"))
import auditlib as al

OUT = al.GATES

QT = str.maketrans({"«": '"', "»": '"', "“": '"', "”": '"', "„": '"',
                    "–": "-", "—": "-", "−": "-"})
RE_NOTE = re.compile(r'<(span|p)\b[^>]*class="note"[^>]*>.*?</\1\s*>',
                     re.I | re.S)
# заголовки статей (h3 структурной формы / <b>Статья…</b> плоской; перед
# словом «Статья» может стоять пустой якорь <a id></a>) не линкуем
RE_HEAD = re.compile(
    r"<h3\b[^>]*>.*?</h3\s*>"
    r"|<b\b[^>]*>(?:\s|<a\b[^>]*>\s*</a\s*>)*Статья\b.*?</b\s*>",
    re.I | re.S)

# Семейства кандидатов (по нормализованному тексту, кавычки уже ")
PATTERNS = [
    ("A: законодательство РК о…",
     re.compile(r"законодательств\w*\s+Республики\s+Казахстан\s+"
                r"(?:о|об|в\s+сфере|в\s+области)\s+[а-яё][^;.]{0,110}")),
    ("B: Закон РК \"…\"",
     re.compile(r"[Зз]акон\w*\s+Республики\s+Казахстан\s+\"[^\"]{3,120}\"")),
    ("C: кодекс РК",
     # прилагательное из 1-3 слов: «Административным процедурно-процессуальным»
     re.compile(r"(?:[А-ЯЁ][\w-]+\s+(?:[а-яё][\w-]+\s+){0,2})?"
                r"[Кк]одекс\w*\s+Республики\s+Казахстан"
                r"(?:\s+\"[^\"]{3,120}\"(?:\s+\(Налоговый\s+кодекс\))?"
                r"|\s+об\s+административных\s+правонарушениях)?")),
]
RE_SELF = re.compile(r"настоящ\w+\s*$")


def scan(slug, mapping_keys):
    path = al.FINAL / f"{slug}_structured.html"
    if not path.exists():
        path = al.FINAL / f"{slug}_ready.html"
    raw = path.read_text(encoding="utf-8")
    tmap = al.TextMap(raw)
    hay = tmap.text.translate(QT)
    contents = [(m.start(2), m.end(2)) for m in al.RE_A_PAIR.finditer(raw)]
    notes = [(m.start(), m.end()) for m in RE_NOTE.finditer(raw)]
    heads = [(m.start(), m.end()) for m in RE_HEAD.finditer(raw)]

    rows, in_notes = [], 0
    seen_spans = []
    for fam, rx in PATTERNS:
        for m in rx.finditer(hay):
            s, e = m.start(), m.end()
            if any(a <= s < b for a, b in seen_spans):
                continue  # семейство A уже захватило это место
            if RE_SELF.search(hay[max(0, s - 12):s]):
                continue
            rs, re_ = tmap.pos[s], tmap.pos[e - 1] + 1
            # голова фразы внутри <a> -> уже залинковано
            head_end = tmap.pos[min(e - 1, s + 25)]
            if any(cs <= rs and head_end <= ce for cs, ce in contents):
                continue
            if any(a <= rs and re_ <= b for a, b in notes):
                in_notes += 1
                continue
            if any(a <= rs < b for a, b in heads):
                continue  # голова фразы в заголовке статьи — не линкуем
            frag = m.group(0)
            key = "ЕСТЬ" if any(
                k.translate(QT) in frag or frag.startswith(k.translate(QT))
                for k in mapping_keys) else "нет"
            partial = any(cs < re_ and rs < ce for cs, ce in contents)
            rows.append((fam, frag, key, partial))
            seen_spans.append((s, e))
    return path.name, rows, in_notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", action="append", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    slugs = al.all_slugs() if args.all else args.doc
    if not slugs:
        ap.error("--doc или --all")

    mapping = json.loads((al.CONFIG / "npa_mapping.json")
                         .read_text(encoding="utf-8"))
    mkeys = list(mapping.keys())

    worst = 0
    for slug in slugs:
        fname, rows, in_notes = scan(slug, mkeys)
        L = [f"# mapping-gap — {slug} ({fname})", "",
             f"Кандидатов вне ссылок и вне сносок: **{len(rows)}**; "
             f"в сносках (не линкуем): {in_notes}.", ""]
        npart = sum(1 for r in rows if r[3])
        if npart:
            L.insert(2, f"**РАЗОРВАННЫХ СПАНОВ: {npart}** — горит часть "
                        "фразы (класс жёлтого Анары), приоритет на фикс.")
        if rows:
            L += ["| семейство | фраза (захват до конца предложения) "
                  "| ключ в маппинге | спан |", "|---|---|---|---|"]
            for fam, frag, key, partial in rows:
                disp = frag if len(frag) <= 95 else frag[:92] + "…"
                st = "**РАЗОРВАН**" if partial else "plain"
                L.append(f"| {fam} | «{disp}» | {key} | {st} |")
        else:
            L.append("Остаток пуст — все кандидатные фразы либо уже "
                     "ссылки, либо в сносках.")
        out = OUT / f"mapping_gap_{slug}.md"
        out.write_text("\n".join(L) + "\n", encoding="utf-8")
        print(f"{slug}: gaps={len(rows)} notes={in_notes} -> {out.name}")
        worst = max(worst, len(rows))
    sys.exit(1 if args.strict and worst else 0)


if __name__ == "__main__":
    main()
