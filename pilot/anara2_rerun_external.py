# -*- coding: utf-8 -*-
"""anara2 BLOCK 6: перепрогон внешней линковки на задетых доках — АДДИТИВНО и БЕЗОПАСНО.

Новый маппinг (653 ключа: +132 акта корпуса B2, +10 вариантов B3, мореплавание-fix) и
дата-в-фразе (B4) вступают в силу. НЕ используем 03.fix_npa_links напрямую — он
decompose-ит <script> (убил бы подсветку final/). Здесь скрипт-безопасно:
  1. Pass-2 (из 03): обернуть КЛЮЧ-подстроку маппинга в корневой <a>, ТОЛЬКО в текст-узлах
     вне <a>/<script>/<style>. Длинные ключи первыми (анти-вложенность).
  2. coalesce_split_act + absorb_prefix (из 72): дата/префикс в спан.
ГЕЙТЫ на каждый док: text-invariant (get_text без разделителя), nested<a>=0, dangling#z
не вырос, нет двойных href. Провал гейта → док ПРОПУСКАЕМ (не пишем), в отчёт.
"""
import io, sys, json, re, importlib.util
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parents[1]
APPLY = "--apply" in sys.argv
HOST = "https://adilet.zan.kz/rus/docs/"
SKIP = {"a", "script", "style", "head", "title", "template"}

spec = importlib.util.spec_from_file_location(
    "m72", ROOT / "scripts/pipeline/72_external_root_link.py")
m72 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m72)

MAP = json.loads((ROOT / "maps/npa_mapping.json").read_text(encoding="utf-8"))
# длинные ключи первыми — короткие формы не вкладываются в уже завёрнутые длинные
KEYS = sorted(MAP.items(), key=lambda kv: len(kv[0]), reverse=True)
cj = json.loads((ROOT / "maps/codes.json").read_text(encoding="utf-8"))
SLUGS = [s for s in cj if not s.startswith("_") and isinstance(cj[s], dict)]


def in_skip(node):
    p = node.parent
    while p is not None:
        if getattr(p, "name", None) in SKIP:
            return True
        p = p.parent
    return False


def wrap_keys(soup, self_id):
    """Pass-2: обернуть ключ-подстроки в корневые <a>. Возвращает число обёрток.
    self_id — doc_id ТЕКУЩЕГО файла: ключи, ведущие на него самого, ПРОПУСКАЕМ
    (самоотсылка корнем = класс ошибки §4; внутренние «настоящего Кодекса» — забота 02)."""
    added = 0
    self_norm = self_id.rstrip("_")
    for tn in list(soup.find_all(string=True)):
        s = str(tn)
        if len(s.strip()) < 6 or in_skip(tn):
            continue
        segments = [("text", s)]
        changed = False
        for name, docid in KEYS:
            if len(name) < 6:
                continue
            if docid.rstrip("_") == self_norm:        # §4: не линкуем сам на себя корнем
                continue
            if not any(k == "text" and name in seg for k, seg in segments):
                continue
            link = f'<a href="{HOST}{docid}">{name}</a>'
            new = []
            for k, seg in segments:
                if k != "text" or name not in seg:
                    new.append((k, seg)); continue
                idx = 0
                while True:
                    pos = seg.find(name, idx)
                    if pos < 0:
                        new.append(("text", seg[idx:])); break
                    if pos > idx:
                        new.append(("text", seg[idx:pos]))
                    new.append(("link", link)); idx = pos + len(name); changed = True
            segments = new
        if changed:
            html = "".join(seg for _, seg in segments)
            tn.replace_with(BeautifulSoup(html, "html.parser"))
            added += sum(1 for k, _ in segments if k == "link")
    return added


def norm(soup):
    return "".join(soup.get_text().split())


def dangling(soup):
    ids = {e.get("id") for e in soup.find_all(attrs={"id": True})}
    ids |= {e.get("name") for e in soup.find_all(attrs={"name": True})}
    n = 0
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if h.startswith("#z"):
            if h[1:] not in ids:
                n += 1
    return n


def double_href(html):
    return len(re.findall(r'href="[^"]*"\s+href=', html))


def main():
    tot_wrap = tot_co = tot_ab = 0
    written = skipped = 0
    changed_docs = []
    fails = []
    for slug in SLUGS:
        self_id = cj[slug].get("doc_id", slug)
        for form in ("ready", "structured"):
            p = ROOT / "final" / f"{slug}_{form}.html"
            if not p.exists():
                continue
            html0 = p.read_text(encoding="utf-8", errors="replace")
            soup = BeautifulSoup(html0, "html.parser")
            selfset = (HOST + self_id, HOST + self_id.rstrip("_"))
            t0 = norm(soup); d0 = dangling(soup)
            sr0 = sum(1 for a in soup.find_all("a", href=True) if a["href"].rstrip("/") in selfset)
            w = wrap_keys(soup, self_id)
            co = m72.coalesce_split_act(soup)
            ab = m72.absorb_prefix(soup)
            if w == 0 and co == 0 and ab == 0:
                continue
            t1 = norm(soup); d1 = dangling(soup)
            nested = sum(1 for a in soup.find_all("a") if a.find("a"))
            out = str(soup)
            dh = double_href(out)
            sr1 = sum(1 for a in soup.find_all("a", href=True) if a["href"].rstrip("/") in selfset)
            self_roots = sr1 - sr0                     # ДОБАВЛЕННЫЕ самокорни (не пред-существующие)
            gate_ok = (t0 == t1 and nested == 0 and d1 <= d0 and dh == 0 and self_roots <= 0)
            if not gate_ok:
                skipped += 1
                fails.append((f"{slug}_{form}", f"textInv={t0==t1} nested={nested} "
                              f"dangle {d0}->{d1} dblhref={dh} selfroot={self_roots}"))
                continue
            tot_wrap += w; tot_co += co; tot_ab += ab
            changed_docs.append((f"{slug}_{form}", w, co, ab))
            if APPLY:
                p.write_text(out, encoding="utf-8"); written += 1
    print(f"задето форм-файлов: {len(changed_docs)} | обёрнуто имён={tot_wrap} "
          f"coalesce={tot_co} absorb={tot_ab}")
    print(f"{'ЗАПИСАНО' if APPLY else 'DRY (не писали)'}: {written} | ГЕЙТ-ПРОВАЛОВ(пропущено): {skipped}")
    for name, why in fails[:20]:
        print(f"   SKIP {name}: {why}")
    print("\nтоп изменённых:")
    for name, w, co, ab in sorted(changed_docs, key=lambda x: -(x[1]+x[2]+x[3]))[:25]:
        print(f"   {name}: wrap={w} coalesce={co} absorb={ab}")
    (ROOT / "reports" / "anara2_rerun_external.json").write_text(json.dumps(
        {"changed": [dict(doc=n, wrap=w, coalesce=c, absorb=a) for n, w, c, a in changed_docs],
         "fails": fails, "totals": dict(wrap=tot_wrap, coalesce=tot_co, absorb=tot_ab,
                                        written=written, skipped=skipped)},
        ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
