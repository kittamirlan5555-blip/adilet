"""
Скрипт 17: Нормализация целей ссылок (ТЗ-01).

Правила:
  1. href вида http(s)://(adilet.zan.kz|85.202.192.66:9096)/(rus|kaz)/docs/<OWN_doc_id>[?query]#zN
     → "#zN", но ТОЛЬКО если в этом же файле есть id="zN" или name="zN".
     Иначе — оставить как есть и занести anchor в отчёт missing_anchor.
  2. Оставшиеся "http://85.202.192.66:9096" → "https://adilet.zan.kz"
     (хост, путь и #zN не трогаем).
  3. НЕ трогаем: javascript:, mailto:, *advices.adilet*, ссылки на ЧУЖИЕ doc_id
     (кроме правки хоста из п.2).

OWN_doc_id берётся из config/codes.json + _deprecated_remaps (старый doc_id
считается принадлежащим тому же коду, что и его текущая замена).

Идемпотентность: правило 1 не матчится на уже-локальные "#zN"; правило 2 не
матчится после переписывания хоста.

Использование:
  python scripts/17_normalize_link_targets.py                # все коды из codes.json
  python scripts/17_normalize_link_targets.py socialnyy      # только socialnyy
  python scripts/17_normalize_link_targets.py --skip upk     # все, кроме upk
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

ROOT = paths.ROOT
FINAL = paths.FINAL
CODES = paths.CODES_JSON

KNOWN_HOSTS = r"adilet\.zan\.kz|85\.202\.192\.66:9096"

# Реальный формат якорей в кодексах. Покрывает наблюдаемые в data/final:
#   z28, z28_1, z28_1_5            (база и суб-якоря)
#   z124-6, z119-2_2_1             (дефис внутри номера статьи: «статья 124-6»)
#   z119h, z43-2h                  (суффикс 'h' — пометка adilet)
#   z101_p4                        (префикс 'p' у суб-сегмента)
#   z116_6-1, z105_1_8-2           (дефис в суб-сегменте)
Z_ANCHOR = r'z\d+(?:-\d+)?h?(?:_p?\d+(?:-\d+)?)*'

# href, указывающий на конкретный якорь "#zN[_M…]" внутри документа adilet/
# внутреннего сервера.
HREF_INTERNAL_RE = re.compile(
    r'''href\s*=\s*(["'])
        (https?://(?:''' + KNOWN_HOSTS + r'''))
        (/(?:rus|kaz)/docs/)
        ([A-Z]\d+_?[A-Z]?)            # doc_id
        (?:\?[^#"'\s]*)?              # опциональный ?query
        \#(''' + Z_ANCHOR + r''')
        \1
    ''',
    re.IGNORECASE | re.VERBOSE,
)

# Старый хост 85.202.192.66:9096 → adilet.zan.kz. Без префикса href:
# покрывает и href'ы, и MotW-комментарии "<!-- saved from url=(0046)http://… -->",
# которые остаются в начале файлов. Текст 85.202.192.66 в свободном тексте
# в кодексах не встречается (только URL'ы), так что замена безопасна.
HOST_REWRITE_RE = re.compile(
    r'http://85\.202\.192\.66:9096',
    re.IGNORECASE,
)

# Сбор якорей: id="zN[_M…]" или name="zN[_M…]".
ANCHOR_RE = re.compile(r'\b(?:id|name)\s*=\s*"(' + Z_ANCHOR + r')"')


def load_codes():
    cfg = json.loads(CODES.read_text(encoding="utf-8"))
    codes = {k: v for k, v in cfg.items() if not k.startswith("_")}
    raw_deprecated = cfg.get("_deprecated_remaps", {}) or {}
    deprecated = {k: v for k, v in raw_deprecated.items() if not k.startswith("_")}
    return codes, deprecated


def own_doc_ids_for(code, codes, deprecated):
    """doc_id'ы, которые считаются «своими» для данного кода:
    основной из codes.json + все старые из _deprecated_remaps, указывающие на него."""
    main = codes[code]["doc_id"]
    own = {main}
    for old, new in deprecated.items():
        if new == main:
            own.add(old)
    return own


def collect_anchors(html_text):
    return set(ANCHOR_RE.findall(html_text))


def normalize_file(path, own_doc_ids):
    text = path.read_text(encoding="utf-8")
    anchors = collect_anchors(text)

    localized = 0
    missing_anchor = []  # list of anchors (str) на свой код, но без якоря в файле

    def repl_internal(m):
        nonlocal localized
        quote = m.group(1)
        doc_id = m.group(4)
        anchor = m.group(5)
        if doc_id not in own_doc_ids:
            return m.group(0)  # ссылка на чужой кодекс — правилом 1 не трогаем
        if anchor not in anchors:
            missing_anchor.append(anchor)
            return m.group(0)  # якоря нет — оставляем, логируем
        localized += 1
        return f'href={quote}#{anchor}{quote}'

    text2 = HREF_INTERNAL_RE.sub(repl_internal, text)

    # Правило 2: остатки старого хоста — переписать на adilet.zan.kz
    host_fix_count = len(HOST_REWRITE_RE.findall(text2))
    text2 = HOST_REWRITE_RE.sub("https://adilet.zan.kz", text2)

    if text2 != text:
        # ГЕЙТ §6.1: правки только в href — видимый текст обязан совпасть
        before = "".join(re.sub(r"<[^>]+>", " ", text).split())
        after = "".join(re.sub(r"<[^>]+>", " ", text2).split())
        if before != after:
            raise SystemExit(f"TEXT-INVARIANCE FAIL: {path.name} — запись отменена")
        path.write_text(text2, encoding="utf-8")

    return localized, host_fix_count, missing_anchor


def process_code(code, codes, deprecated):
    own_ids = own_doc_ids_for(code, codes, deprecated)
    per_file = []
    total_localized = 0
    total_host_fix = 0
    missing_all = []  # (suffix, anchor)
    for suffix in ("ready", "structured"):
        path = FINAL / f"{code}_{suffix}.html"
        if not path.exists():
            print(f"  [!] нет файла: {path.name}")
            continue
        loc, hf, miss = normalize_file(path, own_ids)
        per_file.append((suffix, loc, hf, len(miss), len(set(miss))))
        total_localized += loc
        total_host_fix += hf
        missing_all.extend((suffix, a) for a in miss)
    return {
        "own_ids": sorted(own_ids),
        "per_file": per_file,
        "localized": total_localized,
        "host_fix": total_host_fix,
        "missing_anchor": missing_all,
    }


def main():
    ap = argparse.ArgumentParser(description="ТЗ-01: нормализация целей ссылок.")
    ap.add_argument("codes", nargs="*", help="коды для прогона (пусто = все из codes.json)")
    ap.add_argument("--skip", action="append", default=[], help="код пропустить (можно повторять)")
    args = ap.parse_args()

    codes, deprecated = load_codes()
    target = args.codes if args.codes else list(codes.keys())
    target = [c for c in target if c not in set(args.skip)]
    unknown = [c for c in target if c not in codes]
    if unknown:
        print(f"Неизвестные коды: {unknown}", file=sys.stderr)
        sys.exit(2)

    print(f"Прогон по кодам: {', '.join(target)}")
    if args.skip:
        print(f"Пропущены:        {', '.join(args.skip)}")
    print()

    rows = []
    all_missing = []  # (code, suffix, anchor)
    for code in target:
        print(f"[{code}]  own_doc_ids = {sorted(own_doc_ids_for(code, codes, deprecated))}")
        t = process_code(code, codes, deprecated)
        for suf, loc, hf, miss_total, miss_uniq in t["per_file"]:
            print(f"  {suf:11} localized={loc:>5}  host_fix={hf:>5}  missing={miss_total:>4} ({miss_uniq} уник.)")
        # уникальные анкоры по коду
        uniq = sorted(set(a for _, a in t["missing_anchor"]))
        if uniq:
            preview = ", ".join(uniq[:15])
            extra = "" if len(uniq) <= 15 else f", … (+{len(uniq) - 15})"
            print(f"  missing_anchor uniq ({len(uniq)}): {preview}{extra}")
        print()
        rows.append((code, t["localized"], t["host_fix"], len(uniq)))
        all_missing.extend((code, suf, a) for suf, a in t["missing_anchor"])

    # ── Итоговая таблица ────────────────────────────────────────────
    print("=" * 64)
    print(f"{'код':18}{'локализовано':>15}{'хост-фикс':>12}{'missing_anchor':>17}")
    print("-" * 64)
    for code, loc, hf, miss in rows:
        print(f"{code:18}{loc:>15}{hf:>12}{miss:>17}")
    print("=" * 64)

    # Сводный список missing_anchor (уникальные по коду)
    if all_missing:
        print()
        print("Сводный missing_anchor (уник. по коду):")
        by_code = {}
        for code, suf, a in all_missing:
            by_code.setdefault(code, set()).add(a)
        for code in sorted(by_code):
            anchors = sorted(by_code[code])
            print(f"  {code:18} ({len(anchors)}): {', '.join(anchors)}")
    else:
        print("\nmissing_anchor: пусто.")


if __name__ == "__main__":
    main()
