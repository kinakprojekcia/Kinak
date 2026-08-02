# -*- coding: utf-8 -*-

import importlib.util
from datetime import date
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class LiturgickeVypocty2025A2026Test(unittest.TestCase):
    def test_pohyblive_slavenia_2025_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2025), date(2025, 4, 20))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2025, 11, 30),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2025, 12, 28),
            "Krst Krista Pána": date(2025, 1, 12),
            "Zvestovanie Pána*": date(2025, 3, 25),
            "Popolcová streda": date(2025, 3, 5),
            "Palmová (Kvetná nedeľa)": date(2025, 4, 13),
            "Veľkonočná nedeľa": date(2025, 4, 20),
            "Pondelok vo Veľkonočnej oktáve": date(2025, 4, 21),
            "Nedeľa Božieho milosrdenstva": date(2025, 4, 27),
            "Nanebovstúpenie Pána": date(2025, 5, 29),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2025, 6, 8),
            "Panny Márie, Matky Cirkvi": date(2025, 6, 9),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2025, 6, 12),
            "Najsvätejšej Trojice": date(2025, 6, 15),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2025, 6, 19),
            "Najsvätejšieho Srdca Ježišovho": date(2025, 6, 27),
            "Nepoškvrnené Srdce Panny Márie": date(2025, 6, 28),
            "Krista Kráľa": date(2025, 11, 23),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2025)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_pohyblive_slavenia_2026_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2026), date(2026, 4, 5))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2026, 11, 29),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2026, 12, 27),
            "Krst Krista Pána": date(2026, 1, 11),
            "Zvestovanie Pána*": date(2026, 3, 25),
            "Popolcová streda": date(2026, 2, 18),
            "Palmová (Kvetná nedeľa)": date(2026, 3, 29),
            "Veľkonočná nedeľa": date(2026, 4, 5),
            "Pondelok vo Veľkonočnej oktáve": date(2026, 4, 6),
            "Nedeľa Božieho milosrdenstva": date(2026, 4, 12),
            "Nanebovstúpenie Pána": date(2026, 5, 14),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2026, 5, 24),
            "Panny Márie, Matky Cirkvi": date(2026, 5, 25),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2026, 5, 28),
            "Najsvätejšej Trojice": date(2026, 5, 31),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2026, 6, 4),
            "Najsvätejšieho Srdca Ježišovho": date(2026, 6, 12),
            "Nepoškvrnené Srdce Panny Márie": date(2026, 6, 13),
            "Krista Kráľa": date(2026, 11, 22),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2026)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2025(self):
        pripady = [
            (date(2025, 1, 12), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2025, 3, 5), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2025, 3, 25), "ZV", "ZVESTOVANIE PÁNA", "III."),
            (date(2025, 4, 13), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2025, 4, 17), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2025, 4, 18), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2025, 4, 19), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2025, 4, 20), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2025, 4, 27), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2025, 5, 29), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2025, 6, 8), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2025, 6, 9), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2025, 6, 15), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2025, 6, 27), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2025, 6, 28), "7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", "II."),
            (date(2025, 11, 23), "34C", "KRISTA KRÁĽA", "II."),
            (date(2025, 11, 29), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2025, 11, 30), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2025, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2025, 12, 28), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2026(self):
        pripady = [
            (date(2026, 1, 11), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2026, 2, 18), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2026, 3, 25), "ZV", "ZVESTOVANIE PÁNA", "I."),
            (date(2026, 3, 29), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2026, 4, 2), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2026, 4, 3), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2026, 4, 4), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2026, 4, 5), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2026, 4, 12), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2026, 5, 14), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2026, 5, 24), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2026, 5, 25), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2026, 5, 31), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2026, 6, 12), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2026, 6, 13), "7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", "II."),
            (date(2026, 11, 22), "34C", "KRISTA KRÁĽA", "II."),
            (date(2026, 11, 28), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2026, 11, 29), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2026, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2026, 12, 27), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_krst_pana_v_rokoch_2025_a_2026_ma_samostatny_kod(self):
        pripady = [
            (date(2025, 1, 12), "C", "KKP zajtra 1c1"),
            (date(2026, 1, 11), "A", "KKP zajtra 1c2"),
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

    def test_velkonocna_vigilia_2026_ma_spravny_kod_hlavicku_a_status(self):
        datum_slavenia = date(2026, 4, 4)

        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), "VG")
        self.assertIn(
            "VEĽKONOČNÁ VIGÍLIA",
            kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum_slavenia), datum_slavenia),
        )
        self.assertEqual(kinak.format_skratky_liturgickej_casti(datum_slavenia), "VG zajtra 1VN")
        self.assertIn("Žaltár v breviári: I. týždeň", kinak.zostav_text_status_baru(datum_slavenia))

    def test_neposkvrnene_srdce_2025_predchadza_petrovipavlovi(self):
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(date(2025, 6, 28)), "7TS")
        self.assertEqual(kinak.format_skratky_liturgickej_casti(date(2025, 6, 28)), "7TS zajtra 6L")
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(date(2025, 6, 29)), "6L")
        self.assertIn("SV. PETRA A PAVLA, APOŠTOLOV", kinak.vypocitaj_aktualnu_liturgicku_cast(date(2025, 6, 29)))

    def test_liturgicky_rok_sa_zmeni_na_prvu_adventnu_nedelu_v_rokoch_2025_a_2026(self):
        pripady = [
            (date(2025, 11, 29), "C", "34c1 zajtra 1AD"),
            (date(2025, 11, 30), "A", "1AD zajtra 1AD"),
            (date(2026, 11, 28), "A", "34c2 zajtra 1AD"),
            (date(2026, 11, 29), "B", "1AD zajtra OND"),
        ]

        for datum_slavenia, liturgicky_rok, skratky in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_liturgicky_rok(datum_slavenia), liturgicky_rok)
                self.assertEqual(kinak.format_skratky_liturgickej_casti(datum_slavenia), skratky)


if __name__ == "__main__":
    unittest.main()
