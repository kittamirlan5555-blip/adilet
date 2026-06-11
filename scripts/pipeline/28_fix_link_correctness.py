"""ТОЧЕЧНЫЙ ФИКС КОРРЕКТНОСТИ ССЫЛОК (Вариант 1).

Чинит ровно то, что нашёл аудит (scripts/audit_links_coverage.py):
  WRONG (16) — «статья N» ведёт не на N  → перепривязка href на якорь статьи N.
  SUB   (28) — под-статья «N-K» ведёт на базовую N → перепривязка на якорь N-K.
  BROKEN (9) — #zK нет в DOM → перепривязка на якорь заявленной статьи
               (для приложения — создаётся недостающий якорь).
  dup id (10) — дублирующиеся id подпунктов → 2-е+ вхождение переименовываем.

Правки применяются В ОБА файла: data/final/{code}_ready.html и _structured.html.
Полный структуризатор НЕ запускается. По КАЖДОМУ фиксу печатается before→after.

  python scripts/28_fix_link_correctness.py          # DRY-RUN (ничего не пишет)
  python scripts/28_fix_link_correctness.py --apply  # пишет (с бэкапом)

Источник якорей-целей — _structured (канон по ссылкам): для статьи N якорь = id
контейнера div[data-type=статья][data-number=N] без префикса 'w_'.
"""
import io
import os
import re
import sys
import shutil
import importlib.util
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup, NavigableString, Tag

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

ROOT = paths.ROOT
FINAL = paths.FINAL
BACKUP = paths.BACKUPS / "final_backup_FIXLINKS"

APPLY = "--apply" in sys.argv

