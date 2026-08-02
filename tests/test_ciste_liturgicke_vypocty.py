# -*- coding: utf-8 -*-

from datetime import date, timedelta
import importlib.util
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class CisteLiturgickeVypoctyTest(unittest.TestCase):
    def test_prva_adventna_nedela_je_nedela_v_tyzdni_s_tretim_decembrom(self):
        ocakavane = {
            2023: date(2023, 12, 3),
            2024: date(2024, 12, 1),
            2025: date(2025, 11, 30),
            2026: date(2026, 11, 29),
        }

        for rok, ocakavany_datum in ocakavane.items():
            with self.subTest(rok=rok):
                vysledok = kinak.prva_adventna_nedela(rok)
                self.assertEqual(ocakavany_datum, vysledok)
                self.assertEqual(6, vysledok.weekday())
                self.assertLessEqual(vysledok, date(rok, 12, 3))
                self.assertLess((date(rok, 12, 3) - vysledok).days, 7)

    def test_velkonocna_nedela_zname_datumy_a_rozsah(self):
        zname_datumy = {
            2019: date(2019, 4, 21),
            2020: date(2020, 4, 12),
            2021: date(2021, 4, 4),
            2022: date(2022, 4, 17),
            2023: date(2023, 4, 9),
            2024: date(2024, 3, 31),
            2025: date(2025, 4, 20),
            2026: date(2026, 4, 5),
            2027: date(2027, 3, 28),
            2028: date(2028, 4, 16),
        }

        for rok, ocakavany_datum in zname_datumy.items():
            with self.subTest(rok=rok):
                vysledok = kinak.velkonocna_nedela(rok)
                self.assertEqual(ocakavany_datum, vysledok)
                self.assertEqual(6, vysledok.weekday())

        for rok in range(2000, 2100):
            with self.subTest(rozsah=rok):
                vysledok = kinak.velkonocna_nedela(rok)
                self.assertGreaterEqual(vysledok, date(rok, 3, 22))
                self.assertLessEqual(vysledok, date(rok, 4, 25))

    def test_najblizsia_nedela_po_dni_je_striktne_po_datume(self):
        priklady = {
            date(2023, 1, 2): date(2023, 1, 8),
            date(2023, 1, 7): date(2023, 1, 8),
            date(2023, 1, 8): date(2023, 1, 15),
        }

        for vstup, ocakavany_datum in priklady.items():
            with self.subTest(vstup=vstup):
                self.assertEqual(ocakavany_datum, kinak.najblizsia_nedela_po_dni(vstup))

        for offset in range(7):
            vstup = date(2024, 6, 1) + timedelta(days=offset)
            vysledok = kinak.najblizsia_nedela_po_dni(vstup)
            with self.subTest(vstup=vstup):
                self.assertEqual(6, vysledok.weekday())
                self.assertGreater(vysledok, vstup)
                self.assertLessEqual((vysledok - vstup).days, 7)

    def test_nedela_zaciatku_tyzdna_vracia_nedelu_toho_isteho_tyzdna(self):
        nedela = date(2024, 5, 5)

        for offset in range(7):
            vstup = nedela + timedelta(days=offset)
            with self.subTest(vstup=vstup):
                vysledok = kinak.nedela_zaciatku_tyzdna(vstup)
                self.assertEqual(nedela, vysledok)
                self.assertEqual(6, vysledok.weekday())
                self.assertLessEqual(vysledok, vstup)

    def test_krst_krista_pana_je_nedela_po_zjaveni_pana(self):
        ocakavane = {
            2024: date(2024, 1, 7),
            2025: date(2025, 1, 12),
            2026: date(2026, 1, 11),
        }

        for rok, ocakavany_datum in ocakavane.items():
            with self.subTest(rok=rok):
                self.assertEqual(ocakavany_datum, kinak.krst_krista_pana(rok))

        for rok in range(2020, 2035):
            with self.subTest(rozsah=rok):
                vysledok = kinak.krst_krista_pana(rok)
                self.assertEqual(6, vysledok.weekday())
                self.assertGreater(vysledok, date(rok, 1, 6))

    def test_zvestovanie_pana_sa_presuva_po_velkonocnej_oktave(self):
        ocakavane = {
            2016: date(2016, 4, 4),
            2035: date(2035, 4, 2),
        }

        self.assertEqual(date(2023, 3, 25), kinak.datum_zvestovania_pana(2023))

        for rok, ocakavany_datum in ocakavane.items():
            with self.subTest(rok=rok):
                vysledok = kinak.datum_zvestovania_pana(rok)
                self.assertEqual(ocakavany_datum, vysledok)
                self.assertEqual(0, vysledok.weekday())

    def test_pohyblive_slavenia_maju_stabilne_hodnoty_a_ocakavane_offsety(self):
        for rok in range(2020, 2030):
            with self.subTest(rok=rok):
                prve_volanie = dict(kinak.vypocitaj_datum_pohyblivych_slaveni(rok))
                druhe_volanie = dict(kinak.vypocitaj_datum_pohyblivych_slaveni(rok))
                self.assertEqual(prve_volanie, druhe_volanie)

                velka_noc = prve_volanie["Veľkonočná nedeľa"]
                self.assertEqual(velka_noc - timedelta(days=46), prve_volanie["Popolcová streda"])
                self.assertEqual(velka_noc - timedelta(days=7), prve_volanie["Palmová (Kvetná nedeľa)"])
                self.assertEqual(velka_noc + timedelta(days=49), prve_volanie["Nedeľa zoslania Ducha Svätého (Turíce)"])
                self.assertEqual(velka_noc + timedelta(days=39), prve_volanie["Nanebovstúpenie Pána"])
                self.assertEqual(
                    prve_volanie["Prvá adventná nedeľa (začína nový liturgický rok)"] - timedelta(days=7),
                    prve_volanie["Krista Kráľa"],
                )

    def test_svata_rodina_je_nedela_po_narodeni_alebo_tridsiateho_decembra(self):
        for rok in range(2000, 2050):
            s = kinak.vypocitaj_datum_pohyblivych_slaveni(rok)
            vysledok = s["Svätej rodiny Ježiša, Márie a Jozefa"]
            narodenie = date(rok, 12, 25)

            with self.subTest(rok=rok):
                if narodenie.weekday() == 6:
                    self.assertEqual(date(rok, 12, 30), vysledok)
                else:
                    self.assertEqual(6, vysledok.weekday())
                    self.assertGreater(vysledok, narodenie)
                    self.assertLessEqual((vysledok - narodenie).days, 7)

    def test_narodenie_jana_krstitela_sa_presuva_len_pri_kolizii(self):
        for rok in range(2000, 2050):
            s = kinak.vypocitaj_datum_pohyblivych_slaveni(rok)
            kolizne_datumy = {
                s["Najsvätejšieho Kristovho Tela a Krvi"],
                s["Najsvätejšieho Srdca Ježišovho"],
            }
            povodny_datum = date(rok, 6, 24)
            ocakavany_datum = date(rok, 6, 23) if povodny_datum in kolizne_datumy else povodny_datum

            with self.subTest(rok=rok):
                self.assertEqual(ocakavany_datum, kinak.datum_narodenia_jana_krstitela(rok))

    def test_sv_jozef_zenich_sa_presuva_pri_nedeli_alebo_velkom_tyzdni(self):
        for rok in range(2000, 2050):
            povodny_datum = date(rok, 3, 19)
            velka_noc = kinak.velkonocna_nedela(rok)
            palmova_nedela = velka_noc - timedelta(days=7)

            if palmova_nedela <= povodny_datum < velka_noc:
                ocakavany_datum = palmova_nedela - timedelta(days=1)
            elif povodny_datum.weekday() == 6:
                ocakavany_datum = date(rok, 3, 20)
            else:
                ocakavany_datum = povodny_datum

            with self.subTest(rok=rok):
                self.assertEqual(ocakavany_datum, kinak.datum_sv_jozefa_zenicha(rok))

    def test_neposkvrnene_pocatie_sa_presuva_z_adventnej_nedele_na_pondelok(self):
        self.assertEqual(date(2023, 12, 8), kinak.datum_neposkvrneneho_pocatia(2023))
        self.assertEqual(date(2019, 12, 9), kinak.datum_neposkvrneneho_pocatia(2019))

        for rok in range(2000, 2050):
            povodny_datum = date(rok, 12, 8)
            ocakavany_datum = date(rok, 12, 9) if povodny_datum.weekday() == 6 else povodny_datum
            with self.subTest(rok=rok):
                vysledok = kinak.datum_neposkvrneneho_pocatia(rok)
                self.assertEqual(ocakavany_datum, vysledok)
                self.assertNotEqual(6, vysledok.weekday())

    def test_liturgicky_rok_sa_meni_od_prvej_adventnej_nedele(self):
        for rok in range(2020, 2030):
            advent = kinak.prva_adventna_nedela(rok)
            ocakavany_pred_adventom = ["A", "B", "C"][(rok - 1) % 3]
            ocakavany_od_adventu = ["A", "B", "C"][rok % 3]

            scenare = [
                (advent - timedelta(days=1), ocakavany_pred_adventom),
                (advent, ocakavany_od_adventu),
                (advent + timedelta(days=1), ocakavany_od_adventu),
            ]

            for vstup, ocakavany_rok in scenare:
                with self.subTest(rok=rok, vstup=vstup):
                    self.assertEqual(ocakavany_rok, kinak.vypocitaj_liturgicky_rok(vstup))

        self.assertEqual("C", kinak.vypocitaj_liturgicky_rok(date(2025, 6, 1)))
        self.assertEqual("A", kinak.vypocitaj_liturgicky_rok(kinak.prva_adventna_nedela(2025)))

    def test_format_cislo_piesne_pre_vstup_zachova_varianty(self):
        self.assertEqual("1", kinak.format_cislo_piesne_pre_vstup("001"))
        self.assertEqual("269", kinak.format_cislo_piesne_pre_vstup("269"))
        self.assertEqual("001a", kinak.format_cislo_piesne_pre_vstup("001a"))
        self.assertEqual("269b", kinak.format_cislo_piesne_pre_vstup("269b"))
        self.assertEqual("", kinak.format_cislo_piesne_pre_vstup(""))


if __name__ == "__main__":
    unittest.main()
