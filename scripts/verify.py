# -*- coding: utf-8 -*-
"""ЕДИНАЯ КОМАНДА ВЕРИФИКАЦИИ (§6/§7 CLAUDE.md). READ-ONLY.

Оркестрирует существующие гейты, ничего не дублируя и не меняя:
  на документ:  71_gates --strict      (G1-G6: nested/href/висячие/cross-code/дифф форм)
                75_crosscode_verify --strict
                74_code_freshness_check --strict
                76_mapping_gap_report  (gap-гейт; строгий только с --strict-gaps)
  на корпус (--all): + 67_independent_verify, 64_final_verify, 69_sixcheck_laws
                (маркеры clean= / mismatch= из их вывода; сами скрипты не тронуты)

Запуск:
  python scripts/verify.py --all                  # весь корпус
  python scripts/verify.py socialnyy upk          # выбранные документы
  python scripts/verify.py --all --strict-gaps    # сдаточный режим: гэпы валят гейт

Exit 0 = все гейты PASS. Любой FAIL -> exit 1.
Сводка -> reports/verify_summary.txt. ВАЖНО (§6): этот раннер слеп к границам
спанов и корректности целей — спот-чек руками он не заменяет.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths

PIPELINE = Path(__file__).resolve().parent / "pipeline"
AUDIT = Path(__file__).resolve().parent / "audit"

ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def run(cmd):
    """(returncode, stdout+stderr) дочернего гейта; декодируем как UTF-8."""
    r = subprocess.run([sys.executable, *cmd], cwd=paths.ROOT, env=ENV,
                       capture_output=True)
    out = r.stdout.decode("utf-8", errors="replace") + \
        r.stderr.decode("utf-8", errors="replace")
    return r.returncode, out


def docs_in_final():
    seen = []
    for p in sorted(paths.FINAL.glob("*.html")):
        slug = re.sub(r"_(ready|structured)$", "", p.stem)
        if slug not in seen:
            seen.append(slug)
    return seen


def marker(out, pattern):
    """ПОСЛЕДНЕЕ совпадение: итоговые строки гейтов идут в конце вывода."""
    last = None
    for m in re.finditer(pattern, out):
        last = m.group(1)
    return last


def main():
    ap = argparse.ArgumentParser(description="Единая верификация (read-only)")
    ap.add_argument("docs", nargs="*", help="слаги документов (пусто + --all = весь корпус)")
    ap.add_argument("--all", action="store_true", help="весь корпус + корпусные гейты 67/64/69")
    ap.add_argument("--strict-gaps", action="store_true",
                    help="76_mapping_gap_report валит гейт при гэпах вне сносок (режим сдачи)")
    args = ap.parse_args()

    if not args.docs and not args.all:
        ap.print_help()
        sys.exit(2)
    docs = docs_in_final() if args.all else args.docs

    results = []  # (имя, PASS|FAIL, деталь)

    def record(name, ok, detail=""):
        results.append((name, ok, detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))

    print(f"verify: документов {len(docs)}: {', '.join(docs)}\n")

    # ── per-doc гейты ────────────────────────────────────────────────────
    print(">> 71_gates --strict (G1-G6)")
    doc_args = []
    for d in docs:
        doc_args += ["--doc", d]
    rc, out = run([str(AUDIT / "71_gates.py"), *doc_args, "--strict"])
    red_docs = re.findall(r"ИТОГ (\S+): КРАСНЫХ", out)
    record("71_gates", rc == 0,
           f"RED у: {', '.join(red_docs)}" if red_docs else "")

    print(">> 75_crosscode_verify --strict")
    rc, out = run([str(AUDIT / "75_crosscode_verify.py"), *docs, "--strict"])
    record("75_crosscode", rc == 0,
           marker(out, r"\[crosscode\] ([^\n]*?) ->") or "")

    print(">> 74_code_freshness_check --strict")
    rc, out = run([str(AUDIT / "74_code_freshness_check.py"), *docs, "--strict"])
    record("74_freshness", rc == 0,
           marker(out, r"\[freshness\] ([^\n]*?)  ->") or "")

    print(">> 76_mapping_gap_report" + (" --strict" if args.strict_gaps else " (отчёт)"))
    doc_args = []
    for d in docs:
        doc_args += ["--doc", d]
    cmd = [str(PIPELINE / "76_mapping_gap_report.py"), *doc_args]
    if args.strict_gaps:
        cmd.append("--strict")
    rc, out = run(cmd)
    gaps = re.findall(r"gaps=(\d+)", out)
    detail = "gaps: " + "/".join(gaps) if gaps else ""
    record("76_gap_report", rc == 0, detail)

    # ── корпусные гейты (только --all: скрипты сами обходят весь корпус) ──
    if args.all:
        print(">> 67_independent_verify (корпус)")
        rc, out = run([str(AUDIT / "67_independent_verify.py")])
        mis = marker(out, r"\bmismatch=(\d+)")
        ext = marker(out, r"ext_mismatch=(\d+)")
        ok = rc == 0 and mis == "0" and ext == "0"
        record("67_independent", ok, f"mismatch={mis} ext={ext}")

        print(">> 64_final_verify (корпус)")
        rc, out = run([str(AUDIT / "64_final_verify.py")])
        ok = rc == 0 and marker(out, r"clean=(\w+)") == "True" \
            and marker(out, r"gettext_frozen=(\w+)") == "True"
        record("64_final", ok)

        print(">> 69_sixcheck_laws (корпус)")
        rc, out = run([str(AUDIT / "69_sixcheck_laws.py")])
        ok = rc == 0 and marker(out, r"clean=(\w+)") == "True"
        record("69_sixcheck", ok)

    # ── сводка ───────────────────────────────────────────────────────────
    failed = [r for r in results if not r[1]]
    lines = ["# verify summary", f"документы: {', '.join(docs)}", ""]
    for name, ok, detail in results:
        lines.append(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}".rstrip())
    lines.append("")
    lines.append("ИТОГ: " + ("ВСЕ ГЕЙТЫ PASS" if not failed
                             else f"FAIL: {', '.join(r[0] for r in failed)}"))
    lines.append("Напоминание §6: спот-чек 5-10 ссылок руками раннер не заменяет.")
    summary = "\n".join(lines) + "\n"
    out_fp = paths.GATES / "verify_summary.txt"
    out_fp.write_text(summary, encoding="utf-8")
    print("\n" + summary + f"-> {out_fp}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
