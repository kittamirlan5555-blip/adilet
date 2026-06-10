"""READ-ONLY probe: для подозрительных WRONG из 33 — что РЕАЛЬНО резолвит якорь.
Печатает: код, zID, заголовок статьи-контейнера, ближайший заголовок ПОСЛЕ якоря,
±70 симв вокруг якоря, и существует ли заявленная статья. Ничего не правит.
"""
import sys
import importlib.util
from pathlib import Path
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
REPORT = ROOT / "data" / "reports" / "34_probe_wrong.txt"

_so = sys.stdout
_spec = importlib.util.spec_from_file_location(
    "audit", ROOT / "scripts" / "audit_links_coverage.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
sys.stdout = _so

# (code, zID, заявлено)
PROBES = [
    ("zemelnyy", "z863", "55 (пунктом 2 статьи 55)"),
    ("zemelnyy", "z52", "44-2 (перечень статей)"),
    ("zemelnyy", "z553", "14 (статьи 14 Закона — внешн.?)"),
    ("zemelnyy", "z1660", "81? (части первой настоящего пункта)"),
    ("koap", "z556", "173 (bare artnum)"),
    ("upk", "z3070", "49/48 (главами 48,49)"),
    ("nalog", "z7516", "раздел 7 (структурн.)"),
]

OUT = []


def emit(s=""):
    OUT.append(s)


def heading_of(node):
    """ближайший заголовок-статья, в чьём контейнере физически лежит node."""
    hd = node.find_parent("div", attrs={"data-type": "статья"})
    if hd is None:
        return None, None
    num = hd.get("data-number")
    ttl = ""
    for el in hd.find_all(["h2", "h3", "h4", "p", "b"], recursive=True):
        mt = A.RE_ARTTITLE.match(el.get_text(" ", strip=True))
        if mt:
            ttl = el.get_text(" ", strip=True)[:60]
            break
    return num, ttl


def around(soup, zid, n=70):
    el = soup.find(id=zid) or soup.find(attrs={"name": zid})
    if el is None:
        # ищем <a name> или элемент с этим id среди всех
        for t in soup.find_all(True):
            if t.get("id") == zid or t.get("name") == zid:
                el = t
                break
    if el is None:
        return None, "", ""
    pv = A.preceding_text(el, n)[-n:]
    buf = ""
    for sib in el.next_siblings:
        buf += sib.get_text(" ") if isinstance(sib, Tag) else str(sib)
        if len(buf) >= n:
            break
    import re
    nx = re.sub(r"\s+", " ", buf)[:n]
    return el, pv, nx


def main():
    cache = {}
    for code, zid, claimed in PROBES:
        if code not in cache:
            fp = FINAL / f"{code}_structured.html"
            cache[code] = BeautifulSoup(fp.read_text(encoding="utf-8"), "html.parser")
        soup = cache[code]
        id2art, all_ids, art_numbers, id2next = A.build_id_to_art(soup)
        el, pv, nx = around(soup, zid)
        R = id2art.get(zid)
        Rn = id2next.get(zid)
        host_num, host_ttl = (None, None)
        if el is not None:
            host_num, host_ttl = heading_of(el)
        emit("=" * 92)
        emit(f"[{code}] #{zid}  заявлено: {claimed}")
        emit(f"  резолв R(id2art)={R}  Rn(id2next)={Rn}")
        emit(f"  физич. контейнер якоря: ст.{host_num}  «{host_ttl}»")
        # существуют ли потенциально-заявленные статьи?
        for cand in ("55", "44-2", "14", "81", "173", "49", "48"):
            if cand in art_numbers and any(cand in claimed for _ in [0]):
                pass
        emit(f"  …{pv}[#{zid}]{nx}…")
        # для bare artnum: существует ли статья claim?
    # отдельный блок: существование статей
    for code in ("zemelnyy", "koap", "upk"):
        soup = cache.get(code)
        if soup is None:
            fp = FINAL / f"{code}_structured.html"
            soup = BeautifulSoup(fp.read_text(encoding="utf-8"), "html.parser")
            cache[code] = soup
        _, _, art_numbers, _ = A.build_id_to_art(soup)
        emit("-" * 92)
        emit(f"[{code}] существование статей в art_numbers:")
        for cand in ("44-2", "44-1", "55", "173", "172", "174", "14", "14-1", "49", "48"):
            emit(f"    ст.{cand}: {'ЕСТЬ' if cand in art_numbers else 'НЕТ'}")
    REPORT.write_text("\n".join(OUT) + "\n", encoding="utf-8")
    try:
        sys.stderr.write(f"report -> {REPORT}\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
