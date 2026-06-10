"""
Чанкер НПА. Читает data/final/{code}_structured.html → JSON-дерево + JSONL-чанки.

State-machine на ТЕКСТЕ начала элементов (id ненадёжен).
R1-R14 + homoglyph-tolerant title + split-embedded + orphan-pickup.

Артефакты:
  data/tree/{code}.json       — дерево (статьи → пункты → подпункты)
  data/chunks/{code}.jsonl    — строка = чанк = пункт + продолжения + подпункты
"""
import argparse
import io
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
TREE_DIR = ROOT / "data" / "tree"
CHUNKS_DIR = ROOT / "data" / "chunks"
TREE_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

CODES_JSON = ROOT / "config" / "codes.json"
codes_data = json.loads(CODES_JSON.read_text(encoding="utf-8"))
CODES = {k: v for k, v in codes_data.items() if not k.startswith("_")}

DISCREPANCIES = []
ORPHAN_LOG = []

CODE_LABELS = {
    "nalog": "НК", "trudovoy": "ТК", "grazhdanskiy": "ГК", "predprinimatel": "ПК",
    "socialnyy": "СК", "ekologicheskiy": "ЭК", "zemelnyy": "ЗК", "upk": "УПК",
    "koap": "КоАП", "appk": "АППК", "byudzhet": "БК", "ugolovniy": "УК",
    "grazhdanskiy_osob": "ГК",
}

# Латинские коды для иерархических hier_id (запрос шефа Yergali, v3)
HIER_CODE = {
    "ugolovniy": "UK", "upk": "UPK", "grazhdanskiy": "GK", "nalog": "NK",
    "trudovoy": "TK", "socialnyy": "SK", "ekologicheskiy": "EK", "zemelnyy": "ZK",
    "predprinimatel": "PK", "byudzhet": "BK", "koap": "KOAP", "appk": "APPK",
    "grazhdanskiy_osob": "GK",
}
# CH1/CH2 (Общая/Особенная часть) только в этих кодексах
CODES_WITH_CODE_PART = ("ugolovniy", "upk", "koap")

# ── Regex (R3-R8) ───────────────────────────────────────────────────────
RE_PUNKT = re.compile(r"^\s*(\d+(?:-\d+)?)\.\s")
RE_PODPUNKT = re.compile(r"^\s*(\d+(?:-\d+)?)\)\s")
RE_NESTED = re.compile(r"^\s*(\d+\.\d+)\.\s")
RE_DASH = re.compile(r"^\s*[\-–—]\s")
RE_REPEALED = re.compile(r"Статья\s+(?:\d+(?:-\d+)?\s+)?исключена")

# Homoglyph-tolerant: первая буква С — кирилл (U+0421), лат (U+0043), греч (U+03F9)
C_HOMOGLYPHS = "[СCϹ]"
# Якорь к ^ : текст ДОЛЖЕН начинаться со "Статья N." (исключает quoted "Статья 773." в note)
RE_ARTICLE_TITLE_STRICT = re.compile(
    rf"^\s*{C_HOMOGLYPHS}тать[яиею]\s+(\d+(?:-\d+)?)\s*\."
)
RE_TITLE_PREFIX_STRIP = re.compile(
    rf"^\s*{C_HOMOGLYPHS}тать[яиею]\s+\d+(?:-\d+)?\s*\.\s*"
)
RE_BARE_PREFIX_STRIP = re.compile(r"^\s*\d+(?:-\d+)?\s*\.\s*")

# Bare: ровно "N. {Title}" в <b>, title после префикса ≥ 40 chars (отсекает
# короткие параграф-заголовки в ГК типа "2. Полное товарищество")
RE_BARE_FULL = re.compile(
    r"^\s*(\d+(?:-\d+)?)\s*\.\s+([А-ЯЁ][А-Яа-яёЁA-Za-z0-9 ,\(\)\-«»\"\'–—:;]{40,})\s*$"
)

# ── Split крупных статей-словарей (запрос шефа Yergali) ───────────────────
# Если итоговый чанк > порога И тело преимущественно состоит из подпунктов
# «N)» (root-список ИЛИ один пункт с длинным списком подпунктов), режем
# КАЖДЫЙ подпункт в отдельный чанк. Обычные пункты/части НЕ трогаем.
DICT_SPLIT_CHARS = 6000      # порог размера чанка
DICT_MIN_SUBPOINTS = 3       # «длинный список» = минимум столько подпунктов
DICT_SUBPOINT_RATIO = 0.5    # подпункты должны давать ≥ 50% длины тела


