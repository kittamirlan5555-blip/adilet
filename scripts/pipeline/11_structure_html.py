"""
Скрипт 11: Структурирование HTML кодексов РК в иерархический вид.

Универсально обрабатывает все кодексы АДИЛЕТ. Ключевые особенности:
- Ищет <article> внутри страницы — именно там NPA-контент
- Сохраняет <head>, всё навигационное окружение, CSS/JS/подсветку
- Обрабатывает compound h3 (несколько уровней в одном теге — ТК, ПК)
- Обрабатывает h3-статьи (ГК, ЗК, УПК) и p>b-статьи (НК, ТК, СК...)
- Обрабатывает римские цифры в разделах (ЗК)
- Добавляет data-атрибуты к каждому контейнеру
- Не разрушает существующие якоря, ссылки, id

Иерархия: ЧАСТЬ > РАЗДЕЛ > ПОДРАЗДЕЛ > ГЛАВА > ПАРАГРАФ > СТАТЬЯ
"""

import re
import sys
import argparse
from bs4 import BeautifulSoup, Tag, NavigableString
from copy import copy

# ──────────────────── Уровни иерархии ────────────────────────────────────

LEVELS = {
    'part':       1,
    'section':    2,
    'subsection': 3,
    'chapter':    4,
    'paragraph':  5,
    'subchapter': 6,
    'article':    7,
}

ROMAN_MAP = {
    'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,'VIII':8,
    'IX':9,'X':10,'XI':11,'XII':12,'XIII':13,'XIV':14,'XV':15,
    'XVI':16,'XVII':17,'XVIII':18,'XIX':19,'XX':20,'XXI':21,
    'XXII':22,'XXIII':23,'XXIV':24,'XXV':25,'XXX':30,
}
ROMAN_RE = re.compile(r'^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$', re.I)

TYPE_LABELS = {
    'part':       'часть',
    'section':    'раздел',
    'subsection': 'подраздел',
    'chapter':    'глава',
    'paragraph':  'параграф',
    'subchapter': 'подглава',
    'article':    'статья',
}

# ──────────────────── Классификатор текста ────────────────────────────────

def roman_to_int(s: str) -> int:
    s = s.strip().upper()
    return ROMAN_MAP.get(s, 0)


def classify(text: str):
    """
    Классифицирует заголовочный текст.
    Возвращает (node_type, number, title) или None.
    """
    t = text.strip()
    u = t.upper()

    # ОБЩАЯ ЧАСТЬ / ОСОБЕННАЯ ЧАСТЬ / ЧАСТЬ N
    if re.match(r'(ОБЩАЯ|ОСОБЕННАЯ)\s+ЧАСТЬ', u):
        return ('part', None, t)
    m = re.match(r'ЧАСТЬ\s+(\d+)', u)
    if m:
        return ('part', m.group(1), t)

    # ПОДРАЗДЕЛ (должен идти раньше РАЗДЕЛ)
    m = re.match(r'ПОДРАЗДЕЛ\s+(\d+)', u)
    if m:
        return ('subsection', m.group(1), t)

    # РАЗДЕЛ (арабские и римские)
    m = re.match(r'РАЗДЕЛ\s+([IVXLCDM]+|\d+(?:-\d+)?)\b', u)
    if m:
        num = m.group(1)
        if ROMAN_RE.match(num) and not num.isdigit():
            num = str(roman_to_int(num))
        return ('section', num, t)

    # ПОДГЛАВА (раньше ГЛАВА)
    m = re.match(r'ПОДГЛАВА\s+(\d+[\w-]*)', u)
    if m:
        return ('subchapter', m.group(1), t)

    # ГЛАВА
    m = re.match(r'ГЛАВА\s+(\d+[\w-]*)', u)
    if m:
        return ('chapter', m.group(1), t)

    # ПАРАГРАФ
    m = re.match(r'ПАРАГРАФ\s+(\d+[\w-]*)', u)
    if m:
        return ('paragraph', m.group(1), t)

    # СТАТЬЯ
    m = re.match(r'СТАТЬ[ЯИЕЮ]\s+(\d+[\w-]*)', u)
    if m:
        return ('article', m.group(1), t)

    return None


