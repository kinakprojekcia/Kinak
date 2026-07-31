# -*- coding: utf-8 -*-
"""
Test pravidiel vianočného liturgického obdobia pre roky 2022-2050.

Pravidlá overené priamo voči oficiálnym zdrojom:
- https://liturgia.kbs.sk/sekcia/kalendar (Liturgická komisia KBS - všeobecné pravidlá)
- https://lc.kbs.sk (Liturgický kalendár - konkrétne dni)

Použité pravidlá:
1. 25.12. = Narodenie Pána (1VI)
2. 26.12. = Sv. Štefana (STEF), OKREM ak 26.12. pripadne na nedeľu -> Svätej rodiny (SR)
3. 28.12. = Sv. Neviniatok (NEV), OKREM ak 28.12. pripadne na nedeľu -> Svätej rodiny (SR)
   (Svätá rodina má prednosť pred pevným sviatkom Sv. Neviniatok)
4. Sv. rodiny (SR) sa slávi v nedeľu v Oktáve Narodenia Pána (26.-31.12.),
   ak takáto nedeľa neexistuje (t.j. ak 25.12. je nedeľa), slávi sa 30.12.
   Overené: 28. december 2025 (nedeľa) = Nedeľa Svätej Rodiny (farnostbytca.sk),
   31. december 2023 (nedeľa) = Svätej rodiny (oznamy saldub.sk).
5. Ostatné dni v oktáve (27., 29., 30. resp. 31.12., ak nie sú obsadené) = pokračovanie
   Vianočnej oktávy (1VI).
6. 31.12. = Posledný deň roka (PDR), okrem ak je to deň Sv. rodiny.
7. 1.1. = Panny Márie Bohorodičky (PMB).
8. 6.1. = Zjavenie Pána (1L) - na Slovensku VŽDY fixne 6. januára (prikázaný sviatok,
   nepresúva sa na nedeľu). Overené lc.kbs.sk za 2025: pondelok 6.1.2025 = Zjavenie Pána.
9. Krst Krista Pána (KKP) = vždy najbližšia nedeľa po 6. januári.
   Overené lc.kbs.sk aj viacero TK KBS článkov: 2025 -> nedeľa 12. januára.
"""

from datetime import date, timedelta
import importlib.util
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


def vypocitaj_ocakavane_kody(rok_zaciatku_adventu):
    """Vráti slovník {datum: ocakavany_kod} pre vianočné obdobie rokov
    rok_zaciatku_adventu/rok_zaciatku_adventu+1, podľa pravidiel KBS.
    Opravené: 27.12. je SJE (Sv. Jána), nie 1VI."""
    o = {}
    rok = rok_zaciatku_adventu

    narodenie = date(rok, 12, 25)
    o[narodenie] = "1VI"

    # Najprv urči deň Svätej rodiny
    sr_den = None
    for dd in range(26, 32):
        d = date(rok, 12, dd)
        if d.weekday() == 6:  # nedeľa
            sr_den = d
            break
    if sr_den is None:
        sr_den = date(rok, 12, 30)

    # 26.12.
    d26 = date(rok, 12, 26)
    o[d26] = "SR" if d26 == sr_den else "STEF"

    # 27.12. - SJE, pokiaľ nie je SR
    d27 = date(rok, 12, 27)
    o[d27] = "SR" if d27 == sr_den else "SJE"

    # 28.12.
    d28 = date(rok, 12, 28)
    o[d28] = "SR" if d28 == sr_den else "NEV"

    # Zvyšné dni oktávy 29-31
    for dd in range(29, 32):
        dnes = date(rok, 12, dd)
        if dnes == sr_den:
            o[dnes] = "SR"
        elif dnes not in o:
            # 31.12. je PDR ak nie je SR, inak 1VI
            if dd == 31:
                o[dnes] = "PDR"
            else:
                o[dnes] = "1VI"

    # Ak 30.12. ešte nie je obsadený (môže byť SR)
    d30 = date(rok, 12, 30)
    if d30 not in o:
        o[d30] = "SR" if d30 == sr_den else "1VI"

    # 31.12. už riešený, ale ak je SR, prepíš
    d31 = date(rok, 12, 31)
    if d31 == sr_den:
        o[d31] = "SR"
    elif d31 not in o:
        o[d31] = "PDR"

    o[date(rok + 1, 1, 1)] = "PMB"

    zjavenie = date(rok + 1, 1, 6)
    o[zjavenie] = "1L"

    dni_do_nedele = (6 - zjavenie.weekday()) % 7
    if dni_do_nedele == 0:
        dni_do_nedele = 7
    krst = zjavenie + timedelta(days=dni_do_nedele)
    o[krst] = "KKP"

    return o



def pridaj_testovacie_metody(cls):
    """Pridá do triedy samostatnú testovaciu metódu pre každý rok 2022-2050,
    aby bolo možné spúšťať testy jednotlivo (napr. python -m unittest
    test_vianocne_obdobie_2022_2050.VianocneObdobieTest.test_rok_2030)."""
    for rok in range(2022, 2051):
        def test_metoda(self, rok=rok):
            ocakavania = vypocitaj_ocakavane_kody(rok)
            for datum, ocakavany_kod in sorted(ocakavania.items()):
                with self.subTest(rok=rok, datum=datum):
                    skutocny_kod = kinak.vypocitaj_kod_liturgickej_casti(datum)
                    self.assertEqual(
                        ocakavany_kod,
                        skutocny_kod,
                        f"{datum} ({datum.strftime('%A')}): očakávané "
                        f"'{ocakavany_kod}', ale Kinak.py vrátil '{skutocny_kod}'",
                    )

        test_metoda.__name__ = f"test_rok_{rok}"
        test_metoda.__doc__ = f"Vianočné obdobie {rok}/{rok + 1}"
        setattr(cls, test_metoda.__name__, test_metoda)
    return cls


@pridaj_testovacie_metody
class VianocneObdobieTest(unittest.TestCase):
    """Každá testovacia metóda (test_rok_2022 ... test_rok_2050) overuje
    celé vianočné obdobie daného roka (24.12. - cca 12.1. nasl. roka)."""
    pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
