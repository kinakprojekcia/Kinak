from pathlib import Path
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit testy pre liturgickú logiku z Kinak.py v2.8
Testuje 3 kritické dátumy:
1) 24.6.2038 - kolízia Jána Krstiteľa s Božím Telom
2) 25.3.2027 - Zvestovanie v Zelený štvrtok
3) 19.3.2026 - sv. Jozef bez presunu
"""

import unittest
from datetime import date, timedelta

# === KÓPIA ČISTEJ LOGIKY Z Kinak.py (bez GUI) ===

def prva_adventna_nedela(rok: int) -> date:
    dec3 = date(rok, 12, 3)
    days_back = (dec3.weekday() + 1) % 7
    return dec3 - timedelta(days=days_back)

def velkonocna_nedela(rok: int) -> date:
    a = rok % 19; b = rok // 100; c = rok % 100
    d = b // 4; e = b % 4; f = (b + 8) // 25
    g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30
    i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mesiac = (h + l - 7 * m + 114) // 31
    den = ((h + l - 7 * m + 114) % 31) + 1
    return date(rok, mesiac, den)

def najblizsia_nedela_po_dni(datum: date) -> date:
    dni = (6 - datum.weekday()) % 7
    if dni == 0: dni = 7
    return datum + timedelta(days=dni)

def datum_zvestovania_pana(rok: int) -> date:
    """Kinak.py riadky 124-151"""
    zv = date(rok, 3, 25)
    velka_noc = velkonocna_nedela(rok)
    velky_tyzden_zacatok = velka_noc - timedelta(days=7)
    oktava_koniec = velka_noc + timedelta(days=7)
    if velky_tyzden_zacatok <= zv <= oktava_koniec:
        return oktava_koniec + timedelta(days=1)
    return zv

def vypocitaj_datum_pohyblivych_slaveni(rok: int) -> dict:
    """Kinak.py riadky 153-191"""
    velka_noc = velkonocna_nedela(rok)
    turice = velka_noc + timedelta(days=49)
    return {
        "Najsvätejšieho Kristovho Tela a Krvi": turice + timedelta(days=11),
        "Najsvätejšieho Srdca Ježišovho": turice + timedelta(days=19),
        "Nedeľa Božieho milosrdenstva": velka_noc + timedelta(days=7),
        "Palmová (Kvetná nedeľa)": velka_noc - timedelta(days=7),
        "Veľkonočná nedeľa": velka_noc,
    }

def datum_narodenia_jana_krstitela(rok: int) -> date:
    """Kinak.py riadky 193-203"""
    povodny = date(rok, 6, 24)
    pohyblive = vypocitaj_datum_pohyblivych_slaveni(rok)
    prekazajuce = {
        pohyblive.get("Najsvätejšieho Kristovho Tela a Krvi"),
        pohyblive.get("Najsvätejšieho Srdca Ježišovho"),
    }
    if povodny in prekazajuce:
        return date(rok, 6, 23)
    return povodny

# === TESTY ===

class TestKinakLiturgia(unittest.TestCase):

    def test_1_bozie_telo_2038_koliduje_s_janom(self):
        rok = 2038
        pohyblive = vypocitaj_datum_pohyblivych_slaveni(rok)
        self.assertEqual(pohyblive["Najsvätejšieho Kristovho Tela a Krvi"], date(2038,6,24))
        self.assertEqual(datum_narodenia_jana_krstitela(rok), date(2038,6,23))
        # Hlavička by mala byť: NAJSVÄTEJŠIEHO KRISTOVHO TELA A KRVI

    def test_2_zvestovanie_2027_zeleny_stvrtok(self):
        rok = 2027
        velka_noc = velkonocna_nedela(rok)
        self.assertEqual(velka_noc, date(2027,3,28))
        self.assertEqual(date(2027,3,25).weekday(), 3)  # štvrtok
        self.assertEqual(datum_zvestovania_pana(rok), date(2027,4,5))
        # Hlavička by mala byť: ZELENÝ ŠTVRTOK PÁNOVEJ VEČERE

    def test_3_sv_jozef_2026_bez_presunu(self):
        rok = 2026
        kvetna = velkonocna_nedela(rok) - timedelta(days=7)
        self.assertEqual(kvetna, date(2026,3,29))
        self.assertTrue(date(2026,3,19) < kvetna)
        # Hlavička by mala byť: SV. JOZEFA, ŽENÍCHA PANNY MÁRIE

if __name__ == "__main__":
    unittest.main(verbosity=2)