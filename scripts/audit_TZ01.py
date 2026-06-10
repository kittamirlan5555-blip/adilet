"""
Read-only аудит ТЗ-01 (нормализация целей ссылок).

Для каждого кода из config/codes.json КРОМЕ upk, по файлам
data/final/<code>_ready.html и data/final/<code>_structured.html:

  own_doc = doc_id кода (+ для nalog старый K1700000120 тоже считаем «своим»).

  A = число <a href="..."> с абсолютным URL на adilet.zan.kz ИЛИ
      85.202.192.66:9096, ведущих на own_doc с якорем #zN, при условии что
      якорь id="zN" или name="zN" в этом же файле ЕСТЬ
      (= нелокализованные внутренние ссылки, которые скрипт 17 должен был
      превратить в "#zN").  ДОЛЖНО быть 0.
  C = число вхождений строки "85.202.192.66" в файле.  ДОЛЖНО быть 0.
  D = число href="#zN", где якоря zN в файле НЕТ (битые прыжки).
      ДОЛЖНО быть 0.
  L = всего href="#zN" в файле (для контекста).

PASS = (A == 0 и C == 0 и D == 0).

Скрипт НИЧЕГО не пишет.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
CODES = ROOT / "config" / "codes.json"

KNOWN_HOSTS = r"adilet\.zan\.kz|85\.202\.192\.66:9096"

# Z_ANCHOR: реальный формат z-якорей в кодексах. Покрывает:
#   z28, z28_1, z28_1_5            (база и суб-якоря)
#   z124-6, z119-2_2_1             (дефис внутри номера статьи)
#   z119h, z43-2h                  (суффикс 'h')
#   z101_p4                        (префикс 'p' у суб-сегмента)
#   z116_6-1, z105_1_8-2           (дефис в суб-сегменте)
Z_ANCHOR = r'z\d+(?:-\d+)?h?(?:_p?\d+(?:-\d+)?)*'

HREF_ABS_INTERNAL_RE = re.compile(
    r'''<a\b[^>]*?\bhref\s*=\s*(["'])
        (https?://(?:''' + KNOWN_HOSTS + r'''))
        (/(?:rus|kaz)/docs/)
        ([A-Z]\d+_?[A-Z]?)
        (?:\?[^#"'\s]*)?
        \#(''' + Z_ANCHOR + r''')
        \1
    ''',
    re.IGNORECASE | re.VERBOSE,
)

HREF_LOCAL_ANCHOR_RE = re.compile(
    r'''<a\b[^>]*?\bhref\s*=\s*(["'])\#(''' + Z_ANCHOR + r''')\1''',
    re.IGNORECASE | re.VERBOSE,
)

ANCHOR_RE = re.compile(r'\b(?:id|name)\s*=\s*"(' + Z_ANCHOR + r')"')

IP_LITERAL = "85.202.192.66"


def load_codes():
    cfg = json.loads(CODES.read_text(encoding="utf-8"))
    codes = {k: v for k, v in cfg.items() if not k.startswith("_")}
    raw_dep = cfg.get("_deprecated_remaps", {}) or {}
    deprecated = {k: v for k, v in raw_dep.items() if not k.startswith("_")}
    return codes, deprecated


def own_doc_ids_for(code, codes, deprecated):
    main = codes[code]["doc_id"]
    own = {main}
    for old, new in deprecated.items():
        if new == main:
            own.add(old)
    return own


def audit_file(path: Path, own_ids: set):
    text = path.read_text(encoding="utf-8")
    anchors = set(ANCHOR_RE.findall(text))

    A_examples = []
    A = 0
    for m in HREF_ABS_INTERNAL_RE.finditer(text):
        doc_id = m.group(4)
        anchor = m.group(5)
        if doc_id in own_ids and anchor in anchors:
            A += 1
            if len(A_examples) < 5:
                A_examples.append(m.group(0))

    C = text.count(IP_LITERAL)

    L = 0
    D = 0
    D_examples = []
    for m in HREF_LOCAL_ANCHOR_RE.finditer(text):
        L += 1
        anchor = m.group(2)
        if anchor not in anchors:
            D += 1
            if len(D_examples) < 5:
                D_examples.append(anchor)

    return {
        "A": A, "C": C, "D": D, "L": L,
        "A_examples": A_examples,
        "D_examples": D_examples,
        "anchors_total": len(anchors),
    }


def audit_code(code, codes, deprecated):
    own = own_doc_ids_for(code, codes, deprecated)
    per_file = {}
    totals = {"A": 0, "C": 0, "D": 0, "L": 0}
    a_ex, d_ex = [], []
    for suffix in ("ready", "structured"):
        path = FINAL / f"{code}_{suffix}.html"
        if not path.exists():
            per_file[suffix] = None
            continue
        r = audit_file(path, own)
        per_file[suffix] = r
        for k in totals:
            totals[k] += r[k]
        for ex in r["A_examples"]:
            if len(a_ex) < 5:
                a_ex.append((path.name, ex))
        for ex in r["D_examples"]:
            if len(d_ex) < 5:
                d_ex.append((path.name, ex))
    return {
        "own_ids": sorted(own),
        "per_file": per_file,
        "totals": totals,
        "A_examples": a_ex,
        "D_examples": d_ex,
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("codes", nargs="*",
                    help="коды для проверки (пусто = все из codes.json кроме upk)")
    ap.add_argument("--include-upk", action="store_true",
                    help="включить upk в обход обычного исключения")
    args = ap.parse_args()
    codes, deprecated = load_codes()
    if args.codes:
        target = list(args.codes)
    elif args.include_upk:
        target = list(codes.keys())
    else:
        target = [c for c in codes.keys() if c != "upk"]

    rows = []
    a_examples_global = []
    for code in target:
        r = audit_code(code, codes, deprecated)
        t = r["totals"]
        passed = (t["A"] == 0 and t["C"] == 0 and t["D"] == 0)
        rows.append((code, t["A"], t["C"], t["D"], t["L"], passed, r))
        for fname, snippet in r["A_examples"]:
            if len(a_examples_global) < 5:
                a_examples_global.append((code, fname, snippet))

    # ── таблица ─────────────────────────────────────────────────
    print(f"{'код':18}{'A':>6}{'C':>6}{'D':>6}{'L':>8}  {'результат'}")
    print("-" * 56)
    for code, A, C, D, L, ok, _ in rows:
        verdict = "PASS" if ok else "FAIL"
        print(f"{code:18}{A:>6}{C:>6}{D:>6}{L:>8}  {verdict}")
    print("-" * 56)
    failed = [r for r in rows if not r[5]]
    print(f"итого: {len(rows) - len(failed)} PASS / {len(failed)} FAIL"
          f"  (всего кодов: {len(rows)}, без upk)")

    if a_examples_global:
        print()
        print("Примеры нелокализованных <a href> (A>0):")
        for code, fname, snippet in a_examples_global:
            print(f"  [{code}] {fname}")
            print(f"    {snippet[:240]}")

    # детальный per-file разбор по FAIL
    fail_codes = [r for r in rows if not r[5]]
    if fail_codes:
        print()
        print("Подробно по FAIL-кодам (per-file):")
        for code, A, C, D, L, ok, r in fail_codes:
            print(f"  [{code}] own_ids={r['own_ids']}")
            for suf, pf in r["per_file"].items():
                if pf is None:
                    print(f"    {suf}: файла нет")
                    continue
                print(f"    {suf:11} A={pf['A']:>4} C={pf['C']:>4} "
                      f"D={pf['D']:>4} L={pf['L']:>5} "
                      f"(anchors_in_file={pf['anchors_total']})")
            if r["D_examples"]:
                print(f"    D-примеры (битые #zN): "
                      + ", ".join(f"{n}:{a}" for n, a in r['D_examples']))

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
