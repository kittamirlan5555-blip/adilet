# -*- coding: utf-8 -*-
"""
КРАШ-УСТОЙЧИВЫЙ БАТЧ-ДРАЙВЕР для пилота (100 НПА).

Зачем: штатный scripts/pipeline/pipeline.py делает sys.exit на ПЕРВОЙ же ошибке —
для батча это смерть (один кривой закон убивает весь прогон). Этот драйвер гоняет
каждый док ИЗОЛИРОВАННО (subprocess + try), на падении помечает статус и ЕДЕТ ДАЛЬШЕ.
Кривые/чужого-формата доки уходят в КАРАНТИН на gate-0 (preflight), а не валят батч.

Шаги на каждый док:
    0. preflight  — есть article-сигнатуры? (КРИВО -> карантин, тяжёлые шаги пропускаем)
    1. structure  — 11_structure_html.py            -> final/{slug}_structured.html
    2. links      — pipeline.py {slug}              (01->07->10->02->03->06->13->76)
    3. gate       — 69_sixcheck_laws.py {slug}      (read-only, 6 проверок)
    4. chunk      — chunk_npa.py {slug}             -> derived/tree + derived/chunks
    (ВЕКТОР-СЛОЙ НЕ ТРОГАЕМ — это Фаза B, GPU/DeepSeek, отдельно и потом.)

ЗАПУСК:
    python pilot/02_batch_run.py --all                 # все pilot-доки из codes.json (source/ на диске)
    python pilot/02_batch_run.py Z1500000418 Z070000319_   # конкретные slug
    python pilot/02_batch_run.py --all --steps pre,struct,gate   # быстрый прогон без внешних ссылок
    python pilot/02_batch_run.py --all --timeout 600   # потолок секунд на шаг

ВЫХОД:
    reports/pilot/pilot_report.md   — на каждый док статус + сводка (X чистых / Y карантин / Z упало)
    reports/pilot/pilot_report.csv
"""
import argparse
import csv
import importlib.util
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
FINAL = ROOT / "final"
CHUNKS = ROOT / "derived" / "chunks"
PIPE = ROOT / "scripts" / "pipeline"
AUDIT = ROOT / "scripts" / "audit"
CODES_JSON = ROOT / "maps" / "codes.json"
OUT = ROOT / "reports" / "pilot"
FINAL.mkdir(exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

from bs4 import BeautifulSoup
# переиспользуем настоящий build_article_map (как preflight) — единый критерий «статей»
_spec = importlib.util.spec_from_file_location("amap01", PIPE / "01_build_article_map.py")
_amap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_amap)

RE_ZNAME = re.compile(r"^z\d+")
RE_ART_B = re.compile(r"^Статья\s+\d+(?:-\d+)?\s*\.")
PY = sys.executable
ALL_STEPS = ["pre", "struct", "links", "canon", "gate", "chunk"]


def load_codes() -> dict:
    return {k: v for k, v in json.loads(CODES_JSON.read_text(encoding="utf-8")).items()
            if not k.startswith("_") and isinstance(v, dict)}


