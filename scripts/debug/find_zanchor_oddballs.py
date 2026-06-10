"""Поиск z-якорей, не покрытых текущим Z_ANCHOR = z\\d+(?:_\\d+)*.

Сканирует data/final/*_{ready,structured}.html кроме upk_*, собирает все
значения id="z..." и name="z...", и выводит уникальные значения, которые
НЕ матчатся под ^z\\d+(?:_\\d+)*$.

Read-only.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FINAL = ROOT / "data" / "final"
CODES = ROOT / "config" / "codes.json"

# любой id/name, начинающийся с "z"
ANY_Z = re.compile(r'\b(?:id|name)\s*=\s*"(z[^"]*)"')

# текущий шаблон Z_ANCHOR
STRICT = re.compile(r'^z\d+(?:_\d+)*$')


def main():
    cfg = json.loads(CODES.read_text(encoding="utf-8"))
    codes = [k for k in cfg.keys() if not k.startswith("_") and k != "upk"]

    oddballs = defaultdict(list)  # value -> list of (file, count)
    total_z = 0
    total_strict = 0

    for code in codes:
        for suf in ("ready", "structured"):
            p = FINAL / f"{code}_{suf}.html"
            if not p.exists():
                continue
            t = p.read_text(encoding="utf-8")
            counts = defaultdict(int)
            for m in ANY_Z.finditer(t):
                counts[m.group(1)] += 1
                total_z += 1
                if STRICT.match(m.group(1)):
                    total_strict += 1
            for val, c in counts.items():
                if not STRICT.match(val):
                    oddballs[val].append((p.name, c))

    print(f"Просканировано кодов: {len(codes)} (без upk)")
    print(f"Всего z-якорей:       {total_z}")
    print(f"Покрыто Z_ANCHOR:     {total_strict}")
    print(f"НЕ покрыто:           {total_z - total_strict}")
    print(f"Уникальных НЕ-матч.:  {len(oddballs)}")
    print()

    if not oddballs:
        print("[OK] Все z-якоря покрыты Z_ANCHOR = z\\d+(?:_\\d+)*")
        return

    # сгруппировать по «форме» для понимания, какие классы есть
    shape_groups = defaultdict(list)
    for v in oddballs:
        shape = re.sub(r'\d+', 'N', v)
        shape_groups[shape].append(v)

    print("Классы непокрытых форматов (по «форме» — цифры заменены на N):")
    for shape in sorted(shape_groups, key=lambda s: -len(shape_groups[s])):
        examples = sorted(shape_groups[shape])[:6]
        print(f"  shape={shape!r:25}  uniq={len(shape_groups[shape]):>4}  "
              f"примеры: {examples}")

    print()
    print("Топ-30 уникальных непокрытых значений (по числу вхождений):")
    flat = sorted(oddballs.items(),
                  key=lambda kv: -sum(c for _, c in kv[1]))[:30]
    for val, files in flat:
        total = sum(c for _, c in files)
        where = ", ".join(f"{n}×{c}" for n, c in files[:3])
        more = "" if len(files) <= 3 else f" (+{len(files)-3} файлов)"
        print(f"  {val:30}  всего={total:>4}  {where}{more}")


if __name__ == "__main__":
    main()
