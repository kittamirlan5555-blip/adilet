"""
Скрипт 08: Исправляет самоссылки на подпункты и добавляет ссылки на подпункты
когда они стоят перед уже существующими ссылками на статьи/пункты.

Использование:
  python 08_fix_selfref_subpoints.py --input data/trudovoy_final.html --output data/trudovoy_final2.html \
    --map data/article_map_trudovoy.json --subpoint-map data/subpoint_map_trudovoy.json --doc-id K1500000414

  python 08_fix_selfref_subpoints.py --input data/ugolovniy_final.html --output data/ugolovniy_final2.html \
    --map data/article_map_ugolovniy.json --subpoint-map data/subpoint_map_ugolovniy.json --doc-id K1400000226 \
    --remove-wrong-links
"""

import re
import json
import argparse
from bs4 import BeautifulSoup, NavigableString

BASE_URL = "https://adilet.zan.kz"

# "подпункт(ами/ом/е/а/у/ах) N), M), ... [пункта P] [настоящего пункта|настоящей статьи]"
SELFREF_RE = re.compile(
    r'(подпункт(?:ами|ом|е|а|у|ах)?)\s+'
    r'(\d+(?:-\d+)?)\)'
    r'((?:\s*,\s*\d+(?:-\d+)?\)|\s+и\s+\d+(?:-\d+)?\))*)'
    r'(\s+пункта\s+(\d+(?:-\d+)?))?'
    r'\s+настоящ(?:его\s+пункта|ей\s+статьи)',
    re.IGNORECASE
)

# "пункт(а/у/е/ом/ами) N настоящей статьи" — самоссылка на пункт
PUNKT_SELFREF_RE = re.compile(
    r'(пункт(?:а|у|е|ом|ами)?)\s+'
    r'(\d+(?:-\d+)?)'
    r'\s+настоящ(?:ей\s+статьи|его\s+(?:Кодекса|раздела|главы))',
    re.IGNORECASE
)

# Текстовый узел заканчивающийся на "подпунктах 2), 3) и 4) " — перед существующей ссылкой
TRAILING_SUBP_RE = re.compile(
    r'(подпункт(?:ами|ом|е|а|у|ах)?)\s+'
    r'(\d+(?:-\d+)?)\)'
    r'((?:\s*,\s*\d+(?:-\d+)?\)|\s+и\s+\d+(?:-\d+)?\))*)'
    r'(\s+пункта\s+(\d+(?:-\d+)?))?'
    r'\s*$',
    re.IGNORECASE
)


def make_link(text, anchor, doc_id):
    return f'<a href="{BASE_URL}/rus/docs/{doc_id}#{anchor}">{text}</a>'


def get_all_nums(first_num, extra_str):
    nums = [first_num]
    nums += re.findall(r'(\d+(?:-\d+)?)\)', extra_str)
    return nums


def build_linked(subp_word, nums, extra_str, art_n, punkt_n, subpoint_map, doc_id):
    """Каждый номер — отдельная ссылка, разделители снаружи тега."""
    parts = [f'{subp_word} ']
    for i, num in enumerate(nums):
        anchor = (subpoint_map.get(f'{art_n}_{punkt_n}_{num}') if punkt_n else None) \
                 or subpoint_map.get(f'{art_n}_{num}')
        if i == 0:
            parts.append(make_link(f'{num})', anchor, doc_id) if anchor else f'{num})')
        else:
            sep_m = re.search(r'((?:\s*,\s*|\s+и\s+))' + re.escape(num) + r'\)', extra_str)
            sep = sep_m.group(1) if sep_m else ', '
            parts.append(sep)
            parts.append(make_link(f'{num})', anchor, doc_id) if anchor else f'{num})')
    return ''.join(parts)


def get_article_num(tag):
    if tag.name == 'p':
        b = tag.find('b')
        if b:
            a = b.find('a', attrs={'name': True})
            if a:
                m = re.match(r'Статья\s+(\d+(?:-\d+)?)\s*\.', b.get_text(' ', strip=True))
                if m:
                    return m.group(1)
    if tag.name == 'h3' and tag.get('id'):
        m = re.match(r'\s*Статья\s+(\d+(?:-\d+)?)\s*\.', tag.get_text(' ', strip=True))
        if m:
            return m.group(1)
    return None


def get_punkt_num(tag):
    text = tag.get_text(' ', strip=True) if hasattr(tag, 'get_text') else ''
    m = re.match(r'^\s*(\d+(?:-\d+)?)\.\s', text)
    return m.group(1) if m else None


