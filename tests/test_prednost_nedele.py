# -*- coding: utf-8 -*-

from datetime import date
import importlib.util
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


class PrednostNedeleTest(unittest.TestCase):
    def test_cezrocna_nedela_ma_prednost_pred_sviatkom_panny_marie(self):
        datum = date(2024, 9, 8)
        hlavicka = kinak.zostav_text_hlavicky("A", datum)
        status = kinak.zostav_text_status_baru(datum)

        self.assertEqual("23C", kinak.vypocitaj_kod_liturgickej_casti(datum))
        self.assertIn("23. TÝŽDEŇ CEZROČNÉHO OBDOBIA", hlavicka)
        self.assertIn("nedeľa má prednosť pred: NARODENIE PANNY MÁRIE", status)
        self.assertIn("Žalm z 23c2 zajtra 23c2", status)
        self.assertNotIn("Žalm z NPMAR", status)

    def test_cezrocna_nedela_ma_prednost_pred_sviatkom_archanjelov(self):
        datum = date(2030, 9, 29)
        hlavicka = kinak.zostav_text_hlavicky("A", datum)
        status = kinak.zostav_text_status_baru(datum)

        self.assertEqual("26C", kinak.vypocitaj_kod_liturgickej_casti(datum))
        self.assertIn("26. TÝŽDEŇ CEZROČNÉHO OBDOBIA", hlavicka)
        self.assertIn("nedeľa má prednosť pred: SV. MICHALA, GABRIELA A RAFAELA, ARCHANJELI", status)
        self.assertIn("Žalm z 26c2 zajtra 26c2", status)
        self.assertNotIn("Žalm z MGR", status)

    def test_sviatok_pana_ma_prednost_pred_cezrocnou_nedelou(self):
        datum = date(2028, 8, 6)
        hlavicka = kinak.zostav_text_hlavicky("A", datum)
        status = kinak.zostav_text_status_baru(datum)

        self.assertEqual("PREM", kinak.vypocitaj_kod_liturgickej_casti(datum))
        self.assertIn("PREMENENIE PÁNA (Sviatok), nedeľa", hlavicka)
        self.assertIn("Žalm z PREM", status)
        self.assertNotIn("nedeľa má prednosť pred", hlavicka)

    def test_osobitny_sviatok_ma_prednost_pred_cezrocnou_nedelou(self):
        datum = date(2031, 11, 9)
        hlavicka = kinak.zostav_text_hlavicky("A", datum)
        status = kinak.zostav_text_status_baru(datum)

        self.assertEqual("VPLB", kinak.vypocitaj_kod_liturgickej_casti(datum))
        self.assertIn("VÝROČIE POSVIACKY LATERÁNSKEJ BAZILIKY (Sviatok), nedeľa", hlavicka)
        self.assertIn("Žalm z VPLB", status)
        self.assertNotIn("nedeľa má prednosť pred", hlavicka)

    def test_slavnost_ma_prednost_pred_cezrocnou_nedelou(self):
        datum = date(2026, 7, 5)
        hlavicka = kinak.zostav_text_hlavicky("A", datum)
        status = kinak.zostav_text_status_baru(datum)

        self.assertEqual("CMV", kinak.vypocitaj_kod_liturgickej_casti(datum))
        self.assertIn("SV. CYRILA A METODA (Slávnosť)", hlavicka)
        self.assertIn("Žalm z CMV", status)
        self.assertNotIn("nedeľa má prednosť pred", hlavicka)

    def test_privilegovana_velkonocna_nedela_ma_prednost_a_zvestovanie_sa_presunie(self):
        velka_noc = date(2035, 3, 25)
        presunute_zvestovanie = date(2035, 4, 2)

        hlavicka_velka_noc = kinak.zostav_text_hlavicky("A", velka_noc)
        hlavicka_zvestovanie = kinak.zostav_text_hlavicky("A", presunute_zvestovanie)

        self.assertEqual("1VN", kinak.vypocitaj_kod_liturgickej_casti(velka_noc))
        self.assertIn("Veľkonočná nedeľa", hlavicka_velka_noc)
        self.assertNotIn("ZVESTOVANIE PÁNA", hlavicka_velka_noc)

        self.assertEqual("ZV", kinak.vypocitaj_kod_liturgickej_casti(presunute_zvestovanie))
        self.assertIn("ZVESTOVANIE PÁNA (Slávnosť)", hlavicka_zvestovanie)

    def test_vyssie_dni_maju_prednost_pred_neuvedenymi_alebo_prekazanymi_sviatkami(self):
        pripady = [
            (date(2031, 11, 30), "1AD", "1. ADVENTNÁ NEDEĽA", "OND"),
            (date(2036, 11, 30), "1AD", "1. ADVENTNÁ NEDEĽA", "OND"),
            (date(2042, 11, 30), "1AD", "1. ADVENTNÁ NEDEĽA", "OND"),
            (date(2028, 4, 23), "2VN", "2. VEĽKONOČNÁ NEDEĽA", None),
            (date(2038, 4, 23), "VP", "VEĽKÝ PIATOK", None),
            (date(2038, 4, 25), "1VN", "VEĽKONOČNÁ NEDEĽA", "4L"),
            (date(2049, 4, 25), "2VN", "2. VEĽKONOČNÁ NEDEĽA", "4L"),
            (date(2035, 5, 3), "NP", "NANEBOVSTÚPENIE PÁNA", "FJ"),
            (date(2046, 5, 3), "NP", "NANEBOVSTÚPENIE PÁNA", "FJ"),
        ]

        for datum_slavenia, ocakavany_kod, ocakavany_nazov, prekazany_kod in pripady:
            with self.subTest(datum=datum_slavenia):
                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum_slavenia), datum_slavenia)
                status = kinak.zostav_text_status_baru(datum_slavenia)

                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), ocakavany_kod)
                self.assertIn(ocakavany_nazov, kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia))
                self.assertIn(ocakavany_nazov, hlavicka.upper())
                if prekazany_kod:
                    self.assertNotIn(f"Žalm z {prekazany_kod}", status)

    def test_sv_filip_jakub_sa_pri_kolizii_vynecha(self):
        """3.5. (Sv. Filip a Jakub) sa vynechá tak pri kolízii s privilegovanou
        veľkonočnou nedeľou (2026, 2037, 2043, 2048), ako aj pri kolízii
        s Nanebovstúpením Pána (2035, 2046) – a poznámka o vynechaní musí byť
        zhodne v hlavičke aj v status bare."""
        kolizne_roky = [
            (date(2026, 5, 3), "5VN"),
            (date(2035, 5, 3), "NP"),
            (date(2037, 5, 3), "5VN"),
            (date(2043, 5, 3), "6VN"),
            (date(2046, 5, 3), "NP"),
            (date(2048, 5, 3), "5VN"),
        ]
        for datum, ocakavany_kod in kolizne_roky:
            with self.subTest(datum=datum):
                self.assertTrue(kinak.je_sv_filip_jakub_prekazany(datum))
                self.assertEqual(kinak.popis_vynechaneho_slavenia(datum), "Sv. Filip a Jakub vynechaný")
                self.assertEqual(ocakavany_kod, kinak.vypocitaj_kod_liturgickej_casti(datum))

                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum), datum)
                status = kinak.zostav_text_status_baru(datum)

                self.assertNotIn("Sv. Filip a Jakub vynechaný", hlavicka)
                self.assertIn("Sv. Filip a Jakub vynechaný", status)
                self.assertNotIn("Žalm z FJ", status)

    def test_sv_filip_jakub_sa_bezne_slavi_bez_kolizie(self):
        """V rokoch bez kolízie sa Sv. Filip a Jakub slávi normálne a žiadna
        poznámka o vynechaní sa nesmie objaviť ani v hlavičke, ani v status bare."""
        bezne_roky = [date(2027, 5, 3), date(2028, 5, 3), date(2029, 5, 3), date(2030, 5, 3)]
        for datum in bezne_roky:
            with self.subTest(datum=datum):
                self.assertFalse(kinak.je_sv_filip_jakub_prekazany(datum))
                self.assertIsNone(kinak.popis_vynechaneho_slavenia(datum))
                self.assertEqual("FJ", kinak.vypocitaj_kod_liturgickej_casti(datum))

                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum), datum)
                status = kinak.zostav_text_status_baru(datum)

                self.assertIn("SV. FILIPA A JAKUBA, APOŠTOLOV (Sviatok)", hlavicka)
                self.assertIn("Žalm z FJ", status)
                self.assertNotIn("vynechaný", hlavicka)
                self.assertNotIn("vynechaný", status)

    def test_sv_ondrej_sa_pri_kolizii_s_adventnou_nedelou_vynecha(self):
        """30.11. (Sv. Ondrej) sa pri kolízii s 1. adventnou nedeľou vynechá
        a poznámka o vynechaní musí byť zhodne v hlavičke aj v status bare."""
        kolizne_roky = [date(2031, 11, 30), date(2036, 11, 30), date(2042, 11, 30)]
        for datum in kolizne_roky:
            with self.subTest(datum=datum):
                self.assertTrue(kinak.je_sv_ondrej_prekazany(datum))
                self.assertEqual(
                    kinak.popis_vynechaneho_slavenia(datum),
                    "Sv. Ondrej, apoštol vynechaný (1. adventná nedeľa má prednosť)",
                )
                self.assertEqual("1AD", kinak.vypocitaj_kod_liturgickej_casti(datum))

                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum), datum)
                status = kinak.zostav_text_status_baru(datum)

                self.assertNotIn("Sv. Ondrej, apoštol vynechaný", hlavicka)
                self.assertIn("Sv. Ondrej, apoštol vynechaný", status)
                self.assertNotIn("Žalm z OND", status)

    def test_sv_ondrej_sa_bezne_slavi_bez_kolizie(self):
        """V rokoch bez kolízie sa Sv. Ondrej slávi normálne a žiadna poznámka
        o vynechaní sa nesmie objaviť ani v hlavičke, ani v status bare."""
        bezne_roky = [date(2026, 11, 30), date(2027, 11, 30), date(2028, 11, 30), date(2029, 11, 30)]
        for datum in bezne_roky:
            with self.subTest(datum=datum):
                self.assertFalse(kinak.je_sv_ondrej_prekazany(datum))
                self.assertIsNone(kinak.popis_vynechaneho_slavenia(datum))
                self.assertEqual("OND", kinak.vypocitaj_kod_liturgickej_casti(datum))

                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum), datum)
                status = kinak.zostav_text_status_baru(datum)

                self.assertIn("SV. ONDREJA, APOŠTOLA (Sviatok)", hlavicka)
                self.assertIn("Žalm z OND", status)
                self.assertNotIn("vynechaný", hlavicka)
                self.assertNotIn("vynechaný", status)



if __name__ == "__main__":
    unittest.main()
