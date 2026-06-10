# -*- coding: utf-8 -*-
"""PHASE-2 census (READ-ONLY). For every УК-governed enumeration in RAW upk HTML,
classify each number token by link state:
  PLAIN        - bare number, no <a>
  UPK_INT      - linked to internal #zN (UPK self) -> SUSPECT cross-code mislink
  UK_OK        - linked to K1400000226#z... (correct УК target)
  OTHER        - linked to some other doc
Region = text from a governing 'предусмотренных стать*' / 'статьи N' up to the
forward 'Уголовного кодекса'. Reports per-region and grand totals; cross-checks
map resolution for PLAIN numbers."""
import re, json
from pathlib import Path

ROOT = Path(".").resolve()
H = (ROOT/"data/final/upk_structured.html").read_text(encoding="utf-8")
UKMAP = json.loads((ROOT/"data/maps/article_map_ugolovniy.json").read_text(encoding="utf-8"))

UKDOC = "K1400000226"
# governing-phrase anchors that START an enumeration governed by УК
GOV = re.compile(r"Уголовного кодекса")

# token: an <a ...>...</a> OR a bare number group (NN or NN-N)
ATAG = re.compile(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.S)
NUM = re.compile(r'\d+(?:-\d+)?')

def classify_href(href):
    if href.startswith(f"https://adilet.zan.kz/rus/docs/{UKDOC}"):
        return "UK_OK"
    if href.startswith("#z"):
        return "UPK_INT"
    return "OTHER"

def region_start(end_pos):
    """Walk back from 'Уголовного кодекса' to start of the enumeration."""
    win = H[max(0,end_pos-9000):end_pos]
    # last 'предусмотренных' before end (typical list opener)
    for opener in ("предусмотренных", "статьи 3", "статьёй", "статьей", "статьями", "статьи"):
        k = win.rfind(opener)
        if k >= 0:
            return max(0,end_pos-9000)+k
    return max(0, end_pos-400)

def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)

regions=[]
for gm in GOV.finditer(H):
    end=gm.start()
    start=region_start(end)
    seg=H[start:end]
    # walk seg, find <a> tokens and plain numbers between them
    items=[]  # (num, state, href)
    pos=0
    for am in ATAG.finditer(seg):
        # plain numbers in gap before this <a>
        gap=seg[pos:am.start()]
        for nm in NUM.finditer(strip_tags(gap)):
            items.append((nm.group(0),"PLAIN",None))
        inner=strip_tags(am.group(2))
        href=am.group(1)
        st=classify_href(href)
        for nm in NUM.finditer(inner):
            items.append((nm.group(0),st,href))
        pos=am.end()
    # trailing plain
    for nm in NUM.finditer(strip_tags(seg[pos:])):
        items.append((nm.group(0),"PLAIN",None))
    # only keep regions that look like enumerations (>=1 number) and are 'стать'-led
    if any(s!="PLAIN" for _,s,_ in items) or len(items)>=2:
        regions.append((start,end,items,seg))

# grand totals
from collections import Counter
G=Counter()
plain_resolvable=[]
plain_unres=[]
for (start,end,items,seg) in regions:
    for num,st,href in items:
        G[st]+=1
        if st=="PLAIN":
            if UKMAP.get(num): plain_resolvable.append(num)
            else: plain_unres.append(num)

print("="*100)
print(f"УК-governed 'Уголовного кодекса' occurrences scanned: {len(list(GOV.finditer(H)))}")
print(f"regions kept: {len(regions)}")
print(f"TOKEN STATE TOTALS: {dict(G)}")
print(f"PLAIN resolvable in УК-map: {len(plain_resolvable)}  | PLAIN NOT resolvable: {len(plain_unres)}")
print("PLAIN unresolvable (distinct):", sorted(set(plain_unres)))
print("="*100)
# per-region summary, only regions that contain UPK_INT (the suspect mislinks) or PLAIN numbers
for idx,(start,end,items,seg) in enumerate(regions):
    c=Counter(s for _,s,_ in items)
    if c.get("UPK_INT",0)==0 and c.get("PLAIN",0)==0:
        continue
    head=strip_tags(seg[:60])
    head=re.sub(r"\s+"," ",head)
    print(f"R{idx:02d} @{start} states={dict(c)}  head={head!r}")
