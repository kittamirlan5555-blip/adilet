# -*- coding: utf-8 -*-
"""Тесты ЛЕЧЕНИЯ 02_fix_internal_links (2026-06-10, laws3 Фаза 1).

Закрепляют: (а) SEP_PAT знает все сепараторы перечней включая en/em-dash —
диапазоны «2 – 5» больше не подменяются фолбэком « и »; (б) центральный
инвариант-гейт _vis: замена, меняющая видимый текст, отвергается.

Запуск: PYTHONIOENCODING=utf-8 python -m unittest tests.test_02_heal -v
"""
import re
import importlib.util
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

spec = importlib.util.spec_from_file_location(
    "fix02", SCRIPTS / "pipeline" / "02_fix_internal_links.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class TestSepPat(unittest.TestCase):
    """Регресс порчи диапазонов: сепаратор обязан ЗАХВАТЫВАТЬСЯ как есть."""

    def _cap(self, sep):
        m = re.search("(" + M.SEP_PAT + ")" + re.escape("5"), f"пунктами 2{sep}5")
        return m.group(1) if m else None

    def test_all_separators_captured(self):
        for sep in (", ", " – ", " — ", " - ", " и ", " или "):
            self.assertEqual(self._cap(sep), sep,
                             f"сепаратор {sep!r} должен захватываться (не фолбэк!)")

    def test_en_dash_range_keeps_dash(self):
        # точный сценарий byudzhet-152: «пунктами 2 – 5» — раньше sep_m=None -> ' и '
        m = re.search("(" + M.SEP_PAT + ")5", "пунктами 2 – 5 настоящей статьи")
        self.assertIsNotNone(m)
        self.assertIn("–", m.group(1))


class TestVisGate(unittest.TestCase):
    """Центральный гейт: видимый текст замены == видимому тексту оригинала."""

    def test_wrap_passes(self):
        old = "пунктами 2 – 5"
        new = '<a href="#z1">пунктами 2</a> – <a href="#z2">5</a>'
        self.assertEqual(M._vis(old), M._vis(new))

    def test_corruption_rejected(self):
        old = "пунктами 2 – 5"
        corrupted = '<a href="#z1">пунктами 2</a> и <a href="#z2">5</a>'
        self.assertNotEqual(M._vis(old), M._vis(corrupted),
                            "подмена «–» на «и» обязана ловиться гейтом")

    def test_nbsp_tolerated(self):
        self.assertEqual(M._vis("статьи&nbsp;5"), M._vis("статьи 5"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
