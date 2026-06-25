# -*- coding: utf-8 -*-
"""f08_historical_dated.py — СИСТЕМНЫЙ ФИКС, финал Section A: датированные истор. отсылки.

nalog ст.828/833/848 «Кодекс РК ОТ 25 ДЕКАБРЯ 2017 ГОДА "О налогах…"» (×5) —
датированная отсылка на ОТМЕНЁННУЮ редакцию НК-2017. Решение владельца: линковать
на КОРЕНЬ старого акта `…/docs/K1700000120` (§4, видимая фраза называет ред. 2017,
ремап на 2025 ЗАПРЕЩЁН). Полный спан, обе формы, count-sync.

Гейт freshness: nalog — ПРЕЕМНИК K1700000120 (own_id=K2500000214==STALE_REMAP target),
поэтому 74 классифицирует эти ссылки как hist_links (легитимно, не stale) — без
HISTORICAL_DATED. Регресс-тест: scripts/tests/test_nalog_hist_2017.py.

ЖЁСТКИЙ ФИЛЬТР: только nalog, title «о налогах и других обязательных платежах в
бюджет» И фраза содержит «25 декабря 2017». Так z18 (самоназвание БЕЗ даты, §4
самоотсылка) НЕ трогается, и «Закон "О введении в действие…"» (иной title) тоже.

Запуск:
    python scripts/audit/f08_historical_dated.py            # DRY-RUN
    python scripts/audit/f08_historical_dated.py --apply
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
from bs4 import BeautifulSoup, NavigableString
import find_plain_actrefs as fpa
import f06_corpus_actrefs as f06

CODE = "nalog"
TITLE_NORM = "о налогах и других обязательных платежах в бюджет"
DATE_MARK = "25 декабря 2017"
NGR = "K1700000120"
HREF = "https://adilet.zan.kz/rus/docs/" + NGR
EXPECT = 5


def file_hits(soup):
    """Плейн ACTREF с нужным title И датой 25.12.2017 -> (node, [(s,e,href)])."""
    hits = []
    for t in soup.find_all(string=True):
        if not isinstance(t, NavigableString) or f06.in_skip(t) or not str(t).strip():
            continue
        s = str(t)
        if "Республики Казахстан" not in s or DATE_MARK not in s:
            continue
        spans = []
        for m in fpa.ACTREF.finditer(s):
            ph = m.group(0)
            if DATE_MARK in ph and fpa.norm(fpa.extract_title(ph)) == TITLE_NORM:
                spans.append((m.start(), m.end(), HREF))
        if spans:
            spans.sort()
            hits.append((t, spans))
    return hits


def main():
    apply_mode = "--apply" in sys.argv
    log = ["APPLY (обе формы)" if apply_mode else "DRY-RUN", ""]
    counts = {}
    objs = {}
    for form in f06.FORMS:
        path = paths.FINAL / f"{CODE}_{form}.html"
        if not path.exists():
            continue
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        hits = file_hits(soup)
        counts[form] = sum(len(sp) for _, sp in hits)
        objs[form] = (path, soup, hits)
    log.append(f"nalog ст.828/833/848 -> {NGR} (root): { {f: counts[f] for f in counts} } (ожид {EXPECT})")
    for f, n in counts.items():
        assert n == EXPECT, f"{CODE}/{f}: найдено {n} != {EXPECT}"
    if len(counts) == 2:
        assert counts["structured"] == counts["ready"], "формы рассинхрон"

    for form, (path, soup, hits) in objs.items():
        for t, spans in hits:
            for s, e, href in spans:
                log.append(f"   [{form}] +<a {NGR}> {str(t)[s:e][:78]}")
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
        assert sha1 == sha0, f"{CODE}/{form}: get_text ИЗМЕНИЛСЯ"
        assert nc == 0, f"{CODE}/{form}: вложенные <a>={nc}"
        assert d1 <= d0, f"{CODE}/{form}: dangling#z вырос {d0}->{d1}"
        path.write_text(str(soup), encoding="utf-8")
        log.append(f"   [{form}] ЗАПИСАНО +{counts[form]} sha-inv={sha0 == sha1} "
                   f"nested={nc} dangling {d0}->{d1}")

    report = "\n".join(log)
    print(report)
    out = paths.AUDIT_OUT / "f08_historical_dated_apply.txt"
    out.write_text(report + "\n", encoding="utf-8")
    print(f"\n[лог] {out}")


if __name__ == "__main__":
    main()
