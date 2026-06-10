# scripts/ — реестр скриптов гиперссылок

Скрипты сгруппированы по роли в конвейере. **Порядок запуска** = разделы 1 → 2 →
3, далее верификация (4) по необходимости. `[RO]` = read-only (ничего не пишет в
`data/final`). Номер в имени файла ≈ исторический порядок появления, НЕ порядок
запуска — канонический порядок задаёт `run_pipeline.py`.

> Канон по ссылкам — `*_structured.html`. Фаза-B-правки (раздел 2) применялись
> на нём; `_ready` затем подтягивается (29/30), чанки пересобираются из
> `_structured`. Не перезапускать раздел 1 на исправленных кодексах.

---

## 0. Оркестрация и преобразование форм

| Скрипт | Роль | Вход → выход |
|---|---|---|
| `run_pipeline.py` | мастер-раннер Фазы A (вызывает 01→07→10→02→03→06→13) | `source/{c}.html` → `final/{c}_ready.html` |
| `11_structure_html.py` | структуризатор: добавляет иерархию `div[data-type]` (ЧАСТЬ→…→СТАТЬЯ), не трогая текст/ссылки | `_ready.html` → `_structured.html` |
| `run_structure_all.py` | прогон `11_` по всем 13 кодексам + статистика | все `_ready` → все `_structured` |
| `chunk_npa.py` | чанкер: state-machine по тексту `_structured` | `_structured.html` → `tree/{c}.json` + `chunks/{c}.jsonl` |

---

## 1. Фаза A — построение ссылок (порядок внутри `run_pipeline.py`)

| # | Скрипт | Роль | ТЗ |
|---|---|---|---|
| 1 | `01_build_article_map.py` | статья N → id якоря `zK` (карта в `maps/`) | основа линковки |
| 2 | `07_add_subpoint_anchors.py` | якоря пунктов/подпунктов | основа линковки |
| 3 | `10_cross_code_refs.py` | «ст. N **Налогового кодекса РК**» → одна внешняя ссылка (раньше 02, чтобы забрать специфичный текст) | cross-code |
| 4 | `02_fix_internal_links.py` | «ст. N **настоящего Кодекса**» → внутренняя `#zK` | внутр. покрытие |
| 5 | `03_find_external_npa.py` | голые названия НПА (Закон/Кодекс/Конституция) → внешняя ссылка по `npa_mapping.json` | ТЗ 5.2.3 (внешние) |
| 6 | `06_finalize.py` | CSS/JS подсветка `:target` | оформление |
| 7 | `13_cleanup_html.py` | нормализация/чистка вложенных и осиротевших `<a>` | гигиена HTML |
| 8 | `76_mapping_gap_report.py` `[RO]` | gap-отчёт маппинга: plain/разорванные правовые фразы вне `<a>` + дыры `npa_mapping.json` → `reports/mapping_gap_{slug}.md`. **ОБЯЗАТЕЛЕН перед сдачей**: остаток пуст или объяснён в сдаточной записке | контроль сдачи |
| — | `04_validate.py` `[RO]` | валидация: дубли якорей, битые `#z`, статьи без ссылок, прирост vs исходник | контроль |

---

## 2. Фаза B — корректность ссылок (правки на `_structured`)

Точечные фиксы (каждый делает бэкап в свой `final_backup_*`, ныне в
`archive/data_backups/`). Применялись по ходу ревью; для повторного аудита
обычно не нужны.

