# -*- coding: utf-8 -*-

from datetime import date, timedelta
import importlib.util
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


def nazvy_anticipovanych_slavnosti_z_direktoria() -> set[str]:
    return {
        zaznam["den"]
        for zaznamy in kinak.DIREKTORIUM_DATA.values()
        for zaznam in zaznamy
        if zaznam.get("vlastna_omsa_vigilie") is True
        and zaznam["den"] != "Veľkonočná vigília"
    }


class VigilieDirektoriaTest(unittest.TestCase):
    ROK = 2026

    ANTICIPOVANE_SLAVNOSTI = {
        "Nepoškvrnené počatie Panny Márie (8.XII.)": (
            date(ROK, 12, 8),
            "NEPOŠKVRNENÉ POČATIE PANNY MÁRIE",
        ),
        "Narodenie Pána (25.XII.)": (
            date(ROK, 12, 25),
            "NARODENIE PÁNA",
        ),
        "Zjavenie Pána - Traja králi (6.I.)": (
            date(ROK, 1, 6),
            "ZJAVENIE PÁNA - TRAJA KRÁLI",
        ),
        "Nanebovstúpenie Pána": (
            kinak.velkonocna_nedela(ROK) + timedelta(days=39),
            "NANEBOVSTÚPENIE PÁNA",
        ),
        "Nedeľa zoslania Ducha Svätého (Turíce)": (
            kinak.velkonocna_nedela(ROK) + timedelta(days=49),
            "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO (TURÍCE)",
        ),
        "Narodenie sv. Jána Krstiteľa (24.VI.)": (
            date(ROK, 6, 24),
            "NARODENIE SV. JÁNA KRSTITEĽA",
        ),
        "Sv. Petra a Pavla, apoštolov (29.VI.)": (
            date(ROK, 6, 29),
            "SV. PETRA A PAVLA, APOŠTOLOV",
        ),
        "Nanebovzatie Panny Márie (15.VIII.)": (
            date(ROK, 8, 15),
            "NANEBOVZATIE PANNY MÁRIE",
        ),
        "Všetkých svätých (1.XI.)": (
            date(ROK, 11, 1),
            "VŠETKÝCH SVÄTÝCH",
        ),
    }

    def test_test_pokryva_vsetky_anticipovane_slavnosti_z_direktoria(self):
        self.assertEqual(
            set(self.ANTICIPOVANE_SLAVNOSTI),
            nazvy_anticipovanych_slavnosti_z_direktoria(),
        )

    def test_vigilie_vsetkych_anticipovanych_slavnosti_su_len_v_status_bare(self):
        for nazov, (datum_slavnosti, ocakavana_vigilia) in self.ANTICIPOVANE_SLAVNOSTI.items():
            with self.subTest(slavenie=nazov):
                den_predtym = datum_slavnosti - timedelta(days=1)
                hlavicka = kinak.zostav_text_hlavicky("A", den_predtym)
                status = kinak.zostav_text_status_baru(den_predtym)

                self.assertNotIn("Vigília:", hlavicka)
                self.assertIn(f"Vigília: {ocakavana_vigilia}", status)

    def test_vigilia_presunutej_anticipovanej_slavnosti_je_pred_skutocnym_datumom(self):
        den_pred_presunutym_njk = date(2022, 6, 22)
        presunuty_njk = date(2022, 6, 23)
        povodny_njk = date(2022, 6, 24)

        self.assertEqual(kinak.datum_narodenia_jana_krstitela(2022), presunuty_njk)
        self.assertIn(
            "Vigília: NARODENIE SV. JÁNA KRSTITEĽA",
            kinak.zostav_text_status_baru(den_pred_presunutym_njk),
        )
        self.assertNotIn("Vigília:", kinak.zostav_text_hlavicky("C", den_pred_presunutym_njk))

        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(presunuty_njk), "NJK")
        self.assertNotIn(
            "Vigília: NARODENIE SV. JÁNA KRSTITEĽA",
            kinak.zostav_text_status_baru(presunuty_njk),
        )
        self.assertEqual(kinak.vypocitaj_kod_liturgickej_casti(povodny_njk), "6TS")

    def test_velky_piatok_nezobrazuje_vigiliu_velkonocnej_vigilie(self):
        velky_piatok = kinak.velkonocna_nedela(self.ROK) - timedelta(days=2)
        hlavicka = kinak.zostav_text_hlavicky("A", velky_piatok)
        status = kinak.zostav_text_status_baru(velky_piatok)

        self.assertIn("VEĽKÝ PIATOK", hlavicka)
        self.assertIn("Žalm z VP zajtra VG", status)
        self.assertNotIn("Vigília: VEĽKONOČNÁ VIGÍLIA", status)


if __name__ == "__main__":
    unittest.main()
