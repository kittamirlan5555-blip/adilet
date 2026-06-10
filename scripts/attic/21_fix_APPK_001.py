"""ТЗ Фаза-2 / APPK-001.

В data/final/appk_structured.html ст.38 п.6 (<p id="z406">) ссылка на
«Бюджетным кодексом Республики Казахстан» идёт на старый doc_id
K080000095_. По codes.json актуальный byudzhet.doc_id = K2500000171.
Все остальные кодексы в data/final/ уже ссылаются на K2500000171
(byudzhet:19, nalog:4, ekologicheskiy:N, …), это единственное место,
где остался старый идентификатор.

Минимальная правка: подменяем doc_id внутри href, остальное не трогаем.
"""
import re
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "data" / "final" / "appk_structured.html"

OLD = '<a href="https://adilet.zan.kz/rus/docs/K080000095_">Бюджетным кодексом Республики Казахстан</a>'
NEW = '<a href="https://adilet.zan.kz/rus/docs/K2500000171">Бюджетным кодексом Республики Казахстан</a>'


def main():
    text = FILE.read_text(encoding="utf-8")
    n = text.count(OLD)
    print(f"совпадений старой ссылки: {n}")
    if n == 0:
        if NEW in text:
            print("уже применено — пропускаю.")
        else:
            print("[!] не найдено ни старой, ни новой формы ссылки")
        return
    if n > 1:
        print(f"[!] ожидался 1 матч, найдено {n}; прерываюсь")
        return
    new_text = text.replace(OLD, NEW, 1)
    FILE.write_text(new_text, encoding="utf-8")
    print("[ok] APPK-001: K080000095_ -> K2500000171")


if __name__ == "__main__":
    main()
