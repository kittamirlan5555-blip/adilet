# -*- coding: utf-8 -*-
"""
ГК Особенная (grazhdanskiy_osob) — закрыть блокер. Аккуратно, бэкап, дифф-гейт.

1) ЛИНК-КАНОН на _structured (string-level, чтобы прочее было байт-в-байт):
   222 контент-самоссылки  href="https://adilet.zan.kz/rus/docs/K990000409_#zN"
   -> href="#zN" (внутренний прыжок). Все якоря #zN уже существуют (0 создаём).
   19 chrome/toolbar self-ссылок (/download,/history,/compare,/info,/links,
   /comments,/k990409_.htm,#,#header,bare) — НЕ статейные отсылки, вне контента,
   в _ready не попадают; НЕ трогаем.

2) _READY (flat) из _structured: unwrap div.document + div[data-type];
   decompose 10 compound -label span-заглушек (дубль текста h3, без якорей).
   head/chrome/контент/ссылки/якоря сохраняются.

ASCII-safe stdout; отчёт в data/reports/42_gkosob_canon_ready.txt
"""
import re, sys, shutil
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data/final"
BACKUP = ROOT / "data/final_backup_GKOSOB"
SP = FINAL / "grazhdanskiy_osob_structured.html"
RP = FINAL / "grazhdanskiy_osob_ready.html"
SELFPAT = re.compile(r'href="https://adilet\.zan\.kz/rus/docs/K990000409_#z(\d+)"')
SELFZ_ANY = re.compile(r'href="https://adilet\.zan\.kz/rus/docs/K990000409_#z\d+"')

log = []
def P(s=""): log.append(s)

def main():
    assert SP.exists(), "structured отсутствует"
    orig = SP.read_text(encoding="utf-8")

    # ---- 0. BACKUP (только оригинал, не перезаписывать) ----
    BACKUP.mkdir(parents=True, exist_ok=True)
    bks = BACKUP / "grazhdanskiy_osob_structured.html"
    if not bks.exists():
        shutil.copy2(SP, bks)
    backup_raw = bks.read_text(encoding="utf-8")
    P(f"BACKUP: {bks}  ({len(backup_raw)} bytes)")

    # ---- 1. LINK-CANON (string-level) ----
    new, n = SELFPAT.subn(r'href="#z\1"', orig)
    P(f"\n[1] LINK-CANON: конвертировано self-URL #zN -> #zN : {n}")
    assert n == 222, f"ожидалось 222, получено {n}"
    # якорей создано: 0 (все цели уже имеют id/name=zN; проверено отдельно)
    ids = set(re.findall(r'id="(z\d+)"', new)) | set(re.findall(r'name="(z\d+)"', new))
    targets = set("z"+m for m in SELFPAT.findall(orig))
    missing = sorted(t for t in targets if t not in ids)
    P(f"    distinct targets: {len(targets)} ; anchors missing: {len(missing)} {missing}")
    assert not missing, "есть цели без якоря — нужно создавать"
    P(f"    якорей создано: 0")
    # diff-gate: new == (backup с тем же sub) -> значит изменились ТОЛЬКО эти 222 href
    rebuilt, n2 = SELFPAT.subn(r'href="#z\1"', backup_raw)
    assert rebuilt == new and n2 == 222, "diff-gate: расхождение помимо 222 href"
    # selfURL(#z) в _structured теперь 0
    assert len(SELFZ_ANY.findall(new)) == 0, "остались self-#z URL"
    P(f"    diff-gate _structured: прочее байт-в-байт OK ; selfURL(#z)=0 OK")
    P(f"    bytes: {len(orig)} -> {len(new)}  (delta {len(new)-len(orig)} = -42*222={-42*222})")
    SP.write_text(new, encoding="utf-8")

    # ---- 2. GENERATE _ready (flatten) ----
    soup = BeautifulSoup(new, "html.parser")
    doc = soup.find("div", class_="document")
    assert doc is not None, "div.document не найден"
    # decompose label-stubs (compound virtual parts; дубликат текста h3, без якорей)
    spans = soup.find_all("span", class_=lambda c: c and any(x.endswith("-label") for x in (c if isinstance(c,list) else [c])))
    nsp = 0
    for s in spans:
        assert not (s.get("id") or s.find(attrs={"id": True}) or s.find(attrs={"name": True})), "label-span с якорем!"
        s.decompose(); nsp += 1
    # unwrap hierarchy wrappers: сначала вложенные data-type, затем document
    nwrap = 0
    for d in soup.find_all("div", attrs={"data-type": True}):
        d.unwrap(); nwrap += 1
    doc.unwrap()
    P(f"\n[2] FLATTEN -> _ready: unwrap div.document=1, div[data-type]={nwrap}, decompose label-span={nsp}")
    RP.write_text(str(soup), encoding="utf-8")
    P(f"    written: {RP}  ({RP.stat().st_size} bytes)")

    # ---- 3. SELF-VERIFY _ready ----
    rsoup = BeautifulSoup(RP.read_text(encoding="utf-8"), "html.parser")
    assert rsoup.find("div", class_="document") is None, "div.document остался в _ready"
    assert not rsoup.find_all("div", attrs={"data-type": True}), "data-type остался в _ready"
    assert not rsoup.find_all("span", class_=lambda c: c and any(x.endswith("-label") for x in (c if isinstance(c,list) else [c]))), "label-span остался"
    rtext = RP.read_text(encoding="utf-8")
    n_frag = len(re.findall(r'href="#z\d+"', rtext))
    n_selfz = len(SELFZ_ANY.findall(rtext))
    n_anchor = len(set(re.findall(r'id="z\d+"', rtext)) | set(re.findall(r'name="z\d+"', rtext)))
    has_head = bool(rsoup.find("head")); has_article = bool(rsoup.find("article"))
    P(f"    _ready: <head>={has_head} <article>={has_article} ; "
      f"#z internal links={n_frag} ; self-#z URL={n_selfz} ; distinct anchors={n_anchor}")
    assert n_selfz == 0 and n_frag >= 222 and has_head and has_article

    P("\nГОТОВО: link-canon применён к _structured; _ready сгенерирован. "
      "Дальше: divergence (29), audit cov_real, дифф-гейт.")
    out = "\n".join(log) + "\n"
    (ROOT/"data/reports/42_gkosob_canon_ready.txt").write_text(out, encoding="utf-8")
    sys.stdout.write(out.encode("ascii","replace").decode("ascii"))

if __name__ == "__main__":
    main()
