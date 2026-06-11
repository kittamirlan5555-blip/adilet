# ADILETkz — гиперссылочная обработка правового корпуса РК

Конвейер превращает сырой HTML кодексов и законов РК с **adilet.zan.kz** в
согласованные артефакты: `*_ready.html` (плоская форма со ссылками),
`*_structured.html` (она же с иерархией, КАНОН по ссылкам) и jsonl-чанки для
vector DB. Сейчас в корпусе **24 документа** (13 кодексов + 11 законов).

Агентские правила (полный спан, гейты, грабли) — **CLAUDE.md**. Кто чего
ждёт — **reports/WAITING_ON_HUMANS.md**.

## Карта проекта

```
ADILETkz/
├── README.md, CLAUDE.md, requirements.txt
├── source/        сырые выгрузки adilet (READ-ONLY)         → source/README.md
├── final/         *_ready + *_structured — продукт          → final/README.md
├── maps/          codes.json, npa_mapping.json, карты якорей → maps/README.md
├── scripts/       весь код: paths.py + verify.py
│   ├── pipeline/  шаги построения (вход: pipeline.py)       → scripts/pipeline/README.md
│   ├── audit/     гейты и верификация                       → scripts/audit/README.md
│   ├── tests/     юнит-тесты линковки
│   └── attic/     исторические скрипты (заморожены)
├── derived/       чанки/деревья/structured_out (перегенерируемые) → derived/README.md
├── reports/       доски (WAITING_ON_HUMANS) + gates/ + history/ + раунды → reports/README.md
├── deliverables/  сдаточные пакеты по раундам               → deliverables/README.md
└── docs/          RUNBOOK, brief/, anara/ (история ревью), MOVES, CLEANUP*
```

## Статус документов

| документы | статус |
|---|---|
| 13 кодексов + arbitrazh, bezhenci, goszakup, ocorrupt, zhilishniy | ✅ приняты |
| informatizacii, notariat, obrazovanie | 📤 у Анары (`deliverables/laws3/`) |
| gosuslugi, pravoohranitel, persdata | 📤 пакет готов (`deliverables/laws_r3/`) |
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

История переездов дерева: `docs/MOVES.md` (Фаза A), `docs/CLEANUP.md` (Фаза B),
`docs/CLEANUP_v2.md` (дерево v2, R5).
