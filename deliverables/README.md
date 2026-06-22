# deliverables/ — сдаточные пакеты

Только АКТУАЛЬНЫЕ пакеты для людей. Содержимое — СНАПШОТЫ на момент сдачи
(не синхронизируются с `final/` автоматически). История раундов — в `archive/`
(вне git).

**Текущие пакеты для Анары** (папка + zip; zip gitignored, на диске):
- `anara_batch9/` — 9 новых кодексов: `codes/` (_structured) + `chunks/`
  (chunks.jsonl + index_meta + config) + `reports/` + README. Архив
  `ADILETkz_batch9_anara.zip`.
- `anara_const_laws/` — 9 конституционных законов, та же структура. Архив
  `ADILETkz_const_laws_anara.zip`.

**Прочее:**
- `structured_out_package.zip` — корпус jsonl по схеме шефа (gitignored `*.zip`).
- `vector_layer/` — ранний снапшот вектор-отчётов (только .md; актуальные отчёты —
  в `reports/`, данные — в пакетах выше).

`chunks.jsonl` в пакетах = байт-в-байт `derived/vector_layer/chunks.jsonl`
(git дедуплицирует по содержимому). Новый пакет = новая папка + README с цифрами.
