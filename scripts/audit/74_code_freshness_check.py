# -*- coding: utf-8 -*-
"""ПРОВЕРКА АКТУАЛЬНОСТИ КОДОВ ВНЕШНИХ АКТОВ (§5 CLAUDE.md). READ-ONLY.

`npa_mapping.json` местами ПРОТУХ (старые редакции). Этот скрипт собирает ВСЕ
внешние doc_id (НГР), на которые реально ведут ссылки в готовых документах, и
сверяет их со списком известных «протухших» кодов (STALE_REMAP). Плюс проверяет
сам `npa_mapping.json` на протухшие значения.

НИЧЕГО НЕ МЕНЯЕТ. Только отчёт + (опц.) ненулевой код возврата в --strict.

Что ловит:
  • ссылку на ОТМЕНЁННУЮ/ЗАМЕНЁННУЮ редакцию (по таблице STALE_REMAP §5/HANDOFF);
  • строки npa_mapping.json, которые ведут на протухший код;
  • инвентаризацию ВСЕХ внешних doc_id (для ручной до-сверки незнакомых).

STALE_REMAP пополняется вручную по мере находок (см. §5). Источник истины —
живой adilet (`adilet.zan.kz/rus/docs/{НГР}`); но adilet блокирует ботов, поэтому
здесь — статическая таблица + инвентарь. Онлайн-режим (--online) пробует HEAD,
по умолчанию ВЫКЛ.

Запуск:
  python 74_code_freshness_check.py [code ...] [--strict] [--online]
    без аргументов — все data/final/*_ready.html + *_structured.html.
    --strict — exit 1, если найдены ссылки на протухшие коды.
"""
import re
import sys
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

ROOT = paths.ROOT
FINAL = paths.FINAL
CONFIG = paths.MAPS      # config/ слит в maps/ (Фаза A)
REPORTS = paths.REPORTS

# ─────────────────────────────────────────────────────────────────────────────
# КЛАССИФИКАЦИЯ ПРОТУХШИХ КОДОВ (§5). Авто-ремап разрешён ТОЛЬКО для подтверждённого
# repeal-replace: старый НГР формально отменён И заменён новым актом ТОГО ЖЕ предмета
# с ТЕМ ЖЕ названием. Если старый акт ещё действует, либо при замене сменилось
# название/предмет (видимая фраза != целевой акт) — это НЕ авто-ремап, а NEEDS_REVIEW.
# ─────────────────────────────────────────────────────────────────────────────

# CONFIRMED repeal-replace — авто-ремап безопасен. Оба подтверждены НАШИМ же
# corpus: целевые НГР — это doc_id наших собственных кодексов в config/codes.json
# (nalog=K2500000214, byudzhet=K2500000171), т.е. мы уже работаем с новой редакцией.
STALE_REMAP = {
    "K1700000120": ("K2500000214", "Налоговый кодекс: ред. 2017 -> 2025 (наш byudzhet/nalog в codes.json)"),
    "K080000095_": ("K2500000171", "Бюджетный кодекс: ред. 2008 -> 2025 (наш byudzhet=K2500000171)"),
}

# NEEDS_REVIEW — НЕ ремапить автоматически. Кандидат указан, но требует ручной
# сверки на живом adilet ПРЕЖДЕ чем доверять (причина каждого — почему авто-ремап
# опасен). Эти коды НЕ попадают в strict-гейт и НЕ предлагаются как автозамена.
NEEDS_REVIEW = {
    "Z950002444_": ("Z2600000258?",
                    "«О банках и банковской деятельности»: кандидат — новый закон 2026 "
                    "(Z2600000258), но дата вступления в силу НЕ подтверждена; старый "
                    "1995 мог ещё действовать на момент линковки. Сверить на adilet."),
    "Z1500000383": ("Z2300000030?",
                    "СМЕНА НАЗВАНИЯ: Z1500000383 = «Об общественных СОВЕТАХ», кандидат "
                    "Z2300000030 = «Об общественном КОНТРОЛЕ» — другой предмет/название. "
                    "Видимая фраза != целевой акт -> авто-ремап ЗАПРЕЩЁН, ручной разбор."),
    "Z070000252_": ("K1500000414?",
                    "СМЕНА РЕФЕРЕНТА: Z070000252_ = ЗАКОН «О введении в действие Трудового "
                    "кодекса» (2007), а не сам Кодекс. Кандидат K1500000414 = Трудовой "
                    "КОДЕКС 2015. Это разные акты — проверять контекст фразы вручную."),
}

# Удалён из STALE: Z1400000211 = «О профессиональных союзах» (№211-V, 27.06.2014) —
# ДЕЙСТВУЮЩИЙ, не протух. «О профессиональных квалификациях» = отдельный акт
# Z2300000014 (№14-VIII, 04.07.2023). Оба корректны в npa_mapping, ремап не нужен.

DOCID_IN_HREF = re.compile(r"/docs/([A-Za-z0-9_]+)")


