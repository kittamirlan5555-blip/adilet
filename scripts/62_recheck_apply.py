# -*- coding: utf-8 -*-
"""ANARA RE-CHECK — применение genuine-фиксов (обе формы, только +<a>).

Каждый FIX оборачивает PLAIN (не внутри <a>) вхождения REGEX в inner_main тем же
href в _structured И _ready. Видимый текст не меняется (gate get_text vs
backup_ANARA_RECHECK). Счётчики по формам печатаются (должны совпасть — иначе
дивергенция вырастет). DRY-RUN по умолчанию; --apply пишет.
"""
import re
import sys
import importlib.util
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
BK = ROOT / "data" / "final_backup_ANARA_RECHECK"
APPLY = "--apply" in sys.argv
ONLY = [a for a in sys.argv[1:] if not a.startswith("-")]

S = r"[\s ]+"

# FIXES: список (fix_id, code, regex, href, комментарий)
FIXES = [
    ("upk_uk_st3", "upk",
     r"стат[а-я]+" + S + r"3" + S + r"Уголовного" + S + r"кодекса" + S + r"Республики" + S + r"Казахстан",
     "https://adilet.zan.kz/rus/docs/K1400000226#z3002",
     "УПК: «статьи 3 Уголовного кодекса РК» -> УК ст.3 (z3002)"),
    # nalog «Особенной частью» (2×, -> #z3491) НАМЕРЕННО НЕ ПРИМЕНЯЕТСЯ:
    # 2-е вхождение стоит в начале <p id="z3811"> после прогона из 8 переводов
    # строки; обёртка ставит <a> сразу за ведущим пробелом абзаца, и html.parser
    # схлопывает эти 8 незначащих \n при ре-парсе -> get_text меняется на 8
    # пробельных символов (контент не теряется), что нарушило бы gate
    # «get_text неизменен / чанки не трогать». Это малозначимая структурная
    # самоссылка, уже залинкованная 6× в этом же коде -> SKIP.
    ("koap_osob_chast", "koap",
     r"Особенной" + S + r"част(?:и|ью)\b",
     "#z242",
     "КоАП: структ. «Особенной части/частью» -> Особенная часть (z242), REPEAT"),
    # nalog ст.363 «подпунктом 4) настоящей статьи» (1× PLAIN, line 47866):
    # подпункт 4) ст.363 ИМЕЕТ якорь #z6312 — это подтверждено двумя ссылками
    # внутри той же статьи (стр.47583 «<a href="#z6312">4)</a>», стр.47858
    # «<a href="#z6312">4)</a> настоящей статьи»). Конвенция корпуса: «подпунктом N)»
    # линкуется (9× «подпунктом 4)» в коде, 8 уже WRAPPED). Линкуем только сам
    # «подпунктом 4)»; lookahead на « настоящей статьи» гарантирует ровно 1 PLAIN
    # узел (стр.47866). Обёртка в середине абзаца <p id="z6314"> -> get_text byte-clean.
    ("nalog_st363_pp4", "nalog",
     r"подпунктом" + S + r"4\)(?=" + S + r"настоящей" + S + r"статьи)",
     "#z6312",
     "Налог ст.363: «подпунктом 4) настоящей статьи» -> подпункт 4) ст.363 (z6312)"),
]


def inner(soup):
    return soup.find("div", class_="inner_main") or soup.body or soup


def wrap_regex_plain(soup, rx, href):
    root = inner(soup)
    count = 0
    for node in list(root.find_all(string=True)):
        if node.find_parent("a") is not None:
            continue
        s = str(node)
        if not rx.search(s):
            continue
        parts = []
        last = 0
        for m in rx.finditer(s):
            if m.start() > last:
                parts.append(NavigableString(s[last:m.start()]))
            a = soup.new_tag("a", href=href)
            a.string = m.group(0)
            parts.append(a)
            last = m.end()
            count += 1
        if last < len(s):
            parts.append(NavigableString(s[last:]))
        parent = node.parent
        idx = parent.index(node)
        node.extract()
        for off, p in enumerate(parts):
            parent.insert(idx + off, p)
    return count


def gettext(html):
    return BeautifulSoup(html, "html.parser").get_text()


def main():
    L = ["ANARA RE-CHECK — применение genuine-фиксов",
         f"режим: {'APPLY' if APPLY else 'DRY-RUN'}", "=" * 90]
    # сгруппировать фиксы по коду
    by_code = {}
    for fid, code, rx, href, note in FIXES:
        if ONLY and fid not in ONLY and code not in ONLY:
            continue
        by_code.setdefault(code, []).append((fid, rx, href, note))
    allok = True
    for code, fixes in by_code.items():
        L.append("")
        L.append(f"### {code}")
        results = {}
        for form in ("structured", "ready"):
            html = (FINAL / f"{code}_{form}.html").read_text(encoding="utf-8")
            soup = BeautifulSoup(html, "html.parser")
            per = []
            for fid, rx, href, note in fixes:
                c = wrap_regex_plain(soup, re.compile(rx), href)
                per.append((fid, c, note))
            new_html = str(soup)
            vis_new = gettext(new_html)
            vis_bk = gettext((BK / f"{code}_{form}.html").read_text(encoding="utf-8"))
            g1 = vis_new == vis_bk
            results[form] = (per, new_html, g1, len(vis_bk), len(vis_new))
            for fid, c, note in per:
                L.append(f"  [{form:10}] {fid:16} обёрнуто={c:>3}  | {note}")
            L.append(f"  [{form:10}] G1 get_text vs backup: {'OK' if g1 else 'FAIL %d->%d' % (len(vis_bk), len(vis_new))}")
        # сверка счётчиков между формами
        cs = {fid: c for fid, c, _ in results["structured"][0]}
        cr = {fid: c for fid, c, _ in results["ready"][0]}
        balanced = all(cs[k] == cr.get(k) for k in cs)
        L.append(f"  СЧЁТЧИКИ structured==ready: {'OK' if balanced else 'MISMATCH %s vs %s' % (cs, cr)}")
        ok = results["structured"][2] and results["ready"][2] and balanced
        allok = allok and ok
        if APPLY and ok:
            (FINAL / f"{code}_structured.html").write_text(results["structured"][1], encoding="utf-8")
            (FINAL / f"{code}_ready.html").write_text(results["ready"][1], encoding="utf-8")
            L.append(f"  записано: {code}_structured.html + {code}_ready.html")
        elif APPLY:
            L.append("  НЕ записано (gate FAIL)")
    L.append("")
    L.append("ИТОГ: " + ("ОК" if allok else "ЕСТЬ ПРОБЛЕМА"))
    (ROOT / "data/reports/62_recheck_apply.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"written; APPLY={APPLY}; allok={allok}")


if __name__ == "__main__":
    main()
