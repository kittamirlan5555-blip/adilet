# ADILETkz — гиперссылочная обработка кодексов РК

Конвейер превращает «сырой» HTML кодексов Республики Казахстан с портала
**adilet.zan.kz** в три согласованных артефакта для RAG/поиска:

* `*_ready.html` — плоская читаемая версия со всеми гиперссылками;
* `*_structured.html` — та же версия + иерархическая разметка
  (`<div data-type=…>` ЧАСТЬ → РАЗДЕЛ → ГЛАВА → СТАТЬЯ);
* `chunks/*.jsonl` + `tree/*.json` — чанки и дерево для индексации.

Обрабатывается **13 кодексов** (ready+structured) и **8 законов** (только
`_structured`). Все формы согласованы по видимому тексту и по ссылкам.

### Статус законов

| законы | статус |
|---|---|
| arbitrazh, bezhenci, goszakup, ocorrupt, zhilishniy | ✅ приняты ревью |
| informatizacii, notariat, obrazovanie | 📤 переданы Анаре 2026-06-10, ждут ревью (`deliverables/laws3/`) |
| Конституция, prezident | ⏸ в холде до решения Анары (constitution.html и prezident.html лежат в `source/`, НЕ обрабатывались) |

---

## 1. Карта проекта

```
ADILETkz/
├── README.md                    ← этот файл
├── requirements.txt             beautifulsoup4, lxml (Python 3.10+)
├── ANARA_03_MASTER_CHECKLIST.md     рабочие чек-листы ревью (история)
├── master_anara_remarks_since_13_may.md
│
├── scripts/        ВЕСЬ исполняемый код  →  см. scripts/README.md
│   └── debug/      одноразовые диагностические утилиты
│
├── config/
│   ├── codes.json            реестр 13 кодексов: ключ → doc_id, title, _deprecated_remaps
│   ├── npa_mapping.json      словарь «фраза названия НПА» → doc_id (внешние ссылки)
│   └── manual_overrides.json точечные ручные правки таргетов
│
├── data/           ВСЕ данные  →  см. data/README.md
│   ├── source/     ИСХОДНЫЙ HTML (read-only, НИКОГДА не редактируется)
│   ├── final/      *_ready.html + *_structured.html (13+13) — основной продукт
│   ├── chunks/     *.jsonl (13) — чанки из _structured
│   ├── tree/       *.json (13) — дерево из _structured
│   ├── maps/       article_map_*.json, subpoint_map_*.json (статья → якорь)
│   ├── reports/    отчёты аудита/диффа + ОТЧЁТ_гиперссылки.md (для шефа)
│   ├── send_chef/  выгрузка чанков шефу
│   └── anara_package/  пакет для ревьюера (Анара): чанки + примеры
│
├── brief/          ТЗ и сопроводительные материалы
└── archive/        перенесённое при уборке (бэкапы, одноразовые скрипты) — НЕ активно
    ├── data_backups/      все final_backup_*/ , interm/ , final_interim_*
    ├── old_root_scripts/  fix_*.py, search*.py (исторические одноразовые)
    └── misc/              архивы/черновики
```

`venv/` — локальное виртуальное окружение (не входит в поставку).

---

## 2. Пайплайн гиперссылок: `source → _ready → _structured → chunks`

Две фазы. **Фаза A** строит ссылки с нуля; **Фаза B** — правки корректности,
которые делались уже на `_structured` (он стал каноном).

### Фаза A — построение (`pipeline.py` + структуризатор + чанкер)

```
source/{code}.html             ← read-only исходник с adilet.zan.kz
        │
        │  scripts/pipeline/pipeline.py  (оркестрирует 8 шагов)
        │   01 build_article_map   → статья → якорь
        │   07 add_subpoint_anchors→ якоря пунктов/подпунктов
        │   10 cross_code_refs     → «ст. N Налогового кодекса РК» одной ссылкой
        │   02 fix_internal_links  → «ст. N настоящего Кодекса»
        │   03 find_external_npa   → голые названия НПА → внешние ссылки
        │   06 finalize            → CSS/JS подсветка :target
        │   13 cleanup_html        → нормализация вложенных <a>
        │   76 mapping_gap_report  → gap-отчёт маппинга (ОБЯЗАТЕЛЕН перед сдачей)
        ▼
final/{code}_ready.html        ← плоский HTML со ссылками
        │
        │  11_structure_html.py   (добавляет иерархию div[data-type], не трогая текст/ссылки)
        ▼
final/{code}_structured.html
        │
        │  chunk_npa.py           (state-machine по тексту → дерево + чанки)
        ▼
tree/{code}.json  +  chunks/{code}.jsonl
```

