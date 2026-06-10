# -*- coding: utf-8 -*-
"""ЮНИТ-ТЕСТЫ скриптов 72/73/74/75 на СИНТЕТИЧЕСКИХ мини-примерах HTML.

НЕ зависит от data/final — все фикстуры строятся в памяти / во временной папке,
поэтому тесты пиннят ЛОГИКУ независимо от эталонных файлов законов (их сверим
позже отдельно). Стандартная библиотека unittest + bs4 (pytest не требуется).

Запуск:
  PYTHONIOENCODING=utf-8 python -m unittest tests.test_link_scripts -v
  PYTHONIOENCODING=utf-8 python tests/test_link_scripts.py
"""
import io
import re
import json
import shutil
import tempfile
import contextlib
import importlib.util
import unittest
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


@contextlib.contextmanager
def quiet():
    """Глушит шумный stdout прогоняемых run()-ов, чтобы вывод тестов был чистым."""
    with contextlib.redirect_stdout(io.StringIO()):
        yield


def _load(modname, filename):
    """Импорт модуля с числовым префиксом (нельзя обычным import)."""
    spec = importlib.util.spec_from_file_location(modname, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M72 = _load("ext_root", "72_external_root_link.py")
M73 = _load("chains", "73_fullspan_chains.py")
M74 = _load("freshness", "74_code_freshness_check.py")
M75 = _load("crosscode", "75_crosscode_verify.py")


def soup_of(html):
    return BeautifulSoup(html, "html.parser")


# ======================================================================
# 73 — ПОЛНО-СПАНОВЫЕ ЦЕПОЧКИ (grammar на in-memory soup)
# ======================================================================
class Test73Chains(unittest.TestCase):

    def _apply_all(self, soup):
        """Прогон fixpoint-apply (как в run --apply), возврат (applied, dropped)."""
        applied, dropped, rounds = 0, [], 0
        while True:
            rounds += 1
            cs = M73.scan(soup)
            if not cs:
                break
            c = cs[0]
            dropped.extend(c["drops"])
            M73.apply_chain(c)
            applied += 1
            self.assertLess(rounds, 1000, "fixpoint runaway")
        return applied, dropped

    def test_canonical_same_article_merges(self):
        # §3 канонический пример из докстринга
        html = ('<p><a href="#z1">пунктами 4</a> и <a href="#z2">6</a> '
                '<a href="#z3">статьи 167</a> настоящего Кодекса.</p>')
        soup = soup_of(html)
        cands = M73.scan(soup)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["keep"], "#z1")
        self.assertEqual(cands[0]["drops"], ["#z2", "#z3"])
        sha0 = M73.gettext_sha(soup)
        self._apply_all(soup)
        links = soup.find_all("a")
        self.assertEqual(len(links), 1, "должна остаться ОДНА ссылка")
        self.assertEqual(links[0]["href"], "#z1", "оставляем самый левый href")
        self.assertEqual(links[0].get_text(), "пунктами 4 и 6 статьи 167")
        self.assertEqual(M73.gettext_sha(soup), sha0, "get_text инвариант")
        self.assertEqual(M73.nested_count(soup), 0)

    def test_cross_article_NOT_merged(self):
        # §4: «...статьи 132 ... статьи 143» — РАЗНЫЕ статьи, НЕ сливать.
        html = ('<p><a href="#z132">пункте 2 статьи 132</a> и '
                '<a href="#z2649">пункте 3</a> <a href="#z143">статьи 143</a></p>')
        soup = soup_of(html)
        self.assertEqual(M73.scan(soup), [], "межстатейный список не должен стать цепочкой")

    def test_cross_code_mixed_href_NOT_merged(self):
        # head -> внутр. #z, терминатор -> внешний закон: домены разные, не сливать.
        html = ('<p><a href="#z48">подпунктом 3)</a> '
                '<a href="https://adilet.zan.kz/rus/docs/Z1300000088#z9">пункта 1</a> '
                '<a href="https://adilet.zan.kz/rus/docs/Z1300000088#z4">статьи 4 Закона</a></p>')
        soup = soup_of(html)
        self.assertEqual(M73.scan(soup), [], "смешанные домены href не сливаем")

    def test_cross_code_uniform_href_merges(self):
        # все три -> ОДИН внешний docid: однородно, сливаем.
        h = "https://adilet.zan.kz/rus/docs/Z1300000088"
        html = (f'<p><a href="{h}#z48">подпунктом 3)</a> '
                f'<a href="{h}#z9">пункта 1</a> '
                f'<a href="{h}#z4">статьи 4 Закона</a></p>')
        soup = soup_of(html)
        cands = M73.scan(soup)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["keep"], f"{h}#z48", "оставляем самый левый (самый конкретный)")

    def test_plain_terminator_merges(self):
        # терминатор «статьи M» — ПЛЕЙН-текст; «настоящего Кодекса» НЕ захватываем.
        html = ('<p><a href="#z106">пунктами 3</a> и <a href="#z107">4</a> '
                'статьи 722 настоящего Кодекса.</p>')
        soup = soup_of(html)
        sha0 = M73.gettext_sha(soup)
        cands = M73.scan(soup)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["terminal"], "plain")
        self._apply_all(soup)
        links = soup.find_all("a")
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].get_text(), "пунктами 3 и 4 статьи 722")
        # остаток «настоящего Кодекса» должен остаться ВНЕ ссылки
        self.assertNotIn("настоящего", links[0].get_text())
        self.assertIn("настоящего Кодекса", soup.get_text())
        self.assertEqual(M73.gettext_sha(soup), sha0)

    def test_single_subdivision_is_NOT_chain(self):
        # одиночное «пункта 1 статьи 201» (1 атом) — работа 71, не 73.
        html = '<p><a href="#z851">пункта 1</a> <a href="#z201">статьи 201</a></p>'
        soup = soup_of(html)
        self.assertEqual(M73.scan(soup), [], "нужно >=2 подразделов")

    def test_href_multiset_gate_holds(self):
        html = ('<p><a href="#z1">пунктами 2</a>, <a href="#z2">3</a> и '
                '<a href="#z3">4</a> <a href="#z9">статьи 50</a></p>')
        soup = soup_of(html)
        href0 = M73.href_multiset(soup)
        _, dropped = self._apply_all(soup)
        href1 = M73.href_multiset(soup)
        exp = {}
        for d in dropped:
            exp[d] = exp.get(d, 0) + 1
        for k in set(href0) | set(href1):
            self.assertEqual(href0.get(k, 0) - href1.get(k, 0), exp.get(k, 0),
                             f"href multiset mismatch на {k}")

    # --- ПОКРЫТИЕ СОЕДИНИТЕЛЕЙ: и / , / ; / или (§3 «и», но грамматика шире) ---
    def _chain_one(self, html, expect_text, expect_keep="#z1"):
        """Хелпер: ровно одна цепочка, после apply один <a> с нужным текстом/href."""
        soup = soup_of(html)
        cands = M73.scan(soup)
        self.assertEqual(len(cands), 1, f"ожидалась ровно одна цепочка для {html!r}")
        sha0 = M73.gettext_sha(soup)
        self._apply_all(soup)
        links = soup.find_all("a")
        self.assertEqual(len(links), 1, "после слияния одна ссылка")
        self.assertEqual(links[0]["href"], expect_keep)
        self.assertEqual(links[0].get_text(), expect_text)
        self.assertEqual(M73.gettext_sha(soup), sha0, "get_text инвариант")
        self.assertEqual(M73.nested_count(soup), 0)

    def test_connector_comma(self):
        # запятая как соединитель списка: «1, 2 и 3»
        self._chain_one(
            '<p><a href="#z1">пунктами 1</a>, <a href="#z2">2</a> и '
            '<a href="#z3">3</a> <a href="#z9">статьи 70</a></p>',
            "пунктами 1, 2 и 3 статьи 70")

    def test_connector_semicolon(self):
        # ТОЧКА С ЗАПЯТОЙ — в реальном корпусе цепочек=0, но грамматика обязана
        # её принимать; синтетический пин, чтобы не сломать при правках RE_CONNECTOR.
        self._chain_one(
            '<p><a href="#z1">подпунктами 1)</a>; <a href="#z2">2)</a>; '
            '<a href="#z3">3)</a> <a href="#z9">статьи 5</a></p>',
            "подпунктами 1); 2); 3) статьи 5")

    def test_connector_ili(self):
        # «или» как соединитель (реальный кейс из nalog/ekologicheskiy)
        self._chain_one(
            '<p><a href="#z1">пунктами 3</a> или <a href="#z2">4</a> '
            '<a href="#z9">статьи 699</a></p>',
            "пунктами 3 или 4 статьи 699")

    def test_connector_mixed_comma_ili(self):
        # смешанные соединители в одной цепочке: «, … или …»
        self._chain_one(
            '<p><a href="#z1">пунктами 2</a>, <a href="#z2">3</a> или '
            '<a href="#z3">5</a> <a href="#z9">статьи 12</a></p>',
            "пунктами 2, 3 или 5 статьи 12")


