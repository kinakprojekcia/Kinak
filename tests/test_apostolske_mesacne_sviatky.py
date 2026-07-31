# -*- coding: utf-8 -*-

from datetime import date
import importlib.util
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
if not KINAK_PATH.exists():
    KINAK_PATH = Path(__file__).resolve().parent / "Kinak.py"
if not KINAK_PATH.exists():
    KINAK_PATH = Path(__file__).resolve().parent.parent / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class ApostolskeMesacneSviatkyTest(unittest.TestCase):
    def test_sv_marek_ma_aprilovy_mesacny_kod_mimo_nediel_a_oktavy(self):
        pripady = [
            date(2026, 4, 25),
            date(2034, 4, 25),
        ]

        for datum in pripady:
            with self.subTest(datum=datum):
                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum), datum)

                self.assertEqual("4L", kinak.vypocitaj_kod_liturgickej_casti(datum))
                self.assertIn("SV. MARKA, EVANJELISTU (Sviatok)", hlavicka)
                self.assertIn("Žalm z 4L", kinak.zostav_text_status_baru(datum))

    def test_sv_marek_neprebije_velkonocnu_nedelu_a_oktavu(self):
        pripady = [
            date(2027, 4, 25),
            date(2030, 4, 25),
            date(2032, 4, 25),
            date(2038, 4, 25),
            date(2041, 4, 25),
            date(2049, 4, 25),
        ]

        for datum in pripady:
            with self.subTest(datum=datum):
                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum), datum)

                self.assertNotEqual("4L", kinak.vypocitaj_kod_liturgickej_casti(datum))
                self.assertNotIn("SV. MARKA, EVANJELISTU", hlavicka)

    def test_oktobrove_sviatky_apostolov_a_evanjelistov_maju_kod_10l(self):
        pripady = [
            (date(2027, 10, 18), "SV. LUKÁŠA, EVANJELISTU"),
            (date(2028, 10, 28), "SV. ŠIMONA A JÚDU, APOŠTOLOV"),
        ]

        for datum, nazov in pripady:
            with self.subTest(datum=datum):
                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum), datum)

                self.assertEqual("10L", kinak.vypocitaj_kod_liturgickej_casti(datum))
                self.assertIn(f"{nazov} (Sviatok)", hlavicka)
                self.assertIn("Žalm z 10L", kinak.zostav_text_status_baru(datum))

    def test_oktobrove_sviatky_apostolov_a_evanjelistov_neprebiju_nedelu(self):
        pripady = [
            (date(2026, 10, 18), "SV. LUKÁŠA, EVANJELISTU"),
            (date(2037, 10, 18), "SV. LUKÁŠA, EVANJELISTU"),
            (date(2043, 10, 18), "SV. LUKÁŠA, EVANJELISTU"),
            (date(2048, 10, 18), "SV. LUKÁŠA, EVANJELISTU"),
            (date(2029, 10, 28), "SV. ŠIMONA A JÚDU, APOŠTOLOV"),
            (date(2035, 10, 28), "SV. ŠIMONA A JÚDU, APOŠTOLOV"),
            (date(2040, 10, 28), "SV. ŠIMONA A JÚDU, APOŠTOLOV"),
            (date(2046, 10, 28), "SV. ŠIMONA A JÚDU, APOŠTOLOV"),
        ]

        for datum, nazov in pripady:
            with self.subTest(datum=datum):
                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum), datum)
                status = kinak.zostav_text_status_baru(datum)

                self.assertNotEqual("10L", kinak.vypocitaj_kod_liturgickej_casti(datum))
                self.assertNotIn(f"{nazov} (Sviatok)", hlavicka)
                self.assertNotIn("Žalm z 10L", status)
                # Poznámka o prednosti nedele patrí výlučne do status baru
                # (zostav_text_hlavicky ju zámerne nezobrazuje, aby
                # nedochádzalo k duplicite a aby titulok okna nebol
                # zbytočne dlhý).
                self.assertNotIn(f"nedeľa má prednosť pred: {nazov}", hlavicka)
                self.assertIn(f"nedeľa má prednosť pred: {nazov}", status)


if __name__ == "__main__":
    unittest.main()
