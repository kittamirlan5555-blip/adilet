r"""
ВЫЛЕЧЕН 2026-06-10 (laws3 Фаза 1). История бага ниже; защита теперь ВСТРОЕНА:
Этот скрипт ПЕРЕСОБИРАЕТ видимый текст перечней из частей. Регекс сепаратора
знает только дефис (\s+-\s*), НЕ en-dash «–»: на «пунктами 2 – 5» сепаратор
не матчится и молчаливый фолбэк подменяет диапазон на « и » / «, »
(7 точек: строки ~402/542/602/698/735/776/1004). Это испортило диапазоны в
21 статье 10 документов (см. data/reports/audit/06_fixround_block1.md).
ЛЕЧЕНИЕ: (а) SEP_PAT знает en/em-dash и «или» — диапазоны сохраняют тире;
(б) центральный гейт в апплай-узле: замена, меняющая видимый текст, ПРОПУСКАЕТСЯ
(SKIPPED_INVARIANT в отчёте); (в) файловый гейт перед записью: get_text(вход)
!= get_text(выход) -> вывод НЕ пишется, exit 1. Тесты: tests/test_02_heal.py.
"""
"""
Скрипт 2: Фиксер внутренних ссылок (v5)

Изменения v5:
  - Единообразный стиль: слово "подпунктом/подпунктами" входит в первую ссылку
  - Новый паттерн: "N-N настоящей статьи" -> ссылка на параграф N-N внутри той же статьи
  - Новый паттерн: "пунктах 1), 2), 3) настоящей части" -> ссылки на подпункты текущей части
  - Исправлен PUNKT_CONTEXT: "N (пунктом M) части..." не ложно блокирует линковку N
  - make_subpoint_links: "пункта N" и "статьи N" тоже кликабельны
  - Третий проход: "пунктом 1-1" перед существующей ссылкой на статью

Использование:
  python 02_fix_internal_links.py \
    --input trudovoy.html \
    --map article_map_trudovoy.json \
    --doc-id K1500000414 \
    --output trudovoy_fixed.html \
    --report fix_report.csv
"""

import re

# === ЛЕЧЕНИЕ 2026-06-10: сепаратор перечней знает en/em-dash и «или» ===
SEP_PAT = r'(?:\s*,\s*|\s*[–—-]\s*|\s+и\s+|\s+или\s+)'
_RE_TAGS = re.compile(r'<[^>]+>')


def _vis(s):
    """Видимый текст фрагмента: без тегов, &nbsp; и всех пробелов (гейт)."""
    return re.sub(r'[\s ]+', '', _RE_TAGS.sub('', s).replace('&nbsp;', ''))

import json
import csv
import argparse
from bs4 import BeautifulSoup, NavigableString


# ========== REGEX ПАТТЕРНЫ ==========

SUBPOINT_PATTERN = re.compile(
    r'(подпункт(?:ом|а|е|у|ами|ах|ов)?'
    r'\s+\d+(?:-\d+)?\)'                                # первый подпункт: "подпунктами 1)"
    r'(?:(?:\s*,\s*|\s*[–—-]\s*|\s+и\s+)\d+(?:-\d+)?\))*'  # доп./диапазон: ", 18), 20) и 23)" или " – 4)"
    r')'
    r'(\s+пункт(?:а|е|у|ом|ами)?\s+\d+(?:-\d+)?(?:-\d+)?)'   # "пункта 1" или "пункта 1-1"
    r'(?:(?:\s*,\s*|\s+и\s+)пунктом?\s+\d+(?:-\d+)?(?:-\d+)?\)?)*'  # ", пунктом 1-1"
    r'(\s+стат(?:ь[яиейюёямих]+|ей)\s+(\d+(?:-\d+)?))',
    re.IGNORECASE
)

POINT_ARTICLE_PATTERN = re.compile(
    r'(пункт(?:а|е|у|ом|ами)?\s+\d+(?:-\d+)?'
    r'(?:\))?'                            # опциональная скобка: "пунктом 3)"
    r'(?:(?:\s*,\s*|\s+и\s+)\d+(?:-\d+)?\))*'  # дополнительные: ", 4)"
    r')'
    r'(?:\s+(?:части?|частью)\s+\w+)?'   # опционально: "части первой", "части седьмой"
    r'(\s+стат(?:ь[яиейюёямих]+|ей)\s+(\d+(?:-\d+)?))',
    re.IGNORECASE
)

ARTICLE_PATTERN = re.compile(
    r'(стат(?:ь[яиейюёямих]+|ей)\s+(\d+(?:-\d+)?))'
    r'(?!\d)'                                              # critical: don't match "Статья 5" inside "Статья 59"
    r'(?!\s*\.(?:\s+|\s*[А-ЯЁA-Z]))',
    re.IGNORECASE
)

# Паттерн: "главой N" / "главе N" / "главы N" настоящего Кодекса — ссылка на главу
CHAPTER_PATTERN = re.compile(
    r'(глав(?:ой|е|ы|у|а)\s+(\d+(?:-\d+)?))'
    r'(?=\s+настоящего\s+[Кк]одекса|\s+настоящей\s+[Чч]асти)',
    re.IGNORECASE
)

# Паттерн: "N-N настоящей статьи" — ссылка на параграф N-N внутри той же статьи
# Примеры: "3-1 настоящей статьи", "1-1 настоящей статьи"
SELF_PART_PATTERN = re.compile(
    r'(?<!\d)(\d+-\d+)\s+(настоящей\s+стат(?:ь[яиейюёямих]+|ей))',
    re.IGNORECASE
)

# Паттерн: "пунктом N настоящей статьи" / "пункте N настоящей статьи" / "пункта N настоящей статьи"
# Ссылка на пункт N текущей статьи (обычный пункт без дефиса)
# Примеры: "пунктом 2 настоящей статьи", "пункте 1 настоящей статьи", "пункта 4 настоящей статьи"
SELF_PUNKT_PATTERN = re.compile(
    r'(пункт(?:е|а|у|ом)?)\s+(\d+(?:-\d+)?)\s+(настоящей\s+стат(?:ь[яиейюёямих]+|ей))',
    re.IGNORECASE
)

# Паттерн: "N-N или/," — число N-N в перечислении частей, перед словом "настоящей"
# Примеры: "частями первой, 1-1 или второй настоящей статьи"
#          "частями первой, 1-1, второй или третьей настоящей статьи"
# Захватываем только само число N-N — слово "настоящей статьи" дальше в тексте
SELF_PART_ENUM_PATTERN = re.compile(
    r'(?<=,\s)(\d+-\d+)(?=(?:\s+или|,)\s+\w+(?:(?:,\s+|\s+или\s+)\w+)*\s+настоящей\s+стать)',
    re.IGNORECASE
)

# Паттерн: "части N-N" или "частью N-N" — ссылка на часть N-N текущей статьи
# Примеры: "пунктом 3) части 3-1", "частью 3-1 настоящей статьи"
SELF_PART_CHASTI_PATTERN = re.compile(
    r'(част[ьюие]\w*)\s+(\d+-\d+)',
    re.IGNORECASE
)

# Паттерн: "пунктах N), M), K) настоящей части/пункта" (внутренние ссылки на подпункты)
SAME_PART_SUBP_PATTERN = re.compile(
    r'(пункт(?:ах|е|а|у|ом|ами)?)\s+'
    r'(\d+(?:-\d+)?)\)'
    r'((?:(?:\s*[,и]\s*|\s+и\s+)\d+(?:-\d+)?\))*)'
    r'\s+настоящей\s+(части|пункта|статьи)',
    re.IGNORECASE
)

# Паттерн: "подпунктами N) [, M)] [части первой] настоящего пункта" — подпункты ТОГО ЖЕ пункта
# Примеры:
#   "подпунктами 3), 4), 5) и 6) настоящего пункта"
#   "подпунктом 2) настоящего пункта"
#   "подпунктом 5) части первой настоящего пункта"
#   "подпунктами 1), 3) и 5) части второй настоящего пункта"
SAME_PUNKT_SUBP_PATTERN = re.compile(
    r'(подпункт(?:ом|а|е|у|ами|ах|ов)?)\s+'
    r'(\d+(?:-\d+)?)\)'
    r'((?:(?:\s*,\s*|\s+и\s+)\d+(?:-\d+)?\))*)'
    r'(\s+част(?:ью|и|ей)\s+\S+)?'  # group 4: опц. "части первой/второй/...|N" — сохраняется в выводе
    r'\s+настоящего\s+пункта',
    re.IGNORECASE
)

# Паттерн: "подпунктом N) пункта M настоящей статьи/части"
# Ссылка на подпункт N пункта M ТЕКУЩЕЙ статьи (без явного номера статьи)
SELF_SUBPOINT_PATTERN = re.compile(
    r'(подпункт(?:ом|а|е|у|ами|ах|ов)?)\s+'
    r'(\d+(?:-\d+)?)\)'
    r'((?:(?:\s*,\s*|\s*[–—-]\s*|\s+и\s+)\d+(?:-\d+)?\))*)'
    r'\s+(пункт(?:а|е|у|ом|ами)?)\s+'
    r'(\d+(?:-\d+)?)'
    r'\s+настоящей\s+(?:статьи|части|пункта)',
    re.IGNORECASE
)

