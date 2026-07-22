# -*- coding: utf-8 -*-
"""BLOCK 3 — манифест тяжёлых артефактов (вне git) для масштаба 400+ доков.

Тяжёлые каталоги (source/final/derived/deliverables) в git не тянутся (сотни МБ →
ГБ). Держим их НА ДИСКЕ, а в git — этот манифест: path+size+sha256+mtime по каждому
файлу. Манифест = гарантия целостности: любой может проверить, что его набор данных
совпадает с эталоном, и увидеть, чего не хватает / что изменилось.

    python scripts/data_manifest.py            # СГЕНЕРИРОВАТЬ manifests/data_manifest.json
    python scripts/data_manifest.py --verify    # СВЕРИТЬ диск с манифестом (ничего не пишет)

Восстановление данных — см. docs/DATA_LAYOUT.md (регенерация пайплайном из source/,
либо получить архив у владельца и проверить этим манифестом).
"""
import hashlib, io, json, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEAVY = ["source", "final", "derived", "deliverables"]
MANIFEST = ROOT / "manifests" / "data_manifest.json"
# регенерируемый кэш/мусор — в манифест НЕ включаем (не эталонные данные)
SKIP_DIRS = {"_registry_cache", "__pycache__"}


def sha256(p, buf=1 << 20):
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(buf)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def walk(dirname):
    base = ROOT / dirname
    if not base.exists():
        return []
    out = []
    for p in sorted(base.rglob("*")):
        if p.is_dir():
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        out.append(p)
    return out


def build():
    manifest = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "root_hint": str(ROOT.name),
                "dirs": {}}
    grand_n = grand_sz = 0
    for d in HEAVY:
        files = walk(d)
        entries = []
        tot = 0
        for p in files:
            sz = p.stat().st_size
            entries.append({"path": str(p.relative_to(ROOT)).replace("\\", "/"),
                            "size": sz, "sha256": sha256(p),
                            "mtime": int(p.stat().st_mtime)})
            tot += sz
        manifest["dirs"][d] = {"files": len(entries), "bytes": tot, "entries": entries}
        grand_n += len(entries); grand_sz += tot
        print(f"  {d:14} {len(entries):5} файлов  {tot/1e6:9.1f} MB")
    manifest["total_files"] = grand_n
    manifest["total_bytes"] = grand_sz
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {'ИТОГО':14} {grand_n:5} файлов  {grand_sz/1e6:9.1f} MB  -> {MANIFEST.relative_to(ROOT)}")


def verify():
    if not MANIFEST.exists():
        sys.exit("нет манифеста — сначала запусти без --verify")
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    missing = changed = ok = extra = 0
    on_disk_now = {str(p.relative_to(ROOT)).replace("\\", "/") for d in HEAVY for p in walk(d)}
    in_manifest = set()
    for d, info in man["dirs"].items():
        for e in info["entries"]:
            in_manifest.add(e["path"])
            p = ROOT / e["path"]
            if not p.exists():
                missing += 1
                if missing <= 10:
                    print(f"  ОТСУТСТВУЕТ {e['path']}")
                continue
            if p.stat().st_size != e["size"] or sha256(p) != e["sha256"]:
                changed += 1
                if changed <= 10:
                    print(f"  ИЗМЕНЁН     {e['path']}")
            else:
                ok += 1
    extra = len(on_disk_now - in_manifest)
    print(f"\nсверка: ok={ok}  ОТСУТСТВУЕТ={missing}  ИЗМЕНЁН={changed}  "
          f"новых-вне-манифеста={extra}")
    print("ВЕРДИКТ:", "ЦЕЛОСТНО ✅" if (missing == 0 and changed == 0) else "ЕСТЬ РАСХОЖДЕНИЯ ⚠")
    sys.exit(0 if (missing == 0 and changed == 0) else 1)


if __name__ == "__main__":
    (verify if "--verify" in sys.argv else build)()