def _is_dict_list_unit(unit, body):
    """True, если юнит — это словарь-список: ≥ DICT_MIN_SUBPOINTS подпунктов,
    и текст подпунктов составляет основную часть тела (а не intro-проза)."""
    subs = unit.get("children", [])
    if len(subs) < DICT_MIN_SUBPOINTS:
        return False
    subs_len = 0
    for s in subs:
        subs_len += len(s.get("text", ""))
        subs_len += sum(len(x) for x in s.get("continuations", []))
        for n in s.get("children", []):
            subs_len += len(n.get("text", ""))
    return subs_len >= DICT_SUBPOINT_RATIO * max(1, len(body))


def detect_title(text, src_tag):
    """Return (kind, num) if text+src_tag is an article title, else None.
    kind: 'strict' (has 'Статья', homoglyph-tolerant) | 'bare' (just 'N. Long Title')
    Bare requires src_tag = <p>...<b>... (NOT <h3>: в ГК <h3>N. Title</h3> — это
    заголовки параграфов, не статей)."""
    m_strict = RE_ARTICLE_TITLE_STRICT.match(text)
    if m_strict:
        return ("strict", m_strict.group(1))
    if src_tag is None:
        return None
    # Bare: ONLY <p><b> (not <h3>)
    if src_tag.name == "p":
        b_tag = src_tag.find(["b", "strong"])
        if b_tag:
            b_text = b_tag.get_text(" ", strip=True)
            m_bare = RE_BARE_FULL.match(b_text)
            if m_bare:
                return ("bare", m_bare.group(1))
    return None


def strip_title_prefix(text):
    text = RE_TITLE_PREFIX_STRIP.sub("", text, count=1)
    text = RE_BARE_PREFIX_STRIP.sub("", text, count=1)
    return text.strip()


# ── Тип юнита (R3) ──────────────────────────────────────────────────────

def is_in_osobennaya_chast_koap(article_div):
    for parent in article_div.parents:
        if not isinstance(parent, Tag):
            continue
        cls = parent.get("class") or []
        if "part" in cls:
            h3 = parent.find("h3", recursive=False)
            text = (
                h3.get_text(" ", strip=True).upper()
                if h3 else parent.get_text(" ", strip=True)[:200].upper()
            )
            if "ОСОБЕННАЯ" in text:
                return True
            if "ОБЩАЯ" in text:
                return False
    return False


def get_unit_type(code, article_div, art_num=None):
    if code in ("ugolovniy", "upk"):
        return "часть"
    if code == "koap":
        if article_div is not None and is_in_osobennaya_chast_koap(article_div):
            return "часть"
        # orphan КоАП article: heuristic by data-number (>=242 = Особенная часть)
        if art_num:
            try:
                base = int(re.match(r"(\d+)", art_num).group(1))
                if base >= 242:
                    return "часть"
            except Exception:
                pass
    return "пункт"


# ── Иерархический контекст (hier_id, v3) ─────────────────────────────────

def _div_heading_upper(div):
    """Текст заголовка структурной обёртки (часть/раздел/глава/параграф), UPPER.
    Для structural-part это <h3>, для compound-split — <span class='*-label'>."""
    for child in div.children:
        if isinstance(child, Tag) and child.name in ("h2", "h3", "h4", "span"):
            t = child.get_text(" ", strip=True)
            if t:
                return t.upper()
    return div.get_text(" ", strip=True)[:200].upper()


def build_hier_ctx(code, anchor_tag):
    """Идёт вверх по родителям anchor_tag (article-div или orphan-container),
    собирает структурный контекст ВЫШЕ статьи:
      code_part: 1|2|None   (CH1=Общая, CH2=Особенная; только УК/УПК/КоАП)
      section / chapter / paragraph: номер (str) или None
    Берём ближайший к статье на каждом уровне (parents идут изнутри наружу)."""
    code_part = None
    section = None
    chapter = None
    paragraph = None
    if anchor_tag is not None:
        for parent in anchor_tag.parents:
            if not isinstance(parent, Tag):
                continue
            dtype = parent.get("data-type")
            if not dtype:
                continue
            dnum = parent.get("data-number")
            if dtype == "часть":
                if code in CODES_WITH_CODE_PART and code_part is None:
                    h = _div_heading_upper(parent)
                    if "ОСОБЕННАЯ" in h:
                        code_part = 2
                    elif "ОБЩАЯ" in h:
                        code_part = 1
            elif dtype == "раздел" and section is None:
                section = dnum
            elif dtype == "глава" and chapter is None:
                chapter = dnum
            elif dtype == "параграф" and paragraph is None:
                paragraph = dnum
    return {"code_part": code_part, "section": section,
            "chapter": chapter, "paragraph": paragraph}


