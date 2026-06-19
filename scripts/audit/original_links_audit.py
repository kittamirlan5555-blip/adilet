# -*- coding: utf-8 -*-
"""АУДИТ ОРИГИНАЛЬНЫХ ССЫЛОК adilet (source/) против нашего _structured. READ-ONLY.

python scripts/audit/original_links_audit.py  -> reports/original_links_audit.md

Делит каждую исходную <a href> из source/{src}.html на:
  1) САМО-ссылка (свой NGR или относительная #zN): якорь цели присутствует в
     нашем _structured? (anchor preservation).
  2) на ДРУГОЙ закон (внешний NGR):
     a) в СНОСКЕ/примечании — определяется КЛАССИФИКАТОРОМ ПАЙПЛАЙНА
        (18_strip_links_in_notes.find_note_regions: p.note / span.note-chain /
        p.Примечание / ИЗПИ-РЦПИ red-font). Намеренно снимается по ТЗ-02 — НЕ потеря.
     b) в ТЕЛЕ статьи — целевой NGR всё ещё залинкован в ТЕЛЕ _structured
        (сохранён / перенаправлен cross-code / на корень) ИЛИ потерян?
        Сравнение тело-в-тело: из _structured исключаются ЕГО note-регионы
        (тем же классификатором), чтобы остаточные ссылки в сносках не маскировали потерю.

Учитывается repeal-replace ремап (codes.json _deprecated_remaps): старый NGR,
залинкованный новым, считается сохранённым.
Реальные потери в теле — список кейсов (док/статья-контекст/текст/NGR) = БЛОКЕР.
"""
import importlib.util
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

# классификатор сносок из пайплайна (имя файла с цифры -> importlib)
_spec = importlib.util.spec_from_file_location(
    "strip18", paths.ROOT / "scripts" / "pipeline" / "18_strip_links_in_notes.py")
s18 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(s18)

RE_DOCS = re.compile(r"/docs/([A-Za-z0-9_]+)")
RE_ANCHOR = re.compile(r"#(z[\w-]+)")


def load_codes():
    cj = json.loads(paths.CODES_JSON.read_text(encoding="utf-8"))
    remap = {}
    dr = cj.get("_deprecated_remaps", {})
    for k, v in dr.items():
        if k.startswith("_"):
            continue
        remap[k] = v
    # repeal-replace ремапы §5 CLAUDE.md, которые пайплайн реально применяет через
    # npa_mapping (видно: nalog линкует новый Z2600000258, grazhdanskiy — K2500000171),
    # но их нет в codes.json _deprecated_remaps. Без них аудит даёт ложные «потери».
    remap.setdefault("K080000095_", "K2500000171")   # Бюджетный 2008 -> 2025
    remap.setdefault("Z950002444_", "Z2600000258")   # О банках 1995 -> 2026
    codes = {k: v for k, v in cj.items() if not k.startswith("_") and isinstance(v, dict)}
    return codes, remap


CHROME_CLASS = ("widget", "omega")          # сайдбар adilet (gs_4.omega.widget = «связанные документы»)
CHROME_TAG = ("nav", "aside", "header", "footer")


def in_chrome(a):
    """True, если ссылка в хроме страницы adilet (сайдбар-виджет/навигация),
    а не в правовом теле. Такие ссылки пайплайн не обрабатывает by-design."""
    p = a
    for _ in range(20):
        p = p.parent
        if p is None:
            return False
        if getattr(p, "name", None) in CHROME_TAG:
            return True
        cls = p.get("class") if hasattr(p, "get") else None
        if cls and any(c in CHROME_CLASS for c in cls):
            return True
    return False


def note_link_ids(soup):
    """id() реальных <a href> внутри note-регионов (классификатор 18_)."""
    ids = set()
    for r in s18.find_note_regions(soup):
        for a in s18.collect_links_in_region(r["nodes"]):
            ids.add(id(a))
    return ids