# Маркеры для поиска границ в compound-заголовках
_SPLIT_MARKERS = re.compile(
    r'(?:ОБЩАЯ\s+ЧАСТЬ|ОСОБЕННАЯ\s+ЧАСТЬ|ЧАСТЬ\s+\d'
    r'|ПОДРАЗДЕЛ\s+\d|РАЗДЕЛ\s+(?:[IVXLCDM]+|\d+)'
    r'|ПОДГЛАВА\s+\d|ГЛАВА\s+\d|ПАРАГРАФ\s+\d|СТАТЬ[ЯИЕЮ]\s+\d)',
    re.IGNORECASE
)


def split_compound(text: str):
    """
    Разбивает составной заголовок вида
    'ОБЩАЯ ЧАСТЬ  РАЗДЕЛ 1. ...  Глава 1. ...'
    на отдельные структурные элементы.
    Возвращает список (node_type, number, title) или [].
    """
    text = text.strip()
    matches = list(_SPLIT_MARKERS.finditer(text))
    if len(matches) < 2:
        return []   # не составной
    parts = []
    for i, m in enumerate(matches):
        end = matches[i+1].start() if i + 1 < len(matches) else len(text)
        chunk = text[m.start():end].strip()
        cl = classify(chunk)
        if cl:
            parts.append(cl)
    return parts if len(parts) >= 2 else []


def _marker_chunks(text: str):
    """
    Режет text по границам _SPLIT_MARKERS и классифицирует каждый кусок.
    Возвращает список (classification, chunk_text).
    """
    text = text.strip()
    matches = list(_SPLIT_MARKERS.finditer(text))
    out = []
    for i, m in enumerate(matches):
        end = matches[i+1].start() if i + 1 < len(matches) else len(text)
        chunk = text[m.start():end].strip()
        cl = classify(chunk)
        if cl:
            out.append((cl, chunk))
    return out


def split_merged_heading(text: str):
    """
    Склейка «подзаголовок раздела/части + структурный маркер» в ОДНОМ <h3>,
    напр.: 'НОТАРИАЛЬНЫЕ ДЕЙСТВИЯ ... СОВЕРШЕНИЯ  Глава 6. ...'
    (подзаголовок Раздела 2 слит с «Глава 6.»).

    Срабатывает ТОЛЬКО в «дырке», куда сейчас проваливается такой заголовок:
      - сам заголовок не классифицируется      (classify(text) is None),
      - это не обычный ≥2-маркерный compound    (split_compound(text) == []),
      - но в тексте есть структурный маркер ПОСЛЕ непустого нес-маркерного
        префикса (маркер не в начале строки).

    Возвращает (prefix_text, [(classification, chunk_text), ...]) или None.
    Текст не теряется: префикс + куски маркеров покрывают исходный текст.
    """
    text = text.strip()
    if classify(text) or split_compound(text):
        return None
    m = _SPLIT_MARKERS.search(text)
    if not m:
        return None
    prefix = text[:m.start()].strip()
    if not prefix:
        return None  # маркер в начале — это не склейка-с-префиксом
    chunks = _marker_chunks(text[m.start():])
    if not chunks:
        return None
    return prefix, chunks


# ──────────────────── Вспомогательные функции ─────────────────────────────

def get_anchor_id(tag: Tag):
    """Возвращает id якоря из тега: сначала id атрибут, потом <a name>/<a id> внутри."""
    if isinstance(tag, Tag):
        if tag.get('id'):
            return tag['id']
        a = tag.find('a', attrs={'name': True})
        if a:
            return a.get('id') or a.get('name')
        a = tag.find('a', attrs={'id': True})
        if a:
            return a['id']
    return None


