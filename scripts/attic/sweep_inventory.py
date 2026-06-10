"""
Read-only инвентаризация: B (resolution-mismatch), C (external-anchor mismatch), D (missing-suffix).
Не правит файлы.

Запуск: python scripts/sweep_inventory.py
"""
import json
import re
import sys
import io
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
CODES_JSON = ROOT / "config" / "codes.json"

codes_data = json.loads(CODES_JSON.read_text(encoding="utf-8"))
CODES = {k: v["doc_id"] for k, v in codes_data.items() if not k.startswith("_")}
DOC_TO_CODE = {v: k for k, v in CODES.items()}  # K1400000226 -> ugolovniy

# External code name → our code key mapping
EXT_NAME_MAP = {
    "Уголовно-процессуального": "upk",
    "Уголовно-процессуальным": "upk",
    "Уголовно-процессуальном": "upk",
    "уголовно-процессуальным": "upk",
    "Уголовного кодекса": "ugolovniy",
    "Уголовным кодексом": "ugolovniy",
    "уголовного кодекса": "ugolovniy",
    "Гражданского": "grazhdanskiy",
    "Гражданским": "grazhdanskiy",
    "гражданского кодекса": "grazhdanskiy",
    "Налогового": "nalog",
    "Налоговым": "nalog",
    "Налогом": "nalog",
    "Земельного": "zemelnyy",
    "Земельным": "zemelnyy",
    "Бюджетного": "byudzhet",
    "Бюджетным": "byudzhet",
    "Трудового": "trudovoy",
    "Трудовым": "trudovoy",
    "Социального": "socialnyy",
    "Социальным": "socialnyy",
    "Экологического": "ekologicheskiy",
    "Экологическим": "ekologicheskiy",
    "Предпринимательского": "predprinimatel",
    "Предпринимательским": "predprinimatel",
    "административных правонарушениях": "koap",
    "Административным процедурно-процессуальным": "appk",
    "Административного процедурно-процессуального": "appk",
}


def build_anchor_to_artnum(text):
    """For each id/name=zX, find its parent article-div's data-number.
    Returns dict: anchor -> art_num (or None if no parent article-div)."""
    # Collect all article-div openings with positions
    art_divs = []
    for m in re.finditer(
        r'<div class="article" data-number="([^"]+)" data-type="статья"', text
    ):
        art_divs.append((m.start(), m.group(1)))

    def parent_artnum(pos):
        last_num = None
        for art_pos, num in art_divs:
            if art_pos <= pos:
                last_num = num
            else:
                break
        return last_num

    anchor_map = {}
    for m in re.finditer(r'(?:id|name)="(z[A-Za-z0-9_\-]+)"', text):
        anchor = m.group(1)
        if anchor not in anchor_map:
            anchor_map[anchor] = parent_artnum(m.start())
    return anchor_map


def extract_artnum_from_visible(visible):
    """Try to extract article number from visible text. Returns (artnum, is_article_ref).
    is_article_ref=False means it's likely 'N)' subpункт or 'N-M' часть."""
    v = visible.strip()

    # Skip subpункт refs ending with ')'
    if re.match(r"^\d+(?:-\d+)?\)\s*$", v):
        return None, False

    # 'статья[ями/ей/ью/и] N' or 'стать[ея] N-M'
    m = re.match(r"^(?:стать[еиюьяями]+\s+)(\d+(?:-\d+)?)\s*$", v)
    if m:
        return m.group(1), True

    # 'стать[ея] N (...)' or 'статья N. Title'
    m = re.match(r"^(?:стать[еиюьяями]+\s+)(\d+(?:-\d+)?)\b", v)
    if m:
        return m.group(1), True

    # Bare 'N' (with optional 'и' suffix) - likely list-of-articles ref
    m = re.match(r"^(\d+)\s*$", v)
    if m:
        return m.group(1), True

    # Bare suffix 'N-M' — treat as часть-ref, skip
    if re.match(r"^\d+-\d+\s*$", v):
        return None, False

    # Trailing space etc. — try harder
    m = re.match(r"^(\d+(?:-\d+)?)\b", v)
    if m:
        # also accept if preceded by no 'стать' but is just N — might still be article in list
        # but conservatively skip if it looks like 'N)'
        if "(" in v or ")" in v:
            return None, False
        return m.group(1), True

    return None, False


