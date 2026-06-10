"""
Скрипт 15: Чинит битые якоря в готовом HTML.

Источник битых якорей: исходные HTML с adilet.zan.kz содержат `<a href="…#zXXX">`,
где anchor `zXXX` отсутствует в их же HTML (известный баг adilet). Например:
    <a href="…/K2300000224#z3264">пункта 1</a> <a href="…/K2300000224#z3263">статьи 256</a>
            ^^^^^^^^^^^^^ — `z3264` не существует в socialnyy.html
            эти ссылки попадают в наш ready как есть и при клике уводят в начало кодекса.

Подход:
  1. Собираем все anchor-id из ВСЕХ `data/final/<code>_ready.html`.
  2. Для каждого `<a href>` проверяем: ведёт ли он на существующий anchor?
     - internal (same doc) → проверка в anchor inventory того же кодекса;
     - cross-code (другой doc_id из 12) → проверка в inventory целевого кодекса;
     - external (НПА вне 12 кодексов) → пропускаем (не можем проверить).
  3. Если anchor отсутствует:
     a) Пробуем «исправить»:
        - Текст ссылки = "пункта N" → следующая ссылка содержит "статьи M".
          Берём M и target_doc; ищем `subpoint_map[target]["M_N"]`. Если есть —
          подставляем этот anchor.
        - Текст ссылки = "статьи N" → ищем `article_map[target]["N"]`.
     b) Если исправить нельзя — меняем href на корень документа
        (`http://…/rus/docs/{doc_id}`).

Использование:
  python scripts/15_fix_broken_anchors.py
    (применяется ко всем кодексам из config/codes.json)
"""
import json
import re
import argparse
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
MAPS = ROOT / "data" / "maps"
CODES = ROOT / "config" / "codes.json"
BASE = "http://85.202.192.66:9096"


def load_codes():
    cfg = json.loads(CODES.read_text(encoding="utf-8"))
    return {k: v for k, v in cfg.items() if not k.startswith("_")}


def collect_anchors(html_text: str):
    return set(re.findall(r'\b(?:id|name)\s*=\s*"([^"]+)"', html_text))


HREF_RE = re.compile(r'https?://[^/]+/rus/docs/([A-Z]\d+_?[A-Z]?)(?:#(.+))?$')


def parse_href(href: str):
    m = HREF_RE.match(href.strip())
    if not m:
        return None, None
    return m.group(1), m.group(2)


def find_target_for_doc(doc_id, codes_cfg):
    for code, info in codes_cfg.items():
        if info["doc_id"] == doc_id:
            return code
    return None


