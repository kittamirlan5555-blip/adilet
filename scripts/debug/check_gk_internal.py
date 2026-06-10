import sys, re, json
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup

with open('data/grazhdanskiy.html', 'rb') as f:
    html = f.read().decode('utf-8')
with open('data/article_map_grazhdanskiy.json', encoding='utf-8') as f:
    art_map = json.load(f)

# Invert art_map: anchor -> art_num
anchor_to_art = {v: k for k, v in art_map.items()}

# Cases to investigate
cases = [
    ('п.1 ст.3',    '3',   'пунктах 1,'),
    ('п.1 ст.5',    '5',   'пунктами 1 и'),
    ('п.6 ст.58',   '58',  'пунктах 4 и'),
    ('п.7 ст.157-1','157-1','пунктами 5 и'),
    ('п.8 ст.159',  '159', 'статья 150'),
    ('п.12 ст.159', '159', 'пунктами 3,'),
    ('п.2 ст.162',  '162', 'пунктами 9 и'),
    ('п.1 ст.171',  '171', 'пунктах 5 и'),
    ('п.3 ст.178',  '178', 'статей 177'),
    ('п.5 ст.218',  '218', 'пунктами 3 и'),
    ('п.4 ст.220',  '220', 'Пункты 1-3 настоящей'),
    ('п.3 ст.225',  '225', 'пунктами 1 и'),
    ('п.2 ст.244',  '244', 'пунктами 3 и'),
    ('ст.258',      '258', 'статьями 249-257'),
    ('п.1 ст.263',  '263', 'статей 260, 261'),
    ('ст.265',      '265', 'статьями 259-264'),
    ('п.2 ст.267',  '267', 'пункта 1'),
    ('п.2 ст.321',  '321', 'подпунктами 1 и'),
    ('п.3 ст.334',  '334', 'пунктами 1 и'),
    ('п.3 ст.348',  '348', 'пунктах 1 и'),
    ('ст.400',      '400', 'пунктах 2 и'),
]

for label, art_num, keyword in cases:
    anchor = art_map.get(art_num)
    if not anchor:
        print(f'{label}: anchor NOT FOUND for art {art_num}')
        continue
    # Find article in HTML
    art_pos = html.find(f'"{anchor}"')
    if art_pos < 0:
        print(f'{label}: anchor {anchor} not in HTML')
        continue
    # Search for keyword after article anchor, up to next article
    search_area = html[art_pos:art_pos+8000]
    kw_pos = search_area.lower().find(keyword.lower())
    if kw_pos < 0:
        print(f'{label}: keyword "{keyword}" NOT FOUND in art {art_num} area')
        continue
    # Show full context around keyword
    ctx_start = max(0, kw_pos - 100)
    ctx_end = min(len(search_area), kw_pos + 200)
    ctx = search_area[ctx_start:ctx_end]
    # Check if already linked
    already_linked = '<a href=' in search_area[max(0,kw_pos-10):kw_pos+len(keyword)+20]
    print(f'{label}: {"LINKED" if already_linked else "UNLINKED"} | {ctx.strip()[:200]}')
    print()