def make_hier(code, ctx, art_num, unit_num=None, subunit_num=None):
    """Вернёт (hier_id, hier_path).
    Порядок компактного id: Code → CH → R → G → PG → ST → P → SP.
    Пропущенные уровни не вставляются. Суффиксы (4-1) сохраняются как есть."""
    latin = HIER_CODE.get(code, code.upper())
    cp = ctx.get("code_part")
    sec = ctx.get("section")
    chap = ctx.get("chapter")
    par = ctx.get("paragraph")

    parts = [latin]
    if cp is not None:
        parts.append(f"CH{cp}")
    if sec is not None:
        parts.append(f"R{sec}")
    if chap is not None:
        parts.append(f"G{chap}")
    if par is not None:
        parts.append(f"PG{par}")
    parts.append(f"ST{art_num}")
    if unit_num is not None:
        parts.append(f"P{unit_num}")
    if subunit_num is not None:
        parts.append(f"SP{subunit_num}")
    hier_id = "".join(parts)

    hier_path = {
        "code": latin,
        "code_part": (f"CH{cp}" if cp is not None else None),
        "section": sec,
        "chapter": chap,
        "paragraph": par,
        "article": art_num,
        "unit": unit_num,
        "subunit": subunit_num,
    }
    return hier_id, hier_path


# ── Извлечение сегментов (R12 UPK-special) ───────────────────────────────

def iter_segments(article_div):
    """Yield (anchor_id, text, src_tag) per content segment.
    For UPK <br/>-format src_tag = None (synthetic split).
    Notes (R10/R11) skipped. First title <p><b>Статья N./Cтатья N./N. Заголовок>
    is skipped here (caller handles title separately)."""
    children = list(article_div.children)

    is_upk = False
    for c in children:
        if isinstance(c, Tag) and c.name == "a" and c.get("id"):
            nxt = c.next_sibling
            if isinstance(nxt, NavigableString) and re.match(
                r"\s*\d+(?:-\d+)?[\.\)]\s", str(nxt)
            ):
                is_upk = True
                break

    if is_upk:
        current_anchor = None
        buf = []
        skipped_title = False
        for c in children:
            if isinstance(c, Tag) and c.name == "a" and c.get("id"):
                if buf:
                    text = "".join(buf).strip()
                    if text:
                        yield current_anchor, text, None
                    buf = []
                current_anchor = c.get("id")
                continue
            if isinstance(c, Tag) and c.name == "br":
                if buf:
                    text = "".join(buf).strip()
                    if text:
                        yield current_anchor, text, None
                    buf = []
                    current_anchor = None
                continue
            if isinstance(c, NavigableString):
                buf.append(str(c))
            elif isinstance(c, Tag):
                cls = c.get("class") or []
                if "note" in cls or c.name == "font":
                    continue
                if c.name in ("p", "h3"):
                    txt = c.get_text(" ", strip=True)
                    if not skipped_title and detect_title(txt, c):
                        skipped_title = True
                        continue
                    if "note" in (c.get("class") or []):
                        continue
                buf.append(c.get_text(" "))
        if buf:
            text = "".join(buf).strip()
            if text:
                yield current_anchor, text, None
        return

    # Regular: iterate <p>/<h3>
    skipped_title = False
    for c in children:
        if not isinstance(c, Tag):
            continue
        cls = c.get("class") or []
        if "note" in cls or c.name == "font":
            continue
        if c.name == "span" and "note" in cls:
            continue
        if c.name == "br":
            continue
        if c.name in ("p", "h3"):
            text = c.get_text(" ", strip=True)
            if not text:
                continue
            # Skip the FIRST title only (subsequent embedded titles handled by caller)
            if not skipped_title and detect_title(text, c):
                skipped_title = True
                continue
            yield c.get("id"), text, c


# ── Построение чанков из сегментов ───────────────────────────────────────

