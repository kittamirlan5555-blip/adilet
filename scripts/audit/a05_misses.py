# -*- coding: utf-8 -*-
"""АУДИТ ФАЗА 5: возможные ПРОПУСКИ ревью — места, похожие на «должна быть
ссылка», но не залинкованные и не флагованные. READ-ONLY, только список.

python scripts/audit/a05_misses.py
-> data/reports/audit/05_review_misses.md

Сноски (class="note") исключены — их НЕ линкуем по правилу Анары (R09).
"""
import re
import sys
import bisect
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auditlib as al

PATTERNS = [
    ("внутр. отсылка «статья N настоящего Кодекса/Закона» без ссылки",
     re.compile(r"стат[ье]\w*\s+\d+(?:-\d+)*(?:\s+настоящ\w+\s+(?:Кодекс|Закон)\w*)",
                re.I)),
    ("«в соответствии со статьёй N» без ссылки",
     re.compile(r"(?:в соответствии со?|согласно)\s+стат[ье]\w*\s+\d+(?:-\d+)*", re.I)),
    ("название закона «Закон РК \"…\"» без ссылки",
     re.compile(r"Закон\w*\s+Республики\s+Казахстан\s+[«\"][^»\"]{5,90}[»\"]")),
]

RE_NOTE = re.compile(r'<(span|p)\b[^>]*class="note"[^>]*>.*?</\1\s*>', re.I | re.S)


def blocked_ranges(raw):
    """Диапазоны, где НЕссылка легитимна: сноски + всё до первой статьи (хром)."""
    out = [(m.start(), m.end()) for m in RE_NOTE.finditer(raw)]
    cl = al.article_clusters(raw)
    if cl:
        out.append((0, cl[0][0]))
    out.sort()
    return out


def link_ranges(raw):
    return [(m.start(), m.end()) for m in al.RE_A_PAIR.finditer(raw)]


def inside(ranges_starts, ranges, p):
    i = bisect.bisect_right(ranges_starts, p) - 1
    return i >= 0 and ranges[i][0] <= p < ranges[i][1]


def main():
    L = ["# АУДИТ 05 — возможные пропуски ревью (только список, НЕ чинить)", "",
         "Генератор: scripts/audit/a05_misses.py. Совпадение паттерна вне <a> и вне "
         "сносок = КАНДИДАТ пропуска (человек решает). Сноски исключены (R09).", "",
         "| slug | " + " | ".join(p[0] for p in PATTERNS) + " |",
         "|---|" + "---|" * len(PATTERNS)]
    details = []
    for slug in al.all_slugs():
        form, path = (("ready", al.FINAL / f"{slug}_ready.html")
                      if (al.FINAL / f"{slug}_ready.html").exists()
                      else ("structured", al.FINAL / f"{slug}_structured.html"))
        raw = path.read_text(encoding="utf-8")
        tm = al.TextMap(raw)
        links = link_ranges(raw)
        lstarts = [r[0] for r in links]
        blocked = blocked_ranges(raw)
        bstarts = [r[0] for r in blocked]
        counts = []
        for label, rx in PATTERNS:
            hits = []
            for m in rx.finditer(tm.text):
                rp = tm.pos[m.start()]
                if inside(lstarts, links, rp) or inside(bstarts, blocked, rp):
                    continue
                hits.append((m.group(0)[:90],
                             tm.text[max(0, m.start() - 50):m.end() + 40]))
            counts.append(len(hits))
            if hits:
                details.append((slug, label, hits[:5], len(hits)))
        L.append(f"| {slug} | " + " | ".join(map(str, counts)) + " |")

    L += ["", "## Примеры (до 5 на документ/паттерн)", ""]
    for slug, label, hits, total in details:
        L.append(f"### {slug} — {label} (всего {total})")
        for frag, ctx in hits:
            L.append(f"- `{frag}`")
            L.append(f"  - контекст: …{ctx}…")
        L.append("")
    al.AUDIT_OUT.mkdir(parents=True, exist_ok=True)
    (al.AUDIT_OUT / "05_review_misses.md").write_text("\n".join(L) + "\n",
                                                      encoding="utf-8")
    print("\n".join(L[:30]))


if __name__ == "__main__":
    main()
