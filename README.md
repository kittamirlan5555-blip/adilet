# ADILETkz — гиперссылочная обработка правового корпуса РК

Конвейер превращает сырой HTML кодексов и законов РК с **adilet.zan.kz** в
согласованные артефакты: `*_ready.html` (плоская форма со ссылками),
`*_structured.html` (она же с иерархией, КАНОН по ссылкам) и jsonl-чанки +
faiss-индекс для vector DB. Сейчас в корпусе **25 документов** (13 кодексов +
12 законов).

Агентские правила (полный спан, гейты, грабли) — **CLAUDE.md**. Кто чего
ждёт — **reports/WAITING_ON_HUMANS.md**.

## Карта проекта

Единая точка истины по путям — `scripts/paths.py`. Каждый скрипт берёт пути ТОЛЬКО оттуда.

```
ADILETkz/
├── README.md, CLAUDE.md, requirements.txt
├── source/        сырой HTML adilet — ВХОД (READ-ONLY)            → source/README.md
├── final/         *_ready + *_structured — ПРОДУКТ (канон=_structured) → final/README.md
├── maps/          codes.json, npa_mapping.json, article_map_*, subpoint_map_* → maps/README.md
├── derived/       перегенерируемое из final/                      → derived/README.md
│   ├── tree/          деревья структуры (hier_id)
│   ├── chunks/        чанки по документам
│   ├── structured_out/ jsonl по схеме шефа (hier_id UKCH1R1ST1P1)
│   └── vector_layer/  chunks.jsonl + index.faiss + meta/config (small-to-big retrieval)
├── scripts/       весь код; пути — ТОЛЬКО из paths.py
│   ├── paths.py      единая точка истины по путям
│   ├── verify.py     оркестратор гейтов (verify.py слаг | --all)
│   ├── pipeline/     шаги построения (вход pipeline.py)           → scripts/pipeline/README.md
│   ├── audit/        гейты и независимая верификация              → scripts/audit/README.md
│   ├── vector/       вектор-слой a..j (чанкинг→summary→faiss→эвал)
│   ├── tests/        юнит-тесты линковки
│   └── hooks/        pre-push (тесты + verify по изменённым слагам)
├── reports/       ТОЛЬКО актуальное: доски + вектор-отчёты + audit/ + gates/ → reports/README.md
├── deliverables/  ТОЛЬКО последний пакет (vector_layer/)          → deliverables/README.md
├── docs/          brief/, anara/ — история ревью
└── archive/       всё историческое (раунды, старые пакеты, attic) — НА ДИСКЕ, вне git
```

Локально на диске, но **вне репозитория** (в `.gitignore`): `archive/`, `reports/gates/`
(перегенерируемые гейты), `_old_tree_leftovers/`, `backups/`, `venv/`. История в git
сохранена — архивные файлы восстановимы из прошлых коммитов.

## Статус документов

| документы | статус |
|---|---|
| 13 кодексов + arbitrazh, bezhenci, goszakup, ocorrupt, zhilishniy | ✅ приняты |
| informatizacii, notariat, obrazovanie | 📤 у Анары (пакет — `archive/deliverables/laws3/`) |
| gosuslugi, persdata | ✅ приняты ревью (без замечаний, 2026-06-11) |
| pravoohranitel | 🔁 фидбек получен (6 флагов), правки внесены (пакет — `archive/deliverables/laws_r3/`) |
| Конституция, prezident | ⏸ в холде (лежат в source/, не обрабатывались) |

## Типовые сценарии

**Новый документ** (выгрузка `source/X.html`):
```bash
# 1. запись в maps/codes.json:  "слаг": {"doc_id": "Zxxxxxxxxxx", "title": "...", "source": "X.html"}
python scripts/pipeline/pipeline.py слаг                     # → final/слаг_ready.html
python scripts/pipeline/11_structure_html.py --input final/слаг_ready.html --output final/слаг_structured.html
python scripts/pipeline/68_link_canon.py --doc-id Zxxxxxxxxxx               # канон structured
python scripts/pipeline/68_link_canon.py --doc-id Zxxxxxxxxxx --form ready  # канон ready
python scripts/pipeline/71_fullspan_wrap.py слаг --apply
python scripts/verify.py слаг                                # все гейты + gap-остаток
# gap-остаток ≠ 0 → закрыть кандидатов (ключи в npa_mapping ТОЛЬКО после сверки НГР, §5)
python scripts/pipeline/chunk_npa.py слаг && python scripts/pipeline/structurize.py слаг
```

