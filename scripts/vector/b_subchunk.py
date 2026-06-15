# -*- coding: utf-8 -*-
"""ВЕКТОР-СЛОЙ, ФАЗА B: большие статьи -> сабчанки. ОТДЕЛЬНЫЙ JSON-слой.

python scripts/vector/b_subchunk.py [--top 100]
-> derived/vector_layer/chunks.jsonl   (parent + сабчанки, без summary)
-> reports/subchunk_report.md          (порог «большой», статистика)

ЖЕЛЕЗНЫЕ ПРАВИЛА: HTML/якоря zX НЕ трогаем (читаем только). chunk_id parent = zX
(якорь статьи из article_map), сабчанки = zX_1/_2/_3 (additive). Текст статей не
редактируем — извлекаем как есть. Сегментация по СМЫСЛУ: целые пункты группируются
в 2-3 непрерывных (по порядку) сабчанка примерно поровну по длине.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
from bs4 import BeautifulSoup

OUT_DIR = paths.ROOT / "derived" / "vector_layer"
RE_PUNKT = re.compile(r"^\s*\d+(?:-\d+)?[.)]\s")      # начало пункта/подпункта «N.»/«N)»
RE_TITLE = re.compile(r"^\s*Стать\w*\s+\d")
RE_SENT = re.compile(r"(?<=[.;])\s+(?=[А-ЯЁ0-9])")


def article_units(div):
    """(title, [units]) — title + АТОМАРНЫЕ единицы (по абзацу <p>). Один гигантский
    абзац без разрывов рубим на предложения, чтобы было что балансировать."""
    ps = [p.get_text(" ", strip=True) for p in div.find_all("p")]
    ps = [t for t in ps if t]
    title = ps[0] if ps and RE_TITLE.match(ps[0]) else ""
    units = ps[1:] if title else ps
    if len(units) <= 1 and units and len(units[0]) > 1200:
        units = [s for s in RE_SENT.split(units[0]) if s.strip()]
    return title, units


def split_contiguous(units, k):
    """Непрерывное (порядок сохранён) разбиение на k частей ~поровну по длине;
    границу при возможности сдвигаем на начало пункта «N.»/«N)» (смысловой шов)."""
    k = max(1, min(k, len(units)))
    if k == 1:
        return ["\n".join(units)]
    total = sum(len(u) for u in units)
    target = total / k
    bins, cur, cum = [], [], 0
    for i, u in enumerate(units):
        cur.append(u)
        cum += len(u)
        parts_left = k - len(bins) - 1
        units_left = len(units) - i - 1
        if parts_left <= 0 or units_left < parts_left:
            continue
        nxt_is_punkt = (i + 1 < len(units) and RE_PUNKT.match(units[i + 1]))
        thresh = target * (len(bins) + 1)
        # рубим, когда добрали целевую долю И следующий абзац — новый пункт,
        # либо когда заметно перебрали (≥1.25×) — чтобы не раздуть один бин
        if cum >= thresh and (nxt_is_punkt or cum >= thresh * 1.25):
            bins.append("\n".join(cur))
            cur = []
    if cur:
        bins.append("\n".join(cur))
    return bins


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=100)
    args = ap.parse_args()
    cj = json.loads(paths.CODES_JSON.read_text(encoding="utf-8"))
    slugs = [k for k in cj if not k.startswith("_")]

    # ---- собрать длины всех статей по корпусу ----
    cat = []   # (char_len, slug, num, anchor, title, atoms)
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
            if not anc:
                continue
            title, units = article_units(d)
            body = "\n".join(units)
            cat.append((len(body), slug, code, num, anc, title, units, body))

    cat.sort(key=lambda x: -x[0])
    top = cat[:args.top]
    threshold = top[-1][0]

    # ---- сборка чанков ----
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    nsub = []
    for clen, slug, code, num, anc, title, units, body in top:
        full = (title + "\n" + body) if title else body
        k = 3 if (clen >= 2500 and len(units) >= 3) else (2 if len(units) >= 2 else 1)
        subs = split_contiguous(units, k)
        nsub.append(len(subs))
        # parent
        rows.append({"chunk_id": anc, "parent_id": None, "article_no": str(num),
                     "kind": "parent", "order": 0, "doc_id": code, "code": slug,
                     "anchor": anc, "uid": f"{slug}_{anc}",
                     "article_title": title, "text": full, "char_len": len(full),
                     "n_subchunks": len(subs), "summary": None})
        for i, st in enumerate(subs, 1):
            rows.append({"chunk_id": f"{anc}_{i}", "parent_id": anc,
                         "article_no": str(num), "kind": "subchunk", "order": i,
                         "doc_id": code, "code": slug, "anchor": anc,
                         "uid": f"{slug}_{anc}_{i}", "text": st, "char_len": len(st)})

    out = OUT_DIR / "chunks.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter
    dist = Counter(nsub)
    bydoc = Counter(r["code"] for r in rows if r["kind"] == "parent")
    # реконструкция: склейка сабчанков == тело статьи (parent.text без заголовка)
    sq = lambda s: "".join(s.split())
    subs_by_par = {}
    for r in rows:
        if r["kind"] == "subchunk":
            subs_by_par.setdefault((r["code"], r["parent_id"]), []).append(r)
    rec_exact = rec_body = rec_loss = 0
    for p in (r for r in rows if r["kind"] == "parent"):
        kids = sorted(subs_by_par.get((p["code"], p["chunk_id"]), []), key=lambda x: x["order"])
        joined = sq("\n".join(k["text"] for k in kids))
        ptext, title = sq(p["text"]), sq(p.get("article_title") or "")
        if joined == ptext:
            rec_exact += 1
        elif title and joined == ptext[len(title):]:
            rec_body += 1
        else:
            rec_loss += 1
    L = ["# Сабчанкинг больших статей (вектор-слой, Фаза B)", "",
         f"Источник «больших»: готового набора 100 в репо нет -> взяты **top-{args.top} "
         f"статей по длине тела** (символы get_text). **Порог «большой» = {threshold} "
         f"символов** (длина 100-й статьи; самая длинная — {top[0][0]}).",
         "", f"Чанков всего: **{len(rows)}** = {args.top} parent + {len(rows)-args.top} сабчанков.",
         f"Сабчанков на статью: " + ", ".join(f"{k}→{v} статей" for k, v in sorted(dist.items())),
         "", "Поля чанка: chunk_id, parent_id, article_no, text, char_len, order "
         "(+ doc_id, code, anchor, uid, kind; summary — на parent, Фаза C).",
         "chunk_id parent = якорь статьи zX (НЕ изменён); сабчанк = zX_1/_2/_3 "
         "(additive). Глобальный ключ — uid = `{code}_{zX}` (zX не уникален между "
         "документами).", "",
         "## Реконструкция", "",
         f"Сабчанки реконструируют **ТЕЛО** статьи: склейка `text` сабчанков по "
         f"`order` равна телу статьи — **тело сходится {rec_exact + rec_body}/"
         f"{args.top}, потерь контента {rec_loss}**. Заголовок «Статья N. Название» "
         "в сабчанки НЕ дублируется (by-design); он хранится в `parent.text` "
         f"(целиком) и в `meta.article_title`. Посимвольное совпадение со ВСЕМ "
         f"`parent.text` — **{rec_exact}/{args.top}** (статьи без строки-заголовка); "
         f"у остальных **{rec_body}/{args.top}** разница ровно на заголовок.", "",
         "## Распределение top-100 по документам", "",
         "| документ | больших статей |", "|---|---|"]
    for c, n in bydoc.most_common():
        L.append(f"| {c} | {n} |")
    (paths.REPORTS / "subchunk_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"порог={threshold} симв; чанков {len(rows)} ({args.top} parent + "
          f"{len(rows)-args.top} sub); распределение сабчанков {dict(dist)}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
