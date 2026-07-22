# -*- coding: utf-8 -*-
"""anara2 BLOCK 1: прогон 68_link_canon (Шаг 2c — условная конверсия относит. self-URL)
по всем задетым докам, обе формы. Условие в 68: конвертим #zN только если zN есть в
документе; фантомы остаются относит. adilet-ссылкой. Считаем итог по каждому доку."""
import io, sys, json, re, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
cj = json.loads((ROOT / "maps" / "codes.json").read_text(encoding="utf-8"))
aff = json.loads((ROOT / "reports" / "_anara2_affected.json").read_text(encoding="utf-8"))
slugs = sorted(set(aff["ready"]) | set(aff["structured"]))
print(f"задето доков: {len(slugs)} (ready {len(aff['ready'])}, structured {len(aff['structured'])})")

tot_conv = tot_left = 0
for i, s in enumerate(slugs, 1):
    did = cj[s].get("doc_id", s)
    for form in ("ready", "structured"):
        p = ROOT / "final" / f"{s}_{form}.html"
        if not p.exists():
            continue
        before = p.read_text(encoding="utf-8", errors="replace")
        rel_before = len(re.findall(r'href="/rus/docs/' + re.escape(did) + r'#z', before))
        if rel_before == 0:
            continue
        r = subprocess.run([PY, str(ROOT / "scripts" / "pipeline" / "68_link_canon.py"),
                            "--doc-id", did, "--form", form], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        after = p.read_text(encoding="utf-8", errors="replace")
        rel_after = len(re.findall(r'href="/rus/docs/' + re.escape(did) + r'#z', after))
        conv = rel_before - rel_after
        tot_conv += conv
        tot_left += rel_after
    if i % 40 == 0:
        print(f"  ...{i}/{len(slugs)}  конвертировано={tot_conv} осталось-фантомов={tot_left}")
print(f"\nИТОГ: конвертировано relative-self -> #z: {tot_conv}; осталось фантомов (якоря нет): {tot_left}")
