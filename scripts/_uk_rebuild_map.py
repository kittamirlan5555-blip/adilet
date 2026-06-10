# -*- coding: utf-8 -*-
"""Rebuild authoritative УК article->anchor map from ugolovniy_structured.html.
Extract every <div class="article" data-number="N" ...> and the anchor id used
for that article (h3 id="zNNNN" or div id="w_zNNNN"/"zNNNN"). Reconcile against
existing data/maps/article_map_ugolovniy.json: report VALUE MISMATCHES (existing
map disagrees with HTML) and GAPS (article in HTML w/ anchor, missing from map)
and NO-ANCHOR articles (exist in HTML but carry no id -> unlinkable)."""
import re, json
from pathlib import Path

ROOT=Path(".").resolve()
H=(ROOT/"data/final/ugolovniy_structured.html").read_text(encoding="utf-8")
OLD=json.loads((ROOT/"data/maps/article_map_ugolovniy.json").read_text(encoding="utf-8"))

# each article block
DIV=re.compile(r'<div class="article"[^>]*data-number="([^"]+)"[^>]*?>(.*?)(?=<div class="article"|</body>|$)', re.S)
built={}
noanchor=[]
for m in re.finditer(r'<div class="article"([^>]*)>', H):
    attrs=m.group(1)
    dn=re.search(r'data-number="([^"]+)"', attrs)
    if not dn: continue
    num=dn.group(1)
    # anchor: prefer id on the div attrs (id="w_zNNN" or id="zNNN")
    idm=re.search(r'\bid="(?:w_)?(z\d+)"', attrs)
    z=None
    if idm: z=idm.group(1)
    else:
        # look at the following ~250 chars for <h3 id="zNNN"> or <a name="zNNN">
        tail=H[m.end():m.end()+260]
        hm=re.search(r'<h3[^>]*\bid="(z\d+)"', tail) or re.search(r'name="(z\d+)"', tail)
        if hm: z=hm.group(1)
    if z is None:
        noanchor.append(num); continue
    # keep FIRST occurrence (current edition precedes future-edition dupes)
    if num not in built: built[num]=z

# reconcile
mism=[]; gaps=[]
for num,z in built.items():
    if num in OLD:
        if OLD[num]!=z: mism.append((num,OLD[num],z))
    else:
        gaps.append((num,z))
only_old=[k for k in OLD if k not in built]

print(f"articles in HTML w/ anchor: {len(built)} | existing map: {len(OLD)}")
print(f"NO-ANCHOR articles in HTML (unlinkable): {len(noanchor)} -> {sorted(noanchor)[:40]}")
print(f"VALUE MISMATCH (map != HTML): {len(mism)}")
for n,o,b in mism[:60]: print(f"    ст.{n}: map={o} HTML={b}")
print(f"GAPS (in HTML, missing from map): {len(gaps)}")
for n,z in sorted(gaps, key=lambda x:(len(x[0]),x[0]))[:80]: print(f"    +ст.{n} -> {z}")
print(f"IN MAP but not built-from-HTML (verify): {len(only_old)} -> {sorted(only_old)[:40]}")

# write merged authoritative map (HTML wins; keep OLD-only entries too)
merged=dict(OLD);
for num,z in built.items(): merged[num]=z
Path(ROOT/"data/maps/article_map_ugolovniy_rebuilt.json").write_text(
    json.dumps(merged, ensure_ascii=False, indent=0), encoding="utf-8")
print("wrote data/maps/article_map_ugolovniy_rebuilt.json (merged, HTML-authoritative)")
