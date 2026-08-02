# -*- coding: utf-8 -*-

from datetime import date, timedelta
import importlib.util
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
if not KINAK_PATH.exists():
    KINAK_PATH = Path(__file__).resolve().parent / "Kinak.py"
if not KINAK_PATH.exists():
    KINAK_PATH = Path(__file__).resolve().parent / "Kinak_1.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class StatusBarPrepinaceTest(unittest.TestCase):
    BEZNY_DEN = date(2026, 6, 10)
    DEN_PRED_TURICAMI = kinak.vypocitaj_datum_pohyblivych_slaveni(2026)[
        "Nedeľa zoslania Ducha Svätého (Turíce)"
    ] - timedelta(days=1)

    def test_predvolene_zobrazi_zalm_aj_zaltar(self):
        status = kinak.zostav_text_status_baru(self.BEZNY_DEN)

        self.assertIn("Žalm z", status)
        self.assertIn("zajtra", status)
        self.assertIn("Žaltár v breviári:", status)

    def test_vypnuty_zalm_nezobrazi_cast_zalmu(self):
        status = kinak.zostav_text_status_baru(
            self.BEZNY_DEN,
            zobrazit_zalm=False,
            zobrazit_zaltara=True,
        )

        self.assertNotIn("Žalm z", status)
        self.assertIn("Žaltár v breviári:", status)

    def test_vypnuty_zaltar_nezobrazi_cast_zaltara(self):
        status = kinak.zostav_text_status_baru(
            self.BEZNY_DEN,
            zobrazit_zalm=True,
            zobrazit_zaltara=False,
        )

        self.assertIn("Žalm z", status)
        self.assertNotIn("Žaltár v breviári:", status)

    def test_vypnuty_zalm_aj_zaltar_vrati_prazdny_text_ak_nie_je_vigilia(self):
        status = kinak.zostav_text_status_baru(
            self.BEZNY_DEN,
            zobrazit_zalm=False,
            zobrazit_zaltara=False,
        )

        self.assertEqual("", status)

    def test_vigilia_sa_zobrazi_aj_ked_su_zalm_a_zaltar_vypnute(self):
        status = kinak.zostav_text_status_baru(
            self.DEN_PRED_TURICAMI,
            zobrazit_zalm=False,
            zobrazit_zaltara=False,
        )

        self.assertEqual("  Vigília: NEDEĽA ZOSLANIA DUCHA SVÄTÉHO (TURÍCE)", status)

    def test_explicitna_vigilia_sa_da_skryt_prazdnym_retazcom(self):
        status = kinak.zostav_text_status_baru(
            self.DEN_PRED_TURICAMI,
            zobrazit_zalm=False,
            zobrazit_zaltara=False,
            vigilia="",
        )

        self.assertEqual("", status)


if __name__ == "__main__":
    unittest.main()
