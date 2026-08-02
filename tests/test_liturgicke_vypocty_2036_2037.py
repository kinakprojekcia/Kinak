# -*- coding: utf-8 -*-

import importlib.util
from datetime import date
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class LiturgickeVypocty2036A2037Test(unittest.TestCase):
    def test_pohyblive_slavenia_2036_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2036), date(2036, 4, 13))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2036, 11, 30),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2036, 12, 28),
            "Krst Krista Pána": date(2036, 1, 13),
            "Zvestovanie Pána*": date(2036, 3, 25),
            "Popolcová streda": date(2036, 2, 27),
            "Palmová (Kvetná nedeľa)": date(2036, 4, 6),
            "Veľkonočná nedeľa": date(2036, 4, 13),
            "Pondelok vo Veľkonočnej oktáve": date(2036, 4, 14),
            "Nedeľa Božieho milosrdenstva": date(2036, 4, 20),
            "Nanebovstúpenie Pána": date(2036, 5, 22),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2036, 6, 1),
            "Panny Márie, Matky Cirkvi": date(2036, 6, 2),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2036, 6, 5),
            "Najsvätejšej Trojice": date(2036, 6, 8),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2036, 6, 12),
            "Najsvätejšieho Srdca Ježišovho": date(2036, 6, 20),
            "Nepoškvrnené Srdce Panny Márie": date(2036, 6, 21),
            "Krista Kráľa": date(2036, 11, 23),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2036)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_pohyblive_slavenia_2037_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2037), date(2037, 4, 5))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2037, 11, 29),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2037, 12, 27),
            "Krst Krista Pána": date(2037, 1, 11),
            "Zvestovanie Pána*": date(2037, 3, 25),
            "Popolcová streda": date(2037, 2, 18),
            "Palmová (Kvetná nedeľa)": date(2037, 3, 29),
            "Veľkonočná nedeľa": date(2037, 4, 5),
            "Pondelok vo Veľkonočnej oktáve": date(2037, 4, 6),
            "Nedeľa Božieho milosrdenstva": date(2037, 4, 12),
            "Nanebovstúpenie Pána": date(2037, 5, 14),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2037, 5, 24),
            "Panny Márie, Matky Cirkvi": date(2037, 5, 25),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2037, 5, 28),
            "Najsvätejšej Trojice": date(2037, 5, 31),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2037, 6, 4),
            "Najsvätejšieho Srdca Ježišovho": date(2037, 6, 12),
            "Nepoškvrnené Srdce Panny Márie": date(2037, 6, 13),
            "Krista Kráľa": date(2037, 11, 22),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2037)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2036(self):
        pripady = [
            (date(2036, 1, 13), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2036, 2, 27), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2036, 3, 25), "ZV", "ZVESTOVANIE PÁNA", "IV."),
            (date(2036, 4, 6), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2036, 4, 10), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2036, 4, 11), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2036, 4, 12), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2036, 4, 13), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2036, 4, 20), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2036, 5, 22), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2036, 6, 1), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2036, 6, 2), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2036, 6, 8), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2036, 6, 20), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2036, 6, 21), "7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", "II."),
            (date(2036, 11, 23), "34C", "KRISTA KRÁĽA", "II."),
            (date(2036, 11, 29), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2036, 11, 30), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2036, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2036, 12, 28), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2037(self):
        pripady = [
            (date(2037, 1, 11), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2037, 2, 18), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2037, 3, 25), "ZV", "ZVESTOVANIE PÁNA", "I."),
            (date(2037, 3, 29), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2037, 4, 2), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2037, 4, 3), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2037, 4, 4), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2037, 4, 5), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2037, 4, 12), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2037, 5, 14), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2037, 5, 24), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2037, 5, 25), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2037, 5, 31), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2037, 6, 12), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2037, 6, 13), "7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", "II."),
            (date(2037, 11, 22), "34C", "KRISTA KRÁĽA", "II."),
            (date(2037, 11, 28), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2037, 11, 29), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2037, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2037, 12, 27), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_krst_pana_v_rokoch_2036_a_2037_ma_samostatny_kod(self):
        pripady = [
            (date(2036, 1, 13), "B", "KKP zajtra 1c2"),
            (date(2037, 1, 11), "C", "KKP zajtra 1c1"),
        ]

        for datum_slavenia, liturgicky_rok, skratky in pripady:
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
                self.assertEqual(kinak.format_skratky_liturgickej_casti(datum_slavenia), skratky)

    def test_zvestovanie_2036_a_2037_ostava_na_25_marci(self):
        pripady = [
            (date(2036, 3, 25), "IV."),
            (date(2037, 3, 25), "I."),
        ]

        for datum_slavenia, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), "ZV")
                self.assertEqual(
                    kinak.nazov_pohybliveho_slavenia_pre_datum(datum_slavenia),
                    "ZVESTOVANIE PÁNA",
                )
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_liturgicky_rok_sa_zmeni_na_prvu_adventnu_nedelu_v_rokoch_2036_a_2037(self):
        pripady = [
            (date(2036, 11, 29), "B", "34c2 zajtra 1AD"),
            (date(2036, 11, 30), "C", "1AD zajtra 1AD"),
            (date(2037, 11, 28), "C", "34c1 zajtra 1AD"),
            (date(2037, 11, 29), "A", "1AD zajtra OND"),
        ]

        for datum_slavenia, liturgicky_rok, skratky in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_liturgicky_rok(datum_slavenia), liturgicky_rok)
                self.assertEqual(kinak.format_skratky_liturgickej_casti(datum_slavenia), skratky)


if __name__ == "__main__":
    unittest.main()
