# АУДИТ 01 — Инвентаризация корпуса

Сгенерировано: scripts/audit/a01_inventory.py, 2026-06-10

Кодекс = есть форма `_ready`; закон = только `_structured`.

| slug | doc_id | формы | размер ready/structured | <a href r/s | id+name r/s | article_map | subpoint_map | source (size) | mtime |
|---|---|---|---|---|---|---|---|---|---|
| appk | K2000000350 | ready+structured | 658,494 / 685,877 | 285 / 286 | 1900 / 2129 | 195 | 502 | appk.html (696,059) | 2026-06-01 16:59 |
| arbitrazh | Z1600000488 | structured | — / 183,682 | — / 137 | — / 523 | 60 | 283 | arbitrazh.html (194,396) | 2026-06-08 14:49 |
| bezhenci | Z090000216_ | structured | — / 107,488 | — / 157 | — / 301 | 22 | 142 | bezhenci.html (120,791) | 2026-06-08 14:49 |
| byudzhet | K2500000171 | ready+structured | 1,534,513 / 1,574,946 | 672 / 672 | 4301 / 4517 | 173 | 923 | byudzhet.html (1,597,310) | 2026-06-02 17:10 |
| ekologicheskiy | K2100000400 | ready+structured | 2,122,224 / 2,190,717 | 667 / 667 | 5720 / 6208 | 418 | 1783 | ekologicheskiy.html (2,194,211) | 2026-06-02 13:10 |
| goszakup | Z2400000106 | structured | — / 270,510 | — / 241 | — / 637 | 29 | 363 | goszakup.html (285,739) | 2026-06-08 14:49 |
| grazhdanskiy | K940001000_ | ready+structured | 966,021 / 1,015,470 | 276 / 301 | 2054 / 2513 | 420 | 184 | grazhdanskiy.html (1,015,110) | 2026-06-08 16:23 |
| grazhdanskiy_osob | K990000409_ | ready+structured | 1,514,813 / 1,584,355 | 1,105 / 1,112 | 3900 / 4714 | **НЕТ** | — | GKosobenniy.html (1,587,868) | 2026-06-08 16:24 |
| informatizacii | Z1500000418 | structured | — / 618,436 | — / 713 | — / 1422 | 88 | 814 | obINFORM.html (637,701) | 2026-06-08 14:40 |
| koap | K1400000235 | ready+structured | 3,966,463 / 4,100,199 | 3,649 / 3,649 | 7148 / 8273 | 1072 | 1140 | koap.html (4,292,531) | 2026-06-03 17:36 |
| nalog | K2500000214 | ready+structured | 5,156,330 / 5,352,771 | 4,443 / 4,447 | 14236 / 15275 | 848 | 7307 | nalog.html (5,118,638) | 2026-06-05 15:22 |
| notariat | Z970000155_ | structured | — / 415,305 | — / 521 | — / 1282 | 126 | 605 | notariat.html (427,451) | 2026-06-08 14:40 |
| obrazovanie | Z070000319_ | structured | — / 955,360 | — / 1,006 | — / 2044 | 88 | 1289 | obrazovanie.html (983,122) | 2026-06-08 14:40 |
| ocorrupt | Z1500000410 | structured | — / 223,230 | — / 265 | — / 470 | 33 | 259 | ocorrupt.html (236,207) | 2026-06-08 14:51 |
| predprinimatel | K1500000375 | ready+structured | 1,694,496 / 1,751,483 | 930 / 930 | 4012 / 4431 | 379 | 1575 | predprinimatel.html (1,780,730) | 2026-06-05 15:22 |
| socialnyy | K2300000224 | ready+structured | 1,511,820 / 1,557,950 | 821 / 826 | 3891 / 4207 | 272 | 2415 | socialnyy.html (1,565,091) | 2026-06-02 17:10 |
| trudovoy | K1500000414 | ready+structured | 891,276 / 922,906 | 303 / 303 | 2170 / 2414 | 221 | 848 | trudovoy.html (894,008) | 2026-06-02 10:57 |
| ugolovniy | K1400000226 | ready+structured | 1,716,843 / 1,770,702 | 601 / 601 | 3607 / 4130 | 502 | 928 | ugolovniy.html (1,780,748) | 2026-06-10 10:40 |
| upk | K1400000231 | ready+structured | 2,890,930 / 2,917,042 | 2,522 / 2,522 | 7890 / 8662 | 686 | 0 | upk.html (3,039,192) | 2026-06-10 10:39 |
| zemelnyy | K030000442_ | ready+structured | 1,267,927 / 1,297,650 | 553 / 553 | 2286 / 2492 | 183 | 664 | zemelnyy.html (1,374,085) | 2026-06-02 16:17 |
| zhilishniy | Z970000094_ | structured | — / 810,806 | — / 872 | — / 1909 | 166 | 989 | zhilishniy.html (827,851) | 2026-06-08 15:44 |

**Итого документов: 21 = 13 кодексов (ready+structured) + 8 законов (только structured).**

## Расхождения с ожиданием

- Задание называет «14 кодексов + 10 законов» (=24). Фактически в data/final: **13 + 8 = 21**. Лишних файлов нет; каких 3 документов не хватает до 24 — вопрос шефу (в FINAL.md).
- В config/codes.json документов: 21; без файла в data/final: нет; файлы без записи в codes.json: нет.

## Воспроизводимость
```
PYTHONIOENCODING=utf-8 python scripts/audit/a01_inventory.py
```
