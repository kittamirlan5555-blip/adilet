"""
Этап 4 audit (v5): pages text+anchors через flattening документа.

Подход:
1. Из BS4 строим линейную последовательность (chunk, is_link, href).
2. Полный текст склеиваем; запоминаем диапазоны, которые внутри <a>.
3. Текст разбиваем на "линии" (по \n из <br> и блочных границ).
4. Для каждого замечания находим место "Статья N." в линиях, окно до след. статьи.
5. В окне ищем ключи замечания, проверяем, попали ли они в ссылочный диапазон.
"""
import json, re
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[2]
REGISTER = ROOT / "data" / "reports" / "01_master_remarks.json"
FINAL_DIR = ROOT / "data" / "final"
OUT_JSON = ROOT / "data" / "reports" / "03_anara_current_state_audit.json"
OUT_MD = ROOT / "data" / "reports" / "03_anara_current_state_audit.md"

CODES = ["appk","byudzhet","ekologicheskiy","grazhdanskiy","koap","nalog",
         "predprinimatel","socialnyy","trudovoy","ugolovniy","upk","zemelnyy"]

BLOCK_TAGS = {"p","div","h1","h2","h3","h4","h5","h6","li","tr","ul","ol","article","section","header","footer"}


def flatten(soup):
    """Return:
      text: full text string
      link_ranges: list of (start, end, href) describing slices that were inside <a>
      line_offsets: list of line-start offsets in `text` (each line = block / <br>)
    """
    body = soup.body or soup
    pieces = []
    link_ranges = []  # list of (start_idx, end_idx, href)

    def append_chunk(s, in_link, href, link_start_ref):
        # `link_start_ref` is a list of len 1 [start_offset or None]
        if not s:
            return
        cur = sum(len(p) for p in pieces)
        pieces.append(s)
        if in_link and link_start_ref[0] is None:
            link_start_ref[0] = cur

    def walk(node, link_stack):
        if isinstance(node, NavigableString):
            in_link = bool(link_stack)
            cur_offset = sum(len(p) for p in pieces)
            s = str(node)
            if s:
                pieces.append(s)
                if in_link:
                    # extend the topmost link's text range
                    top = link_stack[-1]
                    if top["start"] is None:
                        top["start"] = cur_offset
                    top["end"] = cur_offset + len(s)
            return
        if not isinstance(node, Tag):
            return
        if node.name == "br":
            pieces.append("\n")
            return
        if node.name in BLOCK_TAGS:
            if pieces and not pieces[-1].endswith("\n"):
                pieces.append("\n")
            for c in node.children:
                walk(c, link_stack)
            if pieces and not pieces[-1].endswith("\n"):
                pieces.append("\n")
            return
        if node.name == "a":
            href = (node.get("href", "") or "").strip()
            # If anchor has no href, it's just an id-target marker — don't treat as a hyperlink range
            if not href or href == "#":
                # still recurse so text is captured, but don't push a link entry
                for c in node.children:
                    walk(c, link_stack)
                return
            entry = {"start": None, "end": None, "href": href}
            link_stack.append(entry)
            for c in node.children:
                walk(c, link_stack)
            link_stack.pop()
            if entry["start"] is not None and entry["end"] is not None:
                link_ranges.append((entry["start"], entry["end"], entry["href"]))
            return
        # generic inline
        for c in node.children:
            walk(c, link_stack)

    walk(body, [])
    text = "".join(pieces)
    return text, link_ranges


def parse_place(place):
    pl = re.sub(r"\s+", " ", place.lower()).replace(")", " ").replace(",", " ")
    art = pt = subpt = chap = para = None
    m = re.search(r"стат(?:ья|ьи|ьей|ьёй|ьею|ье|и|ью|ьями)\s+(\S+)", pl)
    if m: art = m.group(1).strip(".:;")
    m = re.search(r"пункт(?:а|ом|у)?\s+(\S+)", pl)
    if m: pt = m.group(1).strip(".:;")
    m = re.search(r"подпункт(?:а|ом|у|ах|ы)?\s+(\S+)", pl)
    if m: subpt = m.group(1).strip(".:;")
    m = re.search(r"глав(?:а|ы|у|е|ой|ою)\s+(\S+)", pl)
    if m: chap = m.group(1).strip(".:;")
    m = re.search(r"параграф(?:ом|а|у|е)?\s+(\S+)", pl)
    if m: para = m.group(1).strip(".:;")
    return {"article": art, "point": pt, "subpoint": subpt, "chapter": chap, "paragraph": para}


