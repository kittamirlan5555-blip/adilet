"""READ-ONLY: классификация ВСЕХ внутренних <a href="#z..."> на классы A/B/C.

Цель — вскрыть «непроверяемый» класс за WRONG=0. Переиспользует РОВНО тот же
резолвер, что и аудит (audit_links_coverage.py): build_id_to_art, claimed_article,
classify_href. Ничего не правит; пишет отчёт в data/reports/.

Классы (для каждой внутренней ссылки #zK внутри div[data-type]):
  R  = id2art[zK]   «телесный»/эффективный резолв (где якорь физически стоит /
                     заголовок сразу за якорем, если тела между ними нет)
  Rn = id2next[zK]  ближайший заголовок ПОСЛЕ якоря
  claim = номер статьи из текста ссылки (claimed_article == ARTICLE)

  A. VERIFIED_OK — claim == R  (строгое совпадение с эффективным резолвом)
  C. LENIENT     — claim == Rn != R  (совпало ТОЛЬКО по послаблению acc={R,Rn};
                     якорь стоит в теле ст.R, а заявлена следующая ст.Rn — зона off-by-one)
  B. NO_NUMBER   — claimed != ARTICLE: NONART (нет номера: «частью первой»,
                     «настоящего Кодекса», «указанной статьи») или SELF («настоящей статьи»)
  WRONG          — claim вне {R,Rn} (должно быть 0; сверка с аудитом)
  BROKEN         — zK нет в документе (должно быть 0)

  python scripts/32_classify_internal_links.py
"""
import re
import sys
import random
import importlib.util
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
REPORT = ROOT / "data" / "reports" / "32_internal_classes.txt"