# ======================================================================
# 73 — интеграционный прогон run(--apply) с реальными гейтами + IO
# ======================================================================
class Test73RunGates(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._final, self._reports = M73.FINAL, M73.REPORTS
        M73.FINAL = self.tmp / "final"
        M73.REPORTS = self.tmp / "reports"
        M73.FINAL.mkdir(parents=True)

    def tearDown(self):
        M73.FINAL, M73.REPORTS = self._final, self._reports
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_run_apply_passes_all_gates(self):
        # с РЕАЛЬНЫМИ якорями (id=zN), чтобы dangling==0 (жёсткий гейт 73).
        html = (
            '<html><body>'
            '<h2 id="z1">Статья 167</h2><h2 id="z9">Статья 50</h2>'
            '<p>В соответствии с <a href="#z1">пунктами 4</a> и '
            '<a href="#z2">6</a> <a href="#z9">статьи 167</a> закона.</p>'
            '</body></html>')
        (M73.FINAL / "chaintest_ready.html").write_text(html, encoding="utf-8")
        # run в apply: если хоть один assert-гейт упадёт — тест упадёт.
        with quiet():
            M73.run("chaintest", apply_mode=True)
        out = (M73.FINAL / "chaintest_ready.html").read_text(encoding="utf-8")
        s = soup_of(out)
        links = s.find_all("a")
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["href"], "#z1")
        self.assertEqual(links[0].get_text(), "пунктами 4 и 6 статьи 167")


