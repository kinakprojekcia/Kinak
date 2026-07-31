# -*- coding: utf-8 -*-

from datetime import date, timedelta
import importlib.util
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class PohybliveSlaveniaZobrazenieTest(unittest.TestCase):
    ROK = 2026

    OCAKAVANE = {
        "Prvá adventná nedeľa (začína nový liturgický rok)": ("1AD", "1. ADVENTNÁ NEDEĽA"),
        "Svätej rodiny Ježiša, Márie a Jozefa": ("SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA"),
        "Krst Krista Pána": ("KKP", "KRST KRISTA PÁNA"),
        "Zvestovanie Pána*": ("ZV", "ZVESTOVANIE PÁNA"),
        "Popolcová streda": ("PS", "POPOLCOVÁ STREDA"),
        "Palmová (Kvetná nedeľa)": ("VT", "PALMOVÁ (KVETNÁ NEDEĽA)"),
        "Veľkonočná nedeľa": ("1VN", "VEĽKONOČNÁ NEDEĽA"),
        "Pondelok vo Veľkonočnej oktáve": ("VPON", "PONDELOK VO VEĽKONOČNEJ OKTÁVE"),
        "Nedeľa Božieho milosrdenstva": ("2VN", "NEDEĽA BOŽIEHO MILOSRDENSTVA"),
        "Nanebovstúpenie Pána": ("NP", "NANEBOVSTÚPENIE PÁNA"),
        "Nedeľa zoslania Ducha Svätého (Turíce)": ("1TS", "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO"),
        "Panny Márie, Matky Cirkvi": ("2TS", "PANNY MÁRIE, MATKY CIRKVI"),
        "Pána Ježiša Krista, najvyššieho a večného kňaza": (
            "3TS",
            "PÁNA JEŽIŠA KRISTA, NAJVYŠŠIEHO A VEČNÉHO KŇAZA",
        ),
        "Najsvätejšej Trojice": ("4TS", "NAJSVÄTEJŠIA TROJICA"),
        "Najsvätejšieho Kristovho Tela a Krvi": ("5TS", "NAJSVÄTEJŠIEHO KRISTOVHO TELA A KRVI"),
        "Najsvätejšieho Srdca Ježišovho": ("6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO"),
        "Nepoškvrnené Srdce Panny Márie": ("7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE"),
        "Krista Kráľa": ("34c2", "KRISTA KRÁĽA"),
    }

    def test_vsetky_pohyblive_slavenia_su_pokryte_testom(self):
        datumy = kinak.vypocitaj_datum_pohyblivych_slaveni(self.ROK)
        self.assertEqual(set(self.OCAKAVANE), set(datumy))

    def test_hlavicka_a_status_bar_pre_vsetky_pohyblive_slavenia(self):
        datumy = kinak.vypocitaj_datum_pohyblivych_slaveni(self.ROK)

        for nazov, (ocakavana_skratka, ocakavany_text_hlavicky) in self.OCAKAVANE.items():
            with self.subTest(slavenie=nazov):
                datum = datumy[nazov]
                hlavicka = kinak.zostav_text_hlavicky("A", datum)
                status = kinak.zostav_text_status_baru(datum)

                self.assertIn("Kinak v", hlavicka)
                self.assertIn("Liturgický rok A", hlavicka)
                self.assertIn(ocakavany_text_hlavicky.upper(), hlavicka.upper())
                self.assertNotIn("Vigília:", hlavicka)

                self.assertIn(f"Žalm z {ocakavana_skratka}", status)
                self.assertIn("zajtra ", status)
                self.assertIn("Žaltár v breviári:", status)
                self.assertIn("týždeň", status)

    def test_presunute_zvestovanie_pana_sa_zobrazi_ako_slavnost(self):
        datum = kinak.vypocitaj_datum_pohyblivych_slaveni(2016)["Zvestovanie Pána*"]
        self.assertEqual(date(2016, 4, 4), datum)

        hlavicka = kinak.zostav_text_hlavicky("C", datum)
        status = kinak.zostav_text_status_baru(datum)

        self.assertIn("ZVESTOVANIE PÁNA", hlavicka.upper())
        self.assertIn("(Slávnosť)", hlavicka)
        self.assertIn("Žalm z ZV", status)

    def test_vigilie_pohyblivych_slavnosti_su_v_status_bare(self):
        datumy = kinak.vypocitaj_datum_pohyblivych_slaveni(self.ROK)
        vigilie = {
            datumy["Nanebovstúpenie Pána"] - timedelta(days=1): "NANEBOVSTÚPENIE PÁNA",
            datumy["Nedeľa zoslania Ducha Svätého (Turíce)"] - timedelta(days=1): (
                "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO (TURÍCE)"
            ),
        }

        for datum, ocakavana_vigilia in vigilie.items():
            with self.subTest(datum=datum):
                hlavicka = kinak.zostav_text_hlavicky("A", datum)
                status = kinak.zostav_text_status_baru(datum)

                self.assertNotIn("Vigília:", hlavicka)
                self.assertIn(f"Vigília: {ocakavana_vigilia}", status)

    def test_sv_filip_jakub_vynechanie_je_v_status_bare_nie_v_hlavicke(self):
        # 3.5.2026 – 5. veľkonočná nedeľa má prednosť, Sv. Filip a Jakub vynechaný
        datum = date(2026, 5, 3)
        hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum), datum)
        status = kinak.zostav_text_status_baru(datum)

        self.assertTrue(kinak.je_sv_filip_jakub_prekazany(datum))
        self.assertIn("Sv. Filip a Jakub vynechaný", status)
        self.assertNotIn("Sv. Filip a Jakub vynechaný", hlavicka)
        self.assertNotIn("Žalm z FJ", status)
        self.assertIn("Žalm z 5VN", status)

    def test_prednost_nedele_pred_sviatkom_je_v_status_bare_nie_v_hlavicke(self):
        # 18.10.2026 – 29. cezročná nedeľa má prednosť pred Sv. Lukášom
        datum = date(2026, 10, 18)
        hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum), datum)
        status = kinak.zostav_text_status_baru(datum)

        self.assertEqual("29C", kinak.vypocitaj_kod_liturgickej_casti(datum))
        self.assertIn("nedeľa má prednosť pred: SV. LUKÁŠA, EVANJELISTU", status)
        self.assertNotIn("nedeľa má prednosť pred", hlavicka)
        self.assertIn("Žalm z 29c2", status)

    def test_presun_jana_krstitela_je_v_status_bare(self):
        # V roku 2022 padne 24.6. na Božie Telo (pohyblivé), NJK sa presunie na 23.6.
        presunuty = kinak.datum_narodenia_jana_krstitela(2022)
        self.assertEqual(date(2022, 6, 23), presunuty)

        status = kinak.zostav_text_status_baru(presunuty)
        hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(presunuty), presunuty)

        self.assertEqual("NJK", kinak.vypocitaj_kod_liturgickej_casti(presunuty))
        self.assertIn("NARODENIE SV. JÁNA KRSTITEĽA", hlavicka)
        self.assertIn("Narodenie Jána Krstiteľa sa presúva z 24.6.", status)
        self.assertNotIn("Narodenie Jána Krstiteľa sa presúva z 24.6.", hlavicka)


if __name__ == "__main__":
    unittest.main()
