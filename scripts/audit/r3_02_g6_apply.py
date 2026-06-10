# -*- coding: utf-8 -*-
"""R3 БЛОК 1, шаг 2: приведение форм к канону пер-кейс. G6 -> 0.

python scripts/audit/r3_02_g6_apply.py [--apply]
-> reports/r3/g6_apply_report.md

Канон пер-кейс (НЕ валом):
  SPAN/EXTEND — канон = ПОЛНЫЙ спан (§3 CLAUDE.md), в какой бы форме он ни был;
                короткая сторона расширяется сдвигом границ <a>; смежные <a>,
                целиком попавшие в новый спан, поглощаются (их текст остаётся).
  WRAP        — ссылка есть в одной форме, в другой тот же текст плэйн в том же
                контексте -> оборачивается тем же href. Сноски не трогаем.
  SPECIAL     — ручные кейсы (appk PDF/DOCX: канон structured, ready режется).

Движок работает на сырой строке: символы текста НЕ добавляются и НЕ удаляются,
двигаются только теги <a>. Гейт: §6.1 text-invariance обеих форм + пересчёт
G6 после применения.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

HOST = "https://adilet.zan.kz/rus/docs/"
RE_A_PAIR = re.compile(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a\s*>', re.I | re.S)
RE_A_OPEN = re.compile(r'<a\b[^>]*>', re.I)
RE_TAGS = re.compile(r"<[^>]+>")
APPLY = "--apply" in sys.argv

DOCS = ["grazhdanskiy_osob", "grazhdanskiy", "socialnyy", "nalog", "appk",
        "predprinimatel", "koap", "byudzhet"]

LOG = []


def P(s=""):
    LOG.append(s)
    print(s)


def own_doc_id(doc):
    cj = json.loads(paths.CODES_JSON.read_text(encoding="utf-8"))
    v = cj.get(doc)
    return v.get("doc_id") if isinstance(v, dict) else None


def canon_href(h, own):
    h = h.strip()
    if own:
        if h.startswith(HOST + own + "#"):
            return "#" + h.split("#", 1)[1]
        if h == HOST + own:
            return "@SELF_ROOT"
    return h


def norm(s):
    return re.sub(r"[\s\xa0]+", " ", RE_TAGS.sub("", s)).strip()


def canon_pairs(raw, own):
    pairs = Counter()
    for href, inner in RE_A_PAIR.findall(raw):
        pairs[(canon_href(href, own), norm(inner))] += 1
    return pairs


def divergences(raw_s, raw_r, own):
    ps, pr = canon_pairs(raw_s, own), canon_pairs(raw_r, own)
    return ({p for p in ps if p not in pr}, {p for p in pr if p not in ps},
            ps, pr)


def iter_links(raw, own):
    """[(start, end, href_raw, href_canon, inner_raw, inner_norm)]"""
    out = []
    for m in RE_A_PAIR.finditer(raw):
        out.append((m.start(), m.end(), m.group(1),
                    canon_href(m.group(1), own), m.group(2), norm(m.group(2))))
    return out


def walk(raw, pos, need, direction):
    """Съедает need (нормализованный текст) из raw начиная с pos влево(-1)/
    вправо(+1). Теги <a>/</a> поглощаются (записываются), другие теги — отказ.
    Возвращает (new_pos, absorbed_spans) | None."""
    absorbed = []
    chars = list(need) if direction > 0 else list(need)[::-1]
    i = pos
    k = 0
    n = len(raw)
    while k < len(chars):
        if direction > 0 and i >= n or direction < 0 and i <= 0:
            return None
        c = raw[i] if direction > 0 else raw[i - 1]
        if c == "<" and direction > 0 or c == ">" and direction < 0:
            # тег: найти его границы
            if direction > 0:
                j = raw.find(">", i)
                tag = raw[i:j + 1]
                span = (i, j + 1)
                nxt = j + 1
            else:
                j = raw.rfind("<", 0, i)
                tag = raw[j:i]
                span = (j, i)
                nxt = j
            if re.match(r"</?a\b", tag, re.I):
                absorbed.append(span)
                i = nxt
                continue
            return None
        if c in " \t\r\n\xa0":
            # пробел в raw: матчим пробел в need (если он там), иначе скип
            if chars[k] == " ":
                k += 1
            i += direction
            continue
        if chars[k] == " ":
            # need ждёт пробел, а в raw его нет — отказ
            return None
        if c != chars[k]:
            return None
        k += 1
        i += direction
    return (i, absorbed)


def sub_at_boundary(S, F):
    """Индекс S в F по границам слов (не внутри числа/слова), иначе -1."""
    start = 0
    while True:
        idx = F.find(S, start)
        if idx < 0:
            return -1
        before_ok = idx == 0 or not F[idx - 1].isalnum()
        j = idx + len(S)
        after_ok = j == len(F) or not F[j].isalnum()
        if before_ok and after_ok:
            return idx
        start = idx + 1


def extend_one(raw, own, H, S, F):
    """Расширить ОДНО вхождение <a H>S</a> до спана F. Возвращает
    (new_raw, absorbed_hrefs) | None."""
    idx = sub_at_boundary(S, F)
    if idx < 0:
        return None
    P_need, X_need = F[:idx].rstrip(), F[idx + len(S):].lstrip()
    for (a, b, href_raw, hc, inner_raw, inner_n) in iter_links(raw, own):
        if hc != H or inner_n != S:
            continue
        open_end = raw.find(">", a) + 1
        lw = walk(raw, a, P_need, -1) if P_need else (a, [])
        rw = walk(raw, b, X_need, +1) if X_need else (b, [])
        if lw is None or rw is None:
            continue
        lo, labs = lw
        hi, rabs = rw
        # дотянуть границы до ЦЕЛЫХ элементов: walk мог остановиться сразу
        # после открывающего <a> чужого линка (его инер — часть нового спана)
        while True:
            m2 = re.search(r"<a\b[^>]*>[\s\xa0]*$", raw[:lo], re.I)
            if m2:
                lo = m2.start()
                continue
            break
        while True:
            m2 = re.match(r"[\s\xa0]*</a\s*>", raw[hi:], re.I)
            if m2:
                hi += m2.end()
                continue
            break
        region = raw[lo:hi]
        # регион обязан быть сбалансирован по <a> (иначе родилась бы вложенность)
        depth, bal_ok = 0, True
        for t in re.finditer(r"<a\b[^>]*>|</a\s*>", region, re.I):
            depth += 1 if t.group(0)[1] != "/" else -1
            if depth < 0:
                bal_ok = False
                break
        if not bal_ok or depth != 0:
            continue
        absorbed_hrefs = [m.group(1) for m in RE_A_PAIR.finditer(region)
                          if canon_href(m.group(1), own) != H]
        open_tag = raw[a:open_end]
        cleaned = re.sub(r"</a\s*>|<a\b[^>]*>", "", region, flags=re.I)
        new_raw = raw[:lo] + open_tag + cleaned + "</a>" + raw[hi:]
        return new_raw, absorbed_hrefs
    return None


def merge_neighbor(raw, own, H, S, pairs_form, pairs_other):
    """Вхождение <a H>S</a>, рядом (через пробелы) <a H2>T2</a>; объединённый
    спан C с href H2 существует в другой форме с дефицитом здесь -> слить.
    Возвращает (new_raw, H2, C) | None."""
    for (a, b, href_raw, hc, inner_raw, inner_n) in iter_links(raw, own):
        if hc != H or inner_n != S:
            continue
        # сосед справа
        m = re.match(r'([\s\xa0]*)<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a\s*>',
                     raw[b:b + 400], re.I | re.S)
        if m:
            H2 = canon_href(m.group(2), own)
            T2 = norm(m.group(3))
            C = norm(S + " " + T2)
            if pairs_other.get((H2, C), 0) > pairs_form.get((H2, C), 0):
                region = raw[a:b + m.end()]
                cleaned = re.sub(r"</a\s*>|<a\b[^>]*>", "", region, flags=re.I)
                open_tag = re.search(r'<a\b[^>]*>', raw[b:b + m.end()],
                                     re.I).group(0)
                new_raw = raw[:a] + open_tag + cleaned + "</a>" + raw[b + m.end():]
                return new_raw, H2, C
        # сосед слева
        m = re.search(r'<a\b[^>]*href="([^"]*)"[^>]*>([^<]*)</a\s*>([\s\xa0]*)$',
                      raw[max(0, a - 400):a], re.I | re.S)
        if m:
            H2 = canon_href(m.group(1), own)
            T2 = norm(m.group(2))
            C = norm(T2 + " " + S)
            if pairs_other.get((H2, C), 0) > pairs_form.get((H2, C), 0):
                lo = max(0, a - 400) + m.start()
                region = raw[lo:b]
                open_tag = re.search(r'<a\b[^>]*>', region, re.I).group(0)
                cleaned = re.sub(r"</a\s*>|<a\b[^>]*>", "", region, flags=re.I)
                new_raw = raw[:lo] + open_tag + cleaned + "</a>" + raw[b:]
                return new_raw, H2, C
    return None


def context_of(raw, own, H, T, width=45):
    """Контексты (before, after) всех <a H>T</a> в форме-каноне."""
    out = []
    for (a, b, href_raw, hc, inner_raw, inner_n) in iter_links(raw, own):
        if hc == H and inner_n == T:
            out.append((norm(raw[max(0, a - 250):a])[-width:],
                        norm(raw[b:b + 250])[:width], href_raw))
    return out


def balance_prefix(raw):
    """Префиксный баланс <a>: bal[i] = открытых <a> до позиции i (грубо)."""
    events = []
    for m in re.finditer(r"<a\b[^>]*>|</a\s*>", raw, flags=re.I):
        events.append((m.start(), 1 if m.group(0)[1] != "/" else -1))
    return events


def in_link(events, pos):
    bal = 0
    for p, d in events:
        if p >= pos:
            break
        bal += d
    return bal > 0


def text_regex(T):
    return re.compile(r"[\s\xa0]+".join(re.escape(w) for w in T.split()))


def wrap_one(raw, own, H, T, want_ctx):
    """Обернуть плэйн-вхождение T (контекст ~ want_ctx) в <a>."""
    events = balance_prefix(raw)
    best = None
    for m in text_regex(T).finditer(raw):
        if in_link(events, m.start()):
            continue
        if "<" in m.group(0):
            continue
        if 'class="note"' in raw[max(0, m.start() - 300):m.start()]:
            continue
        cb = norm(raw[max(0, m.start() - 250):m.start()])[-45:]
        ca = norm(raw[m.end():m.end() + 250])[:45]
        for (wb, wa, href_raw) in want_ctx:
            score = (cb == wb) + (ca == wa)
            if best is None or score > best[0]:
                best = (score, m.start(), m.end(), href_raw)
    if best is None or best[0] < 2:
        return None
    _, s, e, href_raw = best
    if H == "@SELF_ROOT":
        href = href_raw
    elif H.startswith("#"):
        href = H
    else:
        href = href_raw
    return raw[:s] + f'<a href="{href}">' + raw[s:e] + "</a>" + raw[e:]


RE_ADJ = re.compile(
    r'(<a\b[^>]*href="([^"]*)"[^>]*>)((?:(?!</a\s*>).)*?)</a\s*>'
    r'([\s\xa0]+)(<a\b[^>]*href="\2"[^>]*>)', re.I | re.S)


def collapse_adjacent(raw):
    """<a H>X</a> <a H>Y</a> -> <a H>X Y</a> (один таргет, текст неизменен)."""
    n = 0
    while True:
        m = RE_ADJ.search(raw)
        if not m:
            break
        raw = raw[:m.start()] + m.group(1) + m.group(3) + m.group(4) + raw[m.end():]
        n += 1
    return raw, n


def special_appk(raw_r):
    """appk: ready склеил PDF+DOCX в один <a href=.../download/docx>.
    Канон structured: PDF -> /download, DOCX -> /download/docx."""
    pat = re.compile(
        r'<a\b[^>]*href="(https://adilet\.zan\.kz/rus/docs/K2000000350/download)/docx"[^>]*>'
        r'(\s*PDF\s*)(.*?)(DOCX\s*)</a\s*>', re.I | re.S)
    m = pat.search(raw_r)
    if not m:
        return raw_r, False
    base = m.group(1)
    new = (f'<a href="{base}">{m.group(2).strip()}</a> '
           f'<a href="{base}/docx">{m.group(3).strip()}{m.group(4).strip()}</a>')
    return raw_r[:m.start()] + new + raw_r[m.end():], True


def process(doc):
    own = own_doc_id(doc)
    fs = paths.FINAL / f"{doc}_structured.html"
    fr = paths.FINAL / f"{doc}_ready.html"
    raw = {"s": fs.read_text(encoding="utf-8"),
           "r": fr.read_text(encoding="utf-8")}
    orig_text = {k: "".join(RE_TAGS.sub(" ", v).split()) for k, v in raw.items()}

    stats = Counter()
    manual = []
    wrap_memo = set()

    if doc == "appk":
        raw["r"], done = special_appk(raw["r"])
        if done:
            stats["special"] += 1
            P(f"  SPECIAL appk: PDF/DOCX в ready разделены по канону structured")

    # ПРЕ-ПАСС: смежные <a> с ОДНИМ href = один спан (§3); симметрично обеим формам
    for k in ("s", "r"):
        raw[k], n = collapse_adjacent(raw[k])
        if n:
            stats["collapse"] += n
            P(f"  COLLAPSE[{k}]: склеено смежных одинаковых href: {n}")

    # Итерации: ОДНО действие за проход, после каждого пересчёт расхождений
    for _ in range(600):
        only_s, only_r, ps, pr = divergences(raw["s"], raw["r"], own)
        if not only_s and not only_r:
            break
        progress = False
        # EXTEND: пара (короткий ⊂ длинный) при одном href; правится форма,
        # где сейчас короткий спан (канон = полный спан, §3)
        pairs_cache = {"s": ps, "r": pr}
        for form, only in (("s", only_s), ("r", only_r)):
            other = "r" if form == "s" else "s"
            for (H, S) in sorted(only):
                # 1а: расширить КОРОТКИЙ дивергентный спан до полного из другой
                # формы (дисбаланс счётчиков — защита от каскада на подстроках)
                fulls = [T2 for (H2, T2) in pairs_cache[other]
                         if H2 == H and T2 != S
                         and sub_at_boundary(S, T2) >= 0
                         and len(T2) - len(S) < 120
                         and pairs_cache[other][(H, T2)]
                         > pairs_cache[form].get((H, T2), 0)]
                for F in sorted(fulls, key=len):
                    r2 = extend_one(raw[form], own, H, S, F)
                    if r2:
                        raw[form], absorbed = r2
                        stats["extend"] += 1
                        stats["absorbed"] += len(absorbed)
                        P(f"  EXTEND[{form}] {H} «{S[:40]}»->«{F[:60]}»"
                          + (f" поглощено: {absorbed}" if absorbed else ""))
                        progress = True
                        break
                if progress:
                    break
                # 1б: дивергентный ПОЛНЫЙ спан (H,T) в form — в другой форме
                # найти короткий (H,T2⊂T) и расширить ТАМ (с поглощением)
                shorts = [T2 for (H2, T2) in pairs_cache[other]
                          if H2 == H and T2 != S
                          and sub_at_boundary(T2, S) >= 0
                          and len(S) - len(T2) < 120
                          and pairs_cache[form][(H, S)]
                          > pairs_cache[other].get((H, S), 0)]
                for T2 in sorted(shorts, key=len, reverse=True):
                    r2 = extend_one(raw[other], own, H, T2, S)
                    if r2:
                        raw[other], absorbed = r2
                        stats["extend"] += 1
                        stats["absorbed"] += len(absorbed)
                        P(f"  EXTEND[{other}] {H} «{T2[:40]}»->«{S[:60]}»"
                          + (f" поглощено: {absorbed}" if absorbed else ""))
                        progress = True
                        break
                if progress:
                    break
                # 1в MERGE: вхождение (H,S) поглощается СОСЕДНИМ линком (H2,T2)
                # своей же формы, если объединённый спан есть в другой форме
                mg = merge_neighbor(raw[form], own, H, S, pairs_cache[form],
                                    pairs_cache[other])
                if mg:
                    raw[form], H2, C = mg
                    stats["merge"] += 1
                    P(f"  MERGE[{form}] {H} «{S[:40]}» -> {H2} «{C[:60]}»")
                    progress = True
                    break
            if progress:
                break
        if progress:
            continue
        # WRAP: одиночки; контекст должен совпасть С ОБЕИХ сторон, один раз
        for src, only, tgt_key in (("s", only_s, "r"), ("r", only_r, "s")):
            for (H, T) in sorted(only):
                if (tgt_key, H, T) in wrap_memo:
                    continue
                wrap_memo.add((tgt_key, H, T))
                ctx = context_of(raw[src], own, H, T)
                r2 = wrap_one(raw[tgt_key], own, H, T, ctx)
                if r2:
                    raw[tgt_key] = r2
                    stats["wrap"] += 1
                    P(f"  WRAP[{tgt_key}] {H} «{T[:60]}»")
                    progress = True
                    break
            if progress:
                break
        if not progress:
            break

    only_s, only_r, _, _ = divergences(raw["s"], raw["r"], own)
    for (H, T) in sorted(only_s):
        manual.append(("structured", H, T))
    for (H, T) in sorted(only_r):
        manual.append(("ready", H, T))

    # ГЕЙТЫ: §6.1 text-invariance + отсутствие вложенных/несбалансированных <a>
    ok = True
    for k, f in (("s", fs), ("r", fr)):
        now = "".join(RE_TAGS.sub(" ", raw[k]).split())
        if now != orig_text[k]:
            ok = False
            P(f"  !! TEXT-INVARIANCE FAIL {f.name}")
        depth = nested = 0
        for t in re.finditer(r"<a\b[^>]*>|</a\s*>", raw[k], re.I):
            depth += 1 if t.group(0)[1] != "/" else -1
            if depth > 1 or depth < 0:
                nested += 1
        if nested or depth != 0:
            ok = False
            P(f"  !! NESTED/UNBALANCED <a> FAIL {f.name} (nested={nested}, depth={depth})")
    P(f"  {doc}: collapse={stats['collapse']} extend={stats['extend']} "
      f"merge={stats['merge']} wrap={stats['wrap']} "
      f"absorbed={stats['absorbed']} special={stats['special']} "
      f"остаток={len(manual)} invariance={'OK' if ok else 'FAIL'}")
    for form, H, T in manual:
        P(f"    MANUAL[{form}] {H} «{T[:70]}»")
        # контекст для ручного разбора
        key = "s" if form == "structured" else "r"
        for cb, ca, hr in context_of(raw[key], own, H, T, width=70)[:3]:
            P(f"      ctx: …{cb} ▶ {ca}…  (href={hr})")

    if APPLY and ok:
        fs.write_text(raw["s"], encoding="utf-8")
        fr.write_text(raw["r"], encoding="utf-8")
    return stats, manual, ok


def main():
    docs = [a for a in sys.argv[1:] if not a.startswith("--")] or DOCS
    P(f"# R3 БЛОК 1 — применение канона форм ({'APPLY' if APPLY else 'DRY-RUN'})")
    P("")
    total = Counter()
    all_manual = {}
    for doc in docs:
        P(f"## {doc}")
        st, manual, ok = process(doc)
        total += st
        if manual:
            all_manual[doc] = manual
        P("")
    P(f"ИТОГО: extend={total['extend']} merge={total['merge']} "
      f"wrap={total['wrap']} absorbed={total['absorbed']} "
      f"special={total['special']} "
      f"manual={sum(len(v) for v in all_manual.values())}")
    out = paths.REPORTS / "r3" / "g6_apply_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