# ======================================================================
# 72 — ВНЕШНИЕ АКТЫ -> КОРЕНЬ
# ======================================================================
def _mkphrases(pairs):
    """Повторяет логику load_phrases для синтетики (ws-гибкий, len>=16)."""
    items = []
    for phrase, docid in pairs:
        if len(phrase) < 16:
            continue
        pat = re.sub(r"\\\s+", r"\\s+", re.escape(phrase))
        items.append((re.compile(pat, re.I), phrase, docid))
    items.sort(key=lambda x: -len(x[1]))
    return items


class Test72FindInText(unittest.TestCase):
    def test_longest_first_no_overlap(self):
        phrases = _mkphrases([
            ('Законом Республики Казахстан "О банках и банковской деятельности"', "D1"),
            ('Законом Республики Казахстан "О банках"', "D2"),
        ])
        s = ('в соответствии с Законом Республики Казахстан '
             '"О банках и банковской деятельности" далее')
        spans = M72.find_in_text(s, phrases)
        self.assertEqual(len(spans), 1, "перекрытие: только самый длинный матч")
        self.assertEqual(spans[0][2], "D1")

    def test_min_len_filters_short(self):
        # фраза <16 символов отбрасывается -> нет матча
        phrases = _mkphrases([("Закон", "SHORT")])
        self.assertEqual(M72.find_in_text("это Закон такой", phrases), [])


