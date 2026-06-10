"""ТЗ-03. Read-only разведка по заголовкам статей.

Для каждого кода (кроме upk) и обоих файлов (_ready, _structured):

1. Считаем все <div data-type="статья"> → это «контейнеры статей».
2. Внутри каждого контейнера ищем заголовок «Статья N…» (где N = data-number
   контейнера) и определяем, в каком теге он лежит:
     family_b  — текст «Статья N» внутри <b>  (семья A в твоей терминологии)
     family_h3 — текст «Статья N» внутри <h3> (семья B)
     bare      — текст «Статья N» есть в контейнере, но НЕ внутри <h3>/<b>
     none      — заголовок вообще не нашёлся (нетипично, отметим отдельно)
3. По большинству выбираем доминирующую семью кода.
4. «Сбитые» = статьи, у которых заголовок есть, но он НЕ в доминирующей
   обёртке и НЕ в альтернативной (т.е. совсем не жирный).
   Если статья в альтернативной обёртке (всё-таки жирный, но другой стиль) —
   не считаем сбитой, но отметим в отдельной колонке.

Скрипт ничего не пишет.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
CODES = ROOT / "config" / "codes.json"

# «Статья N.» в начале текстового потока — N = data-number из родителя.
def heading_re(n: str):
    return re.compile(r'^\s*Статья\s+' + re.escape(str(n)) + r'\b')


def first_visible_text(tag, max_len=300):
    """Конкатенирует первые видимые текстовые узлы внутри tag (в порядке
    document-order), пока не наберётся max_len символов или они не кончатся."""
    out = []
    total = 0
    for d in tag.descendants:
        if isinstance(d, NavigableString):
            s = str(d)
            out.append(s)
            total += len(s)
            if total >= max_len:
                break
    return "".join(out)


def find_heading_wrapper(article_div):
    """Возвращает кортеж (family, wrapper_tag_or_None).
    family ∈ {'b', 'h3', 'bare', 'none'}.
    Поиск: ищем первый Tag-потомок (b или h3), чей видимый текст в начале
    содержит 'Статья <N>'. Если такого нет — пробуем найти 'Статья <N>'
    как plain-text в контейнере и помечаем bare; если и его нет — none."""
    n = article_div.get("data-number", "")
    if not n:
        return "none", None
    rx = heading_re(n)

    # 1. Сначала проверим h3-потомков
    for h in article_div.find_all("h3"):
        txt = first_visible_text(h, 200)
        if rx.match(txt):
            return "h3", h

    # 2. Затем b-потомков (любой вложенности)
    for b in article_div.find_all("b"):
        txt = first_visible_text(b, 200)
        if rx.match(txt):
            return "b", b

    # 3. Иначе ищем по plain-тексту — может быть «голый» заголовок
    txt = first_visible_text(article_div, 600)
    if rx.search(txt):
        return "bare", None
    return "none", None


def audit_file(path: Path):
    text = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(text, "html.parser")
    articles = soup.find_all("div", attrs={"data-type": "статья"})

    by_family = Counter()
    broken_numbers = []   # data-number статей с family=='bare'
    none_numbers = []     # data-number статей, где заголовок не нашёлся
    examples = []         # короткие сниппеты для отчёта

    for div in articles:
        fam, _ = find_heading_wrapper(div)
        by_family[fam] += 1
        n = div.get("data-number", "?")
        if fam == "bare":
            broken_numbers.append(n)
            txt = first_visible_text(div, 200).strip()
            txt = re.sub(r'\s+', ' ', txt)[:160]
            examples.append((n, txt))
        elif fam == "none":
            none_numbers.append(n)

    return {
        "total": len(articles),
        "by_family": by_family,
        "broken_numbers": broken_numbers,
        "none_numbers": none_numbers,
        "examples": examples,
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("codes", nargs="*",
                    help="коды для проверки (пусто = все из codes.json кроме upk)")
    args = ap.parse_args()
    cfg = json.loads(CODES.read_text(encoding="utf-8"))
    if args.codes:
        codes = list(args.codes)
    else:
        codes = [k for k in cfg.keys() if not k.startswith("_") and k != "upk"]

    print(f"{'код':18}{'файл':14}{'total':>7}{'b':>6}{'h3':>5}"
          f"{'bare':>6}{'none':>6}  доминирующая  сбитые")
    print("-" * 100)
    all_examples = defaultdict(list)
    for code in codes:
        per_file = {}
        for suf in ("ready", "structured"):
            p = FINAL / f"{code}_{suf}.html"
            if not p.exists():
                continue
            r = audit_file(p)
            per_file[suf] = r
            fam = r["by_family"]
            dom = "h3" if fam.get("h3", 0) >= fam.get("b", 0) else "b"
            broken = ",".join(r["broken_numbers"]) or "—"
            print(f"{code:18}{suf:14}{r['total']:>7}{fam.get('b',0):>6}"
                  f"{fam.get('h3',0):>5}{fam.get('bare',0):>6}"
                  f"{fam.get('none',0):>6}  {dom:13} {broken}")
            for n, txt in r["examples"]:
                all_examples[(code, suf)].append((n, txt))

    # Подробности по сбитым
    if all_examples:
        print()
        print("=== Сбитые (bare) — фрагменты ===")
        for (code, suf), items in all_examples.items():
            print(f"\n[{code}_{suf}]")
            for n, txt in items:
                print(f"  data-number={n!r}: {txt!r}")
    else:
        print("\n[OK] Сбитых заголовков не найдено.")


if __name__ == "__main__":
    main()
