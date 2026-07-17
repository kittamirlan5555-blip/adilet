# -*- coding: utf-8 -*-
"""Независимый аудит ре-прогона 82 (CLAUDE.md §6) — из сырого HTML, мимо гейтов.

Сравнивает НОВЫЙ final/{slug}_ready.html с OLD-снимком в
deliverables/anara_pilot100/codes/{slug}_ready.html (сданный пакет — эталон «до»).

Проверки:
  1. text-invariance (ws-stripped): ''.join(get_text().split()) NEW == OLD.
     Ни merge-фикс (добавляет только пробел), ни новый маппинг (двигает границы <a>)
     не меняют видимый текст → должно быть равно байт-в-байт. Расхождение = ошибка.
  2. merges «\\d+стать» в get_text() без разделителя: NEW должно быть ~0 (было 39).
  3. внешние root-ссылки (docs/ без #z) и #z: считаем дельту NEW-OLD.
  4. якоря: каждый #zN резолвится в id=/name= того же файла (иначе — битый).
  5. гигиена: нет вложенных <a> (a.find('a')), нет двойного href.
Выход: reports/pilot/rerun_audit.md + краткая сводка в stdout.
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
NEWDIR = ROOT / "final"
OLDDIR = ROOT / "deliverables" / "anara_pilot100" / "codes"
OUT = ROOT / "reports" / "pilot" / "rerun_audit.md"
RE_MERGE = re.compile(r"\d+стать")
RE_ZHREF = re.compile(r"#(z\d+)")


def vis(html):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(["script", "style"]):
        t.decompose()
    return "".join(soup.get_text().split()), soup


def audit_one(slug):
    pnew = NEWDIR / f"{slug}_ready.html"
    pold = OLDDIR / f"{slug}_ready.html"
    r = {"slug": slug, "text_ok": None, "merge": 0, "ext_root": 0, "zint": 0,
         "dead_anchor": 0, "nested_a": 0, "dbl_href": 0, "note": ""}
    if not pnew.exists():
        r["note"] = "NEW нет"
        return r
    tnew, soup = vis(pnew.read_text(encoding="utf-8", errors="replace"))
    # 1 text-invariance vs OLD
    if pold.exists():
        told, _ = vis(pold.read_text(encoding="utf-8", errors="replace"))
        r["text_ok"] = (tnew == told)
        if not r["text_ok"]:
            # найдём первую точку расхождения для диагноза
            i = next((k for k in range(min(len(tnew), len(told))) if tnew[k] != told[k]),
                     min(len(tnew), len(told)))
            r["note"] = f"Δtext@{i}: OLD…{told[max(0,i-15):i+15]!r} NEW…{tnew[max(0,i-15):i+15]!r} len {len(told)}->{len(tnew)}"
    else:
        r["note"] = "OLD снимка нет"
    # 2 merges
    r["merge"] = len(RE_MERGE.findall(soup.get_text()))
    # 3 links
    ids = set()
    for tag in soup.find_all(attrs={"id": True}):
        ids.add(tag["id"])
    for tag in soup.find_all(attrs={"name": True}):
        ids.add(tag["name"])
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if "/rus/docs/" in h and "#" not in h:
            r["ext_root"] += 1
        if h.startswith("#"):
            if h.startswith("#z"):
                r["zint"] += 1
            frag = h[1:]                       # ПОЛНЫЙ фрагмент (вкл. под-пункт z80-1),
            if frag and frag not in ids:        # не обрезаем на '-' (иначе ложные dead)
                r["dead_anchor"] += 1
        if a.find("a"):
            r["nested_a"] += 1
    # 5 double href (грубо: два href= в одном теге строкой)
    r["dbl_href"] = len(re.findall(r"<a\b[^>]*\bhref=[^>]*\bhref=", str(soup)))
    return r


def main():
    slugs = [p.stem[:-6] for p in NEWDIR.glob("*_ready.html")]
    # ограничим пилотом (те, у кого есть OLD-снимок)
    pilot = sorted(s for s in slugs if (OLDDIR / f"{s}_ready.html").exists())
    print(f"аудит {len(pilot)} пилотных доков (NEW vs OLD-снимок пакета)\n")
    rows = [audit_one(s) for s in pilot]

    tbad = [r for r in rows if r["text_ok"] is False]
    merges = sum(r["merge"] for r in rows)
    dead = sum(r["dead_anchor"] for r in rows)
    nested = sum(r["nested_a"] for r in rows)
    dbl = sum(r["dbl_href"] for r in rows)
    ext = sum(r["ext_root"] for r in rows)
    zint = sum(r["zint"] for r in rows)

    print(f"1. text-invariance (ws): нарушено в {len(tbad)}/{len(rows)}")
    for r in tbad[:12]:
        print(f"     {r['slug']}: {r['note']}")
    print(f"2. merges \\d+стать (NEW):   {merges}  (baseline было 39)")
    print(f"3. внешние root doc/ (NEW): {ext} | #z внутр (NEW): {zint}")
    print(f"4. битых якорей #z:         {dead}")
    print(f"5. вложенных <a>: {nested} | двойной href: {dbl}")

    md = ["# Ре-прогон 82 — независимый аудит (§6)", "",
          f"- text-invariance нарушено: **{len(tbad)}/{len(rows)}**",
          f"- merges `\\d+стать` (NEW): **{merges}** (было 39)",
          f"- внешние root-ссылки (NEW): **{ext}** | #z внутр: **{zint}**",
          f"- битых якорей #z: **{dead}** | вложенных `<a>`: **{nested}** | двойной href: **{dbl}**", ""]
    if tbad:
        md += ["## Нарушения text-invariance", "| slug | нота |", "|---|---|"]
        md += [f"| {r['slug']} | {r['note']} |" for r in tbad]
    bad_anchor = [r for r in rows if r["dead_anchor"] or r["nested_a"] or r["dbl_href"]]
    if bad_anchor:
        md += ["", "## Гигиена (битые якоря/вложенность)",
               "| slug | dead#z | nested_a | dbl_href |", "|---|--:|--:|--:|"]
        md += [f"| {r['slug']} | {r['dead_anchor']} | {r['nested_a']} | {r['dbl_href']} |" for r in bad_anchor]
    md += ["", "## Все доки", "| slug | text_ok | merge | ext_root | #z | dead#z | nested |",
           "|---|---|--:|--:|--:|--:|--:|"]
    for r in rows:
        md.append(f"| {r['slug']} | {r['text_ok']} | {r['merge']} | {r['ext_root']} | {r['zint']} | {r['dead_anchor']} | {r['nested_a']} |")
    OUT.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\nотчёт: {OUT.relative_to(ROOT)}")
    ok = (len(tbad) == 0 and merges == 0 and dead == 0 and nested == 0 and dbl == 0)
    print("ВЕРДИКТ:", "ЧИСТО ✅" if ok else "ЕСТЬ ЧТО РАЗОБРАТЬ ⚠")


if __name__ == "__main__":
    main()