Соотношение форм: **`_structured = _ready + иерархические обёртки`**.
В `_ready` нет `div.document`, `div[data-type]` и `-label`-span — это плоский
`<article>`. Видимый текст обеих форм идентичен.

### Фаза B — корректность ссылок (канон = `_structured`)

После Фазы A правки корректности (неверный таргет, потерянные структуризатором
валидные ссылки, self-ссылки, внешние НПА, ГК-Особенная) применялись **на
`_structured`**. Поэтому действует инвариант:

> **`_structured` — канон по ссылкам.** `_ready` подтягивается ИЗ него
> (`29_diff_ready_structured.py`/`30_reconcile_ready_safe.py`), а чанки
> пересобираются ИЗ `_structured`. **Никогда** не регенерировать `_structured`
> из `_ready` и **не** перезапускать Фазу A целиком — это сотрёт правки.

---

## 3. Как запустить end-to-end

```bash
pip install -r requirements.txt          # Python 3.10+, bs4 + lxml

# (1) построить _ready из source  (один код / все)
python scripts/pipeline/pipeline.py socialnyy
python scripts/pipeline/pipeline.py --all

# (2) построить _structured из _ready (один / все)
python scripts/pipeline/11_structure_html.py --input final/socialnyy_ready.html \
                                             --output final/socialnyy_structured.html
python scripts/pipeline/run_structure_all.py

# (3) пересобрать чанки/дерево из _structured
python scripts/pipeline/chunk_npa.py --all

# (4) ЕДИНАЯ верификация (read-only): гейты 71/75/74/76 (+ 67/64/69 при --all)
python scripts/verify.py --all                 # весь корпус, exit 1 при FAIL
python scripts/verify.py socialnyy upk         # выбранные документы
#     спот-чек 5-10 ссылок руками раннер НЕ заменяет (§6 CLAUDE.md)

# (4а) аудит покрытия + корректности (read-only, подробный)
python scripts/audit_links_coverage.py

# (4б) структурные профили source (статьи/главы/пропуски/дубли vs карты)
python scripts/audit/a06_source_profiles.py   # -> reports/audit/source_profiles.*

# (5) ОБЯЗАТЕЛЬНО перед сдачей документа: gap-отчёт маппинга
#     (plain/разорванные правовые фразы + дыры npa_mapping;
#      сканирует _structured, при его отсутствии _ready)
python scripts/pipeline/76_mapping_gap_report.py --doc socialnyy     # или --all
#  → reports/mapping_gap_{slug}.md
#  Сдавать документ можно, только когда остаток в отчёте пуст
#  или каждая строка объяснена в сдаточной записке.
```

> ⚠️ Полный прогон Фазы A на уже-исправленных кодексах **не нужен** и сотрёт
> правки корректности. Для проверки целостности достаточно шага (4).

Кириллица в консоли Windows (cp1251) ломается — отчёты пишутся в UTF-8 файлы;
при перенаправлении stdout используйте `PYTHONIOENCODING=utf-8`.

---

## 4. Текущий статус (заморожено)

| Метрика | Значение |
|---|---|
| Кодексов обработано | **13 / 13** (по 3 формы) |
| Покрытие cov_lit (по ТЗ) | **50.5 %** |
| Покрытие cov_cont (без генерик-самоотсылок) | **70.3 %** |
| Покрытие cov_real (адресные ссылки) | **96.7 %** |
| Корректность внутр. ссылок | **WRONG=0, SUB=0, BROKEN=0, dupID=0** |
| Внешние ссылки | каноничная форма `/rus/docs/{ID}`, `name_mismatch=0` |

Полный разбор для шефа — **`data/reports/ОТЧЁТ_гиперссылки.md`**.
Методику покрытия, корректности и остаток см. там.

---

## 5. Конфигурация и расширение

* **Новый кодекс:** положить `source/<key>.html`, добавить запись в
  `maps/codes.json` (`"<key>": {"doc_id": "Kxxxxxxxxxx", "title": "…"}`),
  прогнать Фазу A → B.
* **Новый внешний НПА:** добавить точную фразу-ключ в `maps/npa_mapping.json`
  (`"Закона Республики Казахстан \"О …\"": "Zxxxxxxxxxx"`). Падеж — из текста.
* **Ссылка на старую версию кодекса:** добавить старый doc_id в
  `_deprecated_remaps` в `maps/codes.json`.

Реестр обработанных кодексов:

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

Подробности по каждому скрипту — **`scripts/README.md`**.
Содержимое папок данных — **`data/README.md`**.
