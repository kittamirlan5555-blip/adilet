# -*- coding: utf-8 -*-
"""R3 БЛОК 3: корпусный ремап ROOT-ссылок на подтверждённые repeal-replace пары.

python scripts/audit/r3_06_root_remap.py [--apply]
-> reports/r3/root_remap_report.md

Корзина (а): только ROOT-href (без #z), только подтверждённые §5+веб пары.
Текст НЕ меняется — только атрибут href. laws3-r2 исключены.
Корзина (б)/(в) и артикульные #z — в отчёт (решения людей), НЕ правятся.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import paths

APPLY = "--apply" in sys.argv
SKIP = {"informatizacii", "notariat", "obrazovanie"}

# подтверждённые пары: (старый, новый, доказательство)
PAIRS = [
    ("K1700000120", "K2500000214",
     "Налоговый кодекс 2017 -> 2025. §5 CLAUDE.md: ПОДТВЕРЖДЕНО; цель = наш "
     "действующий nalog (codes.json, source-выгрузка K2500000214)."),
    ("K080000095_", "K2500000171",
     "Бюджетный кодекс 2008 -> 2025. §5 CLAUDE.md: ПОДТВЕРЖДЕНО; цель = наш "
     "действующий byudzhet (codes.json, source-выгрузка K2500000171)."),
    ("Z950002444_", "Z2600000258",
     "Закон «О банках и банковской деятельности в РК»: 1995 №2444 УТРАТИЛ СИЛУ "
     "19.03.2026 по закону №258-VIII от 16.01.2026 (веб-сверка 2026-06-11: "
     "akorda.kz, prg.kz, aequitas.kz); новый Z2600000258 действует, название "
     "идентично, предмет тот же -> repeal-replace."),
]


def main():
    L = [f"# R3 БЛОК 3 — ремап ROOT-ссылок ({'APPLY' if APPLY else 'DRY-RUN'})", ""]
    L.append("## Корзина (а): подтверждённые пары (доказательства)")
    L.append("")
    L.append("| старый | новый | доказательство |")
    L.append("|---|---|---|")
    for old, new, why in PAIRS:
        L.append(f"| {old} | {new} | {why} |")
    L.append("")
    L.append("Ремап: только href вида …/docs/{старый}\" (КОРЕНЬ, без #z); текст "
             "не меняется; laws3-r2 исключены.")
    L.append("")
    L.append("| файл | пара | заменено root | осталось #z (НЕ ремапим, §9) |")
    L.append("|---|---|---|---|")

    total = Counter()
    leftover = Counter()
    for p in sorted(paths.FINAL.glob("*.html")):
        slug = re.sub(r"_(ready|structured)$", "", p.stem)
        if slug in SKIP:
            continue
        raw = p.read_text(encoding="utf-8")
        orig_text = "".join(re.sub(r"<[^>]+>", " ", raw).split())
        changed = False
        for old, new, _ in PAIRS:
            rx_root = re.compile(r'(href="https?://[^"]*/docs/)' + re.escape(old) + r'(")')
            raw2, n = rx_root.subn(r"\g<1>" + new + r"\g<2>", raw)
            n_art = len(re.findall(r'href="https?://[^"]*/docs/'
                                   + re.escape(old) + r"#", raw2))
            if n or n_art:
                L.append(f"| {p.name} | {old}->{new} | {n} | {n_art} |")
                total[old] += n
                leftover[old] += n_art
            if n:
                raw = raw2
                changed = True
        if changed:
            now = "".join(re.sub(r"<[^>]+>", " ", raw).split())
            if now != orig_text:
                L.append(f"!! TEXT-INVARIANCE FAIL {p.name} — НЕ записан")
                continue
            if APPLY:
                p.write_text(raw, encoding="utf-8")

    # ART-фикс (поимённо, §4): grazhdanskiy — фраза «Бюджетным кодексом РК»
    # (акт ЦЕЛИКОМ, без номера статьи) вела на статейный якорь СТАРОГО БК
    # K080000095_#z1498 -> корень нового K2500000171. Текст не меняется.
    L.append("")
    L.append("## ART-фиксы поимённо")
    L.append("")
    n_art_fix = 0
    for suf in ("ready", "structured"):
        p = paths.FINAL / f"grazhdanskiy_{suf}.html"
        raw = p.read_text(encoding="utf-8")
        raw2, n = re.subn(
            r'(href="https?://[^"]*/docs/)K080000095_#z1498(")',
            r"\g<1>K2500000171\g<2>", raw)
        if n and APPLY:
            p.write_text(raw2, encoding="utf-8")
        n_art_fix += n
        L.append(f"- grazhdanskiy_{suf}: K080000095_#z1498 -> K2500000171 "
                 f"(корень, §4: фраза без номера статьи): {n}")
    L.append("- byudzhet: <a K080000095_#z1>Бюджетный кодекс РК</a> в «Признать "
             "утратившим силу…» — ИСТОРИЧЕСКАЯ ссылка преемника на отменяемый акт, "
             "оставлена (теперь вайтлист [2hist] в 74).")
    L.append("")

    # npa_mapping: банковские строки -> новый НГР
    mp = paths.NPA_MAPPING
    mraw = mp.read_text(encoding="utf-8")
    mraw2, mn = re.subn(r'"Z950002444_"', '"Z2600000258"', mraw)
    if APPLY and mn:
        mp.write_text(mraw2, encoding="utf-8")
    L.append("")
    L.append(f"npa_mapping.json: строк Z950002444_ -> Z2600000258: {mn}")
    L.append("")
    L.append("ИТОГО root-ремапов: "
             + ", ".join(f"{k}: {v}" for k, v in total.items())
             + f" (всего {sum(total.values())})")
    L.append("Осталось артикульных #z на старые коды (ручной ре-резолв/решение): "
             + ", ".join(f"{k}: {v}" for k, v in leftover.items()))
    L.append("")

    # ── Артикульные K080000095_#z — поимённый разбор (контексты) ──
    L.append("## Артикульные ссылки на протухшие коды — поимённо (НЕ правились)")
    L.append("")
    for p in sorted(paths.FINAL.glob("*.html")):
        slug = re.sub(r"_(ready|structured)$", "", p.stem)
        if slug in SKIP:
            continue
        raw = p.read_text(encoding="utf-8")
        for old, new, _ in PAIRS:
            for m in re.finditer(r'<a\b[^>]*href="(https?://[^"]*/docs/'
                                 + re.escape(old) + r'#[^"]*)"[^>]*>(.*?)</a>',
                                 raw, re.S):
                ctx = re.sub(r"<[^>]+>", "", raw[max(0, m.start() - 150):m.start()])
                ctx = re.sub(r"\s+", " ", ctx)[-90:]
                txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(2)))
                L.append(f"- {p.name}: <a>{txt[:60]}</a> -> {m.group(1)}")
                L.append(f"  контекст: …{ctx}")
    out = paths.REPORTS / "r3" / "root_remap_report.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"root-ремапов={sum(total.values())} mapping строк={mn} -> {out}")


if __name__ == "__main__":
    main()
