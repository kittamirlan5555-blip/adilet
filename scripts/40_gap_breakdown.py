# -*- coding: utf-8 -*-
"""
READ-ONLY. Вскрытие ковередж-гэпа (РЕАЛЬНЫЕ незалинкованные адресные отсылки).
Денонатор cov_real МИНУС linked, разложенный по типам, плюс СКРЫТЫЙ тип (d).

Типы (по ТЗ пользователя):
  (a) «статья N» внутр.                — bare article ref (RE_ART, не пункт/часть, не FP)
  (b) «пункт N статьи M / N)»          — subpoint-of-article (RE_ART c пункт/часть-префиксом)
  (c) внешний акт по имени без ссылки  — RE_EXT_KOD + RE_ZAKON(имен./дат) + RE_KONST
  (d) перечни, где залинкован только первый номер
        «статьями 108, 109, 115» -> 108=⟦L⟧/ст-матч, 109/115 = ХВОСТ перечня (СКРЫТО от cov_real!)

FP-фильтры идентичны audit_links_coverage (ИЗПИ-сроки, сносочная история, генерик
'настоящего Кодекса' исключены). (a)+(b)+(c) сверяется с A.n_unl_real по коду.
Тип (d) — ДОПОЛНИТЕЛЬНЫЙ гэп: текущий cov_real его НЕ считает.

Выход: data/reports/40_gap_breakdown.txt (+ markdown-таблица в stdout, ascii-safe).
"""
import sys, importlib.util, re
from pathlib import Path
from collections import Counter, defaultdict
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]

# import audit module A (detach its stdout wrapper so it won't close our buffer)
saved = sys.stdout
spec = importlib.util.spec_from_file_location("A", str(ROOT / "scripts/audit_links_coverage.py"))
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
w = sys.stdout; sys.stdout = saved
try: w.detach()
except Exception: pass

LM = A.LINKMARK.strip()  # "⟦L⟧"
EDIT = ("вводится в действие", "действует до", "в редакции", "Заголовок",
        "Сноска", "изложен", "исключен", "исключён", "дополнен", "внесен",
        "внесён", "предусматривается в редакции", "приостанов")
def is_editorial(ctx): return any(k in ctx for k in EDIT)

RE_ART = A.RE_ART                  # \bстат(?:ь..|ей)\s+(\d+(?:-\d+)?)
RE_EXT_KOD = A.RE_EXT_KOD
RE_ZAKON = A.RE_ZAKON
RE_KONST = A.RE_KONST
RE_ARTTITLE = A.RE_ARTTITLE
# «пункт N / часть N / подпункт N) / абзац N» в окне ПЕРЕД 'статьи M' -> тип (b)
RE_SUBPREF = re.compile(r"(?i)(подпункт|пункт|част[ьи]|абзац)[а-яё]*\s+\d+(?:-\d+)?\)?")
TOKEN = r"(?:" + re.escape(LM) + r"|\d+(?:-\d+)?)"
RE_LIST = re.compile(r"(?i)стат(?:ь[а-яё]{0,3}|ей)\s+(" + TOKEN + r"(?:\s*(?:,|\bи\b)\s*" + TOKEN + r")+)")
RE_NUM = re.compile(r"\d+(?:-\d+)?")

ORDER = ["nalog","trudovoy","grazhdanskiy","grazhdanskiy_osob","predprinimatel",
         "socialnyy","ekologicheskiy","zemelnyy","upk","koap","appk","byudzhet","ugolovniy"]

def get_lines(soup):
    blocks = A.content_root(soup)
    art_divs = [b for b in blocks if b.get("data-type") == "статья"]
    lines = []
    for div in art_divs:
        for ln in A.flatten_lines(div):
            if RE_ARTTITLE.match(ln.replace(A.LINKMARK, " ").strip()):
                continue
            lines.append(ln)
    return lines

