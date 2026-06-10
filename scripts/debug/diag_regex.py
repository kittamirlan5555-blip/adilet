import re
from pathlib import Path

KNOWN_HOSTS = r'adilet\.zan\.kz|85\.202\.192\.66:9096'

# точная копия HREF_ABS_INTERNAL_RE из audit_TZ01.py
AUDIT_RE = re.compile(
    r'''<a\b[^>]*?\bhref\s*=\s*(["'])
        (https?://(?:''' + KNOWN_HOSTS + r'''))
        (/(?:rus|kaz)/docs/)
        ([A-Z]\d+_?[A-Z]?)
        (?:\?[^#"'\s]*)?
        \#(z\d+)
        \1
    ''',
    re.IGNORECASE | re.VERBOSE,
)

# та же без префикса <a..., без backreference
PROBE_RE = re.compile(
    r'''href\s*=\s*["']
        https?://(?:''' + KNOWN_HOSTS + r''')
        /(?:rus|kaz)/docs/
        ([A-Z]\d+_?[A-Z]?)
        (?:\?[^#"'\s]*)?
        \#(z\d+)
    ''',
    re.IGNORECASE | re.VERBOSE,
)

t = Path("data/final/trudovoy_ready.html").read_text(encoding="utf-8")
m_audit = list(AUDIT_RE.finditer(t))
m_probe = list(PROBE_RE.finditer(t))
print("AUDIT_RE matches:", len(m_audit))
print("PROBE_RE matches:", len(m_probe))

if m_probe:
    s = m_probe[0].start()
    print("first probe match context:")
    print(repr(t[max(0, s-50):m_probe[0].end()+50]))

# Найти ссылки на own doc K1500000414, которые PROBE нашёл, а AUDIT — НЕТ.
own = "K1500000414"
probe_own = [m for m in m_probe if m.group(1) == own]
audit_own = [m for m in m_audit if m.group(4) == own]
print()
print(f"PROBE matches on own doc: {len(probe_own)}")
print(f"AUDIT matches on own doc: {len(audit_own)}")

# найти 5 примеров, которые PROBE нашёл, но AUDIT нет — сравним по позиции "после =\""
audit_spans = {m.start(): m for m in audit_own}
missed = []
for m in probe_own:
    # AUDIT начинает на "<a", PROBE начинает на "href"; найти "href" внутри AUDIT-матчей
    found = False
    for s, am in audit_spans.items():
        if am.start() <= m.start() <= am.end():
            found = True
            break
    if not found:
        missed.append(m)
        if len(missed) >= 5:
            break

print(f"missing (PROBE has, AUDIT doesn't): {len(missed)} examples shown")
for m in missed:
    s = m.start()
    print()
    print(repr(t[max(0, s-80):m.end()+50]))
