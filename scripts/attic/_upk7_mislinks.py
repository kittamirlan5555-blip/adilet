# -*- coding: utf-8 -*-
"""PHASE-2 BLOCK A scanner (READ-ONLY). Full CLASS of cross-code mislinks:
every <a href="#zNNN">[стать* ]NUM</a> in upk whose enumeration governing is
«Уголовного кодекса». Such an internal link inside a УК-governed list should
target K1400000226#z(NUM). Dedupes, validates the span to «Уголовного кодекса»
is enumeration-like, prints context for manual verification of EACH."""
import re, json, importlib.util
from pathlib import Path

ROOT=Path(".").resolve()
spec=importlib.util.spec_from_file_location("offmap",ROOT/"scripts/_offmap.py")
offmap=importlib.util.module_from_spec(spec); spec.loader.exec_module(offmap)
H=(ROOT/"data/final/upk_structured.html").read_text(encoding="utf-8")
TEXT,OFF=offmap.build(H)
UKMAP=json.loads((ROOT/"data/maps/article_map_ugolovniy.json").read_text(encoding="utf-8"))
UPKMAP=json.loads((ROOT/"data/maps/article_map_upk.json").read_text(encoding="utf-8"))
UPKINV={v:k for k,v in UPKMAP.items()}

GOV=[("настоящего Кодекс","UPK"),("настоящим Кодексом","UPK"),
     ("Уголовно-исполнительного","UIK"),
     ("Уголовного кодекса","UK"),
     ("Гражданского кодекса","GK"),("Гражданского процессуального","GPK"),
     ("Кодекса Республики Казахстан об административных","KOAP"),
     ("Налогового кодекса","NK"),("Конституц","CONST")]

raw2text={}
for ti,ro in enumerate(OFF):
    if ro not in raw2text: raw2text[ro]=ti

def text_pos(raw_pos):
    for r in range(raw_pos, raw_pos+6):
        if r in raw2text: return raw2text[r]
    return None

def nearest_gov(tpos):
    best=None
    for kw,kind in GOV:
        i=TEXT.find(kw,tpos)
        if i>=0 and (best is None or i<best[0]): best=(i,kind,kw)
    return best

# is the TEXT span [a,b] a clean enumeration tail (numbers/ordinals/parens/list words)?
ALLOWED=re.compile(
    r"^[\s\d\-–,;()«»\"]*"
    r"(?:(?:стать(?:ями|ёй|ей|и|я)|част(?:ью|ями|и|ей)|пункт(?:ами|ом|а|ы)?|"
    r"подпункт(?:ами|ом|а|ы)?|абзац(?:ами|ем)?|"
    r"перв(?:ой|ая|ым|ого)|втор(?:ой|ая|ым|ого)|треть(?:ей|я|им)|четверт(?:ой|ая)|"
    r"пят(?:ой|ая)|шест(?:ой|ая)|седьм(?:ой|ая)|восьм(?:ой|ая)|девят(?:ой|ая)|десят(?:ой|ая)|"
    r"одиннадцат(?:ой|ая)|двенадцат(?:ой|ая)|и|или|а|также|в|случа(?:ях|е)|"
    r"жесток(?:ого)?|бесчеловечн(?:ого)?|унижающ(?:его)?|достоинств(?:о|а)|обращени(?:я|е)|"
    r"не|связанн(?:ого)?|с|пытк(?:ами|и)|пунктами)\b[\s\d\-–,;()«»\"]*)*$")

def clean_enum(a,b):
    seg=TEXT[a:b]
    return bool(ALLOWED.match(seg)), seg

A=re.compile(r'<a\b[^>]*href="(#z\d+)"[^>]*>\s*(стать[а-яё]+\s+)?(\d+(?:-\d+)?)\s*</a>', re.I)
seen=set(); cands=[]
for m in A.finditer(H):
    if m.start() in seen: continue
    seen.add(m.start())
    href=m.group(1); num=m.group(3)
    inner_raw=m.start(3)
    tp=text_pos(inner_raw)
    if tp is None: continue
    g=nearest_gov(tp)
    if not g or g[1]!="UK": continue
    gpos,kind,kw=g
    dist=gpos-tp
    if dist>=4000: continue
    ok,seg=clean_enum(tp+len(num), gpos)
    cands.append((m.start(),href,num,dist,UKMAP.get(num),UPKINV.get(href[1:]),ok))

print(f"distinct candidates: {len(cands)}")
print("="*110)
for (pos,href,num,dist,uk,upkart,ok) in cands:
    tp=text_pos(pos) or text_pos(OFF and pos)
    # show TEXT context around the number
    nt=text_pos(re.search(r'>\s*(?:стать[а-яё]+\s+)?(\d)', H[pos:pos+80]).start(1)+pos) if True else None
    ctxs=raw2text.get(pos)
    # simpler: locate number tpos again
    inner_raw=re.search(r'href="#z\d+"[^>]*>\s*(?:стать[а-яё]+\s+)?(\d)', H[pos:pos+120])
    ip=text_pos(pos+inner_raw.start(1))
    ctx=re.sub(r"\s+"," ",TEXT[ip-55:ip+40]) if ip else "?"
    tgt=f"K1400000226#{uk}" if uk else "NO-UK-TARGET"
    print(f"num={num:>6} {href:>8}(UPKст.{upkart}) -> {tgt:>22} dist={dist:>4} enum={'Y' if ok else 'N'}")
    print(f"        ctx: …{ctx}…")
print("="*110)
print("NO УК target (must skip):", [(c[2],c[1]) for c in cands if c[4] is None])
print("NON-enumeration (suspect false-positive, verify):", [(c[2],c[1],c[3]) for c in cands if not c[6]])
