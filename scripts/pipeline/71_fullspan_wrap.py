# -*- coding: utf-8 -*-
"""ПОЛНО-СПАНОВОЕ оборачивание ссылок «пункт N статьи M» -> одна сплошная <a>.

Требование Анары: ссылочная фраза «пункт N статьи M» должна быть ОДНОЙ непрерывной
<a>, а не «пункт N»-линк + «статьи M» плейн (или два отдельных линка). href НЕ меняем
для A/B; для M/C поглощаем менее конкретную цель (пункт > статья; первый якорь диапазона).

ДВИГАЕМ ТОЛЬКО ГРАНИЦЫ <a> через перенос текстовых узлов в DOM — видимый текст
документа (get_text) НЕ меняется (инвариант, проверяется sha ДО==ПОСЛЕ).

ПАТТЕРНЫ:
  A FORWARD : <a>пункт N</a> <плейн «статьи M»>            -> <a>пункт N статьи M</a>   (href тот же)
  B BACKWARD: <плейн «пункт N»> <a>статьи M</a>            -> <a>пункт N статьи M</a>   (href тот же)
  M MERGE   : <a>пункт N</a> <a>статьи M</a>               -> <a>пункт N статьи M</a>   (keep пункт href, drop статья)
  C RANGE   : <a>N</a>-<a>M</a>  |  <a>N</a>-<плейн M>      -> <a>N-M</a>                 (keep 1-й href, drop 2-й)

ГРАНИЦЫ: спан кончается на номере статьи; НЕ поглощаем «настоящего Кодекса/статьи»,
«Республики Казахстан», «Закона …». НЕ сливаем две разные статьи-ссылки. Цепочки из
нескольких пункт-ссылок перед статьёй -> COMPLEX (не трогаем, логируем).

РЕЖИМЫ:
  python 71_fullspan_wrap.py <code...> [--apply]
    без --apply: ФАЗА 1 ИНВЕНТАРИЗАЦИЯ (read-only) -> отчёт data/reports/71_fullspan_<code>.txt
    --apply    : ФАЗА 2 ПРИМЕНИТЬ с гейтами; перезапись data/final/<code>_ready.html
"""
import re
import sys
import json
import hashlib
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

ROOT = paths.ROOT
FINAL = paths.FINAL
REPORTS = paths.GATES    # машинные гейт-отчёты (дерево v2)

ORD = (r"перв|втор|трет|четверт|пят|шест|седьм|восьм|девят|десят|"
       r"одиннадц|двенадц|тринадц|четырнадц|пятнадц")

RE_REF_HEAD = re.compile(r"^\s*(?:(?:под)?пункт\w*|част\w+|абзац\w*)\b", re.I)
RE_REF_ENDNUM = re.compile(r"\d\)?\s*$")                       # ref текст оканчивается номером
RE_ART_HEAD = re.compile(r"^\s*стать\w+\s+\d", re.I)           # «статьи M…» (есть цифра)
RE_NUMONLY = re.compile(r"^\s*\d+\s*$")                        # голый номер (для диапазонов)

# в плейн-тексте СРАЗУ после <a> начинается «статьи M(-K)»
RE_FWD_ART = re.compile(r"^(?P<gap>\s*)(?P<art>стать\w+\s+\d+(?:-\d+)?)", re.I)
# в плейн-тексте СРАЗУ после <a> начинается «-M» (диапазон с плейн-номером)
RE_FWD_RANGE = re.compile(r"^(?P<gap>\s*[–-]\s*)(?P<num>\d+)", re.I)

# опц.квалификатор (часть/абзац+порядков. ИЛИ подпункт+список номеров)
_QUAL = (r"(?:(?:част\w+|абзац\w*)\s+(?:" + ORD + r")\w*"
         r"(?:\s*(?:,|и|или)\s*(?:" + ORD + r")\w*)*"
         r"|подпункт\w*\s+\d+\)?(?:\s*[,)]?\s*\d+\)?)*)")
# ЕДИНИЧНАЯ ссыл.единица в конце предшеств. плейн-текста (для BACKWARD к «статье»):
# опц.квалификатор + РОВНО ОДИН пункт. Жадно ловит «частью второй пункта 3»,
# «частями второй и третьей пункта 1», «подпунктов 1), 2), 4) пункта 2», но при
# «пункта 1 и ... пункта 2 статьи M» берёт только ХВОСТОВУЮ единицу (пункта 2).
RE_BWD_UNIT = re.compile(
    r"(?P<unit>(?:" + _QUAL + r"\s+)?(?:под)?пункт\w*\s+\d+\)?)\s*$", re.I)
