# MOVES — реструктуризация дерева проекта (2026-06-10, Фаза A)

Один коммит `git mv` (история файлов сохранена). Пути в канонических скриптах
переведены на `scripts/paths.py` отдельным коммитом следом.

## Данные

| старый путь | новый путь | что это |
|---|---|---|
| `data/source/` | `source/` | сырые HTML с adilet, read-only |
| `data/final/` | `final/` | рабочие финальные формы `_ready` / `_structured` |
| `data/maps/` | `maps/` | карты «статья → якорь», subpoint-карты |
| `config/codes.json` | `maps/codes.json` | реестр кодексов (doc_id) |
| `config/npa_mapping.json` | `maps/npa_mapping.json` | название акта → НГР |
| `config/manual_overrides.json` | `maps/manual_overrides.json` | точечные оверрайды |
| `data/reports/` | `reports/` | аудиты, SDACHA, флаги Анары, gap-отчёты |
| `data/chunks/` | `chunks/` | JSONL-чанки (производное чанкера) |
| `data/tree/` | `tree/` | JSON-деревья (производное чанкера) |
| `data/anara_package/` | `deliverables/anara_package/` | старый сдаточный пакет Анаре |
| `data/send_chef/` | `deliverables/send_chef/` | пакет шефу (чанки) |
| `data/README.md` | `docs/DATA_LAYOUT_legacy.md` | описание СТАРОЙ раскладки (легаси) |

НЕ перенесено (untracked, на диске в `data/`): `data/final_backup_*/`,
`data/final_pre_links/`, `data/final_pre_fix11_*`, `data/source/*_files/` —
локальные бэкапы/мусор браузера, в репо не идут (.gitignore), убрать с диска
можно после приёмки.

## Скрипты

`scripts/pipeline/` — канонические шаги построения (единая точка входа
`pipeline.py`, бывш. `run_pipeline.py`):
01, 02, 03, 06, 07, 08, 10, 11, 13, 16, 17, 18, 28, 29, 30, 31, 43,
68_link_canon, 71_fullspan_wrap, 72_external_root_link, 73_fullspan_chains,
76_mapping_gap_report, chunk_npa, run_structure_all.

`scripts/audit/` — верификация и аудит (дополнены из scripts/):
64_final_verify, 67_independent_verify, 69_sixcheck_laws,
70_anara_flags_driver, 71_gates, 74_code_freshness_check, 75_crosscode_verify
(+ уже жившие там a01–a05, f01–f04, r2_01–r2_05, auditlib).

Коллизии номеров 70/71 решены разнесением по папкам:
70/71 в `pipeline/` — шаги построения, 70/71 в `audit/` — гейты раундов;
`70_zhilishniy_deadlinks.py` уходит в attic Фазой B.

Остальные скрипты остаются в `scripts/` до Фазы B (attic). Attic-скрипты на
новые пути НЕ переводятся (намеренно — они исторические).

## Пути в коде

Единственная точка истины — [`scripts/paths.py`](scripts/paths.py):
`ROOT, SOURCE, FINAL, MAPS, REPORTS, DELIVERABLES, AUDIT_OUT, CODES_JSON,
NPA_MAPPING, MANUAL_OVERRIDES`. Канонические скрипты и `auditlib` импортируют
его; `auditlib.CONFIG` теперь указывает на `maps/` (config слит в maps).
