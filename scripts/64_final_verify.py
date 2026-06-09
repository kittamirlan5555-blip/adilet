# -*- coding: utf-8 -*-
"""ФИНАЛЬНАЯ ПРОВЕРКА всех 13 кодов, обе формы — READ-ONLY (ничего не пишет в корпус).

Шесть проверок на файл (chrome-навигация = шаблон страницы, выносится отдельно):
  1) parse        — BeautifulSoup(html, html.parser) без исключений;
  2) nested       — <a> внутри <a> (a.find_parent('a')) == 0;
  3) empty        — <a> С атрибутом href со значением '' или '#' == 0
                    (анкер-цели <a id name> без href НЕ считаются);
  4) B-остаток    — TYPE B (РЕАЛЬНЫЙ): СИНГУЛЯР «стать{ья/ьи/ьей} N» + СНАРУЖИ
                    <a>цифра. Плюраль «статьями/статьях/статей N, M, …» —
                    это голова списка (слово управляет НЕСКОЛЬКИМИ ссылками),
                    легитимна, в дефект НЕ идёт (считается отдельно);
  5) внеш-арх     — КРОСС-док http на adilet/docs с /archive/, '?', или датой
                    == 0. Канон https://adilet.zan.kz/rus/docs/{ID}[#z..] — OK;
                    self-док шаблон-навигация (eng/kaz/#header/comments/compare/
                    file_*.htm) и не-док chrome (rss/advertising/soc) — отдельно;
                    нестандартный фрагмент кросс-дока (#8 вместо #z8) — отдельная
                    заметка (наследие, не архив/дата);
  6) висячие      — каждый href='#zNNN' имеет id/name='zNNN' в файле == 0.

Плюс: 3 фикса (raw count + Δ vs backup, обе формы), и get_text-заморозка
(для бэкап-кодов get_text(_structured/_ready) неизменен vs
final_backup_ANARA_RECHECK => чанки, собранные из _structured, консистентны).
"""
import re
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
BK = ROOT / "data" / "final_backup_ANARA_RECHECK"

CODES = ["nalog", "trudovoy", "grazhdanskiy", "grazhdanskiy_osob", "predprinimatel",
         "socialnyy", "ekologicheskiy", "zemelnyy", "upk", "koap", "appk",
         "byudzhet", "ugolovniy"]

SELF = {
    "nalog": "K2500000214", "trudovoy": "K1500000414", "grazhdanskiy": "K940001000",
    "grazhdanskiy_osob": "K990000409", "predprinimatel": "K1500000375",
    "socialnyy": "K2300000224", "ekologicheskiy": "K2100000400",
    "zemelnyy": "K030000442", "upk": "K1400000231", "koap": "K1400000235",
    "appk": "K2000000350", "byudzhet": "K2500000171", "ugolovniy": "K1400000226",
}

CANON = re.compile(r"^https://adilet\.zan\.kz/rus/docs/[A-Z][A-Z0-9]{4,}_?(?:#z[\w.-]+)?$")
DOCREF = re.compile(r"adilet\.zan\.kz/[a-z]+/docs/")
DOCID = re.compile(r"/docs/([A-Z][A-Z0-9]*)_?")          # требует ВЕРХНИЙ регистр (rss -> None)
ARCHDATE = re.compile(r"/archive/|\?|\b\d{2}\.\d{2}\.\d{4}\b|/\d{8}/|[?&]ver=")
TYPEB = re.compile(r"(стать\w+)[\s ]+<a\b[^>]*>\s*\d")
PLURAL = {"статьями", "статьях", "статей"}
HREF_Z = re.compile(r"^#(z[\w.-]+)$")


def check_file(code, form):
    html = (FINAL / f"{code}_{form}.html").read_text(encoding="utf-8")
    r = {"parse": "OK", "nested": 0, "empty": 0, "B": 0, "ext": 0, "dangle": 0,
         "Blist": 0, "chr_self": 0, "chr_nondoc": 0, "fragnote": 0,
         "ctx": {"nested": [], "empty": [], "B": [], "ext": [], "dangle": [], "fragnote": []}}
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        r["parse"] = f"FAIL:{e}"
        return r
    ids = set()
    for t in soup.find_all(attrs={"id": True}):
        ids.add(t["id"])
    for t in soup.find_all(attrs={"name": True}):
        ids.add(t["name"])
    self_id = SELF[code]
    for a in soup.find_all("a"):
        if a.find_parent("a") is not None:
            r["nested"] += 1
            if len(r["ctx"]["nested"]) < 3:
                r["ctx"]["nested"].append(str(a.parent)[:200])
        if not a.has_attr("href"):
            continue
        href = a["href"].strip()
        if href in ("", "#"):
            r["empty"] += 1
            if len(r["ctx"]["empty"]) < 3:
                r["ctx"]["empty"].append(str(a)[:160])
            continue
        m = HREF_Z.match(href)
        if m:
            if m.group(1) not in ids:
                r["dangle"] += 1
                if len(r["ctx"]["dangle"]) < 3:
                    r["ctx"]["dangle"].append(href + " :: " + a.get_text()[:60])
            continue
        if href.startswith("http") and DOCREF.search(href):
            if CANON.match(href):
                continue
            did = DOCID.search(href)
            did = did.group(1) if did else ""
            if not did:
                r["chr_nondoc"] += 1                     # /docs/rss и т.п.
            elif did.rstrip("_") == self_id.rstrip("_"):
                r["chr_self"] += 1                        # self шаблон-навигация
            elif ARCHDATE.search(href):
                r["ext"] += 1                             # РЕАЛЬНО архив/дата кросс-док
                if len(r["ctx"]["ext"]) < 3:
                    r["ctx"]["ext"].append(href)
            else:
                r["fragnote"] += 1                        # кросс-док, нестанд. фрагмент
                if len(r["ctx"]["fragnote"]) < 3:
                    r["ctx"]["fragnote"].append(href)
        elif href.startswith("http"):
            r["chr_nondoc"] += 1                          # advertising/soc/law.gov.kz
    # TYPE B: сингуляр (дефект) vs плюраль-список (легит)
    for mm in TYPEB.finditer(html):
        if mm.group(1).lower() in PLURAL:
            r["Blist"] += 1
        else:
            r["B"] += 1
            if len(r["ctx"]["B"]) < 3:
                s = max(0, mm.start() - 25)
                r["ctx"]["B"].append(html[s:mm.end() + 25].replace("\n", " "))
    return r


