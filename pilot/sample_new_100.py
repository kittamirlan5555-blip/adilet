# -*- coding: utf-8 -*-
"""Проверка чистоты пула НОВЫХ материальных законов + random.sample(100).
Пишет pilot_100.txt строго с LF (без CRLF — прошлый баг заквранил всё)."""
import csv
import io
import json
import random
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[1]
SEED = 20260701

pool = [l.strip() for l in (ROOT / "pilot" / "pool_new.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
meta = {r["ngr"]: r for r in csv.DictReader((ROOT / "pilot" / "pool_new_meta.csv").open(encoding="utf-8"))}

# независимая перепроверка исключений
codes = json.loads((ROOT / "maps" / "codes.json").read_text(encoding="utf-8"))
EXCL = set()
for k, v in codes.items():
    if k.startswith("_"):
        continue
    EXCL.add(k.rstrip("_"))
    if isinstance(v, dict) and v.get("doc_id"):
        EXCL.add(v["doc_id"].rstrip("_"))
for l in (ROOT / "pilot" / "prev_slugs.txt").read_text(encoding="utf-8").splitlines():
    if l.strip():
        EXCL.add(l.strip().rstrip("_"))

def is_amend(t):
    t = (t or "").lower()
    return "внесени" in t and ("измен" in t or "дополнен" in t)

bad_excl = [n for n in pool if n.rstrip("_") in EXCL]
bad_amend = [n for n in pool if is_amend(meta.get(n, {}).get("title", ""))]
bad_dup = [n for n in pool if pool.count(n) > 1]
print(f"пул НОВЫХ материальных: {len(pool)} (уникальных: {len(set(pool))})")
print(f"НАРУШЕНИЙ фильтра — в корпусе/прошлом пилоте: {len(bad_excl)} | амандменты: {len(bad_amend)} | дубли: {len(set(bad_dup))}")
if bad_excl or bad_amend:
    print("  ПРОБЛЕМА:", (bad_excl + bad_amend)[:10])

random.seed(SEED)
n = min(100, len(pool))
sample = random.sample(pool, n)

# LF-only запись (обход CRLF-бага)
(ROOT / "pilot" / "pilot_100.txt").write_bytes(("\n".join(sample) + "\n").encode("utf-8"))

print(f"\nseed={SEED} | выборка={n} -> pilot/pilot_100.txt (LF)")
print("первые 10 (НГР + заголовок):")
for ngr in sample[:10]:
    print(f"  {ngr:14} {meta.get(ngr, {}).get('title', '')[:66]}")
