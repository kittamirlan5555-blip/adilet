# -*- coding: utf-8 -*-
"""f06_corpus_actrefs.py — СИСТЕМНЫЙ ФИКС, Партия 2a: корпусно-резолвнутые акты.

Оборачивает ПОЛНЫМ СПАНОМ (§3) каждое плейн-вхождение фразы «Закон/Кодекс РК
"Название"», чьё название резолвится по корпусу в ЕДИНСТВЕННЫЙ НГР (живая ссылка
в любом из 43 final/*_structured.html) ИЛИ задано владельцем (KNOWN_NGR).
href = КОРЕНЬ внешнего акта `…/docs/{НГР}` (§4). Обе формы, одинаковый href.

Цели берутся НЕ хардкодом, а из того же резолвера, что и отчёт
reports/audit/corpus_resolve.md (find_plain_actrefs --corpus): список (a).
  • (b) «не резолвится» и КОНФЛИКТ-NGR (>1 в корпусе) — НЕ трогаем.
  • SKIP_TITLES (О кибербезопасности — закон не принят) — остаётся плейн.

Гейты (как f05/72): get_text sha ДО==ПОСЛЕ; нет вложенных <a>; dangling#z не
вырос; число обёрток == ожидаемому из резолвера; формы синхронны по числу.

Запуск:
    python scripts/audit/f06_corpus_actrefs.py            # DRY-RUN
    python scripts/audit/f06_corpus_actrefs.py --apply    # запись обеих форм
"""
import sys
import hashlib
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
from bs4 import BeautifulSoup, NavigableString
import find_plain_actrefs as fpa  # резолвер + регэксп + нормализация

HOST = "https://adilet.zan.kz/rus/docs/"
SKIP_PARENTS = {"a", "script", "style", "head", "title"}
FORMS = ("structured", "ready")


def gettext_sha(soup):
    return hashlib.sha256(soup.get_text().encode("utf-8")).hexdigest()


def in_skip(node):
    p = node.parent
    while p is not None:
        if getattr(p, "name", None) in SKIP_PARENTS:
            return True
        p = p.parent
    return False


def collect_ids(soup):
    ids = set()
    for t in soup.find_all(attrs={"id": True}):
        ids.add(t["id"])
    for t in soup.find_all(attrs={"name": True}):
        ids.add(t["name"])
    return ids


def dangling(soup):
    ids = collect_ids(soup)
    return sum(1 for a in soup.find_all("a", href=True)
              if a["href"].strip().startswith("#")
              and a["href"].strip()[1:] and a["href"].strip()[1:] not in ids)


def nested_count(soup):
    return sum(1 for a in soup.find_all("a") if a.find_parent("a") is not None)


def build_targets():
    """-> (RESOLVED{title_norm:ngr}, occ_by_title, skipped, conflict, missing)."""
    files = sorted(paths.FINAL.glob("*_structured.html"))
    all_plain = []
    for f in files:
        p, _, _ = fpa.scan_file(f)
        all_plain += p
    cm = fpa.build_corpus_linkmap(files)
    occ_by_title = defaultdict(list)
    for r in all_plain:
        if r["ngr_src"] != "—":
            continue
        key = fpa.norm(r["title"]) if r["title"] else fpa.norm(r["phrase"])
        occ_by_title[key].append(r)
    RESOLVED, skipped, conflict, missing = {}, {}, {}, {}
    for key, occ in occ_by_title.items():
        if key in fpa.SKIP_TITLES:
            skipped[key] = occ
        elif key in fpa.KNOWN_NGR:
            RESOLVED[key] = fpa.KNOWN_NGR[key]
        elif key in cm and len(cm[key]) == 1:
            RESOLVED[key] = next(iter(cm[key]))
        elif key in cm and len(cm[key]) > 1:
            conflict[key] = occ
        else:
            missing[key] = occ
    return RESOLVED, occ_by_title, skipped, conflict, missing


