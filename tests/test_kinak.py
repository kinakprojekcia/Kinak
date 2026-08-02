# -*- coding: utf-8 -*-
"""
Regresné testy pre liturgickú (doménovú) logiku Kinak.py.

Prečo tieto testy existujú
---------------------------
Kinak.py obsahuje veľa starostlivo vyriešených okrajových prípadov (kolízie
pohyblivých slávení s pevnými dátumami, presuny sviatkov cez nedeľu/Veľký
týždeň, vynechávanie spomienok...), ktoré sa v komentároch kódu odvolávajú na
konkrétne roky (napr. "v roku 2038 padne Najsvätejšie Kristovo Telo a Krv na
24.6."). Bez automatizovaných testov je jediný spôsob, ako tieto tvrdenia
overiť, ručný prepočet – čo pri budúcej úprave (napr. refaktoring
`vypocitaj_kod_liturgickej_casti`) nikto nerobí systematicky, takže sa
regresia ľahko prehliadne.

Táto sada preto:
1. Zamyká presne tie roky, ktoré sú vymenované priamo v docstringoch kódu,
   ako spustiteľné testovacie prípady.
2. Kde je to možné, porovnáva výstup s NEZÁVISLÝM zdrojom (knižnica
   `dateutil.easter` pre Veľkú noc; skutočný archív lc.kbs.sk pre Krst Krista
   Pána 2019 – pozri komentár pri danom teste) namiesto porovnávania funkcie
   samej so sebou.
3. Obsahuje aj rýchly a pomalý (`@pytest.mark.slow`) exhaustívny test cez
   celý podporovaný rozsah rokov (1583–9999, orezaný na rozumný rozsah pre
   CI), ktorý len overuje, že výpočet nikdy nespadne a že číslovanie
   cezročných týždňov je vnútorne konzistentné.

Spustenie
---------
    pip install pytest python-dateutil
    pytest test_kinak.py                 # rýchle testy (pár sekúnd)
    pytest test_kinak.py -m slow          # aj pomalý exhaustívny test (cca 1 min)
    pytest test_kinak.py -v               # podrobný výpis

Súbor očakáva, že `Kinak.py` je v tom istom priečinku (alebo inde na
PYTHONPATH). Tkinter sa pri importe nespúšťa (modul importuje `tkinter`, ale
GUI sa vytvára až v `if __name__ == "__main__":`), takže testy bežia aj bez
zobrazeného okna / headless v CI.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

import Kinak as k

try:
    from dateutil.easter import easter, EASTER_WESTERN
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


# ==========================================================
# 1) VEĽKONOČNÁ NEDEĽA – nezávislé porovnanie s dateutil
# ==========================================================

@pytest.mark.skipif(not HAS_DATEUTIL, reason="python-dateutil nie je nainštalovaný")
@pytest.mark.parametrize("rok", [
    1583, 1600, 1700, 1800, 1900, 1999, 2000,
    *range(2000, 2101),   # celé 21. storočie, nezávislý zdroj je lacný
    2200, 2500, 3000, 5000, 9999,
])
def test_velkonocna_nedela_zhoda_s_nezavislou_kniznicou(rok):
    """Meeus/Jones/Butcher algoritmus v Kinak.py musí zodpovedať dateutil."""
    ocakavany = easter(rok, EASTER_WESTERN)
    assert k.velkonocna_nedela(rok) == ocakavany


@pytest.mark.parametrize("rok,ocakavany", [
    # Ručne overené konkrétne dátumy (nezávisle od dateutil), aby test fungoval
    # aj keď python-dateutil nie je nainštalovaný.
    (2016, date(2016, 3, 27)),
    (2024, date(2024, 3, 31)),
    (2025, date(2025, 4, 20)),
    (2026, date(2026, 4, 5)),
    (2035, date(2035, 3, 25)),  # najskorší možný dátum Veľkej noci
    (2038, date(2038, 4, 25)),  # najneskorší možný dátum Veľkej noci
])
def test_velkonocna_nedela_konkretne_datumy(rok, ocakavany):
    assert k.velkonocna_nedela(rok) == ocakavany


@pytest.mark.parametrize("neplatny_rok", [1582, 1000, 0, -1, 10000])
def test_velkonocna_nedela_odmieta_rok_mimo_gregorianskeho_rozsahu(neplatny_rok):
    with pytest.raises(ValueError):
        k.velkonocna_nedela(neplatny_rok)


def test_velkonocna_nedela_odmieta_nespravny_typ():
    with pytest.raises(TypeError):
        k.velkonocna_nedela("2024")  # type: ignore[arg-type]


# ==========================================================
# 2) ZVESTOVANIE PÁNA – presuny cez Veľký týždeň / oktávu / bežnú nedeľu
# ==========================================================

@pytest.mark.parametrize("rok,ocakavany,popis", [
    # Prípad 1: 25.3. padne do Veľkého týždňa alebo Veľkonočnej oktávy
    #  -> presun na pondelok po Nedeli Božieho milosrdenstva.
    (2016, date(2016, 4, 4), "25.3.2016 = Veľký piatok"),
    (2035, date(2035, 4, 2), "25.3.2035 = Veľkonočná nedeľa (Veľká noc je v tomto "
                              "roku najskôr možná, 25.3.)"),
    # Prípad 2: 25.3. padne na bežnú (nie Kvetnú) adventnú/pôstnu/veľkonočnú
    # nedeľu -> presun na najbližší pondelok (26.3.).
    (2007, date(2007, 3, 26), "25.3.2007 = 5. pôstna nedeľa"),
    (2012, date(2012, 3, 26), "25.3.2012 = 5. pôstna nedeľa"),
    (2057, date(2057, 3, 26), "25.3.2057 = pôstna nedeľa"),
])
def test_zvestovanie_pana_presun(rok, ocakavany, popis):
    assert k.datum_zvestovania_pana(rok) == ocakavany, popis


def test_zvestovanie_pana_bez_kolizie_ostava_25_marca():
    """V rokoch bez kolízie (25.3. nie je nedeľa ani vo Veľkom týždni/oktáve)
    slávnosť ostáva na svojom pôvodnom dátume."""
    # 2023: Veľká noc = 9.4., takže 25.3.2023 je sobota mimo Veľkého týždňa
    # (Kvetná nedeľa 2.4.) aj mimo oktávy.
    assert k.datum_zvestovania_pana(2023) == date(2023, 3, 25)


def test_zvestovanie_pana_sa_nikdy_nepresunie_na_nedelu():
    """Presunutý dátum Zvestovania Pána nesmie nikdy pripadnúť na nedeľu –
    inak by ho znova prebila privilegovaná nedeľa."""
    for rok in range(1583, 2201):
        d = k.datum_zvestovania_pana(rok)
        assert d.weekday() != 6, f"rok {rok}: {d} je nedeľa"


# ==========================================================
# 3) SV. JOZEF, ŽENÍCH – anticipácia pred Kvetnou nedeľou (Notitiae 2006)
# ==========================================================

@pytest.mark.parametrize("rok,ocakavany,popis", [
    # 19.3. padne do Veľkého týždňa (medzi Kvetnou nedeľou vrátane a Veľkou
    # nocou) -> anticipuje sa na sobotu PRED Kvetnou nedeľou (nie na pondelok
    # po oktáve, ako pri Zvestovaní Pána).
    (2008, date(2008, 3, 15), "19.3.2008 = streda Veľkého týždňa (Kvetná 16.3.)"),
    (2062, date(2062, 3, 18), "19.3.2062 = Kvetná nedeľa samotná"),
    # 19.3. padne na bežnú nedeľu (mimo Veľkého týždňa) -> presun na pondelok.
    (2023, date(2023, 3, 20), "19.3.2023 = nedeľa (4. pôstna)"),
])
def test_sv_jozef_zenich_presun(rok, ocakavany, popis):
    assert k.datum_sv_jozefa_zenicha(rok) == ocakavany, popis


def test_sv_jozef_bez_kolizie():
    # 2021: Veľká noc 4.4., Kvetná 28.3. -> 19.3.2021 je piatok mimo Veľkého
    # týždňa a nie je nedeľa.
    assert k.datum_sv_jozefa_zenicha(2021) == date(2021, 3, 19)


# ==========================================================
# 4) NARODENIE SV. JÁNA KRSTITEĽA vs. NAJSV. KRISTOVHO TELA A KRVI (2038)
# ==========================================================

def test_narodenie_jana_krstitela_kolizia_2038():
    """V roku 2038 padne Turíce+11 (Najsv. Kristovo Telo a Krv) na 24.6.,
    rovnaký deň ako Narodenie sv. Jána Krstiteľa. Slávnosť Pána má prednosť,
    Ján Krstiteľ sa anticipuje na 23.6."""
    assert k.velkonocna_nedela(2038) == date(2038, 4, 25)  # najneskoršia Veľká noc
    pohyblive = k.vypocitaj_datum_pohyblivych_slaveni(2038)
    assert pohyblive["Najsvätejšieho Kristovho Tela a Krvi"] == date(2038, 6, 24)

    assert k.datum_narodenia_jana_krstitela(2038) == date(2038, 6, 23)
    # 24.6.2038 musí patriť Božiemu Telu, nie Jánovi Krstiteľovi
    assert k.vypocitaj_kod_liturgickej_casti(date(2038, 6, 24)) == "5TS"
    assert k.vypocitaj_kod_liturgickej_casti(date(2038, 6, 23)) == "NJK"


@pytest.mark.parametrize("rok", [2000, 2010, 2020, 2030, 2050])
def test_narodenie_jana_krstitela_bez_kolizie(rok):
    """Vo väčšine rokov nedochádza ku kolízii a NJK ostáva na 24.6."""
    pohyblive = k.vypocitaj_datum_pohyblivych_slaveni(rok)
    if pohyblive["Najsvätejšieho Kristovho Tela a Krvi"] != date(rok, 6, 24):
        assert k.datum_narodenia_jana_krstitela(rok) == date(rok, 6, 24)


# ==========================================================
# 5) NEPOŠKVRNENÉ SRDCE PANNY MÁRIE – kolízia v rokoch s najneskoršou/
#    druhou najneskoršou Veľkou nocou (2011, 2038, 2095)
# ==========================================================

@pytest.mark.parametrize("rok,ocakavany_datum_nspm,koliduje_s", [
    (2011, date(2011, 7, 2), "Návšteva Preblahoslavenej Panny Márie (2.7.)"),
    (2038, date(2038, 7, 3), "Sv. Tomáš, apoštol (3.7.)"),
    (2095, date(2095, 7, 2), "Návšteva Preblahoslavenej Panny Márie (2.7.)"),
])
def test_neposkvrnene_srdce_pm_prekazane(rok, ocakavany_datum_nspm, koliduje_s):
    pohyblive = k.vypocitaj_datum_pohyblivych_slaveni(rok)
    datum_nspm = pohyblive["Nepoškvrnené Srdce Panny Márie"]
    assert datum_nspm == ocakavany_datum_nspm, (
        f"NSPM v roku {rok} by malo pripadnúť na {ocakavany_datum_nspm}, "
        f"vyšlo {datum_nspm}"
    )
    assert k.je_neposkvrnene_srdce_pm_prekazane(datum_nspm) is True, (
        f"NSPM {rok} malo byť prekázané kolíziou s: {koliduje_s}"
    )
    # V tento deň sa kód liturgickej časti NESMIE vrátiť ako "7TS"
    assert k.vypocitaj_kod_liturgickej_casti(datum_nspm) != "7TS"


def test_neposkvrnene_srdce_pm_bez_kolizie_v_normalnom_roku():
    # 2024: Veľká noc 31.3., Turíce 19.5., NSPM = Turíce+20 = 8.6. - žiadna kolízia
    pohyblive = k.vypocitaj_datum_pohyblivych_slaveni(2024)
    datum_nspm = pohyblive["Nepoškvrnené Srdce Panny Márie"]
    assert k.je_neposkvrnene_srdce_pm_prekazane(datum_nspm) is False
    assert k.vypocitaj_kod_liturgickej_casti(datum_nspm) == "7TS"


# ==========================================================
# 6) NEPOŠKVRNENÉ POČATIE PANNY MÁRIE – presun z nedele na 9.12.
# ==========================================================

@pytest.mark.parametrize("rok", [2019, 2024])
def test_nepoškvrnene_pocatie_presun_z_nedele(rok):
    """8.12.2019 a 8.12.2024 sú nedele -> slávnosť sa slávi 9.12.
    (Overené aj priamo voči lc.kbs.sk archívu, viď code review.)"""
    assert date(rok, 12, 8).weekday() == 6
    assert k.datum_neposkvrneneho_pocatia(rok) == date(rok, 12, 9)


def test_nepoškvrnene_pocatie_bez_presunu():
    # 2023: 8.12. je piatok
    assert date(2023, 12, 8).weekday() != 6
    assert k.datum_neposkvrneneho_pocatia(2023) == date(2023, 12, 8)


# ==========================================================
# 7) OBETOVANIE PÁNA (Candlemas) v nedeľu – prednosť pred bežnou nedeľou
#    (regresný test pre opravu mŕtveho kódu "OP", pozri code review)
# ==========================================================

@pytest.mark.parametrize("rok", [2020, 2025, 2031, 2042, 2048, 2053, 2059])
def test_obetovanie_pana_v_nedelu_ma_prednost(rok):
    """2.2. v týchto rokoch pripadá na nedeľu; Obetovanie Pána (sviatok Pána)
    musí aj tak vyhrať nad bežnou cezročnou nedeľou.

    Toto je zároveň regresný test pre úpravu SVIATKY_PANA_S_PREDNOSTOU_V_NEDELU
    (odstránenie nedosiahnuteľného kódu "OP") – správanie sa nesmie zmeniť,
    keďže o prednosť sa reálne stará vetva `"PÁNA" in nazov_upper`.
    """
    d = date(rok, 2, 2)
    assert d.weekday() == 6
    assert k.vypocitaj_kod_liturgickej_casti(d) == "2L"
    assert k.vypocitaj_aktualnu_liturgicku_cast(d) == "OBETOVANIE PÁNA"


def test_sviatky_pana_s_prednostou_neobsahuje_mrtvy_kod_op():
    """OP nemá vlastný kód (vždy sa rieši ako '2L'), preto by v tejto
    množine nemal byť – jeho prítomnosť by bola mŕtvy/klamlivý kód."""
    assert "OP" not in k.SVIATKY_PANA_S_PREDNOSTOU_V_NEDELU


# ==========================================================
# 8) KRST KRISTA PÁNA – nedeľa po 6. januári, aj keď 6.1. je nedeľa
# ==========================================================

@pytest.mark.parametrize("rok", [2013, 2019, 2030, 2036, 2041, 2047])
def test_krst_krista_pana_ked_je_6_januara_nedela(rok):
    """Keď je 6.1. (Zjavenie Pána) samo nedeľou, Krst Krista Pána sa v
    slovenskom kalendári slávi AŽ nasledujúcu nedeľu (13.1.), nie v
    pondelok, ako je to v krajinách s presunutým Zjavením Pána.

    Nezávisle overené pre rok 2019 priamo voči archívu lc.kbs.sk
    (https://lc.kbs.sk/?mesiac=201901&form=rows): 7.1.2019 je vedený ako
    "Pondelok po Zjavení Pána", zatiaľ čo 13.1.2019 je "Krst Krista Pána".
    """
    assert date(rok, 1, 6).weekday() == 6
    ocakavany = date(rok, 1, 13)
    assert k.krst_krista_pana(rok) == ocakavany
    assert k.vypocitaj_kod_liturgickej_casti(ocakavany) == "KKP"
    # Deň po Zjavení Pána (pondelok) MUSÍ patriť ešte vianočnému obdobiu,
    # nie byť omylom označený ako Krst Pána.
    assert k.vypocitaj_kod_liturgickej_casti(date(rok, 1, 7)) == "2VI"


def test_krst_krista_pana_v_beznom_roku():
    # 2024: 6.1. je sobota -> Krst Pána je nasledujúca nedeľa 7.1.2024
    assert date(2024, 1, 6).weekday() == 5
    assert k.krst_krista_pana(2024) == date(2024, 1, 7)


# ==========================================================
# 9) VIANOČNÁ OKTÁVA – vynechávanie sv. Štefana/Jána/Neviniatok,
#    Svätá rodina na 30.12.
# ==========================================================

@pytest.mark.parametrize("rok", [2004, 2010, 2021, 2027, 2032, 2038, 2049, 2055])
def test_sv_stefan_prekazany_na_nedelu(rok):
    """26.12. v týchto rokoch je nedeľa -> Svätá rodina má prednosť,
    Sv. Štefan sa vynecháva (nepresúva)."""
    d = date(rok, 12, 26)
    assert d.weekday() == 6
    assert k.je_sv_stefan_prekazany(d) is True
    assert k.datum_svatej_rodiny(rok) == d


@pytest.mark.parametrize("rok", [2005, 2011, 2016, 2022, 2033, 2039, 2044, 2050])
def test_svata_rodina_na_31_12_ked_25_12_je_nedela(rok):
    """Keď Narodenie Pána (25.12.) pripadne na nedeľu, niet v Oktáve žiadnej
    ďalšej nedele pre Svätú rodinu -> výnimočne sa slávi 30.12."""
    assert date(rok, 12, 25).weekday() == 6
    assert k.datum_svatej_rodiny(rok) == date(rok, 12, 30)
    assert k.je_svata_rodina_presunuta_na_pdr(date(rok, 12, 30)) is True
    assert k.vypocitaj_kod_liturgickej_casti(date(rok, 12, 30)) == "SR"


# ==========================================================
# 10) SV. ONDREJ vynechaný, ak 30.11. = 1. adventná nedeľa
# ==========================================================

@pytest.mark.parametrize("rok", [2003, 2008, 2014, 2025, 2031, 2036, 2042])
def test_sv_ondrej_prekazany_1_adventnou_nedelou(rok):
    d = date(rok, 11, 30)
    assert k.prva_adventna_nedela(rok) == d
    assert k.je_sv_ondrej_prekazany(d) is True
    assert k.vypocitaj_kod_liturgickej_casti(d) == "1AD"


# ==========================================================
# 11) NANEBOVSTÚPENIE PÁNA vs. SV. FILIP A JAKUB (3.5.)
# ==========================================================

@pytest.mark.parametrize("rok", [2035, 2046])
def test_nanebovstupenie_kolizia_s_filipom_jakubom(rok):
    """V týchto rokoch padne Nanebovstúpenie Pána (Veľká noc + 39 dní) na
    3.5., rovnaký deň ako sviatok Sv. Filipa a Jakuba. Slávnosť Pána musí
    vyhrať."""
    vn = k.velkonocna_nedela(rok)
    assert vn + timedelta(days=39) == date(rok, 5, 3)
    assert k.vypocitaj_kod_liturgickej_casti(date(rok, 5, 3)) == "NP"
    assert k.je_sv_filip_jakub_prekazany(date(rok, 5, 3)) is True


# ==========================================================
# 12) ŽALTÁROVÝ TÝŽDEŇ A DVOJROČNÝ CYKLUS – rozumné hodnoty na kotviacich bodoch
# ==========================================================

@pytest.mark.parametrize("rok", [2020, 2024, 2025, 2030])
def test_zaltarovy_tyzden_na_kotviacich_bodoch(rok):
    """Veľká noc a 1. adventná nedeľa musia vždy resetovať žaltár na I. týždeň."""
    assert k.vypocitaj_tyzden_zaltara(k.velkonocna_nedela(rok)) == "I."
    assert k.vypocitaj_tyzden_zaltara(k.prva_adventna_nedela(rok)) == "I."
    # 1. pôstna nedeľa (Veľká noc - 42 dní) tiež resetuje na I. týždeň
    prva_postna = k.velkonocna_nedela(rok) - timedelta(days=42)
    assert k.vypocitaj_tyzden_zaltara(prva_postna) == "I."


def test_zaltarovy_tyzden_vzdy_vracia_platnu_rimsku_cislicu():
    platne = {"I.", "II.", "III.", "IV."}
    d = date(2025, 1, 1)
    for _ in range(400):
        assert k.vypocitaj_tyzden_zaltara(d) in platne
        d += timedelta(days=1)


def test_parnost_roka_je_1_alebo_2():
    d = date(2025, 1, 1)
    for _ in range(400):
        assert k.get_parnost_roka(d) in (1, 2)
        d += timedelta(days=1)


# ==========================================================
# 13) DEFAULT_CONFIG – regresný test pre opravu "zamrznutej" hodnoty
# ==========================================================

def test_default_config_liturgicky_rok_nie_je_zamrznuty_pri_importe():
    """DEFAULT_CONFIG['liturgical_year'] sa už nesmie počítať pri importe
    modulu (bola by 'zamrznutá' na rok platný v čase importu) – pozri
    code review, oprava #3. Autoritatívna hodnota sa vždy počíta za behu
    cez vypocitaj_liturgicky_rok()."""
    assert k.DEFAULT_CONFIG["liturgical_year"] != k.vypocitaj_liturgicky_rok() or \
           k.DEFAULT_CONFIG["liturgical_year"] == ""
    # Explicitne: má to byť "prázdny" placeholder, nie vypočítaná hodnota A/B/C.
    assert k.DEFAULT_CONFIG["liturgical_year"] not in ("A", "B", "C")


def test_vypocitaj_liturgicky_rok_sa_meni_naprieč_adventom():
    """Deň pred 1. adventnou nedeľou a deň po nej musia patriť do odlišných
    liturgických rokov (A/B/C cyklus)."""
    prva_advent_2024 = k.prva_adventna_nedela(2024)
    pred = prva_advent_2024 - timedelta(days=1)
    assert k.vypocitaj_liturgicky_rok(pred) != k.vypocitaj_liturgicky_rok(prva_advent_2024)


# ==========================================================
# 14) EXHAUSTÍVNE TESTY – žiadne výnimky, konzistentné číslovanie týždňov
# ==========================================================

def _over_rok_bez_vynimky_a_konzistentne(rok: int) -> None:
    """Pomocná funkcia: pre všetky dni daného roka over, že výpočet kódu
    liturgickej časti nespadne, a že číslo cezročného týždňa (nC) je v rámci
    jedného liturgického týždňa (nedeľa–sobota) vždy rovnaké."""
    import re
    d = date(rok, 1, 1)
    koniec = date(rok, 12, 31)
    tyzdenne_cisla: dict[date, set[int]] = {}
    while True:
        kod = k.vypocitaj_kod_liturgickej_casti(d)  # nesmie vyhodiť výnimku
        zhoda = re.fullmatch(r"(\d+)C", kod)
        if zhoda:
            zaciatok_tyzdna = k.nedela_zaciatku_tyzdna(d)
            tyzdenne_cisla.setdefault(zaciatok_tyzdna, set()).add(int(zhoda.group(1)))
        if d == koniec:
            break
        d += timedelta(days=1)

    for zaciatok, cisla in tyzdenne_cisla.items():
        assert len(cisla) == 1, (
            f"rok {rok}, týždeň začínajúci {zaciatok}: nekonzistentné čísla "
            f"cezročného týždňa {cisla}"
        )
    if tyzdenne_cisla:
        vsetky = {c for cisla in tyzdenne_cisla.values() for c in cisla}
        assert min(vsetky) >= 1 and max(vsetky) <= 34, (
            f"rok {rok}: číslo cezročného týždňa mimo rozsahu 1–34: {vsetky}"
        )


@pytest.mark.parametrize("rok", [
    1583, 1584, 1600, 1700, 1800, 1900, 1999, 2000, 2001,
    2011, 2016, 2019, 2020, 2024, 2025, 2035, 2038, 2046, 2057, 2095,
    2100, 2200, 2400, 3000, 9999,
])
def test_rok_bez_vynimky_a_konzistentny_rychly(rok):
    """Rýchla verzia: len 'zaujímavé' roky (spomenuté v komentároch kódu +
    hraničné roky gregoriánskeho rozsahu). Beží v CI pri každom spustení."""
    _over_rok_bez_vynimky_a_konzistentne(rok)


@pytest.mark.slow
def test_kazdy_den_1583_az_2200_bez_vynimky_a_konzistentny():
    """Pomalá, exhaustívna verzia cez 618 rokov (cca 226 000 dní).
    Spustiť explicitne cez `pytest -m slow`."""
    for rok in range(1583, 2201):
        _over_rok_bez_vynimky_a_konzistentne(rok)


# ==========================================================
# 15) FORMÁTOVANIE SKRATIEK – rýchla kontrola, že sa nič nezosype na bežných dňoch
# ==========================================================

@pytest.mark.parametrize("rok", [2024, 2025, 2026])
def test_format_skratku_liturgickej_casti_nespadne(rok):
    d = date(rok, 1, 1)
    koniec = date(rok, 12, 31)
    while d <= koniec:
        kod = k.vypocitaj_kod_liturgickej_casti(d)
        skratka = k.format_skratku_liturgickej_casti(kod, d)
        assert isinstance(skratka, str) and skratka != ""
        d += timedelta(days=1)
