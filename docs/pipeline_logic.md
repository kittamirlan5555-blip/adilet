# Pipeline logic — ADILETkz

Как корпус собирается, проверяется и векторизуется. Обзорный вход — `../README.md`,
приёмка/правила — [HANDOFF.md](HANDOFF.md) и `../CLAUDE.md`. Все пути — из
`scripts/paths.py` (единая точка истины).

## 0. Две формы и инвариант

Каждый документ существует в двух формах в `final/`:
- **`{слаг}_ready.html`** — плоская форма со ссылками.
- **`{слаг}_structured.html`** — та же + иерархия (`div.article` с `data-type`/
  `data-number`, заголовки разделов/глав). **КАНОН по ссылкам.** Чанки строятся
  ТОЛЬКО из неё.

**Инвариант text-invariance:** любой шаг двигает только теги `<a>`/якоря; видимый
текст (`get_text()` без разделителя, ws-stripped) обязан совпасть байт-в-байт с
исходником. Нарушение → запись отменяется. Это центральный предохранитель.

## 1. Построение `_ready` (вход: `pipeline.py {слаг}`)

`scripts/pipeline/pipeline.py` гонит по порядку (источник — `source/{source}.html`,
doc_id — из `codes.json`):

| шаг | скрипт | что делает |
|---|---|---|
| 1 | `01_build_article_map` | статья N → якорь `zX` (4 способа: `<a name>`, `<h3 id>`, `<p id>`, синтет. `zNh`) → `maps/article_map_{слаг}.json` |
| 2 | `07_add_subpoint_anchors` | якоря пунктов/подпунктов → `subpoint_map_{слаг}.json` |
| 3 | `10_cross_code_refs` | «статья N Налогового кодекса» → якорь в целевом кодексе (через codes.json + npa_mapping) |
| 4 | `02_fix_internal_links` | «статья N настоящего Кодекса», «пунктом 2 статьи 35» → `#zX` (своя карта) |
| 5 | `03_find_external_npa` | голые имена актов «Законом РК "…"» → корень `…/docs/{НГР}` |
| 6 | `06_finalize` | CSS/JS подсветка |
| 7 | `13_cleanup_html` | расщепление вложенных `<a>`, нормализация |
| 8 | `76_mapping_gap_report` | отчёт о «дырах» маппинга (не прерывает) |

Затем вручную/скриптами:
- `11_structure_html --input {ready} --output {structured}` — строит иерархию + якоря.
- `68_link_canon --doc-id {НГР}` и `--form ready` — канон: само-URL → `#z`, dedup,
  нормализация внешних; гейт инвариантности.
- `71_fullspan_wrap {слаг} --apply` (и `--form structured`) — полный спан одиночных
  «пункт N статьи M».
- `chunk_npa {слаг}` → `derived/tree/{слаг}.json` + `derived/chunks/{слаг}.jsonl`.
- `structurize {слаг}` → `derived/structured_out/{слаг}.jsonl` (схема шефа, hier_id).

## 2. Типы ссылок и куда ведут

