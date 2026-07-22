# -*- coding: utf-8 -*-
"""anara2 BLOCK 2: ГАРАНТИРОВАННОЕ покрытие маппинга — КАЖДЫЙ акт корпуса.

Проблема (внешний аудит): 132/295 корпусных актов НЕТ в npa_mapping — корпус их
содержит, а сослаться на них нельзя. Причина: прежний автоген брал имена только из
ИЗВЛЕЧЁННЫХ цитат, а не из ВСЕХ актов реестра.

Фикс: для каждого акта codes.json — title (чистим «- ИПС "Әділет"») + doc_id(НГР) →
ключ `"{Название}"` (голая кавычка-имя; 03 оборачивает, 72 поглощает префикс «Закон* РК»).
Это НАШИ акты — title↔НГР верны по построению (мы их ингестили), §5-сверка не нужна.
Ключ уже есть → не трогаем; конфликт (др. НГР) → не трогаем, в отчёт.

Критерий: корпусных актов без записи в маппинге = 0.
"""
import io, sys, json, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "maps" / "npa_mapping.json"


def clean_title(t):
    t = re.sub(r"\s*-\s*ИПС.*$", "", t or "")
    return re.sub(r"\s+", " ", t).strip().strip('«»"""')


def main():
    apply = "--apply" in sys.argv
    cj = json.loads((ROOT / "maps" / "codes.json").read_text(encoding="utf-8"))
    m = json.loads(MAP.read_text(encoding="utf-8"))
    mapped_ngr = {v.rstrip("_") for v in m.values()}
    # реестр: репил-статус + ПОЛНЫЙ title (codes.json режет до 120 симв — годовые
    # бюджетные акты становятся неотличимы; реестр держит полное имя с годом).
    reg = {r["ngr"].rstrip("_"): r for r in
           json.loads((ROOT / "maps" / "corpus_registry.json").read_text(encoding="utf-8"))}
    def repealed(ngr):
        return reg.get(ngr.rstrip("_"), {}).get("repealed", False)
    def best_title(did, ct):
        rt = clean_title(reg.get(did.rstrip("_"), {}).get("title", ""))
        return rt if len(rt) > len(ct) else ct

    # КЛЮЧ-ЦЕНТРИЧНО: каждому акту нужен ИМЕННО quoted-name ключ `"Название"` (его
    # ищет цитата «Законом РК "Название"»). Descriptive-ключи «законодательства о X»
    # НЕ покрывают цитату по имени — потому проверяем наличие САМОГО ключа, а не «НГР
    # где-то есть» (иначе «О техническом регулировании» пролетает, хоть НГР и мапнут).
    added, conflict, forward, skip_short = 0, [], [], 0
    want = {}                                          # act NGR -> нужный quoted-key (для отчёта покрытия)
    for s, v in cj.items():
        if s.startswith("_") or not isinstance(v, dict):
            continue
        did = v.get("doc_id", s)
        name = best_title(did, clean_title(v.get("title", "")))
        if len(name) < 6 or not re.match(r"^[А-ЯЁ]", name):
            skip_short += 1
            continue
        key = f'"{name}"'
        want[did.rstrip("_")] = key
        if key in m:
            if m[key].rstrip("_") != did.rstrip("_"):
                if repealed(m[key]) and not repealed(did):
                    forward.append((key, m[key], did))
                    if apply:
                        m[key] = did
                    added += 1
                else:
                    conflict.append((key, m[key], did))
            continue                                   # ключ уже есть и ведёт куда надо
        if apply:
            m[key] = did
        added += 1

    if apply:
        MAP.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # пере-проверка ПО КЛЮЧУ: у каждого акта его quoted-name ключ есть и ведёт на него?
    still = [(ngr, key) for ngr, key in want.items()
             if key not in m or m[key].rstrip("_") != ngr]
    print(f"добавлено ключей: {added} | forward(repealed→active): {len(forward)} | "
          f"конфликтов: {len(conflict)} | пропущено (не-акт): {skip_short}")
    print(f"npa_mapping теперь: {len(m)} ключей")
    print(f"АКТОВ БЕЗ СВОЕГО quoted-ключа ПОСЛЕ: {len(still)} (цель 0)")
    for ngr, key in still[:15]:
        print(f"   ОСТАЛСЯ {ngr}: {key[:48]} -> {m.get(key, '—')}")
    for k, old, new in conflict[:8]:
        print(f"   CONFLICT {k[:40]!r}: {old} vs {new}")
    # unresolved-отчёт
    (ROOT / "reports" / "anara2_mapping_unresolved.json").write_text(json.dumps(
        {"conflicts": conflict, "forward": forward, "still": still}, ensure_ascii=False, indent=1),
        encoding="utf-8")


if __name__ == "__main__":
    main()
