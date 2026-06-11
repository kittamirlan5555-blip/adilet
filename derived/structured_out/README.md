# structured_out/ — выгрузка для vector DB по схеме шефа

Формат принят шефом в мае (эталон — deliverables/send_chef/
chunks_ugolovniy.jsonl): запись = чанк (пункт/часть + подпункты +
продолжения), `meta.hier_id` вида `UKCH1R1ST1P1`
(код → часть кодекса CH → раздел R → глава G → параграф PG → статья ST →
пункт P → подпункт SP), `meta.hier_path` — то же пообъектно.

Генерация и самотесты (полнота, текст==статьям, ID, иерархия, сложные
случаи): `python scripts/pipeline/structurize.py --all` → QUALITY.md.
jsonl-файлы не в гите (копии derived/chunks/), QUALITY.md — в гите.
