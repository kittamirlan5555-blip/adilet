# -*- coding: utf-8 -*-
"""ЭТАП 0 PRE-FLIGHT: валидация новых выгрузок source/ ПЕРЕД пайплайном. READ-ONLY.

python scripts/audit/preflight_new.py <slug> [<slug> ...]
-> таблица: слаг | статей (article_map) | <a name=z> | h3#z | <b>Статья | doc_id | OK/КРИВО

Эталон сигнатур — заведомо рабочий arbitrazh (печатается первой строкой).
doc_id берётся из СУФФИКСНЫХ self-ссылок /docs/{NGR}/(history|info|links|compare)
— это панель документа adilet, всегда указывает на ТЕКУЩИЙ акт. Частотность голых
/docs/ НЕНАДЁЖНА: внешние акты цитируются чаще собственного (в arbitrazh внешний
Z1900000217 встречается 27 раз против своего Z1600000488 — 23).

КРИВО, если: статей=0 ИЛИ нет ни одной article-сигнатуры ИЛИ article_map сильно
расходится с числом <b>Статья (битая структура/недосейв/чужой формат).
"""
import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

# импорт build_article_map из файла, начинающегося с цифры
_spec = importlib.util.spec_from_file_location(
    "amap01", paths.ROOT / "scripts" / "pipeline" / "01_build_article_map.py")
_amap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_amap)

SELF_SUFFIX = re.compile(r"/docs/([KZ][0-9A-Za-z_]+)/(?:history|info|links|compare|print|word|pdf)")
MANUAL_NGR = {"cifrovoy": "K2600000255"}   # Цифровой кодекс 2026 — задан владельцем
RE_ZNAME = re.compile(r"^z\d+")
RE_ART_B = re.compile(r"^Статья\s+\d+(?:-\d+)?\s*\.")


def doc_id_of(html: str):
    c = Counter(SELF_SUFFIX.findall(html))
    return c.most_common(1)[0][0] if c else None


def analyze(slug: str):
    p = paths.SOURCE / f"{slug}.html"
    if not p.exists():
        return {"slug": slug, "err": "нет файла"}
    html = p.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(["script", "style", "template"]):
        t.decompose()
    a_name = sum(1 for a in soup.find_all("a", attrs={"name": True})
                 if RE_ZNAME.match(a.get("name", "")))
    h3_id = sum(1 for h in soup.find_all("h3", id=True)
                if RE_ZNAME.match(h.get("id", "")))
    b_art = sum(1 for b in soup.find_all("b")
                if RE_ART_B.match(b.get_text(" ", strip=True)))
    arts = _amap.build_article_map(str(p))
    n = len(arts)
    nums = sorted(int(k.split("-")[0]) for k in arts) if arts else []
    rng = f"{nums[0]}..{nums[-1]}" if nums else "—"
    did = MANUAL_NGR.get(slug) or doc_id_of(html)
    # критерий КРИВО
    sig_any = (a_name + h3_id + b_art) > 0
    # article_map должен покрывать >=70% видимых <b>Статья-заголовков (если они есть)
    head_ref = max(b_art, h3_id)
    cover_ok = (head_ref == 0) or (n >= 0.7 * head_ref)
    krivo = (n == 0) or (not sig_any) or (not cover_ok)
    return {"slug": slug, "n": n, "rng": rng, "a_name": a_name, "h3_id": h3_id,
            "b_art": b_art, "doc_id": did or "—", "manual": slug in MANUAL_NGR,
            "ok": not krivo,
            "why": "" if not krivo else
            ("статей=0" if n == 0 else "нет article-сигнатур" if not sig_any
             else f"map {n} << <b>Статья {b_art}")}


def main():
    slugs = sys.argv[1:]
    if not slugs:
        sys.exit("укажи слаги: preflight_new.py lesnoy vodniy ...")
    print(f"{'слаг':<16}{'статей':>7}{'диапазон':>11}{'a_name':>8}{'h3#z':>6}"
          f"{'b.Ст':>6}  {'doc_id':<14}{'структура'}")
    print("-" * 86)
    # эталон
    ref = analyze("arbitrazh")
    print(f"{'arbitrazh(ref)':<16}{ref['n']:>7}{ref['rng']:>11}{ref['a_name']:>8}"
          f"{ref['h3_id']:>6}{ref['b_art']:>6}  {ref['doc_id']:<14}эталон")
    print("-" * 86)
    rows = [analyze(s) for s in slugs]
    for r in rows:
        if r.get("err"):
            print(f"{r['slug']:<16}  !! {r['err']}")
            continue
        tag = "OK" if r["ok"] else f"КРИВО ({r['why']})"
        man = "*" if r["manual"] else " "
        print(f"{r['slug']:<16}{r['n']:>7}{r['rng']:>11}{r['a_name']:>8}"
              f"{r['h3_id']:>6}{r['b_art']:>6}  {r['doc_id']:<13}{man}{tag}")
    ok = [r['slug'] for r in rows if not r.get('err') and r['ok']]
    bad = [r['slug'] for r in rows if r.get('err') or not r['ok']]
    print("-" * 86)
    print(f"ЧИСТЫЕ ({len(ok)}): {' '.join(ok)}")
    print(f"КРИВЫЕ ({len(bad)}): {' '.join(bad) or '—'}")
    print("* doc_id задан владельцем вручную")


if __name__ == "__main__":
    main()
