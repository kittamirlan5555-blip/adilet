"""Проверка кандидата Z_ANCHOR против всех реальных z-якорей в data/final/."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FINAL = ROOT / "data" / "final"
CODES = ROOT / "config" / "codes.json"

ANY_Z = re.compile(r'\b(?:id|name)\s*=\s*"(z[^"]*)"')

# Кандидат: число с опц. -N, опц. суффикс h, затем сколько угодно _<seg>,
# где <seg> = (опц. p)число с опц. -N
Z_CANDIDATE = r'z\d+(?:-\d+)?h?(?:_p?\d+(?:-\d+)?)*'
STRICT = re.compile(r'^' + Z_CANDIDATE + r'$')


def main():
    cfg = json.loads(CODES.read_text(encoding="utf-8"))
    codes = [k for k in cfg.keys() if not k.startswith("_") and k != "upk"]

    all_vals = set()
    for code in codes:
        for suf in ("ready", "structured"):
            p = FINAL / f"{code}_{suf}.html"
            if not p.exists():
                continue
            t = p.read_text(encoding="utf-8")
            for m in ANY_Z.finditer(t):
                all_vals.add(m.group(1))

    unmatched = [v for v in all_vals if not STRICT.match(v)]
    print(f"Z_CANDIDATE = {Z_CANDIDATE}")
    print(f"Всего uniq z-якорей: {len(all_vals)}")
    print(f"НЕ покрыто:          {len(unmatched)}")
    if unmatched:
        print("Примеры (до 30):")
        for v in sorted(unmatched)[:30]:
            print(f"  {v}")
    else:
        print("[OK] Кандидат покрывает 100% реальных z-якорей.")


if __name__ == "__main__":
    main()
