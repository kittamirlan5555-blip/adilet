# -*- coding: utf-8 -*-
"""ВЕКТОР-СЛОЙ, полный корпус: чанкинг ВСЕХ статей 25 документов. ADDITIVE.

python scripts/vector/f_full_chunks.py
-> derived/vector_layer/chunks.jsonl   (parent на статью + сабчанки ≤окна)
-> reports/full_chunk_report.md

Правила: parent.chunk_id = якорь статьи zX (НЕ меняем). Статья с телом > окна
эмбеддера режется по СМЫСЛУ (пункты/абзацы) на сабчанки, каждый ≤ окна, id
additive zX_1, zX_2… (сколько нужно). Мелкая статья (тело ≤ окна) — только parent.
Заголовок «Статья N.» в сабчанки не дублируется (он в parent.text + article_title).
SUMMARY переносятся из текущего chunks.jsonl по (код, статья) — DeepSeek НЕ
вызывается (100 готовых не пересчитываем).
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
from bs4 import BeautifulSoup

OUT = paths.ROOT / "derived" / "vector_layer"
CHUNKS = OUT / "chunks.jsonl"
SPLIT_IF = 1800        # тело > этого -> резать (окно e5/MiniLM ≈ 512 ток ≈ 1800 симв)
SUB_MAX = 1500         # цель сабчанка по телу (запас под «Статья N.» при эмбеддинге)
RE_PUNKT = re.compile(r"^\s*\d+(?:-\d+)?[.)]\s")
RE_TITLE = re.compile(r"^\s*Стать\w*\s+\d")
RE_SENT = re.compile(r"(?<=[.;])\s+(?=[А-ЯЁ0-9])")
RE_REPEALED = re.compile(r"Стать[яи]\s+[\d\-]+\s+исключена", re.I)
RE_DATE = re.compile(r"от\s+(\d{1,2}\.\d{2}\.\d{4})")
RE_LAWNO = re.compile(r"(№\s*\d+(?:-[A-ZА-Я]+)?)")   # «№ 15-VIII», «№ 479-V»
RE_DOCID = re.compile(r"/docs/([A-Za-z0-9_]+)")


def repeal_meta(div):
    """(текст-сноски, {repealing_law, repealing_date}) для исключённой статьи."""
    notes = div.find_all(class_="note")
    foot = next((n.get_text(" ", strip=True) for n in notes
                 if "исключен" in n.get_text().lower()),
                div.get_text(" ", strip=True))
    txt = div.get_text(" ", strip=True)
    date = RE_DATE.search(txt)
    no = RE_LAWNO.search(txt)
    doc = RE_DOCID.search(str(div))
    return foot, {"repealing_law": (no.group(1).replace(" ", " ") if no else None),
                  "repealing_ngr": doc.group(1) if doc else None,
                  "repealing_date": date.group(1) if date else None}


def article_units(div):
    # заголовок может быть в <h3> (УК/ГК/ЗК/…) ИЛИ первым <p> (АППК/налог/…)
    h3 = div.find(["h3", "h4"])
    h3t = h3.get_text(" ", strip=True) if h3 else ""
    h3title = h3t if RE_TITLE.match(h3t) else ""
    ps = [p.get_text(" ", strip=True) for p in div.find_all("p")]
    ps = [t for t in ps if t]
    ptitle = ps[0] if ps and RE_TITLE.match(ps[0]) else ""
    if h3title:
        title, units = h3title, ps                 # заголовок в <h3> -> все <p> = тело
    else:
        title, units = ptitle, (ps[1:] if ptitle else ps)
    # гигантский абзац -> по предложениям; остаток-предложение > окна -> по символам
    out = []
    for u in units:
        pieces = [s for s in RE_SENT.split(u) if s.strip()] if len(u) > SUB_MAX else [u]
        for s in pieces:
            while len(s) > SUB_MAX:
                cut = s.rfind(" ", 0, SUB_MAX)
                cut = cut if cut > SUB_MAX // 2 else SUB_MAX
                out.append(s[:cut].strip())
                s = s[cut:]
            if s.strip():
                out.append(s.strip())
    return title, out


def greedy_subchunks(units):
    """Жадно набираем ≤ SUB_MAX, шов — на начале пункта; гарантируем ≤ окна
    (если один юнит сам > окна — он отдельным сабчанком, уже после sentence-split)."""
    bins, cur, cum = [], [], 0
    for i, u in enumerate(units):
        if cur and cum + len(u) + 1 > SUB_MAX:
            bins.append("\n".join(cur))
            cur, cum = [], 0
        cur.append(u)
        cum += len(u) + 1
    if cur:
        bins.append("\n".join(cur))
    return bins


def main():
    cj = json.loads(paths.CODES_JSON.read_text(encoding="utf-8"))
    slugs = [k for k in cj if not k.startswith("_")]

    # перенос summary из текущего слоя
    carry = {}
    if CHUNKS.exists():
        for l in CHUNKS.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            r = json.loads(l)
            if r.get("kind") == "parent" and r.get("summary"):
                carry[(r["code"], r["article_no"])] = r["summary"]
    OUT.mkdir(parents=True, exist_ok=True)
    if CHUNKS.exists():
        (OUT / "chunks_top100_backup.jsonl").write_text(
            CHUNKS.read_text(encoding="utf-8"), encoding="utf-8")

    rows = []
    n_art = n_small = n_large = n_noanchor = n_repealed = 0
    carried = 0
    repealed_by_doc = {}
    for slug in slugs:
        code = cj[slug]["doc_id"]
        amap = json.loads((paths.MAPS / f"article_map_{slug}.json").read_text(encoding="utf-8"))
        soup = BeautifulSoup((paths.FINAL / f"{slug}_structured.html").read_text(encoding="utf-8"),
                             "html.parser")
        for d in soup.find_all("div", class_="article"):
            if "статья" not in (d.get("data-type") or ""):
                continue
            num = d.get("data-number")
            anc = amap.get(str(num))
            # ИСКЛЮЧЁННАЯ статья (единое правило для всех 25 док) — проверяем ДО якоря:
            # repealed бывает и без живого якоря (статья удалена из карты). parent
            # kind=repealed, текст = сноска, meta = закон/дата; не сабчанкуется, без
            # summary, ВНЕ индекса. Якоря нет -> синтетический chunk_id z{num}rep.
            if RE_REPEALED.search(d.get_text(" ")):
                rep_anc = anc or f"z{num}rep"
                foot, rmeta = repeal_meta(d)
                n_repealed += 1
                repealed_by_doc.setdefault(slug, []).append(str(num))
                rows.append({"chunk_id": rep_anc, "parent_id": None, "article_no": str(num),
                             "kind": "repealed", "order": 0, "doc_id": code, "code": slug,
                             "anchor": anc, "uid": f"{slug}_{rep_anc}", "article_title": "",
                             "text": foot, "char_len": len(foot), "summary": None,
                             "n_subchunks": 0, **rmeta})
                continue
            if not anc:
                n_noanchor += 1
                continue
            title, units = article_units(d)
            body = "\n".join(units)
            full = (title + "\n" + body) if title else body
            n_art += 1
            summary = carry.get((slug, str(num)))
            carried += summary is not None
            rows.append({"chunk_id": anc, "parent_id": None, "article_no": str(num),
                         "kind": "parent", "order": 0, "doc_id": code, "code": slug,
                         "anchor": anc, "uid": f"{slug}_{anc}",
                         "article_title": title, "text": full, "char_len": len(full),
                         "summary": summary})
            if len(body) > SPLIT_IF:
                n_large += 1
                subs = greedy_subchunks(units)
                rows[-1]["n_subchunks"] = len(subs)
                for i, st in enumerate(subs, 1):
                    rows.append({"chunk_id": f"{anc}_{i}", "parent_id": anc,
                                 "article_no": str(num), "kind": "subchunk", "order": i,
                                 "doc_id": code, "code": slug, "anchor": anc,
                                 "uid": f"{slug}_{anc}_{i}", "text": st, "char_len": len(st)})
            else:
                n_small += 1
                rows[-1]["n_subchunks"] = 0

    with CHUNKS.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    sub = [r for r in rows if r["kind"] == "subchunk"]
    over = sum(1 for r in sub if r["char_len"] > SPLIT_IF)
    import statistics as st
    L = ["# Полный чанкинг корпуса (вектор-слой)", "",
         f"25 документов, **{n_art} статей** -> parent-чанк на каждую (chunk_id = "
         f"якорь zX, не изменён). Окно эмбеддера ≈ {SPLIT_IF} симв; тело > окна "
         f"режется по смыслу на сабчанки ≤ {SUB_MAX} симв (additive zX_1..).", "",
         f"- мелких статей (тело ≤ окна, без сабчанков): **{n_small}**",
         f"- крупных (с сабчанками): **{n_large}**, сабчанков всего **{len(sub)}**",
         f"- ИСКЛЮЧЁННЫХ (kind=repealed, без сабчанков/summary, ВНЕ индекса): "
         f"**{n_repealed}** в {len(repealed_by_doc)} док.",
         f"- всего чанков: **{len(rows)}** ({n_art} parent + {len(sub)} subchunk "
         f"+ {n_repealed} repealed)",
         f"- сабчанков длиннее окна (должно быть 0): **{over}**",
         f"- длина сабчанка: медиана {int(st.median([r['char_len'] for r in sub]))}, "
         f"макс {max(r['char_len'] for r in sub)}",
         f"- статей без якоря в карте (пропущены): {n_noanchor}",
         f"- перенесено готовых summary (без DeepSeek): **{carried}**",
         "", "Реконструкция: склейка сабчанков = ТЕЛО статьи; заголовок в "
         "parent.text + meta.article_title (в сабчанки by-design не дублируется).",
         "Бэкап прежнего top-100 слоя: derived/vector_layer/chunks_top100_backup.jsonl."]
    (paths.REPORTS / "full_chunk_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[3:]))


if __name__ == "__main__":
    main()
