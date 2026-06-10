"""ТЗ-02. СТРОГАЯ финальная проверка ТОЛЬКО удалённых внутренних #z-ссылок.

Read-only. Через BeautifulSoup, по data/final_backup_TZ02/ vs data/final/.

Для каждой ИСЧЕЗНУВШЕЙ <a href="#z...">…</a> по каждому коду (кроме upk)
находим её Tag в backup-DOM (по document-order index из SequenceMatcher)
и проверяем СТРУКТУРНО, что в backup-DOM она была внутри сноски/примечания:

  (S1) у <a> есть ПРЕДОК с class, содержащим "note";  ИЛИ
  (S2) ближайший <p>/<div>-предок, чей первый видимый текст начинается на
       "Примечани[ея]";  ИЛИ
  (S3) <a> в красной ИЗПИ/РЦПИ <font>-цепочке (предок-<font color=#FF0000>
       либо имеет сам маркер «Примечание ИЗПИ!/РЦПИ!», либо смежен по <br/>+ws
       с красным <font>, содержащим этот маркер);  ИЛИ
  (S4) <a> в склейке смежных <span class="note">: ближайший непустой и
       не-<a>-сосед слева И справа — это <span class="note">.

Если хоть одна из S1–S4 истинна — ссылка корректно отнесена к сноске.
NOT_IN_NOTE = ни одна структура не сработала = регресс.

NO writes.
"""
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
BACKUP = ROOT / "data" / "final_backup_TZ02"
CODES = ROOT / "config" / "codes.json"

INTERNAL_Z = re.compile(r'^#z\d')
PRIM_RE = re.compile(r'^\s*Примечани[ея]\b')
IZPI_MARK_RE = re.compile(r'Примечани[ея]\s+(?:ИЗПИ|РЦПИ)\s*!')


# ─── helpers ──────────────────────────────────────────────────────────
def is_ws(node):
    return isinstance(node, NavigableString) and not str(node).strip()


def is_a(node):
    return isinstance(node, Tag) and node.name == "a"


def is_br(node):
    return isinstance(node, Tag) and node.name == "br"


def is_note_span(node):
    return (isinstance(node, Tag) and node.name == "span"
            and "note" in (node.get("class") or []))


def is_red_font(node):
    if not (isinstance(node, Tag) and node.name == "font"):
        return False
    c = (node.get("color") or "").lstrip("#").upper()
    return c == "FF0000"


def first_visible_text(tag):
    for d in tag.descendants:
        if isinstance(d, NavigableString):
            s = str(d).strip()
            if s:
                return s
    return ""


# ─── структурные сигналы S1–S4 ────────────────────────────────────────
def s1_ancestor_note(a):
    for p in a.parents:
        if not isinstance(p, Tag):
            continue
        cls = p.get("class") or []
        if any("note" in c for c in cls):
            return True
    return False


def s2_primechanie_block(a):
    for p in a.parents:
        if not isinstance(p, Tag):
            continue
        if p.name in ("p", "div", "li"):
            if PRIM_RE.match(first_visible_text(p)):
                return True
            # дойдя до первого блочного предка — останавливаемся, чтобы не
            # засчитать выше расположенный «Примечание …» из соседней секции.
            return False
    return False


def s3_izpi_red_chain(a):
    red_font = None
    for p in a.parents:
        if is_red_font(p):
            red_font = p
            break
    if red_font is None:
        return False
    if IZPI_MARK_RE.search(red_font.get_text(" ", strip=True)):
        return True
    # шаг назад через смежные ws/<br/>/красный <font>
    cur = red_font.previous_sibling
    while cur is not None:
        if is_ws(cur) or is_br(cur):
            cur = cur.previous_sibling
            continue
        if is_red_font(cur):
            if IZPI_MARK_RE.search(cur.get_text(" ", strip=True)):
                return True
            cur = cur.previous_sibling
            continue
        break
    return False


def s4_note_span_cluster(a):
    """Слева и справа от <a> ближайший не-ws и не-<a> сосед — <span class='note'>."""
    def neighbor(start, direction):
        step = "previous_sibling" if direction == "prev" else "next_sibling"
        cur = getattr(start, step) if start is not None else None
        # некоторые узлы могут быть None
        while cur is not None:
            if is_ws(cur) or is_a(cur):
                cur = getattr(cur, step)
                continue
            return cur
        return None

    prev = neighbor(a, "prev")
    nxt = neighbor(a, "next")
    return is_note_span(prev) and is_note_span(nxt)


