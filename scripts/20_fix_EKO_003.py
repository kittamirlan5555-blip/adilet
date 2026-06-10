"""ТЗ Фаза-2 / EKO-003.

В data/final/ekologicheskiy_structured.html ст.61 п.2 (<p id="z727">)
сейчас:
    2. Оценка трансграничных воздействий проводится в соответствии с
    параграфом 4 настоящей главы и международными договорами…

«параграфом 4 настоящей главы» — внутренняя ссылка на §4 той же главы.
Параграф 4 в этом файле имеет якорь z1024 (заголовок: «Параграф 4.
Оценка трансграничных воздействий»).

Конвенция файла (см. EKO-004): обёртка покрывает только «параграфом 4»;
«настоящей главы» остаётся вне тега.
"""
import re
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "data" / "final" / "ekologicheskiy_structured.html"

OLD_FRAG = 'параграфом 4 настоящей главы'
NEW_FRAG = '<a href="#z1024">параграфом 4</a> настоящей главы'


def main():
    text = FILE.read_text(encoding="utf-8")
    # Должен быть ровно 1 матч — проверим в контексте <p id="z727">.
    n_total = text.count(OLD_FRAG)
    print(f"всего совпадений 'параграфом 4 настоящей главы' в файле: {n_total}")
    if n_total == 0:
        # возможно, уже починено
        if NEW_FRAG in text:
            print("уже применено — пропускаю.")
            return
        print("[!] фраза не найдена. Прерываюсь.")
        return
    if n_total > 1:
        # уточним: только в <p id="z727">
        p_re = re.compile(r'(<p[^>]*id="z727"[^>]*>.*?</p>)', re.S)
        m = p_re.search(text)
        if not m:
            print("[!] <p id=z727> не найден")
            return
        block = m.group(1)
        if OLD_FRAG not in block:
            print("[!] фраза не внутри z727")
            return
        new_block = block.replace(OLD_FRAG, NEW_FRAG, 1)
        new_text = text[:m.start()] + new_block + text[m.end():]
    else:
        new_text = text.replace(OLD_FRAG, NEW_FRAG, 1)

    FILE.write_text(new_text, encoding="utf-8")
    print(f"[ok] EKO-003 fixed in {FILE.name}")


if __name__ == "__main__":
    main()
