# -*- coding: utf-8 -*-
"""FB-A бенч эмбеддинга: 200 реальных сабчанков через e5-large на CPU -> сек/пассаж.
Экстраполяция на объём эмбеддинга нового слоя. 5090 — ОЦЕНКА (не замер)."""
import io, sys, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(".")
counts = json.loads((ROOT / "scripts/vector/_fbA_counts.json").read_text(encoding="utf-8"))
EMBED_NEW = counts["small"] + counts["subchunk"] + counts["summary_needed"]

# 200 реальных сабчанков (репрезентативны по длине — SUB_MAX=1500)
rows = [json.loads(l) for l in (ROOT / "derived/vector_layer/chunks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
subs = [r["text"] for r in rows if r["kind"] == "subchunk"][:200]
texts = ["passage: " + t for t in subs]
avg_chars = sum(len(t) for t in subs) / len(subs)
print(f"бенч: {len(texts)} сабчанков, средн. {avg_chars:.0f} симв")

from sentence_transformers import SentenceTransformer
t0 = time.time()
m = SentenceTransformer("intfloat/multilingual-e5-large")
m.max_seq_length = 512
print(f"модель загружена за {time.time()-t0:.0f}с")

# прогрев (JIT/кэш) на 16, потом замер на 200
m.encode(texts[:16], batch_size=32, normalize_embeddings=True, show_progress_bar=False)
t1 = time.time()
emb = m.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
dt = time.time() - t1
pps = len(texts) / dt
print(f"\n=== ЗАМЕР CPU e5-large ===")
print(f"  {len(texts)} пассажей за {dt:.1f}с -> {pps:.2f} пасс/с ({dt/len(texts)*1000:.0f} мс/пассаж), dim={emb.shape[1]}")

def fmt(sec):
    h = sec / 3600
    return f"{sec:.0f}с" if sec < 90 else (f"{sec/60:.0f}мин" if sec < 5400 else f"{h:.1f}ч")

cpu_all = EMBED_NEW / pps
print(f"\n=== ЭКСТРАПОЛЯЦИЯ на эмбеддинг нового слоя ({EMBED_NEW} пассажей) ===")
print(f"  (а) НОУТ CPU:  {fmt(cpu_all)}  @ {pps:.2f} пасс/с")
for mult, lbl in [(40, "консерв."), (80, "оптим.")]:
    print(f"  (б) 5090 ~x{mult} ({lbl}, ОЦЕНКА): {fmt(cpu_all/mult)}  @ ~{pps*mult:.0f} пасс/с")
print(f"\n  * 5090 — оценка по типичному ускорению fp16 GPU vs CPU на трансформер-энкодере;")
print(f"    реальный замер только на железе. Ноут — прямой замер выше.")
(ROOT / "scripts/vector/_fbA_bench.json").write_text(json.dumps({
    "pps_cpu": pps, "ms_per": dt/len(texts)*1000, "embed_new": EMBED_NEW,
    "cpu_sec": cpu_all}, ensure_ascii=False, indent=1), encoding="utf-8")