def is_article_b_marker(tag: Tag) -> bool:
    """
    True если тег — p с жирным текстом 'Статья N...' внутри.
    Паттерн: <p><b><a ...></a>Статья N. Название</b></p>
    """
    if tag.name != 'p':
        return False
    b = tag.find(['b', 'strong'])
    if not b:
        return False
    t = b.get_text(' ', strip=True)
    return bool(re.match(r'[Сс]тать[яиею]\s+\d', t))


def make_div(soup: BeautifulSoup, node_type: str, number, anchor_id=None) -> Tag:
    div = soup.new_tag('div')
    div['class'] = node_type
    div['data-type'] = TYPE_LABELS.get(node_type, node_type)
    if number is not None:
        div['data-number'] = str(number)
    if anchor_id:
        div['id'] = 'w_' + str(anchor_id)
    return div


# ──────────────────── Разбор плоского контента ────────────────────────────

def flatten_article(article: Tag, soup: BeautifulSoup):
    """
    Обходит прямых потомков <article> и возвращает список:
        ('structural', tag, (node_type, number, title))
        ('virtual',    text, (node_type, number, title))   # для compound-split
        ('content',    tag,  None)
    """
    result = []
    for el in list(article.children):
        if isinstance(el, NavigableString):
            if el.strip():
                result.append(('content', el, None))
            continue

        # h2 / h3 / h4 — потенциальные структурные заголовки
        if el.name in ('h2', 'h3', 'h4'):
            raw_text = el.get_text(' ', strip=True)
            # Попытка разбить compound
            parts = split_compound(raw_text)
            if parts:
                # Особый случай «нотариат гл.6 / zhilishniy»: составной <h3>
                # вида «РАЗДЕЛ N <br><a name="zCH"></a>Глава M. …», где ВНУТРИ
                # одного тега лежит ЯКОРЬ ГЛАВЫ. Старое поведение запихивало весь
                # тег (с якорем главы и текстом главы) в заголовок РАЗДЕЛА, а главу
                # дублировало virtual-span'ом без якоря. Расщепляем по-настоящему:
                #   • раздел  ← новый тег только с текстом маркера + id раздела;
                #   • глава   ← новый тег с РЕАЛЬНЫМ <a name> главы + её название.
                # Триггер строго точечный: РАЗДЕЛ — ГОЛЫЙ маркер «РАЗДЕЛ N» (без
                # собственного названия), сразу за ним глава с внутренним якорем.
                # Это отличает zhilishniy (4 шт.) от прочих кодексов, где у раздела
                # есть своё название («РАЗДЕЛ 1. ОБЩИЕ ПОЛОЖЕНИЯ Глава 1. …») —
                # их поведение не трогаем.
                inner_anchor = (el.find('a', attrs={'name': True}) or
                                el.find('a', attrs={'id': True}))
                bare_section = (len(parts) == 2 and parts[0][0] == 'section' and
                                parts[1][0] == 'chapter' and
                                re.fullmatch(r'РАЗДЕЛ\s+\d+(?:-\d+)?',
                                             parts[0][2].strip(), re.IGNORECASE))
                if inner_anchor is not None and bare_section:
                    # Раздел: только свой маркер-текст, сохраняем id <h3> (если был)
                    sec_tag = soup.new_tag(el.name)
                    base_id = el.get('id')
                    if base_id:
                        sec_tag['id'] = base_id
                    sec_tag.string = parts[0][2]
                    result.append(('structural', sec_tag, parts[0]))
                    # Глава: реальный якорь + название, РЕАЛЬНЫМ тегом
                    ch_tag = soup.new_tag(el.name)
                    ch_tag.append(copy(inner_anchor))
                    ch_tag.append(NavigableString(parts[1][2]))
                    result.append(('structural', ch_tag, parts[1]))
                else:
                    # Первая часть берёт реальный тег
                    result.append(('structural', el, parts[0]))
                    # Остальные — виртуальные (без реального тега)
                    for p in parts[1:]:
                        result.append(('virtual', raw_text, p))
            else:
                cl = classify(raw_text)
                if cl:
                    result.append(('structural', el, cl))
                else:
                    # «дырка»: склейка подзаголовка раздела/части с «Глава N» и т.п.
                    # в одном <h3>. Авто-разбивка — но только для ПЛОСКИХ заголовков
                    # (без вложенных <a name>/<a id>), чтобы не потерять якоря.
                    has_inner_anchor = bool(
                        el.find('a', attrs={'name': True}) or
                        el.find('a', attrs={'id': True}))
                    merged = None if has_inner_anchor else split_merged_heading(raw_text)
                    if merged:
                        prefix, chunks = merged
                        base_id = el.get('id')
                        # префикс (подзаголовок) -> контент, сохраняем исходный якорь.
                        # Трейлинг-пробел ОБЯЗАТЕЛЕН: префикс и заголовок «Глава N»
                        # становятся соседними блочными элементами, и get_text()
                        # склеил бы их в одно слово («СОВЕРШЕНИЯГлава») без разделителя.
                        ptag = soup.new_tag(el.name)
                        if base_id:
                            ptag['id'] = base_id
                        ptag.string = prefix + ' '
                        result.append(('content', ptag, None))
                        # маркеры: первый -> реальный новый тег, далее -> virtual
                        for j, (mcl, chunk_text) in enumerate(chunks):
                            if j == 0:
                                htag = soup.new_tag(el.name)
                                htag.string = chunk_text
                                if base_id:
                                    htag['id'] = f'{base_id}_{mcl[0]}{mcl[1]}'
                                result.append(('structural', htag, mcl))
                            else:
                                result.append(('virtual', chunk_text, mcl))
                    else:
                        result.append(('content', el, None))
            continue

        # p — проверяем паттерн <p><b>Статья N</b></p>
        if el.name == 'p' and is_article_b_marker(el):
            b = el.find(['b', 'strong'])
            t = b.get_text(' ', strip=True)
            cl = classify(t)
            if cl:
                result.append(('structural', el, cl))
                continue

        result.append(('content', el, None))

    return result