def file_hits(soup, RESOLVED):
    hits = []
    for t in soup.find_all(string=True):
        if not isinstance(t, NavigableString) or in_skip(t) or not str(t).strip():
            continue
        s = str(t)
        if "Республики Казахстан" not in s:
            continue
        spans = []
        for m in fpa.ACTREF.finditer(s):
            key = fpa.norm(fpa.extract_title(m.group(0)))
            if key in RESOLVED:
                spans.append((m.start(), m.end(), HOST + RESOLVED[key]))
        if spans:
            spans.sort()
            hits.append((t, spans))
    return hits


def main():
    apply_mode = "--apply" in sys.argv
    RESOLVED, occ_by_title, skipped, conflict, missing = build_targets()
    exp_total = sum(len(occ_by_title[k]) for k in RESOLVED)
    docs = sorted({r["doc"] for k in RESOLVED for r in occ_by_title[k]})

    log = ["APPLY (запись обеих форм)" if apply_mode else "DRY-RUN (без записи)", ""]
    log.append(f"актов-целей: {len(RESOLVED)}  ожидаем вхожд.(structured): {exp_total}")
    log.append(f"SKIP: {sum(len(v) for v in skipped.values())}  "
               f"КОНФЛИКТ: {len(conflict)}  НЕ-резолв(b): {sum(len(v) for v in missing.values())}")
    log.append("")

    per_act = defaultdict(int)
    grand = 0
    for code in docs:
        counts = {}
        objs = {}
        for form in FORMS:
            path = paths.FINAL / f"{code}_{form}.html"
            if not path.exists():
                continue
            soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
            hits = file_hits(soup, RESOLVED)
            counts[form] = sum(len(sp) for _, sp in hits)
            objs[form] = (path, soup, hits)
        # форм-синхрон
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
            sha0 = gettext_sha(soup); d0 = dangling(soup)
            for t, spans in hits:
                s = str(t); pieces = []; last = 0
                for a, b, href in spans:
                    if a > last:
                        pieces.append(NavigableString(s[last:a]))
                    link = soup.new_tag("a", href=href)
                    link.string = s[a:b]
                    pieces.append(link); last = b
                if last < len(s):
                    pieces.append(NavigableString(s[last:]))
                t.replace_with(*pieces)
            sha1 = gettext_sha(soup); d1 = dangling(soup); nc = nested_count(soup)
            assert sha1 == sha0, f"{code}/{form}: get_text ИЗМЕНИЛСЯ"
            assert nc == 0, f"{code}/{form}: вложенные <a>={nc}"
            assert d1 <= d0, f"{code}/{form}: dangling#z вырос {d0}->{d1}"
            path.write_text(str(soup), encoding="utf-8")
            log.append(f"   [{form}] ЗАПИСАНО +{counts[form]} sha-inv={sha0==sha1} "
                       f"nested={nc} dangling {d0}->{d1}")
        grand += sum(counts.values())

    assert sum(per_act.values()) == exp_total, \
        f"structured total {sum(per_act.values())} != ожид {exp_total}"
    log.append("")
    log.append("applied (structured)/акт:")
    # title -> ngr для печати
    for key in sorted(per_act, key=lambda k: -per_act[k]):
        log.append(f"  {per_act[key]:>2}×  [{RESOLVED[key]}]  «{occ_by_title[key][0]['title'][:60]}»")
    log.append("")
    log.append(f"ИТОГО обёрток по всем формам: {grand}  (structured {exp_total})")
    log.append("ОСТАЁТСЯ ПЛЕЙН:")
    log.append(f"  (b) ручной поиск: {sum(len(v) for v in missing.values())} вхожд. / {len(missing)} актов")
    log.append(f"  kibersec (SKIP): {sum(len(v) for v in skipped.values())} вхожд.")
    report = "\n".join(log)
    print(report)
    out = paths.AUDIT_OUT / "f06_corpus_actrefs_apply.txt"
    out.write_text(report + "\n", encoding="utf-8")
    print(f"\n[лог] {out}")


if __name__ == "__main__":
    main()
