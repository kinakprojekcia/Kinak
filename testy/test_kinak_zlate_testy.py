# -*- coding: utf-8 -*-
"""
Zlaté (regresné) testy pre liturgické jadro Kinak.py.

Tieto testy NEPOKRÝVAJÚ celý kalendár – zámerne sa sústreďujú na roky,
kde dochádza ku kolíziám pohyblivých/pevných slávností a na hraničné
roky podporovaného rozsahu. Práve tieto miesta sú v praxi najkrehkejšie
(pozri komentáre "VAROVANIE – obmedzený rozsah implementácie" priamo
v Kinak.py) a najľahšie sa nechtiac pokazia pri budúcich úpravách.

Každý test je buď:
  (a) priamo overený voči oficiálnemu zdroju lc.kbs.sk / Vatican News
      (pozri komentáre pri jednotlivých testoch), alebo
  (b) odvodený z pravidiel zdokumentovaných priamo v docstringoch
      príslušných funkcií v Kinak.py.

Spustenie:
    python -m unittest test_kinak_zlate_testy.py -v
alebo (ak je nainštalovaný pytest):
    pytest test_kinak_zlate_testy.py -v
"""
import unittest
from datetime import date

import Kinak as k


class TestZvestovaniePana(unittest.TestCase):
    """datum_zvestovania_pana – pevný dátum 25.3. s pravidlom presunutia."""

    def test_2016_kolizia_s_velkym_tyzdnom(self):
        # 25.3.2016 = Veľký piatok (Veľká noc 2016 = 27.3.). Kolízia s Veľkým
        # týždňom/oktávou sa rieši presunom na pondelok PO oktáve, nie na
        # najbližší pondelok – teda 4.4., nie 28.3.
        self.assertEqual(k.velkonocna_nedela(2016), date(2016, 3, 27))
        self.assertEqual(date(2016, 3, 25).weekday(), 4)  # piatok
        self.assertEqual(k.datum_zvestovania_pana(2016), date(2016, 4, 4))

    def test_2035_kolizia_s_velkonocnou_nedelou(self):
        # 25.3.2035 = Veľká noc samotná. Rovnaká vetva ako 2016 (kolízia
        # s oktávou), len s iným posunom (Veľká noc je o 2 dni "hlbšie"
        # v okne Veľký_týždeň..oktáva než Veľký piatok).
        self.assertEqual(k.velkonocna_nedela(2035), date(2035, 3, 25))
        self.assertEqual(k.datum_zvestovania_pana(2035), date(2035, 4, 2))

    def test_2020_neutralny_rok_bez_kolizie(self):
        # Kontrolný prípad: 25.3.2020 nie je nedeľa ani vo Veľkom týždni/oktáve
        # -> Zvestovanie ostáva na svojom mieste, 25.3.
        self.assertEqual(date(2020, 3, 25).weekday(), 2)  # streda
        self.assertEqual(k.datum_zvestovania_pana(2020), date(2020, 3, 25))


class TestSvJozefZenich(unittest.TestCase):
    """datum_sv_jozefa_zenicha – 19.3., anticipuje sa (NIE presúva dopredu!)
    pri kolízii s Veľkým týždňom, na rozdiel od Zvestovania Pána."""

    def test_2008_kolizia_s_velkym_tyzdnom_anticipacia(self):
        # Veľká noc 2008 = 23.3., Kvetná nedeľa = 16.3. 19.3.2008 (streda)
        # padá DO Veľkého týždňa (16.3.-22.3.) -> podľa Notitiae 2006 sa
        # slávnosť ANTICIPUJE na sobotu PRED Kvetnou nedeľou (15.3.), nie
        # presúva dopredu za oktávu ako pri Zvestovaní Pána.
        self.assertEqual(k.velkonocna_nedela(2008), date(2008, 3, 23))
        self.assertEqual(date(2008, 3, 19).weekday(), 2)  # streda
        self.assertEqual(k.datum_sv_jozefa_zenicha(2008), date(2008, 3, 15))

    def test_2020_neutralny_rok_bez_kolizie(self):
        self.assertEqual(k.datum_sv_jozefa_zenicha(2020), date(2020, 3, 19))


