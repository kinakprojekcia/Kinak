# -*- coding: utf-8 -*-
"""
Unit test: duplicita poznámky v Hlavičke a v Status bar.

Poznámky o vynechaní pevného slávenia (Sv. Ondrej, Sv. Filip a Jakub,
Sv. Štefan, Sv. Neviniatka, Nepoškvrnené Srdce Panny Márie, Sv. rodina
presunutá na 30.12.) a poznámky o presune/anticipácii pohyblivého dátumu
slávnosti (Zvestovanie Pána, Narodenie sv. Jána Krstiteľa, Sv. Jozef -
ženích, Nepoškvrnené počatie Panny Márie) majú v Kinak.py podľa zámeru
patriť VÝLUČNE do status baru (zostav_text_status_baru), nie do hlavičky
okna (zostav_text_hlavicky) - viď komentáre priamo v zdrojovom kóde
funkcie zostav_text_hlavicky.

Dôvod: v hlavičke by bola informácia duplicitná (status bar ju už
poskytuje) a navyše by zbytočne predlžovala titulok okna, ktorý sa potom
nemusí celý zobraziť.

Tento test preto pre každý známy kolízny/presunový scenár (pokryté
konkrétnymi rokmi 2022-2056, v ktorých daná kolízia/presun reálne
nastáva) overuje:
  1) že STATUS BAR poznámku obsahuje (informácia sa nesmie stratiť),
  2) že HLAVIČKA rovnaké kľúčové slová/frázy NEOBSAHUJE (žiadna duplicita).
"""

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


