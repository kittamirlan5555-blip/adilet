# -*- coding: utf-8 -*-
"""PHASE-2 authoritative per-flag state (READ-ONLY).
Governing classified DOCX-FIRST (the flag's own text usually contains the
governing phrase), HTML-fallback via offset map when docx is truncated.
For each UK-governed flag: locate its enumeration in raw HTML (offset map),
and for every HIGHLIGHTED number classify true link state:
  PLAIN  / UPK_INT(#z internal -> cross-code mislink) / UK_OK(K1400000226) / OTHER
+ map resolution. Also counts non-highlighted PLAIN УК numbers in same regions."""
import zipfile, re, json, importlib.util
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(".").resolve()
spec = importlib.util.spec_from_file_location("offmap", ROOT/"scripts/_offmap.py")
offmap = importlib.util.module_from_spec(spec); spec.loader.exec_module(offmap)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
H = (ROOT/"data/final/upk_structured.html").read_text(encoding="utf-8")
TEXT, OFF = offmap.build(H)
UKMAP = json.loads((ROOT/"data/maps/article_map_ugolovniy.json").read_text(encoding="utf-8"))

def rtext(r): return "".join(t.text or "" for t in r.iter(W+"t"))
def is_hl(r):
    rpr=r.find(W+"rPr")
    if rpr is None: return False
    hl=rpr.find(W+"highlight")
    if hl is not None and hl.get(W+"val") not in (None,"none"): return True
    shd=rpr.find(W+"shd")
    if shd is not None and shd.get(W+"fill") not in (None,"auto","FFFFFF","ffffff"): return True
    return False

root=ET.fromstring(zipfile.ZipFile(ROOT/"anara_review/ChatExport_2026-05-20/files/УПК.docx").read("word/document.xml"))
flags=[]
for p in root.iter(W+"p"):
    full="".join(rtext(r) for r in p.iter(W+"r"))
    hlnums=[]
    for r in p.iter(W+"r"):
        if is_hl(r) and rtext(r).strip():
            hlnums+=re.findall(r"\d+(?:-\d+)?", rtext(r))
    if not hlnums: continue
    flags.append((re.sub(r"[\s\xa0]+"," ",full).strip(), hlnums))

GOVKW=[("настоящего Кодекса","UPK"),("настоящим Кодексом","UPK"),
       ("Уголовно-исполнительного","UIK"),("Уголовного кодекса","UK"),
       ("Уголовного процессуального","UPK"),("Конституц","CONST")]

def gov_from_docx(ft, hlnums):
    """Nearest governing keyword AFTER the last highlighted number in docx text."""
    last=0
    for n in hlnums:
        k=ft.rfind(n)
        if k>last: last=k
    best=None
    for kw,kind in GOVKW:
        i=ft.find(kw,last)
        if i>=0 and (best is None or i<best[0]): best=(i,kind)
    return best[1] if best else None

def flex(s):
    return re.compile(r"\s+".join(re.escape(w) for w in s.split()))

def locate_text(ft):
    """Find flag content start in TEXT via longest literal slice (ws-flexible)."""
    snip=re.sub(r"^.*?стать[яёи]\s+\d+(?:-\d+)?(?:-\d+)?\s*[-–]\s*","",ft)
    snip=snip.strip()
    for L in (90,70,55,40,30,22):
        s=snip[:L].strip()
        if not s: continue
        m=flex(s).search(TEXT)
        if m: return m.start()
    return -1

def gov_from_html(start):
    best=None
    for kw,kind in GOVKW:
        i=TEXT.find(kw,start)
        if i>=0 and (best is None or i<best[0]): best=(i,kind,i)
    return (best[1],best[2]) if best else (None,None)

def anchor_href_at(raw_pos):
    """If raw_pos is inside <a ...>...</a>, return its href; else None."""
    oa=H.rfind("<a ",0,raw_pos); ca=H.rfind("</a>",0,raw_pos)
    if oa>ca and oa>=0:
        m=re.search(r'href="([^"]*)"', H[oa:raw_pos])
        if m: return m.group(1)
    return None