ARTICLE_HEAD = re.compile(r"Статья\s+(\d[0-9\-А-Яа-яA-Za-z]*)\s*\.", re.UNICODE)
CHAPTER_HEAD = re.compile(r"Глава\s+(\d[0-9\-]*)\b", re.UNICODE)


def find_article_span(text, art_n):
    """Return (start, end) char offsets containing the article."""
    if not art_n:
        return None
    # Find "Статья {art_n}."; ensure not followed by another digit (so "Статья 12" != "Статья 121")
    pat = re.compile(rf"Статья\s+{re.escape(art_n)}(?!\d)\s*\.", re.UNICODE)
    m = pat.search(text)
    if not m:
        return None
    start = m.start()
    # next article header
    n = ARTICLE_HEAD.search(text, m.end())
    end = n.start() if n else len(text)
    return (start, end)


def find_chapter_span(text, chap_n):
    if not chap_n:
        return None
    pat = re.compile(rf"Глава\s+{re.escape(chap_n)}(?!\d)\b", re.UNICODE)
    m = pat.search(text)
    if not m:
        return None
    start = m.start()
    n = CHAPTER_HEAD.search(text, m.end())
    end = n.start() if n else len(text)
    return (start, end)


def is_range_inside_link(rng_start, rng_end, link_ranges):
    """Return matching link entry if any link overlaps with [rng_start, rng_end)."""
    for (ls, le, href) in link_ranges:
        # overlap?
        if not (le <= rng_start or ls >= rng_end):
            return (ls, le, href)
    return None


def normalize(s):
    return re.sub(r"\s+", " ", s).strip().lower()


# self-code name fragments to filter from key extraction (per code).
# These appear as ordinary words in the kodex's own text but the audit
# was matching them as if they were the expected link target — false positives.
SELF_CODE_NAME_TOKENS = {
    "appk": ["административн", "процедурно"],
    "byudzhet": ["бюджетн"],
    "ekologicheskiy": ["экологическ"],
    "grazhdanskiy": ["гражданск"],
    "koap": ["об административных правонаруш", "об ап", "административн"],
    "nalog": ["налогов", "о налог"],
    "predprinimatel": ["предпринимательск"],
    "socialnyy": ["социальн"],
    "trudovoy": ["трудов"],
    "ugolovniy": ["уголовн"],
    "upk": ["уголовно-процессуальн", "уголовном", "уголовно"],
    "zemelnyy": ["земельн"],
}