# ── импортируем резолвер из аудита, чтобы классификация совпадала 1-в-1 ──
_spec = importlib.util.spec_from_file_location(
    "audit_mod", ROOT / "scripts" / "audit_links_coverage.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

ORDER = ["nalog", "trudovoy", "grazhdanskiy", "grazhdanskiy_osob",
         "predprinimatel", "socialnyy", "ekologicheskiy", "zemelnyy",
         "upk", "koap", "appk", "byudzhet", "ugolovniy"]

SELF_DOC = A.SELF_DOC
RE_FRAG = re.compile(r"#(z[\w-]+)")
RE_ART_IN = A.RE_ART_IN


def art_to_anchor_map(soup, id2art, id2next, all_ids):
    """data-number статьи -> id-якорь начала статьи.

    Кандидат №1 — id контейнера div без префикса 'w_'. Принимаем его, только
    если он РЕАЛЬНО существует как id= в документе И резолвится в свою статью
    (это отсекает trudovoy, где контейнер ст.32 назван w_z32, но сам якорь z32
    физически лежит в ст.124-2). Иначе берём первый внутренний id-якорь,
    который резолвится в эту же статью."""
    m = {}
    bad = []

    def resolves(anc, n):
        return anc in all_ids and str(n) in {str(id2art.get(anc)),
                                             str(id2next.get(anc))}

    for div in soup.find_all("div", attrs={"data-type": "статья"}):
        n = div.get("data-number")
        if not n:
            continue
        did = div.get("id", "")
        cand = did[2:] if did.startswith("w_") else None
        if cand and A.RE_ZID.match(cand) and resolves(cand, n):
            m[n] = cand
            continue
        chosen = None
        for el in div.descendants:
            if isinstance(el, Tag):
                iid = el.get("id")
                if iid and A.RE_ZID.match(iid) and resolves(iid, n):
                    chosen = iid
                    break
        if chosen:
            m[n] = chosen
            if cand and cand != chosen and A.RE_ZID.match(cand):
                bad.append((n, "container=" + cand, "use=" + chosen))
        elif cand and A.RE_ZID.match(cand):
            m[n] = cand           # последний шанс (может не резолвиться)
            bad.append((n, cand, "no valid inner id"))
    return m, bad


def host_article(a):
    d = a.find_parent("div", attrs={"data-type": "статья"})
    return d.get("data-number") if d is not None else None


def following_text(a, maxlen=90):
    buf = ""
    node = a
    while node is not None and len(buf) < maxlen:
        node = node.next_element
        if node is None:
            break
        if isinstance(node, NavigableString):
            buf += str(node)
    return re.sub(r"\s+", " ", buf)[:maxlen]


def broken_target_article(a, ck, cn):
    """Какой статье принадлежит битая ссылка: из текста ссылки или следующего."""
    if ck == "ARTICLE" and cn:
        return cn
    # NONART (пункт/часть/приложение): ищем «статьи N» сразу после ссылки
    tail = following_text(a)
    if re.search(r"(?i)настоящ\w+\s+стать", tail):
        return host_article(a)
    m = re.search(r"(?i)\bстать[а-яё]{0,3}\s+(\d+(?:-\d+)?)", tail)
    if m:
        return m.group(1)
    return None


def collect_fixes(soup, code, self_doc):
    """Возвращает список фиксов на _structured (с Tag-объектами) + карту якорей."""
    id2art, all_ids, art_numbers, id2next = A.build_id_to_art(soup)
    anchor, bad_anchor = art_to_anchor_map(soup, id2art, id2next, all_ids)

    fixes = []       # dict: kind, tag, old, new, claimed, host, text
    unresolved = []
    for a in soup.find_all("a", href=True):
        if not a.find_parent("div", attrs={"data-type": True}):
            continue
        kind, doc = A.classify_href(a["href"], self_doc)
        if kind != "internal":
            continue
        fm = RE_FRAG.search(a["href"])
        if not fm:
            continue
        zk = fm.group(1)
        ck, cn = A.claimed_article(a)
        host = host_article(a)
        text = a.get_text(" ", strip=True)[:48]

        if zk not in all_ids:  # BROKEN
            tgt = broken_target_article(a, ck, cn)
            if tgt and tgt in anchor:
                fixes.append(dict(kind="BROKEN", tag=a, old=a["href"],
                                  newanc=anchor[tgt], claimed=tgt, host=host,
                                  text=text, oldzk=zk))
            else:
                unresolved.append(dict(kind="BROKEN", host=host, text=text,
                                       href=a["href"], claimed=cn, tgt=tgt))
            continue

        R, Rn = id2art.get(zk), id2next.get(zk)
        acc = {str(R), str(Rn)}
        if ck != "ARTICLE":
            continue
        cns = str(cn)
        if "-" in cns and cns not in art_numbers:
            continue  # диапазон A-B, ведёт на A — ок
        if "-" in cns and cns in art_numbers and cns not in acc:  # SUB
            if cns in anchor:
                fixes.append(dict(kind="SUB", tag=a, old=a["href"],
                                  newanc=anchor[cns], claimed=cns, host=host,
                                  text=text, oldzk=zk))
            else:
                unresolved.append(dict(kind="SUB", host=host, text=text,
                                       href=a["href"], claimed=cns, tgt=None))
            continue
        if cns in acc:
            continue  # OK
        # WRONG
        if cns in anchor:
            fixes.append(dict(kind="WRONG", tag=a, old=a["href"],
                              newanc=anchor[cns], claimed=cns, host=host,
                              text=text, oldzk=zk))
        else:
            unresolved.append(dict(kind="WRONG", host=host, text=text,
                                   href=a["href"], claimed=cns, tgt=None))
    return fixes, unresolved, anchor, bad_anchor


def new_href(old, newanc, self_doc):
    """Меняем только фрагмент; self-URL adilet сворачиваем в относительный #z."""
    if old.strip().startswith("http"):
        m = re.search(r"/docs/([A-Z]\d{6,}_?)", old)
        if m and m.group(1) == self_doc:
            return "#" + newanc            # self-ссылка -> относительная
        return re.sub(r"#z[\w-]+", "#" + newanc, old)
    return re.sub(r"#z[\w-]+", "#" + newanc, old)


def apply_dup_ids(soup):
    """2-е и последующие вхождения дублирующегося id переименовываем уникально."""
    seen = Counter()
    renames = []
    for el in soup.find_all(attrs={"id": True}):
        iid = el.get("id")
        seen[iid] += 1
        if seen[iid] == 1:
            continue
        new = f"{iid}__d{seen[iid]}"
        el["id"] = new
        if el.get("name") == iid:
            el["name"] = new
        renames.append((iid, new))
    return renames


def ekologicheskiy_create_appendix_anchor(soup):
    """BROKEN ekologicheskiy #z4516 «приложению 1»: создаём якорь на заголовке."""
    if soup.find(attrs={"id": "z4516"}):
        return None
    for td in soup.find_all("td"):
        if td.get_text(" ", strip=True).startswith("Приложение 1"):
            span = soup.new_tag("a", id="z4516")
            span["name"] = "z4516"
            td.insert(0, span)
            return "Приложение 1 cell"
    return None


def process():
    print("=" * 100)
    print(f"FIX КОРРЕКТНОСТИ ССЫЛОК — режим: {'APPLY (пишем)' if APPLY else 'DRY-RUN (только показ)'}")
    print("=" * 100)
    if APPLY:
        BACKUP.mkdir(exist_ok=True)

    grand = Counter()
    for code in ORDER:
        sp = FINAL / f"{code}_structured.html"
        rp = FINAL / f"{code}_ready.html"
        if not sp.exists():
            continue
        self_doc = SELF_DOC.get(code, "")
        raw_s_orig = sp.read_text(encoding="utf-8")
        soup_s = BeautifulSoup(raw_s_orig, "html.parser")

        fixes, unresolved, anchor, bad_anchor = collect_fixes(soup_s, code, self_doc)

        # спец-случай: приложение ЭК — создаём недостающий якорь
        created = None
        if code == "ekologicheskiy":
            created = ekologicheskiy_create_appendix_anchor(soup_s)

        kinds = Counter(f["kind"] for f in fixes)
        if not fixes and not unresolved and not bad_anchor and not created:
            continue

        print(f"\n### {code}   "
              f"WRONG={kinds['WRONG']} SUB={kinds['SUB']} BROKEN={kinds['BROKEN']}"
              f"  unresolved={len(unresolved)}")
        if bad_anchor:
            print(f"  ! якоря-цели, не резолвящиеся в свою статью: {bad_anchor[:5]}")

        # карта (oldzk, claimed) -> newanc для применения к _ready
        ready_map = {}
        for f in fixes:
            nh = new_href(f["old"], f["newanc"], self_doc)
            print(f"  [{f['kind']:6}] ст.{f['host']} «{f['text']}» "
                  f"заявл={f['claimed']}")
            print(f"            before: href=\"{f['old']}\"")
            print(f"            after : href=\"{nh}\"")
            f["tag"]["href"] = nh
            ready_map[(f["oldzk"], str(f["claimed"]), f["text"])] = nh
            grand[f["kind"]] += 1
        if created:
            print(f"  [CREATE] ekologicheskiy: добавлен <a id=\"z4516\"> на «{created}»")
            grand["CREATE"] += 1
        for u in unresolved:
            print(f"  [UNRESOLVED {u['kind']}] ст.{u['host']} «{u['text']}» "
                  f"{u['href']} claimed={u['claimed']} tgt={u['tgt']}")

        # dup id на _structured
        ren_s = apply_dup_ids(soup_s)
        if ren_s:
            print(f"  [dupID structured] переименовано {len(ren_s)}: "
                  f"{', '.join(f'{a}->{b}' for a, b in ren_s)}")
            grand["dupID"] += len(ren_s)

        # ── применяем к _ready (если есть) ──
        ren_r = []
        n_ready_href = 0
        if rp.exists():
            raw_r_orig = rp.read_text(encoding="utf-8")
            soup_r = BeautifulSoup(raw_r_orig, "html.parser")
            for a in soup_r.find_all("a", href=True):
                fm = RE_FRAG.search(a["href"])
                if not fm:
                    continue
                zk = fm.group(1)
                ck, cn = A.claimed_article(a)
                txt = a.get_text(" ", strip=True)[:48]
                key = (zk, str(cn), txt)
                if key in ready_map:
                    a["href"] = ready_map[key]
                    n_ready_href += 1
            if code == "ekologicheskiy":
                cr = ekologicheskiy_create_appendix_anchor(soup_r)
                if cr:
                    print(f"  [CREATE _ready] добавлен <a id=\"z4516\"> на «{cr}»")
            ren_r = apply_dup_ids(soup_r)
            print(f"  [_ready] href-правок применено={n_ready_href}, "
                  f"dupID переименовано={len(ren_r)}")
            if APPLY:
                # ГЕЙТ §6.1: двигаются только href/якоря — текст обязан совпасть
                if "".join(re.sub(r"<[^>]+>", " ", raw_r_orig).split()) != \
                        "".join(re.sub(r"<[^>]+>", " ", str(soup_r)).split()):
                    raise SystemExit(f"TEXT-INVARIANCE FAIL: {rp.name}")
                bk = BACKUP / f"{code}_ready.html"
                if not bk.exists():
                    shutil.copy2(rp, bk)
                rp.write_text(str(soup_r), encoding="utf-8")
        else:
            print(f"  [_ready] файла нет (код без линк-пайплайна) — пропуск")

        if APPLY:
            # ГЕЙТ §6.1
            if "".join(re.sub(r"<[^>]+>", " ", raw_s_orig).split()) != \
                    "".join(re.sub(r"<[^>]+>", " ", str(soup_s)).split()):
                raise SystemExit(f"TEXT-INVARIANCE FAIL: {sp.name}")
            bk = BACKUP / f"{code}_structured.html"
            if not bk.exists():
                shutil.copy2(sp, bk)
            sp.write_text(str(soup_s), encoding="utf-8")

    print("\n" + "=" * 100)
    print("ИТОГО фиксов:", dict(grand))
    print("=" * 100)
    if not APPLY:
        print("DRY-RUN: файлы не изменены. Запусти с --apply для записи.")


if __name__ == "__main__":
    process()
