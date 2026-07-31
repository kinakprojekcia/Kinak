# -*- coding: utf-8 -*-

from datetime import date, timedelta
import importlib.util
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


def datum_prikazaneho_slavenia(rok: int, nazov: str, popis: str) -> date:
    if popis == "pohyblivý":
        return kinak.vypocitaj_datum_pohyblivych_slaveni(rok)[nazov]

    den_text, mesiac_text = popis.split(".")
    return date(rok, int(mesiac_text.strip()), int(den_text.strip()))


class PrikazaneSlaveniaZobrazenieTest(unittest.TestCase):
    ROK = 2026

    OCAKAVANE = {
        "Panny Márie Bohorodičky": ("PMB", "PANNY MÁRIE BOHORODIČKY"),
        "Zjavenie Pána - Traja králi": ("1L", "ZJAVENIE PÁNA - TRAJA KRÁLI"),
        "Nanebovstúpenie Pána": ("NP", "NANEBOVSTÚPENIE PÁNA"),
        "Najsvätejšieho Kristovho Tela a Krvi": ("5TS", "NAJSVÄTEJŠIEHO KRISTOVHO TELA A KRVI"),
        "Sv. Petra a Pavla, apoštolov": ("6L", "SV. PETRA A PAVLA, APOŠTOLOV"),
        "Nanebovzatie Panny Márie": ("8L", "NANEBOVZATIE PANNY MÁRIE"),
        "Všetkých svätých": ("11L", "VŠETKÝCH SVÄTÝCH"),
        "Nepoškvrnené počatie Panny Márie": ("12L", "NEPOŠKVRNENÉ POČATIE PANNY MÁRIE"),
        "Narodenie Pána": ("1VI", "NARODENIE PÁNA"),
    }

    def test_vsetky_prikazane_slavenia_su_pokryte_testom(self):
        nazvy_v_aplikacii = {nazov for nazov, _popis in kinak.SLAVNOSTI_DATA}
        self.assertEqual(set(self.OCAKAVANE), nazvy_v_aplikacii)

    def test_hlavicka_a_status_bar_pre_vsetky_prikazane_slavenia(self):
        for nazov, popis in kinak.SLAVNOSTI_DATA:
            with self.subTest(slavenie=nazov):
                datum = datum_prikazaneho_slavenia(self.ROK, nazov, popis)
                ocakavana_skratka, ocakavany_text_hlavicky = self.OCAKAVANE[nazov]

                hlavicka = kinak.zostav_text_hlavicky("A", datum)
                status = kinak.zostav_text_status_baru(datum)

                self.assertIn("Kinak v", hlavicka)
                self.assertIn("Liturgický rok A", hlavicka)
                self.assertIn(ocakavany_text_hlavicky, hlavicka.upper())
                self.assertIn("(Slávnosť)", hlavicka)
                self.assertNotIn("Vigília:", hlavicka)

                self.assertIn(f"Žalm z {ocakavana_skratka}", status)
                self.assertIn("zajtra ", status)
                self.assertIn("Žaltár v breviári:", status)
                self.assertIn("týždeň", status)

    def test_vigilie_prikazanych_slavnosti_su_len_v_status_bare(self):
        vigilie = {
            date(self.ROK, 1, 6) - timedelta(days=1): "ZJAVENIE PÁNA - TRAJA KRÁLI",
            date(self.ROK, 6, 29) - timedelta(days=1): "SV. PETRA A PAVLA, APOŠTOLOV",
            date(self.ROK, 8, 15) - timedelta(days=1): "NANEBOVZATIE PANNY MÁRIE",
            date(self.ROK, 11, 1) - timedelta(days=1): "VŠETKÝCH SVÄTÝCH",
            date(self.ROK, 12, 8) - timedelta(days=1): "NEPOŠKVRNENÉ POČATIE PANNY MÁRIE",
            date(self.ROK, 12, 25) - timedelta(days=1): "NARODENIE PÁNA",
        }

        for datum, ocakavana_vigilia in vigilie.items():
            with self.subTest(datum=datum):
                hlavicka = kinak.zostav_text_hlavicky("A", datum)
                status = kinak.zostav_text_status_baru(datum)

                self.assertNotIn("Vigília:", hlavicka)
                self.assertIn(f"Vigília: {ocakavana_vigilia}", status)

    def test_neposkvrnene_srdce_pm_vynechanie_je_v_status_bare_nie_v_hlavicke(self):
        # V roku 2030 padne Nepoškvrnené Srdce PM na 29.6. – koliduje so Sv. Petrom a Pavlom
        datum = date(2030, 6, 29)
        hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum), datum)
        status = kinak.zostav_text_status_baru(datum)

        self.assertTrue(kinak.je_neposkvrnene_srdce_pm_prekazane(datum))
        self.assertEqual("Nepoškvrnené Srdce Panny Márie vynechané", kinak.popis_vynechaneho_slavenia(datum))
        self.assertIn("Nepoškvrnené Srdce Panny Márie vynechané", status)
        self.assertNotIn("Nepoškvrnené Srdce Panny Márie vynechané", hlavicka)
        self.assertIn("SV. PETRA A PAVLA, APOŠTOLOV", hlavicka.upper())
        self.assertNotIn("Žalm z 7TS", status)


if __name__ == "__main__":
    unittest.main()
