"""READ-ONLY: найти реальные якоря ст.44-2 и ст.55 в zemelnyy (_structured и _ready).
Печатает: заголовок статьи, все <a name>/id ВНУТРИ её div и НЕПОСРЕДСТВЕННО перед ним,
и как резолвер аудита (build_id_to_art) видит каждый кандидат (R=id2art, Rn=id2next).
Ничего не правит.
"""
import re
import sys
import importlib.util
from pathlib import Path
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
REPORT = ROOT / "data" / "reports" / "35_find_anchors.txt"

_so = sys.stdout
_spec = importlib.util.spec_from_file_location(
    "audit", ROOT / "scripts" / "audit_links_coverage.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
sys.stdout = _so

OUT = []


def emit(s=""):
    OUT.append(s)


def anchors_in(node):
    ids = []
    for t in node.find_all(True):
        v = t.get("id") or t.get("name")
        if v and re.match(r"z\d", v):
            ids.append((v, t.name, t.get_text(" ", strip=True)[:30]))
    return ids


def find_art_div(soup, num):
    for d in soup.find_all("div", attrs={"data-type": "статья"}):
        if d.get("data-number") == num:
            return d
    return None


def heading_text(d):
    for el in d.find_all(["h2", "h3", "h4", "p", "b"], recursive=True):
        mt = A.RE_ARTTITLE.match(el.get_text(" ", strip=True))
        if mt:
            return el.get_text(" ", strip=True)[:70]
    return f"(data-number={d.get('data-number')})"


def probe(tag, fname):
    fp = FINAL / fname
    soup = BeautifulSoup(fp.read_text(encoding="utf-8"), "html.parser")
    id2art, all_ids, art_numbers, id2next = A.build_id_to_art(soup)
    emit("#" * 96)
    emit(f"### {tag}: {fname}")
    emit("#" * 96)
    for num in ("44-2", "55", "45", "50"):
        d = find_art_div(soup, num)
        emit("=" * 90)
        if d is None:
            emit(f"ст.{num}: div НЕ найден")
            continue
        emit(f"ст.{num}: {heading_text(d)}")
        # якоря ВНУТРИ div статьи
        ins = anchors_in(d)
        emit(f"  якоря ВНУТРИ div: {ins[:8]}")
        # якорь(и) НЕПОСРЕДСТВЕННО перед div (могут принадлежать заголовку из-за bookmark-before-heading)
        before = []
        prev = d.previous_element
        steps = 0
        while prev is not None and steps < 40:
            if isinstance(prev, Tag):
                v = prev.get("id") or prev.get("name")
                if v and re.match(r"z\d", v):
                    before.append((v, prev.name))
                if prev.name == "div" and prev.get("data-type") == "статья":
                    break
            prev = prev.previous_element
            steps += 1
        emit(f"  якоря ПЕРЕД div (до пред. статьи): {before[:8]}")
        # как резолвер видит первый внутренний якорь
        for zid, *_ in ins[:3]:
            emit(f"    резолв #{zid}: R(id2art)={id2art.get(zid)} Rn(id2next)={id2next.get(zid)}")
    # существующие href, ведущие на 44-2 / 55 где-либо в документе
    emit("-" * 90)
    emit("  существующие <a href> с резолвом R==44-2 или R==55 (правильные образцы):")
    seen = set()
    for a in soup.find_all("a", href=True):
        fm = re.search(r"#(z\d+[\w-]*)", a["href"])
        if not fm:
            continue
        zid = fm.group(1)
        if id2art.get(zid) in ("44-2", "55") and zid not in seen:
            seen.add(zid)
            emit(f"    #{zid} → R={id2art.get(zid)} Rn={id2next.get(zid)} | пример текста: "
                 f"«{a.get_text(' ', strip=True)[:30]}»")
    emit(f"  art_numbers содержит 44-2: {'44-2' in art_numbers}; 55: {'55' in art_numbers}")


def main():
    probe("STRUCTURED", "zemelnyy_structured.html")
    probe("READY", "zemelnyy_ready.html")
    REPORT.write_text("\n".join(OUT) + "\n", encoding="utf-8")
    try:
        sys.stderr.write(f"report -> {REPORT}\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
