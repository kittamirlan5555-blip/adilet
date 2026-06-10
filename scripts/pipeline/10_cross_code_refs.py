"""
Скрипт 10: Cross-code references — единые гиперссылки на чужие НПА

Линкует фразы вида:
    "статьей 820 Налогового кодекса Республики Казахстан"
    "пунктом 1 статьи 822 Налогового кодекса Республики Казахстан"
    "подпунктом 2) пункта 1 статьи 400 Налогового кодекса Республики Казахстан"
    "статьями 249-257 Налогового кодекса Республики Казахстан"
    "статьями 13, 14 и 15 Закона Республики Казахстан «О теплоэнергетике»"
    "главой 94 Налогового кодекса Республики Казахстан"
    "статьи 256 Гражданского кодекса Республики Казахстан"

В ОДНУ объединённую ссылку <a href="DOC#zN">вся фраза</a>.

Источники маппинга:
    config/codes.json        — реестр кодексов (doc_id)
    config/npa_mapping.json  — все формы названий внешних НПА → doc_id
    data/maps/article_map_*.json — статья → якорь для каждого кодекса

Скрипт ставит ссылки ПЕРЕД скриптом 02 (внутренние ссылки) и скриптом 03
(голые названия НПА), чтобы избежать пересечения с уже линкованными участками.

Использование:
    python scripts/10_cross_code_refs.py \
        --input data/socialnyy_anchored.html \
        --output data/socialnyy_xref.html \
        --codes-config config/codes.json \
        --npa-map config/npa_mapping.json \
        --maps-dir data/maps
"""

import re
import json
import argparse
import sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

BASE_URL = "https://adilet.zan.kz"


# === ГРАММАТИЧЕСКИЕ ОКОНЧАНИЯ (все падежи) ===
# стат(ья|ьи|ье|ью|ьей|ьёй|ьями|ьях|ьям) + стат-ей (genitive plural без ь)
# Класс окончаний включает «й» (стат-ьей), «м» (стат-ьям), «х» (стат-ьях).
STAT_WORD = r"(?:стат(?:ь[яиеуюёямихй]+|ей))"
# пункт + варианты окончаний (пункт, пункта, пункте, пункту, пунктом, пункты, пунктов, пунктами, пунктах)
PUNKT_WORD = r"(?:пункт(?:[аеуыом]|ом|ов|ами|ах)?)"
# подпункт + варианты
SUBP_WORD = r"(?:подпункт(?:[аеуыом]|ом|ов|ами|ах)?)"
# глав + варианты (глава, главе, главы, главу, главой, главами, главах)
GLAVA_WORD = r"(?:глав(?:[аеыу]|ой|ами|ах))"
# част + варианты (часть, части, частью, частей, частям, частями, частях)
CHAST_WORD = r"(?:част(?:ь|и|ью|ей|ям|ями|ях)?)"

# === HELPERS ===

def is_inside_link(node):
    p = node.parent if hasattr(node, "parent") else None
    while p:
        if getattr(p, "name", None) == "a":
            return True
        p = p.parent
    return False


def is_in_snoska(node):
    p = node.parent if hasattr(node, "parent") else None
    while p:
        if getattr(p, "name", None) == "span" and "note" in (p.get("class") or []):
            return True
        if getattr(p, "name", None) == "font":
            color = (p.get("color") or "").upper().strip().lstrip("#")
            if color == "FF0000":
                txt = p.get_text()
                if "ИЗПИ" in txt or "РЦПИ" in txt:
                    return True
        if getattr(p, "name", None) in ("body", "article"):
            break
        p = p.parent
    return False


def is_article_heading(node):
    p = node.parent if hasattr(node, "parent") else None
    while p:
        if getattr(p, "name", None) == "b":
            if hasattr(p, "find") and p.find("a", attrs={"name": True}):
                return True
            return False
        if getattr(p, "name", None) in ("h1", "h2", "h3", "h4", "h5", "h6"):
            return True
        if getattr(p, "name", None) in ("p", "article", "body", "div"):
            break
        p = p.parent
    return False


# === ЗАГРУЗКА КОНФИГА И МАППИНГОВ ===

