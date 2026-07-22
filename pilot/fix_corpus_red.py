# -*- coding: utf-8 -*-
"""E1: root-даунгрейд 11 битых cross-code пар в ПРИНЯТОМ корпусе (решение владельца).

Прецедент «статьи 9-4»: цель-якорь не существует нигде (пруф: нет в source цели) →
минимум root того же акта. Правка ТОЛЬКО href (сырой текст, точная строка) — спан и
видимый текст байт-в-байт. Обе формы (_ready/_structured). Бэкапы в scratchpad.

Гейты на каждый файл: get_text (БЕЗ разделителя) sha до==после; вложенных <a> 0;
целевых '#z' для пары не осталось; счёт замен = счёт вхождений.
"""
import hashlib, io, re, shutil, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BAK = Path(r"C:\Users\user\AppData\Local\Temp\claude\C--Users-user-Desktop-ADILETkz"
           r"\05d2f495-4ada-4c40-8b28-90554cb40953\scratchpad\corpus_red_bak")
BAK.mkdir(parents=True, exist_ok=True)

PAIRS = [
    ("grazhdanskiy",      "Z1400000176", "z446"),
    ("grazhdanskiy_osob", "Z2200000178", "z6"),
    ("grazhdanskiy_osob", "Z2300000021", "z0"),
    ("koap",              "Z000000085_", "z17-1"),
    ("koap",              "Z1400000188", "z1436"),
    ("obrazovanie",       "Z1500000314", "z322"),
    ("predprinimatel",    "Z1400000202", "z248"),
    ("predprinimatel",    "Z2400000103", "z0"),
    ("zemelnyy",          "Z1700000047", "z44"),
    ("zemelnyy",          "Z2500000165", "z0"),
    ("zhilishniy",        "Z2300000014", "z0"),
    # +2 MISMATCH, найденные 75-м (тот же класс: live-сетка, на наших сборках ЧУЖАЯ
    # статья: z10=ст.12 вместо ст.10; z8=не-статья вместо ст.8). Ре-поинт на наши
    # якоря НЕ делаем (вшил бы модель A — §9 запаркован) — root нейтрален.
    ("koap",              "Z000000085_", "z10"),
    ("koap",              "Z100000257_", "z8"),
]


def vis_sha(html):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(["script", "style"]):
        t.decompose()
    return hashlib.sha256("".join(soup.get_text().split()).encode()).hexdigest()


def nested(html):
    soup = BeautifulSoup(html, "html.parser")
    return sum(1 for a in soup.find_all("a") if a.find_parent("a"))


apply = "--apply" in sys.argv
bydoc = {}
for doc, tgt, z in PAIRS:
    bydoc.setdefault(doc, []).append((tgt, z))

total = 0
for doc, pairs in bydoc.items():
    for form in ("_ready", "_structured"):
        p = ROOT / "final" / f"{doc}{form}.html"
        if not p.exists():
            continue
        html = p.read_text(encoding="utf-8", errors="replace")
        sha0, n0 = vis_sha(html), nested(html)
        new = html
        repl = 0
        for tgt, z in pairs:
            frag = f"docs/{tgt}#{z}"
            root = f"docs/{tgt}"
            # точная подстрока href с закрывающей кавычкой — не заденем длинные якоря
            for q in ('"', "'"):
                cnt = new.count(frag + q)
                new = new.replace(frag + q, root + q)
                repl += cnt
        if repl == 0:
            continue
        sha1, n1 = vis_sha(new), nested(new)
        left = sum(new.count(f"docs/{t}#{z}") for t, z in pairs)
        ok = (sha0 == sha1) and (n1 == n0) and left == 0
        print(f"  {doc}{form}: замен={repl}  text-inv={sha0==sha1}  nested {n0}->{n1}  "
              f"остаток-пар=0:{left==0}  => {'OK' if ok else 'FAIL'}")
        if not ok:
            sys.exit(f"СТОП: гейт не прошёл на {p.name}")
        if apply:
            shutil.copy2(p, BAK / p.name)
            p.write_text(new, encoding="utf-8")
        total += repl
print(f"\nвсего href-замен: {total}  ({'ЗАПИСАНО, бэкапы: ' + str(BAK) if apply else 'dry-run'})")
