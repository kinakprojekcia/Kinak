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
    """Kompatibilná náhrada - používa aktuálne API Kinak 3.0"""
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


class VelkyTyzdenOktavaTest(unittest.TestCase):
    VELKA_NOC = date(2026, 4, 5)
    KVETNA_NEDELA = VELKA_NOC - timedelta(days=7)

    SCENARE = [
        (KVETNA_NEDELA, "VT", "PALMOVÁ (KVETNÁ NEDEĽA)", "Žalm z VT zajtra VT", "182"),
        (KVETNA_NEDELA + timedelta(days=1), "VT", "VEĽKÝ TÝŽDEŇ", "Žalm z VT zajtra VT", "182"),
        (KVETNA_NEDELA + timedelta(days=2), "VT", "VEĽKÝ TÝŽDEŇ", "Žalm z VT zajtra VT", "182"),
        (KVETNA_NEDELA + timedelta(days=3), "VT", "VEĽKÝ TÝŽDEŇ", "Žalm z VT zajtra ZST", "182"),
        (VELKA_NOC - timedelta(days=3), "ZST", "ZELENÝ ŠTVRTOK", "Žalm z ZST zajtra VP", "244, 1"),
        (VELKA_NOC - timedelta(days=2), "VP", "VEĽKÝ PIATOK", "Žalm z VP zajtra VG", "Poklona krížu:"),
        (VELKA_NOC - timedelta(days=1), "VG", "VEĽKONOČNÁ VIGÍLIA", "Žalm z VG zajtra 1VN", "Asperges - 484"),
        (VELKA_NOC, "1VN", "Veľkonočná nedeľa", "Žalm z 1VN zajtra VPON", "210, 1-2"),
        (VELKA_NOC + timedelta(days=1), "VOKT", "PONDELOK VO VEĽKONOČNEJ OKTÁVE", "Žalm z VPON zajtra 1VN", "193, 1"),
        (VELKA_NOC + timedelta(days=2), "VOKT", "3. deň Veľkonočnej oktávy", "Žalm z 1VN zajtra 1VN", "210, 1-2"),
        (VELKA_NOC + timedelta(days=3), "VOKT", "4. deň Veľkonočnej oktávy", "Žalm z 1VN zajtra 1VN", "210, 1-2"),
        (VELKA_NOC + timedelta(days=4), "VOKT", "5. deň Veľkonočnej oktávy", "Žalm z 1VN zajtra 1VN", "210, 1-2"),
        (VELKA_NOC + timedelta(days=5), "VOKT", "6. deň Veľkonočnej oktávy", "Žalm z 1VN zajtra 1VN", "210, 1-2"),
        (VELKA_NOC + timedelta(days=6), "VOKT", "7. deň Veľkonočnej oktávy", "Žalm z 1VN zajtra 2VN", "210, 1-2"),
        (VELKA_NOC + timedelta(days=7), "2VN", "NEDEĽA BOŽIEHO MILOSRDENSTVA", "Žalm z 2VN zajtra 2VN", "194, 1-2"),
    ]

    def test_velky_tyzden_a_velkonocna_oktava_den_po_dni(self):
        for datum, kod, text_hlavicky, text_statusu, uvod in self.SCENARE:
            with self.subTest(datum=datum):
                hlavicka = kinak.zostav_text_hlavicky("A", datum)
                status = kinak.zostav_text_status_baru(datum)
                odporucania = _ziskaj_jks_odporucania_dnes(datum)

                self.assertEqual(kod, kinak.vypocitaj_kod_liturgickej_casti(datum))
                self.assertIn(text_hlavicky, hlavicka)
                self.assertIn(text_statusu, status)
                self.assertIn("Žaltár v breviári:", status)
                self.assertIsNotNone(odporucania)
                self.assertEqual(uvod, odporucania.get("Úvod"))

    def test_velky_piatok_neobsahuje_vigiliu_velkonocnej_vigilie(self):
        velky_piatok = self.VELKA_NOC - timedelta(days=2)
        status = kinak.zostav_text_status_baru(velky_piatok)

        self.assertIn("Žalm z VP zajtra VG", status)
        self.assertNotIn("Vigília: VEĽKONOČNÁ VIGÍLIA", status)


if __name__ == "__main__":
    unittest.main()
