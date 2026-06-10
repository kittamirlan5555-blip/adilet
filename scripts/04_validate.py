"""
Скрипт 4: Валидация исправленного HTML

Проверяет:
  1. Все <a href="#zN"> ведут на существующий якорь
  2. Нет вложенных <a> внутри <a>
  3. Нет дублирующихся id
  4. Нет текстовых упоминаний статей БЕЗ ссылки (то что мы пропустили)
  5. Сравнивает количество ссылок до и после

Использование:
  python 04_validate.py --original trudovoy.html --fixed trudovoy_fixed.html --map article_map.json
"""

import re
import json
import argparse
from bs4 import BeautifulSoup
from collections import Counter


def load_soup(path: str) -> BeautifulSoup:
    with open(path, "rb") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    for tag in soup.find_all(["script", "style", "template", "veepn-lock-screen"]):
        tag.decompose()
    return soup


def collect_anchors(soup: BeautifulSoup) -> tuple[set, list]:
    """Собирает все якоря и находит дубликаты"""
    anchors = []
    for tag in soup.find_all(True):
        if tag.has_attr("id"):
            anchors.append(tag["id"])
    for a in soup.find_all("a", attrs={"name": True}):
        anchors.append(a["name"])

    seen = set()
    dups = []
    for x in anchors:
        if x in seen:
            dups.append(x)
        seen.add(x)
    return seen, dups


def check_nested_links(soup: BeautifulSoup) -> list:
    """Находит вложенные <a> теги"""
    issues = []
    for a in soup.find_all("a"):
        nested = a.find_all("a")
        if nested:
            issues.append(f"Nested link: {str(a)[:100]}")
    return issues


def check_broken_anchors(soup: BeautifulSoup, anchors: set) -> list:
    """Проверяет что все href="#zN" ведут на существующий якорь"""
    broken = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "#" in href:
            # Извлекаем якорь
            anchor = href.split("#")[-1]
            if anchor and anchor not in anchors:
                broken.append({
                    "href": href,
                    "text": a.get_text(strip=True)[:50],
                    "missing_anchor": anchor
                })
    return broken


def count_remaining_mentions(soup: BeautifulSoup) -> list:
    """
    Считает сколько упоминаний статей осталось без ссылок.
    (для тех что внутри обычного текста, не в заголовках и не в сносках)
    """
    pattern = re.compile(r'\bстать[яиейюёями]+\s+(\d+(?:-\d+)?)\b', re.IGNORECASE)
    remaining = []

    for text_node in soup.find_all(string=True):
        parent = text_node.parent
        if not parent:
            continue
        if parent.name == "a":
            continue

        # Пропускаем заголовки
        is_heading = False
        p = parent
        while p:
            if p.name == "b" and p.find("a", attrs={"name": True}):
                is_heading = True
                break
            if p.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                is_heading = True
                break
            if p.name in ("article", "body"):
                break
            p = p.parent
        if is_heading:
            continue

        # Пропускаем сноски
        is_snoska = False
        p = parent
        while p:
            if p.name == "span" and "note" in (p.get("class") or []):
                is_snoska = True
                break
            if p.name in ("article", "body"):
                break
            p = p.parent
        if is_snoska:
            continue

        txt = str(text_node)
        for m in pattern.finditer(txt):
            remaining.append({
                "match": m.group(0),
                "article": m.group(1),
                "context": txt[max(0, m.start()-20):m.end()+20].strip()
            })

    return remaining


def main():
    ap = argparse.ArgumentParser(description="Валидация исправленного HTML")
    ap.add_argument("--original", help="Оригинальный HTML (для сравнения)")
    ap.add_argument("--fixed", required=True, help="Исправленный HTML")
    ap.add_argument("--map", help="JSON маппинг статья→якорь")
    args = ap.parse_args()

    print("=" * 60)
    print("ВАЛИДАЦИЯ ИСПРАВЛЕННОГО HTML")
    print("=" * 60)

    fixed_soup = load_soup(args.fixed)
    anchors, dup_anchors = collect_anchors(fixed_soup)

    # 1. Дубликаты якорей
    print(f"\n1. Якоря: всего {len(anchors)}, дубликатов: {len(dup_anchors)}")
    if dup_anchors:
        for d in dup_anchors[:5]:
            print(f"   ⚠ Дубликат: {d}")

    # 2. Вложенные ссылки
    nested = check_nested_links(fixed_soup)
    print(f"\n2. Вложенные <a>: {len(nested)}")
    if nested:
        for n in nested[:5]:
            print(f"   ❌ {n}")

    # 3. Битые якоря
    broken = check_broken_anchors(fixed_soup, anchors)
    print(f"\n3. Битые якоря в ссылках: {len(broken)}")
    if broken:
        for b in broken[:10]:
            print(f"   ❌ href={b['href']} text={b['text']} → якорь '{b['missing_anchor']}' не найден")

    # 4. Оставшиеся упоминания без ссылок
    remaining = count_remaining_mentions(fixed_soup)
    print(f"\n4. Упоминания статей без ссылок (в обычном тексте): {len(remaining)}")
    if remaining:
        counter = Counter(r["article"] for r in remaining)
        print(f"   Уникальных статей: {len(counter)}")
        for art, cnt in counter.most_common(10):
            ctx = next(r["context"] for r in remaining if r["article"] == art)
            print(f"   Статья {art}: {cnt} раз. Пример: ...{ctx}...")

    # 5. Сравнение с оригиналом
    if args.original:
        orig_soup = load_soup(args.original)
        orig_links = len(orig_soup.find_all("a", href=True))
        fixed_links = len(fixed_soup.find_all("a", href=True))
        print(f"\n5. Ссылки: было {orig_links} → стало {fixed_links} (добавлено {fixed_links - orig_links})")

    # 6. Маппинг-проверка
    if args.map:
        with open(args.map, "r", encoding="utf-8") as f:
            article_map = json.load(f)
        missing_articles = [r["article"] for r in remaining if r["article"] in article_map]
        not_in_map = [r["article"] for r in remaining if r["article"] not in article_map]
        print(f"\n6. Маппинг: {len(article_map)} статей в маппинге")
        if not_in_map:
            unique_missing = set(not_in_map)
            print(f"   ⚠ Статьи упомянуты но НЕТ в маппинге: {sorted(unique_missing)}")

    # Итог
    print(f"\n{'=' * 60}")
    issues = len(dup_anchors) + len(nested) + len(broken)
    if issues == 0:
        print("✅ Все проверки пройдены!")
    else:
        print(f"⚠ Найдено проблем: {issues}")
    print(f"Оставшиеся упоминания без ссылок: {len(remaining)}")
    print("=" * 60)


if __name__ == "__main__":
    main()