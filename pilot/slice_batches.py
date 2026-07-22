# -*- coding: utf-8 -*-
"""BLOCK 4 — нарезка реестра на батчи по ~100 (стабильный порядок, возобновляемо).

Цель = субстантивные действующие TODO из maps/corpus_registry.json. Стабильный
порядок — сортировка по НГР (детерминизм: тот же батч при повторе). Пишет
pilot/batches/batch_NNN.txt (по одному НГР в строке) + pilot/batches/INDEX.md.
"""
import io, json, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIZE = 100
OUT = ROOT / "pilot" / "batches"
OUT.mkdir(parents=True, exist_ok=True)

rows = json.loads((ROOT / "maps" / "corpus_registry.json").read_text(encoding="utf-8"))
todo = sorted((r["ngr"] for r in rows if r["bucket"] == "TODO"))   # стабильный порядок
batches = [todo[i:i + SIZE] for i in range(0, len(todo), SIZE)]

idx = ["# Батчи прогона (субстантивные TODO из corpus_registry)", "",
       f"Всего TODO: **{len(todo)}**, батчей по {SIZE}: **{len(batches)}**.", "",
       "| батч | НГР | файл |", "|---|--:|---|"]
for n, b in enumerate(batches, 1):
    f = OUT / f"batch_{n:03d}.txt"
    f.write_text("\n".join(b) + "\n", encoding="utf-8")
    idx.append(f"| {n:03d} | {len(b)} | pilot/batches/{f.name} |")
(OUT / "INDEX.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
print(f"TODO={len(todo)} -> {len(batches)} батч(ей) по {SIZE}")
for n, b in enumerate(batches, 1):
    print(f"  batch_{n:03d}: {len(b)} НГР  [{b[0]} .. {b[-1]}]")
