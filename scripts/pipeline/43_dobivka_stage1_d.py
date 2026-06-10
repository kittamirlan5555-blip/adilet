# -*- coding: utf-8 -*-
"""
ДОБИВКА ПОКРЫТИЯ — ЭТАП 1: тип (d) хвосты перечней (самый безопасный).

«статьями N1, N2, N3 …», где залинкован/учтён только N1 (голова) -> оборачиваем
ХВОСТЫ N2,N3,… (индекс>=1) в <a href="#z{anchor}">N</a> ТЕМ ЖЕ паттерном, что
у обычных внутр. ссылок. Только там, где статья N реально существует в коде и
у неё есть валидный якорь.

Детект — ТОЧНО как в gap (scripts/40): RE_LIST по flatten_lines, тот же
editorial-фильтр. Дополнительно тащим provenance узлов, чтобы обернуть ровно
нужный NavigableString-фрагмент (видимый текст байт-в-байт прежний).

Якорь статьи N выбираем так, чтобы ссылка #z{anchor} ПРОШЛА аудит-OK:
  N in {id2art[zK], id2next[zK]}  (acc-множество аудита) — гарантируется по
  построению (берём кандидата из этого же множества; предпочитаем уже
  используемый рабочими ссылками якорь, затем «закладку начала статьи»).

Режимы:
  python scripts/43_dobivka_stage1_d.py            # DRY-RUN инвентаризация
  python scripts/43_dobivka_stage1_d.py --apply    # правит _structured И _ready (бэкап)

ASCII-safe stdout; отчёт в data/reports/43_stage1_d.txt
"""
import re, sys, shutil, difflib, importlib.util
from pathlib import Path
from collections import defaultdict, Counter
from bs4 import BeautifulSoup, NavigableString, Tag

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

ROOT = paths.ROOT
FINAL = paths.FINAL
BACKUP = paths.BACKUPS / "final_backup_DOBIVKA"
APPLY = "--apply" in sys.argv

# ── import audit module A (restore our stdout; detach A's wrapper) ──────────
saved = sys.stdout
spec = importlib.util.spec_from_file_location("A", str(ROOT / "scripts/audit_links_coverage.py"))
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
w = sys.stdout; sys.stdout = saved
try: w.detach()
except Exception: pass

LM = A.LINKMARK            # " ⟦L⟧ "
LMS = LM.strip()           # "⟦L⟧"
BLOCK_TAGS = A.BLOCK_TAGS
RE_ARTTITLE = A.RE_ARTTITLE

EDIT = ("вводится в действие", "действует до", "в редакции", "Заголовок",
        "Сноска", "изложен", "исключен", "исключён", "дополнен", "внесен",
        "внесён", "предусматривается в редакции", "приостанов")
def is_editorial(ctx): return any(k in ctx for k in EDIT)

TOKEN = r"(?:" + re.escape(LMS) + r"|\d+(?:-\d+)?)"
RE_LIST = re.compile(r"(?i)стат(?:ь[а-яё]{0,3}|ей)\s+(" + TOKEN + r"(?:\s*(?:,|\bи\b)\s*" + TOKEN + r")+)")
RE_NUM = re.compile(r"\d+(?:-\d+)?")

STAGE1_CODES = ["upk", "koap", "ugolovniy", "byudzhet"]
EXPECT_D = {"upk": 9, "koap": 9, "ugolovniy": 8, "byudzhet": 1}

log = []
def P(s=""): log.append(s)


# ── canonical article -> anchor (audit-OK by construction) ─────────────────
def build_canon(code, soup):
    self_doc = A.SELF_DOC.get(code, "")
    id2art, all_ids, art_numbers, id2next = A.build_id_to_art(soup)
    cand_start = defaultdict(list)   # id2next == N  (закладка начала статьи)
    cand_body = defaultdict(list)    # id2art  == N  (тело статьи)
    for zk in id2art.keys():         # порядок ключей = документ-порядок якорей
        nx = str(id2next.get(zk)); bd = str(id2art.get(zk))
        if nx and nx != "None": cand_start[nx].append(zk)
        if bd and bd != "None": cand_body[bd].append(zk)
    # якоря, уже используемые РАБОЧИМИ (OK) внутр. ссылками на статью N
    used = defaultdict(Counter)
    for a in soup.find_all("a", href=True):
        if not a.find_parent("div", attrs={"data-type": True}):
            continue
        kind, doc = A.classify_href(a["href"], self_doc)
        if kind != "internal":
            continue
        fm = re.search(r"#(z\d+[\w-]*)", a["href"])
        if not fm:
            continue
        zk = fm.group(1)
        if zk not in all_ids:
            continue
        ck, cn = A.claimed_article(a)
        if ck != "ARTICLE":
            continue
        acc = {str(id2art.get(zk)), str(id2next.get(zk))}
        if str(cn) in acc:
            used[str(cn)][zk] += 1
    canon = {}
    for N in set(cand_start) | set(cand_body):
        if used[N]:
            canon[N] = used[N].most_common(1)[0][0]
        elif cand_start.get(N):
            canon[N] = cand_start[N][0]
        elif cand_body.get(N):
            canon[N] = cand_body[N][0]
    return canon, art_numbers, (id2art, id2next, all_ids)


