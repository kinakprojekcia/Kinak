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


class PresunuteSlaveniaTest(unittest.TestCase):
    ZVESTOVANIE_PANA = {
        # 25. marec padá do Veľkého týždňa
        2005: (date(2005, 4, 4), "VP"),
        2013: (date(2013, 4, 8), "VT"),
        2016: (date(2016, 4, 4), "VP"),
        2024: (date(2024, 4, 8), "VT"),
        2040: (date(2040, 4, 9), "VT"),
        2043: (date(2043, 4, 6), "VT"),
        # 25. marec padá do Veľkonočnej oktávy alebo na Veľkonočnú nedeľu
        2008: (date(2008, 3, 31), "VOKT"),
        2035: (date(2035, 4, 2), "1VN"),
        2046: (date(2046, 4, 2), "1VN"),
    }

    def test_zvestovanie_pana_sa_presunie_po_velkonocnej_oktave(self):
        for rok, (ocakavany_datum, _kod_25_marca) in self.ZVESTOVANIE_PANA.items():
            with self.subTest(rok=rok):
                self.assertEqual(ocakavany_datum, kinak.datum_zvestovania_pana(rok))
                self.assertEqual(
                    ocakavany_datum,
                    kinak.vypocitaj_datum_pohyblivych_slaveni(rok)["Zvestovanie Pána*"],
                )

    def test_povodny_25_marec_nezobrazi_zvestovanie_ak_sa_slavnost_presuva(self):
        for rok, (_ocakavany_datum, ocakavany_kod_25_marca) in self.ZVESTOVANIE_PANA.items():
            with self.subTest(rok=rok):
                povodny_datum = date(rok, 3, 25)
                hlavicka = kinak.zostav_text_hlavicky("A", povodny_datum)
                status = kinak.zostav_text_status_baru(povodny_datum)

                self.assertEqual(ocakavany_kod_25_marca, kinak.vypocitaj_kod_liturgickej_casti(povodny_datum))
                self.assertNotIn("ZVESTOVANIE PÁNA", hlavicka.upper())
                self.assertNotIn("Žalm z ZV", status)

    def test_presunuty_den_zobrazi_zvestovanie_v_hlavicke_a_status_bare(self):
        for rok, (presunuty_datum, _kod_25_marca) in self.ZVESTOVANIE_PANA.items():
            with self.subTest(rok=rok):
                hlavicka = kinak.zostav_text_hlavicky("A", presunuty_datum)
                status = kinak.zostav_text_status_baru(presunuty_datum)

                self.assertEqual("ZV", kinak.vypocitaj_kod_liturgickej_casti(presunuty_datum))
                self.assertIn("ZVESTOVANIE PÁNA (Slávnosť)", hlavicka)
                # Poznámka o presune patrí výlučne do status baru, aby sa
                # neduplikovala s hlavičkou (a aby titulok okna nebol
                # zbytočne dlhý).
                self.assertNotIn("presunutá z 25. marca", hlavicka)
                self.assertIn("Žalm z ZV", status)
                self.assertIn("Zvestovanie Pána sa presúva z 25.3.", status)

    def test_rok_bez_presunu_zobrazi_zvestovanie_25_marca(self):
        datum = date(2026, 3, 25)

        self.assertEqual(datum, kinak.datum_zvestovania_pana(2026))
        self.assertEqual("ZV", kinak.vypocitaj_kod_liturgickej_casti(datum))
        self.assertIn("ZVESTOVANIE PÁNA (Slávnosť)", kinak.zostav_text_hlavicky("A", datum))
        self.assertNotIn("presunutá z 25. marca", kinak.zostav_text_hlavicky("A", datum))
        self.assertIn("Žalm z ZV", kinak.zostav_text_status_baru(datum))

    def test_presunute_narodenie_jana_krstitela_zobrazi_povodny_datum_v_status_bare(self):
        pripady = [
            date(2022, 6, 23),
            date(2033, 6, 23),
            date(2038, 6, 23),
        ]

        for datum in pripady:
            with self.subTest(datum=datum):
                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum), datum)
                status = kinak.zostav_text_status_baru(datum)

                self.assertEqual("NJK", kinak.vypocitaj_kod_liturgickej_casti(datum))
                self.assertIn("NARODENIE SV. JÁNA KRSTITEĽA (Slávnosť)", hlavicka)
                # Poznámka o presune patrí výlučne do status baru.
                self.assertNotIn("presunutá z 24. júna", hlavicka)
                self.assertIn("Narodenie Jána Krstiteľa sa presúva z 24.6.", status)

    def test_pohyblive_slavnosti_presuvaju_jana_krstitela_a_maju_prednost(self):
        for rok in (2022, 2033):
            with self.subTest(rok=rok):
                den_pred_presunutym_janom = date(rok, 6, 22)
                presunuty_jan = date(rok, 6, 23)
                srdce_jezisovo = date(rok, 6, 24)

                self.assertEqual(
                    kinak.vypocitaj_datum_pohyblivych_slaveni(rok)["Najsvätejšieho Srdca Ježišovho"],
                    srdce_jezisovo,
                )
                self.assertEqual(kinak.datum_narodenia_jana_krstitela(rok), presunuty_jan)
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(presunuty_jan), "NJK")
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(srdce_jezisovo), "6TS")

                hlavicka_jana = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(presunuty_jan), presunuty_jan)
                hlavicka_srdca = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(srdce_jezisovo), srdce_jezisovo)
                status_jana = kinak.zostav_text_status_baru(presunuty_jan)

                self.assertIn("NARODENIE SV. JÁNA KRSTITEĽA (Slávnosť)", hlavicka_jana)
                # Poznámka o presune patrí výlučne do status baru.
                self.assertNotIn("presunutá z 24. júna", hlavicka_jana)
                self.assertIn("Narodenie Jána Krstiteľa sa presúva z 24.6.", status_jana)
                self.assertIn("NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO (Slávnosť)", hlavicka_srdca)
                self.assertNotIn("NARODENIE SV. JÁNA KRSTITEĽA", hlavicka_srdca)
                self.assertIn(
                    "Vigília: NARODENIE SV. JÁNA KRSTITEĽA",
                    kinak.zostav_text_status_baru(den_pred_presunutym_janom),
                )
                self.assertNotIn(
                    "Vigília: NARODENIE SV. JÁNA KRSTITEĽA",
                    kinak.zostav_text_status_baru(presunuty_jan),
                )

        srdce_2038 = date(2038, 7, 2)
        den_pred_presunutym_janom_2038 = date(2038, 6, 22)
        presunuty_jan_2038 = date(2038, 6, 23)
        bozie_telo_2038 = date(2038, 6, 24)
        tomas_2038 = date(2038, 7, 3)

        self.assertEqual(
            kinak.vypocitaj_datum_pohyblivych_slaveni(2038)["Najsvätejšieho Kristovho Tela a Krvi"],
            bozie_telo_2038,
        )
        self.assertEqual(kinak.datum_narodenia_jana_krstitela(2038), presunuty_jan_2038)
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(presunuty_jan_2038), "NJK")
        hlavicka_jana_2038 = kinak.zostav_text_hlavicky(
            kinak.vypocitaj_liturgicky_rok(presunuty_jan_2038),
            presunuty_jan_2038,
        )
        status_jana_2038 = kinak.zostav_text_status_baru(presunuty_jan_2038)
        self.assertIn("NARODENIE SV. JÁNA KRSTITEĽA (Slávnosť)", hlavicka_jana_2038)
        # Poznámka o presune patrí výlučne do status baru.
        self.assertNotIn("presunutá z 24. júna", hlavicka_jana_2038)
        self.assertIn("Narodenie Jána Krstiteľa sa presúva z 24.6.", status_jana_2038)
        self.assertIn(
            "Vigília: NARODENIE SV. JÁNA KRSTITEĽA",
            kinak.zostav_text_status_baru(den_pred_presunutym_janom_2038),
        )

        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(bozie_telo_2038), "5TS")
        hlavicka_bozieho_tela = kinak.zostav_text_hlavicky(
            kinak.vypocitaj_liturgicky_rok(bozie_telo_2038),
            bozie_telo_2038,
        )
        self.assertIn("NAJSVÄTEJŠIEHO KRISTOVHO TELA A KRVI", hlavicka_bozieho_tela)
        self.assertNotIn("NARODENIE SV. JÁNA KRSTITEĽA", hlavicka_bozieho_tela)

        self.assertEqual(
            kinak.vypocitaj_datum_pohyblivych_slaveni(2038)["Najsvätejšieho Srdca Ježišovho"],
            srdce_2038,
        )
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(srdce_2038), "6TS")
        hlavicka_2038 = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(srdce_2038), srdce_2038)
        self.assertIn("NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO (Slávnosť)", hlavicka_2038)
        self.assertNotIn("NÁVŠTEVA PREBLAHOSLAVENEJ PANNY MÁRIE", hlavicka_2038)
        self.assertNotIn("presunutá", hlavicka_2038)

        self.assertEqual(
            kinak.vypocitaj_datum_pohyblivych_slaveni(2038)["Nepoškvrnené Srdce Panny Márie"],
            tomas_2038,
        )
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(tomas_2038), "7L")
        hlavicka_tomasa = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(tomas_2038), tomas_2038)
        self.assertIn("SV. TOMÁŠA, APOŠTOLA", hlavicka_tomasa)
        self.assertNotIn("NEPOŠKVRNENÉ SRDCE PANNY MÁRIE", hlavicka_tomasa)

    def test_neposkvrnene_srdce_pm_sa_pri_kolizii_so_slavnostou_vynecha(self):
        pripady = [
            (2028, date(2028, 6, 24), "NJK", "NARODENIE SV. JÁNA KRSTITEĽA"),
            (2030, date(2030, 6, 29), "6L", "SV. PETRA A PAVLA, APOŠTOLOV"),
            (2041, date(2041, 6, 29), "6L", "SV. PETRA A PAVLA, APOŠTOLOV"),
        ]

        for rok, datum_slavenia, ocakavany_kod, ocakavany_nazov in pripady:
            with self.subTest(rok=rok):
                self.assertEqual(
                    kinak.vypocitaj_datum_pohyblivych_slaveni(rok)["Nepoškvrnené Srdce Panny Márie"],
                    datum_slavenia,
                )
                self.assertTrue(kinak.je_neposkvrnene_srdce_pm_prekazane(datum_slavenia))
                self.assertEqual(kinak.popis_vynechaneho_slavenia(datum_slavenia), "Nepoškvrnené Srdce Panny Márie vynechané")
                self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(datum_slavenia), ocakavany_kod)
                self.assertEqual(kinak.vypocitaj_aktualnu_liturgicku_cast(datum_slavenia), ocakavany_nazov)
                self.assertIsNone(kinak.nazov_pohybliveho_slavenia_pre_datum(datum_slavenia))

                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum_slavenia), datum_slavenia)
                status = kinak.zostav_text_status_baru(datum_slavenia)
                self.assertIn(f"{ocakavany_nazov} (Slávnosť)", hlavicka)
                self.assertNotIn("Nepoškvrnené Srdce Panny Márie vynechané", hlavicka)
                self.assertIn("Nepoškvrnené Srdce Panny Márie vynechané", status)
                self.assertNotIn("Žalm z 7TS", status)

    def test_sv_jozef_zenich_sa_presunie_z_postnej_nedele_na_pondelok(self):
        pripady = [
            (2028, date(2028, 3, 19), date(2028, 3, 20)),
            (2034, date(2034, 3, 19), date(2034, 3, 20)),
            (2045, date(2045, 3, 19), date(2045, 3, 20)),
        ]

        for rok, povodny_datum, presunuty_datum in pripady:
            with self.subTest(rok=rok):
                self.assertEqual(presunuty_datum, kinak.datum_sv_jozefa_zenicha(rok))
                self.assertNotEqual("3L", kinak.vypocitaj_kod_liturgickej_casti(povodny_datum))
                self.assertEqual("3L", kinak.vypocitaj_kod_liturgickej_casti(presunuty_datum))

                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(presunuty_datum), presunuty_datum)
                status = kinak.zostav_text_status_baru(presunuty_datum)
                self.assertIn("SV. JOZEFA, ŽENÍCHA (Slávnosť)", hlavicka)
                # Poznámka o presune patrí výlučne do status baru.
                self.assertNotIn("presunutá z 19. marca", hlavicka)
                self.assertIn("Sv. Jozef, ženích sa presúva z 19.3.", status)

    def test_sv_jozef_zenich_sa_presunie_z_velkeho_tyzdna_pred_palmovu_nedelu(self):
        pripady = [
            (2035, date(2035, 3, 17), date(2035, 3, 19)),
            (2046, date(2046, 3, 17), date(2046, 3, 19)),
        ]

        for rok, presunuty_datum, povodny_datum in pripady:
            with self.subTest(rok=rok):
                self.assertEqual(presunuty_datum, kinak.datum_sv_jozefa_zenicha(rok))
                self.assertEqual("3L", kinak.vypocitaj_kod_liturgickej_casti(presunuty_datum))
                self.assertEqual("VT", kinak.vypocitaj_kod_liturgickej_casti(povodny_datum))

                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(presunuty_datum), presunuty_datum)
                status = kinak.zostav_text_status_baru(presunuty_datum)
                self.assertIn("SV. JOZEFA, ŽENÍCHA (Slávnosť)", hlavicka)
                # Poznámka o presune patrí výlučne do status baru.
                self.assertNotIn("presunutá z 19. marca", hlavicka)
                self.assertIn("Sv. Jozef, ženích sa presúva z 19.3.", status)

    def test_neposkvrnene_pocatie_sa_presunie_z_adventnej_nedele_na_pondelok(self):
        pripady = [
            (2030, date(2030, 12, 8), date(2030, 12, 9)),
            (2041, date(2041, 12, 8), date(2041, 12, 9)),
            (2047, date(2047, 12, 8), date(2047, 12, 9)),
        ]

        for rok, povodny_datum, presunuty_datum in pripady:
            with self.subTest(rok=rok):
                self.assertEqual(presunuty_datum, kinak.datum_neposkvrneneho_pocatia(rok))
                self.assertEqual("2AD", kinak.vypocitaj_kod_liturgickej_casti(povodny_datum))
                self.assertEqual("12L", kinak.vypocitaj_kod_liturgickej_casti(presunuty_datum))

                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(presunuty_datum), presunuty_datum)
                status_presunuty = kinak.zostav_text_status_baru(presunuty_datum)
                self.assertIn("NEPOŠKVRNENÉ POČATIE PANNY MÁRIE (Slávnosť)", hlavicka)
                # Poznámka o presune patrí výlučne do status baru.
                self.assertNotIn("presunutá z 8. decembra", hlavicka)
                self.assertIn(
                    "Nepoškvrnené počatie Panny Márie sa presúva z 8.12.",
                    status_presunuty,
                )
                self.assertIn(
                    "Vigília: NEPOŠKVRNENÉ POČATIE PANNY MÁRIE",
                    kinak.zostav_text_status_baru(povodny_datum),
                )


if __name__ == "__main__":
    unittest.main()
