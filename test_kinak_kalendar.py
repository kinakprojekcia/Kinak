# -*- coding: utf-8 -*-
"""
test_kinak_kalendar.py — pytest regresný balík pre doménovú (liturgicko-
kalendárovú) logiku appky Kinak.

PREČO TENTO SÚBOR EXISTUJE
--------------------------
Kód v Kinak.py obsahuje desiatky komentárov, ktoré explicitne pomenúvajú
konkrétne roky, v ktorých dochádza ku kolíziám pohyblivých a pevných slávení
(napr. "2016 – 25.3. = Veľký piatok", "2038 padne na 24.6.", "rokoch 2035
a 2046"...). Až doteraz bola správnosť týchto prípadov podložená len
samotnými komentármi a príležitostným ručným prepočítaním – nič ich
nekontrolovalo automaticky. Presne k tomuto type regresie už raz došlo
(pozri git/revíznu históriu k bodu 1.3/2.3: konsolidácia pevných slávení
do jednej tabuľky nechtiac "aktivovala" starý, dovtedy neškodný konflikt
kódu "1VI" s generickým vianočným kódom a Vianoce začali ukazovať
"OKTÁVA PO NARODENÍ PÁNA" namiesto "NARODENIE PÁNA").

Tento súbor tie roky menuje priamo v teste (parametrizované prípady), aby
akákoľvek budúca úprava, ktorá jeden z nich pokazí, spadla hneď pri `pytest`,
namiesto toho, aby ju niekto objavil až o niekoľko rokov neskôr v ostrej
prevádzke.

AKO SPUSTIŤ
-----------
Tento súbor musí ležať v TOM ISTOM priečinku ako Kinak.py (importuje ho
priamo menom). Appka je tkinter aplikácia, takže spúšťacie prostredie
potrebuje mať nainštalovaný `tkinter` (bežná súčasť Python inštalácie na
Windows/macOS; na Linuxi napr. `apt install python3-tk`). Voliteľné
knižnice `requests`/`beautifulsoup4` nie sú na spustenie týchto testov
potrebné – Kinak.py ich absenciu ošetruje sám (pozri `chybaju_kniznice_
pre_stahovanie()`), tieto testy sieť ani sťahovanie vôbec netestujú. Balík obsahuje 146 testov.

    pip install pytest
    pytest test_kinak_kalendar.py -v

POZNÁMKA K TESTOVACEJ STRATÉGII
--------------------------------
Kde je to možné, testy neoverujú len "čo kód práve vracia" (to by pri
prípadnej budúcej regresii len potvrdilo chybu ako 'novú pravdu'), ale
skutočné, v komentároch zdokumentované LITURGICKÉ PRAVIDLO: napr. že
Zvestovanie Pána v roku 2016 pripadá na Veľký piatok (premisa, overená
cez vlastnú, nezávisle overenú funkciu velkonocna_nedela) A ZÁROVEŇ sa
kvôli tomu slávi až 4. apríla (záver, ktorý test overuje). Pri hlavných
pohyblivých sviatkoch (Veľká noc, 1. adventná nedeľa) sú naviac pridané
dátumy nezávisle overené oproti verejne známym kalendárom, aby test
odhalil aj prípadnú chybu v samotnom výpočte Veľkej noci.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

# Kinak.py leží v tom istom priečinku ako tento testovací súbor.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import Kinak as k  # noqa: E402  (import po sys.path úprave je tu zámerný)


# ==========================================================
# 1. VEĽKONOČNÁ NEDE�ĽA – nezávisle overené referenčné dátumy
# ==========================================================
# Dátumy nižšie sú verejne známe, publikované dátumy Veľkej noci (nezávislé
# od tohto kódu) – slúžia ako "kotva" pre celý zvyšok kalendára, keďže takmer
# všetky pohyblivé slávenia sa počítajú od Veľkej noci.
EASTER_REFERENCE = {
    2016: date(2016, 3, 27),
    2019: date(2019, 4, 21),
    2020: date(2020, 4, 12),
    2021: date(2021, 4, 4),
    2022: date(2022, 4, 17),
    2023: date(2023, 4, 9),
    2024: date(2024, 3, 31),
    2025: date(2025, 4, 20),
    2026: date(2026, 4, 5),
}


@pytest.mark.parametrize("rok, ocakavany_datum", sorted(EASTER_REFERENCE.items()))
def test_velkonocna_nedela_referencne_roky(rok, ocakavany_datum):
    assert k.velkonocna_nedela(rok) == ocakavany_datum


def test_velkonocna_nedela_hranicne_roky_nepada():
    """Krajné roky podporovaného rozsahu (1583–9999) nesmú vyhodiť výnimku."""
    assert isinstance(k.velkonocna_nedela(1583), date)
    assert isinstance(k.velkonocna_nedela(9999), date)


def test_velkonocna_nedela_mimo_rozsahu_vyhodi_chybu():
    with pytest.raises(ValueError):
        k.velkonocna_nedela(1582)
    with pytest.raises(ValueError):
        k.velkonocna_nedela(10000)


# ==========================================================
# 2. PRVÁ ADVENTNÁ NEDEĽA
# ==========================================================
@pytest.mark.parametrize(
    "rok, ocakavany_datum",
    [
        (2023, date(2023, 12, 3)),   # 3.12. je nedeľa -> Advent začína priamo 3.12.
        (2024, date(2024, 12, 1)),   # 3.12.2024 je utorok -> najbližšia nedeľa pred = 1.12.
        (2028, date(2028, 12, 3)),   # neskorý začiatok adventu (viď test 34C nižšie)
    ],
)
def test_prva_adventna_nedela(rok, ocakavany_datum):
    assert k.prva_adventna_nedela(rok) == ocakavany_datum


# ==========================================================
# 3. ZVESTOVANIE PÁNA – kolízie s Veľkým týždňom / oktávou / pôstnymi nedeľami
# ==========================================================
# Roky priamo z docstringu datum_zvestovania_pana().
ZVESTOVANIE_PRESUN_PRIPAD_1 = [2016, 2035]   # 25.3. v Sv. týždni/oktáve -> pondelok po Nedeli Božieho milosrdenstva
ZVESTOVANIE_PRESUN_PRIPAD_2 = [2007, 2012, 2057]  # 25.3. = bežná pôstna nedeľa -> 26.3.


@pytest.mark.parametrize("rok", ZVESTOVANIE_PRESUN_PRIPAD_1)
def test_zvestovanie_presun_velky_tyzden_alebo_oktava(rok):
    velka_noc = k.velkonocna_nedela(rok)
    palmova = velka_noc - timedelta(days=7)
    oktava_koniec = velka_noc + timedelta(days=7)  # Nedeľa Božieho milosrdenstva
    marec25 = date(rok, 3, 25)

    # Premisa: 25.3. musí byť niekde od Kvetnej nedele po Nedeľu Božieho
    # milosrdenstva vrátane (inak by tento rok nebol platným príkladom "prípadu 1").
    assert palmova <= marec25 <= oktava_koniec, (
        f"Rok {rok} už nie je príkladom kolízie so Sv. týždňom/oktávou – "
        f"skontroluj, či sa nezmenil výpočet Veľkej noci."
    )

    # Záver: Zvestovanie sa slávi až pondelok po skončení Veľkonočnej oktávy.
    assert k.datum_zvestovania_pana(rok) == oktava_koniec + timedelta(days=1)


@pytest.mark.parametrize("rok", ZVESTOVANIE_PRESUN_PRIPAD_2)
def test_zvestovanie_presun_na_26_marca(rok):
    velka_noc = k.velkonocna_nedela(rok)
    palmova = velka_noc - timedelta(days=7)
    marec25 = date(rok, 3, 25)

    assert marec25.weekday() == 6, f"Rok {rok}: 25.3. už nie je nedeľa."
    assert not (palmova <= marec25 <= velka_noc + timedelta(days=7)), (
        f"Rok {rok}: 25.3. spadá do Sv. týždňa/oktávy – patrí do 'prípadu 1', nie 2."
    )
    assert k.datum_zvestovania_pana(rok) == date(rok, 3, 26)


def test_zvestovanie_bez_kolizie_ostava_25_marca():
    """Rok, kde 25.3. nie je ani nedeľa v Pôste/Advente/Veľkej noci ani vo Sv. týždni/oktáve."""
    rok = 2025
    marec25 = date(rok, 3, 25)
    velka_noc = k.velkonocna_nedela(rok)
    palmova = velka_noc - timedelta(days=7)
    oktava_koniec = velka_noc + timedelta(days=7)
    assert marec25.weekday() != 6  # 2025-03-25 je utorok
    assert not (palmova <= marec25 <= oktava_koniec)
    assert k.datum_zvestovania_pana(rok) == marec25


# ==========================================================
# 4. SV. JOZEF, ŽENÍCH – anticipácia / presun / bez kolízie
# ==========================================================
def test_sv_jozef_anticipovany_pred_kvetnu_nedelu():
    """
    Rok 2008: Veľká noc 23.3., Kvetná nedeľa 16.3. -> 19.3. spadá do Sv.
    týždňa (Notitiae 2006: anticipuje sa na sobotu pred Kvetnou nedeľou,
    t. j. 15.3., NIE presúva ako Zvestovanie).
    """
    rok = 2008
    velka_noc = k.velkonocna_nedela(rok)
    palmova = velka_noc - timedelta(days=7)
    marec19 = date(rok, 3, 19)

    assert palmova <= marec19 < velka_noc, (
        f"Rok {rok} už nie je príkladom kolízie sv. Jozefa so Sv. týždňom."
    )
    assert k.datum_sv_jozefa_zenicha(rok) == palmova - timedelta(days=1)


def test_sv_jozef_presunuty_z_nedele_2023():
    """
    Rok 2023: 19.3. bola nedeľa (4. pôstna, Laetare), mimo Sv. týždňa
    -> reálne sa slávnosť sv. Jozefa slávila v pondelok 20.3.2023.
    """
    rok = 2023
    marec19 = date(rok, 3, 19)
    velka_noc = k.velkonocna_nedela(rok)
    palmova = velka_noc - timedelta(days=7)

    assert marec19.weekday() == 6
    assert not (palmova <= marec19 < velka_noc)
    assert k.datum_sv_jozefa_zenicha(rok) == date(rok, 3, 20)


def test_sv_jozef_bez_kolizie():
    rok = 2024
    marec19 = date(rok, 3, 19)
    assert marec19.weekday() != 6  # utorok
    assert k.datum_sv_jozefa_zenicha(rok) == marec19


# ==========================================================
# 5. NANEBOVSTÚPENIE PÁNA vs. SV. FILIP A JAKUB (3.5.) – roky 2035, 2046
# ==========================================================
@pytest.mark.parametrize("rok", [2035, 2046])
def test_nanebovstupenie_ma_prednost_pred_filipom_jakubom(rok):
    velka_noc = k.velkonocna_nedela(rok)
    nanebovstupenie = velka_noc + timedelta(days=39)
    maj3 = date(rok, 5, 3)

    assert nanebovstupenie == maj3, (
        f"Rok {rok} už nie je príkladom kolízie Nanebovstúpenia s 3.5. – "
        f"skontroluj výpočet Veľkej noci."
    )
    # Nanebovstúpenie musí vyhrať nad Sv. Filipom a Jakubom rovnakého dňa.
    assert k.vypocitaj_kod_liturgickej_casti(maj3) == "NP"


def test_filip_jakub_bez_kolizie():
    """V bežnom roku (bez kolízie s Nanebovstúpením) musí 3.5. patriť FJ,
    pokiaľ nejde o nedeľu vo Veľkonočnom období (vtedy sa úplne vynecháva)."""
    rok = 2024
    maj3 = date(rok, 5, 3)
    velka_noc = k.velkonocna_nedela(rok)
    assert velka_noc + timedelta(days=39) != maj3
    if maj3.weekday() == 6 and k.je_privilegovana_nedela(maj3):
        pytest.skip(f"3.5.{rok} je privilegovaná nedeľa – FJ sa vynecháva, iný test-case.")
    assert k.vypocitaj_kod_liturgickej_casti(maj3) == "FJ"


# ==========================================================
# 6. NAJSVÄTEJŠIE KRISTOVO TELO A KRV vs. NARODENIE SV. JÁNA KRSTITEĽA – rok 2038
# ==========================================================
def test_najsvatejsie_telo_a_krv_ma_prednost_pred_narodenim_jana_2038():
    rok = 2038
    velka_noc = k.velkonocna_nedela(rok)
    corpus_christi = velka_noc + timedelta(days=60)
    jun24 = date(rok, 6, 24)

    assert corpus_christi == jun24, (
        f"Rok {rok} už nie je príkladom kolízie Najsv. Tela a Krvi s 24.6."
    )
    assert k.vypocitaj_kod_liturgickej_casti(jun24) == "5TS"
    # Narodenie sv. Jána Krstiteľa sa preto MUSÍ posunúť na 23.6.
    assert k.datum_narodenia_jana_krstitela(rok) == date(rok, 6, 23)
    assert k.vypocitaj_kod_liturgickej_casti(date(rok, 6, 23)) == "NJK"


def test_narodenie_jana_krstitela_bez_kolizie_ostava_24_juna():
    rok = 2024
    assert k.datum_narodenia_jana_krstitela(rok) == date(rok, 6, 24)


# ==========================================================
# 7. NEPOŠKVRNENÉ SRDCE PANNY MÁRIE – kolízia s pevnými sviatkami (2.–3.7.)
#    v rokoch 2011, 2038, 2095 (extrémne neskorá Veľká noc, 24.–25.4.)
# ==========================================================
@pytest.mark.parametrize("rok", [2011, 2038, 2095])
def test_nspm_prekazane_v_rokoch_s_neskorou_velkou_nocou(rok):
    velka_noc = k.velkonocna_nedela(rok)
    nspm_datum = velka_noc + timedelta(days=69)  # Turíce (+49) + 20

    # Premisa: ide o extrémne neskorú Veľkú noc (24. alebo 25.4.), pri ktorej
    # NSPM vyjde na 2.–3. júla a kolíduje s NAVPM/Sv. Tomášom.
    assert velka_noc in (date(rok, 4, 24), date(rok, 4, 25)), (
        f"Rok {rok} už nemá extrémne neskorú Veľkú noc – tento test-case už naň neplatí."
    )
    assert nspm_datum in (date(rok, 7, 2), date(rok, 7, 3))
    assert k.je_neposkvrnene_srdce_pm_prekazane(nspm_datum) is True


def test_nspm_normalne_neprekazane():
    """V bežnom roku (skorá/stredná Veľká noc) NSPM nekoliduje s ničím."""
    rok = 2024
    velka_noc = k.velkonocna_nedela(rok)
    nspm_datum = velka_noc + timedelta(days=69)
    assert k.je_neposkvrnene_srdce_pm_prekazane(nspm_datum) is False


# ==========================================================
# 8. KRST KRISTA PÁNA – keď 6.1. pripadne na nedeľu (rok 2019)
# ==========================================================
def test_krst_krista_pana_ked_zjavenie_padne_na_nedelu_2019():
    """
    Reálne overené oproti farskému oznamu (Krst Krista Pána slávený
    13.1.2019, teda nasledujúcu nedeľu PO 6.1., nie hneď v pondelok).
    """
    rok = 2019
    assert date(rok, 1, 6).weekday() == 6, f"Rok {rok}: 6.1. už nie je nedeľa."
    assert k.krst_krista_pana(rok) == date(rok, 1, 13)


def test_krst_krista_pana_bezna_nedela_po_zjaveni():
    rok = 2024
    assert date(rok, 1, 6).weekday() != 6
    krst = k.krst_krista_pana(rok)
    assert krst.weekday() == 6
    assert date(rok, 1, 6) < krst <= date(rok, 1, 12)


# ==========================================================
# 9. SVÄTÁ RODINA – keď Narodenie Pána (25.12.) pripadne na nedeľu
# ==========================================================
@pytest.mark.parametrize("rok", [2005, 2011, 2016, 2022])
def test_svata_rodina_ked_je_25_december_nedela(rok):
    assert date(rok, 12, 25).weekday() == 6, f"Rok {rok}: 25.12. už nie je nedeľa."
    assert k.datum_svatej_rodiny(rok) == date(rok, 12, 30)
    assert k.vypocitaj_kod_liturgickej_casti(date(rok, 12, 30)) == "SR"
    # A samotné 25.12. musí aj tak zostať Narodenie Pána, nie Svätá rodina.
    assert k.vypocitaj_kod_liturgickej_casti(date(rok, 12, 25)) == "1VI"
    assert k.vypocitaj_aktualnu_liturgicku_cast(date(rok, 12, 25)) == "NARODENIE PÁNA"


def test_svata_rodina_bezna_nedela_v_oktave():
    rok = 2024
    assert date(rok, 12, 25).weekday() != 6
    svata_rodina = k.datum_svatej_rodiny(rok)
    assert date(rok, 12, 26) <= svata_rodina <= date(rok, 12, 31)


# ==========================================================
# 10. NEPOŠKVRNENÉ POČATIE – keď 8.12. pripadne na nedeľu (2019, 2024)
# ==========================================================
@pytest.mark.parametrize("rok", [2019, 2024])
def test_nepoškvrnene_pocatie_presun_z_nedele(rok):
    assert date(rok, 12, 8).weekday() == 6, f"Rok {rok}: 8.12. už nie je nedeľa."
    assert k.datum_neposkvrneneho_pocatia(rok) == date(rok, 12, 9)


def test_nepoškvrnene_pocatie_bez_kolizie():
    rok = 2023
    assert date(rok, 12, 8).weekday() != 6
    assert k.datum_neposkvrneneho_pocatia(rok) == date(rok, 12, 8)


# ==========================================================
# 11. NESKORÝ ZAČIATOK ADVENTU – december pred Adventom patrí do 34C
#     (roky 2023, 2028, 2034 – Advent začína až 2.–3. decembra)
# ==========================================================
@pytest.mark.parametrize("rok", [2023, 2028, 2034])
def test_december_pred_adventom_patri_do_34c(rok):
    prva_advent = k.prva_adventna_nedela(rok)
    assert prva_advent >= date(rok, 12, 2), (
        f"Rok {rok} už nezačína Advent neskoro (2.–3.12.) – iný test-case."
    )
    den_pred_adventom = prva_advent - timedelta(days=1)
    assert date(rok, 12, 1) <= den_pred_adventom < prva_advent
    assert k.vypocitaj_kod_liturgickej_casti(den_pred_adventom) == "34C"


# ==========================================================
# 12. LITURGICKÝ ROK (A/B/C) A PARITA (I/II) – všeobecná formula
# ==========================================================
@pytest.mark.parametrize(
    "rok, ocakavany_cyklus",
    [(2022, "A"), (2023, "B"), (2024, "C"), (2025, "A"), (2026, "B")],
)
def test_liturgicky_rok_cyklus(rok, ocakavany_cyklus):
    """
    rok tu = rok_cyklu, teda kalendárny rok, v ktorom ZAČAL Advent (napr.
    "2022" = obdobie od Adventu 2022 do Adventu 2023). Použitý dátum 15.12.
    je zámerne vždy PO 1. adventnej nedeli (tá pripadá najneskôr na 3.12.),
    aby jednoznačne patril do liturgického roka začínajúceho v tomto `rok`u.
    """
    dnes = date(rok, 12, 15)
    assert k.vypocitaj_liturgicky_rok(dnes) == ocakavany_cyklus


def test_parnost_roka_zhoduje_sa_s_parzitou_kalendarneho_roka():
    # 2024 je párny rok -> cyklus II; 2023 nepárny -> cyklus I (mimo Adventu).
    assert k.get_parnost_roka(date(2024, 6, 1)) == 2
    assert k.get_parnost_roka(date(2023, 6, 1)) == 1


# ==========================================================
# 13. REGRESNÝ STRÁŽCA presne pre bod 1.3/2.3 (kolízia kódu "1VI")
# ==========================================================
@pytest.mark.parametrize("rok", [2020, 2021, 2022, 2023, 2024, 2025, 2026, 2030, 2038])
def test_narodenie_pana_nikdy_nevrati_generciky_oktavovy_nazov(rok):
    """
    Presne toto sa pokazilo pri konsolidácii pevných slávení do jednej
    tabuľky (1VI bolo pridané ako tabuľkový záznam a Vianoce začali
    ukazovať generický názov "OKTÁVA PO NARODENÍ PÁNA" namiesto správneho
    "NARODENIE PÁNA", keďže rovnaký kód "1VI" sa používa aj ako spoločný
    kód pre zvyšné dni vianočného obdobia bez vlastného mena).
    """
    vianoce = date(rok, 12, 25)
    assert k.vypocitaj_kod_liturgickej_casti(vianoce) == "1VI"
    assert k.vypocitaj_aktualnu_liturgicku_cast(vianoce) == "NARODENIE PÁNA"


# ==========================================================
# 14. VŠEOBECNÝ "SMOKE TEST" – žiadny deň v širokom rozsahu rokov nesmie
#     spôsobiť výnimku ani prázdny/None výsledok.
# ==========================================================
@pytest.mark.parametrize("rok", range(2015, 2101))
def test_kazdy_den_v_roku_ma_platny_kod_bez_vynimky(rok):
    dnes = date(rok, 1, 1)
    koniec = date(rok, 12, 31)
    while dnes <= koniec:
        kod = k.vypocitaj_kod_liturgickej_casti(dnes)
        assert isinstance(kod, str) and kod, f"{dnes}: prázdny/neplatný kód"
        nazov = k.vypocitaj_aktualnu_liturgicku_cast(dnes)
        assert isinstance(nazov, str) and nazov, f"{dnes}: prázdny/neplatný názov"
        dnes += timedelta(days=1)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
