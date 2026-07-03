# -*- coding: utf-8 -*-
"""Предсдаточная проверка + индекс пакета для Анары (пилот-сотня, действующие).

На КАЖДОМ действующем доке (pilot_audit.csv):
  • gaps = 76_mapping_gap_report.scan, НО по _ready (у пилота ссылки там, не в
    _structured) — через временную копию, реальные файлы не трогаются;
  • ссылки в ТЕЛЕ (div.article): внутренние #z + внешние adilet/docs (корень);
  • text-invariance _ready vs _structured, nested <a>, висячие #z.
Пишет reports/pilot/pilot_index.md (индекс) и печатает НЕчистые.
"""
import csv
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path


def clean_title(t: str) -> str:
    """Срезаем хвост «- ИПС "Әділет"» (и вариации) из заголовка adilet."""
    return re.sub(r"\s*-\s*ИПС.*$", "", t or "").strip()

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "final"
sys.path.insert(0, str(ROOT / "scripts" / "audit"))
import auditlib as al  # noqa

# импорт 76 (имя с цифры — через importlib)
spec = importlib.util.spec_from_file_location("gap76", ROOT / "scripts" / "pipeline" / "76_mapping_gap_report.py")
gap76 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gap76)
MKEYS = list(json.loads((al.CONFIG / "npa_mapping.json").read_text(encoding="utf-8")).keys())

audit = {r["slug"]: r for r in csv.DictReader((ROOT / "pilot" / "pilot_audit.csv").open(encoding="utf-8"))}
status = {r["slug"]: r["status"] for r in csv.DictReader((ROOT / "reports" / "pilot" / "pilot_report.csv").open(encoding="utf-8"))}
codes = json.loads((ROOT / "maps" / "codes.json").read_text(encoding="utf-8"))
active = list(audit.keys())

# temp final where _ready живёт под именем _structured (чтобы 76 сканировал ЛИНКОВАННУЮ форму)
tmp = Path(tempfile.mkdtemp())
for s in active:
    shutil.copy(FINAL / f"{s}_ready.html", tmp / f"{s}_structured.html")
al.FINAL = tmp   # 76.scan берёт al.FINAL в момент вызова


def norm(path):
    soup = BeautifulSoup(Path(path).read_text(encoding="utf-8", errors="replace"), "html.parser")
    for t in soup.find_all(["script", "style", "template"]):
        t.decompose()
    return "".join(soup.get_text().split())


rows = []
for s in active:
    soup = BeautifulSoup((FINAL / f"{s}_ready.html").read_text(encoding="utf-8", errors="replace"), "html.parser")
    # _ready строится из СЫРОГО source (pipeline.py), а не из _structured — в нём
    # НЕТ div.article. Различаем правовые ссылки по href: внутренние #z, внешние —
    # ПОЛНЫЙ https://adilet.zan.kz/rus/docs/... (их ставит 03_find_external_npa);
    # относительные /rus/... , javascript:, #header — это chrome страницы adilet.
    body_int = body_ext = 0
    for a in soup.find_all("a", href=True):
        h = a["href"].strip()
        if h.startswith("#z"):
            body_int += 1
        elif h.startswith(("https://adilet.zan.kz/rus/docs/", "http://adilet.zan.kz/rus/docs/")):
            body_ext += 1
    _, gaps, in_notes = gap76.scan(s, MKEYS)
    ng = len(gaps)
    cov = round(100 * body_ext / (body_ext + ng)) if (body_ext + ng) else 100
    # чистота ссылок
    nested = sum(1 for a in soup.find_all("a") if a.find_parent("a"))
    ids = {t.get("id") for t in soup.find_all(attrs={"id": True})} | {t.get("name") for t in soup.find_all(attrs={"name": True})}
    dangling = sum(1 for a in soup.find_all("a", href=True)
                   if a["href"].strip().startswith("#") and len(a["href"].strip()) > 1 and a["href"].strip()[1:] not in ids)
    ti = "OK" if norm(FINAL / f"{s}_ready.html") == norm(FINAL / f"{s}_structured.html") else "DIFF"
    rows.append({
        "slug": s, "title": clean_title(codes.get(s, {}).get("title", ""))[:60],
        "arts": audit[s]["struct_arts"], "int": body_int, "ext": body_ext,
        "gaps": ng, "cov": cov, "status": status.get(s, "?"),
        "nested": nested, "dangling": dangling, "ti": ti,
    })

shutil.rmtree(tmp, ignore_errors=True)

# индекс
md = ["# Пилот-100 — индекс сдаваемых законов (действующие материальные)", "",
      f"Всего действующих: **{len(rows)}**. Отменённые (18) — в repealed_list.md.",
      "",
      "Колонки: статей — статей в структуре; #z — внутренних ссылок в теле; "
      "ext — внешних ссылок на акты (корень adilet); gaps — неслинкованных внешних "
      "фраз (нет в npa_mapping, 287 записей — покрытие внешних заведомо частичное); "
      "cov — ext/(ext+gaps).", "",
      "| НГР | название | статей | #z | ext | gaps | cov | статус |",
      "|---|---|--:|--:|--:|--:|--:|---|"]
for r in sorted(rows, key=lambda x: x["slug"]):
    md.append(f"| {r['slug']} | {r['title']} | {r['arts']} | {r['int']} | {r['ext']} | "
              f"{r['gaps']} | {r['cov']}% | {r['status']} |")
(ROOT / "reports" / "pilot" / "pilot_index.md").write_text("\n".join(md) + "\n", encoding="utf-8")

# НЕчистые (link-integrity, не coverage)
dirty = [r for r in rows if r["nested"] or r["dangling"] or r["ti"] != "OK" or r["status"] != "DONE"]
print(f"действующих доков: {len(rows)}")
print(f"link-integrity НЕчистых (nested/dangling/text-DIFF/не-DONE): {len(dirty)}")
for r in dirty:
    print(f"  {r['slug']}: nested={r['nested']} dangling={r['dangling']} ti={r['ti']} status={r['status']}")
import statistics
print(f"cov (внешние) медиана: {statistics.median(r['cov'] for r in rows)}% | "
      f"gaps медиана: {int(statistics.median(r['gaps'] for r in rows))}")
print(f"#z внутр всего: {sum(r['int'] for r in rows)} | ext всего: {sum(r['ext'] for r in rows)}")
print("-> reports/pilot/pilot_index.md")