# === B: RESOLUTION-MISMATCH ===
def find_b_mismatches(text, anchor_map):
    """Find <a href='#zN'>visible</a> where visible-article-number ≠ data-number of zN parent."""
    mismatches = []
    for m in re.finditer(
        r'<a[^>]+href="#(z[A-Za-z0-9_\-]+)"[^>]*>([^<]*)</a>', text
    ):
        anchor = m.group(1)
        visible = m.group(2)
        artnum, is_ref = extract_artnum_from_visible(visible)
        if not is_ref or not artnum:
            continue
        target_num = anchor_map.get(anchor)
        if target_num is None:
            continue
        if target_num != artnum:
            mismatches.append((m.start(), anchor, visible.strip(), target_num, artnum))
    return mismatches


# === C: EXTERNAL-ANCHOR mismatch ===
def find_c_mismatches(text, all_anchor_maps):
    """Find <a href='https://adilet...DOC#zN'>visible</a> where visible has external code name,
    and target DOC is one of our 12; verify zN parent in DOC == artnum from visible.
    all_anchor_maps: dict {code -> anchor_map}"""
    mismatches = []
    for m in re.finditer(
        r'<a[^>]+href="https?://adilet\.zan\.kz/(?:rus|kaz)/docs/([A-Z]\d+_?[A-Z]?)(?:#(z[A-Za-z0-9_\-]+))?"[^>]*>([^<]*)</a>',
        text,
    ):
        doc_id = m.group(1)
        anchor = m.group(2)
        visible = m.group(3)
        if doc_id not in DOC_TO_CODE:
            continue
        if not anchor:
            continue  # no anchor → can't verify
        target_code = DOC_TO_CODE[doc_id]
        # Check visible contains article number + external code name
        # extract artnum
        v_artnum = None
        m_art = re.search(r"\bстать[еиюьяями]+\s+(\d+(?:-\d+)?)", visible)
        if m_art:
            v_artnum = m_art.group(1)
        else:
            # bare 'N кодекса' or trailing
            m_art = re.search(r"^(\d+(?:-\d+)?)\s+", visible.strip())
            if m_art:
                v_artnum = m_art.group(1)
        if not v_artnum:
            continue
        # Check external code mention
        has_ext_name = any(name in visible for name in EXT_NAME_MAP)
        if not has_ext_name:
            continue
        # Lookup target anchor in target code's anchor map
        target_map = all_anchor_maps.get(target_code, {})
        actual_artnum = target_map.get(anchor)
        if actual_artnum is None:
            mismatches.append(
                (
                    m.start(),
                    doc_id,
                    anchor,
                    visible.strip()[:60],
                    v_artnum,
                    f"anchor_not_in_{target_code}",
                )
            )
        elif actual_artnum != v_artnum:
            mismatches.append(
                (m.start(), doc_id, anchor, visible.strip()[:60], v_artnum, actual_artnum)
            )
    return mismatches


