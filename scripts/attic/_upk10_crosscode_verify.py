# -*- coding: utf-8 -*-
"""FINAL cross-code verification — INDEPENDENT 2nd method (mirrors script 67,
but for the УПК->УК cross-code links). Builds its OWN УК id->article map straight
from ugolovniy_structured.html (heading-title id  +  data-number of nearest
data-type="статья" ancestor) — does NOT reuse article_map_ugolovniy_rebuilt.json,
so this is a genuinely orthogonal check (no circularity).

For EVERY <a href="...K1400000226#z{X}"> in upk_structured AND upk_ready:
  (a) does id="z{X}" actually exist in УК HTML?
  (b) does the claimed number N (link text / enumeration) equal the article that
      z{X} belongs to per the independent УК map?
Output per file: checked / MATCH / #z-not-found / N!=article. Target MATCH=999, rest=0.
READ-ONLY (writes nothing to the corpus)."""
import re
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(".").resolve()
UKHTML = (ROOT/"data/final/ugolovniy_structured.html").read_text(encoding="utf-8")
UKDOC = "K1400000226"

# homoglyph-tolerant «Статья N.» heading
RE_TITLE = re.compile(r"^\s*[СCϹЅ]тать[яиеью]*\s+(\d+(?:-\d+)?)\s*\.")
RE_CLAIM = re.compile(r"(?i)[сcϲ]тат(?:ь[а-яё]{0,3}|ей)\s+(\d+(?:-\d+)?)")
RE_BARE  = re.compile(r"^\s*(\d+(?:-\d+)?)\s*$")
RE_HREF_UK = re.compile(re.escape(UKDOC)+r"#(z\d+)")

def build_uk_map(soup):
    """INDEPENDENT id->article number. (1) heading id by title text;
    (2) any other id -> data-number of nearest data-type='статья' ancestor."""
    m = {}
    for hh in soup.find_all(["h1","h2","h3","h4","h5","h6"]):
        hid = hh.get("id")
        if not hid: continue
        mt = RE_TITLE.match(hh.get_text(" ", strip=True))
        if mt: m[hid] = mt.group(1)
    for el in soup.find_all(attrs={"id": True}):
        eid = el.get("id")
        if eid in m: continue
        anc = el.find_parent("div", attrs={"data-type": "статья"})
        if anc is not None and anc.get("data-number"):
            m[eid] = anc["data-number"]
    return m

NOANCHOR = {"206","301","303","380-3"}  # УК arts with no own anchor / nonexistent

def claimed_of(text):
    """Article number CLAIMED by the anchor text. Only a bare number or an explicit
    «статья N» counts. «пунктом 1», «главой 17», «Уголовного кодекса», «законом» etc.
    carry NO article number in the anchor itself -> None (article is contextual)."""
    t = re.sub(r"\s+", " ", text).strip()
    bm = RE_BARE.match(t)
    if bm: return bm.group(1)
    cm = RE_CLAIM.search(t)
    if cm: return cm.group(1)
    return None

def verify(path, ukmap):
    soup = BeautifulSoup(Path(path).read_text(encoding="utf-8"), "html.parser")
    res = {"checked":0, "match":0, "range_base":0,
           "notfound":[], "mismatch":[], "noclaim":[], "noanchor":[]}
    for a in soup.find_all("a", href=True):
        hm = RE_HREF_UK.search(a["href"])
        if not hm: continue
        zid = hm.group(1)
        res["checked"] += 1
        text = re.sub(r"\s+"," ", a.get_text(" ", strip=True))
        claimed = claimed_of(text)
        if claimed is not None and claimed in NOANCHOR:
            res["noanchor"].append((zid, claimed, text[:50]))   # must be plain, not linked
        if claimed is None:
            res["noclaim"].append((zid, text[:50])); continue
        R = ukmap.get(zid)
        if R is None:
            res["notfound"].append((zid, claimed, text[:40])); continue
        if R == claimed:
            res["match"] += 1
        elif "-" in claimed and R == claimed.split("-")[0]:
            res["match"] += 1; res["range_base"] += 1
        else:
            res["mismatch"].append((zid, claimed, R, text[:50]))
    return res

def main():
    soup_uk = BeautifulSoup(UKHTML, "html.parser")
    ukmap = build_uk_map(soup_uk)
    print(f"independent УК id->article map: {len(ukmap)} ids "
          f"(headings + data-number ancestors), distinct articles="
          f"{len(set(ukmap.values()))}")
    print("="*96)
    for path in ["data/final/upk_structured.html","data/final/upk_ready.html"]:
        r = verify(path, ukmap)
        print(f"\n=== {Path(path).name} ===")
        print(f"  checked={r['checked']}  MATCH={r['match']}  "
              f"#z-not-found={len(r['notfound'])}  N!=article={len(r['mismatch'])}  "
              f"no-claim={len(r['noclaim'])}   (range->base incl in MATCH: {r['range_base']})")
        if r["notfound"]:
            print("  #z-NOT-FOUND:")
            for zid,cl,tx in r["notfound"][:40]: print(f"     {zid} claim={cl} «{tx}»")
        if r["mismatch"]:
            print("  N!=ARTICLE:")
            for zid,cl,R,tx in r["mismatch"][:60]:
                print(f"     {zid}: claim ст.{cl} -> map ст.{R}   «{tx}»")
        if r["noanchor"]:
            print(f"  NO-ANCHOR-SET links (claimed in {sorted(NOANCHOR)} — MUST be plain):")
            for zid,cl,tx in r["noanchor"]: print(f"     ст.{cl} -> {zid}  «{tx}»")
        print(f"  no-claim(act/chapter/sub-element refs)={len(r['noclaim'])}")
    print("="*96)

if __name__=="__main__":
    main()
