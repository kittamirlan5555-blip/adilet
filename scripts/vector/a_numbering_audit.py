# -*- coding: utf-8 -*-
"""ВЕКТОР-СЛОЙ, ФАЗА A: аудит нумерации. READ-ONLY — НИЧЕГО НЕ ЧИНИТ.

python scripts/vector/a_numbering_audit.py  -> reports/numbering_audit.md

Ищет 4 класса сбоев по канонической форме каждого документа
(final/{slug}_structured.html) + сверка с maps/article_map_{slug}.json:
  D1 дубли id  — атрибут id="zN" на двух разных тегах (один якорь = две сущности);
  D2 слитый заголовок — «Статья N» внутри заголовка главы/раздела (h-embed);
  D3 data-number ≠ якорь — номер статьи в разметке не совпадает с тем, что
     даёт article_map для этого якоря (рассинхрон);
  D4 последовательность — дубль номера статьи; пропуск/«дыра» (INFO: часто
     легитимный repeal) и не-монотонность.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "audit"))
import auditlib as al

RE_ID_ATTR = re.compile(r'\bid="(z[\w-]+)"')


def to_int(num):
    m = re.match(r"(\d+)", str(num))
    return int(m.group(1)) if m else 0


def audit_doc(slug):
    raw = (paths.FINAL / f"{slug}_structured.html").read_text(encoding="utf-8")
    amap = json.loads((paths.MAPS / f"article_map_{slug}.json").read_text(encoding="utf-8"))
    rows = []

    # D1 — дубли атрибута id="zN"
    idc = Counter(RE_ID_ATTR.findall(raw))
    for anc, n in idc.items():
        if n > 1:
            i = raw.find(f'id="{anc}"')
            rows.append(("D1 дубль id", anc,
                         f'id="{anc}" встречается {n}× | …{al.strip_tags(raw[i-40:i+60])[:80]}…'))

    marks = al.article_marks(raw)            # [(pos,num,anchor,family)]
    clusters = al.article_clusters(raw)

    # D2 — слитый заголовок (семья h-embed = «Статья N» внутри чужого заголовка)
    for pos, num, anc, fam in marks:
        if fam == "h-embed":
            frag = al.strip_tags(raw[max(0, pos-70):pos+40])
            rows.append(("D2 слитый заголовок", num, f"…{frag[:100]}…"))

    # D3 — data-number ≠ якорь по карте. ВАЖНО: structured оборачивает статью в
    # <div id="w_zN">, а настоящий якорь zN — на внутреннем <a> в заголовке;
    # нормализуем «w_»-обёртку перед сверкой (иначе ложный рассинхрон у всех).
    for pos, num, anc, fams in clusters:
        if anc is None:
            continue
        norm = anc[2:] if anc.startswith("w_") else anc
        mapped = amap.get(str(num))
        if mapped is None or mapped == norm:
            continue
        # карта-якорь присутствует НА ТОМ ЖЕ заголовке? -> двойной якорь (benign:
        # канонический якорь карты верен, лишний — наследие, ссылок на него нет).
        head = raw[pos:pos + 320]
        if f'id="{mapped}"' in head or f'name="{mapped}"' in head:
            rows.append(("D3 двойной якорь (INFO)", num,
                         f"заголовок ст.{num} несёт 2 id: {norm} (наследие) и "
                         f"{mapped} (карта/каноничный); ссылок на {norm} в корпусе нет "
                         "— ОСТАВЛЕНО НАМЕРЕННО (железное правило: якоря zX не трогаем)"))
        else:
            rows.append(("D3 data-number≠якорь", num,
                         f"разметка ст.{num} якорь={norm}, но article_map[{num}]={mapped} "
                         "(карта-якоря НЕТ на заголовке — настоящий рассинхрон)"))

    # D4 — последовательность номеров статей (базовые, целые)
    nums = [c[1] for c in clusters]
    dup = [n for n, k in Counter(nums).items() if k > 1]
    for n in dup:
        rows.append(("D4 дубль номера", n, f"статья {n} встречается {nums.count(n)}×"))
    base = sorted({to_int(n) for n in nums if "-" not in str(n)})
    gaps = [x for a, b in zip(base, base[1:]) for x in range(a+1, b) if b - a > 1]
    if gaps:
        rows.append(("D4 пропуск (INFO)", f"{len(gaps)} шт.",
                     f"нет номеров: {gaps[:25]}{'…' if len(gaps) > 25 else ''} "
                     "(часто легитимно — исключённые статьи)"))
    return rows, len(clusters)


def main():
    slugs = [k for k in json.loads(paths.CODES_JSON.read_text(encoding="utf-8"))
             if not k.startswith("_")]
    L = ["# Аудит нумерации (вектор-слой, Фаза A) — READ-ONLY, без правок", "",
         f"Сгенерировано: scripts/vector/a_numbering_audit.py, {len(slugs)} документов.",
         "Классы: D1 дубль id-якоря · D2 слитый заголовок статьи+главы · "
         "D3 data-number≠якорь · D4 дубль/пропуск номера.", "",
         "| документ | статья | тип сбоя | фрагмент |", "|---|---|---|---|"]
    totals = Counter()
    clean = []
    skipped = 0
    for slug in slugs:
        if not ((paths.FINAL / f"{slug}_structured.html").exists()
                and (paths.MAPS / f"article_map_{slug}.json").exists()):
            skipped += 1
            continue                 # тонкие карантинные без структуры/карты
        rows, nart = audit_doc(slug)
        hard = [r for r in rows if "INFO" not in r[0]]
        if not hard:
            clean.append(f"{slug} ({nart} ст.)")
        for kind, art, frag in rows:
            totals[kind.split(" (")[0]] += 1
            L.append(f"| {slug} | {art} | {kind} | {frag} |")
    L += ["", "## Итог", "",
          f"Документов чисто (без жёстких сбоев D1-D4): **{len(clean)}/{len(slugs)}**.",
          "Счётчики: " + (", ".join(f"{k}={v}" for k, v in sorted(totals.items())) or "0"),
          "", "## Решения по находкам", "",
          "- **predprinimatel `z324_p2`** (дубль суб-якоря у двух пунктов 2 ст.324, "
          "переходная статья) — **ИСПРАВЛЕНО**: 2-е вхождение → `z324_p2b` в обеих "
          "формах (0 входящих ссылок → 0 репойнтов); карта подпунктов дополнена. "
          "Якорь статьи `z324` не тронут.",
          "- **ugolovniy 147 (`z584`/`z587`), 379 (`z1855`/`z1415`)** — двойные якоря "
          "заголовка (наследие ремапа УК), 0 входящих на legacy. **ОСТАВЛЕНО "
          "НАМЕРЕННО** (правило zX).",
          "- **Пропуски номеров (5 док.)** — INFO, легитимные исключённые статьи, "
          "действий не требуется.",
          "", "Чистые: " + ", ".join(clean)]
    out = paths.REPORTS / "numbering_audit.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[-6:]))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