def _build_tree_and_chunks(code, art_num, title_anchor, title_clean, segments,
                            unit_type, status, hier_ctx=None, hier_partial=False,
                            data_num_for_log=None):
    """segments: list of (anchor, text, src_tag) — body only (no title).
    hier_ctx: dict from build_hier_ctx() (code_part/section/chapter/paragraph).
    hier_partial: True если путь восстановлен (orphan) и не авторитетен.
    Returns (tree, chunks)."""
    label = CODE_LABELS.get(code, code)
    doc_id = CODES[code]["doc_id"]
    if hier_ctx is None:
        hier_ctx = {"code_part": None, "section": None,
                    "chapter": None, "paragraph": None}

    def _meta_hier(unit_num=None, subunit_num=None):
        hid, hpath = make_hier(code, hier_ctx, art_num, unit_num, subunit_num)
        d = {"hier_id": hid, "hier_path": hpath}
        if hier_partial:
            d["hier_partial"] = True
        return d

    art_hier_id, _ = make_hier(code, hier_ctx, art_num)

    if status == "repealed":
        repealed_text = f"[{label} | Статья {art_num}. {title_clean} | СТАТЬЯ ИСКЛЮЧЕНА]"
        tree = {
            "article": art_num, "title": title_clean, "anchor": title_anchor,
            "status": "repealed", "unit_type": None, "hier_id": art_hier_id,
            "children": [],
        }
        meta = {
            "code": code, "doc_id": doc_id, "article": art_num,
            "article_title": title_clean, "unit_type": None,
            "unit_number": None, "status": "repealed",
            "char_len": len(repealed_text),
        }
        meta.update(_meta_hier())
        chunks = [{
            "id": f"{code}_ст{art_num}",
            "text": repealed_text,
            "meta": meta,
        }]
        return tree, chunks

    tree = {
        "article": art_num, "title": title_clean, "anchor": title_anchor,
        "status": "active", "unit_type": unit_type, "hier_id": art_hier_id,
        "children": [],
    }

    current_unit = None
    current_sub = None
    standalone = []

    for anchor, text, _src in segments:
        m_punkt = RE_PUNKT.match(text)
        m_sub = RE_PODPUNKT.match(text)
        m_nested = RE_NESTED.match(text)

        if m_nested:
            target = current_sub if current_sub else current_unit
            if target is not None:
                _pu = current_unit["number"] if current_unit else None
                _psu = current_sub["number"] if current_sub else None
                target.setdefault("children", []).append({
                    "type": "nested", "number": m_nested.group(1),
                    "anchor": anchor, "text": text,
                    "hier_id": make_hier(code, hier_ctx, art_num, _pu, _psu)[0]
                    + f"N{m_nested.group(1)}",
                })
            else:
                standalone.append(text)
            continue

        if m_punkt:
            unum = m_punkt.group(1)
            current_unit = {
                "type": unit_type, "number": unum,
                "anchor": anchor, "text": text,
                "hier_id": make_hier(code, hier_ctx, art_num, unum)[0],
                "children": [], "continuations": [],
            }
            tree["children"].append(current_unit)
            current_sub = None
            continue

        if m_sub:
            if current_unit is None:
                current_unit = {
                    "type": "article-root", "number": None,
                    "anchor": None, "text": "",
                    "hier_id": make_hier(code, hier_ctx, art_num)[0],
                    "children": [], "continuations": [],
                }
                tree["children"].append(current_unit)
            snum = m_sub.group(1)
            sub = {
                "type": "подпункт", "number": snum,
                "anchor": anchor, "text": text,
                "hier_id": make_hier(code, hier_ctx, art_num,
                                     current_unit["number"], snum)[0],
                "continuations": [], "children": [],
            }
            current_unit["children"].append(sub)
            current_sub = sub
            continue

        # R8/R9 continuation
        if current_sub is not None:
            current_sub["continuations"].append(text)
        elif current_unit is not None:
            current_unit["continuations"].append(text)
        else:
            standalone.append(text)

    # No units → one chunk
    if not tree["children"]:
        full_text = "\n".join(standalone) if standalone else ""
        single_text = f"[{label} | Статья {art_num}. {title_clean}]\n{full_text}"
        meta = {
            "code": code, "doc_id": doc_id, "article": art_num,
            "article_title": title_clean, "unit_type": None,
            "unit_number": None, "status": "active",
            "char_len": len(single_text),
        }
        meta.update(_meta_hier())
        chunks = [{
            "id": f"{code}_ст{art_num}",
            "text": single_text,
            "meta": meta,
        }]
        return tree, chunks

    # Build chunks per unit.
    # ВНУТРИ статьи номер пункта/части может повторяться (переходные статьи с
    # встроенными цитатами рестартят нумерацию: «...8. ...2. Тарифы... 9. ...»).
    # Источник так и написан → state-machine честно создаёт два узла «2».
    # Чтобы id были уникальны (требование шефа), 2-му и далее повтору добавляем
    # порядковый суффикс ~N в hier_id и chunk_id + флаг hier_dup_seq.
    chunks = []
    seen_hid = {}
    standalone_consumed = False

    def _register(hid, chunk_id):
        """Дедуп hier_id/chunk_id внутри статьи (повтор номеров в переходных
        статьях). 2-му+ повтору добавляем ~N. Возвращает (hid, id, dup_seq)."""
        seen_hid[hid] = seen_hid.get(hid, 0) + 1
        seq = seen_hid[hid]
        if seq > 1:
            return f"{hid}~{seq}", f"{chunk_id}~{seq}", seq
        return hid, chunk_id, None

    for u_idx, unit in enumerate(tree["children"]):
        if unit["number"] is None:
            unit_label = ""
            base_id = f"{code}_ст{art_num}_root"
            unit_type_meta = None
            unit_num_meta = None
        else:
            unit_label = f"{unit['type']} {unit['number']}"
            short = "ч" if unit["type"] == "часть" else "п"
            base_id = f"{code}_ст{art_num}_{short}{unit['number']}"
            unit_type_meta = unit["type"]
            unit_num_meta = unit["number"]

        intro_parts = []
        if unit["text"]:
            intro_parts.append(unit["text"])
        intro_parts.extend(unit.get("continuations", []))

        body_parts = list(intro_parts)
        for sub in unit.get("children", []):
            body_parts.append(sub["text"])
            body_parts.extend(sub.get("continuations", []))
            for nested in sub.get("children", []):
                body_parts.append(nested["text"])

        body = "\n".join(body_parts)
        header = f"[{label} | Статья {art_num}. {title_clean}"
        if unit_label:
            header += f" | {unit_label}"
        header += "]"
        chunk_text = f"{header}\n{body}"

        # ── SPLIT крупных статей-словарей: чанк > порога И преимущественно
        #    подпункты → каждый подпункт отдельным чанком (id …_пп{K}).
        if len(chunk_text) > DICT_SPLIT_CHARS and _is_dict_list_unit(unit, body):
            di_parts = list(intro_parts)
            if u_idx == 0 and standalone:
                di_parts = list(standalone) + di_parts
                standalone_consumed = True
            dict_intro = "\n".join(p for p in di_parts if p).strip()

            for sub in unit.get("children", []):
                snum = sub["number"]
                if unit["number"] is None:
                    sp_id = f"{code}_ст{art_num}_пп{snum}"
                else:
                    sp_id = f"{code}_ст{art_num}_п{unit['number']}_пп{snum}"
                sp_hid, sp_hpath = make_hier(
                    code, hier_ctx, art_num, unit["number"], snum)
                sp_hid, sp_id, dup_seq = _register(sp_hid, sp_id)
                sub["hier_id"] = sp_hid  # узел дерева в синхроне с чанком

                sp_body_parts = [sub["text"]]
                sp_body_parts.extend(sub.get("continuations", []))
                for nested in sub.get("children", []):
                    sp_body_parts.append(nested["text"])
                sp_body = "\n".join(sp_body_parts)
                sp_header = (f"[{label} | Статья {art_num}. {title_clean} "
                             f"| подпункт {snum}]")
                sp_text = (f"{sp_header}\n{dict_intro}\n{sp_body}"
                           if dict_intro else f"{sp_header}\n{sp_body}")

                sp_meta = {
                    "code": code, "doc_id": doc_id, "article": art_num,
                    "article_title": title_clean, "unit_type": "подпункт",
                    "unit_number": snum, "status": "active",
                    "char_len": len(sp_text),
                    "hier_id": sp_hid, "hier_path": sp_hpath,
                    "split_from": base_id,
                }
                if dup_seq is not None:
                    sp_meta["hier_dup_seq"] = dup_seq
                if hier_partial:
                    sp_meta["hier_partial"] = True
                chunks.append({"id": sp_id, "text": sp_text, "meta": sp_meta})
            continue

        # ── Обычный чанк-юнит (НЕ режем) ──────────────────────────────────
        hid, hpath = make_hier(code, hier_ctx, art_num, unit_num_meta)
        hid, chunk_id, dup_seq = _register(hid, base_id)
        unit["hier_id"] = hid  # держим узел дерева в синхроне с чанком

        meta = {
            "code": code, "doc_id": doc_id, "article": art_num,
            "article_title": title_clean, "unit_type": unit_type_meta,
            "unit_number": unit_num_meta, "status": "active",
            "char_len": len(chunk_text),
            "hier_id": hid, "hier_path": hpath,
        }
        if dup_seq is not None:
            meta["hier_dup_seq"] = dup_seq
        if hier_partial:
            meta["hier_partial"] = True
        chunks.append({
            "id": chunk_id,
            "text": chunk_text,
            "meta": meta,
        })

    if standalone and chunks and not standalone_consumed:
        prefix = "[intro]\n" + "\n".join(standalone) + "\n\n"
        chunks[0]["text"] = prefix + chunks[0]["text"]
        chunks[0]["meta"]["char_len"] = len(chunks[0]["text"])

    return tree, chunks


