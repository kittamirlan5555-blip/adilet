"""READ-ONLY: МЕХАНИЧЕСКАЯ до-верификация внутренних <a href="#z...">.
Данные НЕ трогаем. Только инструмент. Переиспользует резолвер аудита.

Идея: закрыть «слепую зону» верификатора (класс B из скрипта 32 = 8159), извлекая
заявленную статью-цель там, где это делается МЕХАНИЧЕСКИ надёжно:
  R1. видимый текст = голый номер статьи, а ПЕРЕД ним ближайшее управляющее слово —
      «стать…» (перечень «статьями 108, 109, 115-1»): claim = этот номер.
  R2. пункт/часть/подпункт-ссылка с явным ХВОСТОМ «…статьи N»: claim = N.
Затем сверяем claim ∈ acc={R,Rn} (тот же резолв и то же послабление, что в аудите).

Бакеты:
  VERIFIED  = A_strict(claim==R) + A_lenient(claim==Rn) + bare_artnum + subelem_tail
  WRONG     = есть УВЕРЕННЫЙ claim статьи, но claim ∉ {R,Rn}  (ждём 0; печатаем КАЖДУЮ)
  UNVERIF   = self | structural(раздел/глава) | generic(«настоящего Кодекса»/фраза)
              | host_subelem (пункт/часть на «настоящей статьи» — цель = host)

  python scripts/33_verify_internal_max.py
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
REPORT = ROOT / "data" / "reports" / "33_internal_verify.txt"

_so = sys.stdout
_spec = importlib.util.spec_from_file_location(
    "audit", ROOT / "scripts" / "audit_links_coverage.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
sys.stdout = _so

RE_ARTTITLE = A.RE_ARTTITLE
RE_NUM_ONLY = A.RE_NUM_ONLY
ORDER = ["nalog", "trudovoy", "grazhdanskiy", "grazhdanskiy_osob",
         "predprinimatel", "socialnyy", "ekologicheskiy", "zemelnyy",
         "upk", "koap", "appk", "byudzhet", "ugolovniy"]

# управляющие слова перечня (для R1) — стем как в аудите
GOV_ART = re.compile(r"(?i)стат(?:ь[а-яё]{0,3}|ей)")
GOV_SUB = re.compile(r"(?i)(подпункт|пункт|\bчаст|абзац)")
GOV_STRUCT = re.compile(r"(?i)(\bраздел|\bглав|параграф)")
# хвост «…статьи N» (R2): ЯКОРЕМ ^ — «статьи N» должно идти НЕПОСРЕДСТВЕННО за ссылкой
# (между ссылкой и «стать» только цифры/запятые/тире/«и»/скобки), иначе ловим чужой
# «статьи N» из соседнего сочинённого линка или из Сноски. «настоящ… стать» = host (N=None).
RE_TAIL = re.compile(
    r"(?i)^[\s\d,)–—\-и]*"
    r"(?:настоящ\w+\s+стат(?:ь[а-яё]{0,3}|ей)|стат(?:ь[а-яё]{0,3}|ей)\s+(\d+(?:-\d+)?))")
RE_SUBWORD = re.compile(r"(?i)^\s*(пункт|\bчаст|подпункт|абзац)")


def art_titles(soup):
    m = {}
    for d in soup.find_all("div", attrs={"data-type": "статья"}):
        dn = d.get("data-number")
        if dn and dn not in m:
            m[dn] = ""
            for el in d.find_all(["h2", "h3", "h4", "p", "b"], recursive=True):
                mt = RE_ARTTITLE.match(el.get_text(" ", strip=True))
                if mt:
                    m[dn] = el.get_text(" ", strip=True)[:70]
                    break
    return m


def prev_text(a, n=300):
    return A.preceding_text(a, n)[-n:]


def next_text(a, n=80):
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


def governing(pv):
    """Тип ближайшего слева управляющего слова: ART | SUB | STRUCT | None."""
    best = None
    for typ, rx in (("ART", GOV_ART), ("SUB", GOV_SUB), ("STRUCT", GOV_STRUCT)):
        last = None
        for mm in rx.finditer(pv):
            last = mm
        if last and (best is None or last.start() > best[0]):
            best = (last.start(), typ)
    return best[1] if best else None


def trailing_article(nx):
    """N из НЕПОСРЕДСТВЕННОГО хвоста «…статьи N»; None если «настоящей статьи»/нет хвоста."""
    m = RE_TAIL.match(nx)
    if not m:
        return None
    return m.group(1)  # None для ветки «настоящ… стать» (host)


def eff_claim(claim, art_numbers):
    """диапазон «A-B» (не существует как под-статья) -> начало A."""
    if "-" in claim and claim not in art_numbers:
        return claim.split("-")[0]
    return claim


def classify(a, id2art, id2next, all_ids, art_numbers):
    fm = re.search(r"#(z\d+[\w-]*)", a["href"])
    if not fm:
        return ("UNVERIF", "nofrag", None, None, None)
    zk = fm.group(1)
    if zk not in all_ids:
        return ("WRONG", "broken", None, None, None)
    R = id2art.get(zk)
    Rn = id2next.get(zk)
    acc = {str(R), str(Rn)}
    vt = a.get_text(" ", strip=True)
    ck, cn = A.claimed_article(a)

    # уже извлекается аудитом
    if ck == "ARTICLE":
        ce = eff_claim(str(cn), art_numbers)
        if ce in acc:
            tag = "A_strict" if ce == str(R) else "A_lenient"
            return ("VERIFIED", tag, cn, R, Rn)
        return ("WRONG", "article_text", cn, R, Rn)
    if ck == "SELF":
        return ("UNVERIF", "self", None, R, Rn)

    pv = prev_text(a)
    nx = next_text(a)
    gov = governing(pv)
    numm = RE_NUM_ONLY.match(vt)
    is_struct_vt = bool(RE_STRUCT_VT.search(vt))

    # R1: видимый текст — голый номер.
    if numm:
        n = numm.group(1)
        ce = eff_claim(n, art_numbers)
        if ce in acc:
            # якорь РЕЗОЛВИТ ровно в статью с этим номером -> сильнейшее доказательство,
            # независимо от ближайшего управляющего слова (часть/глава могут быть рядом)
            return ("VERIFIED", "bare_artnum", n, R, Rn)
        # номер НЕ совпал с резолвом — выясняем природу, прежде чем кричать WRONG
        if gov == "STRUCT" or is_struct_vt:
            return ("UNVERIF", "structural", n, R, Rn)    # номер ГЛАВЫ/раздела: «главами 39, 40»
        if gov == "SUB":
            return ("UNVERIF", "host_subelem", n, R, Rn)  # номер подпункта/пункта: «1) – 23)»
        if gov == "ART":
            if ce in art_numbers:
                return ("WRONG", "wrong_artnum", n, R, Rn)  # статья N СУЩЕСТВУЕТ, а якорь не на неё
            return ("UNVERIF", "repealed", n, R, Rn)        # «статьями N»: N исключена/нет в кодексе
        return ("UNVERIF", "generic", n, R, Rn)

    # структурная ссылка (раздел/глава/параграф) — цель не статья-уровня, не сверяема
    if gov == "STRUCT" or is_struct_vt:
        return ("UNVERIF", "structural", None, R, Rn)

    # R2: пункт/часть/подпункт с НЕПОСРЕДСТВЕННЫМ хвостом «…статьи N»
    tail = trailing_article(nx)
    if tail is not None:
        ce = eff_claim(tail, art_numbers)
        if ce in acc:
            return ("VERIFIED", "subelem_tail", tail, R, Rn)
        if ce in art_numbers:
            return ("WRONG", "wrong_tail", tail, R, Rn)
        return ("UNVERIF", "generic", tail, R, Rn)

    # «настоящей статьи»/«настоящего пункта»/фраза — цель = host или генерик
    if bool(RE_SUBWORD.match(vt)) or gov == "SUB":
        return ("UNVERIF", "host_subelem", None, R, Rn)
    return ("UNVERIF", "generic", None, R, Rn)


RE_STRUCT_VT = re.compile(r"(?i)(\bраздел|\bглав|параграф)")

records_unv = []
wrongs = []
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
            bucket, tag, claim, R, Rn = classify(a, id2art, id2next, all_ids, art_numbers)
            c[bucket] += 1
            c[f"t_{tag}"] += 1
            if bucket == "WRONG":
                wrongs.append((code, host_article(a), a.get_text(" ", strip=True)[:40],
                               a["href"], claim, R, Rn, tag,
                               prev_text(a, 45)[-45:], next_text(a, 45)))
            elif bucket == "UNVERIF" and tag != "nofrag":
                records_unv.append((code, host_article(a), a.get_text(" ", strip=True)[:40],
                                    a["href"], R, Rn, tag,
                                    prev_text(a, 40)[-40:], next_text(a, 40),
                                    titles.get(str(R), "")))
        c["VERIFIED"] = (c["t_A_strict"] + c["t_A_lenient"]
                         + c["t_bare_artnum"] + c["t_subelem_tail"])
        c["total"] = c["VERIFIED"] + c["WRONG"] + c["UNVERIF"]
        table.append((code, c))

    out = []
    out.append("=" * 108)
    out.append("МЕХАНИЧЕСКАЯ ВЕРИФИКАЦИЯ ВНУТРЕННИХ <a href=\"#z...\"> (12 + ГК-Особ) — READ-ONLY")
    out.append("VERIFIED = A_strict+A_lenient+bare_artnum+subelem_tail | WRONG | TRULY_UNVERIFIABLE")
    out.append("=" * 108)
    out.append(f"{'код':18}{'VERIFIED':>9}{'(A':>6}{'+artnum':>8}{'+tail)':>7}"
               f"{'WRONG':>7}{'UNVERIF':>9}{'ВСЕГО':>7}")
    T = Counter()
    for code, c in table:
        for k in c:
            T[k] += c[k]
        Astrict = c["t_A_strict"] + c["t_A_lenient"]
        out.append(f"{code:18}{c['VERIFIED']:>9}{Astrict:>6}{c['t_bare_artnum']:>8}"
                   f"{c['t_subelem_tail']:>7}{c['WRONG']:>7}{c['UNVERIF']:>9}{c['total']:>7}")
    out.append("-" * 108)
    Astrict = T["t_A_strict"] + T["t_A_lenient"]
    out.append(f"{'ИТОГО':18}{T['VERIFIED']:>9}{Astrict:>6}{T['t_bare_artnum']:>8}"
               f"{T['t_subelem_tail']:>7}{T['WRONG']:>7}{T['UNVERIF']:>9}{T['total']:>7}")
    tot_int = T["total"]
    out.append(f"\n  ВСЕГО внутренних: {tot_int}")
    out.append(f"  МЕХАНИЧЕСКИ ПРОВЕРЕНО (VERIFIED): {T['VERIFIED']} "
               f"({100*T['VERIFIED']/tot_int:.1f}%)  [было A+C=4027 = {100*4027/tot_int:.1f}%]")
    out.append(f"    из них прежний строгий/послабл (A): {Astrict}")
    out.append(f"    добавлено R1 bare_artnum: {T['t_bare_artnum']}")
    out.append(f"    добавлено R2 subelem_tail: {T['t_subelem_tail']}")
    out.append(f"  WRONG: {T['WRONG']}")
    out.append(f"  TRULY_UNVERIFIABLE: {T['UNVERIF']}  "
               f"(self={T['t_self']} structural={T['t_structural']} generic={T['t_generic']} "
               f"host_subelem={T['t_host_subelem']} repealed={T['t_repealed']} nofrag={T['t_nofrag']})")

    out.append("\n" + "=" * 108)
    out.append(f"WRONG — ВСЕ ({len(wrongs)}) с контекстом:")
    out.append("=" * 108)
    for code, host, vt, href, claim, R, Rn, tag, pv, nx in wrongs:
        out.append(f"  [{code}] ст.{host} | «{vt}» {href} | claim={claim} R={R} Rn={Rn} [{tag}]")
        out.append(f"     …{pv}[{vt}]{nx}…")
    if not wrongs:
        out.append("  (пусто) — механических WRONG нет.")

    random.seed(7)
    samp = random.sample(records_unv, min(40, len(records_unv)))
    out.append("\n" + "=" * 108)
    out.append(f"СЭМПЛ TRULY_UNVERIFIABLE — 40 из {len(records_unv)}")
    out.append("формат: [code] host=ст.X | «текст» #zK [подтип] | R=.. Rn=.. | …пред[текст]след… | якорь→ст.R")
    out.append("=" * 108)
    for i, (code, host, vt, href, R, Rn, tag, pv, nx, tR) in enumerate(samp, 1):
        out.append(f"{i:2}. [{code}] host=ст.{host} | «{vt}» {href} [{tag}] | R={R} Rn={Rn}")
        out.append(f"     …{pv}[{vt}]{nx}…   якорь→ ст.{R}: {tR}")

    REPORT.write_text("\n".join(out) + "\n", encoding="utf-8")
    try:
        sys.stderr.write(f"report -> {REPORT}\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
