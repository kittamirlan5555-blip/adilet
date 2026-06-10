# -*- coding: utf-8 -*-
"""Общая библиотека аудита (Фазы 2-3). READ-ONLY утилиты.

Вложенные <a> НИКОГДА не проверяем через BeautifulSoup (парсеры автозакрывают
вложенность и гейт слепнет) — только сырой re-поиск.
"""
import re
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FINAL = ROOT / "data" / "final"
SOURCE = ROOT / "data" / "source"
MAPS = ROOT / "data" / "maps"
CONFIG = ROOT / "config"
AUDIT_OUT = ROOT / "data" / "reports" / "audit"

SOURCE_NAME = {"grazhdanskiy_osob": "GKosobenniy.html",
               "informatizacii": "obINFORM.html"}

ENTITIES = {"&nbsp;": " ", "&quot;": '"', "&amp;": "&", "&lt;": "<",
            "&gt;": ">", "&laquo;": "«", "&raquo;": "»", "&mdash;": "—",
            "&ndash;": "–", "&#171;": "«", "&#187;": "»", "&#8212;": "—",
            "&shy;": ""}

RE_SCRIPT = re.compile(r"<(script|style)\b.*?</\1\s*>", re.I | re.S)
RE_COMMENT = re.compile(r"<!--.*?-->", re.S)
# декорация структуризатора: дублирует текст заголовка главы/раздела/параграфа
RE_LABEL = re.compile(
    r'<span\b[^>]*class="(?:chapter|paragraph|part|section)-label"[^>]*>.*?</span\s*>',
    re.I | re.S)


