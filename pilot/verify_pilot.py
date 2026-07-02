# -*- coding: utf-8 -*-
"""
НЕЗАВИСИМЫЙ АУДИТ пилота — поверх драйвера (его колонки DONE/gate — эвристики).
Читает РЕАЛЬНЫЕ артефакты с диска и реальные заголовки, выносит честный вердикт.

Для каждого пилот-слага (source/{slug}.html на диске, slug в codes.json):
  • реальный title (codes.json) -> класс формата (поправки/ратификация/договор/обычный)
  • final/{slug}_structured.html: число <div class=article data-type=…статья…>
  • final/{slug}_ready.html: есть/нет, размер
  • derived/chunks/{slug}.jsonl: число чанков, число статей, согласованность doc_id
  • честный статус:
      NO_SOURCE / NO_STRUCT(структуризатор дал 0 статей) /
      EMPTY_CHUNK(чанки=0 при наличии structured) /
      DOCID_MISMATCH(в чанках чужой doc_id) / CHUNKED_OK
Выход: pilot/pilot_audit.csv + pilot/pilot_audit.md
"""
import csv
import io
import json
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
FINAL = ROOT / "final"
CHUNKS = ROOT / "derived" / "chunks"
TREE = ROOT / "derived" / "tree"
CODES = json.loads((ROOT / "maps" / "codes.json").read_text(encoding="utf-8"))

# пилот-слаги = НГР-ключи (Z/K/U/... — у нас Z), у которых есть source на диске.
# исключаем 14 «именных» кодов (они не НГР-ключи; пилот регистрирует slug=НГР).
PILOT = [k for k, v in CODES.items()
         if not k.startswith("_") and isinstance(v, dict)
         and (SOURCE / f"{k}.html").exists()
         and k[0].isupper() and any(ch.isdigit() for ch in k)]


def fmt_class(title: str) -> str:
    t = (title or "").lower()
    if "ратифик" in t:
        return "ратификация"
    if "о внесении измен" in t or "внесении изменений" in t or "внесении изменения" in t:
        return "поправки"
    if any(k in t for k in ("договор", "соглашен", "конвенц", "протокол", "хартии", "пакт", "меморандум")):
        return "договор/межд."
    return "обычный закон"


def struct_articles(slug: str) -> int:
    p = FINAL / f"{slug}_structured.html"
    if not p.exists():
        return -1
    soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
    return sum(1 for a in soup.find_all("div", class_="article")
               if "статья" in (a.get("data-type") or ""))


def chunk_stats(slug: str):
    p = CHUNKS / f"{slug}.jsonl"
    if not p.exists():
        return {"exists": False, "n": 0, "arts": 0, "docids": set(), "max_len": 0}
    arts, docids, n, maxl = set(), set(), 0, 0
    for ln in p.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        c = json.loads(ln)
        n += 1
        m = c.get("meta", {})
        arts.add(str(m.get("article")))
        docids.add(m.get("doc_id"))
        maxl = max(maxl, m.get("char_len", 0))
    return {"exists": True, "n": n, "arts": len(arts), "docids": docids, "max_len": maxl}


def verdict(slug, sa, cs):
    if sa < 0:
        return "NO_STRUCT_FILE"
    if sa == 0:
        return "NO_STRUCT"          # структуризатор не выделил статьи
    if not cs["exists"] or cs["n"] == 0:
        return "EMPTY_CHUNK"        # есть структура, но чанков 0
    did = CODES[slug]["doc_id"]
    if cs["docids"] - {did}:
        return "DOCID_MISMATCH"     # в чанках просочился чужой doc_id
    return "CHUNKED_OK"


def main():
    rows = []
    for slug in sorted(PILOT):
        title = CODES[slug].get("title", "")
        fc = fmt_class(title)
        sa = struct_articles(slug)
        cs = chunk_stats(slug)
        ready = FINAL / f"{slug}_ready.html"
        v = verdict(slug, sa, cs)
        rows.append({
            "slug": slug, "doc_id": CODES[slug]["doc_id"], "format": fc,
            "struct_arts": sa, "chunks": cs["n"], "chunk_arts": cs["arts"],
            "ready_kb": (ready.stat().st_size // 1024) if ready.exists() else 0,
            "max_chunk_len": cs["max_len"],
            "verdict": v, "title": title[:80],
        })

    # CSV
    with (ROOT / "pilot" / "pilot_audit.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    by_v = Counter(r["verdict"] for r in rows)
    by_f = Counter(r["format"] for r in rows)
    # cross-tab format × verdict
    ct = Counter((r["format"], r["verdict"]) for r in rows)

    md = ["# Пилот — независимый аудит из реальных артефактов", "",
          f"- всего пилот-доков: **{len(rows)}**", "",
          "## По честному вердикту (из файлов)", "| вердикт | N |", "|---|--:|"]
    for v, c in by_v.most_common():
        md.append(f"| {v} | {c} |")
    md += ["", "## По формату (из реального заголовка)", "| формат | N |", "|---|--:|"]
    for fc, c in by_f.most_common():
        md.append(f"| {fc} | {c} |")
    md += ["", "## Формат × вердикт", "| формат | вердикт | N |", "|---|---|--:|"]
    for (fc, v), c in sorted(ct.items()):
        md.append(f"| {fc} | {v} | {c} |")
    md += ["", "## Все доки", "| slug | формат | стр.статей | чанков | стат.в чанках | ready KB | вердикт | заголовок |",
           "|---|---|--:|--:|--:|--:|---|---|"]
    for r in sorted(rows, key=lambda x: (x["verdict"], x["format"], x["slug"])):
        md.append(f"| {r['slug']} | {r['format']} | {r['struct_arts']} | {r['chunks']} | "
                  f"{r['chunk_arts']} | {r['ready_kb']} | {r['verdict']} | {r['title']} |")
    (ROOT / "pilot" / "pilot_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"пилот-доков: {len(rows)}")
    print("вердикты:", dict(by_v))
    print("форматы :", dict(by_f))
    print("-> pilot/pilot_audit.md + pilot/pilot_audit.csv")


if __name__ == "__main__":
    main()
