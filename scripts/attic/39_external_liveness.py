# -*- coding: utf-8 -*-
"""
PART D liveness — batch HEAD/GET all foreign doc_ids (+ our 13).
Honest-path confirmed by sanity test: nonexistent -> HTTP 404 (~20KB, no <title>),
real -> 200 (large, real <title>). So we classify:
  status 200 + <title> present (non-empty)  -> ALIVE (real doc)
  status 404 / other                         -> DEAD/MISSING
  status 200 but no/empty <title> or tiny    -> SUSPECT (manual)
Reads only first 96KB (title is in <head>; error page is ~20KB total).
READ-ONLY network probe. No source/structured edits.
"""
import sys, io, re, json, ssl, socket, time, urllib.request, urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parents[1]
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
socket.setdefaulttimeout(15)
RE_TITLE = re.compile(rb'<title[^>]*>(.*?)</title>', re.I|re.S)
PARTIAL = 98304

def load_ids():
    foreign = []
    fp = ROOT/'data/reports/_ext_foreign_ids.txt'
    for ln in fp.read_text(encoding='utf-8').splitlines():
        if not ln.strip(): continue
        did, cnt = ln.split('\t')
        foreign.append((did, int(cnt)))
    ours = []
    cfg = json.loads((ROOT/'config/codes.json').read_text(encoding='utf-8'))
    for code, meta in cfg.items():
        if code.startswith('_') or not isinstance(meta, dict): continue
        ours.append((meta['doc_id'], code))
    return foreign, ours

def probe(did):
    url = f'https://adilet.zan.kz/rus/docs/{did}'
    t=time.time()
    try:
        req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        r=urllib.request.urlopen(req, context=ctx)
        body=r.read(PARTIAL)
        m=RE_TITLE.search(body)
        title=m.group(1).decode('utf-8','replace').strip() if m else ''
        return did, r.status, len(body), bool(title), title
    except urllib.error.HTTPError as e:
        return did, f'HTTP{e.code}', 0, False, ''
    except Exception as e:
        return did, f'ERR:{type(e).__name__}', 0, False, ''

def classify(status, has_title):
    if status==200 and has_title: return 'ALIVE'
    if status==200: return 'SUSPECT'
    return 'DEAD'

def main():
    foreign, ours = load_ids()
    all_ids = [(d,'foreign',c) for d,c in foreign] + [(d,'ours',c) for d,c in ours]
    results={}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs={ex.submit(probe,d):(d,kind,c) for d,kind,c in all_ids}
        done=0
        for fut in as_completed(futs):
            did,kind,c=futs[fut]
            r=fut.result(); results[did]=(kind,c,r)
            done+=1
            if done%50==0: sys.stderr.write(f'  ...{done}/{len(all_ids)}\n')
    # tally
    rows=[]
    for did,(kind,c,r) in results.items():
        _,status,blen,has_title,title=r
        verdict=classify(status,has_title)
        rows.append((verdict,kind,did,status,blen,c,title))
    n_alive=sum(1 for x in rows if x[0]=='ALIVE')
    n_dead =sum(1 for x in rows if x[0]=='DEAD')
    n_susp =sum(1 for x in rows if x[0]=='SUSPECT')
    f_alive=sum(1 for x in rows if x[0]=='ALIVE' and x[1]=='foreign')
    o_alive=sum(1 for x in rows if x[0]=='ALIVE' and x[1]=='ours')
    out=[]
    out.append(f'TOTAL probed: {len(rows)}  (foreign {len(foreign)} + ours {len(ours)})')
    out.append(f'ALIVE {n_alive} (foreign {f_alive}/{len(foreign)}, ours {o_alive}/{len(ours)})  SUSPECT {n_susp}  DEAD {n_dead}')
    out.append('')
    if n_dead:
        out.append('DEAD/MISSING:')
        for v,kind,did,st,bl,c,ti in sorted(rows):
            if v=='DEAD': out.append(f'  {did}  status={st}  kind={kind}  refs={c}')
    if n_susp:
        out.append('SUSPECT (200, no <title>):')
        for v,kind,did,st,bl,c,ti in sorted(rows):
            if v=='SUSPECT': out.append(f'  {did}  len={bl}  kind={kind}  refs={c}')
    rpt=ROOT/'data/reports/39_liveness.txt'
    rpt.write_text('\n'.join(out)+'\n', encoding='utf-8')
    # machine table
    tsv=['verdict\tkind\tdoc_id\tstatus\tbody_len\trefs']
    for v,kind,did,st,bl,c,ti in sorted(rows, key=lambda x:(x[0], -(x[5] if isinstance(x[5],int) else 0))):
        tsv.append(f'{v}\t{kind}\t{did}\t{st}\t{bl}\t{c}')
    (ROOT/'data/reports/_ext_liveness.tsv').write_text('\n'.join(tsv)+'\n', encoding='utf-8')
    # ascii-safe stdout
    for ln in out:
        sys.stdout.write(ln.encode('ascii','replace').decode('ascii')+'\n')

if __name__=='__main__':
    main()
