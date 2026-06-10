import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from bs4 import BeautifulSoup
import json, re

with open('data/trudovoy_ready.html', 'rb') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
with open('data/article_map_trudovoy.json') as f:
    art_map = json.load(f)

def find_article_paragraphs(soup, art_num):
    anchor_id = art_map.get(str(art_num))
    if not anchor_id:
        return []
    start = soup.find(id=anchor_id)
    if not start:
        a = soup.find('a', attrs={'name': anchor_id})
        start = a.parent if a else None
    if not start:
        return []
    paragraphs = []
    if start.name == 'p':
        cur = start.next_sibling
        while cur:
            if hasattr(cur, 'name') and cur.name == 'p':
                b = cur.find('b')
                if b and b.find('a', attrs={'name': True}) and 'Статья' in b.get_text():
                    break
                paragraphs.append(cur)
            if hasattr(cur, 'name') and cur.name == 'h3':
                break
            cur = cur.next_sibling
    return paragraphs

def find_para_by_content(paragraphs, content_substr):
    for p in paragraphs:
        txt = p.get_text().strip()
        if content_substr in txt:
            return p
    return None

def check_linked(para, target):
    if para is None:
        return False
    for a in para.find_all('a'):
        if target in a.get_text():
            return True
    return False

# 28
p146 = find_article_paragraphs(soup, '146-1')
p28 = find_para_by_content(p146, 'пункта 1 статьи 30')
if p28:
    links28 = [a.get_text() for a in p28.find_all('a')]
    ok28 = any('подпунктом 2)' in l for l in links28)
    print('28. %s p.2 st.146-1: links=%s' % ('OK' if ok28 else 'FAIL', links28[:6]))
    if not ok28:
        print('   HTML:', str(p28)[:300])
else:
    print('28. FAIL p.2 st.146-1: paragraph not found, total paras=%d' % len(p146))

# 29
p54 = find_article_paragraphs(soup, '54')
p29 = find_para_by_content(p54, 'статьи 52')
if p29:
    links29 = [a.get_text() for a in p29.find_all('a')]
    ok29 = any('1-1' in l for l in links29)
    print('29. %s p.1 st.54: links=%s' % ('OK' if ok29 else 'FAIL', links29[:8]))
else:
    print('29. FAIL p.1 st.54: paragraph not found')

# 30: style check
found_outside = []
for text_node in soup.find_all(string=True):
    txt = str(text_node)
    for m in re.finditer(r'подпункт\w*\s+\d+\)', txt, re.IGNORECASE):
        parent = text_node.parent
        inside = False
        while parent:
            if parent.name == 'a':
                inside = True
                break
            parent = parent.parent
        if not inside:
            ctx = txt[max(0, m.start()-20):m.end()+40].strip()
            if 'законом' not in ctx.lower() and 'конституционным' not in ctx.lower():
                found_outside.append(ctx[:80])

print('30. %s Style: подпункт outside link: %d' % ('OK' if not found_outside else 'CHECK', len(found_outside)))
for f in found_outside[:8]:
    print('   -', repr(f))