# Паттерн: "пунктах/пунктами N и M статьи K" — несколько пунктов + статья другая
# Примеры: "пунктах 1, 2 статьи 1", "пунктами 1 и 2 статьи 1", "пунктах 4 и 5 статьи 41"
# Также: "пунктами 9 и 10 статьи 159", "пунктах 1 – 3 статьи 207"
MULTI_PUNKT_ARTICLE_PATTERN = re.compile(
    r'(пункт(?:ах|е|а|у|ом|ами|ов)?)\s+'
    r'(\d+(?:-\d+)?)'
    r'((?:(?:\s*,\s*|\s*[–—-]\s*|\s+и\s+)\d+(?:-\d+)?)*)'
    r'(?:\s+(?:части?|частью)\s+\w+)?'
    r'(\s+стат(?:ь[яиейюёямих]+|ей)\s+(\d+(?:-\d+)?))',
    re.IGNORECASE
)

# Паттерн: "подпунктах N), M) и K) [пункта P] стать(и|ей) Q [настоящего Кодекса]"
# Примеры:
#   "подпунктах 1), 2) и 4) статьи 176"
#   "подпунктах 1), 2) и 4) статьи 176 настоящего Кодекса"
#   "подпунктами 3), 4) пункта 1 статьи 117"
MULTI_SUBP_ARTICLE_PATTERN = re.compile(
    r'(подпункт(?:ах|ами|ом|у|а|е|ов)?)\s+'
    r'(\d+(?:-\d+)?)\)'
    r'((?:(?:\s*,\s*|\s*[–—-]\s*|\s+и\s+)\d+(?:-\d+)?\))*)'
    r'(?:\s+пункт(?:а|е|у|ом|ами)?\s+(\d+(?:-\d+)?))?'   # опц. "пункта P"
    r'\s+стат(?:ь[яиейюёямих]+|ей)\s+(\d+(?:-\d+)?)',
    re.IGNORECASE
)

# Паттерн: "статьями N-M" или "статей N, M, K" (диапазоны и перечисления статей)
# Примеры: "статьями 249-257", "статьями 259-264", "статей 260, 261", "статей 177, 179-186"
MULTI_ARTICLE_PATTERN = re.compile(
    r'(стат(?:ь[яиейюёямих]+|ей))\s+'
    r'(\d+(?:-\d+)?)'
    r'((?:(?:\s*,\s*|\s*–\s*|\s*-\s*|\s+и\s+)\d+(?:-\d+)?)+)',
    re.IGNORECASE
)

# Паттерн: "пунктами N и M настоящей статьи" — self-ref несколько пунктов той же статьи
# Примеры:
#   "пунктами 5 и 6 настоящей статьи", "пунктами 3 и 4 настоящей статьи"
#   "пунктами 3, 5 настоящей статьи", "пунктами 1 и 2 настоящей статьи"
#   "Пункты 1-3 настоящей статьи", "пунктами 1 – 4 настоящей статьи"
#   "пунктах 2 – 5 настоящей статьи" (диапазон через тире/дефис/em-dash)
SELF_MULTI_PUNKT_PATTERN = re.compile(
    r'(пункт(?:ах|е|а|у|ом|ами|ы|ов)?)\s+'
    r'(\d+(?:-\d+)?)'
    r'((?:(?:\s*[,\-–—]\s*|\s+и\s+)\d+(?:-\d+)?)+)'  # запятая/тире/em/and
    r'\s+настоящей\s+(стат(?:ь[яиейюёямих]+|ей))',
    re.IGNORECASE
)

# Паттерн: "раздела N настоящего Кодекса" / "раздел N настоящего Кодекса"
# Ссылка на раздел N текущего кодекса. Требует section_map (раздел → anchor).
SELF_SECTION_PATTERN = re.compile(
    r'(раздел(?:ом|а|у|е)?)\s+(\d+(?:-\d+)?)\s+настоящего\s+[Кк]одекса',
    re.IGNORECASE
)

# Паттерн: "параграфом N раздела M настоящего Кодекса" / "параграфом N настоящего Кодекса"
SELF_PARAGRAPH_PATTERN = re.compile(
    r'(параграф(?:ом|а|у|е)?)\s+(\d+(?:-\d+)?)'
    r'(?:\s+раздел[аеу]?\s+(\d+(?:-\d+)?))?'
    r'\s+настоящего\s+[Кк]одекса',
    re.IGNORECASE
)

# Паттерн: "частью первой/второй/.../десятой настоящей статьи" — словесные числительные
# Ссылка на часть № <слово→число> текущей статьи
WORD_TO_NUM = {
    'первой': '1', 'первого': '1', 'первая': '1', 'первый': '1',
    'второй': '2', 'второго': '2', 'вторая': '2', 'второй': '2',
    'третьей': '3', 'третьего': '3', 'третья': '3', 'третий': '3',
    'четвертой': '4', 'четвёртой': '4', 'четвертого': '4', 'четвёртого': '4',
    'пятой': '5', 'пятого': '5',
    'шестой': '6', 'шестого': '6',
    'седьмой': '7', 'седьмого': '7',
    'восьмой': '8', 'восьмого': '8',
    'девятой': '9', 'девятого': '9',
    'десятой': '10', 'десятого': '10',
    'одиннадцатой': '11', 'двенадцатой': '12', 'тринадцатой': '13',
    'четырнадцатой': '14', 'пятнадцатой': '15', 'шестнадцатой': '16',
    'семнадцатой': '17', 'восемнадцатой': '18', 'девятнадцатой': '19',
    'двадцатой': '20',
}
_WORD_ALTERNATIVES = '|'.join(re.escape(w) for w in sorted(WORD_TO_NUM, key=len, reverse=True))
SELF_PART_WORD_PATTERN = re.compile(
    r'(част(?:ью|и|ей|ями)\s+)(' + _WORD_ALTERNATIVES + r')'
    r'(?=\s+настоящ(?:ей\s+стат|его\s+пункт))',
    re.IGNORECASE
)


def is_inside_link(element):
    parent = element.parent
    while parent:
        if parent.name == "a":
            return True
        parent = parent.parent
    return False


def is_article_heading(element):
    """True if the text node sits inside an article header.

    Heuristics:
      - any <hN>;
      - any <b> with <a name> or <a id> inside (existing case);
      - any <b> whose immediate text content starts with "Статья N." (KoAP/АППК
        style where the <b> has no explicit anchor inside). We avoid walking
        nested subtrees — only check the first ~40 chars of the element's own
        text to keep this O(1).
    """
    parent = element.parent
    while parent:
        if parent.name == "b":
            # Fast path: check existing anchor markers without get_text recursion
            if parent.find("a", attrs={"name": True}) or parent.find("a", attrs={"id": True}):
                return True
            # Check the very first text inside <b> — usually it IS the article title
            # if this is a header.
            first_text = None
            for ch in parent.children:
                if isinstance(ch, NavigableString):
                    s = str(ch)
                    if s.strip():
                        first_text = s.strip(); break
                else:
                    # If first non-text child is <a name>, that's a header too
                    if getattr(ch, "name", None) == "a" and (ch.get("name") or ch.get("id")):
                        return True
                    break
            if first_text and first_text.startswith("Статья "):
                # Quickly verify "Статья N." pattern via prefix check
                rest = first_text[7:25]
                if rest and rest[0].isdigit():
                    return True
            return False
        if parent.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            return True
        if parent.name in ("p", "article", "body", "div"):
            break
        parent = parent.parent
    return False


def is_in_snoska(element):
    """
    Улучшенная проверка сносок/примечаний.
    Ловит:
    1. Родитель — span.note
    2. Родитель — font color FF0000
    3. Текст содержит "Сноска."
    4. Соседние элементы содержат "Сноска." (текст часто РЯДОМ со span.note)
    5. Весь родительский блок содержит "Сноска."
    """
    # 1-2: родительские теги
    parent = element.parent
    while parent:
        if parent.name == "span" and parent.get("class") and "note" in parent.get("class", []):
            return True
        if parent.name == "font":
            color = (parent.get("color") or "").upper().strip().lstrip("#")
            if color == "FF0000":
                font_text = parent.get_text()
                if "Примечание ИЗПИ" in font_text or "Примечание РЦПИ" in font_text:
                    return True
        if parent.name in ("article", "body"):
            break
        parent = parent.parent

    # 3: сам текст
    text = str(element).strip()
    if "Сноска." in text or "Сноска " in text:
        return True
    if "Примечание." in text or "Примечани" in text[:15]:
        return True

    # 4: соседние элементы ДО текущего содержат "Сноска." или "Примечание."
    block_parent = element.parent
    if block_parent:
        for sibling in block_parent.children:
            if sibling is element:
                break
            sib_text = ""
            if isinstance(sibling, NavigableString):
                sib_text = str(sibling)
            elif hasattr(sibling, 'get_text'):
                sib_text = sibling.get_text()
            if "Сноска." in sib_text or "Сноска " in sib_text:
                return True
            if "Примечание." in sib_text or "Примечани" in sib_text[:15]:
                return True

        # 5: весь родительский блок (если не слишком большой)
        if block_parent.name not in ("article", "body", "div", None):
            full_text = block_parent.get_text()
            if len(full_text) < 2000:
                if "Сноска." in full_text or "Сноска " in full_text:
                    return True
                if full_text.strip().startswith("Примечание"):
                    return True

    return False


def make_link(text, anchor, doc_id, base_url):
    href = f"{base_url}/rus/docs/{doc_id}#{anchor}"
    return f'<a href="{href}">{text}</a>'


