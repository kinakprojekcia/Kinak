# -*- coding: utf-8 -*-

from datetime import date, timedelta
import importlib.util
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
if not KINAK_PATH.exists():
    KINAK_PATH = Path(__file__).resolve().parent / "Kinak.py"
if not KINAK_PATH.exists():
    KINAK_PATH = Path(__file__).resolve().parent / "Kinak_1.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


def _ziskaj_jks_odporucania_dnes(datum):
    """Kompatibilná náhrada za starú funkciu ziskaj_jks_odporucania_dnes - používa aktuálne API Kinak 3.0"""
    kod = kinak.vypocitaj_kod_liturgickej_casti(datum)
    if kod == "PREM":
        return None
    if kod == "VOKT":
        velka_noc = kinak.velkonocna_nedela(datum.year)
        if datum == velka_noc + timedelta(days=1):
            kod_lookup = "VPON"
        else:
            kod_lookup = "1VN"
    else:
        kod_lookup = kod

    liturgicky_den = kinak.DIREKTORIUM_MAP.get(kod_lookup)
    if liturgicky_den is None:
        return None
    for dni in kinak.DIREKTORIUM_DATA.values():
        for den in dni:
            if den.get("den") == liturgicky_den:
                return {
                    "Úvod": den.get("uvodny", ""),
                    "Ofer.": den.get("ofertorium", ""),
                    "Prijím.": den.get("prijimanie", ""),
                    "Kant.": den.get("kant", ""),
                    "Záver": den.get("po_omsi", "")
                }
    return None


class DirektoriumOdporucaniaTest(unittest.TestCase):
    def assert_odporucania(self, datum, ocakavane):
        with self.subTest(datum=datum):
            self.assertEqual(ocakavane, _ziskaj_jks_odporucania_dnes(datum))

    def test_specialne_mapovania_na_vseobecne_direktoriove_zaznamy(self):
        self.assert_odporucania(
            date(2026, 11, 9),
            {
                "Úvod": "257, 1",
                "Ofer.": "257, 5",
                "Prijím.": "270",
                "Kant.": "292, 1-2",
                "Záver": "499",
            },
        )
        self.assert_odporucania(
            date(2026, 7, 2),
            {
                "Úvod": "366, 1",
                "Ofer.": "366, 4",
                "Prijím.": "295",
                "Kant.": "291/525/303",
                "Záver": "344",
            },
        )
        self.assert_odporucania(
            date(2026, 9, 29),
            {
                "Úvod": "444, 1",
                "Ofer.": "444, 2",
                "Prijím.": "273",
                "Kant.": "287, 1-2",
                "Záver": "443",
            },
        )

    def test_datumove_sviatky_s_vlastnym_kodom_nacitania_spravne_odporucania(self):
        self.assert_odporucania(
            date(2026, 6, 24),
            {
                "Úvod": "428, 1-2",
                "Ofer.": "428, 3-4",
                "Prijím.": "283",
                "Kant.": "525",
                "Záver": "449",
            },
        )
        self.assert_odporucania(
            date(2026, 9, 8),
            {
                "Úvod": "404, 1-2",
                "Ofer.": "404",
                "Prijím.": "272",
                "Kant.": "291",
                "Záver": "329",
            },
        )
        self.assert_odporucania(
            date(2026, 9, 14),
            {
                "Úvod": "166, 1-2",
                "Ofer.": "129",
                "Prijím.": "146",
                "Kant.": "160",
                "Záver": "131",
            },
        )
        self.assert_odporucania(
            date(2026, 11, 2),
            {
                "Úvod": "462, 1",
                "Ofer.": "462, 3-4",
                "Prijím.": "280",
                "Kant.": "288",
                "Záver": "464, 1-2",
            },
        )

    def test_premenenie_pana_zamerne_nema_direktoriove_odporucania(self):
        self.assertIsNone(_ziskaj_jks_odporucania_dnes(date(2026, 8, 6)))

    def test_velkonocna_oktava_po_pondelku_pouziva_odporucania_velkonocnej_nedele(self):
        velka_noc = date(2026, 4, 5)
        ocakavane = {
            "Úvod": "210, 1-2",
            "Ofer.": "194",
            "Prijím.": "201",
            "Kant.": "204",
            "Záver": "523/312/195",
        }

        for posun in range(2, 7):
            self.assert_odporucania(velka_noc + timedelta(days=posun), ocakavane)


if __name__ == "__main__":
    unittest.main()
