# -*- coding: utf-8 -*-

import importlib.util
from datetime import date
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class LiturgickeVypocty2032A2033Test(unittest.TestCase):
    def test_pohyblive_slavenia_2032_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2032), date(2032, 3, 28))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2032, 11, 28),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2032, 12, 26),
            "Krst Krista Pána": date(2032, 1, 11),
            "Zvestovanie Pána*": date(2032, 4, 5),
            "Popolcová streda": date(2032, 2, 11),
            "Palmová (Kvetná nedeľa)": date(2032, 3, 21),
            "Veľkonočná nedeľa": date(2032, 3, 28),
            "Pondelok vo Veľkonočnej oktáve": date(2032, 3, 29),
            "Nedeľa Božieho milosrdenstva": date(2032, 4, 4),
            "Nanebovstúpenie Pána": date(2032, 5, 6),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2032, 5, 16),
            "Panny Márie, Matky Cirkvi": date(2032, 5, 17),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2032, 5, 20),
            "Najsvätejšej Trojice": date(2032, 5, 23),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2032, 5, 27),
            "Najsvätejšieho Srdca Ježišovho": date(2032, 6, 4),
            "Nepoškvrnené Srdce Panny Márie": date(2032, 6, 5),
            "Krista Kráľa": date(2032, 11, 21),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2032)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_pohyblive_slavenia_2033_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2033), date(2033, 4, 17))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2033, 11, 27),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2033, 12, 30),
            "Krst Krista Pána": date(2033, 1, 9),
            "Zvestovanie Pána*": date(2033, 3, 25),
            "Popolcová streda": date(2033, 3, 2),
            "Palmová (Kvetná nedeľa)": date(2033, 4, 10),
            "Veľkonočná nedeľa": date(2033, 4, 17),
            "Pondelok vo Veľkonočnej oktáve": date(2033, 4, 18),
            "Nedeľa Božieho milosrdenstva": date(2033, 4, 24),
            "Nanebovstúpenie Pána": date(2033, 5, 26),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2033, 6, 5),
            "Panny Márie, Matky Cirkvi": date(2033, 6, 6),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2033, 6, 9),
            "Najsvätejšej Trojice": date(2033, 6, 12),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2033, 6, 16),
            "Najsvätejšieho Srdca Ježišovho": date(2033, 6, 24),
            "Nepoškvrnené Srdce Panny Márie": date(2033, 6, 25),
            "Krista Kráľa": date(2033, 11, 20),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2033)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2032(self):
        pripady = [
            (date(2032, 1, 11), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2032, 2, 11), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2032, 3, 21), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2032, 3, 25), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2032, 3, 26), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2032, 3, 27), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2032, 3, 28), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2032, 4, 4), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2032, 4, 5), "ZV", "ZVESTOVANIE PÁNA", "II."),
            (date(2032, 5, 6), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2032, 5, 16), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2032, 5, 17), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2032, 5, 23), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2032, 6, 4), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2032, 6, 5), "7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", "II."),
            (date(2032, 11, 21), "34C", "KRISTA KRÁĽA", "II."),
            (date(2032, 11, 27), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2032, 11, 28), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2032, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2032, 12, 26), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2033(self):
        pripady = [
            (date(2033, 1, 9), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2033, 3, 2), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2033, 3, 25), "ZV", "ZVESTOVANIE PÁNA", "III."),
            (date(2033, 4, 10), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2033, 4, 14), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2033, 4, 15), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2033, 4, 16), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2033, 4, 17), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2033, 4, 24), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2033, 5, 26), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2033, 6, 5), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2033, 6, 6), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2033, 6, 12), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2033, 6, 23), "NJK", "NARODENIE SV. JÁNA KRSTITEĽA", "II."),
            (date(2033, 6, 24), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2033, 6, 25), "7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", "II."),
            (date(2033, 11, 20), "34C", "KRISTA KRÁĽA", "II."),
            (date(2033, 11, 26), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2033, 11, 27), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2033, 12, 25), "1VI", "NARODENIE PÁNA", "I."),
            (date(2033, 12, 30), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_zvestovanie_2032_sa_presunie_po_oktave_a_2033_ostane_na_25_marci(self):
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(date(2032, 3, 25)), "ZST")
        self.assertNotIn(
            "ZVESTOVANIE PÁNA",
            kinak.zostav_text_hlavicky(
                kinak.vypocitaj_liturgicky_rok(date(2032, 3, 25)),
                date(2032, 3, 25),
            ),
        )
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(date(2032, 4, 5)), "ZV")
        self.assertEqual(
            kinak.nazov_pohybliveho_slavenia_pre_datum(date(2032, 4, 5)),
            "ZVESTOVANIE PÁNA",
        )

        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(date(2033, 3, 25)), "ZV")
        self.assertEqual(
            kinak.nazov_pohybliveho_slavenia_pre_datum(date(2033, 3, 25)),
            "ZVESTOVANIE PÁNA",
        )

    def test_narodenie_jana_krstitela_sa_v_2033_presunie_pred_srdce_jezisovo(self):
        den_pred_slavnostou = date(2033, 6, 22)
        slavnost = date(2033, 6, 23)
        srdce_jezisovo = date(2033, 6, 24)
        den_po_slavnosti = date(2033, 6, 25)

        self.assertEqual(kinak.datum_narodenia_jana_krstitela(2033), slavnost)
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(slavnost), "NJK")
        self.assertEqual(
            kinak.vypocitaj_aktualnu_liturgicku_cast(slavnost),
            "NARODENIE SV. JÁNA KRSTITEĽA",
        )
        self.assertIsNone(kinak.nazov_pohybliveho_slavenia_pre_datum(slavnost))

        hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(slavnost), slavnost)
        status = kinak.zostav_text_status_baru(slavnost)
        self.assertIn("NARODENIE SV. JÁNA KRSTITEĽA (Slávnosť)", hlavicka)
        self.assertNotIn("NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", hlavicka)
        self.assertNotIn("NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", status)
        self.assertNotIn("Vigília: NARODENIE SV. JÁNA KRSTITEĽA", status)
        self.assertIn(
            "Vigília: NARODENIE SV. JÁNA KRSTITEĽA",
            kinak.zostav_text_status_baru(den_pred_slavnostou),
        )

        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(srdce_jezisovo), "6TS")
        self.assertEqual(
            kinak.vypocitaj_aktualnu_liturgicku_cast(srdce_jezisovo),
            "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO",
        )
        self.assertEqual(
            kinak.nazov_pohybliveho_slavenia_pre_datum(srdce_jezisovo),
            "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO",
        )
        hlavicka_srdca = kinak.zostav_text_hlavicky(
            kinak.vypocitaj_liturgicky_rok(srdce_jezisovo),
            srdce_jezisovo,
        )
        self.assertIn("NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO (Slávnosť)", hlavicka_srdca)
        self.assertNotIn("NARODENIE SV. JÁNA KRSTITEĽA", hlavicka_srdca)

        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(den_po_slavnosti), "7TS")
        self.assertIn(
            "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE",
            kinak.vypocitaj_aktualnu_liturgicku_cast(den_po_slavnosti),
        )

    def test_liturgicky_rok_sa_zmeni_na_prvu_adventnu_nedelu_v_rokoch_2032_a_2033(self):
        pripady = [
            (date(2032, 11, 27), "A", "34c2 zajtra 1AD"),
            (date(2032, 11, 28), "B", "1AD zajtra 1AD"),
            (date(2033, 11, 26), "B", "34c1 zajtra 1AD"),
            (date(2033, 11, 27), "C", "1AD zajtra 1AD"),
        ]

        for datum_slavenia, liturgicky_rok, skratky in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_liturgicky_rok(datum_slavenia), liturgicky_rok)
                self.assertEqual(kinak.format_skratky_liturgickej_casti(datum_slavenia), skratky)


if __name__ == "__main__":
    unittest.main()