# Паттерн для разбора одного подпункта из фразы "подпунктом 9) пункта 1 статьи 52"
SUBPOINT_DETAIL_RE = re.compile(
    r'(подпункт(?:ом|а|е|у|ами|ах)?)\s+'           # слово "подпункт..."
    r'(\d+(?:-\d+)?)\)'                           # номер подпункта: 9)
    r'(?:(?:\s*,\s*|\s+и\s+)\d+(?:-\d+)?\))*'    # возможные дополнительные: ", 18), 20)"
    r'(\s+пункт(?:а|е|у|ом|ами)?)\s+'            # слово "пункта/пункту..."
    r'(\d+(?:-\d+)?(?:-\d+)?)'                    # номер пункта: 1, 1-1
    r'(?:(?:\s*,\s*|\s+и\s+)пунктом?\s+\d+(?:-\d+)?(?:-\d+)?\)?)*'
    r'(\s+стат(?:ь[яиейюёямих]+|ей))\s+'                  # слово "статьи/статьей..."
    r'(\d+(?:-\d+)?)',                             # номер статьи: 52
    re.IGNORECASE
)


def make_subpoint_links(full_match, article_map, subpoint_map, doc_id, base_url):
    """
    Создаёт ссылки для фразы типа "подпунктом 9) пункта 1 статьи 52".

    Стиль: слово "подпунктом" включается в первую ссылку:
      <a href="#z52_1_9">подпунктом 9)</a> <a href="#z428">пункта 1</a> <a href="#z52">статьи 52</a>

    Возвращает строку с HTML или None если не удалось разобрать.
    """
    dm = SUBPOINT_DETAIL_RE.search(full_match)
    if not dm:
        return None

    subp_word = dm.group(1)      # "подпунктом"
    subp_n = dm.group(2)         # "9"
    punkt_word = dm.group(3)     # " пункта"
    punkt_n = dm.group(4)        # "1"
    art_word = dm.group(5)       # " статьи"
    art_n = dm.group(6)          # "52"

    if art_n not in article_map:
        return None

    art_anchor = article_map[art_n]

    # Якорь для пункта: ищем в subpoint_map по ключу "art_punkt"
    # если нет — используем якорь статьи как fallback
    punkt_anchor = subpoint_map.get(f'{art_n}_{punkt_n}') or art_anchor

    # Извлекаем ВСЕ номера подпунктов из перечисления до начала "пункта"
    subp_section = full_match[dm.start(1):dm.start(3)]  # от "подпунктами" до " пункта"
    all_subp_nums = re.findall(r'(\d+(?:-\d+)?)\)', subp_section)
    if not all_subp_nums:
        all_subp_nums = [subp_n]

    # Строим HTML:
    # Первый подпункт: слово "подпунктом" ВКЛЮЧЕНО в ссылку -> единообразный стиль
    # Последующие подпункты: только число, разделитель снаружи
    parts = []
    for i, num in enumerate(all_subp_nums):
        anchor = subpoint_map.get(f'{art_n}_{punkt_n}_{num}') or \
                 subpoint_map.get(f'{art_n}_{num}') or \
                 art_anchor
        if i == 0:
            # Включаем слово "подпунктом" в ссылку
            parts.append(make_link(f'{subp_word} {num})', anchor, doc_id, base_url))
        else:
            sep_m = re.search('(' + SEP_PAT + ')' + re.escape(num) + r'\)', subp_section)
            sep = sep_m.group(1) if sep_m else ', '
            parts.append(sep)
            parts.append(make_link(f'{num})', anchor, doc_id, base_url))

    # "пункта N" — ссылка на якорь пункта
    parts.append(f' ')
    parts.append(make_link(f'{punkt_word.strip()} {punkt_n}', punkt_anchor, doc_id, base_url))
    # "статьи N" — ссылка на статью
    parts.append(f' ')
    parts.append(make_link(f'{art_word.strip()} {art_n}', art_anchor, doc_id, base_url))

    return ''.join(parts)


