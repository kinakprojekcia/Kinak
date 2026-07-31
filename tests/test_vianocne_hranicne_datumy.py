# -*- coding: utf-8 -*-

from datetime import date
import importlib.util
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class VianocneHranicneDatumyTest(unittest.TestCase):
    def assert_zobrazenie(self, datum, kod, text_hlavicky, text_statusu):
        with self.subTest(datum=datum):
            hlavicka = kinak.zostav_text_hlavicky("A", datum)
            status = kinak.zostav_text_status_baru(datum)

            self.assertEqual(kod, kinak.vypocitaj_kod_liturgickej_casti(datum))
            self.assertIn(text_hlavicky, hlavicka.upper())
            self.assertIn(text_statusu, status)
            self.assertIn("Žaltár v breviári:", status)

    def test_prechod_od_stvrtej_adventnej_nedele_po_novy_rok(self):
        scenare = [
            (date(2022, 12, 24), "4AD", "ŠTVRTÝ ADVENTNÝ TÝŽDEŇ", "Žalm z 4AD zajtra 1VI"),
            (date(2022, 12, 25), "1VI", "NARODENIE PÁNA (SLÁVNOSŤ)", "Žalm z 1VI zajtra STEF"),
            (date(2022, 12, 26), "STEF", "SV. ŠTEFANA, PRVÉHO MUČENÍKA (SVIATOK)", "Žalm z STEF zajtra SJE"),
            (date(2022, 12, 31), "PDR", "POSLEDNÝ DEŇ ROKA", "Žalm z PDR zajtra PMB"),
            (date(2023, 1, 1), "PMB", "PANNY MÁRIE BOHORODIČKY (SLÁVNOSŤ)", "Žalm z PMB zajtra 2VI"),
            (date(2023, 1, 6), "1L", "ZJAVENIE PÁNA - TRAJA KRÁLI (SLÁVNOSŤ)", "Žalm z 1L zajtra 2VI"),
            (date(2023, 1, 7), "2VI", "VIANOČNÉ OBDOBIE", "Žalm z 2VI zajtra KKP"),
            (date(2023, 1, 8), "KKP", "KRST KRISTA PÁNA", "Žalm z KKP zajtra 1c1"),
            (date(2023, 1, 9), "1C", "1. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "Žalm z 1c1 zajtra 1c1"),
        ]

        for datum, kod, text_hlavicky, text_statusu in scenare:
            self.assert_zobrazenie(datum, kod, text_hlavicky, text_statusu)

    def test_svaty_rodina_a_krst_pana_v_roku_2026_2027(self):
        self.assert_zobrazenie(
            date(2026, 12, 27),
            "SR",
            "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA (SVIATOK)",
            "Žalm z SR zajtra NEV",
        )
        self.assert_zobrazenie(
            date(2027, 1, 10),
            "KKP",
            "KRST KRISTA PÁNA (SVIATOK)",
            "Žalm z KKP zajtra 1c1",
        )

    def test_krst_pana_sa_na_7_alebo_8_januara_zobrazi_ako_sviatok_krstu_pana(self):
        hlavicka = kinak.zostav_text_hlavicky("A", date(2023, 1, 8))

        self.assertIn("KRST KRISTA PÁNA", hlavicka)
        self.assertNotIn("2. VIANOČNÁ NEDEĽA", hlavicka)

    def test_vigilia_narodenia_pana_je_len_v_status_bare(self):
        datum = date(2022, 12, 24)
        hlavicka = kinak.zostav_text_hlavicky("A", datum)
        status = kinak.zostav_text_status_baru(datum)

        self.assertNotIn("Vigília:", hlavicka)
        self.assertIn("Vigília: NARODENIE PÁNA", status)


if __name__ == "__main__":
    unittest.main()