# ── Парсинг статьи с поддержкой embedded-split ───────────────────────────

def parse_article(code, article_div):
    """Returns list[(tree, chunks)]. Length >1 if embedded articles split out."""
    data_num = article_div.get("data-number")
    hier_ctx = build_hier_ctx(code, article_div)

    # Pre-scan: find title segments (the very first valid <p>/<h3>, plus any
    # subsequent ones that look like article headers)
    children = list(article_div.children)

    # The first title (legitimate one) and any subsequent embedded titles
    title_points = []  # list of (child_index, text, src_tag, kind, num, anchor)

    for idx, c in enumerate(children):
        if not isinstance(c, Tag):
            continue
        if c.name not in ("p", "h3"):
            continue
        cls = c.get("class") or []
        if "note" in cls:
            continue
        text = c.get_text(" ", strip=True)
        if not text:
            continue
        det = detect_title(text, c)
        if det:
            kind, num = det
            # title_anchor
            anchor = c.get("id")
            if not anchor:
                a = c.find("a", attrs={"id": True}) or c.find("a", attrs={"name": True})
                if a:
                    anchor = a.get("id") or a.get("name")
            title_points.append((idx, text, c, kind, num, anchor))

    if not title_points:
        # No detectable title: fallback parse with data_num
        segments = list(iter_segments(article_div))
        unit_type = get_unit_type(code, article_div, data_num)
        status = "active"
        for c in article_div.children:
            if isinstance(c, Tag):
                cls = c.get("class") or []
                if "note" in cls and RE_REPEALED.search(c.get_text()):
                    status = "repealed"
                    break
        tree, chunks = _build_tree_and_chunks(
            code, data_num, None, "", segments, unit_type, status,
            hier_ctx=hier_ctx, data_num_for_log=data_num
        )
        return [(tree, chunks)]

    # SHORTCUT: single title — use iter_segments() (handles UPK <br/>-format)
    if len(title_points) == 1:
        idx, text, src_tag, kind, num, anchor = title_points[0]
        segments = list(iter_segments(article_div))
        title_clean = strip_title_prefix(text)
        unit_type = get_unit_type(code, article_div, num)
        status = "active"
        for c in article_div.children:
            if isinstance(c, Tag):
                cls = c.get("class") or []
                if "note" in cls and RE_REPEALED.search(c.get_text()):
                    status = "repealed"
                    break
        if data_num and num != data_num:
            DISCREPANCIES.append({
                "code": code, "kind": "first_title_mismatch",
                "data_number": data_num, "title_number": num,
                "anchor": anchor, "snippet": text[:80],
            })
        tree, chunks = _build_tree_and_chunks(
            code, num, anchor, title_clean, segments, unit_type, status,
            hier_ctx=hier_ctx, data_num_for_log=data_num
        )
        return [(tree, chunks)]

    # MULTI-TITLE: split each region between consecutive title-points
    results = []
    for j, (idx, text, src_tag, kind, num, anchor) in enumerate(title_points):
        end_idx = title_points[j + 1][0] if j + 1 < len(title_points) else len(children)
        sub_children = children[idx + 1: end_idx]

        segments = []
        for c in sub_children:
            if not isinstance(c, Tag):
                continue
            cls = c.get("class") or []
            if "note" in cls or c.name == "font":
                continue
            if c.name == "span" and "note" in cls:
                continue
            if c.name == "br":
                continue
            if c.name in ("p", "h3"):
                txt = c.get_text(" ", strip=True)
                if not txt:
                    continue
                segments.append((c.get("id"), txt, c))

        title_clean = strip_title_prefix(text)
        unit_type = get_unit_type(code, article_div if j == 0 else None, num)

        # repealed detection: scan sub_children for note "Статья N исключена"
        status = "active"
        for c in sub_children:
            if isinstance(c, Tag):
                cls = c.get("class") or []
                if "note" in cls and RE_REPEALED.search(c.get_text()):
                    status = "repealed"
                    break

        # log discrepancy
        if j == 0:
            if data_num and num != data_num:
                DISCREPANCIES.append({
                    "code": code, "kind": "first_title_mismatch",
                    "data_number": data_num, "title_number": num,
                    "anchor": anchor, "snippet": text[:80],
                })
        else:
            DISCREPANCIES.append({
                "code": code, "kind": "embedded_article_split",
                "data_number": data_num, "title_number": num,
                "anchor": anchor, "snippet": text[:80],
            })

        tree, chunks = _build_tree_and_chunks(
            code, num, anchor, title_clean, segments, unit_type, status,
            hier_ctx=hier_ctx, data_num_for_log=data_num
        )
        results.append((tree, chunks))

    return results