| тип | пример | цель |
|---|---|---|
| внутренняя | «статьёй 100 настоящего Кодекса» | `#zX` в этом файле |
| внешний акт целиком | «Законом РК "О банках…"» | КОРЕНЬ `…/docs/{НГР}` (без #z) — безопасно |
| cross-code на статью | «статьёй 258 Уголовного кодекса» | якорь статьи в целевом кодексе ИЛИ корень (§9) |
| сноска/правка (ТЗ-02) | «Сноска. … Законом РК от…» | НЕ линкуем (снимается `18_`) |

**§9:** наши якоря ≠ якоря живого adilet. Cross-code/само-ссылка источника на
якорь, который у нас не резолвится или ведёт на другую статью → **корень**
(`78_crosscode_root`). Безопасный дефолт, не ломается.

## 3. Гейты — `verify.py {слаг}|--all`

Оркестратор `scripts/verify.py` прогоняет (slug-уровень и корпусные):

| гейт | что ловит |
|---|---|
| `71_gates` G1–G6 | G1 сырые `</a></a>` · G2 вложенные `<a>` · G3 двойной href · G4 битый внутренний `#z` · G5 cross-code якорь отсутствует в цели · G6 рассинхрон форм `_ready`/`_structured` |
| `75_crosscode` | MISMATCH: «статья N» ведёт на якорь ДРУГОЙ статьи (опасная мислинка §4) |
| `74_freshness` | протухшие НГР (отменённые редакции, §5) |
| `76_gap` | плейн/разорванные правовые фразы + дыры npa_mapping |
| `67_independent` | независимая сверка ссылок из сырого HTML |
| `64_final`, `69_sixcheck` | корпусные финальные проверки |

ВАЖНО: гейты слепы к тому, СОВПАДАЕТ ли якорь с целевой средой (§9) и к границам
спанов — нужна независимая проверка (`original_links_audit.py`, `audit_links_coverage.py`).

**Покрытие:** `audit_links_coverage.py` — cov_lit / cov_cont / **cov_real** (доля
залинкованных правовых отсылок без генерик-самоотсылок и сносочных FP) + PART 2
(OK/WRONG/BROKEN внутренних `#z`).

## 4. Вектор-слой (`scripts/vector/`, small-to-big)

| шаг | скрипт | результат |
|---|---|---|
| чанкинг | `f_full_chunks` | `chunks.jsonl`: parent на статью (`chunk_id`=якорь zX) + subchunk `zX_N` (≤окна ~1800) + repealed (`kind=repealed`) |
| summary | `c_summarize --all` | DeepSeek-выжимки крупных статей (ключ ТОЛЬКО из env `DEEPSEEK_API_KEY`, в файлы не пишется) |
| индекс | `g_build_index` | faiss `index.faiss` + `index_meta.jsonl`: эмбед мелких статей/сабчанков/summary; **repealed ВНЕ индекса**; MiniLM-384 (опц. `--model e5`) |
| эвал | `i_retrieval_eval` | hit@1/hit@3 → `reports/retrieval_eval.md` |
| валидация | `d_validate` | достоверность summary (числа/термины из оригинала) → `reports/summary_eval.md` |
| repealed | `j_repealed_audit` | единый подход repealed по всем докам → `reports/repealed_uniformity.md` |

Ретрив: запрос → эмбед → faiss top-k → резолв в РОДИТЕЛЬСКУЮ статью (uid) → payload =
полный текст статьи (small-to-big). Якоря статей в чанках не меняются; репил —
в `chunks.jsonl` есть, в индексе нет.

## 5. Скрипты, добавленные в batch9 (на случай «что это»)

| скрипт | зачем |
|---|---|
| `audit/preflight_new.py` | pre-flight новых выгрузок: структура парсится как у рабочих? doc_id из панели adilet (`/history`,`/info`,`/links`)? |
| `pipeline/77_unwrap_dangling.py` | висячие self-`#z` (adilet mid-paragraph якоря, удаляемые `13_cleanup`) → в текст (text-invariant) |
| `pipeline/78_crosscode_root.py` | cross-code на несогласуемый/чужой якорь (§4/§6/§9) → корень |
| `pipeline/79_canon_self_anchor.py` | свести «статья N» к якорю article_map в обеих формах (чинит G6 + мислинки `_ready`) |
| `audit/original_links_audit.py` | аудит ОРИГИНАЛЬНЫХ ссылок adilet: само-ссылки целы? внешние в теле сохранены/потеряны? (классификатор сносок — пайплайновый `18_`, не эвристика) |

## 6. Защита от регрессий

- **pre-push hook** (`scripts/hooks/pre-push`): юнит-тесты + `verify` по изменённым
  слагам; FAIL блокирует пуш.
- **Юнит-тесты:** `python -m unittest discover -s scripts/tests -t .`
- При FAIL гейта: чинить ТОЛЬКО скриптом с text-invariance-гейтом, не перегенерацией
  принятого документа.
