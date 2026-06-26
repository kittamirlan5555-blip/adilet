# -*- coding: utf-8 -*-
"""НОЧНОЙ пересбор e5-индекса в фоне. Самодостаточный, устойчивый, всё в лог.

Пишет reports/e5_build.log с таймстампами: прогресс эмбеддинга (≥ раз в ~2 мин),
запись index.faiss/meta/config, валидацию и sanity-поиск. Любое падение ловится и
пишется в лог с трейсбэком (видно, ГДЕ упал). Текст чанков НЕ меняется.

Эмбеддинг: passage:-префикс, L2-норма, dim=1024 (см. embedder.py). Для скорости
пассажи сортируются по длине (бакетинг → меньше паддинга), потом порядок векторов
восстанавливается — на корректность не влияет.

Запуск (детачнуто, переживает отключение):
    HF_HUB_OFFLINE=1 python scripts/vector/run_e5_overnight.py
"""
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
import embedder
import g_build_index as g
import i_retrieval_eval as iv          # только ради iv.QUERIES (28 запросов с эталонами)

OUT = paths.ROOT / "derived" / "vector_layer"
LOG = paths.REPORTS / "e5_build.log"
BATCH = 32
PROGRESS_EVERY_SEC = 120


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
    print(line, flush=True)


def build(rows):
    import numpy as np
    passages, meta = g.build_passages(rows)
    log(f"пассажей к эмбеддингу: {len(passages)} (ожид 17786)")
    model = embedder.get_model()
    log(f"модель: {embedder.MODEL} | device={model.device} | max_seq={model.max_seq_length}")

    # длинно-сортированный бакетинг: меньше паддинга -> быстрее на CPU
    order = sorted(range(len(passages)), key=lambda i: len(passages[i]))
    vecs = np.zeros((len(passages), embedder.DIM), dtype="float32")
    t0 = time.time(); last = t0
    for bi in range(0, len(order), BATCH):
        idxs = order[bi:bi + BATCH]
        batch = [embedder.PASSAGE_PREFIX + passages[i] for i in idxs]
        v = model.encode(batch, batch_size=BATCH, normalize_embeddings=True,
                         convert_to_numpy=True, show_progress_bar=False).astype("float32")
        for k, i in enumerate(idxs):
            vecs[i] = v[k]
        done = min(bi + BATCH, len(order))
        now = time.time()
        if now - last >= PROGRESS_EVERY_SEC or done == len(order):
            rate = done / (now - t0) if now > t0 else 0
            eta = (len(order) - done) / rate / 60 if rate else 0
            log(f"эмбеддинг {done}/{len(order)} ({done/len(order):.0%}) "
                f"~{rate:.2f} пасс/с, ETA ~{eta:.0f} мин")
            last = now
    log(f"эмбеддинг ГОТОВ за {(time.time()-t0)/60:.1f} мин, shape {vecs.shape}")
    norms = np.linalg.norm(vecs, axis=1)
    log(f"L2-нормы векторов: min {norms.min():.4f} / max {norms.max():.4f} (ожид ~1.0)")
    return vecs, meta


