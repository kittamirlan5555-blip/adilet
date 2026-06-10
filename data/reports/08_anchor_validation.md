# Этап — Строгий audit якорей (внутренних и cross-code)

Проверяем КАЖДЫЙ `<a href>` во всех 12 кодексах: ведёт ли он на существующий якорь?

## Распределение статусов (по всему корпусу)

| Статус | Кол-во |
|---|---|
| PASS_INTERNAL | 12088 |
| PASS_EXTERNAL_UNVERIFIED | 9226 |
| PASS_EXTERNAL_ROOT | 1080 |
| PASS_CROSSCODE | 921 |
| PASS_OFFSITE_OR_NAV | 577 |
| PASS_TARGET_ROOT | 344 |

## Failure breakdown по кодексам

| Кодекс | broken internal | broken external | empty/hash | wrong_href | **всего FAIL** |
|---|---|---|---|---|---|
| `appk` | 0 | 0 | 0 | 0 | **0** |
| `byudzhet` | 0 | 0 | 0 | 0 | **0** |
| `ekologicheskiy` | 0 | 0 | 0 | 0 | **0** |
| `grazhdanskiy` | 0 | 0 | 0 | 0 | **0** |
| `koap` | 0 | 0 | 0 | 0 | **0** |
| `nalog` | 0 | 0 | 0 | 0 | **0** |
| `predprinimatel` | 0 | 0 | 0 | 0 | **0** |
| `socialnyy` | 0 | 0 | 0 | 0 | **0** |
| `trudovoy` | 0 | 0 | 0 | 0 | **0** |
| `ugolovniy` | 0 | 0 | 0 | 0 | **0** |
| `upk` | 0 | 0 | 0 | 0 | **0** |
| `zemelnyy` | 0 | 0 | 0 | 0 | **0** |

## Примеры FAIL_BROKEN_INTERNAL_ANCHOR (первые 30)

| Код | href | text | target_anchor |
|---|---|---|---|

## Примеры FAIL_BROKEN_EXTERNAL_ANCHOR (первые 30)

| Код | href | text | target_code | target_anchor |
|---|---|---|---|---|
