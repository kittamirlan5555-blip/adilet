"""
Скрипт 07: Добавляет якоря (id) к подпунктам и пунктам внутри статей

Проблема: подпункты "1) текст...", "9) текст..." — просто <p> без id.
Нельзя ссылаться на "подпунктом 9) пункта 1 статьи 52" — нет якоря.

Решение: добавляем id вида:
  - подпункт 9) пункта 1 статьи 52  →  id="z52_1_9"
  - подпункт 3) пункта 2 статьи 52  →  id="z52_2_3"
  - подпункт 9) статьи 48 (если без пункта)  →  id="z48_9"
  - пункт 1) статьи 48 (numbered punkt) →  id="z48_p1"

Формат id: z{статья}_{пункт}_{подпункт}  или  z{статья}_{подпункт}

Использование:
  python 07_add_subpoint_anchors.py --input data/trudovoy.html --output data/trudovoy_anchored.html --map data/article_map_trudovoy.json
  python 07_add_subpoint_anchors.py --input data/ugolovniy.html --output data/ugolovniy_anchored.html --map data/article_map_ugolovniy.json
"""

import re
import json
import argparse
from bs4 import BeautifulSoup, NavigableString, Tag


# Паттерны для определения типа параграфа

# Подпункт: начинается с "N)" или "N-M)" — например "1)", "9)", "4-1)", "13)"
SUBPOINT_RE = re.compile(r'^\s*(\d+(?:-\d+)?)\)\s')

# Пункт: начинается с "N." — например "1.", "2.", "12."
PUNKT_RE = re.compile(r'^\s*(\d+(?:-\d+)?)\.\s')

# Часть (часть первая/вторая...): для УК
CHAST_RE = re.compile(r'^\s*(\d+(?:-\d+)?)\.\s')


def get_article_anchor(tag):
    """Возвращает (номер_статьи, anchor) если тег является заголовком статьи."""
    # Трудовой: <p><b><a name="zN"></a>Статья N. ...</b></p>
    # КоАП после инжекции: <p><b><a id="zNh" name="zNh"></a>Статья N. ...</b></p>
    if tag.name == 'p':
        b = tag.find('b')
        if b:
            a = b.find('a', attrs={'name': True}) or b.find('a', attrs={'id': True})
            if a:
                text = b.get_text(' ', strip=True)
                m = re.match(r'Статья\s+(\d+(?:-\d+)?)\s*\.', text)
                if m:
                    return m.group(1), (a.get('name') or a.get('id'))
    # Уголовный: <h3 id="zN"> Статья N. ...</h3>
    if tag.name == 'h3' and tag.get('id'):
        text = tag.get_text(' ', strip=True)
        m = re.match(r'\s*Статья\s+(\d+(?:-\d+)?)\s*\.', text)
        if m:
            return m.group(1), tag['id']
    return None, None


def inject_synthetic_anchors(soup, article_map):
    """Для статей, у которых в HTML нет <a name>/<id>, инжектируем <a id="z<N>h">.

    Использует синтетические anchor-names из article_map (созданные скриптом 01,
    Способ 4). Возвращает количество инжектированных якорей.
    """
    injected = 0
    # Все <b>Статья N. ...</b> внутри <p>
    for b in soup.find_all('b'):
        btxt = b.get_text(' ', strip=True)
        m = re.match(r'^Статья\s+(\d+(?:-\d+)?)\s*\.', btxt)
        if not m:
            continue
        art_num = m.group(1)
        target_anchor = article_map.get(art_num)
        if not target_anchor:
            continue
        # Если внутри <b> УЖЕ есть <a name|id> с этим anchor — пропускаем
        existing = b.find('a', attrs={'name': True}) or b.find('a', attrs={'id': True})
        if existing:
            continue
        # Только для синтетических anchor (заканчиваются на 'h')
        if not target_anchor.endswith('h'):
            continue
        # Инжектируем <a id="zNh" name="zNh"></a> в начало <b>
        new_anchor = soup.new_tag('a', attrs={'id': target_anchor, 'name': target_anchor})
        b.insert(0, new_anchor)
        injected += 1
    # <h3>Статья N. ...</h3> без id (konstsud и пр.) — СТРОГО паттерн «Статья N.»
    for h3 in soup.find_all('h3'):
        if h3.get('id'):
            continue
        htxt = h3.get_text(' ', strip=True)
        m = re.match(r'^Статья\s+(\d+(?:-\d+)?)\s*\.', htxt)
        if not m:
            continue
        target_anchor = article_map.get(m.group(1))
        if not target_anchor or not target_anchor.endswith('h'):
            continue
        if h3.find('a', attrs={'name': True}) or h3.find('a', attrs={'id': True}):
            continue
        new_anchor = soup.new_tag('a', attrs={'id': target_anchor, 'name': target_anchor})
        h3.insert(0, new_anchor)
        injected += 1
    return injected


def is_in_snoska(tag):
    """Проверяет что тег внутри сноски."""
    parent = tag.parent
    while parent:
        if parent.name == 'span' and 'note' in (parent.get('class') or []):
            return True
        if parent.name == 'font':
            color = (parent.get('color') or '').upper().strip().lstrip('#')
            if color == 'FF0000':
                text = parent.get_text()
                if 'Примечание ИЗПИ' in text or 'Примечание РЦПИ' in text:
                    return True
        if parent.name in ('body', 'article'):
            break
        parent = parent.parent
    return False