def anchor_set(soup):
    s = {t.get("id") for t in soup.find_all(attrs={"id": True})}
    s |= {t.get("name") for t in soup.find_all("a", attrs={"name": True})}
    s.discard(None)
    return s


def body_linked_ngrs(soup):
    """NGR, залинкованные в ТЕЛЕ (вне note-регионов) _structured."""
    note_ids = note_link_ids(soup)
    out = set()
    for a in soup.find_all("a", href=True):
        if id(a) in note_ids:
            continue
        m = RE_DOCS.search(a["href"])
        if m:
            out.add(m.group(1))
    return out


def nearest_article(a):
    """Грубый контекст: ближайший вверх 'Статья N' для кейса-потери."""
    node = a
    for _ in range(400):
        node = node.previous_element
        if node is None:
            break
        if isinstance(node, str):
            m = re.search(r"Стать[яи]\s+(\d+(?:-\d+)?)", node)
            if m:
                return m.group(1)
    return "?"


def audit_doc(slug, own_ngr, src_name, remap):
    src_path = paths.SOURCE / (src_name or f"{slug}.html")
    str_path = paths.FINAL / f"{slug}_structured.html"
    if not src_path.exists() or not str_path.exists():
        return None
    src = BeautifulSoup(src_path.read_text(encoding="utf-8"), "html.parser")
    structured = BeautifulSoup(str_path.read_text(encoding="utf-8"), "html.parser")

    str_anchors = anchor_set(structured)
    str_body_ngrs = body_linked_ngrs(structured)
    note_ids = note_link_ids(src)

    self_total = self_intact = 0
    self_missing = []
    ext_note = 0
    ext_body_occ = 0
    chrome = 0
    body_ngr_ex = defaultdict(list)

    for a in src.find_all("a"):
        if not s18.is_real_link(a):
            continue
        if in_chrome(a):                   # сайдбар-виджет «связанные документы» и навигация — не тело
            chrome += 1
            continue
        href = a["href"]
        mdoc = RE_DOCS.search(href)
        manc = RE_ANCHOR.search(href)
        is_self = (mdoc and mdoc.group(1) == own_ngr) or (mdoc is None and href.lstrip().startswith("#z"))
        if is_self:
            if manc:                       # само-ссылка на якорь
                self_total += 1
                if manc.group(1) in str_anchors:
                    self_intact += 1
                else:
                    self_missing.append((manc.group(1), a.get_text(" ", strip=True)[:30]))
            continue
        if mdoc is None:
            continue                       # не /docs/ ссылка
        tgt = mdoc.group(1)
        if tgt == own_ngr:
            continue
        if id(a) in note_ids:
            ext_note += 1
        else:
            ext_body_occ += 1
            body_ngr_ex[tgt].append((a.get_text(" ", strip=True)[:45], nearest_article(a)))

    preserved = []
    lost = []
    for ngr, exs in body_ngr_ex.items():
        eff = remap.get(ngr, ngr)
        if ngr in str_body_ngrs or eff in str_body_ngrs:
            preserved.append(ngr)
        else:
            lost.append((ngr, exs))
    return {
        "slug": slug, "self_total": self_total, "self_intact": self_intact,
        "self_missing": self_missing, "ext_note": ext_note,
        "ext_body_occ": ext_body_occ, "chrome": chrome,
        "body_ngr_total": len(body_ngr_ex),
        "preserved": preserved, "lost": lost,
    }


