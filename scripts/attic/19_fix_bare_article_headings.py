"""ТЗ-03 ШАГ 2. Точечная починка единственной «сбитой» статьи.

В data/final/grazhdanskiy_structured.html ст.147 имеет заголовок,
завёрнутый в <span class="article-label">…</span> (не жирный). Соседние
статьи кодекса используют семью <h3>. Согласно ТЗ-03, минимальная правка:
заменить span-обёртку на <h3>, текст внутри сохранить.

Якорь z311 (= article-map: 147 → z311) физически уже занят:
  <div class="chapter" data-number="4" data-type="глава" id="w_z311">
    <h3 id="z311"> Глава 4. Сделки Статья 147. Понятие сделки </h3>
Создавать дубликат id="z311" нельзя — это сломает уникальность анкоров.
Поэтому новый <h3> внутри <div data-number="147"> остаётся БЕЗ id, а
пропавший якорь z311 на самом контейнере статьи фиксируется в отчёте
data/reports/TZ05_missing_anchors.json для ТЗ-05.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "data" / "final" / "grazhdanskiy_structured.html"
REPORT = ROOT / "data" / "reports" / "TZ05_missing_anchors.json"

OLD = '<span class="article-label">Статья 147. Понятие сделки</span>'
NEW = '<h3>Статья 147. Понятие сделки</h3>'


def main():
    text = FILE.read_text(encoding="utf-8")
    count = text.count(OLD)
    if count == 1:
        new_text = text.replace(OLD, NEW, 1)
        FILE.write_text(new_text, encoding="utf-8")
        print(f"[ok] {FILE.name}: span.article-label -> <h3>  (st.147)")
    elif count == 0:
        # уже применено или уже было <h3>; убедимся, что <h3> на месте
        if NEW in text:
            print(f"[skip] {FILE.name}: span -> <h3> уже применён ранее.")
        else:
            print(f"[!] target span не найден и нового <h3> тоже нет!")
            return
    else:
        print(f"[!] target span встречается {count} раз — ожидалось 1.")
        return

    # Отчёт для ТЗ-05
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "code": "grazhdanskiy",
        "file": "grazhdanskiy_structured.html",
        "article_number": "147",
        "expected_anchor_per_article_map": "z311",
        "expected_container_anchor": "w_z311",
        "reason_not_applied": (
            "z311 уже занят '<h3 id=\"z311\">' внутри <div class=\"chapter\" "
            "id=\"w_z311\"> — в adilet-источнике заголовок главы 4 и заголовок "
            "ст.147 сидят в одном <h3>. Дубль id создаст коллизию якорей, "
            "поэтому id на новом <h3> ст.147 не выставлен. Решить в рамках "
            "ТЗ-05 (например, перенести z311 с главы на статью + завести "
            "отдельный якорь для главы)."
        ),
    }
    existing = []
    if REPORT.exists():
        try:
            existing = json.loads(REPORT.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []
    # Не дублировать ту же запись
    if not any(e.get("article_number") == "147" and
               e.get("code") == "grazhdanskiy" for e in existing):
        existing.append(record)
    REPORT.write_text(json.dumps(existing, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"[report] записано в {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
