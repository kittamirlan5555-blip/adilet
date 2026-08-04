# -*- coding: utf-8 -*-
"""Сборка deliverables/scripts_delivery/ — КОД конвейеров для шефа (не данные).

Структура пакета ПОВТОРЯЕТ структуру репозитория, иначе ломаются импорты:
скрипты делают `sys.path.insert(0, parents[1]); import paths` и зовут друг друга
по относительным путям (scripts/pipeline/..., scripts/audit/...).

НЕ кладём: тяжёлые данные (chunks.jsonl / index.faiss / embed_kit/model 2.2 ГБ),
одноразовые фиксы (scripts/audit/f0*, r2_*, r3_*, r4_*), __pycache__, ключи/.env.
"""
import io, sys, json, shutil, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DST = ROOT / "deliverables" / "scripts_delivery"

# --- состав пакета: (откуда, куда) ---
PIPELINE = ["01_build_article_map.py", "02_fix_internal_links.py", "03_find_external_npa.py",
            "06_finalize.py", "07_add_subpoint_anchors.py", "10_cross_code_refs.py",
            "11_structure_html.py", "13_cleanup_html.py", "18_strip_links_in_notes.py",
            "68_link_canon.py", "71_fullspan_wrap.py", "72_external_root_link.py",
            "73_fullspan_chains.py", "76_mapping_gap_report.py",
            "pipeline.py", "chunk_npa.py"]
# verify.py зовёт 64/67/69/71_gates/74/75 — без них гейт не запустится
AUDIT = ["64_final_verify.py", "67_independent_verify.py", "69_sixcheck_laws.py",
         "71_gates.py", "74_code_freshness_check.py", "75_crosscode_verify.py"]
VECTOR = ["embedder.py", "f_full_chunks.py", "c_summarize.py", "g_build_index.py",
          "i_retrieval_eval.py"]
DRIVER = ["01_ingest_adilet.py", "02_batch_run.py"]
MAPS = ["npa_mapping.json", "codes.json", "corpus_registry.json"]


def main():
    if DST.exists():
        shutil.rmtree(DST)
    copied = []

    def cp(src: Path, rel: str):
        dst = DST / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)

    cp(ROOT / "scripts/paths.py", "scripts/paths.py")
    cp(ROOT / "scripts/verify.py", "scripts/verify.py")
    for f in PIPELINE:
        cp(ROOT / "scripts/pipeline" / f, f"scripts/pipeline/{f}")
    for f in AUDIT:
        cp(ROOT / "scripts/audit" / f, f"scripts/audit/{f}")
    for f in VECTOR:
        cp(ROOT / "scripts/vector" / f, f"scripts/vector/{f}")
    for f in DRIVER:
        cp(ROOT / "pilot" / f, f"pilot/{f}")
    for f in MAPS:
        cp(ROOT / "maps" / f, f"maps/{f}")
    # embed_kit БЕЗ model/ (2.2 ГБ весов) и __pycache__
    for f in ("embed.py", "requirements.txt", "README.md"):
        p = ROOT / "embed_kit" / f
        if p.exists():
            cp(p, f"embed_kit/{f}")

    print(f"скопировано файлов: {len(copied)}")
    for grp in ("scripts/pipeline", "scripts/audit", "scripts/vector", "pilot",
                "maps", "embed_kit", "scripts/"):
        n = len([c for c in copied if c.startswith(grp)])
        print(f"   {grp:22s} {n}")

    # ---------- САМОДОСТАТОЧНОСТЬ ----------
    print("\n--- проверка самодостаточности ---")
    have = {Path(c).name for c in copied}
    missing = {}
    for p in DST.rglob("*.py"):
        txt = p.read_text(encoding="utf-8", errors="replace")
        for ref in set(re.findall(r'"([0-9a-z_]+\.py)"', txt)) | \
                   set(re.findall(r"'([0-9a-z_]+\.py)'", txt)):
            if ref not in have:
                missing.setdefault(ref, []).append(p.relative_to(DST).as_posix())
    if missing:
        for ref, who in sorted(missing.items()):
            print(f"   ОТСУТСТВУЕТ {ref}  <- зовут: {', '.join(who[:3])}")
    else:
        print("   OK: все вызываемые .py есть в пакете")

    # абсолютные пути с машины разработчика
    abs_hits = []
    for p in DST.rglob("*"):
        if p.is_file() and p.suffix in (".py", ".md", ".txt", ".json"):
            for m in re.finditer(r"[A-Za-z]:\\\\?Users|/Users/[a-z]|Desktop[\\/]ADILETkz",
                                 p.read_text(encoding="utf-8", errors="replace")):
                abs_hits.append((p.relative_to(DST).as_posix(), m.group(0)))
    print(f"   абсолютные пути с машины: {len(abs_hits)}"
          + ("" if not abs_hits else f"  {abs_hits[:5]}"))

    # ---------- БЕЗОПАСНОСТЬ ----------
    print("\n--- скан секретов ---")
    pats = {"sk-": r"sk-[A-Za-z0-9]{8,}", "api_key": r"api[_-]?key\s*[=:]\s*['\"][^'\"]{8,}",
            "token": r"token\s*[=:]\s*['\"][^'\"]{8,}",
            "password": r"password\s*[=:]\s*['\"][^'\"]{4,}"}
    total = 0
    for name, pat in pats.items():
        hits = []
        for p in DST.rglob("*"):
            if p.is_file():
                t = p.read_text(encoding="utf-8", errors="replace")
                for m in re.finditer(pat, t, re.I):
                    hits.append((p.relative_to(DST).as_posix(), m.group(0)[:40]))
        total += len(hits)
        print(f"   {name:10s} совпадений: {len(hits)}" + ("" if not hits else f"  {hits[:3]}"))
    print(f"   ИТОГО потенциальных секретов: {total}")


if __name__ == "__main__":
    main()
