# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Testy GNLYC 60 pre kritické roky 2011, 2035, 2038, 2046, 2095
Overuje, že refaktor vypocitaj_kod_liturgickej_casti nerozbil precedenciu slávností.

GNLYC 60 (zjednodušene):
  1. Veľkonočné trojdnie
  2. Slávnosti Pána (Vianoce, Zjavenie, Nanebovstúpenie, Turíce, Najsv. Trojica,
     Božie Telo, Najsv. Srdce...)
  3. Nedele adventné, pôstne, veľkonočné
  4. Slávnosti Panny Márie a svätých vo všeobecnom kalendári
  5. Vlastné slávnosti, potom sviatky Pána, potom nedele cezročného obdobia,
     potom sviatky, spomienky...
  Pohyblivá slávnosť Pána > pevná slávnosť svätca
  Nedeľa v Cezročnom období > sviatok apoštola
"""

import sys
import types

# --- Mock GUI závislostí, aby sa Kinak dal importovať bez tkinteru ---
for _name in ['tkinter','tkinter.font','tkinter.ttk','tkinter.messagebox','tkinter.colorchooser','tkinter.filedialog','screeninfo','requests','bs4']:
    if _name not in sys.modules:
        _m = types.ModuleType(_name)
        if _name == 'tkinter':
            _m.Tk = object
            _m.TclError = Exception
        if _name == 'tkinter.font':
            _m.Font = lambda *a, **k: types.SimpleNamespace(configure=lambda *a, **k: None, cget=lambda *a, **k: None)
        if _name == 'screeninfo':
            _m.get_monitors = None
        if _name == 'bs4':
            _m.BeautifulSoup = None
        sys.modules[_name] = _m

from datetime import date, timedelta
from Kinak import (
    velkonocna_nedela,
    datum_zvestovania_pana,
    datum_sv_jozefa_zenicha,
    datum_narodenia_jana_krstitela,
    vypocitaj_datum_pohyblivych_slaveni,
    vypocitaj_kod_liturgickej_casti,
    je_neposkvrnene_srdce_pm_prekazane,
    najdi_pevne_slavenie_s_vlastnym_kodom,
)

def assert_eq(actual, expected, msg):
    if actual != expected:
        raise AssertionError(f"{msg}: očakávané {expected!r}, got {actual!r}")
    print(f"  ✓ {msg} = {actual}")

def run():
    failures = 0
    def test_block(name, fn):
        nonlocal failures
        print(f"\n== {name} ==")
        try:
            fn()
        except AssertionError as e:
            failures += 1
            print(f"  ✗ FAIL: {e}")
        except Exception as e:
            failures += 1
            print(f"  ✗ ERROR: {e}")
            import traceback; traceback.print_exc()

    # ------------------------------------------------------------
    # 2011 – Veľká noc 24.4. (najneskorší možný dátum pred 2038)
    # ------------------------------------------------------------
    def test_2011():
        y = 2011
        vn = velkonocna_nedela(y)
        assert_eq(vn, date(2011,4,24), "Veľká noc 2011")
        # Zvestovanie 25.3. je piatok v pôste, nie vo Svätom týždni/oktáve → ostáva
        assert_eq(datum_zvestovania_pana(y), date(2011,3,25), "Zvestovanie 2011 nepresunuté")
        assert_eq(vypocitaj_kod_liturgickej_casti(date(2011,3,25)), "ZV", "Zvestovanie má prednosť pred pôstnym piatkom")

        # Corpus Christi 23.6., Ján Krstiteľ 24.6. – bez kolízie
        cc = vypocitaj_datum_pohyblivych_slaveni(y)["Najsvätejšieho Kristovho Tela a Krvi"]
        assert_eq(cc, date(2011,6,23), "Božie Telo 2011")
        assert_eq(datum_narodenia_jana_krstitela(y), date(2011,6,24), "Ján Krstiteľ 2011 bez presunu")
        assert_eq(vypocitaj_kod_liturgickej_casti(date(2011,6,23)), "5TS", "Božie Telo > bežný deň")
        assert_eq(vypocitaj_kod_liturgickej_casti(date(2011,6,24)), "NJK", "Ján Krstiteľ 24.6.2011")

        # NSPM 2.7. koliduje s Návštevou PM 2.7. (sviatok) → NSPM vynechané (spomienka < sviatok)
        nspm = vypocitaj_datum_pohyblivych_slaveni(y)["Nepoškvrnené Srdce Panny Márie"]
        assert_eq(nspm, date(2011,7,2), "NSPM 2011 dátum")
        assert_eq(je_neposkvrnene_srdce_pm_prekazane(nspm), True, "NSPM 2011 prekážané")
        assert_eq(vypocitaj_kod_liturgickej_casti(date(2011,7,2)), "NAVPM", "Návšteva PM > NSPM (GNLYC 60)")

        # 3.7.2011 je nedeľa – 14. nedeľa cez rok má prednosť pred Tomášom (sviatok)
        assert_eq(vypocitaj_kod_liturgickej_casti(date(2011,7,3)), "14C", "Nedeľa > sviatok apoštola")

    # ------------------------------------------------------------
    # 2035 – Veľká noc 25.3. (najskorší možný), Zvestovanie aj Jozef v kolízii
    # ------------------------------------------------------------
    def test_2035():
        y = 2035
        vn = velkonocna_nedela(y)
        assert_eq(vn, date(2035,3,25), "Veľká noc 2035 = 25.3.")
        # Zvestovanie 25.3. = Veľkonočná nedeľa → presun na pondelok po oktáve (2.4.)
        assert_eq(date(y,3,25).weekday(), 6, "25.3.2035 je nedeľa")
        assert_eq(datum_zvestovania_pana(y), date(2035,4,2), "Zvestovanie 2035 presun na 2.4.")
        assert_eq(vypocitaj_kod_liturgickej_casti(date(2035,4,2)), "ZV", "Presunuté Zvestovanie slávené 2.4.")

        # Jozef 19.3. padá do Veľkého týždňa (Kvetná nedeľa 18.3.) → anticipácia na sobotu 17.3. (Notitiae 2006)
        assert_eq(datum_sv_jozefa_zenicha(y), date(2035,3,17), "Jozef 2035 anticipovaný na 17.3.")
        assert_eq(vypocitaj_kod_liturgickej_casti(date(2035,3,17)), "3L", "Jozef anticipovaný")

        # Nanebovstúpenie 3.5.2035 koliduje s Filipom a Jakubom (3.5.) → slávnosť Pána > sviatok apoštolov
        naneb = vn + timedelta(days=39)
        assert_eq(naneb, date(2035,5,3), "Nanebovstúpenie 2035 = 3.5.")
        assert_eq(vypocitaj_kod_liturgickej_casti(naneb), "NP", "Nanebovstúpenie > Filip/Jakub (GNLYC 60)")

    # ------------------------------------------------------------
    # 2038 – Veľká noc 25.4. (najneskorší), kaskádové kolízie v júni/júli
    # ------------------------------------------------------------
    def test_2038():
        y = 2038
        vn = velkonocna_nedela(y)
        assert_eq(vn, date(2038,4,25), "Veľká noc 2038 = 25.4. najneskorší")
        # Božie Telo 24.6.2038 → Ján Krstiteľ sa presúva na 23.6. (pohyblivá slávnosť Pána > pevná slávnosť svätca)
        cc = vypocitaj_datum_pohyblivych_slaveni(y)["Najsvätejšieho Kristovho Tela a Krvi"]
        assert_eq(cc, date(2038,6,24), "Božie Telo 2038 = 24.6.")
        assert_eq(datum_narodenia_jana_krstitela(y), date(2038,6,23), "Ján Krstiteľ 2038 presun na 23.6.")
        assert_eq(vypocitaj_kod_liturgickej_casti(date(2038,6,23)), "NJK", "Presunutý Ján 23.6.2038")
        assert_eq(vypocitaj_kod_liturgickej_casti(date(2038,6,24)), "5TS", "Božie Telo 24.6.2038 > Ján")

        # Najsv. Srdce 2.7.2038 → prednosť pred Návštevou 2.7.
        srdce = vypocitaj_datum_pohyblivych_slaveni(y)["Najsvätejšieho Srdca Ježišovho"]
        assert_eq(srdce, date(2038,7,2), "Srdce 2038 = 2.7.")
        assert_eq(vypocitaj_kod_liturgickej_casti(date(2038,7,2)), "6TS", "Srdce Ježišovo > Návšteva (slávnosť Pána > sviatok)")

        # NSPM 3.7.2038 koliduje s Tomášom 3.7. (sviatok) → Tomáš > NSPM (spomienka), NSPM vynechané
        nspm = vypocitaj_datum_pohyblivych_slaveni(y)["Nepoškvrnené Srdce Panny Márie"]
        assert_eq(nspm, date(2038,7,3), "NSPM 2038 = 3.7.")
        assert_eq(je_neposkvrnene_srdce_pm_prekazane(nspm), True, "NSPM 2038 prekážané Tomášom")
        # kód pre Tomáša je v tabuľke ako '7L' s vlastným názvom, ale dôležité je že nie je 7TS
        kod_3_7 = vypocitaj_kod_liturgickej_casti(date(2038,7,3))
        assert_eq(kod_3_7, "7L", "Tomáš 3.7.2038 > NSPM")
        # ochrana pred regresiou kaskády: keby sa Ján nepresunul dynamicky, NSPM by mohlo nesprávne vyjsť ako voľné
        assert_eq(najdi_pevne_slavenie_s_vlastnym_kodom(date(2038,7,3))[0], "7L", "Pevné slávenie 3.7. existuje")

    # ------------------------------------------------------------
    # 2046 – opakovanie 2035 (Veľká noc 25.3.)
    # ------------------------------------------------------------
    def test_2046():
        y = 2046
        assert_eq(velkonocna_nedela(y), date(2046,3,25), "Veľká noc 2046")
        assert_eq(datum_zvestovania_pana(y), date(2046,4,2), "Zvestovanie 2046 presun ako 2035")
        assert_eq(datum_sv_jozefa_zenicha(y), date(2046,3,17), "Jozef 2046 anticipácia")
        assert_eq(vypocitaj_kod_liturgickej_casti(date(2046,5,3)), "NP", "Nanebovstúpenie 2046 > Filip/Jakub")

    # ------------------------------------------------------------
    # 2095 – opakovanie 2011 (Veľká noc 24.4.), overenie stability po 70 rokoch
    # ------------------------------------------------------------
    def test_2095():
        y = 2095
        vn = velkonocna_nedela(y)
        assert_eq(vn, date(2095,4,24), "Veľká noc 2095")
        nspm = vypocitaj_datum_pohyblivych_slaveni(y)["Nepoškvrnené Srdce Panny Márie"]
        assert_eq(nspm, date(2095,7,2), "NSPM 2095 = 2.7.")
        assert_eq(je_neposkvrnene_srdce_pm_prekazane(nspm), True, "NSPM 2095 prekážané")
        assert_eq(vypocitaj_kod_liturgickej_casti(date(2095,7,2)), "NAVPM", "NAVPM > NSPM aj v 2095")

    # Spusti
    test_block("2011 – neskorá Veľká noc, NSPM vs Návšteva", test_2011)
    test_block("2035 – skorá Veľká noc, Zvestovanie + Jozef + Nanebovstúpenie", test_2035)
    test_block("2038 – najneskoršia Veľká noc, Božie Telo vs Ján, Srdce vs Návšteva, NSPM vs Tomáš", test_2038)
    test_block("2046 – skorá Veľká noc (recidíva 2035)", test_2046)
    test_block("2095 – neskorá Veľká noc (recidíva 2011)", test_2095)

    print("\n" + "="*60)
    if failures == 0:
        print("Všetky GNLYC 60 testy prešli ✓")
    else:
        print(f"{failures} test blokov zlyhalo ✗")
    return failures

if __name__ == "__main__":
    import sys
    sys.exit(run())
