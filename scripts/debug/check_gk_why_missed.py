import sys, re, json
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup

with open('data/grazhdanskiy.html', 'rb') as f:
    html = f.read().decode('utf-8')
with open('data/article_map_grazhdanskiy.json', encoding='utf-8') as f:
    art_map = json.load(f)

# Detailed analysis of each unlinked case
cases = [
    # (label, art_num, keyword, target_art, target_punkt)
    ('п.1 ст.3',    '3',    'пунктах 1, 2 статьи 1',          '1',   None),
    ('п.1 ст.5',    '5',    'пунктами 1 и 2 статьи 1',         '1',   None),
    ('п.6 ст.58',   '58',   'пунктах 4 и 5 статьи 41',         '41',  None),
    ('п.7 ст.157-1','157-1','пунктами 5 и 6 настоящей статьи', '157-1', None),
    ('п.8 ст.159',  '159',  'статья 150 настоящего',            '150', None),
    ('п.12 ст.159', '159',  'пунктами 3, 5 настоящей статьи',  '159', None),
    ('п.2 ст.162',  '162',  'пунктами 9 и 10 статьи 159',      '159', None),
    ('п.1 ст.171',  '171',  'пунктах 5 и 7 статьи 170',        '170', None),
    ('п.3 ст.178',  '178',  'статей 177, 179-186',              '177', None),
    ('п.5 ст.218',  '218',  'пунктами 3 и 4 настоящей статьи', '218', None),
    ('п.4 ст.220',  '220',  'Пункты 1-3 настоящей статьи',     '220', None),
    ('п.3 ст.225',  '225',  'пунктами 1 и 2 настоящей статьи', '225', None),
    ('п.2 ст.244',  '244',  'пунктами 3 и 4 настоящей статьи', '244', None),
    ('ст.258',      '258',  'статьями 249-257',                 '249', None),
    ('п.1 ст.263',  '263',  'статей 260, 261 настоящего',       '260', None),
    ('ст.265',      '265',  'статьями 259-264',                 '259', None),
    ('п.2 ст.267',  '267',  'правилами пункта 1',               '267', None),  # already linked to external?
    ('п.3 ст.334',  '334',  'пунктами 1 и 2 настоящей статьи', '334', None),
    ('п.3 ст.348',  '348',  'пунктах 1 и 2 статьи 346',        '346', None),
    ('ст.400',      '400',  'пунктах 2 и 3 статьи 399',        '399', None),
]

print('=== WHY MISSED: Internal reference analysis ===')
for label, art_num, pattern, target_art, _ in cases:
    anchor = art_map.get(art_num)
    if not anchor:
        print(f'{label}: NO ANCHOR')
        continue
    art_pos = html.find(f'"{anchor}"')
    if art_pos < 0:
        continue
    search_area = html[art_pos:art_pos+8000]
    kw_pos = search_area.lower().find(pattern.lower()[:30])
    if kw_pos < 0:
        print(f'{label}: pattern not found')
        continue
    ctx = search_area[max(0,kw_pos-20):kw_pos+len(pattern)+100]

    # Classify the type
    if 'настоящей статьи' in pattern.lower():
        ref_type = 'SELF_REF (same article punkty)'
    elif 'настоящего' in pattern.lower() and target_art != art_num:
        ref_type = 'OTHER_ART ref'
    else:
        ref_type = 'CROSS_ART ref'

    target_exists = target_art in art_map
    print(f'{label}: type={ref_type} target_art={target_art} in_map={target_exists}')
    print(f'  text: ...{ctx[:120]}...')
    print()
