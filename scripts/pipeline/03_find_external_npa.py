"""
Скрипт 3: Поиск упоминаний внешних НПА без ссылок

Находит в тексте упоминания:
  - "Закон Республики Казахстан «О ...»"
  - "Кодекс Республики Казахстан" (Уголовный, Гражданский и т.д.)
  - "Конституция Республики Казахстан"

которые НЕ обёрнуты в <a> тег.

Выдаёт CSV-отчёт, который можно вручную проверить и дополнить маппингом на doc_id.
Если передать --npa-map с маппингом, автоматически вставит ссылки.

Использование:
  # Шаг 1: Найти все упоминания (для ручной проверки)
  python 03_find_external_npa.py --input trudovoy.html --output npa_mentions.csv

  # Шаг 2: После того как заполнили маппинг — автофикс
  python 03_find_external_npa.py --input trudovoy.html --npa-map npa_mapping.json --output-html trudovoy_fixed.html
"""

import re
import json
import csv
import argparse
from bs4 import BeautifulSoup, NavigableString


# === ПАТТЕРНЫ ДЛЯ ВНЕШНИХ НПА ===

# "Закон[ом/а/у] Республики Казахстан «О чём-то там»"
# или "Законом Республики Казахстан "О чём-то""
NPA_LAW_PATTERN = re.compile(
    r'(Закон(?:ом|а|у|е|ы)?\s+Республики\s+Казахстан\s+[«"][^»"]+[»"])',
    re.IGNORECASE
)

# "Кодекс[ом/а] Республики Казахстан" (Гражданский/Уголовный/...)
# Обычно перед словом "Кодекс" идёт название: "Уголовно-процессуальный кодекс"
NPA_CODEX_PATTERN = re.compile(
    r'((?:[А-ЯЁа-яё-]+\s+){0,3}[Кк]одекс(?:ом|а|у|е)?\s+Республики\s+Казахстан)',
    re.IGNORECASE
)

# "Конституци[я/ей/и] Республики Казахстан"
NPA_CONSTITUTION_PATTERN = re.compile(
    r'(Конституци[яией]+\s+Республики\s+Казахстан)',
    re.IGNORECASE
)

# "Постановлени[е/ем/я] Правительства РК"
NPA_POSTANOVLENIE_PATTERN = re.compile(
    r'(Постановлени[еяюем]+\s+Правительства\s+Республики\s+Казахстан)',
    re.IGNORECASE
)

ALL_NPA_PATTERNS = [
    ("law", NPA_LAW_PATTERN),
    ("codex", NPA_CODEX_PATTERN),
    ("constitution", NPA_CONSTITUTION_PATTERN),
    ("postanovlenie", NPA_POSTANOVLENIE_PATTERN),
]


def is_inside_link(element):
    parent = element.parent
    while parent:
        if parent.name == "a":
            return True
        parent = parent.parent
    return False


def is_in_snoska(element):
    parent = element.parent
    while parent:
        if parent.name == "span" and "note" in (parent.get("class") or []):
            return True
        if parent.name in ("article", "body"):
            break
        parent = parent.parent
    return False


def find_npa_mentions(html_path: str) -> list[dict]:
    """
    Находит все упоминания НПА в тексте, которые не обёрнуты в ссылки.
    """
    with open(html_path, "rb") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    for tag in soup.find_all(["script", "style", "template", "veepn-lock-screen"]):
        tag.decompose()

    mentions = []

    for text_node in soup.find_all(string=True):
        if is_inside_link(text_node):
            continue
        txt = str(text_node)
        if len(txt.strip()) < 15:
            continue

        in_snoska = is_in_snoska(text_node)

        for npa_type, pattern in ALL_NPA_PATTERNS:
            for m in pattern.finditer(txt):
                mentions.append({
                    "type": npa_type,
                    "match": m.group(1),
                    "context": txt[max(0, m.start()-30):m.end()+30].strip(),
                    "in_snoska": in_snoska,
                    "doc_id": "",  # заполняется вручную или через API
                })

    return mentions


_ZAKON_WORD_RE = re.compile(r'^Закон', re.IGNORECASE)
_LAW_TAIL_RE = re.compile(
    r'^(\s*Республики\s+Казахстан\s+["\u00ab]([^"\u00bb\n]{5,200})["\u00bb])',
    re.IGNORECASE
)