class DuplicitaPoznamkyVHlavickeAVStatusBarTest(unittest.TestCase):
    """Pre každý scenár overí, že poznámka o vynechaní/presune je
    PRÁVE v status bare a NIE JE duplicitne aj v hlavičke."""

    def assert_poznamka_iba_v_status_bare(self, datum, ocakavany_fragment_statusu,
                                           zakazane_frazy_v_hlavicke):
        """
        datum: dátum, ktorý sa má overiť
        ocakavany_fragment_statusu: podreťazec, ktorý MUSÍ byť v status bare
        zakazane_frazy_v_hlavicke: zoznam podreťazcov, ktoré sa NESMÚ
            vyskytnúť v hlavičke (typicky kľúčové slová danej poznámky)
        """
        with self.subTest(datum=datum):
            hlavicka = kinak.zostav_text_hlavicky(dnes=datum)
            status = kinak.zostav_text_status_baru(dnes=datum)

            # 1) Status bar musí poznámku obsahovať - informácia sa nesmie stratiť.
            self.assertIn(
                ocakavany_fragment_statusu,
                status,
                f"{datum}: status bar neobsahuje očakávanú poznámku "
                f"'{ocakavany_fragment_statusu}' (status bar: '{status}')",
            )

            # 2) Hlavička nesmie obsahovať rovnakú informáciu duplicitne.
            for fraza in zakazane_frazy_v_hlavicke:
                self.assertNotIn(
                    fraza,
                    hlavicka,
                    f"{datum}: hlavička obsahuje duplicitnú poznámku "
                    f"'{fraza}', hoci tá istá informácia je už v status bare "
                    f"(hlavička: '{hlavicka}')",
                )

    # ------------------------------------------------------------------
    # VYNECHANIA (pevné slávenie sa v danom roku vynecháva, nepresúva sa)
    # ------------------------------------------------------------------

    def test_nspm_vynechane_2028(self):
        self.assert_poznamka_iba_v_status_bare(
            date(2028, 6, 24),
            "Nepoškvrnené Srdce Panny Márie vynechané",
            ["vynechané", "vynechaný", "vynechaní"],
        )

    def test_sv_ondrej_vynechany_2025(self):
        self.assert_poznamka_iba_v_status_bare(
            date(2025, 11, 30),
            "Sv. Ondrej, apoštol vynechaný",
            ["vynechaný", "Ondrej"],
        )

    def test_sv_filip_jakub_vynechany_2026(self):
        self.assert_poznamka_iba_v_status_bare(
            date(2026, 5, 3),
            "Sv. Filip a Jakub vynechaný",
            ["vynechaný", "Filip"],
        )

    def test_sv_stefan_vynechany_2027(self):
        self.assert_poznamka_iba_v_status_bare(
            date(2027, 12, 26),
            "Sv. Štefan, prvý mučeník vynechaný",
            ["vynechaný", "Štefan"],
        )

    def test_sv_neviniatka_vynechani_2025(self):
        self.assert_poznamka_iba_v_status_bare(
            date(2025, 12, 28),
            "Sv. Neviniatka, mučeníci vynechaní",
            ["vynechaní", "Neviniatk"],
        )

    def test_svata_rodina_presunuta_na_30_12_rok_2022(self):
        # Poznámka v deň, KAM bola Sv. rodina presunutá (30.12.)
        self.assert_poznamka_iba_v_status_bare(
            date(2022, 12, 30),
            "Sviatok Svätej rodiny presunutý z 31.12.",
            ["presunutý"],
        )

    def test_svata_rodina_presunuta_na_30_12_rok_2022_zdrojovy_den(self):
        # Poznámka v deň, ODKIAĽ bola Sv. rodina presunutá (31.12.)
        self.assert_poznamka_iba_v_status_bare(
            date(2022, 12, 31),
            "Sviatok Svätej rodiny presunutý na 30.12.",
            ["presunutý"],
        )

    # ------------------------------------------------------------------
    # PRESUNY / ANTICIPÁCIE pohyblivého dátumu slávnosti
    # ------------------------------------------------------------------

    def test_zvestovanie_presunute_2024(self):
        self.assert_poznamka_iba_v_status_bare(
            date(2024, 4, 8),
            "Zvestovanie Pána sa presúva z 25.3.",
            ["presunutá z 25", "presunuté z 25"],
        )

    def test_jan_krstitel_presunuty_2022(self):
        self.assert_poznamka_iba_v_status_bare(
            date(2022, 6, 23),
            "Narodenie Jána Krstiteľa sa presúva z 24.6.",
            ["presunutá z 24", "presúva z 24"],
        )

    def test_sv_jozef_presunuty_dopredu_2023(self):
        # 19.3.2023 bola nedeľa -> presun na 20.3.
        self.assert_poznamka_iba_v_status_bare(
            date(2023, 3, 20),
            "Sv. Jozef, ženích sa presúva z 19.3.",
            ["presunutá z 19", "presúva z 19"],
        )

    def test_sv_jozef_anticipovany_dozadu_2035(self):
        # 19.3.2035 padá do Veľkého týždňa -> anticipácia na 17.3.
        self.assert_poznamka_iba_v_status_bare(
            date(2035, 3, 17),
            "Sv. Jozef, ženích sa presúva z 19.3.",
            ["presunutá z 19", "presúva z 19"],
        )

    def test_neposkvrnene_pocatie_presunute_2024(self):
        self.assert_poznamka_iba_v_status_bare(
            date(2024, 12, 9),
            "Nepoškvrnené počatie Panny Márie sa presúva z 8.12.",
            ["presunutá z 8", "presúva z 8"],
        )

    # ------------------------------------------------------------------
    # Všeobecná (parametrizovaná) kontrola cez popis_vynechaneho_slavenia:
    # pre KAŽDÝ deň v rokoch 2022-2056, kde funkcia vráti neprázdnu
    # poznámku, musí byť táto poznámka v status bare a NESMIE byť (ako
    # celý reťazec) súčasťou hlavičky.
    # ------------------------------------------------------------------

    def test_ziadna_poznamka_o_vynechani_nie_je_duplicitne_v_hlavicke(self):
        pocet_najdenych = 0
        for rok in range(2022, 2057):
            for mesiac, den in [(11, 30), (5, 3), (12, 26), (12, 28), (12, 30)]:
                try:
                    datum = date(rok, mesiac, den)
                except ValueError:
                    continue
                poznamka = kinak.popis_vynechaneho_slavenia(datum)
                if not poznamka:
                    continue
                pocet_najdenych += 1
                with self.subTest(rok=rok, datum=datum, poznamka=poznamka):
                    hlavicka = kinak.zostav_text_hlavicky(dnes=datum)
                    status = kinak.zostav_text_status_baru(dnes=datum)
                    self.assertIn(poznamka, status)
                    self.assertNotIn(poznamka, hlavicka)

        # Ak by sa pravidlá v Kinak.py zmenili tak, že sa v rozsahu rokov
        # už nikdy nevyskytne žiadne vynechanie, test by mlčky neoveroval
        # nič - preto trváme na tom, že aspoň niekoľko scenárov musí byť
        # reálne nájdených a otestovaných.
        self.assertGreater(
            pocet_najdenych, 0,
            "V testovanom rozsahu rokov sa neobjavil žiadny scenár "
            "vynechania - test nič neoveril.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
