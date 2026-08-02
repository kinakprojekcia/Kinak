# -*- coding: utf-8 -*-

import importlib.util
from datetime import date
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


class LiturgickeVypocty2038A2039Test(unittest.TestCase):
    def test_pohyblive_slavenia_2038_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2038), date(2038, 4, 25))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2038, 11, 28),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2038, 12, 26),
            "Krst Krista Pána": date(2038, 1, 10),
            "Zvestovanie Pána*": date(2038, 3, 25),
            "Popolcová streda": date(2038, 3, 10),
            "Palmová (Kvetná nedeľa)": date(2038, 4, 18),
            "Veľkonočná nedeľa": date(2038, 4, 25),
            "Pondelok vo Veľkonočnej oktáve": date(2038, 4, 26),
            "Nedeľa Božieho milosrdenstva": date(2038, 5, 2),
            "Nanebovstúpenie Pána": date(2038, 6, 3),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2038, 6, 13),
            "Panny Márie, Matky Cirkvi": date(2038, 6, 14),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2038, 6, 17),
            "Najsvätejšej Trojice": date(2038, 6, 20),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2038, 6, 24),
            "Najsvätejšieho Srdca Ježišovho": date(2038, 7, 2),
            "Nepoškvrnené Srdce Panny Márie": date(2038, 7, 3),
            "Krista Kráľa": date(2038, 11, 21),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2038)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_pohyblive_slavenia_2039_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2039), date(2039, 4, 10))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2039, 11, 27),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2039, 12, 30),
            "Krst Krista Pána": date(2039, 1, 9),
            "Zvestovanie Pána*": date(2039, 3, 25),
            "Popolcová streda": date(2039, 2, 23),
            "Palmová (Kvetná nedeľa)": date(2039, 4, 3),
            "Veľkonočná nedeľa": date(2039, 4, 10),
            "Pondelok vo Veľkonočnej oktáve": date(2039, 4, 11),
            "Nedeľa Božieho milosrdenstva": date(2039, 4, 17),
            "Nanebovstúpenie Pána": date(2039, 5, 19),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2039, 5, 29),
            "Panny Márie, Matky Cirkvi": date(2039, 5, 30),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2039, 6, 2),
            "Najsvätejšej Trojice": date(2039, 6, 5),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2039, 6, 9),
            "Najsvätejšieho Srdca Ježišovho": date(2039, 6, 17),
            "Nepoškvrnené Srdce Panny Márie": date(2039, 6, 18),
            "Krista Kráľa": date(2039, 11, 20),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2039)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2038(self):
        pripady = [
            (date(2038, 1, 10), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2038, 3, 10), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2038, 3, 25), "ZV", "ZVESTOVANIE PÁNA", "II."),
            (date(2038, 4, 18), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2038, 4, 22), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2038, 4, 23), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2038, 4, 24), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2038, 4, 25), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2038, 5, 2), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2038, 6, 3), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2038, 6, 13), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2038, 6, 14), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2038, 6, 20), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2038, 6, 23), "NJK", "NARODENIE SV. JÁNA KRSTITEĽA", "I."),
            (date(2038, 6, 24), "5TS", "NAJSVÄTEJŠIEHO KRISTOVHO TELA A KRVI", "I."),
            (date(2038, 7, 2), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2038, 7, 3), "7L", "SV. TOMÁŠA, APOŠTOLA", "II."),
            (date(2038, 11, 21), "34C", "KRISTA KRÁĽA", "II."),
            (date(2038, 11, 27), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2038, 11, 28), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2038, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2038, 12, 26), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2039(self):
        pripady = [
            (date(2039, 1, 9), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2039, 2, 23), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2039, 3, 25), "ZV", "ZVESTOVANIE PÁNA", "IV."),
            (date(2039, 4, 3), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2039, 4, 7), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2039, 4, 8), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2039, 4, 9), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2039, 4, 10), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2039, 4, 17), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2039, 5, 19), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2039, 5, 29), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2039, 5, 30), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2039, 6, 5), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2039, 6, 17), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2039, 6, 18), "7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", "II."),
            (date(2039, 11, 20), "34C", "KRISTA KRÁĽA", "II."),
            (date(2039, 11, 26), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2039, 11, 27), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2039, 12, 25), "1VI", "NARODENIE PÁNA", "I."),
            (date(2039, 12, 30), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_srdce_jezisovo_2038_ma_prednost_pred_navstevou_panny_marie(self):
        datum_slavenia = date(2038, 7, 2)

        self.assertEqual(
            kinak.vypocitaj_datum_pohyblivych_slaveni(2038)["Najsvätejšieho Srdca Ježišovho"],
            datum_slavenia,
        )
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), "6TS")
        self.assertEqual(
            kinak.nazov_pohybliveho_slavenia_pre_datum(datum_slavenia),
            "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO",
        )
        self.assertIn(
            "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO",
            kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum_slavenia), datum_slavenia),
        )
        self.assertNotIn(
            "NÁVŠTEVA PREBLAHOSLAVENEJ PANNY MÁRIE",
            kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum_slavenia), datum_slavenia),
        )
        self.assertEqual(kinak.format_skratky_liturgickej_casti(datum_slavenia), "6TS zajtra 7L")

    def test_bozie_telo_2038_presunie_narodenie_jana_krstitela(self):
        datum_slavenia = date(2038, 6, 24)
        presunuty_jan = date(2038, 6, 23)

        self.assertEqual(
            kinak.vypocitaj_datum_pohyblivych_slaveni(2038)["Najsvätejšieho Kristovho Tela a Krvi"],
            datum_slavenia,
        )
        self.assertEqual(kinak.datum_narodenia_jana_krstitela(2038), presunuty_jan)
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(presunuty_jan), "NJK")
        hlavicka_jana = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(presunuty_jan), presunuty_jan)
        status_jana = kinak.zostav_text_status_baru(presunuty_jan)
        self.assertIn("NARODENIE SV. JÁNA KRSTITEĽA", hlavicka_jana)
        self.assertIn("Narodenie Jána Krstiteľa sa presúva z 24.6.", status_jana)

        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), "5TS")
        hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum_slavenia), datum_slavenia)
        self.assertIn("NAJSVÄTEJŠIEHO KRISTOVHO TELA A KRVI", hlavicka)
        self.assertNotIn("NARODENIE SV. JÁNA KRSTITEĽA", hlavicka)

    def test_svaty_tomas_2038_ma_prednost_pred_neposkvrnenym_srdcom(self):
        datum_slavenia = date(2038, 7, 3)

        self.assertEqual(
            kinak.vypocitaj_datum_pohyblivych_slaveni(2038)["Nepoškvrnené Srdce Panny Márie"],
            datum_slavenia,
        )
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), "7L")
        hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum_slavenia), datum_slavenia)
        self.assertIn("SV. TOMÁŠA, APOŠTOLA", hlavicka)
        self.assertNotIn("NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", hlavicka)
        self.assertEqual(kinak.format_skratky_liturgickej_casti(datum_slavenia), "7L zajtra 14c2")

    def test_krst_pana_v_rokoch_2038_a_2039_ma_samostatny_kod(self):
        pripady = [
            (date(2038, 1, 10), "A", "KKP zajtra 1c2"),
            (date(2039, 1, 9), "B", "KKP zajtra 1c1"),
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

    def test_liturgicky_rok_sa_zmeni_na_prvu_adventnu_nedelu_v_rokoch_2038_a_2039(self):
        pripady = [
            (date(2038, 11, 27), "A", "34c2 zajtra 1AD"),
            (date(2038, 11, 28), "B", "1AD zajtra 1AD"),
            (date(2039, 11, 26), "B", "34c1 zajtra 1AD"),
            (date(2039, 11, 27), "C", "1AD zajtra 1AD"),
        ]

        for datum_slavenia, liturgicky_rok, skratky in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_liturgicky_rok(datum_slavenia), liturgicky_rok)
                self.assertEqual(kinak.format_skratky_liturgickej_casti(datum_slavenia), skratky)


if __name__ == "__main__":
    unittest.main()