# импорт аудита (он переопределяет sys.stdout на import — сохраним/вернём)
_so = sys.stdout
_spec = importlib.util.spec_from_file_location(
    "audit", ROOT / "scripts" / "audit_links_coverage.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
sys.stdout = _so

RE_ARTTITLE = A.RE_ARTTITLE
ORDER = ["nalog", "trudovoy", "grazhdanskiy", "grazhdanskiy_osob",
         "predprinimatel", "socialnyy", "ekologicheskiy", "zemelnyy",
         "upk", "koap", "appk", "byudzhet", "ugolovniy"]


def art_titles(soup):
    m = {}
    for d in soup.find_all("div", attrs={"data-type": "статья"}):
        dn = d.get("data-number")
        if not dn:
            continue
        ttl = ""
        for el in d.find_all(["h2", "h3", "h4", "p", "b"], recursive=True):
            mt = RE_ARTTITLE.match(el.get_text(" ", strip=True))
            if mt:
                ttl = el.get_text(" ", strip=True)[:70]
                break
        m[dn] = ttl
    return m


def prev_ctx(a, n=40):
    return A.preceding_text(a, n)[-n:]


def next_ctx(a, n=40):
    buf = ""
    for sib in a.next_siblings:
        buf += sib.get_text(" ") if isinstance(sib, Tag) else str(sib)
        if len(buf) >= n:
            break
    return re.sub(r"\s+", " ", buf)[:n]


def host_article(a):
    hd = a.find_parent("div", attrs={"data-type": "статья"})
    if hd is None:
        return None
    for el in hd.find_all(["h2", "h3", "h4", "p"], recursive=True):
        mt = RE_ARTTITLE.match(el.get_text(" ", strip=True))
        if mt:
            return mt.group(1)
    return hd.get("data-number")


records_B = []   # (code, host, text, zk, R, Rn, prev, next, titleR, subtype)
records_C = []   # (code, host, text, zk, R, Rn, claim, prev, next, titleRn, titleR)
table = []


def main():
    for code in ORDER:
        fp = FINAL / f"{code}_structured.html"
        if not fp.exists():
            continue
        soup = BeautifulSoup(fp.read_text(encoding="utf-8"), "html.parser")
        self_doc = A.SELF_DOC.get(code, "")
        id2art, all_ids, art_numbers, id2next = A.build_id_to_art(soup)
        titles = art_titles(soup)
        c = Counter()
        for a in soup.find_all("a", href=True):
            if not a.find_parent("div", attrs={"data-type": True}):
                continue
            kind, doc = A.classify_href(a["href"], self_doc)
            if kind != "internal":
                continue
            fm = re.search(r"#(z\d+[\w-]*)", a["href"])
            if not fm:
                c["nofrag"] += 1
                continue
            zk = fm.group(1)
            if zk not in all_ids:
                c["BROKEN"] += 1
                continue
            ck, cn = A.claimed_article(a)
            R = id2art.get(zk)
            Rn = id2next.get(zk)
            txt = a.get_text(" ", strip=True)[:40]
            if ck in ("NONART", "SELF"):
                sub = "self" if ck == "SELF" else "nonart"
                c["B"] += 1
                c[f"B_{sub}"] += 1
                # под-классификация B (почему «непроверяема» по номеру):
                if ck == "SELF":
                    c["Bx_self"] += 1
                else:
                    mnum = A.RE_NUM_ONLY.match(txt)
                    if mnum and mnum.group(1) in {str(R), str(Rn)}:
                        # голый номер статьи в перечислении «статьями A, B, C» —
                        # якорь ведёт ровно на эту статью → ПО СУТИ проверяемо
                        c["Bx_artnum"] += 1
                    elif (mnum or re.match(r"(?i)\s*(пункт|част|подпункт|абзац)",
                                           txt) or
                          A.RE_PUNKT_TAIL.search(prev_ctx(a))):
                        c["Bx_subelem"] += 1   # пункт/часть/подпункт → цель = статья-контейнер
                    else:
                        c["Bx_generic"] += 1   # «настоящего Кодекса», раздел/глава, фраза
                records_B.append((code, host_article(a), txt, zk, R, Rn,
                                  prev_ctx(a), next_ctx(a), titles.get(str(R), ""), sub))
                continue
            # ck == ARTICLE
            cn_str = str(cn)
            claim = cn_str
            if "-" in cn_str and cn_str not in art_numbers:
                claim = cn_str.split("-")[0]
            acc = {str(R), str(Rn)}
            if claim not in acc:
                c["WRONG"] += 1
            elif claim == str(R):
                c["A"] += 1
            else:  # claim == str(Rn) and Rn != R
                c["C"] += 1
                records_C.append((code, host_article(a), txt, zk, R, Rn, cn,
                                  prev_ctx(a), next_ctx(a),
                                  titles.get(str(Rn), ""), titles.get(str(R), "")))
        c["total"] = (c["A"] + c["B"] + c["C"] + c["WRONG"] + c["BROKEN"] + c["nofrag"])
        table.append((code, c))

    out = []
    out.append("=" * 100)
    out.append("КЛАССИФИКАЦИЯ ВНУТРЕННИХ <a href=\"#z...\"> (12 кодов + ГК-Особ) — READ-ONLY")
    out.append("A=строгий(claim==R)  C=послабление(claim==Rn!=R, off-by-one зона)  "
               "B=без номера(NONART/SELF)")
    out.append("=" * 100)
    out.append(f"{'код':18}{'A':>7}{'C':>7}{'B':>7}{'(B_self':>8}{'B_nonart)':>10}"
               f"{'WRONG':>7}{'BROKEN':>7}{'ВСЕГО':>7}")
    T = Counter()
    for code, c in table:
        for k in ("A", "C", "B", "B_self", "B_nonart", "WRONG", "BROKEN", "nofrag", "total",
                  "Bx_self", "Bx_artnum", "Bx_subelem", "Bx_generic"):
            T[k] += c[k]
        out.append(f"{code:18}{c['A']:>7}{c['C']:>7}{c['B']:>7}{c['B_self']:>8}"
                   f"{c['B_nonart']:>10}{c['WRONG']:>7}{c['BROKEN']:>7}{c['total']:>7}")
    out.append("-" * 100)
    out.append(f"{'ИТОГО':18}{T['A']:>7}{T['C']:>7}{T['B']:>7}{T['B_self']:>8}"
               f"{T['B_nonart']:>10}{T['WRONG']:>7}{T['BROKEN']:>7}{T['total']:>7}")
    out.append(f"\n  A+C = {T['A'] + T['C']}  (должно == аудит OK=4027)")
    out.append(f"  B   = {T['B']}  (= NONART {T['B_nonart']} + SELF {T['B_self']}; "
               f"аудит NONART=8156, SELF=3)")
    out.append(f"  nofrag(внутр. без #z) = {T['nofrag']}")
    out.append("\n  Под-классификация B (почему цель не сверяется по номеру):")
    out.append(f"    Bx_artnum  = {T['Bx_artnum']:>5}  голый № статьи в перечне «статьями A,B,C» "
               f"→ якорь ведёт ровно на эту статью (ПО СУТИ проверяемо; слепая зона верификатора)")
    out.append(f"    Bx_subelem = {T['Bx_subelem']:>5}  пункт/часть/подпункт/№) → цель = статья-контейнер "
               f"(не статья-уровень claim)")
    out.append(f"    Bx_generic = {T['Bx_generic']:>5}  «настоящего Кодекса»/раздел/глава/фраза "
               f"(истинно генерик)")
    out.append(f"    Bx_self    = {T['Bx_self']:>5}  «настоящей статьи» (сверяемо против host; "
               f"3 легаси SELF_WRONG)")

    random.seed(42)
    sb = random.sample(records_B, min(30, len(records_B)))
    sc = random.sample(records_C, min(20, len(records_C)))

    out.append("\n" + "=" * 100)
    out.append(f"СЭМПЛ B — 30 случайных из {len(records_B)} (NO_NUMBER): цель по номеру НЕ сверяема")
    out.append("формат: [code] host=ст.X | «текст» #zK [subtype] | R=.. Rn=.. | …пред[текст]след…")
    out.append("=" * 100)
    for i, (code, host, txt, zk, R, Rn, pv, nx, tR, sub) in enumerate(sb, 1):
        out.append(f"{i:2}. [{code}] host=ст.{host} | «{txt}» #{zk} [{sub}] | R={R} Rn={Rn}")
        out.append(f"     …{pv}[{txt}]{nx}…")
        out.append(f"     якорь #{zk} → ст.{R}: {tR}")

    out.append("\n" + "=" * 100)
    out.append(f"СЭМПЛ C — 20 случайных из {len(records_C)} (LENIENT): claim==Rn!=R (off-by-one зона)")
    out.append("формат: заявлено ст.CLAIM; якорь в теле ст.R, ведёт на ст.Rn")
    out.append("=" * 100)
    for i, (code, host, txt, zk, R, Rn, cn, pv, nx, tRn, tR) in enumerate(sc, 1):
        out.append(f"{i:2}. [{code}] host=ст.{host} | «{txt}» #{zk} | заявл={cn} | R(тело)={R} Rn(след)={Rn}")
        out.append(f"     …{pv}[{txt}]{nx}…")
        out.append(f"     ведёт→ ст.{Rn}: {tRn}")
        out.append(f"     тело→  ст.{R}: {tR}")

    REPORT.write_text("\n".join(out) + "\n", encoding="utf-8")
    try:
        sys.stderr.write(f"report -> {REPORT}\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
