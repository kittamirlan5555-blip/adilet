# -*- coding: utf-8 -*-
"""ФАЗА B: демонстрация small-to-big на 10 запросах по НОВЫМ законам (не corpus-43).

Каждый запрос: query -> e5(query:) -> faiss top-k -> берём попавший ПАССАЖ
(сабчанк/summary/мелкую статью) -> резолвим в РОДИТЕЛЬСКУЮ статью (uid) ->
отдаём ПОЛНЫЙ текст статьи. Показываем: тип попавшего пассажа (src) и что
родительская статья — та, что ожидалась (ключ в заголовке). READ-ONLY.

python scripts/vector/phase_b_newlaw_eval.py  ->  reports/phase_b_newlaw_eval.md
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

OUT = paths.ROOT / "derived" / "vector_layer"

# (запрос, ключ-СТЕМ в заголовке эталонной статьи, код нового закона, человеч. имя закона)
QUERIES = [
    ("охрана государственной границы республики казахстан", "охрана государственной границы", "Z1300000070", "О Государственной границе РК"),
    ("какие бывают отрасли классы и виды страхования", "отрасли, классы и виды страхования", "Z000000126_", "О страховой деятельности"),
    ("каков правовой статус банка второго уровня", "правовой статус банка", "Z2600000258", "О банках и банковской деятельности (2026)"),
    ("какие существуют виды автомобильных перевозок", "виды автомобильных перевозок", "Z030000476_", "Об автомобильном транспорте"),
    ("единая дежурно-диспетчерская служба 112", "112", "Z1400000188", "О гражданской защите"),
    ("кто является субъектом управления государственным имуществом", "субъекты управления государственным имуществом", "Z1100000413", "О государственном имуществе"),
    ("ответственность за преднамеренное банкротство должника", "преднамеренное банкротство", "Z1400000176", "О реабилитации и банкротстве"),
    ("какие документы являются исполнительными", "перечень исполнительных документов", "Z100000261_", "Об исполнительном производстве"),
    ("что такое магистральная железнодорожная сеть", "магистральная железнодорожная сеть", "Z010000266_", "О железнодорожном транспорте"),
    ("государственное регулирование рынка ценных бумаг", "государственное регулирование рынка ценных бумаг", "Z030000461_", "О рынке ценных бумаг"),
]


def main():
    rows = [json.loads(l) for l in (OUT / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    parents = {(r["code"], r["chunk_id"]): r for r in rows if r["kind"] == "parent"}
    by_art = {}
    for (c, anc), p in parents.items():
        by_art[(c, p["article_no"])] = p

    import faiss
    import embedder
    cfg = json.loads((OUT / "index_config.json").read_text(encoding="utf-8"))
    idx = faiss.read_index(str(OUT / "index.faiss"))
    meta = [json.loads(l) for l in (OUT / "index_meta.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    def retrieve(q, k=3):
        v = embedder.encode_queries([q], show=False)
        D, I = idx.search(v, 60)
        out, seen = [], set()
        for rank, j in enumerate(I[0]):
            m = meta[j]
            key = (m["code"], m["article"])
            if key in seen:
                continue
            seen.add(key)
            out.append((key, float(D[0][rank]), m["src"]))
            if len(out) == k:
                break
        return out

    def ground_truth(kw, code):
        kwl = kw.lower()
        out = set()
        for (c, anc), p in parents.items():
            if c != code:
                continue
            hay = ((p.get("article_title") or "") + " " + p["text"][:110]).lower()
            if kwl in hay:
                out.add((c, p["article_no"]))
        return out

    L = ["# Фаза B — small-to-big на новых законах (10 запросов)", "",
         f"Индекс: `{cfg['model']}` ({cfg['dim']}-dim), {cfg['vectors']} векторов. "
         "Демонстрация: запрос → e5 → faiss top-k → попавший **пассаж** (сабчанк/"
         "summary/мелкая статья) → резолв в **родительскую статью** → её ПОЛНЫЙ текст.",
         "", "| запрос | закон | ожид. ст. | top-1 (код/ст: score, тип пассажа) | hit@1 | hit@3 |",
         "|---|---|---|---|---|---|"]
    h1 = h3 = 0
    examples = []
    for q, kw, code, name in QUERIES:
        gt = ground_truth(kw, code)
        top = retrieve(q, 3)
        got = [a for a, _, _ in top]
        hit1 = bool(gt) and got[0] in gt
        hit3 = bool(gt) and any(g in gt for g in got)
        h1 += hit1
        h3 += hit3
        gt_s = ", ".join(f"{a}" for c, a in sorted(gt)) if gt else "—"
        (c0, a0), s0, src0 = top[0]
        L.append(f"| {q[:40]} | {name[:26]} | {gt_s[:16]} | {c0}/{a0}:{s0:.2f}·{src0} | "
                 f"{'✅' if hit1 else '—'} | {'✅' if hit3 else '❌'} |")
        # small-to-big: показать резолв в полный текст родителя
        tgt = got[0] if hit1 else (next((g for g in got if g in gt), got[0]) if gt else got[0])
        par = by_art.get(tgt)
        if par and len(examples) < 5:
            title = par.get("article_title") or par["text"][:60]
            examples.append(
                f"**«{q}»** → пассаж-тип `{src0}` → родитель **{tgt[0]}/ст.{tgt[1]}** "
                f"«{title[:70]}» → полный текст {par['char_len']} симв "
                f"(n_subchunks={par.get('n_subchunks',0)}, uid {par['uid']})")

    n = len(QUERIES)
    L += ["", f"**Итог (новые законы): hit@1 = {h1}/{n} ({h1/n:.0%}), "
          f"hit@3 = {h3}/{n} ({h3/n:.0%}).**", "",
          "### Small-to-big — примеры (запрос → пассаж → полный текст родителя)", ""] + \
         [f"- {e}" for e in examples]
    (paths.REPORTS / "phase_b_newlaw_eval.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"NEW-LAW: hit@1={h1}/{n} hit@3={h3}/{n} -> reports/phase_b_newlaw_eval.md")
    for e in examples:
        print("  " + e.replace("**", ""))


if __name__ == "__main__":
    main()
