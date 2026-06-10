import sys, re, os, json
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup

files = [
    ('data/final/nalog_ready.html', 'NALOG', 'K2500000214',
     'data/maps/article_map_nalog.json', 'data/maps/subpoint_map_nalog.json', 'data/reports/report_nalog.csv'),
    ('data/final/grazhdanskiy_ready.html', 'GRAZHDANSKIY', 'K940001000_',
     'data/maps/article_map_grazhdanskiy.json', 'data/maps/subpoint_map_grazhdanskiy.json', 'data/reports/report_grazhdanskiy.csv'),
]

for fname, label, doc_id, art_map_f, sub_map_f, report_f in files:
    print(f'=== {label} ===')

    art_map = json.load(open(art_map_f)) if os.path.exists(art_map_f) else {}
    sub_map = json.load(open(sub_map_f)) if os.path.exists(sub_map_f) else {}
    print(f'  Статей в маппинге:         {len(art_map)}')
    print(f'  Подпунктов/пунктов:        {len(sub_map)}')

    # Count from report
    if os.path.exists(report_f):
        with open(report_f, encoding='utf-8') as f:
            lines = f.readlines()
        print(f'  Строк в CSV-отчёте:        {len(lines)-1}')

    with open(fname, 'rb') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    all_links = soup.find_all('a', href=True)
    internal = [l for l in all_links if doc_id in l.get('href', '')]
    external = [l for l in all_links if doc_id not in l.get('href', '') and '85.202.192.66' in l.get('href', '')]

    # Breakdown of internal links
    stat_links = [l for l in internal if re.search(r'стать', l.get_text(), re.I)]
    punkt_links = [l for l in internal if re.search(r'пункт', l.get_text(), re.I) and not re.search(r'стать', l.get_text(), re.I)]
    subp_links = [l for l in internal if re.search(r'подпункт', l.get_text(), re.I)]
    other_links = [l for l in internal if not re.search(r'стать|пункт|подпункт', l.get_text(), re.I)]

    print(f'  Внутренних ссылок всего:   {len(internal)}')
    print(f'    из них на статьи:        {len(stat_links)}')
    print(f'    из них на пункты:        {len(punkt_links)}')
    print(f'    из них на подпункты:     {len(subp_links)}')
    print(f'    прочие (числовые, etc):  {len(other_links)}')
    print(f'  Внешних НПА ссылок:        {len(external)}')

    # External breakdown by doc
    ext_docs = {}
    for l in external:
        href = l.get('href', '')
        m = re.search(r'/docs/([A-Z0-9_]+)', href)
        if m:
            ext_docs[m.group(1)] = ext_docs.get(m.group(1), 0) + 1
    print(f'  Внешние НПА (топ-5 по doc_id):')
    for d, cnt in sorted(ext_docs.items(), key=lambda x: -x[1])[:5]:
        print(f'    {d}: {cnt}')
    print()
