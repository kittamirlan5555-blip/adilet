# -*- coding: utf-8 -*-
"""ПОШТУЧНАЯ диагностика дивергенции _ready vs _structured (READ-ONLY).

difflib по глобальной href-последовательности (скрипт 29) мис-парит несвязанные
insert/delete как retarget. Здесь выравниваем ПО СТАТЬЯМ (обе формы знают номер
статьи: structured — data-number; ready — заголовок «Статья N.»), внутри статьи
список ссылок короткий, поэтому диф локален и точен.

Для каждой расхождения печатаем обе стороны + ВЕРДИКТ АУДИТА (claimed N из текста
vs резолв якоря по КАНОН-модели structured): OK / WRONG / BROKEN / NONART / EXT.
Это даёт основу для решения «куда выравнивать».
"""
import re
import sys
import difflib
import importlib.util
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"

_spec = importlib.util.spec_from_file_location("audit_mod", ROOT / "scripts" / "audit_links_coverage.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

CODES = ["nalog", "predprinimatel", "socialnyy", "upk", "koap", "appk", "byudzhet"]
ALLDIV = ["nalog", "trudovoy", "grazhdanskiy", "grazhdanskiy_osob", "predprinimatel",
          "socialnyy", "ekologicheskiy", "zemelnyy", "upk", "koap", "appk",
          "byudzhet", "ugolovniy"]


def norm_href(href, self_doc):
    h = href.strip()
    if h.startswith("#z"):
        return h
    if h.startswith("javascript") or h.startswith("mailto"):
        return None
    m = re.search(r"/docs/([A-Z]\d{6,}_?)(#z[\w-]+)?", h)
    if m:
        doc, frag = m.group(1), m.group(2) or ""
        if doc == self_doc and frag:
            return frag
        return f"/docs/{doc}{frag}"
    return None


def collect_struct(soup, self_doc):
    """structured: ссылка -> номер статьи через предка div[data-type=статья]."""
    out = []
    for a in soup.find_all("a", href=True):
        host = a.find_parent("div", attrs={"data-type": "статья"})
        if host is None:
            continue
        sig = norm_href(a["href"], self_doc)
        if sig is None:
            continue
        art = host.get("data-number")
        out.append((art, sig, re.sub(r"\s+", " ", a.get_text(" ", strip=True)), a))
    return out


def ready_content_root(soup):
    """контент документа в ready = div.inner_main (внутри неё статьи);
    вне неё — хром adilet (хедер-меню, баннеры, футер-виджет «Популярные документы»)."""
    root = soup.find("div", class_="inner_main")
    return root or soup.body or soup


def collect_ready(soup, self_doc):
    """ready (плоский): идём в порядке документа ВНУТРИ inner_main, трекаем
    текущую статью по заголовку «Статья N.» (RE_ARTTITLE на текстовом узле)."""
    out = []
    cur = [None]

    def walk(node):
        for ch in node.children:
            if isinstance(ch, NavigableString):
                t = str(ch).strip()
                if t:
                    m = A.RE_ARTTITLE.match(t)
                    if m:
                        cur[0] = m.group(1)
            elif isinstance(ch, Tag):
                if ch.name == "a" and ch.has_attr("href"):
                    sig = norm_href(ch["href"], self_doc)
                    if sig is not None:
                        out.append((cur[0], sig, re.sub(r"\s+", " ", ch.get_text(" ", strip=True)), ch))
                else:
                    # заголовок может быть в теге (h3/p) с единым текстом
                    if ch.name in ("h1", "h2", "h3", "h4", "p"):
                        m = A.RE_ARTTITLE.match(ch.get_text(" ", strip=True))
                        if m:
                            cur[0] = m.group(1)
                    walk(ch)

    walk(ready_content_root(soup))
    return out


def by_article(links):
    d = {}
    for art, sig, txt, a in links:
        d.setdefault(art, []).append((sig, txt, a))
    return d


def audit_internal(a, zk, id2art, id2next, all_ids):
    """вердикт для внутренней #zK ссылки по канон-модели structured."""
    if zk not in all_ids:
        return "BROKEN"
    ck, cn = A.claimed_article(a)
    if ck == "NONART":
        return "NONART"
    if ck == "SELF":
        return "SELF"
    acc = {str(id2art.get(zk)), str(id2next.get(zk))}
    cn_str = str(cn)
    if cn_str in acc:
        return "OK"
    if "-" in cn_str:
        if cn_str.split("-")[0] in acc:
            return "OK(range)"
    return f"WRONG(claim={cn},resolve={id2art.get(zk)}/{id2next.get(zk)})"


def verdict(sig, a, id2art, id2next, all_ids):
    if sig.startswith("#z"):
        return audit_internal(a, sig[1:], id2art, id2next, all_ids)
    if sig.startswith("/docs/"):
        return "EXT"
    return "?"


def diff_article(arts_R, arts_S):
    """внутри статьи: difflib по sig; возвращает список (kind, R_item, S_item)."""
    kR = [x[0] for x in arts_R]
    kS = [x[0] for x in arts_S]
    sm = difflib.SequenceMatcher(a=kR, b=kS, autojunk=False)
    rows = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            n = max(i2 - i1, j2 - j1)
            for k in range(n):
                ri = arts_R[i1 + k] if i1 + k < i2 else None
                si = arts_S[j1 + k] if j1 + k < j2 else None
                rows.append(("retarget" if ri and si else ("only_ready" if ri else "only_struct"), ri, si))
        elif tag == "delete":
            for k in range(i1, i2):
                rows.append(("only_ready", arts_R[k], None))
        elif tag == "insert":
            for k in range(j1, j2):
                rows.append(("only_struct", None, arts_S[k]))
    return rows


def main():
    only = sys.argv[1:] or CODES
    L = ["ПОШТУЧНАЯ ДИАГНОСТИКА ДИВЕРГЕНЦИИ (per-article, READ-ONLY)",
         "вердикт = аудит ссылки по КАНОН-модели structured (claim vs резолв якоря)",
         "=" * 100]
    grand = Counter()
    for code in only:
        rp = FINAL / f"{code}_ready.html"
        sp = FINAL / f"{code}_structured.html"
        if not (rp.exists() and sp.exists()):
            continue
        self_doc = A.SELF_DOC.get(code, "")
        soup_r = BeautifulSoup(rp.read_text(encoding="utf-8"), "html.parser")
        soup_s = BeautifulSoup(sp.read_text(encoding="utf-8"), "html.parser")
        id2art, all_ids, art_numbers, id2next = A.build_id_to_art(soup_s)
        R = by_article(collect_ready(soup_r, self_doc))
        S = by_article(collect_struct(soup_s, self_doc))
        arts = sorted(set(R) | set(S), key=lambda x: (x is None, x))
        block = []
        cc = Counter()
        for art in arts:
            rows = diff_article(R.get(art, []), S.get(art, []))
            for kind, ri, si in rows:
                cc[kind] += 1
                rv = sv = ""
                if ri:
                    rv = f"{ri[0]} «{ri[1][:48]}» [{verdict(ri[0], ri[2], id2art, id2next, all_ids)}]"
                if si:
                    sv = f"{si[0]} «{si[1][:48]}» [{verdict(si[0], si[2], id2art, id2next, all_ids)}]"
                block.append(f"  ст.{str(art):<8} {kind:11}")
                if rv:
                    block.append(f"      ready : {rv}")
                if sv:
                    block.append(f"      struct: {sv}")
        L.append("")
        L.append(f"########## {code}  (retarget={cc['retarget']} only_ready={cc['only_ready']} only_struct={cc['only_struct']}) ##########")
        L += block
        grand.update(cc)
    L.append("")
    L.append("=" * 100)
    L.append(f"ИТОГО: retarget={grand['retarget']} only_ready={grand['only_ready']} only_struct={grand['only_struct']}  ВСЕГО={sum(grand.values())}")
    out = "\n".join(L) + "\n"
    (ROOT / "data/reports/52_divergence_diag.txt").write_text(out, encoding="utf-8")
    sys.stdout.write(f"written {len(out)} chars; total={sum(grand.values())}\n")


if __name__ == "__main__":
    main()