def state_of(raw_pos):
    href=anchor_href_at(raw_pos)
    if href is None: return "PLAIN",None
    if href.startswith("https://adilet.zan.kz/rus/docs/K1400000226"): return "UK_OK",href
    if href.startswith("#z"): return "UPK_INT",href
    return "OTHER",href

# classify all flags
results=[]
for idx,(ft,hlnums) in enumerate(flags):
    gov=gov_from_docx(ft,hlnums)
    src="docx"
    start=locate_text(ft)
    govpos=None
    if gov is None:                      # truncated -> html fallback
        if start>=0:
            gov,govpos=gov_from_html(start); src="html"
        else:
            gov="NOLOC"; src="noloc"
    results.append((idx,ft,hlnums,gov,src,start,govpos))

uk=[r for r in results if r[3]=="UK"]
print("="*100)
print(f"flags total={len(flags)}  UK-governed (docx-first)={len(uk)}")
nonuk=[(r[0],r[3]) for r in results if r[3]!="UK"]
print(f"non-UK flags (excluded): {len(nonuk)} -> {nonuk}")
print("="*100)

grand={"PLAIN_link":0,"PLAIN_unres":0,"UK_OK":0,"UPK_INT":0,"OTHER":0}
nonhl_plain=0
per=[]
for (idx,ft,hlnums,gov,src,start,govpos) in uk:
    # region end = governing pos in TEXT (forward from start)
    if start<0:
        per.append((idx,ft,hlnums,"NOLOC",[])); continue
    # greedy IN-ORDER match of highlighted multiset over a generous window
    window=TEXT[start:start+12000]
    toks=[(m.group(0),start+m.start()) for m in re.finditer(r"\d+(?:-\d+)?",window)]
    rows=[]; used=[False]*len(toks); cur=0
    for n in hlnums:
        for ti in range(cur,len(toks)):
            if used[ti] or toks[ti][0]!=n: continue
            used[ti]=True; cur=ti+1
            st,href=state_of(OFF[toks[ti][1]])
            res=UKMAP.get(n)
            rows.append((n,st,res,href))
            if st=="PLAIN":
                if res: grand["PLAIN_link"]+=1
                else: grand["PLAIN_unres"]+=1
            else: grand[st]=grand.get(st,0)+1
            break
        else:
            rows.append((n,"NOTFOUND",UKMAP.get(n),None))
    # non-highlighted plain numbers within the matched span (УК-resolvable)
    span_end=toks[cur-1][1] if cur>0 else start
    for ti,(tn,tp) in enumerate(toks):
        if used[ti] or tp>span_end: continue
        st,_=state_of(OFF[tp])
        if st=="PLAIN" and UKMAP.get(tn): nonhl_plain+=1
    per.append((idx,ft,hlnums,"UK",rows))

print("PER-FLAG (UK):")
for (idx,ft,hlnums,gov,rows) in per:
    head=ft[:48]
    if gov=="NOLOC":
        print(f"#{idx:02d} NOLOC hl={hlnums} :: {head!r}"); continue
    cnt={}
    for n,st,res,href in rows: cnt[st]=cnt.get(st,0)+1
    print(f"#{idx:02d} hl={len(hlnums):>3} {cnt}  :: {head!r}")
    # list the actionable (PLAIN) ones
    pl=[(n,res) for n,st,res,href in rows if st=='PLAIN']
    if pl: print(f"      PLAIN->link: {pl}")
    mis=[(n,href) for n,st,res,href in rows if st=='UPK_INT']
    if mis: print(f"      UPK_INT mislinks: {mis}")
print("="*100)
print("GRAND (highlighted numbers in UK regions):", grand)
print("Non-highlighted PLAIN УК-resolvable numbers in same regions:", nonhl_plain)
