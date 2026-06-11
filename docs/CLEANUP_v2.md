# CLEANUP v2 — дерево по-человечески (раунд R5, 2026-06-11)

## Переезды (git mv, история сохранена)

| было | стало |
|---|---|
| `chunks/`, `tree/`, `structured_out/` | `derived/{chunks,tree,structured_out}/` |
| `law_kit/` | `deliverables/law_kit/` |
| `brief/` | `docs/brief/` |
| `ANARA_03_MASTER_CHECKLIST.md`, `master_anara_remarks_since_13_may.md` | `docs/anara/` |
| `MOVES.md`, `CLEANUP.md` | `docs/` |
| `tests/` | `scripts/tests/` (запуск: `python -m unittest discover -s scripts/tests -t .`) |
| `reports/<машинные гейты>` (113 шт.: 64/67/69/74/75, 71_gates_*, 68_*, 71_fullspan_*, 72/73_*, mapping_gap_*, report_*.csv, verify_summary) | `reports/gates/` |
| `reports/<россыпь прошлых раундов>` (72 шт.: 00–63b, SDACHA-серия, fixlinks-csv, AUDIT_итог и пр.) | `reports/history/` |
| `reports/out_audit/` | `reports/history/out_audit/` |

Скрипты переведены на новые пути через `scripts/paths.py`
(GATES, DERIVED, STRUCTURED_OUT); поведение не менялось.

## Удалено (контент остаётся в git-истории до этого коммита)

Мёртвые промежуточные дампы отладки прошлых раундов (29 файлов):
все `reports/_*.txt` (26 шт.: _audit_*, _diag_div, _token_counts и пр.),
`reports/audit_full.txt`, `reports/audit_full_run.txt`,
`reports/08_anchor_validation.json` (перегенерируемый дамп валидации),
`reports/03_anara_current_state_audit.json` (md-версия сохранена в history/),
`reports/TZ05_missing_anchors.json`.

История Анары (реестры, чеклисты, флаги, SDACHA) НЕ удалялась — переехала
в docs/anara/ и reports/history/.