def load_registry(codes_config_path, npa_map_path, maps_dir):
    """
    Возвращает список целей для линковки. Каждая цель:
        {
            'forms': [список текстовых форм названия НПА],
            'doc_id': 'K1234567',
            'article_map': {'1': 'z7', ...} или {} если карты нет,
        }

    Цели сортируются по убыванию длины самой длинной формы, чтобы более
    специфичные совпадения проверялись раньше общих.
    """
    with open(codes_config_path, encoding="utf-8") as f:
        codes_config = json.load(f)
    with open(npa_map_path, encoding="utf-8") as f:
        npa_map = json.load(f)

    # Группируем NPA-формы по doc_id
    forms_by_doc = {}
    for form, doc_id in npa_map.items():
        if form.startswith("_"):
            continue
        forms_by_doc.setdefault(doc_id, []).append(form)

    targets = []
    # Сначала кодексы (есть article_map)
    seen_docs = set()
    for code_key, info in codes_config.items():
        if code_key.startswith("_"):
            continue
        doc_id = info["doc_id"]
        map_file = Path(maps_dir) / f"article_map_{code_key}.json"
        article_map = {}
        if map_file.exists():
            with open(map_file, encoding="utf-8") as f:
                article_map = json.load(f)
        # Also load subpoint_map (контекст: пункт N статьи M → anchor пункта)
        subp_file = Path(maps_dir) / f"subpoint_map_{code_key}.json"
        subpoint_map = {}
        if subp_file.exists():
            with open(subp_file, encoding="utf-8") as f:
                subpoint_map = json.load(f)

        forms = forms_by_doc.get(doc_id, [])
        # doc_id с trailing _ vs без — нормализуем: пробуем оба варианта
        alt_doc = doc_id.rstrip("_") if doc_id.endswith("_") else doc_id + "_"
        forms += forms_by_doc.get(alt_doc, [])

        if not forms:
            continue
        targets.append({
            "forms": sorted(set(forms), key=len, reverse=True),
            "doc_id": doc_id,
            "article_map": article_map,
            "subpoint_map": subpoint_map,
            "is_code": True,
            "key": code_key,
        })
        seen_docs.add(doc_id)
        seen_docs.add(alt_doc)

    # Затем все остальные НПА (законы и кодексы без article_map)
    for doc_id, forms in forms_by_doc.items():
        if doc_id in seen_docs:
            continue
        targets.append({
            "forms": sorted(set(forms), key=len, reverse=True),
            "doc_id": doc_id,
            "article_map": {},
            "is_code": False,
            "key": None,
        })

    # Глобальная сортировка: длиннейшая форма первой (специфичные раньше)
    targets.sort(key=lambda t: max(len(f) for f in t["forms"]), reverse=True)
    return targets


# === ПОСТРОЕНИЕ РЕГЭКСПОВ ===

def build_target_regex(form):
    """
    Превращает текстовую форму названия в regex, толерантный к:
      - вариативным пробелам/неразрывным пробелам
      - вариантам кавычек (« » " " ‟ „)
      - одной vs двум пробелам внутри
    """
    parts = []
    i = 0
    quote_class = r'["«»«»“”„‟]'
    while i < len(form):
        ch = form[i]
        if ch in '"«»«»“”„‟':
            parts.append(quote_class)
        elif ch == " ":
            parts.append(r"\s+")
        else:
            parts.append(re.escape(ch))
        i += 1
    return "".join(parts)


def build_combined_pattern(targets):
    """
    Возвращает скомпилированный regex, который захватывает:
      group "prefix" — необязательная преамбула: "подпунктом N) ", "пунктом M ", и т.д.
      group "stat"   — обязательная часть со статьёй (число)
      group "num"    — первый номер статьи (для подбора якоря)
      group "code"   — название НПА
    Плюс отдельный паттерн для главы и для одного только названия.
    """
    code_alt = "|".join(f"(?:{build_target_regex(f)})" for t in targets for f in t["forms"])
    # Сохраняем ассоциацию формы → target
    return code_alt


