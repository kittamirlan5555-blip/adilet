# Структурные профили source (read-only)

Дубли базовых номеров статей в кодексах РК легальны (статьи «N-1», «N-2» — 
вставные); «дубли» ниже — повтор ПОЛНОГО номера, это аномалия выгрузки.
«дельта_карты» = статей в article_map минус в source: карта строится по
якорям финального файла, расхождение — повод смотреть руками.

| slug | файл | KB | статей | глав | параграфов | пропуски баз | дубли | сноски | в карте | дельта |
|---|---|---|---|---|---|---|---|---|---|---|
| appk | appk.html | 683 | 195 | 31 | 0 | 0 | 0 | 90 | 195 | 0 |
| arbitrazh | arbitrazh.html | 191 | 60 | 8 | 0 | 0 | 0 | 28 | 60 | 0 |
| bezhenci | bezhenci.html | 119 | 22 | 0 | 0 | 0 | 0 | 15 | 22 | 0 |
| byudzhet | byudzhet.html | 1568 | 175 | 33 | 0 | 0 | 2 | 31 | 173 | -2 |
| constitution | constitution.html | 294 | 5 | 0 | 0 | 63 | 0 | 64 | — | — |
| ekologicheskiy | ekologicheskiy.html | 2153 | 419 | 31 | 8 | 0 | 1 | 107 | 418 | -1 |
| gosuslugi | oGosUslug.html | 300 | 43 | 6 | 0 | 0 | 2 | 58 | 41 | -2 |
| goszakup | goszakup.html | 281 | 29 | 5 | 0 | 0 | 0 | 10 | 29 | 0 |
| grazhdanskiy | grazhdanskiy.html | 991 | 424 | 24 | 15 | 1 | 0 | 263 | 425 | 1 |
| grazhdanskiy_osob | GKosobenniy.html | 1557 | 744 | 41 | 45 | 0 | 0 | 279 | 738 | -6 |
| informatizacii | obINFORM.html | 626 | 120 | 13 | 0 | 3 | 32 | 89 | 88 | -32 |
| koap | koap.html | 4207 | 1073 | 56 | 0 | 3 | 1 | 933 | 1072 | -1 |
| mestnoe_upravlenie | mestniySAMOUPRAVLENIE.html | 561 | 64 | 6 | 0 | 0 | 2 | 67 | — | — |
| nalog | nalog.html | 5019 | 852 | 98 | 84 | 0 | 4 | 0 | 848 | -4 |
| notariat | notariat.html | 420 | 126 | 18 | 0 | 11 | 0 | 108 | 126 | 0 |
| obrazovanie | obrazovanie.html | 964 | 89 | 12 | 0 | 0 | 1 | 99 | 88 | -1 |
| ocorrupt | ocorrupt.html | 232 | 33 | 5 | 0 | 0 | 0 | 24 | 33 | 0 |
| persdata | personalDATA.html | 184 | 38 | 6 | 0 | 0 | 0 | 29 | 38 | 0 |
| pravoohranitel | pravoohranitel.html | 595 | 98 | 12 | 0 | 0 | 0 | 99 | 98 | 0 |
| predprinimatel | predprinimatel.html | 1747 | 382 | 36 | 12 | 24 | 3 | 297 | 379 | -3 |
| prezident | prezident.html | 134 | 39 | 0 | 0 | 0 | 0 | 32 | — | — |
| socialnyy | socialnyy.html | 1535 | 272 | 23 | 35 | 0 | 0 | 95 | 272 | 0 |
| trudovoy | trudovoy.html | 875 | 222 | 23 | 0 | 0 | 1 | 164 | 221 | -1 |
| ugolovniy | ugolovniy.html | 1741 | 503 | 18 | 0 | 0 | 1 | 469 | 502 | -1 |
| upk | upk.html | 2974 | 686 | 75 | 0 | 22 | 0 | 441 | 686 | 0 |
| zemelnyy | zemelnyy.html | 1347 | 186 | 21 | 0 | 0 | 0 | 166 | 183 | -3 |
| zhilishniy | zhilishniy.html | 812 | 166 | 20 | 3 | 0 | 0 | 166 | 166 | 0 |

Пропуски базовой нумерации (исключённые статьи — норма для действующих
редакций; перечислены для контроля):

- constitution: 63 → 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33 …
- grazhdanskiy: 1 → 147
- informatizacii: 3 → 45, 46, 47
- koap: 3 → 69, 173, 312
- notariat: 11 → 63, 64, 65, 66, 67, 68, 87, 88, 89, 90, 91
- predprinimatel: 24 → 158, 159, 212, 213, 214, 215, 242, 243, 244, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271
- upk: 22 → 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469