# ТОЛЬКО квалификатор в конце плейн-текста (для BACKWARD к «пункту»-линку):
RE_BWD_QUAL = re.compile(r"(?P<unit>" + _QUAL + r")\s*$", re.I)
# линк начинается со ссыл.головы пункта/подпункта
RE_PUNKT_HEAD = re.compile(r"^\s*(?:под)?пункт\w*\s+\d", re.I)


def code_path(code):
    return FINAL / f"{code}_ready.html"


def gettext_sha(soup):
    return hashlib.sha256(soup.get_text().encode("utf-8")).hexdigest()


def href_multiset(soup):
    out = {}
    for a in soup.find_all("a", href=True):
        out[a["href"]] = out.get(a["href"], 0) + 1
    return out


def prev_significant(node):
    """Возвращает (узел, собранный_whitespace). Узел — первый предшествующий
    значимый sibling (Tag или непустой NavigableString); ws — склеенные пустые строки."""
    p = node.previous_sibling
    ws = ""
    while p is not None and isinstance(p, NavigableString) and str(p).strip() == "":
        ws = str(p) + ws
        p = p.previous_sibling
    return p, ws


def text_of(node):
    return node.get_text() if isinstance(node, Tag) else str(node)


def detect(a):
    """Классифицирует якорь a. Возвращает dict-кандидат или None.
    kind: A|B|M|C ; плюс данные для применения."""
    t = a.get_text()

    # ---- сторона СТАТЬИ: a == «статьи M» -> B (плейн пункт слева) или M (линк-пункт слева)
    if RE_ART_HEAD.match(t):
        prev, ws = prev_significant(a)
        if isinstance(prev, Tag) and prev.name == "a" and RE_REF_HEAD.match(text_of(prev)) \
                and RE_REF_ENDNUM.search(text_of(prev)):
            # цепочка? предыдущий значимый перед prev — ещё один ref-линк -> COMPLEX
            pprev, _ = prev_significant(prev)
            if isinstance(pprev, Tag) and pprev.name == "a" and RE_REF_HEAD.match(text_of(pprev)):
                return {"kind": "COMPLEX", "a": a, "why": "chain ref-link before статья",
                        "preview": text_of(pprev) + " | " + text_of(prev) + " | " + t}
            return {"kind": "M", "ref": prev, "art": a, "ws": ws,
                    "keep": prev.get("href"), "drop": a.get("href"),
                    "before": text_of(prev) + ws + t,
                    "after": (text_of(prev) + ws + t)}
        if isinstance(prev, NavigableString):
            m = RE_BWD_UNIT.search(str(prev))
            if m:
                tail = str(prev)[m.start("unit"):]
                head = str(prev)[:m.start("unit")]
                return {"kind": "B", "art": a, "prev": prev, "tail": tail, "head": head,
                        "keep": a.get("href"),
                        "before": "…" + str(prev)[-30:] + "[" + t + "]",
                        "after": "…" + head[-20:] + "[" + tail + t + "]"}
        return None

    # ---- линк начинается с «пункт/подпункт N» и слева плейн-квалификатор «часть X» ----
    if RE_PUNKT_HEAD.match(t):
        prev, ws = prev_significant(a)
        if isinstance(prev, NavigableString):
            m = RE_BWD_QUAL.search(str(prev))
            if m and "пункт" not in m.group("unit").lower():
                tail = str(prev)[m.start("unit"):]
                head = str(prev)[:m.start("unit")]
                return {"kind": "B", "art": a, "prev": prev, "tail": tail, "head": head,
                        "keep": a.get("href"),
                        "before": "…" + str(prev)[-30:] + "[" + t[:20] + "]",
                        "after": "…" + head[-20:] + "[" + tail + t[:20] + "]"}

    # ---- сторона ПУНКТА/номера: a — ref или номер -> A (плейн статья) / C (диапазон)
    nxt = a.next_sibling
    if isinstance(nxt, NavigableString):
        s = str(nxt)
        if RE_REF_HEAD.match(t) and RE_REF_ENDNUM.search(t):
            m = RE_FWD_ART.match(s)
            if m:
                absorbed = s[:m.end("art")]
                return {"kind": "A", "a": a, "sib": nxt, "absorbed": absorbed,
                        "rest": s[m.end("art"):], "keep": a.get("href"),
                        "before": "[" + t + "]" + s[:30],
                        "after": "[" + t + absorbed + "]" + s[m.end("art"):][:20]}
        if RE_FWD_RANGE.match(s) and (RE_NUMONLY.match(t) or RE_REF_ENDNUM.search(t)):
            m = RE_FWD_RANGE.match(s)
            absorbed = s[:m.end("num")]
            return {"kind": "C", "a": a, "sib": nxt, "absorbed": absorbed,
                    "rest": s[m.end("num"):], "keep": a.get("href"), "drop": None,
                    "before": "[" + t + "]" + s[:20], "after": "[" + t + absorbed + "]"}
    # диапазон с линк-номером: <a>N</a> <ws «-»> <a>M</a>
    if RE_NUMONLY.match(t) or RE_REF_ENDNUM.search(t):
        p = a.next_sibling
        ws = ""
        while isinstance(p, NavigableString) and str(p).strip() in ("", "-", "–", "—") \
                and ("-" in str(p) or "–" in str(p) or str(p).strip() == "" ):
            ws += str(p)
            p = p.next_sibling
            if "-" in ws or "–" in ws:
                break
        if ("-" in ws or "–" in ws) and isinstance(p, Tag) and p.name == "a" \
                and RE_NUMONLY.match(p.get_text()):
            return {"kind": "C", "lo": a, "hi": p, "ws": ws,
                    "keep": a.get("href"), "drop": p.get("href"),
                    "before": "[" + t + "]" + ws + "[" + p.get_text() + "]",
                    "after": "[" + t + ws + p.get_text() + "]"}
    return None


