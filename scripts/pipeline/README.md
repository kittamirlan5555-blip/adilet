# scripts/pipeline/ — канонические шаги построения

Вход — `pipeline.py` (оркестрирует 01→07→10→02→03→06→13→76 для слага из
maps/codes.json; `--verify-only` = только gap-гейт, read-only). Дальше:
`11_structure_html` (плоская → структурная форма), `68_link_canon --doc-id
{НГР} [--form ready]` (канонизация ссылок, ОБЕИХ форм), `71_fullspan_wrap`,
при необходимости 72/73 (внешние корни, цепочки).

`structurize.py --all` — jsonl по схеме шефа → derived/structured_out/.
`chunk_npa.py {слаг}|--all` — чанки/деревья → derived/.

Все пути — через `scripts/paths.py`. Скрипты, пишущие в final/, обязаны
держать внутри text-invariance-гейт (§6.1). Отчёты шагов → reports/gates/.
Полный порядок и команды — в корневом README, «Типовые сценарии».
