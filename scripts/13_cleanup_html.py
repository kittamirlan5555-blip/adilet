"""
Скрипт 13: Чистка HTML — устраняет вложенные <a> и осиротевшие </a>.

Применяется после всех других обработчиков. Делает:

  1. Вложенные <a> — поднимает внутренний <a> на уровень родителя, разделяя
     внешний на два независимых тега. Если внутренний пустой, удаляется.
     Если внешний тег после разделения пуст — удаляется.

  2. Осиротевшие </a> в исходном тексте (как голая строка) — игнорируются
     парсером html.parser; lxml же их выкидывает. Здесь дополнительно прогоняем
     текст через lxml-парсер и сериализуем заново, чтобы зафиксировать структуру.

  3. <a> без href или с пустым/некорректным href — оставляются как есть; такие
     дефекты в DOM остаются явно видны в валидаторе.

Использование:
    python scripts/13_cleanup_html.py --input data/X_xref.html --output data/X_clean.html
"""

import argparse
import re
from bs4 import BeautifulSoup


def _flatten_nested_anchors(soup):
    """
    Поднимает вложенные <a> на уровень родителя, разделяя внешний.

    Пример:
        <a href="A">left <a href="B">mid</a> right</a>
    превращается в:
        <a href="A">left </a><a href="B">mid</a><a href="A"> right</a>

    Возвращает число обработанных кейсов.
    """
    fixed = 0
    changed = True
    # Цикл повторяется пока есть вложенные — могут быть в несколько слоёв.
    while changed:
        changed = False
        for outer in list(soup.find_all("a")):
            inner_anchors = outer.find_all("a", recursive=False)
            # find_all по children — но <a> может быть и глубже. Берём всех потомков-<a>.
            inner_anchors = outer.find_all("a")
            if not inner_anchors:
                continue
            # Берём ПЕРВЫЙ вложенный
            inner = inner_anchors[0]
            if inner is outer:
                continue
            # Собираем содержимое до inner, сам inner, и после inner
            children = list(outer.children)
            before, after = [], []
            seen_inner = False
            for ch in children:
                # Проверяем что inner находится либо ch, либо внутри ch
                if ch is inner:
                    seen_inner = True
                    continue
                # inner может быть глубже — но в нашем случае выравнивания достаточно
                # сделать обнаружение в первом уровне.
                # Если ch — это контейнер (не <a>), но содержит inner — пропускаем,
                # такое будет обработано на следующей итерации.
                if hasattr(ch, "find") and ch.find(inner.name) is inner:
                    # inner глубже — обработаем на следующем витке
                    seen_inner = True
                    continue
                if not seen_inner:
                    before.append(ch)
                else:
                    after.append(ch)

            if not seen_inner:
                # Inner вложен глубже — попробуем на следующей итерации, выводя его наверх
                # Простейший вариант: перенесём inner на место выше — но рискованно.
                # Делаем точечно: оборачиваем inner в копию outer без вложения.
                # На практике этот путь почти не срабатывает после первого витка.
                inner.unwrap_target = None  # маркер
                # просто прерываем — оставим этот случай, html.parser проявит его в выводе
                continue

            attrs = dict(outer.attrs)

            # Создаём новый left-<a> с before, оставляем inner, создаём right-<a> с after
            new_left = soup.new_tag("a", **attrs) if before else None
            if new_left:
                for c in before:
                    new_left.append(c.extract() if hasattr(c, "extract") else c)
            new_right = soup.new_tag("a", **attrs) if after else None
            if new_right:
                for c in after:
                    new_right.append(c.extract() if hasattr(c, "extract") else c)

            # Заменяем outer последовательностью: left, inner, right
            replacement = []
            if new_left and (new_left.get_text(strip=True) or new_left.contents):
                replacement.append(new_left)
            replacement.append(inner.extract())
            if new_right and (new_right.get_text(strip=True) or new_right.contents):
                replacement.append(new_right)

            # Вставляем элементы перед outer и удаляем outer
            for r in replacement:
                outer.insert_before(r)
            outer.decompose()
            fixed += 1
            changed = True
            break  # начинаем цикл заново
    return fixed


def _remove_orphan_closing(html):
    """
    Убирает осиротевшие </a> которые встречаются СРАЗУ после открывающего блочного
    тега, например: <p></a><a href="...">  — это происходит от прежних некорректных
    замен текстовых узлов.

    Делаем простой эвристический проход:
        1. Считаем баланс <a>/</a>. Если перекос — удаляем лишние </a>.
        2. Удаляем </a> которые НЕ имеют парного открытия слева.
    """
    # Эвристика 1: убираем </a> которые идут сразу после открывающих блочных
    # или инлайн-тегов (включая <b>/<strong>/<span>), которые часто становятся
    # обёрткой заголовков статей. Без этой чистки <p><b></a>… ломает <b> в
    # некоторых парсерах и заголовок «Статья N.» перестаёт быть жирным.
    html = re.sub(
        r'(<(?:p|li|td|div|article|b|strong|span|h[1-6])[^>]*>\s*)</a>',
        r'\1',
        html,
        flags=re.IGNORECASE,
    )
    # Эвристика 2: проходим по строке, поддерживаем стек открытий
    # Балансируем теги: если </a> идёт без соответствующего открытого <a>,
    # удаляем такой </a>. Этого недостаточно для совсем глубоких случаев,
    # но снимает основные грязные точки.
    out = []
    pos = 0
    depth = 0
    open_re = re.compile(r'<a\b[^>]*>', re.IGNORECASE)
    close_re = re.compile(r'</a\s*>', re.IGNORECASE)
    while pos < len(html):
        op = open_re.search(html, pos)
        cl = close_re.search(html, pos)
        if op is None and cl is None:
            out.append(html[pos:])
            break
        if cl is None or (op is not None and op.start() < cl.start()):
            out.append(html[pos:op.end()])
            depth += 1
            pos = op.end()
        else:
            if depth > 0:
                out.append(html[pos:cl.end()])
                depth -= 1
            else:
                # Осиротевшее </a> — пропускаем
                out.append(html[pos:cl.start()])
            pos = cl.end()
    return ''.join(out)


