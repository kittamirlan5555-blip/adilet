# -*- coding: utf-8 -*-
"""f07_manual_actrefs.py — СИСТЕМНЫЙ ФИКС, Партия 2b: акты с НГР, зарезолвленными
владельцем поиском по adilet (в корпусе живых ссылок не было → не резолвились авто).

Метод как f06/72: полный спан (§3), КОРЕНЬ внешнего акта `…/docs/{НГР}` (§4),
обе формы, одинаковый href, count-sync. Гейты — те же (get_text-инвариантность,
нет вложенных <a>, dangling#z не вырос, число обёрток == ожидаемому).

ИСКЛЮЧЕНО (НЕ линкуем):
  • gossimvoly/16 z45 «Конст. закон от 24.01.1996 "О государственных символах"» —
    переходная норма «Признать утратившим силу» на ПРЕДШЕСТВЕННИКА самого gossimvoly
    (тот же предмет/название) → самоотсылка, класс nalog/2/tamozhenniy/544 (§4).
    Зафиксировано в reports/audit/actref_exclusions.md.
  • О кибербезопасности — закон не принят (SKIP_TITLES в find_plain_actrefs).

Запуск:
    python scripts/audit/f07_manual_actrefs.py            # DRY-RUN
    python scripts/audit/f07_manual_actrefs.py --apply     # запись обеих форм
"""
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
from bs4 import BeautifulSoup, NavigableString
import find_plain_actrefs as fpa
import f06_corpus_actrefs as f06  # переиспользуем file_hits/гейт-хелперы

# norm(title) -> НГР (владелец, поиск по adilet; все ДЕЙСТВУЮТ, не repealed)
MANUAL = {
    "о миграции населения": "Z1100000477",
    "о правоохранительной службе": "Z1100000380",
    "об органах национальной безопасности республики казахстан": "Z950002710_",
    "о жилищных строительных сбережениях в республике казахстан": "Z000000110_",
    "о реабилитации жертв массовых политических репрессий": "Z930002200_",
    "об игорном бизнесе": "Z070000219_",
    "об охране селекционных достижений": "Z990000422_",
}


def main():
    apply_mode = "--apply" in sys.argv
    files = sorted(paths.FINAL.glob("*_structured.html"))
    all_plain = []
    for f in files:
        p, _, _ = fpa.scan_file(f)
        all_plain += p
    occ = defaultdict(list)
    for r in all_plain:
        if r["ngr_src"] != "—":
            continue
        key = fpa.norm(r["title"]) if r["title"] else fpa.norm(r["phrase"])
        if key in MANUAL:
            occ[key].append(r)
    exp_total = sum(len(v) for v in occ.values())
    docs = sorted({r["doc"] for v in occ.values() for r in v})

    log = ["APPLY (запись обеих форм)" if apply_mode else "DRY-RUN (без записи)", ""]
    missing_titles = [k for k in MANUAL if k not in occ]
    log.append(f"актов-целей: {len(MANUAL)}  найдено в плейне: {len(occ)}  "
               f"ожид. structured-вхожд.: {exp_total}")
    if missing_titles:
        log.append(f"⚠ не найдены плейн-вхождения для: {missing_titles}")

    per_act = defaultdict(int)
    grand = 0
    for code in docs:
        counts, objs = {}, {}
        for form in f06.FORMS:
            path = paths.FINAL / f"{code}_{form}.html"
            if not path.exists():
                continue
            soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
            hits = f06.file_hits(soup, MANUAL)
            counts[form] = sum(len(sp) for _, sp in hits)
            objs[form] = (path, soup, hits)
        if len(counts) == 2:
            assert counts["structured"] == counts["ready"], \
                f"{code}: формы рассинхрон {counts}"
        log.append(f"== {code}: { {f: counts[f] for f in counts} }")
        for form, (path, soup, hits) in objs.items():
            for t, spans in hits:
                for s, e, href in spans:
                    if form == "structured":
                        per_act[fpa.norm(fpa.extract_title(str(t)[s:e]))] += 1
            if not apply_mode:
                continue
            sha0 = f06.gettext_sha(soup); d0 = f06.dangling(soup)
            for t, spans in hits:
                s = str(t); pieces = []; last = 0
                for a, b, href in spans:
                    if a > last:
                        pieces.append(NavigableString(s[last:a]))
                    link = soup.new_tag("a", href=href); link.string = s[a:b]
                    pieces.append(link); last = b
                if last < len(s):
                    pieces.append(NavigableString(s[last:]))
                t.replace_with(*pieces)
            sha1 = f06.gettext_sha(soup); d1 = f06.dangling(soup); nc = f06.nested_count(soup)
            assert sha1 == sha0, f"{code}/{form}: get_text ИЗМЕНИЛСЯ"
            assert nc == 0, f"{code}/{form}: вложенные <a>={nc}"
            assert d1 <= d0, f"{code}/{form}: dangling#z вырос {d0}->{d1}"
            path.write_text(str(soup), encoding="utf-8")
            log.append(f"   [{form}] ЗАПИСАНО +{counts[form]} sha-inv={sha0 == sha1} "
                       f"nested={nc} dangling {d0}->{d1}")
        grand += sum(counts.values())

    assert sum(per_act.values()) == exp_total, \
        f"structured total {sum(per_act.values())} != ожид {exp_total}"
    log.append("\napplied (structured)/акт:")
    for key in sorted(per_act, key=lambda k: -per_act[k]):
        log.append(f"  {per_act[key]}× [{MANUAL[key]}] «{occ[key][0]['title'][:55]}»")
    log.append(f"\nИТОГО обёрток по всем формам: {grand}  (structured {exp_total})")
    report = "\n".join(log)
    print(report)
    out = paths.AUDIT_OUT / "f07_manual_actrefs_apply.txt"
    out.write_text(report + "\n", encoding="utf-8")
    print(f"\n[лог] {out}")


if __name__ == "__main__":
    main()