def precompile_patterns(targets):
    """
    Для каждой target-формы строим:
      - SUBP_PUNKT_ART_CODE
      - PUNKT_ART_CODE
      - ART_CODE  (включая множественные/диапазоны)
      - GLAVA_CODE
    Возвращаем список (regex, target, kind).
    """
    compiled = []
    # Для каждой формы создаём отдельные компилированные regex'ы
    for t in targets:
        for form in t["forms"]:
            form_re = build_target_regex(form)
            # Подпункт + пункт + статья + код
            p1 = re.compile(
                r"(?P<full>"
                rf"(?P<subp>{SUBP_WORD}\s+\d+(?:-\d+)?\)"
                rf"(?:\s*(?:,\s*|\s+и\s+)\d+(?:-\d+)?\))*"
                rf"\s+)"
                rf"(?P<punkt>{PUNKT_WORD}\s+\d+(?:-\d+)?\s+)"
                rf"(?P<stat>{STAT_WORD}\s+(?P<num>\d+(?:-\d+)?)"
                rf"(?:\s*(?:,\s*|\s+и\s+)\d+(?:-\d+)?)*"
                rf"\s+)"
                rf"(?P<code>{form_re})"
                r")",
                re.IGNORECASE,
            )
            compiled.append((p1, t, "subp_punkt_art_code"))

            # Пункт + статья + код
            p2 = re.compile(
                r"(?P<full>"
                rf"(?P<punkt>{PUNKT_WORD}\s+\d+(?:-\d+)?\s+)"
                rf"(?P<stat>{STAT_WORD}\s+(?P<num>\d+(?:-\d+)?)"
                rf"(?:\s*(?:,\s*|\s+и\s+)\d+(?:-\d+)?)*"
                rf"\s+)"
                rf"(?P<code>{form_re})"
                r")",
                re.IGNORECASE,
            )
            compiled.append((p2, t, "punkt_art_code"))

            # Статья + код (включая множественные, диапазоны)
            p3 = re.compile(
                r"(?P<full>"
                rf"(?P<stat>{STAT_WORD}\s+(?P<num>\d+(?:-\d+)?)"
                rf"(?:\s*(?:,\s*|\s*[–-]\s*|\s+и\s+)\d+(?:-\d+)?)*"
                rf"\s+)"
                rf"(?P<code>{form_re})"
                r")",
                re.IGNORECASE,
            )
            compiled.append((p3, t, "art_code"))

            # Глава + код
            p4 = re.compile(
                r"(?P<full>"
                rf"(?P<glava>{GLAVA_WORD}\s+(?P<num>\d+(?:-\d+)?)\s+)"
                rf"(?P<code>{form_re})"
                r")",
                re.IGNORECASE,
            )
            compiled.append((p4, t, "glava_code"))
    return compiled


# === НАХОЖДЕНИЕ И ЗАМЕНА ===

def _extract_punkt_subp(match):
    """Из именованных групп regex'а вытаскиваем номера пункта и подпункта."""
    gd = match.groupdict()
    punkt_num = None
    subp_num = None
    pg = gd.get("punkt")
    if pg:
        pm = re.search(r"\d+(?:-\d+)?", pg)
        if pm:
            punkt_num = pm.group(0)
    sg = gd.get("subp")
    if sg:
        sm = re.search(r"\d+(?:-\d+)?", sg)
        if sm:
            subp_num = sm.group(0)
    return punkt_num, subp_num


def find_all_matches(text, compiled):
    """
    Возвращает список (start, end, full_text, target, kind, num, punkt, subp).
    Если есть несколько перекрывающихся совпадений — выбирается длиннейшее.
    """
    candidates = []
    for regex, target, kind in compiled:
        for m in regex.finditer(text):
            num = m.group("num") if "num" in m.groupdict() else None
            punkt_num, subp_num = _extract_punkt_subp(m)
            candidates.append((m.start(), m.end(), m.group("full"), target, kind, num, punkt_num, subp_num))

    if not candidates:
        return []

    # Сортируем: сначала по длине совпадения (по убыванию), потом по позиции
    candidates.sort(key=lambda x: (-(x[1] - x[0]), x[0]))

    # Выбираем непересекающиеся, отдавая приоритет длиннейшим
    selected = []
    for c in candidates:
        s, e = c[0], c[1]
        if not any(s < se and e > ss for ss, se, *_ in selected):
            selected.append(c)

    selected.sort(key=lambda x: x[0])
    return selected


