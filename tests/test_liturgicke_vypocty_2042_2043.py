# -*- coding: utf-8 -*-

import importlib.util
from datetime import date
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class LiturgickeVypocty2042A2043Test(unittest.TestCase):
    def test_pohyblive_slavenia_2042_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2042), date(2042, 4, 6))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2042, 11, 30),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2042, 12, 28),
            "Krst Krista Pána": date(2042, 1, 12),
            "Zvestovanie Pána*": date(2042, 3, 25),
            "Popolcová streda": date(2042, 2, 19),
            "Palmová (Kvetná nedeľa)": date(2042, 3, 30),
            "Veľkonočná nedeľa": date(2042, 4, 6),
            "Pondelok vo Veľkonočnej oktáve": date(2042, 4, 7),
            "Nedeľa Božieho milosrdenstva": date(2042, 4, 13),
            "Nanebovstúpenie Pána": date(2042, 5, 15),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2042, 5, 25),
            "Panny Márie, Matky Cirkvi": date(2042, 5, 26),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2042, 5, 29),
            "Najsvätejšej Trojice": date(2042, 6, 1),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2042, 6, 5),
            "Najsvätejšieho Srdca Ježišovho": date(2042, 6, 13),
            "Nepoškvrnené Srdce Panny Márie": date(2042, 6, 14),
            "Krista Kráľa": date(2042, 11, 23),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2042)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_pohyblive_slavenia_2043_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2043), date(2043, 3, 29))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2043, 11, 29),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2043, 12, 27),
            "Krst Krista Pána": date(2043, 1, 11),
            "Zvestovanie Pána*": date(2043, 4, 6),
            "Popolcová streda": date(2043, 2, 11),
            "Palmová (Kvetná nedeľa)": date(2043, 3, 22),
            "Veľkonočná nedeľa": date(2043, 3, 29),
            "Pondelok vo Veľkonočnej oktáve": date(2043, 3, 30),
            "Nedeľa Božieho milosrdenstva": date(2043, 4, 5),
            "Nanebovstúpenie Pána": date(2043, 5, 7),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2043, 5, 17),
            "Panny Márie, Matky Cirkvi": date(2043, 5, 18),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2043, 5, 21),
            "Najsvätejšej Trojice": date(2043, 5, 24),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2043, 5, 28),
            "Najsvätejšieho Srdca Ježišovho": date(2043, 6, 5),
            "Nepoškvrnené Srdce Panny Márie": date(2043, 6, 6),
            "Krista Kráľa": date(2043, 11, 22),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2043)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2042(self):
        pripady = [
            (date(2042, 1, 12), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2042, 2, 19), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2042, 3, 25), "ZV", "ZVESTOVANIE PÁNA", "I."),
            (date(2042, 3, 30), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2042, 4, 3), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2042, 4, 4), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2042, 4, 5), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2042, 4, 6), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2042, 4, 13), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2042, 5, 15), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2042, 5, 25), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2042, 5, 26), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2042, 6, 1), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2042, 6, 13), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2042, 6, 14), "7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", "II."),
            (date(2042, 11, 23), "34C", "KRISTA KRÁĽA", "II."),
            (date(2042, 11, 29), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2042, 11, 30), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2042, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2042, 12, 28), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2043(self):
        pripady = [
            (date(2043, 1, 11), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2043, 2, 11), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2043, 3, 22), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2043, 3, 26), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2043, 3, 27), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2043, 3, 28), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2043, 3, 29), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2043, 4, 5), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2043, 4, 6), "ZV", "ZVESTOVANIE PÁNA", "II."),
            (date(2043, 5, 7), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2043, 5, 17), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2043, 5, 18), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2043, 5, 24), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2043, 6, 5), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2043, 6, 6), "7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", "II."),
            (date(2043, 11, 22), "34C", "KRISTA KRÁĽA", "II."),
            (date(2043, 11, 28), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2043, 11, 29), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2043, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2043, 12, 27), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_zvestovanie_2043_sa_presunie_po_velkonocnej_oktave(self):
        self.assertEqual(
            kinak.vypocitaj_datum_pohyblivych_slaveni(2043)["Zvestovanie Pána*"],
            date(2043, 4, 6),
        )
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(date(2043, 3, 25)), "VT")
        self.assertNotIn(
            "ZVESTOVANIE PÁNA",
            kinak.zostav_text_hlavicky(
                kinak.vypocitaj_liturgicky_rok(date(2043, 3, 25)),
                date(2043, 3, 25),
            ),
        )
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(date(2043, 4, 6)), "ZV")
        self.assertEqual(
            kinak.nazov_pohybliveho_slavenia_pre_datum(date(2043, 4, 6)),
            "ZVESTOVANIE PÁNA",
        )
        self.assertEqual(kinak.format_skratky_liturgickej_casti(date(2043, 4, 5)), "2VN zajtra ZV")

    def test_krst_pana_v_rokoch_2042_a_2043_ma_samostatny_kod(self):
        pripady = [
            (date(2042, 1, 12), "B", "KKP zajtra 1c2"),
            (date(2043, 1, 11), "C", "KKP zajtra 1c1"),
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

    def test_liturgicky_rok_sa_zmeni_na_prvu_adventnu_nedelu_v_rokoch_2042_a_2043(self):
        pripady = [
            (date(2042, 11, 29), "B", "34c2 zajtra 1AD"),
            (date(2042, 11, 30), "C", "1AD zajtra 1AD"),
            (date(2043, 11, 28), "C", "34c1 zajtra 1AD"),
            (date(2043, 11, 29), "A", "1AD zajtra OND"),
        ]

        for datum_slavenia, liturgicky_rok, skratky in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_liturgicky_rok(datum_slavenia), liturgicky_rok)
                self.assertEqual(kinak.format_skratky_liturgickej_casti(datum_slavenia), skratky)


if __name__ == "__main__":
    unittest.main()
