# -*- coding: utf-8 -*-
"""Сборка ПАКЕТА v2 для Анары -> deliverables/anara_pilot100_v2/.

Отдельный пакет (сданный v1 `anara_pilot100/` НЕ трогаем — снимок). Структура v1 +
свежий индекс (маппинг 414) + anara_response.md (ответ на замечания с агрегатами).
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
PKG = ROOT / "deliverables" / "anara_pilot100_v2"
CODES = json.loads((ROOT / "maps" / "codes.json").read_text(encoding="utf-8"))


def clean_title(t):
    return re.sub(r"\s*-\s*ИПС.*$", "", t or "").strip()


if PKG.exists():
    shutil.rmtree(PKG)
(PKG / "codes").mkdir(parents=True)
(PKG / "reports").mkdir(parents=True)

active = [r["slug"] for r in csv.DictReader((ROOT / "pilot" / "pilot_audit.csv").open(encoding="utf-8"))]
status = {r["slug"]: r for r in csv.DictReader((ROOT / "reports" / "pilot" / "pilot_report.csv").open(encoding="utf-8"))}

# 1. codes/ — свежие _ready (merge-fix + новый маппинг)
copied = 0
for s in active:
    src = FINAL / f"{s}_ready.html"
    if src.exists():
        shutil.copy2(src, PKG / "codes" / f"{s}_ready.html")
        copied += 1

# 2. reports/ — свежий индекс + ответ Анаре + repealed + summary (если есть)
shutil.copy2(ROOT / "reports" / "pilot" / "pilot_index.md", PKG / "reports" / "index.md")
shutil.copy2(ROOT / "reports" / "anara_response.md", PKG / "reports" / "anara_response.md")
shutil.copy2(ROOT / "reports" / "pilot" / "rerun_audit.md", PKG / "reports" / "rerun_audit.md")
shutil.copy2(ROOT / "maps" / "anara_pilot_flags.json", PKG / "reports" / "anara_pilot_flags.json")
for opt in ("repealed_list.md", "PILOT_SUMMARY.md"):
    srcp = ROOT / "deliverables" / "anara_pilot100" / "reports" / opt
    if srcp.exists():
        shutil.copy2(srcp, PKG / "reports" / opt)

done = sum(1 for s in active if status.get(s, {}).get("status") == "DONE")
green = sum(1 for s in active if status.get(s, {}).get("gate") == "GREEN")

readme = f"""# ADILETkz — пилотный пакет v2 (закрытие замечаний Анары)

Обновлённая сдача по пилоту: **{copied} действующих законов РК**. Отличия от v1:
исправлены **склейки** «пункта 1статьи 5» (39 → 0 по корпусу) и **добавлено 80
проверенных внешних актов** в маппинг (334 → 414 ключей) — закрыт названный Анарой
класс жёлтых флагов (внешние акты по имени). Форма — `_ready` (линкованная).

## Цифры (из реальных отчётов, независимый аудит §6)

- Действующих законов: **{copied}** — {done} DONE, гейт GREEN **{green}/{copied}**.
- Склейки «цифра+статьи»: **39 → 0**.
- Внешних ссылок на корень акта: **3396 → 3633 (+237)**; ключей маппинга **334 → 414**.
- text-invariance (без пробелов) vs сданный v1: **0/82 нарушений** (текст не изменён).
- Все **10 названных Анарой актов** — залинкованы (см. `reports/anara_response.md`, §3).

## Структура

```
anara_pilot100_v2/
├── README.md                — этот файл
├── codes/                   — {copied} документов *_ready.html (действующие, линкованные)
└── reports/
    ├── anara_response.md     — ОТВЕТ на замечания (агрегаты до/после, 10 актов, методика)
    ├── index.md             — таблица: НГР | название | статей | #z | ext | gaps | cov | статус
    ├── rerun_audit.md        — независимый аудит §6 (text-invariance, склейки, якоря)
    ├── repealed_list.md      — отменённые (не включены)
    └── PILOT_SUMMARY.md       — сводка для шефа/Анары
```

## Как читать

- `codes/*_ready.html` — открывать в **браузере** (в Word гиперссылки визуально не видны —
  отсюда часть жёлтых у Анары была ложной: место уже залинковано).
- `reports/anara_response.md` — главный документ ответа: что было / что стало / что осталось
  на ручной проход (с правом вето ревьюера).

> Канон в репозитории: `final/*_ready.html`. Сданный v1 `anara_pilot100/` не изменялся.
> Пофлаговая (statья/цитата) таблица достраивается по получении `.docx` с жёлтыми выделениями.
"""
(PKG / "README.md").write_text(readme, encoding="utf-8")

print(f"codes/: {copied} | reports: {sorted(p.name for p in (PKG/'reports').iterdir())}")
print(f"пакет: {PKG.relative_to(ROOT)}")
