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


# ориентиры скорости для ETA (замер на ноутном CPU: 0.75 пасс/с; GPU — оценка)
RATE_CPU = 0.75            # пасс/с (реальный замер e5-large на этом классе CPU)
RATE_GPU_EST = 40.0       # пасс/с, КОНСЕРВ. оценка для 5090 (смоук уточнит)


def select_device(requested):
    """Выбор устройства: auto|cpu|cuda. GPU НЕ обязателен (сервер может быть без карты).
    Для cuda — проверка Blackwell sm_120 (старый torch карту не увидит) с внятной ошибкой.
    Возвращает (torch, device_str, rate_hint)."""
    try:
        import torch
    except ImportError:
        sys.exit("STOP: не установлен torch. GPU: requirements.txt (cu128). "
                 "CPU: pip install torch (обычная сборка).")
    has_cuda = torch.cuda.is_available()
    if requested == "cpu":
        dev = "cpu"
    elif requested == "cuda":
        if not has_cuda:
            sys.exit("STOP: --device cuda, но CUDA не видна (нет карты/драйвера, или torch=+cpu). "
                     "nvidia-smi должен показывать карту. Для CPU: --device cpu (или auto).")
        dev = "cuda"
    else:                                   # auto
        dev = "cuda" if has_cuda else "cpu"
    if dev == "cuda":
        cap = torch.cuda.get_device_capability(0)          # 5090 -> (12, 0)
        arches = torch.cuda.get_arch_list()
        sm = f"sm_{cap[0]}{cap[1]}"
        print(f"УСТРОЙСТВО: GPU {torch.cuda.get_device_name(0)} ({sm}), torch {torch.__version__}")
        print(f"    arch_list: {arches}")
        if cap[0] >= 12 and not any(a in ("sm_120", "sm_90") for a in arches):
            sys.exit(f"STOP: карта {sm} (Blackwell), но torch собран без sm_120 (arch_list {arches}). "
                     "Нужен torch под CUDA 12.8+ (cu128) — иначе 'no kernel image ... for the device'. "
                     "Либо гони на CPU: --device cpu.")
        return torch, "cuda", RATE_GPU_EST
    print(f"УСТРОЙСТВО: CPU (torch {torch.__version__}) — GPU не выбран/не найден. "
          "fp16 отключён (на CPU медленно/неточно).")
    return torch, "cpu", RATE_CPU


def _eta(n, rate, dev):
    sec = n / max(rate, 1e-9)
    h = sec / 3600
    t = f"{sec/60:.0f} мин" if sec < 5400 else f"{h:.1f} ч"
    note = "(замер CPU 0.75 пасс/с)" if dev == "cpu" else "(ОЦЕНКА GPU ~40 пасс/с; смоук уточнит)"
    return f"~{t} {note}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default=str(HERE / "chunks.jsonl"))
    ap.add_argument("--model", default=str(HERE / "model"),
                    help="локальный путь к e5-large (офлайн) или HF-имя")
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--limit", type=int, default=0, help="смоук: только первые N пассажей")
    ap.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto",
                    help="auto (GPU если есть, иначе CPU) | cpu | cuda")
    args = ap.parse_args()

    torch, device, rate = select_device(args.device)
    from sentence_transformers import SentenceTransformer

    rows = [json.loads(l) for l in Path(args.chunks).read_text(encoding="utf-8").splitlines() if l.strip()]
    passages, meta = build_passages(rows)
    if args.limit:
        passages, meta = passages[:args.limit], meta[:args.limit]
    N = len(passages)
    print(f"пассажей к эмбеддингу: {N}" + (f" (СМОУК limit={args.limit})" if args.limit else ""))
    print(f"ожидаемая длительность: {_eta(N, rate, device)}")
    if device == "cpu" and not args.limit and N > 5000:
        print("  ВНИМАНИЕ: полный прогон на CPU долгий — рекомендую сначала --limit 200 "
              "(смоук), либо GPU. Прогон resume-able (обрыв → продолжит).")

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

    model = SentenceTransformer(args.model, device=device)
    model.max_seq_length = 512
    if device == "cuda":
        model.half()                 # fp16 ТОЛЬКО на GPU (на CPU медленно/неточно)
    t0 = time.time(); t_start_done = done
    try:
        from tqdm import tqdm
        bar = tqdm(total=N, initial=done, unit="пасс")
    except ImportError:
        bar = None
    cur_bs = args.batch          # текущий batch; при OOM снижается вдвое и ПЕРСИСТИТ
    OOMError = getattr(torch.cuda, "OutOfMemoryError", RuntimeError)

    def encode_slice(texts):
        """Энкод среза с автоснижением batch при OOM (не краш). Внутр. batch_size
        управляет памятью GPU; снижение персистит на последующие срезы."""
        nonlocal cur_bs
        while True:
            try:
                return model.encode(texts, batch_size=cur_bs, normalize_embeddings=True,
                                    show_progress_bar=False, convert_to_numpy=True)
            except OOMError:
                if device == "cuda":
                    torch.cuda.empty_cache()
                if cur_bs <= 1:
                    raise
                cur_bs = max(1, cur_bs // 2)
                print(f"  OOM на 8 ГБ → снижаю batch до {cur_bs}, повтор среза…", flush=True)

    for i in range(done, N, args.batch):
        j = min(i + args.batch, N)
        emb = encode_slice([PASSAGE_PREFIX + p for p in passages[i:j]])
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