def process_text_node(text, article_map, doc_id, base_url,
                      allow_bare_numbers=False, subpoint_map=None,
                      current_article=None, part_anchor_map=None,
                      current_part=None, chapter_map=None):
    """
    current_article: номер текущей статьи (для SELF_PART_PATTERN)
    part_anchor_map: dict (art_num, part_num) -> anchor_id  (для SELF_PART_PATTERN)
    current_part: номер текущей части/пункта (для SAME_PART_SUBP_PATTERN)
    """
    if subpoint_map is None:
        subpoint_map = {}
    if part_anchor_map is None:
        part_anchor_map = {}
    if chapter_map is None:
        chapter_map = {}
    changes = []
    result = text
    replacements = []

    # === "главой N настоящего Кодекса" — ссылка на главу ===
    if chapter_map:
        for m in CHAPTER_PATTERN.finditer(result):
            ch_num = m.group(2)
            overlaps = any(r[0] < m.end() and r[1] > m.start() for r in replacements)
            if not overlaps and ch_num in chapter_map:
                anchor = chapter_map[ch_num]
                full_match = m.group(1)
                link = make_link(full_match, anchor, doc_id, base_url)
                replacements.append((m.start(), m.start() + len(full_match), full_match, link, f'ch{ch_num}'))

    for m in SUBPOINT_PATTERN.finditer(result):
        art_num = m.group(4)
        if art_num in article_map:
            full_match = m.group(0)
            # Пробуем создать детальные ссылки (подпункт + пункт + статья отдельно)
            if subpoint_map:
                detail = make_subpoint_links(
                    full_match, article_map, subpoint_map, doc_id, base_url
                )
                if detail:
                    replacements.append((m.start(), m.end(), full_match, detail, art_num))
                    continue
            # Fallback: одна ссылка на статью
            anchor = article_map[art_num]
            link = make_link(full_match, anchor, doc_id, base_url)
            replacements.append((m.start(), m.end(), full_match, link, art_num))

    for m in POINT_ARTICLE_PATTERN.finditer(result):
        art_num = m.group(3)
        overlaps = any(r[0] < m.end() and r[1] > m.start() for r in replacements)
        if not overlaps and art_num in article_map:
            anchor = article_map[art_num]
            full_match = m.group(0)
            link = make_link(full_match, anchor, doc_id, base_url)
            replacements.append((m.start(), m.end(), full_match, link, art_num))

    # === "пунктах N, M статьи K" / "пунктами N и M статьи K" / "пунктах N – M статьи K" ===
    for m in MULTI_PUNKT_ARTICLE_PATTERN.finditer(result):
        art_num = m.group(5)
        overlaps = any(r[0] < m.end() and r[1] > m.start() for r in replacements)
        if not overlaps and art_num in article_map:
            anchor = article_map[art_num]
            full_match = m.group(0)
            link = make_link(full_match, anchor, doc_id, base_url)
            replacements.append((m.start(), m.end(), full_match, link, art_num))

    # === "подпунктах N), M) и K) [пункта P] статьи Q" ===
    for m in MULTI_SUBP_ARTICLE_PATTERN.finditer(result):
        art_num = m.group(5)
        overlaps = any(r[0] < m.end() and r[1] > m.start() for r in replacements)
        if not overlaps and art_num in article_map:
            anchor = article_map[art_num]
            full_match = m.group(0)
            link = make_link(full_match, anchor, doc_id, base_url)
            replacements.append((m.start(), m.end(), full_match, link, art_num))

    # === "статьями 249-257" / "статей 260, 261" (диапазоны и перечисления) ===
    # Создаём ОТДЕЛЬНУЮ ссылку для каждой статьи в перечислении
    for m in MULTI_ARTICLE_PATTERN.finditer(result):
        first_art = m.group(2)
        overlaps = any(r[0] < m.end() and r[1] > m.start() for r in replacements)
        if overlaps:
            continue
        # Разбираем все статьи в перечислении
        word = m.group(1)       # "статьями" / "статей"
        rest = m.group(3)       # ", 16 и 18" / "-257" / ", 261"
        # Под-статья N-K (напр. «статья 7-1») vs диапазон «статьи 5-10».
        # Если "N-K" целиком — реальный ключ карты (т.е. это ОДНА под-статья,
        # а не перечень/диапазон) — линкуем весь матч на её собственный якорь,
        # а не на базовую статью N. rest должен быть РОВНО "-K" (одно число).
        sub_only = re.fullmatch(r'\s*[-–]\s*(\d+(?:-\d+)?)', rest or '')
        sub_key = f'{first_art}-{sub_only.group(1)}' if sub_only else None
        if sub_key and sub_key in article_map:
            anchor = article_map[sub_key]
            full_match = m.group(0)
            link = make_link(full_match, anchor, doc_id, base_url)
            replacements.append((m.start(), m.end(), full_match, link, sub_key))
        elif (sub_only and '-' not in sub_only.group(1)
              and int(sub_only.group(1)) < int(re.match(r'\d+', first_art).group(0))
              and sub_key not in article_map):
            # Форма "N-K" с K<N, которой НЕТ в карте — это ссылка на НЕсуществующую
            # под-статью (редакц. примечание «дополнить статьей 30-2 ... вводится в
            # действие …»), а НЕ диапазон "N–M". Цели нет → НЕ линкуем (оставляем текст).
            pass
        # Проверяем: если это диапазон (дефис между числами) — одна ссылка
        elif re.match(r'\s*[-–]\s*\d', rest):
            if first_art in article_map:
                anchor = article_map[first_art]
                full_match = m.group(0)
                link = make_link(full_match, anchor, doc_id, base_url)
                replacements.append((m.start(), m.end(), full_match, link, first_art))
        else:
            # Перечисление через запятую/и — отдельные ссылки
            # Извлекаем все числа из rest
            extra_arts = re.findall(r'(\d+(?:-\d+)?)', rest)
            all_arts = [first_art] + extra_arts
            # Проверяем что хоть одна статья есть в маппинге
            if not any(a in article_map for a in all_arts):
                continue
            # Строим HTML: "статьями" + ссылки через разделители
            link_parts = []
            seps = re.findall(r'(\s*,\s*|\s*–\s*|\s*-\s*|\s+и\s+)', rest)
            for i, art in enumerate(all_arts):
                if i == 0:
                    text = f'{word} {art}'
                else:
                    sep = seps[i-1] if i-1 < len(seps) else ', '
                    link_parts.append(sep)
                    text = art
                if art in article_map:
                    link_parts.append(make_link(text, article_map[art], doc_id, base_url))
                else:
                    link_parts.append(text)
            new_html = ''.join(link_parts)
            replacements.append((m.start(), m.end(), m.group(0), new_html, first_art))

    for m in ARTICLE_PATTERN.finditer(result):
        art_num = m.group(2)
        overlaps = any(r[0] < m.end() and r[1] > m.start() for r in replacements)
        if not overlaps and art_num in article_map:
            anchor = article_map[art_num]
            full_match = m.group(1)
            link = make_link(full_match, anchor, doc_id, base_url)
            replacements.append((m.start(), m.start() + len(full_match), full_match, link, art_num))

    if current_article and part_anchor_map:
        # === "пунктом N настоящей статьи" — ссылка на пункт N текущей статьи ===
        # ВАЖНО: обрабатываем РАНЬШЕ SELF_PART_PATTERN, чтобы "пунктом 4-1 настоящей статьи"
        # не раздваивалось на два совпадения (пунктом 4-1 + 4-1 настоящей статьи)
        for m in SELF_PUNKT_PATTERN.finditer(result):
            punkt_word = m.group(1)   # "пунктом"
            punkt_num = m.group(2)    # "2"
            nastoyashchey = m.group(3)  # "настоящей статьи"
            overlaps = any(r[0] < m.end() and r[1] > m.start() for r in replacements)
            if overlaps:
                continue
            anchor = part_anchor_map.get((current_article, punkt_num))
            if anchor:
                # Линкуем только "пунктом N" — "настоящей статьи" оставляем снаружи
                linked_part = make_link(f'{punkt_word} {punkt_num}', anchor, doc_id, base_url)
                new_html = linked_part + ' ' + nastoyashchey
                replacements.append((m.start(), m.end(), m.group(0), new_html, f'{current_article}_p{punkt_num}'))

        # === "пунктами N и M настоящей статьи" — self-ref несколько пунктов ===
        for m in SELF_MULTI_PUNKT_PATTERN.finditer(result):
            punkt_word = m.group(1)   # "пунктами"
            first_num = m.group(2)    # "5"
            rest = m.group(3)         # " и 6" или ", 5"
            nastoyashchey = m.group(4)  # "статьи"
            overlaps = any(r[0] < m.end() and r[1] > m.start() for r in replacements)
            if overlaps:
                continue
            # Collect all numbers
            all_nums = [first_num] + re.findall(r'(\d+(?:-\d+)?)', rest)
            link_parts = []
            any_linked = False
            for i, num in enumerate(all_nums):
                anchor = part_anchor_map.get((current_article, num))
                if i == 0:
                    if anchor:
                        link_parts.append(make_link(f'{punkt_word} {num}', anchor, doc_id, base_url))
                        any_linked = True
                    else:
                        link_parts.append(f'{punkt_word} {num}')
                else:
                    sep_m = re.search('(' + SEP_PAT + ')' + re.escape(num), rest)
                    sep = sep_m.group(1) if sep_m else ' и '
                    link_parts.append(sep)
                    if anchor:
                        link_parts.append(make_link(num, anchor, doc_id, base_url))
                        any_linked = True
                    else:
                        link_parts.append(num)
            if any_linked:
                link_parts.append(f' настоящей {nastoyashchey}')
                new_html = ''.join(link_parts)
                replacements.append((m.start(), m.end(), m.group(0), new_html, f'{current_article}_multi'))

        # === "части N-N" / "частью N-N" — ссылка на часть N-N текущей статьи ===
        # ВАЖНО: обрабатываем РАНЬШЕ SELF_PART_PATTERN, чтобы "частью 3-2 настоящей статьи"
        # не раздваивалось: SELF_PART_CHASTI захватывает "частью 3-2", а SELF_PART — "3-2 настоящей статьи"
        for m in SELF_PART_CHASTI_PATTERN.finditer(result):
            part_num = m.group(2)   # "3-1"
            overlaps = any(r[0] < m.end() and r[1] > m.start() for r in replacements)
            if overlaps:
                continue
            anchor = part_anchor_map.get((current_article, part_num))
            if anchor:
                full_match = m.group(0)
                link = make_link(full_match, anchor, doc_id, base_url)
                replacements.append((m.start(), m.end(), full_match, link, f'{current_article}_{part_num}'))

        # === "частью первой/второй/... настоящей статьи" — словесное числительное ===
        for m in SELF_PART_WORD_PATTERN.finditer(result):
            prefix = m.group(1)        # "частью " / "части " / "частей "
            word = m.group(2).lower()  # "первой" / "второй" / ...
            num = WORD_TO_NUM.get(word)
            if not num:
                continue
            overlaps = any(r[0] < m.end() and r[1] > m.start() for r in replacements)
            if overlaps:
                continue
            anchor = part_anchor_map.get((current_article, num))
            if anchor:
                # Линкуем фразу "<prefix><word>" целиком
                full = prefix + m.group(2)
                link = make_link(full, anchor, doc_id, base_url)
                replacements.append((m.start(), m.end(), full, link, f'{current_article}_p{num}'))

        # === "N-N настоящей статьи" — ссылка на параграф N-N внутри текущей статьи ===
        # Линкуем ТОЛЬКО номер N-N, слова "настоящей статьи" остаются обычным текстом
        for m in SELF_PART_PATTERN.finditer(result):
            part_num = m.group(1)   # "3-1"
            nastoyashchey = m.group(2)  # "настоящей статьи"
            overlaps = any(r[0] < m.end() and r[1] > m.start() for r in replacements)
            if overlaps:
                continue
            anchor = part_anchor_map.get((current_article, part_num))
            if anchor:
                link = make_link(part_num, anchor, doc_id, base_url)
                new_html = link + ' ' + nastoyashchey
                replacements.append((m.start(), m.end(), m.group(0), new_html, f'{current_article}_{part_num}'))

        # === "частями X, N-N или Y настоящей статьи" — N-N в перечислении частей ===
        for m in SELF_PART_ENUM_PATTERN.finditer(result):
            part_num = m.group(1)   # "1-1"
            overlaps = any(r[0] < m.end() and r[1] > m.start() for r in replacements)
            if overlaps:
                continue
            anchor = part_anchor_map.get((current_article, part_num))
            if anchor:
                full_match = m.group(1)
                link = make_link(full_match, anchor, doc_id, base_url)
                replacements.append((m.start(), m.end(), full_match, link, f'{current_article}_{part_num}'))

    # === "пунктах N), M) настоящей части" — ссылки на подпункты текущей части ===
    if current_article and current_part and subpoint_map:
        for m in SAME_PART_SUBP_PATTERN.finditer(result):
            overlaps = any(r[0] < m.end() and r[1] > m.start() for r in replacements)
            if overlaps:
                continue
            punkt_word = m.group(1)   # "пунктах"
            first_num = m.group(2)    # "1"
            rest = m.group(3)         # ", 2), 3) и 4)"
            scope_word = m.group(4)   # "части"

            # Собираем все номера
            all_nums = [first_num] + re.findall(r'(\d+(?:-\d+)?)\)', rest)

            # Строим ссылки: слово "пунктах" в первую ссылку
            link_parts = []
            for i, num in enumerate(all_nums):
                anchor = subpoint_map.get(f'{current_article}_{current_part}_{num}') or \
                         subpoint_map.get(f'{current_article}_{num}')
                if i == 0:
                    link_text = f'{punkt_word} {num})'
                    if anchor:
                        link_parts.append(make_link(link_text, anchor, doc_id, base_url))
                    else:
                        link_parts.append(link_text)
                else:
                    sep_m = re.search('(' + SEP_PAT + ')' + re.escape(num) + r'\)', rest)
                    sep = sep_m.group(1) if sep_m else ', '
                    link_parts.append(sep)
                    if anchor:
                        link_parts.append(make_link(f'{num})', anchor, doc_id, base_url))
                    else:
                        link_parts.append(f'{num})')

            link_parts.append(f' настоящей {scope_word}')
            new_html = ''.join(link_parts)
            full_match = m.group(0)
            replacements.append((m.start(), m.end(), full_match, new_html, f'{current_article}_{current_part}'))

    # === "подпунктами N) настоящего пункта" — ссылки на подпункты того же пункта ===
    if current_article and current_part and subpoint_map:
        for m in SAME_PUNKT_SUBP_PATTERN.finditer(result):
            overlaps = any(r[0] < m.end() and r[1] > m.start() for r in replacements)
            if overlaps:
                continue
            subp_word = m.group(1)   # "подпунктами"
            first_num = m.group(2)   # "3"
            rest = m.group(3)        # ", 4), 5) и 6)"
            chasti_seg = m.group(4) or ''   # " части первой" или ''

            all_nums = [first_num] + re.findall(r'(\d+(?:-\d+)?)\)', rest)

            link_parts = []
            for i, num in enumerate(all_nums):
                anchor = subpoint_map.get(f'{current_article}_{current_part}_{num}') or \
                         subpoint_map.get(f'{current_article}_{num}')
                if i == 0:
                    link_text = f'{subp_word} {num})'
                    if anchor:
                        link_parts.append(make_link(link_text, anchor, doc_id, base_url))
                    else:
                        link_parts.append(link_text)
                else:
                    sep_m = re.search('(' + SEP_PAT + ')' + re.escape(num) + r'\)', rest)
                    sep = sep_m.group(1) if sep_m else ', '
                    link_parts.append(sep)
                    if anchor:
                        link_parts.append(make_link(f'{num})', anchor, doc_id, base_url))
                    else:
                        link_parts.append(f'{num})')

            link_parts.append(f'{chasti_seg} настоящего пункта')
            new_html = ''.join(link_parts)
            full_match = m.group(0)
            replacements.append((m.start(), m.end(), full_match, new_html, f'{current_article}_{current_part}'))

    # === "подпунктом N) пункта M настоящей статьи" — ссылка на подпункт текущей статьи ===
    if current_article and subpoint_map:
        for m in SELF_SUBPOINT_PATTERN.finditer(result):
            overlaps = any(r[0] < m.end() and r[1] > m.start() for r in replacements)
            if overlaps:
                continue
            subp_word = m.group(1)    # "подпунктом"
            first_num = m.group(2)    # "2"
            extra = m.group(3)        # "" или ", 3) и 4)"
            punkt_word = m.group(4)   # "пункта"
            punkt_n = m.group(5)      # "1"

            all_nums = [first_num] + re.findall(r'(\d+(?:-\d+)?)\)', extra)

            # Ищем якорь пункта
            punkt_anchor = subpoint_map.get(f'{current_article}_{punkt_n}')

            link_parts = []
            for i, num in enumerate(all_nums):
                anchor = subpoint_map.get(f'{current_article}_{punkt_n}_{num}') or \
                         subpoint_map.get(f'{current_article}_{num}')
                if i == 0:
                    link_text = f'{subp_word} {num})'
                    if anchor:
                        link_parts.append(make_link(link_text, anchor, doc_id, base_url))
                    else:
                        link_parts.append(link_text)
                else:
                    sep_m = re.search('(' + SEP_PAT + ')' + re.escape(num) + r'\)', extra)
                    sep = sep_m.group(1) if sep_m else ', '
                    link_parts.append(sep)
                    if anchor:
                        link_parts.append(make_link(f'{num})', anchor, doc_id, base_url))
                    else:
                        link_parts.append(f'{num})')

            # "пункта M"
            if punkt_anchor:
                link_parts.append(f' {make_link(f"{punkt_word} {punkt_n}", punkt_anchor, doc_id, base_url)}')
            else:
                link_parts.append(f' {punkt_word} {punkt_n}')

            # Восстанавливаем хвост: "настоящей статьи/части"
            tail_m = re.search(r'\s+настоящей\s+(?:статьи|части|пункта)', m.group(0), re.IGNORECASE)
            link_parts.append(tail_m.group(0) if tail_m else ' настоящей статьи')

            new_html = ''.join(link_parts)
            full_match = m.group(0)
            replacements.append((m.start(), m.end(), full_match, new_html, f'{current_article}_s{punkt_n}'))

    # === Голые номера статей в перечислениях ===
    has_article_context = allow_bare_numbers or re.search(r'стать|в статьях', result, re.IGNORECASE)
    if has_article_context:
        BARE_NUM_PATTERN = re.compile(
            r'(?:,\s*|;\s*|\s+и\s+)'   # перед числом: запятая, точка с запятой, или "и"
            r'(\d+(?:-\d+)?)'           # число: 125, 188-1, 214-2
            r'(?=\s|,|;|\(| –| -|$)'   # после числа: пробел, запятая, скобка, тире (НЕ ")")
        )
        # Месяцы и слова-маркеры, после которых число — точно дата/срок, а не статья
        DATE_AFTER_RE = re.compile(
            r'^\s+(?:янв|фев|мар|апр|мая|июн|июл|авг|сен|окт|ноя|дек|год|лет|месяц|раб|кален|процент)',
            re.IGNORECASE
        )
        # Паттерн для определения "пунктного" контекста
        PUNKT_CONTEXT = re.compile(
            r'(?:под)?пункт(?:ами|ом|а|е|у)?\s+\d+(?:-\d+)?\)',
            re.IGNORECASE
        )
        for m in BARE_NUM_PATTERN.finditer(result):
            art_num = m.group(1)
            num_start = m.start(1)
            num_end = m.end(1)
            overlaps = any(r[0] < num_end and r[1] > num_start for r in replacements)
            if overlaps:
                continue
            # Если после числа идёт месяц/год/процент — это дата/сумма, а не статья
            if DATE_AFTER_RE.match(result[num_end:num_end + 20]):
                continue
            # Если непосредственно ПЕРЕД разделителем стоит цифра — это
            # десятичная дробь ("6,19", "4,8") а не перечисление статей.
            sep_start = m.start()
            if sep_start > 0 and result[sep_start - 1].isdigit():
                continue
            if art_num in article_map:
                ctx_start = max(0, num_start - 100)
                context_before = result[ctx_start:num_start]
                if PUNKT_CONTEXT.search(context_before):
                    last_punkt = list(PUNKT_CONTEXT.finditer(context_before))
                    if last_punkt:
                        after_punkt = context_before[last_punkt[-1].end():]
                        if not re.search(r'стать', after_punkt, re.IGNORECASE):
                            # Дополнительная проверка: если сразу после "пунктом N)"
                            # идёт "части" — это описатель предыдущей статьи (формат
                            # "N (пунктом M) части..."), число является статьёй.
                            abs_punkt_end = ctx_start + last_punkt[-1].end()
                            immediately_after = result[abs_punkt_end:abs_punkt_end + 20]
                            if re.match(r'\s+части', immediately_after, re.IGNORECASE):
                                pass  # это описатель — число является статьёй
                            else:
                                continue  # пропускаем — это номер пункта, не статьи
                anchor = article_map[art_num]
                link = make_link(art_num, anchor, doc_id, base_url)
                replacements.append((num_start, num_end, art_num, link, art_num))

    replacements.sort(key=lambda x: x[0], reverse=True)
    for start, end, original, link, art_num in replacements:
        # ЛЕЧЕНИЕ 2026-06-10: замена обязана сохранять видимый текст байт-в-байт
        # (без тегов/пробелов); иначе пропуск — это и был источник порчи диапазонов
        if _vis(link) != _vis(result[start:end]):
            changes.append({"original": original, "article": art_num,
                            "anchor": "SKIPPED_INVARIANT", "link": link})
            continue
        result = result[:start] + link + result[end:]
        changes.append({
            "original": original,
            "article": art_num,
            "anchor": article_map.get(art_num, "?"),
            "link": link
        })

    return result, changes