def fix_html_anchors(html_path: Path, codes_cfg, anchor_inventories, article_maps, subpoint_maps, code_for_doc):
    text = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(text, "lxml")
    fixed = 0
    dropped = 0
    a_tags = list(soup.find_all("a", href=True))
    for i, a in enumerate(a_tags):
        href = (a.get("href") or "").strip()
        if not href or href == "#":
            # Empty href / hash — unwrap
            a.unwrap()
            dropped += 1
            continue
        doc_id, anchor = parse_href(href)
        if not doc_id:
            # Probably pure-anchor href like "#zN"
            if href.startswith("#"):
                anchor_only = href[1:]
                inv = anchor_inventories.get(html_path.stem.replace("_ready", ""), set())
                if anchor_only in inv:
                    continue  # OK
                # broken — drop
                a.unwrap()
                dropped += 1
            continue
        target_code = code_for_doc.get(doc_id)
        if not target_code:
            # External NPA outside 12 codes — can't verify, keep as-is
            continue
        inv = anchor_inventories.get(target_code, set())
        if not anchor:
            # link to root — OK
            continue
        if anchor in inv:
            continue  # OK
        # === Broken: try to repair ===
        link_text = a.get_text(" ", strip=True)
        # Repair pattern A: "пункта/пункт/пунктом N" — look at next sibling <a>
        m_punkt = re.match(r"^\s*пункт\w*\s+(\d+(?:-\d+)?)\)?\s*$", link_text, re.IGNORECASE)
        if m_punkt:
            pn = m_punkt.group(1)
            # find next <a> sibling
            sib = a.next_sibling
            steps = 0
            while sib is not None and steps < 6:
                if getattr(sib, "name", None) == "a":
                    sib_text = sib.get_text(" ", strip=True)
                    am = re.search(r"стать\w+\s+(\d+(?:-\d+)?)", sib_text, re.IGNORECASE)
                    if am:
                        art_n = am.group(1)
                        sm = subpoint_maps.get(target_code, {})
                        new_anchor = sm.get(f"{art_n}_{pn}")
                        if not new_anchor:
                            # fallback: article map
                            new_anchor = article_maps.get(target_code, {}).get(art_n)
                        if new_anchor:
                            a["href"] = f"{BASE}/rus/docs/{doc_id}#{new_anchor}"
                            fixed += 1
                            break
                steps += 1
                sib = sib.next_sibling
            else:
                # Couldn't repair — fall back to doc root
                a["href"] = f"{BASE}/rus/docs/{doc_id}"
                fixed += 1
            continue
        # Repair pattern B: "статьи/статья/статьёй N"
        m_art = re.match(r"^\s*стать\w+\s+(\d+(?:-\d+)?)", link_text, re.IGNORECASE)
        if m_art:
            art_n = m_art.group(1)
            new_anchor = article_maps.get(target_code, {}).get(art_n)
            if new_anchor:
                a["href"] = f"{BASE}/rus/docs/{doc_id}#{new_anchor}"
                fixed += 1
            else:
                a["href"] = f"{BASE}/rus/docs/{doc_id}"
                fixed += 1
            continue
        # Repair pattern C: "главой/главы N"
        m_ch = re.match(r"^\s*глав\w+\s+(\d+(?:-\d+)?)", link_text, re.IGNORECASE)
        if m_ch:
            # We don't have chapter map; just point to doc root
            a["href"] = f"{BASE}/rus/docs/{doc_id}"
            fixed += 1
            continue
        # Fallback: doc root
        a["href"] = f"{BASE}/rus/docs/{doc_id}"
        fixed += 1
    html_path.write_text(str(soup), encoding="utf-8")
    return fixed, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", nargs="*", help="Specific code keys to process (default: all)")
    args = ap.parse_args()

    codes_cfg = load_codes()
    target_codes = args.codes or list(codes_cfg.keys())

    anchor_inventories = {}
    article_maps = {}
    subpoint_maps = {}
    code_for_doc = {info["doc_id"]: c for c, info in codes_cfg.items()}

    # Pre-load anchor inventories and maps
    for code in codes_cfg:
        p = FINAL / f"{code}_ready.html"
        if p.exists():
            anchor_inventories[code] = collect_anchors(p.read_text(encoding="utf-8"))
        amf = MAPS / f"article_map_{code}.json"
        if amf.exists():
            article_maps[code] = json.loads(amf.read_text(encoding="utf-8"))
        smf = MAPS / f"subpoint_map_{code}.json"
        if smf.exists():
            subpoint_maps[code] = json.loads(smf.read_text(encoding="utf-8"))

    total_fixed = 0
    total_dropped = 0
    for code in target_codes:
        p = FINAL / f"{code}_ready.html"
        if not p.exists():
            continue
        fixed, dropped = fix_html_anchors(p, codes_cfg, anchor_inventories, article_maps, subpoint_maps, code_for_doc)
        print(f"  {code}: fixed={fixed} dropped={dropped}")
        total_fixed += fixed
        total_dropped += dropped
        # After fix, anchor inventory may have changed slightly (we removed some unwrapped <a>); refresh
        anchor_inventories[code] = collect_anchors(p.read_text(encoding="utf-8"))
    print(f"\nTotal fixed: {total_fixed}, dropped (empty/hash): {total_dropped}")


if __name__ == "__main__":
    main()