def files_for(codes):
    if codes:
        out = []
        for c in codes:
            for suf in ("_ready.html", "_structured.html"):
                p = FINAL / f"{c}{suf}"
                if p.exists():
                    out.append(p)
        return out
    return sorted(FINAL.glob("*_ready.html")) + sorted(FINAL.glob("*_structured.html"))


def own_docids():
    """НГР наших собственных документов — их со стороны мы НЕ считаем 'внешними'."""
    cj = json.loads((CONFIG / "codes.json").read_text(encoding="utf-8"))
    return {v["doc_id"] for k, v in cj.items() if isinstance(v, dict) and "doc_id" in v}


def scan_file_docids(path):
    """Возвращает Counter doc_id -> число ссылок в файле (по href)."""
    text = path.read_text(encoding="utf-8")
    cnt = defaultdict(int)
    for m in re.finditer(r'href="[^"]*?' + r"/docs/([A-Za-z0-9_]+)", text):
        cnt[m.group(1)] += 1
    return cnt


def scan_file_links(path):
    """{(docid, kind): count}; kind: 'root' (href=/docs/{NGR}) | 'art' (/docs/{NGR}#z…).

    КРИТИЧНО для авто-ремапа (§5/§9): подмена НГР безопасна ТОЛЬКО для ROOT-ссылок
    (на акт ЦЕЛИКОМ — корень не зависит от внутренней нумерации). АРТИКУЛЬНАЯ ссылка
    `/docs/{старый_NGR}#zN` на ПЕРЕКОДИФИЦИРОВАННЫЙ акт ремапу подменой НГР НЕ
    подлежит: новый кодекс перенумерован, тот же `#zN` в нём указывает на ЧУЖУЮ
    статью (как УК в §9). Такие коды -> ручной разбор (ре-резолвить N по НОВОЙ карте)."""
    text = path.read_text(encoding="utf-8")
    out = defaultdict(int)
    for hm in re.finditer(r'href="([^"]*)"', text):
        m = re.search(r"/docs/([A-Za-z0-9_]+)(#[\w-]*)?", hm.group(1))
        if not m:
            continue
        frag = m.group(2)
        kind = "art" if (frag and frag.lstrip("#")) else "root"
        out[(m.group(1), kind)] += 1
    return out


def check_mapping(table=None):
    """Возвращает [(phrase, id, fresh_id, reason)] для строк mapping, чьё значение в table.

    table по умолчанию STALE_REMAP (подтверждённые). Передай NEEDS_REVIEW, чтобы
    выписать строки-кандидаты на ручной разбор отдельной секцией."""
    if table is None:
        table = STALE_REMAP
    m = json.loads((CONFIG / "npa_mapping.json").read_text(encoding="utf-8"))
    bad = []
    for phrase, did in m.items():
        if did in table:
            fresh, why = table[did]
            bad.append((phrase, did, fresh, why))
    return bad