# Паттерн: "подпунктом 9) " или "подпунктами 1), 18) " или "подпунктами 1) – 4) " — перед существующей <a> ссылкой
_TRAILING_SUBP_RE = re.compile(
    r'(подпункт(?:ом|а|е|у|ами|ах|ов)?)\s+'
    r'(\d+(?:-\d+)?)\)'
    r'((?:(?:\s*,\s*|\s*[–—-]\s*|\s+и\s+)\d+(?:-\d+)?\))*)\s*$',
    re.IGNORECASE
)


def _fix_subpoint_prefixes(soup, subpoint_map, doc_id, base_url, skip_snoska,
                           art_heading_re=None):
    """
    Второй проход: ищет текстовые узлы вида "подпунктом 9) " которые заканчиваются
    прямо перед уже существующей ссылкой <a href="...#zART">пункта N</a>.
    Оборачивает "подпунктом 9)" в ссылку — слово "подпунктом" включается в ссылку.
    Также обрабатывает "настоящей статьи" (самоссылки) используя контекст текущей статьи.
    """
    changes = []
    for text_node in soup.find_all(string=True):
        if is_inside_link(text_node):
            continue
        if skip_snoska and is_in_snoska(text_node):
            continue

        txt = str(text_node)
        m = _TRAILING_SUBP_RE.search(txt)
        if not m:
            continue

        subp_word = m.group(1)   # "подпунктом"
        subp_n = m.group(2)      # "9"
        extra = m.group(3)       # ", 18), 20)" или ""

        # Обходим следующие сиблинги чтобы найти "пункта N" и "статьи N"
        punkt_n = None
        art_n = None
        is_self_ref = False   # True если "настоящей статьи" — самоссылка
        sib = text_node.next_sibling
        while sib and art_n is None:
            if getattr(sib, 'name', None) == 'a':
                sib_text = sib.get_text()
                if re.search(r'стать', sib_text, re.IGNORECASE):
                    # Извлекаем номер статьи из ТЕКСТА ссылки (а не из href, т.к.
                    # anchor #zNNN не совпадает с номером статьи).
                    at_m = re.search(r'стать\w*\s+(\d+(?:-\d+)?)', sib_text, re.IGNORECASE)
                    if at_m:
                        art_n = at_m.group(1)
                    else:
                        # fallback: пробуем #z{num}, если anchor совпадает с номером
                        href = sib.get('href', '')
                        art_m = re.search(r'#z(\d+(?:-\d+)?)$', href)
                        if art_m:
                            art_n = art_m.group(1)
                elif re.search(r'пункт', sib_text, re.IGNORECASE) and punkt_n is None:
                    pt_m = re.search(r'пункт\w*\s+(\d+(?:-\d+)?)', sib_text, re.IGNORECASE)
                    if pt_m:
                        punkt_n = pt_m.group(1)
            elif isinstance(sib, str) and sib.strip():
                pt_m = re.search(r'пункт\w*\s+(\d+(?:-\d+)?)', sib, re.IGNORECASE)
                if pt_m and punkt_n is None:
                    punkt_n = pt_m.group(1)
                at_m = re.search(r'стать\w+\s+(\d+(?:-\d+)?)', sib, re.IGNORECASE)
                if at_m:
                    art_n = at_m.group(1)
                elif re.search(r'настоящей\s+стать', sib, re.IGNORECASE):
                    # Самоссылка: "настоящей статьи" без явного номера
                    is_self_ref = True
                    art_n = '__self__'  # временный маркер
            sib = getattr(sib, 'next_sibling', None)
            if sib and sib.parent != text_node.parent:
                break

        # Для самоссылок: определяем текущую статью из контекста
        if is_self_ref and art_n == '__self__' and art_heading_re:
            current_art = _get_current_article(text_node, art_heading_re)
            if current_art:
                art_n = current_art
            else:
                art_n = None

        if not art_n:
            continue

        subp_anchor = None
        if punkt_n:
            subp_anchor = subpoint_map.get(f'{art_n}_{punkt_n}_{subp_n}')
        if not subp_anchor:
            subp_anchor = subpoint_map.get(f'{art_n}_{subp_n}')
        if not subp_anchor:
            # Фолбэк: если у статьи всего один (неявный) пункт — подпункты
            # лежат под "1": "{art}_1_{subp}".
            subp_anchor = subpoint_map.get(f'{art_n}_1_{subp_n}')
            if subp_anchor and not punkt_n:
                # Используем неявный пункт 1 для последующих перечислений
                punkt_n = '1'

        if not subp_anchor:
            # Фолбэк для внешних доков: нет subpoint_map → расширяем существующий
            # следующий <a> так, чтобы он включал префикс "подпунктами N), M) ".
            # Этим достигается «одна объединённая ссылка» для внешних кодексов/законов.
            ext_a = None
            cur = text_node.next_sibling
            steps = 0
            while cur is not None and steps < 4:
                if getattr(cur, 'name', None) == 'a':
                    ext_a = cur
                    break
                if isinstance(cur, str) and cur.strip():
                    break
                cur = getattr(cur, 'next_sibling', None)
                steps += 1
            if ext_a is None:
                continue
            # Перед существующей <a> вырезаем "подпунктом N) ..." из текстового
            # узла и переносим в начало <a>.
            prefix_text = txt[m.start():]   # "подпунктом N), M) "
            txt_before = txt[:m.start()]
            text_node.replace_with(BeautifulSoup(txt_before, 'html.parser'))
            # Вставляем prefix_text в начало содержимого ext_a
            ext_a.insert(0, prefix_text)
            changes.append({'original': prefix_text, 'article': art_n, 'anchor': ext_a.get('href', ''), 'link': str(ext_a)})
            continue

        all_nums = [subp_n] + re.findall(r'(\d+(?:-\d+)?)\)', extra)

        before = txt[:m.start()]
        linked_parts = []
        for i, num in enumerate(all_nums):
            anchor = subpoint_map.get(f'{art_n}_{punkt_n}_{num}') if punkt_n else None
            if not anchor:
                anchor = subpoint_map.get(f'{art_n}_{num}')

            if i == 0:
                # Включаем слово "подпунктом" в ссылку — единообразный стиль
                if not anchor:
                    linked_parts.append(f'{subp_word} {num})')
                else:
                    linked_parts.append(make_link(f'{subp_word} {num})', anchor, doc_id, base_url))
            else:
                sep_m = re.search('(' + SEP_PAT + ')' + re.escape(num) + r'\)', extra)
                sep = sep_m.group(1) if sep_m else ', '
                if not anchor:
                    linked_parts.append(f'{sep}{num})')
                else:
                    linked_parts.append(sep)
                    linked_parts.append(make_link(f'{num})', anchor, doc_id, base_url))

        new_html = before + ''.join(linked_parts) + ' '
        new_node = BeautifulSoup(new_html, 'html.parser')
        text_node.replace_with(new_node)
        changes.append({'original': f'{subp_word} {subp_n}){extra}', 'article': art_n, 'anchor': subp_anchor, 'link': new_html})

    return changes