# ── Orphan pickup ────────────────────────────────────────────────────────

def find_orphan_articles(code, soup):
    """Find article titles outside any <div class='article'>. Build pseudo-articles."""
    results = []
    seen_anchors = set()  # dedupe

    # Look for <b>/<strong> and <h3> with title pattern
    candidates = []
    for tag in soup.find_all(["b", "strong", "h3"]):
        bt = tag.get_text(" ", strip=True)
        det = detect_title(bt, tag if tag.name == "h3" else tag.parent)
        if not det:
            continue
        # Must NOT be inside <div class="article">
        in_art = False
        p = tag
        while p:
            if isinstance(p, Tag) and p.name == "div" and "article" in (p.get("class") or []):
                in_art = True
                break
            p = p.parent
        if in_art:
            continue
        # Identify anchor
        if tag.name == "h3":
            anchor = tag.get("id")
            container = tag
        else:
            inner_a = tag.find("a", attrs={"id": True}) or tag.find("a", attrs={"name": True})
            anchor = inner_a.get("id") if inner_a else (tag.parent.get("id") if tag.parent else None)
            container = tag.parent if tag.parent and tag.parent.name in ("p", "h3") else tag
        if anchor in seen_anchors:
            continue
        seen_anchors.add(anchor)
        candidates.append((tag, container, det, anchor, bt))

    for tag, container, (kind, num), anchor, bt in candidates:
        # Collect body siblings until next title or article-div
        segments = []
        cur = container.next_sibling
        while cur is not None:
            if isinstance(cur, Tag):
                if cur.name == "div" and "article" in (cur.get("class") or []):
                    break
                cls = cur.get("class") or []
                if cur.name in ("p", "h3"):
                    txt = cur.get_text(" ", strip=True)
                    bb = cur.find(["b", "strong"])
                    if (cur.name == "h3" or bb) and txt:
                        # Check if it's a next article title
                        next_det = detect_title(txt, cur)
                        if next_det:
                            break
                    if "note" not in cls and txt:
                        segments.append((cur.get("id"), txt, cur))
                if cur.name == "br":
                    pass
            cur = cur.next_sibling

        title_clean = strip_title_prefix(bt)
        # hier path восстановлен по родителям container (ближайшая глава/часть) —
        # помечаем hier_partial: позиция inferred, не из article-обёртки
        hier_ctx = build_hier_ctx(code, container)
        unit_type = get_unit_type(code, container, num)
        # repealed? (rare in orphans)
        status = "active"
        ORPHAN_LOG.append({
            "code": code, "article": num, "anchor": anchor,
            "snippet": bt[:80], "body_segs": len(segments),
            "hier_ctx": {k: v for k, v in hier_ctx.items() if v is not None},
        })
        tree, chunks = _build_tree_and_chunks(
            code, num, anchor, title_clean, segments, unit_type, status,
            hier_ctx=hier_ctx, hier_partial=True, data_num_for_log=None
        )
        # Mark as orphan in meta
        for ch in chunks:
            ch["meta"]["orphan_pickup"] = True
        tree["orphan_pickup"] = True
        results.append((tree, chunks))

    return results


