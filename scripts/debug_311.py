import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pathlib import Path
from bs4 import BeautifulSoup, Tag

text = Path('data/final/koap_structured.html').read_text(encoding='utf-8')
soup = BeautifulSoup(text, 'html.parser')

target = soup.find('a', id='z1127')
art = target.find_parent('div', class_='article')
print(f'wrapper data-number={art.get("data-number")}')

for i, c in enumerate(list(art.children)):
    if isinstance(c, Tag) and c.name in ('p', 'h3'):
        b = c.find(['b','strong'])
        t = c.get_text(' ', strip=True)[:80]
        if b:
            bt = b.get_text(' ', strip=True)[:90]
            print(f'  [{i}] <{c.name}><b>: {bt}')
        else:
            print(f'  [{i}] <{c.name}>: {t}')