# Паттерн для "пунктом N-N" как отдельного текстового узла в конце
_ORPHAN_PUNKT_RE = re.compile(
    r'(?:(?:,\s*)|(?:^\s*))'
    r'(пункт(?:а|е|у|ом|ами)?)\s+'
    r'(\d+(?:-\d+)?)'
    r'\s*$',
    re.IGNORECASE
)

# Паттерн: "части N-N" в конце текстового узла перед <a>статьи N</a>
_ORPHAN_CHASTI_RE = re.compile(
    r'(част[ьюие]\w*)\s+'
    r'(\d+-\d+)'
    r'\s*$',
    re.IGNORECASE
)


def _get_next_art_sibling(text_node, article_map):
    """Ищет следующий <a>статьи N</a> среди сиблингов. Возвращает номер статьи или None."""
    sib = text_node.next_sibling
    steps = 0
    while sib and steps < 5:
        steps += 1
        if getattr(sib, 'name', None) == 'a':
            sib_text = sib.get_text()
            if re.search(r'стать', sib_text, re.IGNORECASE):
                art_num_m = re.search(r'(\d+(?:-\d+)?)\s*$', sib_text)
                if art_num_m:
                    art_n = art_num_m.group(1)
                    if art_n in article_map:
                        return art_n
        sib = getattr(sib, 'next_sibling', None)
    return None


def _fix_orphan_punkt_refs(soup, article_map, subpoint_map, doc_id, base_url, skip_snoska, part_anchor_map=None):
    """
    Третий проход: ищет текстовые узлы вида ", пунктом 1-1" или "части 2-1" которые
    заканчиваются прямо перед уже существующей ссылкой <a href="...#zART">статьи N</a>.
    """
    changes = []
    for text_node in soup.find_all(string=True):
        if is_inside_link(text_node):
            continue
        if skip_snoska and is_in_snoska(text_node):
            continue

        txt = str(text_node)

        # Паттерн 1: "пунктом N-N" в конце
        m = _ORPHAN_PUNKT_RE.search(txt)
        if m:
            punkt_word = m.group(1)
            punkt_n = m.group(2)
            art_n = _get_next_art_sibling(text_node, article_map)
            if art_n:
                punkt_anchor = subpoint_map.get(f'{art_n}_{punkt_n}') or article_map[art_n]
                before = txt[:m.start()]
                sep = txt[m.start():m.start(1)]
                linked = sep + make_link(f'{punkt_word} {punkt_n}', punkt_anchor, doc_id, base_url)
                new_html = before + linked
                new_node = BeautifulSoup(new_html, 'html.parser')
                text_node.replace_with(new_node)
                changes.append({'original': txt, 'article': art_n, 'anchor': punkt_anchor, 'link': new_html})
                continue

        # Паттерн 2: "части N-N" в конце (напр. "части 2-1 статьи 43")
        m2 = _ORPHAN_CHASTI_RE.search(txt)
        if m2:
            chasti_word = m2.group(1)
            part_n = m2.group(2)
            art_n = _get_next_art_sibling(text_node, article_map)
            if art_n:
                # Ищем якорь части: сначала в part_anchor_map, потом в subpoint_map, потом в article_map
                part_anchor = (
                    (part_anchor_map.get((art_n, part_n)) if part_anchor_map else None)
                    or subpoint_map.get(f'{art_n}_{part_n}')
                    or article_map[art_n]
                )
                before = txt[:m2.start()]
                sep = txt[m2.start():m2.start(1)]
                linked = sep + make_link(f'{chasti_word} {part_n}', part_anchor, doc_id, base_url)
                new_html = before + linked
                new_node = BeautifulSoup(new_html, 'html.parser')
                text_node.replace_with(new_node)
                changes.append({'original': txt, 'article': art_n, 'anchor': part_anchor, 'link': new_html})

    return changes


# Паттерн для "подпунктом N) пункта M" в конце текстового узла (перед готовой <a>статьи N</a>)
_ORPHAN_SUBP_PUNKT_RE = re.compile(
    r'(подпункт(?:ом|а|е|у|ами|ах)?)\s+'
    r'(\d+(?:-\d+)?)\)'
    r'((?:(?:\s*,\s*|\s+и\s+)\d+(?:-\d+)?\))*)'
    r'\s+(пункт(?:а|е|у|ом|ами)?)\s+'
    r'(\d+(?:-\d+)?)'
    r'\s*$',
    re.IGNORECASE
)