def scan(soup):
    cands = []
    for a in soup.find_all("a"):
        if a.find_parent("a") is not None:
            continue
        c = detect(a)
        if c:
            cands.append(c)
    return cands


# ---------------- APPLY (DOM-мутации, get_text-инвариантные) ----------------

def apply_A(c):
    a, sib = c["a"], c["sib"]
    a.append(NavigableString(c["absorbed"]))
    sib.replace_with(NavigableString(c["rest"]))


def apply_B(c):
    a, prev = c["art"], c["prev"]
    a.insert(0, NavigableString(c["tail"]))
    prev.replace_with(NavigableString(c["head"]))


def apply_M(c):
    ref, art = c["ref"], c["art"]
    cur = ref.next_sibling
    while cur is not None:
        nxt = cur.next_sibling
        if cur is art:
            for child in list(art.children):
                ref.append(child.extract())
            art.decompose()
            break
        ref.append(cur.extract())
        cur = nxt


def apply_C(c):
    if "absorbed" in c:                       # диапазон с плейн-номером (forward-like)
        a, sib = c["a"], c["sib"]
        a.append(NavigableString(c["absorbed"]))
        sib.replace_with(NavigableString(c["rest"]))
    else:                                     # диапазон двух линк-номеров
        lo, hi = c["lo"], c["hi"]
        cur = lo.next_sibling
        while cur is not None:
            nxt = cur.next_sibling
            if cur is hi:
                for child in list(hi.children):
                    lo.append(child.extract())
                hi.decompose()
                break
            lo.append(cur.extract())
            cur = nxt


APPLIERS = {"A": apply_A, "B": apply_B, "M": apply_M, "C": apply_C}


def collect_ids(soup):
    ids = set()
    for t in soup.find_all(attrs={"id": True}):
        ids.add(t["id"])
    for t in soup.find_all(attrs={"name": True}):
        ids.add(t["name"])
    return ids


def dangling(soup):
    ids = collect_ids(soup)
    bad = 0
    for a in soup.find_all("a", href=True):
        h = a["href"].strip()
        if h.startswith("#"):
            if h[1:] and h[1:] not in ids:
                bad += 1
    return bad


def nested_count(soup):
    return sum(1 for a in soup.find_all("a") if a.find_parent("a") is not None)


