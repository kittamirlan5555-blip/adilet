# -*- coding: utf-8 -*-
"""ФИКС-РАУНД БЛОК 2: мислинки по 03_links_*.json.

python scripts/audit/f02_fix_mislinks.py [--apply]
-> data/reports/audit/07_fixround_block2.md

Операции: RETARGET (смена href при том же видимом тексте) и UNLINK (снятие <a>,
текст остаётся). Гейты пер-файл: nows-инвариантность vs снапшот до правки,
вложенных </a></a> = 0, двойных href = 0; пер-ретаргет: новый якорь обязан
резолвиться в статью с номером из текста (резолвер a03).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auditlib as al

# (slug, op, old_href, link_text, new_href|None, причина)
FIXES = [
    # koap: перечневый off-by-one (аудит 03) -> ретаргет по article_map_koap
    ("koap", "retarget", "#z1239", "368", "#z1242", "перечень бил в тело ст.367"),
    ("koap", "retarget", "#z1246", "370", "#z1248", "перечень бил в ст.369"),
    ("koap", "retarget", "#z1249", "371", "#z1253", "перечень бил в ст.370"),
    ("koap", "retarget", "#z1263", "375", "#z1265", "перечень бил в ст.374"),
    ("koap", "retarget", "#z4780", "381", "#z1275", "перечень бил в ст.380-1"),
    ("koap", "retarget", "#z1288", "386", "#z1290", "перечень бил в ст.385"),
    ("koap", "retarget", "#z1292", "388", "#z1294", "перечень бил в ст.387"),
    # koap: статей 173 и 312 НЕТ в выгрузке (класс УК-380-3) -> снять ссылку
    ("koap", "unlink", "#z556", "173", None, "ст.173 нет в выгрузке; вёл в тело ст.172"),
    ("koap", "unlink", "#z1127", "312", None, "ст.312 нет в выгрузке; вёл в ст.311"),
    # zemelnyy: 44-2 бил в 44-1
    ("zemelnyy", "retarget", "#z2002", "44-2", "#z2008", "бил в ст.44-1; 44-2=z2008 по карте"),
    # grazhdanskiy_osob: битые cross-якоря generic-отсылок -> корень акта (§4)
    ("grazhdanskiy_osob", "retarget",
     "https://adilet.zan.kz/rus/docs/Z970000094_#z152", "Закона",
     "https://adilet.zan.kz/rus/docs/Z970000094_", "якоря z152 нет в цели; generic -> корень"),
    ("grazhdanskiy_osob", "retarget",
     "https://adilet.zan.kz/rus/docs/K2300000224#z0", "Социальным кодексом",
     "https://adilet.zan.kz/rus/docs/K2300000224", "якоря z0 нет; generic -> корень"),
    # socialnyy: «статьей 9-4» — статья ЧУЖОГО закона -> корень акта (решение шефа)
    ("socialnyy", "retarget", "#z198", "статьей 9-4",
     "https://adilet.zan.kz/rus/docs/Z030000474_",
     "9-4 = статья Z030000474_, бил в собственную ст.9 (прецедент)"),
    # nalog: «статьи 351-1» — статья НК-2017, в НК-2025 нет -> снять (решение шефа)
    ("nalog", "unlink", "#z6174", "статьи 351-1", None,
     "цитата на НК-2017; бил в собственную ст.351 (прецедент)"),
    # ОТЛОЖЕНО до Блока 3: grazhdanskiy_osob «статей 151-152» -> K940001000_#z151h
    # (у ст.151 ГК нет якоря — инжекция в Блоке 3, ретаргет там же)
]


def find_links(raw, old, text):
    """Все вхождения <a href=old>text</a> (текст сравнивается strip_tags)."""
    hits = []
    for m in al.RE_A_PAIR.finditer(raw):
        if m.group(1) == old and al.strip_tags(m.group(2)) == text:
            hits.append(m)
    return hits


def main():
    apply_mode = "--apply" in sys.argv
    L = ["# ФИКС-РАУНД БЛОК 2 — мислинки (03_links_*.json)", "",
         f"Режим: {'APPLY' if apply_mode else 'DRY-RUN'}.", "",
         "| документ | форма | операция | текст | старый href | новый | вхожд. | резолв-гейт |",
         "|---|---|---|---|---|---|---|---|"]
    by_slug = {}
    for fx in FIXES:
        by_slug.setdefault(fx[0], []).append(fx)

    total = 0
    for slug, fixes in by_slug.items():
        # резолвер цели: для внутренних — сам документ
        doc = None
        for form in ("ready", "structured"):
            p = al.FINAL / f"{slug}_{form}.html"
            if not p.exists():
                continue
            raw0 = p.read_text(encoding="utf-8")
            raw = raw0
            for _slug, op, old, text, new, why in fixes:
                hits = find_links(raw, old, text)
                gate = "—"
                if op == "retarget" and new.startswith("#"):
                    if doc is None or doc.slug != slug:
                        import importlib
                        a03 = importlib.import_module("a03_links")
                        doc = a03.Doc(slug)
                    res, ap_ = doc.resolve(new[1:])
                    gate = ("PASS" if res and text.split()[-1] in res
                            else f"**FAIL res={res}**")
                for m in reversed(hits):
                    if op == "retarget":
                        newtag = m.group(0).replace(f'href="{old}"', f'href="{new}"', 1)
                        raw = raw[:m.start()] + newtag + raw[m.end():]
                    else:                                   # unlink
                        raw = raw[:m.start()] + m.group(2) + raw[m.end():]
                L.append(f"| {slug} | {form} | {op} | {text!r} | `{old}` | "
                         f"`{new or '(plain)'}` | {len(hits)} | {gate} |")
                total += len(hits)
            # гейты пер-файл
            t0, t1 = al.TextMap(raw0), al.TextMap(raw)
            assert t0.nows == t1.nows, f"{slug}_{form}: get_text ИЗМЕНИЛСЯ!"
            assert not al.RE_NESTED_CLOSE.findall(raw), f"{slug}_{form}: nested!"
            assert not al.RE_DOUBLE_HREF.findall(raw), f"{slug}_{form}: dbl href!"
            if apply_mode:
                p.write_text(raw, encoding="utf-8")

    L += ["", f"**Всего заменённых/снятых вхождений: {total}** "
          "(вхождений > кейсов: koap 173 встречается 3 раза тем же паром href+текст).",
          "", "Гейты пер-файл: nows-инвариант (assert), nested=0, double=0.",
          "", "ОТЛОЖЕНО в Блок 3: grazhdanskiy_osob «статей 151-152» -> якорь ст.151 "
          "ГК (статья без якоря, нужна инжекция z151h)."]
    al.AUDIT_OUT.mkdir(parents=True, exist_ok=True)
    (al.AUDIT_OUT / "07_fixround_block2.md").write_text("\n".join(L) + "\n",
                                                        encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