def _fix_orphan_subp_punkt_refs(soup, article_map, subpoint_map, doc_id, base_url, skip_snoska):
    """
    Пятый проход: ищет текстовые узлы вида "подпунктом N) пункта M" которые заканчиваются
    прямо перед уже существующей ссылкой <a href="...#zART">статьи N</a>.
    Оборачивает "подпунктом N)" и "пункта M" в ссылки.
    """
    changes = []
    for text_node in soup.find_all(string=True):
        if is_inside_link(text_node):
            continue
        if skip_snoska and is_in_snoska(text_node):
            continue

        txt = str(text_node)
        m = _ORPHAN_SUBP_PUNKT_RE.search(txt)
        if not m:
            continue

        subp_word = m.group(1)    # "подпунктом"
        subp_n = m.group(2)       # "1"
        extra = m.group(3)        # "" или ", 2)"
        punkt_word = m.group(4)   # "пункта"
        punkt_n = m.group(5)      # "1-1"

        # Ищем следующую ссылку на статью среди сиблингов
        art_n = None
        sib = text_node.next_sibling
        steps = 0
        while sib and art_n is None and steps < 5:
            steps += 1
            if getattr(sib, 'name', None) == 'a':
                sib_text = sib.get_text()
                if re.search(r'стать', sib_text, re.IGNORECASE):
                    art_m = re.search(r'(\d+(?:-\d+)?)\s*$', sib_text)
                    if art_m:
                        art_n = art_m.group(1)
            sib = getattr(sib, 'next_sibling', None)

        if not art_n or art_n not in article_map:
            continue

        all_nums = [subp_n] + re.findall(r'(\d+(?:-\d+)?)\)', extra)

        # Якорь пункта
        punkt_anchor = subpoint_map.get(f'{art_n}_{punkt_n}') or article_map[art_n]

        before = txt[:m.start()]
        link_parts = []
        for i, num in enumerate(all_nums):
            anchor = subpoint_map.get(f'{art_n}_{punkt_n}_{num}') or \
                     subpoint_map.get(f'{art_n}_{num}') or \
                     artikel_anchor if (artikel_anchor := article_map.get(art_n)) else None
            if i == 0:
                if anchor:
                    link_parts.append(make_link(f'{subp_word} {num})', anchor, doc_id, base_url))
                else:
                    link_parts.append(f'{subp_word} {num})')
            else:
                sep_m = re.search('(' + SEP_PAT + ')' + re.escape(num) + r'\)', extra)
                sep = sep_m.group(1) if sep_m else ', '
                link_parts.append(sep)
                if anchor:
                    link_parts.append(make_link(f'{num})', anchor, doc_id, base_url))
                else:
                    link_parts.append(f'{num})')

        link_parts.append(' ')
        link_parts.append(make_link(f'{punkt_word} {punkt_n}', punkt_anchor, doc_id, base_url))

        new_html = before + ''.join(link_parts)
        new_node = BeautifulSoup(new_html, 'html.parser')
        text_node.replace_with(new_node)
        changes.append({'original': txt, 'article': art_n, 'anchor': punkt_anchor, 'link': new_html})

    return changes


def _get_current_article(text_node, art_heading_re):
    """Определяет номер статьи для данного текстового узла по предшествующим h3/b тегам."""
    el = text_node.parent
    while el:
        # УК: <h3 id="zN"> Статья N.
        if el.name == 'h3':
            m = art_heading_re.search(el.get_text())
            if m:
                return m.group(1)
        # Поднимаемся выше — ищем предыдущий h3 среди сиблингов
        # Перебираем предыдущих сиблингов родителя
        if el.parent:
            for prev in el.previous_siblings:
                if getattr(prev, 'name', None) == 'h3':
                    m = art_heading_re.search(prev.get_text() if hasattr(prev, 'get_text') else '')
                    if m:
                        return m.group(1)
                # Трудовой: <p><b><a name="zN"></a>Статья N.
                if getattr(prev, 'name', None) == 'p':
                    b = prev.find('b') if hasattr(prev, 'find') else None
                    if b and b.find('a', attrs={'name': True}):
                        m = art_heading_re.search(b.get_text())
                        if m:
                            return m.group(1)
        if el.name in ('body', 'article', 'html'):
            break
        el = el.parent
    return None


def _get_current_part(text_node):
    """Определяет номер текущей части/пункта из контекста параграфа.

    Способы определения, по приоритету:
    1. Текст самого <p> начинается с "N." -> это пункт N.
    2. id самого <p> вида z{art}_{part}_{subpart} -> пункт = part.
    3. Просматриваем предыдущих сиблингов <p>: если у кого-то id вида
       z{art}_{part}_{subpart} (подпункт) — берём part. Если у кого-то текст
       начинается с "N." — берём N. Это нужно для "завершающих" параграфов
       пункта, которые сами не содержат номера (например, после списка
       подпунктов идёт обобщающее предложение).

    Поиск ограничен той же статьёй: останавливаемся, если встретили <p>/<b>
    с заголовком "Статья N." — это переход в предыдущую статью.
    """
    el = text_node.parent
    SUBP_ID_RE = re.compile(r'^z\d+(?:-\d+)?_(\d+(?:-\d+)?)_\d+(?:-\d+)?$')
    PUNKT_PREFIX_RE = re.compile(r'^\s*(\d+(?:-\d+)?)\.\s')
    ARTICLE_HEADING_RE = re.compile(r'^\s*Статья\s+\d+')

    # 1-2: проверяем сам <p>
    while el:
        if el.name == 'p':
            text = el.get_text().strip()
            m = PUNKT_PREFIX_RE.match(text)
            if m:
                return m.group(1)
            pid = el.get('id', '')
            m2 = SUBP_ID_RE.match(pid)
            if m2:
                return m2.group(1)
            break  # нашли <p>, дальше будем смотреть его сиблингов
        if el.name in ('body', 'article'):
            return None
        el = el.parent

    if not el or el.name != 'p':
        return None

    # 3: смотрим предыдущих сиблингов
    sib = el.previous_sibling
    while sib is not None:
        name = getattr(sib, 'name', None)
        if name in ('h1', 'h2', 'h3', 'h4'):
            # Заголовок главы/статьи — стоп
            return None
        if name == 'p':
            sib_text = sib.get_text().strip() if hasattr(sib, 'get_text') else ''
            # Заголовок статьи: <p><b>Статья N. ...</b></p>
            b = sib.find('b') if hasattr(sib, 'find') else None
            if b and ARTICLE_HEADING_RE.match(b.get_text().strip()):
                return None
            # Подпункт: id вида z{art}_{part}_{subpart}
            pid = sib.get('id', '')
            m = SUBP_ID_RE.match(pid)
            if m:
                return m.group(1)
            # Параграф начинается с "N." — это пункт N
            m2 = PUNKT_PREFIX_RE.match(sib_text)
            if m2:
                return m2.group(1)
        sib = sib.previous_sibling
    return None


_SWEEP_ARTICLE_RE = re.compile(
    r'стат(?:ь[яиейюёямих]+|ей)\s+(\d+(?:-\d+)?)(?!\d)'
    r'(?=\s+настоящ(?:его|ей|им|ему))',
    re.IGNORECASE,
)


def _sweep_remaining_articles(soup, article_map, doc_id, base_url, skip_snoska, art_heading_re=None):
    """Final pass: in any remaining text node, find 'статья(N)... настоящ(...)'
    and wrap N in <a>. Avoids text inside <a>, inside article headers (<b>Статья N. ...</b>),
    inside snoska. Avoids double-linking via per-node replacement.
    """
    changes = []
    for text_node in soup.find_all(string=True):
        if is_inside_link(text_node):
            continue
        if is_article_heading(text_node):
            continue
        if skip_snoska and is_in_snoska(text_node):
            continue
        txt = str(text_node)
        if not txt or len(txt) < 8:
            continue
        # collect matches
        repls = []
        for m in _SWEEP_ARTICLE_RE.finditer(txt):
            art_num = m.group(1)
            if art_num not in article_map:
                continue
            full = m.group(0)  # "статьи 220"
            repls.append((m.start(), m.end(), full, art_num))
        if not repls:
            continue
        # apply replacements
        new_html_parts = []
        last = 0
        for start, end, full, art_num in repls:
            new_html_parts.append(txt[last:start])
            anchor = article_map[art_num]
            new_html_parts.append(make_link(full, anchor, doc_id, base_url))
            last = end
            changes.append({"original": full, "article": art_num, "anchor": anchor})
        new_html_parts.append(txt[last:])
        new_html = ''.join(new_html_parts)
        new_soup = BeautifulSoup(new_html, "html.parser")
        text_node.replace_with(new_soup)
    return changes


