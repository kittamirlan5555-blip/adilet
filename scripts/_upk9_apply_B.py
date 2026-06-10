# -*- coding: utf-8 -*-
"""PHASE-2 BLOCK B apply: wrap Anara's highlighted PLAIN УК numbers in
<a href="https://adilet.zan.kz/rus/docs/K1400000226#z{N}">N</a> (bare number).
Scope = exactly the highlighted numbers in UK-governed flag paragraphs (docx).
Skip already-linked (DONE) and unresolvable (301/303/380-3). Composites (108-1)
wrapped whole. get_text MUST stay byte-identical (only <a></a> inserted).
Runs per-file (symmetric). dry-run prints plan + sha; --apply writes."""
import zipfile, re, json, sys, hashlib, importlib.util
from pathlib import Path
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup

ROOT=Path(".").resolve()
spec=importlib.util.spec_from_file_location("offmap",ROOT/"scripts/_offmap.py")
offmap=importlib.util.module_from_spec(spec); spec.loader.exec_module(offmap)
UKMAP=json.loads((ROOT/"data/maps/article_map_ugolovniy_rebuilt.json").read_text(encoding="utf-8"))
UKDOC="https://adilet.zan.kz/rus/docs/K1400000226"
W="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

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
FLAGS=[]
for p in root.iter(W+"p"):
    full="".join(rtext(r) for r in p.iter(W+"r"))
    hlnums=[]
    for r in p.iter(W+"r"):
        if is_hl(r) and rtext(r).strip(): hlnums+=re.findall(r"\d+(?:-\d+)?", rtext(r))
    if not hlnums: continue
    FLAGS.append((re.sub(r"[\s\xa0]+"," ",full).strip(), hlnums))

GOV=[("настоящего Кодекс","UPK"),("настоящим Кодексом","UPK"),
     ("Уголовно-исполнительного","UIK"),("Уголовного кодекса","UK"),
     ("Уголовного процессуального","UPK"),("Конституц","CONST")]
def gov_docx(ft,hl):
    last=0
    # use last NON-trivial highlighted number (len>=2) to avoid the '3' corruption noise
    cand=[n for n in hl if len(n)>=2] or hl
    for n in cand:
        k=ft.rfind(n)
        if k>last: last=k
    best=None
    for kw,kind in GOV:
        i=ft.find(kw,last)
        if i>=0 and (best is None or i<best[0]): best=(i,kind)
    return best[1] if best else None

def flex(s): return re.compile(r"\s+".join(re.escape(w) for w in s.split()))

def anchor_at(H,raw_pos):
    oa=H.rfind("<a ",0,raw_pos); ca=H.rfind("</a>",0,raw_pos)
    if oa>ca and oa>=0:
        m=re.search(r'href="([^"]*)"',H[oa:raw_pos])
        return m.group(1) if m else "?"
    return None

def gt_sha(H): return hashlib.sha256(BeautifulSoup(H,"html.parser").get_text().encode()).hexdigest()[:16]

def process(path, apply, verbose=False):
    H=Path(path).read_text(encoding="utf-8")
    sha0=gt_sha(H)
    TEXT,OFF=offmap.build(H)
    wraps=[]  # (raw_start, raw_end, num, z)
    per=[]
    stat={"wrap":0,"done":0,"unres":0,"upkint":0,"other":0,"notfound":0}
    for idx,(ft,hl) in enumerate(FLAGS):
        if gov_docx(ft,hl)!="UK": continue
        snip=re.sub(r"^.*?стать[яёи]\s+\d+(?:-\d+)?(?:-\d+)?\s*[-–]\s*","",ft).strip()
        start=-1
        for L in (90,70,55,40,30,22):
            s=snip[:L].strip()
            if not s: continue
            m=flex(s).search(TEXT)
            if m: start=m.start(); break
        if start<0:
            per.append((idx,"NOLOC",hl,{})); continue
        window=TEXT[start:start+12000]
        toks=[(mm.group(0),start+mm.start(),start+mm.end()) for mm in re.finditer(r"\d+(?:-\d+)?",window)]
        cur=0; rows=[]
        for n in hl:
            for ti in range(cur,len(toks)):
                if toks[ti][0]!=n: continue
                tv,ts,te=toks[ti]; cur=ti+1
                rs=OFF[ts]; re_=OFF[te-1]+1
                href=anchor_at(H,rs)
                z=UKMAP.get(n)
                if href is None:
                    if z:
                        wraps.append((rs,re_,n,z)); rows.append((n,"wrap")); stat["wrap"]+=1
                    else:
                        rows.append((n,"unres")); stat["unres"]+=1
                elif href.startswith(UKDOC): rows.append((n,"done")); stat["done"]+=1
                elif href.startswith("#z"): rows.append((n,"upkint")); stat["upkint"]+=1
                else: rows.append((n,"other")); stat["other"]+=1
                break
            else:
                rows.append((n,"notfound")); stat["notfound"]+=1
        per.append((idx,"UK",hl,rows))
    # apply wraps right-to-left
    wraps.sort(key=lambda x:x[0], reverse=True)
    H2=H
    for rs,re_,n,z in wraps:
        H2=H2[:rs]+f'<a href="{UKDOC}#{z}">'+H2[rs:re_]+"</a>"+H2[re_:]
    sha1=gt_sha(H2)
    print(f"\n=== {Path(path).name} ===  wraps={stat['wrap']} done={stat['done']} unres={stat['unres']} "
          f"upkint={stat['upkint']} other={stat['other']} notfound={stat['notfound']}")
    print(f"  get_text sha before={sha0} after={sha1}  {'OK' if sha0==sha1 else 'CHANGED!!'}")
    if verbose:
        for idx,gov,hl,rows in per:
            if gov!="UK": print(f"  #{idx} {gov}"); continue
            from collections import Counter
            c=Counter(s for _,s in rows)
            if c.get("notfound") or c.get("upkint") or c.get("other"):
                print(f"  #{idx} {dict(c)} :: {rows}")
    if apply and sha0==sha1:
        Path(path).write_text(H2,encoding="utf-8"); print("  WROTE.")
    elif apply:
        print("  REFUSED (get_text changed).")
    return stat

if __name__=="__main__":
    apply="--apply" in sys.argv; verbose="--v" in sys.argv
    print("MODE:", "APPLY" if apply else "DRY-RUN")
    for p in ["data/final/upk_structured.html","data/final/upk_ready.html"]:
        process(p, apply, verbose)
