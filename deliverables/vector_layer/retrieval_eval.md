# Ретрив-эвал вектор-слоя (small-to-big)

Модель: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384-dim), индекс faiss (12013 векторов: текст мелких статей + сабчанки с заголовком + summary крупных). «Эталон» запроса — статьи, чей ЗАГОЛОВОК содержит тему.

| запрос | эталон (код/ст.) | топ-3 (код/ст: score, тип) | hit@1 | hit@3 |
|---|---|---|---|---|
| как исчисляется налог на добавленную стоим | nalog/125, nalog/130, nalog/134, nalog/1 | nalog/259:0.85·sub, nalog/480:0.85·sub, nalog/490:0.83·sub | ✅ | ✅ |
| кто признаётся налоговым резидентом респуб | nalog/167, nalog/221, nalog/222, nalog/2 | nalog/221:0.78·art, nalog/359:0.77·art, nalog/693:0.77·sub | ✅ | ✅ |
| ответственность за умышленное причинение с | ugolovniy/100, ugolovniy/101, ugolovniy/ | upk/222:0.73·art, grazhdanskiy_osob/940:0.70·art, grazhdanskiy_osob/941:0.68·art | — | ❌ |
| наказание за кражу чужого имущества | ugolovniy/187, ugolovniy/188 | ugolovniy/189:0.85·sub, ugolovniy/188:0.81·art, ugolovniy/192:0.81·art | — | ✅ |
| ответственность за мошенничество | ugolovniy/187, ugolovniy/190 | koap/439:0.71·art, ocorrupt/24:0.71·sub, ugolovniy/190:0.68·sub | — | ✅ |
| меры пресечения в уголовном процессе | upk/136, upk/137, upk/138, upk/139, upk/ | upk/327:0.83·art, upk/291:0.82·art, upk/341:0.81·art | — | ❌ |
| права подозреваемого при задержании | upk/64 | upk/131:0.84·art, upk/150:0.82·art, upk/133:0.82·art | — | ❌ |
| основания расторжения трудового договора п | trudovoy/50, trudovoy/52, trudovoy/53, t | trudovoy/52:0.86·sub, trudovoy/58:0.82·art, trudovoy/56:0.80·art | ✅ | ✅ |
| ежегодный оплачиваемый трудовой отпуск | trudovoy/95, trudovoy/96 | pravoohranitel/73:0.83·art, trudovoy/95:0.83·art, trudovoy/92:0.80·art | — | ✅ |
| срок исковой давности | grazhdanskiy/162, grazhdanskiy/177, graz | grazhdanskiy/177:0.83·art, grazhdanskiy/185:0.81·art, grazhdanskiy/179:0.80·art | ✅ | ✅ |
| право собственности и его содержание | grazhdanskiy/188, grazhdanskiy/194, graz | grazhdanskiy/188:0.90·sub, grazhdanskiy/199:0.88·art, grazhdanskiy/213:0.87·art | ✅ | ✅ |
| договор купли-продажи товара | grazhdanskiy_osob/406, grazhdanskiy_osob | grazhdanskiy_osob/445:0.75·art, grazhdanskiy_osob/450:0.74·art, grazhdanskiy_osob/406:0.74·art | ✅ | ✅ |
| пенсионные выплаты по возрасту | socialnyy/199, socialnyy/200, socialnyy/ | socialnyy/207:0.86·art, socialnyy/210:0.82·sub, socialnyy/263:0.81·sub | ✅ | ✅ |
| приватизация жилища | zhilishniy/13 | zhilishniy/13:0.81·sub, zhilishniy/98-2:0.67·art, zhilishniy/105:0.66·art | ✅ | ✅ |
| управление объектом кондоминиума | zhilishniy/31, zhilishniy/32, zhilishniy | zhilishniy/2:0.52·sub, zhilishniy/51-4:0.51·sub, zhilishniy/38:0.49·sub | — | ✅ |
| оценка воздействия на окружающую среду | ekologicheskiy/38, ekologicheskiy/64, ek | ekologicheskiy/65:0.86·sub, ekologicheskiy/64:0.82·art, ekologicheskiy/72:0.81·sub | ✅ | ✅ |
| экологический аудит | ekologicheskiy/100, ekologicheskiy/101,  | ekologicheskiy/104:0.76·sub, ekologicheskiy/105:0.76·art, ekologicheskiy/88:0.74·sub | ✅ | ✅ |
| право частной собственности на земельный у | zemelnyy/133, zemelnyy/137, zemelnyy/138 | zemelnyy/47:0.87·sub, zemelnyy/69:0.86·sub, zemelnyy/25:0.86·art | ✅ | ✅ |
| аренда земельного участка и землепользован | zemelnyy/129, zemelnyy/138, zemelnyy/164 | zemelnyy/50:0.79·sub, zemelnyy/78:0.78·sub, grazhdanskiy_osob/520:0.78·art | — | ✅ |
| поступления в республиканский бюджет | byudzhet/120, byudzhet/122, byudzhet/123 | byudzhet/86:0.83·sum, byudzhet/168:0.83·sub, byudzhet/95:0.83·sub | ✅ | ✅ |
| государственная поддержка субъектов малого | predprinimatel/100, predprinimatel/100-1 | predprinimatel/232:0.84·art, predprinimatel/234:0.80·art, predprinimatel/96:0.70·sub | ✅ | ✅ |
| правовой статус педагога | obrazovanie/37-1, obrazovanie/50, obrazo | obrazovanie/51:0.75·sub, obrazovanie/50:0.70·art, obrazovanie/1:0.70·sub | ✅ | ✅ |
| обжалование административного акта в суде | appk/164, appk/168, appk/169, appk/91 | koap/830:0.86·art, upk/415:0.84·art, upk/483:0.82·art | — | ❌ |
| понятие административного акта | appk/1, appk/10, appk/102, appk/103, app | appk/80:0.86·sub, appk/69:0.83·art, appk/167-2:0.82·art | ✅ | ✅ |
| способы осуществления государственных заку | goszakup/10, goszakup/12, goszakup/16 | goszakup/6:0.75·sub, goszakup/16:0.73·sub, goszakup/10:0.72·sub | — | ✅ |
| противодействие коррупции и антикоррупцион | koap/439, koap/680, koap/681, ocorrupt/1 | ocorrupt/18:0.81·art, ocorrupt/5:0.76·art, ocorrupt/23:0.76·art | ✅ | ✅ |
| защита персональных данных | persdata/10, persdata/11, persdata/12, p | informatizacii/56:0.75·art, persdata/20:0.74·art, persdata/21:0.71·art | — | ✅ |
| порядок назначения акима района | mestnoe_upravlenie/23-1, mestnoe_upravle | mestnoe_upravlenie/38-1:0.69·sub, mestnoe_upravlenie/32:0.69·sub, mestnoe_upravlenie/38:0.67·sub | ✅ | ✅ |

