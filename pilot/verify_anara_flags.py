# -*- coding: utf-8 -*-
"""Блоки A1+A5: распарсить жёлтые флаги из docx Анары и сверить с _ready.

A1: docx -> maps/anara_pilot_flags.json  (закон+slug, статья, цитата, жёлтый спан,
    класс external|internal, имя акта в кавычках).
A5: для КАЖДОГО флага — жёлтый спан в НОВОМ _ready уже ссылка? CLOSED/OPEN.

Метод сверки (из сырого HTML, не гейтом): выравниваем текст _ready посимвольно с
флагом in_a (внутри <a>?), нормализуем (без пробелов) с сохранением флага, находим
абзац флага, внутри него — жёлтый спан, и проверяем, что «якорная фраза» спана
(имя акта в кавычках / «9-4») ВНУТРИ <a>. CLOSED если да.
"""
import io
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "final"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
QUOTES = "«»\"“”„''"

LAW2SLUG = {
    "Об обеспечении единства измерений": "Z000000053_",
    "О биологической безопасности Республики Казахстан": "Z2200000122",
    "О Службе государственной охраны Республики Казахстан": "Z950002483_",
    "Об автомобильном транспорте": "Z030000476_",
    "О рынке ценных бумаг": "Z030000461_",
}


def nows(s):
    return "".join((s or "").split())


def parse_docx(path):
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    body = ET.fromstring(xml).find(f"{W}body")
    flags = []
    cur_law = cur_slug = cur_art = None
    for p in body.iter(f"{W}p"):
        full = ""
        hl = []
        for r in p.findall(f"{W}r"):
            rpr = r.find(f"{W}rPr")
            yellow = rpr is not None and rpr.find(f"{W}highlight") is not None \
                and rpr.find(f"{W}highlight").get(f"{W}val") == "yellow"
            txt = "".join(t.text or "" for t in r.findall(f"{W}t"))
            full += txt
            if yellow and txt.strip():
                hl.append(txt.strip())
        s = full.strip()
        mlaw = re.match(r"ЗРК\s*[«\"](.+?)[»\"]", s)
        mart = re.match(r"^(Статья\s+[\d-]+)", s)
        if mlaw:
            cur_law = mlaw.group(1).strip()
            cur_slug = LAW2SLUG.get(cur_law)
            cur_art = None
        elif mart:
            cur_art = mart.group(1)
        for h in hl:
            # имя акта в кавычках -> external; иначе «статья 9-4» -> internal
            names = re.findall(r'[«"]([^«»"]{4,120})[»"]', h)
            is_ext = bool(names)
            flags.append({
                "law": cur_law, "slug": cur_slug, "article": cur_art,
                "citation": s[:200], "highlight": h,
                "class": "external" if is_ext else "internal",
                "act_names": names,
            })
    return flags


def char_in_a(html):
    """(нормализ. без пробелов текст, in_a по символу, href по символу)."""
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(["script", "style"]):
        t.decompose()
    chars, ina, href = [], [], []
    for tn in soup.find_all(string=True):
        a = tn.find_parent("a")
        h = a.get("href", "") if a else ""
        for ch in str(tn):
            if not ch.isspace():
                chars.append(ch)
                ina.append(a is not None)
                href.append(h)
    return "".join(chars), ina, href


def verify(flag, ntext, ina, href):
    """Жёлтый спан флага уже ссылка в _ready? Проба:
    external — имя акта в кавычках; internal — «стать*9-4» (НЕ голое «9-4», иначе
    ловится «19-4)» — номер пункта). Считаем ВСЕ вхождения пробы; CLOSED если КАЖДОЕ
    внутри <a> (near-дубликаты цитат — напр. ст.45 и ст.79 идентичны — оба должны гореть)."""
    if flag["class"] == "external":
        probe = nows(flag["act_names"][0])
    else:
        m = re.search(r"стать\w*\s*9-4", flag["highlight"])
        probe = nows(m.group(0)) if m else "стать9-4"
    occ = [i for i in range(len(ntext) - len(probe) + 1) if ntext[i:i + len(probe)] == probe]
    if not occ:
        return "OPEN", "spanned-текст не найден", ""
    linked = sum(1 for i in occ if all(ina[i:i + len(probe)]))
    tgts = sorted({href[i].split("/rus/docs/")[-1] for i in occ if href[i]})
    status = "CLOSED" if linked == len(occ) else ("PARTIAL" if linked else "OPEN")
    return status, f"вхождений {len(occ)}, залинковано {linked}", ";".join(tgts)


def main():
    flags = parse_docx(ROOT / "pilot" / "anara_pilot_remarks.docx")
    caches = {}
    for f in flags:
        s = f["slug"]
        if s and s not in caches:
            caches[s] = char_in_a((FINAL / f"{s}_ready.html").read_text(encoding="utf-8", errors="replace"))
    rows = []
    for f in flags:
        if not f["slug"]:
            f["status"], f["note"], f["target"] = "NO_SLUG", "", ""
        else:
            ntext, ina, href = caches[f["slug"]]
            f["status"], f["note"], f["target"] = verify(f, ntext, ina, href)
        rows.append(f)

    (ROOT / "maps" / "anara_pilot_flags.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    from collections import Counter
    st = Counter(r["status"] for r in rows)
    print(f"флагов: {len(rows)} | " + " ".join(f"{k}={v}" for k, v in st.items()))
    print("=" * 90)
    for r in rows:
        name = (r["act_names"][0] if r["act_names"] else r["highlight"])[:42]
        print(f"  [{r['status']:6}] {r['slug'] or '?':13} {r['article'] or '?':11} "
              f"{r['class']:8} «{name}» -> {r['target']}  {r['note']}")


if __name__ == "__main__":
    main()
