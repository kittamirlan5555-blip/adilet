# -*- coding: utf-8 -*-
"""FB-A инвентарь: считает объёмы вектор-слоя по НОВЫМ докам, БЕЗ записи артефактов.
Переиспользует ТОЧНУЮ логику f_full_chunks (article_units/greedy_subchunks/пороги).
Ничего не производит и не перезаписывает — только счёт."""
import io, sys, json, importlib.util
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup

ROOT = Path(".")
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("fchunks", ROOT / "scripts" / "vector" / "f_full_chunks.py")
F = importlib.util.module_from_spec(spec)
sys.modules["fchunks"] = F
spec.loader.exec_module(F)   # __name__ != __main__ -> main() НЕ вызывается

CODES = json.loads((ROOT / "maps" / "codes.json").read_text(encoding="utf-8"))
OLD = json.loads((ROOT / "derived" / "vector_layer" / "chunks.jsonl").read_text(encoding="utf-8").splitlines()[0])
old_codes = set()
for l in (ROOT / "derived" / "vector_layer" / "chunks.jsonl").read_text(encoding="utf-8").splitlines():
    if l.strip():
        old_codes.add(json.loads(l)["code"])

# === порог summary: из старого слоя (min char_len у parent с summary) ===
oldrows = [json.loads(l) for l in (ROOT / "derived/vector_layer/chunks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
sums = [r for r in oldrows if r["kind"] == "parent" and r.get("summary")]
SUM_THRESH = min(r["char_len"] for r in sums)      # 5031 наблюдаемо
# сверка: сколько старых parent имеют char_len>=порога (должно ≈ числу summary)
oldpar = [r for r in oldrows if r["kind"] == "parent"]
ge = sum(1 for r in oldpar if r["char_len"] >= SUM_THRESH)
print(f"СВЕРКА summary-порога: min char_len у summary={SUM_THRESH}; "
      f"старых parent с char_len>={SUM_THRESH}: {ge} (summary фактически: {len(sums)})")

# === новые доки ===
new_slugs = []
missing = []
for slug, v in CODES.items():
    if slug.startswith("_") or not isinstance(v, dict):
        continue
    if slug in old_codes:           # old_codes = r["code"] = СЛАГ старого слоя
        continue                    # уже в корпусе-43
    st = ROOT / "final" / f"{slug}_structured.html"
    am = ROOT / "maps" / f"article_map_{slug}.json"
    if st.exists() and am.exists():
        new_slugs.append(slug)
    else:
        missing.append((slug, st.exists(), am.exists()))
print(f"\nновых доков (не в корпусе-43, есть _structured+article_map): {len(new_slugs)}")
if missing:
    print(f"  без структуры/карты (пропущены): {len(missing)} -> {[m[0] for m in missing[:8]]}")

# === счёт по логике f_full_chunks ===
tot = Counter()
big_summary = 0
sum_body_chars = 0
per = []
for slug in new_slugs:
    amap = json.loads((ROOT / "maps" / f"article_map_{slug}.json").read_text(encoding="utf-8"))
    soup = BeautifulSoup((ROOT / "final" / f"{slug}_structured.html").read_text(encoding="utf-8", errors="replace"), "html.parser")
    n_art = n_small = n_large = n_sub = n_rep = n_noanc = n_sumt = 0
    for d in soup.find_all("div", class_="article"):
        if "статья" not in (d.get("data-type") or ""):
            continue
        num = d.get("data-number")
        anc = amap.get(str(num))
        if F.RE_REPEALED.search(d.get_text(" ")):
            n_rep += 1
            continue
        if not anc:
            n_noanc += 1
            continue
        title, units = F.article_units(d)
        body = "\n".join(units)
        full = (title + "\n" + body) if title else body
        n_art += 1
        if len(body) > F.SPLIT_IF:
            n_large += 1
            n_sub += len(F.greedy_subchunks(units))
        else:
            n_small += 1
        if len(full) >= SUM_THRESH:
            n_sumt += 1
            sum_body_chars += len(full)
    tot["parent"] += n_art; tot["small"] += n_small; tot["large"] += n_large
    tot["subchunk"] += n_sub; tot["repealed"] += n_rep; tot["noanchor"] += n_noanc
    big_summary += n_sumt
    per.append((slug, n_art, n_large, n_sub, n_rep, n_sumt))

print("\n=== ИНВЕНТАРЬ НОВЫХ ДОКОВ (вектор-слой) ===")
print(f"  документов:            {len(new_slugs)}")
print(f"  статей (parent):       {tot['parent']}")
print(f"  мелких (тело≤1800):    {tot['small']}")
print(f"  крупных (>1800→сабч):  {tot['large']}")
print(f"  сабчанков ожидается:   {tot['subchunk']}")
print(f"  repealed-сносок:       {tot['repealed']}")
print(f"  без якоря (пропуск):   {tot['noanchor']}")
print(f"  ВСЕГО чанков (без sum):{tot['parent']+tot['subchunk']+tot['repealed']}")
print(f"  индексируемых (parent+sub, repealed вне): {tot['parent']+tot['subchunk']}")
print(f"\n  к СУММАРИЗАЦИИ (char_len>={SUM_THRESH}): {big_summary} статей")
print(f"  суммарно символов на суммаризацию: {sum_body_chars:,} (~{sum_body_chars//4:,} вход-токенов груб.)")
# топ по summary-нагрузке
per.sort(key=lambda x: -x[5])
print("\n  топ-8 доков по числу summary:")
for slug, a, lg, sb, rp, sm in per[:8]:
    print(f"    {slug:14} статей={a:4} крупных={lg:4} сабч={sb:5} summary={sm}")
# сохраним числа для сметы
(ROOT / "scripts/vector/_fbA_counts.json").write_text(json.dumps({
    "docs": len(new_slugs), **dict(tot), "summary_needed": big_summary,
    "summary_thresh": SUM_THRESH, "summary_input_chars": sum_body_chars,
    "new_slugs": new_slugs}, ensure_ascii=False, indent=1), encoding="utf-8")
