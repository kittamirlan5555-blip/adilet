"""
Скрипт 09: Целевые исправления УК (ugolovniy_ready.html)

1. z2879 (ст3 п18-1): добавить ссылки на подпункты "пунктом N) части X статьи Y"
2. z2422 (ст72 п3 подп3-1): добавить ссылки "пунктами 1) и 2) части седьмой настоящей статьи"
3. z72_3_4 (ст72 п3 подп4): исправить неверную ссылку #z307 -> z72_7_3
4. z72_4_3 (ст72 п4 подп3): добавить ссылки "пунктами 1) и 2) части седьмой"
5. z72_4_4 (ст72 п4 подп4): добавить ссылку "пунктом 3) части седьмой"
6. z2425 (ст73 п2-1): добавить ссылки "пунктами 2) и 3) части седьмой статьи 72"
7. z388 (ст85 п10): добавить ссылки "пунктами 2) и 4) части первой статьи 84"
8. z426 (ст98 п1): разбить одну ссылку на отдельные ссылки для 3) и 5)
9. z495 (ст120 п4): добавить ссылки на части первой, второй, третьей, пунктом 3) части 3-1, частью 3-2
"""

import re
import json
from bs4 import BeautifulSoup, NavigableString

BASE_URL = "http://85.202.192.66:9096"
DOC_ID = "K1400000226"


def link(text, anchor):
    return f'<a href="{BASE_URL}/rus/docs/{DOC_ID}#{anchor}">{text}</a>'