def extract_keys(fragment, current_code=None):
    nf = normalize(fragment)
    keys = []
    self_tokens = SELF_CODE_NAME_TOKENS.get(current_code, []) if current_code else []

    def add(k):
        k = re.sub(r"\s+", " ", k.strip()).strip()
        # Filter out keys that are essentially just a self-code name token
        # (e.g., "земельный", "трудового", "налоговый") — these are too generic.
        if self_tokens:
            for tok in self_tokens:
                if k.startswith(tok):
                    # Check if the key has at least one OTHER significant word
                    rest = k[len(tok):].strip().lstrip("ая ое ом у е ах их ыми ого ему ой ью ом ии")
                    if not rest or len(rest) < 6:
                        return  # skip — too generic
        if 8 <= len(k) <= 120 and k not in keys:
            keys.append(k)
    # Cross-code mentions: code name + " кодекс*"
    # ВАЖНО: требуем чтобы за code-name шло слово "кодекс*" — иначе бы "социальных",
    # "земельных" и т.д. матчились бы как ключи на любые упоминания этих слов в
    # обычном тексте, что приводило к false positives.
    for m in re.finditer(r"(налогов\w+|трудов\w+|гражданск\w+|уголовно-процессуальн\w+|уголовн\w+|социальн\w+|предпринимательск\w+|экологическ\w+|административн\w+\s+процедурно\w+|бюджетн\w+|земельн\w+|водн\w+|лесн\w+)\s+кодекс\w+(?:\s+республики казахстан)?", nf):
        add(m.group(0))
    # Cross-code with article number
    for m in re.finditer(r"стат(?:ьей|ьи|ью|ье|ьями)\s+\d[\d\-]*(?:\s*,\s*\d[\d\-]*)*\s+\w+ кодекса", nf):
        add(m.group(0))
    # quoted law name
    for m in re.finditer(r'закон(?:ом|а|у|е)?\s+(?:республики казахстан|рк)\s*"[^"]+?"', nf):
        add(m.group(0))
    # law "X" without quotes
    for m in re.finditer(r'закон(?:ом|а|у|е)?\s+(?:республики казахстан|рк)\s+о[бт]?\s+[\w\s\-,]+?(?=\s*[\.,;:]|$|\(|\))', nf):
        add(m.group(0))
    # "законодательством ... о X"
    for m in re.finditer(r'законодательств\w+\s+(?:республики казахстан\s+)?о[бт]?\s+[\w\s\-]+?(?=\s*[\.,;:]|$|\(|\))', nf):
        add(m.group(0))
    for m in re.finditer(r'законодательным актом республики казахстан\s+о[бт]?\s+[\w\s\-]+?(?=\s*[\.,;:]|$)', nf):
        add(m.group(0))
    # NOTE: bare "настоящего кодекса" / "настоящей статьи" / etc. are intentionally
    # NOT added as keys. They're so generic and rarely included *inside* the <a>
    # wrapper (links are on numbers/article-names, not on the trailing "наст-")
    # that including them causes massive false-negative FAIL_NOT_LINKED.
    # параграф / раздел / глава X
    for m in re.finditer(r'параграф(?:ом)?\s+\S+', nf):
        add(m.group(0))
    for m in re.finditer(r'раздел[аеу]?\s+\d\S*', nf):
        add(m.group(0))
    for m in re.finditer(r'глав(?:ой|ы|у|а)?\s+\d\S*', nf):
        add(m.group(0))
    # "статью N"
    for m in re.finditer(r'стат(?:ью|ьями|ьей|ьи|ьёй)\s+\d[\d\-]*', nf):
        add(m.group(0))
    # Constitutional law: требуем явное имя закона в кавычках или конкретное
    # сочетание, иначе ключ типа "конституционными законами республики казахстан"
    # ложно матчится на префикс, а реальная ссылка стоит на ИМЕНИ закона —
    # это давало false positive FAIL_NOT_LINKED.
    for m in re.finditer(r'конституц\w+\s+закон\w+\s+(?:республики казахстан\s+)?"[^"]+?"', nf):
        add(m.group(0))
    return keys


def find_substr(text, key, scope_start, scope_end):
    """Find first occurrence of `key` in text[scope_start:scope_end], case-insensitive.
    Returns (start, end) absolute offsets or None.
    """
    lowtext = text.lower()
    pos = lowtext.find(key, scope_start, scope_end)
    if pos < 0:
        return None
    return (pos, pos + len(key))


def evaluate(remark, text, link_ranges):
    current_code = remark.get("code")
    place = parse_place(remark["place_raw"])
    span = find_article_span(text, place["article"])
    if span is None and place["chapter"]:
        span = find_chapter_span(text, place["chapter"])
    if span is None:
        return {"status": "FAIL_NOT_FOUND",
                "reason": f"article '{place.get('article')}' / chapter '{place.get('chapter')}' not located",
                "keys": [], "matches": []}
    start, end = span
    keys = extract_keys(remark["fragment"], current_code=current_code)
    if not keys:
        # Check if the section has any external links at all
        link_in_section = any(start <= ls and le <= end for (ls, le, _) in link_ranges)
        return {"status": "PASS_UNCLASSIFIED" if link_in_section else "FAIL_NOT_LINKED",
                "reason": "No keys derived; section has anchors" if link_in_section else "No keys derived; section has no anchors",
                "keys": keys, "matches": [], "excerpt": text[start:start+200]}
    matches = []
    for k in keys:
        loc = find_substr(text, k, start, end)
        if loc is None:
            matches.append({"key": k, "found_in_text": False, "linked": None, "href": None})
            continue
        kstart, kend = loc
        link_match = is_range_inside_link(kstart, kend, link_ranges)
        if link_match:
            ls, le, href = link_match
            matches.append({"key": k, "found_in_text": True, "linked": True, "href": href, "link_text_span": [ls, le]})
        else:
            matches.append({"key": k, "found_in_text": True, "linked": False, "href": None})
    # Verdict
    any_linked = any(m["linked"] for m in matches if m.get("linked"))
    any_text_only = any(m["found_in_text"] and not m["linked"] for m in matches)
    any_found = any(m["found_in_text"] for m in matches)
    if any_linked:
        # Find first linked match
        ml = next(m for m in matches if m.get("linked"))
        href = ml["href"]
        if not href:
            return {"status": "FAIL_EMPTY_HREF", "reason": "linked but href empty", "keys": keys, "matches": matches}
        if href == "#":
            return {"status": "FAIL_HASH_HREF", "reason": "linked but href='#'", "keys": keys, "matches": matches}
        return {"status": "PASS", "reason": f"Linked. First href: {href}", "keys": keys, "matches": matches,
                "excerpt": text[start:start+200]}
    if any_text_only:
        # text present but no link
        m0 = next(m for m in matches if m["found_in_text"] and not m["linked"])
        return {"status": "FAIL_NOT_LINKED",
                "reason": f"Key '{m0['key'][:50]}' is in section text but NOT wrapped in <a>",
                "keys": keys, "matches": matches,
                "excerpt": text[start:start+200]}
    # Not in text at all
    return {"status": "FAIL_NOT_FOUND",
            "reason": f"None of {len(keys)} keys found in article text (first key='{keys[0][:50]}')",
            "keys": keys, "matches": matches,
            "excerpt": text[start:start+200]}