def fix_html(html_path, article_map, doc_id, base_url, skip_snoska=True, subpoint_map=None,
             part_anchor_map=None, chapter_map=None):
    with open(html_path, "rb") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    for tag in soup.find_all(["script", "style", "template", "veepn-lock-screen"]):
        tag.decompose()

    if part_anchor_map is None:
        part_anchor_map = {}
    if chapter_map is None:
        chapter_map = {}

    all_changes = []

    # Паттерн для заголовков статей
    ART_HEADING_RE = re.compile(r'Статья\s+(\d+(?:-\d+)?)', re.IGNORECASE)

    text_nodes = []
    for text_node in soup.find_all(string=True):
        if is_inside_link(text_node):
            continue
        if is_article_heading(text_node):
            continue
        if skip_snoska and is_in_snoska(text_node):
            continue
        if len(str(text_node).strip()) < 3:
            continue
        text_nodes.append(text_node)

    for text_node in text_nodes:
        original_text = str(text_node)

        # Контекст для голых номеров
        allow_bare = False
        parent_block = text_node.parent
        if parent_block:
            parent_text = parent_block.get_text() if parent_block.name else ""
            if re.search(r'стать|в статьях', parent_text, re.IGNORECASE):
                allow_bare = True

        # Определяем текущую статью и часть для self-reference паттернов
        current_article = _get_current_article(text_node, ART_HEADING_RE) if part_anchor_map else None
        current_part = _get_current_part(text_node) if (subpoint_map and current_article) else None

        new_text, changes = process_text_node(
            original_text, article_map, doc_id, base_url,
            allow_bare_numbers=allow_bare,
            subpoint_map=subpoint_map,
            current_article=current_article,
            part_anchor_map=part_anchor_map,
            current_part=current_part,
            chapter_map=chapter_map,
        )
        if changes:
            new_soup = BeautifulSoup(new_text, "html.parser")
            text_node.replace_with(new_soup)
            for c in changes:
                c["context"] = original_text[:100].strip()
            all_changes.extend(changes)

    # === Второй проход: "подпунктом N)" перед уже готовыми ссылками ===
    if subpoint_map:
        all_changes.extend(_fix_subpoint_prefixes(
            soup, subpoint_map, doc_id, base_url, skip_snoska,
            art_heading_re=ART_HEADING_RE
        ))

    # === Третий проход: "пунктом N-N" / "части N-N" перед уже готовой ссылкой на статью ===
    all_changes.extend(_fix_orphan_punkt_refs(soup, article_map, subpoint_map or {}, doc_id, base_url, skip_snoska, part_anchor_map=part_anchor_map))

    # === Пятый проход: "подпунктом N) пункта M" перед уже готовой ссылкой на статью ===
    all_changes.extend(_fix_orphan_subp_punkt_refs(soup, article_map, subpoint_map or {}, doc_id, base_url, skip_snoska))

    # === Шестой проход (sweep): "статья N настоящего Кодекса" — намерение
    # покрыть кейсы UPK типа "частями 13-1, 13-3 и 13-4 статьи 220 настоящего
    # Кодекса" (только сама "статьи 220" без линка). Временно отключено: вызывал
    # деградацию производительности на крупных файлах (UPK, КоАП).
    # TODO: переписать через сериализацию + один глобальный re.sub по строке.
    pass  # _sweep_remaining_articles(soup, article_map, doc_id, base_url, skip_snoska)

    # Добавляем id к <a name="zN"> для CSS :target
    for a_tag in soup.find_all("a", attrs={"name": True}):
        name_val = a_tag["name"]
        if re.match(r'^z\d+', name_val) and not a_tag.get("id"):
            existing = soup.find(id=name_val)
            if not existing:
                a_tag["id"] = name_val

    return soup, all_changes


def build_part_anchor_map(html_path):
    """
    Строит маппинг (art_num, part_num) -> anchor_id для всех параграфов N-N.
    Используется для линковки "3-1 настоящей статьи" -> id параграфа "3-1." внутри статьи.
    """
    with open(html_path, "rb") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    part_anchor_map = {}
    ART_HEADING_RE = re.compile(r'Статья\s+(\d+(?:-\d+)?)', re.IGNORECASE)

    all_tags = list(soup.find_all(['p', 'h3', 'div']))
    current_article = None

    for tag in all_tags:
        # Определяем текущую статью
        if tag.name == 'h3':
            m = ART_HEADING_RE.search(tag.get_text())
            if m:
                current_article = m.group(1)
                continue
        if tag.name == 'p':
            b = tag.find('b')
            if b and b.find('a', attrs={'name': True}):
                m = ART_HEADING_RE.search(b.get_text())
                if m:
                    current_article = m.group(1)
                    continue

        if not current_article:
            continue

        # Ищем параграфы начинающиеся с "N." или "N-N." (пункты статьи)
        if tag.name == 'p' and tag.get('id'):
            text = tag.get_text().strip()
            # N-N. (с дефисом: "3-1.", "1-1.")
            m = re.match(r'^\s*(\d+-\d+)\.', text)
            if m:
                part_num = m.group(1)
                part_anchor_map[(current_article, part_num)] = tag['id']
                continue
            # N. (обычный пункт: "1.", "2.", "3.")
            m2 = re.match(r'^\s*(\d+)\.(?!\d)', text)
            if m2:
                part_num = m2.group(1)
                # Не перезаписываем если уже есть (первый встреченный пункт N приоритетнее)
                if (current_article, part_num) not in part_anchor_map:
                    part_anchor_map[(current_article, part_num)] = tag['id']

    return part_anchor_map


def build_chapter_map(html_path):
    """
    Строит маппинг глава_N -> anchor_id из h3-заголовков глав.
    """
    with open(html_path, "rb") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    chapter_map = {}
    CHAPTER_HEAD_RE = re.compile(r'[Гг]лава\s+(\d+(?:-\d+)?)', re.IGNORECASE)
    for tag in soup.find_all(['h2', 'h3', 'h4']):
        m = CHAPTER_HEAD_RE.search(tag.get_text())
        if m and tag.get('id'):
            ch_num = m.group(1)
            if ch_num not in chapter_map:
                chapter_map[ch_num] = tag['id']
    # Also check <a name="..."> inside p>b heading
    for tag in soup.find_all('p'):
        b = tag.find('b')
        if b:
            a = b.find('a', attrs={'name': True})
            if a:
                m = CHAPTER_HEAD_RE.search(b.get_text())
                if m:
                    ch_num = m.group(1)
                    anchor = a.get('id') or a.get('name')
                    if anchor and ch_num not in chapter_map:
                        chapter_map[ch_num] = anchor
    return chapter_map


def main():
    ap = argparse.ArgumentParser(description="Фиксит внутренние ссылки на статьи в HTML кодекса")
    ap.add_argument("--input", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--doc-id", required=True)
    ap.add_argument("--base-url", default="http://85.202.192.66:9096")
    ap.add_argument("--output", required=True)
    ap.add_argument("--report", default="fix_report.csv")
    ap.add_argument("--include-snoska", action="store_true")
    ap.add_argument("--subpoint-map", default=None, help="JSON маппинг подпунктов (из скрипта 07)")
    args = ap.parse_args()

    with open(args.map, "r", encoding="utf-8") as f:
        article_map = json.load(f)

    subpoint_map = {}
    if args.subpoint_map:
        with open(args.subpoint_map, "r", encoding="utf-8") as f:
            subpoint_map = json.load(f)
        print(f"Загружен маппинг подпунктов: {len(subpoint_map)} записей")

    # Строим маппинг параграфов N-N для self-reference паттернов
    part_anchor_map = build_part_anchor_map(args.input)
    print(f"Загружен маппинг параграфов N-N: {len(part_anchor_map)} записей")

    # Строим маппинг глав
    chapter_map = build_chapter_map(args.input)
    print(f"Загружен маппинг глав: {len(chapter_map)} глав")

    print(f"Загружен маппинг: {len(article_map)} статей")
    print(f"Обрабатываю: {args.input}")
    print(f"Doc ID: {args.doc_id}")
    print(f"Base URL: {args.base_url}")
    print(f"Сноски: {'включены' if args.include_snoska else 'пропускаются'}")
    print()

    fixed_soup, changes = fix_html(
        args.input, article_map, args.doc_id, args.base_url,
        skip_snoska=not args.include_snoska,
        subpoint_map=subpoint_map,
        part_anchor_map=part_anchor_map,
        chapter_map=chapter_map,
    )

    # CSS + JS подсветка
    TARGET_HIGHLIGHT = """
<style>
:target { background-color: #FFFF88 !important; padding: 4px 8px; transition: background-color 0.3s ease; }
h3:target { background-color: #FFFF88 !important; padding: 4px 8px; border-radius: 4px; }
.highlight-target { background-color: #FFFF88 !important; padding: 4px 8px; border-radius: 4px; transition: background-color 0.3s ease; }
</style>
<script>
function highlightTarget() {
    document.querySelectorAll('.highlight-target').forEach(function(el) { el.classList.remove('highlight-target'); });
    var hash = window.location.hash.substring(1);
    if (!hash) return;
    var target = document.getElementById(hash) || document.querySelector('a[name="' + hash + '"]');
    if (!target) return;
    var el = target;
    while (el && !['P', 'H3', 'H2', 'DIV', 'ARTICLE'].includes(el.tagName)) { el = el.parentElement; }
    if (el) el.classList.add('highlight-target');
}
window.addEventListener('hashchange', highlightTarget);
window.addEventListener('load', highlightTarget);
document.addEventListener('click', function(e) {
    var a = e.target.closest('a');
    if (a && a.hash) { setTimeout(highlightTarget, 50); }
});
</script>
"""

    # ЛЕЧЕНИЕ 2026-06-10: файловый гейт — текст входа должен == тексту выхода
    _src_txt = "".join(BeautifulSoup(open(args.input, encoding="utf-8").read(),
                                     "html.parser").get_text().split())
    _out_txt = "".join(fixed_soup.get_text().split())
    if _src_txt != _out_txt:
        raise SystemExit("ГЕЙТ 02: get_text ИЗМЕНИЛСЯ — вывод НЕ записан "
                         "(см. шапку файла, лечение 2026-06-10)")

    html_str = str(fixed_soup)
    if "<head>" in html_str:
        html_str = html_str.replace("<head>", "<head>" + TARGET_HIGHLIGHT, 1)
    elif "<body>" in html_str:
        html_str = html_str.replace("<body>", TARGET_HIGHLIGHT + "<body>", 1)
    else:
        html_str = TARGET_HIGHLIGHT + html_str

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_str)

    print(f"Исправлено ссылок: {len(changes)}")
    print(f"Результат: {args.output}")

    if changes:
        with open(args.report, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["original", "article", "anchor", "link", "context"])
            w.writeheader()
            w.writerows(changes)
        print(f"Отчёт: {args.report}")

        articles_fixed = set(c["article"] for c in changes)
        print(f"\nУникальных статей затронуто: {len(articles_fixed)}")
        print(f"Топ-10 самых частых:")
        from collections import Counter
        counter = Counter(c["article"] for c in changes)
        for art, cnt in counter.most_common(10):
            print(f"  Статья {art}: {cnt} ссылок добавлено")
    else:
        print("Ничего не найдено для исправления!")


if __name__ == "__main__":
    main()