def gettext(p):
    return BeautifulSoup(Path(p).read_text(encoding="utf-8"), "html.parser").get_text()


def main():
    L = []
    P = L.append
    P("=" * 110)
    P("ФИНАЛЬНАЯ ПРОВЕРКА 13 КОДОВ × 2 ФОРМЫ — READ-ONLY  (chrome = шаблон, вынесен отдельно)")
    P("=" * 110)
    P(f"{'код':18}{'форма':11}{'parse':7}{'nested':7}{'empty':6}{'B-real':7}{'внеш-арх':9}{'висяч':7}"
      f"   [B-список / chrome self|nondoc / frag]")
    P("-" * 110)
    bad = []
    for code in CODES:
        for form in ("structured", "ready"):
            r = check_file(code, form)
            P(f"{code:18}{form:11}{r['parse']:7}{r['nested']:>5} {r['empty']:>5} "
              f"{r['B']:>5} {r['ext']:>7} {r['dangle']:>6}   "
              f"[{r['Blist']} / {r['chr_self']}|{r['chr_nondoc']} / {r['fragnote']}]")
            if r["parse"] != "OK" or r["nested"] or r["empty"] or r["B"] or r["ext"] or r["dangle"]:
                bad.append((code, form, r))
    P("-" * 110)

    if bad:
        P("\n!!! РЕАЛЬНЫЕ НЕНУЛИ — КОНТЕКСТЫ:")
        for code, form, r in bad:
            P(f"\n[{code}_{form}] nested={r['nested']} empty={r['empty']} B-real={r['B']} внеш-арх={r['ext']} висяч={r['dangle']}")
            for k in ("nested", "empty", "B", "ext", "dangle"):
                for c in r["ctx"][k]:
                    P(f"   {k}: {c}")
    else:
        P("\nВСЕ ШЕСТЬ РЕАЛЬНЫХ ПРОВЕРОК = 0 ПО ВСЕМ 26 ФАЙЛАМ.")

    # информационная заметка по fragnote (наследие, не архив/дата)
    frag = [(c, f, check_file(c, f)) for c in CODES for f in ("structured", "ready")]
    frag = [(c, f, r) for (c, f, r) in frag if r["fragnote"]]
    if frag:
        P("\n(инфо) КРОСС-ДОК НЕСТАНДАРТНЫЙ ФРАГМЕНТ (наследие, не архив/дата, не дефект):")
        seen = set()
        for c, f, r in frag:
            for u in r["ctx"]["fragnote"]:
                if u not in seen:
                    seen.add(u)
                    P(f"   [{c}] {u}")

    P("\n" + "=" * 110)
    P("3 ПОСЛЕДНИХ ФИКСА — current vs backup (Δ = добавлено в этом проходе):")
    P("=" * 110)
    fixes = [
        ("upk", re.compile(r'<a href="[^"]*K1400000226#z3002">стать[а-я]+ 3'), "UK ст.3"),
        ("koap", re.compile(r'<a href="#z242">Особенной част'), "Особенная часть"),
        ("nalog", re.compile(r'<a href="#z6312">подпунктом 4\)</a>'), "подпункт 4) ст.363"),
    ]
    for code, rx, lab in fixes:
        line = f"  {code:8} ({lab})"
        for form in ("structured", "ready"):
            cur = len(rx.findall((FINAL / f"{code}_{form}.html").read_text(encoding="utf-8")))
            bp = BK / f"{code}_{form}.html"
            old = len(rx.findall(bp.read_text(encoding="utf-8"))) if bp.exists() else None
            d = f"Δ+{cur - old}" if old is not None else "Δ?(нет backup)"
            line += f"  {form}: {cur}"
            if old is not None:
                line += f" (было {old}, {d})"
        P(line)

    P("\n" + "=" * 110)
    P("GET_TEXT-ЗАМОРОЗКА (чанки строятся из _structured; backup = срез до прохода):")
    P("=" * 110)
    gt_ok = True
    for code in CODES:
        bks, bkr = BK / f"{code}_structured.html", BK / f"{code}_ready.html"
        if bks.exists():
            fs = gettext(bks) == gettext(FINAL / f"{code}_structured.html")
            fr = gettext(bkr) == gettext(FINAL / f"{code}_ready.html") if bkr.exists() else True
            gt_ok = gt_ok and fs and fr
            P(f"  {code:18} vs backup: _structured={'НЕИЗМЕНЕН' if fs else 'ИЗМЕНЁН!'}  "
              f"_ready={'НЕИЗМЕНЕН' if fr else 'ИЗМЕНЁН!'}")
        else:
            P(f"  {code:18} в этом проходе НЕ правился (нет backup) => чанки консистентны by-construction")

    P("\n" + "=" * 110)
    P(f"ИТОГ:  6-проверок-чисто={not bad}  |  get_text-заморозка(backup-коды)={gt_ok}")
    P("=" * 110)
    out = ROOT / "data/reports/64_final_verify.txt"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"written: {out}  clean={not bad}  gettext_frozen={gt_ok}")


if __name__ == "__main__":
    main()