def analyze(code):
    fp = ROOT / f"data/final/{code}_structured.html"
    soup = BeautifulSoup(fp.read_text(encoding="utf-8"), "html.parser")
    lines = get_lines(soup)
    cnt = Counter()  # a,b,c,d
    ex = defaultdict(list)
    for txt in lines:
        # ---- (a)/(b): RE_ART unlinked article refs ----
        for m in RE_ART.finditer(txt):
            ctx = txt[max(0, m.start()-45):m.end()+35]
            fp_edit = is_editorial(ctx) or bool(re.match(
                r"(?i)\s*Стать[яиею]\s+\d+(?:-\d+)?\s+(вводится|действует|приостан)", txt[m.start():]))
            if fp_edit:
                continue
            before = txt[max(0, m.start()-30):m.start()]
            typ = "b" if RE_SUBPREF.search(before) else "a"
            cnt[typ] += 1
            ex[typ].append((code, re.sub(r"\s+"," ",m.group(0)).strip(),
                            re.sub(r"\s+"," ",ctx).strip()))
        # ---- (c): external act by name ----
        for m in RE_EXT_KOD.finditer(txt):
            if m.group(1).lower().startswith("настоящ"):
                continue
            cnt["c"] += 1
            ex["c"].append((code, "<Прил> кодекс: "+re.sub(r"\s+"," ",m.group(0)).strip(),
                            re.sub(r"\s+"," ",txt[max(0,m.start()-30):m.end()+30]).strip()))
        for m in RE_ZAKON.finditer(txt):
            ctx = txt[max(0, m.start()-10):m.end()+45]
            if re.search(r"от\s+\d", m.group(0)) and is_editorial(ctx):
                continue
            cnt["c"] += 1
            ex["c"].append((code, "Закон: "+re.sub(r"\s+"," ",m.group(0)).strip(),
                            re.sub(r"\s+"," ",ctx).strip()))
        for m in RE_KONST.finditer(txt):
            cnt["c"] += 1
            ex["c"].append((code, "Конституция",
                            re.sub(r"\s+"," ",txt[max(0,m.start()-30):m.end()+30]).strip()))
        # ---- (d): enumeration tails ----
        for m in RE_LIST.finditer(txt):
            ctx = txt[max(0, m.start()-45):m.end()+20]
            if is_editorial(ctx):
                continue
            lst = m.group(1)
            # ordered tokens
            toks = re.findall(re.escape(LM) + r"|\d+(?:-\d+)?", lst)
            # bare-number tokens at index>=1 are unlinked tails
            tail = 0
            for i, tk in enumerate(toks):
                if i == 0:
                    continue
                if tk != LM and RE_NUM.fullmatch(tk):
                    tail += 1
            if tail:
                cnt["d"] += tail
                ex["d"].append((code, f"перечень (+{tail} хвост): стать… "+re.sub(r"\s+"," ",lst).strip()[:60],
                                re.sub(r"\s+"," ",ctx).strip()))
    # cross-check vs audit n_unl_real
    r = A.analyze_code(code)
    return cnt, ex, r["n_unl_real"], r["n_linked"], r["coverage_real"]

def main():
    out = []
    rows = []
    EX = defaultdict(list)
    Ta=Tb=Tc=Td=Tur=0
    for code in ORDER:
        cnt, ex, n_ur, n_link, cov = analyze(code)
        a,b,c,d = cnt["a"],cnt["b"],cnt["c"],cnt["d"]
        abc = a+b+c
        rows.append((code, a, b, c, d, abc, n_ur, cov))
        Ta+=a; Tb+=b; Tc+=c; Td+=d; Tur+=n_ur
        for t in "abcd":
            EX[t].extend(ex[t])
    out.append("# Ковередж-гэп: РЕАЛЬНЫЕ незалинкованные адресные отсылки (READ-ONLY)\n")
    out.append("Денонатор cov_real МИНУС linked, по типам. (a)+(b)+(c) сверены с A.n_unl_real.")
    out.append("Тип (d) — перечни-хвосты — ДОПОЛНИТЕЛЬНЫЙ гэп: cov_real его НЕ считает (хвостовые номера")
    out.append("не имеют слова «статья» перед собой, RE_ART их не видит).\n")
    out.append("| код | (a) статья N | (b) пункт/часть ст.M | (c) внеш.акт по имени | a+b+c | n_unl_real(аудит) | свер | (d) хвост перечня |")
    out.append("|---|---:|---:|---:|---:|---:|:--:|---:|")
    for code,a,b,c,d,abc,n_ur,cov in rows:
        ok = "OK" if abs(abc-n_ur)<=2 else f"d{abc-n_ur:+d}"
        out.append(f"| {code} | {a} | {b} | {c} | {abc} | {n_ur} | {ok} | {d} |")
    out.append(f"| **ИТОГО** | **{Ta}** | **{Tb}** | **{Tc}** | **{Ta+Tb+Tc}** | **{Tur}** | | **{Td}** |")
    out.append("")
    out.append(f"Реальный гэп (a+b+c) = {Ta+Tb+Tc} ссылок ; СКРЫТЫЙ тип (d) = {Td} хвостовых номеров (сверх cov_real).")
    out.append("")
    # 30 raw examples spread across types/codes
    out.append("## 30 сырых примеров (по типам)\n")
    picks = []
    pools = {t: list(EX[t]) for t in "abcd"}
    ti = 0; types = ["a","b","c","d"]
    while len(picks) < 30 and any(pools[t] for t in types):
        t = types[ti % 4]
        if pools[t]:
            picks.append((t, pools[t].pop(0)))
        ti += 1
    for t,(code,ph,ctx) in picks:
        out.append(f"- **({t})** [{code}] «{ph}»  …{ctx}…")
    txt = "\n".join(out) + "\n"
    (ROOT/"data/reports/40_gap_breakdown.txt").write_text(txt, encoding="utf-8")
    sys.stdout.write(txt.encode("ascii","replace").decode("ascii"))

if __name__ == "__main__":
    main()
