"""Фаза-2 / Социальный кодекс. Точечные правки.

1. WRONG (target). В файле 9 ссылок `<a href="#z1505">` с inner-text
   «статьях 101-1» / «статье 101-1» ведут на якорь ст.101 (без -1).
   Меняем на `#z3538` — это якорь ст.101-1. Из 9: 5 — в пунктах чеклиста
   (SOC-006/008/016/026/033a), 4 — в соседних статьях (ст.243/246/248);
   все 9 явно сломаны, чиним все.

2. MISSING. SOC-027 (<p id="z2555">, ст.197 п.1 подп.2)) — «с соблюдением
   условий подпункта 1) пункта 1» не обёрнут. Подп.1) п.1 ст.197 = z2553.
   Оборачиваем строго фразу «подпункта 1) пункта 1» в одну ссылку → z2553.
"""
import re
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "data" / "final" / "socialnyy_structured.html"

# Replace-all правки: меняем только href, inner-текст не трогаем.
ALL_REPLACES = [
    ('<a href="#z1505">статьях 101-1</a>',
     '<a href="#z3538">статьях 101-1</a>',
     5),  # ожидаемых совпадений
    ('<a href="#z1505">статье 101-1</a>',
     '<a href="#z3538">статье 101-1</a>',
     4),
]

# Точечная правка для SOC-027 — уникальный по контексту фрагмент в z2555.
SINGLE_EDITS = [
    ("SOC-027",
     'с соблюдением условий подпункта 1) пункта 1 и <a href="#z2557">пункта 3</a> настоящей статьи.',
     'с соблюдением условий <a href="#z2553">подпункта 1) пункта 1</a> и <a href="#z2557">пункта 3</a> настоящей статьи.'),
]


def main():
    text = FILE.read_text(encoding="utf-8")

    # 1. WRONG fixes
    total_target_fixed = 0
    for old, new, expected in ALL_REPLACES:
        n_before = text.count(old)
        if n_before != expected:
            print(f"[!] '{old[:40]}…' ожидалось {expected}, в файле {n_before}")
        text = text.replace(old, new)
        n_after = text.count(old)
        m1 = re.search(r'#(z\d+)', old).group(1)
        m2 = re.search(r'#(z\d+)', new).group(1)
        replaced = n_before - n_after
        print(f"[ok] href#{m1}->{m2}: заменено {replaced}, осталось {n_after}")
        total_target_fixed += replaced
    print(f"всего target-фиксов: {total_target_fixed}")

    # 2. MISSING fix (SOC-027)
    for label, old, new in SINGLE_EDITS:
        n = text.count(old)
        if n == 1:
            text = text.replace(old, new, 1)
            print(f"[ok] {label}: применено")
        elif n == 0:
            if new in text:
                print(f"[skip] {label}: уже применено")
            else:
                print(f"[!]   {label}: не найдено")
        else:
            print(f"[!]   {label}: {n} совпадений (ожидалось 1)")

    FILE.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
