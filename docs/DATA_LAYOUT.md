# DATA_LAYOUT — раскладка данных на масштабе (400+ актов)

## Проблема
На пилоте-100 git уже держит **~477 МБ** рабочего дерева (история `.git` ~316 МБ),
из них 98 % — тяжёлые артефакты:

| каталог | тракт в git | назначение |
|---|--:|---|
| `deliverables/` | 211 МБ | пакеты для Анары/Ергали (снимки) |
| `derived/` | 120 МБ | перегенерируемое: chunks/tree/structured_out/vector_layer |
| `final/` | 91 МБ | `*_ready.html` / `*_structured.html` (продукт, регенерируется из `source/`) |
| `source/` | 48 МБ | сырьё adilet (ВХОД, скачивается) |

На 400+ актов это **гигабайты** — git (и особенно `push`) не потянет.

## Решение: код в git, данные — на диске + манифест

**В git (лёгкое, версионируем):**
`scripts/`, `pilot/` (код), `maps/` (карты: `codes.json`, `npa_mapping.json`,
`article_map_*`, `subpoint_map_*`, `corpus_registry.json`), `reports/` (отчёты, доски),
`docs/`, `CLAUDE.md`, `README.md`, `manifests/`.

**Вне git (тяжёлое, на диске):** `source/ final/ derived/ deliverables/`.
Их **целостность** фиксирует `manifests/data_manifest.json` — `path + size + sha256 + mtime`
по каждому файлу (генератор `scripts/data_manifest.py`). Манифест мал (~0.3 МБ на 1449
файлов) и коммитится.

## Как проверить свой набор данных
```
python scripts/data_manifest.py --verify
```
→ сверяет диск с манифестом: `ok / ОТСУТСТВУЕТ / ИЗМЕНЁН / новых-вне-манифеста`,
вердикт `ЦЕЛОСТНО`/`РАСХОЖДЕНИЯ`. Расхождение = у тебя не тот набор (или устаревший
манифест — регенерируй после нового прогона).

## Как восстановить данные
1. **`source/`** — регенерируется закачкой с adilet: `pilot/01_ingest_adilet.py`
   (НГР из `maps/corpus_registry.json`; TLS-бандл `pilot/certs/adilet_chain.pem`).
2. **`final/`** — регенерируется из `source/` пайплайном:
   `pilot/02_batch_run.py <slugs>` (structure→links→canon→gate→chunk).
3. **`derived/`** — из `final/`: `chunk_npa.py`, `scripts/vector/*` (Фаза B, отдельно).
4. **`deliverables/`** — из `final/`: `pilot/build_package*.py`.
5. Либо получить готовый архив тяжёлых каталогов у владельца и проверить манифестом.

После каждого прогона, меняющего данные, — **обновить манифест**:
`python scripts/data_manifest.py` и закоммитить `manifests/data_manifest.json`.

## Миграция существующего git (ТРЕБУЕТ СЛОВА ВЛАДЕЛЬЦА — НЕ выполнено)
Тяжёлые каталоги уже в истории. Чтобы вывести их из индекса (файлы на диске
ОСТАЮТСЯ, это не удаление данных):
```
# 1. манифест уже собран и закоммичен (целостность зафиксирована)
python scripts/data_manifest.py            # обновить при необходимости
# 2. вывести из индекса (диск не трогает):
git rm -r --cached source final derived deliverables
git commit -m "data: move heavy artifacts out of git (manifest-tracked)"
```
> `.gitignore` уже исключает эти каталоги для БУДУЩИХ файлов (прогон 400 не забьёт git).
> История `.git` от прошлых коммитов не уменьшится без `filter-repo`/`gc` — это
> ОТДЕЛЬНЫЙ разрушительный шаг, тоже по слову владельца.

**Что НЕ сделано без подтверждения:** сам `git rm --cached` и чистка истории. Сначала
план + манифест (этот файл + `manifests/data_manifest.json`) — по правилу «не удаляй
ничего без моего слова».
