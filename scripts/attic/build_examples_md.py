"""Build ПРИМЕРЫ_сложных_статей.md by extracting REAL data from tree/ and chunks/."""
import json
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TREE = ROOT / "data" / "tree"
CHUNKS = ROOT / "data" / "chunks"
OUT = ROOT / "data" / "anara_package" / "ПРИМЕРЫ_сложных_статей.md"


def load_chunks(code):
    chunks = []
    with (CHUNKS / f"{code}.jsonl").open(encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))
    return chunks


def load_tree(code):
    return json.loads((TREE / f"{code}.json").read_text(encoding="utf-8"))


def find_article_tree(tree_data, art_num):
    for art in tree_data["articles"]:
        if art["article"] == art_num:
            return art
    return None


def render_tree_compact(art, max_subs_per_unit=15):
    lines = [f'article={art["article"]}, title="{art["title"][:80]}{"…" if len(art["title"])>80 else ""}", '
             f'status={art["status"]}, unit_type={art.get("unit_type")}, children={len(art["children"])}']
    for u in art["children"]:
        if u["number"] is None:
            lines.append(f'  [root-attach] subs={len(u.get("children",[]))}')
            continue
        nsubs = len(u.get("children", []))
        nconts = len(u.get("continuations", []))
        lines.append(f'  ├─ {u["type"]} {u["number"]} (anchor={u.get("anchor")}): подпунктов={nsubs}, продолжений={nconts}')
        for s in u.get("children", [])[:max_subs_per_unit]:
            nested = s.get("children", [])
            extra = f' [nested={len(nested)}]' if nested else ''
            lines.append(f'  │   └─ подпункт {s["number"]} (anchor={s.get("anchor")}){extra}')
        if nsubs > max_subs_per_unit:
            lines.append(f'  │   └─ … (+{nsubs - max_subs_per_unit} ещё подпунктов)')
    return "\n".join(lines)


def render_chunks(chunks_for_art, max_text=2500):
    out = []
    for ch in chunks_for_art:
        meta_json = json.dumps(ch["meta"], ensure_ascii=False)
        text = ch["text"]
        if len(text) > max_text:
            text = text[:max_text] + f"\n  …\n  [обрезано, полная длина {len(ch['text'])} chars]"
        out.append(f"**`{ch['id']}`** — char_len={ch['meta']['char_len']}\n\n"
                   f"meta:\n```json\n{meta_json}\n```\n\n"
                   f"text:\n```\n{text}\n```")
    return "\n\n---\n\n".join(out)


def section(code, art_num, why, max_text=2500):
    tree_data = load_tree(code)
    art = find_article_tree(tree_data, art_num)
    chunks = load_chunks(code)
    arts_chunks = [c for c in chunks if c["meta"]["article"] == art_num]
    parts = [
        f"## {why['header']}",
        "",
        f"**Чем сложна:** {why['why']}",
        "",
        "**Фрагмент дерева:**",
        "",
        "```",
        render_tree_compact(art),
        "```",
        "",
        f"**Чанки ({len(arts_chunks)}):**",
        "",
        render_chunks(arts_chunks, max_text=max_text),
    ]
    return "\n".join(parts)


def main():
    parts = [
        "# Примеры сложных статей — чанкер ADILETkz",
        "",
        "_Сгенерировано автоматически из `data/tree/` и `data/chunks/`. "
        "Демонстрирует, что чанкер корректно обрабатывает разные паттерны structurization._",
        "",
        "---",
        "",
    ]

    parts.append(section(
        "predprinimatel", "82",
        {"header": "1. ПК ст.82 — пункт с 13 подпунктами (включая suffix 4-1) в одном чанке",
         "why": "Пункт 3 содержит 13 подпунктов (1)–12) + suffix-подпункт 4-1) между 4) и 5)) и "
                "несколько продолжений после списка. Главное требование шефа: ВСЁ это собирается "
                "в ОДИН чанк, чтобы при векторном поиске пункт+подпункты не рвались."},
        max_text=4500,
    ))
    parts.append("\n---\n")

    parts.append(section(
        "upk", "32",
        {"header": "2. УПК ст.32 — особый формат `<br/>` (не `<p>`)",
         "why": "В УПК статьи структурированы НЕ через `<p>` теги (как в остальных кодексах), "
                "а через `<a id=\"zN\"></a>1. Текст<br/>2. Текст<br/>...`. Без правила R12 "
                "(UPK-special, разделение по `<br/>`) вся статья ушла бы одним сплошным чанком. "
                "Правило корректно разрезает на 6 частей. Также `unit_type=часть` (не пункт) — "
                "согласно правилу R3 для УК/УПК."},
        max_text=1500,
    ))
    parts.append("\n---\n")

    parts.append(section(
        "koap", "200",
        {"header": "3. КоАП ст.200 — Особенная часть, санкции «– влечёт штраф» подцеплены к части",
         "why": "Каждая часть статьи Особенной части КоАП = гипотеза правонарушения + санкция "
                "(штраф). Санкция оформлена как отдельный `<p>– влечёт штраф…</p>` (правило R8). "
                "Чанкер подцепляет санкцию как **continuation** к соответствующей части, чтобы "
                "при поиске «штраф за нарушение реализации алкоголя» нашёлся целостный фрагмент "
                "(нарушение + наказание)."},
        max_text=1500,
    ))
    parts.append("\n---\n")

    parts.append(section(
        "predprinimatel", "37",
        {"header": "4. ПК ст.37 — исключённая статья (status=repealed)",
         "why": "Статья 37 исключена Законом РК. Текст содержит только sноску об исключении. "
                "Чанкер фиксирует `status=repealed` в meta и создаёт один чанк с явным флагом "
                "«СТАТЬЯ ИСКЛЮЧЕНА» в шапке. При поиске эти чанки можно фильтровать (исключать "
                "из выдачи) либо использовать для исторической справки."},
        max_text=1500,
    ))
    parts.append("\n---\n")

    parts.append(section(
        "koap", "312",
        {"header": "5. БОНУС — КоАП ст.312, восстановлена через orphan-pickup",
         "why": "В исходном HTML заголовок написан с **латинской** C: «**C**татья 312» "
                "(U+0043 вместо кириллической С U+0421). Структуризатор не распознал — "
                "статья оказалась orphaned (вне любого `<div class=\"article\">`) и потерялась "
                "бы в чанках. Чанкер ловит этот класс багов: homoglyph-tolerant `[СCϹ]` в "
                "regex + orphan-pickup pass. Статья восстановлена, чанки помечены "
                "`orphan_pickup: true` для прозрачности."},
        max_text=1500,
    ))
    parts.append("\n---\n")

    parts.append("## Сводка покрытия")
    parts.append("")
    parts.append("| Кодекс | Статей | Чанков |")
    parts.append("|---|---:|---:|")
    for code in ("predprinimatel", "upk", "koap"):
        tree_data = load_tree(code)
        chunks = load_chunks(code)
        parts.append(f"| {code} | {len(tree_data['articles'])} | {len(chunks)} |")
    parts.append("")
    parts.append("_Полный пакет (12 кодексов, 5380 статей, 18 873 чанков) в `data/tree/` и `data/chunks/`._")

    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {OUT}, {OUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