class TextMap:
    """Текст без тегов (схлопнутые пробелы, известные entity развёрнуты) +
    pos_map: индекс символа текста -> позиция в сыром HTML."""

    def __init__(self, raw, drop_script=True, strip_labels=False):
        self.raw = raw
        blocked = []
        if drop_script:
            for rx in (RE_SCRIPT, RE_COMMENT):
                for m in rx.finditer(raw):
                    blocked.append((m.start(), m.end()))
        if strip_labels:
            for m in RE_LABEL.finditer(raw):
                blocked.append((m.start(), m.end()))
        blocked.sort()
        text, pos = [], []
        i, n, b = 0, len(raw), 0
        in_tag = False
        last_ws = True
        while i < n:
            if b < len(blocked) and i >= blocked[b][0]:
                i = blocked[b][1]
                b += 1
                continue
            ch = raw[i]
            if ch == "<":
                in_tag = True
                i += 1
                continue
            if in_tag:
                if ch == ">":
                    in_tag = False
                i += 1
                continue
            if ch == "&":
                semi = raw.find(";", i, i + 9)
                ent = raw[i:semi + 1] if semi != -1 else None
                if ent in ENTITIES:
                    rep = ENTITIES[ent]
                    if rep and not (rep == " " and last_ws):
                        if rep == " ":
                            text.append(" ")
                            pos.append(i)
                            last_ws = True
                        else:
                            text.append(rep)
                            pos.append(i)
                            last_ws = False
                    i = semi + 1
                    continue
            if ch.isspace() or ch == "\xa0":
                if not last_ws:
                    text.append(" ")
                    pos.append(i)
                    last_ws = True
                i += 1
                continue
            text.append(ch)
            pos.append(i)
            last_ws = False
            i += 1
        self.text = "".join(text).strip()
        self.pos = pos
        # вариант БЕЗ пробелов вообще — канонический инвариант проекта (§6.1:
        # ''.join(get_text().split())); межтеговые пробелы форм не считаются.
        nows, npos = [], []
        for ch, p in zip(self.text, self.pos):
            if ch != " ":
                nows.append(ch)
                npos.append(p)
        self.nows = "".join(nows)
        self.nows_pos = npos

    def raw_at_nows(self, ni, width=200):
        if not self.nows_pos:
            return ""
        ni = max(0, min(ni, len(self.nows_pos) - 1))
        rp = self.nows_pos[ni]
        return self.raw[max(0, rp - width // 2): rp + width // 2]

    def raw_at(self, ti, width=200):
        """Сырой HTML-сниппет вокруг текстовой позиции ti."""
        if not self.pos:
            return ""
        ti = max(0, min(ti, len(self.pos) - 1))
        rp = self.pos[ti]
        return self.raw[max(0, rp - width // 2): rp + width // 2]


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


# ---------- статьи: три семейства разметки (ТЗ-03) ----------
RE_HBLOCK = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1\s*>", re.I | re.S)
RE_BBLOCK = re.compile(r"<b\b[^>]*>(.*?)</b\s*>", re.I | re.S)
RE_DIVART = re.compile(r'<div\b[^>]*data-type="статья"[^>]*>', re.I)
RE_DATanum = re.compile(r'data-number="([^"]+)"')
RE_TITLE = re.compile(r"^\s*Статья\s+(\d+(?:-\d+)*)\s*[.\s]")
RE_ANYID = re.compile(r'(?:id|name)="([^"]+)"')


def _opening_tag(raw, start):
    end = raw.find(">", start)
    return raw[start:end + 1] if end != -1 else raw[start:start + 200]


def article_marks(raw):
    """Все маркеры статей: [(pos, num, anchor|None, family)]."""
    out = []
    for m in RE_HBLOCK.finditer(raw):
        inner_txt = strip_tags(m.group(2))
        t = RE_TITLE.match(inner_txt)
        if t:
            anc = RE_ANYID.search(_opening_tag(raw, m.start()))
            if not anc:
                anc = RE_ANYID.search(m.group(2)[:200])
            out.append((m.start(), t.group(1), anc.group(1) if anc else None, "h"))
            continue
        # СЛИТЫЙ заголовок («Глава 4. Сделки Статья 147. …», прецеденты
        # zhilishniy/grazhdanskiy): «Статья N.» ВНУТРИ h-блока не в начале —
        # маркер ставим на позицию вхождения в raw (нужно для source-файлов,
        # где слияние не расщеплено)
        em = re.search(r"Статья\s+(\d+(?:-\d+)*)\s*\.", m.group(2))
        if em and not inner_txt.lower().startswith("статья"):
            out.append((m.start(2) + em.start(), em.group(1), None, "h-embed"))
    for m in RE_BBLOCK.finditer(raw):
        t = RE_TITLE.match(strip_tags(m.group(1)))
        if not t:
            continue
        # якорь: сперва ВНУТРИ <b> (ready: <b><a id="zN"></a>Статья…), затем назад
        anc = RE_ANYID.search(m.group(1)[:200])
        if not anc:
            window = raw[max(0, m.start() - 300):m.start()]
            for am in RE_ANYID.finditer(window):
                anc = am
        out.append((m.start(), t.group(1), anc.group(1) if anc else None, "b"))
    for m in RE_DIVART.finditer(raw):
        tag = m.group(0)
        t = RE_DATanum.search(tag)
        if not t or not re.fullmatch(r"\d+(?:-\d+)*", t.group(1)):
            continue
        anc = RE_ANYID.search(tag) or RE_ANYID.search(raw[m.end():m.end() + 300])
        out.append((m.start(), t.group(1), anc.group(1) if anc else None, "div"))
    out.sort()
    return out


def article_clusters(raw):
    """Маркеры одной статьи в радиусе 600 симв сливаются в один экземпляр.
    -> [(pos, num, anchor|None, families:set)] в порядке документа."""
    clusters = []
    for pos, num, anc, fam in article_marks(raw):
        if clusters and clusters[-1][1] == num and pos - clusters[-1][0] < 600:
            p, n, a, f = clusters[-1]
            clusters[-1] = (p, n, a or anc, f | {fam})
        else:
            clusters.append((pos, num, anc, {fam}))
    return clusters


# ---------- ссылки ----------
RE_A_PAIR = re.compile(r'<a\b[^>]*?href="([^"]*)"[^>]*>(.*?)</a\s*>', re.I | re.S)
RE_NESTED_CLOSE = re.compile(r"</a>\s*</a>")
RE_DOUBLE_HREF = re.compile(r"<a[^>]*href=[^>]*href=")
RE_IDS = re.compile(r'(?:id|name)="([^"]+)"')


def links_of(raw):
    """[(pos, href, text, raw_match)] всех <a href>."""
    return [(m.start(), m.group(1), strip_tags(m.group(2)), m.group(0))
            for m in RE_A_PAIR.finditer(raw)]


def ids_of(raw):
    return set(RE_IDS.findall(raw))


def id_positions(raw):
    d = {}
    for m in RE_IDS.finditer(raw):
        d.setdefault(m.group(1), m.start())
    return d


def rng(slug):
    """Детерминированный генератор для воспроизводимых выборок."""
    return random.Random(f"audit-2026-{slug}")


def doc_files(slug):
    return {f: FINAL / f"{slug}_{f}.html"
            for f in ("structured", "ready")
            if (FINAL / f"{slug}_{f}.html").exists()}


def source_file(slug):
    p = SOURCE / SOURCE_NAME.get(slug, f"{slug}.html")
    return p if p.exists() else None


def all_slugs():
    out = {}
    for p in sorted(FINAL.glob("*_ready.html")):
        out.setdefault(p.name[:-len("_ready.html")], set()).add("ready")
    for p in sorted(FINAL.glob("*_structured.html")):
        out.setdefault(p.name[:-len("_structured.html")], set()).add("structured")
    return sorted(out)
