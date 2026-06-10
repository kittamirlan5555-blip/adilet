# Этап 4 — Audit состояния (v5, по реестру 01_master_remarks.json)

Замечаний: 404. HTML: `data/final/<code>_ready.html`. Подход: flatten text + link ranges.

## Статусы

| Статус | Кол-во |
|---|---|
| PASS | 234 |
| PASS_UNCLASSIFIED | 156 |
| FAIL_NOT_FOUND | 12 |
| MANUAL_REVIEW | 2 |

## По кодексам

| Кодекс | Всего | PASS | FAIL_* | UNCLASS/MANUAL |
|---|---|---|---|---|
| `_GLOBAL` | 1 | 0 | 0 | 1 |
| `appk` | 14 | 8 | 0 | 6 |
| `byudzhet` | 1 | 1 | 0 | 0 |
| `ekologicheskiy` | 13 | 9 | 0 | 4 |
| `grazhdanskiy` | 57 | 30 | 1 | 26 |
| `koap` | 30 | 16 | 0 | 14 |
| `nalog` | 21 | 16 | 1 | 4 |
| `predprinimatel` | 74 | 38 | 3 | 33 |
| `socialnyy` | 52 | 33 | 1 | 18 |
| `trudovoy` | 27 | 19 | 3 | 5 |
| `ugolovniy` | 37 | 4 | 2 | 31 |
| `upk` | 51 | 48 | 1 | 2 |
| `zemelnyy` | 26 | 12 | 0 | 14 |

## Детальная таблица

