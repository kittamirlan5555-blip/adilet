# Аудит лимита e5 (512 токенов) по индексируемым пассажам

Модель: `intfloat/multilingual-e5-large`, лимит **512** токенов (префикс `passage: ` + спецтокены учтены). Индексируемых пассажей: **17786**.

- истинная длина (БЕЗ обрезки) > 512 токенов: **25** (0.1%) — у этих пассажей e5 теряет хвост;
- после символьного окна WIN=1800: > 512 токенов: **23** (это режет уже сама e5 поверх окна);
- токены/пассаж (истинные): median **253**, p90 **336**, max **3106**.

## Превышение по типу пассажа (истинная длина)

| src | >512 | всего | доля |
|---|---|---|---|
| subchunk | 20 | 10575 | 0.2% |
| article | 2 | 6546 | 0.0% |
| summary | 3 | 665 | 0.5% |

## Список превышающих 512 токенов (истинная длина), топ-25 из 25

| код | uid | src | символы | токены |
|---|---|---|---|---|
| zdorovyenaroda | zdorovyenaroda_z8 | summary | 13264 | 3106 |
| obrazovanie | obrazovanie_z3 | summary | 3867 | 794 |
| ugolovniy | ugolovniy_z1705_2 | subchunk | 1594 | 680 |
| koap | koap_z3239_1 | subchunk | 1551 | 664 |
| nalog | nalog_z9657_1 | subchunk | 1699 | 650 |
| ekologicheskiy | ekologicheskiy_z4470 | article | 1600 | 633 |
| nalog | nalog_z9650_2 | subchunk | 1576 | 623 |
| predprinimatel | predprinimatel_z324_9 | subchunk | 1481 | 621 |
| koap | koap_z3239_2 | subchunk | 1525 | 614 |
| nalog | nalog_z9650_1 | subchunk | 1578 | 600 |
| nalog | nalog_z10302_4 | subchunk | 1526 | 573 |
| nalog | nalog_z10302_1 | subchunk | 1551 | 565 |
| appk | appk_z1424_1 | subchunk | 1529 | 565 |
| koap | koap_z2792_2 | subchunk | 1596 | 564 |
| nalog | nalog_z10302_3 | subchunk | 1448 | 556 |
| koap | koap_z2233_2 | subchunk | 1536 | 556 |
| nalog | nalog_z10691_11 | subchunk | 1589 | 553 |
| nalog | nalog_z10302_2 | subchunk | 1494 | 552 |
| koap | koap_z2227_4 | subchunk | 1415 | 539 |
| nalog | nalog_z10691_9 | subchunk | 1184 | 537 |
| UIK | UIK_z889_1 | subchunk | 1538 | 525 |
| koap | koap_z2227_3 | subchunk | 1514 | 521 |
| koap | koap_z2233_4 | subchunk | 1471 | 517 |
| koap | koap_z2233 | summary | 1502 | 516 |
| alatau | alatau_z1144 | article | 1524 | 515 |
