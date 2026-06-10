# -*- coding: utf-8 -*-
"""LAWS3 ФАЗА 2: точечные обёртки notariat/obrazovanie (по 00_diagnosis.md).

python scripts/audit/f04_laws3_wraps.py [--apply]
-> data/reports/laws3/01_wraps_report.md

Полный спан фразы -> <a href>; фраза обязана лежать в плейн-тексте (вне <a>).
НГР: корпус-верифицированные (см. диагноз); «О гос. имуществе» = Z1100000413,
НЕ K080000095_ из протухшего mapping. Гейты: nows-инвариант, </a></a>=0 сырым,
двойных href=0, счёт обёрток == ожиданию.
Попутно: npa_mapping.json — фикс 4 мусорных рядов (K080000095_ -> Z1100000413
для фраз «О государственном имуществе») + 3 новые фразы.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auditlib as al

A = "https://adilet.zan.kz/rus/docs/"

# (slug, видимая фраза-СПАН (regex, ws-гибкий), href, ожидаемых вхождений)
WRAPS = [
    # --- notariat: 5 имён законов -> корни ---
    ("notariat", r'Законом Республики Казахстан "О государственной регистрации '
                 r'прав на недвижимое имущество"', A + "Z070000310_", 1),
    ("notariat", r'Законом Республики Казахстан "О государственном имуществе"',
     A + "Z1100000413", 1),
    ("notariat", r'Законом Республики Казахстан "О разрешениях и уведомлениях"',
     A + "Z1400000202", 1),
    ("notariat", r'Закона Республики Казахстан "О жилищных отношениях"',
     A + "Z970000094_", 1),
    ("notariat", r'Законом Республики Казахстан "Об электронном документе '
                 r'и электронной цифровой подписи"', A + "Z030000370_", 1),
    # --- notariat: 2 cross-code (спан «статьи N <Кодекс> РК», квалификатор вне) ---
    ("notariat", r'статьи 3 Уголовного кодекса Республики Казахстан',
     A + "K1400000226#z3002", 1),
    ("notariat", r'статьи 291 Гражданского кодекса Республики Казахстан',
     A + "K940001000_#z611", 1),
    # --- obrazovanie: 5 мест (50-1 единым спаном со статьёй) ---
    ("obrazovanie", r'статьи 50-1 Закона Республики Казахстан "О воинской '
                    r'службе и статусе военнослужащих"', A + "Z1200000561", 1),
    ("obrazovanie", r'Законом Республики Казахстан "О некоммерческих организациях"',
     A + "Z010000142_", 1),
    ("obrazovanie", r'Законом Республики Казахстан "Об акционерных обществах"',
     A + "Z030000415_", 1),
    ("obrazovanie", r'Закона Республики Казахстан "О разрешениях и уведомлениях"',
     A + "Z1400000202", 1),
    ("obrazovanie", r'Законом Республики Казахстан "О государственном имуществе"',
     A + "Z1100000413", 1),
]

MAPPING_FIX = {  # фраза -> новый НГР (только мусорные ряды госимущества)
    "value_from": "K080000095_",
    "только_для_фраз_с": "О государственном имуществе",
    "new": "Z1100000413",
}
MAPPING_ADD = {
    'Закона Республики Казахстан "О жилищных отношениях"': "Z970000094_",
    'Законом Республики Казахстан "О некоммерческих организациях"': "Z010000142_",
    'Закона Республики Казахстан "О воинской службе и статусе военнослужащих"':
        "Z1200000561",
}


def wrap_plain(raw, phrase_rx, href):
    """Оборачивает ПЕРВОЕ плейн-вхождение фразы (вне <a>, без тегов внутри).
    Возвращает (raw, n_wrapped)."""
    rx = re.compile(phrase_rx.replace(" ", r"\s+"))
    links = [(m.start(), m.end()) for m in al.RE_A_PAIR.finditer(raw)]
    n = 0
    out = raw
    for m in rx.finditer(raw):
        if any(a <= m.start() < b for a, b in links):
            continue                      # уже внутри <a>
        if "<" in m.group(0):
            continue                      # фраза разорвана тегами — не наш кейс
        out = out[:m.start()] + f'<a href="{href}">{m.group(0)}</a>' + out[m.end():]
        n += 1
        break                             # по одному вхождению за вызов
    return out, n


def main():
    apply_mode = "--apply" in sys.argv
    OUT = al.ROOT / "data" / "reports" / "laws3"
    OUT.mkdir(parents=True, exist_ok=True)
    L = ["# LAWS3 ФАЗА 2 — точечные обёртки", "",
         f"Режим: {'APPLY' if apply_mode else 'DRY-RUN'}.", "",
         "| закон | спан | href | обёрнуто/ожидалось | гейт |", "|---|---|---|---|---|"]
    ok = True
    by_slug = {}
    for slug, ph, href, exp in WRAPS:
        by_slug.setdefault(slug, []).append((ph, href, exp))

    for slug, items in by_slug.items():
        p = al.FINAL / f"{slug}_structured.html"
        raw0 = p.read_text(encoding="utf-8")
        raw = raw0
        for ph, href, exp in items:
            raw, n = wrap_plain(raw, ph, href)
            g = "PASS" if n == exp else "**FAIL**"
            ok &= (n == exp)
            disp = re.sub(r"\\s\+", " ", ph)
            L.append(f"| {slug} | {disp[:60]}… | `{href.split('/')[-1]}` | {n}/{exp} | {g} |")
        t0, t1 = al.TextMap(raw0), al.TextMap(raw)
        inv = t0.nows == t1.nows
        nested = len(al.RE_NESTED_CLOSE.findall(raw))
        dbl = len(al.RE_DOUBLE_HREF.findall(raw))
        L.append(f"| {slug} | — файловые гейты — | | nows-инвариант={'PASS' if inv else 'FAIL'} "
                 f"| nested={nested} dbl={dbl} |")
        ok &= inv and nested == 0 and dbl == 0
        if apply_mode and ok:
            p.write_text(raw, encoding="utf-8")

    # ---- mapping ----
    mp = al.CONFIG / "npa_mapping.json"
    m = json.loads(mp.read_text(encoding="utf-8"))
    fixed_rows = []
    for k, v in m.items():
        if v == MAPPING_FIX["value_from"] and MAPPING_FIX["только_для_фраз_с"].lower() in k.lower():
            fixed_rows.append(k)
            m[k] = MAPPING_FIX["new"]
    added = [k for k in MAPPING_ADD if k not in m]
    m.update({k: v for k, v in MAPPING_ADD.items() if k in added})
    L += ["", f"## npa_mapping.json",
          f"- исправлено мусорных рядов «О гос. имуществе» K080000095_ -> Z1100000413: "
          f"**{len(fixed_rows)}**"]
    for k in fixed_rows:
        L.append(f"  - {k!r}")
    L.append(f"- добавлено фраз: **{len(added)}** {added}")
    if apply_mode and ok:
        mp.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")

    L.append(f"\n**ИТОГ: {'ВСЁ PASS' + (' — ПРИМЕНЕНО' if apply_mode else '') if ok else 'ЕСТЬ FAIL — НЕ ПРИМЕНЯТЬ'}**")
    (OUT / "01_wraps_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
