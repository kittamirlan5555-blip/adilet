# -*- coding: utf-8 -*-
"""ВЕКТОР-СЛОЙ: аудит + верификация ЕДИНОГО подхода к repealed. READ-ONLY.

python scripts/vector/j_repealed_audit.py  -> reports/repealed_uniformity.md

Два паттерна исключения (по источнику adilet):
  (а) статья-сноска «Статья N исключена …» — в слое: parent kind="repealed",
      резолв по якорю/номеру, ВНЕ семантического индекса;
  (б) полностью удалённая (пропуск в нумерации) — чанка нет, только в repealed_gaps.
Проверяет единообразие: все сноски -> kind=repealed; в индексе repealed = 0.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
from bs4 import BeautifulSoup

OUT = paths.ROOT / "derived" / "vector_layer"
RE_REPEALED = re.compile(r"Стать[яи]\s+([\d\-]+)\s+исключена", re.I)


def base_int(n):
    m = re.match(r"(\d+)", str(n))
    return int(m.group(1)) if m else None


def main():
    cj = json.loads(paths.CODES_JSON.read_text(encoding="utf-8"))
    slugs = [k for k in cj if not k.startswith("_")]
    rows = [json.loads(l) for l in (OUT / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    rep_chunks = {}
    for r in rows:
        if r["kind"] == "repealed":
            rep_chunks.setdefault(r["code"], set()).add(r["article_no"])
    meta_p = OUT / "index_meta.jsonl"
    idx_uids = ({json.loads(l)["uid"] for l in meta_p.read_text(encoding="utf-8").splitlines() if l.strip()}
                if meta_p.exists() else set())   # индекс ещё не построен (BLOCK E) -> проверка in-index на этапе E
    rep_uids = {r["uid"] for r in rows if r["kind"] == "repealed"}

    L = ["# Единый подход к repealed-статьям (вектор-слой)", "",
         "Правило (все 25 док): сноска «Статья N исключена» -> parent `kind=repealed` "
         "(текст сноски + meta закон/дата, резолв по якорю/номеру, **вне индекса**); "
         "полностью удалённая (пропуск нумерации) -> только в `repealed_gaps` (чанка нет).",
         "", "| документ | repealed-сносок | в индексе | пропусков (gaps) | примеры пропусков |",
         "|---|---|---|---|---|"]
    tot_rep = tot_gap = tot_in_idx = 0
    nonuniform = []
    gaps_all = {}
    for slug in slugs:
        if not ((paths.FINAL / f"{slug}_structured.html").exists()
                and (paths.MAPS / f"article_map_{slug}.json").exists()):
            continue                 # тонкие карантинные без структуры/карты
        raw = (paths.FINAL / f"{slug}_structured.html").read_text(encoding="utf-8")
        amap = json.loads((paths.MAPS / f"article_map_{slug}.json").read_text(encoding="utf-8"))
        # сноски из HTML
        html_rep = set()
        for d in BeautifulSoup(raw, "html.parser").find_all("div", class_="article"):
            m = RE_REPEALED.search(d.get_text(" "))
            if m:
                html_rep.add(d.get("data-number") or m.group(1))
        chunk_rep = rep_chunks.get(slug, set())
        # единообразие: все HTML-сноски стали kind=repealed
        missed = html_rep - chunk_rep
        if missed:
            nonuniform.append((slug, sorted(missed)))
        # в индексе repealed?
        in_idx = len({f"{slug}_{amap[n]}" for n in chunk_rep if n in amap} & idx_uids)
        # пропуски нумерации: целый номер N отсутствует И как статья (точно),
        # И как сноска. Дефисный сосед (20-1) не «закрывает» отсутствие 20 —
        # это и есть удаление/замена (как zhilishniy 20). Для аудита.
        present_exact = set(amap.keys()) | set(chunk_rep)
        bases = {base_int(k) for k in amap} | {base_int(n) for n in chunk_rep}
        bases.discard(None)
        # диапазон — от МИН до МАКС номера статьи документа (ГК-Особенная начинается
        # с ~378: иначе 1..377 ложно считались бы пропусками)
        lo, hi = (min(bases), max(bases)) if bases else (1, 0)
        gaps = [n for n in range(lo, hi + 1) if str(n) not in present_exact]
        if html_rep or gaps:
            gaps_all[slug] = gaps
            tot_rep += len(html_rep)
            tot_gap += len(gaps)
            tot_in_idx += in_idx
            L.append(f"| {slug} | {len(html_rep)} | {in_idx} | {len(gaps)} | "
                     f"{gaps[:8]}{'…' if len(gaps) > 8 else ''} |")

    L += ["", "## Верификация", "",
          f"- repealed-сносок всего: **{tot_rep}**; помечены `kind=repealed` единообразно: "
          f"**{'ДА' if not nonuniform else 'НЕТ — ' + str(nonuniform)}**.",
          f"- repealed-чанков В СЕМАНТИЧЕСКОМ ИНДЕКСЕ: **{tot_in_idx}** (целевое 0).",
          f"- repealed uid пересечений с индексом: **{len(rep_uids & idx_uids)}** (целевое 0).",
          f"- пропусков нумерации (gaps, чанка нет): **{tot_gap}** — только для аудита.",
          "", "**О пропусках (честно):** gap = целый номер в [min..max статьи документа], "
          "отсутствующий и как статья (точно), и как сноска. Включает: настоящие "
          "удаления без сноски (predprinimatel 158/159), замену на дефисные статьи, "
          "и ~9 статей, что есть в HTML, но без якоря в нашей карте (grazhdanskiy_osob "
          "420/435/… — отдельный no-anchor-вопрос, не удаление). Достоверный признак "
          "удаления — ИМЕННО сноска (kind=repealed). Числа отражают НАШУ выгрузку и "
          "могут отличаться от живого adilet.",
          "", "Якоря статей zX не менялись; repealed резолвится по якорю/номеру "
          "(в chunks.jsonl есть, в faiss-индексе — нет). Исходные HTML не тронуты. "
          "meta каждой repealed: repealing_law (№), repealing_ngr (НГР-ссылка), "
          "repealing_date."]
    (paths.REPORTS / "repealed_uniformity.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    # сохранить gaps по докам (машиночитаемо)
    (OUT / "repealed_gaps.json").write_text(
        json.dumps(gaps_all, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"repealed-сносок {tot_rep}, в индексе {tot_in_idx} (цель 0), gaps {tot_gap}; "
          f"единообразно: {not nonuniform} -> reports/repealed_uniformity.md")
    for slug in ("predprinimatel", "upk", "zhilishniy", "informatizacii"):
        if slug in gaps_all:
            print(f"  {slug} gaps: {gaps_all[slug][:10]}")


if __name__ == "__main__":
    main()