**Защита от регрессий (pre-push hook):**
```bash
cp scripts/hooks/pre-push .git/hooks/pre-push   # установка (раз на клон)
# на push: юнит-тесты + verify по изменённым слагам; FAIL = пуш блокируется.
# Осознанный обход (например, пуш заведомо красного WIP): git push --no-verify
```

**Проверка корпуса целиком:**
```bash
python scripts/verify.py --all          # exit 0 = зелёный; сводка reports/gates/verify_summary.txt
python -m unittest discover -s scripts/tests -t .
```

**Сдача Анаре:** убедиться `verify.py слаг` зелёный и gap-остаток
пуст/объяснён → собрать `deliverables/<раунд>/` (обе формы + SDACHA_*.md:
цифры, что не линковано и почему, вето-строки) → после её жёлтых пометок
каждую делать ссылкой ПОЛНЫМ СПАНОМ (§2.1 CLAUDE.md), гейты, спот-чек.

**FAIL гейта:** открыть отчёт в `reports/gates/` (71_gates_слаг.txt и т.д.) →
смотреть конкретный RED → чинить ТОЛЬКО скриптом с text-invariance-гейтом →
повторить `verify.py слаг`. G6 (формы разошлись) →
`python scripts/audit/r3_02_g6_apply.py слаг --apply` (канон пер-кейс).
Никогда не «чинить» перегенерацией принятого документа.

## Инвариант форм

**`_structured` — канон по ссылкам**; `_ready` синхронизируется с ним
(G6-гейт). Видимый текст обеих форм байт-в-байт равен source (§6.1).
Чанки строятся ТОЛЬКО из `_structured`.

## Реестр документов

Кодексы:

| Кодекс | Ключ | doc_id |
|--------|------|--------|
| Налоговый | nalog | K2500000214 |
| Трудовой | trudovoy | K1500000414 |
| Гражданский (Общая) | grazhdanskiy | K940001000_ |
| Гражданский (Особенная) | grazhdanskiy_osob | K990000409_ |
| Предпринимательский | predprinimatel | K1500000375 |
| Социальный | socialnyy | K2300000224 |
| Экологический | ekologicheskiy | K2100000400 |
| Земельный | zemelnyy | K030000442_ |
| УПК | upk | K1400000231 |
| КоАП | koap | K1400000235 |
| АППК | appk | K2000000350 |
| Бюджетный | byudzhet | K2500000171 |
| Уголовный | ugolovniy | K1400000226 |

Законы — ключи в `maps/codes.json`; новые R3/R4:

| Закон | Ключ | doc_id |
|---|---|---|
| О государственных и социально ответственных услугах | gosuslugi | Z1300000088 |
| О правоохранительной службе | pravoohranitel | Z1100000380 |
| О персональных данных и их защите | persdata | Z1300000094 |

Структуризация для vector DB по схеме шефа (hier_id вида `UKCH1R1ST1P1`):
`python scripts/pipeline/structurize.py --all` → `derived/structured_out/`.

## Вектор-слой (semantic retrieval)

Small-to-big: parent-чанк на статью (`chunk_id` = якорь `zX`, НЕ меняется),
additive-сабчанки `zX_1..` для длинных статей, summary (DeepSeek) для крупных,
faiss-индекс по эмбеддингам MiniLM; исключённые (`kind=repealed`) — в `chunks.jsonl`,
но ВНЕ индекса. Артефакты — `derived/vector_layer/`.

```bash
python scripts/vector/f_full_chunks.py      # чанкинг всех статей → chunks.jsonl
python scripts/vector/c_summarize.py --all   # summary крупных (ключ из env DEEPSEEK_API_KEY)
python scripts/vector/g_build_index.py       # faiss-индекс (MiniLM; --model e5 для e5-large)
python scripts/vector/i_retrieval_eval.py    # hit@1/hit@3 → reports/retrieval_eval.md
python scripts/vector/j_repealed_audit.py    # единый repealed-подход → reports/repealed_uniformity.md
```

История переездов дерева и прошлых раундов — в `archive/` (`archive/docs/MOVES.md`,
`archive/docs/CLEANUP.md`, `archive/docs/CLEANUP_v2.md`; раунды — `archive/reports/`,
`archive/deliverables/`).