def make_link(target, num, full_text, kind, punkt_num=None, subp_num=None):
    """
    Строит <a href="...">full_text</a>.

    Логика выбора якоря (от самого точного к самому общему):
      - kind == "glava_code": главу не находим в article_map (там номера статей),
        ссылаемся на корень документа.
      - punkt_num/subp_num заданы → пробуем subpoint_map с ключами
        f"{num}_{punkt_num}_{subp_num}", f"{num}_{punkt_num}", только потом
        откатываемся к article_map[num].
      - kind == "art_code": берём article_map[num].
      - Для законов (без article_map) — корень документа (мы не уверены, что
        anchor "z{num}" реален; лучше не строить битый href).
    """
    doc_id = target["doc_id"]
    article_map = target["article_map"]
    subpoint_map = target.get("subpoint_map", {})

    anchor = None
    if kind == "glava_code":
        anchor = None
    elif num:
        # 1) subp + punkt + art
        if subp_num and punkt_num:
            anchor = subpoint_map.get(f"{num}_{punkt_num}_{subp_num}")
        # 2) punkt + art
        if not anchor and punkt_num:
            anchor = subpoint_map.get(f"{num}_{punkt_num}")
        # 3) art only
        if not anchor and num in article_map:
            anchor = article_map[num]

    if anchor:
        href = f"{BASE_URL}/rus/docs/{doc_id}#{anchor}"
    else:
        # Нет точного якоря — ссылаемся на корень документа, чтобы не было
        # битого фрагмента типа #z<непредсказуемый>.
        href = f"{BASE_URL}/rus/docs/{doc_id}"
    return f'<a href="{href}">{full_text}</a>'


def process_text_node(text, compiled):
    """Возвращает (новый_html, кол-во_замен) или (исходный_text, 0)."""
    matches = find_all_matches(text, compiled)
    if not matches:
        return text, 0

    parts = []
    cursor = 0
    for start, end, full, target, kind, num, punkt_num, subp_num in matches:
        parts.append(text[cursor:start])
        parts.append(make_link(target, num, full, kind, punkt_num=punkt_num, subp_num=subp_num))
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts), len(matches)


# === ОСНОВНАЯ ОБРАБОТКА ===

def unwrap_deprecated_links(soup, deprecated_remaps):
    """
    Раз-оборачивает <a> ссылки, указывающие на устаревшие doc_id.
    Возвращает количество раз-обёрнутых ссылок. После этого сам regex
    скрипта снова найдёт фразу и поставит правильный URL.
    """
    if not deprecated_remaps:
        return 0
    count = 0
    deprecated_ids = [k for k in deprecated_remaps if not k.startswith("_")]
    for a_tag in list(soup.find_all("a", href=True)):
        href = a_tag["href"]
        if any(dep in href for dep in deprecated_ids):
            a_tag.unwrap()
            count += 1
    return count


def process_html(input_path, output_path, codes_config, npa_map, maps_dir, skip_snoska=True):
    targets = load_registry(codes_config, npa_map, maps_dir)
    compiled = precompile_patterns(targets)
    print(f"Загружено целей: {len(targets)} (форм: {sum(len(t['forms']) for t in targets)})")

    # Загружаем remap-таблицу
    with open(codes_config, encoding="utf-8") as f:
        cfg = json.load(f)
    deprecated_remaps = cfg.get("_deprecated_remaps", {})

    with open(input_path, "rb") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    for tag in soup.find_all(["script", "style", "template", "veepn-lock-screen"]):
        tag.decompose()

    # Раз-оборачиваем устаревшие ссылки — regex затем найдёт фразы заново
    unwrapped = unwrap_deprecated_links(soup, deprecated_remaps)
    if unwrapped:
        print(f"Раз-обёрнуто устаревших <a> ссылок: {unwrapped}")
        # После unwrap соседние NavigableString-сиблинги остаются отдельными узлами.
        # smooth() объединит их в один, чтобы regex мог искать через бывшую границу.
        soup.smooth()

    total_replaced = 0
    text_nodes = [n for n in soup.find_all(string=True)]
    for text_node in text_nodes:
        if is_inside_link(text_node):
            continue
        if is_article_heading(text_node):
            continue
        if skip_snoska and is_in_snoska(text_node):
            continue
        txt = str(text_node)
        if len(txt.strip()) < 8:
            continue

        new_html, count = process_text_node(txt, compiled)
        if count > 0:
            text_node.replace_with(BeautifulSoup(new_html, "html.parser"))
            total_replaced += count

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(str(soup))
    print(f"Создано cross-code ссылок: {total_replaced}")
    print(f"Результат: {output_path}")


def main():
    ap = argparse.ArgumentParser(description="Добавляет cross-code ссылки одним <a>")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--codes-config", default=str(paths.CODES_JSON))
    ap.add_argument("--npa-map", default=str(paths.NPA_MAPPING))
    ap.add_argument("--maps-dir", default=str(paths.MAPS))
    ap.add_argument("--include-snoska", action="store_true")
    args = ap.parse_args()

    process_html(
        args.input, args.output,
        args.codes_config, args.npa_map, args.maps_dir,
        skip_snoska=not args.include_snoska,
    )


if __name__ == "__main__":
    main()