# === D: MISSING-SUFFIX ===
def find_d_missing_suffix(text, own_anchor_map_by_artnum):
    """Find plain (not in <a>) 'N-x' patterns where suffix article exists in same file.
    own_anchor_map_by_artnum: dict {artnum -> anchor}.
    Look for suffix-form ('N-M') in lists, NOT inside <a> tags."""
    missing = []
    # We look for patterns like "<a ...>N</a>, N-x," where N-x is plain.
    # Or "статьями ..., 108-1, ..." with 108-1 plain.
    # Heuristic: find 'N-M' as standalone token NOT inside <a>...</a>

    # Strip all <a>...</a> first to avoid false positives
    text_no_links = re.sub(r"<a\b[^>]*>.*?</a>", " ", text, flags=re.DOTALL)

    # find "N-M" tokens (where M is a small digit)
    for m in re.finditer(r"\b(\d+)-(\d+)(?=[\s,;\)\.])", text_no_links):
        candidate = f"{m.group(1)}-{m.group(2)}"
        # Skip if M > 99 (likely a real number range)
        if int(m.group(2)) > 99:
            continue
        # Check if this suffix article exists in own file
        if candidate in own_anchor_map_by_artnum:
            # Get context (be careful — text_no_links is shifted)
            # search same candidate in original text — approximate by position offset
            # quick check: appear as plain not in <a>
            missing.append((m.start(), candidate))
    # Dedupe by position
    seen = set()
    unique = []
    for pos, art in missing:
        key = (pos // 200, art)  # rough dedupe
        if key not in seen:
            seen.add(key)
            unique.append((pos, art))
    return unique


# === MAIN ===
def main():
    files = sorted(FINAL.glob("*_structured.html"))
    print(f"Scanning {len(files)} *_structured.html files...\n")

    # Pre-build anchor maps for all codes
    all_anchor_maps = {}
    own_artnum_maps = {}  # code -> {artnum -> wrapper_anchor_id}
    file_texts = {}

    for f in files:
        code = f.stem.replace("_structured", "")
        text = f.read_text(encoding="utf-8")
        file_texts[code] = text
        all_anchor_maps[code] = build_anchor_to_artnum(text)
        # Build artnum -> anchor (for D)
        artnum_to_anchor = {}
        for m in re.finditer(
            r'<div class="article" data-number="([^"]+)" data-type="статья" id="w_(z[A-Za-z0-9_\-]+)"',
            text,
        ):
            artnum, anchor = m.group(1), m.group(2)
            artnum_to_anchor[artnum] = anchor
        own_artnum_maps[code] = artnum_to_anchor

    # Now scan each file
    summary = []
    examples = defaultdict(dict)  # code -> {B/C/D -> [examples]}

    for f in files:
        code = f.stem.replace("_structured", "")
        text = file_texts[code]
        anchor_map = all_anchor_maps[code]
        own_arts = own_artnum_maps[code]

        b_mm = find_b_mismatches(text, anchor_map)
        c_mm = find_c_mismatches(text, all_anchor_maps)
        d_ms = find_d_missing_suffix(text, own_arts)

        summary.append((code, len(b_mm), len(c_mm), len(d_ms)))

        # Save 3 examples each
        examples[code]["B"] = b_mm[:3]
        examples[code]["C"] = c_mm[:3]
        examples[code]["D"] = d_ms[:3]

    # Print table
    print(f"{'код':18} {'B-mismatch':>11} {'C-mismatch':>11} {'D-missing':>11}")
    print("-" * 60)
    total_b = total_c = total_d = 0
    for code, b, c, d in summary:
        print(f"{code:18} {b:>11} {c:>11} {d:>11}")
        total_b += b
        total_c += c
        total_d += d
    print("-" * 60)
    print(f"{'TOTAL':18} {total_b:>11} {total_c:>11} {total_d:>11}")
    print()

    # Print examples
    counts_by_code = {row[0]: row[1:] for row in summary}
    for code, b, c, d in summary:
        if b == 0 and c == 0 and d == 0:
            continue
        print(f"\n=== {code} examples ===")
        for idx, kind in enumerate(("B", "C", "D")):
            ex = examples[code].get(kind, [])
            total = counts_by_code[code][idx]
            if total == 0:
                continue
            print(f"  [{kind}] (showing up to 3 of {total}):")
            for e in ex:
                if kind == "B":
                    pos, anchor, visible, target_num, vis_num = e
                    print(
                        f"      pos={pos} href=#{anchor} visible={visible[:30]!r} → факт.ст.{target_num} (ожидали ст.{vis_num})"
                    )
                elif kind == "C":
                    pos, doc_id, anchor, visible, v_artnum, actual = e
                    print(
                        f"      pos={pos} {doc_id}#{anchor} visible={visible[:60]!r} → factual={actual} (visible artnum={v_artnum})"
                    )
                else:
                    pos, art = e
                    print(f"      pos={pos} suffix-ст.{art} (anchor exists in own file)")

    return summary, examples


if __name__ == "__main__":
    main()
