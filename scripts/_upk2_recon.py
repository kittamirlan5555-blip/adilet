# -*- coding: utf-8 -*-
"""PHASE-2 recon (READ-ONLY). Re-parse УПК.docx highlighted runs; classify each
flag paragraph's governing via FULL upk HTML; dump the UK-governed ones with
highlighted numbers + a raw-locator, and for each number show PLAIN vs WRAPPED
state inside its enumeration region. Also show existing K1400000226 convention."""
import zipfile, re, json
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ROOT = Path(".").resolve()
DOCX = ROOT/"anara_review/ChatExport_2026-05-20/files/УПК.docx"
HTMLP = ROOT/"data/final/upk_structured.html"
UKMAP = json.loads((ROOT/"data/maps/article_map_ugolovniy.json").read_text(encoding="utf-8"))

def norm(s): return re.sub(r"[\s\xa0]+"," ",s).strip()
root = ET.fromstring(zipfile.ZipFile(DOCX).read("word/document.xml"))
def rtext(r): return "".join(t.text or "" for t in r.iter(W+"t"))
def is_hl(r):
    rpr=r.find(W+"rPr")
    if rpr is None: return False
    hl=rpr.find(W+"highlight")
    if hl is not None and hl.get(W+"val") not in (None,"none"): return True
    shd=rpr.find(W+"shd")
    if shd is not None and shd.get(W+"fill") not in (None,"auto","FFFFFF","ffffff"): return True
    return False

flags=[]
for p in root.iter(W+"p"):
    full="".join(rtext(r) for r in p.iter(W+"r"))
    hl=[rtext(r) for r in p.iter(W+"r") if is_hl(r) and rtext(r).strip()]
    if not hl: continue
    m=re.search(r"стать[яёи]\s+(\d+(?:-\d+)?)\s*[-–]", full)
    art=m.group(1) if m else "?"
    nums=[]
    for h in hl: nums+=re.findall(r"\d+(?:-\d+)?",h)
    flags.append((norm(full), art, hl, nums))

raw = HTMLP.read_text(encoding="utf-8")
sp = BeautifulSoup(raw,"html.parser")
HT = norm(sp.get_text(" "))

def find_snip(ft):
    snip=re.sub(r"^.*?стать[яёи]\s+\d+(?:-\d+)?\s*[-–]\s*","",ft)
    for L in (70,60,50,40,30,22,16):
        s=snip[:L]
        i=HT.find(s)
        if i>=0: return i,s
    return -1,snip[:22]

def gov_near(pos):
    KW=[("настоящего Кодекса","UPK"),("Уголовного кодекса","UK"),
        ("Уголовно-исполнительного кодекса","UIK"),("Конституц","CONST")]
    best=None
    for kw,kind in KW:
        i=HT.find(kw,pos)
        if i>=0 and (best is None or i<best[0]): best=(i,kind,kw)
    return best[1] if best else "OTHER"

uk=[]
for i,(ft,art,hl,nums) in enumerate(flags):
    pos,s=find_snip(ft)
    gov = gov_near(pos) if pos>=0 else "NOLOC"
    if gov=="UK" or (gov=="NOLOC" and nums==["3"]) or (gov=="NOLOC"):
        uk.append((i,art,hl,nums,pos,s,gov))

print(f"всего флаг-параграфов={len(flags)}; UK/NOLOC отобрано={len(uk)}")
print(f"сумма подсвеченных чисел в отобранных = {sum(len(u[3]) for u in uk)}")
print("="*100)
# resolve coverage in map
allnums=set()
for u in uk: allnums.update(u[3])
unres=sorted(n for n in allnums if UKMAP.get(n) is None)
print("РАЗЛИЧНЫХ чисел:", len(allnums), "| НЕ резолвится по УК-карте:", unres)
print("="*100)
for (i,art,hl,nums,pos,s,gov) in uk:
    print(f"#{i:02d} ст.{art} gov={gov} nums({len(nums)})={nums}")
    print(f"     snip={s[:60]!r} pos={pos}")