def corpus_keys() -> set:
    """Ключи ЗАКОММИЧЕННОГО corpus codes.json (HEAD) — их пилот-прогон трогать НЕ должен
    (перезапись их final/*_ready|_structured.html = порча курируемого корпуса). Пилотные
    НГР добавляются в codes.json на лету и в HEAD отсутствуют, поэтому сюда не попадают."""
    try:
        r = subprocess.run(["git", "show", "HEAD:maps/codes.json"], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8")
        if r.returncode == 0:
            return {k for k in json.loads(r.stdout) if not k.startswith("_")}
    except Exception:
        pass
    return set()


def preflight(slug: str) -> dict:
    """gate-0: статей(article_map) + сигнатуры. КРИВО -> карантин."""
    p = SOURCE / f"{slug}.html"
    if not p.exists():
        return {"ok": False, "why": "нет source", "n": 0}
    soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
    for t in soup.find_all(["script", "style", "template"]):
        t.decompose()
    a_name = sum(1 for a in soup.find_all("a", attrs={"name": True}) if RE_ZNAME.match(a.get("name", "")))
    h3_id = sum(1 for h in soup.find_all("h3", id=True) if RE_ZNAME.match(h.get("id", "")))
    b_art = sum(1 for b in soup.find_all("b") if RE_ART_B.match(b.get_text(" ", strip=True)))
    try:
        n = len(_amap.build_article_map(str(p)))
    except Exception as e:
        return {"ok": False, "why": f"map-краш: {type(e).__name__}", "n": 0}
    sig = a_name + h3_id + b_art
    head = max(b_art, h3_id)
    cover_ok = (head == 0) or (n >= 0.7 * head)
    if n == 0:
        return {"ok": False, "why": "статей=0", "n": 0}
    if sig == 0:
        return {"ok": False, "why": "нет сигнатур", "n": n}
    if not cover_ok:
        return {"ok": False, "why": f"map {n}<<загол {head}", "n": n}
    return {"ok": True, "why": "", "n": n}


def run(cmd: list, timeout: int) -> tuple[bool, str]:
    """subprocess с потолком времени; НИКОГДА не роняет драйвер."""
    try:
        r = subprocess.run(cmd, cwd=ROOT, timeout=timeout,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            return True, (r.stdout or "").strip().splitlines()[-1:] and (r.stdout.strip().splitlines()[-1]) or ""
        tail = (r.stderr or r.stdout or "").strip().splitlines()
        return False, (tail[-1] if tail else f"rc={r.returncode}")
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT>{timeout}s"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def gate_pass(slug: str, timeout: int) -> tuple[str, str]:
    """69_sixcheck_laws: вердикт по ЯВНОМУ clean=. Возвращаем (GREEN/RED/ERR, нота).

    69 всегда завершается rc=0 и печатает ПОСЛЕДНЕЙ строкой
    'written: … clean=True|False' (итог 6 проверок). Раньше gate_pass искал
    в этой строке слова-провалы — их там нет никогда, поэтому гейт был no-op
    (всегда GREEN, GATE_RED недостижим). Теперь парсим clean= напрямую."""
    ok, msg = run([PY, str(AUDIT / "69_sixcheck_laws.py"), slug], timeout)
    if not ok:
        return "ERR", msg
    low = msg.lower()
    if "clean=false" in low:
        return "RED", msg[:60]
    if "clean=true" in low:
        return "GREEN", msg[:60]
    # неожиданный формат вывода 69 — не выдаём ложный GREEN
    return "ERR", msg[:60]


def struct_article_count(slug: str) -> int:
    """Число <div class=article data-type=…статья…> в _structured (как verify_pilot).
    -1 если файла нет."""
    p = FINAL / f"{slug}_structured.html"
    if not p.exists():
        return -1
    soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
    return sum(1 for a in soup.find_all("div", class_="article")
               if "статья" in (a.get("data-type") or ""))


def chunk_article_stats(slug: str) -> tuple:
    """(число чанков, число РАЗНЫХ статей в чанках). (0,0) если файла нет."""
    p = CHUNKS / f"{slug}.jsonl"
    if not p.exists():
        return 0, 0
    arts, n = set(), 0
    for ln in p.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        c = json.loads(ln)
        n += 1
        arts.add(str(c.get("meta", {}).get("article")))
    return n, len(arts)


def process(slug: str, doc_id: str, steps: list, timeout: int) -> dict:
    row = {"slug": slug, "doc_id": doc_id, "n": 0, "pre": "-", "struct": "-",
           "links": "-", "canon": "-", "gate": "-", "chunk": "-", "sa": "-", "ca": "-",
           "status": "", "note": ""}
    t0 = time.time()

    # 0 PREFLIGHT
    if "pre" in steps:
        pf = preflight(slug)
        row["n"] = pf["n"]
        if not pf["ok"]:
            row["pre"] = "КРИВО"
            row["status"] = "QUARANTINE"
            row["note"] = pf["why"]
            return row
        row["pre"] = "ok"

    # 1 STRUCTURE
    if "struct" in steps:
        out = FINAL / f"{slug}_structured.html"
        ok, msg = run([PY, str(PIPE / "11_structure_html.py"),
                       "--input", str(SOURCE / f"{slug}.html"), "--output", str(out)], timeout)
        row["struct"] = "ok" if ok else "FAIL"
        if not ok:
            row["status"] = "STRUCT_FAIL"
            row["note"] = msg
            return row

    # 2 LINKS (штатный оркестратор, изолированно)
    if "links" in steps:
        ok, msg = run([PY, str(PIPE / "pipeline.py"), slug], timeout)
        row["links"] = "ok" if ok else "FAIL"
        if not ok:
            row["status"] = "PIPE_FAIL"
            row["note"] = msg
            # не выходим — гейт/чанк ещё могут дать сигнал; но статус уже зафиксирован

    # 2.5 CANON — каноническая линковка (CLAUDE.md §7 / scripts/pipeline/README):
    #     после pipeline.py (links) идут 68 (self full-URL -> относительный #z +
    #     нормализация внешних), 71 (полный спан «пункт N статьи M»), 73 (спан
    #     цепочек), 72 (внешние акты -> корень), 18 (снять ссылки в сносках).
    #     КАЖДЫЙ шаг СТРОГО по одному slug — иначе их --all-дефолт затрёт корпус.
    if "canon" in steps:
        canon_cmds = [
            ("68", [PY, str(PIPE / "68_link_canon.py"), "--doc-id", doc_id, "--form", "ready"]),
            ("71", [PY, str(PIPE / "71_fullspan_wrap.py"), slug, "--apply", "--form", "ready"]),
            ("73", [PY, str(PIPE / "73_fullspan_chains.py"), slug, "--apply"]),
            ("72", [PY, str(PIPE / "72_external_root_link.py"), slug, "--apply"]),
            ("18", [PY, str(PIPE / "18_strip_links_in_notes.py"), slug]),
        ]
        fails = []
        for lbl, cmd in canon_cmds:
            ok, msg = run(cmd, timeout)
            if not ok:
                fails.append(f"{lbl}({msg[:18]})")
        row["canon"] = "ok" if not fails else "FAIL:" + ",".join(f.split("(")[0] for f in fails)
        if fails and not row["note"]:
            row["note"] = "canon " + "; ".join(fails)

    # 3 GATE
    if "gate" in steps:
        g, note = gate_pass(slug, timeout)
        row["gate"] = g
        if not row["note"]:
            row["note"] = note

    # 4 CHUNK
    if "chunk" in steps:
        ok, msg = run([PY, str(PIPE / "chunk_npa.py"), slug], timeout)
        row["chunk"] = "ok" if ok else "FAIL"
        if not ok and not row["note"]:
            row["note"] = msg

    # ЧЕСТНЫЙ статус: DONE только если чанки реально покрыли ВСЕ статьи структуры.
    # (раньше DONE = «не упало» → пустые/orphan-выходы висели зелёными.)
    if not row["status"]:
        if "chunk" in steps:
            sa = struct_article_count(slug)
            nchunks, ca = chunk_article_stats(slug)
            row["sa"], row["ca"] = sa, ca
            if nchunks == 0:
                row["status"] = "EMPTY"            # чанков нет вовсе
                row["note"] = f"chunks=0 (структ.статей={sa})"
            elif sa < 0 or ca != sa:
                row["status"] = "UNDER_CHUNK"       # чанки есть, но статьи не сошлись
                row["note"] = f"чанк-статей {ca} != структ-статей {sa}"
            elif row.get("gate") not in ("GREEN", "-"):
                row["status"] = "GATE_RED"
            else:
                row["status"] = "DONE"
        else:
            row["status"] = "DONE" if row.get("gate") in ("GREEN", "-") else "GATE_RED"
    row["note"] = f"{row['note']}  ({time.time()-t0:.0f}s)".strip()
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*", help="конкретные slug; иначе --all")
    ap.add_argument("--all", action="store_true", help="все pilot-доки из codes.json с source/ на диске")
    ap.add_argument("--steps", default="all", help=f"подмножество из {','.join(ALL_STEPS)} или all")
    ap.add_argument("--timeout", type=int, default=900, help="потолок секунд на шаг")
    args = ap.parse_args()

    steps = ALL_STEPS if args.steps == "all" else [s.strip() for s in args.steps.split(",")]
    codes = load_codes()
    if args.all:
        slugs = [s for s in codes if (SOURCE / f"{s}.html").exists()]
    else:
        slugs = args.slugs
    if not slugs:
        sys.exit("нет доков: дай slug или --all (и проверь, что source/{slug}.html есть)")

    # ГАРД: пилот НЕ трогает закоммиченный корпус. Если в списке есть slug из HEAD
    # codes.json (кодекс/готовый закон) — отказ (иначе шаги links/canon/chunk
    # перезапишут курируемые final/*.html). --all цепляет корпус -> тоже упрётся сюда.
    _corpus = corpus_keys()
    clash = sorted(s for s in slugs if s in _corpus)
    if clash:
        sys.exit(f"ОТКАЗ: в списке {len(clash)} слаг(ов) из закоммиченного корпуса "
                 f"(их править нельзя): {clash}. Дай только пилотные НГР (не --all).")

    print(f"батч: {len(slugs)} доков | шаги: {','.join(steps)} | timeout/шаг: {args.timeout}s\n")
    rows = []
    for i, s in enumerate(slugs, 1):
        did = codes.get(s, {}).get("doc_id", s)
        r = process(s, did, steps, args.timeout)
        rows.append(r)
        print(f"[{i}/{len(slugs)}] {s:<16} pre={r['pre']:<5} str={r['struct']:<4} "
              f"lnk={r['links']:<4} canon={r['canon']:<6} gate={r['gate']:<5} chunk={r['chunk']:<4} "
              f"ст/чанк={r['sa']}/{r['ca']}  => {r['status']}  {r['note']}")

    # ── сводка ──
    by = Counter(r["status"] for r in rows)
    green = sum(1 for r in rows if r["gate"] == "GREEN")
    md = ["# Пилот-прогон НПА — сводка", "",
          f"- всего: **{len(rows)}**",
          f"- шаги: `{','.join(steps)}`", ""]
    for st, c in by.most_common():
        md.append(f"- {st}: **{c}**")
    md += ["", f"- гейт GREEN: **{green}/{len(rows)}**", "",
           "## Карантин (gate-0 КРИВО — разобрать формат)",
           "| slug | статей | причина |", "|---|---|---|"]
    for r in rows:
        if r["status"] == "QUARANTINE":
            md.append(f"| {r['slug']} | {r['n']} | {r['note']} |")
    md += ["", "## Упавшие на пайплайне (struct/pipe/gate)",
           "| slug | статус | нота |", "|---|---|---|"]
    for r in rows:
        if r["status"] in ("STRUCT_FAIL", "PIPE_FAIL", "GATE_RED"):
            md.append(f"| {r['slug']} | {r['status']} | {r['note']} |")
    md += ["", "## Недочанковано (структура есть, статьи в чанках не сошлись)",
           "| slug | структ-статей | чанк-статей | статус | нота |", "|---|--:|--:|---|---|"]
    for r in rows:
        if r["status"] in ("UNDER_CHUNK", "EMPTY"):
            md.append(f"| {r['slug']} | {r['sa']} | {r['ca']} | {r['status']} | {r['note']} |")
    md += ["", "## Все доки",
           "| slug | doc_id | стат. | pre | struct | links | canon | gate | chunk | ст/чанк | статус |",
           "|---|---|--:|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['slug']} | {r['doc_id']} | {r['n']} | {r['pre']} | {r['struct']} | "
                  f"{r['links']} | {r['canon']} | {r['gate']} | {r['chunk']} | {r['sa']}/{r['ca']} | {r['status']} |")
    (OUT / "pilot_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    with (OUT / "pilot_report.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("\n" + "=" * 64)
    for st, c in by.most_common():
        print(f"  {st:<14} {c}")
    print(f"  гейт GREEN:    {green}/{len(rows)}")
    print(f"отчёт: {(OUT / 'pilot_report.md').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
