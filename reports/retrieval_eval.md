# Ретрив-эвал вектор-слоя (small-to-big)

Модель: `intfloat/multilingual-e5-large` (1024-dim), индекс faiss (17786 векторов: текст мелких статей + сабчанки с заголовком + summary крупных). «Эталон» запроса — статьи, чей ЗАГОЛОВОК содержит тему.

| запрос | эталон (код/ст.) | топ-3 (код/ст: score, тип) | hit@1 | hit@3 |
|---|---|---|---|---|
| как исчисляется налог на добавленную стоим | nalog/125, nalog/130, nalog/134, nalog/1 | nalog/490:0.89·sub, nalog/480:0.89·sub, nalog/484:0.89·sub | ✅ | ✅ |
| кто признаётся налоговым резидентом респуб | nalog/167, nalog/221, nalog/222, nalog/2 | nalog/222:0.87·sub, nalog/233:0.87·art, nalog/226:0.87·sub | ✅ | ✅ |
| ответственность за умышленное причинение с | ugolovniy/100, ugolovniy/101, ugolovniy/ | ugolovniy/112:0.87·art, ugolovniy/106:0.87·art, ugolovniy/104:0.87·art | — | ❌ |
| наказание за кражу чужого имущества | ugolovniy/187, ugolovniy/188 | ugolovniy/189:0.88·sub, ugolovniy/188:0.87·art, ugolovniy/191:0.87·art | — | ✅ |
| ответственность за мошенничество | ugolovniy/187, ugolovniy/190 | grazhdanskiy/359:0.85·art, ugolovniy/190:0.85·sub, koap/211-1:0.85·sub | — | ✅ |
| меры пресечения в уголовном процессе | upk/136, upk/137, upk/138, upk/139, upk/ | UIK/169:0.86·sub, upk/150:0.86·art, appk/123:0.86·art | — | ✅ |
| права подозреваемого при задержании | upk/64 | upk/274:0.86·art, pravoohranitel/15:0.85·sub, upk/150:0.85·art | — | ❌ |
| основания расторжения трудового договора п | trudovoy/50, trudovoy/52, trudovoy/53, t | trudovoy/52:0.92·sub, trudovoy/54:0.90·art, trudovoy/56:0.89·art | ✅ | ✅ |
| ежегодный оплачиваемый трудовой отпуск | trudovoy/95, trudovoy/96 | trudovoy/92:0.90·art, trudovoy/96:0.90·art, trudovoy/95:0.90·art | — | ✅ |
| срок исковой давности | grazhdanskiy/162, grazhdanskiy/177, graz | grazhdanskiy/177:0.92·art, grazhdanskiy/178:0.91·art, nalog/65:0.91·sum | ✅ | ✅ |
| право собственности и его содержание | grazhdanskiy/188, grazhdanskiy/194, graz | grazhdanskiy/188:0.89·sub, grazhdanskiy/191:0.87·art, zemelnyy/21:0.86·art | ✅ | ✅ |
| договор купли-продажи товара | grazhdanskiy_osob/406, grazhdanskiy_osob | grazhdanskiy_osob/446:0.89·art, grazhdanskiy_osob/407:0.89·art, grazhdanskiy_osob/445:0.88·art | ✅ | ✅ |
| пенсионные выплаты по возрасту | socialnyy/199, socialnyy/200, socialnyy/ | socialnyy/210:0.89·sub, socialnyy/202:0.89·sub, socialnyy/211:0.88·art | ✅ | ✅ |
| приватизация жилища | zhilishniy/13 | zhilishniy/13:0.86·sub, zhilishniy/15:0.85·art, zhilishniy/109:0.85·sub | ✅ | ✅ |
| управление объектом кондоминиума | zhilishniy/31, zhilishniy/33, zhilishniy | zhilishniy/51-4:0.89·sub, zhilishniy/47:0.88·art, vodniy/121:0.87·art | ✅ | ✅ |
| оценка воздействия на окружающую среду | ekologicheskiy/38, ekologicheskiy/64, ek | ekologicheskiy/64:0.88·art, ekologicheskiy/65:0.88·sub, ekologicheskiy/66:0.88·sub | ✅ | ✅ |
| экологический аудит | ekologicheskiy/100, ekologicheskiy/101,  | ekologicheskiy/187:0.85·art, ekologicheskiy/47:0.85·art, ekologicheskiy/49:0.84·art | ✅ | ✅ |
| право частной собственности на земельный у | zemelnyy/133, zemelnyy/137, zemelnyy/138 | zemelnyy/12:0.88·sum, zemelnyy/26:0.88·sub, zemelnyy/24:0.87·sub | — | ✅ |
| аренда земельного участка и землепользован | zemelnyy/129, zemelnyy/138, zemelnyy/164 | zemelnyy/43-1:0.87·sub, zemelnyy/64:0.86·sub, zemelnyy/39:0.86·sub | — | ❌ |
| поступления в республиканский бюджет | byudzhet/120, byudzhet/122, byudzhet/123 | byudzhet/23:0.88·sub, byudzhet/168:0.86·sub, byudzhet/24:0.86·sub | ✅ | ✅ |
| государственная поддержка субъектов малого | predprinimatel/100, predprinimatel/100-1 | predprinimatel/232:0.89·art, predprinimatel/92:0.87·art, predprinimatel/91:0.87·art | ✅ | ✅ |
| правовой статус педагога | obrazovanie/37-1, obrazovanie/50, obrazo | obrazovanie/50:0.88·art, obrazovanie/51:0.86·sub, obrazovanie/37-1:0.85·art | ✅ | ✅ |
| обжалование административного акта в суде | appk/164, appk/168, appk/169, appk/91 | koap/830:0.88·art, appk/91:0.88·sub, koap/826-2:0.88·sub | — | ✅ |
| понятие административного акта | appk/1, appk/10, appk/102, appk/103, app | appk/79:0.87·art, appk/83:0.86·art, appk/80:0.86·sub | ✅ | ✅ |
| способы осуществления государственных заку | goszakup/10, goszakup/12, goszakup/16 | goszakup/10:0.90·sub, goszakup/6:0.88·sub, goszakup/16:0.87·sub | ✅ | ✅ |
| противодействие коррупции и антикоррупцион | koap/439, koap/680, koap/681, ocorrupt/1 | ocorrupt/12:0.87·sum, ocorrupt/10:0.86·art, ocorrupt/1:0.86·sub | ✅ | ✅ |
| защита персональных данных | persdata/10, persdata/11, persdata/12, p | persdata/21:0.89·art, persdata/20:0.89·art, persdata/5:0.88·art | ✅ | ✅ |
| порядок назначения акима района | mestnoe_upravlenie/23-1, mestnoe_upravle | mestnoe_upravlenie/32-2:0.89·art, mestnoe_upravlenie/32:0.89·sub, mestnoe_upravlenie/32-1:0.88·art | ✅ | ✅ |

