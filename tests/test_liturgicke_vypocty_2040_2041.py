# -*- coding: utf-8 -*-

import importlib.util
from datetime import date
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class LiturgickeVypocty2040A2041Test(unittest.TestCase):
    def test_pohyblive_slavenia_2040_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2040), date(2040, 4, 1))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2040, 12, 2),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2040, 12, 30),
            "Krst Krista Pána": date(2040, 1, 8),
            "Zvestovanie Pána*": date(2040, 4, 9),
            "Popolcová streda": date(2040, 2, 15),
            "Palmová (Kvetná nedeľa)": date(2040, 3, 25),
            "Veľkonočná nedeľa": date(2040, 4, 1),
            "Pondelok vo Veľkonočnej oktáve": date(2040, 4, 2),
            "Nedeľa Božieho milosrdenstva": date(2040, 4, 8),
            "Nanebovstúpenie Pána": date(2040, 5, 10),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2040, 5, 20),
            "Panny Márie, Matky Cirkvi": date(2040, 5, 21),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2040, 5, 24),
            "Najsvätejšej Trojice": date(2040, 5, 27),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2040, 5, 31),
            "Najsvätejšieho Srdca Ježišovho": date(2040, 6, 8),
            "Nepoškvrnené Srdce Panny Márie": date(2040, 6, 9),
            "Krista Kráľa": date(2040, 11, 25),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2040)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_pohyblive_slavenia_2041_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2041), date(2041, 4, 21))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2041, 12, 1),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2041, 12, 29),
            "Krst Krista Pána": date(2041, 1, 13),
            "Zvestovanie Pána*": date(2041, 3, 25),
            "Popolcová streda": date(2041, 3, 6),
            "Palmová (Kvetná nedeľa)": date(2041, 4, 14),
            "Veľkonočná nedeľa": date(2041, 4, 21),
            "Pondelok vo Veľkonočnej oktáve": date(2041, 4, 22),
            "Nedeľa Božieho milosrdenstva": date(2041, 4, 28),
            "Nanebovstúpenie Pána": date(2041, 5, 30),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2041, 6, 9),
            "Panny Márie, Matky Cirkvi": date(2041, 6, 10),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2041, 6, 13),
            "Najsvätejšej Trojice": date(2041, 6, 16),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2041, 6, 20),
            "Najsvätejšieho Srdca Ježišovho": date(2041, 6, 28),
            "Nepoškvrnené Srdce Panny Márie": date(2041, 6, 29),
            "Krista Kráľa": date(2041, 11, 24),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2041)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2040(self):
        pripady = [
            (date(2040, 1, 8), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2040, 2, 15), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2040, 3, 25), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2040, 3, 29), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2040, 3, 30), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2040, 3, 31), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2040, 4, 1), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2040, 4, 8), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2040, 4, 9), "ZV", "ZVESTOVANIE PÁNA", "II."),
            (date(2040, 5, 10), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2040, 5, 20), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2040, 5, 21), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2040, 5, 27), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2040, 6, 8), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2040, 6, 9), "7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", "II."),
            (date(2040, 11, 25), "34C", "KRISTA KRÁĽA", "II."),
            (date(2040, 12, 1), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2040, 12, 2), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2040, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2040, 12, 30), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2041(self):
        pripady = [
            (date(2041, 1, 13), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2041, 3, 6), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2041, 3, 25), "ZV", "ZVESTOVANIE PÁNA", "III."),
            (date(2041, 4, 14), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2041, 4, 18), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2041, 4, 19), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2041, 4, 20), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2041, 4, 21), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2041, 4, 28), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2041, 5, 30), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2041, 6, 9), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2041, 6, 10), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2041, 6, 16), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2041, 6, 28), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2041, 6, 29), "6L", "SV. PETRA A PAVLA, APOŠTOLOV", "II."),
            (date(2041, 11, 24), "34C", "KRISTA KRÁĽA", "II."),
            (date(2041, 11, 30), "OND", "SV. ONDREJA, APOŠTOLA", "IV."),
            (date(2041, 12, 1), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2041, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2041, 12, 29), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_zvestovanie_2040_sa_presunie_po_velkonocnej_oktave(self):
        self.assertEqual(
            kinak.vypocitaj_datum_pohyblivych_slaveni(2040)["Zvestovanie Pána*"],
            date(2040, 4, 9),
        )
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(date(2040, 3, 25)), "VT")
        self.assertIn(
            "PALMOVÁ",
            kinak.vypocitaj_aktualnu_liturgicku_cast(date(2040, 3, 25)),
        )
        self.assertNotIn(
            "ZVESTOVANIE PÁNA",
            kinak.zostav_text_hlavicky(
                kinak.vypocitaj_liturgicky_rok(date(2040, 3, 25)),
                date(2040, 3, 25),
            ),
        )
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(date(2040, 4, 9)), "ZV")
        self.assertEqual(
            kinak.nazov_pohybliveho_slavenia_pre_datum(date(2040, 4, 9)),
            "ZVESTOVANIE PÁNA",
        )
        self.assertEqual(kinak.format_skratky_liturgickej_casti(date(2040, 4, 8)), "2VN zajtra ZV")

    def test_neposkvrnene_srdce_2041_ustupi_petrovipavlovi(self):
        datum_slavenia = date(2041, 6, 29)

        self.assertEqual(
            kinak.vypocitaj_datum_pohyblivych_slaveni(2041)["Nepoškvrnené Srdce Panny Márie"],
            datum_slavenia,
        )
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), "6L")
        self.assertIn(
            "SV. PETRA A PAVLA, APOŠTOLOV",
            kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia),
        )
        hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum_slavenia), datum_slavenia)
        self.assertTrue(kinak.je_neposkvrnene_srdce_pm_prekazane(datum_slavenia))
        self.assertEqual(kinak.popis_vynechaneho_slavenia(datum_slavenia), "Nepoškvrnené Srdce Panny Márie vynechané")
        status = kinak.zostav_text_status_baru(datum_slavenia)
        self.assertIn("Nepoškvrnené Srdce Panny Márie vynechané", status)
        self.assertEqual(kinak.format_skratky_liturgickej_casti(datum_slavenia), "6L zajtra 13c1")

    def test_liturgicky_rok_sa_zmeni_na_prvu_adventnu_nedelu_v_rokoch_2040_a_2041(self):
        pripady = [
            (date(2040, 12, 1), "C", "34c2 zajtra 1AD"),
            (date(2040, 12, 2), "A", "1AD zajtra 1AD"),
            (date(2041, 11, 30), "A", "OND zajtra 1AD"),
            (date(2041, 12, 1), "B", "1AD zajtra 1AD"),
        ]

        for datum_slavenia, liturgicky_rok, skratky in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_liturgicky_rok(datum_slavenia), liturgicky_rok)
                self.assertEqual(kinak.format_skratky_liturgickej_casti(datum_slavenia), skratky)


if __name__ == "__main__":
    unittest.main()