def fix_uk(html_path, output_path):
    with open(html_path, 'rb') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    fixed_tags = []

    # =========================================================
    # Fix 1: z2879 — добавить ссылки на подпункты
    # "пунктом N) части X статьи Y" -> link to z{art}_{chunk}_{num}
    # =========================================================
    PUNKT_CHAST_FULL_RE = re.compile(
        r'(пункт(?:ом|ами|а|у|е|ах)?)\s+(\d+(?:-\d+)?)\)\s+части\s+(\w+)',
        re.IGNORECASE
    )
    ORDINAL = {
        'первой': '1', 'второй': '2', 'третьей': '3', 'четвертой': '4',
        'пятой': '5', 'шестой': '6', 'седьмой': '7', 'восьмой': '8',
        'девятой': '9', 'десятой': '10'
    }

    with open('data/maps/subpoint_map_ugolovniy.json', encoding='utf-8') as f:
        sub_map = json.load(f)
    with open('data/maps/article_map_ugolovniy.json', encoding='utf-8') as f:
        art_map = json.load(f)
    rev_art = {v: k for k, v in art_map.items()}

    tag_2879 = soup.find(id='z2879')
    if tag_2879:
        # Process each text node in z2879
        for text_node in list(tag_2879.find_all(string=True)):
            if text_node.parent and text_node.parent.name == 'a':
                continue
            txt = str(text_node)
            # Find all "пунктом N) части X" patterns
            matches = list(PUNKT_CHAST_FULL_RE.finditer(txt))
            if not matches:
                continue
            # Find art num from next sibling <a> tag
            next_art_sib = text_node.next_sibling
            steps = 0
            art_anchor = None
            while next_art_sib and steps < 3:
                if hasattr(next_art_sib, 'name') and next_art_sib.name == 'a':
                    href = next_art_sib.get('href', '')
                    am = re.search(r'#(z\d+)$', href)
                    if am:
                        art_anchor = am.group(1)
                    break
                next_art_sib = getattr(next_art_sib, 'next_sibling', None)
                steps += 1
            if not art_anchor:
                continue
            art_num = rev_art.get(art_anchor)
            if not art_num:
                continue

            # Build new HTML with links for each пунктом N)
            new_html = txt
            offset = 0
            result = []
            last_end = 0
            for m in matches:
                chast_num = ORDINAL.get(m.group(3).lower())
                if not chast_num:
                    continue
                subp_num = m.group(2)
                anchor = sub_map.get(f'{art_num}_{chast_num}_{subp_num}')
                if not anchor:
                    continue
                # Add text before match
                result.append(txt[last_end:m.start()])
                # Add linked version: "пунктом N)" stays in link, "части X" stays plain
                result.append(link(f'{m.group(1)} {subp_num})', anchor))
                # Add " части X" as plain text
                result.append(f' части {m.group(3)}')
                last_end = m.end()
            if result:
                result.append(txt[last_end:])
                new_html = ''.join(result)
                text_node.replace_with(BeautifulSoup(new_html, 'html.parser'))
                fixed_tags.append('z2879')

    # =========================================================
    # Fix 2: z2422 — "пунктами 1) и 2) части седьмой настоящей статьи"
    # Add links to z72_7_1, z72_7_2
    # =========================================================
    tag_2422 = soup.find(id='z2422')
    if tag_2422:
        old_html = str(tag_2422)
        new_inner = tag_2422.decode_contents()
        # Pattern: "пунктами 1) и 2) части седьмой настоящей статьи"
        new_inner = re.sub(
            r'пунктами 1\) и 2\) части седьмой настоящей статьи',
            f'пунктами {link("1)", "z72_7_1")} и {link("2)", "z72_7_2")} части седьмой настоящей статьи',
            new_inner
        )
        tag_2422.clear()
        tag_2422.append(BeautifulSoup(new_inner, 'html.parser'))
        fixed_tags.append('z2422')

    # =========================================================
    # Fix 3: z72_3_4 — исправить неверную ссылку #z307 -> z72_7_3
    # =========================================================
    tag_3_4 = soup.find(id='z72_3_4')
    if tag_3_4:
        for a in tag_3_4.find_all('a', href=True):
            if '#z307' in a.get('href', ''):
                a['href'] = a['href'].replace('#z307', '#z72_7_3')
                fixed_tags.append('z72_3_4')
                break

    # =========================================================
    # Fix 4: z72_4_3 — "пунктами 1) и 2) части седьмой"
    # =========================================================
    tag_4_3 = soup.find(id='z72_4_3')
    if tag_4_3:
        new_inner = tag_4_3.decode_contents()
        new_inner = re.sub(
            r'пунктами 1\) и 2\) части седьмой',
            f'пунктами {link("1)", "z72_7_1")} и {link("2)", "z72_7_2")} части седьмой',
            new_inner
        )
        tag_4_3.clear()
        tag_4_3.append(BeautifulSoup(new_inner, 'html.parser'))
        fixed_tags.append('z72_4_3')

    # =========================================================
    # Fix 5: z72_4_4 — "пунктом 3) части седьмой настоящей статьи"
    # =========================================================
    tag_4_4 = soup.find(id='z72_4_4')
    if tag_4_4:
        new_inner = tag_4_4.decode_contents()
        # Check if already a link
        if 'z72_7_3' not in new_inner:
            new_inner = re.sub(
                r'пунктом 3\) части седьмой',
                f'{link("пунктом 3)", "z72_7_3")} части седьмой',
                new_inner
            )
            tag_4_4.clear()
            tag_4_4.append(BeautifulSoup(new_inner, 'html.parser'))
            fixed_tags.append('z72_4_4')

    # =========================================================
    # Fix 6: z2425 — "пунктами 2) и 3) части седьмой статьи 72"
    # =========================================================
    tag_2425 = soup.find(id='z2425')
    if tag_2425:
        new_inner = tag_2425.decode_contents()
        new_inner = re.sub(
            r'пунктами 2\) и 3\) части седьмой',
            f'пунктами {link("2)", "z72_7_2")} и {link("3)", "z72_7_3")} части седьмой',
            new_inner
        )
        tag_2425.clear()
        tag_2425.append(BeautifulSoup(new_inner, 'html.parser'))
        fixed_tags.append('z2425')

    # =========================================================
    # Fix 7: z388 — "пунктами 2) и 4) части первой статьи 84"
    # =========================================================
    tag_388 = soup.find(id='z388')
    if tag_388:
        new_inner = tag_388.decode_contents()
        if 'z84_1_2' not in new_inner:
            new_inner = re.sub(
                r'пунктами 2\) и 4\) части первой',
                f'пунктами {link("2)", "z84_1_2")} и {link("4)", "z84_1_4")} части первой',
                new_inner
            )
            tag_388.clear()
            tag_388.append(BeautifulSoup(new_inner, 'html.parser'))
            fixed_tags.append('z388')

    # =========================================================
    # Fix 8: z426 — разбить одну ссылку "пунктами 3) и 5) части первой статьи 91"
    # на: "пунктами 3) и 5) части первой статьи 91" -> отдельные ссылки
    # =========================================================
    tag_426 = soup.find(id='z426')
    if tag_426:
        # Find the single link that covers entire phrase
        for a in tag_426.find_all('a', href=True):
            a_text = a.get_text()
            if 'пунктами 3) и 5)' in a_text and 'статьи 91' in a_text:
                # Replace with: пунктами {link(3)} и {link(5)} части первой {link(статьи 91)}
                art91_anchor = 'z402'
                new_html = (
                    f'пунктами {link("3)", "z91_1_3")} и {link("5)", sub_map["91_1_5"])}'
                    f' части первой {link("статьи 91", art91_anchor)}'
                )
                a.replace_with(BeautifulSoup(new_html, 'html.parser'))
                fixed_tags.append('z426')
                break

    # =========================================================
    # Fix 9: z495 — "частями первой, второй, третьей, пунктом 3) части 3-1 и частью 3-2"
    # Добавить ссылки на каждую часть и подпункт
    # =========================================================
    tag_495 = soup.find(id='z495')
    if tag_495:
        new_inner = tag_495.decode_contents()
        # Replace "частями первой, второй, третьей, пунктом 3) части 3-1 и частью 3-2 настоящей статьи"
        old_phrase = r'частями первой, второй, третьей, пунктом 3\) части 3-1 и частью 3-2 настоящей статьи'
        new_phrase = (
            f'частями {link("первой", "z490")}, {link("второй", "z2429")}, '
            f'{link("третьей", "z494")}, '
            f'пунктом {link("3)", "z2695")} части {link("3-1", "z2362")} '
            f'и частью {link("3-2", "z2437")} настоящей статьи'
        )
        if re.search(old_phrase, new_inner):
            new_inner = re.sub(old_phrase, new_phrase, new_inner)
            tag_495.clear()
            tag_495.append(BeautifulSoup(new_inner, 'html.parser'))
            fixed_tags.append('z495')

    print(f'Исправлено тегов: {len(fixed_tags)}')
    for t in fixed_tags:
        print(f'  - {t}')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))
    print(f'Результат: {output_path}')


if __name__ == '__main__':
    fix_uk('data/final/ugolovniy_ready.html', 'data/final/ugolovniy_ready.html')
