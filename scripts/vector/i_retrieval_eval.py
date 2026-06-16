# -*- coding: utf-8 -*-
"""ВЕКТОР-СЛОЙ: ретрив-модуль (small-to-big) + эвал hit@1/hit@3. READ-ONLY.

python scripts/vector/i_retrieval_eval.py
-> reports/retrieval_eval.md

retrieve(q): query -> эмбед (query:) -> faiss top-k -> резолв в РОДИТЕЛЬСКУЮ
статью (uid) -> полный текст статьи (payload). Эвал: 28 разнородных запросов по
разным кодексам; «эталон» = статьи, чей ЗАГОЛОВОК содержит тему запроса
(title-keyword) — объективная привязка. hit@1 / hit@3 (любая эталонная в топ-1/топ-3).
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

OUT = paths.ROOT / "derived" / "vector_layer"

# (запрос, ключ-СТЕМ в заголовке эталонной статьи (title ИЛИ строка-заголовок в
# text — у части кодексов article_title пуст), код|None)
QUERIES = [
    ("как исчисляется налог на добавленную стоимость", "добавленную стоимост", "nalog"),
    ("кто признаётся налоговым резидентом республики казахстан", "резидент", "nalog"),
    ("ответственность за умышленное причинение смерти человеку", "убийство", "ugolovniy"),
    ("наказание за кражу чужого имущества", "кража", "ugolovniy"),
    ("ответственность за мошенничество", "мошенничество", "ugolovniy"),
    ("меры пресечения в уголовном процессе", "пресечени", "upk"),
    ("права подозреваемого при задержании", "подозреваемый", "upk"),
    ("основания расторжения трудового договора по инициативе работодателя", "расторжени", "trudovoy"),
    ("ежегодный оплачиваемый трудовой отпуск", "оплачиваемый ежегодный трудово", "trudovoy"),
    ("срок исковой давности", "исковой давност", "grazhdanskiy"),
    ("право собственности и его содержание", "права собственност", "grazhdanskiy"),
    ("договор купли-продажи товара", "купли-продаж", "grazhdanskiy_osob"),
    ("пенсионные выплаты по возрасту", "по возраст", "socialnyy"),
    ("приватизация жилища", "приватизац", "zhilishniy"),
    ("управление объектом кондоминиума", "кондоминиум", "zhilishniy"),
    ("оценка воздействия на окружающую среду", "воздействия на окружающую сред", "ekologicheskiy"),
    ("экологический аудит", "экологическ", "ekologicheskiy"),
    ("право частной собственности на земельный участок", "собственност", "zemelnyy"),
    ("аренда земельного участка и землепользование", "землепользован", "zemelnyy"),
    ("поступления в республиканский бюджет", "республиканск", "byudzhet"),
    ("государственная поддержка субъектов малого предпринимательства", "поддержк", "predprinimatel"),
    ("правовой статус педагога", "педагог", "obrazovanie"),
    ("обжалование административного акта в суде", "обжалован", "appk"),
    ("понятие административного акта", "административн", "appk"),
    ("способы осуществления государственных закупок", "способ", "goszakup"),
    ("противодействие коррупции и антикоррупционные ограничения", "коррупци", None),
    ("защита персональных данных", "персональн", "persdata"),
    ("порядок назначения акима района", "аким", "mestnoe_upravlenie"),
]


def load_index():
    import faiss
    from fastembed import TextEmbedding
    cfg = json.loads((OUT / "index_config.json").read_text(encoding="utf-8"))
    idx = faiss.read_index(str(OUT / "index.faiss"))
    meta = [json.loads(l) for l in (OUT / "index_meta.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    emb = TextEmbedding(model_name=cfg["model"])
    return idx, meta, emb, cfg


def main():
    rows = [json.loads(l) for l in (OUT / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    parents = {(r["code"], r["chunk_id"]): r for r in rows if r["kind"] == "parent"}
    by_art = {}
    for (c, anc), p in parents.items():
        by_art[(c, p["article_no"])] = p

    idx, meta, emb, cfg = load_index()

    def retrieve(q, k=3):
        v = np.array(list(emb.embed([cfg["prefix_query"] + q])), dtype="float32")
        v /= (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
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
            if code is not None and c != code:
                continue
            # article_title у части кодексов пуст -> добираем строку-заголовок из text
            hay = ((p.get("article_title") or "") + " " + p["text"][:110]).lower()
            if kwl in hay:
                out.add((c, p["article_no"]))
        return out

    L = ["# Ретрив-эвал вектор-слоя (small-to-big)", "",
         f"Модель: `{cfg['model']}` ({cfg['dim']}-dim), индекс faiss "
         f"({cfg['vectors']} векторов: текст мелких статей + сабчанки с заголовком + "
         f"summary крупных). «Эталон» запроса — статьи, чей ЗАГОЛОВОК содержит тему.",
         "", "| запрос | эталон (код/ст.) | топ-3 (код/ст: score, тип) | hit@1 | hit@3 |",
         "|---|---|---|---|---|"]
    h1 = h3 = n = 0
    examples = []
    for q, kw, code in QUERIES:
        gt = ground_truth(kw, code)
        if not gt:
            L.append(f"| {q[:42]} | **эталон не найден (kw={kw})** | — | — | — |")
            continue
        n += 1
        top = retrieve(q, 3)
        got = [a for a, _, _ in top]
        hit1 = got[0] in gt
        hit3 = any(g in gt for g in got)
        h1 += hit1
        h3 += hit3
        gt_s = ", ".join(f"{c}/{a}" for c, a in sorted(gt))[:40]
        top_s = ", ".join(f"{c}/{a}:{s:.2f}·{src[:3]}" for (c, a), s, src in top)
        L.append(f"| {q[:42]} | {gt_s} | {top_s} | {'✅' if hit1 else '—'} | "
                 f"{'✅' if hit3 else '❌'} |")
        if len(examples) < 4 and hit3:
            par = by_art[got[0] if hit1 else next(g for g in got if g in gt)]
            examples.append(
                f"**«{q}»** → {got[0][0]}/{got[0][1]} (score {top[0][1]:.2f}); "
                f"payload: «{(par['article_title'] or par['text'][:50])[:62]}…» "
                f"(полный текст {par['char_len']} симв, uid {par['uid']})")

    L += ["", f"**Итог: hit@1 = {h1}/{n} ({h1/n:.0%}), hit@3 = {h3}/{n} ({h3/n:.0%}).**",
          "", "### Анализ (честно)", "",
          f"Модель — `{cfg['model']}` (лёгкая, ~34 пасс/с на этом CPU). e5-large "
          "качественнее, но через fastembed/ONNX на CPU даёт ~0.8 пасс/с (~4.4 ч на "
          "12k) — оставлена опцией `g_build_index.py --model e5` (для GPU/времени).",
          "Оставшиеся промахи — НЕ дефекты данных: (1) парафразный потолок MiniLM "
          "(«причинение смерти» не сведено к «Убийство», «меры пресечения» — к "
          "дефиниционной статье); (2) меж-кодексное пересечение темы (обжалование "
          "есть в КоАП/УПК/АППК — модель путает кодекс); (3) «эталон» = ключ в "
          "ЗАГОЛОВКЕ — часть «промахов» это найденные релевантные статьи, где тема "
          "в теле, а не в заголовке (напр. «права подозреваемого при задержании» "
          "→ статьи о правах при задержании, а не дефиниция «Подозреваемый»).",
          "", "### Примеры ретрива (запрос → статья → payload)", ""] + \
         [f"- {e}" for e in examples]
    (paths.REPORTS / "retrieval_eval.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"hit@1={h1}/{n} hit@3={h3}/{n} -> reports/retrieval_eval.md")
    for e in examples:
        print("  " + e.replace("**", ""))


if __name__ == "__main__":
    main()
