# -*- coding: utf-8 -*-
"""Чанкер подзаконных актов. Решение владельца: ЕДИНИЦА = ПУНКТ (функциональный аналог
статьи — именно на пункт ссылаются), схема uid прежняя.

  parent   — пункт: uid = {code}_{zN}, где zN — ГОТОВЫЙ якорь adilet
  сабчанки — при теле > SPLIT_IF: uid = {code}_{zN}_1, _2, … (как в законах)
  kind     — "punkt" | "appendix" (приложения-формы чанкуем, но помечаем, чтобы их
             можно было исключить из индекса так же, как repealed)

Наследует пороги вектор-слоя законов: SPLIT_IF=1800, SUB_MAX=1500.
"""
import io, sys, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from bs4 import BeautifulSoup
from collections import Counter

SPLIT_IF = 1800
SUB_MAX = 1500
RE_SENT = re.compile(r"(?<=[.;:])\s+")


def split_body(text):
    if len(text) <= SPLIT_IF:
        return [text]
    parts, cur = [], ""
    for s in RE_SENT.split(text):
        while len(s) > SUB_MAX:
            cut = s.rfind(" ", 0, SUB_MAX)
            cut = cut if cut > SUB_MAX // 2 else SUB_MAX
            parts.append(s[:cut].strip()); s = s[cut:].strip()
        if cur and len(cur) + len(s) + 1 > SUB_MAX:
            parts.append(cur.strip()); cur = s
        else:
            cur = (cur + " " + s).strip()
    if cur:
        parts.append(cur.strip())
    return [p for p in parts if p]


def chunk_doc(html, struct, code):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style"]):
        t.decompose()
    text_of = {}
    for e in soup.find_all(attrs={"id": True}):
        if re.match(r"^z\d+$", e.get("id")):
            text_of[e["id"]] = re.sub(r"\s+", " ", e.get_text(" ", strip=True))

    out = []
    for b in struct["blocks"]:
        kind = "appendix" if b["kind"] == "appendix" else "punkt"
        for num, anc in b["punkt"].items():
            body = text_of.get(anc, "")
            if not body:
                continue
            uid = f"{code}_{anc}"
            pieces = split_body(body)
            out.append({"uid": uid, "code": code, "kind": kind, "anchor": anc,
                        "block": b["title"][:120], "block_kind": b["kind"],
                        "punkt": num, "text": body, "char_len": len(body),
                        "n_sub": len(pieces) if len(pieces) > 1 else 0})
            if len(pieces) > 1:
                for i, p in enumerate(pieces, 1):
                    out.append({"uid": f"{uid}_{i}", "code": code, "kind": kind + "_sub",
                                "anchor": anc, "parent_uid": uid, "block": b["title"][:120],
                                "block_kind": b["kind"], "punkt": num,
                                "text": p, "char_len": len(p)})
    return out


def main():
    src, structd, outp = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    rows, stats = [], Counter()
    for f in sorted(src.glob("*.html")):
        sp = structd / f"{f.stem}.json"
        if not sp.exists():
            continue
        st = json.loads(sp.read_text(encoding="utf-8"))
        ch = chunk_doc(f.read_text(encoding="utf-8", errors="replace"), st, f.stem)
        rows += ch
        stats["docs"] += 1
    with outp.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    par = [r for r in rows if not r["kind"].endswith("_sub")]
    sub = [r for r in rows if r["kind"].endswith("_sub")]
    app = [r for r in par if r["kind"] == "appendix"]
    print(f"документов: {stats['docs']}")
    print(f"   parent-чанков (пункты) : {len(par)}")
    print(f"      из них appendix     : {len(app)}  (можно исключить из индекса)")
    print(f"      нормативных punkt   : {len(par)-len(app)}")
    print(f"   сабчанков (тело>{SPLIT_IF}) : {len(sub)}")
    print(f"   ВСЕГО строк            : {len(rows)}")
    if par:
        ln = sorted(r["char_len"] for r in par)
        print(f"   медиана длины пункта   : {ln[len(ln)//2]} симв  (макс {ln[-1]})")
    print(f"   уникальных uid         : {len(set(r['uid'] for r in rows))} (должно == всего строк)")


if __name__ == "__main__":
    main()