class Test72Run(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._f, self._c, self._r = M72.FINAL, M72.CONFIG, M72.REPORTS
        M72.FINAL = self.tmp / "final"
        M72.CONFIG = self.tmp / "config"
        M72.REPORTS = self.tmp / "reports"
        for d in (M72.FINAL, M72.CONFIG):
            d.mkdir(parents=True)

    def tearDown(self):
        M72.FINAL, M72.CONFIG, M72.REPORTS = self._f, self._c, self._r
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _mapping(self, d):
        (M72.CONFIG / "npa_mapping.json").write_text(
            json.dumps(d, ensure_ascii=False), encoding="utf-8")

    def test_plain_phrase_wrapped_to_root(self):
        self._mapping({'Законом Республики Казахстан "О нотариате"': "Z970000155_"})
        html = ('<html><body><p>регулируется Законом Республики Казахстан '
                '"О нотариате" в полном объёме.</p></body></html>')
        (M72.FINAL / "exttest_ready.html").write_text(html, encoding="utf-8")
        before = soup_of(html).get_text()
        with quiet():
            M72.run("exttest", apply_mode=True, min_len=16)
        out = soup_of((M72.FINAL / "exttest_ready.html").read_text(encoding="utf-8"))
        a = out.find("a", href="https://adilet.zan.kz/rus/docs/Z970000155_")
        self.assertIsNotNone(a, "фраза должна обернуться в КОРЕНЬ без #z")
        self.assertEqual(a.get_text(), 'Законом Республики Казахстан "О нотариате"')
        self.assertEqual(out.get_text(), before, "видимый текст не меняется")
        self.assertEqual(M72.nested_count(out), 0)

    def test_partial_overlap_NOT_touched(self):
        # фраза частично уже в <a> -> PARTIAL, ничего не оборачиваем заново.
        self._mapping({'Законом Республики Казахстан "О банках"': "Z2600000258"})
        html = ('<html><body><p><a href="#z1">Законом</a> Республики Казахстан '
                '"О банках" сказано.</p></body></html>')
        (M72.FINAL / "parttest_ready.html").write_text(html, encoding="utf-8")
        before = soup_of(html).get_text()
        with quiet():
            M72.run("parttest", apply_mode=True, min_len=16)
        out = soup_of((M72.FINAL / "parttest_ready.html").read_text(encoding="utf-8"))
        self.assertIsNone(out.find("a", href=re.compile("docs/Z2600000258")),
                          "PARTIAL не должен добавлять корневую ссылку")
        self.assertEqual(out.get_text(), before)
        self.assertEqual(M72.nested_count(out), 0)


# ======================================================================
# 74 — АКТУАЛЬНОСТЬ КОДОВ
# ======================================================================
class Test74Freshness(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._f, self._c, self._r = M74.FINAL, M74.CONFIG, M74.REPORTS
        M74.FINAL = self.tmp / "final"
        M74.CONFIG = self.tmp / "config"
        M74.REPORTS = self.tmp / "reports"
        for d in (M74.FINAL, M74.CONFIG):
            d.mkdir(parents=True)

    def tearDown(self):
        M74.FINAL, M74.CONFIG, M74.REPORTS = self._f, self._c, self._r
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_stale_mapping_row_detected(self):
        # любой ключ из STALE_REMAP (подтверждённый repeal-replace) детектится
        stale = next(iter(M74.STALE_REMAP))
        (M74.CONFIG / "npa_mapping.json").write_text(
            json.dumps({"Какой-то кодекс Республики Казахстан": stale,
                        "Свежий акт": "Z9999999999"}, ensure_ascii=False),
            encoding="utf-8")
        bad = M74.check_mapping()                 # default = STALE_REMAP
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0][1], stale)

    def test_stale_link_in_file_counted(self):
        stale = next(iter(M74.STALE_REMAP))
        html = (f'<p><a href="https://adilet.zan.kz/rus/docs/{stale}">Акт</a> и '
                f'<a href="https://adilet.zan.kz/rus/docs/Z9999999999">другой</a></p>')
        p = M74.FINAL / "freshtest_ready.html"
        p.write_text(html, encoding="utf-8")
        cnt = M74.scan_file_docids(p)
        self.assertEqual(cnt[stale], 1)
        self.assertEqual(cnt["Z9999999999"], 1)
        self.assertIn(stale, M74.STALE_REMAP)

    def test_confirmed_remaps_are_our_own_codes(self):
        # §5: оба подтверждённых ремапа целятся в doc_id наших же кодексов.
        self.assertEqual(M74.STALE_REMAP["K1700000120"][0], "K2500000214")  # nalog
        self.assertEqual(M74.STALE_REMAP["K080000095_"][0], "K2500000171")  # byudzhet
        self.assertEqual(set(M74.STALE_REMAP), {"K1700000120", "K080000095_"},
                         "в авто-ремапе ТОЛЬКО подтверждённые repeal-replace")

    def test_needs_review_not_in_auto_remap(self):
        # §5: кандидаты на ручной разбор НЕ должны попадать в авто-ремап STALE_REMAP.
        for did in ("Z950002444_", "Z1500000383", "Z070000252_"):
            self.assertIn(did, M74.NEEDS_REVIEW)
            self.assertNotIn(did, M74.STALE_REMAP)

    def test_Z1400000211_not_stale_anywhere(self):
        # «О профессиональных союзах» ДЕЙСТВУЮЩИЙ — не ремапить ни авто, ни review.
        self.assertNotIn("Z1400000211", M74.STALE_REMAP)
        self.assertNotIn("Z1400000211", M74.NEEDS_REVIEW)

    def test_articular_stale_link_not_auto_remap(self):
        # §5/§9: ROOT-ссылка на протухший код = auto-remap-safe; АРТИКУЛЬНАЯ (#z) — НЕТ.
        stale = next(iter(M74.STALE_REMAP))
        html = (f'<p>акт целиком <a href="https://adilet.zan.kz/rus/docs/{stale}">x</a> '
                f'и статья <a href="https://adilet.zan.kz/rus/docs/{stale}#z1498">y</a></p>')
        p = M74.FINAL / "artstale_ready.html"
        p.write_text(html, encoding="utf-8")
        links = M74.scan_file_links(p)
        self.assertEqual(links[(stale, "root")], 1, "ROOT -> авто-ремап разрешён")
        self.assertEqual(links[(stale, "art")], 1, "#z -> НЕ авто-ремап (ручной ре-резолв)")

    def test_check_mapping_needs_review_table(self):
        # check_mapping(NEEDS_REVIEW) выписывает строки-кандидаты отдельной таблицей
        review_id = "Z1500000383"
        (M74.CONFIG / "npa_mapping.json").write_text(
            json.dumps({'Законом Республики Казахстан "Об общественных советах"': review_id,
                        "Свежий акт": "Z9999999999"}, ensure_ascii=False),
            encoding="utf-8")
        rev = M74.check_mapping(M74.NEEDS_REVIEW)
        self.assertEqual(len(rev), 1)
        self.assertEqual(rev[0][1], review_id)
        # та же строка НЕ должна светиться как подтверждённо протухшая
        self.assertEqual(M74.check_mapping(M74.STALE_REMAP), [])


