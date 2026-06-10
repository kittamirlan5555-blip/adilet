# -*- coding: utf-8 -*-
"""ДИАГНОСТИКА grazhdanskiy cov_real 78.9% — READ-ONLY (ничего не правит).

Разбивает «незалинкованные linkable-рефы» ГК на 4 категории, переиспользуя
ТЕ ЖЕ регексы/резолв, что и audit_links_coverage.py, чтобы числа сходились
с аудитом (cov_real = n_link/(n_link + n_unl_real), n_unl_real = 79):

  A) genuine внутр. кросс-реф «статья N», НЕ редакц.-FP, и номер N присутствует
     как статья В ЭТОМ кодексе (есть якорь-цель) -> ДОБИВКА-able;
  A*) «статья N», НЕ FP, но номера N в ГК НЕТ -> кросс-акт/вне диапазона
      (внутренне НЕ добивается; показываем отдельно);
  B) генерик-самоссылки «настоящего Кодекса/статьи/закона» (исключаются методикой);
  C) внешние акты по имени (<Прил> кодекс / Закон РК имен. / Конституция) — без NGR/якоря;
  D) ложные: редакц./сносочные (вводится/действует/в редакции/исключен/Сноска…).

Сверка: A + A* + C(non-FP)  ==  n_unl_real(79);  B == самоотс(265);
        D(статья-FP + закон-FP) == редФП(392).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_links_coverage as A  # переиспуем регексы/хелперы/резолв
from bs4 import BeautifulSoup

CODE = "grazhdanskiy"
FINAL = A.FINAL
ROOT = A.ROOT

soup = BeautifulSoup((FINAL / f"{CODE}_structured.html").read_text(encoding="utf-8"),
                     "html.parser")
id2art, all_ids, art_numbers, id2next = A.build_id_to_art(soup)

blocks = A.content_root(soup)
art_divs = [b for b in blocks if b.get("data-type") == "статья"]
lines = []
for div in art_divs:
    for ln in A.flatten_lines(div):
        if A.RE_ARTTITLE.match(ln.replace(A.LINKMARK, " ").strip()):
            continue
        lines.append(ln)

EDIT = ("вводится в действие", "действует до", "в редакции", "Заголовок",
        "Сноска", "изложен", "исключен", "исключён", "дополнен", "внесен",
        "внесён", "предусматривается в редакции", "приостанов")


def is_editorial(ctx):
    return any(k in ctx for k in EDIT)


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


A_list = []      # (num, ctx) — добивка-able
Astar_list = []  # (num, ctx) — статья N, номера нет в ГК
B_count = 0
C_list = []      # (kind, ctx)
D_stat = 0       # редакц.-FP среди «статья N»
D_zakon = 0      # редакц.-FP среди «Закон РК …от <дата>»

for txt in lines:
    for m in A.RE_ART.finditer(txt):
        num = m.group(1)
        ctx = txt[max(0, m.start() - 45):m.end() + 35]
        fp = is_editorial(ctx) or bool(re.match(
            r"(?i)\s*Стать[яиею]\s+\d+(?:-\d+)?\s+(вводится|действует|приостан)",
            txt[m.start():]))
        if fp:
            D_stat += 1
            continue
        base = num.split("-")[0]
        if num in art_numbers or base in art_numbers:
            A_list.append((num, clean(ctx)))
        else:
            Astar_list.append((num, clean(ctx)))
    for _ in A.RE_SELF.finditer(txt):
        B_count += 1
    for m in A.RE_EXT_KOD.finditer(txt):
        if m.group(1).lower().startswith("настоящ"):
            continue
        C_list.append(("кодекс", clean(txt[max(0, m.start() - 30):m.end() + 25])))
    for m in A.RE_ZAKON.finditer(txt):
        ctx = txt[max(0, m.start() - 10):m.end() + 45]
        fp = bool(re.search(r"от\s+\d", m.group(0))) and is_editorial(ctx)
        if fp:
            D_zakon += 1
        else:
            C_list.append(("закон", clean(ctx)))
    for m in A.RE_KONST.finditer(txt):
        C_list.append(("конституция", clean(txt[max(0, m.start() - 30):m.end() + 20])))

nA = len(A_list)
nAstar = len(Astar_list)
nC = len(C_list)
nD = D_stat + D_zakon
n_unl_real = nA + nAstar + nC

L = []
P = L.append
P("=" * 100)
P("ДИАГНОСТИКА grazhdanskiy (ГК, Общая часть) — cov_real 78.9% — READ-ONLY")
P("=" * 100)
P(f"  статья-номеров в ГК (art_numbers): {len(art_numbers)}    строк тела (без заголовков): {len(lines)}")
P("")
P("  КАТЕГОРИИ «незалинкованных linkable-рефов»:")
P(f"    A  genuine внутр. «статья N», НЕ-FP, якорь-цель ЕСТЬ в ГК (ДОБИВКА-able) : {nA}")
P(f"    A* «статья N», НЕ-FP, номера в ГК НЕТ (кросс-акт/вне диапазона)          : {nAstar}")
P(f"    B  генерик-самоссылки «настоящего Кодекса/статьи/закона» (методика)      : {B_count}")
P(f"    C  внешние по имени (<Прил> кодекс / Закон РК имен. / Конституция)       : {nC}")
P(f"    D  ложные редакц./сносочные (статья-FP={D_stat} + закон-FP={D_zakon})            : {nD}")
P("")
P(f"  СВЕРКА С АУДИТОМ:")
P(f"    n_unl_real = A + A* + C = {nA} + {nAstar} + {nC} = {n_unl_real}   (аудит ждёт 79)")
P(f"    B (самоотс)             = {B_count}                  (аудит ждёт 265)")
P(f"    D (редФП)               = {nD}                  (аудит ждёт 392)")
P("")

# C-разбивка по типу
from collections import Counter
ckind = Counter(k for k, _ in C_list)
P("  C по типам: " + ", ".join(f"{k}={v}" for k, v in ckind.most_common()))
P("")

P("-" * 100)
P(f"  10 ПРИМЕРОВ ИЗ КАТЕГОРИИ A (добивка-able — есть якорь-цель в ГК):")
P("-" * 100)
if A_list:
    for i, (num, ctx) in enumerate(A_list[:10], 1):
        P(f"  {i:>2}. ст.{num:<5} …{ctx}…")
else:
    P("  (пусто — категория A отсутствует)")
P("")

if Astar_list:
    P("-" * 100)
    P(f"  (инфо) до 8 примеров A* (статья N, номера в ГК нет — кросс-акт/вне диапазона):")
    P("-" * 100)
    for i, (num, ctx) in enumerate(Astar_list[:8], 1):
        P(f"  {i:>2}. ст.{num:<5} …{ctx}…")
    P("")

P("=" * 100)
if nA == 0:
    P("ВЫВОД: A = 0  →  78.9% это ЧИСТО МЕТОДИКА (генерик-самоссылки B + внешние C +")
    P("        редакц.-FP D). Внутренних добивка-able кросс-рефов НЕТ. ГК фактически готов.")
elif nA <= 5:
    P(f"ВЫВОД: A = {nA} (мизер) → 78.9% почти полностью методика; точечная добивка возможна,")
    P("        но влияние на cov_real ничтожно. ГК практически готов.")
else:
    P(f"ВЫВОД: A = {nA} — ЗАМЕТНО. Это реальные внутр. кросс-рефы с якорем-целью в ГК,")
    P("        не залинкованные. Готовить добивку по образцу Анары (точечные wrap'ы).")
P("=" * 100)

out = ROOT / "data" / "reports" / "65_grazhdanskiy_diag.txt"
out.write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"written: {out}  A={nA} A*={nAstar} B={B_count} C={nC} D={nD} unl_real={n_unl_real}")
