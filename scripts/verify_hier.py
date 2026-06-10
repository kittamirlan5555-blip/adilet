"""Verification of hier_id (chunker v3). Prints RAW evidence for boss Yergali."""
import json
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CHUNKS = ROOT / "data" / "chunks"
TREE = ROOT / "data" / "tree"

CODES = ["nalog", "trudovoy", "grazhdanskiy", "predprinimatel", "socialnyy",
         "ekologicheskiy", "zemelnyy", "upk", "koap", "appk", "byudzhet", "ugolovniy"]


def load_chunks(code):
    return [json.loads(l) for l in (CHUNKS / f"{code}.jsonl").open(encoding="utf-8")]


def load_tree(code):
    return json.loads((TREE / f"{code}.json").read_text(encoding="utf-8"))


def show(chunk):
    m = chunk["meta"]
    extra = "  hier_partial=True" if m.get("hier_partial") else ""
    print(f"  id={chunk['id']}")
    print(f"  hier_id = {m['hier_id']}{extra}")
    print(f"  hier_path = {json.dumps(m['hier_path'], ensure_ascii=False)}")
    print()


def find_article_node(tree, art):
    for a in tree["articles"]:
        if a["article"] == art:
            return a
    return None


print("=" * 90)
print("(а) 3 примера meta из УК на разных глубинах")
print("=" * 90)
uk = load_chunks("ugolovniy")
uk_tree = load_tree("ugolovniy")

# 1) статья БЕЗ пунктов (unit_number=None, единственный чанк статьи)
no_unit = next(c for c in uk if c["meta"]["unit_number"] is None
               and c["meta"]["status"] == "active")
print("[1] Статья БЕЗ частей (article-level, один чанк):")
show(no_unit)

# 2) часть статьи (unit_number задан)
with_unit = next(c for c in uk if c["meta"]["unit_number"] is not None)
print("[2] Часть статьи (unit-level чанк):")
show(with_unit)

# 3) подпункт — берём из ДЕРЕВА (чанки не дробятся до подпункта; SP живёт в узле дерева)
print("[3] Подпункт (узел дерева — чанки не дробятся глубже части):")
found = False
for a in uk_tree["articles"]:
    for u in a["children"]:
        for s in u.get("children", []):
            if s.get("type") == "подпункт":
                print(f"  статья {a['article']} / часть {u['number']} / подпункт {s['number']}")
                print(f"  node.hier_id = {s['hier_id']}")
                found = True
                break
        if found:
            break
    if found:
        break
print()

print("=" * 90)
print("(б) Спот-чеки")
print("=" * 90)

# УПК ст.32 части 1 и 6
upk = load_chunks("upk")
print("УПК ст.32 (R12 <br/>-формат) — части 1 и 6:")
for c in upk:
    m = c["meta"]
    if m["article"] == "32" and m["unit_number"] in ("1", "6"):
        print(f"  часть {m['unit_number']:>2}: hier_id = {m['hier_id']}  "
              f"| path={json.dumps(m['hier_path'], ensure_ascii=False)}")
print()

# ПК ст.82 п.3 пп.4-1 (suffix) — из дерева
pk_tree = load_tree("predprinimatel")
a82 = find_article_node(pk_tree, "82")
print("ПК ст.82 п.3 пп.4-1 (suffix сохранён) — узлы дерева:")
for u in a82["children"]:
    if u["number"] == "3":
        print(f"  пункт 3:   node.hier_id = {u['hier_id']}")
        for s in u.get("children", []):
            if s["number"] == "4-1":
                print(f"  пп. 4-1:   node.hier_id = {s['hier_id']}   <-- suffix")
print()

# КоАП ст.200 ч.1 — CH2 (Особенная часть)?
koap = load_chunks("koap")
print("КоАП ст.200 ч.1 (Особенная часть → должно быть CH2):")
for c in koap:
    m = c["meta"]
    if m["article"] == "200" and m["unit_number"] == "1":
        print(f"  hier_id = {m['hier_id']}")
        print(f"  hier_path = {json.dumps(m['hier_path'], ensure_ascii=False)}")
print()

# КоАП ст.312 orphan — hier_id + hier_partial
print("КоАП ст.312 (orphan, Latin-C homoglyph) — hier_id + hier_partial:")
for c in koap:
    m = c["meta"]
    if m["article"] == "312":
        print(f"  id={c['id']}")
        print(f"  hier_id = {m['hier_id']}")
        print(f"  hier_partial = {m.get('hier_partial')}  orphan_pickup = {m.get('orphan_pickup')}")
        print(f"  hier_path = {json.dumps(m['hier_path'], ensure_ascii=False)}")
        print()

print("=" * 90)
print("(в) Уникальность hier_id по ВСЕМ чанкам")
print("=" * 90)
all_ids = []
per_code_dups = {}
for code in CODES:
    ids = [c["meta"]["hier_id"] for c in load_chunks(code)]
    all_ids.extend(ids)
    if len(set(ids)) != len(ids):
        from collections import Counter
        dups = [k for k, v in Counter(ids).items() if v > 1]
        per_code_dups[code] = dups

total = len(all_ids)
uniq = len(set(all_ids))
print(f"  total chunks   = {total}")
print(f"  unique hier_id = {uniq}")
print(f"  len(set)==len  -> {uniq == total}")
if uniq != total:
    from collections import Counter
    cnt = Counter(all_ids)
    dups = [(k, v) for k, v in cnt.items() if v > 1]
    print(f"  DUPLICATES ({len(dups)}):")
    for k, v in dups[:40]:
        print(f"    {k}  x{v}")
    if per_code_dups:
        print("  by code:", {k: len(v) for k, v in per_code_dups.items()})
print()

print("=" * 90)
print("(г) Итоги по 12 кодексам")
print("=" * 90)
print(f"{'код':14} {'чанков':>7} {'уник.hier':>10} {'partial':>8} {'orphan':>7}")
print("-" * 50)
g_total = g_uniq_ok = 0
for code in CODES:
    ch = load_chunks(code)
    ids = [c["meta"]["hier_id"] for c in ch]
    partial = sum(1 for c in ch if c["meta"].get("hier_partial"))
    orphan = sum(1 for c in ch if c["meta"].get("orphan_pickup"))
    uok = len(set(ids))
    print(f"{code:14} {len(ch):>7} {uok:>10} {partial:>8} {orphan:>7}")
    g_total += len(ch)
print("-" * 50)
print(f"{'TOTAL':14} {g_total:>7} {len(set(all_ids)):>10}")