# ======================================================================
# 75 — CROSS-CODE СВЕРКА ЯКОРЕЙ
# ======================================================================
class Test75CrossCode(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._f, self._m, self._c, self._r = M75.FINAL, M75.MAPS, M75.CONFIG, M75.REPORTS
        M75.FINAL = self.tmp / "final"
        M75.MAPS = self.tmp / "maps"
        M75.CONFIG = self.tmp / "config"
        M75.REPORTS = self.tmp / "reports"
        for d in (M75.FINAL, M75.MAPS, M75.CONFIG):
            d.mkdir(parents=True)
        (M75.CONFIG / "codes.json").write_text(json.dumps({
            "src": {"doc_id": "SRC000"}, "tgt": {"doc_id": "TGT000"}}),
            encoding="utf-8")
        (M75.MAPS / "article_map_tgt.json").write_text(
            json.dumps({"167": "z353"}), encoding="utf-8")

    def tearDown(self):
        M75.FINAL, M75.MAPS, M75.CONFIG, M75.REPORTS = \
            self._f, self._m, self._c, self._r
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reverse_map(self):
        rev = M75.load_reverse_map("tgt")
        self.assertEqual(rev.get("z353"), "167")

    def test_article_candidates(self):
        s = soup_of('<a href="/docs/TGT000#z353">статьи 167</a>')
        cands = M75.article_candidates(s.find("a"))
        self.assertIn("167", cands)

    def test_OK_when_anchor_matches_text(self):
        html = ('<p>в силу <a href="/docs/TGT000#z353">статьи 167</a> '
                'кодекса</p>')
        (M75.FINAL / "src_ready.html").write_text(html, encoding="utf-8")
        # run печатает отчёт; strict=False -> без exit
        with quiet():
            M75.run(["src"], strict=False, do_self=False)
        txt = (M75.REPORTS / "75_crosscode_verify.txt").read_text(encoding="utf-8")
        self.assertIn("MISMATCH=0", txt)
        self.assertIn("OK=1", txt)

    def test_MISMATCH_when_anchor_points_elsewhere(self):
        # текст говорит «статьи 999», но якорь z353 -> статья 167 по карте
        html = '<p>см. <a href="/docs/TGT000#z353">статьи 999</a></p>'
        (M75.FINAL / "src_ready.html").write_text(html, encoding="utf-8")
        with quiet():
            M75.run(["src"], strict=False, do_self=False)
        txt = (M75.REPORTS / "75_crosscode_verify.txt").read_text(encoding="utf-8")
        self.assertIn("MISMATCH=1", txt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