class TestNarodenieJanaKrstitela(unittest.TestCase):
    """datum_narodenia_jana_krstitela – 24.6., presúva sa na 23.6. pri
    kolízii s ktoroukoľvek slávnosťou Pána z POHYBLIVE_SLAVNOSTI_PANA."""

    def test_2022_kolizia_s_najsvatejsim_srdcom_jezisovym(self):
        # 24.6.2022 = piatok = Najsvätejšieho Srdca Ježišovho (pohyblivá
        # slávnosť Pána, počíta sa od Veľkej noci) -> Ján Krstiteľ ustupuje
        # na 23.6.
        poh = k.vypocitaj_datum_pohyblivych_slaveni(2022)
        self.assertEqual(poh["Najsvätejšieho Srdca Ježišovho"], date(2022, 6, 24))
        self.assertEqual(k.datum_narodenia_jana_krstitela(2022), date(2022, 6, 23))

    def test_2038_kolizia_s_najsvatejsim_kristovym_telom_a_krvou(self):
        # Iný rok, INÁ kolidujúca slávnosť (Najsvätejšieho Kristovho Tela
        # a Krvi namiesto Najsvätejšieho Srdca Ježišovho) – dôležité overiť
        # obe, keďže funkcia kontroluje kolíziu s CELOU množinou
        # POHYBLIVE_SLAVNOSTI_PANA, nie len s jednou konkrétnou slávnosťou.
        poh = k.vypocitaj_datum_pohyblivych_slaveni(2038)
        self.assertEqual(poh["Najsvätejšieho Kristovho Tela a Krvi"], date(2038, 6, 24))
        self.assertEqual(k.datum_narodenia_jana_krstitela(2038), date(2038, 6, 23))

    def test_2020_neutralny_rok_bez_kolizie(self):
        self.assertEqual(k.datum_narodenia_jana_krstitela(2020), date(2020, 6, 24))


class TestNeposkvrnenePocatie(unittest.TestCase):
    """datum_neposkvrneneho_pocatia – 8.12., presúva sa na 9.12., ak 8.12.
    padne na nedeľu (vtedy je vždy 2. adventná nedeľa, pozri docstring
    priamo vo funkcii)."""

    def test_2019_8_decembra_nedela(self):
        self.assertEqual(date(2019, 12, 8).weekday(), 6)  # nedeľa
        self.assertEqual(k.datum_neposkvrneneho_pocatia(2019), date(2019, 12, 9))

    def test_2024_8_decembra_nedela(self):
        self.assertEqual(date(2024, 12, 8).weekday(), 6)  # nedeľa
        self.assertEqual(k.datum_neposkvrneneho_pocatia(2024), date(2024, 12, 9))

    def test_2020_neutralny_rok_bez_kolizie(self):
        self.assertEqual(k.datum_neposkvrneneho_pocatia(2020), date(2020, 12, 8))


class TestKrstKristaPana(unittest.TestCase):
    """krst_krista_pana – nedeľa PO 6. januári (najblizsia_nedela_po_dni
    vracia nedeľu striktne PO zadanom dni).

    Hraničný prípad: čo ak 6. január sám pripadne na nedeľu? V Kinaku sa
    Zjavenie Pána na Slovensku slávi na PEVNÝ dátum 6.1. (neprenáša sa na
    nedeľu, pozri komentár pri KALENDAR_ZDROJE v Kinak.py), takže vtedy
    Zjavenie "obsadí" túto nedeľu a Krst Pána musí ísť na ĎALŠIU nedeľu
    (13.1.), NIE na pondelok 7.1., ako by sa dalo mylne očakávať podľa
    pravidla pre krajiny s presúvaným Zjavením Pána.

    OVERENÉ voči primárnemu zdroju: lc.kbs.sk/?den=20190113 uvádza priamo
    "Nedeľa 13. január 2019 ... Krst Krista Pána, sviatok" a pápež
    František mal v ten deň (13.1.2019) anjelovú modlitbu práve na sviatok
    Krstu Krista Pána (Vatican News, 13.1.2019). 6.1.2019 bola nedeľa.
    """

    def test_2019_6_januara_nedela_over_lc_kbs_sk(self):
        self.assertEqual(date(2019, 1, 6).weekday(), 6)  # nedeľa
        self.assertEqual(k.krst_krista_pana(2019), date(2019, 1, 13))

    def test_2030_6_januara_nedela(self):
        self.assertEqual(date(2030, 1, 6).weekday(), 6)
        self.assertEqual(k.krst_krista_pana(2030), date(2030, 1, 13))

    def test_2036_6_januara_nedela(self):
        self.assertEqual(date(2036, 1, 6).weekday(), 6)
        self.assertEqual(k.krst_krista_pana(2036), date(2036, 1, 13))

    def test_2041_6_januara_nedela(self):
        self.assertEqual(date(2041, 1, 6).weekday(), 6)
        self.assertEqual(k.krst_krista_pana(2041), date(2041, 1, 13))

    def test_2025_neutralny_rok_bez_kolizie(self):
        # Kontrolný prípad: 6.1.2025 NIE je nedeľa -> Krst Pána je
        # jednoducho najbližšia nasledujúca nedeľa.
        self.assertNotEqual(date(2025, 1, 6).weekday(), 6)
        self.assertEqual(k.krst_krista_pana(2025), date(2025, 1, 12))


