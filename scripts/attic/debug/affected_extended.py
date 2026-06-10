"""Какие коды содержат href на own_doc#<extended-anchor>, который текущий
узкий Z_ANCHOR = z\\d+(?:_\\d+)* пропускает (но расширенный покроет)?
Read-only."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FINAL = ROOT / "data" / "final"
CODES = ROOT / "config" / "codes.json"

KNOWN_HOSTS = r'adilet\.zan\.kz|85\.202\.192\.66:9096'
NARROW = r'z\d+(?:_\d+)*'
EXTENDED = r'z\d+(?:-\d+)?h?(?:_p?\d+(?:-\d+)?)*'

cfg = json.loads(CODES.read_text(encoding="utf-8"))
codes = {k: v for k, v in cfg.items() if not k.startswith("_") and k != "upk"}
remap = {k: v for k, v in cfg.get("_deprecated_remaps", {}).items()
         if not k.startswith("_")}


def own_ids(code):
    main = codes[code]["doc_id"]
    s = {main}
    for old, new in remap.items():
        if new == main:
            s.add(old)
    return s


narrow_re_tmpl = (r'href\s*=\s*["\']https?://(?:' + KNOWN_HOSTS +
                  r')/(?:rus|kaz)/docs/{did}(?:\?[^#"\' ]*)?#(' + NARROW + r')["\']')
ext_re_tmpl = (r'href\s*=\s*["\']https?://(?:' + KNOWN_HOSTS +
               r')/(?:rus|kaz)/docs/{did}(?:\?[^#"\' ]*)?#(' + EXTENDED + r')["\']')

print(f"{'code':18}{'narrow_only':>12}{'ext_only':>10}{'delta':>8}")
print("-" * 50)
for code in codes:
    delta_total = 0
    for suf in ("ready", "structured"):
        p = FINAL / f"{code}_{suf}.html"
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        for did in own_ids(code):
            esc = re.escape(did)
            n = re.compile(narrow_re_tmpl.format(did=esc), re.I)
            e = re.compile(ext_re_tmpl.format(did=esc), re.I)
            nm = sum(1 for _ in n.finditer(t))
            em = sum(1 for _ in e.finditer(t))
            delta = em - nm
            if delta:
                print(f"  {code}_{suf} did={did}: narrow={nm} ext={em} delta={delta}")
            delta_total += delta
    if delta_total:
        print(f"  -> TOTAL delta for {code}: {delta_total}")
