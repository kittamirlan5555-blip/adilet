# -*- coding: utf-8 -*-
"""ГЕЙТЫ ОТДАЧИ (§2.1/§6 CLAUDE.md + методика УПК-раунда). READ-ONLY.

Гонять ПЕРЕД ЛЮБОЙ отдачей файлов. Проверяет обе формы документа
(data/final/{doc}_structured.html и {doc}_ready.html — какие существуют):

  G1. `</a>\\s*</a>` == 0 СЫРЫМ ПОИСКОМ (НЕ через BeautifulSoup: lxml/html.parser
      автозакрывают вложенные <a> и гейт через soup СЛЕП — пойманный баг УПК-раунда).
  G2. вложенных <a> == 0 (сырой скан глубины открытий/закрытий <a>).
  G3. двойных href в одном теге == 0.
  G4. битых внутренних #z == 0 (каждый href="#x" существует как id=/name= в файле).
  G5. cross-code якоря существуют в файле-цели (для целей из нашего корпуса
      config/codes.json; чужие документы проверить нечем — пропускаются).
  G6. формы синхронны: множества пар (canon-href, text) обеих форм совпадают,
      содержательных расхождений 0 (self-абсолютные ссылки канонизируются в #z).

Запуск:
  python 71_gates.py --doc upk [--doc nalog ...] [--strict]
    --strict: exit 1 при любом красном гейте.
Отчёт: data/reports/71_gates_{doc}.txt
"""
import re
import sys
import json
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

ROOT = paths.ROOT
FINAL = paths.FINAL
CONFIG = paths.MAPS      # config/ слит в maps/ (Фаза A)
REPORTS = paths.REPORTS

HOST = "https://adilet.zan.kz/rus/docs/"