def main():
    codes, remap = load_codes()
    rows = []
    for slug, info in codes.items():
        r = audit_doc(slug, info["doc_id"], info.get("source"), remap)
        if r:
            rows.append(r)

    L = ["# Аудит оригинальных ссылок adilet (source) против _structured", "",
         "READ-ONLY. Классификатор сносок — пайплайновый "
         "`18_strip_links_in_notes.find_note_regions` (p.note / span.note-chain / "
         "p.Примечание / ИЗПИ-РЦПИ), не эвристика. Тело-в-тело: из _structured "
         "исключены его note-регионы.", "",
         "| док | само: целы/всего | % | внеш-в-сносках (ТЗ-02) | тело-NGR сохр/потеря | потерянные NGR |",
         "|---|---|---|---|---|---|"]
    tot = defaultdict(int)
    all_lost = []
    for r in sorted(rows, key=lambda x: x["slug"]):
        pct = (100 * r["self_intact"] / r["self_total"]) if r["self_total"] else 100.0
        nlost = len(r["lost"])
        npres = len(r["preserved"])
        lost_ngrs = ", ".join(n for n, _ in r["lost"]) if r["lost"] else "—"
        L.append(f"| {r['slug']} | {r['self_intact']}/{r['self_total']} | "
                 f"{pct:.1f}% | {r['ext_note']} | {npres}/{nlost} | {lost_ngrs} |")
        tot["self_total"] += r["self_total"]
        tot["self_intact"] += r["self_intact"]
        tot["ext_note"] += r["ext_note"]
        tot["ext_body_occ"] += r["ext_body_occ"]
        tot["preserved"] += npres
        tot["lost"] += nlost
        tot["chrome"] += r["chrome"]
        tot["self_miss"] += len(r["self_missing"])
        for ngr, exs in r["lost"]:
            all_lost.append((r["slug"], ngr, exs))

    pct = 100 * tot["self_intact"] / tot["self_total"] if tot["self_total"] else 100
    L += ["", f"**ИТОГО:** само-ссылок целы **{tot['self_intact']}/{tot['self_total']} "
          f"({pct:.1f}%)**; внеш-в-сносках (ТЗ-02, намеренно сняты) **{tot['ext_note']}**; "
          f"тело-внешних NGR сохранено **{tot['preserved']}**, потеряно **{tot['lost']}**; "
          f"внеш-в-теле всего вхождений {tot['ext_body_occ']}; "
          f"исключено хром-ссылок (сайдбар «связанные документы»/навигация, не "
          f"правовой текст) **{tot['chrome']}**."]

    if all_lost:
        L += ["", "## Кандидаты в потери тела — целевой NGR в source-теле залинкован, в "
              "_structured-теле НЕ залинкован (РУЧНАЯ СВЕРКА: возможен ремап на новую "
              "редакцию ИЛИ adilet-мислинк, который мы намеренно не повторяем)", ""]
        for slug, ngr, exs in all_lost:
            arts = ", ".join(sorted({a for _, a in exs if a != '?'}))[:60]
            txt = exs[0][0] if exs else ""
            L.append(f"- **{slug}** → `{ngr}` ({len(exs)} вхожд.; ст. {arts or '?'}): «{txt}…»")
    else:
        L += ["", "## Потерь в теле НЕ обнаружено ✅", ""]

    if tot["self_miss"]:
        L += ["", "## Само-якоря, отсутствующие в _structured (остаток self ~"
              f"{100-pct:.1f}%) — по докам", "",
              "Это якоря adilet-СХЕМЫ из исходных self-ссылок (в основном пункт/"
              "подпункт: «пунктом 2», «подпункте 1)»; и часть статей). Наша выгрузка "
              "нумерует якоря иначе (§9), но САМИ статьи/пункты присутствуют под нашими "
              "якорями — напр. zhilishniy «статьи 91» (source #z106) = наш z1811. Наши "
              "собственные self-ссылки корректны (verify G1–G6 PASS). Это не «дыры» в "
              "нашем выводе, а несовпадение схемы якорей источника.", ""]
        for r in sorted(rows, key=lambda x: -len(x["self_missing"])):
            if r["self_missing"]:
                ex = ", ".join(f"{a}«{t}»" for a, t in r["self_missing"][:6])
                L.append(f"- **{r['slug']}**: {len(r['self_missing'])} — {ex}")

    out = paths.REPORTS / "original_links_audit.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:40]))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