# ── flatten WITH node provenance (mirror of A.flatten_lines) ───────────────
def flatten_segments(el):
    """Возвращает список строк; каждая строка = список сегментов
    (kind, node, text): 'T'=NavigableString (text=str(node)), 'L'=<a> (text=LM)."""
    lines = []
    cur = []
    def flush():
        if cur:
            lines.append(cur[:]); cur.clear()
    def walk(node):
        for ch in node.children:
            if isinstance(ch, NavigableString):
                cur.append(("T", ch, str(ch)))
            elif isinstance(ch, Tag):
                if ch.name == "a":
                    cur.append(("L", ch, LM))
                elif ch.name == "br":
                    flush()
                elif ch.name in BLOCK_TAGS:
                    flush(); walk(ch); flush()
                else:
                    walk(ch)
    walk(el)
    flush()
    return lines


def line_index(segs):
    """(line_str, spans) ; spans=[(start,end,kind,node,text)]."""
    spans = []
    pos = 0
    parts = []
    for kind, node, text in segs:
        spans.append((pos, pos + len(text), kind, node, text))
        parts.append(text)
        pos += len(text)
    return "".join(parts), spans


def detect_tails(soup, canon):
    """Возвращает список ops: dict(node, off, length, num, anchor, exists, snippet, head).
    Детект 1:1 с gap (RE_LIST по строкам статья-div, editorial-фильтр)."""
    blocks = A.content_root(soup)
    art_divs = [b for b in blocks if b.get("data-type") == "статья"]
    ops = []
    n_tail_total = 0          # все хвосты (как считает gap), включая несуществующие
    skipped = []              # хвосты, для которых нет якоря (не оборачиваем)
    for div in art_divs:
        for segs in flatten_segments(div):
            line_str, spans = line_index(segs)
            probe = line_str.replace(LMS, " ").strip()
            if RE_ARTTITLE.match(probe):       # строка-заголовок статьи — как в gap
                continue
            for m in RE_LIST.finditer(line_str):
                ctx = line_str[max(0, m.start() - 45):m.end() + 20]
                if is_editorial(ctx):
                    continue
                lst = m.group(1)
                base = m.start(1)
                toks = list(re.finditer(re.escape(LMS) + r"|\d+(?:-\d+)?", lst))
                for i, tk in enumerate(toks):
                    if i == 0:
                        continue                # голова перечня — НЕ трогаем (stage1)
                    s = tk.group(0)
                    if s == LMS or not RE_NUM.fullmatch(s):
                        continue                # уже линк / не число
                    n_tail_total += 1
                    ts = base + tk.start(); te = base + tk.end()
                    # локализуем узел
                    seg = next((sp for sp in spans if sp[0] <= ts and te <= sp[1] and sp[2] == "T"), None)
                    snippet = re.sub(r"\s+", " ", line_str[max(0, m.start()-10):m.end()+10]).strip()
                    head = toks[0].group(0)
                    if seg is None:
                        skipped.append((s, "узел-не-T", snippet)); continue
                    off = ts - seg[0]
                    node = seg[3]
                    if str(node)[off:off + len(s)] != s:
                        skipped.append((s, "сдвиг-оффсета", snippet)); continue
                    anchor = canon.get(s)
                    if not anchor:
                        skipped.append((s, "нет-якоря/статьи", snippet)); continue
                    ops.append(dict(node=node, off=off, length=len(s), num=s,
                                    anchor=anchor, snippet=snippet, head=head))
    return ops, n_tail_total, skipped


