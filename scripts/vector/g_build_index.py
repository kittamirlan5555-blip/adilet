# -*- coding: utf-8 -*-
"""ВЕКТОР-СЛОЙ: построение faiss-индекса (e5-large). READ-ONLY к chunks.jsonl.

python scripts/vector/g_build_index.py
-> derived/vector_layer/index.faiss        (персистентный)
-> derived/vector_layer/index_meta.jsonl   (строка индекса -> parent uid/код/статья)
-> derived/vector_layer/index_config.json

Эмбеддим (e5-large, префикс passage:):
  • мелкие статьи (без сабчанков) — текст статьи напрямую;
  • сабчанки крупных — с «Статья N. Название» в начале (контекст, +точность);
  • summary крупных статей.
Каждый вектор -> родительская статья (small-to-big payload через uid).
Индекс — косинус (IndexFlatIP по L2-нормированным). КЛЮЧЕЙ/СЕКРЕТОВ в индексе нет
(только тексты НПА + summary).
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

OUT = paths.ROOT / "derived" / "vector_layer"
CHUNKS = OUT / "chunks.jsonl"
# По умолчанию MiniLM: e5-large через fastembed/ONNX на этом CPU даёт ~0.8 пасс/с
# (~4.4 ч на 12k — неприемлемо); MiniLM ~43 пасс/с (~5 мин), смоук показал 10/10.
# Принудительно e5-large: --model e5 (медленно, но качество выше — если есть GPU/время).
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
E5 = "intfloat/multilingual-e5-large"
WIN = 1800
BATCH = 64


def main():
    rows = [json.loads(l) for l in CHUNKS.read_text(encoding="utf-8").splitlines() if l.strip()]
    parents = {(r["code"], r["chunk_id"]): r for r in rows if r["kind"] == "parent"}
    title_of = {k: (p.get("article_title") or "") for k, p in parents.items()}

    passages, meta = [], []
    for r in rows:
        if r["kind"] == "parent":
            if r.get("n_subchunks", 0) == 0:                 # мелкая статья — целиком
                passages.append(r["text"][:WIN]); src = "article"
            elif r.get("summary"):                            # крупная — summary
                passages.append(r["summary"][:WIN]); src = "summary"
            else:
                continue
            meta.append((r["uid"], r["code"], r["article_no"], r["chunk_id"], src))
        else:                                                 # сабчанк (+заголовок-контекст)
            title = title_of.get((r["code"], r["parent_id"]), "")
            txt = (title + "\n" + r["text"]) if title else r["text"]
            passages.append(txt[:WIN])
            meta.append((r["uid"], r["code"], r["article_no"], r["parent_id"], "subchunk"))

    import time
    from fastembed import TextEmbedding
    model = E5 if "--model" in sys.argv and "e5" in sys.argv[sys.argv.index("--model") + 1] else MODEL
    emb = TextEmbedding(model_name=model)
    pref = "passage: " if "e5" in model else ""
    print(f"эмбеддинг {len(passages)} пассажей: {model}, batch {BATCH}…", flush=True)
    vlist, t0 = [], time.time()
    for i, v in enumerate(emb.embed([pref + p for p in passages], batch_size=BATCH), 1):
        vlist.append(v)
        if i % 2000 == 0 or i == len(passages):
            print(f"  {i}/{len(passages)}  ({i/(time.time()-t0):.0f} пасс/с)", flush=True)
    vecs = np.array(vlist, dtype="float32")
    vecs /= (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9)

    import faiss
    idx = faiss.IndexFlatIP(vecs.shape[1])
    idx.add(vecs)
    faiss.write_index(idx, str(OUT / "index.faiss"))
    with (OUT / "index_meta.jsonl").open("w", encoding="utf-8") as f:
        for uid, code, art, anc, src in meta:
            f.write(json.dumps({"uid": uid, "code": code, "article": art,
                                "anchor": anc, "src": src}, ensure_ascii=False) + "\n")
    (OUT / "index_config.json").write_text(json.dumps(
        {"model": model, "dim": int(vecs.shape[1]), "vectors": len(passages),
         "prefix_query": "query: " if "e5" in model else "",
         "prefix_passage": pref, "metric": "cosine(IP/normalized)"},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"индекс: {len(passages)} векторов, dim {vecs.shape[1]}, модель {model} "
          f"-> index.faiss + index_meta.jsonl")


if __name__ == "__main__":
    main()
