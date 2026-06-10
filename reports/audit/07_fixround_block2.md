# ФИКС-РАУНД БЛОК 2 — мислинки (03_links_*.json)

Режим: APPLY.

| документ | форма | операция | текст | старый href | новый | вхожд. | резолв-гейт |
|---|---|---|---|---|---|---|---|
| koap | ready | retarget | '368' | `#z1239` | `#z1242` | 1 | PASS |
| koap | ready | retarget | '370' | `#z1246` | `#z1248` | 1 | PASS |
| koap | ready | retarget | '371' | `#z1249` | `#z1253` | 1 | PASS |
| koap | ready | retarget | '375' | `#z1263` | `#z1265` | 1 | PASS |
| koap | ready | retarget | '381' | `#z4780` | `#z1275` | 1 | PASS |
| koap | ready | retarget | '386' | `#z1288` | `#z1290` | 1 | PASS |
| koap | ready | retarget | '388' | `#z1292` | `#z1294` | 1 | PASS |
| koap | ready | unlink | '173' | `#z556` | `(plain)` | 4 | — |
| koap | ready | unlink | '312' | `#z1127` | `(plain)` | 1 | — |
| koap | structured | retarget | '368' | `#z1239` | `#z1242` | 1 | PASS |
| koap | structured | retarget | '370' | `#z1246` | `#z1248` | 1 | PASS |
| koap | structured | retarget | '371' | `#z1249` | `#z1253` | 1 | PASS |
| koap | structured | retarget | '375' | `#z1263` | `#z1265` | 1 | PASS |
| koap | structured | retarget | '381' | `#z4780` | `#z1275` | 1 | PASS |
| koap | structured | retarget | '386' | `#z1288` | `#z1290` | 1 | PASS |
| koap | structured | retarget | '388' | `#z1292` | `#z1294` | 1 | PASS |
| koap | structured | unlink | '173' | `#z556` | `(plain)` | 4 | — |
| koap | structured | unlink | '312' | `#z1127` | `(plain)` | 1 | — |
| zemelnyy | ready | retarget | '44-2' | `#z2002` | `#z2008` | 1 | PASS |
| zemelnyy | structured | retarget | '44-2' | `#z2002` | `#z2008` | 1 | PASS |
| grazhdanskiy_osob | ready | retarget | 'Закона' | `https://adilet.zan.kz/rus/docs/Z970000094_#z152` | `https://adilet.zan.kz/rus/docs/Z970000094_` | 1 | — |
| grazhdanskiy_osob | ready | retarget | 'Социальным кодексом' | `https://adilet.zan.kz/rus/docs/K2300000224#z0` | `https://adilet.zan.kz/rus/docs/K2300000224` | 1 | — |
| grazhdanskiy_osob | structured | retarget | 'Закона' | `https://adilet.zan.kz/rus/docs/Z970000094_#z152` | `https://adilet.zan.kz/rus/docs/Z970000094_` | 1 | — |
| grazhdanskiy_osob | structured | retarget | 'Социальным кодексом' | `https://adilet.zan.kz/rus/docs/K2300000224#z0` | `https://adilet.zan.kz/rus/docs/K2300000224` | 1 | — |
| socialnyy | ready | retarget | 'статьей 9-4' | `#z198` | `https://adilet.zan.kz/rus/docs/Z030000474_` | 1 | — |
| socialnyy | structured | retarget | 'статьей 9-4' | `#z198` | `https://adilet.zan.kz/rus/docs/Z030000474_` | 1 | — |
| nalog | ready | unlink | 'статьи 351-1' | `#z6174` | `(plain)` | 1 | — |
| nalog | structured | unlink | 'статьи 351-1' | `#z6174` | `(plain)` | 1 | — |

**Всего заменённых/снятых вхождений: 34** (вхождений > кейсов: koap 173 встречается 3 раза тем же паром href+текст).

Гейты пер-файл: nows-инвариант (assert), nested=0, double=0.

ОТЛОЖЕНО в Блок 3: grazhdanskiy_osob «статей 151-152» -> якорь ст.151 ГК (статья без якоря, нужна инжекция z151h).