**Итог: hit@1 = 17/28 (61%), hit@3 = 24/28 (86%).**

### Анализ (честно)

Модель — `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (лёгкая, ~34 пасс/с на этом CPU). e5-large качественнее, но через fastembed/ONNX на CPU даёт ~0.8 пасс/с (~4.4 ч на 12k) — оставлена опцией `g_build_index.py --model e5` (для GPU/времени).
Оставшиеся промахи — НЕ дефекты данных: (1) парафразный потолок MiniLM («причинение смерти» не сведено к «Убийство», «меры пресечения» — к дефиниционной статье); (2) меж-кодексное пересечение темы (обжалование есть в КоАП/УПК/АППК — модель путает кодекс); (3) «эталон» = ключ в ЗАГОЛОВКЕ — часть «промахов» это найденные релевантные статьи, где тема в теле, а не в заголовке (напр. «права подозреваемого при задержании» → статьи о правах при задержании, а не дефиниция «Подозреваемый»).

### Примеры ретрива (запрос → статья → payload)

- **«как исчисляется налог на добавленную стоимость»** → nalog/259 (score 0.85); payload: «Статья 259. Вычет налога на добавленную стоимость плательщикам…» (полный текст 2947 симв, uid nalog_z4510)
- **«кто признаётся налоговым резидентом республики казахстан»** → nalog/221 (score 0.78); payload: «Статья 221. Общие положения по налогообложению резидентов и не…» (полный текст 898 симв, uid nalog_z3874)
- **«наказание за кражу чужого имущества»** → ugolovniy/189 (score 0.85); payload: «Статья 188. Кража…» (полный текст 1393 симв, uid ugolovniy_z701)
- **«ответственность за мошенничество»** → koap/439 (score 0.71); payload: «Статья 190. Мошенничество…» (полный текст 2792 симв, uid ugolovniy_z711)
