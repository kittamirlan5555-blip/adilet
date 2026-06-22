# reports/ — отчёты и доски

Только ЖИВЫЕ доски и АКТУАЛЬНЫЕ отчёты (история раундов — в `archive/`, вне git).

**Доски:**
- `WAITING_ON_HUMANS.md` — что ждёт людей (Анару/шефа/владельца). Главная доска.
- `needs_review_table.md` — решения по NEEDS_REVIEW-ссылкам.

**Метрики / аудиты (перегенерируемые скриптами):**
- `new9_metrics.md`, `const_laws_metrics.md` — метрики батчей (batch9, конст. законы).
- `original_links_audit.md` — аудит оригинальных ссылок adilet (source → _structured).
- `consistency_43.md` — сводная консистентность по всем 43 докам.
- `numbering_audit.md` — аудит нумерации/гранулярности.

**Вектор-слой:**
- `full_chunk_report.md`, `subchunk_report.md` — чанкинг.
- `summary_eval.md`, `summary_samples.md` — достоверность summary.
- `repealed_uniformity.md` — единый подход к repealed (43 дока).
- `retrieval_eval.md` — hit@1/hit@3.

**Подпапки:**
- `audit/` — машинные отчёты аудит-скриптов.
- `gates/` — машинные отчёты `verify.py` (G1–G6, crosscode, freshness, gap, …).
  ПЕРЕГЕНЕРИРУЮТСЯ, **gitignored** (на диске, руками не править).
- `r3/` — машинный отчёт g6-апплая, **gitignored**.

Прошлые раунды (history, anara_r2, laws3, r3–r7) перенесены в `archive/`
(вне git; восстановимо из git-истории).
