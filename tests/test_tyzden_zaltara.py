# -*- coding: utf-8 -*-

from datetime import date, timedelta
import importlib.util
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class TyzdenZaltaraTest(unittest.TestCase):
    RIMSKE_TYZDNE = {1: "I.", 2: "II.", 3: "III.", 4: "IV."}

    def test_adventny_cyklus_zacina_prvou_adventnou_nedelou(self):
        prva_adventna = kinak.prva_adventna_nedela(2025)

        scenare = [
            (prva_adventna, "I."),
            (prva_adventna + timedelta(days=6), "I."),
            (prva_adventna + timedelta(days=7), "II."),
            (prva_adventna + timedelta(days=14), "III."),
            (prva_adventna + timedelta(days=21), "IV."),
        ]

        for datum, ocakavany_tyzden in scenare:
            with self.subTest(datum=datum):
                self.assertEqual(ocakavany_tyzden, kinak.vypocitaj_tyzden_zaltara(datum))

    def test_cezrocne_obdobie_po_krste_pana_startuje_prvym_tyzdnom(self):
        scenare = [
            (date(2026, 1, 12), "1C", "I."),
            (date(2026, 1, 17), "1C", "I."),
            (date(2026, 1, 18), "2C", "II."),
            (date(2026, 2, 8), "5C", "I."),
            (date(2026, 2, 15), "6C", "II."),
        ]

        for datum, ocakavany_kod, ocakavany_tyzden in scenare:
            with self.subTest(datum=datum):
                self.assertEqual(ocakavany_kod, kinak.vypocitaj_kod_liturgickej_casti(datum))
                self.assertEqual(ocakavany_tyzden, kinak.vypocitaj_tyzden_zaltara(datum))

    def test_cezrocne_obdobie_po_turiciach_sedi_s_cislom_cezrocneho_tyzdna(self):
        scenare = [
            (date(2026, 5, 26), "8C", "IV."),
            (date(2026, 6, 8), "10C", "II."),
            (date(2026, 11, 22), "34C", "II."),
            (date(2027, 5, 18), "7C", "III."),
            (date(2027, 11, 21), "34C", "II."),
        ]

        for datum, ocakavany_kod, ocakavany_tyzden in scenare:
            with self.subTest(datum=datum):
                self.assertEqual(ocakavany_kod, kinak.vypocitaj_kod_liturgickej_casti(datum))
                self.assertEqual(ocakavany_tyzden, kinak.vypocitaj_tyzden_zaltara(datum))

    def test_cezrocny_kod_urcuje_tyzden_zaltara_pred_postom_aj_po_turiciach(self):
        datumy = [
            date(2026, 1, 12),
            date(2026, 1, 18),
            date(2026, 2, 8),
            date(2026, 5, 26),
            date(2026, 6, 8),
            date(2026, 11, 22),
            date(2027, 1, 11),
            date(2027, 5, 18),
            date(2027, 11, 21),
        ]

        for datum in datumy:
            kod = kinak.vypocitaj_kod_liturgickej_casti(datum)
            cislo_tyzdna = int(kod[:-1])
            ocakavany_tyzden = self.RIMSKE_TYZDNE[((cislo_tyzdna - 1) % 4) + 1]

            with self.subTest(datum=datum, kod=kod):
                self.assertTrue(kod.endswith("C"))
                self.assertEqual(ocakavany_tyzden, kinak.vypocitaj_tyzden_zaltara(datum))

    def test_krst_pana_na_7_alebo_8_januara_uzatvara_vianocne_obdobie(self):
        scenare = [
            (date(2023, 1, 8), "KKP", "III."),
            (date(2023, 1, 9), "1C", "I."),
            (date(2024, 1, 7), "KKP", "II."),
            (date(2024, 1, 8), "1C", "I."),
        ]

        for datum, ocakavany_kod, ocakavany_tyzden in scenare:
            with self.subTest(datum=datum):
                self.assertEqual(ocakavany_kod, kinak.vypocitaj_kod_liturgickej_casti(datum))
                self.assertEqual(ocakavany_tyzden, kinak.vypocitaj_tyzden_zaltara(datum))

    def test_den_krstu_pana_este_nepouziva_cezrocny_reset(self):
        krst_pana = kinak.krst_krista_pana(2026)

        self.assertEqual("KKP", kinak.vypocitaj_kod_liturgickej_casti(krst_pana))
        self.assertEqual("III.", kinak.vypocitaj_tyzden_zaltara(krst_pana))

    def test_prechod_vianocne_obdobie_cez_krst_pana_do_cezrocneho_obdobia(self):
        krst_pana = kinak.krst_krista_pana(2026)
        den_po_krste = krst_pana + timedelta(days=1)
        najblizsia_nedela = den_po_krste + timedelta(days=(6 - den_po_krste.weekday()) % 7)

        scenare = [
            (krst_pana - timedelta(days=1), "2VI", "II."),
            (krst_pana, "KKP", "III."),
            (den_po_krste, "1C", "I."),
            (najblizsia_nedela, "2C", "II."),
        ]

        for datum, ocakavany_kod, ocakavany_tyzden in scenare:
            with self.subTest(datum=datum):
                self.assertEqual(ocakavany_kod, kinak.vypocitaj_kod_liturgickej_casti(datum))
                self.assertEqual(ocakavany_tyzden, kinak.vypocitaj_tyzden_zaltara(datum))

    def test_popolcova_streda_a_dni_pred_prvou_postnou_nedelou_su_stvrty_tyzden(self):
        velka_noc = kinak.velkonocna_nedela(2026)
        popolcova_streda = velka_noc - timedelta(days=46)
        prva_postna = velka_noc - timedelta(days=42)

        for posun in range((prva_postna - popolcova_streda).days):
            datum = popolcova_streda + timedelta(days=posun)
            with self.subTest(datum=datum):
                self.assertEqual("IV.", kinak.vypocitaj_tyzden_zaltara(datum))

    def test_postne_obdobie_resetuje_cyklus_na_prvu_postnu_nedelu(self):
        prva_postna = kinak.velkonocna_nedela(2026) - timedelta(days=42)

        scenare = [
            (prva_postna, "I."),
            (prva_postna + timedelta(days=7), "II."),
            (prva_postna + timedelta(days=14), "III."),
            (prva_postna + timedelta(days=21), "IV."),
            (prva_postna + timedelta(days=28), "I."),
            (prva_postna + timedelta(days=35), "II."),
        ]

        for datum, ocakavany_tyzden in scenare:
            with self.subTest(datum=datum):
                self.assertEqual(ocakavany_tyzden, kinak.vypocitaj_tyzden_zaltara(datum))

    def test_velkonocne_obdobie_resetuje_cyklus_na_velkonocnu_nedelu(self):
        velka_noc = kinak.velkonocna_nedela(2026)

        scenare = [
            (velka_noc, "I."),
            (velka_noc + timedelta(days=7), "II."),
            (velka_noc + timedelta(days=14), "III."),
            (velka_noc + timedelta(days=21), "IV."),
            (velka_noc + timedelta(days=28), "I."),
            (velka_noc + timedelta(days=49), "IV."),
        ]

        for datum, ocakavany_tyzden in scenare:
            with self.subTest(datum=datum):
                self.assertEqual(ocakavany_tyzden, kinak.vypocitaj_tyzden_zaltara(datum))

    def test_velkonocna_vigilia_pouziva_prvy_tyzden_zaltara(self):
        for rok in range(2022, 2026):
            velkonocna_vigilia = kinak.velkonocna_nedela(rok) - timedelta(days=1)

            with self.subTest(rok=rok, datum=velkonocna_vigilia):
                self.assertEqual("VG", kinak.vypocitaj_kod_liturgickej_casti(velkonocna_vigilia))
                self.assertEqual("I.", kinak.vypocitaj_tyzden_zaltara(velkonocna_vigilia))

    def test_postny_a_velkonocny_reset_funguje_aj_v_roku_s_inym_datumom_velkej_noci(self):
        velka_noc = kinak.velkonocna_nedela(2027)
        popolcova_streda = velka_noc - timedelta(days=46)
        prva_postna = velka_noc - timedelta(days=42)

        scenare = [
            (popolcova_streda, "PS", "IV."),
            (prva_postna, "1P", "I."),
            (prva_postna + timedelta(days=7), "2P", "II."),
            (velka_noc - timedelta(days=7), "VT", "II."),
            (velka_noc, "1VN", "I."),
            (velka_noc + timedelta(days=7), "2VN", "II."),
            (velka_noc + timedelta(days=14), "3VN", "III."),
        ]

        for datum, ocakavany_kod, ocakavany_tyzden in scenare:
            with self.subTest(datum=datum):
                self.assertEqual(ocakavany_kod, kinak.vypocitaj_kod_liturgickej_casti(datum))
                self.assertEqual(ocakavany_tyzden, kinak.vypocitaj_tyzden_zaltara(datum))

    def test_status_bar_zobrazuje_tyzden_zaltara_vo_viacerych_obdobiach(self):
        scenare = [
            (date(2026, 1, 12), "Žaltár v breviári: I. týždeň"),
            (date(2026, 2, 18), "Žaltár v breviári: IV. týždeň"),
            (date(2026, 2, 22), "Žaltár v breviári: I. týždeň"),
            (date(2026, 4, 5), "Žaltár v breviári: I. týždeň"),
            (date(2026, 11, 22), "Žaltár v breviári: II. týždeň"),
        ]

        for datum, ocakavany_text in scenare:
            with self.subTest(datum=datum):
                self.assertIn(ocakavany_text, kinak.zostav_text_status_baru(datum))

    def test_sobota_pred_adventom_ostava_v_starom_cykle_a_advent_resetuje_na_prvy_tyzden(self):
        prva_adventna = kinak.prva_adventna_nedela(2026)
        sobota_pred_adventom = prva_adventna - timedelta(days=1)

        self.assertEqual("34C", kinak.vypocitaj_kod_liturgickej_casti(sobota_pred_adventom))
        self.assertEqual("II.", kinak.vypocitaj_tyzden_zaltara(sobota_pred_adventom))
        self.assertIn("Žaltár v breviári: II. týždeň", kinak.zostav_text_status_baru(sobota_pred_adventom))

        self.assertEqual("1AD", kinak.vypocitaj_kod_liturgickej_casti(prva_adventna))
        self.assertEqual("I.", kinak.vypocitaj_tyzden_zaltara(prva_adventna))
        self.assertIn("Žaltár v breviári: I. týždeň", kinak.zostav_text_status_baru(prva_adventna))

    def test_status_bar_pouziva_vypocitany_tyzden_zaltara(self):
        status = kinak.zostav_text_status_baru(date(2026, 1, 12))

        self.assertIn("Žaltár v breviári: I. týždeň", status)


if __name__ == "__main__":
    unittest.main()
