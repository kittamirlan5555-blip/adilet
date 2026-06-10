"""
Скрипт 16: Targeted manual overrides.

Применяет точечные правки к `data/final/<code>_ready.html`, определённые в
`config/manual_overrides.json`. Для каждого override:
  1. Загружает <code>_ready.html.
  2. Локализует find_phrase в окне рядом с context_marker.
  3. Если anchor_phrase ВНУТРИ найденного окна ещё НЕ обёрнут в <a>, оборачивает
     его в <a href="http://…/rus/docs/{doc_id}#{anchor}">…</a>.
  4. Проверяет, что целевой anchor существует в `<target_code>_ready.html`
     (или хотя бы валиден doc_id). Если anchor отсутствует — НЕ применяет
     override и пишет warning.

Никогда не создаёт href="" / href="#" / nested <a>.

Использование:
    python scripts/16_apply_targeted_overrides.py
    python scripts/16_apply_targeted_overrides.py --dry-run
"""
import json
import re
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

ROOT = paths.ROOT
FINAL = paths.FINAL
CONFIG = paths.MANUAL_OVERRIDES
CODES_CFG = paths.CODES_JSON
BASE = "https://adilet.zan.kz"


def collect_anchors(html: str):
    return set(re.findall(r'\b(?:id|name)\s*=\s*"([^"]+)"', html))


def is_inside_link(html: str, pos: int):
    """Check if position `pos` is inside an <a> ... </a>."""
    # Find last <a> opening before pos
    last_open = html.rfind('<a ', 0, pos)
    if last_open < 0:
        last_open = html.rfind('<a\t', 0, pos)
    if last_open < 0:
        return False
    # Find first </a> after last_open
    last_close = html.find('</a>', last_open, pos)
    if last_close < 0:
        # we're between <a> ... pos with no </a> before pos
        return True
    return False


def apply_overrides(dry_run=False):
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    codes_cfg = json.loads(CODES_CFG.read_text(encoding="utf-8"))
    doc_to_code = {v["doc_id"]: k for k, v in codes_cfg.items() if not k.startswith("_")}

    # Pre-collect anchor inventories
    inventories = {}
    for code in codes_cfg:
        if code.startswith("_"): continue
        p = FINAL / f"{code}_ready.html"
        if p.exists():
            inventories[code] = collect_anchors(p.read_text(encoding="utf-8"))

    # Group overrides by source code
    by_code = {}
    for ov in cfg["overrides"]:
        by_code.setdefault(ov["code"], []).append(ov)

    summary = []
    for code, overrides in by_code.items():
        p = FINAL / f"{code}_ready.html"
        if not p.exists():
            print(f"  [SKIP] {code}: file missing"); continue
        html = p.read_text(encoding="utf-8")
        original_len = len(html)
        applied = 0
        warnings = []
        for ov in overrides:
            ov_id = ov["id"]
            find_phrase = ov["find_phrase"]
            anchor_phrase = ov["anchor_phrase"]
            doc_id = ov["doc_id"]
            anchor = ov["anchor"]
            ctx = ov.get("context_marker")
            before_must = ov.get("before_must_be")

            # Verify target anchor existence
            target_code = doc_to_code.get(doc_id)
            if target_code and target_code in inventories:
                if anchor not in inventories[target_code]:
                    # Special-case: target_code == code AND html still being built
                    if target_code == code and anchor in collect_anchors(html):
                        pass
                    else:
                        warnings.append(f"  [SKIP] {ov_id}: anchor {anchor} not found in {target_code}_ready.html")
                        continue
            # Locate context_marker
            if ctx:
                ctx_pos = html.find(ctx)
                if ctx_pos < 0:
                    warnings.append(f"  [SKIP] {ov_id}: context_marker '{ctx[:30]}' not found")
                    continue
                # Search find_phrase within window after ctx_pos. We need a
                # window big enough to cover long articles (КоАП ст.804 ≈ 60К
                # chars). Cap by next "Статья N+1." if available.
                win_start = ctx_pos
                # Look for next "Статья ..." header after ctx_pos
                next_art = re.search(r'<b[^>]*><a[^>]*></a>Статья\s+\d', html[ctx_pos + len(ctx):])
                if not next_art:
                    next_art = re.search(r'>Статья\s+\d', html[ctx_pos + len(ctx):])
                if next_art:
                    win_end = ctx_pos + len(ctx) + next_art.start()
                else:
                    win_end = min(len(html), ctx_pos + 100000)

            # Find find_phrase position in window
            phrase_pos = html.find(find_phrase, win_start, win_end)
            if phrase_pos < 0:
                warnings.append(f"  [SKIP] {ov_id}: find_phrase not located in window")
                continue
            # Find anchor_phrase WITHIN that phrase
            inner_start = html.find(anchor_phrase, phrase_pos, phrase_pos + len(find_phrase) + 5)
            if inner_start < 0:
                warnings.append(f"  [SKIP] {ov_id}: anchor_phrase not inside find_phrase")
                continue
            inner_end = inner_start + len(anchor_phrase)
            # Optionally check before_must_be
            if before_must:
                # Verify the chars right before inner_start match
                check_start = inner_start - len(before_must)
                if check_start < 0 or html[check_start:inner_start] != before_must:
                    warnings.append(f"  [SKIP] {ov_id}: before_must check failed")
                    continue
            # Is this anchor_phrase already inside an <a> tag?
            if is_inside_link(html, inner_start):
                warnings.append(f"  [SKIP-already-linked] {ov_id}: anchor_phrase already inside <a>")
                continue
            # Build replacement
            href = f"{BASE}/rus/docs/{doc_id}#{anchor}"
            new_link = f'<a href="{href}">{anchor_phrase}</a>'
            html = html[:inner_start] + new_link + html[inner_end:]
            applied += 1
            print(f"  [OK]  {ov_id}: linked '{anchor_phrase}' → {href}")

        if applied and not dry_run:
            p.write_text(html, encoding="utf-8")
            print(f"  ✓ {code}: applied {applied} override(s); file size {original_len} → {len(html)}")
        elif applied:
            print(f"  [DRY] {code}: would apply {applied} override(s)")
        for w in warnings:
            print(w)
        summary.append((code, applied, len(warnings)))
    print("\nSummary:")
    for code, applied, warned in summary:
        print(f"  {code}: applied={applied}, skipped/warned={warned}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    apply_overrides(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
