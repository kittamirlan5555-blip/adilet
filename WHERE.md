# ГДЕ ЧТО ЛЕЖИТ (полстраницы для человека)

| папка | что это | можно трогать? |
|---|---|---|
| `final/` | **рабочие документы** — `*_ready.html` + `*_structured.html` (24 шт.) | только скриптами с гейтами |
| `source/` | **сырьё** — выгрузки adilet | НЕТ (read-only) |
| `deliverables/` | **что отправляем Анаре** — пакеты по раундам (laws3, laws_r3, laws_r4) + SDACHA-описи | копировать наружу — да |
| `derived/structured_out/` | **jsonl для шефа** (vector DB, hier_id) + QUALITY.md | перегенерируемо (`structurize.py --all`) |
| `derived/chunks/`, `derived/tree/` | чанки и деревья (промежуточное) | перегенерируемо |
| `reports/` | отчёты: `WAITING_ON_HUMANS.md` (кто что должен решить), `gates/` (свежие гейты), раунды r3–r6, `history/` | читать |
| `scripts/` | весь код: `verify.py` (главная проверка), `pipeline/`, `audit/`, `tests/`, `hooks/`, `attic/` (заморожено) | да |
| `maps/` | `codes.json` (реестр), `npa_mapping.json` (фраза→НГР), карты якорей | через скрипты/с верификацией НГР |
| `docs/` | RUNBOOK, brief (ТЗ), история ревью | читать |
| `backups/` | автобэкапы текущих скриптов (создаются заново) | игнорить |
| `_old_tree_leftovers/` | **трупы старого дерева** (749MB) — см. LEFTOVERS.md | ИГНОРИТЬ, не работать |
| `venv/`, `.claude/` | окружение питона / настройки агента | игнорить |

Быстрые команды: `python scripts/verify.py --all` (всё зелёное = корпус ок),
`python scripts/verify.py слаг` (один документ). Правила агента — `CLAUDE.md`.
Соседняя `adilet_public_OLD_NE_TROGAT/` — замороженная старая витрина, не работать.
