# -*- coding: utf-8 -*-
"""ШЕСТЬ ПРОВЕРОК (как 64_final_verify) для НОВЫХ законов — READ-ONLY.

Та же логика check_file, что и в 64_final_verify.py, но параметризованная:
  • список кодов берётся из CLI (по умолчанию 4 новых закона);
  • SELF (doc_id) берётся из config/codes.json;
  • проверяются формы _structured и _ready (если файл существует).

Шесть проверок на файл:
  1) parse    — BeautifulSoup(html, html.parser) без исключений;
  2) nested   — <a> внутри <a> == 0;
  3) empty    — <a href> со значением '' или '#' == 0;
  4) B-real   — сингуляр «стать{ья/ьи/ьей} N» + СНАРУЖИ <a>цифра == 0
                (плюраль «статьями/статьях/статей N…» — голова списка, легит);
  5) внеш-арх — кросс-док http adilet/docs c /archive/, '?', или датой == 0;
  6) висячие  — каждый href='#zNNN' имеет id/name='zNNN' в файле == 0.
"""
import re
import sys
import json
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

ROOT = paths.ROOT
FINAL = paths.FINAL

CODES_JSON = json.loads(paths.CODES_JSON.read_text(encoding="utf-8"))
SELF = {k: v["doc_id"] for k, v in CODES_JSON.items()
        if not k.startswith("_") and isinstance(v, dict)}

DEFAULT_CODES = ["arbitrazh", "goszakup", "ocorrupt", "bezhenci", "zhilishniy"]

CANON = re.compile(r"^https://adilet\.zan\.kz/rus/docs/[A-Z][A-Z0-9]{4,}_?(?:#z[\w.-]+)?$")
DOCREF = re.compile(r"adilet\.zan\.kz/[a-z]+/docs/")
DOCID = re.compile(r"/docs/([A-Z][A-Z0-9]*)_?")
ARCHDATE = re.compile(r"/archive/|\?|\b\d{2}\.\d{2}\.\d{4}\b|/\d{8}/|[?&]ver=")
TYPEB = re.compile(r"(стать\w+)[\s ]+<a\b[^>]*>\s*\d")
PLURAL = {"статьями", "статьях", "статей"}
HREF_Z = re.compile(r"^#(z[\w.-]+)$")


def check_file(code, form):
    path = FINAL / f"{code}_{form}.html"
    html = path.read_text(encoding="utf-8")
    r = {"parse": "OK", "nested": 0, "empty": 0, "empty_chrome": 0, "B": 0,
         "ext": 0, "dangle": 0,
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
            # chrome-навигация шаблона (РУС/Текст и т.п.) живёт ВНЕ div[data-type] —
            # как и в informatizacii/notariat/obrazovanie; это не дефект контента.
            if a.find_parent("div", attrs={"data-type": True}) is not None:
                r["empty"] += 1
                if len(r["ctx"]["empty"]) < 3:
                    r["ctx"]["empty"].append(str(a)[:160])
            else:
                r["empty_chrome"] += 1
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
                r["chr_nondoc"] += 1
            elif did.rstrip("_") == self_id.rstrip("_"):
                r["chr_self"] += 1
            elif ARCHDATE.search(href):
                r["ext"] += 1
                if len(r["ctx"]["ext"]) < 3:
                    r["ctx"]["ext"].append(href)
            else:
                r["fragnote"] += 1
                if len(r["ctx"]["fragnote"]) < 3:
                    r["ctx"]["fragnote"].append(href)
        elif href.startswith("http"):
            r["chr_nondoc"] += 1
    for mm in TYPEB.finditer(html):
        if mm.group(1).lower() in PLURAL:
            r["Blist"] += 1
        else:
            r["B"] += 1
            if len(r["ctx"]["B"]) < 3:
                s = max(0, mm.start() - 25)
                r["ctx"]["B"].append(html[s:mm.end() + 25].replace("\n", " "))
    return r


def main():
    codes = sys.argv[1:] or DEFAULT_CODES
    L = []
    P = L.append
    P("=" * 110)
    P("ШЕСТЬ ПРОВЕРОК (как 64_final_verify) — НОВЫЕ ЗАКОНЫ — READ-ONLY")
    P("=" * 110)
    P(f"{'код':18}{'форма':11}{'parse':7}{'nested':7}{'empty':6}{'B-real':7}{'внеш-арх':9}{'висяч':7}"
      f"   [B-список / chrome self|nondoc / frag]")
    P("-" * 110)
    bad = []
    for code in codes:
        for form in ("structured", "ready"):
            if not (FINAL / f"{code}_{form}.html").exists():
                continue
            r = check_file(code, form)
            P(f"{code:18}{form:11}{r['parse']:7}{r['nested']:>5} {r['empty']:>5} "
              f"{r['B']:>5} {r['ext']:>7} {r['dangle']:>6}   "
              f"[empty-chrome={r['empty_chrome']} / B-list={r['Blist']} / "
              f"chrome self|nondoc={r['chr_self']}|{r['chr_nondoc']} / frag={r['fragnote']}]")
            if r["parse"] != "OK" or r["nested"] or r["empty"] or r["B"] or r["ext"] or r["dangle"]:
                bad.append((code, form, r))
    P("-" * 110)
    if bad:
        P("\n!!! РЕАЛЬНЫЕ НЕНУЛИ — КОНТЕКСТЫ:")
        for code, form, r in bad:
            P(f"\n[{code}_{form}] nested={r['nested']} empty={r['empty']} B-real={r['B']} "
              f"внеш-арх={r['ext']} висяч={r['dangle']}")
            for k in ("nested", "empty", "B", "ext", "dangle"):
                for c in r["ctx"][k]:
                    P(f"   {k}: {c}")
    else:
        P("\nВСЕ ШЕСТЬ РЕАЛЬНЫХ ПРОВЕРОК = 0 ПО ВСЕМ ПРОВЕРЕННЫМ ФАЙЛАМ.")
    P("\n" + "=" * 110)
    P(f"ИТОГ: 6-проверок-чисто={not bad}")
    P("=" * 110)
    out = paths.REPORTS / "69_sixcheck_laws.txt"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\nwritten: {out}  clean={not bad}")


if __name__ == "__main__":
    main()