# ── Обработка кодекса ────────────────────────────────────────────────────

def process_code(code):
    path = FINAL / f"{code}_structured.html"
    if not path.exists():
        print(f"  {code}: file not found")
        return None, None
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")

    trees = []
    chunks_all = []

    # 1. Process article divs (with split-embedded support)
    for art in soup.find_all("div", class_="article"):
        if "статья" not in (art.get("data-type") or ""):
            continue
        for tree, chunks in parse_article(code, art):
            trees.append(tree)
            chunks_all.extend(chunks)

    # 2. Orphan pickup
    for tree, chunks in find_orphan_articles(code, soup):
        trees.append(tree)
        chunks_all.extend(chunks)

    return trees, chunks_all


def save_artifacts(code, trees, chunks):
    tree_path = TREE_DIR / f"{code}.json"
    tree_path.write_text(
        json.dumps(
            {"code": code, "doc_id": CODES[code]["doc_id"], "articles": trees},
            ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    chunks_path = CHUNKS_DIR / f"{code}.jsonl"
    with chunks_path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"  {code}: {len(trees)} articles, {len(chunks)} chunks → {tree_path.name} + {chunks_path.name}")


# ── Тест на 7 статьях ────────────────────────────────────────────────────

TEST_ARTICLES = [
    ("predprinimatel", "82", "ПК ст.82 (12 подпунктов + suffix 4-1)"),
    ("ugolovniy",      "4",  "УК ст.4 (без пунктов)"),
    ("upk",            "32", "УПК ст.32 (<br/>-формат R12)"),
    ("koap",           "200","КоАП ст.200 Особ.ч."),
    ("grazhdanskiy",   "147","ГК ст.147"),
    ("ekologicheskiy", "418","ЭК ст.418 (Переходные)"),
    ("predprinimatel", "37", "ПК ст.37 (исключённая)"),
]


def run_tests():
    for code, art_num, desc in TEST_ARTICLES:
        path = FINAL / f"{code}_structured.html"
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        target = None
        for a in soup.find_all("div", class_="article"):
            if a.get("data-number") == art_num and "статья" in (a.get("data-type") or ""):
                target = a
                break
        if target is None:
            print(f"\n=== {desc} ===  NOT FOUND")
            continue
        results = parse_article(code, target)
        print(f"\n{'='*100}")
        print(f"=== {desc} === parsed_articles={len(results)}")
        for k, (tree, chunks) in enumerate(results):
            print(f"  [{k}] art={tree['article']} status={tree['status']} unit_type={tree.get('unit_type')} "
                  f"children={len(tree['children'])} chunks={len(chunks)}")


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("code", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()

    if args.test:
        run_tests()
        return

    if args.all:
        DISCREPANCIES.clear()
        ORPHAN_LOG.clear()
        stats_rows = []
        for code in CODES:
            trees, chunks = process_code(code)
            if trees:
                save_artifacts(code, trees, chunks)
                repealed = sum(1 for c in chunks if c["meta"]["status"] == "repealed")
                orphans = sum(1 for c in chunks if c["meta"].get("orphan_pickup"))
                lens = [c["meta"]["char_len"] for c in chunks]
                gt4k = sum(1 for L in lens if L > 4000)
                gt8k = sum(1 for L in lens if L > 8000)
                stats_rows.append({
                    "code": code, "articles": len(trees), "chunks": len(chunks),
                    "repealed": repealed, "orphans": orphans,
                    "max_char_len": max(lens) if lens else 0,
                    "gt4k": gt4k, "gt8k": gt8k,
                })

        print()
        print("=" * 80)
        print(f"DISCREPANCIES: {len(DISCREPANCIES)}")
        print("=" * 80)
        for d in DISCREPANCIES:
            extra = f"  snippet={d.get('snippet')!r}" if d.get('snippet') else ""
            print(f"  [{d.get('kind','?')}] {d['code']:14} data-number={d.get('data_number')!s:8} "
                  f"title={d['title_number']!r}  anchor={d['anchor']}{extra}")

        print()
        print("=" * 80)
        print(f"ORPHAN articles picked up: {len(ORPHAN_LOG)}")
        print("=" * 80)
        for o in ORPHAN_LOG:
            print(f"  {o['code']:14} ст.{o['article']:8} anchor={o['anchor']}  "
                  f"body_segs={o['body_segs']}  snippet={o['snippet']!r}")

        print()
        print("=" * 90)
        print(f"{'код':14} {'статей':>7} {'чанков':>7} {'repealed':>9} {'orphan':>7} {'max_char':>9} {'>4000':>7} {'>8000':>7}")
        print("-" * 90)
        totals = {"articles": 0, "chunks": 0, "repealed": 0, "orphans": 0,
                  "max_char_len": 0, "gt4k": 0, "gt8k": 0}
        for r in stats_rows:
            print(f"{r['code']:14} {r['articles']:>7} {r['chunks']:>7} {r['repealed']:>9} "
                  f"{r['orphans']:>7} {r['max_char_len']:>9} {r['gt4k']:>7} {r['gt8k']:>7}")
            for k in ("articles", "chunks", "repealed", "orphans", "gt4k", "gt8k"):
                totals[k] += r[k]
            totals["max_char_len"] = max(totals["max_char_len"], r["max_char_len"])
        print("-" * 90)
        print(f"{'TOTAL':14} {totals['articles']:>7} {totals['chunks']:>7} {totals['repealed']:>9} "
              f"{totals['orphans']:>7} {totals['max_char_len']:>9} {totals['gt4k']:>7} {totals['gt8k']:>7}")
        return

    if args.code:
        if args.code not in CODES:
            print(f"Unknown code: {args.code}")
            sys.exit(1)
        trees, chunks = process_code(args.code)
        if trees:
            save_artifacts(args.code, trees, chunks)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
