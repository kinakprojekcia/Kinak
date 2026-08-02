# -*- coding: utf-8 -*-

import importlib.util
from datetime import date
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class LiturgickeVypocty2034A2035Test(unittest.TestCase):
    def test_pohyblive_slavenia_2034_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2034), date(2034, 4, 9))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2034, 12, 3),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2034, 12, 31),
            "Krst Krista Pána": date(2034, 1, 8),
            "Zvestovanie Pána*": date(2034, 3, 25),
            "Popolcová streda": date(2034, 2, 22),
            "Palmová (Kvetná nedeľa)": date(2034, 4, 2),
            "Veľkonočná nedeľa": date(2034, 4, 9),
            "Pondelok vo Veľkonočnej oktáve": date(2034, 4, 10),
            "Nedeľa Božieho milosrdenstva": date(2034, 4, 16),
            "Nanebovstúpenie Pána": date(2034, 5, 18),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2034, 5, 28),
            "Panny Márie, Matky Cirkvi": date(2034, 5, 29),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2034, 6, 1),
            "Najsvätejšej Trojice": date(2034, 6, 4),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2034, 6, 8),
            "Najsvätejšieho Srdca Ježišovho": date(2034, 6, 16),
            "Nepoškvrnené Srdce Panny Márie": date(2034, 6, 17),
            "Krista Kráľa": date(2034, 11, 26),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2034)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_pohyblive_slavenia_2035_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2035), date(2035, 3, 25))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2035, 12, 2),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2035, 12, 30),
            "Krst Krista Pána": date(2035, 1, 7),
            "Zvestovanie Pána*": date(2035, 4, 2),
            "Popolcová streda": date(2035, 2, 7),
            "Palmová (Kvetná nedeľa)": date(2035, 3, 18),
            "Veľkonočná nedeľa": date(2035, 3, 25),
            "Pondelok vo Veľkonočnej oktáve": date(2035, 3, 26),
            "Nedeľa Božieho milosrdenstva": date(2035, 4, 1),
            "Nanebovstúpenie Pána": date(2035, 5, 3),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2035, 5, 13),
            "Panny Márie, Matky Cirkvi": date(2035, 5, 14),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2035, 5, 17),
            "Najsvätejšej Trojice": date(2035, 5, 20),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2035, 5, 24),
            "Najsvätejšieho Srdca Ježišovho": date(2035, 6, 1),
            "Nepoškvrnené Srdce Panny Márie": date(2035, 6, 2),
            "Krista Kráľa": date(2035, 11, 25),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2035)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2034(self):
        pripady = [
            (date(2034, 1, 8), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2034, 2, 22), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2034, 3, 25), "ZV", "ZVESTOVANIE PÁNA", "IV."),
            (date(2034, 4, 2), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2034, 4, 6), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2034, 4, 7), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2034, 4, 8), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2034, 4, 9), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2034, 4, 16), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2034, 5, 18), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2034, 5, 28), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2034, 5, 29), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2034, 6, 4), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2034, 6, 16), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2034, 6, 17), "7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", "II."),
            (date(2034, 11, 26), "34C", "KRISTA KRÁĽA", "II."),
            (date(2034, 12, 2), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2034, 12, 3), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2034, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2034, 12, 31), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2035(self):
        pripady = [
            (date(2035, 1, 7), "KKP", "KRST KRISTA PÁNA", "II."),
            (date(2035, 2, 7), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2035, 3, 18), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2035, 3, 22), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2035, 3, 23), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2035, 3, 24), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2035, 3, 25), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2035, 4, 1), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2035, 4, 2), "ZV", "ZVESTOVANIE PÁNA", "II."),
            (date(2035, 5, 3), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2035, 5, 13), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2035, 5, 14), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2035, 5, 20), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2035, 6, 1), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2035, 6, 2), "7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", "II."),
            (date(2035, 11, 25), "34C", "KRISTA KRÁĽA", "II."),
            (date(2035, 12, 1), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2035, 12, 2), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2035, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2035, 12, 30), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_krst_pana_na_7_alebo_8_januara_ma_samostatny_kod(self):
        pripady = [
            (date(2034, 1, 8), "C"),
            (date(2035, 1, 7), "A"),
        ]

        for datum_slavenia, liturgicky_rok in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(
                    kinak.vypocitaj_datum_pohyblivych_slaveni(datum_slavenia.year)["Krst Krista Pána"],
                    datum_slavenia,
                )
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), "KKP")
                self.assertIn(
                    "KRST KRISTA PÁNA",
                    kinak.zostav_text_hlavicky(liturgicky_rok, datum_slavenia),
                )
                self.assertNotIn("2. VIANOČNÁ NEDEĽA", kinak.zostav_text_hlavicky(liturgicky_rok, datum_slavenia))

    def test_zvestovanie_2034_ostane_na_25_marci_a_2035_sa_presunie_po_oktave(self):
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(date(2034, 3, 25)), "ZV")
        self.assertEqual(
            kinak.nazov_pohybliveho_slavenia_pre_datum(date(2034, 3, 25)),
            "ZVESTOVANIE PÁNA",
        )

        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(date(2035, 3, 25)), "1VN")
        self.assertIn(
            "Veľkonočná nedeľa",
            kinak.zostav_text_hlavicky(
                kinak.vypocitaj_liturgicky_rok(date(2035, 3, 25)),
                date(2035, 3, 25),
            ),
        )
        self.assertNotIn(
            "ZVESTOVANIE PÁNA",
            kinak.zostav_text_hlavicky(
                kinak.vypocitaj_liturgicky_rok(date(2035, 3, 25)),
                date(2035, 3, 25),
            ),
        )
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(date(2035, 4, 2)), "ZV")
        self.assertEqual(
            kinak.nazov_pohybliveho_slavenia_pre_datum(date(2035, 4, 2)),
            "ZVESTOVANIE PÁNA",
        )

    def test_liturgicky_rok_sa_zmeni_na_prvu_adventnu_nedelu_v_rokoch_2034_a_2035(self):
        pripady = [
            (date(2034, 12, 2), "C", "34c2 zajtra 1AD"),
            (date(2034, 12, 3), "A", "1AD zajtra 1AD"),
            (date(2035, 12, 1), "A", "34c1 zajtra 1AD"),
            (date(2035, 12, 2), "B", "1AD zajtra 1AD"),
        ]

        for datum_slavenia, liturgicky_rok, skratky in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_liturgicky_rok(datum_slavenia), liturgicky_rok)
                self.assertEqual(kinak.format_skratky_liturgickej_casti(datum_slavenia), skratky)


if __name__ == "__main__":
    unittest.main()
