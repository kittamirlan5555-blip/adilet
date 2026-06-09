# RUNBOOK — обработка одного закона РК от и до

Для новичка. **Только терминал, без AI.** Каждый шаг: команда → ожидаемый результат → что считать «ок».

Закон-пример, на котором этот кит проверен: **«Об информатизации», NGR `Z1500000418`** (ключ `obinform`).
Везде ниже подставляйте свой `{ключ}` (латиницей, без пробелов, напр. `obinform`) и `{NGR}` (напр. `Z1500000418`).

---

## 0. Подготовка (один раз)

1. Установить Python 3.9+ и зависимость:
   ```
   pip install beautifulsoup4
   ```
2. Открыть терминал в папке `law_kit/` (все команды ниже запускаются отсюда).
3. Включить UTF-8 вывод (иначе кириллица ломается на Windows-консоли cp1251):
   - **Windows PowerShell:** `$env:PYTHONIOENCODING="utf-8"`
   - **Windows cmd:** `set PYTHONIOENCODING=utf-8`
   - **Linux/macOS:** `export PYTHONIOENCODING=utf-8`

> `data/source/` — единственный источник правды. Он **read-only**: правьте только выходные файлы.
> Любой шаг можно перезапустить с нуля от шага 3 — исходник не меняется.

---

## 1. Скачать закон с adilet → `data/source/{ключ}.html`

1. Открыть закон на `adilet.zan.kz` в браузере.
2. `Ctrl+S` → «Веб-страница полностью» → сохранить как `data/source/{ключ}.html`.

**Ожидаемо:** файл `data/source/{ключ}.html` весит сотни КБ (пример obinform ≈ 620 КБ).
**Ок, если:** файл существует и открывается, в нём виден текст статей.

---

## 2. Записать NGR в `config/codes.json`

Открыть `config/codes.json` и добавить строку в список (NGR = из URL adilet, напр. `Z1500000418`):

```json
  "obinform": {"doc_id": "Z1500000418", "title": "Об информатизации"},
```

**Ок, если:** JSON валиден (нет «висящей» запятой у последнего элемента), ключ совпадает с именем файла `data/source/{ключ}.html`.

---

## 3. Структурировать → проверить выход

```
python scripts/11_structure_html.py --input data/source/{ключ}.html --output data/final/{ключ}_structured.html
```

**Ожидаемо (печатает в консоль):**
```
    разделов: 3
    глав: 13
    статей: 88
```
**Ок, если:**
- `статей` > 0 и примерно совпадает с числом статей в оглавлении на adilet;
- `разделов`/`глав` соответствуют структуре закона (у `obinform`: 3 раздела, 13 глав, 88 статей — **проверено**).

Быстрая проверка вложенности (все статьи должны лежать внутри глав/разделов):
```
python -c "from bs4 import BeautifulSoup as B; from pathlib import Path; s=B(Path('data/final/{ключ}_structured.html').read_text(encoding='utf-8'),'html.parser'); arts=s.find_all('div',{'data-type':'статья'}); bad=sum(1 for d in arts if not d.find_parent('div',{'data-type':'глава'})); print('статей:',len(arts),'не вложено в главу:',bad)"
```
**Ок, если:** `не вложено в главу: 0` (либо небольшое число для законов без глав).

> **Склейка «подзаголовок раздела + Глава N» в одном `<h3>`.** Иногда adilet
> отдаёт подзаголовок раздела и первую главу одним заголовком, напр.
> `…НОТАРИАЛЬНЫЕ ДЕЙСТВИЯ И ПРАВИЛА ИХ СОВЕРШЕНИЯ  Глава 6. …`. Структуризатор
> теперь **сам разбивает** такой заголовок (подзаголовок → контент раздела,
> «Глава N» → отдельная глава), текст не теряется. Ручная правка `data/source/`
> **не нужна** — если глав в выводе на одну меньше, чем в оглавлении, это, скорее
> всего, как раз такой случай: просто сверьте число `глав` с adilet.
>
> **Слитый «РАЗДЕЛ N + Глава M» с ВНУТРЕННИМ якорем главы.** Отдельный подвид той же
> склейки: «голый» маркер раздела и глава лежат в одном `<h3>`, а якорь главы —
> внутренний `<a name>`, напр. `<h3 id="z12">РАЗДЕЛ 2 <br><a name="z13"></a>Глава 2. …</h3>`
> (пример — `zhilishniy`, разделы 2,4,5,6). Структуризатор расщепляет такой тег
> по-настоящему: раздел получает только «РАЗДЕЛ N», а глава — **отдельный реальный
> узел** со своим якорем (`z13` и т.п.) и названием. Срабатывает точечно — только на
> «голый» «РАЗДЕЛ N» (без собственного названия); кодексы вида
> `РАЗДЕЛ 1. ОБЩИЕ ПОЛОЖЕНИЯ Глава 1. …` не затрагиваются.

---

## 4. Внутренние ссылки (3 под-шага: карта → якоря → ссылки)

