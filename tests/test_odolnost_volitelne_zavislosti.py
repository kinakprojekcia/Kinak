# -*- coding: utf-8 -*-

from datetime import date
import importlib.util
from pathlib import Path
import tempfile
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class FakeMaster:
    def __init__(self):
        self.attributes_calls = []
        self.geometry_calls = []
        self.configure_calls = []
        self.overrideredirect_calls = []

    def attributes(self, *args):
        self.attributes_calls.append(args)

    def geometry(self, value):
        self.geometry_calls.append(value)

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)

    def overrideredirect(self, value):
        self.overrideredirect_calls.append(value)

    def winfo_screenwidth(self):
        return 1024

    def winfo_screenheight(self):
        return 768


class OdolnostVolitelneZavislostiTest(unittest.TestCase):
    def test_logovanie_chyby_nepadne_ani_pri_nezapisatelnej_log_ceste(self):
        povodne_enable = kinak.ENABLE_DIAGNOSTICS
        povodny_log_path = kinak.LOG_PATH
        povodny_stderr = kinak.sys.stderr

        class BrokenStderr:
            def write(self, _text):
                raise RuntimeError("stderr unavailable")

        with tempfile.TemporaryDirectory() as temp:
            kinak.ENABLE_DIAGNOSTICS = True
            kinak.LOG_PATH = Path(temp) / "neexistujuci" / "diagnostika.txt"
            kinak.sys.stderr = BrokenStderr()
            try:
                kinak.log_exception("test logging fallback", RuntimeError("boom"))
                kinak.log_info("info without writable log")
            finally:
                kinak.ENABLE_DIAGNOSTICS = povodne_enable
                kinak.LOG_PATH = povodny_log_path
                kinak.sys.stderr = povodny_stderr

    def test_vespery_vratia_false_ak_chybaju_requests_alebo_bs4(self):
        with tempfile.TemporaryDirectory() as temp:
            vystup = Path(temp) / "vespery.txt"
            povodne_requests = kinak.requests
            povodne_bs = kinak.BeautifulSoup
            try:
                kinak.requests = None
                kinak.BeautifulSoup = object
                self.assertFalse(kinak.stiahni_vespery_z_breviar(date(2026, 6, 7), vystup))
                self.assertFalse(vystup.exists())

                kinak.requests = object()
                kinak.BeautifulSoup = None
                self.assertFalse(kinak.stiahni_vespery_z_breviar(date(2026, 6, 7), vystup))
                self.assertFalse(vystup.exists())
            finally:
                kinak.requests = povodne_requests
                kinak.BeautifulSoup = povodne_bs

    def test_projection_window_move_and_maximize_funguje_bez_screeninfo(self):
        app = object.__new__(kinak.ProjectionWindow)
        app.master = FakeMaster()
        app.preferred_monitor_index = None

        povodne_get_monitors = kinak.get_monitors
        try:
            kinak.get_monitors = None
            app.move_and_maximize()
        finally:
            kinak.get_monitors = povodne_get_monitors

        self.assertEqual(app.master.attributes_calls, [("-fullscreen", True)])
        self.assertEqual(app.master.geometry_calls, [])


if __name__ == "__main__":
    unittest.main()