def run(code, apply_mode):
    path = code_path(code)
    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    sha0 = gettext_sha(soup)
    href0 = href_multiset(soup)
    dangle0 = dangling(soup)

    cands = scan(soup)
    by = {"A": 0, "B": 0, "M": 0, "C": 0, "COMPLEX": 0}
    for c in cands:
        by[c["kind"]] += 1

    L = []
    P = L.append
    P("=" * 100)
    P(f"ПОЛНО-СПАНОВОЕ ОБОРАЧИВАНИЕ — {code}_ready.html — "
      f"{'ФАЗА 2 APPLY' if apply_mode else 'ФАЗА 1 ИНВЕНТАРИЗАЦИЯ (read-only)'}")
    P("=" * 100)
    P(f"кандидатов: A(forward)={by['A']}  B(backward)={by['B']}  M(merge-2-links)={by['M']}  "
      f"C(range)={by['C']}  COMPLEX(skip)={by['COMPLEX']}")
    P("-" * 100)
    shown = 0
    for c in cands:
        line = f"[{c['kind']}] before: {c.get('before','')!r}   ->   after: {c.get('after', c.get('why',''))!r}"
        if c["kind"] != "COMPLEX":
            line += f"   keep={c.get('keep')}" + (f" drop={c.get('drop')}" if c.get('drop') else "")
        P(line)
        shown += 1

    actionable = [c for c in cands if c["kind"] in APPLIERS]

    if not apply_mode:
        out = REPORTS / f"71_fullspan_{code}.txt"
        out.write_text("\n".join(L) + "\n", encoding="utf-8")
        head = "\n".join(L[:5] + ["...", *L[5:45]]) if len(L) > 50 else "\n".join(L)
        print(head)
        print(f"\n[inventory] {code}: actionable={len(actionable)} complex={by['COMPLEX']} "
              f"-> {out}")
        return

    # ---------------- ФАЗА 2: применяем по fixpoint ----------------
    applied = {"A": 0, "B": 0, "M": 0, "C": 0}
    dropped_hrefs = []
    rounds = 0
    while True:
        rounds += 1
        cs = [c for c in scan(soup) if c["kind"] in APPLIERS]
        if not cs:
            break
        c = cs[0]
        if c.get("drop"):
            dropped_hrefs.append((c["kind"], c["keep"], c["drop"]))
        APPLIERS[c["kind"]](c)
        applied[c["kind"]] += 1
        if rounds > 100000:
            raise RuntimeError("fixpoint runaway")

    # ---- ГЕЙТЫ ----
    sha1 = gettext_sha(soup)
    href1 = href_multiset(soup)
    dangle1 = dangling(soup)
    nested1 = nested_count(soup)

    assert sha1 == sha0, f"GET_TEXT CHANGED! {sha0[:12]} -> {sha1[:12]}"
    assert nested1 == 0, f"NESTED <a> = {nested1}"
    assert dangle1 == 0, f"DANGLING #z = {dangle1} (было {dangle0})"

    # href-инвариант для A/B: их применение не должно менять multiset.
    # Уменьшения допустимы ТОЛЬКО на drop-цели от M/C.
    expected_drops = {}
    for _, keep, drop in dropped_hrefs:
        expected_drops[drop] = expected_drops.get(drop, 0) + 1
    diffs = []
    keys = set(href0) | set(href1)
    for k in keys:
        d = href0.get(k, 0) - href1.get(k, 0)
        if d != 0:
            exp = expected_drops.get(k, 0)
            if d != exp:
                diffs.append((k, href0.get(k, 0), href1.get(k, 0), exp))
    assert not diffs, f"HREF multiset unexpected change: {diffs}"

    P("-" * 100)
    P(f"ПРИМЕНЕНО: A={applied['A']} B={applied['B']} M={applied['M']} C={applied['C']} "
      f"(раундов={rounds})")
    P(f"ГЕЙТЫ: get_text sha ДО==ПОСЛЕ={sha0 == sha1} ({sha0[:12]})  nested<a>={nested1}  "
      f"dangling#z={dangle1}  href-diff-unexpected={len(diffs)}")
    P(f"ПОГЛОЩЁННЫЕ href (M/C, менее конкретные): {len(dropped_hrefs)}")
    for kind, keep, drop in dropped_hrefs:
        P(f"   {kind}: keep {keep}  drop {drop}")

    path.write_text(str(soup), encoding="utf-8")
    out = REPORTS / f"71_fullspan_{code}_applied.txt"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:60]))
    print(f"\n[APPLIED] {code}: A={applied['A']} B={applied['B']} M={applied['M']} C={applied['C']}  "
          f"sha-invariant={sha0 == sha1}  nested={nested1}  dangling={dangle1}  -> wrote {path.name}")
    print(f"report: {out}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply_mode = "--apply" in sys.argv
    codes = args or ["grazhdanskiy", "grazhdanskiy_osob"]
    for code in codes:
        run(code, apply_mode)


if __name__ == "__main__":
    main()
