# -*- coding: utf-8 -*-
"""R7 Пункт 0: РАЗМОРОЗКА линковки по внесённым ключам (правила §4 приняты:
gosuslugi/persdata прошли ревью без замечаний, вкл. 13 самоотсылок gosuslugi).

python scripts/audit/r7_00_unfreeze_counts.py [--apply]
-> reports/r7/00_unfreeze_report.md

Фразы «законодательств* РК <хвост>» (14 ключей: 6 R2 + 8 R6, все НГР
верифицированы ранее) оборачиваются ПОЛНЫМ СПАНОМ:
  - предмет ЧУЖОГО акта -> корень https://adilet.zan.kz/rus/docs/{НГР} (§4);
  - предмет СВОЕГО документа -> профильная статья «Законодательство…» (#якорь)
    — принятое правило самоотсылок.
ПРОПУСКАЮТСЯ: informatizacii/notariat/obrazovanie (пакет SDACHA_R2 ждёт ответа),
mestnoe_upravlenie (слинкован конвейером R6), сноски (class=note и «Сноска.»-зоны).
Гейты пер-файл: nows-инвариант, </a></a>=0 сырым, двойных href=0.
"""
import importlib.util
import json
import re
import sys
import bisect
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auditlib as al

spec = importlib.util.spec_from_file_location(
    "r2c", Path(__file__).parent / "r2_05_corpus_counts.py")
r2c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r2c)

SKIP = {"informatizacii", "notariat", "obrazovanie", "mestnoe_upravlenie"}
SELF_PROFILE = {  # slug -> профильная статья (самоотсылки)
    "koap": "1", "ocorrupt": "3", "persdata": "4",
}
RE_NOTE = re.compile(r'<(span|p)\b[^>]*class="note"[^>]*>.*?</\1\s*>', re.I | re.S)


def note_zones(raw, tm):
    zones = [(m.start(), m.end()) for m in RE_NOTE.finditer(raw)]
    for m in re.finditer(r"Сноска\.", tm.text):
        rp = tm.pos[m.start()]
        zones.append((rp, rp + 1200))
    zones.sort()
    return zones


def main():
    apply_mode = "--apply" in sys.argv
    cj = json.loads((al.MAPS / "codes.json").read_text(encoding="utf-8"))
    doc_ids = {k: v["doc_id"] for k, v in cj.items()
               if isinstance(v, dict) and "doc_id" in v}
    rxs = [(label, ngr, r2c.build_rx(tail)) for label, ngr, tail in r2c.PHRASES]

    L = ["# R7 Пункт 0 — разморозка линковки по внесённым ключам", "",
         f"Режим: {'APPLY' if apply_mode else 'DRY-RUN'}. Пропуски: {sorted(SKIP)} "
         "(пакет у ревьюера / свежепострен), сноски.", "",
         "| документ | форма | ключ | обёрнуто | цель |", "|---|---|---|---|---|"]
    total = 0
    touched = set()
    for slug in al.all_slugs():
        if slug in SKIP:
            continue
        own_id = doc_ids.get(slug)
        amap_p = al.MAPS / f"article_map_{slug}.json"
        amap = json.loads(amap_p.read_text(encoding="utf-8")) if amap_p.exists() else {}
        for form, p in al.doc_files(slug).items():
            raw0 = p.read_text(encoding="utf-8")
            raw = raw0
            doc_n = 0
            for label, ngr, rx in rxs:
                if ngr == own_id:
                    prof = SELF_PROFILE.get(slug)
                    anc = amap.get(prof) if prof else None
                    href = f"#{anc}" if anc else None
                    tgt = f"#{anc} (своя ст.{prof})" if anc else None
                else:
                    href = f"https://adilet.zan.kz/rus/docs/{ngr}"
                    tgt = ngr
                if href is None:
                    continue
                n_key = 0
                while True:
                    tm = al.TextMap(raw)
                    links = [(m.start(), m.end()) for m in al.RE_A_PAIR.finditer(raw)]
                    ls = [a for a, b in links]
                    zones = note_zones(raw, tm)
                    zs = [a for a, b in zones]
                    hit = None
                    for m in rx.finditer(tm.text):
                        rp = tm.pos[m.start()]
                        i = bisect.bisect_right(ls, rp) - 1
                        if i >= 0 and links[i][0] <= rp < links[i][1]:
                            continue
                        j = bisect.bisect_right(zs, rp) - 1
                        if j >= 0 and zones[j][0] <= rp < zones[j][1]:
                            continue
                        a_raw = tm.pos[m.start()]
                        b_raw = tm.pos[m.end() - 1] + 1
                        seg = raw[a_raw:b_raw]
                        if "<a" in seg or "</a" in seg:
                            continue
                        hit = (a_raw, b_raw, seg)
                        break
                    if hit is None:
                        break
                    a_raw, b_raw, seg = hit
                    raw = raw[:a_raw] + f'<a href="{href}">{seg}</a>' + raw[b_raw:]
                    n_key += 1
                if n_key:
                    L.append(f"| {slug} | {form} | {label} | {n_key} | {tgt} |")
                    total += n_key
                    doc_n += n_key
            if doc_n:
                tm0, tm1 = al.TextMap(raw0), al.TextMap(raw)
                assert tm0.nows == tm1.nows, f"{slug}_{form}: ТЕКСТ ИЗМЕНИЛСЯ"
                assert not al.RE_NESTED_CLOSE.findall(raw)
                assert not al.RE_DOUBLE_HREF.findall(raw)
                touched.add(slug)
                if apply_mode:
                    p.write_text(raw, encoding="utf-8")
    L += ["", f"**Всего обёрнуто: {total}; затронуто документов: {len(touched)}** "
          f"({sorted(touched)})",
          "", "Гейты пер-файл: nows-инвариант, nested=0, dbl=0 (assert)."]
    out = al.ROOT / "reports" / "r7"
    out.mkdir(parents=True, exist_ok=True)
    (out / "00_unfreeze_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[-6:]))
    print("touched:", " ".join(sorted(touched)))


if __name__ == "__main__":
    main()