def is_in_snoska(node):
    p = node.parent
    while p:
        if p.name == 'span' and 'note' in (p.get('class') or []):
            return True
        if p.name == 'font':
            color = (p.get('color') or '').upper().strip().lstrip('#')
            if color == 'FF0000' and ('ИЗПИ' in p.get_text() or 'РЦПИ' in p.get_text()):
                return True
        if p.name in ('body', 'article'):
            break
        p = p.parent
    return False


def build_punkt_map(soup):
    """Строит маппинг (art_num, punkt_num) -> tag_id для всех пунктов статей."""
    punkt_map = {}
    current_art = None
    for tag in soup.find_all(['p', 'h3', 'h2']):
        art = get_article_num(tag)
        if art:
            current_art = art
            continue
        if not current_art:
            continue
        tag_id = tag.get('id', '')
        if not tag_id:
            continue
        txt = tag.get_text(' ', strip=True)
        m = re.match(r'^\s*(\d+(?:-\d+)?)\.\s', txt)
        if m:
            key = (current_art, m.group(1))
            if key not in punkt_map:
                punkt_map[key] = tag_id
    return punkt_map


def fix_all(html_path, subpoint_map, doc_id, remove_wrong_links=False):
    with open(html_path, 'rb') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    punkt_map = build_punkt_map(soup)

    fixed = 0
    removed = 0
    current_art = None
    current_punkt = None

    for tag in soup.find_all(['p', 'h3', 'h2']):
        art = get_article_num(tag)
        if art:
            current_art = art
            current_punkt = None
            continue
        if not current_art:
            continue
        pn = get_punkt_num(tag)
        if pn:
            current_punkt = pn

        if is_in_snoska(tag):
            continue

        # Обрабатываем все текстовые узлы в теге
        for text_node in list(tag.find_all(string=True)):
            if text_node.parent and text_node.parent.name == 'a':
                continue
            if is_in_snoska(text_node):
                continue

            txt = str(text_node)

            # === Тип 1: самоссылка ("настоящего пункта" / "настоящей статьи") ===
            m = SELFREF_RE.search(txt)
            if m:
                subp_word = m.group(1)
                first_num = m.group(2)
                extra = m.group(3) or ''
                punkt_n = m.group(5) or current_punkt
                nums = get_all_nums(first_num, extra)

                has_any = any(
                    subpoint_map.get(f'{current_art}_{punkt_n}_{n}') or subpoint_map.get(f'{current_art}_{n}')
                    for n in nums
                )
                if not has_any:
                    continue

                linked = build_linked(subp_word, nums, extra, current_art, punkt_n, subpoint_map, doc_id)
                # Составляем результат: до совпадения + linked + остаток совпадения начиная с "пункта N настоящ..."
                before = txt[:m.start()]
                # Хвост: "пункта N настоящего пункта" или "настоящей статьи"
                after_nums_pos = m.start(4) if m.group(4) else m.start() + len(m.group(1)) + 1 + len(m.group(2)) + 1 + len(extra)
                tail = txt[after_nums_pos:]  # " пункта N настоящего пункта..." или " настоящей статьи..."
                after_match = txt[m.end():]
                new_html = before + linked + tail.rstrip() + after_match

                text_node.replace_with(BeautifulSoup(new_html, 'html.parser'))
                fixed += len(nums)
                break

            # === Тип 2: "подпунктах 2), 3) и 4) " перед существующей ссылкой ===
            m2 = TRAILING_SUBP_RE.search(txt)
            if not m2:
                continue

            subp_word = m2.group(1)
            first_num = m2.group(2)
            extra = m2.group(3) or ''
            punkt_ref_full = m2.group(4) or ''  # " пункта N"
            punkt_ref_num = m2.group(5)

            # Определяем статью и пункт из соседних тегов
            art_n = None
            punkt_n = punkt_ref_num or current_punkt

            sib = text_node.next_sibling
            steps = 0
            while sib and art_n is None and steps < 8:
                if getattr(sib, 'name', None) == 'a':
                    sib_text = sib.get_text()
                    href = sib.get('href', '')
                    if re.search(r'стать', sib_text, re.IGNORECASE):
                        am = re.search(r'#z(\d+(?:-\d+)?)$', href)
                        if am:
                            art_n = am.group(1)
                    elif re.search(r'пункт', sib_text, re.IGNORECASE) and not punkt_ref_num:
                        pm = re.search(r'(\d+(?:-\d+)?)', sib_text)
                        if pm:
                            punkt_n = pm.group(1)
                elif isinstance(sib, str) and sib.strip():
                    if re.search(r'настоящ', sib, re.IGNORECASE):
                        art_n = current_art
                        break
                    am = re.search(r'стать\w+\s+(\d+(?:-\d+)?)', sib, re.IGNORECASE)
                    if am:
                        art_n = am.group(1)
                sib = getattr(sib, 'next_sibling', None)
                steps += 1

            if not art_n:
                # Если не нашли статью — пробуем текущую
                art_n = current_art

            nums = get_all_nums(first_num, extra)
            has_any = any(
                subpoint_map.get(f'{art_n}_{punkt_n}_{n}') or subpoint_map.get(f'{art_n}_{n}')
                for n in nums
            )
            if not has_any:
                continue

            before = txt[:m2.start()]
            linked = build_linked(subp_word, nums, extra, art_n, punkt_n, subpoint_map, doc_id)
            # Preserve trailing space from original text if punkt_ref_full is empty
            trailing_space = ' ' if (not punkt_ref_full and txt.endswith(' ')) else ''
            new_html = before + linked + punkt_ref_full + trailing_space

            text_node.replace_with(BeautifulSoup(new_html, 'html.parser'))
            fixed += len(nums)

    # === Тип 4: "пункта N настоящей статьи" — самоссылка на пункт ===
    # Второй проход — после всех замен текстовых узлов выше
    current_art = None
    current_punkt = None
    for tag in soup.find_all(['p', 'h3', 'h2']):
        art = get_article_num(tag)
        if art:
            current_art = art
            current_punkt = None
            continue
        if not current_art:
            continue
        pn = get_punkt_num(tag)
        if pn:
            current_punkt = pn
        if is_in_snoska(tag):
            continue

        for text_node in list(tag.find_all(string=True)):
            if text_node.parent and text_node.parent.name == 'a':
                continue
            if is_in_snoska(text_node):
                continue
            txt = str(text_node)
            m4 = PUNKT_SELFREF_RE.search(txt)
            if not m4:
                continue
            punkt_ref = m4.group(2)
            target = punkt_map.get((current_art, punkt_ref))
            if not target:
                continue
            # Replace just the "пункта N" part with a link, keep the rest
            before = txt[:m4.start()]
            # The match includes "пункта N настоящей статьи"
            # We link "пункта N" and keep " настоящей статьи" as plain text
            punkt_word = m4.group(1)  # "пункта", "пункту", etc.
            linked_punkt = make_link(f'{punkt_word} {punkt_ref}', target, doc_id)
            suffix = txt[m4.start() + len(punkt_word) + 1 + len(punkt_ref):]
            new_html = before + linked_punkt + suffix
            text_node.replace_with(BeautifulSoup(new_html, 'html.parser'))
            fixed += 1
            break

    # === Тип 3: убираем неверные ссылки в УК ===
    if remove_wrong_links:
        # Убираем ссылки вида <a href="...#z1">2</a>) где цифра = номер пункта, не статьи
        # Признак: текст ссылки — одна цифра, рядом "части ... настоящей статьи" или "настоящего"
        for a_tag in list(soup.find_all('a', href=True)):
            href = a_tag.get('href', '')
            am = re.search(r'#z(\d+)$', href)
            if not am:
                continue
            link_text = a_tag.get_text().strip()
            # Ссылка только если текст — цифра и якорь маленький (z1-z30 = статьи 1-30)
            if not re.match(r'^\d{1,2}$', link_text):
                continue
            anchor_num = int(am.group(1))
            if anchor_num > 50:
                continue
            # Контекст: есть ли "настоящей/настоящего" в родительском теге
            parent_text = a_tag.parent.get_text() if a_tag.parent else ''
            if re.search(r'настоящ', parent_text, re.IGNORECASE):
                a_tag.replace_with(a_tag.get_text())
                removed += 1

        print(f'Убрано неверных ссылок: {removed}')

    return soup, fixed, removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--map', required=True)
    ap.add_argument('--subpoint-map', required=True)
    ap.add_argument('--doc-id', required=True)
    ap.add_argument('--remove-wrong-links', action='store_true')
    args = ap.parse_args()

    with open(args.subpoint_map, encoding='utf-8') as f:
        subpoint_map = json.load(f)
    with open(args.map, encoding='utf-8') as f:
        article_map = json.load(f)

    soup, fixed, removed = fix_all(args.input, subpoint_map, args.doc_id, args.remove_wrong_links)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(str(soup))

    print(f'Добавлено ссылок на подпункты: {fixed}')
    print(f'Результат: {args.output}')


if __name__ == '__main__':
    main()