| ID | Код | Место | Тип реестра | Статус | Причина | Первый href |
|---|---|---|---|---|---|---|
| `appk_001` | `appk` | пункт 6 статья 38 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K080000095_ | `http://85.202.192.66:9096/rus/docs/K080000095_` |
| `appk_002` | `appk` | пункт 1 статья 81 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2000000350#z647 | `http://85.202.192.66:9096/rus/docs/K2000000350#z647` |
| `appk_003` | `appk` | пункт 1 статья 104-1 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2000000350#z938 | `http://85.202.192.66:9096/rus/docs/K2000000350#z938` |
| `appk_004` | `appk` | подпункт 1) пункт 2 статья 111 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `appk_005` | `appk` | пункт 1 статья 115 | INTERNAL_LINK_MISSING_SECTION_OR_PARAGRAPH | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2000000350#z1068 | `http://85.202.192.66:9096/rus/docs/K2000000350#z1068` |
| `appk_006` | `appk` | пункт 8 статья 131 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `appk_007` | `appk` | подпункт 10) пункт 2 статья 138 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `appk_008` | `appk` | пункт 3 статья 149 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `appk_009` | `appk` | статья 162 | INTERNAL_LINK_MISSING_SECTION_OR_PARAGRAPH | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2000000350#z928 | `http://85.202.192.66:9096/rus/docs/K2000000350#z928` |
| `appk_010` | `appk` | пункт 3 статья 164 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2000000350#z938 | `http://85.202.192.66:9096/rus/docs/K2000000350#z938` |
| `appk_011` | `appk` | пункт 4 статья 164 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/Z950002464_#z1 | `https://adilet.zan.kz/rus/docs/Z950002464_#z1` |
| `appk_012` | `appk` | пункт 3-1 статья 169 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K2000000350#z264 | `https://adilet.zan.kz/rus/docs/K2000000350#z264` |
| `byudzhet_001` | `byudzhet` | пункт 1 статья 115 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1500000438 | `http://85.202.192.66:9096/rus/docs/Z1500000438` |
| `ekologicheskiy_001` | `ekologicheskiy` | пункт 1 статья 20 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1500000401 | `http://85.202.192.66:9096/rus/docs/Z1500000401` |
| `ekologicheskiy_002` | `ekologicheskiy` | подпункт 3) пункт 3 статья 20 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1300000094 | `http://85.202.192.66:9096/rus/docs/Z1300000094` |
| `ekologicheskiy_003` | `ekologicheskiy` | пункт 2 статья 61 | UNKNOWN | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2100000400#z1024 | `http://85.202.192.66:9096/rus/docs/K2100000400#z1024` |
| `ekologicheskiy_004` | `ekologicheskiy` | пункт 8 статья 69 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2100000400#z852 | `http://85.202.192.66:9096/rus/docs/K2100000400#z852` |
| `ekologicheskiy_005` | `ekologicheskiy` | пункт 2 статья 129 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z050000093_ | `http://85.202.192.66:9096/rus/docs/Z050000093_` |
| `ekologicheskiy_006` | `ekologicheskiy` | пункт 1 статья 176 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ekologicheskiy_007` | `ekologicheskiy` | пункт 8 статья 186 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ekologicheskiy_008` | `ekologicheskiy` | пункт 5 статья 191 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ekologicheskiy_009` | `ekologicheskiy` | пункт 8) статья 255 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z2500000193 | `http://85.202.192.66:9096/rus/docs/Z2500000193` |
| `ekologicheskiy_010` | `ekologicheskiy` | статья 261 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K030000477_ | `http://85.202.192.66:9096/rus/docs/K030000477_` |
| `ekologicheskiy_011` | `ekologicheskiy` | пункт 1 статья 262 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K030000442_ | `http://85.202.192.66:9096/rus/docs/K030000442_` |
| `ekologicheskiy_012` | `ekologicheskiy` | пункт 3 статья 263 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K030000477_ | `http://85.202.192.66:9096/rus/docs/K030000477_` |
| `ekologicheskiy_013` | `ekologicheskiy` | пункт 2 статья 363 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `koap_001` | `koap` | пункт 4 статья 40 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000235#z59h | `http://85.202.192.66:9096/rus/docs/K1400000235#z59h` |
| `koap_002` | `koap` | пункт 1 статья 44 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `koap_003` | `koap` | пункт 2 статья 45 | INTERNAL_LINK_MISSING_ARTICLE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `koap_004` | `koap` | статья 49 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `koap_005` | `koap` | пункт 1 статья 50 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `koap_006` | `koap` | пункт 3 статья 59 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K940001000_ | `http://85.202.192.66:9096/rus/docs/K940001000_` |
| `koap_007` | `koap` | Пункт 2-1 статья 62 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `koap_008` | `koap` | пункт 10 статья 179 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z2200000178 | `http://85.202.192.66:9096/rus/docs/Z2200000178` |
| `koap_009` | `koap` | пункт 16 статья 181 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z2200000178 | `http://85.202.192.66:9096/rus/docs/Z2200000178` |
| `koap_010` | `koap` | пункт 1 статья 211 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z2300000094 | `http://85.202.192.66:9096/rus/docs/Z2300000094` |
| `koap_011` | `koap` | подпункт 1) пункт 1 статья 285 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `koap_012` | `koap` | подпункт 1) пункт 3 статья 285 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `koap_013` | `koap` | статья 349 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `koap_014` | `koap` | пункт 5 статья 356 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `koap_015` | `koap` | пункт 9 статья 356 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `koap_016` | `koap` | пункт 4 статья 401 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z010000143_ | `http://85.202.192.66:9096/rus/docs/Z010000143_` |
| `koap_017` | `koap` | статья 501 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z100000257_#z8 | `http://85.202.192.66:9096/rus/docs/Z100000257_#z8` |
| `koap_018` | `koap` | статья 522 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `koap_019` | `koap` | статья 669 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `koap_020` | `koap` | пункт 1 статья 729 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000235#z251 | `https://adilet.zan.kz/rus/docs/K1400000235#z251` |
| `koap_021` | `koap` | пункт 5 статья 802 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z040000588_ | `http://85.202.192.66:9096/rus/docs/Z040000588_` |
| `koap_022` | `koap` | пункт 1 статья 804 | UNKNOWN | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000235#z486 | `https://adilet.zan.kz/rus/docs/K1400000235#z486` |
| `koap_023` | `koap` | пункт 3 статья 804 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `koap_024` | `koap` | подпункт 1) пункт 3 статья 822 | INTERNAL_LINK_MISSING_SECTION_OR_PARAGRAPH | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000235#z80 | `http://85.202.192.66:9096/rus/docs/K1400000235#z80` |
| `koap_025` | `koap` | пункт 2 статья 829-10 | INTERNAL_LINK_MISSING_SECTION_OR_PARAGRAPH | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000235#z80 | `http://85.202.192.66:9096/rus/docs/K1400000235#z80` |
| `koap_026` | `koap` | пункт 3 статья 870 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z950002529_ | `http://85.202.192.66:9096/rus/docs/Z950002529_` |
| `koap_027` | `koap` | пункт 2 статья 875 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000235#z3079 | `http://85.202.192.66:9096/rus/docs/K1400000235#z3079` |
| `koap_028` | `koap` | пункт 2) статья 889 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000235#z8h | `http://85.202.192.66:9096/rus/docs/K1400000235#z8h` |
| `koap_029` | `koap` | пункт 1 статья 894 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K940001000_ | `http://85.202.192.66:9096/rus/docs/K940001000_` |
| `koap_030` | `koap` | пункт 1 статья 910-1 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_001` | `predprinimatel` | пункт 3 статья 23 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K940001000_ | `http://85.202.192.66:9096/rus/docs/K940001000_` |
| `predprinimatel_002` | `predprinimatel` | пункт 3 стсатья 35 | UNKNOWN | **FAIL_NOT_FOUND** | article 'None' / chapter 'None' not located | `—` |
| `predprinimatel_003` | `predprinimatel` | подпункт 7) пункт 2 статья 38 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_004` | `predprinimatel` | пункт 3 статья 78 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_005` | `predprinimatel` | пункт 2) статья 79-3 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_006` | `predprinimatel` | пункт 3) статья 79-3 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_007` | `predprinimatel` | пункт 2 статья 82 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_008` | `predprinimatel` | пункт 4 статья 82 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_009` | `predprinimatel` | подпункт 2) пункт 2 статья 90-5 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000231 | `http://85.202.192.66:9096/rus/docs/K1400000231` |
| `predprinimatel_010` | `predprinimatel` | пункт 24) статья 90-6 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_011` | `predprinimatel` | пункт 9 статья 95-1 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K940001000_ | `http://85.202.192.66:9096/rus/docs/K940001000_` |
| `predprinimatel_012` | `predprinimatel` | пункт 2 статья 107 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375#z83 | `http://85.202.192.66:9096/rus/docs/K1500000375#z83` |
| `predprinimatel_013` | `predprinimatel` | пункт 2 статья 120 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_014` | `predprinimatel` | пункт 2 статья 129 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_015` | `predprinimatel` | пункт 4 статья 129 | UNKNOWN | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1500000375#z131 | `https://adilet.zan.kz/rus/docs/K1500000375#z131` |
| `predprinimatel_016` | `predprinimatel` | подпункт 3) пункт 4 статья 129 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_017` | `predprinimatel` | подпункт 12) пункт 4 статья 129 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K030000481_ | `http://85.202.192.66:9096/rus/docs/K030000481_` |
| `predprinimatel_018` | `predprinimatel` | пункт 5 статья 129 | UNKNOWN | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1500000375#z131 | `https://adilet.zan.kz/rus/docs/K1500000375#z131` |
| `predprinimatel_019` | `predprinimatel` | пункт 8 статья 129 | UNKNOWN | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1500000375#z131 | `https://adilet.zan.kz/rus/docs/K1500000375#z131` |
| `predprinimatel_020` | `predprinimatel` | пункт 8-1 статья 129 | UNKNOWN | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1500000375#z131 | `https://adilet.zan.kz/rus/docs/K1500000375#z131` |
| `predprinimatel_021` | `predprinimatel` | пункт 9 статья 129 | UNKNOWN | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1500000375#z131 | `https://adilet.zan.kz/rus/docs/K1500000375#z131` |
| `predprinimatel_022` | `predprinimatel` | пункт 11 статья 129 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1500000375#z157 | `https://adilet.zan.kz/rus/docs/K1500000375#z157` |
| `predprinimatel_023` | `predprinimatel` | пункт 13 статья 129 | UNKNOWN | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1500000375#z154 | `https://adilet.zan.kz/rus/docs/K1500000375#z154` |
| `predprinimatel_024` | `predprinimatel` | пункт 14 статья 129 | INTERNAL_LINK_MISSING_SELFREF | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1500000375#z130 | `https://adilet.zan.kz/rus/docs/K1500000375#z130` |
| `predprinimatel_025` | `predprinimatel` | пункт 15 статья 129 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_026` | `predprinimatel` | пункт 15 статья 129 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_027` | `predprinimatel` | пункт 16 статья 129 | UNKNOWN | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1500000375#z131 | `https://adilet.zan.kz/rus/docs/K1500000375#z131` |
| `predprinimatel_028` | `predprinimatel` | пункт 17 статья 129 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_029` | `predprinimatel` | пункт 18 статья 129 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_030` | `predprinimatel` | пункт 18-1 статья 129 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_031` | `predprinimatel` | пункт 19 статья 129 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_032` | `predprinimatel` | пункт 6 статья 131 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_033` | `predprinimatel` | пункт 3 статья 134 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_034` | `predprinimatel` | пункт 4 статья 134 | INTERNAL_LINK_MISSING_SECTION_OR_PARAGRAPH | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375#z1231 | `http://85.202.192.66:9096/rus/docs/K1500000375#z1231` |
| `predprinimatel_035` | `predprinimatel` | пункт 4 статья 144 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_036` | `predprinimatel` | подпункт 8 пункт 5 статья 144 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_037` | `predprinimatel` | пункт 13 статья 144 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_038` | `predprinimatel` | пункт 1 статья 146 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_039` | `predprinimatel` | пункт 10 статья 152 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000231 | `http://85.202.192.66:9096/rus/docs/K1400000231` |
| `predprinimatel_040` | `predprinimatel` | подпункт 6) пункт 1 статья 155 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_041` | `predprinimatel` | пункт 2 статья 157 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000231 | `http://85.202.192.66:9096/rus/docs/K1400000231` |
| `predprinimatel_042` | `predprinimatel` | пункт 5 статья 169 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_043` | `predprinimatel` | пункт 9 статья 192 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_044` | `predprinimatel` | пункт 10 статья 193 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_045` | `predprinimatel` | пункт 3-3 статья 194 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_046` | `predprinimatel` | пункт 4 статья 196 | INTERNAL_LINK_MISSING_ARTICLE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_047` | `predprinimatel` | пункт 5 статья 204 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375#z207 | `http://85.202.192.66:9096/rus/docs/K1500000375#z207` |
| `predprinimatel_048` | `predprinimatel` | пункт 3 статья 217 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375#z216 | `http://85.202.192.66:9096/rus/docs/K1500000375#z216` |
| `predprinimatel_049` | `predprinimatel` | подпункт 1) пункт 2 статья 218 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375#z170h | `http://85.202.192.66:9096/rus/docs/K1500000375#z170h` |
| `predprinimatel_050` | `predprinimatel` | подпункт 2) пункт 2 статья 218 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375#z174 | `http://85.202.192.66:9096/rus/docs/K1500000375#z174` |
| `predprinimatel_051` | `predprinimatel` | подпункт 1) пункт 1 статья 224 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375#z223 | `http://85.202.192.66:9096/rus/docs/K1500000375#z223` |
| `predprinimatel_052` | `predprinimatel` | пункт 1 статья 231 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375#z174 | `http://85.202.192.66:9096/rus/docs/K1500000375#z174` |
| `predprinimatel_053` | `predprinimatel` | статья 232 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375#z93 | `http://85.202.192.66:9096/rus/docs/K1500000375#z93` |
| `predprinimatel_054` | `predprinimatel` | статья 232-1 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375#z93 | `http://85.202.192.66:9096/rus/docs/K1500000375#z93` |
| `predprinimatel_055` | `predprinimatel` | пункт 2) статья 232-1 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_056` | `predprinimatel` | пункт 3 статья 241 | EXTERNAL_LINK_MISSING_CROSSCODE | **FAIL_NOT_FOUND** | None of 1 keys found in article text (first key='налоговым кодексом республики казахстан') | `—` |
| `predprinimatel_057` | `predprinimatel` | пункт 1) статья 277 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `predprinimatel_058` | `predprinimatel` | подпункт 5) пункт 2 статья 281 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_059` | `predprinimatel` | подпункт 3) пункт 4 статья 283-1 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `predprinimatel_060` | `predprinimatel` | подпункт 1) пункт 7 статья 283-1 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `predprinimatel_061` | `predprinimatel` | пункт 5 статья 283-2 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `predprinimatel_062` | `predprinimatel` | пункт 1 статья 283-4 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `predprinimatel_063` | `predprinimatel` | подпункт 2) пункт 2 статья 283-4 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `predprinimatel_064` | `predprinimatel` | пункт 4 статья 283-4 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `predprinimatel_065` | `predprinimatel` | пункт 6 статья 283-4 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `predprinimatel_066` | `predprinimatel` | пункт 7 статья 283-4 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `predprinimatel_067` | `predprinimatel` | пункт 3 статья 295-2 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `predprinimatel_068` | `predprinimatel` | пункт 5 статья 304 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_069` | `predprinimatel` | пункт 1 статья 323 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_070` | `predprinimatel` | подпункт 4) пункт 1 статья 324 | UNKNOWN | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375#z22h | `http://85.202.192.66:9096/rus/docs/K1500000375#z22h` |
| `predprinimatel_071` | `predprinimatel` | пункт 2 статья 324 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `predprinimatel_072` | `predprinimatel` | пункт 3 статья 324 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375#z119h | `http://85.202.192.66:9096/rus/docs/K1500000375#z119h` |
| `predprinimatel_073` | `predprinimatel` | пункт 8 статья 324 | INTERNAL_LINK_MISSING_ARTICLE | **FAIL_NOT_FOUND** | None of 2 keys found in article text (first key='статьи 118 настоящего кодекса') | `—` |
| `predprinimatel_074` | `predprinimatel` | пункт 9 статья 324 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375#z119h | `http://85.202.192.66:9096/rus/docs/K1500000375#z119h` |
| `socialnyy_001` | `socialnyy` | подпункт 36) пункт 1 статья 1 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214#z12988 | `http://85.202.192.66:9096/rus/docs/K2500000214#z12988` |
| `socialnyy_002` | `socialnyy` | подпункт 80) пункт 1 статья 1 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_003` | `socialnyy` | подпункт 119) пункт 1 статья 1 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214#z12988 | `http://85.202.192.66:9096/rus/docs/K2500000214#z12988` |
| `socialnyy_004` | `socialnyy` | пункт 6) статья 12 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_005` | `socialnyy` | подпункт 5) пункт 3 статья 28 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2300000224#z590 | `http://85.202.192.66:9096/rus/docs/K2300000224#z590` |
| `socialnyy_006` | `socialnyy` | пункт 2 статья 78 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_007` | `socialnyy` | подпункт 5) пункт 3 статья 83 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_008` | `socialnyy` | пункт 1 статья 85 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_009` | `socialnyy` | пункт 2 статья 85 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2300000224#z1276 | `http://85.202.192.66:9096/rus/docs/K2300000224#z1276` |
| `socialnyy_010` | `socialnyy` | статья 89 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2300000224#z1326 | `http://85.202.192.66:9096/rus/docs/K2300000224#z1326` |
| `socialnyy_011` | `socialnyy` | подпункт 2) пункт 3 статья 95 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/Z950002676_#z49 | `https://adilet.zan.kz/rus/docs/Z950002676_#z49` |
| `socialnyy_012` | `socialnyy` | пункт 3 статья 101-1 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `socialnyy_013` | `socialnyy` | пункт 4 статья 101-1 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `socialnyy_014` | `socialnyy` | пункт 5 статья 101-1 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `socialnyy_015` | `socialnyy` | статья 102-1 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `socialnyy_016` | `socialnyy` | пункт 3 статья 118 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_017` | `socialnyy` | пункт 3 статья 132 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K2300000224#z1845 | `https://adilet.zan.kz/rus/docs/K2300000224#z1845` |
| `socialnyy_018` | `socialnyy` | подпункт 8) пункт 8 статья 155 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_019` | `socialnyy` | пункт 3 статья 160 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2300000224#z2201 | `http://85.202.192.66:9096/rus/docs/K2300000224#z2201` |
| `socialnyy_020` | `socialnyy` | пункт 2 статья 163 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2300000224#z2416 | `http://85.202.192.66:9096/rus/docs/K2300000224#z2416` |
| `socialnyy_021` | `socialnyy` | пункт 2 статья 164 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2300000224#z1879 | `http://85.202.192.66:9096/rus/docs/K2300000224#z1879` |
| `socialnyy_022` | `socialnyy` | пункт 1 статья 165 | INTERNAL_LINK_MISSING_SECTION_OR_PARAGRAPH | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2300000224#z1434 | `http://85.202.192.66:9096/rus/docs/K2300000224#z1434` |
| `socialnyy_023` | `socialnyy` | пункт 5 статья 177 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2300000224#z2984 | `http://85.202.192.66:9096/rus/docs/K2300000224#z2984` |
| `socialnyy_024` | `socialnyy` | пункт 5 статья 178 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2300000224#z2282 | `http://85.202.192.66:9096/rus/docs/K2300000224#z2282` |
| `socialnyy_025` | `socialnyy` | пункт 3-1 статья 181 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_026` | `socialnyy` | подпункт 2) пункт 1 статья 197 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_027` | `socialnyy` | пункт 3 статья 224 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_028` | `socialnyy` | пункт 2 статья 226 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_029` | `socialnyy` | пункт 8 статья 226 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_030` | `socialnyy` | пункт 9 статья 234 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K2300000224#z2649 | `https://adilet.zan.kz/rus/docs/K2300000224#z2649` |
| `socialnyy_031` | `socialnyy` | пункт 2 статья 237 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K2300000224#z2984 | `https://adilet.zan.kz/rus/docs/K2300000224#z2984` |
| `socialnyy_032` | `socialnyy` | пункт 1 статья 240 | EXTERNAL_LINK_MISSING_LAW | **FAIL_NOT_FOUND** | None of 1 keys found in article text (first key='законом республики казахстан "о гражданстве респуб') | `—` |
| `socialnyy_033` | `socialnyy` | пункт 3 статья 244 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214#z12999 | `http://85.202.192.66:9096/rus/docs/K2500000214#z12999` |
| `socialnyy_034` | `socialnyy` | пункт 1 статья 245 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214#z6907 | `http://85.202.192.66:9096/rus/docs/K2500000214#z6907` |
| `socialnyy_035` | `socialnyy` | пункт 2 статья 245 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_036` | `socialnyy` | пункт 3 статья 245 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214#z6907 | `http://85.202.192.66:9096/rus/docs/K2500000214#z6907` |
| `socialnyy_037` | `socialnyy` | пункт 5 статья 245 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214#z6907 | `http://85.202.192.66:9096/rus/docs/K2500000214#z6907` |
| `socialnyy_038` | `socialnyy` | пункт 7 статья 245 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214#z6907 | `http://85.202.192.66:9096/rus/docs/K2500000214#z6907` |
| `socialnyy_039` | `socialnyy` | подпункт 6) пункт 9 статья 248 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214#z13013 | `http://85.202.192.66:9096/rus/docs/K2500000214#z13013` |
| `socialnyy_040` | `socialnyy` | подпункт 2) пункт 1 статья 249 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `socialnyy_041` | `socialnyy` | подпункт 3) пункт 1 статья 249 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_042` | `socialnyy` | пункт 2 статья 249 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214 | `http://85.202.192.66:9096/rus/docs/K2500000214` |
| `socialnyy_043` | `socialnyy` | пункт 2 статья 251 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_044` | `socialnyy` | пункт 1 статья 254 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_045` | `socialnyy` | пункт 2 статья 254 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2300000224#z3162 | `http://85.202.192.66:9096/rus/docs/K2300000224#z3162` |
| `socialnyy_046` | `socialnyy` | пункт 6 статья 256 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K940001000_ | `http://85.202.192.66:9096/rus/docs/K940001000_` |
| `socialnyy_047` | `socialnyy` | подпункт 2) пункт 6 статья 262 | UNKNOWN | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214#z12512 | `http://85.202.192.66:9096/rus/docs/K2500000214#z12512` |
| `socialnyy_048` | `socialnyy` | подпункт 1) пункт 7 статья 262 | UNKNOWN | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214#z12512 | `http://85.202.192.66:9096/rus/docs/K2500000214#z12512` |
| `trudovoy_001` | `trudovoy` | Подпункт 27 пункта 2 стать 23 | INTERNAL_LINK_MISSING_ARTICLE | **FAIL_NOT_FOUND** | article 'None' / chapter 'None' not located | `—` |
| `trudovoy_002` | `trudovoy` | Подпункт 2 пункта 1 статьи 30 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000414#z51 | `http://85.202.192.66:9096/rus/docs/K1500000414#z51` |
| `trudovoy_003` | `trudovoy` | Подпункты 23, 24 пункта 1 статьи 52 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2300000224 | `http://85.202.192.66:9096/rus/docs/K2300000224` |
| `trudovoy_004` | `trudovoy` | Пункт 1 статьи 65 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000414#z66 | `http://85.202.192.66:9096/rus/docs/K1500000414#z66` |
| `trudovoy_005` | `trudovoy` | Пункт 4 статьи 73 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000414#z86 | `http://85.202.192.66:9096/rus/docs/K1500000414#z86` |
| `trudovoy_006` | `trudovoy` | Пункт 2 статьи 103 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000414#z75 | `http://85.202.192.66:9096/rus/docs/K1500000414#z75` |
| `trudovoy_007` | `trudovoy` | Пункт 4 статьи 127-3 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `trudovoy_008` | `trudovoy` | Пункт 4-1 статьи 133 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000414#z114 | `http://85.202.192.66:9096/rus/docs/K1500000414#z114` |
| `trudovoy_009` | `trudovoy` | Пункт 2 статьи 137-1 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `trudovoy_010` | `trudovoy` | Статья 141 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z2000000321 | `http://85.202.192.66:9096/rus/docs/Z2000000321` |
| `trudovoy_011` | `trudovoy` | Статья 143-1 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1500000410 | `http://85.202.192.66:9096/rus/docs/Z1500000410` |
| `trudovoy_012` | `trudovoy` | Статья 145-1 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `trudovoy_013` | `trudovoy` | Пункт 2 статьи 146-1 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000414#z30 | `http://85.202.192.66:9096/rus/docs/K1500000414#z30` |
| `trudovoy_014` | `trudovoy` | Пункт 4-1 статьи 159 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1500000410 | `http://85.202.192.66:9096/rus/docs/Z1500000410` |
| `trudovoy_015` | `trudovoy` | Подпункт 1) пункта 1 статьи 176 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `trudovoy_016` | `trudovoy` | Пункт 5 статьи 191 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375 | `http://85.202.192.66:9096/rus/docs/K1500000375` |
| `trudovoy_017` | `trudovoy` | Пункт 1 статьи 195 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375 | `http://85.202.192.66:9096/rus/docs/K1500000375` |
| `trudovoy_018` | `trudovoy` | Пункт 2 статьи 195 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000414#z198 | `http://85.202.192.66:9096/rus/docs/K1500000414#z198` |
| `trudovoy_019` | `trudovoy` | Пункт 3 статьи 198 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z2000000349 | `http://85.202.192.66:9096/rus/docs/Z2000000349` |
| `trudovoy_020` | `trudovoy` | Статья 200 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375 | `http://85.202.192.66:9096/rus/docs/K1500000375` |
| `upk_001` | `upk` | пункт 3 статья 32 | UNKNOWN | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226#z2902 | `http://85.202.192.66:9096/rus/docs/K1400000226#z2902` |
| `upk_002` | `upk` | подпункт 5) пункт 1 статья 35 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z192 | `https://adilet.zan.kz/rus/docs/K1400000231#z192` |
| `upk_003` | `upk` | пункт 2 статья 42-1 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z1003 | `https://adilet.zan.kz/rus/docs/K1400000231#z1003` |
| `upk_004` | `upk` | пункт 4 статья 58 | UNKNOWN | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z1420 | `https://adilet.zan.kz/rus/docs/K1400000231#z1420` |
| `upk_005` | `upk` | подпункт 6) пункт 1 статья 61 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z1639 | `https://adilet.zan.kz/rus/docs/K1400000231#z1639` |
| `upk_006` | `upk` | пункт 3 статья 63 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z1646 | `https://adilet.zan.kz/rus/docs/K1400000231#z1646` |
| `upk_007` | `upk` | подпункт 6) пункт 2 статья 65-1 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z583 | `https://adilet.zan.kz/rus/docs/K1400000231#z583` |
| `upk_008` | `upk` | пункт 4 статья 97 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `upk_009` | `upk` | пункт 4 статья 112 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z1090 | `https://adilet.zan.kz/rus/docs/K1400000231#z1090` |
| `upk_010` | `upk` | пункт 2 статья 136 | UNKNOWN | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000226#z432 | `https://adilet.zan.kz/rus/docs/K1400000226#z432` |
| `upk_011` | `upk` | статья 159 | UNKNOWN | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000231#z5088 | `http://85.202.192.66:9096/rus/docs/K1400000231#z5088` |
| `upk_012` | `upk` | статья 187 | UNKNOWN | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_013` | `upk` | статья 191 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_014` | `upk` | пункт 2 статья 192 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_015` | `upk` | подпункт 1) пункт 3 статья 192 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z1646 | `https://adilet.zan.kz/rus/docs/K1400000231#z1646` |
| `upk_016` | `upk` | подпункт 11) пункт 2 статья 193 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000226#z1492 | `https://adilet.zan.kz/rus/docs/K1400000226#z1492` |
| `upk_017` | `upk` | пункт 2 статья 223 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z1890 | `https://adilet.zan.kz/rus/docs/K1400000231#z1890` |
| `upk_018` | `upk` | пункт 1 статья 254 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z1890 | `https://adilet.zan.kz/rus/docs/K1400000231#z1890` |
| `upk_019` | `upk` | пункт 2 статья 254 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z1890 | `https://adilet.zan.kz/rus/docs/K1400000231#z1890` |
| `upk_020` | `upk` | пункт 3 статья 268 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z1890 | `https://adilet.zan.kz/rus/docs/K1400000231#z1890` |
| `upk_021` | `upk` | пункт 12 статья 272 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z5126 | `https://adilet.zan.kz/rus/docs/K1400000231#z5126` |
| `upk_022` | `upk` | глава 38 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_023` | `upk` | статья 298 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_024` | `upk` | пункт 1 статья 298 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_025` | `upk` | пункт 3 статья 299 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000226#z949 | `https://adilet.zan.kz/rus/docs/K1400000226#z949` |
| `upk_026` | `upk` | статья 300 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_027` | `upk` | пункт 1 статья 300 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_028` | `upk` | глава 39 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_029` | `upk` | статья 301 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_030` | `upk` | Пункт 2 статья 302 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_031` | `upk` | Пункт 7 статья 302-1 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000226#z949 | `https://adilet.zan.kz/rus/docs/K1400000226#z949` |
| `upk_032` | `upk` | Пункт 2 статья 303 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_033` | `upk` | статья 305 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_034` | `upk` | пункт 1 статья 305 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z2473 | `https://adilet.zan.kz/rus/docs/K1400000231#z2473` |
| `upk_035` | `upk` | подпункт 2) пункт 1 статья 307 | UNKNOWN | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000226#z447 | `https://adilet.zan.kz/rus/docs/K1400000226#z447` |
| `upk_036` | `upk` | пункт 3 статья 314 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_037` | `upk` | пункт 3) статья 437 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000226#z7 | `https://adilet.zan.kz/rus/docs/K1400000226#z7` |
| `upk_038` | `upk` | пункт 1 статья 471 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z3361 | `https://adilet.zan.kz/rus/docs/K1400000231#z3361` |
| `upk_039` | `upk` | пункт 3 статья 484 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z3444 | `https://adilet.zan.kz/rus/docs/K1400000231#z3444` |
| `upk_040` | `upk` | пункт 2 статья 486 | INTERNAL_LINK_MISSING_ARTICLE | **FAIL_NOT_FOUND** | None of 1 keys found in article text (first key='статье 485 настоящего кодекса') | `—` |
| `upk_041` | `upk` | статья 498-2 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z5492 | `https://adilet.zan.kz/rus/docs/K1400000231#z5492` |
| `upk_042` | `upk` | пункт 4 статья 518 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_043` | `upk` | пункт 1 статья 523 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226#z417 | `http://85.202.192.66:9096/rus/docs/K1400000226#z417` |
| `upk_044` | `upk` | пункт 11) статья 547 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_045` | `upk` | пункт 8 статья 551 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000226 | `http://85.202.192.66:9096/rus/docs/K1400000226` |
| `upk_046` | `upk` | пункт 3-1 статья 551-1 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z3812 | `https://adilet.zan.kz/rus/docs/K1400000231#z3812` |
| `upk_047` | `upk` | пункт 2 статья 552 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z5241 | `https://adilet.zan.kz/rus/docs/K1400000231#z5241` |
| `upk_048` | `upk` | пункт 3 статья 617-5 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000231#z5335 | `http://85.202.192.66:9096/rus/docs/K1400000231#z5335` |
| `upk_049` | `upk` | подпункт 3) пункт 1 статья 629-4 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1400000231#z208 | `http://85.202.192.66:9096/rus/docs/K1400000231#z208` |
| `upk_050` | `upk` | пункт 10 статья 656 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K1400000231#z230 | `https://adilet.zan.kz/rus/docs/K1400000231#z230` |
| `zemelnyy_001` | `zemelnyy` | подпункт 2-3) пункт 3 статья 9 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000375#z234 | `http://85.202.192.66:9096/rus/docs/K1500000375#z234` |
| `zemelnyy_002` | `zemelnyy` | подпункт 10-1) пункт 2 статья 14-1 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `zemelnyy_003` | `zemelnyy` | пункт 3 статья 32 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `zemelnyy_004` | `zemelnyy` | пункт 4 статья 32 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `zemelnyy_005` | `zemelnyy` | подпункт 4) пункт 1 статья 33 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `zemelnyy_006` | `zemelnyy` | пункт 1 статья 36 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K030000442_#z21 | `http://85.202.192.66:9096/rus/docs/K030000442_#z21` |
| `zemelnyy_007` | `zemelnyy` | пункт 6 статья 37 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `zemelnyy_008` | `zemelnyy` | пункт 4 статья 38 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K030000442_#z72 | `https://adilet.zan.kz/rus/docs/K030000442_#z72` |
| `zemelnyy_009` | `zemelnyy` | пункт 5 статья 38 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K030000442_#z47 | `https://adilet.zan.kz/rus/docs/K030000442_#z47` |
| `zemelnyy_010` | `zemelnyy` | пункт 1 статья 42 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `zemelnyy_011` | `zemelnyy` | пункт 3 статья 42 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2100000400 | `http://85.202.192.66:9096/rus/docs/K2100000400` |
| `zemelnyy_012` | `zemelnyy` | статья 43 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `zemelnyy_013` | `zemelnyy` | подпункт 8)  пункт 1 статья 48 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `zemelnyy_014` | `zemelnyy` | пункт 2 статья 49-2 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `zemelnyy_015` | `zemelnyy` | подпункт 3) пункт 2 статья 81 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K030000442_#z103 | `https://adilet.zan.kz/rus/docs/K030000442_#z103` |
| `zemelnyy_016` | `zemelnyy` | подпункт 3) пункт 3 статья 81 | INTERNAL_LINK_MISSING_ARTICLE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `zemelnyy_017` | `zemelnyy` | подпункт 5) пункт 2 статья 84 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `zemelnyy_018` | `zemelnyy` | пункт 2 статья 94 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K030000442_#z103 | `https://adilet.zan.kz/rus/docs/K030000442_#z103` |
| `zemelnyy_019` | `zemelnyy` | подпункт 2) пункт 2 статья 100 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K030000442_#z103 | `https://adilet.zan.kz/rus/docs/K030000442_#z103` |
| `zemelnyy_020` | `zemelnyy` | пункт 4 статья 100 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K030000442_#z100 | `https://adilet.zan.kz/rus/docs/K030000442_#z100` |
| `zemelnyy_021` | `zemelnyy` | пункт 6 статья 100 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K030000442_#z110 | `https://adilet.zan.kz/rus/docs/K030000442_#z110` |
| `zemelnyy_022` | `zemelnyy` | пункт 4 статья 104 | INTERNAL_LINK_MISSING_ARTICLE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `zemelnyy_023` | `zemelnyy` | пункт 1 статья 105 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K030000442_#z191 | `https://adilet.zan.kz/rus/docs/K030000442_#z191` |
| `zemelnyy_024` | `zemelnyy` | пункт 3 статья 127 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `zemelnyy_025` | `zemelnyy` | пункт 5) статья 165 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: https://adilet.zan.kz/rus/docs/K030000442_#z102 | `https://adilet.zan.kz/rus/docs/K030000442_#z102` |
| `nalog_001` | `nalog` | подпункт 1) пункт 3 статья 13 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z080000067_ | `http://85.202.192.66:9096/rus/docs/Z080000067_` |
| `nalog_002` | `nalog` | пункт 2 статья 14 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z080000067_ | `http://85.202.192.66:9096/rus/docs/Z080000067_` |
| `nalog_003` | `nalog` | подпункт 1) пункт 2 статья 15 | EXTERNAL_LINK_MISSING_CROSSCODE | **FAIL_NOT_FOUND** | None of 1 keys found in article text (first key='закон рк о здоровье народа и системе здравоохранен') | `—` |
| `nalog_004` | `nalog` | пункт 1 статья 16 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1500000372 | `http://85.202.192.66:9096/rus/docs/Z1500000372` |
| `nalog_005` | `nalog` | подпункт 1) пункт 1 статья 17 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1400000207 | `http://85.202.192.66:9096/rus/docs/Z1400000207` |
| `nalog_006` | `nalog` | пункт 8) статья 21 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1800000183 | `http://85.202.192.66:9096/rus/docs/Z1800000183` |
| `nalog_007` | `nalog` | пункт 8 статья 43 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1400000176 | `http://85.202.192.66:9096/rus/docs/Z1400000176` |
| `nalog_008` | `nalog` | подпункт 2) пункт 5 статья 44 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2300000224 | `http://85.202.192.66:9096/rus/docs/K2300000224` |
| `nalog_009` | `nalog` | подпункт 10 пункт 2 статья 45 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1400000176 | `http://85.202.192.66:9096/rus/docs/Z1400000176` |
| `nalog_010` | `nalog` | подпункт 7) пункт 3 статья 45 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z2200000178 | `http://85.202.192.66:9096/rus/docs/Z2200000178` |
| `nalog_011` | `nalog` | пункт 2 статья 49 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z030000370_ | `http://85.202.192.66:9096/rus/docs/Z030000370_` |
| `nalog_012` | `nalog` | подпункт 2) пункт 1 статья 275 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z060000167_ | `http://85.202.192.66:9096/rus/docs/Z060000167_` |
| `nalog_013` | `nalog` | подпункт 3) пункт 2 статья 320 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `nalog_014` | `nalog` | подпункт 7) пункт 1 статья 337 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `nalog_015` | `nalog` | подпункт 2) пункт 2 статья 357 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `nalog_016` | `nalog` | подпункт 4) статья 363 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `nalog_017` | `nalog` | подпункт 2) пункт 5 статья 422 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z950002464_#z1 | `http://85.202.192.66:9096/rus/docs/Z950002464_#z1` |
| `nalog_018` | `nalog` | подпункт 10) пункт 1 статья 479 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1600000444 | `http://85.202.192.66:9096/rus/docs/Z1600000444` |
| `nalog_019` | `nalog` | подпункт 12) пункт 1 статья 479 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1400000263 | `http://85.202.192.66:9096/rus/docs/Z1400000263` |
| `nalog_020` | `nalog` | подпункт 1) пункт 9 статья 724 | INTERNAL_LINK_MISSING_SECTION_OR_PARAGRAPH | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214#z6546 | `http://85.202.192.66:9096/rus/docs/K2500000214#z6546` |
| `nalog_021` | `nalog` | пункт 1 статья 820 | INTERNAL_LINK_MISSING_SECTION_OR_PARAGRAPH | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214#z6277 | `http://85.202.192.66:9096/rus/docs/K2500000214#z6277` |
| `grazhdanskiy_001` | `grazhdanskiy` | пункт 1 статья 3 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_002` | `grazhdanskiy` | пункт 1 статья 5 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_003` | `grazhdanskiy` | пункт 1 статья 20-1 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z2200000178 | `http://85.202.192.66:9096/rus/docs/Z2200000178` |
| `grazhdanskiy_004` | `grazhdanskiy` | пункт 2 статья 21 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1400000176 | `http://85.202.192.66:9096/rus/docs/Z1400000176` |
| `grazhdanskiy_005` | `grazhdanskiy` | статья 21-1 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1400000176 | `http://85.202.192.66:9096/rus/docs/Z1400000176` |
| `grazhdanskiy_006` | `grazhdanskiy` | пункт 4 статья 49 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1400000176 | `http://85.202.192.66:9096/rus/docs/Z1400000176` |
| `grazhdanskiy_007` | `grazhdanskiy` | пункт 6 статья 50 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z030000415_ | `http://85.202.192.66:9096/rus/docs/Z030000415_` |
| `grazhdanskiy_008` | `grazhdanskiy` | статья 52 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1400000176 | `http://85.202.192.66:9096/rus/docs/Z1400000176` |
| `grazhdanskiy_009` | `grazhdanskiy` | статья 54 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1400000176 | `http://85.202.192.66:9096/rus/docs/Z1400000176` |
| `grazhdanskiy_010` | `grazhdanskiy` | пункт 6 статья 58 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_011` | `grazhdanskiy` | статья 64 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1200000056 | `http://85.202.192.66:9096/rus/docs/Z1200000056` |
| `grazhdanskiy_012` | `grazhdanskiy` | статья 64 (вариант 2) | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1700000062 | `http://85.202.192.66:9096/rus/docs/Z1700000062` |
| `grazhdanskiy_013` | `grazhdanskiy` | пункт 2 статья 74 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_014` | `grazhdanskiy` | статья 78 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_015` | `grazhdanskiy` | статья 82 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z980000220_ | `http://85.202.192.66:9096/rus/docs/Z980000220_` |
| `grazhdanskiy_016` | `grazhdanskiy` | пункт 3 статья 132 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/U950002723_ | `http://85.202.192.66:9096/rus/docs/U950002723_` |
| `grazhdanskiy_017` | `grazhdanskiy` | пункт 1 статья 133 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/U950002723_ | `http://85.202.192.66:9096/rus/docs/U950002723_` |
| `grazhdanskiy_018` | `grazhdanskiy` | пункт 3 статья 139 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z030000461_ | `http://85.202.192.66:9096/rus/docs/Z030000461_` |
| `grazhdanskiy_019` | `grazhdanskiy` | пункт 4 статья 156 | EXTERNAL_LINK_MISSING_LAW | **FAIL_NOT_FOUND** | None of 1 keys found in article text (first key='законом республики казахстан "о противодействии ле') | `—` |
| `grazhdanskiy_020` | `grazhdanskiy` | пункт 7 статья 157-1 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_021` | `grazhdanskiy` | пункт 8 статья 159 | INTERNAL_LINK_MISSING_ARTICLE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_022` | `grazhdanskiy` | пункт 12 статья 159 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_023` | `grazhdanskiy` | пункт 2 статья 162 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_024` | `grazhdanskiy` | пункт 1 статья 171 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_025` | `grazhdanskiy` | пункт 3 статья 178 | INTERNAL_LINK_MISSING_ARTICLE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_026` | `grazhdanskiy` | подпункт 6) пункт 1 статья 182 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z2300000021 | `http://85.202.192.66:9096/rus/docs/Z2300000021` |
| `grazhdanskiy_027` | `grazhdanskiy` | пункт 6 статья 192 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K080000095_ | `http://85.202.192.66:9096/rus/docs/K080000095_` |
| `grazhdanskiy_028` | `grazhdanskiy` | пункт 7 статья 192 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K080000095_ | `http://85.202.192.66:9096/rus/docs/K080000095_` |
| `grazhdanskiy_029` | `grazhdanskiy` | пункт 2 статья 196 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K080000095_ | `http://85.202.192.66:9096/rus/docs/K080000095_` |
| `grazhdanskiy_030` | `grazhdanskiy` | пункт 2 статья 202 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_031` | `grazhdanskiy` | пункт 7 статья 209 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z040000576_ | `http://85.202.192.66:9096/rus/docs/Z040000576_` |
| `grazhdanskiy_032` | `grazhdanskiy` | пункт 5 статья 218 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_033` | `grazhdanskiy` | пункт 4 статья 220 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_034` | `grazhdanskiy` | пункт 3 статья 225 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_035` | `grazhdanskiy` | статья 229 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z060000126_ | `http://85.202.192.66:9096/rus/docs/Z060000126_` |
| `grazhdanskiy_036` | `grazhdanskiy` | пункт 5 статья 235 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1600000486 | `http://85.202.192.66:9096/rus/docs/Z1600000486` |
| `grazhdanskiy_037` | `grazhdanskiy` | пункт 2 статья 244 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_038` | `grazhdanskiy` | подпункт 9) пункт 2 статья 249 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_039` | `grazhdanskiy` | подпункт 1) пункт 3 статья 249 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K080000095_ | `http://85.202.192.66:9096/rus/docs/K080000095_` |
| `grazhdanskiy_040` | `grazhdanskiy` | статья 258 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K940001000_#z523 | `http://85.202.192.66:9096/rus/docs/K940001000_#z523` |
| `grazhdanskiy_041` | `grazhdanskiy` | пункт 1 статья 263 | INTERNAL_LINK_MISSING_ARTICLE | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_042` | `grazhdanskiy` | статья 265 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K940001000_#z869 | `http://85.202.192.66:9096/rus/docs/K940001000_#z869` |
| `grazhdanskiy_043` | `grazhdanskiy` | пункт 2 статья 267 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_044` | `grazhdanskiy` | подпункт 2) пункт 2 статья 321 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_045` | `grazhdanskiy` | пункт 1 статья 282 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1600000011 | `http://85.202.192.66:9096/rus/docs/Z1600000011` |
| `grazhdanskiy_046` | `grazhdanskiy` | пункт 2 статья 282 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_047` | `grazhdanskiy` | пункт 2 статья 291 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z970000155_ | `http://85.202.192.66:9096/rus/docs/Z970000155_` |
| `grazhdanskiy_048` | `grazhdanskiy` | пункт 2 статья 318 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/U950002723_ | `http://85.202.192.66:9096/rus/docs/U950002723_` |
| `grazhdanskiy_049` | `grazhdanskiy` | пункт 1 статья 328 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1200000056 | `http://85.202.192.66:9096/rus/docs/Z1200000056` |
| `grazhdanskiy_050` | `grazhdanskiy` | пункт 2-1 статья 328 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z2300000094 | `http://85.202.192.66:9096/rus/docs/Z2300000094` |
| `grazhdanskiy_051` | `grazhdanskiy` | пункт 3 статья 334 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_052` | `grazhdanskiy` | пункт 3 статья 348 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_053` | `grazhdanskiy` | пункт 1-1 статья 380 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1600000486 | `http://85.202.192.66:9096/rus/docs/Z1600000486` |
| `grazhdanskiy_054` | `grazhdanskiy` | пункт 8 статья 390 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1600000486 | `http://85.202.192.66:9096/rus/docs/Z1600000486` |
| `grazhdanskiy_055` | `grazhdanskiy` | статья 400 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_056` | `grazhdanskiy` | подпункт 2) пункт 2 статья 404 | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `grazhdanskiy_057` | `grazhdanskiy` | статья 50 | TOO_MUCH_TEXT_LINKED | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_001` | `ugolovniy` | пункт 1-1 статья 3 | INTERNAL_LINK_MISSING_LIST | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_002` | `ugolovniy` | пункт 3) статья 3 | INTERNAL_LINK_MISSING_LIST | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_003` | `ugolovniy` | подпункт 5) пункт 2 статья 48 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_004` | `ugolovniy` | пункт 3-2 статья 120 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_005` | `ugolovniy` | пункт 3-2 статья 121 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_006` | `ugolovniy` | пункт 4 статья 121 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_007` | `ugolovniy` | пункт 2 статья 150 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_008` | `ugolovniy` | пункт 3 статья 206 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_009` | `ugolovniy` | пункт 3 статья 207 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_010` | `ugolovniy` | пункт 2 статья 249 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_011` | `ugolovniy` | пункт 3 статья 249 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_012` | `ugolovniy` | пункт 2 статья 339 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_013` | `ugolovniy` | пункт 3 статья 339 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_014` | `ugolovniy` | пункт 4 статья 361 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_015` | `ugolovniy` | пункт 2 статья 366 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_016` | `ugolovniy` | пункт 3 статья 366 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_017` | `ugolovniy` | пункт 4 статья 366 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_018` | `ugolovniy` | пункт 4 статья 370 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_019` | `ugolovniy` | пункт 2 статья 392 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_020` | `ugolovniy` | пункт 2 статья 438 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_021` | `ugolovniy` | пункт 3 статья 438 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_022` | `ugolovniy` | пункт 4 статья 438 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_023` | `ugolovniy` | пункт 2 статья 439 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_024` | `ugolovniy` | пункт 3 статья 439 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_025` | `ugolovniy` | пункт 4 статья 439 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_026` | `ugolovniy` | пункт 3 статья 440 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_027` | `ugolovniy` | пункт 4 статья 440 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_028` | `ugolovniy` | пункт 1-1 статья 467 | INTERNAL_LINK_MISSING_SELFREF | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_029` | `ugolovniy` | подпункт 2) пункт 5 статья 48 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_030` | `ugolovniy` | пункт 1 статья 218-1 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z2300000021 | `http://85.202.192.66:9096/rus/docs/Z2300000021` |
| `ugolovniy_031` | `ugolovniy` | пункт 2 статья 218-1 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z2300000021 | `http://85.202.192.66:9096/rus/docs/Z2300000021` |
| `ugolovniy_032` | `ugolovniy` | пункт 4 статья 223 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `ugolovniy_033` | `ugolovniy` | подпункт 2) пункт 4 статья 361 | EXTERNAL_LINK_MISSING_LAW | **FAIL_NOT_FOUND** | None of 1 keys found in article text (first key='законом республики казахстан "об амнистии граждан ') | `—` |
| `ugolovniy_034` | `ugolovniy` | подпункт 4) пункт 3 статья 365 | EXTERNAL_LINK_MISSING_LAW | **FAIL_NOT_FOUND** | None of 1 keys found in article text (first key='законом республики казахстан "об амнистии граждан ') | `—` |
| `ugolovniy_035` | `ugolovniy` | статья 98-1 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1800000131 | `http://85.202.192.66:9096/rus/docs/Z1800000131` |
| `ugolovniy_036` | `ugolovniy` | статья 98-2 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1800000131 | `http://85.202.192.66:9096/rus/docs/Z1800000131` |
| `ugolovniy_037` | `ugolovniy` | статья 3 пункт 1-1 (фото) | UNKNOWN | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `trudovoy_021` | `trudovoy` | пункт 2 статья 146-1 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000414#z30 | `http://85.202.192.66:9096/rus/docs/K1500000414#z30` |
| `trudovoy_022` | `trudovoy` | пункт 4-1 статья 159 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1500000410 | `http://85.202.192.66:9096/rus/docs/Z1500000410` |
| `trudovoy_023` | `trudovoy` | статья 143-1 | EXTERNAL_LINK_MISSING_LAW | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/Z1500000410 | `http://85.202.192.66:9096/rus/docs/Z1500000410` |
| `trudovoy_024` | `trudovoy` | пункт 2 статья 137-1 | EXTERNAL_LINK_MISSING_LAW | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `trudovoy_025` | `trudovoy` | подпункт 41-7) пункт 1 статья 16 | EXTERNAL_LINK_MISSING_LAW | **FAIL_NOT_FOUND** | None of 1 keys found in article text (first key='закон республики казахстан "о персональных данных ') | `—` |
| `trudovoy_026` | `trudovoy` | пункт 1 статья 54 | INTERNAL_LINK_MISSING_ARTICLE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K1500000414#z52 | `http://85.202.192.66:9096/rus/docs/K1500000414#z52` |
| `trudovoy_027` | `trudovoy` | трудовой текст | INTERNAL_LINK_MISSING_SELFREF | **FAIL_NOT_FOUND** | article 'None' / chapter 'None' not located | `—` |
| `socialnyy_049` | `socialnyy` | пункт 5 статья 245 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214#z6907 | `http://85.202.192.66:9096/rus/docs/K2500000214#z6907` |
| `socialnyy_050` | `socialnyy` | пункт 1 статья 245 | TOO_MUCH_TEXT_LINKED | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_051` | `socialnyy` | пункт 10 статья 248 | TOO_MUCH_TEXT_LINKED | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `socialnyy_052` | `socialnyy` | пункт 5 статья 246 | EXTERNAL_LINK_MISSING_CROSSCODE | **PASS** | Linked. First href: http://85.202.192.66:9096/rus/docs/K2500000214#z13013 | `http://85.202.192.66:9096/rus/docs/K2500000214#z13013` |
| `zemelnyy_026` | `zemelnyy` | статья 81 (фото) | TOO_MUCH_TEXT_LINKED | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `appk_013` | `appk` | статья 107 (фото) | TOO_MUCH_TEXT_LINKED | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `appk_014` | `appk` | статья 115 (структура) | ARTICLE_TITLE_NOT_BOLD | **PASS_UNCLASSIFIED** | No keys derived; section has anchors | `—` |
| `_GLOBAL_001` | `_GLOBAL` | все кодексы — заголовки статей | UNKNOWN | **MANUAL_REVIEW** | Global structural remark (article headers boldness check) | `—` |
| `upk_051` | `upk` | ВЕСЬ КОДЕКС | REGRESSION | **MANUAL_REVIEW** | Whole-code regression — covered by per-remark checks | `—` |