def _normalize_with_lxml(html):
    """
    Прогоняет HTML через lxml-парсер: он автоматически закрывает вложенные <a>
    и нормализует структуру. Возвращает строку.
    """
    soup = BeautifulSoup(html, "lxml")
    # lxml оборачивает в <html><body>; если в исходном этого не было,
    # извлекаем содержимое body
    body = soup.body
    if body is None:
        return str(soup)
    # Преобразуем содержимое <body> в строку
    inner = "".join(str(c) for c in body.children)
    # Возвращаем как есть (DOCTYPE / saved-from-url-комментарий и т.п. lxml сохраняет в html-узле)
    # Проверяем что в исходном был <article> или это обёрнуто
    return inner


def _merge_adjacent_same_doc_links(soup):
    """
    Объединяет идущие подряд <a href="DOC#anchor">…</a> + <a href="DOC">…</a>,
    относящиеся к одному и тому же документу, в одну ссылку. Это даёт пользователю
    «одну объединённую ссылку» для фраз вида «статьёй 40 Закона РК "О…"».

    Условия объединения:
      - Оба <a> ведут на один и тот же doc_id (часть href до '#').
      - Первый имеет якорь (#zN), второй — нет (или тот же).
      - Между ними только пробельный текст.
    Берётся анкор более конкретного (первого) тега, текст склеивается.
    """
    merged = 0

    def split_href(href):
        """Возвращает (doc_id, anchor). doc_id извлекается из URL — это последний
        сегмент пути перед якорем, чтобы старые/новые хосты считались одним документом."""
        if not href:
            return "", ""
        base, _, anchor = href.partition("#")
        # Берём последний сегмент пути после "/docs/" если есть
        doc_id = base
        if "/docs/" in base:
            doc_id = base.split("/docs/", 1)[1].split("/", 1)[0].split("?", 1)[0]
        else:
            doc_id = base.rstrip("/").rsplit("/", 1)[-1]
        return doc_id, anchor

    for a in list(soup.find_all("a", href=True)):
        if not a.parent:
            continue
        base1, anc1 = split_href(a["href"])
        # Ищем непосредственно следующий тег <a> того же документа
        sib = a.next_sibling
        gap_text = ""
        while sib is not None and (isinstance(sib, str) or getattr(sib, "name", None) == "br"):
            if isinstance(sib, str):
                if sib.strip():
                    sib = None
                    break
                gap_text += str(sib)
                sib = sib.next_sibling
                continue
            sib = sib.next_sibling
        if sib is None or getattr(sib, "name", None) != "a" or not sib.get("href"):
            continue
        base2, anc2 = split_href(sib["href"])
        if base1 != base2:
            continue
        # Не объединяем если оба имеют разные якоря (могут быть на разные места)
        if anc1 and anc2 and anc1 != anc2:
            continue
        # Объединяем: контент первого + gap_text + контент второго
        # Анкор — из первого, если есть, иначе из второго
        new_href = a["href"] if anc1 else sib["href"]
        # Переносим содержимое второго в первый
        a["href"] = new_href
        if gap_text:
            a.append(gap_text.replace("\n", " "))
        for c in list(sib.children):
            a.append(c.extract() if hasattr(c, "extract") else c)
        # Удаляем пустые "промежуточные" NavigableString между a и sib
        cur = a.next_sibling
        while cur is not None and cur is not sib:
            nxt = cur.next_sibling
            if isinstance(cur, str) and not cur.strip():
                cur.extract()
            cur = nxt
        sib.decompose()
        merged += 1
    return merged


def cleanup(input_path, output_path):
    with open(input_path, encoding="utf-8") as f:
        html = f.read()

    # Шаг 1: убираем осиротевшие </a> после открытия блочного тега
    html = _remove_orphan_closing(html)

    # Шаг 2: парсим html.parser и поднимаем вложенные <a>
    # (lxml-нормализация ломается на встречающихся в source-файлах <?endif] —
    # IE-conditional остатках, поэтому используем только html.parser).
    soup = BeautifulSoup(html, "html.parser")
    flattened = _flatten_nested_anchors(soup)

    # Шаг 3: объединение соседних ссылок одного документа в одну
    merged = _merge_adjacent_same_doc_links(soup)

    final = str(soup)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final)
    # Подсчёт результата
    opens = len(re.findall(r"<a[^>]*>", final))
    closes = len(re.findall(r"</a>", final))
    nested = len(re.findall(r"<a[^>]+>[^<]{0,200}<a[^>]+>", final))
    print(f"Cleanup: вложенных дополнительно поднято = {flattened}, "
          f"соседних ссылок объединено = {merged}")
    print(f"Итог: opens={opens} closes={closes} delta={opens-closes} nested={nested}")
    print(f"Результат: {output_path}")


def main():
    ap = argparse.ArgumentParser(description="Чистка HTML: вложенные <a>, осиротевшие </a>")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    cleanup(args.input, args.output)


if __name__ == "__main__":
    main()
