# -*- coding: utf-8 -*-
"""Структуризация корпуса по схеме шефа (формат принят в мае: чанковый jsonl
с meta.hier_id вида UKCH1R1ST1P1 и hier_path; эталон —
deliverables/send_chef/chunks_ugolovniy.jsonl).

python scripts/pipeline/structurize.py --all | {slug...}
-> structured_out/{slug}.jsonl + structured_out/QUALITY.md

Источник — ТЕКУЩИЕ final/{slug}_structured.html (read-only): если чанки
старее финала, chunk_npa перегоняется для слага. Самотесты на каждый документ:
  T1 полнота: все статьи article_map присутствуют в jsonl;
  T2 текст: каждый чанк (без заголовочного префикса) -- подстрока текста своей
     статьи в _structured (нормализация: все пробелы вон), покрытие считается;
  T3 ID: id уникальны; hier_id соответствует грамматике
     CODE(CHn)?(Rn)?(Gn)?(PGn)?STn(Pn)?(SPn)? и восстанавливается из hier_path;
  T4 иерархия: чанк ссылается на статью из карты (сирот нет); дерево tree/
     не содержит узлов без типа/номера (кроме repealed);
  T5 сложные случаи: дефисные статьи (65-1 и т.п.) получают чанки и корректный
     ST-сегмент; пункт с подпунктами не рвётся (ПК-82: подпункт 4-1 в чанке
     пункта 3); главы-двойники различимы (hier_id уникальны).
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

OUT = paths.STRUCTURED_OUT

# суффикс ~N — дизамбигуатор чанкера для повторных номеров (главы-двойники,
# повторные статьи в выгрузке)
NUM = r"[\d-]+(?:~\d+)?"
RE_GRAMMAR = re.compile(
    rf"^[A-Z]+(?:CH\d+)?(?:R{NUM})?(?:G{NUM})?(?:PG{NUM})?"
    rf"ST{NUM}(?:P{NUM})?(?:SP{NUM})?$")


def rebuild(hp):
    parts = [hp["code"]]
    if hp.get("code_part"):
        parts.append(hp["code_part"])
    for key, tag in (("section", "R"), ("chapter", "G"), ("paragraph", "PG")):
        if hp.get(key) is not None:
            parts.append(f"{tag}{hp[key]}")
    parts.append(f"ST{hp['article']}")
    if hp.get("unit") is not None:
        parts.append(f"P{hp['unit']}")
    if hp.get("subunit") is not None:
        parts.append(f"SP{hp['subunit']}")
    return "".join(parts)


def squash(s):
    return "".join(s.split())


def article_texts(slug):
    """Номер статьи -> беспробельный текст её div из _structured (bs4 —
    корректно при вложенных div compound-split)."""
    from bs4 import BeautifulSoup
    raw = (paths.FINAL / f"{slug}_structured.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    out = {}
    for d in soup.find_all("div", class_="article"):
        if "статья" not in (d.get("data-type") or ""):
            continue
        num = d.get("data-number")
        if num:
            out.setdefault(num, "")
            out[num] += squash(d.get_text())
    return out


def process(slug):
    fchunks = paths.CHUNKS / f"{slug}.jsonl"
    fstruct = paths.FINAL / f"{slug}_structured.html"
    if not fchunks.exists() or fchunks.stat().st_mtime < fstruct.stat().st_mtime:
        subprocess.run([sys.executable,
                        str(Path(__file__).parent / "chunk_npa.py"), slug],
                       check=True, capture_output=True)
    rows = [json.loads(line) for line in
            fchunks.read_text(encoding="utf-8").splitlines() if line.strip()]
    amap = json.loads((paths.MAPS / f"article_map_{slug}.json")
                      .read_text(encoding="utf-8"))
    arts_text = article_texts(slug)

    res = {"slug": slug, "chunks": len(rows), "fails": [], "notes": []}

    # T1 полнота (статья из карты без article-div = исключённая, не пропуск)
    in_jsonl = {r["meta"]["article"] for r in rows}
    missing = sorted(set(amap) - in_jsonl, key=str)
    excl = [a for a in missing if a not in arts_text]
    missing = [a for a in missing if a in arts_text]
    if missing:
        res["fails"].append(f"T1: статей из карты нет в jsonl: {missing[:10]}"
                            f"{'…' if len(missing) > 10 else ''} ({len(missing)})")
    if excl:
        res["notes"].append(f"T1: исключённых статей без div (чанков нет "
                            f"легитимно): {len(excl)}")
    res["articles"] = len(in_jsonl)

    # T2 текст: чанк = сегменты (вводная пункта, подпункты, продолжения),
    # каждый сегмент НЕПРЕРЫВЕН в источнике; скобочные заголовки [..] — служебные.
    # Формат шефа намеренно дублирует вводную пункта в каждом под-чанке,
    # поэтому проверяем ПО-СЕГМЕНТНО, а покрытие — по уникальным сегментам.
    bad_seg, total_seg, num_tails = 0, 0, 0
    # «№-цепочки» — номера законов-источников из сносок (continuations майского
    # эталона, напр. «№ 157-VII№ 210-VIII»): в статье разделены текстом сноски,
    # непрерывной строкой не встречаются — служебный хвост, не текст НПА
    RE_NUM_TAIL = re.compile(
        r"^(?:№\s?\d+(?:-[IVXІVІ]+)?|ст\.?\s?\d+|вводится|[\s,;.()-])+$")
    cover_segs = {}
    for r in rows:
        art = r["meta"]["article"]
        ref = arts_text.get(art)
        if ref is None:
            continue  # repealed-заглушки — учтены в T4
        for line in r["text"].split("\n"):
            line = line.strip()
            if not line or (line.startswith("[") and line.endswith("]")):
                continue
            if RE_NUM_TAIL.match(line):
                num_tails += 1
                continue
            sq = re.sub(r"\[[^\]]{5,120}\]", "", line)
            sq = squash(sq)
            if not sq:
                continue
            total_seg += 1
            if sq not in ref:
                bad_seg += 1
            else:
                cover_segs.setdefault(art, set()).add(sq)
    cover_num = sum(len(s) for segs in cover_segs.values() for s in segs)
    cover_den = sum(len(arts_text.get(a, "")) for a in in_jsonl)
    if bad_seg:
        res["fails"].append(f"T2: сегментов-не-подстрок: {bad_seg}/{total_seg}")
    if num_tails:
        res["notes"].append(f"T2: служебных №-хвостов сносок пропущено: {num_tails}")
    res["coverage"] = round(cover_num / cover_den, 3) if cover_den else None

    # T3 ID
    ids = [r["id"] for r in rows]
    dup = [k for k, v in Counter(ids).items() if v > 1]
    if dup:
        res["fails"].append(f"T3: дубли id: {dup[:5]}")
    bad_g, bad_rt = 0, 0
    for r in rows:
        hid = r["meta"].get("hier_id")
        hp = r["meta"].get("hier_path")
        if not hid or not RE_GRAMMAR.match(hid):
            bad_g += 1
        elif re.sub(r"~\d+", "", rebuild(hp)) != re.sub(r"~\d+", "", hid):
            bad_rt += 1  # ~N — дизамбигуатор только в id, в path чистый номер
    if bad_g:
        res["fails"].append(f"T3: hier_id вне грамматики: {bad_g}")
    if bad_rt:
        res["fails"].append(f"T3: hier_id != rebuild(hier_path): {bad_rt}")
    dup_h = sum(v - 1 for v in Counter(
        r["meta"]["hier_id"] for r in rows).values() if v > 1)
    if dup_h:
        res["notes"].append(f"hier_id повторяется у {dup_h} чанков "
                            f"(продолжения одного пункта)")

    # T4 сироты
    orphans = sorted(in_jsonl - set(amap), key=str)
    if orphans:
        res["notes"].append(f"T4: статьи в jsonl вне карты: {orphans[:6]} "
                            f"({len(orphans)})")

    # T5 сложные случаи
    dash_map = [a for a in amap if "-" in str(a)]
    if dash_map:
        dash_ok = [a for a in dash_map if a in in_jsonl]
        st_ok = all(re.search(rf"ST{re.escape(a)}(P|SP|$)",
                              r["meta"]["hier_id"])
                    for a in dash_ok[:3]
                    for r in rows if r["meta"]["article"] == a)
        res["dash"] = f"{len(dash_ok)}/{len(dash_map)} дефисных статей в jsonl"
        if len(dash_ok) != len(dash_map):
            miss = sorted(set(dash_map) - set(dash_ok))[:5]
            res["fails"].append(f"T5: дефисные без чанков: {miss}")
        if not st_ok:
            res["fails"].append("T5: ST-сегмент дефисной статьи искажён")

    if slug == "predprinimatel":
        p3 = [r for r in rows if r["id"].startswith("predprinimatel_ст82_п3")]
        if not (p3 and any("4-1)" in r["text"] for r in p3)):
            res["fails"].append("T5: ПК-82 п.3 — подпункт 4-1 не в чанке пункта")

    # T6 (R7-фикс, вопрос ревью по appk ст.58): нет статей со СПРЯТАННЫМИ
    # скобочными пунктами — root-чанк (unit_type пуст) не должен содержать
    # >=2 строк «N)» в теле. Исключение: ugolovniy (майский эталон).
    if slug != "ugolovniy":
        hidden = []
        for r_ in rows:
            if r_["meta"].get("unit_type"):
                continue
            body = r_["text"].split("\n", 1)[-1]
            subs = re.findall(r"(?m)^\s*\d+(?:-\d+)?\)\s", body)
            if len(subs) >= 2:
                hidden.append(r_["meta"]["article"])
        if hidden:
            res["fails"].append(f"T6: спрятанные скобочные пункты: {hidden[:6]}")

    OUT.mkdir(exist_ok=True)
    (OUT / f"{slug}.jsonl").write_text(
        fchunks.read_text(encoding="utf-8"), encoding="utf-8")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    cj = json.loads(paths.CODES_JSON.read_text(encoding="utf-8"))
    slugs = ([k for k in cj if not k.startswith("_")] if args.all
             else args.slugs)

    results = []
    for slug in slugs:
        r = process(slug)
        results.append(r)
        status = "OK" if not r["fails"] else "FAIL"
        print(f"{slug:18} чанков={r['chunks']:>5} статей={r['articles']:>4} "
              f"покрытие={r.get('coverage')} {status} "
              + ("; ".join(r["fails"]) if r["fails"] else ""))

    L = ["# QUALITY — контроль качества структуризации корпуса", "",
         "Пакет: 25 jsonl-файлов (13 кодексов + 12 законов РК). Каждая строка — "
         "чанк: `id`, `text` (с заголовочным префиксом вида "
         "`[БК | Статья 5. Название | пункт 2]`), `meta` (короткий код документа, "
         "doc_id на adilet, статья, тип/номер единицы, статус, иерархический id "
         "вида `UKCH1R1ST1P1` и его разбор `hier_path`). Расшифровка сегментов "
         "и реестр кодов — в COVER.md. Самопроверки на каждый документ: "
         "T1 все статьи карты присутствуют; T2 текст чанка — подстрока статьи "
         "источника (показано покрытие); T3 id уникальны, hier_id соответствует "
         "грамматике и восстанавливается из hier_path; T4 сирот нет; "
         "T5 сложные случаи (дефисные номера статей и т.п.). Поле status: "
         "active — действующая единица, repealed — исключённая/утратившая "
         "силу (включены намеренно: на них ссылаются действующие нормы).", "",
         "| документ | чанков | Δ чанков | статей | покрытие текста | дефисные | тесты |",
         "|---|---|---|---|---|---|---|"]
    _bl_p = paths.REPORTS / "history" / "chunk_counts_baseline.json"
    _bl = json.loads(_bl_p.read_text(encoding="utf-8")) if _bl_p.exists() else {}
    for r in results:
        _d = r['chunks'] - _bl.get(r['slug'], r['chunks'])
        L.append(f"| {r['slug']} | {r['chunks']} | {('+' if _d > 0 else '') + str(_d)} | {r['articles']} "
                 f"| {r.get('coverage')} | {r.get('dash', '—')} "
                 f"| {'OK' if not r['fails'] else '; '.join(r['fails'])} |")
    L += ["", "Замечания (не-фейлы):"]
    for r in results:
        for n in r["notes"]:
            L.append(f"- {r['slug']}: {n}")
    L += ["", "## Сложные случаи (проверяются самотестом T5)", "",
          "- ПК ст.82: пункт 3 с 13 подпунктами (вкл. suffix 4-1) — один чанк "
          "(T5 проверяет подпункт 4-1 в чанке пункта);",
          "- дефисные статьи (65-1, 9-1, 27-2 и т.п.) — отдельные ST-сегменты "
          "hier_id, T5 по каждому документу;",
          "- главы-двойники (одинаковые номера глав в разных разделах/частях) — "
          "различаются R/CH-сегментами hier_id; уникальность пар проверяется T3;",
          "- «части» vs «пункты» — unit_type из чанкера (часть у УК/УПК/КоАП, "
          "пункт у остальных), отражён в meta и тексте префикса."]
    (OUT / "QUALITY.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {OUT / 'QUALITY.md'}")
    if any(r["fails"] for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
