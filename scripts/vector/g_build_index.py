# -*- coding: utf-8 -*-
"""ВЕКТОР-СЛОЙ: построение faiss-индекса (e5-large). READ-ONLY к chunks.jsonl.

python scripts/vector/g_build_index.py
-> derived/vector_layer/index.faiss        (персистентный)
-> derived/vector_layer/index_meta.jsonl   (строка индекса -> parent uid/код/статья)
-> derived/vector_layer/index_config.json

Эмбеддим (e5-large, префикс passage: — см. embedder.py):
  • мелкие статьи (без сабчанков) — текст статьи напрямую;
  • сабчанки крупных — с «Статья N. Название» в начале (контекст, +точность);
  • summary крупных статей.
repealed — ВНЕ индекса. Каждый вектор -> родительская статья (small-to-big payload
через uid). Индекс — косинус (IndexFlatIP по L2-нормированным эмбеддингам e5).
КЛЮЧЕЙ/СЕКРЕТОВ в индексе нет (только тексты НПА + summary).

Конструирование пассажей вынесено в build_passages() — её же использует
h_token_audit (аудит лимита 512 токенов), чтобы мерить РОВНО то, что индексируется.
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

OUT = paths.ROOT / "derived" / "vector_layer"
CHUNKS = OUT / "chunks.jsonl"
WIN = 1800          # символьное окно пассажа (унаследовано; ≈512 токенов e5, см. h_token_audit)
BATCH = 32


def build_passages(rows, win=WIN):
    """Из chunks-строк собирает (passages, meta) ровно как для индекса.

    win — символьное окно (None = без обрезки, для аудита истинной длины).
    meta: список (uid, code, article_no, anchor, src), src ∈ {article,summary,subchunk}.
    """
    parents = {(r["code"], r["chunk_id"]): r for r in rows if r["kind"] == "parent"}
    title_of = {k: (p.get("article_title") or "") for k, p in parents.items()}

    def cut(s):
        return s if win is None else s[:win]

    passages, meta = [], []
    for r in rows:
        if r["kind"] == "repealed":                       # исключённые — ВНЕ индекса
            continue
        if r["kind"] == "parent":
            if r.get("n_subchunks", 0) == 0:              # мелкая статья — целиком
                passages.append(cut(r["text"])); src = "article"
            elif r.get("summary"):                        # крупная — summary
                passages.append(cut(r["summary"])); src = "summary"
            else:
                continue
            meta.append((r["uid"], r["code"], r["article_no"], r["chunk_id"], src))
        else:                                             # сабчанк (+заголовок-контекст)
            title = title_of.get((r["code"], r["parent_id"]), "")
            txt = (title + "\n" + r["text"]) if title else r["text"]
            passages.append(cut(txt))
            meta.append((r["uid"], r["code"], r["article_no"], r["parent_id"], "subchunk"))
    return passages, meta


def _load_from_vectors(vec_path, ids_path):
    """BLOCK E: индекс из ГОТОВЫХ векторов embed_kit (эмбеддинг на 5090), без GPU/модели.
    Сверяет ids.jsonl с build_passages(chunks) — порядок и uid должны совпасть 1-в-1."""
    import numpy as np
    rows = [json.loads(l) for l in CHUNKS.read_text(encoding="utf-8").splitlines() if l.strip()]
    _, meta = build_passages(rows)
    ids = [json.loads(l) for l in Path(ids_path).read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(ids) != len(meta):
        sys.exit(f"STOP: ids.jsonl {len(ids)} != пассажей chunks {len(meta)} — векторы от ДРУГОГО chunks.jsonl")
    mism = sum(1 for a, b in zip(ids, meta) if a["uid"] != b[0])
    if mism:
        sys.exit(f"STOP: {mism} несовпадений uid между ids.jsonl и chunks — не тот прогон")
    vecs = np.load(vec_path).astype("float32")
    if vecs.shape[0] != len(meta):
        sys.exit(f"STOP: vectors.npy {vecs.shape[0]} != пассажей {len(meta)}")
    # ре-нормализуем на всякий (fp16 GPU мог чуть сбить L2)
    import numpy as _np
    n = _np.linalg.norm(vecs, axis=1, keepdims=True); n[n == 0] = 1.0
    vecs = vecs / n
    print(f"из готовых векторов: {vecs.shape[0]} шт, dim {vecs.shape[1]}, "
          f"uid-сверка с chunks: OK")
    return vecs, [(m[0], m[1], m[2], m[3], m[4]) for m in meta]


def main():
    if "--from-vectors" in sys.argv:
        vp = sys.argv[sys.argv.index("--from-vectors") + 1]
        ip = sys.argv[sys.argv.index("--ids") + 1] if "--ids" in sys.argv else str(Path(vp).with_name("ids.jsonl"))
        vecs, meta = _load_from_vectors(vp, ip)
        MODEL = "intfloat/multilingual-e5-large"; QP, PP, MT = "query: ", "passage: ", 512
        import faiss
        idx = faiss.IndexFlatIP(vecs.shape[1]); idx.add(vecs)
        faiss.write_index(idx, str(OUT / "index.faiss"))
        with (OUT / "index_meta.jsonl").open("w", encoding="utf-8") as f:
            for uid, code, art, anc, src in meta:
                f.write(json.dumps({"uid": uid, "code": code, "article": art,
                                    "anchor": anc, "src": src}, ensure_ascii=False) + "\n")
        (OUT / "index_config.json").write_text(json.dumps(
            {"model": MODEL, "dim": int(vecs.shape[1]), "vectors": len(meta),
             "prefix_query": QP, "prefix_passage": PP, "metric": "cosine(IP/normalized)",
             "max_tokens": MT, "char_window": WIN,
             "embedded_on": os.environ.get("EMBED_DEVICE_NOTE", "GPU/embed_kit")},
            ensure_ascii=False, indent=1), encoding="utf-8")
        # проверка: repealed вне индекса (в meta их быть не может by build_passages)
        rep = sum(1 for m in meta if m[4] == "repealed")
        print(f"индекс: {len(meta)} векторов, repealed в индексе={rep} (цель 0) "
              f"-> index.faiss + index_meta.jsonl + index_config.json")
        return

    rows = [json.loads(l) for l in CHUNKS.read_text(encoding="utf-8").splitlines() if l.strip()]
    passages, meta = build_passages(rows)

    import embedder
    print(f"эмбеддинг {len(passages)} пассажей: {embedder.MODEL} "
          f"(префикс '{embedder.PASSAGE_PREFIX}'), batch {BATCH}…", flush=True)
    t0 = time.time()
    vecs = embedder.encode_passages(passages, batch_size=BATCH)   # уже L2-норм, float32
    print(f"  готово за {time.time() - t0:.0f}с, dim {vecs.shape[1]}", flush=True)
    assert vecs.shape[0] == len(passages), "число векторов != числа пассажей"

    import faiss
    idx = faiss.IndexFlatIP(vecs.shape[1])
    idx.add(vecs)
    faiss.write_index(idx, str(OUT / "index.faiss"))
    with (OUT / "index_meta.jsonl").open("w", encoding="utf-8") as f:
        for uid, code, art, anc, src in meta:
            f.write(json.dumps({"uid": uid, "code": code, "article": art,
                                "anchor": anc, "src": src}, ensure_ascii=False) + "\n")
    (OUT / "index_config.json").write_text(json.dumps(
        {"model": embedder.MODEL, "dim": int(vecs.shape[1]), "vectors": len(passages),
         "prefix_query": embedder.QUERY_PREFIX, "prefix_passage": embedder.PASSAGE_PREFIX,
         "metric": "cosine(IP/normalized)", "max_tokens": embedder.MAX_TOKENS,
         "char_window": WIN},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"индекс: {len(passages)} векторов, dim {vecs.shape[1]}, модель {embedder.MODEL} "
          f"-> index.faiss + index_meta.jsonl + index_config.json")


if __name__ == "__main__":
    main()
