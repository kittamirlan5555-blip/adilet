"""Диагностика: насколько глубоко скрипт 17 нормализовал ссылки.
   Read-only; печатает разнообразные счётчики, чтобы выяснить, где
   могли «спрятаться» 164/200 нелокализованных ссылок."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FINAL = ROOT / "data" / "final"

TARGETS = [
    ("trudovoy",       "K1500000414"),
    ("predprinimatel", "K1500000375"),
    ("nalog",          "K2500000214"),
    ("socialnyy",      "K2300000224"),
]

HOSTS = r"(?:adilet\.zan\.kz|85\.202\.192\.66:9096)"
ANCHOR_RE = re.compile(r'\b(?:id|name)\s*=\s*"(z\d+)"')

def re_count(p, t):
    return len(re.findall(p, t, re.I))

for code, did in TARGETS:
    for suf in ("ready", "structured"):
        p = FINAL / f"{code}_{suf}.html"
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        anchors = set(ANCHOR_RE.findall(t))

        all_href           = re_count(r'href\s*=', t)
        abs_any            = re_count(r'href\s*=\s*["\']https?://' + HOSTS, t)
        abs_own_anywhere   = re_count(r'href\s*=\s*["\']https?://' + HOSTS + r'/(?:rus|kaz)/docs/' + did, t)
        abs_own_with_z     = re_count(r'href\s*=\s*["\']https?://' + HOSTS + r'/(?:rus|kaz)/docs/' + did + r'(?:\?[^#"\' ]*)?#z\d+', t)
        local_zN           = re_count(r'href\s*=\s*["\']#z\d+["\']', t)
        ip_text            = t.count("85.202.192.66")

        # absolute → own_doc → #zN, where the anchor IS present in the file
        # (= would-be A; должно быть 0 после скрипта 17)
        a_pattern = re.compile(
            r'href\s*=\s*["\']https?://' + HOSTS +
            r'/(?:rus|kaz)/docs/' + did + r'(?:\?[^#"\' ]*)?#(z\d+)',
            re.I)
        present, missing = 0, 0
        for m in a_pattern.finditer(t):
            if m.group(1) in anchors:
                present += 1
            else:
                missing += 1

        print(f"[{code}_{suf}]  doc_id={did}  anchors_in_file={len(anchors)}")
        print(f"   all_href={all_href}  abs_any_host={abs_any}  ip_text={ip_text}")
        print(f"   abs_to_own_doc(any)={abs_own_anywhere}  abs_to_own_doc#zN={abs_own_with_z}")
        print(f"     [+] anchor present in file: {present}   <- A")
        print(f"     [-] anchor MISSING in file: {missing}   (не лечится скриптом 17)")
        print(f"   local href=#zN:    {local_zN}")
        print()