class TestHraniceRozsahu(unittest.TestCase):
    """GREGORIANSKY_MIN_ROK/MAX_ROK a s nimi súvisiace okrajové prípady."""

    def test_rok_1583_je_odmietnuty_validaciou(self):
        # Rok 1583 je zámerne MIMO podporovaného rozsahu (GREGORIANSKY_MIN_ROK
        # = 1584), pretože vypocitaj_tyzden_zaltara pre časť roka 1584
        # interne potrebuje predchádzajúci rok (1583) – keby bol 1583 sám
        # podporovaný, jeho vlastný január by potreboval rok 1582 atď.
        # Pozri komentár pri GREGORIANSKY_MIN_ROK v Kinak.py.
        self.assertEqual(k.GREGORIANSKY_MIN_ROK, 1584)
        with self.assertRaises(ValueError):
            k._over_gregoriansky_rok(1583)
        with self.assertRaises(ValueError):
            k.vypocitaj_tyzden_zaltara(date(1583, 6, 15))

    def test_rok_1584_ma_zname_male_okno_vynimiek(self):
        # Zdokumentovaný, akceptovaný zvyškový okrajový prípad: prvých 8 dní
        # januára 1584 (do Krstu Pána vrátane) + 2.2.1584 (Obetovanie Pána,
        # kód nezodpovedajúci vzoru "nC") potrebujú 1. adventnú nedeľu roka
        # 1583, ktorý je mimo rozsahu -> ValueError. Mimo tohto úzkeho okna
        # (9 z 366 dní) rok 1584 funguje bez chyby.
        for den in (1, 2, 3, 4, 5, 6, 7, 8):
            with self.assertRaises(ValueError):
                k.vypocitaj_tyzden_zaltara(date(1584, 1, den))
        with self.assertRaises(ValueError):
            k.vypocitaj_tyzden_zaltara(date(1584, 2, 2))
        # Deň hneď po tomto okne už funguje normálne.
        k.vypocitaj_tyzden_zaltara(date(1584, 2, 3))  # nesmie vyhodiť výnimku

    def test_9999_12_31_date_max_nespadne_na_overflow(self):
        # Regresný test pre OverflowError: date.max + timedelta(days=1) by
        # vyhodilo OverflowError, keďže "zajtrajšok" pre 31.12.9999
        # neexistuje. format_skratky_liturgickej_casti musí tento okrajový
        # prípad ošetriť bez pádu (vynechaním "zajtra" časti).
        vysledok = k.format_skratky_liturgickej_casti(date(9999, 12, 31))
        self.assertIsInstance(vysledok, str)
        self.assertNotIn("zajtra", vysledok)

    def test_9999_12_30_stale_pocita_aj_zajtrajsok(self):
        # Kontrolný prípad tesne pred hranicou: 30.12.9999 ešte MÁ platný
        # "zajtrajšok" (31.12.9999), takže formát obsahuje aj časť "zajtra".
        vysledok = k.format_skratky_liturgickej_casti(date(9999, 12, 30))
        self.assertIn("zajtra", vysledok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