# ──────────────────── Построение иерархии ─────────────────────────────────

def build_tree(soup: BeautifulSoup, flat: list) -> Tag:
    """
    Принимает плоский список из flatten_article(),
    возвращает div.document с вложенными div-обёртками.
    """
    root = soup.new_tag('div', **{'class': 'document'})
    # stack: список (container_div, node_type, level)
    stack = [(root, 'root', 0)]

    def cur():
        return stack[-1][0]

    def pop_to(target_level: int):
        while len(stack) > 1 and stack[-1][2] >= target_level:
            stack.pop()

    for kind, el, cl in flat:
        if kind == 'content':
            cur().append(el)
            continue

        node_type, number, title = cl
        level = LEVELS[node_type]
        pop_to(level)

        # Определяем anchor_id
        if kind == 'structural':
            anchor_id = get_anchor_id(el)
        else:
            anchor_id = None

        wrapper = make_div(soup, node_type, number, anchor_id)

        if kind == 'structural':
            wrapper.append(el)
        else:
            # virtual — создаём span-заглушку (реальный тег уже добавлен в предыдущем элементе)
            span = soup.new_tag('span', **{'class': f'{node_type}-label'})
            span.string = title
            wrapper.append(span)

        cur().append(wrapper)
        stack.append((wrapper, node_type, level))

    return root


# ──────────────────── Точка входа ─────────────────────────────────────────

