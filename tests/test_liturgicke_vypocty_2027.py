# -*- coding: utf-8 -*-

import importlib.util
from datetime import date
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class LiturgickeVypocty2027Test(unittest.TestCase):
    def test_pohyblive_slavenia_2027_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2027), date(2027, 3, 28))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2027, 11, 28),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2027, 12, 26),
            "Krst Krista Pána": date(2027, 1, 10),
            "Zvestovanie Pána*": date(2027, 4, 5),
            "Popolcová streda": date(2027, 2, 10),
            "Palmová (Kvetná nedeľa)": date(2027, 3, 21),
            "Veľkonočná nedeľa": date(2027, 3, 28),
            "Pondelok vo Veľkonočnej oktáve": date(2027, 3, 29),
            "Nedeľa Božieho milosrdenstva": date(2027, 4, 4),
            "Nanebovstúpenie Pána": date(2027, 5, 6),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2027, 5, 16),
            "Panny Márie, Matky Cirkvi": date(2027, 5, 17),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2027, 5, 20),
            "Najsvätejšej Trojice": date(2027, 5, 23),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2027, 5, 27),
            "Najsvätejšieho Srdca Ježišovho": date(2027, 6, 4),
            "Nepoškvrnené Srdce Panny Márie": date(2027, 6, 5),
            "Krista Kráľa": date(2027, 11, 21),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2027)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2027(self):
        pripady = [
            (date(2027, 1, 10), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2027, 2, 10), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2027, 3, 21), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2027, 3, 25), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2027, 3, 26), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2027, 3, 27), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2027, 3, 28), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2027, 4, 4), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2027, 5, 6), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2027, 5, 16), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2027, 5, 17), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2027, 5, 23), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2027, 6, 4), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2027, 6, 5), "7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", "II."),
            (date(2027, 11, 21), "34C", "KRISTA KRÁĽA", "II."),
            (date(2027, 11, 27), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2027, 11, 28), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2027, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2027, 12, 26), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_zvestovanie_2027_sa_presunie_z_velkeho_tyzdna_az_po_oktave(self):
        povodny_datum = date(2027, 3, 25)
        presunuty_datum = date(2027, 4, 5)

        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(povodny_datum), "ZST")
        self.assertNotIn(
            "ZVESTOVANIE PÁNA",
            kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(povodny_datum), povodny_datum),
        )

        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(presunuty_datum), "ZV")
        self.assertEqual(
            kinak.nazov_pohybliveho_slavenia_pre_datum(presunuty_datum),
            "ZVESTOVANIE PÁNA",
        )
        self.assertIn(
            "ZVESTOVANIE PÁNA (Slávnosť)",
            kinak.zostav_text_hlavicky(
                kinak.vypocitaj_liturgicky_rok(presunuty_datum),
                presunuty_datum,
            ),
        )

    def test_liturgicky_rok_sa_v_2027_zmeni_na_prvu_adventnu_nedelu(self):
        self.assertEqual(kinak.vypocitaj_liturgicky_rok(date(2027, 11, 27)), "B")
        self.assertEqual(kinak.vypocitaj_liturgicky_rok(date(2027, 11, 28)), "C")
        self.assertEqual(kinak.format_skratky_liturgickej_casti(date(2027, 11, 27)), "34c1 zajtra 1AD")
        self.assertEqual(kinak.format_skratky_liturgickej_casti(date(2027, 11, 28)), "1AD zajtra 1AD")


if __name__ == "__main__":
    unittest.main()