RE_A_TAG = re.compile(r"<a\b[^>]*>|</a\s*>", re.I)
RE_NESTED_CLOSE = re.compile(r"</a>\s*</a>")
RE_DOUBLE_HREF = re.compile(r"<a[^>]*href=[^>]*href=")
RE_INTERNAL = re.compile(r'href="#([^"]+)"')
RE_IDS = re.compile(r'(?:id|name)="([^"]+)"')
RE_CROSS = re.compile(r'href="[^"]*?/docs/([A-Za-z0-9_]+)#([^"]+)"')
RE_A_PAIR = re.compile(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a\s*>', re.I | re.S)
RE_TAGS = re.compile(r"<[^>]+>")


def codes_map():
    cj = json.loads((CONFIG / "codes.json").read_text(encoding="utf-8"))
    return {v["doc_id"]: k for k, v in cj.items()
            if isinstance(v, dict) and "doc_id" in v}


def own_doc_id(doc):
    cj = json.loads((CONFIG / "codes.json").read_text(encoding="utf-8"))
    v = cj.get(doc)
    return v.get("doc_id") if isinstance(v, dict) else None


def file_for(code):
    for suf in ("_ready.html", "_structured.html"):
        p = FINAL / f"{code}{suf}"
        if p.exists():
            return p
    return None


def nested_depth_violations(raw):
    """Сырой скан: число открытий <a> при уже открытом <a> (+ дисбаланс)."""
    depth = 0
    nested = 0
    unbalanced = 0
    for m in RE_A_TAG.finditer(raw):
        if m.group(0)[1] != "/":
            depth += 1
            if depth > 1:
                nested += 1
        else:
            depth -= 1
            if depth < 0:
                unbalanced += 1
                depth = 0
    return nested, unbalanced + (1 if depth != 0 else 0)


def broken_internal(raw):
    ids = set(RE_IDS.findall(raw))
    return sorted({h for h in RE_INTERNAL.findall(raw) if h not in ids})


def cross_missing(raw, d2c, ids_cache):
    """[(docid, anchor)] — якоря на НАШИ документы, которых нет в файле-цели."""
    missing = []
    for docid, anchor in set(RE_CROSS.findall(raw)):
        code = d2c.get(docid)
        if code is None:
            continue                      # чужой документ — проверить нечем
        if docid not in ids_cache:
            p = file_for(code)
            ids_cache[docid] = set(RE_IDS.findall(
                p.read_text(encoding="utf-8"))) if p else None
        ids = ids_cache[docid]
        if ids is None:
            continue
        if anchor not in ids:
            missing.append((docid, anchor))
    return sorted(missing)


def canon_pairs(raw, own):
    """Counter пар (canon-href, текст-без-тегов-схлопнутый) всех <a href>."""
    pairs = Counter()
    for href, inner in RE_A_PAIR.findall(raw):
        h = href.strip()
        if own:
            if h.startswith(HOST + own + "#"):
                h = "#" + h.split("#", 1)[1]
            elif h == HOST + own:
                h = "@SELF_ROOT"
        t = re.sub(r"\s+", " ", RE_TAGS.sub("", inner)).strip()
        pairs[(h, t)] += 1
    return pairs


def run_doc(doc, d2c, ids_cache):
    forms = [p for p in (FINAL / f"{doc}_structured.html",
                         FINAL / f"{doc}_ready.html") if p.exists()]
    L = []
    P = L.append
    P("=" * 100)
    P(f"71_gates — {doc} — формы: {[p.name for p in forms] or 'НЕТ ФАЙЛОВ'}")
    P("=" * 100)
    red = 0
    if not forms:
        P("RED: файлов документа нет в data/final")
        return L, 1

    own = own_doc_id(doc)
    raws = {}
    for p in forms:
        raw = p.read_text(encoding="utf-8")
        raws[p.name] = raw

        g1 = len(RE_NESTED_CLOSE.findall(raw))
        g2, unbal = nested_depth_violations(raw)
        g3 = len(RE_DOUBLE_HREF.findall(raw))
        g4 = broken_internal(raw)
        g5 = cross_missing(raw, d2c, ids_cache)

        def line(name, bad, detail):
            nonlocal red
            status = "GREEN" if not bad else "RED"
            if bad:
                red += 1
            P(f"  [{status}] {name:28} {detail}")

        P(f"\n-- {p.name}")
        line("G1 </a></a> raw", g1, f"{g1}")
        line("G2 вложенные <a> (depth)", g2 or unbal, f"nested={g2} unbalanced={unbal}")
        line("G3 двойной href", g3, f"{g3}")
        line("G4 битые внутренние #z", g4, f"{len(g4)}" + (f" напр. {g4[:6]}" if g4 else ""))
        line("G5 cross-code якоря", g5, f"missing={len(g5)}" +
             (f" напр. {g5[:5]}" if g5 else " (все цели корпуса резолвятся)"))

    if len(forms) == 2:
        a, b = (canon_pairs(raws[p.name], own) for p in forms)
        only_a = set(a) - set(b)
        only_b = set(b) - set(a)
        diverge = len(only_a) + len(only_b)
        status = "GREEN" if diverge == 0 else "RED"
        if diverge:
            red += 1
        P(f"\n  [{status}] G6 синхронность форм        расхождений={diverge}")
        for h, t in sorted(only_a)[:5]:
            P(f"      только в {forms[0].name}: ({h!r}, {t[:50]!r})")
        for h, t in sorted(only_b)[:5]:
            P(f"      только в {forms[1].name}: ({h!r}, {t[:50]!r})")
    else:
        P("\n  [----] G6 синхронность форм        (одна форма — сравнивать не с чем)")

    P(f"\nИТОГ {doc}: {'ВСЁ ЗЕЛЁНОЕ' if red == 0 else f'КРАСНЫХ ГЕЙТОВ: {red}'}")
    return L, red


def main():
    docs = []
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        if argv[i] == "--doc" and i + 1 < len(argv):
            docs.append(argv[i + 1])
            i += 2
        elif not argv[i].startswith("--"):
            docs.append(argv[i])
            i += 1
        else:
            i += 1
    strict = "--strict" in argv
    if not docs:
        print("usage: python 71_gates.py --doc {slug} [--doc ...] [--strict]")
        sys.exit(2)

    d2c = codes_map()
    ids_cache = {}
    total_red = 0
    REPORTS.mkdir(parents=True, exist_ok=True)
    for doc in docs:
        L, red = run_doc(doc, d2c, ids_cache)
        total_red += red
        out = REPORTS / f"71_gates_{doc}.txt"
        out.write_text("\n".join(L) + "\n", encoding="utf-8")
        print("\n".join(L))
        print(f"-> {out}\n")

    if strict and total_red:
        sys.exit(1)


if __name__ == "__main__":
    main()