def classify(a):
    """Возвращает первый сработавший сигнал из S1..S4 или 'NONE'."""
    if s1_ancestor_note(a): return "S1"
    if s2_primechanie_block(a): return "S2"
    if s3_izpi_red_chain(a): return "S3"
    if s4_note_span_cluster(a): return "S4"
    return "NONE"


# ─── alignment через BS4-DOM с локальным контекстом ──────────────────
#
# Проблема: при дубликатах (4× <a href="#z1263">№ 375-V</a> в файле)
# SequenceMatcher по ключу (href, inner) выбирает «выживших» произвольно,
# и может назвать удалённым тот, что на самом деле уцелел.
#
# Решение: для каждой <a href="#z…"> вычисляем fingerprint
#    (href, inner, prev_text, next_text),
# где prev_text/next_text — по 60 символов нормализованного текста
# непосредственно до/после ссылки в документе (через soup-traversal,
# не по байтам — устойчиво к различиям сериализации BS4).
# Этот fingerprint практически гарантированно уникален для каждой
# конкретной позиции ссылки. Сравниваем multiset-ы backup vs current —
# несовпавшие в backup записи — исчезнувшие.
WS_RE = re.compile(r'\s+')


def normalize(s):
    return WS_RE.sub(' ', s).strip()


def collect_internal_a_with_context(soup, window=60):
    """[(href, inner, prev_ctx, next_ctx, tag)] в document-order для всех
    <a href='#z…'>."""
    nodes = list(soup.descendants)
    # построим текстовую ленту и индексы <a>-тегов в ней.
    pieces = []   # последовательность кусков плэйн-текста
    cumlen = []   # cumlen[i] = суммарная длина pieces[:i]
    a_positions = []  # (idx_in_pieces, tag, href, inner)
    total = 0
    for node in nodes:
        if isinstance(node, NavigableString):
            s = str(node)
            pieces.append(s)
            cumlen.append(total)
            total += len(s)
        elif isinstance(node, Tag) and node.name == "a":
            href = node.get("href") or ""
            if INTERNAL_Z.match(href):
                inner = node.get_text()
                a_positions.append((len(pieces), node, href, inner))
    # склеим всё в одну строку для контекста
    full = "".join(pieces)
    cumlen.append(total)

    out = []
    for (idx, tag, href, inner) in a_positions:
        # позиция в full, куда «вставится» inner — это cumlen[idx]
        # (т.к. inner-текст ссылки сам идёт как NavigableString после <a>
        # в descendants, и его pieces придут позже; но визуально inner
        # располагается ровно в этой точке).
        pos = cumlen[idx]
        prev_ctx = normalize(full[max(0, pos - window):pos])[-window:]
        next_start = pos  # после <a> текст продолжится с next-сиблингов;
                          # inner_text идёт в потоке pieces начиная с idx
        # Возьмём контекст ПОСЛЕ inner: pos + len(inner)
        after = pos + len(inner)
        # но inner сам присутствует как pieces[idx]; следующий контекст —
        # после него. Возьмём normalize первых window символов после
        # позиции `after` в full.
        next_ctx = normalize(full[after:after + window])[:window]
        out.append((href, inner, prev_ctx, next_ctx, tag))
    return out


def disappeared_internal_via_context(backup_soup, current_soup):
    B = collect_internal_a_with_context(backup_soup)
    C = collect_internal_a_with_context(current_soup)

    # multiset выживших по fingerprint
    surv = {}
    for (href, inner, pc, nc, _) in C:
        k = (href, inner, pc, nc)
        surv[k] = surv.get(k, 0) + 1

    gone_tags = []
    ambiguous = 0
    for (href, inner, pc, nc, tag) in B:
        k = (href, inner, pc, nc)
        if surv.get(k, 0) > 0:
            surv[k] -= 1
        else:
            gone_tags.append(tag)
    return gone_tags, ambiguous


