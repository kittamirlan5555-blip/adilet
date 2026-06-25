# -*- coding: utf-8 -*-
"""ВЕКТОР-СЛОЙ: аудит лимита 512 токенов e5 по ВСЕМ индексируемым пассажам. READ-ONLY.

e5 МОЛЧА обрезает вход > 512 токенов → теряется хвост пассажа → просадка качества.
Скрипт токенайзером e5 меряет КАЖДЫЙ индексируемый пассаж (ровно как строит
g_build_index.build_passages, с префиксом 'passage: ' и спецтокенами) и выводит:
  • сколько пассажей > 512 токенов в ИСТИННОЙ длине (без обрезки — что теряется);
  • сколько > 512 ПОСЛЕ символьного окна WIN (что реально режет e5 при индексации);
  • список превышающих (код/uid/src/символы/токены) — для решения о до-резке сабчанков.
Текст чанков НЕ меняется (только измерение).

python scripts/vector/h_token_audit.py  -> reports/e5_token_audit.md
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
import embedder
import g_build_index as g

OUT = paths.ROOT / "derived" / "vector_layer"
LIMIT = embedder.MAX_TOKENS      # 512
PREF = embedder.PASSAGE_PREFIX


def tok_lens(passages, tok, bs=512):
    """Длины в токенах (с префиксом passage: и спецтокенами <s></s>)."""
    out = []
    for i in range(0, len(passages), bs):
        enc = tok([PREF + p for p in passages[i:i + bs]], add_special_tokens=True)["input_ids"]
        out.extend(len(x) for x in enc)
    return out


def main():
    rows = [json.loads(l) for l in (OUT / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    tok = embedder.get_tokenizer()

    full_p, meta = g.build_passages(rows, win=None)     # истинная длина
    fed_p, _ = g.build_passages(rows, win=g.WIN)        # что реально подаётся (окно WIN)
    n = len(full_p)
    full_len = tok_lens(full_p, tok)
    fed_len = tok_lens(fed_p, tok)

    over_full = [(meta[i], full_len[i], len(full_p[i])) for i in range(n) if full_len[i] > LIMIT]
    over_fed_n = sum(1 for x in fed_len if x > LIMIT)
    over_full.sort(key=lambda x: -x[1])
    src_over = Counter(m[4] for m, _, _ in over_full)
    src_tot = Counter(m[4] for m in meta)

    import numpy as np
    fa = np.array(full_len)
    L = ["# Аудит лимита e5 (512 токенов) по индексируемым пассажам", "",
         f"Модель: `{embedder.MODEL}`, лимит **{LIMIT}** токенов "
         f"(префикс `{PREF}` + спецтокены учтены). Индексируемых пассажей: **{n}**.", "",
         f"- истинная длина (БЕЗ обрезки) > {LIMIT} токенов: **{len(over_full)}** "
         f"({len(over_full)/n:.1%}) — у этих пассажей e5 теряет хвост;",
         f"- после символьного окна WIN={g.WIN}: > {LIMIT} токенов: **{over_fed_n}** "
         f"(это режет уже сама e5 поверх окна);",
         f"- токены/пассаж (истинные): median **{int(np.median(fa))}**, "
         f"p90 **{int(np.percentile(fa,90))}**, max **{int(fa.max())}**.", "",
         "## Превышение по типу пассажа (истинная длина)", "",
         "| src | >512 | всего | доля |", "|---|---|---|---|"]
    for s in ("subchunk", "article", "summary"):
        if src_tot[s]:
            L.append(f"| {s} | {src_over[s]} | {src_tot[s]} | {src_over[s]/src_tot[s]:.1%} |")
    L += ["", f"## Список превышающих {LIMIT} токенов (истинная длина), топ-{min(60,len(over_full))} из {len(over_full)}", "",
          "| код | uid | src | символы | токены |", "|---|---|---|---|---|"]
    for m, tl, ch in over_full[:60]:
        L.append(f"| {m[1]} | {m[0]} | {m[4]} | {ch} | {tl} |")
    if len(over_full) > 60:
        L.append(f"\n_(ещё {len(over_full)-60} — полный список в reports/e5_token_audit.csv)_")
    out = paths.REPORTS / "e5_token_audit.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    # полный CSV
    csv = paths.REPORTS / "e5_token_audit.csv"
    csv.write_text("code,uid,src,chars,tokens\n" + "\n".join(
        f"{m[1]},{m[0]},{m[4]},{ch},{tl}" for m, tl, ch in over_full), encoding="utf-8")
    print(f"индексируемых {n}; >512 истинных: {len(over_full)} ({len(over_full)/n:.1%}); "
          f">512 после WIN={g.WIN}: {over_fed_n} -> {out.name} (+ .csv)")
    for m, tl, ch in over_full[:8]:
        print(f"  {m[1]}/{m[0]} [{m[4]}] {ch}симв {tl}ток")


if __name__ == "__main__":
    main()
