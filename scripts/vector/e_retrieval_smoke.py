# -*- coding: utf-8 -*-
"""ВЕКТОР-СЛОЙ, ретрив-смоук (что просил шеф «протести»). READ-ONLY.

Лёгкий мультиязычный эмбеддер (fastembed ONNX,
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2, ~0.22ГБ — НЕ large).
Схема small-to-big: эмбеддим summary parent-чанков + тексты сабчанков; ретрив
ВОЗВРАЩАЕТ полный текст родительской статьи. Индекс — косинус по numpy (faiss не
обязателен для 400 векторов). 10 разнородных запросов на русском → топ-3.

python scripts/vector/e_retrieval_smoke.py  -> дописывает раздел в reports/summary_eval.md
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

CHUNKS = paths.ROOT / "derived" / "vector_layer" / "chunks.jsonl"
# Модель/префиксы — из единого embedder (e5-large). NB: этот смоук РЕ-ЭМБЕДДИТ весь
# корпус инлайн (с e5 на CPU — долго); для рутинного поиска используй
# i_retrieval_eval (персистентный faiss-индекс, эмбеддит только запрос).

# (запрос, ожидаемая статья (code, article)) — все цели в наборе top-100
QUERIES = [
    ("налогообложение прибыли контролируемой иностранной компании", ("nalog", "335")),
    ("ответственность за отмывание доходов и финансирование терроризма", ("koap", "214")),
    ("доход от прироста стоимости при продаже недвижимого имущества", ("nalog", "383")),
    ("какие полномочия у маслихата местного представительного органа", ("mestnoe_upravlenie", "6")),
    ("государственный контроль за соблюдением законодательства об информатизации", ("informatizacii", "64-2")),
    ("общественные слушания по экологическим вопросам", ("ekologicheskiy", "73")),
    ("права и обязанности единого накопительного пенсионного фонда", ("socialnyy", "35")),
    ("в каких случаях проводятся государственные закупки", ("goszakup", "16")),
    ("собрание собственников квартир в многоквартирном доме", ("zhilishniy", "42")),
    ("основные понятия используемые в трудовом законодательстве", ("trudovoy", "1")),
]


def main():
    rows = [json.loads(l) for l in CHUNKS.read_text(encoding="utf-8").splitlines() if l.strip()]
    parents = {(r["code"], r["article_no"]): r for r in rows if r["kind"] == "parent"}
    if not all(p.get("summary") for p in parents.values()):
        sys.exit("STOP: не у всех parent есть summary — сперва c_summarize --all.")

    import embedder

    # заголовок статьи как КОНТЕКСТ при эмбеддинге сабчанка (chunks.jsonl не меняем —
    # это только представление для эмбеддинга; заголовок — сильный топик-сигнал)
    anc2title = {(r["code"], r["chunk_id"]): (r.get("article_title") or "")
                 for r in rows if r["kind"] == "parent"}
    # корпус: summary parent + тексты сабчанков; каждый -> родительская статья
    corpus, meta = [], []
    for r in rows:
        if r["kind"] == "parent" and r.get("summary"):
            corpus.append(r["summary"])
            meta.append((r["code"], r["article_no"], "summary"))
        elif r["kind"] == "subchunk":
            title = anc2title.get((r["code"], r["parent_id"]), "")
            text = (title + "\n" + r["text"]) if title else r["text"]
            corpus.append(text[:1800])           # заголовок-контекст + тело, окно эмбеддера
            meta.append((r["code"], r["parent_id"], "subchunk"))
    # parent_id сабчанка = anchor; сопоставим обратно к (code, article)
    anc2art = {(r["code"], r["chunk_id"]): r["article_no"]
               for r in rows if r["kind"] == "parent"}
    meta = [(c, anc2art.get((c, a), a), kind) for (c, a, kind) in meta]

    M = embedder.encode_passages(corpus)                       # 'passage: ' + L2-норм
    Q = embedder.encode_queries([q for q, _ in QUERIES], show=False)   # 'query: ' + L2-норм

    L = ["", "## Ретрив-смоук (small-to-big)", "",
         f"Эмбеддер: `{embedder.MODEL}` ({embedder.DIM}-dim, e5, префиксы "
         f"passage:/query:). Индекс: косинус "
         f"(numpy) по {len(corpus)} векторам (summary parent + сабчанки). Ретрив "
         "возвращает полный текст родительской статьи. 10 запросов, топ-3 разных "
         "статей.", "", "| запрос | ожидалось | топ-3 (статья: score) | вердикт |",
         "|---|---|---|---|"]
    hits = 0
    examples = []
    for qi, (q, exp) in enumerate(QUERIES):
        sims = M @ Q[qi]
        order = np.argsort(-sims)
        seen, top = [], []
        for j in order:
            art = (meta[j][0], meta[j][1])
            if art in seen:
                continue
            seen.append(art)
            top.append((art, float(sims[j])))
            if len(top) == 3:
                break
        got = [a for a, _ in top]
        ok = exp in got
        rank = got.index(exp) + 1 if ok else None
        hits += ok
        cell = ", ".join(f"{c}/{a}: {s:.2f}" for (c, a), s in top)
        L.append(f"| {q[:46]} | {exp[0]}/{exp[1]} | {cell} | "
                 f"{'✅ #' + str(rank) if ok else '❌ мимо'} |")
        if qi < 4:
            par = parents[exp]
            examples.append(
                f"**Запрос:** «{q}»\n  - топ-1: {top[0][0][0]}/{top[0][0][1]} "
                f"(score {top[0][1]:.2f}); ожидалось {exp[0]}/{exp[1]} → "
                f"{'найдено #' + str(rank) if ok else 'не в топ-3'}\n"
                f"  - возвращён payload (родитель {par['uid']}, {par['char_len']} симв): "
                f"«{(par['article_title'] or par['text'][:50])[:60]}…»")
    L += ["", f"**Итог: {hits}/10 запросов — нужная статья в топ-3.**", "",
          "### Примеры (запрос → что нашлось → payload)", ""] + examples
    p = paths.REPORTS / "summary_eval.md"
    p.write_text(p.read_text(encoding="utf-8").rstrip() + "\n" + "\n".join(L) + "\n",
                 encoding="utf-8")
    print(f"ретрив-смоук: {hits}/10 в топ-3 -> дописано в {p.name}")
    for e in examples:
        print(e.replace("**", "").replace("  - ", "    "))


if __name__ == "__main__":
    main()