def main():
    remarks = json.loads(REGISTER.read_text(encoding="utf-8"))
    docs = {}
    for code in CODES:
        f = FINAL_DIR / f"{code}_ready.html"
        if not f.exists():
            docs[code] = None; continue
        soup = BeautifulSoup(f.read_text(encoding="utf-8"), "lxml")
        text, link_ranges = flatten(soup)
        docs[code] = (text, link_ranges)
        print(f"  {code}: text={len(text)}c, links={len(link_ranges)}")

    rows = []
    for r in remarks:
        if r["code"] == "_GLOBAL":
            rows.append({**r, "status": "MANUAL_REVIEW", "reason": "Global structural remark (article headers boldness check)"})
            continue
        if r["code"] == "upk" and "регрессия" in r["fragment"].lower():
            rows.append({**r, "status": "MANUAL_REVIEW", "reason": "Whole-code regression — covered by per-remark checks"})
            continue
        doc = docs.get(r["code"])
        if doc is None:
            rows.append({**r, "status": "FAIL_NOT_FOUND", "reason": "HTML missing"})
            continue
        text, link_ranges = doc
        v = evaluate(r, text, link_ranges)
        rows.append({**r, **v})

    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    from collections import Counter, defaultdict
    by_st = Counter(r["status"] for r in rows)
    print("\nStatus:", dict(by_st.most_common()))
    by_cs = defaultdict(Counter)
    for r in rows:
        by_cs[r["code"]][r["status"]] += 1
    print("\nBy code:")
    for c in sorted(by_cs):
        print(f"  {c}: {dict(by_cs[c])}")

    md = [f"# Этап 4 — Audit состояния (v5, по реестру 01_master_remarks.json)\n\n",
          f"Замечаний: {len(rows)}. HTML: `data/final/<code>_ready.html`. Подход: flatten text + link ranges.\n\n",
          "## Статусы\n\n| Статус | Кол-во |\n|---|---|\n"]
    for k, v in by_st.most_common():
        md.append(f"| {k} | {v} |\n")
    md.append("\n## По кодексам\n\n| Кодекс | Всего | PASS | FAIL_* | UNCLASS/MANUAL |\n|---|---|---|---|---|\n")
    for c in sorted(by_cs):
        cnt = by_cs[c]
        tot = sum(cnt.values())
        p = sum(v for k, v in cnt.items() if k.startswith("PASS") and "UNCLASS" not in k)
        f_ = sum(v for k, v in cnt.items() if k.startswith("FAIL"))
        oth = tot - p - f_
        md.append(f"| `{c}` | {tot} | {p} | {f_} | {oth} |\n")
    md.append("\n## Детальная таблица\n\n")
    md.append("| ID | Код | Место | Тип реестра | Статус | Причина | Первый href |\n|---|---|---|---|---|---|---|\n")
    for r in rows:
        mh = r.get("matches") or []
        first_href = next((m.get("href","") for m in mh if m.get("linked")), "—")
        reason = (r.get("reason") or "")
        if len(reason) > 130: reason = reason[:127] + "…"
        place = r["place_raw"].replace("|", "\\|")
        md.append(f"| `{r['id']}` | `{r['code']}` | {place} | {r['problem_type']} | **{r['status']}** | {reason} | `{first_href or '—'}` |\n")
    OUT_MD.write_text("".join(md), encoding="utf-8")
    print(f"\nWrote: {OUT_JSON.name}, {OUT_MD.name}")


if __name__ == "__main__":
    main()