**Итог: hit@1 = 19/28 (68%), hit@3 = 25/28 (89%).**

### Анализ (честно)

Модель — `intfloat/multilingual-e5-large` (лёгкая, ~34 пасс/с на этом CPU). e5-large качественнее, но через fastembed/ONNX на CPU даёт ~0.8 пасс/с (~4.4 ч на 12k) — оставлена опцией `g_build_index.py --model e5` (для GPU/времени).
Оставшиеся промахи — НЕ дефекты данных: (1) парафразный потолок MiniLM («причинение смерти» не сведено к «Убийство», «меры пресечения» — к дефиниционной статье); (2) меж-кодексное пересечение темы (обжалование есть в КоАП/УПК/АППК — модель путает кодекс); (3) «эталон» = ключ в ЗАГОЛОВКЕ — часть «промахов» это найденные релевантные статьи, где тема в теле, а не в заголовке (напр. «права подозреваемого при задержании» → статьи о правах при задержании, а не дефиниция «Подозреваемый»).

### Примеры ретрива (запрос → статья → payload)

- **«как исчисляется налог на добавленную стоимость»** → nalog/490 (score 0.89); payload: «Статья 490. Дополнительная сумма налога на добавленную стоимос…» (полный текст 6626 симв, uid nalog_z8360)
- **«кто признаётся налоговым резидентом республики казахстан»** → nalog/222 (score 0.87); payload: «Статья 222. Физическое лицо – резидент…» (полный текст 3180 симв, uid nalog_z3879)
- **«наказание за кражу чужого имущества»** → ugolovniy/189 (score 0.88); payload: «Статья 188. Кража…» (полный текст 1393 симв, uid ugolovniy_z701)
- **«ответственность за мошенничество»** → grazhdanskiy/359 (score 0.85); payload: «Статья 190. Мошенничество…» (полный текст 2792 симв, uid ugolovniy_z711)