### 4a. Карта «статья → якорь»
```
python scripts/01_build_article_map.py --input data/final/{ключ}_structured.html --output data/maps/article_map_{ключ}.json
```
**Ожидаемо:** `Найдено статей: 88` (= число статей из шага 3).

### 4b. Инжекция якорей-заголовков + карта подпунктов  *(обязательно!)*
```
python scripts/07_add_subpoint_anchors.py --input data/final/{ключ}_structured.html --output data/final/{ключ}_structured.html --map data/maps/article_map_{ключ}.json --subpoint-map-output data/maps/subpoint_map_{ключ}.json
```
**Ожидаемо:** `Инжектировано синтетических anchor-заголовков: 76` и `Добавлено якорей к подпунктам: …`.
**Зачем:** adilet даёт реальный якорь не у каждого заголовка статьи. Без этого шага ссылки `статья N` будут вести в пустоту (битые). Команда читает файл целиком и перезаписывает — запуск «на месте» безопасен.

### 4c. Расстановка ссылок
```
python scripts/02_fix_internal_links.py --input data/final/{ключ}_structured.html --map data/maps/article_map_{ключ}.json --subpoint-map data/maps/subpoint_map_{ключ}.json --doc-id {NGR} --output data/final/{ключ}_structured.html --report data/reports/{ключ}_fixlinks.csv
```
**Ожидаемо:** `Исправлено ссылок: 91` (пример obinform).

### 4d. КОНТРОЛЬ: битых якорей быть не должно
```
python -c "from bs4 import BeautifulSoup as B; from pathlib import Path; import re; SELF='{NGR}'; s=B(Path('data/final/{ключ}_structured.html').read_text(encoding='utf-8'),'html.parser'); ids={t.get('id') for t in s.find_all(attrs={'id':True})}|{a.get('name') for a in s.find_all('a',{'name':True})}; frags=[m.group(1) for a in s.find_all('a',href=True) for m in [re.search(r'/docs/'+SELF+r'#(z[\\w-]+)',a['href']) or re.match(r'#(z[\\w-]+)',a['href'])] if m]; broken=[f for f in frags if f not in ids]; print('само-ссылок:',len(frags),'битых:',len(broken)); print(broken[:10])"
```
**Ок, если:** `битых: 0` (пример obinform: само-ссылок 95, битых 0). Если битых > 0 — значит пропустили шаг 4b.

---

## 5. Аудит корректности (WRONG / SUB / BROKEN = 0)

Аудит сам берёт список кодов из `config/codes.json` — **ничего править в Python не нужно**
(достаточно, что вы добавили ключ на шаге 2). Коды без `data/final/{код}_structured.html`
молча пропускаются, так что в таблице вы увидите только свой `{ключ}`.

```
python scripts/audit_links_coverage.py
```
**Ожидаемо:** таблица «PART 2 — КОРРЕКТНОСТЬ». В строке `{ключ}`:
```
{ключ}   OK=..  WRONG=0  SUB=0  BROKEN=0  ...
```
**Ок, если:** `WRONG=0`, `SUB=0`, `BROKEN=0` (это жёсткие требования).
`SELF_W` и `NONART` — информационные (возможны ложные срабатывания, не дефекты). `dupID=0` желательно.

---

## 6. Чанкинг

Требует `{ключ}` в `config/codes.json` (сделано на шаге 2).
```
python scripts/chunk_npa.py {ключ}
```
**Ожидаемо:** `{ключ}: 88 articles, 365 chunks → {ключ}.json + {ключ}.jsonl` (пример obinform).
Артефакты: `data/tree/{ключ}.json` (дерево) и `data/chunks/{ключ}.jsonl` (чанки).
**Ок, если:** `articles` = число статей из шага 3; файлы непустые; в чанке есть `meta.hier_id` (напр. `OBINFORMR1G1ST1SP1`).

---

## 7. Финальная проверка

### 7a. Независимый верификатор (2-й метод)
Тоже берёт коды и NGR из `config/codes.json` — **ничего править в Python не нужно**.
Необработанные коды пропускаются, так что в таблице будет только ваш `{ключ}`.
```
python scripts/67_independent_verify.py
```
**Ок, если:** для `{ключ}` — `НЕ совпало = 0`, `не-резолв = 0`, `name↔NGR = 0`.

> Примечание: внутренний счётчик `checked` у этого верификатора считает только
> **относительные** само-ссылки вида `#zN`. Минимальный маршрут (шаги 3–4) оставляет
> само-ссылки в полной форме `…/docs/{NGR}#zN`, поэтому здесь `checked` может быть `0`
> (проверять нечего — это норма). Корректность само-ссылок при этом уже подтверждена
> аудитом на шаге 5 (`WRONG = SUB = BROKEN = 0`), который понимает обе формы.

### 7b. Дивергенция `_ready` vs `_structured` (опционально)
Скрипт `29_diff_ready_structured.py` сравнивает две формы файла (`_ready` и `_structured`).
В минимальном маршруте одного закона делается **только `_structured`**, поэтому этот шаг
**не нужен** (он для кодексов, где ведут обе формы). Если когда-нибудь появится `{ключ}_ready.html` —
добавьте `{ключ}` в список `CODES` скрипта 29 и запустите `python scripts/29_diff_ready_structured.py`
(ожидается ДИФФ=0).

