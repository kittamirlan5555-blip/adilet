# -*- coding: utf-8 -*-
"""Build a get_text<->raw offset map for an HTML string.
TEXT[i] is the i-th visible (entity-decoded) character; OFF[i] is the raw index
in `html` where TEXT[i] originates. Tags and comments are skipped. Lets us locate
a textual phrase and translate back to an exact raw insertion point."""
import re
from html import unescape

_TOKEN = re.compile(r"<!--.*?-->|<[^>]*>|&#?\w+;|[^<&]+", re.S)

def build(html):
    chars = []
    off = []
    for m in _TOKEN.finditer(html):
        s = m.group(0)
        start = m.start()
        if s.startswith("<"):
            continue                      # tag or comment -> skip
        if s.startswith("&"):
            dec = unescape(s)             # entity -> decoded char(s)
            for c in dec:
                chars.append(c); off.append(start)
            continue
        for k, c in enumerate(s):         # plain run, 1:1 mapping
            chars.append(c); off.append(start + k)
    return "".join(chars), off

if __name__ == "__main__":
    from pathlib import Path
    h = Path("data/final/upk_structured.html").read_text(encoding="utf-8")
    T, O = build(h)
    needle = "2. По делам об уголовных правонарушениях, предусмотренных статьями 99"
    i = T.find(needle)
    print("TEXT len", len(T), "| needle at TEXT", i, "-> raw", O[i])
    print("raw slice:", repr(h[O[i]:O[i]+90]))
    # round-trip a number deeper in the list (e.g. '100')
    j = T.find(", 100", i) + 2
    print("'100' TEXT", j, "raw", O[j], "raw ctx:", repr(h[O[j]-40:O[j]+20]))
