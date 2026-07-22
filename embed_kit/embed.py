# -*- coding: utf-8 -*-
"""EMBED_KIT — эмбеддинг пассажей вектор-слоя на GPU (RTX 5090 / Blackwell sm_120).

Самодостаточно: читает chunks.jsonl, строит РОВНО те пассажи, что индексирует
g_build_index (мелкая статья / summary крупной / сабчанк+заголовок; префикс
'passage: '; окно 1800 симв), эмбеддит e5-large (fp16, батчи), пишет:
  vectors.npy   — (N, 1024) float32, L2-нормированные
  ids.jsonl     — N строк (uid, code, article, anchor, src) — выравнены с vectors
RESUME: при перезапуске продолжает с последнего сохранённого (memmap + progress.json),
НЕ пересчитывает. Смоук: --limit 200 (замер скорости на карте).

Запуск:  python embed.py --chunks chunks.jsonl --model ./model [--limit 200]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
WIN = 1800                      # символьное окно (как g_build_index.WIN)
PASSAGE_PREFIX = "passage: "    # e5 асимметричный префикс индексируемого пассажа
DIM = 1024


# ── ровно build_passages из g_build_index (скопировано, чтобы kit был автономен) ──
def build_passages(rows, win=WIN):
    parents = {(r["code"], r["chunk_id"]): r for r in rows if r["kind"] == "parent"}
    title_of = {k: (p.get("article_title") or "") for k, p in parents.items()}

    def cut(s):
        return s if win is None else s[:win]

    passages, meta = [], []
    for r in rows:
        if r["kind"] == "repealed":
            continue
        if r["kind"] == "parent":
            if r.get("n_subchunks", 0) == 0:
                passages.append(cut(r["text"])); src = "article"
            elif r.get("summary"):
                passages.append(cut(r["summary"])); src = "summary"
            else:
                continue
            meta.append((r["uid"], r["code"], r["article_no"], r["chunk_id"], src))
        else:
            title = title_of.get((r["code"], r["parent_id"]), "")
            txt = (title + "\n" + r["text"]) if title else r["text"]
            passages.append(cut(txt))
            meta.append((r["uid"], r["code"], r["article_no"], r["parent_id"], "subchunk"))
    return passages, meta


def check_gpu():
    """5090 = Blackwell sm_120. Старый torch НЕ содержит kernel'ов sm_120 → упадёт
    внятно ЗДЕСЬ, а не мистическим CUDA error в середине прогона."""
    try:
        import torch
    except ImportError:
        sys.exit("STOP: не установлен torch. См. requirements.txt (CUDA 12.8+ сборка).")
    if not torch.cuda.is_available():
        sys.exit("STOP: CUDA не видна (torch.cuda.is_available()=False). Проверь драйвер "
                 "и что torch — СБОРКА ПОД CUDA (не +cpu). nvidia-smi должен показывать карту.")
    cap = torch.cuda.get_device_capability(0)      # 5090 -> (12, 0)
    name = torch.cuda.get_device_name(0)
    arches = torch.cuda.get_arch_list()
    sm = f"sm_{cap[0]}{cap[1]}"
    print(f"GPU: {name}  capability {cap} ({sm})  torch {torch.__version__}")
    print(f"    torch arch_list: {arches}")
    if cap[0] >= 12 and not any(a in ("sm_120", "sm_90") for a in arches):
        sys.exit(f"STOP: карта {sm} (Blackwell), но torch собран без sm_120 в arch_list "
                 f"{arches}. Нужен torch под CUDA 12.8+ (cu128). Обнови по requirements.txt "
                 "— иначе будет 'no kernel image is available for execution on the device'.")
    return torch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default=str(HERE / "chunks.jsonl"))
    ap.add_argument("--model", default=str(HERE / "model"),
                    help="локальный путь к e5-large (офлайн) или HF-имя")
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--limit", type=int, default=0, help="смоук: только первые N пассажей")
    args = ap.parse_args()

    torch = check_gpu()
    from sentence_transformers import SentenceTransformer

    rows = [json.loads(l) for l in Path(args.chunks).read_text(encoding="utf-8").splitlines() if l.strip()]
    passages, meta = build_passages(rows)
    if args.limit:
        passages, meta = passages[:args.limit], meta[:args.limit]
    N = len(passages)
    print(f"пассажей к эмбеддингу: {N}" + (f" (СМОУК limit={args.limit})" if args.limit else ""))

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    vpath, ipath, ppath = out / "vectors.npy", out / "ids.jsonl", out / "progress.json"

    # ids.jsonl — детерминирован, пишем целиком сразу (выравнен с будущими vectors)
    with ipath.open("w", encoding="utf-8") as f:
        for uid, code, art, anc, src in meta:
            f.write(json.dumps({"uid": uid, "code": code, "article": art,
                                "anchor": anc, "src": src}, ensure_ascii=False) + "\n")

    # memmap векторов известного размера + progress (сколько contiguous готово)
    if vpath.exists() and ppath.exists():
        vecs = np.lib.format.open_memmap(vpath, mode="r+")
        done = json.loads(ppath.read_text())["done"]
        if vecs.shape != (N, DIM):
            sys.exit(f"STOP: размер vectors.npy {vecs.shape} != ({N},{DIM}). Удали out/ и начни заново.")
        print(f"RESUME: уже готово {done}/{N}, продолжаю…")
    else:
        vecs = np.lib.format.open_memmap(vpath, mode="w+", dtype=np.float32, shape=(N, DIM))
        done = 0

    model = SentenceTransformer(args.model, device="cuda")
    model.max_seq_length = 512
    model.half()                     # fp16 на GPU
    t0 = time.time(); t_start_done = done
    try:
        from tqdm import tqdm
        bar = tqdm(total=N, initial=done, unit="пасс")
    except ImportError:
        bar = None
    for i in range(done, N, args.batch):
        j = min(i + args.batch, N)
        emb = model.encode([PASSAGE_PREFIX + p for p in passages[i:j]],
                            batch_size=args.batch, normalize_embeddings=True,
                            show_progress_bar=False, convert_to_numpy=True)
        vecs[i:j] = emb.astype(np.float32)
        done = j
        ppath.write_text(json.dumps({"done": done, "N": N}))
        if bar:
            bar.update(j - i)
        elif done % (args.batch * 20) == 0:
            print(f"  {done}/{N}", flush=True)
    if bar:
        bar.close()
    vecs.flush()
    dt = time.time() - t0
    n = done - t_start_done
    print(f"\nГОТОВО: {done}/{N} векторов -> {vpath.name} (+ {ipath.name}); "
          f"{n} за {dt:.0f}с = {n/max(dt,1e-9):.0f} пасс/с")
    print("Забрать назад: out/vectors.npy + out/ids.jsonl (в derived/vector_layer/ на ноут).")


if __name__ == "__main__":
    main()
