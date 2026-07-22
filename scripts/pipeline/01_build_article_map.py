"""
Скрипт 1: Строит маппинг номер_статьи → якорь (anchor id)

Парсит HTML кодекса и находит все заголовки статей вида:
  <a name="z1"></a>Статья 1. Основные понятия...
  <b><a name="z99"></a>Статья 99. Оформление привлечения...</b>

Результат: JSON-файл { "1": "z1", "99": "z99", "204": "z204", ... }

Использование:
  python 01_build_article_map.py --input trudovoy.html --output article_map_trudovoy.json
"""

import re
import json
import argparse
from bs4 import BeautifulSoup


def build_article_map(html_path: str) -> dict:
    """
    Находит все <a name="zXXX"> за которыми идёт текст "Статья N."
    Возвращает dict: { "N": "zXXX", ... }
    """
    with open(html_path, "rb") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Убираем мусор
    for tag in soup.find_all(["script", "style", "template", "veepn-lock-screen"]):
        tag.decompose()

    article_map = {}

    # === Способ 1: <a name="zNNN"> + текст "Статья N." (Трудовой кодекс) ===
    for a_tag in soup.find_all("a", attrs={"name": True}):
        anchor = a_tag["name"]
        if not re.match(r'^z\d+', anchor):
            continue

        next_text = ""
        sibling = a_tag.next_sibling
        if sibling:
            if isinstance(sibling, str):
                next_text = sibling.strip()
            elif hasattr(sibling, 'get_text'):
                next_text = sibling.get_text(" ", strip=True)

        if not next_text:
            parent = a_tag.parent
            if parent:
                next_text = parent.get_text(" ", strip=True)

        m = re.search(r'Статья\s+(\d+(?:-\d+)?)\s*\.', next_text)
        if not m:
            # РАЗОРВАННЫЙ заголовок (класс Z070000234_): «Статья 1<b>. </b>Название» —
            # точка в ВЛОЖЕННОМ теге, сосед-текст «Статья 1» БЕЗ точки. Ретрай по
            # родителю (get_text склеит куски: «Статья 1 . Название»); СТРОГО в
            # начале текста родителя — иначе поймаем упоминания «статья N» из тела.
            parent = a_tag.parent
            if parent:
                m = re.match(r'\s*Статья\s+(\d+(?:-\d+)?)\s*\.',
                             parent.get_text(" ", strip=True)[:120])
        if not m:
            # БЕЗ ТОЧКИ И НАЗВАНИЯ (класс Z970000097_ вексель-1997): «<b><a name=z5>
            # Статья 3  </b>» — заголовок = ТОЛЬКО «Статья N». СТРОГО fullmatch по
            # тексту родителя (ин-текст отсылки «статьи N…» в генитиве не пройдут).
            parent = a_tag.parent
            if parent:
                m = re.fullmatch(r'Статья\s+(\d+(?:-\d+)?)',
                                 parent.get_text(" ", strip=True))
        if m:
            article_num = m.group(1)
            if article_num not in article_map:
                article_map[article_num] = anchor

    # === Способ 2: <h3 id="zNNN"> Статья N. ... </h3> (Уголовный кодекс) ===
    for h3_tag in soup.find_all("h3", id=True):
        anchor = h3_tag["id"]
        if not re.match(r'^z\d+', anchor):
            continue

        text = h3_tag.get_text(" ", strip=True)
        m = re.search(r'Статья\s+(\d+(?:-\d+)?)\s*\.', text)
        if m:
            article_num = m.group(1)
            if article_num not in article_map:
                article_map[article_num] = anchor

    # === Способ 3: <p> или <div> с id="zNNN" содержащий "Статья N." ===
    for tag in soup.find_all(["p", "div"], id=True):
        anchor = tag["id"]
        if not re.match(r'^z\d+', anchor):
            continue
        if anchor in [v for v in article_map.values()]:
            continue

        text = tag.get_text(" ", strip=True)[:100]
        m = re.match(r'\s*Статья\s+(\d+(?:-\d+)?)\s*\.', text)
        if m:
            article_num = m.group(1)
            if article_num not in article_map:
                article_map[article_num] = anchor

    # === Способ 4: <p><b>Статья N. ...</b></p> без anchor (КоАП, АППК, УК и т.п.) ===
    # Заголовок есть, но ни <a name>, ни id у обёрток нет. Назначаем
    # синтетический якорь "z<N>h" (h = header). Скрипт 07 затем инжектирует
    # <a id="z<N>h"> в начало <b>.
    for b in soup.find_all("b"):
        btxt = b.get_text(" ", strip=True)
        m = re.match(r"^Статья\s+(\d+(?:-\d+)?)\s*\.", btxt)
        if not m:
            continue
        article_num = m.group(1)
        if article_num in article_map:
            continue
        # Уже есть anchor где-то рядом?
        if b.find("a", attrs={"name": True}) or b.find("a", attrs={"id": True}):
            continue
        # Назначаем синтетический
        synth = f"z{article_num}h"
        article_map[article_num] = synth

    # === Способ 5: <h3>Статья N. ...</h3> БЕЗ id (konstsud, часть ГК/УК/ЗК) ===
    # Заголовок-статья в <h3>, но adilet не дал id (Способ 2 его не поймал).
    # СТРОГО паттерн "Статья N." в начале — НЕ любой <h3> (секционные «Глава…»,
    # «Раздел…», «ПОЛОЖЕНИЯ» НЕ якорим). Аддитивно: только где якоря ещё нет.
    # Скрипт 07 затем инжектирует <a id="z<N>h"> в начало <h3>.
    for h3 in soup.find_all("h3"):
        if h3.get("id"):
            continue  # уже учтён Способом 2
        htxt = h3.get_text(" ", strip=True)
        m = re.match(r"^Статья\s+(\d+(?:-\d+)?)\s*\.", htxt)
        if not m:
            continue
        article_num = m.group(1)
        if article_num in article_map:
            continue
        if h3.find("a", attrs={"name": True}) or h3.find("a", attrs={"id": True}):
            continue
        synth = f"z{article_num}h"
        article_map[article_num] = synth

    return article_map


def main():
    ap = argparse.ArgumentParser(description="Строит маппинг статья→якорь из HTML кодекса")
    ap.add_argument("--input", required=True, help="HTML-файл кодекса")
    ap.add_argument("--output", required=True, help="Выходной JSON-файл")
    args = ap.parse_args()

    article_map = build_article_map(args.input)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(article_map, f, ensure_ascii=False, indent=2)

    print(f"Найдено статей: {len(article_map)}")
    print(f"Маппинг сохранён в: {args.output}")

    # Показать первые 10 для проверки
    for i, (num, anchor) in enumerate(sorted(article_map.items(), key=lambda x: int(x[0].split('-')[0]))):
        if i >= 10:
            print("...")
            break
        print(f"  Статья {num} → #{anchor}")


if __name__ == "__main__":
    main()