# -*- coding: utf-8 -*-

from datetime import date, timedelta
import importlib.util
from pathlib import Path
import re
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
if not KINAK_PATH.exists():
    KINAK_PATH = Path(__file__).resolve().parent / "Kinak.py"
if not KINAK_PATH.exists():
    KINAK_PATH = Path(__file__).resolve().parent / "Kinak_1.py"
PIESNE_DIR = KINAK_PATH.parent / "piesne"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


def skratky_zo_status_baru(zaciatocny_rok=2020, koncovy_rok=2040):
    skratky = {}
    for rok in range(zaciatocny_rok, koncovy_rok + 1):
        datum = date(rok, 1, 1)
        while datum.year == rok:
            text = kinak.format_skratky_liturgickej_casti(datum)
            match = re.fullmatch(r"(\S+) zajtra (\S+)", text)
            if not match:
                raise AssertionError(f"Neočakávaný formát skratiek pre {datum}: {text!r}")

            for skratka in match.groups():
                skratky.setdefault(skratka.upper(), datum)

            datum += timedelta(days=1)

    return skratky


class SuboryPreStatusSkratkyTest(unittest.TestCase):
    def test_kazda_skratka_zo_status_baru_ma_subor_piesne(self):
        if not PIESNE_DIR.exists():
            self.skipTest(f"Priečinok s piesňami neexistuje: {PIESNE_DIR} - test preskočený v CI")
        dostupne_subory = {subor.stem.upper() for subor in PIESNE_DIR.glob("*.txt")}
        if not dostupne_subory:
            self.skipTest(f"Priečinok {PIESNE_DIR} je prázdny - test preskočený")
        skratky = skratky_zo_status_baru()
        chybajuce = {
            skratka: priklad
            for skratka, priklad in skratky.items()
            if skratka not in dostupne_subory
        }

        self.assertEqual({}, chybajuce)

    def test_testovany_rozsah_obsahuje_ocakavane_specialne_skratky(self):
        skratky = set(skratky_zo_status_baru())
        ocakavane = {
            "MGR",
            "NAVPM",
            "NJK",
            "NP",
            "NPMAR",
            "PMB",
            "PREM",
            "PSK",
            "STEF",
            "VG",
            "VPLB",
            "VPON",
            "ZOS",
            "ZST",
            "ZV",
        }

        self.assertTrue(ocakavane <= skratky)


if __name__ == "__main__":
    unittest.main()
