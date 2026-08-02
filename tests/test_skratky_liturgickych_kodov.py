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


class SkratkyLiturgickychKodovTest(unittest.TestCase):
    def test_specialne_preklady_kodov_na_skratky_zalmu(self):
        scenare = [
            ("2VIN", date(2026, 1, 4), "2VI"),
            ("PS", date(2026, 2, 18), "PS"),
            ("PPS", date(2026, 2, 19), "PS"),
            ("VOKT", date(2026, 4, 6), "VPON"),
            ("VOKT", date(2026, 4, 7), "1VN"),
            ("ZP", date(2026, 1, 6), "1L"),
            ("34C", date(2025, 11, 23), "34c1"),
            ("34C", date(2026, 11, 22), "34c2"),
            ("13C", date(2025, 6, 28), "13c1"),
            ("13C", date(2026, 6, 28), "13c2"),
        ]

        for kod, datum, ocakavana_skratka in scenare:
            with self.subTest(kod=kod, datum=datum):
                self.assertEqual(
                    ocakavana_skratka,
                    kinak.format_skratku_liturgickej_casti(kod, datum),
                )

    def test_vlastne_kody_sa_pouziju_bez_zmeny(self):
        scenare = [
            ("1AD", date(2026, 11, 29)),
            ("1VN", date(2026, 4, 5)),
            ("2TS", date(2026, 5, 25)),
            ("MGR", date(2026, 9, 29)),
            ("NAVPM", date(2026, 7, 2)),
            ("NJK", date(2026, 6, 24)),
            ("PMB", date(2027, 1, 1)),
            ("PREM", date(2026, 8, 6)),
            ("STEF", date(2026, 12, 26)),
            ("TOM", date(2026, 7, 3)),
            ("VG", date(2026, 4, 4)),
            ("VPLB", date(2026, 11, 9)),
            ("ZOS", date(2026, 11, 2)),
            ("ZST", date(2026, 4, 2)),
            ("ZV", date(2026, 3, 25)),
        ]

        for kod, datum in scenare:
            with self.subTest(kod=kod, datum=datum):
                self.assertEqual(kod, kinak.format_skratku_liturgickej_casti(kod, datum))

    def test_format_skratky_dnes_a_zajtra_pre_hranicne_dni(self):
        scenare = [
            (date(2026, 2, 18), "PS zajtra PS"),
            (date(2026, 4, 5), "1VN zajtra VPON"),
            (date(2026, 4, 6), "VPON zajtra 1VN"),
            (date(2026, 4, 11), "1VN zajtra 2VN"),
            (date(2026, 5, 24), "1TS zajtra 2TS"),
            (date(2026, 6, 28), "13c2 zajtra 6L"),
            (date(2026, 11, 28), "34c2 zajtra 1AD"),
            (date(2026, 12, 25), "1VI zajtra STEF"),
            (date(2026, 12, 26), "STEF zajtra SR"),
            (date(2027, 1, 1), "PMB zajtra 2VI"),
        ]

        for datum, ocakavane in scenare:
            with self.subTest(datum=datum):
                self.assertEqual(ocakavane, kinak.format_skratky_liturgickej_casti(datum))

    def test_sv_tomas_sa_v_status_bare_zobrazi_ako_7l(self):
        # Sv. Tomáš, apoštol (3.7.) nemá v Kinak.py vlastnú skratku - zdieľa
        # spoločný mesačný kód "7L" s ostatnými júlovými sviatkami apoštolov
        # a evanjelistov (sv. Mária Magdaléna 22.7., sv. Jakub 25.7.), ktoré
        # majú spoločné odporúčané piesne "Sviatky apoštolov".
        datum = date(2026, 7, 3)

        self.assertEqual("7L", kinak.vypocitaj_kod_liturgickej_casti(datum))
        self.assertEqual("7L zajtra 13c2", kinak.format_skratky_liturgickej_casti(datum))
        self.assertIn("Žalm z 7L zajtra 13c2", kinak.zostav_text_status_baru(datum))

    def test_sv_tomas_pouziva_odporucane_piesne_zo_sviatkov_apostolov(self):
        self.assertEqual("Sviatky apoštolov", kinak.DIREKTORIUM_MAP["7L"])


if __name__ == "__main__":
    unittest.main()