# ── apply wraps to one soup (group by node, split once) ────────────────────
def apply_ops(soup, ops):
    bynode = defaultdict(list)
    for op in ops:
        bynode[id(op["node"])].append(op)
    nodes = {id(op["node"]): op["node"] for op in ops}
    nwrapped = 0
    for nid, group in bynode.items():
        node = nodes[nid]
        text = str(node)
        group.sort(key=lambda o: o["off"])
        pieces = []
        cur = 0
        for op in group:
            o = op["off"]; ln = op["length"]
            assert text[o:o+ln] == op["num"], "оффсет разъехался при apply"
            if o > cur:
                pieces.append(NavigableString(text[cur:o]))
            a = soup.new_tag("a", href="#" + op["anchor"])
            a.string = op["num"]
            pieces.append(a)
            cur = o + ln
            nwrapped += 1
        if cur < len(text):
            pieces.append(NavigableString(text[cur:]))
        # version-safe replace: insert pieces before node, then drop node
        for p in pieces:
            node.insert_before(p)
        node.extract()
    return nwrapped


# ── byte-identity gate: changed lines differ ONLY by inserted <a> wraps ────
# strip MY wrap pattern from BOTH sides so a pre-existing numeric #z link on a
# changed line cancels out (no false fail); equality then proves the only
# textual delta is inserted <a href="#z..">NUM</a> wrappers around bare numbers.
RE_UNWRAP = re.compile(r'<a href="#z[\w-]+">(\d+(?:-\d+)?)</a>')
def prove_text_identity(before, after, label):
    bl = before.splitlines(keepends=True)
    al = after.splitlines(keepends=True)
    sm = difflib.SequenceMatcher(None, bl, al, autojunk=False)
    bad = []
    nchg = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        nchg += 1
        b = "".join(bl[i1:i2]); a = "".join(al[j1:j2])
        if RE_UNWRAP.sub(r"\1", a) != RE_UNWRAP.sub(r"\1", b):
            bad.append((tag, b[:120], a[:120]))
    ok = not bad
    P(f"    [{label}] diff-блоков строк={nchg} ; обратная-развёртка==оригинал: {'OK' if ok else 'FAIL'}")
    if bad:
        for t, b, a in bad[:3]:
            P(f"        FAIL {t}: B«{b}» A«{a}»")
    return ok


def tag_inventory(soup):
    return Counter(t.name for t in soup.find_all(True))


def process(code, do_apply):
    sp = FINAL / f"{code}_structured.html"
    rp = FINAL / f"{code}_ready.html"
    s_raw = sp.read_text(encoding="utf-8")
    soup_s = BeautifulSoup(s_raw, "html.parser")
    canon, art_numbers, _ = build_canon(code, soup_s)
    ops_s, n_tail, skipped = detect_tails(soup_s, canon)
    P(f"\n=== {code} ===")
    P(f"  тип(d) хвостов всего (как в gap): {n_tail}  (ожид {EXPECT_D[code]})  "
      f"| обёрнуто: {len(ops_s)} | пропущено(нет статьи/якоря): {len(skipped)}")
    # примеры before->after
    for op in ops_s[:6]:
        P(f"    +<a href=#{op['anchor']}> {op['num']}  [голова {op['head']}]  …{op['snippet']}…")
    for num, why, snip in skipped[:6]:
        P(f"    skip {num} ({why})  …{snip}…")
    return dict(code=code, sp=sp, rp=rp, s_raw=s_raw, soup_s=soup_s,
                canon=canon, ops_s=ops_s, n_tail=n_tail, skipped=skipped)