| Скрипт | Роль | ТЗ / повод |
|---|---|---|
| `08_fix_selfref_subpoints.py` | self-ссылки на подпункты/пункты «настоящей статьи» | корректность self |
| `09_fix_uk_specific.py` | целевые правки Уголовного кодекса | ТЗ-01 / УК |
| `14_sweep_remaining_internal_articles.py` | дочистка незалинкованных «статья N» | внутр. покрытие |
| `15_fix_broken_anchors.py` | починка ссылок на несуществующие `#z` | BROKEN→0 |
| `16_apply_targeted_overrides.py` | ручные оверрайды из `config/manual_overrides.json` | точечно |
| `17_normalize_link_targets.py` | нормализация таргетов | гигиена |
| `18_strip_links_in_notes.py` | снять `<a>` внутри сносок/примечаний (ИЗПИ) | **ТЗ-02** |
| `19_fix_bare_article_headings.py` | починка «сбитого» заголовка статьи | **ТЗ-03** |
| `20_fix_EKO_003.py` | Экологический — EKO-003 | Фаза-2 |
| `21_fix_APPK_001.py` | АППК — APPK-001 | Фаза-2 |
| `22_fix_KOAP.py` | КоАП — 8 MISSING + 4 WRONG | Фаза-2 |
| `23_fix_SOC.py` | Социальный — точечные | Фаза-2 |
| `24_phase2_trudovoy.py` | Трудовой — Фаза-2 | Фаза-2 |
| `25_phase2_predprinimatel_fix.py` | Предпринимательский — Фаза-2 | Фаза-2 |
| `26_fix_koap_docx6.py` | КоАП — правки из ревью-файла «КоАП (6).docx» | ревью |
| `28_fix_link_correctness.py` | общий точечный фикс корректности таргетов (Вариант 1) | **ТЗ-01** |
| `31_add_lost_links_structured.py` | вернуть в `_structured` валидные ссылки, потерянные структуризатором | внутр. покрытие |
| `42_gkosob_canon_ready.py` | ГК-Особенная: линк-канон 222 self-URL `#zN`, генерация `_ready` (13/13) | блокер ГК-Особ |
| `43_dobivka_stage1_d.py` | добивка ЭТАП-1: обёртка хвостов перечней «статьями N1, **N2, N3**…» без изменения текста | добивка (d) |

---

## 3. Sync `_ready` ↔ `_structured`

| Скрипт | Роль |
|---|---|
| `29_diff_ready_structured.py` | `[RO]` по умолчанию: link-level дифф `_ready` vs `_structured`; `--reconcile` подтягивает `_ready` по href из `_structured` |
| `30_reconcile_ready_safe.py` | безопасный текстово-выверенный reconcile канона из `_structured` в `_ready` (бэкап `final_backup_RECONCILE`) |

> ⚠️ `29 --reconcile` слепо считает `_structured` каноном и разворачивает «лишние»
> ссылки `_ready`. Текущий остаточный дифф **двусторонний** (в `_ready` есть
> корректные ссылки, которых нет в `_structured`) — слепой reconcile их уничтожит.
> Перед reconcile сверять по `audit_OK` (см. ОТЧЁТ, раздел «Дивергенция»).

---

## 4. Аудит и верификация `[RO]`

| Скрипт | Роль |
|---|---|
| `audit_links_coverage.py` | **главный аудит**: покрытие (cov_lit/cov_cont/cov_real) + корректность (OK/WRONG/SUB/BROKEN/SELF/NONART) + атрибуция внешних |
| `32_classify_internal_links.py` | классификация всех внутр. `#z` на классы A/B/C |
| `33_verify_internal_max.py` | механическая до-верификация внутренних `#z` |
| `34_probe_wrong.py` | пробинг подозрительных WRONG: что реально резолвит якорь |
| `35_find_anchors.py` / `36_inventory_targets.py` | поиск/инвентаризация якорей и таргетов |
| `40_gap_breakdown.py` | разбор «gap» — типы незалинкованных (a/b/c/d) |
| `38_external_audit.py` | аудит ВНЕШНИХ ссылок (ТЗ 5.2.3): doc_id известен/NGR, архивные, имя↔doc_id |
| `39_external_liveness.py` | проверка «живости» внешних актов (HTTP) |
| `audit_TZ01.py`, `audit_TZ02.py`, `audit_TZ02_strict.py`, `audit_TZ03.py` | строгие аудиты по пунктам ТЗ-01/02/03 (диффят `archive/data_backups/final_backup_TZ0*` vs `final/`) |
| `audit_uk_skeleton.py` | аудит структуры УК |
| `27_verify_koap_docx6.py` | верификация правок «КоАП (6).docx» |
| `stats_ready.py` | статистика ссылок по `_ready` |
| `verify_hier.py` | верификация `hier_id` чанкера |
| `04_validate.py` | см. раздел 1 |

`debug/` и корневые `diag_*.py`, `debug_311.py`, `sweep_inventory.py`,
`build_anara_verification.py`, `build_examples_md.py` — одноразовые
диагностические/упаковочные утилиты (не часть конвейера).

---

## Быстрый прогон проверки целостности

```bash
python scripts/audit_links_coverage.py            # покрытие + корректность
PYTHONIOENCODING=utf-8 python scripts/29_diff_ready_structured.py   # дифф ready↔structured
```
