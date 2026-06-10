# -*- coding: utf-8 -*-
"""PHASE-2 BLOCK A apply: retarget cross-code MISLINKS (internal #z under
«Уголовного кодекса» governing) -> K1400000226#z(N) by rebuilt УК map.
href-only: get_text MUST stay byte-identical. Unresolvable УК arts (206/301/303
have no УК anchor) -> UNWRAP the wrong link to PLAIN (residual). Runs on a file;
dry-run prints plan + get_text sha; --apply writes. Operates per-file so it is
naturally symmetric across _structured/_ready (each scanned independently)."""
import re, json, sys, hashlib, importlib.util
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(".").resolve()
spec=importlib.util.spec_from_file_location("offmap",ROOT/"scripts/_offmap.py")
offmap=importlib.util.module_from_spec(spec); spec.loader.exec_module(offmap)
UKMAP=json.loads((ROOT/"data/maps/article_map_ugolovniy_rebuilt.json").read_text(encoding="utf-8"))
UKDOC="https://adilet.zan.kz/rus/docs/K1400000226"

GOV=[("настоящего Кодекс","UPK"),("настоящим Кодексом","UPK"),
     ("Уголовно-исполнительного","UIK"),("Уголовного кодекса","UK"),
     ("Гражданского кодекса","GK"),("Гражданского процессуального","GPK"),
     ("Кодекса Республики Казахстан об административных","KOAP"),
     ("Налогового кодекса","NK"),("Конституц","CONST")]
ALLOWED=re.compile(
    r"^[\s\d\-–,;()«»\"]*"
    r"(?:(?:стать(?:ями|ёй|ей|и|я)|част(?:ью|ями|и|ей)|пункт(?:ами|ом|а|ы)?|"
    r"подпункт(?:ами|ом|а|ы)?|абзац(?:ами|ем)?|перв(?:ой|ая|ым|ого)|втор(?:ой|ая|ым|ого)|"
    r"треть(?:ей|я|им)|четверт(?:ой|ая)|пят(?:ой|ая)|шест(?:ой|ая)|седьм(?:ой|ая)|"
    r"восьм(?:ой|ая)|девят(?:ой|ая)|десят(?:ой|ая)|одиннадцат(?:ой|ая)|двенадцат(?:ой|ая)|"
    r"и|или|а|также|в|случа(?:ях|е)|жесток(?:ого)?|бесчеловечн(?:ого)?|унижающ(?:его)?|"
    r"достоинств(?:о|а)|обращени(?:я|е)|не|связанн(?:ого)?|с|пытк(?:ами|и)|пунктами)"
    r"\b[\s\d\-–,;()«»\"]*)*$")
A=re.compile(r'<a\b[^>]*?href="(#z\d+)"[^>]*?>\s*(стать[а-яё]+\s+)?(\d+(?:-\d+)?)\s*</a>', re.I)

def scan(H):
    TEXT,OFF=offmap.build(H)
    raw2text={}
    for ti,ro in enumerate(OFF):
        if ro not in raw2text: raw2text[ro]=ti
    def tpos(rp):
        for r in range(rp,rp+6):
            if r in raw2text: return raw2text[r]
        return None
    def near(tp):
        best=None
        for kw,kind in GOV:
            i=TEXT.find(kw,tp)
            if i>=0 and (best is None or i<best[0]): best=(i,kind)
        return best
    retar=[]; unwrap=[]
    for m in A.finditer(H):
        href=m.group(1); num=m.group(3)
        tp=tpos(m.start(3))
        if tp is None: continue
        g=near(tp)
        if not g or g[1]!="UK": continue
        gpos,kind=g
        if gpos-tp>=4000: continue
        if not ALLOWED.match(TEXT[tp+len(num):gpos]): continue
        z=UKMAP.get(num)
        if z:   # retarget href value span (group 1)
            retar.append((m.start(1),m.end(1),href,f"{UKDOC}#{z}",num))
        else:   # unresolvable (206/301/303) -> unwrap whole anchor to inner num
            unwrap.append((m.start(),m.end(),m.group(0),num))
    return retar,unwrap

def gt_sha(H): return hashlib.sha256(BeautifulSoup(H,"html.parser").get_text().encode()).hexdigest()[:16]

def process(path, apply):
    H=Path(path).read_text(encoding="utf-8")
    sha0=gt_sha(H)
    retar,unwrap=scan(H)
    # apply right-to-left (merge by start desc)
    edits=[("RT",s,e,new) for (s,e,old,new,num) in retar]+[("UW",s,e,num) for (s,e,full,num) in unwrap]
    edits.sort(key=lambda x:x[1], reverse=True)
    H2=H
    for kind,s,e,payload in edits:
        if kind=="RT":
            # s..e is the bare href VALUE span (regex group 1 = #zNNN, no href="),
            # so substitute the new bare value only — wrapping in href="..." here
            # doubled the attribute (href="href="...""), a get_text-invariant corruption.
            H2=H2[:s]+payload+H2[e:]
        else:  # unwrap -> inner number text
            H2=H2[:s]+payload+H2[e:]
    sha1=gt_sha(H2)
    print(f"\n=== {Path(path).name} ===")
    print(f"  retargets={len(retar)}  unwraps(206-type)={len(unwrap)}")
    from collections import Counter
    cc=Counter(num for *_,num in retar)
    print("  retarget by num:", dict(sorted(cc.items(), key=lambda x:int(x[0].split('-')[0]))))
    print("  unwrap nums:", [u[3] for u in unwrap])
    print(f"  get_text sha: before={sha0} after={sha1}  {'OK(invariant)' if sha0==sha1 else 'CHANGED!!'}")
    if apply and sha0==sha1:
        Path(path).write_text(H2, encoding="utf-8")
        print("  WROTE.")
    elif apply:
        print("  REFUSED to write (get_text changed).")
    return [(n if False else num) for *_,num in retar], [u[3] for u in unwrap]

if __name__=="__main__":
    apply="--apply" in sys.argv
    print("MODE:", "APPLY" if apply else "DRY-RUN")
    for p in ["data/final/upk_structured.html","data/final/upk_ready.html"]:
        process(p, apply)
