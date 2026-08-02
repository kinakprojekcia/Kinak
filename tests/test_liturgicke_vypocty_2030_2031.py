# -*- coding: utf-8 -*-

import importlib.util
from datetime import date
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class LiturgickeVypocty2030A2031Test(unittest.TestCase):
    def test_pohyblive_slavenia_2030_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2030), date(2030, 4, 21))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2030, 12, 1),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2030, 12, 29),
            "Krst Krista Pána": date(2030, 1, 13),
            "Zvestovanie Pána*": date(2030, 3, 25),
            "Popolcová streda": date(2030, 3, 6),
            "Palmová (Kvetná nedeľa)": date(2030, 4, 14),
            "Veľkonočná nedeľa": date(2030, 4, 21),
            "Pondelok vo Veľkonočnej oktáve": date(2030, 4, 22),
            "Nedeľa Božieho milosrdenstva": date(2030, 4, 28),
            "Nanebovstúpenie Pána": date(2030, 5, 30),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2030, 6, 9),
            "Panny Márie, Matky Cirkvi": date(2030, 6, 10),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2030, 6, 13),
            "Najsvätejšej Trojice": date(2030, 6, 16),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2030, 6, 20),
            "Najsvätejšieho Srdca Ježišovho": date(2030, 6, 28),
            "Nepoškvrnené Srdce Panny Márie": date(2030, 6, 29),
            "Krista Kráľa": date(2030, 11, 24),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2030)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_pohyblive_slavenia_2031_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2031), date(2031, 4, 13))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2031, 11, 30),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2031, 12, 28),
            "Krst Krista Pána": date(2031, 1, 12),
            "Zvestovanie Pána*": date(2031, 3, 25),
            "Popolcová streda": date(2031, 2, 26),
            "Palmová (Kvetná nedeľa)": date(2031, 4, 6),
            "Veľkonočná nedeľa": date(2031, 4, 13),
            "Pondelok vo Veľkonočnej oktáve": date(2031, 4, 14),
            "Nedeľa Božieho milosrdenstva": date(2031, 4, 20),
            "Nanebovstúpenie Pána": date(2031, 5, 22),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2031, 6, 1),
            "Panny Márie, Matky Cirkvi": date(2031, 6, 2),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2031, 6, 5),
            "Najsvätejšej Trojice": date(2031, 6, 8),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2031, 6, 12),
            "Najsvätejšieho Srdca Ježišovho": date(2031, 6, 20),
            "Nepoškvrnené Srdce Panny Márie": date(2031, 6, 21),
            "Krista Kráľa": date(2031, 11, 23),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2031)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2030(self):
        pripady = [
            (date(2030, 1, 13), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2030, 3, 6), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2030, 3, 25), "ZV", "ZVESTOVANIE PÁNA", "III."),
            (date(2030, 4, 14), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2030, 4, 18), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2030, 4, 19), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2030, 4, 20), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2030, 4, 21), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2030, 4, 28), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2030, 5, 30), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2030, 6, 9), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2030, 6, 10), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2030, 6, 16), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2030, 6, 28), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2030, 6, 29), "6L", "SV. PETRA A PAVLA, APOŠTOLOV", "II."),
            (date(2030, 11, 24), "34C", "KRISTA KRÁĽA", "II."),
            (date(2030, 11, 30), "OND", "SV. ONDREJA, APOŠTOLA", "IV."),
            (date(2030, 12, 1), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2030, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2030, 12, 29), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2031(self):
        pripady = [
            (date(2031, 1, 12), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2031, 2, 26), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2031, 3, 25), "ZV", "ZVESTOVANIE PÁNA", "IV."),
            (date(2031, 4, 6), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2031, 4, 10), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2031, 4, 11), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2031, 4, 12), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2031, 4, 13), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2031, 4, 20), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2031, 5, 22), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2031, 6, 1), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2031, 6, 2), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2031, 6, 8), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2031, 6, 20), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2031, 6, 21), "7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", "II."),
            (date(2031, 11, 23), "34C", "KRISTA KRÁĽA", "II."),
            (date(2031, 11, 29), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2031, 11, 30), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2031, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2031, 12, 28), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_zvestovanie_2030_a_2031_ostane_na_25_marci(self):
        for datum_slavenia in (date(2030, 3, 25), date(2031, 3, 25)):
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), "ZV")
                self.assertEqual(
                    kinak.nazov_pohybliveho_slavenia_pre_datum(datum_slavenia),
                    "ZVESTOVANIE PÁNA",
                )
                self.assertIn(
                    "ZVESTOVANIE PÁNA (Slávnosť)",
                    kinak.zostav_text_hlavicky(
                        kinak.vypocitaj_liturgicky_rok(datum_slavenia),
                        datum_slavenia,
                    ),
                )

    def test_sv_peter_a_pavol_ma_29_6_2030_prednost_pred_neposkvrnenym_srdcom(self):
        den_pred_slavnostou = date(2030, 6, 28)
        slavnost = date(2030, 6, 29)

        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(den_pred_slavnostou), "6TS")
        self.assertIn(
            "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO",
            kinak.vypocitaj_aktualnu_liturgicku_cast(den_pred_slavnostou),
        )
        self.assertIn(
            "Vigília: SV. PETRA A PAVLA, APOŠTOLOV",
            kinak.zostav_text_status_baru(den_pred_slavnostou),
        )
        self.assertNotIn(
            "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE",
            kinak.zostav_text_status_baru(den_pred_slavnostou),
        )

        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(slavnost), "6L")
        self.assertEqual(
            kinak.vypocitaj_aktualnu_liturgicku_cast(slavnost),
            "SV. PETRA A PAVLA, APOŠTOLOV",
        )
        self.assertIsNone(kinak.nazov_pohybliveho_slavenia_pre_datum(slavnost))

        hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(slavnost), slavnost)
        status = kinak.zostav_text_status_baru(slavnost)
        self.assertTrue(kinak.je_neposkvrnene_srdce_pm_prekazane(slavnost))
        self.assertEqual(kinak.popis_vynechaneho_slavenia(slavnost), "Nepoškvrnené Srdce Panny Márie vynechané")
        self.assertIn("SV. PETRA A PAVLA, APOŠTOLOV (Slávnosť)", hlavicka)
        status = kinak.zostav_text_status_baru(slavnost)
        self.assertIn("Nepoškvrnené Srdce Panny Márie vynechané", status)
        self.assertNotIn("Žalm z 7TS", status)

    def test_liturgicky_rok_sa_zmeni_na_prvu_adventnu_nedelu_v_rokoch_2030_a_2031(self):
        pripady = [
            (date(2030, 11, 30), "B", "OND zajtra 1AD"),
            (date(2030, 12, 1), "C", "1AD zajtra 1AD"),
            (date(2031, 11, 29), "C", "34c1 zajtra 1AD"),
            (date(2031, 11, 30), "A", "1AD zajtra 1AD"),
        ]

        for datum_slavenia, liturgicky_rok, skratky in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_liturgicky_rok(datum_slavenia), liturgicky_rok)
                self.assertEqual(kinak.format_skratky_liturgickej_casti(datum_slavenia), skratky)


if __name__ == "__main__":
    unittest.main()
