"""Quick check of HTML nesting issues in ready files."""
import re
import sys
from pathlib import Path

files = sys.argv[1:] or list(Path("data/final").glob("*_ready.html"))

for f in files:
    p = Path(f)
    html = p.read_text(encoding="utf-8")
    nested = re.findall(r"<a[^>]+>[^<]{0,200}<a[^>]+>", html)
    opens = len(re.findall(r"<a[^>]*>", html))
    closes = len(re.findall(r"</a>", html))
    print(f"{p.name}: opens={opens} closes={closes} delta={opens-closes} nested={len(nested)}")