def fix_orphan_zakon_links(soup, base_url: str) -> list:
    """
    Handles the pattern: <a href="...DOCID#anchor">Законом</a> + NavigableString 'Республики Казахстан "О..."'
    Expands the link to cover the full law name, pointing to the root doc (no #anchor).
    """
    changes = []
    for a_tag in list(soup.find_all('a')):
        a_text = a_tag.get_text().strip()
        if not _ZAKON_WORD_RE.match(a_text):
            continue
        href = a_tag.get('href', '')
        if '/docs/' not in href:
            continue
        # Extract doc_id (strip any #anchor)
        doc_id_raw = href.split('/docs/')[-1].split('#')[0].split('?')[0].rstrip('/')
        sib = a_tag.next_sibling
        if not isinstance(sib, NavigableString):
            continue
        tail = str(sib)
        m = _LAW_TAIL_RE.match(tail)
        if not m:
            continue
        law_portion = m.group(1)
        after = tail[m.end():]
        full_text = a_text + law_portion
        new_href = f'{base_url}/rus/docs/{doc_id_raw}'
        new_a = BeautifulSoup(f'<a href="{new_href}">{full_text}</a>', 'html.parser').find('a')
        # Replace sibling text node first, then the <a>
        sib.replace_with(after)
        a_tag.replace_with(new_a)
        changes.append({'zakon': a_text, 'doc_id': doc_id_raw, 'law': m.group(2)[:60]})
    return changes


def fix_npa_links(html_path: str, npa_map: dict, base_url: str) -> tuple:
    """
    Оборачивает упоминания НПА в ссылки используя маппинг.
    npa_map: { "Закон Республики Казахстан «Об акционерных обществах»": "Z030000415", ... }
    """
    with open(html_path, "rb") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    for tag in soup.find_all(["script", "style", "template", "veepn-lock-screen"]):
        tag.decompose()

    changes = []

    # Pass 1: fix orphan <a>Законом</a> + plain text law name pattern
    orphan_changes = fix_orphan_zakon_links(soup, base_url)
    changes.extend(orphan_changes)
    if orphan_changes:
        print(f"  [orphan-zakon] Исправлено: {len(orphan_changes)}")

    # Pass 2: fix plain text NPA mentions
    text_nodes = []
    for text_node in soup.find_all(string=True):
        if is_inside_link(text_node):
            continue
        if len(str(text_node).strip()) < 15:
            continue
        text_nodes.append(text_node)

    # Сортируем фразы по убыванию длины — более длинные/специфичные первыми,
    # чтобы короткие формы не вкладывались внутрь уже завёрнутых длинных.
    sorted_npa = sorted(npa_map.items(), key=lambda kv: len(kv[0]), reverse=True)

    for text_node in text_nodes:
        original = str(text_node)
        # Сегментируем строку: сегменты текста вне <a> чередуются с уже завёрнутыми <a>…</a>.
        # На каждом проходе по новой фразе обрабатываем только «text»-сегменты.
        segments = [("text", original)]
        made_changes = False

        for npa_name, doc_id in sorted_npa:
            if not any(kind == "text" and npa_name in s for kind, s in segments):
                continue
            href = f'{base_url}/rus/docs/{doc_id}'
            link = f'<a href="{href}">{npa_name}</a>'
            new_segments = []
            replaced_here = False
            for kind, s in segments:
                if kind != "text" or npa_name not in s:
                    new_segments.append((kind, s))
                    continue
                # Разбиваем s по вхождениям npa_name: чередуем text-куски и link-куски
                idx = 0
                while True:
                    pos = s.find(npa_name, idx)
                    if pos < 0:
                        new_segments.append(("text", s[idx:]))
                        break
                    if pos > idx:
                        new_segments.append(("text", s[idx:pos]))
                    new_segments.append(("link", link))
                    idx = pos + len(npa_name)
                    replaced_here = True
            if replaced_here:
                segments = new_segments
                made_changes = True
                changes.append({"npa": npa_name, "doc_id": doc_id})

        if made_changes:
            result = "".join(s for _, s in segments)
            new_soup = BeautifulSoup(result, "html.parser")
            text_node.replace_with(new_soup)

    return soup, changes


def main():
    ap = argparse.ArgumentParser(description="Поиск/фикс упоминаний внешних НПА")
    ap.add_argument("--input", required=True, help="HTML-файл кодекса")
    ap.add_argument("--output", default="npa_mentions.csv", help="CSV-отчёт")
    ap.add_argument("--npa-map", help="JSON маппинг название_НПА → doc_id (для автофикса)")
    ap.add_argument("--base-url", default="http://85.202.192.66:9096")
    ap.add_argument("--output-html", help="Выходной HTML с исправленными ссылками")
    args = ap.parse_args()

    if args.npa_map and args.output_html:
        # Режим автофикса
        with open(args.npa_map, "r", encoding="utf-8") as f:
            npa_map = json.load(f)
        soup, changes = fix_npa_links(args.input, npa_map, args.base_url)
        with open(args.output_html, "w", encoding="utf-8") as f:
            f.write(str(soup))
        print(f"Исправлено внешних ссылок: {len(changes)}")
    else:
        # Режим поиска
        mentions = find_npa_mentions(args.input)
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["type", "match", "context", "in_snoska", "doc_id"])
            w.writeheader()
            w.writerows(mentions)
        print(f"Найдено упоминаний НПА: {len(mentions)}")
        print(f"Отчёт: {args.output}")

        # Уникальные НПА
        unique = set(m["match"] for m in mentions if not m["in_snoska"])
        print(f"Уникальных НПА (вне сносок): {len(unique)}")
        for npa in sorted(unique):
            print(f"  - {npa}")


if __name__ == "__main__":
    main()