def maybe_online(docids):
    """Best-effort HEAD на adilet (часто блокируется). Возвращает {docid: status|err}."""
    import urllib.request
    res = {}
    for did in sorted(docids):
        url = f"https://adilet.zan.kz/rus/docs/{did}"
        try:
            req = urllib.request.Request(url, method="HEAD",
                                         headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                res[did] = r.status
        except Exception as e:
            res[did] = f"ERR {type(e).__name__}"
    return res


def run(codes, strict, online):
    own = own_docids()
    files = files_for(codes)
    L = []
    P = L.append
    P("=" * 100)
    P("ПРОВЕРКА АКТУАЛЬНОСТИ КОДОВ (§5) — READ-ONLY")
    P("=" * 100)

    # ---- 1) ПОДТВЕРЖДЁННО протухшие значения в самом npa_mapping.json ----
    bad_map = check_mapping(STALE_REMAP)
    P(f"\n[1] npa_mapping.json — ПОДТВЕРЖДЁННО протухших строк (авто-ремап OK) = {len(bad_map)}")
    for phrase, stale, fresh, why in bad_map:
        P(f"    ПРОТУХ {stale} -> {fresh}  | {why}")
        P(f"           фраза: {phrase!r}")

    # ---- 1b) КАНДИДАТЫ НА РУЧНОЙ РАЗБОР (НЕ авто-ремап) ----
    review_map = check_mapping(NEEDS_REVIEW)
    P(f"\n[1b] npa_mapping.json — КАНДИДАТЫ NEEDS_REVIEW (НЕ ремапить авто) = {len(review_map)}")
    for phrase, did, cand, why in review_map:
        P(f"    ? {did} -> {cand}")
        P(f"        причина: {why}")
        P(f"        фраза:   {phrase!r}")

    # ---- 2) ссылки на подтверждённо протухшие коды: ROOT vs АРТИКУЛЬНЫЕ ----
    # Авто-ремап (подмена НГР) БЕЗОПАСЕН ТОЛЬКО для ROOT (href=/docs/{NGR}). Артикульная
    # (/docs/{NGR}#zN) на перекодифицированный акт -> #zN указывает на ЧУЖУЮ статью в
    # новой редакции (§9). Такие -> NEEDS_REVIEW (ре-резолвить N по НОВОЙ карте статей).
    per_file_root = []        # (fname, {docid: n})  ROOT — auto-remap-safe
    per_file_art = []         # (fname, {docid: n})  articular — на ручной разбор
    global_root = defaultdict(int)
    global_art = defaultdict(int)
    review_links = defaultdict(int)
    all_external = defaultdict(int)
    for p in files:
        cnt = scan_file_docids(p)
        for d, n in cnt.items():
            if d not in own:
                all_external[d] += n
            if d in NEEDS_REVIEW:
                review_links[d] += n
        root_hits, art_hits = {}, {}
        for (d, kind), n in scan_file_links(p).items():
            if d not in STALE_REMAP:
                continue
            if kind == "root":
                root_hits[d] = root_hits.get(d, 0) + n
                global_root[d] += n
            else:
                art_hits[d] = art_hits.get(d, 0) + n
                global_art[d] += n
        if root_hits:
            per_file_root.append((p.name, root_hits))
        if art_hits:
            per_file_art.append((p.name, art_hits))

    total_root_stale = sum(global_root.values())
    total_art_stale = sum(global_art.values())

    P(f"\n[2] ROOT-ссылки на протухшие коды (АВТО-РЕМАП ПОДМЕНОЙ НГР БЕЗОПАСЕН): "
      f"{total_root_stale} (в {len(per_file_root)} файлах)")
    for fname, hits in per_file_root:
        for d, n in sorted(hits.items(), key=lambda x: -x[1]):
            fresh, why = STALE_REMAP[d]
            P(f"    {fname:34} {d} ×{n}  ->  {fresh}   ({why})")

    P(f"\n[2a] АРТИКУЛЬНЫЕ (#z) ссылки на протухшие коды — НЕ РЕМАПИТЬ ПОДМЕНОЙ НГР "
      f"(§9), -> NEEDS_REVIEW: {total_art_stale} (в {len(per_file_art)} файлах)")
    P("     перекодификация перенумеровала акт: тот же #zN -> ЧУЖАЯ статья; нужно")
    P("     РЕ-РЕЗОЛВИТЬ номер статьи по НОВОЙ карте целевого кодекса, а не менять НГР.")
    for fname, hits in per_file_art:
        for d, n in sorted(hits.items(), key=lambda x: -x[1]):
            fresh, why = STALE_REMAP[d]
            P(f"    {fname:34} {d}#z ×{n}  -> ре-резолв статьи в {fresh}   ({why})")

    # ---- 2b) ссылки на NEEDS_REVIEW коды (mapping-уровень, ручной разбор) ----
    total_review_links = sum(review_links.values())
    P(f"\n[2b] ССЫЛКИ НА NEEDS_REVIEW КОДЫ (ручной разбор): {total_review_links}")
    for d, n in sorted(review_links.items(), key=lambda x: -x[1]):
        cand, why = NEEDS_REVIEW[d]
        P(f"    {d:16} ×{n}  ->  {cand}   ({why[:60]}…)")

    # ---- 3) инвентарь всех внешних doc_id (для ручной до-сверки) ----
    P(f"\n[3] ИНВЕНТАРЬ внешних doc_id (всего уникальных: {len(all_external)}):")
    for d, n in sorted(all_external.items(), key=lambda x: -x[1]):
        if d in STALE_REMAP:
            flag = "  <-- ПРОТУХ"
        elif d in NEEDS_REVIEW:
            flag = "  <-- NEEDS_REVIEW"
        else:
            flag = ""
        P(f"    {d:16} ×{n}{flag}")

    # ---- 4) опц. онлайн-проверка ----
    if online:
        P("\n[4] ОНЛАЙН HEAD adilet (best-effort, часто блокируется):")
        for d, st in maybe_online(set(all_external)).items():
            P(f"    {d:16} {st}")

    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / "74_code_freshness.txt"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\n[freshness] ROOT-stale(авто-ремап-safe)={total_root_stale}  "
          f"ART-stale(#z, ручной ре-резолв)={total_art_stale}  строк mapping={len(bad_map)} "
          f"| NEEDS_REVIEW: ссылок={total_review_links} строк={len(review_map)}  -> {out}")

    # strict гейтит ТОЛЬКО на АВТО-РЕМАП-БЕЗОПАСНОЕ: ROOT-stale + протухшие строки mapping.
    # Артикульные stale (#z) и NEEDS_REVIEW — ручной разбор, НЕ авто-ремап -> не блокер.
    if strict and (total_root_stale or bad_map):
        sys.exit(1)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict" in sys.argv
    online = "--online" in sys.argv
    run(args, strict, online)


if __name__ == "__main__":
    main()
