# -*- coding: utf-8 -*-

import importlib.util
from datetime import date
from pathlib import Path
import unittest

KINAK_PATH = Path(__file__).resolve().parent / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)

class TestLiturgickeVypoctyDo2050(unittest.TestCase):
    def test_pohyblive_slavenia_2028_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2028), date(2028, 4, 16))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2028, 12, 3),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2028, 12, 31),
            "Krst Krista Pána": date(2028, 1, 9),
            "Zvestovanie Pána*": date(2028, 3, 25),
            "Popolcová streda": date(2028, 3, 1),
            "Palmová (Kvetná nedeľa)": date(2028, 4, 9),
            "Veľkonočná nedeľa": date(2028, 4, 16),
            "Pondelok vo Veľkonočnej oktáve": date(2028, 4, 17),
            "Nedeľa Božieho milosrdenstva": date(2028, 4, 23),
            "Nanebovstúpenie Pána": date(2028, 5, 25),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2028, 6, 4),
            "Panny Márie, Matky Cirkvi": date(2028, 6, 5),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2028, 6, 8),
            "Najsvätejšej Trojice": date(2028, 6, 11),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2028, 6, 15),
            "Najsvätejšieho Srdca Ježišovho": date(2028, 6, 23),
            "Nepoškvrnené Srdce Panny Márie": date(2028, 6, 24),
            "Krista Kráľa": date(2028, 11, 26),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2028)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_pohyblive_slavenia_2029_maju_ocakavane_datumy(self):
        self.assertEqual(kinak.velkonocna_nedela(2029), date(2029, 4, 1))

        ocakavane = {
            "Prvá adventná nedeľa (začína nový liturgický rok)": date(2029, 12, 2),
            "Svätej rodiny Ježiša, Márie a Jozefa": date(2029, 12, 30),
            "Krst Krista Pána": date(2029, 1, 7),
            "Zvestovanie Pána*": date(2029, 4, 9),
            "Popolcová streda": date(2029, 2, 14),
            "Palmová (Kvetná nedeľa)": date(2029, 3, 25),
            "Veľkonočná nedeľa": date(2029, 4, 1),
            "Pondelok vo Veľkonočnej oktáve": date(2029, 4, 2),
            "Nedeľa Božieho milosrdenstva": date(2029, 4, 8),
            "Nanebovstúpenie Pána": date(2029, 5, 10),
            "Nedeľa zoslania Ducha Svätého (Turíce)": date(2029, 5, 20),
            "Panny Márie, Matky Cirkvi": date(2029, 5, 21),
            "Pána Ježiša Krista, najvyššieho a večného kňaza": date(2029, 5, 24),
            "Najsvätejšej Trojice": date(2029, 5, 27),
            "Najsvätejšieho Kristovho Tela a Krvi": date(2029, 5, 31),
            "Najsvätejšieho Srdca Ježišovho": date(2029, 6, 8),
            "Nepoškvrnené Srdce Panny Márie": date(2029, 6, 9),
            "Krista Kráľa": date(2029, 11, 25),
        }

        vypocitane = kinak.vypocitaj_datum_pohyblivych_slaveni(2029)

        for nazov, datum_slavenia in ocakavane.items():
            with self.subTest(nazov=nazov):
                self.assertEqual(vypocitane[nazov], datum_slavenia)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2028(self):
        pripady = [
            (date(2028, 1, 9), "KKP", "KRST KRISTA PÁNA", "III."),
            (date(2028, 3, 1), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2028, 3, 25), "ZV", "ZVESTOVANIE PÁNA", "III."),
            (date(2028, 4, 9), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2028, 4, 13), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2028, 4, 14), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2028, 4, 15), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2028, 4, 16), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2028, 4, 23), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2028, 5, 25), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2028, 6, 4), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2028, 6, 5), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2028, 6, 11), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2028, 6, 23), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2028, 11, 26), "34C", "KRISTA KRÁĽA", "II."),
            (date(2028, 12, 2), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2028, 12, 3), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2028, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2028, 12, 31), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_kody_obdobi_a_tyzdne_zaltara_na_hranicach_roka_2029(self):
        pripady = [
            (date(2029, 1, 7), "KKP", "KRST KRISTA PÁNA", "II."),
            (date(2029, 2, 14), "PS", "POPOLCOVÁ STREDA", "IV."),
            (date(2029, 3, 25), "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "II."),
            (date(2029, 3, 29), "ZST", "ZELENÝ ŠTVRTOK", "II."),
            (date(2029, 3, 30), "VP", "VEĽKÝ PIATOK", "II."),
            (date(2029, 3, 31), "VG", "VEĽKONOČNÁ VIGÍLIA", "I."),
            (date(2029, 4, 1), "1VN", "VEĽKONOČNÁ NEDEĽA", "I."),
            (date(2029, 4, 8), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "II."),
            (date(2029, 4, 9), "ZV", "ZVESTOVANIE PÁNA", "II."),
            (date(2029, 5, 10), "NP", "NANEBOVSTÚPENIE PÁNA", "II."),
            (date(2029, 5, 20), "1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO", "IV."),
            (date(2029, 5, 21), "2TS", "PANNY MÁRIE, MATKY CIRKVI", "IV."),
            (date(2029, 5, 27), "4TS", "NAJSVÄTEJŠIA TROJICA", "I."),
            (date(2029, 6, 8), "6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO", "II."),
            (date(2029, 6, 9), "7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", "II."),
            (date(2029, 11, 25), "34C", "KRISTA KRÁĽA", "II."),
            (date(2029, 12, 1), "34C", "34. TÝŽDEŇ CEZROČNÉHO OBDOBIA", "II."),
            (date(2029, 12, 2), "1AD", "1. ADVENTNÁ NEDEĽA", "I."),
            (date(2029, 12, 25), "1VI", "NARODENIE PÁNA", "IV."),
            (date(2029, 12, 30), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", "I."),
        ]

        for datum_slavenia, kod, cast, tyzden_zaltara in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), kod)
                self.assertIn(cast, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertEqual(kinak.vypocitaj_tyzden_zaltara(datum_slavenia), tyzden_zaltara)

    def test_zvestovanie_2028_ostane_na_25_marci_a_2029_sa_presunie_po_oktave(self):
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(date(2028, 3, 25)), "ZV")
        self.assertEqual(
            kinak.nazov_pohybliveho_slavenia_pre_datum(date(2028, 3, 25)),
            "ZVESTOVANIE PÁNA",
        )

        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(date(2029, 3, 25)), "VT")
        self.assertNotIn(
            "ZVESTOVANIE PÁNA",
            kinak.zostav_text_hlavicky(
                kinak.vypocitaj_liturgicky_rok(date(2029, 3, 25)),
                date(2029, 3, 25),
            ),
        )
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(date(2029, 4, 9)), "ZV")
        self.assertEqual(
            kinak.nazov_pohybliveho_slavenia_pre_datum(date(2029, 4, 9)),
            "ZVESTOVANIE PÁNA",
        )

    def test_narodenie_jana_krstitela_ma_24_6_2028_prednost_pred_neposkvrnenym_srdcom(self):
        den_pred_slavnostou = date(2028, 6, 23)
        slavnost = date(2028, 6, 24)

        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(den_pred_slavnostou), "6TS")
        self.assertIn(
            "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO",
            kinak.vypocitaj_aktualnu_liturgicku_cast(den_pred_slavnostou),
        )
        self.assertIn(
            "Vigília: NARODENIE SV. JÁNA KRSTITEĽA",
            kinak.zostav_text_status_baru(den_pred_slavnostou),
        )

        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(slavnost), "NJK")
        self.assertEqual(
            kinak.vypocitaj_aktualnu_liturgicku_cast(slavnost),
            "NARODENIE SV. JÁNA KRSTITEĽA",
        )
        self.assertIsNone(kinak.nazov_pohybliveho_slavenia_pre_datum(slavnost))

        hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(slavnost), slavnost)
        self.assertTrue(kinak.je_neposkvrnene_srdce_pm_prekazane(slavnost))
        self.assertEqual(kinak.popis_vynechaneho_slavenia(slavnost), "Nepoškvrnené Srdce Panny Márie vynechané")
        self.assertIn("NARODENIE SV. JÁNA KRSTITEĽA (Slávnosť)", hlavicka)
        status = kinak.zostav_text_status_baru(slavnost)
        self.assertIn("Nepoškvrnené Srdce Panny Márie vynechané", status)



    
    def test_konflikty_sv_ondrej_a_filip_jakub_2028_2050(self):
        """Overí, že konflikty pre 30.11. a 3.5. sú správne detegované."""
        ocakavane_ondrej = {
            2031: "1. adventná nedeľa",
            2036: "1. adventná nedeľa",
            2042: "1. adventná nedeľa",
        }
        ocakavane_fj = {
            2035: "nedeľa",
            2037: "nedeľa",
            2043: "nedeľa",
            2046: "Nanebovstúpenie",
            2048: "nedeľa",
        }

        for rok in range(2028, 2051):
            with self.subTest(rok=rok, sviatok="Ondrej"):
                ondrej = date(rok, 11, 30)
                je_konflikt = kinak.je_sv_ondrej_prekazany(ondrej)
                if rok in ocakavane_ondrej:
                    self.assertTrue(je_konflikt, f"{rok} mal byť konflikt")
                    # over aj Status bar
                    self.assertIn("Sv. Ondrej, apoštol vynechaný",
                                  kinak.zostav_text_status_baru(ondrej))
                else:
                    self.assertFalse(je_konflikt)

            with self.subTest(rok=rok, sviatok="FilipJakub"):
                fj = date(rok, 5, 3)
                je_konflikt = kinak.je_sv_filip_jakub_prekazany(fj)
                if rok in ocakavane_fj:
                    self.assertTrue(je_konflikt, f"{rok} mal byť konflikt")
                    self.assertIn("Sv. Filip a Jakub vynechaný",
                                  kinak.zostav_text_status_baru(fj))
                    # špeciálna kontrola pre rok 2046 – kolízia s Nanebovstúpením
                    if rok == 2046:
                        datumy = kinak.vypocitaj_datum_pohyblivych_slaveni(rok)
                        # nájdi Nanebovstúpenie v slovníku
                        nanebovstupenie = None
                        for nazov, d in datumy.items():
                            if "Nanebovstúpenie" in nazov:
                                nanebovstupenie = d
                                break
                        if nanebovstupenie is not None:
                            self.assertEqual(fj, nanebovstupenie)
                        else:
                            # fallback ak by sa nenašlo
                            self.assertEqual(fj, date(rok, 5, 14))
                else:
                    self.assertFalse(je_konflikt)

    def test_status_bar_obsahuje_info_o_koliziach(self):
        # NSPM vynechané 2028
        status_2028_nspm = kinak.zostav_text_status_baru(date(2028, 6, 24))
        self.assertIn("Nepoškvrnené Srdce Panny Márie vynechané", status_2028_nspm)

        # Zvestovanie presunuté 2029 – na pôvodnom dátume
        status_2029_povodny = kinak.zostav_text_status_baru(date(2029, 3, 25))
        # text sa zmenil: "presunuté na" -> "sa presúva na"
        self.assertTrue(
            "Zvestovanie Pána presunuté na 9.4." in status_2029_povodny or
            "Zvestovanie Pána sa presúva na 9.4." in status_2029_povodny or
            "Zvestovanie Pána" in status_2029_povodny and "9.4." in status_2029_povodny
        )

        # Zvestovanie presunuté 2029 – na novom dátume
        status_2029_novy = kinak.zostav_text_status_baru(date(2029, 4, 9))
        self.assertTrue(
            "Zvestovanie Pána presunuté z 25.3." in status_2029_novy or
            "Zvestovanie Pána presunuté z 25.3" in status_2029_novy or
            "presúva z 25.3" in status_2029_novy or
            ("Zvestovanie" in status_2029_novy and "25.3" in status_2029_novy)
        )

        # Sv. Ondrej vynechaný (príklad 2031)
        status_ondrej = kinak.zostav_text_status_baru(date(2031, 11, 30))
        self.assertIn("Sv. Ondrej, apoštol vynechaný", status_ondrej)

        # Sv. Filip a Jakub vynechaný (príklad 2035)
        status_fj = kinak.zostav_text_status_baru(date(2035, 5, 3))
        self.assertIn("Sv. Filip a Jakub vynechaný", status_fj)


    def test_neviniatka_sviatok_28_12_pre_kazdy_rok_2028_2050(self):
        """Overí, že 28.12. je NEV, okrem rokov keď pripadne na nedeľu (vtedy má prednosť Svätá rodina)."""
        for rok in range(2028, 2051):
            with self.subTest(rok=rok):
                datum = date(rok, 12, 28)
                kod = kinak.vypocitaj_kod_liturgickej_casti(datum)
                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum), datum)
                status = kinak.zostav_text_status_baru(datum)

                if datum.weekday() == 6:  # nedeľa
                    self.assertEqual(kod, "SR", f"{rok}-12-28 má byť Svätá rodina")
                    self.assertIn("RODINY", hlavicka)
                else:
                    self.assertEqual(kod, "NEV", f"{rok}-12-28 má byť NEV")
                    self.assertIn("NEVINIATOK", hlavicka)
                    self.assertIn("Žalm z NEV zajtra", status)
                    # over že predchádzajúci deň ukazuje zajtra NEV
                    predosly = date(rok, 12, 27)
                    status_pred = kinak.zostav_text_status_baru(predosly)
                    self.assertIn("zajtra NEV", status_pred)

    def test_liturgicky_rok_sa_zmeni_na_prvu_adventnu_nedelu_v_rokoch_2028_a_2029(self):
        pripady = [
            (date(2028, 12, 2), "C", "34c2 zajtra 1AD"),
            (date(2028, 12, 3), "A", "1AD zajtra 1AD"),
            (date(2029, 12, 1), "A", "34c1 zajtra 1AD"),
            (date(2029, 12, 2), "B", "1AD zajtra 1AD"),
        ]

        for datum_slavenia, liturgicky_rok, skratky in pripady:
            with self.subTest(datum=datum_slavenia):
                self.assertEqual(kinak.vypocitaj_liturgicky_rok(datum_slavenia), liturgicky_rok)
                self.assertEqual(kinak.format_skratky_liturgickej_casti(datum_slavenia), skratky)

if __name__ == "__main__":
    unittest.main()