def find_content_article(soup: BeautifulSoup):
    """
    Находит <article> с NPA-контентом (может быть вложен глубоко).
    """
    # Все article теги, выбираем тот, в котором есть h3 или b>Статья
    articles = soup.find_all('article')
    if not articles:
        return None
    if len(articles) == 1:
        return articles[0]
    # Если несколько — берём с наибольшим контентом
    return max(articles, key=lambda a: len(a.get_text()))


def _has_direct_marker(article: Tag) -> bool:
    """Есть ли структурный маркер (h3-заголовок или p>b>Статья) среди ПРЯМЫХ
    детей <article> — то, что видит flatten_article."""
    for el in article.children:
        if not isinstance(el, Tag):
            continue
        if el.name in ('h2', 'h3', 'h4') and (
                classify(el.get_text(' ', strip=True)) or split_compound(el.get_text(' ', strip=True))):
            return True
        if el.name == 'p' and is_article_b_marker(el):
            return True
    return False


def _has_deep_marker(article: Tag) -> bool:
    """Есть ли маркеры статей где-то ВНУТРИ (не обязательно прямыми детьми)."""
    for p in article.find_all('p'):
        if is_article_b_marker(p):
            return True
    for h in article.find_all(['h3', 'h4']):
        if classify(h.get_text(' ', strip=True)):
            return True
    return False


def unwrap_div_layout(article: Tag) -> int:
    """Вариант-B раскладки adilet: контент завёрнут в per-блок <div>
    (article > div > p > b > Статья), поэтому маркеры НЕ прямые дети <article>,
    и flatten_article видит только опаковые <div> → 0 статей.

    Если среди ПРЯМЫХ детей нет ни одного структурного маркера, а глубже они
    есть — разворачиваем <div>-обёртки на уровень (до 3 раз, на случай вложенных),
    пока маркеры не станут прямыми детьми. ПЛОСКИЕ раскладки (маркеры уже прямые)
    не трогаем вовсе → регресс на нормальных кодексах исключён по построению.
    Возвращает число раундов разворота (0 = не тронуто).
    Текст-инвариант сохраняется: узлы только переносятся на уровень выше."""
    if _has_direct_marker(article) or not _has_deep_marker(article):
        return 0
    rounds = 0
    for _ in range(3):
        if _has_direct_marker(article):
            break
        changed = False
        new_children = []
        for el in list(article.children):
            if isinstance(el, Tag) and el.name == 'div':
                new_children.extend(list(el.children))
                changed = True
            else:
                new_children.append(el)
        if not changed:
            break
        article.clear()
        for c in new_children:
            article.append(c)
        rounds += 1
    return rounds


def process_file(input_path: str, output_path: str):
    print(f'  {input_path} -> ', end='', flush=True)

    with open(input_path, 'rb') as f:
        raw = f.read()

    soup = BeautifulSoup(raw, 'html.parser')

    article = find_content_article(soup)
    if not article:
        print('WARN: <article> не найден, пропускаю')
        return None

    unwrap_div_layout(article)     # variant-B: развернуть div-обёртки статей
    flat = flatten_article(article, soup)

    # Строим дерево
    new_tree = build_tree(soup, flat)

    # Заменяем содержимое article на структурированное дерево
    article.clear()
    article.append(new_tree)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))

    print(output_path)
    return new_tree


def count_stats(tree: Tag) -> dict:
    if tree is None:
        return {}
    stats = {}
    for cls in LEVELS:
        stats[cls] = len(tree.find_all('div', class_=cls, recursive=True))
    return stats


# ──────────────────── CLI ─────────────────────────────────────────────────

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Структурирование HTML кодексов РК')
    ap.add_argument('--input',  required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    tree = process_file(args.input, args.output)
    stats = count_stats(tree)
    labels = {
        'part':'частей','section':'разделов','subsection':'подразделов',
        'chapter':'глав','paragraph':'параграфов','subchapter':'подглав',
        'article':'статей',
    }
    for k, label in labels.items():
        v = stats.get(k, 0)
        if v:
            print(f'    {label}: {v}')
