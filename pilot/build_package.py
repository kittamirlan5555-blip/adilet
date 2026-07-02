# -*- coding: utf-8 -*-
"""Сборка пакета Анары deliverables/anara_pilot100/ (по образцу anara_batch9).

Структура:
  anara_pilot100/
    README.md                — обзор + цифры
    codes/                   — *_ready.html действующих законов (линкованная форма)
    reports/
      index.md               — НГР|название|статей|#z|ext|gaps|cov|статус (UNDER_CHUNK помечен)
      repealed_list.md        — 18 отменённых (НГР|название|чем отменён — из шапки)
      PILOT_SUMMARY.md         — копия сводки для шефа/Анары
"""
import csv
import io
import json
import re
import shutil
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "final"
PKG = ROOT / "deliverables" / "anara_pilot100"
CODES = json.loads((ROOT / "maps" / "codes.json").read_text(encoding="utf-8"))


def clean_title(t):
    return re.sub(r"\s*-\s*ИПС.*$", "", t or "").strip()


# ── пере-собираем структуру пакета с нуля ──
if PKG.exists():
    shutil.rmtree(PKG)
(PKG / "codes").mkdir(parents=True)
(PKG / "reports").mkdir(parents=True)

# активные (из pilot_audit) + статус (из pilot_report)
active = [r["slug"] for r in csv.DictReader((ROOT / "pilot" / "pilot_audit.csv").open(encoding="utf-8"))]
status = {r["slug"]: r for r in csv.DictReader((ROOT / "reports" / "pilot" / "pilot_report.csv").open(encoding="utf-8"))}

# 1. codes/ — *_ready.html
copied = 0
for s in active:
    src = FINAL / f"{s}_ready.html"
    if src.exists():
        shutil.copy2(src, PKG / "codes" / f"{s}_ready.html")
        copied += 1

# 2. reports/index.md — из pilot_index.md (уже посчитан build_index.py)
idx_src = (ROOT / "reports" / "pilot" / "pilot_index.md").read_text(encoding="utf-8")
(PKG / "reports" / "index.md").write_text(idx_src, encoding="utf-8")

# 3. repealed_list.md — 18 отменённых, «чем отменён» из шапки source
manifest = list(csv.DictReader((ROOT / "pilot" / "ingest_manifest.csv").open(encoding="utf-8")))
repealed = [r["ngr"] for r in manifest if r["verdict"] == "REPEALED"]
# «утратил силу <ЧЕМ>» — захват акта+даты минимально ДО номера «№/N NNN[-RR]»
# (даты ДД.ММ.ГГГГ с точками — не режем по точке; стоп сразу после номера акта)
RE_REP = re.compile(r"[Уу]тратил\w*\s+силу\s*[-—]?\s*(.{5,75}?(?:№|N)\s*\d[\dIVXLХІ-]*)")
rows = []
for ngr in repealed:
    p = ROOT / "source" / f"{ngr}.html"
    title = clean_title(CODES.get(ngr, {}).get("title", ""))
    bywhom = ""
    if p.exists():
        soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
        art = soup.find("article") or soup
        txt = art.get_text(" ", strip=True)
        # title из <title> если не в codes.json (repealed не регистрируются)
        if not title and soup.title and soup.title.string:
            title = clean_title(soup.title.string)
        m = RE_REP.search(txt[:1500])
        if m:
            bywhom = re.sub(r"\s+", " ", m.group(1)).strip().rstrip("(,; ")
    rows.append((ngr, title, bywhom))

L = ["# Отменённые законы — НЕ обрабатывались (утратили силу)", "",
     f"Найдено детектором статуса при ингесте: **{len(rows)}**. В корпус НЕ включены "
     "(мёртвые редакции, заменены новыми актами). «Чем отменён» — из шапки документа.",
     "", "| НГР | название | утратил силу — чем |", "|---|---|---|"]
for ngr, title, byw in rows:
    L.append(f"| {ngr} | {title} | {byw} |")
(PKG / "reports" / "repealed_list.md").write_text("\n".join(L) + "\n", encoding="utf-8")

# 4. PILOT_SUMMARY.md копией
shutil.copy2(ROOT / "reports" / "pilot" / "PILOT_SUMMARY.md", PKG / "reports" / "PILOT_SUMMARY.md")

# 5. README.md
done = sum(1 for s in active if status.get(s, {}).get("status") == "DONE")
uc = [s for s in active if status.get(s, {}).get("status") == "UNDER_CHUNK"]
readme = f"""# ADILETkz — пилотный пакет (100 случайных законов), для Анары

Самодостаточный пакет по пилоту: **{len(active)} действующих материальных законов РК**,
прогнанных через структуру + ссылки (внутренние #z, внешние → корень, полный спан).
Проверено независимо из сырого HTML (не только гейтами). Форма — `_ready` (линкованная).

## Цифры (из реальных отчётов)

- **Действующих законов в пакете: {len(active)}** — {done} чисто (DONE), {len(uc)} UNDER_CHUNK.
- **Отменённых отсеяно: {len(rows)}** (утратили силу — см. `reports/repealed_list.md`).
- Внутренние ссылки «статья N настоящего Закона» → `#z` (канон 68); внешние акты → корень;
  полный спан (71/73); ссылки в сносках сняты (18) — правило Анары.
- Покрытие внешних ссылок частичное (npa_mapping = 287 записей) — ожидаемо.

## Структура

```
anara_pilot100/
├── README.md                — этот файл
├── codes/                   — {copied} документов *_ready.html (действующие, линкованные)
└── reports/
    ├── index.md             — таблица: НГР | название | статей | #z | ext | gaps | cov | статус
    ├── repealed_list.md      — {len(rows)} отменённых (НГР | название | чем отменён)
    └── PILOT_SUMMARY.md       — сводка для шефа/Анары (без техжаргона)
```

## Как читать

- `codes/*_ready.html` — открывать в **браузере** (не в Word: там ссылки визуально не видны).
- `reports/index.md` — что где: сколько статей, внутренних `#z`, внешних `ext`, дыр `gaps`, cov.
  **{uc[0] if uc else '—'}** помечен `UNDER_CHUNK` (2 статьи «исключена», мелочь — статьи в чанках 162 vs 164).
- Хром страницы adilet (меню/реклама, ~44 ссылки) остаётся как есть — так же, как в прошлых
  пакетах корпуса (batch9): это стандартное оформление страницы adilet, не правовой текст.

> Канон в репозитории: `final/*_ready.html`. Пакет — снимок для приёмки.
"""
(PKG / "README.md").write_text(readme, encoding="utf-8")

print(f"codes/: {copied} файлов | repealed_list: {len(rows)} | UNDER_CHUNK: {uc}")
print(f"пакет: {PKG.relative_to(ROOT)}")