### Итоговый чек-лист «закон готов»
- [ ] шаг 3: `статей > 0`, вложенность ок
- [ ] шаг 4a: `Найдено статей` = `статей`
- [ ] шаг 4b: якоря инжектированы
- [ ] шаг 4d: **битых якорей = 0**
- [ ] шаг 5: **WRONG = SUB = BROKEN = 0**
- [ ] шаг 6: `articles` = `статей`, чанки непустые
- [ ] шаг 7a: **НЕ совпало = 0**, не-резолв = 0

Всё отмечено → закон обработан корректно.

---

## Шпаргалка (всё подряд, пример obinform / Z1500000418)

```
# 0
pip install beautifulsoup4
$env:PYTHONIOENCODING="utf-8"            # PowerShell (cmd: set PYTHONIOENCODING=utf-8)
# 2: вручную добавить "obinform" в config/codes.json
# 3
python scripts/11_structure_html.py --input data/source/obinform.html --output data/final/obinform_structured.html
# 4a
python scripts/01_build_article_map.py --input data/final/obinform_structured.html --output data/maps/article_map_obinform.json
# 4b
python scripts/07_add_subpoint_anchors.py --input data/final/obinform_structured.html --output data/final/obinform_structured.html --map data/maps/article_map_obinform.json --subpoint-map-output data/maps/subpoint_map_obinform.json
# 4c
python scripts/02_fix_internal_links.py --input data/final/obinform_structured.html --map data/maps/article_map_obinform.json --subpoint-map data/maps/subpoint_map_obinform.json --doc-id Z1500000418 --output data/final/obinform_structured.html --report data/reports/obinform_fixlinks.csv
# 5 (коды берутся из codes.json — Python не правим)
python scripts/audit_links_coverage.py
# 6
python scripts/chunk_npa.py obinform
# 7a (коды берутся из codes.json — Python не правим)
python scripts/67_independent_verify.py
```

---

## CHANGELOG

**2026-06-08 — `scripts/11_structure_html.py`: расщепление слитого «РАЗДЕЛ N + Глава M» с ВНУТРЕННИМ якорем главы.**
> **Дамир — обнови свою копию `scripts/11_structure_html.py`** (возьми новый файл; прежний — `scripts/11_structure_html.py.bak_premergesplit`).
> Что изменилось: к авто-разбивке слитых заголовков добавлен случай, когда «голый»
> маркер раздела и глава лежат в ОДНОМ `<h3>`, а якорь главы — внутренний `<a name>`,
> напр. `<h3 id="z12">РАЗДЕЛ 2 <br><a name="z13"></a>Глава 2. …</h3>`. Раньше такой
> тег целиком уходил в заголовок РАЗДЕЛА: якорь главы оказывался «заперт» в разделе,
> а название главы дублировалось virtual-копией без якоря (глава получала `id=None`).
> Теперь раздел получает только «РАЗДЕЛ N», а глава — отдельный **реальный** узел с
> якорем и названием. Триггер строго точечный: только «голый» «РАЗДЕЛ N» (без своего
> названия) + глава с внутренним якорем; кодексы вида `РАЗДЕЛ 1. ОБЩИЕ ПОЛОЖЕНИЯ
> Глава 1. …` НЕ затрагиваются. Изменения только в `11`; остальные скрипты и формат
> вывода прежние. Проверено на ОРИГИНАЛЕ `data/source/zhilishniy.html`: разделы
> 2,4,5,6 → главы 2/9/16/17 стали реальными узлами с якорями `z13/z79/z136/z140`,
> текст глав в get_text больше не дублируется; 6 разделов / 18 глав / 165 статей,
> все гейты зелёные (audit WRONG/SUB/BROKEN/dupID/name_mismatch=0, 67 mismatch=0,
> 6-проверок=0, чанки 645). **Регрессия:** прогон обновлённого `11` на ВСЕХ 21
> источниках — байт-в-байт совпало 20/21, изменился ТОЛЬКО `zhilishniy`.

**2026-06-05 — `scripts/11_structure_html.py`: авто-разбивка слитых заголовков «раздел+глава».**
> **Дамир — обнови свою копию `scripts/`** (возьми новый `11_structure_html.py`).
> Что изменилось: структуризатор теперь сам разбивает заголовок вида
> `…ПОДЗАГОЛОВОК РАЗДЕЛА  Глава N. …` на два элемента (подзаголовок → контент,
> «Глава N» → отдельная глава). Раньше такая склейка «съедала» главу (на «О нотариате»
> терялась глава 6), и приходилось вручную править исходник — **теперь не нужно**.
> Изменения только в `11`; остальные скрипты и формат вывода прежние. Проверено:
> «О нотариате» из ОРИГИНАЛА `data/source/notariat.html` → 2 раздела / 19 глав /
> 126 статей (глава 6 = ст. 34–38), все гейты зелёные; 14 ранее готовых доков —
> структура без изменений (регрессий нет). Бэкап прежней версии:
> `scripts/11_structure_html.py.bak_presplit`.