def write_index(vecs, meta):
    import faiss
    idx = faiss.IndexFlatIP(vecs.shape[1])
    idx.add(vecs)
    faiss.write_index(idx, str(OUT / "index.faiss"))
    with (OUT / "index_meta.jsonl").open("w", encoding="utf-8") as f:
        for uid, code, art, anc, src in meta:
            f.write(json.dumps({"uid": uid, "code": code, "article": art,
                                "anchor": anc, "src": src}, ensure_ascii=False) + "\n")
    cfg = {"model": embedder.MODEL, "dim": int(vecs.shape[1]), "vectors": int(idx.ntotal),
           "prefix_query": embedder.QUERY_PREFIX, "prefix_passage": embedder.PASSAGE_PREFIX,
           "metric": "cosine(IP/normalized)", "max_tokens": embedder.MAX_TOKENS,
           "char_window": g.WIN}
    (OUT / "index_config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    log(f"ЗАПИСАНО: index.faiss ({idx.ntotal} векторов) + index_meta.jsonl + index_config.json")
    log("index_config.json = " + json.dumps(cfg, ensure_ascii=False))
    return idx, cfg


def validate(rows, idx, cfg):
    log("--- ВАЛИДАЦИЯ ---")
    meta_rows = [json.loads(l) for l in (OUT / "index_meta.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    ok_dim = cfg["dim"] == 1024
    ok_vec = idx.ntotal == 17786 == len(meta_rows)
    log(f"dim={cfg['dim']} -> {'OK' if ok_dim else 'FAIL (ожид 1024)'}")
    log(f"vectors={idx.ntotal}, meta={len(meta_rows)} -> {'OK' if ok_vec else 'FAIL (ожид 17786)'}")
    parents = {(r['code'], r['chunk_id']) for r in rows if r['kind'] == 'parent'}
    orphans = [m for m in meta_rows if (m['code'], m['anchor']) not in parents]
    log(f"orphans (meta anchor без parent-якоря): {len(orphans)} -> "
        f"{'OK' if not orphans else 'FAIL ' + str([o['uid'] for o in orphans[:5]])}")
    rep_uids = {r['uid'] for r in rows if r['kind'] == 'repealed'}
    inter = rep_uids & {m['uid'] for m in meta_rows}
    log(f"repealed∩index uid: {len(inter)} -> {'OK' if not inter else 'FAIL ' + str(list(inter)[:5])}")
    return meta_rows, (ok_dim and ok_vec and not orphans and not inter)


def sanity(rows, idx, meta_rows):
    log("--- SANITY-ПОИСК (28 запросов iv.QUERIES, префикс 'query: ') ---")
    parents = {(r['code'], r['chunk_id']): r for r in rows if r['kind'] == 'parent'}

    def retrieve(q, k=3):
        v = embedder.encode_queries([q], show=False)
        D, I = idx.search(v, 60)
        out, seen = [], set()
        for rank, j in enumerate(I[0]):
            m = meta_rows[j]; key = (m['code'], m['article'])
            if key in seen:
                continue
            seen.add(key); out.append((key, float(D[0][rank])))
            if len(out) == k:
                break
        return out

    def ground_truth(kw, code):
        kwl = kw.lower(); out = set()
        for (c, anc), p in parents.items():
            if code is not None and c != code:
                continue
            hay = ((p.get('article_title') or '') + ' ' + p['text'][:110]).lower()
            if kwl in hay:
                out.add((c, p['article_no']))
        return out

    h1 = h3 = n = 0
    for q, kw, code in iv.QUERIES:
        gt = ground_truth(kw, code)
        if not gt:
            continue
        n += 1
        top = retrieve(q, 3)
        got = [a for a, _ in top]
        hit1 = got[0] in gt
        hit3 = any(g_ in gt for g_ in got)
        h1 += hit1; h3 += hit3
        log(f"  «{q[:38]}» -> {[f'{c}/{a}:{s:.2f}' for (c, a), s in top]} "
            f"| hit@1={'Y' if hit1 else '-'} hit@3={'Y' if hit3 else '-'}")
    log(f"SANITY ИТОГ: hit@1={h1}/{n} ({h1/n:.0%}), hit@3={h3}/{n} ({h3/n:.0%})  "
        f"|| MiniLM baseline: hit@1 17/28 (61%), hit@3 23/28 (82%)")


def main():
    t_start = time.time()
    log("=" * 72)
    log("СТАРТ ночного пересбора e5-индекса (intfloat/multilingual-e5-large, 1024d)")
    rows = [json.loads(l) for l in (OUT / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    log(f"chunks.jsonl: {len(rows)} строк")
    vecs, meta = build(rows)
    idx, cfg = write_index(vecs, meta)
    meta_rows, val_ok = validate(rows, idx, cfg)
    log(f"ВАЛИДАЦИЯ: {'ВСЁ OK' if val_ok else 'ЕСТЬ FAIL (см. выше)'}")
    sanity(rows, idx, meta_rows)
    log(f"ГОТОВО ✅  полное время {(time.time()-t_start)/60:.1f} мин")
    log("=" * 72)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("ОШИБКА — процесс упал:\n" + traceback.format_exc())
        sys.exit(1)