# ─── описание для отчёта ──────────────────────────────────────────────
def describe_link(a):
    parent = a.parent
    parent_desc = "(detached)"
    if isinstance(parent, Tag):
        attrs = " ".join(f'{k}="{v}"' if not isinstance(v, list)
                         else f'{k}="{" ".join(v)}"'
                         for k, v in parent.attrs.items())
        parent_desc = f"<{parent.name}{(' ' + attrs) if attrs else ''}>"
    # короткий контекст: текст родителя
    if isinstance(parent, Tag):
        ctx = parent.get_text(" ", strip=True)
        ctx = ctx[:240] + ("…" if len(ctx) > 240 else "")
    else:
        ctx = ""
    return {
        "href": a.get("href", ""),
        "text": a.get_text("", strip=False),
        "parent": parent_desc,
        "ctx": ctx,
    }


# ─── главный обход ────────────────────────────────────────────────────
def audit_code(code):
    total_internal = 0
    total_not_in_note = 0
    by_signal = {"S1": 0, "S2": 0, "S3": 0, "S4": 0, "NONE": 0}
    examples = []
    for suf in ("ready", "structured"):
        b = BACKUP / f"{code}_{suf}.html"
        c = FINAL / f"{code}_{suf}.html"
        if not b.exists() or not c.exists():
            continue
        bt = b.read_text(encoding="utf-8")
        ct = c.read_text(encoding="utf-8")
        bs = BeautifulSoup(bt, "html.parser")
        cs = BeautifulSoup(ct, "html.parser")
        gone, _ = disappeared_internal_via_context(bs, cs)
        # gone содержит BS4-Tag'и в backup-DOM для каждой исчезнувшей ссылки
        total_internal += len(gone)
        for a in gone:
            sig = classify(a)
            by_signal[sig] += 1
            if sig == "NONE":
                total_not_in_note += 1
                if len(examples) < 8:
                    d = describe_link(a)
                    d["file"] = f"{code}_{suf}.html"
                    examples.append(d)
    return total_internal, total_not_in_note, by_signal, examples


def main():
    import argparse
    global BACKUP
    ap = argparse.ArgumentParser()
    ap.add_argument("codes", nargs="*",
                    help="коды для проверки (пусто = все из codes.json кроме upk)")
    ap.add_argument("--backup-dir", default=str(BACKUP),
                    help="каталог бэкапа для diff (по умолчанию final_backup_TZ02)")
    args = ap.parse_args()
    BACKUP = Path(args.backup_dir)
    cfg = json.loads(CODES.read_text(encoding="utf-8"))
    if args.codes:
        codes = list(args.codes)
    else:
        codes = [k for k in cfg.keys() if not k.startswith("_") and k != "upk"]

    print(f"{'код':18}{'removed_int':>12}{'S1':>6}{'S2':>5}{'S3':>5}"
          f"{'S4':>5}{'NOT_IN_NOTE':>14}")
    print("-" * 65)
    grand = {"int": 0, "S1": 0, "S2": 0, "S3": 0, "S4": 0, "NIN": 0}
    all_examples = []
    for code in codes:
        n_int, n_nin, sig, ex = audit_code(code)
        print(f"{code:18}{n_int:>12}{sig['S1']:>6}{sig['S2']:>5}"
              f"{sig['S3']:>5}{sig['S4']:>5}{n_nin:>14}")
        grand["int"] += n_int
        for k in ("S1", "S2", "S3", "S4"):
            grand[k] += sig[k]
        grand["NIN"] += n_nin
        for e in ex:
            e["code"] = code
            all_examples.append(e)
    print("-" * 65)
    print(f"{'ИТОГО':18}{grand['int']:>12}{grand['S1']:>6}{grand['S2']:>5}"
          f"{grand['S3']:>5}{grand['S4']:>5}{grand['NIN']:>14}")

    if grand["NIN"] == 0:
        print("\n[OK] NOT_IN_NOTE == 0 по всем кодам — внутренние ссылки "
              "тела не задеты. ТЗ-02 закрыт окончательно.")
        sys.exit(0)

    print(f"\n[FAIL] NOT_IN_NOTE = {grand['NIN']}. Примеры (до 5 на запуск):")
    for e in all_examples[:15]:
        print(f"\n  file={e['file']}")
        print(f"  href={e['href']!r}  text={e['text']!r}")
        print(f"  parent_tag={e['parent']}")
        print(f"  ctx={e['ctx']!r}")
    sys.exit(1)


if __name__ == "__main__":
    main()
