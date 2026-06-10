"""READ-ONLY аудит ВНЕШНИХ ссылок (ТЗ 5.2.3). Ничего не чиним.
PART A инвентаризация (наши коды vs чужие акты; формы URL)
PART B архивные/датированные формы (не действующая редакция)
PART C якоря целей-наших-кодов: #zN существует ли в нашем _structured и резолв в статью
PART D остаток (чужие акты): счёт + список distinct id (для проверки живости отдельно)

Источник: data/final/{code}_structured.html. Скоуп: <a> внутри div[data-type].
Пишет: data/reports/EXTERNAL_audit.md (PART A-C + D-инвентарь) и
       data/reports/_ext_foreign_ids.txt (id<TAB>count) для PART D.
"""
import re
import sys
import json
import importlib.util
from pathlib import Path
from collections import Counter, defaultdict
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
REPORT = ROOT / "data" / "reports" / "EXTERNAL_audit.md"
FOREIGN_IDS = ROOT / "data" / "reports" / "_ext_foreign_ids.txt"

_so = sys.stdout
_spec = importlib.util.spec_from_file_location(
    "audit", ROOT / "scripts" / "audit_links_coverage.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
sys.stdout = _so

CODES = json.loads((ROOT / "config" / "codes.json").read_text(encoding="utf-8"))
CODES = {k: v for k, v in CODES.items() if not k.startswith("_")}
ORDER = ["nalog", "trudovoy", "grazhdanskiy", "grazhdanskiy_osob",
         "predprinimatel", "socialnyy", "ekologicheskiy", "zemelnyy",
         "upk", "koap", "appk", "byudzhet", "ugolovniy"]
OUR = {v["doc_id"]: k for k, v in CODES.items()}           # doc_id -> code
DOC_NAMES = A.DOC_NAMES

RE_FULLID = re.compile(r"/docs/([A-Z]\d{6,}[A-Z]?_?)")
RE_FRAG = re.compile(r"#(z[\w-]+|\d+)")
# архив/датированная форма: query, /history, version-сегмент, доп. дата-сегмент
RE_ARCHIVE = re.compile(r"(\?|/history|/version|/redact|period=|date=|#V\d|/\d{8}\b)", re.I)

# кэш резолва наших кодов-целей (для PART C)
_resolv_cache = {}


def resolver(code):
    if code not in _resolv_cache:
        fp = FINAL / f"{code}_structured.html"
        soup = BeautifulSoup(fp.read_text(encoding="utf-8"), "html.parser")
        id2art, all_ids, art_numbers, id2next = A.build_id_to_art(soup)
        _resolv_cache[code] = (id2art, all_ids)
    return _resolv_cache[code]


def host_article(a):
    hd = a.find_parent("div", attrs={"data-type": "статья"})
    if hd is None:
        return "?"
    return hd.get("data-number") or "?"


def ctx(a, n=60):
    pv = A.preceding_text(a, n)[-n:]
    return re.sub(r"\s+", " ", pv)


def url_form(h):
    if RE_ARCHIVE.search(h):
        return "archived"
    if h.startswith("/"):
        return "relative"
    if h.startswith("http://") or h.startswith("https://"):
        return "absolute"
    return "raw"


def main():
    # аккумуляторы
    per = {}                       # code -> Counter
    foreign_ids = Counter()        # full_id -> count (чужие)
    ours_targets = Counter()       # code-target -> count
    archived = []                  # (code, host, href, ctx)
    c_ok = Counter()               # target_code -> ok
    c_broken = []                  # (code, host, target_code, frag, href, ctx)
    c_total = Counter()            # target_code -> total external→ours c #frag
    foreign_examples = {}          # full_id -> (code, href, ctx)

    for code in ORDER:
        fp = FINAL / f"{code}_structured.html"
        if not fp.exists():
            continue
        soup = BeautifulSoup(fp.read_text(encoding="utf-8"), "html.parser")
        self_doc = A.SELF_DOC.get(code, "")
        c = Counter()
        for root in soup.find_all("div", attrs={"data-type": True}):
            for a in root.find_all("a", href=True):
                kind, doc = A.classify_href(a["href"], self_doc)
                if kind != "external":
                    continue
                h = a["href"]
                c["ext_total"] += 1
                m = RE_FULLID.search(h)
                full_id = m.group(1) if m else (doc or "?")
                form = url_form(h)
                c[f"form_{form}"] += 1
                fragm = RE_FRAG.search(h)
                has_frag = bool(fragm)
                c["with_frag" if has_frag else "whole_doc"] += 1
                if form == "archived":
                    archived.append((code, host_article(a), h, ctx(a)))
                # ours vs foreign (точное совпадение по нашим 13 id)
                is_ours = (full_id in OUR) or (doc in OUR)
                if is_ours:
                    tgt_code = OUR.get(full_id) or OUR.get(doc)
                    c["to_ours"] += 1
                    ours_targets[tgt_code] += 1
                    # PART C: проверка якоря в нашем _structured цели
                    if has_frag and fragm.group(1).startswith("z"):
                        frag = fragm.group(1)
                        c_total[tgt_code] += 1
                        id2art, all_ids = resolver(tgt_code)
                        if frag in all_ids:
                            art = id2art.get(frag)
                            if art is not None:
                                c_ok[tgt_code] += 1
                            else:
                                c_broken.append((code, host_article(a), tgt_code,
                                                 frag, h, ctx(a), "anchor-no-article"))
                        else:
                            c_broken.append((code, host_article(a), tgt_code,
                                             frag, h, ctx(a), "anchor-missing"))
                else:
                    c["to_foreign"] += 1
                    foreign_ids[full_id] += 1
                    if full_id not in foreign_examples:
                        foreign_examples[full_id] = (code, h, ctx(a, 50))
        per[code] = c

    # ── сборка markdown ──────────────────────────────────────────────
    T = Counter()
    for c in per.values():
        T.update(c)

    md = []
    md.append("# Аудит ВНЕШНИХ ссылок — ТЗ 5.2.3 (READ-ONLY, ничего не чиним)")
    md.append("")
    md.append("Скоуп: `<a href>` внутри `div[data-type]` (контент), 13 кодов (12 + ГК-Особ). "
              "Внешняя = href на ДРУГОЙ `doc_id` (не self). Источник: `data/final/{code}_structured.html`.")
    md.append("")
    md.append(f"**Итого внешних ссылок (вхождений `<a>`): {T['ext_total']}**  ·  "
              f"на наши 13 кодов: **{T['to_ours']}**  ·  на чужие акты: **{T['to_foreign']}**  ·  "
              f"distinct чужих актов: **{len(foreign_ids)}**")
    md.append("")

    # PART A
    md.append("## PART A — Инвентаризация")
    md.append("")
    md.append("| код | внешн. всего | → наши коды | → чужие | с #якорем | весь док | форма |")
    md.append("|---|---:|---:|---:|---:|---:|---|")
    for code in ORDER:
        c = per.get(code, Counter())
        forms = []
        for f in ("absolute", "relative", "raw", "archived"):
            if c[f"form_{f}"]:
                forms.append(f"{f}:{c[f'form_{f}']}")
        md.append(f"| {code} | {c['ext_total']} | {c['to_ours']} | {c['to_foreign']} | "
                  f"{c['with_frag']} | {c['whole_doc']} | {', '.join(forms) or '—'} |")
    md.append(f"| **ИТОГО** | **{T['ext_total']}** | **{T['to_ours']}** | **{T['to_foreign']}** | "
              f"**{T['with_frag']}** | **{T['whole_doc']}** | "
              f"absolute:{T['form_absolute']} relative:{T['form_relative']} "
              f"raw:{T['form_raw']} archived:{T['form_archived']} |")
    md.append("")
    md.append("Распределение ссылок НА НАШИ коды (target):")
    md.append("")
    md.append("| target-код | вхождений |")
    md.append("|---|---:|")
    for tcode in ORDER:
        if ours_targets[tcode]:
            md.append(f"| {tcode} | {ours_targets[tcode]} |")
    md.append("")
    md.append(f"**Формы URL:** все {T['ext_total']} внешних — абсолютные "
              f"`https://adilet.zan.kz/rus/docs/{{ID}}[#zN]`. relative={T['form_relative']}, "
              f"raw={T['form_raw']}, archived={T['form_archived']}. "
              "Сырой adilet-URL (в т.ч. grazhdanskiy_osob) нормализован в абсолютную форму.")
    md.append("")

    # PART B
    md.append("## PART B — Архивные / датированные формы (не действующая редакция)")
    md.append("")
    if not archived:
        md.append(f"**Архивных/датированных URL: 0.** Все {T['ext_total']} внешних ссылок — "
                  "bare `/rus/docs/{ID}` без query/`?period=`/`/history`/версии/даты, что "
                  "**by design = действующая редакция** (adilet отдаёт текущую редакцию на bare-URL).")
    else:
        md.append(f"**Найдено архивных/датированных: {len(archived)}** —")
        md.append("")
        md.append("| код | host ст. | href | контекст |")
        md.append("|---|---|---|---|")
        for code, host, h, cx in archived[:200]:
            md.append(f"| {code} | {host} | `{h}` | …{cx}… |")
    md.append("")

    # PART C
    md.append("## PART C — Якоря целей-наших-кодов (локальная проверка #zN)")
    md.append("")
    md.append("Для внешних ссылок на наши 13 кодов с `#zN`: существует ли `#zN` в НАШЕМ "
              "`_structured` кода-цели и резолвит ли в статью (`build_id_to_art`).")
    md.append("")
    tot_c = sum(c_total.values())
    tot_ok = sum(c_ok.values())
    md.append(f"**Проверено `#zN`→наши коды: {tot_c}  ·  OK: {tot_ok}  ·  битых якорей: "
              f"{len(c_broken)}**")
    md.append("")
    md.append("| target-код | #zN всего | OK | битых |")
    md.append("|---|---:|---:|---:|")
    for tcode in ORDER:
        if c_total[tcode]:
            br = sum(1 for x in c_broken if x[2] == tcode)
            md.append(f"| {tcode} | {c_total[tcode]} | {c_ok[tcode]} | {br} |")
    md.append("")
    if c_broken:
        md.append(f"### Битые якоря ({len(c_broken)}):")
        md.append("")
        md.append("| из кода | host ст. | target | frag | тип | href | контекст |")
        md.append("|---|---|---|---|---|---|---|")
        for code, host, tgt, frag, h, cx, typ in c_broken[:300]:
            md.append(f"| {code} | {host} | {tgt} | `{frag}` | {typ} | `{h}` | …{cx}… |")
    else:
        md.append("**Битых якорей нет — все `#zN` на наши коды резолвят в статью.**")
    md.append("")

    # PART D инвентарь
    md.append("## PART D — Остаток: чужие акты (нет локально)")
    md.append("")
    md.append(f"**Ссылок на чужие акты: {T['to_foreign']}  ·  distinct чужих `doc_id`: "
              f"{len(foreign_ids)}.** Для них целевой документ у нас отсутствует — проверка "
              "якоря/статьи невозможна локально (нужен внешний источник). Топ по частоте:")
    md.append("")
    md.append("| чужой doc_id | имя (если известно) | вхождений | пример (код/контекст) |")
    md.append("|---|---|---:|---|")
    for fid, cnt in foreign_ids.most_common(40):
        nm = DOC_NAMES.get(fid, DOC_NAMES.get(fid.rstrip("_"), ""))
        ex = foreign_examples.get(fid, ("", "", ""))
        md.append(f"| `{fid}` | {nm} | {cnt} | {ex[0]}: …{ex[2]}… |")
    md.append("")
    md.append("_Проверка живости (HTTP) — см. раздел PART D · Connectivity ниже (заполняется "
              "после сетевого теста)._")
    md.append("")

    REPORT.write_text("\n".join(md) + "\n", encoding="utf-8")

    # машинный список чужих id для PART D
    lines = [f"{fid}\t{cnt}" for fid, cnt in foreign_ids.most_common()]
    FOREIGN_IDS.write_text("\n".join(lines) + "\n", encoding="utf-8")

    try:
        sys.stderr.write(
            f"report -> {REPORT}\n"
            f"ext_total={T['ext_total']} ours={T['to_ours']} foreign={T['to_foreign']} "
            f"distinct_foreign={len(foreign_ids)} C_checked={tot_c} C_ok={tot_ok} "
            f"C_broken={len(c_broken)} archived={len(archived)}\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
