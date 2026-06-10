"""
Скрипт 14: Финальный sweep — линкует оставшиеся «статью/статьи/статьёй N
настоящего Кодекса» в готовом HTML.

Работает на уровне строки (не через BS4), чтобы быть быстрым на больших файлах
(КоАП ~4 МБ, УПК ~3 МБ, Налоговый ~5 МБ).

Логика:
  1. Разбираем HTML на сегменты внутри/вне <a>…</a>.
  2. В сегментах ВНЕ <a> ищем 'статья N' (любая падежная форма), где N в
     article_map, и сразу за N идёт ' настоящего/настоящей/настоящим Кодекса/у/ом'.
  3. Оборачиваем найденный фрагмент в <a href="…">…</a>.

Использование:
  python scripts/14_sweep_remaining_internal_articles.py \
    --input data/final/upk_ready.html \
    --output data/final/upk_ready.html \
    --map data/maps/article_map_upk.json \
    --doc-id K1400000231
"""
import argparse
import json
import re
from pathlib import Path

ARTICLE_RE = re.compile(
    r'\bстат(?:ь[яиейюёямих]+|ей)\s+(\d+(?:-\d+)?)(?!\d)'
    r'(?=\s+настоящ(?:его\s+[Кк]одекса|ему\s+[Кк]одексу|им\s+[Кк]одексом|ей\s+[Сс]тат))',
    re.UNICODE
)

# We also need to skip article HEADERS (e.g., "Статья 5." inside <b>...)
# When a match is the start of a header context, skip. Heuristic: skip when
# the match is followed by ". " + capital letter.
def is_header_position(text, m):
    after = text[m.end():m.end() + 6]
    return bool(re.match(r'\s*\.\s+[А-ЯЁA-Z]', after))


def split_outside_anchors(html: str):
    """Yield (kind, text) tuples where kind = 'outside' or 'inside_a'.
    Outside chunks are safe to modify; inside_a chunks must be passed through.
    """
    out = []
    pos = 0
    open_re = re.compile(r'<a\b[^>]*>', re.IGNORECASE)
    close_re = re.compile(r'</a\s*>', re.IGNORECASE)
    depth = 0
    while pos < len(html):
        if depth == 0:
            m = open_re.search(html, pos)
            if not m:
                yield 'outside', html[pos:]; break
            if m.start() > pos:
                yield 'outside', html[pos:m.start()]
            yield 'tag', m.group(0)
            pos = m.end()
            depth = 1
        else:
            # find next open or close
            mo = open_re.search(html, pos)
            mc = close_re.search(html, pos)
            if mc is None:
                # broken HTML, dump rest
                yield 'inside', html[pos:]
                break
            if mo and mo.start() < mc.start():
                # nested <a> opening — already abnormal; pass through
                yield 'inside', html[pos:mo.end()]
                pos = mo.end()
                depth += 1
            else:
                yield 'inside', html[pos:mc.start()]
                yield 'tag', mc.group(0)
                pos = mc.end()
                depth -= 1


def sweep(input_path: Path, output_path: Path, map_path: Path, doc_id: str, base_url="https://adilet.zan.kz"):
    article_map = json.loads(map_path.read_text(encoding="utf-8"))
    html = input_path.read_text(encoding="utf-8")

    new_parts = []
    added = 0
    for kind, chunk in split_outside_anchors(html):
        if kind != 'outside':
            new_parts.append(chunk)
            continue
        # apply pattern
        repls = []
        for m in ARTICLE_RE.finditer(chunk):
            art_num = m.group(1)
            if art_num not in article_map:
                continue
            if is_header_position(chunk, m):
                continue
            repls.append((m.start(), m.end(), m.group(0), art_num))
        if not repls:
            new_parts.append(chunk)
            continue
        # build replaced chunk
        out_parts = []
        last = 0
        for start, end, full, art_num in repls:
            out_parts.append(chunk[last:start])
            anchor = article_map[art_num]
            href = f"{base_url}/rus/docs/{doc_id}#{anchor}"
            out_parts.append(f'<a href="{href}">{full}</a>')
            last = end
            added += 1
        out_parts.append(chunk[last:])
        new_parts.append(''.join(out_parts))

    new_html = ''.join(new_parts)
    output_path.write_text(new_html, encoding="utf-8")
    print(f"Sweep added: {added} article links → {output_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--doc-id", required=True)
    ap.add_argument("--base-url", default="https://adilet.zan.kz")
    args = ap.parse_args()
    sweep(Path(args.input), Path(args.output), Path(args.map), args.doc_id, args.base_url)


if __name__ == "__main__":
    main()