def add_subpoint_anchors(html_path, article_map):
    """
    Проходит по HTML и добавляет id к подпунктам.
    Возвращает (soup, subpoint_map) где subpoint_map:
      { "52_1_9": "z52_1_9", "52_1_1": "z52_1_1", ... }
    """
    with open(html_path, 'rb') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # Шаг 0: инжектируем синтетические <a id="zNh"> для статей,
    # у которых заголовок без anchor (KoAP/АППК/УПК и т.п.).
    synth_injected = inject_synthetic_anchors(soup, article_map)
    if synth_injected:
        print(f'Инжектировано синтетических anchor-заголовков: {synth_injected}')

    # Обратный маппинг: anchor → article_num
    anchor_to_art = {v: k for k, v in article_map.items()}

    subpoint_map = {}  # "art_punkt_subp" → anchor_id
    added_count = 0

    # Собираем все блочные теги в порядке документа
    all_tags = soup.find_all(['p', 'h3', 'div'])

    current_article = None   # номер текущей статьи
    current_punkt = None     # номер текущего пункта (1., 2., ...)
    in_subpoint_list = False # находимся внутри списка подпунктов

    for tag in all_tags:
        if is_in_snoska(tag):
            continue

        # Проверяем: это заголовок статьи?
        art_num, art_anchor = get_article_anchor(tag)
        if art_num:
            current_article = art_num
            current_punkt = None
            in_subpoint_list = False
            continue

        if not current_article:
            continue

        text = tag.get_text(' ', strip=True)
        if not text:
            continue

        # Проверяем: это пункт (1., 2., ...)?
        m_punkt = PUNKT_RE.match(text)
        if m_punkt and not tag.get('id', '').startswith('z52_'):
            # Это пункт статьи (часть 1., 2., ...)
            punkt_num = m_punkt.group(1)
            current_punkt = punkt_num
            in_subpoint_list = False
            # Якорь для пункта: либо реальный id, либо инжектируем синтетический.
            # Это нужно для корректной работы ссылок типа "пунктом N статьи M"
            # (cross-code из script 10) и "пунктом N настоящей статьи" (script 02).
            key = f'{current_article}_{punkt_num}'
            existing_id = tag.get('id')
            if existing_id:
                # У тега уже есть id (типа z428) — записываем маппинг на него
                subpoint_map[key] = existing_id
            else:
                # Инжектируем синтетический anchor
                synth = f'z{current_article}_p{punkt_num}'
                new_a = soup.new_tag('a', attrs={'id': synth, 'name': synth})
                tag.insert(0, new_a)
                subpoint_map[key] = synth
                added_count += 1
            continue

        # Проверяем: это подпункт (1), 2), 9), ...)?
        m_subp = SUBPOINT_RE.match(text)
        if m_subp:
            subp_num = m_subp.group(1)
            in_subpoint_list = True

            # Формируем уникальный id
            if current_punkt:
                anchor_id = f'z{current_article}_{current_punkt}_{subp_num}'
                key = f'{current_article}_{current_punkt}_{subp_num}'
            else:
                anchor_id = f'z{current_article}_{subp_num}'
                key = f'{current_article}_{subp_num}'

            # Добавляем id только если его ещё нет
            if not tag.get('id'):
                tag['id'] = anchor_id
                subpoint_map[key] = anchor_id
                added_count += 1
            elif tag.get('id') != anchor_id:
                # У тега уже есть id (например z1203 для "4-1)") — записываем маппинг на него
                subpoint_map[key] = tag['id']
        elif in_subpoint_list and tag.get('id'):
            # Встретили тег с id после списка подпунктов — это следующий пункт
            in_subpoint_list = False

    print(f'Добавлено якорей к подпунктам: {added_count}')
    print(f'Всего подпунктов в маппинге: {len(subpoint_map)}')
    return soup, subpoint_map


def main():
    ap = argparse.ArgumentParser(description='Добавляет якоря к подпунктам статей')
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--map', required=True, help='article_map JSON')
    ap.add_argument('--subpoint-map-output', default=None,
                    help='Куда сохранить маппинг подпунктов (JSON)')
    args = ap.parse_args()

    with open(args.map, encoding='utf-8') as f:
        article_map = json.load(f)

    soup, subpoint_map = add_subpoint_anchors(args.input, article_map)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(str(soup))
    print(f'Результат: {args.output}')

    if args.subpoint_map_output:
        with open(args.subpoint_map_output, 'w', encoding='utf-8') as f:
            json.dump(subpoint_map, f, ensure_ascii=False, indent=2)
        print(f'Маппинг подпунктов: {args.subpoint_map_output}')

    # Показать примеры
    sample = list(subpoint_map.items())[:15]
    print('\nПримеры маппинга:')
    for key, anchor in sample:
        parts = key.split('_')
        if len(parts) == 3:
            print(f'  подпункт {parts[2]}) пункта {parts[1]} статьи {parts[0]} → #{anchor}')
        else:
            print(f'  подпункт {parts[1]}) статьи {parts[0]} → #{anchor}')


if __name__ == '__main__':
    main()