def main():
    P("=" * 92)
    P("ДОБИВКА ЭТАП 1 — тип (d) хвосты перечней  " + ("[APPLY]" if APPLY else "[DRY-RUN]"))
    P("=" * 92)
    infos = []
    grand = 0; grand_tail = 0
    for code in STAGE1_CODES:
        info = process(code, APPLY)
        infos.append(info)
        grand += len(info["ops_s"]); grand_tail += info["n_tail"]
    P("\n" + "-" * 92)
    P(f"ИТОГО хвостов тип(d) обнаружено: {grand_tail} (ожид 27) ; будет обёрнуто: {grand}")

    if not APPLY:
        P("\nDRY-RUN: ничего не записано. Запусти с --apply для правки _structured И _ready.")
        out = "\n".join(log) + "\n"
        (paths.REPORTS / "43_stage1_d.txt").write_text(out, encoding="utf-8")
        sys.stdout.write(out.encode("ascii", "replace").decode("ascii"))
        return

    # ── APPLY ──
    BACKUP.mkdir(parents=True, exist_ok=True)
    P("\n" + "=" * 92)
    P("APPLY + ГЕЙТЫ")
    P("=" * 92)
    for info in infos:
        code = info["code"]; sp = info["sp"]; rp = info["rp"]
        # backup once
        for f in (sp, rp):
            bk = BACKUP / f.name
            if not bk.exists():
                shutil.copy2(f, bk)
        # --- _structured ---
        soup_s = info["soup_s"]; s_before = info["s_raw"]
        text_before_s = soup_s.get_text()
        inv_before_s = tag_inventory(soup_s)
        nw_s = apply_ops(soup_s, info["ops_s"])
        text_after_s = soup_s.get_text()
        inv_after_s = tag_inventory(soup_s)
        s_after = str(soup_s)
        # --- _ready (independent detect on its own article body, same canon) ---
        r_before = rp.read_text(encoding="utf-8")
        soup_r = BeautifulSoup(r_before, "html.parser")
        ops_r = detect_tails_ready(soup_r, info["canon"])
        text_before_r = soup_r.get_text()
        inv_before_r = tag_inventory(soup_r)
        nw_r = apply_ops(soup_r, ops_r)
        text_after_r = soup_r.get_text()
        inv_after_r = tag_inventory(soup_r)
        r_after = str(soup_r)

        P(f"\n=== {code} ===  обёрнуто structured={nw_s} ready={nw_r}")
        # GATE 1: visible text byte-identical
        g1s = text_before_s == text_after_s
        g1r = text_before_r == text_after_r
        P(f"  GATE1 видимый текст идентичен: structured={g1s} ready={g1r}")
        prove_text_identity(s_before, s_after, "structured")
        prove_text_identity(r_before, r_after, "ready")
        # GATE 1b: only <a> grew, by exactly nwrapped; other tags unchanged
        da_s = inv_after_s["a"] - inv_before_s["a"]
        other_s = {k: (inv_after_s[k]-inv_before_s[k]) for k in set(inv_before_s)|set(inv_after_s) if k != "a" and inv_after_s[k]-inv_before_s[k]}
        da_r = inv_after_r["a"] - inv_before_r["a"]
        other_r = {k: (inv_after_r[k]-inv_before_r[k]) for k in set(inv_before_r)|set(inv_after_r) if k != "a" and inv_after_r[k]-inv_before_r[k]}
        P(f"  GATE1b tag-инвентарь: structured d<a>={da_s} (==nwrapped {da_s==nw_s}) прочее={other_s or '0'} ; "
          f"ready d<a>={da_r} (=={nw_r==da_r}) прочее={other_r or '0'}")
        # GATE consistency: same wraps in both
        P(f"  GATE2 structured==ready по числу обёрток: {nw_s==nw_r} ({nw_s}=={nw_r})")
        if g1s and g1r and da_s == nw_s and da_r == nw_r and not other_s and not other_r and nw_s == nw_r:
            sp.write_text(s_after, encoding="utf-8")
            rp.write_text(r_after, encoding="utf-8")
            P(f"  ЗАПИСАНО: {sp.name}, {rp.name}")
        else:
            P(f"  !! ГЕЙТ НЕ ПРОЙДЕН — {code} НЕ записан")

    out = "\n".join(log) + "\n"
    (paths.REPORTS / "43_stage1_d.txt").write_text(out, encoding="utf-8")
    sys.stdout.write(out.encode("ascii", "replace").decode("ascii"))


def detect_tails_ready(soup, canon):
    """Тот же детект, но корень _ready = <article> (нет div[data-type])."""
    root = soup.find("article") or soup.body or soup
    ops = []
    for segs in flatten_segments(root):
        line_str, spans = line_index(segs)
        probe = line_str.replace(LMS, " ").strip()
        if RE_ARTTITLE.match(probe):
            continue
        for m in RE_LIST.finditer(line_str):
            ctx = line_str[max(0, m.start() - 45):m.end() + 20]
            if is_editorial(ctx):
                continue
            lst = m.group(1); base = m.start(1)
            toks = list(re.finditer(re.escape(LMS) + r"|\d+(?:-\d+)?", lst))
            for i, tk in enumerate(toks):
                if i == 0:
                    continue
                s = tk.group(0)
                if s == LMS or not RE_NUM.fullmatch(s):
                    continue
                ts = base + tk.start(); te = base + tk.end()
                seg = next((sp for sp in spans if sp[0] <= ts and te <= sp[1] and sp[2] == "T"), None)
                if seg is None:
                    continue
                off = ts - seg[0]; node = seg[3]
                if str(node)[off:off + len(s)] != s:
                    continue
                anchor = canon.get(s)
                if not anchor:
                    continue
                ops.append(dict(node=node, off=off, length=len(s), num=s, anchor=anchor))
    return ops


if __name__ == "__main__":
    main()
