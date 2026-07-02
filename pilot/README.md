# pilot/ — прогон случайных законов РК через пайплайн

Инструменты для сбора случайных НПА с adilet.zan.kz и прогона их через штатный пайплайн
(**структура → ссылки → чанки**; вектор-слой НЕ трогается) с честной оценкой результата.

Цель — стресс-тест пайплайна на произвольных законах (не на 14 курируемых кодексах) и
выявление форматов, которые он не тянет. Изолирован от готового корпуса.

## TLS к adilet (обязательно)

adilet отдаёт **неполную цепочку** сертификата → `requests` с `verify=True` падает на всех
запросах. Готовый бандл (certifi + промежуточный GoGetSSL из AIA) лежит в `certs/adilet_chain.pem`.
Экспортируй перед любым сетевым шагом (верификация НЕ ослабляется, хостнейм проверяется):

```bash
export REQUESTS_CA_BUNDLE="$(pwd)/pilot/certs/adilet_chain.pem"
```

Пересобрать бандл (если протухнет промежуточный): скачать URL из AIA-расширения листа
(`caIssuers`, сейчас `cacerts.digicert.com/GoGetSSLG2TLSRSA4096SHA2562022CA-1.crt`) в PEM и
дописать к `certifi.where()`.

## Пайплайн запуска

```bash
export REQUESTS_CA_BUNDLE="$(pwd)/pilot/certs/adilet_chain.pem"

# 1. Собрать пул НОВЫХ материальных Z-законов (BFS по перекрёстным ссылкам).
#    Исключает: корпус (maps/codes.json), прошлый пилот (prev_slugs.txt),
#    законы-поправки (<title> «О внесении изменени…»). Кэширует кандидатов в source/.
python pilot/collect_new.py                      # -> pool_new.txt, pool_new_meta.csv

# 2. Выборка 100 (фикс seed, воспроизводимо), запись С LF (не CRLF!).
python pilot/sample_new_100.py                   # -> pilot_100.txt

# 3. Ингест: качает/читает-с-диска + вердикт (см. статусы ниже). Пишет source/{НГР}.html,
#    ingest_manifest.csv; чистые (OK) регистрирует в maps/codes.json (slug = НГР).
python pilot/01_ingest_adilet.py pilot/pilot_100.txt

# 4. Батч по ЯВНОМУ списку слагов (НЕ --all! см. ниже). Гоняет каждый док изолированно.
python pilot/02_batch_run.py $(cat pilot/pilot_100.txt)   # -> reports/pilot/pilot_report.{md,csv}

# 5. Независимый аудит из РЕАЛЬНЫХ файлов (колонки драйвера — эвристики).
python pilot/verify_pilot.py                     # -> pilot_audit.{md,csv}
python pilot/spotcheck.py <slug> ...             # §6 из сырого HTML на выбранных доках
```

## Инструменты

| файл | что делает |
|---|---|
| `collect_new.py` | BFS-сбор пула новых материальных Z-законов (фильтры: корпус/прошлый/поправки), кэш в `source/` |
| `sample_new_100.py` | `random.sample(100)` из пула → `pilot_100.txt` (LF, фикс seed) |
| `01_ingest_adilet.py` | закачка НПА + вердикт (OK/REPEALED/FETCH_THIN/NO_DOCID/FETCH_FAIL), регистрация OK в codes.json |
| `02_batch_run.py` | краш-устойчивый батч preflight→structure→pipeline→gate→chunk, ЧЕСТНЫЙ статус |
| `verify_pilot.py` | аудит из файлов: struct-статьи vs чанк-статьи, класс формата, вердикт |
| `spotcheck.py` | §6-проверка из сырого HTML (text-invariance, nested `<a>`, пустой href, висячие `#z`) |
| `certs/adilet_chain.pem` | TLS-бандл для fetch (см. выше) |

## Статусы

**Ингест (`ingest_manifest.csv`):**
- `OK` — есть article-сигнатуры и doc_id → зарегистрирован в codes.json;
- `REPEALED` — в шапке (до первой «Статья N.») стоит «утратил силу» → **в codes.json НЕ берём**;
- `FETCH_THIN` — 0 article-сигнатур (чужой формат / старый HTML);
- `NO_DOCID` — нет панельных self-ссылок;
- `FETCH_FAIL` — HTTP != 200.

**Батч-драйвер (`pilot_report.md`) — статус ЧЕСТНЫЙ (не «просто не упало»):**
- `DONE` — chunk-файл есть, чанков >0 И **число статей в чанках == числу `div.article` в структуре**;
- `UNDER_CHUNK` — чанки есть, но статьи не сошлись (напр. структуризатор потерял статьи, или часть «исключена»);
- `EMPTY` — чанков нет вовсе;
- `QUARANTINE` — preflight отсёк (статей=0 / нет сигнатур / карта << заголовков);
- `STRUCT_FAIL` / `PIPE_FAIL` / `GATE_RED` — падение соответствующего шага.

Колонки `pre/struct/links/gate/chunk` = «шаг отработал», `ст/чанк` = struct-статьи / чанк-статьи.

**Аудит (`verify_pilot.py`):** `CHUNKED_OK` (статьи==чанки, doc_id консистентен) / `NO_STRUCT`
(0 `div.article`) / `EMPTY_CHUNK` / `DOCID_MISMATCH` / `NO_STRUCT_FILE`.

## ⚠️ Безопасность корпуса

- **НЕ запускай `02_batch_run.py --all`.** `--all` берёт ВСЕ slug из codes.json с `source/` на
  диске → зацепит 38 курируемых кодексов и **перезапишет их `final/*_structured.html`**. Всегда
  гоняй по ЯВНОМУ списку пилотных слагов.
- Пилот регистрирует свои НГР в общем `maps/codes.json` (runtime-артефакт) — эти записи в git
  не коммитим; чистый corpus-codes.json = 43 записи. Пересобирается ингестом.
- Слаги всегда чистить от `\r` (файлы пишем с LF): CRLF ломает `source/{slug}.html`-резолвинг.
