# -*- coding: utf-8 -*-
"""Регресс: датированные истор. отсылки nalog ст.828/833/848 на НК-2017
(K1700000120) ДОЛЖНЫ классифицироваться 74_freshness как hist_links
(легитимно, преемник->отменённый акт), а НЕ как ROOT-stale (иначе strict-гейт
ложно упадёт / кто-то «починит» подменой НГР на 2025, сломав датированную фразу).

Инвариант: nalog = ПРЕЕМНИК K1700000120, т.е. STALE_REMAP["K1700000120"][0] ==
doc_id(nalog) из codes.json. На этом строится hist_links-исключение (74 стр.252).

Запуск: python -m unittest tests.test_nalog_hist_2017 -v
"""
import re
import json
import importlib.util
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent

spec = importlib.util.spec_from_file_location(
    "fresh74", SCRIPTS / "audit" / "74_code_freshness_check.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

OLD = "K1700000120"


class TestNalogHist2017(unittest.TestCase):

    def setUp(self):
        codes = json.loads((ROOT / "maps" / "codes.json").read_text(encoding="utf-8"))
        self.nalog_id = codes["nalog"]["doc_id"]

    def test_successor_invariant(self):
        """K1700000120 отмечен протухшим И его преемник = наш nalog."""
        self.assertIn(OLD, M.STALE_REMAP, "K1700000120 должен быть в STALE_REMAP")
        self.assertEqual(M.STALE_REMAP[OLD][0], self.nalog_id,
                         "преемник НК-2017 обязан быть doc_id(nalog) — иначе "
                         "ссылки nalog->K1700000120 не попадут в hist_links")

    def test_dated_refs_present_and_root(self):
        """В nalog есть >=5 ROOT-ссылок на K1700000120 (датированные отсылки 828/833/848)."""
        html = (ROOT / "final" / "nalog_structured.html").read_text(encoding="utf-8")
        roots = len(re.findall(r'href="https://adilet\.zan\.kz/rus/docs/'
                               + OLD + r'"', html))
        self.assertGreaterEqual(roots, 5,
                                f"ожидали >=5 root-ссылок на {OLD}, нашли {roots}")

    def test_classified_hist_not_stale(self):
        """74_freshness на nalog: ROOT-stale=0, K1700000120 учтён как hist (не stale)."""
        # повторяем классификацию 74 (стр.247-269) на nalog без печати/exit
        own = M.own_docids()
        files = M.files_for(["nalog"])
        root_stale = 0
        hist = 0
        for p in files:
            slug = re.sub(r"_(ready|structured)$", "", p.stem)
            own_id = self.nalog_id if slug == "nalog" else None
            for (d, kind), n in M.scan_file_links(p).items():
                if d not in M.STALE_REMAP:
                    continue
                if M.STALE_REMAP[d][0] == own_id:        # hist_links
                    hist += n
                    continue
                if (slug, d) in M.HISTORICAL_DATED:
                    hist += n
                    continue
                if slug in M.WAITING_REVIEW:
                    continue
                if kind == "root":
                    root_stale += n
        self.assertEqual(root_stale, 0, "nalog не должен иметь ROOT-stale ссылок")
        self.assertGreaterEqual(hist, 10, "K1700000120 (обе формы ×5) должен быть в hist")


if __name__ == "__main__":
    unittest.main()
