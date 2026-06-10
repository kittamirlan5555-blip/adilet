"""LINK-LEVEL ДИФФ _ready vs _structured + сверка/синхронизация.

Цель: _structured — канон по ссылкам (его мерил аудит). _ready должен СОВПАДАТЬ
с ним по ссылкам. Этот скрипт извлекает упорядоченную последовательность
контент-ссылок (внутр. #zK + внешн./self /docs) из обоих файлов и сравнивает.

Расхождения = прошлые ручные правки, которые есть только в _structured (или
только в _ready, напр. #z23 — линк, вручную снятый в _structured, но оставшийся
в _ready). difflib показывает replace/delete/insert.

  python scripts/29_diff_ready_structured.py            # измерить (read-only)
  python scripts/29_diff_ready_structured.py --reconcile # подтянуть _ready по _structured
"""
import io
import re
import sys
import difflib
import importlib.util
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup, NavigableString, Tag

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

ROOT = paths.ROOT
FINAL = paths.FINAL
RECONCILE = "--reconcile" in sys.argv

_spec = importlib.util.spec_from_file_location(
    "audit_mod", ROOT / "scripts" / "audit_links_coverage.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
SELF_DOC = A.SELF_DOC

# только пайплайновые коды (у grazhdanskiy_osob нет _ready)
CODES = ["nalog", "trudovoy", "grazhdanskiy", "predprinimatel", "socialnyy",
         "ekologicheskiy", "zemelnyy", "upk", "koap", "appk", "byudzhet",
         "ugolovniy"]


def norm_href(href, self_doc):
    """Контент-ссылка -> канон-сигнатура; nav/мусор -> None (игнор)."""
    h = href.strip()
    if h.startswith("#z"):
        return h
    if h.startswith("javascript") or h.startswith("mailto"):
        return None
    m = re.search(r"/docs/([A-Z]\d{6,}_?)(#z[\w-]+)?", h)
    if m:
        doc, frag = m.group(1), m.group(2) or ""
        if doc == self_doc and frag:          # self-URL -> относительная
            return frag
        return f"/docs/{doc}{frag}"
    return None


def link_sigs(soup, self_doc):
    """Список (sig, text, tag) контент-ссылок в порядке документа."""
    out = []
    for a in soup.find_all("a", href=True):
        sig = norm_href(a["href"], self_doc)
        if sig is None:
            continue
        txt = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        out.append((sig, txt, a))
    return out


# режим ключа сравнения: HREF-only (значимый таргет) либо HREF+TEXT
HREF_ONLY = "--with-text" not in sys.argv


def diff_code(code):
    rp = FINAL / f"{code}_ready.html"
    sp = FINAL / f"{code}_structured.html"
    self_doc = SELF_DOC.get(code, "")
    soup_r = BeautifulSoup(rp.read_text(encoding="utf-8"), "html.parser")
    soup_s = BeautifulSoup(sp.read_text(encoding="utf-8"), "html.parser")
    R = link_sigs(soup_r, self_doc)
    S = link_sigs(soup_s, self_doc)
    if HREF_ONLY:
        keyR = [s for s, t, _ in R]
        keyS = [s for s, t, _ in S]
    else:
        keyR = [(s, t) for s, t, _ in R]
        keyS = [(s, t) for s, t, _ in S]
    sm = difflib.SequenceMatcher(a=keyR, b=keyS, autojunk=False)
    ops = [op for op in sm.get_opcodes() if op[0] != "equal"]
    return soup_r, R, S, keyR, keyS, ops, rp


def show(code, R, S, ops):
    if not ops:
        print(f"  {code:18} ready_links={len(R):>5} structured_links={len(S):>5}  ДИФФ=0")
        return 0
    n = 0
    print(f"  {code:18} ready_links={len(R):>5} structured_links={len(S):>5}  расхождений:")
    for tag, i1, i2, j1, j2 in ops:
        if tag == "replace":
            for k in range(max(i2 - i1, j2 - j1)):
                rv = R[i1 + k][:2] if i1 + k < i2 else None
                sv = S[j1 + k][:2] if j1 + k < j2 else None
                print(f"      REPLACE ready={rv}  ->  structured={sv}")
                n += 1
        elif tag == "delete":
            for k in range(i1, i2):
                print(f"      ONLY_IN_READY  {R[k][:2]}  (в structured ссылки нет)")
                n += 1
        elif tag == "insert":
            for k in range(j1, j2):
                print(f"      ONLY_IN_STRUCT {S[k][:2]}  (в ready ссылки нет)")
                n += 1
    return n


def reconcile_code(code, soup_r, R, S, ops, rp):
    """Подтягиваем _ready по _structured на уровне href.
    REPLACE: меняем href ready-ссылки на structured-сигнатуру.
    ONLY_IN_READY (delete): ссылку в _ready разворачиваем в текст (её нет в каноне).
    ONLY_IN_STRUCT (insert): требует оборачивания текста — печатаем для ручного
    разбора (на практике не встречается; если встретится — увидим)."""
    changed = 0
    manual = []
    for tag, i1, i2, j1, j2 in ops:
        if tag == "replace":
            for k in range(max(i2 - i1, j2 - j1)):
                if i1 + k < i2 and j1 + k < j2:
                    a = R[i1 + k][2]
                    new_sig = S[j1 + k][0]
                    # переносим только href; для self берём относительный #z
                    a["href"] = new_sig
                    changed += 1
                elif i1 + k < i2:  # лишняя ссылка в ready -> развернуть
                    a = R[i1 + k][2]
                    a.replace_with(NavigableString(a.get_text()))
                    changed += 1
                else:              # не хватает ссылки -> ручной разбор
                    manual.append(("insert", S[j1 + k][:2]))
        elif tag == "delete":
            for k in range(i1, i2):
                a = R[k][2]
                a.replace_with(NavigableString(a.get_text()))
                changed += 1
        elif tag == "insert":
            for k in range(j1, j2):
                manual.append(("insert", S[k][:2]))
    if changed:
        rp.write_text(str(soup_r), encoding="utf-8")
    return changed, manual


def categorize(R, S, ops):
    """Считает по категориям (href-only): retarget(replace), only_ready, only_struct."""
    c = Counter()
    for tag, i1, i2, j1, j2 in ops:
        if tag == "replace":
            c["retarget"] += min(i2 - i1, j2 - j1)
            c["only_ready"] += max(0, (i2 - i1) - (j2 - j1))
            c["only_struct"] += max(0, (j2 - j1) - (i2 - i1))
        elif tag == "delete":
            c["only_ready"] += i2 - i1
        elif tag == "insert":
            c["only_struct"] += j2 - j1
    return c


def main():
    mode = "RECONCILE" if RECONCILE else "MEASURE (read-only)"
    key = "HREF-only" if HREF_ONLY else "HREF+TEXT"
    print("=" * 100)
    print(f"LINK-LEVEL ДИФФ _ready vs _structured — режим: {mode}; ключ: {key}")
    print("=" * 100)
    total = 0
    manual_all = []
    grand = Counter()
    print(f"  {'код':18}{'ready':>7}{'struct':>7}{'retarget':>10}"
          f"{'only_ready':>12}{'only_struct':>13}")
    detail = []
    for code in CODES:
        soup_r, R, S, keyR, keyS, ops, rp = diff_code(code)
        if RECONCILE and ops:
            changed, manual = reconcile_code(code, soup_r, R, S, ops, rp)
            print(f"  {code:18}{len(R):>7}{len(S):>7}  применено правок={changed}; "
                  f"ручных={len(manual)}")
            manual_all += [(code, m) for m in manual]
        else:
            c = categorize(R, S, ops)
            grand.update(c)
            print(f"  {code:18}{len(R):>7}{len(S):>7}{c['retarget']:>10}"
                  f"{c['only_ready']:>12}{c['only_struct']:>13}")
            detail.append((code, R, S, ops))
            total += sum(c.values())
    print("-" * 100)
    if RECONCILE:
        if manual_all:
            print("ТРЕБУЮТ РУЧНОГО РАЗБОРА (ссылка есть в structured, нет в ready):")
            for code, m in manual_all:
                print(f"   [{code}] {m}")
        else:
            print("Ручного разбора не требуется.")
        print("Готово. Перезапусти без --reconcile для проверки ДИФФ==0.")
    else:
        print(f"  {'ИТОГО':18}{'':>7}{'':>7}{grand['retarget']:>10}"
              f"{grand['only_ready']:>12}{grand['only_struct']:>13}")
        print(f"\nВСЕГО расхождений (href-уровень): {total}")
        if "--list" in sys.argv:
            print("\nДЕТАЛИ:")
            for code, R, S, ops in detail:
                show(code, R, S, ops)


if __name__ == "__main__":
    main()
