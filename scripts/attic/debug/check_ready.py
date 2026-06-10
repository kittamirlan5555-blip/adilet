import sys, re, os
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup

files = [
    ('data/nalog_ready.html', 'NALOG', 'K2500000214'),
    ('data/grazhdanskiy_ready.html', 'GRAZHDANSKIY', 'K940001000_'),
]

for fname, label, doc_id in files:
    exists = os.path.exists(fname)
    size = os.path.getsize(fname) if exists else 0
    print(f'=== {label} ===')
    print(f'  Файл: {"EXISTS" if exists else "MISSING"} ({size:,} bytes)')
    if not exists:
        continue

    with open(fname, 'rb') as f:
        html_bytes = f.read()
    html = html_bytes.decode('utf-8')
    soup = BeautifulSoup(html_bytes, 'html.parser')

    # 1. Raw HTML in visible text
    raw_a_open = len(re.findall(r'&lt;a\s', html))
    raw_a_close = len(re.findall(r'&lt;/a&gt;', html))
    # href= without quotes in text nodes
    text_content = ' '.join(t for t in soup.find_all(string=True))
    raw_href_in_text = len(re.findall(r'href=', text_content))
    print(f'  Escaped &lt;a: {raw_a_open},  &lt;/a&gt;: {raw_a_close}')
    print(f'  href= in visible text: {raw_href_in_text}')

    # 2. Links inside span.note
    note_links = []
    for a in soup.find_all('a', href=True):
        for p in a.parents:
            if p.name == 'span' and 'note' in (p.get('class') or []):
                note_links.append((a.get_text()[:50], a.get('href', '')[:70]))
                break
    self_note = [(t, h) for t, h in note_links if doc_id in h]
    print(f'  Links in span.note: {len(note_links)} total, self-links in notes: {len(self_note)}')
    for t, h in self_note[:3]:
        print(f'    {repr(t)} -> {h}')

    # 3. 'Законом' as internal link
    zakon_internal = [a for a in soup.find_all('a', href=True)
                      if doc_id in a.get('href', '') and 'Закон' in a.get_text()]
    print(f'  "Законом" as internal link: {len(zakon_internal)}')
    for a in zakon_internal[:3]:
        print(f'    {repr(a.get_text()[:60])} -> {a["href"][:80]}')

    # 4. Statistics
    all_links = soup.find_all('a', href=True)
    internal = [l for l in all_links if doc_id in l.get('href', '')]
    external = [l for l in all_links if doc_id not in l.get('href', '') and '85.202.192.66' in l.get('href', '')]
    nested_a = sum(1 for a in soup.find_all('a') if a.find('a'))
    print(f'  Internal links (self): {len(internal)}')
    print(f'  External NPA links:    {len(external)}')
    print(f'  Nested <a> tags:       {nested_a}')
    print()
