# -*- coding: utf-8 -*-
from __future__ import annotations   # Aby testy bežali aj na Python 3.9

import sys
import os
import re
import json
import tempfile
import shutil
import traceback
import platform
import html
import unicodedata
import time
import threading  # Pre plynulý chod GUI pri sťahovaní
from concurrent.futures import ThreadPoolExecutor
import atexit
import random
import logging
from functools import lru_cache
from logging.handlers import RotatingFileHandler
import socket
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import cast, Callable, Any

# Knižnice tretích strán
try:
    import requests
except ImportError:
    requests = None

try:
    from requests.adapters import HTTPAdapter
except ImportError:
    HTTPAdapter = None  # type: ignore

try:
    from urllib3.util.retry import Retry
except ImportError:
    Retry = None  # type: ignore

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# GUI knižnica
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, colorchooser, filedialog

# ==========================================================
# Bezpečný import screeninfo
# ==========================================================
try:
    from screeninfo import get_monitors
except ImportError:
    get_monitors = None

# ==========================================================
# ZÁKLADNÉ NASTAVENIA
# ==========================================================

KINAK_VERSION = "3.1"

GREGORIANSKY_MIN_ROK = 1583
GREGORIANSKY_MAX_ROK = 9999

def _over_gregoriansky_rok(rok: int) -> None:
    if not isinstance(rok, int):
        raise TypeError(f"rok musí byť int, zadané: {type(rok).__name__}")
    if not GREGORIANSKY_MIN_ROK <= rok <= GREGORIANSKY_MAX_ROK:
        raise ValueError(
            f"Liturgický kalendár je presne vypočítateľný iba pre gregoriánsky kalendár "
            f"v rozsahu {GREGORIANSKY_MIN_ROK}-{GREGORIANSKY_MAX_ROK}. Zadaný rok: {rok}"
        )

def _over_gregoriansky_datum(datum) -> None:
    try:
        rok = datum.year
    except AttributeError:
        raise TypeError(f"očakáva sa datetime.date, zadané: {type(datum).__name__}")
    _over_gregoriansky_rok(rok)

def vypocitaj_liturgicky_rok(dnes: date | None = None) -> str:
    """
    Automaticky určí liturgický rok (A, B alebo C) podľa zadaného alebo dnešného dátumu.

    Nový liturgický rok začína vždy Prvou adventnou nedeľou (nedeľa
    v týždni obsahujúcom 3. december daného roka).

    Logika:
    - Ak sme ešte pred Prvou adventnou nedeľou, liturgický rok
      začal v adventom MINULÉHO kalendárneho roka (rok_cyklu = dnes.year - 1).
    - Ak sme v deň Prvej adventnej nedele alebo po ňom, nový liturgický rok
      práve začal (rok_cyklu = dnes.year).

    Cyklus sa počíta podľa kalendárneho roka, v ktorom Advent začal
    (nie podľa kalendárneho roka samotného dátumu pred Adventom):
        rok % 3 == 0  →  A   (napr. 2022, 2025, 2028 …)
        rok % 3 == 1  →  B   (napr. 2023, 2026, 2029 …)
        rok % 3 == 2  →  C   (napr. 2021, 2024, 2027 …)
    """
    dnes = dnes or date.today()

    # Určíme rok, v ktorom začal aktuálny liturgický Advent
    # Používame globálnu prva_adventna_nedela() – jediná autoritatívna implementácia.
    if dnes >= prva_adventna_nedela(dnes.year):
        rok_cyklu = dnes.year        # Advent tohto roka už začal
    else:
        rok_cyklu = dnes.year - 1   # ešte sme v liturgickom roku začatom vlani

    return ["A", "B", "C"][rok_cyklu % 3]


@lru_cache(maxsize=None)
def prva_adventna_nedela(rok: int) -> date:
    """
    Prvá adventná nedeľa = nedeľa v týždni s 3. decembrom.

    Cachované cez @lru_cache: čistá funkcia jedného celočíselného
    parametra, volaná opakovane pre ten istý rok (napr. z
    vypocitaj_datum_pohyblivych_slaveni aj priamo z GUI).
    """
    _over_gregoriansky_rok(rok)
    dec3 = date(rok, 12, 3)
    days_back = (dec3.weekday() + 1) % 7   # weekday(): Po=0 … Ne=6
    return dec3 - timedelta(days=days_back)


@lru_cache(maxsize=None)
def velkonocna_nedela(rok: int) -> date:
    """
    Vypočíta dátum Veľkonočnej nedele pre gregoriánsky kalendár.
    Pre výpočet sa používa Meeus-Jones-Butcher algoritmus (Anonymous Gregorian).

    Cachované cez @lru_cache: v súbore sa volá opakovane (desiatky krát)
    pre ten istý rok z mnohých ďalších funkcií (presuny sviatkov,
    prednosť, žaltár...), preto sa oplatí výsledok si zapamätať.
    """
    # Validácia rozsahu (algoritmus platí len pre gregoriánsky kalendár, rok
    # 1583-9999) je centralizovaná v _over_gregoriansky_rok, aby nevznikali
    # dve nezávislé miesta s rovnakým pravidlom, ktoré sa môžu časom rozísť.
    _over_gregoriansky_rok(rok)

    a = rok % 19
    b = rok // 100
    c = rok % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mesiac = (h + l - 7 * m + 114) // 31
    den = ((h + l - 7 * m + 114) % 31) + 1
    return date(rok, mesiac, den)


def najblizsia_nedela_po_dni(datum: date) -> date:
    """Vráti najbližšiu nedeľu striktne po zadanom dátume."""
    dni = (6 - datum.weekday()) % 7
    if dni == 0:
        dni = 7
    return datum + timedelta(days=dni)


def nedela_zaciatku_tyzdna(datum: date) -> date:
    """Vráti nedeľu, ktorou sa začína aktuálny liturgický týždeň."""
    return datum - timedelta(days=(datum.weekday() + 1) % 7)


def krst_krista_pana(rok: int) -> date:
    """Krst Krista Pána: nedeľa po Zjavení Pána (6. januári)."""
    _over_gregoriansky_rok(rok)
    return najblizsia_nedela_po_dni(date(rok, 1, 6))


def datum_svatej_rodiny(rok: int) -> date:
    """
    Sviatok Svätej rodiny Ježiša, Márie a Jozefa: nedeľa nasledujúca po
    Narodení Pána (25. XII.), alebo 30. XII., ak Narodenie Pána pripadne
    práve na nedeľu.
    """
    _over_gregoriansky_rok(rok)
    narodenie_pana = date(rok, 12, 25)
    if narodenie_pana.weekday() == 6:
        return date(rok, 12, 30)
    return najblizsia_nedela_po_dni(narodenie_pana)


def datum_zvestovania_pana(rok: int) -> date:
    """
    Zvestovanie Pána: pevný dátum 25. marca, ale s pravidlom presunutia.

    Podľa čl. 5 Všeobecných smerníc o liturgickom roku a o kalendári
    (porov. breviar.kbs.sk/docs/smernice_lrk.htm) majú nedele adventné,
    pôstne a veľkonočné prednosť pred všetkými slávnosťami a sviatkami
    Pána. Slávnosti, ktoré na tieto nedele pripadnú, sa preto presúvajú
    na nasledujúci pondelok — s jedinou výnimkou, ak ide o kolíziu
    s Kvetnou nedeľou alebo Veľkonočnou nedeľou; tá sa rieši osobitne
    cez Veľkonočnú oktávu.

    Rozlišujú sa teda dva prípady presunu:
      1. 25. marca padne na niektorý deň Veľkého týždňa (Kvetná nedeľa
         až Biela sobota) alebo na niektorý deň Veľkonočnej oktávy
         (Veľkonočná nedeľa až Nedeľa Božieho milosrdenstva vrátane)
         → presun na pondelok bezprostredne nasledujúci po Nedeli
         Božieho milosrdenstva (t. j. prvý deň po skončení oktávy).
      2. 25. marca padne na inú (bežnú) adventnú, pôstnu alebo
         veľkonočnú nedeľu, mimo Veľkého týždňa a oktávy
         → presun na najbližší nasledujúci pondelok (26. marca).

    Príklady rokov s presunutím:
        2016 – 25.3. = Veľký piatok        → presun na 4.4. (prípad 1)
        2035 – 25.3. = Kvetná nedeľa       → presun na 2.4. (prípad 1)
        2007 – 25.3. = 5. pôstna nedeľa    → presun na 26.3. (prípad 2)
        2012 – 25.3. = 5. pôstna nedeľa    → presun na 26.3. (prípad 2)
        2057 – 25.3. = pôstna nedeľa       → presun na 26.3. (prípad 2)
    """
    _over_gregoriansky_rok(rok)
    zv = date(rok, 3, 25)
    velka_noc = velkonocna_nedela(rok)

    # Veľký týždeň začína Kvetnou nedeľou (7 dní pred VN)
    velky_tyzden_zacatok = velka_noc - timedelta(days=7)
    # Veľkonočná oktáva končí Nedeľou Božieho milosrdenstva (7 dní po VN)
    oktava_koniec = velka_noc + timedelta(days=7)

    if velky_tyzden_zacatok <= zv <= oktava_koniec:
        # Presun na prvý pondelok po skončení oktávy
        return oktava_koniec + timedelta(days=1)

    if zv.weekday() == 6:
        # Bežná (nie Kvetná) adventná/pôstna/veľkonočná nedeľa
        # má prednosť → slávnosť sa presúva na najbližší pondelok.
        return zv + timedelta(days=1)

    return zv

@lru_cache(maxsize=None)
def vypocitaj_datum_pohyblivych_slaveni(rok: int) -> dict:
    """
    Vypočíta konkrétne dátumy všetkých pohyblivých slávení pre daný rok.
    Vracia slovník: {názov slávenia: date}

    Cachované cez @lru_cache. POZOR: volajúci kód nesmie vrátený slovník
    meniť "in place" (napr. priradením kľúča alebo .update/.pop) — všetky
    volania v tomto súbore ho už dnes len čítajú (.get/.items/`in`), takže
    cachovanie je bezpečné; pri budúcich úpravách zachovaj tento kontrakt,
    prípadne si pred mutáciou spravte plytkú kópiu (dict(...)).
    """
    velka_noc   = velkonocna_nedela(rok)
    turice      = velka_noc + timedelta(days=49)
    prva_advent = prva_adventna_nedela(rok)
    krista_krala = prva_advent - timedelta(days=7)

    # Svätá rodina - jediný zdroj pravdy: datum_svatej_rodiny()
    svata_rodina = datum_svatej_rodiny(rok)

    return {
        "Prvá adventná nedeľa (začína nový liturgický rok)": prva_advent,
        "Svätej rodiny Ježiša, Márie a Jozefa":             svata_rodina,
        "Krst Krista Pána":                                  krst_krista_pana(rok),
        "Zvestovanie Pána*":                                 datum_zvestovania_pana(rok),
        "Popolcová streda":                                  velka_noc - timedelta(days=46),
        "Palmová (Kvetná nedeľa)":                           velka_noc - timedelta(days=7),
        "Veľkonočná nedeľa":                                 velka_noc,
        "Pondelok vo Veľkonočnej oktáve":                    velka_noc + timedelta(days=1),
        "Nedeľa Božieho milosrdenstva":                      velka_noc + timedelta(days=7),
        "Nanebovstúpenie Pána":                              velka_noc + timedelta(days=39),
        "Nedeľa zoslania Ducha Svätého (Turíce)":            turice,
        "Panny Márie, Matky Cirkvi":                         turice + timedelta(days=1),
        "Pána Ježiša Krista, najvyššieho a večného kňaza":   turice + timedelta(days=4),
        "Najsvätejšej Trojice":                              turice + timedelta(days=7),
        "Najsvätejšieho Kristovho Tela a Krvi":              turice + timedelta(days=11),
        "Najsvätejšieho Srdca Ježišovho":                    turice + timedelta(days=19),
        "Nepoškvrnené Srdce Panny Márie":                    turice + timedelta(days=20),
        "Krista Kráľa":                                      krista_krala,
    }

# Pohyblivé "slávnosti Pána" – podľa Všeobecných noriem liturgického roka
# (č. 60) majú prednosť pred pevnou slávnosťou svätca rovnakého stupňa
# tabuľky liturgických dní. Narodenie sv. Jána Krstiteľa (24.6., pevná
# slávnosť svätca) sa preto pri kolízii s ktoroukoľvek z nich vynúteno
# presúva. Zoznam je zámerne širší než matematicky nutné pre 24.6. (v praxi
# ho tam vie zasiahnuť len Najsvätejšie Kristovo Telo a Krv a Najsvätejšie
# Srdce Ježišovo) – ak sa kalendár v budúcnosti rozšíri o ďalšiu pohyblivú
# slávnosť Pána, stačí ju doplniť sem namiesto úpravy logiky nižšie.
POHYBLIVE_SLAVNOSTI_PANA: tuple[str, ...] = (
    "Nanebovstúpenie Pána",
    "Nedeľa zoslania Ducha Svätého (Turíce)",
    "Pána Ježiša Krista, najvyššieho a večného kňaza",
    "Najsvätejšej Trojice",
    "Najsvätejšieho Kristovho Tela a Krvi",
    "Najsvätejšieho Srdca Ježišovho",
)


def datum_narodenia_jana_krstitela(rok: int) -> date:
    """Narodenie sv. Jána Krstiteľa; pri kolízii s pohyblivou slávnosťou Pána sa presúva na 23.6."""
    _over_gregoriansky_rok(rok)
    povodny_datum = date(rok, 6, 24)
    pohyblive = vypocitaj_datum_pohyblivych_slaveni(rok)
    prekazajuce_slavnosti = {pohyblive.get(nazov) for nazov in POHYBLIVE_SLAVNOSTI_PANA}
    if povodny_datum in prekazajuce_slavnosti:
        return date(rok, 6, 23)
    return povodny_datum

def je_neposkvrnene_srdce_pm_prekazane(datum: date) -> bool:
    """NSPM je spomienka; pri kolízii so slávnosťou/sviatkom sa vynechá, nepresúva."""
    pohyblive = vypocitaj_datum_pohyblivych_slaveni(datum.year)
    datum_nspm = pohyblive.get("Nepoškvrnené Srdce Panny Márie")
    if datum != datum_nspm:
        return False

    if datum == datum_narodenia_jana_krstitela(datum.year):
        return True
    if datum == date(datum.year, 6, 29):  # Sv. Petra a Pavla, apoštolov (slávnosť)
        return True

    # Extrémne zriedkavý okrajový prípad: NSPM (Turíce+20) sa počíta zo dňa
    # Veľkej noci, takže keď Veľká noc pripadne na svoj najneskorší možný
    # dátum (25.4.), NSPM vyjde až na 2.–3. júla, kde už koliduje s pevnými
    # sviatkami z PEVNE_SLAVENIA_S_VLASTNYM_KODOM (napr. Návšteva Panny
    # Márie 2.7., Sv. Tomáš apoštol 3.7.). Stalo sa to v roku 2011 a stane sa
    # znova v rokoch 2038 a 2095. Namiesto pridávania ďalších natvrdo
    # napísaných dátumov kontrolujeme priamo voči existujúcej tabuľke, aby
    # akékoľvek jej budúce rozšírenie bolo automaticky pokryté aj tu.
    if najdi_pevne_slavenie_s_vlastnym_kodom(datum) is not None:
        return True

    return False


def je_sv_ondrej_prekazany(datum: date) -> bool:
    """Sv. Ondrej (30.11.) je sviatok; ak pripadne na 1. adventnú nedeľu,
    nedeľa má prednosť a sviatok sa vynechá (nepresúva sa)."""
    if datum != date(datum.year, 11, 30):
        return False
    return prva_adventna_nedela(datum.year) == datum


def je_sv_filip_jakub_prekazany(datum: date) -> bool:
    """Sv. Filip a Jakub (3.5.) je sviatok; ak pripadne na nedeľu vo Veľkonočnom období
    alebo na slávnosť Nanebovstúpenia Pána, v danom roku sa vynechá (nepresúva sa)."""
    if datum.month != 5 or datum.day != 3:
        return False
    # kolízia s privilegovanou nedeľou (všetky veľkonočné nedele)
    if datum.weekday() == 6 and je_privilegovana_nedela(datum):
        return True
    # kolízia s Nanebovstúpením Pána
    pohyblive = vypocitaj_datum_pohyblivych_slaveni(datum.year)
    if pohyblive.get("Nanebovstúpenie Pána") == datum:
        return True
    return False


def _je_pevny_sviatok_v_oktave_prekazany(datum: date, mesiac: int, den: int) -> bool:
    """
    Spoločné pravidlo pre pevné sviatky v Oktáve Narodenia Pána (26.-28.12.):
    ak zadaný dátum pripadne presne na deň {mesiac}.{den}. A ZÁROVEŇ ide o
    nedeľu, má prednosť Svätá rodina a sviatok sa v danom roku vynechá
    (nepresúva sa na iný deň).

    Jedna spoločná implementácia pre je_sv_stefan_prekazany,
    je_sv_jana_prekazany a je_sv_neviniatka_prekazane – ak by sa pravidlo
    v budúcnosti menilo, stačí upraviť len tu.
    """
    if datum != date(datum.year, mesiac, den):
        return False
    return datum.weekday() == 6


def je_sv_stefan_prekazany(datum: date) -> bool:
    """Sv. Štefan, prvý mučeník (26.12.) je sviatok; ak pripadne na nedeľu,
    nedeľa v Oktáve Narodenia Pána (Svätej rodiny) má prednosť a sviatok sa
    v danom roku vynechá (nepresúva sa)."""
    return _je_pevny_sviatok_v_oktave_prekazany(datum, 12, 26)


def je_sv_neviniatka_prekazane(datum: date) -> bool:
    """Sv. Neviniatka, mučeníci (28.12.) je sviatok; ak pripadne na nedeľu,
    nedeľa v Oktáve Narodenia Pána (Svätej rodiny) má prednosť a sviatok sa
    v danom roku vynechá (nepresúva sa)."""
    return _je_pevny_sviatok_v_oktave_prekazany(datum, 12, 28)


def je_sv_jana_prekazany(datum: date) -> bool:
    """Sv. Ján, apoštol a evanjelista (27.12.) je sviatok; ak pripadne na
    nedeľu, nedeľa v Oktáve Narodenia Pána (Svätej rodiny) má prednosť a
    sviatok sa v danom roku vynechá (nepresúva sa)."""
    return _je_pevny_sviatok_v_oktave_prekazany(datum, 12, 27)


def je_svata_rodina_presunuta_na_pdr(datum: date) -> bool:
    """Sv. rodina sa slávi v nedeľu v Oktáve Narodenia Pána (26.-31.12.);
    ak Narodenie Pána pripadne na nedeľu, žiadna taká nedeľa v oktáve
    neexistuje a Sv. rodina sa výnimočne slávi 30.12. namiesto bežného
    Posledného dňa roka v rovnaký deň."""
    if datum != date(datum.year, 12, 30):
        return False
    return date(datum.year, 12, 25).weekday() == 6


def popis_vynechaneho_slavenia(dnes: date | None = None) -> str | None:
    """Vráti poznámku pre slávenie, ktoré je v daný deň liturgicky vynechané."""
    dnes = dnes or date.today()
    if je_neposkvrnene_srdce_pm_prekazane(dnes):
        return "Nepoškvrnené Srdce Panny Márie vynechané"
    if je_sv_ondrej_prekazany(dnes):
        return "Sv. Ondrej, apoštol vynechaný (1. adventná nedeľa má prednosť)"
    if je_sv_filip_jakub_prekazany(dnes):
        return "Sv. Filip a Jakub vynechaný"
    if je_sv_stefan_prekazany(dnes):
        return "Sv. Štefan, prvý mučeník vynechaný (sviatok Svätej rodiny má prednosť)"
    if je_sv_jana_prekazany(dnes):
        return "Sv. Ján, apoštol a evanjelista vynechaný (sviatok Svätej rodiny má prednosť)"
    if je_sv_neviniatka_prekazane(dnes):
        return "Sv. Neviniatka, mučeníci vynechaní (sviatok Svätej rodiny má prednosť)"
    if je_svata_rodina_presunuta_na_pdr(dnes):
        return "Sviatok Svätej rodiny presunutý z 31.12. (Narodenie Pána pripadlo na nedeľu)"
    return None


def datum_sv_jozefa_zenicha(rok: int) -> date:
    """Sv. Jozef, ženích; ak 19.3. prekáža nedeľa alebo Veľký týždeň, presúva sa."""
    povodny_datum = date(rok, 3, 19)
    velka_noc = velkonocna_nedela(rok)
    palmova_nedela = velka_noc - timedelta(days=7)

    if palmova_nedela <= povodny_datum < velka_noc:
        # Notitiae 2006: sv. Jozef sa pri kolízii so Svätým týždňom
        # anticipuje na sobotu pred Kvetnou nedeľou, na rozdiel od Zvestovania.
        return palmova_nedela - timedelta(days=1)

    if povodny_datum.weekday() == 6:
        return povodny_datum + timedelta(days=1)

    return povodny_datum

def datum_neposkvrneneho_pocatia(rok: int) -> date:
    """
    Nepoškvrnené počatie; ak 8.12. padne na nedeľu, presúva sa na 9.12.

    POZOR pred "opravou" na zložitejšiu kontrolu (overenie adventnej nedele +
    kolízie s vyššími slávnosťami) – nie je potrebná, aj keď sa tak na prvý
    pohľad javí:
    1. 8.12. môže byť nedeľou len ako 2. adventná nedeľa – 1. adventná nedeľa
       je vždy v rozsahu 27.11.–3.12., takže 2. adventná nedeľa je vždy
       v rozsahu 4.12.–10.12., do ktorého 8.12. vždy spadá. Iná možnosť
       (napr. cezročná nedeľa) nastať nemôže.
    2. 9.12. nemá v rímskom ani slovenskom kalendári žiadnu vyššie postavenú
       fixnú slávnosť/sviatok, takže "najbližší voľný deň" (GNLYC č. 60) je
       vždy nasledujúci deň.
    Overené aj priamo oproti lc.kbs.sk a kbs.sk/tkkbs.sk pre roky 2019 a 2024
    (oba roky mali 8.12. v nedeľu) – slávnosť sa reálne slávila 9.12.
    """
    povodny_datum = date(rok, 12, 8)
    if povodny_datum.weekday() == 6:
        return povodny_datum + timedelta(days=1)
    return povodny_datum

def format_cislo_piesne_pre_vstup(cislo: str) -> str:
    """Číselné prefixy zobrazí bez núl, varianty ako 001a ponechá celé."""
    cislo = (cislo or "").strip()
    return str(int(cislo)) if cislo.isdigit() else cislo

POHYBLIVE_NAZVY_PRE_HLAVICKU = {
    "Prvá adventná nedeľa (začína nový liturgický rok)": "1. adventná nedeľa",
    "Zvestovanie Pána*": "Zvestovanie Pána",
    "Nedeľa Božieho milosrdenstva": "2. veľkonočná nedeľa (Nedeľa Božieho milosrdenstva)",
    "Najsvätejšej Trojice": "Najsvätejšia Trojica",
    "Krista Kráľa": "34. cezročná nedeľa (Krista Kráľa)",
}

def nazov_pohybliveho_slavenia_pre_datum(datum: date) -> str | None:
    """Vráti presný názov pohyblivého slávenia pre hlavičku, ak pripadá na dátum."""
    pevne_slavenie = najdi_pevne_slavenie_s_vlastnym_kodom(datum)
    if pevne_slavenie and vypocitaj_kod_liturgickej_casti(datum) == pevne_slavenie[0]:
        return None

    presny_datum = najdi_presny_datum_v_direktoriu(datum)
    if presny_datum and vypocitaj_kod_liturgickej_casti(datum) == presny_datum[0]:
        return None

    for nazov, datum_slavenia in vypocitaj_datum_pohyblivych_slaveni(datum.year).items():
        if datum_slavenia == datum:
            return (POHYBLIVE_NAZVY_PRE_HLAVICKU.get(nazov) or nazov).upper()
    return None

PORADOVE_MUZSKE = {
    1: "PRVÝ",
    2: "DRUHÝ",
    3: "TRETÍ",
    4: "ŠTVRTÝ",
    5: "PIATY",
    6: "ŠIESTY",
    7: "SIEDMY",
    8: "ÔSMY",
    9: "DEVIATY",
    10: "DESIATY",
}

PORADOVE_ZENSKE = {
    1: "PRVÁ",
    2: "DRUHÁ",
    3: "TRETIA",
    4: "ŠTVRTÁ",
    5: "PIATA",
    6: "ŠIESTA",
    7: "SIEDMA",
    8: "ÔSMA",
    9: "DEVIATA",
    10: "DESIATA",
}

# Slovenské názvy dní týždňa (weekday() 0=pondelok … 6=nedeľa)
DNI_TYZDNA_SK = {
    0: "pondelok",
    1: "utorok",
    2: "streda",
    3: "štvrtok",
    4: "piatok",
    5: "sobota",
    6: "nedeľa",
}

LITURGICKE_CASTI_PODLA_KODU = {
    # Adventné obdobie
    "1AD": "PRVÝ ADVENTNÝ TÝŽDEŇ",
    "2AD": "DRUHÝ ADVENTNÝ TÝŽDEŇ",
    "3AD": "TRETÍ ADVENTNÝ TÝŽDEŇ",
    "4AD": "ŠTVRTÝ ADVENTNÝ TÝŽDEŇ",

    # Vianočné obdobie
    "1VI": "OKTÁVA PO NARODENÍ PÁNA",
    "2VI": "VIANOČNÉ OBDOBIE",
    "STEF": "SV. ŠTEFANA, PRVÉHO MUČENÍKA",
    "SJE": "SV. JÁNA, APOŠTOLA A EVANJELISTU",
    "NEV": "SV. NEVINIATOK, MUČENÍKOV",
    "SR": "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA",
    "PDR": "POSLEDNÝ DEŇ ROKA",    
    "2VIN": "DRUHÁ NEDEĽA PO NARODENÍ PÁNA",
    "ZP": "ZJAVENIE PÁNA",
    "KKP": "KRST KRISTA PÁNA",
    "PMB": "PANNY MÁRIE BOHORODIČKY",
    "NMJ": "NAJSVÄTEJŠIE MENO JEŽIŠ",

    # Pôstne obdobie
    "PS": "POPOLCOVÁ STREDA A DNI PO NEJ",
    "PPS": "TÝŽDEŇ POPOLCOVEJ STREDY", # Dni 1–3 po Popolcovej strede (štv–sob pred 1. pôstnou nedeľou)
    "1P": "PRVÝ PÔSTNY TÝŽDEŇ",
    "2P": "DRUHÝ PÔSTNY TÝŽDEŇ",
    "3P": "TRETÍ PÔSTNY TÝŽDEŇ",
    "4P": "ŠTVRTÝ PÔSTNY TÝŽDEŇ",
    "5P": "PIATY PÔSTNY TÝŽDEŇ",
    "ZST": "ZELENÝ ŠTVRTOK",
    "VP": "VEĽKÝ PIATOK",
    "VT": "VEĽKÝ TÝŽDEŇ (SVÄTÝ TÝŽDEŇ)",
    
    # Veľkonočné obdobie
    "VG": "VEĽKONOČNÁ VIGÍLIA",
    "1VN": "VEĽKONOČNÁ NEDEĽA",
    "VOKT": "VEĽKONOČNÁ OKTÁVA",
    "VPON": "PONDELOK VO VEĽKONOČNEJ OKTÁVE",
    "2VN": "NEDEĽA BOŽIEHO MILOSRDENSTVA",
    "3VN": "TRETIA VEĽKONOČNÁ NEDEĽA",
    "4VN": "ŠTVRTÁ VEĽKONOČNÁ NEDEĽA",
    "5VN": "PIATA VEĽKONOČNÁ NEDEĽA",
    "6VN": "ŠIESTA VEĽKONOČNÁ NEDEĽA",
    "NP": "NANEBOVSTÚPENIE PÁNA",
    "7VN": "SIEDMA VEĽKONOČNÁ NEDEĽA",

    # Zvestovanie Pána – môže byť v pôstnom období (25.3.) alebo presunuté
    # na pondelok po veľkonočnej oktáve (ak 25.3. padne do VT alebo oktávy)
    "ZV": "ZVESTOVANIE PÁNA",

    # Turíce a sviatky nadväzujúce na Veľkú noc    
    "1TS": "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO (TURÍCE)",
    "2TS": "PANNY MÁRIE, MATKY CIRKVI",
    "3TS": "PÁNA JEŽIŠA KRISTA, NAJVYŠŠIEHO A VEČNÉHO KŇAZA",
    "4TS": "NAJSVÄTEJŠIA TROJICA",
    "5TS": "NAJSVÄTEJŠIEHO KRISTOVHO TELA A KRVI",
    "6TS": "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO",
    "7TS": "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE",

    # Pevné slávenia s vlastným kódom (pred direktóriom, aby nevyhralo xL)
    "FJ": "SV. FILIPA A JAKUBA, APOŠTOLOV",
    "NJK": "NARODENIE SV. JÁNA KRSTITEĽA",
    "NAVPM": "NÁVŠTEVA PREBLAHOSLAVENEJ PANNY MÁRIE",
    "BEN": "SV. BENEDIKTA, OPÁTA, PATRÓNA EURÓPY",
    "BRI": "SV. BRIGITY, REHOĽNÍČKY, PATRÓNKY EURÓPY",
    "VAV": "SV. VAVRINCA, DIAKONA A MUČENÍKA",
    "BAR": "SV. BARTOLOMEJA, APOŠTOLA",    
    "MATE": "SV. MATÚŠA, APOŠTOLA A EVANJELISTU",
    "OND": "SV. ONDREJA, APOŠTOLA",
    "CMV": "SV. CYRILA A METODA",
    "PREM": "PREMENENIE PÁNA",
    "NPMAR": "NARODENIE PANNY MÁRIE",
    "PSK": "POVÝŠENIE SVÄTÉHO KRÍŽA",
    "MGR": "SV. MICHALA, GABRIELA A RAFAELA, ARCHANJELI",
    "ZOS": "SPOMIENKA NA VŠETKÝCH ZOSNULÝCH VERIACICH",
    "VPLB": "VÝROČIE POSVIACKY LATERÁNSKEJ BAZILIKY",
}

RIMSKE_MESIACE = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
    "VIII": 8,
    "IX": 9,
    "X": 10,
    "XI": 11,
    "XII": 12,
}

SVIATKY_PANA_S_PREDNOSTOU_V_NEDELU = {
    "OP",    # Obetovanie Pána
    "PREM",  # Premenenie Pána
    "PSK",   # Povýšenie Svätého kríža
    "VPLB",  # Výročie posviacky Lateránskej baziliky
}

OSOBITNE_DNI_S_PREDNOSTOU_V_NEDELU = {
    "ZOS",   # Spomienka na Všetkých zosnulých veriacich
}

# Správny liturgický stupeň pre kódy, kde sa direktórium nezhoduje
# (napr. direktórium má generický záznam s iným stupňom ako skutočná slávnosť)
STUPEN_OVERRIDE = {
    "MGR":  "Sviatok",   # Sv. Michala, Gabriela a Rafaela – direktórium má "O sv. anjeloch" (Spomienka)
    "NAVPM": "Sviatok",   # Návšteva preblahoslavenej Panny Márie – piesne z direktória sa berú zo všeobecného záznamu "Sviatky Panny Márie"
    "PREM": "Sviatok",   # Premenenie Pána – direktórium nemá záznam
    "SR":   "Sviatok",
    "STEF": "Sviatok",
    "NEV": "Sviatok",
    "BEN":  "Sviatok",
    "BRI":  "Sviatok",
    "VAV":  "Sviatok",
    "BAR":  "Sviatok",
    "FJ":  "Sviatok",
    "MATE":  "Sviatok",
    "OND":  "Sviatok",
    "VPLB": "Sviatok",   # Výročie posviacky Lateránskej baziliky – piesne z direktória sa berú zo všeobecného záznamu "Výročie posviacky chrámu"
    "4L":   "Sviatok",   # Aprílové sviatky svätých mužov majú viac konkrétnych názvov – piesne z direktória sa berú zo všeobecného záznamu "Sviatky svätých mužov"
    "7L":   "Sviatok",   # Júlové sviatky apoštolov majú viac konkrétnych názvov – piesne z direktória sa berú zo všeobecného záznamu "Sviatky apoštolov"
    "10L":  "Sviatok",   # Októbrové sviatky mučeníkov majú viac konkrétnych názvov – piesne z direktória sa berú zo všeobecného záznamu "Sviatky mučeníkov"
}

PEVNE_SLAVENIA_S_VLASTNYM_KODOM = [
    # Tieto pevné dni majú v aplikácii vlastný používateľský názov a kód.
    # Mapa slúži najmä pri hlavičke a upozornení "nedeľa má prednosť pred...",
    # aj keď sa odporúčané piesne môžu brať z všeobecnejšieho direktóriového
    # záznamu. Napr. VPLB zobrazujeme ako konkrétne Výročie posvätenia
    # Lateránskej baziliky, ale piesne sa mapujú cez "Výročie posviacky chrámu".
    #
    # Posledné pole (date_fn) je None pre bežné pevné dátumy (mesiac/deň platí
    # každý rok rovnako). Tri slávnosti (3L, NJK, 12L) sa v niektorých rokoch
    # posúvajú na iný deň (kolízia s nedeľou/Veľkým týždňom) – pre tie je tu
    # namiesto None funkcia date_fn(rok), ktorá vráti skutočný dátum slávenia
    # v danom roku; najdi_pevne_slavenie_s_vlastnym_kodom() ju použije namiesto
    # pevného mesiac/deň.
    (3, 19, "3L", "SV. JOZEFA, ŽENÍCHA", "Slávnosť", datum_sv_jozefa_zenicha),

    (4, 25, "4L", "SV. MARKA, EVANJELISTU", "Sviatok", None),
    (4, 29, "4L", "SV. KATARÍNY SIENSKEJ, PANNY A UČITEĽKY CIRKVI, PATRÓNKY EURÓPY", "Sviatok", None),

    (5, 3, "FJ", "SV. FILIPA A JAKUBA, APOŠTOLOV", "Sviatok", None),

    (6, 24, "NJK", "NARODENIE SV. JÁNA KRSTITEĽA", "Slávnosť", datum_narodenia_jana_krstitela),
    (7, 2, "NAVPM", "NÁVŠTEVA PREBLAHOSLAVENEJ PANNY MÁRIE", "Sviatok", None),
    # CMV bol donedávna vynechaný z tejto tabuľky a ošetrený len samostatným
    # if-om vo vypocitaj_kod_liturgickej_casti – ten if-blok bol odstránený
    # (viď poznámka nad "Narodenie Pána má používať vianočný súbor 1VI..."
    # v tej funkcii), keďže duplikoval presne tento záznam. CMV je odteraz
    # definované JEDINE tu, čo využívajú aj ostatné funkcie na detekciu
    # kolízií (napr. je_neposkvrnene_srdce_pm_prekazane).
    (7, 5, "CMV", "SV. CYRILA A METODA, SLOVANSKÝCH VIEROZVESTOV", "Slávnosť", None),
    (7, 11, "BEN", "SV. BENEDIKTA, OPÁTA, PATRÓNA EURÓPY", "Sviatok", None),
    (7, 23, "BRI", "SV. BRIGITY, REHOĽNÍČKY, PATRÓNKY EURÓPY", "Sviatok", None),
    (8, 6, "PREM", "PREMENENIE PÁNA", "Sviatok", None),
    (8, 10, "VAV", "SV. VAVRINCA, DIAKONA A MUČENÍKA", "Sviatok", None),
    (8, 24, "BAR", "SV. BARTOLOMEJA, APOŠTOLA", "Sviatok", None),

    (7, 3, "7L", "SV. TOMÁŠA, APOŠTOLA", "Sviatok", None),
    (7, 22, "7L", "SV. MÁRIE MAGDALÉNY", "Sviatok", None),
    (7, 25, "7L", "SV. JAKUBA, APOŠTOLA", "Sviatok", None),


    (9, 8, "NPMAR", "NARODENIE PANNY MÁRIE", "Sviatok", None),
    (9, 14, "PSK", "POVÝŠENIE SVÄTÉHO KRÍŽA", "Sviatok", None),
    (9, 21, "MATE", "SV. MATÚŠA, APOŠTOLA A EVANJELISTU", "Sviatok", None),
    (9, 29, "MGR", "SV. MICHALA, GABRIELA A RAFAELA, ARCHANJELI", "Sviatok", None),

    (10, 18, "10L", "SV. LUKÁŠA, EVANJELISTU", "Sviatok", None),
    (10, 28, "10L", "SV. ŠIMONA A JÚDU, APOŠTOLOV", "Sviatok", None),

    (11, 2, "ZOS", "SPOMIENKA NA VŠETKÝCH ZOSNULÝCH VERIACICH", "Spomienka", None),
    (11, 9, "VPLB", "VÝROČIE POSVIACKY LATERÁNSKEJ BAZILIKY", "Sviatok", None),
    (11, 30, "OND", "SV. ONDREJA, APOŠTOLA", "Sviatok", None),
    (12, 8, "12L", "NEPOŠKVRNENÉ POČATIE PANNY MÁRIE", "Slávnosť", datum_neposkvrneneho_pocatia),

    # Novoročné obdobie (26.12.–3.1.). Tieto dni mali predtým samostatné
    # if-bloky vo vypocitaj_kod_liturgickej_casti – rovnaký vzor ako
    # CMV/NAVPM/PREM a pod. vyššie, zjednotené sem z rovnakého dôvodu
    # (jediný zdroj pravdy pre kód/názov/stupeň). Nazov pre "PMB" je zámerne
    # zhodný (case-insenzitívne, bez dátumovej prípony) s príslušným záznamom
    # v direktóriu ("Panny Márie Bohorodičky (1.I.)"), aby ma_vlastnu_omsu_vigilie()
    # správne rozpoznala jeho vigíliu bez ohľadu na to, ktorý zdroj názvu sa
    # práve použije.
    #
    # POZOR – "1VI" (Narodenie Pána, 25.12.) sem ZÁMERNE NEPATRÍ, hoci by inak
    # zapadalo do rovnakého vzoru: kód "1VI" totiž nie je len kódom tohto
    # jedného dňa, ale zároveň aj generickým kódom celého zvyšku vianočného
    # obdobia (26.–31.12., okrem dní vyššie a Svätej rodiny) vracaným
    # o kúsok nižšie vo vypocitaj_kod_liturgickej_casti(). Skúška v tomto
    # module ukázala, že pridanie riadku (12, 25, "1VI", ...) sem spôsobí, že
    # vypocitaj_aktualnu_liturgicku_cast() pre 25.12. omylom vráti generický
    # názov "OKTÁVA PO NARODENÍ PÁNA" (z LITURGICKE_CASTI_PODLA_KODU["1VI"])
    # namiesto správneho "NARODENIE PÁNA" – kód sa zhoduje, ale ide o iný deň.
    # Narodenie Pána preto ostáva ošetrené explicitne (vypocitaj_kod_liturgickej_casti
    # aj vypocitaj_aktualnu_liturgicku_cast nižšie).
    (12, 26, "STEF", "SV. ŠTEFANA, PRVÉHO MUČENÍKA", "Sviatok", None),
    (12, 27, "SJE", "SV. JÁNA, APOŠTOLA A EVANJELISTU", "Sviatok", None),
    (12, 28, "NEV", "SV. NEVINIATOK, MUČENÍKOV", "Sviatok", None),
    (12, 31, "PDR", "POSLEDNÝ DEŇ ROKA", "", None),
    (1, 1, "PMB", "PANNY MÁRIE BOHORODIČKY", "Slávnosť", None),
    (1, 3, "NMJ", "NAJSVÄTEJŠIE MENO JEŽIŠ", "Spomienka", None),
]

# Mapovanie kódov na liturgické dni pre prepojenie s direktóriom
# (aby pritiahlo odporúčané piesne z direktória do popisu)
DIREKTORIUM_MAP = {
    # Adventné obdobie
    "1AD": "1. adventná nedeľa",
    "2AD": "2. adventná nedeľa",
    "3AD": "3. adventná nedeľa",
    "4AD": "4. adventná nedeľa",

    # Vianočné obdobie
    "1VI": "Narodenie Pána (25.XII.)",
    "STEF": "Sv. Štefana, prvého mučeníka (26.XII.)",
    "SJE": "Sviatky apoštolov",
    "NEV": "Sviatky mučeníkov",
    "SR": "Svätej rodiny Ježiša, Márie a Jozefa",
    "PDR": "Posledný deň roka",
    "2VI": "2. vianočná nedeľa",
    "KKP": "Krst Krista Pána",
    "PMB": "Panny Márie Bohorodičky (1.I.)",
    "NMJ": "Najsvätejšie meno Ježiš",

    # Pôstne obdobie
    "PS": "Popolcová streda",
    "1P": "1. pôstna nedeľa",
    "2P": "2. pôstna nedeľa",
    "3P": "3. pôstna nedeľa",
    "4P": "4. pôstna nedeľa",
    "5P": "5. pôstna nedeľa",
    "VT": "Palmová (Kvetná nedeľa)",
    "ZST": "Zelený štvrtok",
    "VP": "Veľký piatok",
    "ZV": "Zvestovanie Pána*",

    # Veľkonočné obdobie
    "VG": "Veľkonočná vigília",
    "1VN": "Veľkonočná nedeľa",
    "VPON": "Pondelok vo Veľkonočnej oktáve",
    "2VN": "2. veľkonočná nedeľa",
    "3VN": "3. veľkonočná nedeľa",
    "4VN": "4. veľkonočná nedeľa",
    "5VN": "5. veľkonočná nedeľa",
    "6VN": "6. veľkonočná nedeľa",
    "NP": "Nanebovstúpenie Pána",
    "7VN": "7. veľkonočná nedeľa",

    # Cezročné obdobie
    # Interný kód nC označuje n. týždeň cezročného obdobia.
    # V direktóriu sa JKS viažu na nedeľné záznamy; DIREKTORIUM_DATA nemá
    # samostatné JKS odporúčania pre 1. cezročnú nedeľu, lebo ju nahrádza
    # sviatok Krstu Pána.
    "1C": None,
    "2C": "2. cezročná nedeľa",
    "3C": "3. cezročná nedeľa",
    "4C": "4. cezročná nedeľa",
    "5C": "5. cezročná nedeľa",
    "6C": "6. cezročná nedeľa",
    "7C": "7. cezročná nedeľa",
    "8C": "8. cezročná nedeľa",
    "9C": "9. cezročná nedeľa",
    "10C": "10. cezročná nedeľa",
    "11C": "11. cezročná nedeľa",
    "12C": "12. cezročná nedeľa",
    "13C": "13. cezročná nedeľa",
    "14C": "14. cezročná nedeľa",
    "15C": "15. cezročná nedeľa",
    "16C": "16. cezročná nedeľa",
    "17C": "17. cezročná nedeľa",
    "18C": "18. cezročná nedeľa",
    "19C": "19. cezročná nedeľa",
    "20C": "20. cezročná nedeľa",
    "21C": "21. cezročná nedeľa",
    "22C": "22. cezročná nedeľa",
    "23C": "23. cezročná nedeľa",
    "24C": "24. cezročná nedeľa",
    "25C": "25. cezročná nedeľa",
    "26C": "26. cezročná nedeľa",
    "27C": "27. cezročná nedeľa",
    "28C": "28. cezročná nedeľa",
    "29C": "29. cezročná nedeľa",
    "30C": "30. cezročná nedeľa",
    "31C": "31. cezročná nedeľa",
    "32C": "32. cezročná nedeľa",
    "33C": "33. cezročná nedeľa",
    "34C": "34. cezročná nedeľa",

    # Turíce a sviatky
    "1TS": "Nedeľa zoslania Ducha Svätého (Turíce)",
    "2TS": "Panny Márie, Matky Cirkvi",
    "3TS": "Pána Ježiša Krista, najvyššieho a večného kňaza",
    "4TS": "Najsvätejšia Trojica",
    "5TS": "Najsvätejšieho Kristovho Tela a Krvi",
    "6TS": "Najsvätejšieho Srdca Ježišovho",
    "7TS": "Nepoškvrnené Srdce Panny Márie",

    # Cezročné sviatky
    "NJK":   "Narodenie sv. Jána Krstiteľa (24.VI.)",
    "NAVPM": "Sviatky Panny Márie", #  keďže v DIREKTORIUM_DATA nie je samostatný riadok pre tento sviatok, mapuje sa na Sviatky Panny Márie   
    "CMV":   "Sv. Cyrila a Metoda (5.VII.)",
    "BEN":   "Sviatky svätých mužov",
    "BRI":   "Sviatky svätých žien",
    "PREM":  None,  # Zámerný sentinel: Premenenie Pána (6.VIII.) nemá vhodný direktóriový záznam, preto sa JKS odporúčania nenačítajú.
    "VAV":   "Sviatky mučeníkov",
    "BAR":   "Sviatky apoštolov",
    "FJ":   "Sviatky apoštolov",    
    "NPMAR": "Narodenie Panny Márie (8.IX.)",
    "PSK":   "Povýšenie Svätého kríža (14.IX.)",
    "MATE":   "Sviatky apoštolov",
    "MGR":   "O sv. anjeloch",  # stupeň korigovaný cez STUPEN_OVERRIDE (Sviatok, nie Spomienka)
    "ZOS":   "Spomienka na Všetkých zosnulých veriacich (2.XI.)",
    "VPLB":  "Výročie posviacky chrámu",  # stupeň korigovaný cez STUPEN_OVERRIDE (Sviatok, nie Slávnosť)
    "OND":   "Sviatky apoštolov",

    # Mesačné
    "1L": "Zjavenie Pána - Traja králi (6.I.)",
    "2L": "Obetovanie Pána (2.II.)",
    "3L": "Sv. Jozefa, ženícha (19.III.)",
    "4L": "Sviatky svätých mužov",        
    "5L": "Sv. Jozefa, robotníka (1.V.)",
    "6L": "Sv. Petra a Pavla, apoštolov (29.VI.)",    
    "7L": "Sviatky apoštolov",    
    "8L": "Nanebovzatie Panny Márie (15.VIII.)",
    "9L": "Sedembolestnej Panny Márie (15.IX.)",
    "10L": "Sviatky mučeníkov",   
    "11L": "Všetkých svätých (1.XI.)",
    "12L": "Nepoškvrnené počatie Panny Márie (8.XII.)"
}


def je_privilegovana_nedela(datum: date) -> bool:
    """
    Nedele adventné, pôstne a veľkonočné majú prednosť aj pred slávnosťami.

    Cezročné nedele sem zámerne nepatria: bežná cezročná nedeľa môže ustúpiť
    slávnosti alebo sviatku Pána podľa pevného pravidla prednosti.
    """
    if datum.weekday() != 6:
        return False

    velka_noc = velkonocna_nedela(datum.year)
    prva_postna = velka_noc - timedelta(days=42)
    turice = velka_noc + timedelta(days=49)
    prva_adventna = prva_adventna_nedela(datum.year)

    return (
        # Adventné nedele sú privilegované len do 24.12.; ak 25.12. pripadne na nedeľu,
        # prednosť má slávnosť Narodenia Pána.
        prva_adventna <= datum < date(datum.year, 12, 25)
        or prva_postna <= datum <= turice
    )


def je_den_s_prednostou_pred_pevnym_slavenim(datum: date) -> bool:
    """Dni Veľkého týždňa a Veľkonočnej oktávy majú prednosť pred pevným dátumom."""
    velka_noc = velkonocna_nedela(datum.year)
    velky_tyzden_zaciatok = velka_noc - timedelta(days=7)
    oktava_koniec = velka_noc + timedelta(days=7)
    return velky_tyzden_zaciatok <= datum <= oktava_koniec


def pevne_slavenie_ma_prednost_pred_nedelou(
    datum: date,
    kod: str | None,
    nazov: str | None,
    stupen: str | None,
) -> bool:
    """
    Centrálne pravidlo prednosti pevného dátumu pred nedeľou.

    Bežná nedeľa ustupuje slávnostiam a sviatkom Pána. Nedele adventné,
    pôstne a veľkonočné majú prednosť aj pred slávnosťami. Spomienky a
    sviatky svätých alebo Panny Márie nedeľu neprebíjajú, okrem osobitne uvedených dní.
    """
    if je_den_s_prednostou_pred_pevnym_slavenim(datum):
        return False

    if datum.weekday() != 6:
        return True

    kod = (kod or "").upper()
    nazov_upper = (nazov or "").upper()
    stupen = (stupen or "").strip()

    if kod in OSOBITNE_DNI_S_PREDNOSTOU_V_NEDELU:
        return True

    if je_privilegovana_nedela(datum):
        return False

    if stupen == "Slávnosť":
        return True

    if stupen == "Sviatok":
        return (
            kod in SVIATKY_PANA_S_PREDNOSTOU_V_NEDELU
            or "PÁNA" in nazov_upper
            or "SVÄTÉHO KRÍŽA" in nazov_upper
            or "LATERÁNSKEJ BAZILIKY" in nazov_upper
            or "POSVIACKY CHRÁMU" in nazov_upper
        )

    return False


def najdi_presny_datum_v_direktoriu(
    datum: date,
    vyzaduj_prednost: bool = True,
) -> tuple[str, str] | None:
    """
    Ak Direktórium obsahuje záznam s presným dátumom v tvare (14.IX.),
    vráti jeho mesačný kód (napr. 9L) a názov bez dátumu.
    """
    data = DIREKTORIUM_DATA
    pattern = re.compile(r"\((\d{1,2})\.([IVX]+)\.\)")

    for zaznamy in data.values():
        for zaznam in zaznamy:
            den = str(zaznam.get("den", ""))
            match = pattern.search(den)
            if not match:
                continue

            den_v_mesiaci = int(match.group(1))
            mesiac = RIMSKE_MESIACE.get(match.group(2))
            if den_v_mesiaci == datum.day and mesiac == datum.month:
                nazov = pattern.sub("", den).strip()
                kod = f"{mesiac}L"
                stupen = str(zaznam.get("stupen", ""))
                if vyzaduj_prednost and not pevne_slavenie_ma_prednost_pred_nedelou(datum, kod, nazov, stupen):
                    continue
                return kod, nazov.upper()

    return None

def najdi_pevne_slavenie_s_vlastnym_kodom(datum: date) -> tuple[str, str, str] | None:
    """Vráti pevné slávenie evidované mimo dátumového riadku direktória."""
    for mesiac, den, kod, nazov, stupen, date_fn in PEVNE_SLAVENIA_S_VLASTNYM_KODOM:
        if date_fn is not None:
            # Slávnosť sa môže v niektorých rokoch posunúť na iný deň
            # (kolízia s nedeľou/Veľkým týždňom) – skutočný dátum zisťujeme
            # cez date_fn(rok) namiesto pevného mesiac/deň.
            if datum == date_fn(datum.year):
                return kod, nazov, stupen
        elif datum.month == mesiac and datum.day == den:
            return kod, nazov, stupen
    return None

def nazov_liturgickej_casti_podla_kodu(kod: str) -> str:
    """Preloží interný kód obdobia na text hlavičky zladený s direktóriom."""
    if kod in LITURGICKE_CASTI_PODLA_KODU:
        return LITURGICKE_CASTI_PODLA_KODU[kod]

    match = re.fullmatch(r"(\d+)L", kod)
    if match:
        return f"MESAČNÉ - {match.group(1)}. MESIAC"

    match = re.fullmatch(r"(\d+)C", kod)
    if match:
        return f"{match.group(1)}. TÝŽDEŇ CEZROČNÉHO OBDOBIA"

    return "CEZROČNÉ OBDOBIE"

def vypocitaj_kod_liturgickej_casti(dnes: date | None = None) -> str:
    """
    Vráti interný kód aktuálnej liturgickej časti.

    Kódy nadväzujú na existujúce členenie programu: 1AD-4AD, 1P-5P, VT,
    1VN-7VN, 1TS-7TS a 1C-34C. Špeciálne dni zo Slávení majú vlastné kódy.
    """
    dnes = dnes or date.today()

    # Zvestovanie Pána: pevný 25.3. alebo presunutý dátum po veľkonočnej oktáve.
    # Kontrolujeme pred direktóriom, pretože direktórium vracia generický mesačný
    # kód (3L), nie špecifický kód ZV.
    if dnes == datum_zvestovania_pana(dnes.year) and pevne_slavenie_ma_prednost_pred_nedelou(dnes, "ZV", "Zvestovanie Pána", "Slávnosť"):
        return "ZV"

    # Najsvätejšie Kristovo Telo a Krv je prikázaná pohyblivá slávnosť; v roku
    # 2038 padne na 24.6. a má v KBS kalendári prednosť pred Narodením sv. Jána.
    if dnes == vypocitaj_datum_pohyblivych_slaveni(dnes.year)["Najsvätejšieho Kristovho Tela a Krvi"]:
        return "5TS"

    # Narodenie sv. Jána Krstiteľa: 24.6.; ak ho prekryje Srdce Ježišovo, presúva sa na 23.6.
    if dnes == datum_narodenia_jana_krstitela(dnes.year) and pevne_slavenie_ma_prednost_pred_nedelou(dnes, "NJK", "Narodenie sv. Jána Krstiteľa", "Slávnosť"):
        return "NJK"

    # Najsvätejšie Srdce Ježišovo je pohyblivá slávnosť; v neskorých
    # veľkonočných rokoch môže padnúť na pevný 2.7. a má prednosť pred NAVPM.
    if dnes == vypocitaj_datum_pohyblivych_slaveni(dnes.year)["Najsvätejšieho Srdca Ježišovho"]:
        return "6TS"

    # POZNÁMKA: Návšteva preblahoslavenej Panny Márie (NAVPM, 2.7.), Sv. Cyrila
    # a Metoda (CMV, 5.7.), Premenenie Pána (PREM, 6.8.), Narodenie Panny Márie
    # (NPMAR, 8.9.), Povýšenie Svätého kríža (PSK, 14.9.), Sv. Michala, Gabriela
    # a Rafaela (MGR, 29.9.), Spomienka na Všetkých zosnulých (ZOS, 2.11.),
    # Výročie posviacky Lateránskej baziliky (VPLB, 9.11.) a časť novoročného
    # obdobia (Sv. Štefan STEF 26.12., Sv. Ján SJE 27.12., Sv. Neviniatka NEV
    # 28.12., Posledný deň roka PDR 31.12., Panny Márie Bohorodičky PMB 1.1.,
    # Najsvätejšie meno Ježiš NMJ 3.1.) tu kedysi mali samostatné if-bloky,
    # hoci ich kód/názov/stupeň sú zhodné so záznamami v
    # PEVNE_SLAVENIA_S_VLASTNYM_KODOM – dve miesta s tou istou logikou sa
    # časom vedeli rozísť (presne to sa už raz stalo pri CMV, pozri komentár
    # pri tabuľke). Odstránené: o kód aj o prednosť pred nedeľou sa teraz stará
    # jediný zdroj pravdy – lookup `najdi_pevne_slavenie_s_vlastnym_kodom`
    # nižšie v tejto funkcii (spolu s `pevne_slavenie_ma_prednost_pred_nedelou`).
    #
    # Narodenie Pána (1VI, 25.12.) do tejto konsolidácie ZÁMERNE nepatrí – jeho
    # kód "1VI" je zároveň generickým kódom pre celé zvyšné vianočné obdobie
    # (pozri `if dnes >= date(dnes.year, 12, 25): ... return "1VI"` nižšie),
    # takže pridanie samostatného riadku do tabuľky by spôsobilo, že
    # vypocitaj_aktualnu_liturgicku_cast() by pre 25.12. omylom vrátil
    # generický názov "OKTÁVA PO NARODENÍ PÁNA" namiesto správneho "NARODENIE
    # PÁNA" (kódy sa zhodujú, no ide o iný deň). Preto ostáva ošetrené
    # explicitne aj v tejto funkcii, aj vo vypocitaj_aktualnu_liturgicku_cast().
    #
    # Musí sa skontrolovať PRED direktóriovým lookupom nižšie (najdi_presny_datum_v_direktoriu):
    # direktórium má pre 25.12. vlastný záznam s dátumovou príponou "(25.XII.)",
    # ktorý by inak vrátil generický mesačný kód "12L" namiesto správneho "1VI".
    if dnes == date(dnes.year, 12, 25) and pevne_slavenie_ma_prednost_pred_nedelou(dnes, "1VI", "Narodenie Pána", "Slávnosť"):
        return "1VI"

    # Nanebovstúpenie Pána (40. deň po Veľkej noci) je slávnosť Pána a má prednosť
    # pred akýmkoľvek pevným dátumom (napr. v rokoch 2035 a 2046 padne na 3.5.,
    # kde by inak nižšie uvedený lookup vrátil kolidujúci sviatok "FJ" – Sv. Filip
    # a Jakub). Musí sa skontrolovať PRED lookupom pevných slávení s vlastným kódom,
    # inak by sa tento test nižšie (pri kóde "NP") nikdy nevykonal.
    if dnes == velkonocna_nedela(dnes.year) + timedelta(days=39):
        return "NP"

    pevne_slavenie = najdi_pevne_slavenie_s_vlastnym_kodom(dnes)
    if pevne_slavenie:
        pevny_kod, pevny_nazov, pevny_stupen = pevne_slavenie
        if pevne_slavenie_ma_prednost_pred_nedelou(dnes, pevny_kod, pevny_nazov, pevny_stupen):
            return pevny_kod

    presny_datum = najdi_presny_datum_v_direktoriu(dnes)
    if presny_datum:
        kod, _nazov = presny_datum
        povodny_jan = date(dnes.year, 6, 24)
        if not (
            dnes == povodny_jan
            and datum_narodenia_jana_krstitela(dnes.year) != povodny_jan
            and "JÁNA KRSTITEĽA" in _nazov
        ):
            return kod

    velka_noc = velkonocna_nedela(dnes.year)
    popolcova_streda = velka_noc - timedelta(days=46)
    prva_postna_nedela = velka_noc - timedelta(days=42)
    palmova_nedela = velka_noc - timedelta(days=7)
    turice = velka_noc + timedelta(days=49)
    prva_adventna = prva_adventna_nedela(dnes.year)
    krst_pana = krst_krista_pana(dnes.year)

    if dnes >= date(dnes.year, 12, 25):
        # Svätá rodina - jediný zdroj pravdy
        svata_rodina = datum_svatej_rodiny(dnes.year)
        if dnes == svata_rodina:
            return "SR"
        return "1VI"

    if dnes <= krst_pana:
        druha_vianocna_nedela = next(
            (date(dnes.year, 1, den) for den in range(2, 6) if date(dnes.year, 1, den).weekday() == 6),
            None
        )
        if dnes == date(dnes.year, 1, 6) and pevne_slavenie_ma_prednost_pred_nedelou(dnes, "ZP", "Zjavenie Pána", "Slávnosť"):
            return "ZP"
        if dnes == krst_pana:
            return "KKP"
        if druha_vianocna_nedela and dnes == druha_vianocna_nedela:
            return "2VIN"
        return "2VI"

    if krst_pana < dnes < popolcova_streda:
        # nC označuje týždeň cezročného obdobia, nie nutne n-tú nedeľu.
        # Po Krste Pána začína 1C hneď v nasledujúci deň; samotná 1. cezročná nedeľa
        # sa v praxi neslávi samostatne, lebo ju nahrádza Krst Pána.
        tyzden = ((dnes - krst_pana).days // 7) + 1
        return f"{tyzden}C"

    if dnes == popolcova_streda:
        return "PS"

    if popolcova_streda < dnes < palmova_nedela:
        if dnes < prva_postna_nedela:
            return "PPS"
        tyzden = ((dnes - prva_postna_nedela).days // 7) + 1
        return f"{tyzden}P"

    if palmova_nedela <= dnes < velka_noc:
        if dnes == velka_noc - timedelta(days=3):
            return "ZST"
        if dnes == velka_noc - timedelta(days=2):
            return "VP"
        if dnes == velka_noc - timedelta(days=1):
            return "VG"
        return "VT"

    if dnes == velka_noc:
        return "1VN"

    if velka_noc < dnes < velka_noc + timedelta(days=7):
        return "VOKT"

    # POZNÁMKA: Kontrola presunutého Zvestovania Pána (pondelok po veľkonočnej
    # oktáve) sa tu úmyselne NEOPAKUJE – rovnaká podmienka
    # (dnes == datum_zvestovania_pana(dnes.year) + rovnaká kontrola prednosti)
    # sa vyhodnocuje už úplne na začiatku tejto funkcie a je tam s rovnakým
    # `dnes` vždy deterministicky rovnaká, takže druhé vyhodnotenie na tomto
    # mieste by bolo nedosiahnuteľné (dead code) – pôvodne tu bola aj kontrola
    # Nanebovstúpenia Pána, tá sa z rovnakého dôvodu presunula úplne na
    # začiatok funkcie (pred lookup pevných slávení s vlastným kódom), aby ju
    # nemohol prekryť kolidujúci pevný dátum (napr. Sv. Filip a Jakub, 3.5.,
    # v rokoch 2035 a 2046).

    if velka_noc + timedelta(days=7) <= dnes < turice:
        tyzden = ((dnes - velka_noc).days // 7) + 1
        return f"{tyzden}VN"

    specialne_po_turiciach = {
        turice: "1TS",
        turice + timedelta(days=1): "2TS",
        turice + timedelta(days=4): "3TS",
        turice + timedelta(days=7): "4TS",
        turice + timedelta(days=11): "5TS",
        turice + timedelta(days=19): "6TS",
        turice + timedelta(days=20): "7TS",
    }
    if dnes in specialne_po_turiciach:
        kod_specialneho = specialne_po_turiciach[dnes]
        if kod_specialneho == "7TS" and je_neposkvrnene_srdce_pm_prekazane(dnes):
            pass
        else:
            return kod_specialneho

    if turice < dnes < prva_adventna:
        # Pokrýva aj 1.–2. december v rokoch, kde Advent začína až 2. alebo 3.
        # decembra (napr. 2023, 2028, 2034…). Tieto dni liturgicky patria do
        # 34. cezročného týždňa (Krista Kráľa) a cezročná vetva ich správne
        # zaradí — nie je potrebná explicitná vetva pre "december pred Adventom".
        krista_krala = prva_adventna - timedelta(days=7)
        zaciatok_tyzdna = nedela_zaciatku_tyzdna(dnes)
        tyzden = 34 - ((krista_krala - zaciatok_tyzdna).days // 7)
        tyzden = max(1, min(34, tyzden))
        return f"{tyzden}C"

    if prva_adventna <= dnes < date(dnes.year, 12, 25):
        tyzden = min(4, ((dnes - prva_adventna).days // 7) + 1)
        return f"{tyzden}AD"

    return "2VI"

def vypocitaj_aktualnu_liturgicku_cast(dnes: date | None = None) -> str:
    """
    Určí aktuálnu liturgickú časť pre hlavné okno aplikácie.

    Výstup je zámerne stručný a veľkými písmenami, napr.:
    25. TÝŽDEŇ CEZROČNÉHO OBDOBIA, ŠTVRTÝ PÔSTNY TÝŽDEŇ,
    VEĽKÝ TÝŽDEŇ (SVÄTÝ TÝŽDEŇ), PIATA VEĽKONOČNÁ NEDEĽA.
    """
    dnes = dnes or date.today()
    kod_dna = vypocitaj_kod_liturgickej_casti(dnes)

    pevne_slavenie = najdi_pevne_slavenie_s_vlastnym_kodom(dnes)
    if pevne_slavenie and kod_dna == pevne_slavenie[0]:
        return LITURGICKE_CASTI_PODLA_KODU.get(kod_dna, pevne_slavenie[1].upper())

    presny_datum = najdi_presny_datum_v_direktoriu(dnes)
    if presny_datum and kod_dna == presny_datum[0]:
        _kod, nazov = presny_datum
        return nazov

    pohyblive_slavenie = nazov_pohybliveho_slavenia_pre_datum(dnes)
    if pohyblive_slavenie:
        return pohyblive_slavenie

    if dnes == date(dnes.year, 12, 25):
        return "NARODENIE PÁNA"

    return nazov_liturgickej_casti_podla_kodu(kod_dna)

PRESUNUTE_SLAVNOSTI = [
    # Slávnosti/sviatky s pevným kalendárnym dátumom, ktoré sa v niektorých
    # rokoch (kolízia s nedeľou/Veľkým týždňom a pod.) presúvajú na iný deň.
    # Jedna spoločná tabuľka pre popis_presunu_slavnosti() aj
    # zostav_text_status_baru() – predtým mala každá funkcia vlastnú (takmer
    # identickú) kópiu tohto vzoru pre každú zo 4 slávností zvlášť.
    #
    # kod                    – kód liturgickej časti pridelený skutočnému dňu slávenia
    # povodny_mesiac/den     – pôvodný (bežný) kalendárny dátum
    # skutocny_datum_fn(rok) – funkcia vracajúca skutočný (prípadne presunutý) dátum
    # genitiv_povodneho_datumu – text pre popis_presunu_slavnosti, napr. "25. marca"
    # na_sablona             – text do status baru, keď sme na PÔVODNOM dátume
    #                          a slávenie sa presunulo inam ({den}/{mesiac}/{rok}
    #                          zodpovedajú skutočnému dátumu)
    # z_text                 – text do status baru, keď sme na SKUTOČNOM
    #                          (presunutom) dátume
    {
        "kod": "ZV",
        "povodny_mesiac": 3, "povodny_den": 25,
        "skutocny_datum_fn": datum_zvestovania_pana,
        "genitiv_povodneho_datumu": "25. marca",
        "na_sablona": "Zvestovanie Pána sa presúva na {den}.{mesiac}.{rok}",
        "z_text": "Zvestovanie Pána sa presúva z 25.3.",
    },
    {
        "kod": "3L",
        "povodny_mesiac": 3, "povodny_den": 19,
        "skutocny_datum_fn": datum_sv_jozefa_zenicha,
        "genitiv_povodneho_datumu": "19. marca",
        "na_sablona": "Sv. Jozef, ženích sa presúva na {den}.{mesiac}.{rok}",
        "z_text": "Sv. Jozef, ženích sa presúva z 19.3.",
    },
    {
        "kod": "NJK",
        "povodny_mesiac": 6, "povodny_den": 24,
        "skutocny_datum_fn": datum_narodenia_jana_krstitela,
        "genitiv_povodneho_datumu": "24. júna",
        "na_sablona": "Narodenie Jána Krstiteľa sa presúva na {den}.{mesiac}.{rok}",
        "z_text": "Narodenie Jána Krstiteľa sa presúva z 24.6.",
    },
    {
        "kod": "12L",
        "povodny_mesiac": 12, "povodny_den": 8,
        "skutocny_datum_fn": datum_neposkvrneneho_pocatia,
        "genitiv_povodneho_datumu": "8. decembra",
        "na_sablona": "Nepoškvrnené počatie Panny Márie sa presúva na {den}.{mesiac}.{rok}",
        "z_text": "Nepoškvrnené počatie Panny Márie sa presúva z 8.12.",
    },
]


def popis_presunu_slavnosti(dnes: date | None = None) -> str | None:
    """Vráti krátky popis pôvodného dátumu, ak je dnešná slávnosť presunutá."""
    dnes = dnes or date.today()
    kod_dna = vypocitaj_kod_liturgickej_casti(dnes)

    for polozka in PRESUNUTE_SLAVNOSTI:
        povodny_datum = date(dnes.year, polozka["povodny_mesiac"], polozka["povodny_den"])
        if (
            kod_dna == polozka["kod"]
            and dnes == polozka["skutocny_datum_fn"](dnes.year)
            and dnes != povodny_datum
        ):
            return f"presunutá z {polozka['genitiv_povodneho_datumu']}"
    return None

def get_parnost_roka(datum: date) -> int:
    """
    Vráti párnosť liturgického roka pre dvojročný cyklus všedných dní
    cezročného obdobia (1 = nepárny → Year I / c1, 2 = párny → Year II / c2).

    Liturgický rok sa pre účely tohto cyklu pomenúva podľa kalendárneho roka,
    do ktorého spadá jeho januárovo-novembrová časť (napr. liturgický rok
    "2025" trvá od 1. adventnej nedele 2024 do konca novembra 2025 a je to
    Year I, pretože 2025 je nepárny).

    Pre dátumy pred Prvou adventnou nedeľou daného kalendárneho roka (vrátane
    okrajových 27.11.–3.12., ktoré ešte patria do predošlého liturgického roka)
    sa číslo liturgického roka zhoduje s datum.year. Od Prvej adventnej nedele
    (vrátane) už začal nový liturgický rok, ktorého januárovo-novembrová časť
    pripadne na datum.year + 1.
    """
    if datum >= prva_adventna_nedela(datum.year):
        lit_rok_cislo = datum.year + 1
    else:
        lit_rok_cislo = datum.year
    return 2 if lit_rok_cislo % 2 == 0 else 1

def format_skratku_liturgickej_casti(kod: str, datum: date) -> str:
    """Skratka do hlavičky; cezročné obdobie doplní párnosť roka ako c1/c2."""
    if kod == "2VIN":
        return "2VI"
    if kod in ("PS", "PPS"):
        return "PS"
    # Špeciálny prípad: Veľkonočný pondelok → VPON
    if kod == "VOKT" and datum == velkonocna_nedela(datum.year) + timedelta(days=1):
        return "VPON"     
       
    if kod == "VOKT":
        return "1VN"
    # Pevné dátumy — skratka žalmu je číslo mesiaca + L (napr. január = 1L)
    PEVNE_DATUMOVE_KODY = {"ZP"}
    if kod in PEVNE_DATUMOVE_KODY:
        return f"{datum.month}L"
    match = re.fullmatch(r"(\d+)C", kod)
    if match:
        parnost = get_parnost_roka(datum)
        return f"{match.group(1)}c{parnost}"
    return kod

def format_skratky_liturgickej_casti(dnes: date | None = None) -> str:
    dnes = dnes or date.today()
    zajtra = dnes + timedelta(days=1)
    dnes_kod = vypocitaj_kod_liturgickej_casti(dnes)
    zajtra_kod = vypocitaj_kod_liturgickej_casti(zajtra)
    return (
        f"{format_skratku_liturgickej_casti(dnes_kod, dnes)} "
        f"zajtra {format_skratku_liturgickej_casti(zajtra_kod, zajtra)}"
    )

def format_aktualna_liturgicka_cast(dnes: date | None = None) -> str:
    return f"Aktuálna liturgická časť:\n{vypocitaj_aktualnu_liturgicku_cast(dnes)}"

def zostav_text_hlavicky(
    liturgicky_rok: str | None = None,
    dnes: date | None = None,
    casove_vztahy: dict | None = None,
) -> str:
    """Zostaví text titulku hlavného okna rovnakou logikou, akú používa GUI."""
    dnes = dnes or date.today()
    liturgicky_rok = liturgicky_rok or vypocitaj_liturgicky_rok(dnes)
    cz = casove_vztahy or zostavit_casove_vztahy_titulku(dnes)
    zaklad = f"{cz['predpona']}{cz['hlavny']}"

    pripony = []
    # Poznámka o presune slávnosti (Zvestovanie / Ján Krstiteľ / sv. Jozef /
    # Nepoškvrnené počatie) sa zobrazuje iba v status bare (pozri
    # zostav_text_status_baru), nie v titulku okna – v hlavičke by bola
    # duplicitná a navyše predlžuje text titulku tak, že sa nemusí celý
    # zobraziť.
    # Poznámka o vynechanom slávení (NSPM / Sv. Ondrej / Sv. Filip a Jakub) sa
    # zobrazuje iba v status bare (pozri zostav_text_status_baru), nie v titulku
    # okna – v hlavičke je to duplicitná informácia, lebo hlavný názov dňa
    # (napr. "1. ADVENTNÁ NEDEĽA") už sám osebe ukazuje, čo sa dnes slávi.
    # Poznámka o prednosti nedele pred sviatkom sa presunula do status baru
    # (na žiadosť používateľa), preto ju tu nezobrazujeme.

    pripona = ("  –  " + "  |  ".join(pripony)) if pripony else ""
    return (
        f"Kinak v{KINAK_VERSION} | Liturgický rok {liturgicky_rok} – "
        f"{zaklad}{pripona}"
    )

def zostav_text_status_baru(
    dnes: date | None = None,
    zobrazit_zalm: bool = True,
    zobrazit_zaltara: bool = True,
    vigilia: str | None = None,
    vynechane: str | None = None,
) -> str:
    """Zostaví text stavového riadku bez potreby vytvárať Tkinter widgety."""
    dnes = dnes or date.today()
    casti = []

    if zobrazit_zalm:
        skratky = format_skratky_liturgickej_casti(dnes)
        casti.append(f"Žalm z {skratky} / xL?")  # xL? je tu fixne zobrazené zámerne. xL = mesačné sviatky podľa mesiacov (1L–12L). Užívateľ ho použije ak nenašiel vhodný žalm v navrhovaných skratkách.

    if zobrazit_zaltara:
        tyzden = vypocitaj_tyzden_zaltara(dnes)
        casti.append(f"Žaltár v breviári: {tyzden} týždeň")

    # Poznámka o vynechanom slávení v kolíznych rokoch 
    if vynechane is None:
        vynechane = popis_vynechaneho_slavenia(dnes)
    if vynechane:
        casti.append(vynechane)

    # Doplnenie informácie o presune pevných slávností/sviatkov (Zvestovanie
    # Pána, sv. Jozef ženích, Narodenie Jána Krstiteľa, Nepoškvrnené počatie)
    # – spoločná tabuľka PRESUNUTE_SLAVNOSTI, pozri jej definíciu vyššie.
    for polozka in PRESUNUTE_SLAVNOSTI:
        povodny_datum = date(dnes.year, polozka["povodny_mesiac"], polozka["povodny_den"])
        skutocny_datum = polozka["skutocny_datum_fn"](dnes.year)
        if dnes == povodny_datum:
            # sme na pôvodnom dátume, ale slávenie sa naň nepripadá (presunuté inam)
            if skutocny_datum != dnes:
                casti.append(polozka["na_sablona"].format(
                    den=skutocny_datum.day, mesiac=skutocny_datum.month, rok=skutocny_datum.year
                ))
        else:
            # sme na presunutom dátume, informuj odkiaľ
            if dnes == skutocny_datum and dnes != povodny_datum:
                casti.append(polozka["z_text"])

    # Doplnenie informácie o presunutí Svätej rodiny na 31.12.
    # (zrkadlovo k poznámke v popis_vynechaneho_slavenia, ktorá sa zobrazuje
    # 30.12.; tu informujeme v deň, kde by Sv. rodina bežne bola, prečo tam nie je)
    # Nie je súčasťou PRESUNUTE_SLAVNOSTI – iná podmienka (kolízia s nedeľou
    # Narodenia Pána), nie pevný dátum s funkciou skutočného dátumu.
    if dnes.month == 12 and dnes.day == 31:
        if je_svata_rodina_presunuta_na_pdr(date(dnes.year, 12, 30)):
            casti.append(
                "Sviatok Svätej rodiny presunutý na 30.12. (Narodenie Pána pripadlo na nedeľu)"
            )

    if vigilia is None:
        vigilia = zostavit_casove_vztahy_titulku(dnes)["vigilia"]
    if vigilia:
        casti.append(f"Vigília: {vigilia}")

    # Prednosť nedele pred sviatkom „ak nepadne na nedeľu“ – zobraz len v status bare
    prednost = zostavit_casove_vztahy_titulku(dnes)["prednost_nedele"]
    if prednost:
        casti.append(f"nedeľa má prednosť pred: {prednost}")

    return "  " + "  |  ".join(casti) if casti else ""

def zostavit_casove_vztahy_titulku(dnes: date | None = None) -> dict:
    """
    Zostaví časové vzťahy (odpočty) pre titulok hlavného okna.

    Vracia dict:
      predpona        – „časť: " (pre bežné ferié/nedele) alebo „" (pre odpočty/slávnosti)
      hlavny          – text za znakom „–" v titulku, napr.:
                          „3. deň Veľkonočnej oktávy (streda)"
                          „5. deň po Popolcovej strede (štvrtok)"
                          „25. TÝŽDEŇ CEZROČNÉHO OBDOBIA, štvrtok"
                          „NANEBOVZATIE PANNY MÁRIE (Slávnosť)"
      presun          – krátka poznámka o pôvodnom dátume presunutej slávnosti
      vigilia         – str s názvom zajtrajšej slávnosti/sviatku, ak je dnes jej vigília; inak None
      prednost_nedele – str s názvom sviatku, ak cezročná nedeľa má prednosť pred sviatkom; inak None

    Logika odpočtov:
    • Veľkonočná oktáva (kód 1VN / VOKT):  „N. deň Veľkonočnej oktávy"
    • Týždeň Popolcovej stredy (PPS):      „N. deň po Popolcovej strede"
    • Slávnosť (z direktória):              „NAZOV (Slávnosť)"  – bez dňa týždňa
    • Pomenovaná nedeľa (stupen=Nedeľa):    samotný názov  – deň je súčasťou mena
    • Sviatok / Spomienka:                  „NAZOV (stupen), den_tyzdna"
    • Všetko ostatné (ferié, cezročné…):    „časť: NAZOV, den_tyzdna"
    """
    dnes = dnes or date.today()
    zajtra = dnes + timedelta(days=1)
    den = DNI_TYZDNA_SK[dnes.weekday()]

    velka_noc    = velkonocna_nedela(dnes.year)
    popol_streda = velka_noc - timedelta(days=46)

    kod          = vypocitaj_kod_liturgickej_casti(dnes)
    aktualna_cast = vypocitaj_aktualnu_liturgicku_cast(dnes)
    stupen       = STUPEN_OVERRIDE.get(kod) or ziskaj_stupen_liturgickeho_dna(aktualna_cast)

    # ── Odpočet / hlavný popis ───
    predpona = ""

    if kod == "1VN":
        # Veľkonočná nedeľa = 1. deň oktávy (nedeľa je implicitná)
        hlavny = "Veľkonočná nedeľa – 1. deň Veľkonočnej oktávy"

    elif kod == "VOKT":
        # Dni 2–7 oktávy (pon–sob po Veľkej noci)
        n = (dnes - velka_noc).days + 1
        if dnes == velka_noc + timedelta(days=1):
            hlavny = f"{aktualna_cast} – {n}. deň Veľkonočnej oktávy"
        else:
            hlavny = f"{n}. deň Veľkonočnej oktávy ({den})"

    elif kod == "1VI":
        # Vianočná oktáva: 25.XII. (deň 1) – 31.XII. (deň 7).
        # Dec 25 a Jan 1 sú v direktóriu ako Slávnosť, takže sem
        # dopadnú prakticky len dni 2–7 (26.–31.XII.).
        vianoce = date(dnes.year if dnes.month == 12 else dnes.year - 1, 12, 25)
        n = (dnes - vianoce).days + 1
        if dnes == vianoce:
            hlavny = f"{aktualna_cast} (Slávnosť)"
        elif dnes.weekday() == 6:
            # Nedeľa v oktáve má vlastný liturgický názov;
            # deň oktávy doplníme za pomlčku
            hlavny = f"{aktualna_cast} – {n}. deň Vianočnej oktávy"
        else:
            hlavny = f"{n}. deň Vianočnej oktávy ({den})"

    elif kod == "PPS":
        # Dni 1–3 po Popolcovej strede (štv–sob pred 1. pôstnou nedeľou)
        n = (dnes - popol_streda).days
        hlavny = f"{n}. deň po Popolcovej strede ({den})"

    elif stupen == "Slávnosť":
        # Slávnosť – deň týždňa sa nepripája (je súčasťou slávnosti)
        hlavny = f"{aktualna_cast} (Slávnosť)"

    elif stupen in ("Sviatok", "Spomienka"):
        hlavny = f"{aktualna_cast} ({stupen}), {den}"

    elif stupen == "Nedeľa":
        # Pomenovaná nedeľa (adventná, pôstna, veľkonočná) – slovo „nedeľa"
        # je priamo v názve, zbytočné ho opakovať
        hlavny = aktualna_cast

    else:
        # Ferié cezročné, adventné, pôstne, veľkonočné… + cezročné nedele
        predpona = "časť: "
        hlavny = f"{aktualna_cast}, {den}"

    # ── Vigília ─────────────────────────────────────────────────────────────
    # Anticipovaná omša (omša v predvečer s platnosťou na nasledujúci deň)
    # patrí liturgicky-právne len SLÁVNOSTIAM.
    #
    # Dôvod: Slávnosť má Prvé vešpery – jej liturgický deň začína už večer
    # predtým (porov. GIRM a Všeobecné smernice Liturgie hodín, č. 59).
    # Preto omša slávená v predvečer platí na nasledujúci deň.
    #
    # Sviatky ani spomienky Prvé vešpery nemajú – ich liturgický deň
    # začína až ránom, takže omša v predvečer by platila na dnešok.
    #
    # Nie všetky slávnosti sú v praxi anticipované – zobrazujeme len tie,
    # ktoré sú v direktóriu výslovne označené: vlastna_omsa_vigilie: True.
    # (Napr. Krista Kráľa alebo Najsvätejšia Trojica anticipovanú omšu
    # v bežnej praxi nemajú, hoci sú tiež slávnosťami.)
    vigilia = None
    zajtrajsi_kod = vypocitaj_kod_liturgickej_casti(zajtra)
    zajtra_pevne = najdi_pevne_slavenie_s_vlastnym_kodom(zajtra)
    if zajtra_pevne and zajtrajsi_kod == zajtra_pevne[0]:
        _z_kod, z_nazov, z_stupen = zajtra_pevne
        if z_stupen == "Slávnosť" and ma_vlastnu_omsu_vigilie(z_nazov):
            vigilia = z_nazov

    zajtra_presny = najdi_presny_datum_v_direktoriu(zajtra)
    if vigilia is None and zajtra_presny:
        z_kod, z_nazov = zajtra_presny
        z_stupen = ziskaj_stupen_liturgickeho_dna(z_nazov)
        povodny_jan = date(zajtra.year, 6, 24)
        presny_datum_plati = not (
            zajtra == povodny_jan
            and datum_narodenia_jana_krstitela(zajtra.year) != povodny_jan
            and "JÁNA KRSTITEĽA" in z_nazov
        )
        if presny_datum_plati and z_stupen == "Slávnosť" and ma_vlastnu_omsu_vigilie(z_nazov):
            vigilia = z_nazov

    if vigilia is None:
        # Pohyblivé slávnosti nemajú pevný dátum v direktóriu,
        # preto ich vigíliu treba dopočítať z dátumu Veľkej noci.
        velka_noc_zajtra = velkonocna_nedela(zajtra.year)
        pohyblive_vigilie = {
            velka_noc_zajtra + timedelta(days=39): "NANEBOVSTÚPENIE PÁNA",
            velka_noc_zajtra + timedelta(days=49): "NEDEĽA ZOSLANIA DUCHA SVÄTÉHO (TURÍCE)",
        }
        if zajtra in pohyblive_vigilie:
            vigilia = pohyblive_vigilie[zajtra]

    # ── Prednosť nedele ──────────────────────────────────────────────────────
    # Ak je dnes cezročná nedeľa a direktórium obsahuje sviatok/spomienku
    # na tento dátum, nedeľa má prednosť a upozorníme naň.
    prednost_nedele = None
    if dnes.weekday() == 6 and re.fullmatch(r"\d+C", kod):
        presny_dnes = najdi_presny_datum_v_direktoriu(dnes, vyzaduj_prednost=False)
        if presny_dnes:
            kandidat_kod, kandidat_nazov = presny_dnes
            kandidat_stupen = ziskaj_stupen_liturgickeho_dna(kandidat_nazov)
        else:
            kandidat = najdi_pevne_slavenie_s_vlastnym_kodom(dnes)
            if kandidat:
                kandidat_kod, kandidat_nazov, kandidat_stupen = kandidat
            else:
                kandidat_kod = kandidat_nazov = kandidat_stupen = None

        if (
            kandidat_kod
            and kandidat_nazov
            and kandidat_stupen in ("Slávnosť", "Sviatok", "Spomienka")
            and not pevne_slavenie_ma_prednost_pred_nedelou(
                dnes,
                kandidat_kod,
                kandidat_nazov,
                kandidat_stupen,
            )
        ):
            prednost_nedele = kandidat_nazov

    return {
        "predpona":        predpona,
        "hlavny":          hlavny,
        "presun":          popis_presunu_slavnosti(dnes),
        "vynechane":       popis_vynechaneho_slavenia(dnes),
        "vigilia":         vigilia,
        "prednost_nedele": prednost_nedele,
    }

def ziskaj_stupen_liturgickeho_dna(aktualna_cast: str) -> str:
    """
    Vráti stupeň slávenia ('Slávnosť', 'Sviatok', 'Spomienka', 'Nedeľa', '')
    pre daný názov liturgického dňa (uppercase reťazec).
    Porovnáva case-insensitívne a ignoruje dátumové suffixy v zátvorkách.
    """
    if not aktualna_cast:
        return ""

    def normalizuj_nazov(text: str, odstran_doplnky: bool = False) -> str:
        text = str(text).strip().lower().replace("*", "")
        text = re.sub(r'\s*\(\d{1,2}\.[ivx]+\.\)', '', text).strip()
        if odstran_doplnky:
            text = re.sub(r'\s*\([^)]*\)', '', text).strip()
        return re.sub(r"\s+", " ", text)

    hladane_varianty = {
        normalizuj_nazov(aktualna_cast),
        normalizuj_nazov(aktualna_cast, odstran_doplnky=True),
    }
    data = DIREKTORIUM_DATA
    for zaznamy in data.values():
        for zaznam in zaznamy:
            den_raw = str(zaznam.get("den", ""))
            den_varianty = {
                normalizuj_nazov(den_raw),
                normalizuj_nazov(den_raw, odstran_doplnky=True),
            }
            if hladane_varianty & den_varianty or den_raw.upper() == aktualna_cast.upper():
                return zaznam.get("stupen", "")
    return ""

def ma_vlastnu_omsu_vigilie(nazov: str) -> bool:
    """
    Vráti True, ak sa daná slávnosť anticipuje – t. j. či sa jej omša
    slávi už v predvečer s platnosťou na nasledujúci deň.

    Liturgicko-právny základ:
        Anticipovaná omša prislúcha len SLÁVNOSTIAM, pretože len slávnosti
        majú Prvé vešpery (liturgický deň začína večer predtým).
        Sviatky a spomienky Prvé vešpery nemajú – omša v ich predvečer
        by mala platnosť aktuálneho dňa, nie nasledujúceho.

    V direktóriu je anticipácia označená kľúčom:
        vlastna_omsa_vigilie: True   – slávnosť sa anticipuje
        vlastna_omsa_vigilie: False  – slávnosť sa neanticipuje
        (kľúč chýba)                – sviatok / spomienka → vráti False

    Porovnáva case-insensitívne a ignoruje dátumové suffixy v zátvorkách,
    rovnako ako ziskaj_stupen_liturgickeho_dna().
    """
    if not nazov:
        return False
    hladany = nazov.strip().lower()
    data = DIREKTORIUM_DATA
    for zaznamy in data.values():
        for zaznam in zaznamy:
            den_raw = str(zaznam.get("den", ""))
            den_clean = re.sub(r'\s*\(\d{1,2}\.[IVX]+\.\)', '', den_raw).strip().lower()
            if den_clean == hladany or den_raw.upper() == nazov.upper():
                return bool(zaznam.get("vlastna_omsa_vigilie", False))
    return False


def vypocitaj_tyzden_zaltara(dnes: date | None = None) -> str:
    """
    Vráti rímsku číslicu týždňa žaltára (I.–IV.) pre daný deň.
    Žaltár má 4 týždne, cyklus sa spúšťa od 1. adventnej nedele.
    Veľkonočná nedeľa resetuje cyklus na I. týždeň.
    Kinak nemá samostatný kód pre Bielu sobotu cez deň; deň pred Veľkou nocou
    reprezentuje kód VG, teda Veľkonočnú vigíliu, ktorá patrí k I. týždňu.
    """
    _RIMSKE = {1: "I.", 2: "II.", 3: "III.", 4: "IV."}
    dnes = dnes or date.today()
    rok = dnes.year

    # Používame globálne funkcie – jediné autoritatívne implementácie.
    # prva_adventna_nedela() je definovaná cez 3. december (nie cez Vianoce),
    # čo je liturgicky správne a konzistentné so zvyškom kódu.
    # velkonocna_nedela() je zdieľaný Gaussov algoritmus pre celú aplikáciu.

    # Zistíme, v ktorom liturgickom roku sa nachádzame
    # (nový liturgický rok začína 1. adventnou nedeľou)
    ad_tento = prva_adventna_nedela(rok)
    ad_minuly = prva_adventna_nedela(rok - 1)

    if dnes >= ad_tento:
        # Sme po začiatku nového liturgického roka (adventné obdobie)
        # Žaltár štartuje 0-indexom od 1. adventnej: AD nedeľa 1 = týždeň 1
        dni_od_adventu = (dnes - ad_tento).days
        tyzden = (dni_od_adventu // 7 % 4) + 1
    else:
        # Cezročné, pôstne, veľkonočné — obdobia majú vlastné body začiatku cyklu.
        vn = velkonocna_nedela(rok)
        prva_postna = vn - timedelta(days=42)

        turice = vn + timedelta(days=49)

        if turice < dnes < ad_tento:
            # Po Turícach pokračuje cezročné obdobie číslom týždňa dopočítaným
            # spätne od Krista Kráľa. Žaltár preto nadväzuje na kód nC.
            kod = vypocitaj_kod_liturgickej_casti(dnes)
            match = re.fullmatch(r"(\d+)C", kod or "")
            if match:
                tyzden = ((int(match.group(1)) - 1) % 4) + 1
            else:
                dni = (dnes - vn).days
                tyzden = (dni // 7 % 4) + 1
        elif dnes == vn - timedelta(days=1):
            # Veľkonočná vigília (VG) je v Kinaku samostatné slávenie.
            tyzden = 1
        elif dnes >= vn:
            # Veľkonočné: Veľkonočná nedeľa = I. týždeň.
            dni = (dnes - vn).days
            tyzden = (dni // 7 % 4) + 1
        elif vn - timedelta(days=46) <= dnes < prva_postna:
            # Popolcová streda až sobota pred 1. pôstnou nedeľou používajú
            # IV. týždeň žaltára; 1. pôstna nedeľa potom resetuje cyklus na I.
            tyzden = 4
        elif dnes >= prva_postna:
            # Pôstne: 1. pôstna nedeľa = I. týždeň žaltára.
            dni = (dnes - prva_postna).days
            tyzden = (dni // 7 % 4) + 1
        elif krst_krista_pana(rok) < dnes:
            # Po Krste Pána začína 1. týždeň cezročného obdobia; žaltár sa
            # riadi číslom cezročného týždňa, nie pokračovaním adventného cyklu.
            kod = vypocitaj_kod_liturgickej_casti(dnes)
            match = re.fullmatch(r"(\d+)C", kod or "")
            if match:
                tyzden = ((int(match.group(1)) - 1) % 4) + 1
            else:
                dni_od_adventu = (dnes - ad_minuly).days
                tyzden = (dni_od_adventu // 7 % 4) + 1
        elif dnes >= ad_minuly:
            # Vianočné obdobie a cezročné dni pred pôstom sa odvíjajú od
            # začiatku aktuálneho liturgického roka (minuloročného adventu).
            dni_od_adventu = (dnes - ad_minuly).days
            tyzden = (dni_od_adventu // 7 % 4) + 1
        else:
            # Záloha pre neštandardný vstup mimo očakávaných rozsahov.
            tyzden = 1

    return _RIMSKE.get(tyzden, "I.")

# Liturgický rok sa nepočíta do konštanty (bola by "zamrznutá" pri štarte
# procesu), ale vždy nanovo cez vypocitaj_liturgicky_rok() pri každom použití –
# vďaka tomu sa hodnota A/B/C správne zmení aj keď appka beží dlhšie
# (cez polnoc prvej adventnej nedele).

# ==========================================================
# DIREKTORIUM_DATA – obsah direktória KBS (piesne/žalmy pre pevné a pohyblivé
# slávenia), potrebný pre najdi_presny_datum_v_direktoriu() vyššie.
# ==========================================================
DIREKTORIUM_DATA = {
    "Adventné": [
    {
      "den": "1. adventná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "4, 1-2",
      "ofertorium": "4, 8-10",
      "prijimanie": "25",
      "kant": "8",
      "po_omsi": "28"
    },
    {
      "den": "2. adventná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "16, 1-2",
      "ofertorium": "16, 5-6",
      "prijimanie": "20",
      "kant": "24",
      "po_omsi": "29"
    },
    {
      "den": "3. adventná nedeľa",
      "stupen": "Nedeľa",      
      "uvodny": "24, 1-2",
      "ofertorium": "24, 3-4",
      "prijimanie": "26, 17",
      "kant": "28, 1-2",
      "po_omsi": "5"
    },
    {
      "den": "4. adventná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "21, 1-2",
      "ofertorium": "21, 5-6",
      "prijimanie": "3/18/19",
      "kant": "20, 1-2",
      "po_omsi": "30"
    },
    {
      "den": "Nepoškvrnené počatie Panny Márie (8.XII.)",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": True,
      "poznamka": "Nepoškvrnené počatie Panny Márie (8.XII.)",
      "uvodny": "363, 1-2",
      "ofertorium": "33, 1-2",
      "prijimanie": "295",
      "kant": "8",
      "po_omsi": "332"
    },
    {
      "den": "Votívne omše o Panne Márii (roráty)",      
      "stupen": "",
      "uvodny": "22, 1-2",
      "ofertorium": "2, 3-4",
      "prijimanie": "3",
      "kant": "8",
      "po_omsi": "2 / 30, 1-2"
    }
  ],
  "Vianočné": [
    {
      "den": "Narodenie Pána (25.XII.)",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": True,
      "poznamka": "Narodenie Pána vigília",
      "uvodny": "46, 1-2",
      "ofertorium": "50, 1-2",
      "prijimanie": "56",
      "kant": "39",
      "po_omsi": "88"
    },
    {
      "den": "Vo svätej noci",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": False,
      "uvodny": "49, 1-2",
      "ofertorium": "51, 1-2",
      "prijimanie": "53/56",
      "kant": "39",
      "po_omsi": "88"
    },
    {
      "den": "Na úsvite",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": False,
      "uvodny": "68",
      "ofertorium": "95, 1-3",
      "prijimanie": "45/42",
      "kant": "75, 1-2",
      "po_omsi": "76"
    },
    {
      "den": "Vo dne",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": False,
      "uvodny": "44, 1-2",
      "ofertorium": "90, 7",
      "prijimanie": "37/48/75",
      "kant": "54, 1-2",
      "po_omsi": "45"
    },    
    {
      "den": "Sv. Štefana, prvého mučeníka (26.XII.)",
      "stupen": "Sviatok",
      "uvodny": "40, 1-2",
      "ofertorium": "48, 1-2",
      "prijimanie": "39",
      "kant": "61, 1-4",
      "po_omsi": "51, 1-2"
    },    
    {
      "den": "Svätej rodiny Ježiša, Márie a Jozefa",
      "stupen": "Sviatok",      
      "uvodny": "62, 1-2",
      "ofertorium": "501",
      "prijimanie": "56/96",
      "kant": "37",
      "po_omsi": "503, 1"
    },
    {
      "den": "Posledný deň roka",      
      "stupen": "",
      "uvodny": "71, 1-2",
      "ofertorium": "49, 1-2",
      "prijimanie": "66",
      "kant": "75, 1-2",
      "po_omsi": "61, 1-4"
    },
    {
      "den": "Panny Márie Bohorodičky (1.I.)",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": False,
      "poznamka": "Panny Márie Bohorodičky",
      "uvodny": "67, 1-2 / 219, 1-3",
      "ofertorium": "97, 1-2",
      "prijimanie": "42/80",
      "kant": "62, 1-2",
      "po_omsi": "524/106"
    },   
    {
      "den": "2. vianočná nedeľa",
      "stupen": "Nedeľa",
      "poznamka": "Druhá nedeľa po Narodení Pána",
      "uvodny": "64, 1-2",
      "ofertorium": "36",
      "prijimanie": "46, 1-2",
      "kant": "37, 1-2",
      "po_omsi": "76"
    },
    {
      "den": "Najsvätejšie meno Ježiš",      
      "stupen": "Spomienka",
      "uvodny": "115, 1-2",
      "ofertorium": "76, 1-2",
      "prijimanie": "52",
      "kant": "40, 1-2",
      "po_omsi": "61"
    },
    {
      "den": "Zjavenie Pána - Traja králi (6.I.)",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": True,
      "poznamka": "Zjavenie Pána - Traja králi (6.I.)",      
      "uvodny": "109, 1-2",
      "ofertorium": "90, 7",
      "prijimanie": "56/111",
      "kant": "46, 1-2",
      "po_omsi": "113"
    },
    {
      "den": "Krst Krista Pána",
      "stupen": "Sviatok",
      "uvodny": "113, 1-2",
      "ofertorium": "115, 1-2",
      "prijimanie": "66",
      "kant": "525",
      "po_omsi": "118"
    }   
  ],
  "Pôstne": [
    {
      "den": "Popolcová streda",
      "stupen": "",
      "poznamka": "Popolcová streda",
      "uvodny": "123, 1-3",
      "ofertorium": "123, 4-6",
      "prijimanie": "151",
      "kant": "160",
      "po_omsi": "174, 1-2"
    },
    {
      "den": "1. pôstna nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "151, 1-2",
      "ofertorium": "151, 3-4",
      "prijimanie": "148",
      "kant": "152",
      "po_omsi": "150"
    },
    {
      "den": "2. pôstna nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "173, 1-2",
      "ofertorium": "115, 1-2",
      "prijimanie": "174",
      "kant": "160",
      "po_omsi": "145"
    },
    {
      "den": "3. pôstna nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "157",
      "ofertorium": "119, 1-2",
      "prijimanie": "264",
      "kant": "140",
      "po_omsi": "491"
    },
    {
      "den": "4. pôstna nedeľa",
      "stupen": "Nedeľa",      
      "uvodny": "167, 1",
      "ofertorium": "167, 4",
      "prijimanie": "129",
      "kant": "135, 1-2",
      "po_omsi": "133"
    },
    {
      "den": "5. pôstna nedeľa",
      "stupen": "Nedeľa",      
      "uvodny": "166, 1-2",
      "ofertorium": "131, 1-2",
      "prijimanie": "149",
      "kant": "160",
      "po_omsi": "146, 1-2"
    },
    {
      "den": "Palmová (Kvetná nedeľa)",
      "stupen": "Nedeľa",
      "poznamka": "Palmová nedeľa",
      "uvodny": "182",
      "ofertorium": "133, 1-2",
      "prijimanie": "153",
      "kant": "160",
      "po_omsi": "150, 1"
    },    
    {
      "den": "Zelený štvrtok",
      "stupen": "",
      "uvodny": "244, 1",
      "ofertorium": "244, 4",
      "prijimanie": "270",
      "kant": "269, 1-5",
      "po_omsi": ""
    },
    {
      "den": "Veľký piatok",
      "stupen": "",
      "uvodny": "Poklona krížu:",
      "ofertorium": "131, 129, 146",
      "prijimanie": "152, 135, 133",
      "kant": "160",
      "po_omsi": ""
    },
    {
      "den": "Sv. Jozefa, ženícha (19.III.)",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": False,
      "poznamka": "Sv. Jozefa, ženícha (19.III.)",
      "uvodny": "419, 1-2",
      "ofertorium": "419, 3",
      "prijimanie": "295",
      "kant": "287",
      "po_omsi": "449"
    },
    {
      "den": "Zvestovanie Pána*",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": False,
      "uvodny": "33, 1-2",
      "ofertorium": "33, 2-3",
      "prijimanie": "295",
      "kant": "",
      "po_omsi": ""
    }
  ],
  "Veľkonočné": [
    {
      "den": "Veľkonočná vigília",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": True,
      "uvodny": "Asperges - 484",
      "ofertorium": "202",
      "prijimanie": "201, 199",
      "kant": "200",
      "po_omsi": "192, 526, 317, 312"
    },
    {
      "den": "Veľkonočná nedeľa",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": False,
      "uvodny": "210, 1-2",
      "ofertorium": "194",
      "prijimanie": "201",
      "kant": "204",
      "po_omsi": "523/312/195"
    },    
    {
      "den": "Pondelok vo Veľkonočnej oktáve",
      "stupen": "Slávnosť",
      "uvodny": "193, 1",
      "ofertorium": "193, 4",
      "prijimanie": "192",
      "kant": "198",
      "po_omsi": "200"
    },
    {
      "den": "2. veľkonočná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "194, 1-2",
      "ofertorium": "194, 3-4",
      "prijimanie": "211",
      "kant": "212",
      "po_omsi": "201"
    },
    {
      "den": "3. veľkonočná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "202, 1-2",
      "ofertorium": "204, 1-2",
      "prijimanie": "209",
      "kant": "198",
      "po_omsi": "212"
    },
    {
      "den": "4. veľkonočná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "211, 1-2",
      "ofertorium": "199, 1-2",
      "prijimanie": "202",
      "kant": "511",
      "po_omsi": "312/195"
    },
    
    {
      "den": "Sv. Jozefa, robotníka (1.V.)",      
      "stupen": "Spomienka",
      "poznamka": "Sv. Jozefa, robotníka (1.V.)",
      "uvodny": "420, 1-2",
      "ofertorium": "420, 3-4",
      "prijimanie": "295",
      "kant": "288",
      "po_omsi": "449"
    },
    {
      "den": "5. veľkonočná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "200, 1-2",
      "ofertorium": "195, 1-2",
      "prijimanie": "204",
      "kant": "198",
      "po_omsi": "385"
    },
    {
      "den": "6. veľkonočná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "210, 1-2",
      "ofertorium": "199, 1-2",
      "prijimanie": "192",
      "kant": "194",
      "po_omsi": "313"
    },
    {
      "den": "Nanebovstúpenie Pána",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": True,
      "poznamka": "Nanebovstúpenie Pána",
      "uvodny": "213, 1-3",
      "ofertorium": "213, 4-6",
      "prijimanie": "195",
      "kant": "198",
      "po_omsi": "214"
    },
    {
      "den": "7. veľkonočná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "213, 1-3",
      "ofertorium": "201",
      
      "prijimanie": "194",
      "kant": "214",
      "po_omsi": "219"
    },    
    {
      "den": "Nedeľa zoslania Ducha Svätého (Turíce)",      
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": True,
      "poznamka": "(Turíce)",
      "uvodny": "218/219",
      "ofertorium": "218, 5-6/219",
      "prijimanie": "202",
      "kant": "287",
      "po_omsi": "216"
    }
    
  ],  
  "Cezročné": [
    {
      "den": "Svätodušný pondelok",
      "stupen": "Sviatok",
      "uvodny": "216, 1-2",
      "ofertorium": "216, 3-4",
      "prijimanie": "293",
      "kant": "217a",
      "po_omsi": ""
    }, 
    {
      "den": "Panny Márie, Matky Cirkvi",
      "stupen": "Spomienka",
      "uvodny": "366, 1",
      "ofertorium": "336, 4",
      "prijimanie": "295",
      "kant": "291/525/303",
      "po_omsi": "344"
    }, 
    {
      "den": "Pána Ježiša Krista, najvyššieho a večného kňaza",
      "stupen": "Sviatok",
      "uvodny": "269",
      "ofertorium": "",
      "prijimanie": "262",
      "kant": "",
      "po_omsi": "554"
    },  
    {
      "den": "Najsvätejšia Trojica",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": False,
      "uvodny": "248, 1",
      "ofertorium": "248, 4",
      "prijimanie": "273",
      "kant": "221",
      "po_omsi": "492"
    },
    {
      "den": "Najsvätejšieho Kristovho Tela a Krvi",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": False,
      "uvodny": "244, 1",
      "ofertorium": "244, 4",
      "prijimanie": "272",
      "kant": "303",
      "po_omsi": "498"
    },
    {
      "den": "Najsvätejšieho Srdca Ježišovho",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": False,
      "uvodny": "242, 1",
      "ofertorium": "242, 4",
      "prijimanie": "227",
      "kant": "229",
      "po_omsi": "503"
    },
    {
      "den": "Nepoškvrnené Srdce Panny Márie",
      "stupen": "Spomienka",
      "uvodny": "366, 1",
      "ofertorium": "366, 4",
      "prijimanie": "295",
      "kant": "291/525/303",
      "po_omsi": "344"
    },
    {
      "den": "2. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "237, 1",
      "ofertorium": "237, 4",
      "prijimanie": "268",
      "kant": "287",
      "po_omsi": "114"
    },    
    {
      "den": "3. cezročná nedeľa",
      "stupen": "Nedeľa",
      "poznamka": "Nedeľa Božieho slova",
      "uvodny": "246, 1",
      "ofertorium": "246, 4",
      "prijimanie": "282",
      "kant": "292, 1-2",
      "po_omsi": "118"
    },
    {
      "den": "4. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "249, 1",
      "ofertorium": "249, 5-6",
      "prijimanie": "293",
      "kant": "269",
      "po_omsi": "115"
    },
    {
      "den": "5. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "239, 1",
      "ofertorium": "239, 5-6",
      "prijimanie": "265",
      "kant": "272",
      "po_omsi": "336"
    },
    {
      "den": "6. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "251, 1",
      "ofertorium": "251, 5-6",
      "prijimanie": "300",
      "kant": "276",
      "po_omsi": "119"
    },
    {
      "den": "7. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "253, 1",
      "ofertorium": "253, 4-5",
      "prijimanie": "267",
      "kant": "",
      "po_omsi": "498"
    },
    {
      "den": "8. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "242, 1",
      "ofertorium": "242, 4",
      "prijimanie": "283",
      "kant": "",
      "po_omsi": "499"
    },
    {
      "den": "9. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "256, 1",
      "ofertorium": "256, 4",
      "prijimanie": "299",
      "kant": "",
      "po_omsi": ""
    },
    {
      "den": "10. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "255, 1",
      "ofertorium": "255, 4",
      "prijimanie": "262",
      "kant": "221",
      "po_omsi": "227"
    },
    {
      "den": "11. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "247, 1",
      "ofertorium": "247, 4-5",
      "prijimanie": "267",
      "kant": "263, 1-2",
      "po_omsi": "426"
    },
    {
      "den": "12. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "238, 1",
      "ofertorium": "238, 5-6",
      "prijimanie": "273",
      "kant": "291",
      "po_omsi": "229"
    },
    {
      "den": "13. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "248, 1",
      "ofertorium": "248, 4",
      "prijimanie": "263",
      "kant": "525",
      "po_omsi": "429"
    },
    {
      "den": "14. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "247, 1",
      "ofertorium": "247, 4-5",
      "prijimanie": "275",
      "kant": "",
      "po_omsi": ""
    },
    {
      "den": "15. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "256, 1",
      "ofertorium": "256, 4",
      "prijimanie": "296",
      "kant": "287",
      "po_omsi": "369"
    },
    {
      "den": "16. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "257, 1",
      "ofertorium": "257, 5",
      "prijimanie": "275",
      "kant": "265, 1-2",
      "po_omsi": "370"
    },
    {
      "den": "17. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "247, 1",
      "ofertorium": "247, 4-5",
      "prijimanie": "283",
      "kant": "273",
      "po_omsi": "437"
    },
    {
      "den": "18. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "244, 1",
      "ofertorium": "244, 4",
      "prijimanie": "267",
      "kant": "276",
      "po_omsi": "372"
    },
    {
      "den": "19. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "238, 1",
      "ofertorium": "238, 5-6",
      "prijimanie": "268",
      "kant": "293",
      "po_omsi": "332"
    },
    {
      "den": "20. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "253, 1",
      "ofertorium": "253, 4-5",
      "prijimanie": "296",
      "kant": "275",
      "po_omsi": "376"
    },
    {
      "den": "21. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "248, 1",
      "ofertorium": "248, 4",
      "prijimanie": "265",
      "kant": "282",
      "po_omsi": "330"
    },
    {
      "den": "22. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "251, 1",
      "ofertorium": "251, 5-6",
      "prijimanie": "293",
      "kant": "268",
      "po_omsi": "372"
    },
    {
      "den": "23. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "259, 1-2",
      "ofertorium": "259, 6-7",
      "prijimanie": "300",
      "kant": "284",
      "po_omsi": "377"
    },
    {
      "den": "24. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "256, 1",
      "ofertorium": "256, 4",
      "prijimanie": "282",
      "kant": "272",
      "po_omsi": "131"
    },
    {
      "den": "25. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "237, 1",
      "ofertorium": "237, 4",
      "prijimanie": "270",
      "kant": "493, 1-2",
      "po_omsi": "396"
    },
    {
      "den": "26. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "241, 1",
      "ofertorium": "241, 6",
      "prijimanie": "262",
      "kant": "221",
      "po_omsi": "442"
    },
    {
      "den": "27. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "255, 1",
      "ofertorium": "255, 4",
      "prijimanie": "268",
      "kant": "299",
      "po_omsi": "410"
    },
    {
      "den": "28. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "239, 1",
      "ofertorium": "239, 5-6",
      "prijimanie": "295",
      "kant": "273",
      "po_omsi": "415"
    },
    {
      "den": "29. cezročná nedeľa",      
      "stupen": "Nedeľa",
      "uvodny": "258, 1",
      "ofertorium": "258, 4",
      "prijimanie": "280",
      "kant": "263",
      "po_omsi": "412"
    },
    {
      "den": "30. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "245, 1",
      "ofertorium": "245, 5",
      "prijimanie": "263",
      "kant": "292",
      "po_omsi": "413"
    },
    {
      "den": "31. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "239, 1",
      "ofertorium": "239, 5",
      "prijimanie": "267",
      "kant": "300",
      "po_omsi": "344"
    },
    {
      "den": "32. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "247, 1",
      "ofertorium": "247, 4-5",
      "prijimanie": "275",
      "kant": "511",
      "po_omsi": "499"
    },
    {
      "den": "33. cezročná nedeľa",
      "stupen": "Nedeľa",
      "uvodny": "238, 1",
      "ofertorium": "238, 5-6",
      "prijimanie": "299",
      "kant": "283",
      "po_omsi": "498"
    },
    {
      "den": "34. cezročná nedeľa",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": False,
      "poznamka": "Krista Kráľa",
      "uvodny": "498",
      "ofertorium": "498",
      "prijimanie": "299",
      "kant": "276",
      "po_omsi": "499"
    }
  ],
  "Sviatky v cezročnom období": [
    {
      "den": "Obetovanie Pána (2.II.)",
      "stupen": "Sviatok",
      "poznamka": "Obetovanie Pána (2.II.)",
      "uvodny": "378",
      "ofertorium": "359, 4-5",
      "prijimanie": "295",
      "kant": "268",
      "po_omsi": "378"
    },    
    {
      "den": "Narodenie sv. Jána Krstiteľa (24.VI.)",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": True,
      "poznamka": "Narodenie sv. Jána Krstiteľa (24.VI.)",
      "uvodny": "428, 1-2",
      "ofertorium": "428, 3-4",
      "prijimanie": "283",
      "kant": "525",
      "po_omsi": "449"
    },
    {
      "den": "Sv. Petra a Pavla, apoštolov (29.VI.)",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": True,
      "poznamka": "Sv. Petra a Pavla, apoštolov (29.VI.)",
      "uvodny": "429, 1-2",
      "ofertorium": "429, 3-4",
      "prijimanie": "299",
      "kant": "287",
      "po_omsi": "523"
    },
    {
      "den": "Sv. Cyrila a Metoda (5.VII.)",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": False,
      "poznamka": "Sv. Cyrila a Metoda (5.VII.)",
      "uvodny": "504, 1",
      "ofertorium": "504, 4",
      "prijimanie": "299",
      "kant": "431",
      "po_omsi": "524/432"
    },    
    {
      "den": "Nanebovzatie Panny Márie (15.VIII.)",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": True,
      "poznamka": "Nanebovzatie Panny Márie (15.VIII.)",
      "uvodny": "383",
      "ofertorium": "383",
      "prijimanie": "295",
      "kant": "525",
      "po_omsi": "372"
    },
    {
      "den": "Narodenie Panny Márie (8.IX.)",
      "stupen": "Sviatok",
      "poznamka": "Narodenie Panny Márie (8.IX.)",
      "uvodny": "404, 1-2",
      "ofertorium": "404",
      "prijimanie": "272",
      "kant": "291",
      "po_omsi": "329"
    },   
    {
      "den": "Povýšenie Svätého kríža (14.IX.)",
      "stupen": "Sviatok",
      "poznamka": "Povýšenie Svätého kríža (14.IX.)",
      "uvodny": "166, 1-2",
      "ofertorium": "129",
      "prijimanie": "146",
      "kant": "160",
      "po_omsi": "131"
    },
    {
      "den": "Sedembolestnej Panny Márie (15.IX.)",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": False,
      "poznamka": "Sedembolestnej Panny Márie (15.IX.)",
      "uvodny": "405, 1-2",
      "ofertorium": "396, 1-3",
      "prijimanie": "299",
      "kant": "525",
      "po_omsi": "394, 1-2"
    },
    {
      "den": "Všetkých svätých (1.XI.)",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": True,
      "poznamka": "Všetkých svätých (1.XI.)",
      "uvodny": "417, 1-2",
      "ofertorium": "417, 3-4",
      "prijimanie": "273",
      "kant": "525",
      "po_omsi": "449"
    },
    {
      "den": "Spomienka na Všetkých zosnulých veriacich (2.XI.)",
      "stupen": "Spomienka",
      "poznamka": "Spomienka na Všetkých zosnulých veriacich (2.XI.)",
      "uvodny": "462, 1",
      "ofertorium": "462, 3-4",
      "prijimanie": "280",
      "kant": "288",
      "po_omsi": "464, 1-2"
    },    
    {
      "den": "Výročie posviacky chrámu",
      "stupen": "Slávnosť",
      "vlastna_omsa_vigilie": False,
      "poznamka": "Výročie posviacky chrámu",
      "uvodny": "257, 1",
      "ofertorium": "257, 5",
      "prijimanie": "270",
      "kant": "292, 1-2",
      "po_omsi": "499"
    },
    {
      "den": "Sviatky Panny Márie",
      "stupen": "Sviatok",
      "poznamka": "Sviatky Panny Márie",
      "uvodny": "366, 1",
      "ofertorium": "366, 4",
      "prijimanie": "295",
      "kant": "291/525/303",
      "po_omsi": "344"
    },
    {
      "den": "Sviatky apoštolov",
      "stupen": "Sviatok",
      "poznamka": "Sviatky apoštolov",
      "uvodny": "454, 1-2",
      "ofertorium": "454, 3-4",
      "prijimanie": "296",
      "kant": "525",
      "po_omsi": "454, 9-10"
    },
    {
      "den": "Sviatky mučeníkov",
      "stupen": "Sviatok",
      "poznamka": "Sviatky mučeníkov",
      "uvodny": "455, 1",
      "ofertorium": "455, 2",
      "prijimanie": "275",
      "kant": "525",
      "po_omsi": "456, 1-2"
    },
    {
      "den": "Sviatky panien",
      "stupen": "Sviatok",
      "uvodny": "457, 1-2",
      "ofertorium": "457, 3-4",
      "prijimanie": "275",
      "kant": "287",
      "po_omsi": "457, 9-10"
    },
    {
      "den": "Sviatky svätých mužov",
      "stupen": "Sviatok",
      "poznamka": "Sviatky svätých mužov",
      "uvodny": "458",
      "ofertorium": "458",
      "prijimanie": "",
      "kant": "",
      "po_omsi": "458, 6-7"
    },    
    {
      "den": "Sviatky svätých žien",
      "stupen": "Sviatok",
      "poznamka": "Sviatky svätých žien",
      "uvodny": "459b",
      "ofertorium": "459b",
      "prijimanie": "",
      "kant": "",
      "po_omsi": "459b, 6-7"
    },   
    {
      "den": "Votívna omša o Kristovej krvi",
      "stupen": "",
      "uvodny": "500",
      "ofertorium": "500",
      "prijimanie": "267",
      "kant": "292, 1-2",
      "po_omsi": "500, 4"
    },
    {
      "den": "Votívna omša o Božom milosrdenstve",
      "stupen": "",
      "uvodny": "249, 1",
      "ofertorium": "249, 5-6",
      "prijimanie": "261, 1-2",
      "kant": "511",
      "po_omsi": "493"
    },
    {
      "den": "O sv. anjeloch",
      "stupen": "Spomienka",
      "poznamka": "O sv. anjeloch",
      "uvodny": "444, 1",
      "ofertorium": "444, 2",
      "prijimanie": "273",
      "kant": "287, 1-2",
      "po_omsi": "443"
    }
  ]
}


# Predvolený (štartovací) stav diagnostiky/logovania do súboru (pozri LOG_PATH
# nižšie). Používateľ ho môže kedykoľvek prepnúť v Nastaveniach → Pokročilé →
# Diagnostika; runtime hodnotu potom mení výhradne funkcia nastav_diagnostiku()
# (sekcia DIAGNOSTIKA / LOGOVANIE nižšie) volaná z nacitat_nastavenia() a
# _zbieraj_a_normalizuj_nastavenia_z_gui(). Táto konštanta je teda len
# východisková hodnota pred prvým načítaním config.json.
ENABLE_DIAGNOSTICS = True


# ==========================================================
# CESTY (Modernizované cez pathlib)
# ==========================================================
IS_FROZEN = getattr(sys, "frozen", False)

if IS_FROZEN:
    # Adresár s EXE súborom
    BASE_DIR = Path(sys.executable).parent
    # _MEIPASS pre interné ikony
    INTERNAL_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent
    INTERNAL_DIR = BASE_DIR

def _vytvor_adresar_s_fallbackom(cesta: Path, popis: str, fallback_meno: str) -> tuple[Path, str | None]:
    """Vytvori adresar; pri zlyhani pouzije docasny fallback namiesto padu pri starte."""
    try:
        cesta.mkdir(parents=True, exist_ok=True)
        return cesta, None
    except Exception as primary_error:
        fallback = Path(tempfile.gettempdir()) / fallback_meno
        sprava = (
            f"{popis}: nepodarilo sa vytvorit {cesta} ({primary_error!r}); "
            f"pouzivam fallback {fallback}"
        )
        try:
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback, sprava
        except Exception as fallback_error:
            docasny = Path(tempfile.mkdtemp(prefix=f"{fallback_meno}_"))
            return (
                docasny,
                f"{sprava}; pevny fallback zlyhal ({fallback_error!r}); pouzivam {docasny}",
            )


CONFIG_DIR_FALLBACK_INFO = None
SONG_FOLDER_FALLBACK_INFO = None

# Konfiguracny adresar (AppData)
if platform.system() == "Windows":
    CONFIG_DIR = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData/Local")) / "Kinak"
else:
    CONFIG_DIR = Path.home() / ".config/Kinak"

CONFIG_DIR, CONFIG_DIR_FALLBACK_INFO = _vytvor_adresar_s_fallbackom(
    CONFIG_DIR,
    "Konfiguracny adresar",
    "Kinak",
)

CONFIG_FILE_PATH = CONFIG_DIR / "config.json"
LOG_PATH = CONFIG_DIR / "diagnostika.txt"

# --- LOGIKA PRE PIESNE ---
LOCAL_SONG_FOLDER = BASE_DIR / "piesne"
SYSTEM_SONG_FOLDER = CONFIG_DIR / "piesne"

# Rozhodnutie o predvolenom priecinku (Pri distribucii priloz priecinok piesne k suboru EXE.)
if LOCAL_SONG_FOLDER.is_dir():
    DEFAULT_SONG_FOLDER = LOCAL_SONG_FOLDER
else:
    DEFAULT_SONG_FOLDER, SONG_FOLDER_FALLBACK_INFO = _vytvor_adresar_s_fallbackom(
        SYSTEM_SONG_FOLDER,
        "Systemovy priecinok piesni",
        "Kinak_piesne",
    )

# Cesty k ikonám
ICONS_DIR = INTERNAL_DIR / "icons"
APP_ICON = ICONS_DIR / "Kinak32.ico"
ICON_PNG = ICONS_DIR / "Kinak_128r.png"

# ==========================================================
# DIAGNOSTIKA / LOGOVANIE - s rotaciou
# ==========================================================
LOG_MAX_BYTES = 5000000  # 5 MB
LOG_BACKUP_COUNT = 3
_kinak_logger = None

def _get_kinak_logger():
    global _kinak_logger
    if _kinak_logger is not None:
        return _kinak_logger
    logger = logging.getLogger("Kinak")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    try:
        if logger.handlers:
            logger.handlers.clear()
    except Exception:
        pass
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            filename=str(LOG_PATH),
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8"
        )
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except Exception as e:
        try:
            print(f"[LOGGING SETUP ERROR] {e}", file=sys.stderr)
        except Exception:
            pass
    _kinak_logger = logger
    return logger

def _log(level, message, exc=None):
    if not ENABLE_DIAGNOSTICS:
        return
    try:
        logger = _get_kinak_logger()
        lvl = getattr(logging, level.upper(), logging.INFO)
        if exc is not None:
            logger.log(lvl, message, exc_info=(type(exc), exc, exc.__traceback__))
        else:
            logger.log(lvl, message)
    except Exception as logging_error:
        try:
            print(f"[LOGGING ERROR] {message} | {logging_error}", file=sys.stderr)
        except Exception:
            pass

def log_exception(context, exc):
    if not ENABLE_DIAGNOSTICS:
        return
    _log("ERROR", context, exc)

def log_info(message):
    if not ENABLE_DIAGNOSTICS:
        return
    _log("INFO", message)

def log_debug(message):
    if not ENABLE_DIAGNOSTICS:
        return
    _log("DEBUG", message)


def nastav_diagnostiku(povolena: bool) -> None:
    """
    Zapne/vypne diagnostické logovanie za behu – bez nutnosti reštartu appky.

    Volá sa z dvoch miest:
      - nacitat_nastavenia() pri štarte/znovunačítaní config.json,
      - _zbieraj_a_normalizuj_nastavenia_z_gui() pri každej zmene prepínača
        "Diagnostika" v okne Nastavenia (cez ulozit_nastavenia()).

    Prechod False→True sa zaloguje AŽ PO nastavení príznaku (inak by log_info
    ešte videl starú hodnotu False a nič by nezapísal). Prechod True→False sa
    naopak zaloguje ešte PRED vypnutím, aby v logu ostala stopa, že a kedy bolo
    logovanie vypnuté.
    """
    global ENABLE_DIAGNOSTICS
    povolena = bool(povolena)
    if povolena and not ENABLE_DIAGNOSTICS:
        ENABLE_DIAGNOSTICS = True
        log_info("Diagnostika zapnutá v nastaveniach.")
    elif not povolena and ENABLE_DIAGNOSTICS:
        log_info("Diagnostika vypnutá v nastaveniach.")
        ENABLE_DIAGNOSTICS = False
    else:
        ENABLE_DIAGNOSTICS = povolena


def update_progress(
    progress_callback,
    sprava: str,
    aktualny: int | None = None,
    spolu: int | None = None,
) -> None:
    """
    Spoločný pomocník na nahlásenie priebehu sťahovania (nahrádza predtým
    7× duplicitne definovanú lokálnu funkciu `progress(...)` vnútri
    jednotlivých `stiahni_*` funkcií).

    Ak je `progress_callback` volateľný, zavolá ho s (sprava, aktualny, spolu)
    a prípadnú výnimku bezpečne zaloguje, aby zlyhanie GUI callbacku nikdy
    nezhodilo samotné sťahovanie.
    """
    if callable(progress_callback):
        try:
            progress_callback(sprava, aktualny, spolu)
        except Exception as e:
            log_exception("[LC-KBS] Progress callback zlyhal", e)

# ==========================================================
# Inicializácia diagnostiky (Pathlib verzia)
# ==========================================================

def chybaju_kniznice_pre_stahovanie() -> list[str]:
    """Vráti zoznam chýbajúcich knižníc potrebných na sťahovanie textov."""
    chybaju = []
    if requests is None:
        chybaju.append("requests")
    if BeautifulSoup is None:
        chybaju.append("beautifulsoup4")
    return chybaju


def zobraz_chybu_chybajucich_kniznic_pre_stahovanie() -> bool:
    """Zobrazí používateľovi jasnú chybu, ak chýbajú knižnice pre sťahovanie."""
    chybaju = chybaju_kniznice_pre_stahovanie()
    if not chybaju:
        return False

    nazvy = ", ".join(chybaju)
    log_info(f"Sťahovanie nie je dostupné, chýbajú knižnice: {nazvy}")
    messagebox.showerror(
        "Chýbajú knižnice",
        "Funkcia sťahovania čítaní, vešpier, refrénov a cezročných týždňov nie je dostupná, "
        f"pretože chýbajú tieto Python knižnice: {nazvy}.\n\n"
        "Doinštalujte ich príkazom:\n"
        "pip install requests beautifulsoup4\n\n"
        "Ak používate EXE verziu, treba ich zahrnúť pri zostavení aplikácie."
    )
    return True


# Viaceré kandidátske ciele pre kontrolu pripojenia. Predtým sa appka
# spoliehala výhradne na priamy TCP na 1.1.1.1:53 – ak sieť (napr. školská/
# firemná so striktným firewallom) blokuje práve tento konkrétny host/port,
# appka nahlásila "žiadne pripojenie", hoci HTTPS na skutočné ciele
# sťahovania mohol byť úplne priechodný. Zoznam preto obsahuje aj samotné
# reálne ciele sťahovania (lc.kbs.sk, breviar.kbs.sk na porte 443) ako
# poslednú záchranu.
_INTERNET_KONTROLA_HOSTY: tuple[tuple[str, int], ...] = (
    ("1.1.1.1", 53),         # Cloudflare DNS – rýchla kontrola priamo na IP (bez DNS resolvingu)
    ("8.8.8.8", 53),         # Google DNS – záložný host pre prípad, že 1.1.1.1 je blokovaný
    ("lc.kbs.sk", 443),      # reálny cieľ sťahovania čítaní / refrénov žalmov
    ("breviar.kbs.sk", 443), # reálny cieľ sťahovania vešpier
)

def _over_internet_socket(timeout: float = 2.0) -> bool:
    """
    Čistá kontrola internetového pripojenia bez akýchkoľvek GUI vedľajších
    účinkov (žiadny messagebox) – vďaka tomu je BEZPEČNÉ volať ju aj
    z pozadového (worker) vlákna, na rozdiel od je_internet_dostupny().

    Postupne skúša ciele z _INTERNET_KONTROLA_HOSTY a vráti True hneď po
    prvom úspešnom spojení; "žiadne pripojenie" nahlási až keď zlyhajú
    úplne všetky – jeden zablokovaný host/port tak appku už neblokuje
    falošne, pokiaľ je aspoň jeden z cieľov (vrátane reálnych serverov
    lc.kbs.sk/breviar.kbs.sk) reálne dosiahnuteľný.
    """
    for host, port in _INTERNET_KONTROLA_HOSTY:
        try:
            socket.create_connection((host, port), timeout=timeout)
            return True
        except OSError:
            continue
    return False


def je_internet_dostupny(timeout: float = 2.0) -> bool:
    """
    Rýchla kontrola internetu – vráti True ak je pripojenie, inak zobrazí chybu.

    POZOR – táto funkcia volá messagebox, takže je bezpečné ju volať LEN
    z hlavného (GUI) vlákna. Zo sťahovacieho worker vlákna (kde by messagebox
    z iného než hlavného vlákna bol nekorektný voči Tkinter) použite priamo
    _over_internet_socket(), ktorá je čisto informatívna bez vedľajších účinkov.
    """
    if _over_internet_socket(timeout):
        return True
    messagebox.showerror("Žiadne internetové pripojenie", "Nie ste pripojení na internet.\n\nSkontrolujte Wi-Fi/kábel a skúste znova.")
    return False


def zobraz_chybu_stahovania(nazov: str, zdroj: str):
    """Jednotné chybové hlásenie pre všetky sťahovania."""
    messagebox.showerror(
        "Chyba pri sťahovaní",
        f"Nepodarilo sa stiahnuť {nazov} z {zdroj}.\n\n"
        "Možné príčiny:\n"
        "• Žiadne internetové pripojenie\n"
        f"• Stránka {zdroj} je nedostupná\n"
        "• Prístup mohol zablokovať Firewall alebo Antivírus\n"
        "• Zmenila sa štruktúra stránky\n\n"
        "Podrobnosti v logu."
    )

def init_diagnostics():
    if not ENABLE_DIAGNOSTICS:
        return
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # LOG_PATH je teraz objekt Path, môžeme ho otvoriť priamo
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write("\n" + "="*40 + "\n")
            f.write(f"Štart Kinak v{KINAK_VERSION} | {now}\n")
            f.write(f"OS: {platform.platform()}\n")
            f.write(f"Architektúra: {platform.machine()}\n")
            f.write(f"Python: {platform.python_version()}\n")            
            f.write(f"Režim: {'EXE' if IS_FROZEN else 'Script'}\n")
            
            # .resolve() vráti absolútnu cestu, čo je pre diagnostiku najistejšie
            f.write(f"Base Dir: {BASE_DIR.resolve()}\n")
            f.write(f"Config: {CONFIG_DIR.resolve()}\n")
            if CONFIG_DIR_FALLBACK_INFO:
                f.write(f"Config fallback: {CONFIG_DIR_FALLBACK_INFO}\n")
            
            # Pridáme informáciu o priečinku s piesňami pre lepší prehľad
            f.write(f"Songs Dir: {DEFAULT_SONG_FOLDER.resolve()}\n")
            if SONG_FOLDER_FALLBACK_INFO:
                f.write(f"Songs fallback: {SONG_FOLDER_FALLBACK_INFO}\n")
            f.write("="*40 + "\n")
            
    except Exception as e:
        try:
            # Ak zlyhá zápis do súboru, vypíšeme to aspoň do systémového erroru
            sys.stderr.write(f"[INIT LOG ERROR] {e}\n")
        except Exception:
            pass

# ==========================================================
# POMOCNÉ FUNKCIE NA ÚROVNI MODULU
# ==========================================================

def normalize_diacritics(text: str) -> str:
    """
    Normalizuje reťazec – odstráni diakritiku a prevedie na malé písmená.
    Ponecháva medzery, interpunkciu a ostatné znaky.
    Používa sa na porovnávanie textov bez ohľadu na diakritiku
    (napr. pri validácii stiahnutých čítaní).
    Pozri aj: ControlApp.normalize_alnum() – agresívnejší variant len pre alfanum.
    """
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.lower()

def estimate_text_height(text: str, font_obj, wraplength: int) -> int:
    """
    Odhadne výšku textu v pixeloch pri danom wraplength.
    Simuluje zalamovanie slov rovnako ako Tkinter Label – bez renderovania.
    Používaná v ProjectionWindow aj ControlApp (live preview).

    Poznámka k \\xa0 (nezlomiteľná medzera):
        Tk Label zalamuje wraplength VÝHRADNE na ASCII medzere (U+0020).
        \\xa0 Tk považuje za súčasť slova — token "aaa\\xa0bbb" sa NEzalamuje.
        Python str.split() naopak \\xa0 rozdeľuje, čo by spôsobilo nadhodnotenie
        počtu riadkov (písmo by bolo príliš malé). Preto \\xa0 nahrádzame bežnou
        medzerou ešte pred tokenizáciou, čím odhad zodpovedá správaniu Tk.
    """
    try:
        if not text:
            return font_obj.metrics("linespace")

        total_lines = 0
        line_h = font_obj.metrics("linespace")

        for paragraph in text.split("\n"):
            words = paragraph.replace("\xa0", " ").split()
            if not words:
                total_lines += 1
                continue

            line = words[0]
            for word in words[1:]:
                if font_obj.measure(line + " " + word) <= wraplength:
                    line += " " + word
                else:
                    total_lines += 1
                    line = word
            total_lines += 1

        return total_lines * line_h

    except Exception as e:
        log_exception("estimate_text_height: chyba pri výpočte", e)
        try:
            # Fallback: odhadneme počet riadkov podľa zalomení v texte.
            # Lepšia aproximácia ako hardcoded "3" – pri dlhom texte by
            # hodnota 3 spôsobila príliš veľké písmo v projekcii.
            approx_lines = max(1, text.count("\n") + 1) if text else 1
            return font_obj.metrics("linespace") * approx_lines
        except Exception as e2:
            log_exception("estimate_text_height: fallback zlyhal", e2)
            return 40

# ==========================================================
# GLOBÁLNE UI KONŠTANTY
# ==========================================================
# Fonty sú detekované dynamicky funkciou _inicializovat_fonty(), ktorá sa volá
# v __main__ hneď po vytvorení Tk inštancie (tkfont.families() ju vyžaduje).
# Predvolené hodnoty slúžia ako univerzálny fallback – platné na všetkých platformách.
FONT_NAME: str = "Arial"
FONT_MONO: str = "Courier"

def _inicializovat_fonty() -> None:
    """
    Detekuje systémové fonty a nastaví globálne konštanty FONT_NAME a FONT_MONO.

    Musí byť volaná po vytvorení Tk inštancie (tkfont.families() to vyžaduje),
    ale PRED prvým vytvorením ProjectionWindow alebo ControlApp – inak by
    všetky widgety dostali predvolený fallback „Arial" namiesto systémového fontu.

    Správne poradie v __main__:
        root = tk.Tk()
        root.withdraw()
        _inicializovat_fonty()   # ← hneď tu, pred ControlApp(root)
        app = ControlApp(root)
    """
    global FONT_NAME, FONT_MONO
    try:
        _available_fonts = tkfont.families()

        if sys.platform == "darwin":
            FONT_NAME = "SF Pro Display" if "SF Pro Display" in _available_fonts else "Helvetica"
            FONT_MONO = "Menlo"
        elif sys.platform == "win32":
            FONT_NAME = "Segoe UI" if "Segoe UI" in _available_fonts else "Arial"
            FONT_MONO = "Consolas"
        else:
            FONT_NAME = "Ubuntu" if "Ubuntu" in _available_fonts else "DejaVu Sans"
            FONT_MONO = "Monospace" if "Monospace" in _available_fonts else "Courier"

    except Exception as e_font:
        log_exception("_inicializovat_fonty: Chyba pri detekcii fontov", e_font)
        FONT_NAME = "Arial"
        FONT_MONO = "Courier"

# TEXT_COLOR, BACKGROUND_COLOR a DEFAULT_USE_FADE sú aktívne konštanty:
# používajú sa v ProjectionWindow.__init__ a ControlApp (nie len ako init hodnoty).
TEXT_COLOR = "#ffffff"
BACKGROUND_COLOR = "#1e1e1e"
PANEL_BG_COLOR = "#1e1e1e"

# Farba textu labelu odporúčaných piesní z direktória (svetlomodrá).
# Definovaná ako konštanta, aby ju `.config(fg=...)` pri mazaní textu
# neprepísalo späť na bielu.
DIREKTORIUM_LABEL_FG = "#aaddff"
TEXT_PANEL_BG = "#2e2e2e"

WRAP_PADDING_RATIO = 0.06
MIN_WRAP = 240
# Podiel šírky okna použitý ako max_w pri výpočte veľkosti písma v projekcii.
# Zvyšok (6 %) tvorí horizontálny padding (zrkadlí WRAP_PADDING_RATIO).
PROJECTION_WRAP_RATIO = 0.94

# Konštanty pre Live Preview panel (update_live_preview)
PREVIEW_FONT_INIT   = 20   # počiatočná veľkosť písma pre iteratívny výpočet
PREVIEW_FONT_MIN    = 8    # minimálna povolená veľkosť písma v preview
PREVIEW_LOOP_LIMIT  = 15   # max. počet iterácií pri zmenšovaní písma (ochrana pred zacyklením)

# Konštanty pre horný panel strofy (vypocitaj_velkost_pisma_pre_strofu)
STROFA_FONT_INIT    = 40   # počiatočná veľkosť písma (najväčšia povolená)
STROFA_FONT_MIN     = 14   # minimálna veľkosť písma (čitateľnosť)
STROFA_LOOP_LIMIT   = 30   # ochrana pred zacyklením
STROFA_PADDING_H    = 60   # horizontálny padding (2× padx=20 + rezerva)
STROFA_PADDING_V    = 30   # vertikálny padding (2× pady=10 + rezerva)

# Oneskorenia jednorazových inicializačných callbackov pri štarte ControlApp (ms)
_STARTUP_FOCUS_DELAY_MS   = 300   # focus na manual_entry
_STARTUP_PREVIEW_DELAY_MS = 600   # prvý live preview render
_STARTUP_SAVE_DELAY_MS    = 800   # uloženie nastavení po inicializácii GUI

# Adventné a Pôstne majú rovnakú liturgickú farbu (fialová) – zámerné.
LITURGICKE_OBDOBIA = {
    "Adventné": "#FF80FF",
    "Vianočné": "#FFCC33",
    "Pôstne":   "#FF80FF",
    "Veľkonočné": "#FFCC33",
    "Cezročné": "#80FF00"
}

DEFAULT_CONFIG = {
    # Poznámka: "base_dir" sa ukladá do JSON len pre informáciu.
    # Pri štarte sa BASE_DIR vždy určuje nezávisle od tohto záznamu (pozri sekciu CESTY).
    "base_dir": str(BASE_DIR),
    "font_size": 75,
    "text_color": LITURGICKE_OBDOBIA.get("Cezročné", "#80FF00"),
    "song_folder": str(DEFAULT_SONG_FOLDER),  
    "liturgical_season": "Cezročné",
    "liturgical_year": vypocitaj_liturgicky_rok(),
    "default_filter_obdobie": "Cezročné C2",
    "pouzit_vlastnu_farbu": False,
    "bottom_margin": 40,
    "reserved_vertical_ratio": 0.20,
    "zobrazit_direktorium": False,
    "fade_speed": "mierne rýchle",
    "pomocnik_font_size": 14,
    "pomocnik_x": -1,
    "pomocnik_y": -1,
    "pomocnik_width": -1,
    "pomocnik_height": -1,
    "pomocnik_last_tab": 1,
    "zobrazovat_live_preview": True,
    "zobrazovat_specialne_znaky": True,
    "zobrazovat_znaky_chorov": True,
    "statusbar_tyzden_zaltara": True,
    "statusbar_skratka_zalmu": True,
    "statusbar_jks_piesne": True,
    "main_window_x": -1,
    "main_window_y": -1,
    "main_window_width": -1,
    "main_window_height": -1,
    "settings_window_width": -1,
    "settings_window_height": -1,
    "direktorium_window_width": -1,
    "direktorium_window_height": -1,
    "slavnosti_window_width": -1,
    "slavnosti_window_height": -1,
    "about_window_width": -1,
    "about_window_height": -1,
    "about_last_tab": 1,
    "about_font_size": 12,
    "preferred_monitor_index": 0,
    # Diagnostické logovanie do LOG_PATH (Nastavenia → Pokročilé → Diagnostika).
    # Predvolene zapnuté, aby pri páde/chybe mal používateľ reálne čo poslať na
    # podporu; kedykoľvek sa dá v nastaveniach vypnúť (pozri nastav_diagnostiku()).
    "diagnostika_povolena": True,
}

# FONT_SIZE je predvolená hodnota; ControlApp spravuje aktuálny stav
# výhradne cez self.font_size a ProjectionWindow cez self.font_size.
# Globálna konštanta sa číta len pri inicializácii DEFAULT_CONFIG.
FONT_SIZE = DEFAULT_CONFIG["font_size"]
MAX_FONT_SIZE = 150  # horná hranica slidera veľkosti písma (r. vytvorit_nastavenia_okno)

DEFAULT_USE_FADE = True

# --- Globálne zoznamy liturgických slávení ---

SLAVNOSTI_DATA = [
    ("Panny Márie Bohorodičky", "1. 1"),           # [PMB]
    ("Zjavenie Pána - Traja králi", "6. 1"),                # [ZP]
    ("Nanebovstúpenie Pána", "pohyblivý"),                  # [NP]
    ("Najsvätejšieho Kristovho Tela a Krvi", "pohyblivý"),  # [TIK]
    ("Sv. Petra a Pavla, apoštolov", "29. 6"),              # [PP]
    ("Nanebovzatie Panny Márie", "15. 8"),                  # [NPM]
    ("Všetkých svätých", "1. 11"),                          # [VS]
    ("Nepoškvrnené počatie Panny Márie", "8. 12"),          # [NPPM]
    ("Narodenie Pána", "25. 12"),                           # [NPAN]
]

NEPRIKAZANE_DATA = [
    ("Najsvätejšie meno Ježiš", "3. 1"),                               # [NMJ]
    ("Obetovanie Pána (Hromnice)", "2. 2"),                            # [OP]     
    ("Popolcová streda", "pohyblivý"),                                 # [PS]   
    ("Sv. Jozefa, ženícha Panny Márie", "19. 3"),                      # [SJ]
    ("Zvestovanie Pána*", "25. 3"),                                    # [ZV]
    ("Pondelok vo Veľkonočnej oktáve", "pohyblivý"),                   # [VPON]    
    ("Turíčny pondelok", "pohyblivý"),                                 # [TPON]
    ("Pána Ježiša Krista, najvyššieho a večného kňaza", "pohyblivý"),  # [VK] 
    ("Najsvätejšieho Srdca Ježišovho", "pohyblivý"),                   # [NSJ]
    ("Nepoškvrnené Srdce Panny Márie", "pohyblivý"),                   # [NSPM]
    ("Narodenie sv. Jána Krstiteľa", "24. 6"),                         # [NJK]
    ("Návšteva preblahoslavenej Panny Márie", "2. 7"),                 # [NAVPM]
    ("Sv. Cyrila a Metoda, slovanských vierozvestov", "5. 7"),         # [CMV] 
    ("Premenenie Pána", "6. 8"),                                       # [PREM]
    ("Narodenie Panny Márie", "8. 9"),                                 # [NPMAR]
    ("Povýšenie Svätého kríža", "14. 9"),                              # [PSK]
    ("Sedembolestnej Panny Márie, patrónky Slovenska", "15. 9"),       # [SPM]
    ("Sv. Michala, Gabriela a Rafaela, archanieli", "29. 9"),             # [MGR] 
    ("Spomienka na Všetkých zosnulých veriacich", "2. 11"),            # [ZOS]
    ("Výročie posviacky Lateránskej baziliky", "9. 11"),              # [VPLB]   
    ("Sv. Štefana, prvého mučeníka", "26. 12"),                        # [STEF]
    ("Sv. Neviniatok, mučeníkov", "28. 12"),                           # [NEV]
]

POHYBLIVE_DATA = [
    ("Prvá adventná nedeľa (začína nový liturgický rok)",
     "Nasleduje po slávnosti Krista Kráľa."),                                      # [1AD]

    ("Svätej rodiny Ježiša, Márie a Jozefa",
     "Nedeľa nasledujúca po Narodení Pána alebo 30. decembra v situácii, že slávnosť Narodenia Pána pripadne na nedeľu."),  # [SR]

    ("Krst Krista Pána",
     "Nedeľa po Zjavení Pána uzatvára vianočné obdobie."),  # [KKP]

    ("Popolcová streda",
     "Streda v siedmom týždni pred Veľkonočnou nedeľou."),                          # [PS]

    ("Palmová (Kvetná nedeľa)",
     "Nedeľa pred Veľkonočnou nedeľou."),                                           # [VT]

    ("Veľkonočná nedeľa",
     "Nedeľa po prvom jarnom splne mesiaca. Môže pripadnúť na jednu z nedieľ od 22. marca do 25. apríla."),  # [1VN]
    
    ("Pondelok vo Veľkonočnej oktáve",                   
     "Nasleduje hneď po Veľkonočnej nedeli."),                                      # [VPON]

    ("Nedeľa Božieho milosrdenstva",
     "Druhá veľkonočná nedeľa, posledný deň veľkonočnej oktávy."),                  # [NBM]

    ("Nanebovstúpenie Pána",
     "Štyridsiaty deň po Veľkej noci – pripadá vždy na štvrtok 6. veľkonočného týždňa"),                                            # [NP]

    ("Nedeľa zoslania Ducha Svätého (Turíce)",
     "Päťdesiaty deň po Veľkej noci - uzatvára sa veľkonočné obdobie."),            # [TUR]
    
    ("Panny Márie, Matky Cirkvi",
     "Deň po Zoslaní Ducha Svätého - Turíčny pondelok."),                           # [PMMC]

    ("Pána Ježiša Krista, najvyššieho a večného kňaza",
     "Štvrtok po slávnosti Zoslania Ducha Svätého."),                               # [VK]

    ("Najsvätejšej Trojice",
     "Prvá nedeľa po slávnosti Zoslania Ducha Svätého."),                           # [NT]

    ("Najsvätejšieho Kristovho Tela a Krvi",
     "Štvrtok po slávnosti Najsvätejšej Trojice."),                                 # [TIK]

    ("Najsvätejšieho Srdca Ježišovho",
     "Piatok v týždni po slávnosti Najsvätejšieho Kristovho Tela a Krvi."),         # [NSJ]
    
    ("Nepoškvrnené Srdce Panny Márie",
     "Sobota po Najsvätejšom Srdci Ježišovom."),                                  # [NSPM]

    ("Krista Kráľa",
     "Posledná, 34. cezročná nedeľa v liturgickom roku."),                        # [KK]
]

SLAVNOSTI_KODY_PRE_VYBER = {
    "Panny Márie Bohorodičky": "PMB",
    "Zjavenie Pána - Traja králi": "1L",
    "Nanebovstúpenie Pána": "NP",
    "Najsvätejšieho Kristovho Tela a Krvi": "5TS",
    "Sv. Petra a Pavla, apoštolov": "6L",
    "Nanebovzatie Panny Márie": "8L",
    "Všetkých svätých": "11L",
    "Nepoškvrnené počatie Panny Márie": "12L",
    "Narodenie Pána": "1VI",
    "Najsvätejšie meno Ježiš": "NMJ",
    "Obetovanie Pána (Hromnice)": "2L",
    "Popolcová streda": "PS",
    "Sv. Jozefa, ženícha Panny Márie": "3L",
    "Zvestovanie Pána*": "ZV",
    "Pondelok vo Veľkonočnej oktáve": "VPON",
    "Turíčny pondelok": "2TS",
    "Pána Ježiša Krista, najvyššieho a večného kňaza": "3TS",
    "Najsvätejšieho Srdca Ježišovho": "6TS",
    "Nepoškvrnené Srdce Panny Márie": "7TS",
    "Narodenie sv. Jána Krstiteľa": "NJK",
    "Návšteva preblahoslavenej Panny Márie": "NAVPM",
    "Sv. Cyrila a Metoda, slovanských vierozvestov": "CMV",
    "Premenenie Pána": "PREM",
    "Narodenie Panny Márie": "NPMAR",
    "Povýšenie Svätého kríža": "PSK",
    "Sedembolestnej Panny Márie, patrónky Slovenska": "9L",
    "Sv. Michala, Gabriela a Rafaela, archanieli": "MGR",
    "Spomienka na Všetkých zosnulých veriacich": "ZOS",
    "Výročie posviacky Lateránskej baziliky": "VPLB",
    "Sv. Štefana, prvého mučeníka": "STEF",
    "Sv. Jána, apoštola a evanjelistu": "SJE",    
    "Sv. Neviniatok, mučeníkov": "NEV",
    "Prvá adventná nedeľa (začína nový liturgický rok)": "1AD",
    "Svätej rodiny Ježiša, Márie a Jozefa": "SR",
    "Krst Krista Pána": "KKP",
    "Palmová (Kvetná nedeľa)": "VT",
    "Veľkonočná nedeľa": "1VN",
    "Nedeľa Božieho milosrdenstva": "2VN",
    "Nedeľa zoslania Ducha Svätého (Turíce)": "1TS",
    "Panny Márie, Matky Cirkvi": "2TS",
    "Najsvätejšej Trojice": "4TS",
    "Krista Kráľa": "34C",
}


def vyber_prvu_piesen_z_direktorioveho_textu(text):
    """Z direktóriového zápisu typu '244, 1' alebo '3/18/19' vyberie prvé číslo piesne."""
    match = re.search(r"\b\d{1,3}[a-zA-Z]?\b", str(text or ""))
    return match.group(0) if match else ""

# --- Direktórium vložené priamo do kódu ---
#
# Kľúč  vlastna_omsa_vigilie  (bool | chýba):
#   True  – slávnosť sa ANTICIPUJE: omša v predvečer platí na nasledujúci deň.
#           Liturgický základ: slávnosť má Prvé vešpery, jej deň začína
#           večer predtým (GIRM; Všeobecné smernice Liturgie hodín, č. 59).
#           Príklady: Turíce, Nanebovzatie Panny Márie, Všetkých svätých…
#   False – slávnosť sa neanticipuje (napr. Krista Kráľa, Najsv. Trojica).
#   chýba – záznam je Sviatok alebo Spomienka; anticipácia sa na ne
#           nevzťahuje, pretože nemajú Prvé vešpery.
#
# (DIREKTORIUM_DATA je definovaná vyššie, hneď po ostatných liturgických
# tabuľkách a funkciách – pozri sekciu "ZÁKLADNÉ NASTAVENIA" na začiatku
# súboru.)

FADE_PRESETS = {
    "vypnuté": {"steps": 0,  "delay": 0},
    "rýchle": {"steps": 10, "delay": 10},
    "mierne rýchle": {"steps": 20, "delay": 15},
    "mierne stredné": {"steps": 35, "delay": 20},
    "stredné": {"steps": 60, "delay": 25},
    "pomalé": {"steps": 90, "delay": 30},
    "veľmi pomalé": {"steps": 120, "delay": 35},    
}

def spustit_startovaciu_diagnostiku() -> None:
    """Inicializuje diagnostiku pri reálnom štarte aplikácie, nie pri importe modulu."""
    init_diagnostics()
    log_info("Spúšťam aplikáciu...")
    log_debug(f"BASE_DIR = {BASE_DIR}")
    log_debug(f"CONFIG_FILE_PATH = {CONFIG_FILE_PATH}")
    log_debug(f"DEFAULT_SONG_FOLDER = {DEFAULT_SONG_FOLDER}")
    log_debug(f"ICONS_DIR = {ICONS_DIR}")
    log_debug(f"APP_ICON = {APP_ICON}")
    log_info(f"DIREKTORIUM_DATA načítané, sekcie: {list(DIREKTORIUM_DATA.keys())}")

# ==========================================================
# LC.KBS.SK - STIAHNUTIE ČÍTANÍ Z KONFERENCIE BISKUPOV SLOVENSKA
# ==========================================================

def _zapis_text_atomicky(cesta: Path | str, text: str, encoding: str = "utf-8") -> None:
    """Zapise text tak, aby povodny subor ostal zachovany pri zlyhani zapisu."""
    cesta = Path(cesta)
    cesta.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    fd, temp_str = tempfile.mkstemp(
        dir=str(cesta.parent),
        prefix=f".{cesta.name}.",
        suffix=".tmp",
    )
    temp_path = Path(temp_str)

    try:
        with os.fdopen(fd, "w", encoding=encoding, errors="strict") as tf:
            tf.write(text)
            tf.flush()
            os.fsync(tf.fileno())

        os.replace(str(temp_path), str(cesta))
        temp_path = None
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception as e:
                log_exception("_zapis_text_atomicky: nepodarilo sa odstranit docasny subor", e)


REFRENY_MESIACE_SK = {
    1: "JANUÁR", 2: "FEBRUÁR", 3: "MAREC", 4: "APRÍL",
    5: "MÁJ", 6: "JÚN", 7: "JÚL", 8: "AUGUST",
    9: "SEPTEMBER", 10: "OKTÓBER", 11: "NOVEMBER", 12: "DECEMBER",
}

REFRENY_MESIACE_SUBORY = {
    1: "1L", 2: "2L", 3: "3L", 4: "4L",
    5: "5L", 6: "6L", 7: "7L", 8: "8L",
    9: "9L", 10: "10L", 11: "11L", 12: "12L",
}

CEZROCNE_TYZDNE_ROK_MIN = 2000
CEZROCNE_TYZDNE_ROK_MAX = 2100
CEZROCNE_NEDIELNE_CYKLY = ("A", "B", "C")
CEZROCNE_DNI_TYZDNA = {
    1: 0,  # pondelok
    2: 1,  # utorok
    3: 2,  # streda
    4: 3,  # štvrtok
    5: 4,  # piatok
    6: 5,  # sobota
}

REFRENY_DELAY_S = 1.0
LC_KBS_REFRENY_MAX_POKUSOV = 3
LC_KBS_REFRENY_RETRY_DELAY_S = 1.5
LC_KBS_DOCASNE_HTTP_STATUSY = {429, 500, 502, 503, 504}

LC_KBS_USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
]

def _validuj_rok_pre_gui(hodnota: object) -> int:
    try:
        rok = int(str(hodnota).strip())
    except Exception:
        raise ValueError(f"Rok musí byť celé číslo, zadané: {hodnota!r}")
    _over_gregoriansky_rok(rok)
    return rok

def zisti_vlastnosti_roku(rok: int) -> dict:
    try:
        rok = _validuj_rok_pre_gui(rok)
    except (ValueError, TypeError) as e:
        return {"chyba": str(e), "rozsah": f"{GREGORIANSKY_MIN_ROK}-{GREGORIANSKY_MAX_ROK}"}
    try:
        vianocny_den = date(rok, 12, 25).weekday()
        return {"rok": rok, "vianocny_den": vianocny_den}
    except ValueError as e:
        return {"chyba": f"Zlyhalo spracovanie dátumu: {e}"}


def _vyber_user_agent() -> str:
    try:
        base = random.choice(LC_KBS_USER_AGENTS)
    except Exception:
        base = LC_KBS_USER_AGENTS[0]
    return f"{base} Kinak/{KINAK_VERSION}"

def _vytvor_lc_kbs_session() -> Any:
    if requests is None:
        return None
    try:
        session = requests.Session()
    except Exception:
        return None
    if HTTPAdapter is not None and Retry is not None:
        try:
            retry = Retry(
                total=LC_KBS_REFRENY_MAX_POKUSOV,
                connect=LC_KBS_REFRENY_MAX_POKUSOV,
                read=LC_KBS_REFRENY_MAX_POKUSOV,
                backoff_factor=LC_KBS_REFRENY_RETRY_DELAY_S,
                status_forcelist=tuple(LC_KBS_DOCASNE_HTTP_STATUSY),
                allowed_methods=frozenset(["GET", "HEAD"]),
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
        except Exception:
            pass
    return session



def _lc_kbs_headers(ucel: str = "") -> dict:
    suffix = f" {ucel}" if ucel else ""
    ua = _vyber_user_agent()
    if suffix and suffix not in ua:
        ua = f"{ua}{suffix}"
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "sk-SK,sk;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }


def _stiahni_lc_kbs_soup(datum: date, timeout: tuple[int, int] = (5, 20)) -> Any | None:
    """
    Stiahne a naparsuje stránku lc.kbs.sk pre daný dátum.

    Retry na úrovni HTTPAdapter/urllib3.Retry (nastavený v _vytvor_lc_kbs_session)
    rieši nižšie-úrovňové zlyhania spojenia; táto slučka navyše pokrýva prípady,
    kde spojenie prebehlo, ale server vrátil dočasnú chybu (LC_KBS_DOCASNE_HTTP_STATUSY),
    alebo požiadavka zlyhala inak (timeout, výpadok siete, prerušené spojenie) –
    s osobitným logovaním pre každý typ chyby, aby bolo pri diagnostike jasné,
    kde presne sťahovanie zlyhalo.
    """
    _over_gregoriansky_datum(datum)
    if chybaju_kniznice_pre_stahovanie():
        return None

    requests_module = requests
    beautiful_soup = BeautifulSoup
    assert requests_module is not None and beautiful_soup is not None

    datum_str = datum.strftime("%Y-%m-%d")
    session = _vytvor_lc_kbs_session()

    request_exception_type = getattr(requests_module, "RequestException", Exception)
    http_error_type = getattr(requests_module, "HTTPError", request_exception_type)
    timeout_type = getattr(requests_module, "Timeout", request_exception_type)
    connection_error_type = getattr(requests_module, "ConnectionError", request_exception_type)

    try:
        for pokus in range(1, LC_KBS_REFRENY_MAX_POKUSOV + 1):
            url = f"https://lc.kbs.sk/?den={datum_str}&_={int(time.time())}"
            try:
                headers = _lc_kbs_headers("refreny-zalmov")
                resp = session.get(url, headers=headers, timeout=timeout) if session else requests_module.get(url, headers=headers, timeout=timeout)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or "utf-8"
                if not resp.encoding or resp.encoding.lower() in ("iso-8859-1", "latin-1"):
                    resp.encoding = "utf-8"
                return beautiful_soup(resp.text, "html.parser")

            except http_error_type as e:
                status_code = getattr(getattr(e, "response", None), "status_code", None)
                if status_code in LC_KBS_DOCASNE_HTTP_STATUSY and pokus < LC_KBS_REFRENY_MAX_POKUSOV:
                    log_debug(
                        f"[LC-KBS] Dátum {datum_str}: HTTP {status_code}, "
                        f"skúšam znova ({pokus}/{LC_KBS_REFRENY_MAX_POKUSOV})."
                    )
                    time.sleep(LC_KBS_REFRENY_RETRY_DELAY_S * pokus)
                    continue

                log_info(
                    f"[LC-KBS] Dátum {datum_str}: server vrátil HTTP {status_code or 'chyba'} "
                    f"po {pokus} pokusoch, refrén preskakujem."
                )
                return None

            except (timeout_type, connection_error_type) as e:
                if pokus < LC_KBS_REFRENY_MAX_POKUSOV:
                    log_debug(
                        f"[LC-KBS] Dátum {datum_str}: sieťová chyba ({e}), "
                        f"skúšam znova ({pokus}/{LC_KBS_REFRENY_MAX_POKUSOV})."
                    )
                    time.sleep(LC_KBS_REFRENY_RETRY_DELAY_S * pokus)
                    continue

                log_info(
                    f"[LC-KBS] Dátum {datum_str}: sieťová chyba aj po "
                    f"{LC_KBS_REFRENY_MAX_POKUSOV} pokusoch, refrén preskakujem."
                )
                return None

            except request_exception_type as e:
                # Sem padá napr. ChunkedEncodingError ("Response ended prematurely")
                # – ide o prerušenie spojenia, oplatí sa znova skúsiť.
                if pokus < LC_KBS_REFRENY_MAX_POKUSOV:
                    log_debug(
                        f"[LC-KBS] Dátum {datum_str}: požiadavka zlyhala ({e}), "
                        f"skúšam znova ({pokus}/{LC_KBS_REFRENY_MAX_POKUSOV})."
                    )
                    time.sleep(LC_KBS_REFRENY_RETRY_DELAY_S * pokus)
                    continue

                log_info(f"[LC-KBS] Dátum {datum_str}: požiadavka zlyhala ({e}), refrén preskakujem.")
                return None

        return None

    except Exception as e:
        # Neočakávaná (nesieťová) chyba – nemá zmysel ju opakovať.
        log_exception(f"[LC-KBS] Neočakávaná chyba pri dátume {datum_str}", e)
        return None

    finally:
        # Session sa zatvára VŽDY (úspech aj zlyhanie) – predtým sa pri
        # úspešnom sťahovaní na prvý pokus session nezatvárala vôbec.
        if session is not None:
            try:
                session.close()
            except Exception:
                pass


def _vycisti_refren_zalmu_lc_kbs(text: str) -> str:
    t = html.unescape(text or "").strip()
    t = re.sub(r"^[Rr]\s*[.:]\s*", "", t).strip()
    t = t.lstrip(":. ").strip()
    t = re.sub(r":(?!\s)", ": ", t)
    t = re.sub(r"\s*alebo\s+[Aa]leluja\.?\s*$", "", t, flags=re.IGNORECASE).strip()
    return _vycisti_text_lc_kbs(t)


def _extrahuj_refreny_zalmov_lc_kbs(soup) -> list[str]:
    """Extrahuje všetky refrény responzóriových žalmov zo stránky lc.kbs.sk."""
    if not soup:
        return []

    refreny = []
    seen = set()

    def pridaj(text: str):
        cisty = _vycisti_refren_zalmu_lc_kbs(text)
        if not cisty or len(cisty) < 5:
            return
        if cisty not in seen:
            refreny.append(cisty)
            seen.add(cisty)

    ignorujeme_zalm = False
    elementy = soup.find_all(["p", "h3", "h4", "h5", "strong", "b", "li", "em", "i"])

    for elem in elementy:
        text = elem.get_text(" ", strip=True)
        if len(text) < 2:
            continue

        low = text.lower()

        if text.strip().lower().startswith(("r.", "r:")):
            pridaj(text)
            if ignorujeme_zalm:
                continue

        if ignorujeme_zalm:
            normalized = normalize_diacritics(low)
            nadpisy = (
                "citanie z", "z listu", "zo skutkov", "evanjelium",
                "zaciatok", "prve citanie", "druhe citanie", "z knihy",
            )
            if any(normalized.startswith(nadpis) for nadpis in nadpisy):
                ignorujeme_zalm = False
            else:
                continue

        if normalize_diacritics(low).startswith(("responzoriovy zalm", "zalm")):
            ignorujeme_zalm = True
            continue

    if not refreny:
        try:
            for riadok in soup.get_text("\n").split("\n"):
                r = riadok.strip()
                if r.lower().startswith(("r.", "r:")) and len(r) > 5:
                    pridaj(r)
        except Exception as e:
            log_exception("[LC-KBS] Fallback extrakcia refrénu zlyhala", e)

    return refreny


def _vsetky_dni_roka(rok: int) -> list[date]:
    d = date(rok, 1, 1)
    end = date(rok, 12, 31)
    dni = []
    while d <= end:
        dni.append(d)
        d += timedelta(days=1)
    return dni


def _roky_podla_blizkosti(preferovany_rok: int, parita: int | None = None) -> list[int]:
    roky = range(CEZROCNE_TYZDNE_ROK_MIN, CEZROCNE_TYZDNE_ROK_MAX + 1)
    if parita is not None:
        roky = [rok for rok in roky if rok % 2 == parita]
    return sorted(roky, key=lambda rok: (abs(rok - preferovany_rok), rok))


def _najdi_datum_cezrocnej_nedele(tyzden: int, cyklus: str, preferovany_rok: int) -> date | None:
    """
    Nájde reprezentatívny dátum nedele pre daný cezročný týždeň a cyklus A/B/C.

    1. cezročná nedeľa sa liturgicky prekrýva s Krstom Pána; preto pre 1C
    sťahujeme nedeľné refrény zo sviatku Krstu Pána.
    """
    cyklus = cyklus.upper()
    for rok in _roky_podla_blizkosti(preferovany_rok):
        if tyzden == 1:
            datum = krst_krista_pana(rok)
            if vypocitaj_liturgicky_rok(datum) == cyklus:
                return datum
            continue

        for datum in _vsetky_dni_roka(rok):
            if (
                datum.weekday() == 6
                and vypocitaj_liturgicky_rok(datum) == cyklus
                and vypocitaj_kod_liturgickej_casti(datum) == f"{tyzden}C"
            ):
                return datum
    return None


def _najdi_datum_cezrocneho_vs_dna(tyzden: int, den_index: int, parita: int, preferovany_rok: int) -> date | None:
    """Nájde reprezentatívny feriálny dátum pre týždeň, deň Po-So a párnosť roka."""
    for rok in _roky_podla_blizkosti(preferovany_rok, parita=parita):
        for datum in _vsetky_dni_roka(rok):
            if datum.weekday() != den_index:
                continue
            if vypocitaj_kod_liturgickej_casti(datum) == f"{tyzden}C":
                return datum
    return None


def _stiahni_prvy_refren_lc_kbs(datum: date) -> str | None:
    soup = _stiahni_lc_kbs_soup(datum)
    refreny = _extrahuj_refreny_zalmov_lc_kbs(soup)
    return refreny[0] if refreny else None


def stiahni_cezrocne_tyzdenne_refreny_pre_rok(rok: int, vystup_priecinok: Path, progress_callback=None) -> dict:
    ctx_or = _priprav_kontext_alebo_vrat_chybu(
        rok, vystup_priecinok, "backup_cezrocne", progress_callback,
        "[LC-KBS] Sťahovanie cezročných týždňov preskočené: chýbajú knižnice."
    )
    if isinstance(ctx_or, dict):
        return ctx_or
    ctx: _RefrenyKontext = ctx_or

    parita = 2 if rok % 2 == 0 else 1
    parita_roka = rok % 2
    parita_text = "párny" if parita == 2 else "nepárny"
    kody = [f"{t}C{parita}" for t in range(1, 35)]

    ctx.zalohuj_kody(kody)
    celkovo = 34 * (len(CEZROCNE_NEDIELNE_CYKLY) + len(CEZROCNE_DNI_TYZDNA))
    spracuj_slot = ctx.vytvor_spracuj_slot(celkovo, pocitaj_datumy_nezistene=True)

    ctx.progress(f"Začínam sťahovanie cezročných týždňov pre rok {rok}.", 0, celkovo)

    try:
        for tyzden in range(1, 35):
            ctx.aktualny_subor = f"{tyzden}C{parita}"
            bloky = [f"{tyzden}. TÝŽDEŇ CEZROČNÉHO OBDOBIA ({parita_text} rok)"]
            for cyklus in CEZROCNE_NEDIELNE_CYKLY:
                datum = _najdi_datum_cezrocnej_nedele(tyzden, cyklus, rok)
                bloky.append(f"{cyklus}: {spracuj_slot(f'{tyzden}C{parita} {cyklus}', datum)}")
            for cislo_dna, den_index in CEZROCNE_DNI_TYZDNA.items():
                datum = _najdi_datum_cezrocneho_vs_dna(tyzden, den_index, parita_roka, rok)
                bloky.append(f"{cislo_dna}. {spracuj_slot(f'{tyzden}C{parita} deň {cislo_dna}', datum)}")
            ctx.zapis_bloky(ctx.aktualny_subor, bloky)
    except _PredcasneUkoncenieStahovania as e:
        log_info(f"[LC-KBS] Cezročné týždenné refrény {rok}: predčasne ukončené – {e}")

    log_info(
        f"[LC-KBS] Cezročné týždenné refrény {rok} – súhrn: "
        f"spracovaných položiek {ctx.pocitadlo.aktualny_slot}/{celkovo}, chyby {ctx.pocitadlo.chyby}"
        + (f" ({', '.join(ctx.chybne_kody)})" if ctx.chybne_kody else "") + "."
    )
    ctx.progress(f"Hotovo. Spracovaných položiek: {ctx.pocitadlo.aktualny_slot}, chyby: {ctx.pocitadlo.chyby}.", ctx.pocitadlo.aktualny_slot, celkovo)

    return {
        "uspech": (ctx.pocitadlo.aktualny_slot - ctx.pocitadlo.chyby) > 0,
        "celkovo": ctx.pocitadlo.aktualny_slot,
        "chyby": ctx.pocitadlo.chyby,
        "chybne_kody": ctx.chybne_kody,
        "datumy_nezistene": ctx.datumy_nezistene,
        "subory": ctx.zapisane,
        "zaloha": ctx.backup.retazec_alebo_none,
        "parita": parita,
    }


def _najdi_datum_nedele_v_obdobi(
    tyzden: int,
    cyklus: str,
    preferovany_rok: int,
    zaciatok_obdobia_fn: Callable[[int], date],
) -> "date | None":
    """
    Spoločná logika pre _najdi_datum_postnej_nedele, _najdi_datum_veľkonocnej_nedele
    a _najdi_datum_adventnej_nedele: nájde nedeľu n-tého týždňa liturgického obdobia
    (počítaného od zaciatok_obdobia_fn(rok)) v požadovanom cykle A/B/C.

    Ak by bolo pri budúcej úprave treba zmeniť túto logiku, stačí upraviť len tu –
    predtým mala každá z troch funkcií vlastnú (identickú) kópiu tohto cyklu.
    """
    cyklus = cyklus.upper()
    for rok in _roky_podla_blizkosti(preferovany_rok):
        zaciatok = zaciatok_obdobia_fn(rok)
        kandidat = zaciatok + timedelta(weeks=tyzden - 1)
        if kandidat.weekday() == 6 and vypocitaj_liturgicky_rok(kandidat) == cyklus:
            return kandidat
    return None


def _najdi_datum_vs_dna_v_obdobi(
    tyzden: int,
    den_index: int,
    preferovany_rok: int,
    zaciatok_obdobia_fn: Callable[[int], date],
    je_spravny_kod_fn: Callable[[str], bool],
) -> "date | None":
    """
    Spoločná logika pre _najdi_datum_postneho_vs_dna, _najdi_datum_veľkonocneho_vs_dna
    a _najdi_datum_adventneho_vs_dna: nájde feriálny deň (Po=0..So=5) v n-tom týždni
    liturgického obdobia a overí, že vypočítaný liturgický kód zodpovedá očakávanému
    (predikát `je_spravny_kod_fn`, lebo veľkonočný variant má výnimku pre NP).
    """
    for rok in _roky_podla_blizkosti(preferovany_rok):
        zaciatok = zaciatok_obdobia_fn(rok)
        zaciatok_tyzdna = zaciatok + timedelta(weeks=tyzden - 1)
        kandidat = zaciatok_tyzdna + timedelta(days=den_index + 1)
        kod = vypocitaj_kod_liturgickej_casti(kandidat)
        if je_spravny_kod_fn(kod):
            return kandidat
    return None


def _zaciatok_postneho_obdobia(rok: int) -> date:
    """Prvá pôstna nedeľa (Veľká noc – 42 dní), spoločný začiatok pre pôstne funkcie."""
    return velkonocna_nedela(rok) - timedelta(days=42)


def _najdi_datum_postnej_nedele(tyzden: int, cyklus: str, preferovany_rok: int) -> "date | None":
    """Nájde reprezentatívny dátum pôstnej nedele pre daný týždeň (1–5) a cyklus A/B/C."""
    return _najdi_datum_nedele_v_obdobi(
        tyzden, cyklus, preferovany_rok, zaciatok_obdobia_fn=_zaciatok_postneho_obdobia
    )


def _najdi_datum_postneho_vs_dna(tyzden: int, den_index: int, preferovany_rok: int) -> "date | None":
    """Nájde reprezentatívny feriálny dátum pôstneho týždňa (1–5) a dňa (Po=0..So=5)."""
    ocakavany = f"{tyzden}P"
    return _najdi_datum_vs_dna_v_obdobi(
        tyzden, den_index, preferovany_rok,
        zaciatok_obdobia_fn=_zaciatok_postneho_obdobia,
        je_spravny_kod_fn=lambda kod: kod == ocakavany,
    )


def _najdi_datum_pps_dna(posun_dni: int, preferovany_rok: int) -> "date | None":
    """
    Nájde reprezentatívny dátum dňa v týždni Popolcovej stredy (kód PPS),
    t. j. štvrtok (posun_dni=1), piatok (posun_dni=2) alebo sobota (posun_dni=3)
    po Popolcovej strede, pred 1. pôstnou nedeľou.
    """
    for rok in _roky_podla_blizkosti(preferovany_rok):
        velka_noc = velkonocna_nedela(rok)
        popolcova_streda = velka_noc - timedelta(days=46)
        kandidat = popolcova_streda + timedelta(days=posun_dni)
        if vypocitaj_kod_liturgickej_casti(kandidat) == "PPS":
            return kandidat
    return None



def _najdi_datum_veľkonocnej_nedele(tyzden: int, cyklus: str, preferovany_rok: int) -> "date | None":
    """Nájde reprezentatívny dátum veľkonočnej nedele pre daný týždeň (1–7) a cyklus A/B/C."""
    return _najdi_datum_nedele_v_obdobi(
        tyzden, cyklus, preferovany_rok, zaciatok_obdobia_fn=velkonocna_nedela
    )


def _najdi_datum_veľkonocneho_vs_dna(tyzden: int, den_index: int, preferovany_rok: int) -> "date | None":
    """Nájde feriálny dátum veľkonočného týždňa (2–7) a dňa (Po=0..So=5)."""
    ocakavany = "VOKT" if tyzden == 1 else f"{tyzden}VN"
    return _najdi_datum_vs_dna_v_obdobi(
        tyzden, den_index, preferovany_rok,
        zaciatok_obdobia_fn=velkonocna_nedela,
        je_spravny_kod_fn=lambda kod: kod == ocakavany or (tyzden == 6 and den_index == 3 and kod == "NP"),
    )


def _najdi_datum_adventnej_nedele(tyzden: int, cyklus: str, preferovany_rok: int) -> "date | None":
    """Nájde reprezentatívny dátum adventnej nedele pre daný týždeň (1–4) a cyklus A/B/C."""
    return _najdi_datum_nedele_v_obdobi(
        tyzden, cyklus, preferovany_rok, zaciatok_obdobia_fn=prva_adventna_nedela
    )


def _najdi_datum_adventneho_vs_dna(tyzden: int, den_index: int, preferovany_rok: int) -> "date | None":
    """Nájde feriálny dátum adventného týždňa (1–4) a dňa (Po=0..So=5)."""
    ocakavany = f"{tyzden}AD"
    return _najdi_datum_vs_dna_v_obdobi(
        tyzden, den_index, preferovany_rok,
        zaciatok_obdobia_fn=prva_adventna_nedela,
        je_spravny_kod_fn=lambda kod: kod == ocakavany,
    )


# Hlavičky pre pôstne súbory
_POSTNE_NAZVY = {
    1: "PRVÝ PÔSTNY TÝŽDEŇ",
    2: "DRUHÝ PÔSTNY TÝŽDEŇ",
    3: "TRETÍ PÔSTNY TÝŽDEŇ",
    4: "ŠTVRTÝ PÔSTNY TÝŽDEŇ (NEDEĽA LAETARE)",
    5: "PIATY PÔSTNY TÝŽDEŇ (SMRTNÁ NEDEĽA)",
}

# Hlavičky pre veľkonočné súbory
_VEĽKONOCNE_NAZVY = {
    1: "VEĽKONOČNÁ NEDEĽA (VEĽKONOČNÁ OKTÁVA)",
    2: "DRUHÁ VEĽKONOČNÁ NEDEĽA (NEDEĽA BOŽIEHO MILOSRDENSTVA)",
    3: "TRETIA VEĽKONOČNÁ NEDEĽA",
    4: "ŠTVRTÁ VEĽKONOČNÁ NEDEĽA",
    5: "PIATA VEĽKONOČNÁ NEDEĽA",
    6: "ŠIESTA VEĽKONOČNÁ NEDEĽA",
    7: "SIEDMA VEĽKONOČNÁ NEDEĽA",
}

# Hlavičky pre adventné súbory
_ADVENTNE_NAZVY = {
    1: "PRVÝ ADVENTNÝ TÝŽDEŇ",
    2: "DRUHÝ ADVENTNÝ TÝŽDEŇ",
    3: "TRETÍ ADVENTNÝ TÝŽDEŇ (NEDEĽA GAUDETE)",
    4: "ŠTVRTÝ ADVENTNÝ TÝŽDEŇ",
}


def stiahni_liturgicke_tyzdne_refreny(rok: int, vystup_priecinok: Path, progress_callback=None) -> dict:
    ctx_or = _priprav_kontext_alebo_vrat_chybu(
        rok, vystup_priecinok, "backup_lit_tyzdne", progress_callback,
        "[LC-KBS] Sťahovanie liturgických týždňov preskočené: chýbajú knižnice."
    )
    if isinstance(ctx_or, dict):
        return ctx_or
    ctx: _RefrenyKontext = ctx_or

    kody = [f"{t}P" for t in range(1, 6)] + ["VT"] + [f"{t}VN" for t in range(1, 8)] + [f"{t}AD" for t in range(1, 5)]
    ctx.zalohuj_kody(kody)

    celkovo = 5 * (3 + 6) + 6 + 7 * (3 + 6) + 4 * (3 + 6)
    spracuj_slot = ctx.vytvor_spracuj_slot(celkovo)
    ctx.progress(f"Začínam sťahovanie liturgických týždňov pre rok {rok}.", 0, celkovo)

    try:
        # Pôstne
        for tyzden in range(1, 6):
            ctx.aktualny_subor = f"{tyzden}P"
            bloky = [_POSTNE_NAZVY[tyzden]]
            for cyklus in CEZROCNE_NEDIELNE_CYKLY:
                datum = _najdi_datum_postnej_nedele(tyzden, cyklus, rok)
                bloky.append(f"{cyklus}: {spracuj_slot(f'{tyzden}P {cyklus}', datum)}")
            for cislo_dna, den_index in CEZROCNE_DNI_TYZDNA.items():
                datum = _najdi_datum_postneho_vs_dna(tyzden, den_index, rok)
                bloky.append(f"{cislo_dna}. {spracuj_slot(f'{tyzden}P deň {cislo_dna}', datum)}")
            ctx.zapis_bloky(ctx.aktualny_subor, bloky)
            log_info(f"[LC-KBS] {tyzden}P ({rok}): uložené.")

        # Veľký týždeň – špeciálne (viac refrénov na deň)
        ctx.aktualny_subor = "VT"
        nedela_kvetna = velkonocna_nedela(rok) - timedelta(days=7)
        pondelok_vt = velkonocna_nedela(rok) - timedelta(days=6)
        utorok_vt = velkonocna_nedela(rok) - timedelta(days=5)
        streda_vt = velkonocna_nedela(rok) - timedelta(days=4)
        stvrtok_vt = velkonocna_nedela(rok) - timedelta(days=3)
        piatok_vt = velkonocna_nedela(rok) - timedelta(days=2)
        polozky_vt = [
            (nedela_kvetna, "PALMOVÁ (KVETNÁ) NEDEĽA – NEDEĽA UTRPENIA PÁNA"),
            (pondelok_vt, "PONDELOK VEĽKÉHO TÝŽDŇA"),
            (utorok_vt, "UTOROK VEĽKÉHO TÝŽDŇA"),
            (streda_vt, "STREDA VEĽKÉHO TÝŽDŇA"),
            (stvrtok_vt, "ZELENÝ ŠTVRTOK"),
            (piatok_vt, "VEĽKÝ PIATOK"),
        ]
        bloky_vt = ["VEĽKÝ TÝŽDEŇ (SVÄTÝ TÝŽDEŇ)"]
        for datum_vt, nazov_vt in polozky_vt:
            ctx.pocitadlo.aktualny_slot += 1
            ctx.progress(f"VT – {nazov_vt}: sťahujem {datum_vt.strftime('%d.%m.%Y')}...", ctx.pocitadlo.aktualny_slot, celkovo)
            soup_vt = _stiahni_lc_kbs_soup(datum_vt)
            refreny_vt = _extrahuj_refreny_zalmov_lc_kbs(soup_vt)
            time.sleep(REFRENY_DELAY_S)
            ctx.zaznamenaj_vysledok(bool(refreny_vt))
            if not refreny_vt:
                ctx.pocitadlo.chyby += 1
                bloky_vt.append(nazov_vt + "\n\n1. [refrén sa nepodarilo stiahnuť]")
                continue
            riadky = [f"1. {refreny_vt[0]}"] if len(refreny_vt) == 1 else [f"{i}. {r}" for i, r in enumerate(refreny_vt, start=1)]
            bloky_vt.append(nazov_vt + "\n\n" + "\n\n".join(riadky))
        ctx.zapis_bloky("VT", bloky_vt, oddelovac="\n\n\n")
        log_info(f"[LC-KBS] VT ({rok}): uložené.")

        # Veľkonočné
        for tyzden in range(1, 8):
            ctx.aktualny_subor = f"{tyzden}VN"
            bloky = [_VEĽKONOCNE_NAZVY[tyzden]]
            for cyklus in CEZROCNE_NEDIELNE_CYKLY:
                datum = _najdi_datum_veľkonocnej_nedele(tyzden, cyklus, rok)
                bloky.append(f"{cyklus}: {spracuj_slot(f'{tyzden}VN {cyklus}', datum)}")
            for cislo_dna, den_index in CEZROCNE_DNI_TYZDNA.items():
                datum = _najdi_datum_veľkonocneho_vs_dna(tyzden, den_index, rok)
                bloky.append(f"{cislo_dna}. {spracuj_slot(f'{tyzden}VN deň {cislo_dna}', datum)}")
            ctx.zapis_bloky(ctx.aktualny_subor, bloky)
            log_info(f"[LC-KBS] {tyzden}VN ({rok}): uložené.")

        # Adventné
        for tyzden in range(1, 5):
            ctx.aktualny_subor = f"{tyzden}AD"
            bloky = [_ADVENTNE_NAZVY[tyzden]]
            for cyklus in CEZROCNE_NEDIELNE_CYKLY:
                datum = _najdi_datum_adventnej_nedele(tyzden, cyklus, rok)
                bloky.append(f"{cyklus}: {spracuj_slot(f'{tyzden}AD {cyklus}', datum)}")
            for cislo_dna, den_index in CEZROCNE_DNI_TYZDNA.items():
                datum = _najdi_datum_adventneho_vs_dna(tyzden, den_index, rok)
                bloky.append(f"{cislo_dna}. {spracuj_slot(f'{tyzden}AD deň {cislo_dna}', datum)}")
            ctx.zapis_bloky(ctx.aktualny_subor, bloky)
    except _PredcasneUkoncenieStahovania as e:
        log_info(f"[LC-KBS] Liturgické týždne {rok}: predčasne ukončené – {e}")

    log_info(f"[LC-KBS] Liturgické týždne {rok} – súhrn: spracovaných {ctx.pocitadlo.aktualny_slot}/{celkovo}, chyby {ctx.pocitadlo.chyby}.")
    ctx.progress(f"Hotovo. Spracovaných položiek: {ctx.pocitadlo.aktualny_slot}, chyby: {ctx.pocitadlo.chyby}.", ctx.pocitadlo.aktualny_slot, celkovo)

    return {
        "uspech": (ctx.pocitadlo.aktualny_slot - ctx.pocitadlo.chyby) > 0,
        "celkovo": ctx.pocitadlo.aktualny_slot,
        "chyby": ctx.pocitadlo.chyby,
        "subory": ctx.zapisane,
        "zaloha": ctx.backup.retazec_alebo_none,
    }


class _PocitadloSlotov:
    """
    Malé mutovateľné počítadlo zdieľané medzi `spracuj_slot` (pozri
    `_vytvor_spracuj_slot`) a zvyškom volajúcej funkcie. Oboje potrebuje
    priebežne čítať aj zapisovať `aktualny_slot`/`chyby` počas behu –
    nielen vnútri `spracuj_slot`, ale aj v blokoch spracovaných manuálne
    (napr. Veľký týždeň, jednodenné slávenia).
    """
    __slots__ = ("aktualny_slot", "chyby")

    def __init__(self):
        self.aktualny_slot = 0
        self.chyby = 0


def _vytvor_spracuj_slot(pocitadlo, chybne_kody, aktualny_subor_getter, celkovo_slotov, progress_callback, na_vysledok=None):
    """
    Vytvorí funkciu spracuj_slot(label, datum) používanú pri sťahovaní
    jednotlivých dátumových "slotov" (nedele/férie) v
    `stiahni_postne_velkonocne_refreny` a `stiahni_adventne_vianocne_refreny`
    (predtým 2× bajtovo identická lokálna funkcia).

    - pocitadlo: zdieľaná `_PocitadloSlotov` inštancia.
    - chybne_kody: zdieľaný list, do ktorého sa (bez duplicít) pridávajú
      kódy súborov, pri ktorých nastala chyba.
    - aktualny_subor_getter: bezparametrová funkcia vracajúca kód práve
      spracovávaného súboru – volajúci ju typicky zadá ako
      `lambda: aktualny_subor`, keďže hodnota tejto premennej sa v jeho
      slučke priebežne mení pred každým novým týždňom/dňom.
    - celkovo_slotov, progress_callback: pozri `update_progress`.
    - na_vysledok: voliteľný callback(uspech: bool) – circuit breaker
      (pozri _RefrenyKontext.zaznamenaj_vysledok). Volá sa iba pri
      skutočnom sieťovom pokuse, nie keď `datum` nebolo vôbec nájdené
      (to je zlyhanie vyhľadávacej logiky, nie servera).
    """
    def spracuj_slot(label, datum):
        pocitadlo.aktualny_slot += 1
        aktualny_subor = aktualny_subor_getter()
        if datum is None:
            pocitadlo.chyby += 1
            if aktualny_subor and aktualny_subor not in chybne_kody:
                chybne_kody.append(aktualny_subor)
            update_progress(progress_callback, f"{label}: dátum sa nepodarilo nájsť.",
                             pocitadlo.aktualny_slot, celkovo_slotov)
            return "[dátum sa nepodarilo nájsť]"
        update_progress(progress_callback, f"{label}: sťahujem {datum.strftime('%d.%m.%Y')}...",
                         pocitadlo.aktualny_slot, celkovo_slotov)
        refren = _stiahni_prvy_refren_lc_kbs(datum)
        time.sleep(REFRENY_DELAY_S)
        if refren:
            if na_vysledok:
                na_vysledok(True)
            return refren
        pocitadlo.chyby += 1
        if aktualny_subor and aktualny_subor not in chybne_kody:
            chybne_kody.append(aktualny_subor)
        if na_vysledok:
            na_vysledok(False)
        return "[refrén sa nepodarilo stiahnuť]"

    return spracuj_slot


# ==========================================================
# KONSOLIDOVANÁ INFRAŠTRUKTÚRA PRE HROMADNÉ SŤAHOVANIE REFRÉNOV
# ==========================================================
# Deväť funkcií stiahni_*_pre_rok malo identickú kostru:
#   - kontrola knižníc
#   - mkdir vystup_priecinok
#   - backup priečinok + kopírovanie existujúcich .txt
#   - počítadlo slotov / chyby / preskočené / zapisane_subory
#   - spracuj_slot (progress + sleep + chybové hlásenie)
#   - zápis súboru cez _zapis_text_atomicky
#   - log_info súhrn + update_progress Hotovo + return dict
#
# Nasledujúce tri pomocné triedy/funkcie túto kostru zjednocujú,
# aby jednotlivé stiahni_* funkcie obsahovali už len svoju špecifickú
# logiku (aké kódy, ako nájsť dátum, ako poskladať bloky).
# Všetky pôvodné návratové kľúče zostávajú zachované pre GUI vrstvu.

class _BackupManager:
    """Spravuje backup priečinok pre hromadné sťahovanie."""

    def __init__(self, vystup_priecinok: Path, prefix: str, rok: int):
        self.vystup = Path(vystup_priecinok)
        self.vystup.mkdir(parents=True, exist_ok=True)
        self.cesta = self.vystup / f"{prefix}_{rok}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._vytvorena = False

    def zalohuj(self, kod: str) -> None:
        povodny = self.vystup / f"{kod}.txt"
        if povodny.exists():
            self.cesta.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(povodny, self.cesta / povodny.name)
            except Exception as e:
                log_exception(f"_BackupManager.zalohuj {kod}", e)
            else:
                self._vytvorena = True

    def zalohuj_zoznam(self, kody) -> None:
        for k in kody:
            self.zalohuj(k)

    @property
    def retazec_alebo_none(self) -> str | None:
        return str(self.cesta) if self._vytvorena else None


class _PredcasneUkoncenieStahovania(Exception):
    """
    Interná výnimka (circuit breaker): vyhodí sa, keď za sebou zlyhá príliš
    veľa sťahovaní jednotlivých dátumov (server zjavne neodpovedá).

    Bez tejto poistky by veľké sťahovanie (napr. cezročné týždne = ~300
    samostatných dátumov) muselo pri výpadku lc.kbs.sk nechať KAŽDÝ jeden
    dátum nezávisle vyčerpať celý retry cyklus (3 pokusy × timeout (5,20)s
    + rastúce oneskorenia ≈ 80 s na dátum) – teoreticky až rádovo hodiny na
    jedno kliknutie. Táto výnimka preruší zvyšok slučky hneď po niekoľkých
    zlyhaniach za sebou namiesto márneho opakovania toho istého zlyhania.
    """
    pass


MAX_PO_SEBE_ZLYHANI_STAHOVANIA = 5


class _RefrenyKontext:
    """
    Zdieľaný kontext pre všetky hromadné sťahovania refrénov.
    Drží počítadlá, zoznamy chýb, backup manažér a progress callback.
    """

    def __init__(self, rok: int, vystup_priecinok: Path, backup_prefix: str, progress_callback=None):
        self.rok = rok
        self.vystup = Path(vystup_priecinok)
        self.vystup.mkdir(parents=True, exist_ok=True)
        self.backup = _BackupManager(self.vystup, backup_prefix, rok)
        self.progress_callback = progress_callback

        self.pocitadlo = _PocitadloSlotov()
        self.chybne_kody: list[str] = []
        self.preskocene_kody: list[str] = []
        self.zapisane: list[str] = []
        self.datumy_nezistene = 0
        self.preskocenych = 0
        self._aktualny_subor = ""

        # Circuit breaker proti kaskádovému zlyhaniu pri výpadku servera.
        self.po_sebe_zlyhani = 0
        self.predcasne_ukoncene = False

    @property
    def aktualny_subor(self) -> str:
        return self._aktualny_subor

    @aktualny_subor.setter
    def aktualny_subor(self, hodnota: str) -> None:
        self._aktualny_subor = hodnota

    def zalohuj_kody(self, kody) -> None:
        self.backup.zalohuj_zoznam(kody)

    def zaznamenaj_vysledok(self, uspech: bool) -> None:
        """
        Zaznamená výsledok jedného sťahovacieho pokusu (jeden konkrétny
        dátum). Ak zlyhá MAX_PO_SEBE_ZLYHANI_STAHOVANIA-krát za sebou (bez
        prerušenia úspechom), vyhodí _PredcasneUkoncenieStahovania – server
        je pravdepodobne nedostupný a ďalšie márne skúšanie nemá zmysel.
        """
        if uspech:
            self.po_sebe_zlyhani = 0
            return
        self.po_sebe_zlyhani += 1
        if self.po_sebe_zlyhani >= MAX_PO_SEBE_ZLYHANI_STAHOVANIA:
            self.predcasne_ukoncene = True
            raise _PredcasneUkoncenieStahovania(
                f"{self.po_sebe_zlyhani} sťahovaní za sebou zlyhalo – server pravdepodobne neodpovedá."
            )

    def vytvor_spracuj_slot(self, celkovo_slotov: int, pocitaj_datumy_nezistene: bool = False):
        """Vráti spracuj_slot uzavretý nad týmto kontextom."""
        zaklad = _vytvor_spracuj_slot(
            self.pocitadlo,
            self.chybne_kody,
            lambda: self._aktualny_subor,
            celkovo_slotov,
            self.progress_callback,
            na_vysledok=self.zaznamenaj_vysledok,
        )

        if not pocitaj_datumy_nezistene:
            return zaklad

        def wrapper(label, datum):
            if datum is None:
                self.datumy_nezistene += 1
            return zaklad(label, datum)

        return wrapper

    def zapis_bloky(self, kod: str, bloky: list[str], oddelovac: str = "\n\n") -> Path:
        """Zapíše bloky do {kod}.txt a eviduje súbor."""
        cesta = self.vystup / f"{kod}.txt"
        obsah = "\n" + oddelovac.join(bloky) + "\n"
        _zapis_text_atomicky(cesta, obsah, encoding="utf-8")
        self.zapisane.append(str(cesta))
        return cesta

    def zapis_obsah(self, kod: str, obsah: str) -> Path:
        cesta = self.vystup / f"{kod}.txt"
        _zapis_text_atomicky(cesta, obsah, encoding="utf-8")
        self.zapisane.append(str(cesta))
        return cesta

    def progress(self, sprava: str, aktualne: int, celkovo: int) -> None:
        update_progress(self.progress_callback, sprava, aktualne, celkovo)


def _priprav_kontext_alebo_vrat_chybu(rok: int, vystup_priecinok: Path, backup_prefix: str, progress_callback, log_sprava: str) -> _RefrenyKontext | dict:
    """Spoločný vstupný bod: kontrola knižníc + vytvorenie kontextu. Pri chybe vráti dict."""
    if chybaju_kniznice_pre_stahovanie():
        log_info(log_sprava)
        return {"uspech": False, "celkovo": 0, "chyby": 0, "subory": [], "zaloha": None}
    return _RefrenyKontext(rok, vystup_priecinok, backup_prefix, progress_callback)


def stiahni_postne_velkonocne_refreny(rok: int, vystup_priecinok: Path, progress_callback=None) -> dict:
    ctx_or = _priprav_kontext_alebo_vrat_chybu(
        rok, vystup_priecinok, "backup_postne_velkonocne", progress_callback,
        "[LC-KBS] Sťahovanie pôstnych/veľkonočných týždňov preskočené: chýbajú knižnice."
    )
    if isinstance(ctx_or, dict):
        return ctx_or
    ctx: _RefrenyKontext = ctx_or

    vsetky_kody = [f"{t}P" for t in range(1, 6)] + ["VT"] + [f"{t}VN" for t in range(1, 8)]
    JEDNODENNE = [
        ("ZV", "Zvestovanie Pána"),
        ("ZST", "Zelený štvrtok"),
        ("VP", "Veľký piatok"),
        ("VG", "Veľkonočná vigília"),
        ("VPON", "Pondelok vo Veľkonočnej oktáve"),
        ("NP", "Nanebovstúpenie Pána"),
    ]
    ctx.zalohuj_kody(vsetky_kody + ["PS"] + [k for k, _ in JEDNODENNE])

    celkovo = 5 * (3 + 6) + 6 + 7 * (3 + 6) + 4 + len(JEDNODENNE)
    spracuj_slot = ctx.vytvor_spracuj_slot(celkovo)
    ctx.progress(f"Začínam sťahovanie pôstnych a veľkonočných týždňov pre rok {rok}.", 0, celkovo)

    try:
        for tyzden in range(1, 6):
            ctx.aktualny_subor = f"{tyzden}P"
            bloky = [_POSTNE_NAZVY[tyzden]]
            for cyklus in CEZROCNE_NEDIELNE_CYKLY:
                datum = _najdi_datum_postnej_nedele(tyzden, cyklus, rok)
                bloky.append(f"{cyklus}: {spracuj_slot(f'{tyzden}P {cyklus}', datum)}")
            for cislo_dna, den_index in CEZROCNE_DNI_TYZDNA.items():
                datum = _najdi_datum_postneho_vs_dna(tyzden, den_index, rok)
                bloky.append(f"{cislo_dna}. {spracuj_slot(f'{tyzden}P deň {cislo_dna}', datum)}")
            ctx.zapis_bloky(ctx.aktualny_subor, bloky)
            log_info(f"[LC-KBS] {tyzden}P ({rok}): uložené.")

        # VT
        ctx.aktualny_subor = "VT"
        nedela_kvetna = velkonocna_nedela(rok) - timedelta(days=7)
        pondelok_vt = velkonocna_nedela(rok) - timedelta(days=6)
        utorok_vt = velkonocna_nedela(rok) - timedelta(days=5)
        streda_vt = velkonocna_nedela(rok) - timedelta(days=4)
        stvrtok_vt = velkonocna_nedela(rok) - timedelta(days=3)
        piatok_vt = velkonocna_nedela(rok) - timedelta(days=2)
        polozky_vt = [
            (nedela_kvetna, "PALMOVÁ (KVETNÁ) NEDEĽA – NEDEĽA UTRPENIA PÁNA"),
            (pondelok_vt, "PONDELOK VEĽKÉHO TÝŽDŇA"),
            (utorok_vt, "UTOROK VEĽKÉHO TÝŽDŇA"),
            (streda_vt, "STREDA VEĽKÉHO TÝŽDŇA"),
            (stvrtok_vt, "ŠTVRTOK VEĽKÉHO TÝŽDŇA – ZELENÝ ŠTVRTOK"),
            (piatok_vt, "VEĽKÝ PIATOK"),
        ]
        bloky_vt = ["VEĽKÝ TÝŽDEŇ (SVÄTÝ TÝŽDEŇ)"]
        for datum_vt, nazov_vt in polozky_vt:
            ctx.pocitadlo.aktualny_slot += 1
            ctx.progress(f"VT – {nazov_vt}: sťahujem {datum_vt.strftime('%d.%m.%Y')}...", ctx.pocitadlo.aktualny_slot, celkovo)
            soup_vt = _stiahni_lc_kbs_soup(datum_vt)
            refreny_vt = _extrahuj_refreny_zalmov_lc_kbs(soup_vt)
            time.sleep(REFRENY_DELAY_S)
            ctx.zaznamenaj_vysledok(bool(refreny_vt))
            if not refreny_vt:
                ctx.pocitadlo.chyby += 1
                if "VT" not in ctx.chybne_kody:
                    ctx.chybne_kody.append("VT")
                bloky_vt.append(nazov_vt + "\n\n1. [refrén sa nepodarilo stiahnuť]")
                continue
            riadky = [f"1. {refreny_vt[0]}"] if len(refreny_vt) == 1 else [f"{i}. {r}" for i, r in enumerate(refreny_vt, start=1)]
            bloky_vt.append(nazov_vt + "\n\n" + "\n\n".join(riadky))
        ctx.zapis_bloky("VT", bloky_vt, oddelovac="\n\n\n")
        log_info(f"[LC-KBS] VT ({rok}): uložené.")

        for tyzden in range(1, 8):
            ctx.aktualny_subor = f"{tyzden}VN"
            bloky = [_VEĽKONOCNE_NAZVY[tyzden]]
            for cyklus in CEZROCNE_NEDIELNE_CYKLY:
                datum = _najdi_datum_veľkonocnej_nedele(tyzden, cyklus, rok)
                bloky.append(f"{cyklus}: {spracuj_slot(f'{tyzden}VN {cyklus}', datum)}")
            for cislo_dna, den_index in CEZROCNE_DNI_TYZDNA.items():
                datum = _najdi_datum_veľkonocneho_vs_dna(tyzden, den_index, rok)
                bloky.append(f"{cislo_dna}. {spracuj_slot(f'{tyzden}VN deň {cislo_dna}', datum)}")
            ctx.zapis_bloky(ctx.aktualny_subor, bloky)
            log_info(f"[LC-KBS] {tyzden}VN ({rok}): uložené.")

        # PS
        ctx.aktualny_subor = "PS"
        bloky_ps = ["POPOLCOVÁ STREDA A DNI PO NEJ"]
        datum_streda = _zistí_datum_sviatku("PS", rok)
        bloky_ps.append(f"3. {spracuj_slot('PS – Popolcová streda', datum_streda)}")
        for cislo_dna, posun, nazov_dna in ((4, 1, "štvrtok"), (5, 2, "piatok"), (6, 3, "sobota")):
            datum_pps = _najdi_datum_pps_dna(posun, rok)
            bloky_ps.append(f"{cislo_dna}. {spracuj_slot(f'PS – {nazov_dna} po Popolcovej strede', datum_pps)}")
        ctx.zapis_bloky("PS", bloky_ps)
        log_info(f"[LC-KBS] PS ({datum_streda.strftime('%Y-%m-%d') if datum_streda else str(rok)}): uložené.")

        # Jednodenné
        for kod, popis in JEDNODENNE:
            ctx.aktualny_subor = kod
            ctx.pocitadlo.aktualny_slot += 1
            ctx.progress(f"{kod} – {popis}...", ctx.pocitadlo.aktualny_slot, celkovo)
            datum = _zistí_datum_sviatku(kod, rok)
            if datum is None:
                ctx.preskocenych += 1
                if kod not in ctx.preskocene_kody:
                    ctx.preskocene_kody.append(kod)
                ctx.progress(f"{kod}: v roku {rok} sa neslávi, súbor zostáva.", ctx.pocitadlo.aktualny_slot, celkovo)
                log_info(f"[LC-KBS] {kod}: vynechaný v roku {rok}.")
                continue
            ctx.progress(f"{kod}: sťahujem {datum.strftime('%d.%m.%Y')}...", ctx.pocitadlo.aktualny_slot, celkovo)
            soup = _stiahni_lc_kbs_soup(datum)
            refreny = _extrahuj_refreny_zalmov_lc_kbs(soup)
            time.sleep(REFRENY_DELAY_S)
            ctx.zaznamenaj_vysledok(bool(refreny))
            if not refreny:
                ctx.pocitadlo.chyby += 1
                if kod not in ctx.chybne_kody:
                    ctx.chybne_kody.append(kod)
                ctx.progress(f"{kod}: refrén sa nepodarilo stiahnuť.", ctx.pocitadlo.aktualny_slot, celkovo)
                continue
            nazov = vypocitaj_aktualnu_liturgicku_cast(datum)
            obsah = f"\n{nazov}\n\n1. {refreny[0]}\n" if len(refreny) == 1 else "\n" + "\n".join([nazov] + [f"\n{i}. {r}" for i, r in enumerate(refreny, start=1)]) + "\n"
            ctx.zapis_obsah(kod, obsah)
            log_info(f"[LC-KBS] {kod} ({datum}): uložené.")
    except _PredcasneUkoncenieStahovania as e:
        log_info(f"[LC-KBS] Pôstne/veľkonočné refrény {rok}: predčasne ukončené – {e}")

    log_info(
        f"[LC-KBS] Pôstne/veľkonočné refrény {rok} – súhrn: spracovaných {ctx.pocitadlo.aktualny_slot}/{celkovo}, "
        f"preskočených {ctx.preskocenych}" + (f" ({', '.join(ctx.preskocene_kody)})" if ctx.preskocene_kody else "") +
        f", chyby {ctx.pocitadlo.chyby}" + (f" ({', '.join(ctx.chybne_kody)})" if ctx.chybne_kody else "") + "."
    )
    ctx.progress(f"Hotovo. Spracovaných položiek: {ctx.pocitadlo.aktualny_slot}, chyby: {ctx.pocitadlo.chyby}.", ctx.pocitadlo.aktualny_slot, celkovo)

    return {
        "uspech": (ctx.pocitadlo.aktualny_slot - ctx.pocitadlo.chyby) > 0,
        "celkovo": ctx.pocitadlo.aktualny_slot,
        "chyby": ctx.pocitadlo.chyby,
        "chybne_kody": ctx.chybne_kody,
        "preskocených": ctx.preskocenych,
        "preskocene_kody": ctx.preskocene_kody,
        "subory": ctx.zapisane,
        "zaloha": ctx.backup.retazec_alebo_none,
    }


def stiahni_adventne_vianocne_refreny(rok: int, vystup_priecinok: Path, progress_callback=None) -> dict:
    ctx_or = _priprav_kontext_alebo_vrat_chybu(
        rok, vystup_priecinok, "backup_adventne", progress_callback,
        "[LC-KBS] Sťahovanie adventných týždňov preskočené: chýbajú knižnice."
    )
    if isinstance(ctx_or, dict):
        return ctx_or
    ctx: _RefrenyKontext = ctx_or

    kody = [f"{t}AD" for t in range(1, 5)]
    ctx.zalohuj_kody(kody)
    celkovo = 4 * (3 + 6)
    spracuj_slot = ctx.vytvor_spracuj_slot(celkovo)
    ctx.progress(f"Začínam sťahovanie adventných týždňov pre rok {rok}.", 0, celkovo)

    try:
        for tyzden in range(1, 5):
            ctx.aktualny_subor = f"{tyzden}AD"
            bloky = [_ADVENTNE_NAZVY[tyzden]]
            for cyklus in CEZROCNE_NEDIELNE_CYKLY:
                datum = _najdi_datum_adventnej_nedele(tyzden, cyklus, rok)
                bloky.append(f"{cyklus}: {spracuj_slot(f'{tyzden}AD {cyklus}', datum)}")
            for cislo_dna, den_index in CEZROCNE_DNI_TYZDNA.items():
                datum = _najdi_datum_adventneho_vs_dna(tyzden, den_index, rok)
                bloky.append(f"{cislo_dna}. {spracuj_slot(f'{tyzden}AD deň {cislo_dna}', datum)}")
            ctx.zapis_bloky(ctx.aktualny_subor, bloky)
    except _PredcasneUkoncenieStahovania as e:
        log_info(f"[LC-KBS] Adventné/vianočné refrény {rok}: predčasne ukončené – {e}")

    log_info(
        f"[LC-KBS] Adventné/vianočné refrény {rok} – súhrn: spracovaných {ctx.pocitadlo.aktualny_slot}/{celkovo}, chyby {ctx.pocitadlo.chyby}"
        + (f" ({', '.join(ctx.chybne_kody)})" if ctx.chybne_kody else "") + "."
    )
    ctx.progress(f"Hotovo. Spracovaných položiek: {ctx.pocitadlo.aktualny_slot}, chyby: {ctx.pocitadlo.chyby}.", ctx.pocitadlo.aktualny_slot, celkovo)

    return {
        "uspech": (ctx.pocitadlo.aktualny_slot - ctx.pocitadlo.chyby) > 0,
        "celkovo": ctx.pocitadlo.aktualny_slot,
        "chyby": ctx.pocitadlo.chyby,
        "chybne_kody": ctx.chybne_kody,
        "subory": ctx.zapisane,
        "zaloha": ctx.backup.retazec_alebo_none,
    }


# ── TURÍCE A SVIATKY NADVÄZUJÚCE NA VEĽKÚ NOC (1TS–7TS) ─────────────────────

_TS_CYKLICKE_KODY: tuple[str, ...] = ("1TS", "4TS", "5TS", "6TS")
_TS_JEDNORAZOVE_KODY: tuple[str, ...] = ("2TS", "3TS", "7TS")
_TS_POSUN_OD_TURIC: dict[str, int] = {
    "1TS": 0,
    "2TS": 1,
    "3TS": 4,
    "4TS": 7,
    "5TS": 11,
    "6TS": 19,
    "7TS": 20,
}


def _najdi_datum_turickeho_sviatku(kod: str, cyklus: str, preferovany_rok: int) -> "date | None":
    """
    Nájde reprezentatívny dátum sviatku po Turícach (1TS, 4TS, 5TS alebo 6TS)
    pre daný liturgický cyklus A/B/C – rovnaký princíp ako
    `_najdi_datum_veľkonocnej_nedele` a podobné funkcie pre ostatné obdobia.
    """
    cyklus = cyklus.upper()
    posun = _TS_POSUN_OD_TURIC[kod]
    for rok in _roky_podla_blizkosti(preferovany_rok):
        velka_noc = velkonocna_nedela(rok)
        turice = velka_noc + timedelta(days=49)
        kandidat = turice + timedelta(days=posun)
        if vypocitaj_liturgicky_rok(kandidat) != cyklus:
            continue
        if vypocitaj_kod_liturgickej_casti(kandidat) == kod:
            return kandidat
    return None


def stiahni_turicne_sviatky_pre_rok(rok: int, vystup_priecinok: Path, progress_callback=None) -> dict:
    ctx_or = _priprav_kontext_alebo_vrat_chybu(
        rok, vystup_priecinok, "backup_turice", progress_callback,
        "[LC-KBS] Sťahovanie Turíc a nadväzujúcich sviatkov preskočené: chýbajú knižnice."
    )
    if isinstance(ctx_or, dict):
        return ctx_or
    ctx: _RefrenyKontext = ctx_or

    kody = list(_TS_CYKLICKE_KODY) + list(_TS_JEDNORAZOVE_KODY)
    ctx.zalohuj_kody(kody)
    celkovo = len(_TS_CYKLICKE_KODY) * 3 + len(_TS_JEDNORAZOVE_KODY)
    spracuj_slot = ctx.vytvor_spracuj_slot(celkovo)
    ctx.progress(f"Začínam sťahovanie Turíc a nadväzujúcich sviatkov pre rok {rok}.", 0, celkovo)

    try:
        for kod in _TS_CYKLICKE_KODY:
            ctx.aktualny_subor = kod
            nazov = LITURGICKE_CASTI_PODLA_KODU.get(kod, kod)
            bloky = [nazov]
            for cyklus in CEZROCNE_NEDIELNE_CYKLY:
                datum = _najdi_datum_turickeho_sviatku(kod, cyklus, rok)
                bloky.append(f"{cyklus}: {spracuj_slot(f'{kod} {cyklus}', datum)}")
            ctx.zapis_bloky(kod, bloky)
            log_info(f"[LC-KBS] {kod} ({rok}): uložené.")

        for kod in _TS_JEDNORAZOVE_KODY:
            ctx.aktualny_subor = kod
            ctx.pocitadlo.aktualny_slot += 1
            ctx.progress(f"{kod}...", ctx.pocitadlo.aktualny_slot, celkovo)
            datum = _zistí_datum_sviatku(kod, rok)
            if datum is None:
                ctx.preskocenych += 1
                if kod not in ctx.preskocene_kody:
                    ctx.preskocene_kody.append(kod)
                ctx.progress(f"{kod}: v roku {rok} sa neslávi.", ctx.pocitadlo.aktualny_slot, celkovo)
                log_info(f"[LC-KBS] {kod}: vynechaný v roku {rok}.")
                continue
            ctx.progress(f"{kod}: sťahujem {datum.strftime('%d.%m.%Y')}...", ctx.pocitadlo.aktualny_slot, celkovo)
            soup = _stiahni_lc_kbs_soup(datum)
            refreny = _extrahuj_refreny_zalmov_lc_kbs(soup)
            time.sleep(REFRENY_DELAY_S)
            ctx.zaznamenaj_vysledok(bool(refreny))
            if not refreny:
                ctx.pocitadlo.chyby += 1
                if kod not in ctx.chybne_kody:
                    ctx.chybne_kody.append(kod)
                ctx.progress(f"{kod}: refrén sa nepodarilo stiahnuť.", ctx.pocitadlo.aktualny_slot, celkovo)
                continue
            nazov = vypocitaj_aktualnu_liturgicku_cast(datum)
            obsah = f"\n{nazov}\n\n1. {refreny[0]}\n" if len(refreny) == 1 else "\n" + "\n".join([nazov] + [f"\n{i}. {r}" for i, r in enumerate(refreny, start=1)]) + "\n"
            ctx.zapis_obsah(kod, obsah)
            log_info(f"[LC-KBS] {kod} ({datum}): uložené.")
    except _PredcasneUkoncenieStahovania as e:
        log_info(f"[LC-KBS] Turíce a nadväzujúce sviatky {rok}: predčasne ukončené – {e}")

    log_info(
        f"[LC-KBS] Turíce a nadväzujúce sviatky {rok} – súhrn: spracovaných {ctx.pocitadlo.aktualny_slot}/{celkovo}, "
        f"preskočených {ctx.preskocenych}" + (f" ({', '.join(ctx.preskocene_kody)})" if ctx.preskocene_kody else "") +
        f", chyby {ctx.pocitadlo.chyby}" + (f" ({', '.join(ctx.chybne_kody)})" if ctx.chybne_kody else "") + "."
    )
    ctx.progress(f"Hotovo. Spracovaných položiek: {ctx.pocitadlo.aktualny_slot}, chyby: {ctx.pocitadlo.chyby}.", ctx.pocitadlo.aktualny_slot, celkovo)

    return {
        "uspech": (ctx.pocitadlo.aktualny_slot - ctx.pocitadlo.chyby) > 0,
        "celkovo": ctx.pocitadlo.aktualny_slot,
        "chyby": ctx.pocitadlo.chyby,
        "chybne_kody": ctx.chybne_kody,
        "preskocených": ctx.preskocenych,
        "preskocene_kody": ctx.preskocene_kody,
        "subory": ctx.zapisane,
        "zaloha": ctx.backup.retazec_alebo_none,
    }


def stiahni_refreny_zalmov_pre_rok(rok: int, vystup_priecinok: Path, progress_callback=None) -> dict:
    ctx_or = _priprav_kontext_alebo_vrat_chybu(
        rok, vystup_priecinok, "backup_refreny", progress_callback,
        "[LC-KBS] Sťahovanie refrénov preskočené: chýbajú knižnice."
    )
    if isinstance(ctx_or, dict):
        return ctx_or
    ctx: _RefrenyKontext = ctx_or

    ctx.zalohuj_kody(REFRENY_MESIACE_SUBORY.values())
    dni = _vsetky_dni_roka(rok)
    celkovo = len(dni)
    chyby = 0
    vysledky: dict[int, list[str]] = {m: [] for m in range(1, 13)}

    ctx.progress(f"Začínam sťahovanie refrénov pre rok {rok}.", 0, celkovo)

    try:
        for idx, datum in enumerate(dni, start=1):
            ctx.progress(f"{datum.strftime('%d.%m.%Y')}: sťahujem...", idx, celkovo)
            soup = _stiahni_lc_kbs_soup(datum)
            refreny = _extrahuj_refreny_zalmov_lc_kbs(soup)
            time.sleep(REFRENY_DELAY_S)
            ctx.zaznamenaj_vysledok(bool(refreny))
            if refreny:
                text_refrenu = refreny[0]
            else:
                chyby += 1
                text_refrenu = "[refrén sa nepodarilo stiahnuť]"
            vysledky[datum.month].append(f"{datum.day}. {text_refrenu}")
    except _PredcasneUkoncenieStahovania as e:
        log_info(f"[LC-KBS] Refrény {rok}: predčasne ukončené – {e}")

    for mesiac in range(1, 13):
        kod = REFRENY_MESIACE_SUBORY[mesiac]
        obsah = f"\n{mesiac}. MESIAC – REFRÉNY ŽALMOV PRE ROK {rok}\n\n" + "\n\n".join(vysledky[mesiac]) + "\n"
        ctx.zapis_obsah(kod, obsah)

    log_info(f"[LC-KBS] Refrény {rok} – súhrn: spracovaných {celkovo}, bez refrénu {chyby}.")
    ctx.progress(f"Hotovo. Spracovaných dní: {celkovo}, bez refrénu: {chyby}.", celkovo, celkovo)

    return {
        "uspech": (celkovo - chyby) > 0,
        "celkovo": celkovo,
        "chyby": chyby,
        "subory": ctx.zapisane,
        "zaloha": ctx.backup.retazec_alebo_none,
    }


LITURGICKE_SVIATKY_KODY: list[tuple[str, str]] = [
    # Cezročné sviatky
    ("FJ",   "Sv. Filipa a Jakuba, apoštolov (3. V.)"),
    ("NJK",  "Narodenie sv. Jána Krstiteľa (24. VI.)"),
    ("NAVPM","Návšteva preblahoslavenej Panny Márie (2. VII.)"),
    ("CMV",  "Sv. Cyrila a Metoda (5. VII.)"),
    ("BEN",  "Sv. Benedikta, opáta (11. VII.)"),
    ("BRI",  "Sv. Brigity, rehoľníčky (23. VII.)"),
    #("6L",   "Sv. Petra a Pavla, apoštolov (29. VI.)"),
    ("PREM", "Premenenie Pána (6. VIII.)"),
    ("VAV",  "Sv. Vavrinca, diakona a mučeníka (10. VIII.)"),
    #("8L",   "Nanebovzatie Panny Márie (15. VIII.)"),
    ("BAR",  "Sv. Bartolomeja, apoštola (24. VIII.)"),
    ("NPMAR","Narodenie Panny Márie (8. IX.)"),
    ("PSK",  "Povýšenie Svätého kríža (14. IX.)"),
    ("MATE", "Sv. Matúša, apoštola a evanjelistu (21. IX.)"),
    ("MGR",  "Sv. Michala, Gabriela a Rafaela, archanieli (29. IX.)"),
    #("11L",  "Všetkých svätých (1. XI.)"),
    ("ZOS",  "Spomienka na Všetkých zosnulých (2. XI.)"),
    ("VPLB", "Výročie posviacky Lateránskej baziliky (9. XI.)"),
    ("OND",  "Sv. Ondreja, apoštola (30. XI.)"),
    #("12L",  "Nepoškvrnené počatie Panny Márie (8. XII.)"),
]

VIANOCNE_SVIATKY_KODY: list[tuple[str, str]] = [
    ("SR",   "Svätej rodiny Ježiša, Márie a Jozefa – nedeľa po Narodení Pána "
              "(alebo 30. XII., ak Narodenie Pána pripadne na nedeľu)"),
    ("STEF", "Sv. Štefana, prvého mučeníka (26. XII.) – ak nepadne na nedeľu"),
    ("SJE",  "Sv. Jána, apoštola a evanjelistu (27. XII.) – ak nepadne na nedeľu"),
    ("NEV",  "Sv. Neviniatok, mučeníkov (28. XII.) – ak nepadne na nedeľu"),
    ("PDR",  "Posledný deň roka (31. XII.) – ak nepadne na nedeľu"),
    ("PMB",  "Panny Márie Bohorodičky (1. I.)"),
    ("NMJ",  "Najsvätejšie meno Ježiš (3. I.) – ak nepadne na nedeľu"),
    ("KKP",  "Krst Krista Pána"),
]

_PEVNE_KODY: dict[str, tuple[int, int]] = {
    "1VI":   (12, 25),
    "STEF":  (12, 26),
    "SJE":   (12, 27),
    "NEV":   (12, 28),
    "PDR":   (12, 31),
    "PMB":   (1,  1),
    "NMJ":   (1,  3),
    "1L":    (1,  6),
    "FJ":    (5,  3),
    "NAVPM": (7,  2),
    "CMV":   (7,  5),
    "BEN":   (7,  11),
    "BRI":   (7,  23),
    "6L":    (6,  29),
    "PREM":  (8,  6),
    "VAV":   (8,  10),
    "8L":    (8,  15),
    "BAR":   (8,  24),
    "NPMAR": (9,  8),
    "PSK":   (9,  14),
    "MATE":  (9,  21),
    "MGR":   (9,  29),
    "11L":   (11, 1),
    "ZOS":   (11, 2),
    "VPLB":  (11, 9),
    "OND":   (11, 30),
    "12L":   (12, 8),
    "2VI":   (1,  2),   # reprezentatívny deň 2. vianočného obdobia
}

_OKTAVA_NAZVY_PODLA_DNA: dict[int, str] = {
    25: "NARODENIE PÁNA (1. deň oktávy)",
    26: "SV. ŠTEFANA, PRVÉHO MUČENÍKA (2. deň oktávy)",
    27: "SV. JÁNA, APOŠTOLA A EVANJELISTU (3. deň oktávy)",
    28: "SV. NEVINIATOK, MUČENÍKOV (4. deň oktávy)",
    29: "PIATY DEŇ OKTÁVY",
    30: "ŠIESTY DEŇ OKTÁVY",
    31: "SIEDMY DEŇ OKTÁVY",
}

_NAZOV_NEDELE_SVATEJ_RODINY = (
    "PRVÁ NEDEĽA PO NARODENÍ PÁNA (NEDEĽA SVÄTEJ RODINY - JEŽIŠA, MÁRIE A JOZEFA)"
)


def _zistí_datum_sviatku(kod: str, rok: int) -> "date | None":
    """
    Vráti dátum, v ktorom sa sviatok daného kódu v danom roku skutočne slávi,
    alebo None ak sa sviatok neslávi (vynechaný/prekrytý).
    Pre pohyblivé sviatky hľadá dátum v danom roku aj susedných rokoch.
    """
    # Špeciálne sviatky s vlastnou logikou presunu
    specialne: dict[str, Callable[[int], date | None]] = {
        "ZV": datum_zvestovania_pana,
        "NJK": datum_narodenia_jana_krstitela,
        "12L": datum_neposkvrneneho_pocatia,
        "KKP": krst_krista_pana,
        "VPON": lambda r: vypocitaj_datum_pohyblivych_slaveni(r).get("Pondelok vo Veľkonočnej oktáve"),
    }
    
    if kod in specialne:
        try:
            datum = specialne[kod](rok)
        except Exception:
            return None
        if datum is None:
            return None
        # VPON má interný kód VOKT – nekontrolujeme zhodu kódu
        if kod == "VPON":
            return datum
        skutocny = vypocitaj_kod_liturgickej_casti(datum)
        return datum if skutocny == kod else None

    if kod in _PEVNE_KODY:
        mesiac, den = _PEVNE_KODY[kod]
        try:
            datum = date(rok, mesiac, den)
        except ValueError:
            return None
        skutocny = vypocitaj_kod_liturgickej_casti(datum)
        return datum if skutocny == kod else None

    # Pohyblivé – hľadáme dátum v kalendárnom roku
    try:
        zaciatok = date(rok, 1, 1)
    except ValueError:
        return None
    for offset in range(366):
        d = zaciatok + timedelta(days=offset)
        if d.year != rok:
            break
        if vypocitaj_kod_liturgickej_casti(d) == kod:
            return d
    return None


def stiahni_liturgicke_sviatky_pre_rok(rok: int, vystup_priecinok: Path, progress_callback=None) -> dict:
    ctx_or = _priprav_kontext_alebo_vrat_chybu(
        rok, vystup_priecinok, "backup_sviatky", progress_callback,
        "[LC-KBS] Sťahovanie sviatkov preskočené: chýbajú knižnice."
    )
    if isinstance(ctx_or, dict):
        return ctx_or
    ctx: _RefrenyKontext = ctx_or

    celkovo = len(LITURGICKE_SVIATKY_KODY)
    # POZOR: "stiahnutych"/"chyby" tu nie sú to isté ako ctx.pocitadlo –
    # počítajú len skutočne úspešne/neúspešne stiahnuté položky (nie
    # spracované sloty), preto ostávajú vlastné lokálne premenné a
    # ctx.pocitadlo sa v tejto funkcii nepoužíva.
    stiahnutych = 0
    chyby = 0
    ctx.progress(f"Začínam sťahovanie sviatkov pre rok {rok}.", 0, celkovo)

    try:
        for idx, (kod, popis) in enumerate(LITURGICKE_SVIATKY_KODY, start=1):
            ctx.aktualny_subor = kod
            ctx.progress(f"{kod} – {popis}...", idx, celkovo)
            datum = _zistí_datum_sviatku(kod, rok)
            if datum is None:
                ctx.preskocenych += 1
                ctx.preskocene_kody.append(kod)
                ctx.progress(f"{kod}: v roku {rok} sa neslávi.", idx, celkovo)
                continue
            ctx.progress(f"{kod}: sťahujem {datum.strftime('%d.%m.%Y')}...", idx, celkovo)
            ctx.backup.zalohuj(kod)
            soup = _stiahni_lc_kbs_soup(datum)
            refreny = _extrahuj_refreny_zalmov_lc_kbs(soup)
            time.sleep(REFRENY_DELAY_S)
            ctx.zaznamenaj_vysledok(bool(refreny))
            if not refreny:
                chyby += 1
                ctx.chybne_kody.append(kod)
                ctx.progress(f"{kod}: refrén sa nepodarilo stiahnuť.", idx, celkovo)
                continue
            nazov = vypocitaj_aktualnu_liturgicku_cast(datum)
            obsah = f"\n{nazov}\n\n1. {refreny[0]}\n" if len(refreny) == 1 else "\n" + "\n".join([nazov] + [f"\n{i}. {r}" for i, r in enumerate(refreny, start=1)]) + "\n"
            ctx.zapis_obsah(kod, obsah)
            stiahnutych += 1
    except _PredcasneUkoncenieStahovania as e:
        log_info(f"[LC-KBS] Liturgické sviatky {rok}: predčasne ukončené – {e}")

    log_info(
        f"[LC-KBS] Liturgické sviatky {rok} – súhrn: stiahnutých {stiahnutych}/{celkovo}, preskočených {ctx.preskocenych}"
        + (f" ({', '.join(ctx.preskocene_kody)})" if ctx.preskocene_kody else "") + f", chyby {chyby}" + (f" ({', '.join(ctx.chybne_kody)})" if ctx.chybne_kody else "") + "."
    )
    ctx.progress(f"Hotovo. Stiahnutých: {stiahnutych}, preskočených: {ctx.preskocenych}, chyby: {chyby}.", celkovo, celkovo)

    return {
        "uspech": stiahnutych > 0,
        "celkovo": celkovo,
        "stiahnutych": stiahnutych,
        "chyby": chyby,
        "chybne_kody": ctx.chybne_kody,
        "preskocených": ctx.preskocenych,
        "preskocene_kody": ctx.preskocene_kody,
        "subory": ctx.zapisane,
        "zaloha": ctx.backup.retazec_alebo_none,
    }


def _zostav_text_kompilovaneho_useku(polozky: list[tuple[date, str]], na_vysledok=None) -> tuple[str, int, int]:
    """
    Zostaví text kompilovaného viacdňového súboru (napr. 1VI.txt, 2VI.txt)
    z už vopred pripravených dvojíc (dátum, názov). Po sebe idúce dni s
    rovnakým názvom sa zoskupia pod jeden spoločný nadpis; refrény sa
    označia číslom dňa v mesiaci (napr. "25.1", "25.2", "26.", ...).

    na_vysledok: voliteľný callback(uspech: bool) – circuit breaker (pozri
    _RefrenyKontext.zaznamenaj_vysledok), volaný po každom stiahnutom dni.

    Vráti (obsah, počet úspešne stiahnutých dní, počet dní s chybou).
    """
    bloky: list[str] = []
    aktualny_nazov: str | None = None
    aktualne_riadky: list[str] = []
    stiahnutych = 0
    chyby = 0

    def uzavri_blok():
        nonlocal aktualny_nazov, aktualne_riadky
        if aktualny_nazov is not None and aktualne_riadky:
            bloky.append(aktualny_nazov + "\n\n" + "\n\n".join(aktualne_riadky))
        aktualny_nazov = None
        aktualne_riadky = []

    for datum, nazov in polozky:
        soup = _stiahni_lc_kbs_soup(datum)
        refreny = _extrahuj_refreny_zalmov_lc_kbs(soup)
        time.sleep(REFRENY_DELAY_S)
        if na_vysledok:
            na_vysledok(bool(refreny))

        if nazov != aktualny_nazov:
            uzavri_blok()
            aktualny_nazov = nazov

        if not refreny:
            chyby += 1
            aktualne_riadky.append(f"{datum.day}. [refrén sa nepodarilo stiahnuť]")
            continue

        stiahnutych += 1
        if len(refreny) == 1:
            aktualne_riadky.append(f"{datum.day}. {refreny[0]}")
        else:
            for i, r in enumerate(refreny, start=1):
                aktualne_riadky.append(f"{datum.day}.{i} {r}")

    uzavri_blok()
    obsah = "\n" + "\n\n\n".join(bloky) + "\n"
    return obsah, stiahnutych, chyby


def stiahni_vianocne_sviatky_pre_rok(rok: int, vystup_priecinok: Path, progress_callback=None) -> dict:
    ctx_or = _priprav_kontext_alebo_vrat_chybu(
        rok, vystup_priecinok, "backup_vianocne", progress_callback,
        "[LC-KBS] Sťahovanie vianočných sviatkov preskočené: chýbajú knižnice."
    )
    if isinstance(ctx_or, dict):
        return ctx_or
    ctx: _RefrenyKontext = ctx_or

    celkovo = len(VIANOCNE_SVIATKY_KODY) + 2
    # POZOR: "stiahnutych"/"chyby" tu (rovnako ako v stiahni_liturgicke_sviatky_pre_rok)
    # nie sú to isté ako ctx.pocitadlo – ctx.pocitadlo sa v tejto funkcii nepoužíva.
    stiahnutych = 0
    chyby = 0
    ctx.progress(f"Začínam sťahovanie vianočných sviatkov pre rok {rok}.", 0, celkovo)

    _JANUAROVE_KODY = {"PMB", "NMJ", "KKP"}

    try:
        for idx, (kod, popis) in enumerate(VIANOCNE_SVIATKY_KODY, start=1):
            ctx.aktualny_subor = kod
            ctx.progress(f"{kod} – {popis}...", idx, celkovo)
            rok_sviatku = rok + 1 if kod in _JANUAROVE_KODY else rok
            datum = _zistí_datum_sviatku(kod, rok_sviatku)
            if datum is None:
                ctx.preskocenych += 1
                ctx.preskocene_kody.append(kod)
                ctx.progress(f"{kod}: v roku {rok_sviatku} sa neslávi.", idx, celkovo)
                continue
            ctx.progress(f"{kod}: sťahujem {datum.strftime('%d.%m.%Y')}...", idx, celkovo)
            ctx.backup.zalohuj(kod)
            soup = _stiahni_lc_kbs_soup(datum)
            refreny = _extrahuj_refreny_zalmov_lc_kbs(soup)
            time.sleep(REFRENY_DELAY_S)
            ctx.zaznamenaj_vysledok(bool(refreny))
            if not refreny:
                chyby += 1
                ctx.chybne_kody.append(kod)
                ctx.progress(f"{kod}: refrén sa nepodarilo stiahnuť.", idx, celkovo)
                continue
            nazov = vypocitaj_aktualnu_liturgicku_cast(datum)
            obsah = f"\n{nazov}\n\n1. {refreny[0]}\n" if len(refreny) == 1 else "\n" + "\n".join([nazov] + [f"\n{i}. {r}" for i, r in enumerate(refreny, start=1)]) + "\n"
            ctx.zapis_obsah(kod, obsah)
            stiahnutych += 1
            log_info(f"[LC-KBS] {kod} ({datum.strftime('%Y-%m-%d')}): uložené.")

        # 1VI
        idx = len(VIANOCNE_SVIATKY_KODY) + 1
        ctx.aktualny_subor = "1VI"
        ctx.progress("1VI – Narodenie Pána a oktáva...", idx, celkovo)
        polozky_1vi: list[tuple[date, str]] = []
        for den in range(25, 32):
            datum_dna = date(rok, 12, den)
            nazov_dna = _NAZOV_NEDELE_SVATEJ_RODINY if datum_dna == datum_svatej_rodiny(rok) else _OKTAVA_NAZVY_PODLA_DNA[den]
            polozky_1vi.append((datum_dna, nazov_dna))
        polozky_1vi.append((date(rok + 1, 1, 1), "SLÁVNOSŤ PANNY MÁRIE BOHORODIČKY (8. deň oktávy)"))
        ctx.backup.zalohuj("1VI")
        obsah_1vi, ok_1vi, chyby_1vi = _zostav_text_kompilovaneho_useku(polozky_1vi, na_vysledok=ctx.zaznamenaj_vysledok)
        ctx.zapis_obsah("1VI", obsah_1vi)
        if ok_1vi > 0:
            stiahnutych += 1
        if chyby_1vi > 0:
            chyby += 1
            ctx.chybne_kody.append("1VI")

        # 2VI
        idx = len(VIANOCNE_SVIATKY_KODY) + 2
        rok_januara = rok + 1
        ctx.aktualny_subor = "2VI"
        ctx.progress(f"2VI – 2. vianočné obdobie ({rok}/{rok_januara})...", idx, celkovo)
        druha_nedela = najblizsia_nedela_po_dni(date(rok_januara, 1, 1))
        zaciatok_2vi = druha_nedela if druha_nedela < date(rok_januara, 1, 6) else date(rok_januara, 1, 2)
        koniec_2vi = krst_krista_pana(rok_januara)
        polozky_2vi: list[tuple[date, str]] = []
        if koniec_2vi >= zaciatok_2vi:
            for i in range((koniec_2vi - zaciatok_2vi).days + 1):
                d = zaciatok_2vi + timedelta(days=i)
                polozky_2vi.append((d, vypocitaj_aktualnu_liturgicku_cast(d)))
        ctx.backup.zalohuj("2VI")
        obsah_2vi, ok_2vi, chyby_2vi = _zostav_text_kompilovaneho_useku(polozky_2vi, na_vysledok=ctx.zaznamenaj_vysledok)
        ctx.zapis_obsah("2VI", obsah_2vi)
        if ok_2vi > 0:
            stiahnutych += 1
        if chyby_2vi > 0:
            chyby += 1
            ctx.chybne_kody.append("2VI")
    except _PredcasneUkoncenieStahovania as e:
        log_info(f"[LC-KBS] Vianočné obdobie {rok}/{rok + 1}: predčasne ukončené – {e}")

    log_info(
        f"[LC-KBS] Vianočné obdobie {rok}/{rok + 1} – súhrn: stiahnutých {stiahnutych}/{celkovo}, preskočených {ctx.preskocenych}"
        + (f" ({', '.join(ctx.preskocene_kody)})" if ctx.preskocene_kody else "") + f", chyby {chyby}" + (f" ({', '.join(ctx.chybne_kody)})" if ctx.chybne_kody else "") + "."
    )
    ctx.progress(f"Hotovo. Stiahnutých: {stiahnutych}, preskočených: {ctx.preskocenych}, chyby: {chyby}.", celkovo, celkovo)

    return {
        "uspech": stiahnutych > 0,
        "celkovo": celkovo,
        "stiahnutych": stiahnutych,
        "chyby": chyby,
        "chybne_kody": ctx.chybne_kody,
        "preskocených": ctx.preskocenych,
        "preskocene_kody": ctx.preskocene_kody,
        "subory": ctx.zapisane,
        "zaloha": ctx.backup.retazec_alebo_none,
    }


def _zisti_http_kodovanie(response, kontext: str, fallback: str) -> str:
    """
    Spoľahlivo zistí kódovanie HTTP odpovede namiesto slepého spoliehania sa
    na `response.apparent_encoding` (heuristika, ktorá pri stredoeurópskom
    texte s diakritikou býva nespoľahlivá).

    Zdieľaná pre stiahni_citania_z_lc_kbs aj stiahni_vespery_z_breviar –
    predtým mala každá funkcia svoj vlastný, navzájom nekonzistentný
    fallback (jedna 'utf-8', druhá 'windows-1250') riešený len ad-hoc.

    Poradie priorít:
    1. Ak HTTP hlavička Content-Type sama obsahuje charset, je to
       najspoľahlivejší zdroj – requests ho už automaticky použil.
    2. Inak sa skúsi nájsť <meta charset="..."> priamo v HTML tele
       odpovede (druhý najspoľahlivejší zdroj).
    3. Až keď ani jedno nevyjde, použije sa apparent_encoding – ale ak
       hádže typický falošný odhad iso-8859-1/latin-1 pre stredoeurópsky
       text, použije sa `fallback` špecifický pre danú stránku (líši sa
       medzi lc.kbs.sk a breviar.kbs.sk – nie je isté, že obe stránky
       skutočne používajú rovnaké kódovanie).
    """
    header_ct = response.headers.get("Content-Type", "")
    if "charset=" in header_ct.lower():
        log_debug(f"[{kontext}] Kódovanie z HTTP hlavičky: {response.encoding}")
        return response.encoding or fallback

    try:
        zaciatok = response.content[:2048].decode("ascii", errors="ignore")
        m = re.search(r'charset=["\']?\s*([\w-]+)', zaciatok, re.IGNORECASE)
        if m:
            log_debug(f"[{kontext}] Kódovanie nájdené v <meta charset>: {m.group(1)}")
            return m.group(1)
    except Exception as e:
        log_debug(f"[{kontext}] Hľadanie <meta charset> v HTML zlyhalo: {e}")

    odhad = response.apparent_encoding or fallback
    if odhad.lower() in ("iso-8859-1", "latin-1"):
        log_debug(
            f"[{kontext}] apparent_encoding odhadol '{odhad}' (typický falošný "
            f"odhad pre stredoeurópsky text) – používam fallback '{fallback}'."
        )
        return fallback
    return odhad


def stiahni_citania_z_lc_kbs(datum: date, vystup_cesta: Path | str) -> bool:
    _over_gregoriansky_datum(datum)
    url = None
    if chybaju_kniznice_pre_stahovanie():
        return False
    requests_module = requests
    beautiful_soup = BeautifulSoup
    assert requests_module is not None and beautiful_soup is not None
    req_exc = getattr(requests_module, "RequestException", Exception)
    http_exc = getattr(requests_module, "HTTPError", req_exc)
    to_exc = getattr(requests_module, "Timeout", req_exc)
    conn_exc = getattr(requests_module, "ConnectionError", req_exc)
    session = _vytvor_lc_kbs_session()
    response = None
    try:
        datum_str = datum.strftime("%Y-%m-%d")
        for pokus in range(1, LC_KBS_REFRENY_MAX_POKUSOV + 1):
            url = f"https://lc.kbs.sk/?den={datum_str}&_={int(time.time())}"
            headers = _lc_kbs_headers("citania")
            try:
                if session is not None:
                    response = session.get(url, headers=headers, timeout=(5, 15))
                else:
                    response = requests_module.get(url, headers=headers, timeout=(5, 15))
                response.raise_for_status()
                break
            except http_exc as e:
                sc = getattr(getattr(e, "response", None), "status_code", None)
                if sc in LC_KBS_DOCASNE_HTTP_STATUSY and pokus < LC_KBS_REFRENY_MAX_POKUSOV:
                    time.sleep(LC_KBS_REFRENY_RETRY_DELAY_S * pokus)
                    continue
                return False
            except (to_exc, conn_exc, req_exc):
                if pokus < LC_KBS_REFRENY_MAX_POKUSOV:
                    time.sleep(LC_KBS_REFRENY_RETRY_DELAY_S * pokus)
                    continue
                return False
        if response is None:
            return False
        response.encoding = _zisti_http_kodovanie(response, "LC-KBS", fallback="utf-8")
        soup = beautiful_soup(response.text, 'html.parser')
        vystup = ["="*60, "ČÍTANIA NA SVÄTÚ OMŠU", f"{datum.strftime('%d.%m.%Y')}", "="*60, ""]
        nazov_info = _extrahovaj_info_dna_lc_kbs(soup, datum)
        if nazov_info:
            vystup.extend(_vycisti_text_lc_kbs(r) for r in nazov_info)
            vystup.append("")
        citania_texty = _extrahovaj_vsetky_citania_lc_kbs(soup)
        if not citania_texty:
            return False
        vystup.extend(citania_texty)
        celkovy_text = "\n".join(vystup)
        if len(celkovy_text) < 200:
            return False
        _zapis_text_atomicky(vystup_cesta, celkovy_text, encoding="utf-8")
        return True
    except Exception as e:
        log_exception(f"stiahni_citania_z_lc_kbs: neočakávaná chyba (URL: {url or 'neznáma'})", e)
        return False
    finally:
        if 'session' in locals() and session is not None:
            try:
                session.close()
            except Exception:
                pass


def _lc_kbs_ocakava_dve_citania(datum, nazov_info) -> bool:
    """Nedele a slávnosti majú mať dve čítania pred evanjeliom."""
    if datum.weekday() == 6:
        return True

    info_text = "\n".join(nazov_info or [])
    info_norm = normalize_diacritics(info_text)
    return "slavnost" in info_norm


def _lc_kbs_pocet_citani_pred_evanjeliom(citania_texty: list) -> int:
    """Spočíta neevanjeliové čítania vo výstupe z LC-KBS extraktora."""
    pocet = 0
    oddelovac = "-" * 60

    for i, riadok in enumerate(citania_texty or []):
        if riadok != oddelovac:
            continue
        if i + 2 >= len(citania_texty) or citania_texty[i + 2] != oddelovac:
            continue

        nadpis_norm = normalize_diacritics(citania_texty[i + 1].strip())
        if not nadpis_norm or "refren zalmu" in nadpis_norm:
            continue
        if not any(k in nadpis_norm for k in (
            "citanie", "evanjelium", "evanjelia", "utrpenie",
            "zaciatok", "skutkov apostolov",
        )):
            continue
        if "evanjelium" in nadpis_norm or "evanjelia" in nadpis_norm:
            break

        pocet += 1

    return pocet

def _extrahovaj_info_dna_lc_kbs(soup, datum):
    """
    Extrahuje názov dňa a liturgickú farbu z lc.kbs.sk.
    """
    vystup = []

    if not soup:
        return vystup

    # PRIORITIZOVANÉ selektory – najšpecifickejšie ako prvé
    nazov_selektory = [
        '.nazov-dna',
        '.den-nadpis',
        '.page-title',
        '.nadpis',
        '.title',
        'div[class*="nazov"]',
        'div[class*="den"]',
        'h2',          # najčastejšie správne
        'h1'           # najmenej spoľahlivé, až na konci
    ]

    # Kľúčové slová bez diakritiky
    KLUCOVE_SLOVA = [
        'nedela', 'pondelok', 'utorok', 'streda', 'stvrtok', 'piatok', 'sobota',
        'slavnost', 'sviatok', 'spomienka', 'obdobie', 'cezrocne',
        'feria', 'pamiatka', 'sv.', 'svaty', 'svata',
        'utrpenie', 'pasie'
    ]

    # 1. Hľadanie názvu dňa
    nasiel_sa_nazov = False
    for selektor in nazov_selektory:
        try:
            elem = soup.select_one(selektor)
            if not elem:
                continue

            text = elem.get_text(strip=True)
            if len(text) < 5:
                continue

            # Odstránenie farby prilepenej na konci názvu dňa (F, B, Č, Z)
            text = re.sub(r'\s*[FBČZ]$', '', text, flags=re.IGNORECASE)

            # Rozbitie prilepených slov (malé → veľké písmeno)
            text = re.sub(
                r'([a-záäčďéíĺľňóôŕšťúýž])([A-ZÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ])',
                r'\1 \2',
                text
            )

            # Špeciálne opravy LC‑KBS
            text = text.replace("Balebo", "B alebo")
            text = text.replace("Čalebo", "Č alebo")
            text = text.replace("Zalebo", "Z alebo")
            text = re.sub(r'([ABCČ])\s*\(', r'\1 (', text)

            text_norm = normalize_diacritics(text)

            # Ignorujeme balast
            if text_norm in ['liturgicky kalendar', 'kalendar']:
                continue

            # Kontrola kľúčových slov
            if any(kw in text_norm for kw in KLUCOVE_SLOVA):
                vystup.append(text)
                nasiel_sa_nazov = True
                break

        except Exception as e_sel:
            log_exception(f"_extrahovaj_info_dna_lc_kbs: chyba pri selektore '{selektor}'", e_sel)
            continue

    if not nasiel_sa_nazov:
        # 2. Fallback: ak sa nenašiel názov, použijeme deň v týždni
        dni = ['Pondelok', 'Utorok', 'Streda', 'Štvrtok', 'Piatok', 'Sobota', 'Nedeľa']
        vystup.append(dni[datum.weekday()])


    # 3. Liturgická farba
    farba_selektory = ['.farba', '.liturgicka-farba', 'span[class*="farba"]', '.color']
    for selektor in farba_selektory:
        try:
            elem = soup.select_one(selektor)
            if elem:
                # Primárne text, potom title/alt
                farba_text = (
                    elem.get_text(strip=True)
                    or elem.get('title')
                    or elem.get('alt')
                )

                if farba_text:
                    # Robustné odstránenie všetkého pred farbou
                    cista_farba = re.sub(
                        r'(?i)^.*?(farba|farba dna)[^a-z0-9]*',
                        '',
                        farba_text
                    ).strip()

                    if cista_farba:
                        vystup.append(f"Liturgická farba: {cista_farba.capitalize()}")
                        break
        except Exception as e_farba:
            log_exception(f"_extrahovaj_info_dna_lc_kbs: chyba pri selektore farby '{selektor}'", e_farba)
            continue

    return vystup

def _extrahovaj_vsetky_citania_lc_kbs(soup):

    def _vycisti_refren(text):
        t = text.strip()
        t = re.sub(r'^[Rr]\s*[.:]\s*', '', t).strip()
        t = t.lstrip(':. ').strip()
        return t

    vystup = []
    if not soup:
        log_debug("[LC-KBS] Soup je prázdny – nič neextrahujem.")
        return vystup

    log_debug("[LC-KBS] Začínam extrakciu čítaní...")

    elementy = soup.find_all(['p', 'h3', 'h4', 'h5', 'strong', 'b', 'li', 'em', 'i'])
    log_debug(f"[LC-KBS] Počet HTML elementov na spracovanie: {len(elementy)}")

    aktualna_sekcia = None
    aktualne_riadky = []
    najdene_sekcie = []

    refreny_zalmov = []
    refreny_zalmov_seen = set()
    ignorujeme_zalm = False
    refren_aktualneho_zalmu = None
    pocet_ignorovanych_od_zalmu = 0
    # Bezpečnostná poistka: ak sa po tomto počte prvkov od začiatku žalmu
    # nenájde nadpis ďalšieho čítania (napr. kvôli zmene štruktúry stránky),
    # ignorovanie žalmu sa nútene ukončí a do logu sa zapíše varovanie,
    # namiesto toho, aby sa zvyšok stránky potichu zahodil.
    MAX_ELEMENTOV_BEZ_NADPISU_ZALM = 15

    def _pridaj_refren_zalmu(text):
        nonlocal refren_aktualneho_zalmu
        cisty = _vycisti_refren(text)
        if not cisty:
            return
        refren = f"R.: {cisty}"
        if refren_aktualneho_zalmu == refren:
            return
        if refren in refreny_zalmov_seen:
            refren_aktualneho_zalmu = refren
            return
        refreny_zalmov.append(refren)
        refreny_zalmov_seen.add(refren)
        refren_aktualneho_zalmu = refren
        log_debug(f"[LC-KBS] Nájdený refrén: {refren}")

    def je_nadpis_citania(text):
        t = normalize_diacritics(text.lower().replace("\xa0", " ").strip())
        if len(t) > 150:
            return False

        # Nadpis môže začínať číslovaním typu "1.", "2)" alebo "1".
        t = re.sub(r'^\d+\s*[.)]?\s*', '', t)
        t = re.sub(r'\s+', ' ', t).strip()
        if re.match(r"^evanjelium(\s+\d+)?\s+podla\b", t):
            return True

        nadpisove_prefixy = (
            "zaciatok",
            "citanie z",
            "citanie zo",
            "prve citanie",
            "druhe citanie",
            "z knihy",
            "z listu",
            "zo skutkov",
            "zo svateho evanjelia",
            "evanjelium podla",
            "utrpenie nasho pana",
            "panovo utrpenie",
        )
        return t.startswith(nadpisove_prefixy)

    # -----------------------------
    # HLAVNÁ SLUČKA
    # -----------------------------
    for elem in elementy:
        text = elem.get_text(" ", strip=True)
        if len(text) < 2:
            continue

        low = text.lower()

        # 1. Refrén žalmu
        if text.strip().lower().startswith(('r.', 'r:')):
            _pridaj_refren_zalmu(text)
            if ignorujeme_zalm:
                continue

        # 2. Ignorovanie žalmu
        if ignorujeme_zalm:
            if je_nadpis_citania(text):
                ignorujeme_zalm = False
                pocet_ignorovanych_od_zalmu = 0
            else:
                pocet_ignorovanych_od_zalmu += 1
                if pocet_ignorovanych_od_zalmu > MAX_ELEMENTOV_BEZ_NADPISU_ZALM:
                    log_info(
                        "[LC-KBS] VAROVANIE: po žalme sa ani po "
                        f"{MAX_ELEMENTOV_BEZ_NADPISU_ZALM} prvkoch nenašiel nadpis "
                        "ďalšieho čítania – štruktúra stránky sa pravdepodobne "
                        "zmenila. Ignorovanie žalmu nútene ukončujem, aby sa "
                        "nestratil zvyšok textu."
                    )
                    ignorujeme_zalm = False
                    pocet_ignorovanych_od_zalmu = 0
                    # Bez 'continue' – tento prvok sa nižšie spracuje bežným
                    # spôsobom (môže ísť napr. rovno o nadpis, ktorý predošlá
                    # kontrola z nejakého dôvodu nerozpoznala).
                else:
                    continue

        # 3. Koniec sekcie
        if "počuli sme božie slovo" in low or "počuli sme slovo pánovo" in low:
            veta_konca = (
                "Počuli sme Božie slovo."
                if "božie" in low else
                "Počuli sme slovo Pánovo."
            )
            aktualne_riadky.append(veta_konca)

            if aktualna_sekcia and aktualne_riadky:
                obsah = "\n".join(aktualne_riadky).strip()
                if len(obsah) > 20:
                    najdene_sekcie.append((aktualna_sekcia, obsah))
                    log_debug(f"[LC-KBS] Uložená sekcia: {aktualna_sekcia}")

            aktualna_sekcia = None
            aktualne_riadky = []
            continue

        # 4. Nový nadpis čítania
        if je_nadpis_citania(text):
            if aktualna_sekcia and aktualne_riadky:
                obsah = "\n".join(aktualne_riadky).strip()
                if len(obsah) > 20:
                    najdene_sekcie.append((aktualna_sekcia, obsah))
                    log_debug(f"[LC-KBS] Uložená sekcia: {aktualna_sekcia}")

            aktualna_sekcia = text
            aktualne_riadky = []
            ignorujeme_zalm = False
            log_debug(f"[LC-KBS] Začínam novú sekciu: {text}")
            continue

        # 5. Začiatok žalmu
        if low.startswith(("responzóriový žalm", "žalm")):
            ignorujeme_zalm = True
            refren_aktualneho_zalmu = None
            pocet_ignorovanych_od_zalmu = 0
            log_debug("[LC-KBS] Začína žalm – ignorujem text žalmu.")
            continue

        # 6. Zber textu
        if aktualna_sekcia:
            if text.startswith('(') and text.endswith(')'):
                continue
            aktualne_riadky.append(text)

    # -----------------------------
    # Uloženie poslednej sekcie
    # -----------------------------
    if aktualna_sekcia and aktualne_riadky:
        obsah = "\n".join(aktualne_riadky).strip()
        if len(obsah) > 20:
            najdene_sekcie.append((aktualna_sekcia, obsah))
            log_debug(f"[LC-KBS] Uložená posledná sekcia: {aktualna_sekcia}")

    # -----------------------------
    # Fallback hľadanie refrénu
    # -----------------------------
    if not refreny_zalmov:
        log_debug("[LC-KBS] Refrén nebol nájdený v hlavnej slučke – spúšťam fallback.")
        try:
            cely_text = soup.get_text("\n")
            for riadok in cely_text.split("\n"):
                r = riadok.strip()
                if r.lower().startswith(('r.', 'r:')) and len(r) > 5:
                    cisty = _vycisti_refren(r)
                    if cisty and len(cisty) >= 8:
                        _pridaj_refren_zalmu(r)
        except Exception as e_fb:
            log_debug(f"[LC-KBS] Fallback hľadanie refrenu zlyhalo: {e_fb}")

    # ------------------------------------------------------------
    # Formátovanie výstupu
    # ------------------------------------------------------------

    # Najprv pridáme všetky čítania
    for nadpis, obsah in najdene_sekcie:
        vystup.append("-" * 60)
        vystup.append(nadpis.upper())
        vystup.append("-" * 60)
        vystup.append(_vycisti_text_lc_kbs(obsah))
        vystup.append("")

    # Pridáme refrény žalmov – vždy, ak existujú (pokrýva aj fallback prípad bez čítaní)
    for refren_zalmu in refreny_zalmov:
        vystup.append("-" * 60)
        vystup.append("REFRÉN ŽALMU")
        vystup.append("-" * 60)
        vystup.append(refren_zalmu)
        vystup.append("")
    if refreny_zalmov:
        log_debug(f"[LC-KBS] Pridané refrény žalmov do výstupu: {len(refreny_zalmov)}")

    log_debug("[LC-KBS] Extrahovanie dokončené.")
    return vystup


def _vycisti_text_lc_kbs(text):
    """
    Vyčistí text z lc.kbs.sk a inteligentne spája rozbité úvodzovky aj cez prázdne riadky.
    Opravuje aj osamotenú hornú úvodzovku “ na samostatnom riadku.
    """

    if not text:
        return ""

    # 1. Automatický prevod HTML entít
    text = html.unescape(text)

    # 2. Odstránenie neviditeľných a problematických znakov
    text = re.sub(r'[\u200b\ufeff\r\u200c\u200d\u2060]', '', text)
    text = text.replace('\xa0', ' ')  # pevná medzera

    # 3. Normalizácia medzier
    text = re.sub(r' +', ' ', text)
    
    # 3a. Opravy medzier okolo zátvoriek a pred '#'
    text = re.sub(r'(\S)\(', r'\1 (', text)   # slovo( → slovo (
    text = re.sub(r'\)(\S)', r') \1', text)   # )slovo → ) slovo
    text = re.sub(r'(\w)\(', r'\1 (', text)   # slovo1(slovo2) → slovo1 (slovo2)
    text = re.sub(r'\)(\w)', r') \1', text)   # (slovo2)slovo3 → (slovo2) slovo3
    text = re.sub(r'(\w)#', r'\1 #', text)    # slovo3# → slovo3 #

    # 3b. Oprava chýbajúcich medzier okolo zátvoriek a pred '#'
    text = re.sub(r'(\w)\(', r'\1 (', text)   # slovo1(slovo2) → slovo1 (slovo2)
    text = re.sub(r'\)(\w)', r') \1', text)   # (slovo2)slovo3 → (slovo2) slovo3
    text = re.sub(r'(\w)#', r'\1 #', text)    # slovo3# → slovo3 #  
   
    # 4. Normalizácia prázdnych riadkov
    text = re.sub(r'\n\s*\n+', '\n\n', text)

    # 5. Rozdelenie na riadky (odstránime len koncové medzery)
    riadky = [r.rstrip() for r in text.split('\n')]
    final_lines = []

    # 6. Všetky typy úvodzoviek
    quote_chars = set("„“”‟\"'‚‘’")

    for line in riadky:

        # prázdny riadok ide rovno do výstupu
        if not line:
            final_lines.append("")
            continue

        cleaned_no_space = line.replace(" ", "")

        # test: obsahuje riadok len úvodzovky?
        is_only_quotes = cleaned_no_space and all(ch in quote_chars for ch in cleaned_no_space)

        if is_only_quotes and final_lines:
            # nájdi posledný neprázdny riadok
            idx = len(final_lines) - 1
            while idx >= 0 and not final_lines[idx].strip():
                idx -= 1

            if idx >= 0:
                log_debug(
                    f"[CITANIA] Spájam osamotenú úvodzovku '{cleaned_no_space}' "
                    f"so riadkom: '{final_lines[idx]}'"
                )
                final_lines[idx] = final_lines[idx] + cleaned_no_space
                continue

        # inak normálne pridáme riadok
        final_lines.append(line)

    # 7. Odstránenie trojitých entrov
    vysledok = "\n".join(final_lines)
    vysledok = re.sub(r'\n{3,}', '\n\n', vysledok)

    return vysledok.strip()

# =============================================================
# BREVIAR.KBS.SK – STIAHNUTIE VEŠPIER
# =============================================================
#
# POZNÁMKY K LITURGICKEJ ŠTRUKTÚRE ŽALMOV A PROJEKCII
#
# HVIEZDIČKA ( * )
#   Delí verš na dve polovice – prvá a druhá polovica patria
#   k tomu istému veršu a pokračujú na ďalšom riadku.
#   Za riadkom končiacim * preto NESMIE byť prázdny riadok.
#
# ČERVENÝ KRÍŽIK ( † )
#   Verš je rozdelený na tri časti: pred †, medzi † a *, za *.
#   Ak sa antifóna zhoduje so začiatkom žalmu, v texte žalmu
#   je na tom mieste †. Znamená: "neopakuj tie slová, pokračuj
#   až za krížikom." Pri speve sa text zaspieva dvakrát, lebo
#   melódia antifóny je iná ako melódia žalmu.
#   Za riadkom končiacim † preto NESMIE byť prázdny riadok.
#
# PRÁZDNY RIADOK = STROFA
#   Prázdny riadok medzi skupinami veršov označuje hranicu strofy.
#   Každá strofa sa zobrazuje na jednej obrazovke projektora.
#
# STRIEDANIE CHÓROV
#   Pri každej zmene strofy (= zmene obrazovky) sa striedajú chóry:
#   prvú strofu recituje ľavý chór, druhú pravý, atď.
#   Označenie chórov sa do súboru nevkladá – riadi sa tým kantor.
#
# =============================================================

_BREVIAR_BASE    = "https://breviar.kbs.sk"
_BREVIAR_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def _breviar_url_vespery(d) -> str:
    return f"{_BREVIAR_BASE}/cgi-bin/l.cgi?qt=pdt&d={d.day}&m={d.month}&r={d.year}&p=mv"

_BREVIAR_SKIP_EXACT = {
    "×", "Dnes", "Téma", "Texty", "Informácie", "Download", "Jazyk", "▼",
    "čeština", "latinčina", "maďarčina", "islandčina", "čeština/dominikánsky",
    "vpravo ⚞", "⚟ vľavo", "☰", "breviar.sk", "Juraj Vidéky",
    "↑ navrch", "↓ naspodok", # "*", "†",
    "Ako bolo", "Aleluja.", "Aleluja",
    "i Synu i Duchu Svätému",
    "Žalm", "Chválospev",
    "Chválospev na meno Pánovo",
    "Vešpery", "Prvé vešpery", "Druhé vešpery",
    "(", ")",
}
_BREVIAR_SKIP_PREFIX = (
    "© ", "pre Kongregáciu", "pre Spoločnosť", "pre františk",
    "pre sale", "pre Rehoľu", "pre bosých", "pre kanon", "pre uršul",
    "pre premonštr", "pre rehoľu Piar", "pre Misijn",
    "Kalendár Liturgie", "1999-20", "Text © KBS",
    # Vysvetľujúce poznámky k spievanej/recitovanej forme
    "v zátvorkách", "na začiatku a na konci",
    "Ak sa iba recituje", "Ak sa spieva",
    "O Baránkovej", "Porov.", "Porov ",
    # Navigačné odkazy na alternatívny hymnus (napr. "(iný hymnus (2/2) »)")
    "(iný hymnus",
    # Poznámka o pracovnom preklade hymnu
    "Pracovný preklad",
)
_BREVIAR_SKIP_RE = re.compile(
    r"^("
    r"\(zobraziť.*\)|"
    r"\(skryť.*\)|"
    r"\(použiť.*\)|"
    r"[IVX]+|"
    r"\d+[,.\s]*\d*|"
    r"[A-Z][a-z]+ \d+,.*|"
    r"Zjv.*|"
    r"[.\s·•,;:×☰⚞⚟©▼»«↑↓\-=†]+"
    r")$"
)

_BREVIAR_MAGNIFICAT = [
    "Velebí *",
    "moja duša Pána",
    "",
    "a môj duch jasá *",
    "v Bohu, mojom Spasiteľovi,",
    "",
    "lebo zhliadol na poníženosť svojej služobnice. *",
    "Hľa, od tejto chvíle blahoslaviť ma budú všetky pokolenia,",
    "",
    "lebo veľké veci mi urobil ten, ktorý je mocný, *",
    "a svätý je jeho meno",
    "",
    "a jeho milosrdenstvo z pokolenia na pokolenie *",
    "s tými, čo sa ho boja.",
    "",
    "Ukázal silu svojho ramena, *",
    "rozptýlil tých, čo v srdci pyšne zmýšľajú.",
    "",
    "Mocnárov zosadil z trónov *",
    "a povýšil ponížených.",
    "",
    "Hladných nakŕmil dobrotami *",
    "a bohatých prepustil naprázdno.",
    "",
    "Ujal sa Izraela, svojho služobníka, *",
    "lebo pamätá na svoje milosrdenstvo,",
    "",
    "ako sľúbil našim otcom, *",
    "Abrahámovi a jeho potomstvu naveky.",
    "",
    "Sláva Otcu i Synu *",
    "i Duchu Svätému.",
    "",
    "Ako bolo na počiatku, tak nech je i teraz i vždycky *",
    "i na veky vekov. Amen.",
]

def _breviar_preskoc(t: str) -> bool:
    t = t.replace("\xa0", " ").strip()

    # ---------------------------------------------------------
    #  Nikdy nepreskakovať úvodné liturgické riadky
    # ---------------------------------------------------------
    if t in (
        "Bože, príď mi na pomoc.",
        "Pane, ponáhľaj sa mi pomáhať.",
        "Sláva Otcu i Synu *",
        "i Duchu Svätému.",
        "Ako bolo na počiatku, tak nech je i teraz i vždycky *",
        "i na veky vekov. Amen.",
    ):
        return False

    # ---------------------------------------------------------
    #  Pôvodná logika preskakovania
    # ---------------------------------------------------------
    if t in _BREVIAR_SKIP_EXACT:
        return True
    if any(t.startswith(p) for p in _BREVIAR_SKIP_PREFIX):
        return True
    if "Mocnárov zosadil" in t and "*" not in t:
        return True
    if _BREVIAR_SKIP_RE.match(t):
        return True

    return False


def _breviar_extrahuj(soup) -> list:
    for sid in ("mySidebar", "mySidebarR", "myOpenbtnL", "myOpenbtnR"):
        el = soup.find(id=sid)
        if el:
            el.decompose()
    for cls in ("sidebar", "sidebarR", "openbtn", "openbtnR",
                "calendar", "dropdown-btn", "dropdown-container", "tts_mute"):
        for el in soup.find_all(class_=cls):
            el.decompose()

    raw_lines = [line.strip() for line in soup.get_text("\n").splitlines()]

    # --- Hľadanie začiatku ---
    zac = None
    for i, r in enumerate(raw_lines):
        if r.lower() in ("vešpery", "prvé vešpery", "druhé vešpery"):
            zac = i
            log_debug(f"[BREVIAR] Začiatok nájdený cez nadpis vešpier: riadok {i} → '{r}'")
            break

    if zac is None:
        for i, r in enumerate(raw_lines):
            if "(skryť" in r.lower() and "navigáci" in r.lower():
                zac = i + 1
                log_debug(f"[BREVIAR] Začiatok nájdený cez navigačný fallback: riadok {i + 1}")
                break

    if zac is None:
        log_debug(
            "[BREVIAR] VAROVANIE: Začiatok obsahu sa nenašiel – použitý fallback zac=0. "
            "Štruktúra breviar.kbs.sk sa mohla zmeniť."
        )
        zac = 0

    # --- Hľadanie konca ---
    # Hľadáme PRVÝ výskyt "↑ navrch" za začiatkom obsahu (nie posledný),
    # aby sme nezahrnuli prípadné Prvé vešpery ďalšej slávnosti, ktoré
    # môžu nasledovať na tej istej stránke breviar.kbs.sk.
    kon = len(raw_lines)
    nasiel_koniec = False
    for i in range(zac, len(raw_lines)):
        if raw_lines[i] == "↑ navrch":
            kon = i
            nasiel_koniec = True
            log_debug(f"[BREVIAR] Koniec nájdený cez '↑ navrch': riadok {i}")
            break

    if not nasiel_koniec:
        log_debug(
            f"[BREVIAR] VAROVANIE: Marker '↑ navrch' nebol nájdený – "
            f"použitý fallback kon={kon} (celý zvyšok stránky). "
            "Štruktúra breviar.kbs.sk sa mohla zmeniť."
        )

    obsah = raw_lines[zac:kon]

    # --- Hľadanie konca modlitby ---
    for i, r in enumerate(obsah):
        if r in ("Otče náš", "MODLITBA"):
            log_debug(f"[BREVIAR] Obsah skrátený na marker '{r}': riadok {i}")
            return obsah[:i]

    log_debug(
        "[BREVIAR] VAROVANIE: Stop-marker 'Otče náš'/'MODLITBA' nebol nájdený – "
        f"vrátený celý obsah ({len(obsah)} riadkov). "
        "Výstup môže obsahovať nadbytočný text."
    )
    return obsah

# Konštanty pre _breviar_formatuj – definované na úrovni modulu,
# nie vo vnútri slučky, aby sa nealokovali opakovane pri každej iterácii.

# Fragmenty textu „Sláva Otcu", ktoré sa po spracovaní preskakujú z raw vstupu.
_SLAVA_FRAGMENTY = frozenset({
    "Ako bolo", "i na veky vekov. Amen.",
    "Aleluja.", "Aleluja",
    "i Synu i Duchu Svätému",
    "i Duchu Svätému.", "i Duchu Svätému",
})

# Riadky, ktoré tvoria samostatný odsek (prázdny riadok pred aj za).
_VLASTNY_ODSEK = frozenset({
    "Bože, príď mi na pomoc.",
    "Pane, ponáhľaj sa mi pomáhať.",
})


_BREVIAR_SEKCIE = {"HYMNUS", "PSALMÓDIA", "KRÁTKE ČÍTANIE", "KRÁTKE RESPONZÓRIUM",
                   "EVANJELIOVÝ CHVÁLOSPEV", "PROSBY"}


def _formatuj_kratke_responzorium(riadky_raw: list, zaciatok: int) -> tuple:
    """
    Spracuje blok krátkeho responzória od pozície `zaciatok`.
    Vracia (zoznam_riadkov, nová_pozícia_i).
    Volaná z _breviar_formatuj.
    """
    skupiny = []
    skupina = []
    zachovat = {"Aleluja.", "Aleluja", "i Synu i Duchu Svätému"}
    k = zaciatok
    while k < len(riadky_raw):
        r = riadky_raw[k].replace("\xa0", " ").strip()
        if r in _BREVIAR_SEKCIE:
            break
        if r == "Ant. na Magnifikat:" or r in ("Otče náš", "MODLITBA"):
            break
        if r == "":
            if skupina:
                skupiny.append(skupina)
                skupina = []
        elif r in zachovat or not _breviar_preskoc(r):
            skupina.append(r)
        k += 1
    if skupina:
        skupiny.append(skupina)

    riadky = []
    for skupina in skupiny:
        if not skupina:
            continue

        if skupina[0].startswith("Sláva Otcu"):
            if len(skupina) > 1 and skupina[1] == "i Synu i Duchu Svätému":
                riadky.append("Sláva Otcu i Synu i Duchu Svätému.")
            else:
                text = " ".join(skupina)
                riadky.append(text if text.endswith(".") else text + ".")
            continue

        if "*" in skupina:
            hviezda = skupina.index("*")
            zaciatok_textu = " ".join(skupina[:hviezda]).strip()
            odpoved = " ".join(skupina[hviezda + 1:]).strip()
            if not odpoved.endswith("."):
                odpoved += "."
            riadky.append(f"{zaciatok_textu} * {odpoved}")
        else:
            riadky.append(" ".join(skupina))

    return riadky, k


def _zbieraj_ant(riadky_raw: list, zaciatok: int) -> tuple:
    """
    Zbiera viacriadkový text antifóny (vrátane Aleluja.) od danej pozície.
    Vracia (text_antifony, nová_pozícia_i).
    Volaná z _breviar_formatuj.
    """
    casti = []
    k = zaciatok
    while k < len(riadky_raw):
        rl = riadky_raw[k].strip()
        if rl == "" or rl in _BREVIAR_SEKCIE:
            break
        if rl in ("Aleluja.", "Aleluja"):   # zachovaj aj keď je v SKIP_EXACT
            casti.append(rl)
        elif not _breviar_preskoc(rl):
            casti.append(rl)
        k += 1
    return " ".join(casti), k


def _breviar_formatuj(riadky_raw: list) -> list:
    vystup = []
    i = 0
    predosly_bol_text = False
    v_hymne = False
    aktualna_sekcia = None  # sledujeme aktuálnu sekciu

    SEKCIE = _BREVIAR_SEKCIE

    while i < len(riadky_raw):
        t = riadky_raw[i]

        if t == "":
            if predosly_bol_text:
                if v_hymne and vystup and vystup[-1] != "":
                    vystup[-1] = vystup[-1] + " _"
                vystup.append("")
                predosly_bol_text = False
            i += 1
            continue

        # Riadok začínajúci čiarkou je zalomenie z HTML – prilepíme k predošlému riadku
        if t.startswith(", ") and vystup and vystup[-1] != "":
            vystup[-1] = vystup[-1].rstrip() + t
            i += 1
            continue

        # ------------------------------------------------------------------
        #  OTVÁRACIE ALELUJA. V PSALMÓDII (nedeľná štruktúra chválospevu)
        #  Ak Aleluja. stojí tesne pred veršom s *, zachováme ho ako
        #  prvý riadok strofy (dostane [L]/[P] v oznac_chory).
        #  Ak nie je pred *, je to fragment Slávy Otcu → preskočiť.
        # ------------------------------------------------------------------
        if t in ("Aleluja.", "Aleluja") and aktualna_sekcia == "PSALMÓDIA":
            k = i + 1
            while k < len(riadky_raw) and riadky_raw[k].strip() == "":
                k += 1
            nasledujuci = riadky_raw[k].strip() if k < len(riadky_raw) else ""
            if "*" in nasledujuci:
                if nasledujuci.startswith("Aleluja."):
                    vystup.append("Aleluja.")
                    predosly_bol_text = True
                    i += 1
                    continue
                # Otváracie Aleluja. patrí na ten istý riadok ako prvý verš strofy.
                if vystup and vystup[-1] != "":
                    vystup.append("")
                vystup.append("Aleluja. " + nasledujuci)
                predosly_bol_text = True
                i = k + 1
                continue
            # inak (fragment Slávy Otcu) – preskočiť
            i += 1
            continue
        # ------------------------------------------------------------------

        if _breviar_preskoc(t):
            i += 1
            continue

        if t in SEKCIE:
            v_hymne = (t == "HYMNUS")
            aktualna_sekcia = t
            if vystup and vystup[-1] != "":
                vystup.append("")
            vystup.append(t)
            vystup.append("")
            predosly_bol_text = False
            i += 1

            if t == "PROSBY":
                zvolanie = None
                # Predpočítame frekvenciu riadkov od aktuálnej pozície jednorazovo
                # v O(n). Pôvodné `r in riadky_raw[i+1:]` vytváralo nový slice
                # v každej iterácii cyklu, čo je O(n²) celkovo.
                # Riadok s frekvenciou > 1 sa v úseku PROSBY opakuje → je to zvolanie.
                _prosby_pocty: dict = {}
                for _pr in riadky_raw[i:]:
                    _prosby_pocty[_pr] = _prosby_pocty.get(_pr, 0) + 1
                while i < len(riadky_raw):
                    r = riadky_raw[i]
                    if r in SEKCIE or r in ("Otče náš", "MODLITBA"):
                        break
                    if r and not _breviar_preskoc(r) and zvolanie is None:
                        if _prosby_pocty.get(r, 0) > 1:
                            zvolanie = r
                    i += 1
                if zvolanie:
                    vystup.append(zvolanie)
                predosly_bol_text = True
                continue

            if v_hymne:
                hymnus_riadky = []
                while i < len(riadky_raw):
                    r = riadky_raw[i]
                    if r in SEKCIE or r.startswith("Sláva Otcu") or r == "PSALMÓDIA":
                        break
                    if r and not _breviar_preskoc(r):
                        hymnus_riadky.append(r)
                    i += 1
                for idx, rl in enumerate(hymnus_riadky):
                    vystup.append(rl)
                    je_koniec_strofy = (idx + 1) % 4 == 0
                    je_posledny = (idx + 1 == len(hymnus_riadky))
                    if je_koniec_strofy or je_posledny:
                        vystup[-1] = vystup[-1] + " _"
                        if not je_posledny:
                            vystup.append("")
                predosly_bol_text = True
                v_hymne = False
            elif t == "KRÁTKE RESPONZÓRIUM":
                responzorium, i = _formatuj_kratke_responzorium(riadky_raw, i)
                for idx, riadok in enumerate(responzorium):
                    if idx:
                        vystup.append("")
                    vystup.append(riadok)
                predosly_bol_text = bool(responzorium)
            continue

        # ---------------------------------------------------------
        #  OPRAVENÁ ČASŤ — KRÁTKE RESPONZÓRIUM MÁ VÝNIMKU
        # ---------------------------------------------------------
        if t.startswith("Sláva Otcu"):            

            # Výnimka: v KRÁTKE RESPONZÓRIUM sa text NEUPRAVUJE
            if aktualna_sekcia == "KRÁTKE RESPONZÓRIUM":
                if vystup and vystup[-1] != "":
                    vystup.append("")
                i += 1
                if i < len(riadky_raw) and riadky_raw[i].replace("\xa0", " ").strip() == "i Synu i Duchu Svätému":
                    vystup.append("Sláva Otcu i Synu i Duchu Svätému.")
                    predosly_bol_text = True
                    i += 1
                    continue
                vystup.append(t)   # presne tak, ako je na webe
                predosly_bol_text = True
                continue

            # Štandardné spracovanie pre žalmy a chválospevy
            if vystup and vystup[-1] != "":
                vystup.append("")
            vystup.append("Sláva Otcu i Synu *")
            vystup.append("i Duchu Svätému.")
            vystup.append("")
            vystup.append("Ako bolo na počiatku, tak nech je i teraz i vždycky *")
            vystup.append("i na veky vekov. Amen.")

            predosly_bol_text = True

            i += 1
            while i < len(riadky_raw) and riadky_raw[i].strip() in _SLAVA_FRAGMENTY | {""}:
                i += 1
            continue
        # ---------------------------------------------------------

        if t == "Ant. na Magnifikat:":
            j = i + 1
            while j < len(riadky_raw) and riadky_raw[j].strip() == "":
                j += 1
            ant_text = riadky_raw[j] if j < len(riadky_raw) and not _breviar_preskoc(riadky_raw[j]) else ""
            if vystup and vystup[-1] != "":
                vystup.append("")
            if ant_text:
                vystup.append(f"Ant. na Magnifikat: {ant_text}")
                i = j + 1
            else:
                vystup.append(t)
                i += 1
            vystup.append("")
            vystup.extend(_BREVIAR_MAGNIFICAT)
            vystup.append("")
            if ant_text:
                vystup.append(f"Ant.: {ant_text}")
            predosly_bol_text = True
            continue

        if re.match(r"^Ant\.\s*\d*$", t):
            cislo = t.replace("Ant.", "").strip()
            je_zatváracia = (cislo == "")
            j = i + 1
            while j < len(riadky_raw) and riadky_raw[j].strip() == "":
                j += 1

            if je_zatváracia:
                # Sláva Otcu – skontroluj, či v raw PRED Ant. nasleduje Sláva-fragment;
                # ak áno, raw handler ju vloží sám; ak nie (niektoré žalmy ju vynechávajú),
                # vložíme ju tu.
                # Pozri sa dozadu v raw: je medzi posledným neprázdnym
                # a aktuálnym indexom i nejaký Sláva-fragment?
                slava_v_raw = any(
                    riadky_raw[k].strip() in ("Sláva Otcu i Synu", "Sláva Otcu i Synu *")
                    for k in range(max(0, i - 15), i)
                )
                if not slava_v_raw:
                    if vystup and vystup[-1] != "":
                        vystup.append("")
                    vystup.append("Sláva Otcu i Synu *")
                    vystup.append("i Duchu Svätému.")
                    vystup.append("")
                    vystup.append("Ako bolo na počiatku, tak nech je i teraz i vždycky *")
                    vystup.append("i na veky vekov. Amen.")
                vystup.append("")
                ant_text, i = _zbieraj_ant(riadky_raw, j)
                if ant_text:
                    vystup.append(f"Ant. {ant_text}")
                else:
                    i += 1
                predosly_bol_text = True
                continue

            ant_text, i = _zbieraj_ant(riadky_raw, j)
            if vystup and vystup[-1] != "":
                vystup.append("")
            if ant_text:
                vystup.append(f"Ant. {cislo} {ant_text}".strip())
            else:
                vystup.append(t)
            # preskočíme na prvý žalmový verš (s *) alebo na Aleluja. (nedeľná psalmódia)
            while i < len(riadky_raw) and "*" not in riadky_raw[i] and riadky_raw[i].strip() not in ("Aleluja.", "Aleluja"):
                i += 1
            vystup.append("")
            predosly_bol_text = False
            continue

        # ------------------------------------------------------------------
        #  RÉFRÉN V PSALMÓDII – recitovaná forma
        # ------------------------------------------------------------------
        # (R. Aleluja.) – spievaná forma medzi polveršami: pri recitácii vynechať
        if t.startswith("(R."):
            k = i + 1
            while k < len(riadky_raw) and riadky_raw[k].strip() in (
                    "", "Aleluja.", "Aleluja", ")"):
                k += 1
            # Nič nevypisujeme – pri recitácii sa réfrén medzi polveršami nehovorí
            i = k
            continue

        # R. Aleluja. (Aleluja.) – záverečný réfrén strofy → len „Aleluja."
        # Odoberie prázdny riadok PRED sebou, aby Aleluja. zostalo SÚČASŤOU strofy.
        # Prázdny riadok ZA blokom (pred ďalšou strofou) ponecháme – bude spracovaný ďalej.
        if t == "R." and aktualna_sekcia == "PSALMÓDIA":
            k = i + 1
            while k < len(riadky_raw) and riadky_raw[k].strip() in (
                    "Aleluja.", "Aleluja", "(Aleluja.)"):
                k += 1
            if vystup and vystup[-1] == "":
                vystup.pop()   # stiahne medzeru pred R. aby Aleluja. bolo v tej istej strofe
            vystup.append("Aleluja.")
            predosly_bol_text = True
            i = k
            continue
        # ------------------------------------------------------------------

        if t in _VLASTNY_ODSEK:
            if vystup and vystup[-1] != "":
                vystup.append("")
            vystup.append(t)
            vystup.append("")
            predosly_bol_text = False
            i += 1
            continue

        vystup.append(t)
        predosly_bol_text = True
        i += 1

    while vystup and not vystup[0]:
        vystup.pop(0)
    while vystup and not vystup[-1]:
        vystup.pop()

    vysledok = []
    for r in vystup:
        if r == "" and vysledok and (vysledok[-1].endswith("*") or vysledok[-1].endswith("†")):
            continue
        vysledok.append(r)
    return vysledok

def _normalizuj_aleluja_v_tretej_antifone_psalmodie(riadky: list) -> list:
    """Upravi uvodne Aleluja. v strofach Ant. 3 podla zaverecneho Aleluja."""
    PREFIX_RE = re.compile(r"^(\[(?:L|P)\]\s*)(.*)$")
    PRVY_RIADOK_RE = re.compile(r"^(\[(?:L|P)\]\s*)?(.*)$")
    SEKCIE = {"HYMNUS", "PSALMÓDIA", "KRÁTKE ČÍTANIE", "KRÁTKE RESPONZÓRIUM",
              "EVANJELIOVÝ CHVÁLOSPEV", "PROSBY", "MODLITBA"}
    pouziva_prefixy_chorov = any(PREFIX_RE.match(r) for r in riadky)

    def uprav_strofu(strofa: list) -> list:
        if not strofa:
            return strofa

        m = PRVY_RIADOK_RE.match(strofa[0])
        if not m:
            return strofa

        prefix, prvy_text = m.groups()
        prefix = prefix or ""
        prvy_text = prvy_text.strip()
        zvysok = strofa[1:]

        if prvy_text == "Aleluja.":
            for idx, riadok in enumerate(zvysok):
                text = riadok.strip()
                if not text:
                    continue
                prvy_text = text if text.startswith("Aleluja.") else "Aleluja. " + text
                del zvysok[idx]
                break

        koniec_idx = None
        for idx in range(len(zvysok) - 1, -1, -1):
            if zvysok[idx].strip():
                koniec_idx = idx
                break

        posledny_text = prvy_text if koniec_idx is None else zvysok[koniec_idx].strip()
        konci_aleluja = posledny_text.endswith("Aleluja.")
        zacina_aleluja = prvy_text.startswith("Aleluja.")

        if konci_aleluja and not zacina_aleluja:
            prvy_text = "Aleluja. " + prvy_text if prvy_text else "Aleluja."
        elif zacina_aleluja and not konci_aleluja:
            prvy_text = prvy_text[len("Aleluja."):].lstrip()
            if not prvy_text:
                for idx, riadok in enumerate(zvysok):
                    text = riadok.strip()
                    if not text:
                        continue
                    prvy_text = text
                    del zvysok[idx]
                    break

        return [prefix + prvy_text] + zvysok

    vysledok = []
    aktualna_sekcia = None
    v_tretej_antifone = False
    strofa = []

    def vyprazdni_strofu():
        nonlocal strofa
        if strofa:
            vysledok.extend(uprav_strofu(strofa))
            strofa = []

    for r in riadky:
        if r in SEKCIE:
            vyprazdni_strofu()
            aktualna_sekcia = r
            v_tretej_antifone = False
            vysledok.append(r)
            continue

        if aktualna_sekcia == "PSALMÓDIA" and r.startswith("Ant."):
            vyprazdni_strofu()
            v_tretej_antifone = r.startswith("Ant. 3")
            vysledok.append(r)
            continue

        if v_tretej_antifone and PREFIX_RE.match(r):
            vyprazdni_strofu()
            strofa = [r]
            continue

        if v_tretej_antifone and not pouziva_prefixy_chorov:
            if strofa:
                strofa.append(r)
                if not r.strip():
                    vyprazdni_strofu()
                continue

            if r.strip():
                strofa = [r]
            else:
                vysledok.append(r)
            continue

        if strofa:
            strofa.append(r)
        else:
            vysledok.append(r)

    vyprazdni_strofu()
    return vysledok

def oznac_chory(riadky: list, oznacit_lp: bool = True) -> list:
    """
    Označí riadky prefixmi pre striedanie chórov.

    oznacit_lp=True  – pridáva [L]/[P] aj V./R.
    oznacit_lp=False – pridáva iba V./R. (KRÁTKE RESPONZÓRIUM);
                       [L]/[P] pre HYMNUS, PSALMÓDIA a MAGNIFIKAT sa vynechajú.
    """
    vys = []
    aktualna_sekcia = None
    lavyp = True
    v_strofe = False
    vr_striedanie = True
    v_magnifikate = False
    v_alelujovom_chvalospeve = False

    for r in riadky:

        # Sekcie
        if r in ("HYMNUS", "PSALMÓDIA", "KRÁTKE ČÍTANIE", "KRÁTKE RESPONZÓRIUM", "EVANJELIOVÝ CHVÁLOSPEV"):
            aktualna_sekcia = r
            lavyp = True
            v_strofe = False
            vr_striedanie = True
            v_magnifikate = False
            vys.append(r)
            continue

        # Antifóna na Magnifikat
        if r.startswith("Ant. na Magnifikat"):
            v_magnifikate = True
            lavyp = True
            v_strofe = False
            vys.append(r)
            continue

        # Ant. (po Magnifikate)
        if r.startswith("Ant.:"):
            v_magnifikate = False
            vys.append(r)
            continue

        # MAGNIFIKAT
        if v_magnifikate:
            if r.strip() == "":
                v_strofe = False
                vys.append(r)
                continue

            if not v_strofe:
                if oznacit_lp:
                    prefix = "[L] " if lavyp else "[P] "
                    vys.append(prefix + r)
                else:
                    vys.append(r)
                v_strofe = True
                lavyp = not lavyp
            else:
                vys.append(r)
            continue

        # KRÁTKE RESPONZÓRIUM
        if aktualna_sekcia == "KRÁTKE RESPONZÓRIUM":
            if r.strip() == "":
                vys.append(r)
                continue

            if r.startswith(("V. ", "R. ")):
                vys.append(r)
            else:
                prefix = "V. " if vr_striedanie else "R. "
                vys.append(prefix + r)
            vr_striedanie = not vr_striedanie
            continue

        # Antifóny – nikdy neoznačujeme
        if r.startswith("Ant."):
            # Detekcia alelujového chválospevu IBA podľa Ant. 3
            if r.startswith("Ant. 3"):
                v_alelujovom_chvalospeve = True
            else:
                v_alelujovom_chvalospeve = False

            vys.append(r)
            continue

        # Prázdny riadok = koniec strofy
        if r.strip() == "":
            v_strofe = False
            vys.append(r)
            continue

        # HYMNUS
        if aktualna_sekcia == "HYMNUS":
            if not v_strofe:
                if oznacit_lp:
                    prefix = "[L] " if lavyp else "[P] "
                    vys.append(prefix + r)
                else:
                    vys.append(r)
                v_strofe = True
                lavyp = not lavyp
            else:
                vys.append(r)
            continue

        # PSALMÓDIA
        if aktualna_sekcia == "PSALMÓDIA":

            # ============================================================
            #  ALELUJOVÝ CHVÁLOSPEV (Ant. 3)
            # ============================================================
            if v_alelujovom_chvalospeve:

                # ❗ DOXOLÓGIA – nesmie dostať Aleluja.
                if r.startswith("Sláva Otcu") or r.startswith("Ako bolo"):
                    if not v_strofe:
                        if oznacit_lp:
                            prefix = "[L] " if lavyp else "[P] "
                            vys.append(prefix + r)
                        else:
                            vys.append(r)
                        v_strofe = True
                        lavyp = not lavyp
                    else:
                        vys.append(r)
                    continue

                # Štandardná strofa chválospevu
                if not v_strofe:
                    # prefix + Aleluja.
                    if oznacit_lp:
                        prefix = "[L] " if lavyp else "[P] "
                        vys.append(prefix + "Aleluja.")
                    else:
                        vys.append("Aleluja.")

                    lavyp = not lavyp
                    v_strofe = True

                    # prvý riadok strofy
                    vys.append(r)

                else:
                    vys.append(r)

                continue

            # ============================================================
            #  ŠTANDARDNÉ ŽALMY (Ant. 1 a Ant. 2)
            # ============================================================
            if not v_strofe:
                if oznacit_lp:
                    prefix = "[L] " if lavyp else "[P] "
                    vys.append(prefix + r)
                else:
                    vys.append(r)
                v_strofe = True
                lavyp = not lavyp
            else:
                vys.append(r)

            continue

        # Ostatné sekcie
        vys.append(r)

    return vys

def stiahni_vespery_z_breviar(datum, vystup_cesta, oznacit_chory=True):
    """
    Stiahne Vešpery z breviar.kbs.sk a uloží do TXT súboru
    vo formáte pripravenom na projekciu.

    Args:
        datum:        date objekt
        vystup_cesta: Path objekt (napr. Path("piesne/vespery.txt"))
        oznacit_chory: zachované pre kompatibilitu volaní; zobrazenie/skrytie
                       [L]/[P] sa rieši až pri projekcii podľa nastavení.

    Returns:
        bool: True ak úspešné, False ak zlyhalo
    """
    url = None

    if chybaju_kniznice_pre_stahovanie():
        log_info("[BREVIAR] Stahovanie preskocene: chybaju requests alebo beautifulsoup4.")
        return False

    requests_module = requests
    beautiful_soup = BeautifulSoup
    assert requests_module is not None
    assert beautiful_soup is not None

    try:
        log_info(f"[BREVIAR] Sťahujem vešpery pre {datum.isoformat()} ...")
        url = _breviar_url_vespery(datum)

        resp = requests_module.get(url, headers=_BREVIAR_HEADERS, timeout=20)
        resp.raise_for_status()
        enc = _zisti_http_kodovanie(resp, "BREVIAR", fallback="windows-1250")
        resp.encoding = enc
        log_info(f"[BREVIAR] Stiahnuté: {len(resp.text)} znakov, kódovanie: {resp.encoding}")

        soup = beautiful_soup(resp.text, "html.parser")
        raw  = _breviar_extrahuj(soup)
        riadky = _breviar_formatuj(raw)
        # Interný text vešpier drží značky chórov vždy, aby sa dali v nastaveniach
        # okamžite zobraziť/skryť bez opätovného sťahovania.
        riadky = oznac_chory(riadky, oznacit_lp=True)
        riadky = _normalizuj_aleluja_v_tretej_antifone_psalmodie(riadky)


        if len(riadky) < 10:
            log_info("[BREVIAR] Príliš málo textu – parsovanie zlyhalo.")
            return False

        hlavicka = [
            "VEŠPERY  –  VEČERNÁ CHVÁLA",
            datum.strftime("%d.%m.%Y"),
            "",
        ]
        celok = "\n".join(hlavicka + riadky)

        try:
            _zapis_text_atomicky(vystup_cesta, celok, encoding="utf-8")
        except UnicodeEncodeError as e_enc:
            log_exception(
                "[BREVIAR] Chyba kódovania pri zápise súboru – text obsahuje znaky "
                "mimo UTF-8. Súbor nebol uložený.",
                e_enc,
            )
            return False

        log_info(f"[BREVIAR] Hotovo – vešpery uložené: {vystup_cesta}")
        return True

    except requests_module.RequestException as e:
        log_exception(f"[BREVIAR] Chyba pri sťahovaní z URL: {url or 'neznáma'}", e)
        return False
    except Exception as e:
        log_exception("[BREVIAR] Neočakávaná chyba", e)
        return False

class ProjectionWindow:
    """Samostatné okno pre projekciu na druhej obrazovke."""

    def __init__(
        self,
        master,
        font_size,
        text_color=TEXT_COLOR,
        *,
        fade_enabled=DEFAULT_USE_FADE,
        bottom_margin=None,
        reserved_vertical_ratio=None,
        fade_speed=None,
        preferred_monitor_index=0
    ):
        self.master = master

        # Uloženie základnej veľkosti písma ako atribút inštancie.
        # ControlApp aktualizuje self.font_size pri každej zmene nastavení,
        # čím odstraňuje potrebu čítať globálnu premennú FONT_SIZE.
        self.font_size: int = int(font_size)

        try:
            self.master.overrideredirect(True)
        except Exception as e:
            log_exception("ProjectionWindow.overrideredirect", e)

        self.master.configure(bg=BACKGROUND_COLOR)

        # fade_speed
        self.fade_speed = (
            fade_speed if fade_speed is not None
            else DEFAULT_CONFIG["fade_speed"]
        )

        self.fade_enabled = bool(fade_enabled)

        # cache
        self.raw_text_content = ""
        self.current_text_content = ""
        self.current_title_text = ""

        self.target_text_color = text_color
        self._configure_after_id = None
        self._debounce_title_after_id = None
        
        # --- doplnené atribúty ---
        self.zobrazovat_live_preview: bool = False
        self.zobrazovat_specialne_znaky: bool = True
        self.zobrazovat_znaky_chorov: bool = True
        
                
        self.preferred_monitor_index = preferred_monitor_index

        # bottom_margin
        self.bottom_margin = (
            bottom_margin if bottom_margin is not None
            else DEFAULT_CONFIG["bottom_margin"]
        )

        # reserved_vertical_ratio
        self.reserved_vertical_ratio = (
            reserved_vertical_ratio if reserved_vertical_ratio is not None
            else DEFAULT_CONFIG["reserved_vertical_ratio"]
        )

        # ------------------------------------------------------------------
        # bezpečné načítanie ikony
        # ------------------------------------------------------------------
        ikon_path = Path(ICON_PNG)

        try:
            if ikon_path.is_file():
                _ikonka = tk.PhotoImage(file=str(ikon_path))
                try:
                    self.master.iconphoto(True, _ikonka)
                except Exception as e:
                    log_exception("ProjectionWindow.iconphoto", e)
                self._ikonka_ref = _ikonka
            else:
                self._ikonka_ref = tk.PhotoImage(width=1, height=1)

        except Exception as e:
            log_exception("ProjectionWindow.icon_load", e)
            try:
                self._ikonka_ref = tk.PhotoImage(width=1, height=1)
            except Exception as e2:
                log_exception("ProjectionWindow.icon_fallback", e2)
                self._ikonka_ref = None

        # ------------------------------------------------------------------
        # horný titulok — začína čierny (fade-in ho zafarbí)
        # ------------------------------------------------------------------
        safe_font_name = FONT_NAME or "Arial"

        self.title_label = tk.Label(
            self.master,
            text="",
            font=(safe_font_name, max(18, int(font_size * 0.25)), "bold"),
            anchor="n",
            justify=tk.CENTER,
            bg=BACKGROUND_COLOR,
            fg="#000000"
        )
        self.title_label.pack(side=tk.TOP, fill=tk.X, padx=20, pady=(20, 0))

        # ------------------------------------------------------------------
        # hlavné textové pole — začína čierne (fade-in ho zafarbí)
        # ------------------------------------------------------------------
        self.text_label = tk.Label(
            self.master,
            text="",
            font=(safe_font_name, font_size, "bold"),
            anchor="center",
            justify=tk.CENTER,
            bg=BACKGROUND_COLOR,
            fg="#000000",
            wraplength=self._compute_wraplength()  # dynamicky podľa rozlíšenia
        )
        self.text_label.pack(
            expand=True,
            fill=tk.BOTH,
            padx=10,
            pady=(0, self.bottom_margin)
        )

        self.current_color = "#000000"

        # maximalizácia na cieľový monitor
        self.move_and_maximize()

        # debounced resize handler
        try:
            self.master.bind("<Configure>", self._on_configure_debounced)
        except Exception as e:
            log_exception("ProjectionWindow.bind(<Configure>)", e)
        
    def _compute_wraplength(self):
        """
        Inteligentný výpočet wraplength pre projekciu.
        Rešpektuje:
            - šírku projekčného okna
            - WRAP_PADDING_RATIO (horizontálny padding)
            - minimálnu šírku textu
            - ultrawide monitory (21:9, 32:9)
        """
        try:
            win_w = self.master.winfo_width()
            if win_w < 200:  # fallback pri inicializácii
                win_w = self.master.winfo_screenwidth()

            # 1) Základný padding
            padding = int(win_w * WRAP_PADDING_RATIO)

            # 2) Základný wraplength
            wrap = win_w - (2 * padding)

            # 3) Minimálna šírka
            if wrap < MIN_WRAP:
                log_debug(f"wraplength extrémne nízky → {wrap}px, nastavujem MIN_WRAP={MIN_WRAP}")
            wrap = max(wrap, MIN_WRAP)

            # 4) Ultrawide optimalizácia
            win_h = self.master.winfo_height()
            if win_h < 50:
                win_h = self.master.winfo_screenheight()

            aspect_ratio = win_w / max(1, win_h)

            if aspect_ratio > 2.6:      # 32:9
                log_info(f"Ultrawide 32:9 detekovaný (AR={aspect_ratio:.2f}), wrap zmenšený na 60%")
                wrap = int(wrap * 0.60)
            elif aspect_ratio > 2.0:    # 21:9
                log_info(f"Ultrawide 21:9 detekovaný (AR={aspect_ratio:.2f}), wrap zmenšený na 75%")
                wrap = int(wrap * 0.75)

            # 5) Ergonomický horný limit
            if wrap > 1600:
                log_debug(f"wraplength extrémne vysoký → {wrap}px, obmedzujem na 1600px")
            wrap = min(wrap, 1600)

            return wrap

        except Exception as e:
            log_exception("_compute_wraplength: kritická chyba, vraciam fallback 800px", e)
            return 800  # bezpečný fallback    
    
    def _on_configure_debounced(self, event=None):
        # Zruší predchádzajúci naplánovaný callback (debouncing).
        old_id = getattr(self, "_configure_after_id", None)
        if old_id:
            try:
                self.master.after_cancel(old_id)
            except Exception as e:
                log_exception("_on_configure_debounced: after_cancel failed", e)
            self._configure_after_id = None

        # Naplánuje nový callback s debounce oneskorením.
        # Pri zlyhaní after() callback jednoducho preskočíme – ďalšia <Configure>
        # udalosť ho znova naplánuje. Synchronné volanie on_configure() tu zámerne
        # nie je: pri opakovanom zlyhaní by blokovalo UI pri každom pohybe okna.
        try:
            self._configure_after_id = self.master.after(150, self.on_configure)
        except Exception as e:
            log_exception("_on_configure_debounced: master.after failed, preskakujem", e)
            self._configure_after_id = None

    def on_configure(self, event=None):
        try:
            # FONT_SIZE môže byť str → bezpečne pretypujeme
            try:
                base_font_size = float(self.font_size)
            except (TypeError, ValueError):
                base_font_size = 24.0

            # 1) Bezpečné získanie rozmerov okna
            try:
                win_w = self.master.winfo_width()
                if win_w < 50:
                    win_w = self.master.winfo_screenwidth()
                win_w = max(200, win_w)

                win_h = self.master.winfo_height()
                if win_h < 50:
                    win_h = self.master.winfo_screenheight()
                win_h = max(200, win_h)
            except Exception as e:
                log_exception("on_configure: chyba pri zisťovaní rozmerov", e)
                return

            # 2) Výpočet wraplength
            try:
                wraplen = max(100, self._compute_wraplength())
                self.text_label.config(wraplength=wraplen)
            except Exception as e:
                log_exception("on_configure: chyba pri nastavovaní wraplength", e)

            # 3) Škálovanie písma
            try:
                base_width = 1920
                scale = min(1.0, win_w / base_width) if win_w > 0 else 1.0
                new_font_size = max(18, int(base_font_size * scale))

                self._apply_font_sizes(new_font_size)
            except Exception as e:
                log_exception("on_configure: chyba pri škálovaní písma", e)

            # 4) Aktualizácia UI úloh
            try:
                self.master.update_idletasks()
            except Exception as e:
                log_exception("on_configure: update_idletasks zlyhal", e)

        except Exception as e:
            log_exception("on_configure: KRITICKÉ ZLYHANIE METÓDY", e)

    # ------------------------------------------------------------
    #  APLIKÁCIA VEĽKOSTI PÍSMA
    # ------------------------------------------------------------
    def _apply_font_sizes(self, main_size):
        try:
            # ochrana pred extrémne malými hodnotami
            try:
                main_size = max(10, int(main_size))
            except (ValueError, TypeError) as e:
                log_exception("_apply_font_sizes: neplatná hodnota main_size", e)
                main_size = 40  # fallback hodnota

            safe_font_name: str = FONT_NAME or "Arial"

            # hlavný text
            try:
                self.text_label.config(font=(safe_font_name, main_size, "bold"))
            except Exception as e:
                log_exception("_apply_font_sizes: chyba pri nastavovaní text_label fontu", e)

            # titulok
            try:
                title_size = max(14, int(main_size * 0.42))
                self.title_label.config(font=(safe_font_name, title_size, "bold"))
            except Exception as e:
                log_exception("_apply_font_sizes: chyba pri nastavovaní title_label fontu", e)

        except Exception as e:
            log_exception("_apply_font_sizes: hlavná chyba metódy", e)        
                       
        
    # ------------------------------------------------------------
    #  PRESUN A MAXIMALIZÁCIA NA CIEĽOVÝ MONITOR
    # ------------------------------------------------------------
    def move_and_maximize(self):
        """Presunie projekčné okno na cieľový monitor a maximalizuje ho."""
        
        monitors = []
        # Skontrolujeme, či get_monitors nie je None, skôr než ho zavoláme
        if get_monitors is not None:
            try:
                monitors = get_monitors()
            except Exception as e:
                log_exception("move_and_maximize.get_monitors", e)
                monitors = []
        else:
            log_info("move_and_maximize: knižnica screeninfo nie je k dispozícii.")

        # fallback: fullscreen na primárnom monitore
        if not monitors:
            try:
                self.master.attributes("-fullscreen", True)
            except Exception as e:
                log_exception("move_and_maximize.no_monitors.fullscreen", e)
            return

        # preferovaný monitor
        pref = getattr(self, "preferred_monitor_index", None)
        if isinstance(pref, int) and 0 <= pref < len(monitors):
            target = monitors[pref]
        else:
            if len(monitors) == 1:
                target = monitors[0]
            else:
                # nájdi ne-primárny monitor
                non_primary = None
                for m in monitors:
                    if hasattr(m, "is_primary") and not getattr(m, "is_primary", False):
                        non_primary = m
                        break

                if non_primary:
                    target = non_primary
                else:
                    # fallback: najväčší monitor
                    try:
                        target = max(monitors, key=lambda m: m.width * m.height)
                    except Exception as e:
                        log_exception("move_and_maximize.select_largest_monitor", e)
                        target = monitors[0]

        # maximalizácia
        try:
            width = max(200, getattr(target, "width", self.master.winfo_screenwidth()))
            height = max(200, getattr(target, "height", self.master.winfo_screenheight()))
            x = int(getattr(target, "x", 0))
            y = int(getattr(target, "y", 0))

            self.master.overrideredirect(True)
            self.master.geometry(f"{width}x{height}+{x}+{y}")
            self.master.configure(bg=BACKGROUND_COLOR)

        except Exception as e:
            log_exception("move_and_maximize.apply_geometry", e)
            try:
                self.master.attributes("-fullscreen", True)
            except Exception as e2:
                log_exception("move_and_maximize.fullscreen_fallback", e2)

    def update_text(self, text):
        """Aktualizuje text na projekcii s dynamickou veľkosťou a plynulým nábehom (fade in)."""
        try:
            raw_text = text or ""
            self.raw_text_content = raw_text
            text = raw_text

            if not getattr(self, "zobrazovat_znaky_chorov", True):
                text = re.sub(r"(?m)^\[(?:L|P)\]\s*", "", text)
            if not getattr(self, "zobrazovat_specialne_znaky", True):
                text = text.replace("·", "").replace("_", "")

            # 1. Ak sa text nezmenil, nerob nič
            if getattr(self, "current_text_content", None) == text:
                return

            self.current_text_content = text

            # 2. Synchronizácia rozmerov (iba idletasks!)
            root_win = self.master
            root_win.update_idletasks()

            # 3. Získanie nastavení – priamo z atribútov inštancie
            base_size = self.font_size
            font_family: str = FONT_NAME or "Arial"
            bg_color = BACKGROUND_COLOR

            win_w = root_win.winfo_width()
            win_h = root_win.winfo_height()

            if win_w < 300:
                win_w = root_win.winfo_screenwidth()
            if win_h < 200:
                win_h = root_win.winfo_screenheight()

            max_w = int(win_w * PROJECTION_WRAP_RATIO)
            max_h = int(win_h * (1.0 - self.reserved_vertical_ratio))

            # ------------------------------------------------------------
            # 4. DYNAMICKÝ VÝPOČET VEĽKOSTI (BINÁRNE VYHĽADÁVANIE)
            # ------------------------------------------------------------
            low = 10
            high = int(base_size)
            optimal_size = low

            # Persistent font objekt uložený ako self._proj_test_font – vytvorí sa raz
            # a ďalšie volania iba reconfigurujú family/size. Predíde sa tým rastu
            # internej Tk tabuľky fontov pri každom volaní update_text.
            if getattr(self, "_proj_test_font", None) is None:
                self._proj_test_font = tkfont.Font(family=font_family, size=low, weight="bold")
            else:
                self._proj_test_font.configure(family=font_family, size=low)
            test_font = self._proj_test_font
            while low <= high:
                mid = (low + high) // 2
                test_font.configure(size=mid)

                total_h = self._estimate_text_height(text, test_font, max_w)

                if total_h <= max_h:
                    optimal_size = mid
                    low = mid + 1
                else:
                    high = mid - 1

            current_size = optimal_size

            # 5. STOP starú animáciu
            self._stop_fade_animation(self.text_label)

            # 6. Nastavenie počiatočného stavu
            self.text_label.config(
                text=text,
                font=(font_family, current_size, "bold"),
                wraplength=max_w,
                justify="center",
                fg=bg_color
            )

            self.text_label.lift()

            # 7. Spustenie fade-in
            try:
                self._animate_fade_in(self.text_label)
            except Exception as e_fade:
                self.text_label.config(fg=self.target_text_color)
                log_exception("Manuálne spustenie fade-in zlyhalo", e_fade)

        except Exception as e:
            log_exception("ProjectionWindow.update_text zlyhal", e)             


    # ------------------------------------------------------------
    #  AKTUALIZÁCIA TITULKU
    # ------------------------------------------------------------
    def update_title(self, name, current=None, total=None):
        try:
            # 0) Neaktualizuj, ak sa názov nezmenil A text je stále viditeľný
            # (ak bol text skrytý a obnovený s rovnakým názvom, fade-in sa MUSÍ spustiť)
            if (hasattr(self, "current_title_text")
                    and self.current_title_text == name
                    and self.title_label.cget("fg") == self.target_text_color):
                return

            self.current_title_text = name

            # 1) Ak nie je čo zobraziť
            if not name:
                try:
                    self.title_label.config(text="")
                except Exception as e:
                    log_exception("update_title: chyba pri čistení labelu", e)
                return

            # 2) Reset debounce (ak existuje)
            if getattr(self, "_debounce_title_after_id", None):
                try:
                    self.master.after_cancel(self._debounce_title_after_id)
                except Exception as e:
                    log_exception("update_title: after_cancel failed", e)
                self._debounce_title_after_id = None

            # 3) Nastavenie textu titulku
            try:
                self.title_label.config(text=name)
            except Exception as e:
                log_exception("update_title: chyba pri nastavení textu", e)

            # 4) Logika pre fade-in (len pre hlavnú projekciu)
            try:
                if self.fade_enabled:
                    # Nastavíme farbu na farbu pozadia (aby bol text neviditeľný)
                    self.title_label.config(fg=BACKGROUND_COLOR)
                    # Spustíme novú univerzálnu animáciu
                    self._animate_fade_in(self.title_label)
                else:
                    # Ak je fade vypnutý, nastavíme hneď cieľovú farbu
                    self.title_label.config(fg=self.target_text_color)
            except Exception as e:
                log_exception("update_title: chyba pri fade-in / farbe", e)

        except Exception as e:
            # Hlavný záchytný bod pre celú metódu
            log_exception("update_title: hlavná chyba metódy", e)    
            
            
    def update_style(self, bg_color):
        """
        Aktualizuje iba farbu pozadia projekčného okna.
        Farba textu sa tu zámerne nemení – fade‑in efekt si riadi farbu
        pomocou target_text_color, ktorý nastavuje ControlApp.
        """
        try:
            current_font = self.text_label["font"]

            # Textovú farbu nemeníme – fade‑in zabezpečuje plynulý prechod
            # z čiernej do cieľovej farby bez náhlych kontrastov.
            self.text_label.config(font=current_font, bg=bg_color)
            self.title_label.config(bg=bg_color)
            self.master.configure(bg=bg_color)

            # target_text_color sa tu NEnastavuje – riadi ho ControlApp
            # pri zmene farby textu alebo pri fade‑in animácii.

        except Exception as e:            
            log_exception("Chyba pri aktualizácii štýlu (pozadia) projekčného okna", e)     
       
                                  
    def _get_safe_rgb(self, color_value):
        """
        Pomocná metóda: Bezpečne získa RGB (0-255) z akejkoľvek Tkinter farby.
        Funguje pre HEX (#ffffff), názvy (white, red) aj systémové farby.
        """
        if not color_value:
            return (255, 255, 255) 
            
        try:
            # winfo_rgb vráti 16-bitové hodnoty (0-65535), musíme ich previesť na 8-bit
            rgb16 = self.master.winfo_rgb(color_value)
            return (rgb16[0] // 256, rgb16[1] // 256, rgb16[2] // 256)
        except Exception as e:
            # Fallback na bielu v prípade chyby
            log_exception("_get_safe_rgb: neplatná farba", e)
            return (255, 255, 255)        
        
    def _estimate_text_height(self, text, font_obj, wraplength):
        """
        Odhad výšky textu – deleguje na modulo-úrovňovú funkciu estimate_text_height().
        Zachované pre spätnú kompatibilitu interných volaní v triede.
        """
        return estimate_text_height(text, font_obj, wraplength)
        
        
    def _stop_fade_animation(self, widget):
        """Zastaví prebiehajúcu fade animáciu pre daný widget."""
        if not widget or not widget.winfo_exists():
            return

        attr_id = f"_fade_after_id_{id(widget)}"
        old_id = getattr(self, attr_id, None)

        if old_id:
            try:
                self.master.after_cancel(old_id)
            except Exception as e_cancel:
                log_exception(f"_stop_fade_animation: after_cancel zlyhal pre widget {id(widget)}", e_cancel)

        setattr(self, attr_id, None)   
                

    def _animate_fade_in(self, widget, current_step=0):
        # 1. Základná kontrola - ak widget neexistuje, nepokračujeme
        if not widget.winfo_exists():
            return

        try:
            # 2. Zastavenie predchádzajúcej animácie IBA pri štarte novej
            if current_step == 0:
                self._stop_fade_animation(widget)

            # Získanie presetov
            preset = FADE_PRESETS.get(self.fade_speed, FADE_PRESETS["mierne rýchle"])
            steps = preset["steps"]
            delay = preset["delay"]
            target = self.target_text_color

            # Ak nie sú kroky alebo je iba jeden krok, nastav rovno cieľovú farbu a skonči.
            # steps <= 0: fade je vypnutý
            # steps == 1: (steps - 1) == 0 → ZeroDivisionError pri výpočte pomeru
            if steps <= 1:
                widget.config(fg=target)
                return

            # Výpočet pomeru (0.0 až 1.0) – steps >= 2, takže (steps - 1) >= 1
            ratio = min(max(current_step / (steps - 1), 0.0), 1.0)

            # Získanie RGB hodnôt
            tr, tg, tb = self._get_safe_rgb(target)
            sr, sg, sb = self._get_safe_rgb(BACKGROUND_COLOR)

            # Interpolácia farby
            r = int(sr + (tr - sr) * ratio)
            g = int(sg + (tg - sg) * ratio)
            b = int(sb + (tb - sb) * ratio)

            # Nastavenie aktuálnej farby
            widget.config(fg=f"#{r:02x}{g:02x}{b:02x}")

            attr_id = f"_fade_after_id_{id(widget)}"

            # Pokračovanie animácie, ak nie sme na poslednom kroku
            if current_step < steps - 1:
                new_id = self.master.after(
                    delay,
                    lambda: self._animate_fade_in(widget, current_step + 1)
                )
                setattr(self, attr_id, new_id)
            else:
                # Finálna farba
                widget.config(fg=target)
                setattr(self, attr_id, None)

        except Exception as e:
            log_exception("Chyba počas behu fade-in animácie", e)

            # Záchranné nastavenie finálnej farby
            try:
                if widget.winfo_exists():
                    widget.config(fg=self.target_text_color)
            except Exception as e2:
                log_exception("Fade-in: nepodarilo sa nastaviť finálnu farbu po chybe", e2)

            # Vyčistenie animácie po chybe
            self._stop_fade_animation(widget)         
            
      
def _vytvor_on_close_handler(top: tk.Toplevel, on_close_callback):
    """
    Vytvorí obsluhu zatvorenia okna, ktorá pred jeho zničením zaznamená
    aktuálne rozmery a odovzdá ich cez `on_close_callback(w, h)`.

    Nahrádza 2× duplicitne definovanú lokálnu funkciu `_on_close`
    v `DirektoriumApp` a `SlavnostiApp` (obe okná majú rovnaký vzor:
    zisti šírku/výšku, zavolaj callback, zavri okno; prípadnú výnimku
    z callbacku ticho ignoruj, aby zatvorenie okna nikdy nezlyhalo).
    """
    def _on_close():
        try:
            w = top.winfo_width()
            h = top.winfo_height()
            on_close_callback(w, h)
        except Exception:
            pass
        top.destroy()

    return _on_close


class DirektoriumApp:
    """Samostatné okno pre zobrazenie tabuľky direktória piesní."""

    def __init__(self, master, direktorium_data, init_width=None, init_height=None, on_close_callback=None, on_song_select=None):
        self.top = tk.Toplevel(master)
        self.top.title("Direktórium (Odporúčané piesne z JKS na jednotlivé nedele a sviatky liturgického roka)")

        win_w = init_width  if (init_width  and init_width  >= 400) else 1000
        win_h = init_height if (init_height and init_height >= 300) else 660
        screen_w = self.top.winfo_screenwidth()
        x = max(0, screen_w - win_w - 20)
        y = 20
        self.top.geometry(f"{win_w}x{win_h}+{x}+{y}")

        # --- MODÁLNE OKNO ---
        self.top.transient(master)
        self.top.grab_set()
        self.top.focus_set()

        # Zachytenie rozmerov pri zatvorení
        if on_close_callback:
            _on_close = _vytvor_on_close_handler(self.top, on_close_callback)
            self.top.protocol("WM_DELETE_WINDOW", _on_close)
            self.top.bind("<Escape>", lambda e: _on_close())
        else:
            self.top.protocol("WM_DELETE_WINDOW", self.top.destroy)
            self.top.bind("<Escape>", lambda e: self.top.destroy())

        # uloženie dát
        self.direktorium_data = direktorium_data
        self.on_song_select = on_song_select

        # --- vyhľadávací panel ---
        search_frame = tk.Frame(self.top)
        search_frame.pack(fill="x", padx=5, pady=5)

        tk.Label(search_frame, text="Vyhľadaj:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind("<Return>", lambda event: self.search())

        tk.Button(search_frame, text="Hľadaj", command=self.search).pack(side="left", padx=5)
        tk.Button(search_frame, text="Reset", command=self.reset).pack(side="left")

        # --- tabuľka ---
        frame = tk.Frame(self.top)
        frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            frame,
            columns=("den", "uvod", "ofert", "prij", "kant", "po_omsi"),
            show="headings"
        )
        self.tree.pack(side="left", fill="both", expand=True)

        v_scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        v_scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=v_scrollbar.set)

        h_scrollbar = ttk.Scrollbar(self.top, orient="horizontal", command=self.tree.xview)
        h_scrollbar.pack(side="bottom", fill="x")
        self.tree.configure(xscrollcommand=h_scrollbar.set)

        style = ttk.Style(self.top)

        safe_font_name: str = FONT_NAME or "Arial"

        style.configure("Treeview", font=(safe_font_name, 11))
        style.configure("Treeview.Heading", font=(safe_font_name, 11, "bold"))

        # hlavičky
        self.tree.heading("den", text="Liturgický deň", anchor="w")
        self.tree.heading("uvod", text="Úvodný spev", anchor="w")
        self.tree.heading("ofert", text="Ofertórium", anchor="w")
        self.tree.heading("prij", text="Na prijímanie", anchor="w")
        self.tree.heading("kant", text="Kant.", anchor="w")
        self.tree.heading("po_omsi", text="Po omši", anchor="w")

        # stĺpce
        self.tree.column("den", width=350, anchor="w", stretch=False)
        self.tree.column("uvod", width=140, anchor="w", stretch=False)
        self.tree.column("ofert", width=130, anchor="w", stretch=False)
        self.tree.column("prij", width=120, anchor="w", stretch=False)
        self.tree.column("kant", width=105, anchor="w", stretch=False)
        self.tree.column("po_omsi", width=130, anchor="w", stretch=False)

        # štýly pre hlavičky období
        self.tree.tag_configure(
            "obdobie",
            background="#000033",
            foreground="white",
            font=(safe_font_name, 11, "bold")
        )

        # Pastelové farby podľa obdobia
        self.tree.tag_configure("Adventné1", background="#e6ccff")
        self.tree.tag_configure("Adventné2", background="#d1b3ff")

        self.tree.tag_configure("Vianočné1", background="#ffffcc")
        self.tree.tag_configure("Vianočné2", background="#fff799")

        self.tree.tag_configure("Veľkonočné1", background="#ffffcc")
        self.tree.tag_configure("Veľkonočné2", background="#fff799")

        self.tree.tag_configure("Cezročné1", background="#ccffcc")
        self.tree.tag_configure("Cezročné2", background="#99ff99")

        self.tree.tag_configure("Pôstne1", background="#f2ccff")
        self.tree.tag_configure("Pôstne2", background="#e0b3ff")

        # default sivé zebra riadky
        self.tree.tag_configure("riadok1", background="#f0f0f0")
        self.tree.tag_configure("riadok2", background="#ffffff")
        
        # ------------------------------------------------------------
        #  ODSADENIE (rovnaké ako v SlavnostiApp, ale bez šípky)
        # ------------------------------------------------------------
        self.INDENT = "  "

        # načítanie obsahu
        self.reset()

        self.tree.bind("<Double-1>", self.vyber_piesen_z_kliknutej_bunky)

    def vyber_piesen_z_kliknutej_bunky(self, event=None):
        on_song_select = getattr(self, "on_song_select", None)
        if not callable(on_song_select):
            return

        try:
            item_id = self.tree.identify_row(event.y) if event is not None else ""
            column = self.tree.identify_column(event.x) if event is not None else ""
            if not item_id:
                selected = self.tree.selection()
                item_id = selected[0] if selected else ""
            if not item_id:
                return

            values = self.tree.item(item_id, "values")
            if not values:
                return

            try:
                column_index = int(str(column).lstrip("#")) - 1
            except Exception:
                column_index = 1

            zvysne_stlpce = [v for i, v in enumerate(values[1:], start=1) if i != column_index]

            candidates = []
            if 0 < column_index < len(values):
                candidates.append(values[column_index])
            candidates.extend(zvysne_stlpce)

            for text in candidates:
                kod = vyber_prvu_piesen_z_direktorioveho_textu(text)
                if kod:
                    on_song_select(kod)
                    return "break"
        except Exception as e:
            log_exception("DirektoriumApp: výber piesne z tabuľky zlyhal", e)

    # ------------------------------------------------------------
    #  Pomocná funkcia: výber tagu podľa obdobia a indexu
    # ------------------------------------------------------------
    def get_tag(self, obdobie, i):
        if obdobie in ("Adventné", "Vianočné", "Veľkonočné", "Cezročné", "Pôstne"):
            return f"{obdobie}{1 if i % 2 == 0 else 2}"
        return "riadok1" if i % 2 == 0 else "riadok2"

    # ------------------------------------------------------------
    #  Pomocná funkcia: vloženie hlavičky sekcie
    # ------------------------------------------------------------
    def insert_section_header(self, obdobie):
        self.tree.insert("", "end", values=(obdobie, "", "", "", "", ""), tags=("obdobie",))

    # ------------------------------------------------------------
    #  RESET – pôvodné zobrazenie
    # ------------------------------------------------------------
    def reset(self):
        self.tree.delete(*self.tree.get_children())

        for obdobie, riadky in self.direktorium_data.items():
            self.insert_section_header(obdobie)

            for i, riadok in enumerate(riadky):
                values = (
                    self.INDENT + riadok.get("den", ""),   # ← ODSADENIE
                    riadok.get("uvodny", ""),
                    riadok.get("ofertorium", ""),
                    riadok.get("prijimanie", ""),
                    riadok.get("kant", ""),
                    riadok.get("po_omsi", "")
                )
                tag = self.get_tag(obdobie, i)
                self.tree.insert("", "end", values=values, tags=(tag,))

    # ------------------------------------------------------------
    #  SEARCH – filtrovanie podľa textu
    # ------------------------------------------------------------
    def search(self):
        # Normalizované vyhľadávanie (bez diakritiky, case-insensitive)
        query = normalize_diacritics(self.search_var.get())

        self.tree.delete(*self.tree.get_children())

        for obdobie, riadky in self.direktorium_data.items():
            matched = [
                r for r in riadky
                if any(query in normalize_diacritics(str(v)) for v in r.values())
            ]

            if matched:
                self.insert_section_header(obdobie)

                for i, riadok in enumerate(matched):
                    values = (
                        self.INDENT + riadok.get("den", ""),
                        riadok.get("uvodny", ""),
                        riadok.get("ofertorium", ""),
                        riadok.get("prijimanie", ""),
                        riadok.get("kant", ""),
                        riadok.get("po_omsi", "")
                    )
                    tag = self.get_tag(obdobie, i)
                    self.tree.insert("", "end", values=values, tags=(tag,))         
                   
                  
class SlavnostiApp:
    # ------------------------------------------------------------
    #  KONŠTRUKTOR
    # ------------------------------------------------------------
    def __init__(self, master, slavnosti_data, neprikazane_data, pohyblive_data, init_width=None, init_height=None, on_close_callback=None, on_song_select=None):
        self.top = tk.Toplevel(master)
        self.top.title("Liturgické slávenia pre celý rok")

        win_w = init_width  if (init_width  and init_width  >= 400) else 960
        win_h = init_height if (init_height and init_height >= 300) else 680
        screen_w = self.top.winfo_screenwidth()
        x = max(0, screen_w - win_w - 20)
        y = 20
        self.top.geometry(f"{win_w}x{win_h}+{x}+{y}")
        
        # Centrálna premenná pre font – používa sa v celom okne
        self.font_family: str = FONT_NAME or "Arial"

        # --- MODÁLNE OKNO ---
        self.top.transient(master)
        self.top.grab_set()
        self.top.focus_set()

        # Zachytenie rozmerov pri zatvorení
        if on_close_callback:
            _on_close = _vytvor_on_close_handler(self.top, on_close_callback)
            self.top.protocol("WM_DELETE_WINDOW", _on_close)
            self.top.bind("<Escape>", lambda e: _on_close())
        else:
            self.top.protocol("WM_DELETE_WINDOW", self.top.destroy)
            self.top.bind("<Escape>", lambda e: self.top.destroy())

        # Uložíme si dáta pre filtrovanie
        self.slavnosti_data = slavnosti_data
        self.neprikazane_data = neprikazane_data
        self.pohyblive_data = pohyblive_data
        self.on_song_select = on_song_select

        # ------------------------------------------------------------
        #  FILTRE – tlačidlá s rovnakou šírkou + hrubý rámik pri aktívnom
        # ------------------------------------------------------------
        filter_frame = tk.Frame(self.top)
        filter_frame.pack(fill="x", padx=10, pady=(5, 0))

        BUTTON_WIDTH = 14   # rovnaká šírka tlačidiel

        self.filter_buttons = {}

        def make_btn(name, obdobie):
            # Kontajner pre prúžok hore + tlačidlo
            wrapper = tk.Frame(filter_frame)
            wrapper.pack(side="left", padx=0)

            # Farebný prúžok hore (default neviditeľný)
            stripe = tk.Frame(wrapper, height=4, width=130, bg=self.top.cget("bg"))
            stripe.pack(side="bottom")

            # Samotné tlačidlo
            btn = tk.Button(
                wrapper,
                text=name,
                font=(self.font_family, 12),
                width=BUTTON_WIDTH,
                relief="flat",
                bd=0,
                highlightthickness=0
            )
            btn.config(command=lambda: self.apply_filter(obdobie))
            btn.pack(side="top", padx=4)

            # Hover efekt – jemné zosvetlenie
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#e6e6e6"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=self.top.cget("bg")))

            # Uložíme oba prvky
            self.filter_buttons[name] = (btn, stripe)

        make_btn("Všetko", None)
        make_btn("Adventné", "Adventné")
        make_btn("Vianočné", "Vianočné")
        make_btn("Pôstne", "Pôstne")
        make_btn("Veľkonočné", "Veľkonočné")
        make_btn("Cezročné", "Cezročné")

        # ------------------------------------------------------------
        #  TABUĽKA
        # ------------------------------------------------------------
        table_frame = tk.Frame(self.top)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)

        scroll_y = ttk.Scrollbar(table_frame, orient="vertical")
        scroll_y.pack(side="right", fill="y")
        scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")
        scroll_x.pack(side="bottom", fill="x")

        self.tree = ttk.Treeview(
            table_frame,
            columns=("feast",),
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )
        self.tree.pack(side="left", fill="both", expand=True)

        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        # ------------------------------------------------------------
        #  ŠTÝLY TABUĽKY
        # ------------------------------------------------------------
        style = ttk.Style(self.top)
        style.configure("Treeview", font=(self.font_family, 11), rowheight=38)
        style.configure("Treeview.Heading", font=(self.font_family, 11, "bold"))

        self.tree.heading("feast", text="Slávenia", anchor="w")
        self.tree.column("feast", width=1150, anchor="w", stretch=True)

        # ------------------------------------------------------------
        #  TAGY – farby riadkov
        # ------------------------------------------------------------
        self.tree.tag_configure("obdobie",
            background="#000033",
            foreground="white",
            font=(self.font_family, 11, "bold")
        )

        # Pastelové farby podľa Direktória
        self.tree.tag_configure("Adventné1", background="#e6ccff")
        self.tree.tag_configure("Adventné2", background="#d1b3ff")

        self.tree.tag_configure("Vianočné1", background="#ffffcc")
        self.tree.tag_configure("Vianočné2", background="#fff799")

        self.tree.tag_configure("Veľkonočné1", background="#ffffcc")
        self.tree.tag_configure("Veľkonočné2", background="#fff799")

        self.tree.tag_configure("Cezročné1", background="#ccffcc")
        self.tree.tag_configure("Cezročné2", background="#99ff99")

        self.tree.tag_configure("Pôstne1", background="#f2ccff")
        self.tree.tag_configure("Pôstne2", background="#e0b3ff")

        # Sivá zebra fallback
        self.tree.tag_configure("riadok1", background="#f0f0f0")
        self.tree.tag_configure("riadok2", background="#ffffff")

        # Bold text
        self.tree.tag_configure("bold", font=(self.font_family, 11, "bold"))
        self.tree.tag_configure("note", font=(self.font_family, 11))

        # ------------------------------------------------------------
        #  ODSADENIE
        # ------------------------------------------------------------
        self.INDENT = "  "
        self.DATE_PREFIX = "  ↳ "

        # ------------------------------------------------------------
        #  PEVNÉ FARBY PRE KAŽDÝ SVIATOK
        # ------------------------------------------------------------
        # Niektoré sviatky sa v tomto slovníku vyskytujú viackrát (napr. raz
        # v sekcii PRIKÁZANÉ a znova v sekcii POHYBLIVÉ). Je to zámerné a správne:
        # tieto sviatky sú zároveň prikázané aj pohyblivé (napr. Nanebovstúpenie
        # Pána, Najsvätejšieho Kristovho Tela a Krvi). Ich farba je v oboch
        # prípadoch rovnaká, takže výsledok je identický bez ohľadu na to,
        # ktorý záznam Python použije.
        # Rovnako Adventné aj Pôstne obdobie majú liturgicky rovnakú farbu
        # (fialovú), čo je teologicky správne – nejde o chybu.
        self.FARBY_SVIATKOV = {
            # PRIKÁZANÉ
            "Panny Márie Bohorodičky": "Vianočné",
            "Zjavenie Pána - Traja králi": "Vianočné",
            "Nanebovstúpenie Pána": "Veľkonočné",
            "Najsvätejšieho Kristovho Tela a Krvi": "Cezročné",
            "Sv. Petra a Pavla, apoštolov": "Cezročné",
            "Nanebovzatie Panny Márie": "Cezročné",
            "Všetkých svätých": "Cezročné",
            "Nepoškvrnené počatie Panny Márie": "Adventné",
            "Narodenie Pána": "Vianočné",

            # NEPRIKÁZANÉ
            "Najsvätejšie meno Ježiš": "Vianočné",
            "Obetovanie Pána (Hromnice)": "Cezročné",
            "Sv. Jozefa, ženícha Panny Márie": "Pôstne",
            "Zvestovanie Pána*": "Pôstne",
            "Pondelok vo Veľkonočnej oktáve": "Veľkonočné",            
            "Turíčny pondelok": "Cezročné",
            "Najsvätejšieho Srdca Ježišovho": "Cezročné",
            "Nepoškvrnené Srdce Panny Márie": "Cezročné",
            "Narodenie sv. Jána Krstiteľa": "Cezročné",
            "Návšteva preblahoslavenej Panny Márie": "Cezročné",
            "Sv. Cyrila a Metoda, slovanských vierozvestov": "Cezročné",           
            "Premenenie Pána": "Cezročné",
            "Narodenie Panny Márie": "Cezročné",
            "Povýšenie Svätého kríža": "Cezročné",
            "Sedembolestnej Panny Márie, patrónky Slovenska": "Cezročné",
            "Sv. Michala, Gabriela a Rafaela, archanieli": "Cezročné",
            "Spomienka na Všetkých zosnulých veriacich": "Cezročné",
            "Výročie posviacky Lateránskej baziliky": "Cezročné",
            "Sv. Štefana, prvého mučeníka": "Vianočné",

            # POHYBLIVÉ
            # Poznámka: niektoré sviatky sa opakujú z vyššie uvedených sekcií,
            # pretože sú zároveň pohyblivé (dátum sa mení podľa roka). Farba
            # zostáva rovnaká – opakovanie je teda bezpečné a zámerné.
            "Prvá adventná nedeľa (začína nový liturgický rok)": "Adventné",
            "Svätej rodiny Ježiša, Márie a Jozefa": "Vianočné",
            "Krst Krista Pána": "Vianočné",
            "Popolcová streda": "Pôstne",
            "Palmová (Kvetná nedeľa)": "Pôstne",
            "Veľkonočná nedeľa": "Veľkonočné",
            "Nedeľa Božieho milosrdenstva": "Veľkonočné",
            "Nanebovstúpenie Pána": "Veľkonočné",
            "Nedeľa zoslania Ducha Svätého (Turíce)": "Veľkonočné",
            "Panny Márie, Matky Cirkvi": "Cezročné",
            "Pána Ježiša Krista, najvyššieho a večného kňaza": "Cezročné",
            "Najsvätejšej Trojice": "Cezročné",
            "Najsvätejšieho Kristovho Tela a Krvi": "Cezročné",
            "Najsvätejšieho Srdca Ježišovho": "Cezročné",
            "Nepoškvrnené Srdce Panny Márie": "Cezročné",
            "Krista Kráľa": "Cezročné",
        }

        # ------------------------------------------------------------
        #  NAČÍTANIE TABUĽKY (bez filtra)
        # ------------------------------------------------------------
        self.apply_filter(None)
        self.tree.bind("<Double-1>", self.vyber_slavenie_z_kliknuteho_riadku)

        # ------------------------------------------------------------
        #  POZNÁMKY – pergamen + rámik
        # ------------------------------------------------------------
        self.note_frame1 = tk.Frame(
            self.top,
            bg="#f3e7d3",
            highlightbackground="#d6c7b4",
            highlightcolor="#d6c7b4",
            highlightthickness=1
        )

        tk.Label(
            self.note_frame1,
            text="Pozn. č. 1: Pohyblivé sviatky sú tie, ktoré nemajú stály dátum slávenia a takmer všetky závisia od pohyblivého sviatku Veľká noc. "
                 "Nicejský snem v roku 325 nariadil, že Veľká noc sa má sláviť v nedeľu po prvom jarnom splne mesiaca.",
            wraplength=950, justify="left", anchor="w",
            font=(self.font_family, 11, "italic"),
            bg="#f3e7d3", fg="#5a4632"
        ).pack(fill="x")

        tk.Label(
            self.note_frame1,
            text="Veľkonočná nedeľa je teda prvá nedeľa po prvom splne po jarnej rovnodnovosti (po 21. marci),",
            wraplength=950, justify="left", anchor="w",
            font=(self.font_family, 11, "bold"),
            bg="#f3e7d3", fg="#3d2f22"
        ).pack(fill="x")

        tk.Label(
            self.note_frame1,
            text="čo môže pripadnúť na jednu z nedieľ od 22. marca do 25. apríla. Termín sviatkov Veľkej noci je pohyblivý "
                 "a je závislý od lunárneho cyklu. Následne sú známe aj dátumy Zeleného štvrtka, Veľkého piatku, Bielej soboty "
                 "a Veľkonočného pondelka a tiež ostatných pohyblivých sviatkov.",
            wraplength=950, justify="left", anchor="w",
            font=(self.font_family, 11, "italic"),
            bg="#f3e7d3", fg="#5a4632"
        ).pack(fill="x")

        self.note_frame2 = tk.Frame(
            self.top,
            bg="#f3e7d3",
            highlightbackground="#d6c7b4",
            highlightcolor="#d6c7b4",
            highlightthickness=1
        )

        tk.Label(
            self.note_frame2,
            text="Pozn. č. 2: Keď dátum 25. marca (slávnosť Zvestovania Pána) pripadne na niektorý deň Veľkého týždňa alebo veľkonočnej oktávy, "
                 "slávnosť sa presúva na najbližší deň po veľkonočnej oktáve.",
            wraplength=950, justify="left", anchor="w",
            font=(self.font_family, 11, "italic"),
            bg="#f3e7d3", fg="#5a4632"
        ).pack(fill="x")

        # ------------------------------------------------------------
        #  TLAČIDLO NA SKRYTIE / ZOBRAZENIE POZNÁMOK
        # ------------------------------------------------------------
        self.notes_visible = False
        self.toggle_btn = tk.Button(
            self.top,
            text="Poznámky ▼",
            font=(self.font_family, 11),
            command=self.toggle_notes
        )
        self.toggle_btn.pack(fill="x", padx=10, pady=5)

    def vyber_slavenie_z_kliknuteho_riadku(self, event=None):
        on_song_select = getattr(self, "on_song_select", None)
        if not callable(on_song_select):
            return

        try:
            item_id = self.tree.identify_row(event.y) if event is not None else ""
            if not item_id:
                selected = self.tree.selection()
                item_id = selected[0] if selected else ""
            if not item_id:
                return

            tags = self.tree.item(item_id, "tags")
            if tags and "obdobie" in tags:
                return

            values = self.tree.item(item_id, "values")
            if not values:
                return

            nazov = str(values[0]).strip()
            if nazov.startswith("↳"):
                previous_id = self.tree.prev(item_id)
                if not previous_id:
                    return
                previous_values = self.tree.item(previous_id, "values")
                if not previous_values:
                    return
                nazov = str(previous_values[0]).strip()

            kod = SLAVNOSTI_KODY_PRE_VYBER.get(nazov)
            if kod:
                on_song_select(kod)
                return "break"
        except Exception as e:
            log_exception("SlavnostiApp: výber slávenia z tabuľky zlyhal", e)


    # ------------------------------------------------------------
    #  FUNKCIA: URČENIE OBDOBIA
    # ------------------------------------------------------------
    def get_obdobie(self, feast):
        return self.FARBY_SVIATKOV.get(feast, None)
    

    # ------------------------------------------------------------
    #  FUNKCIA: FARBA RIADKU
    # ------------------------------------------------------------
    def get_fixed_color(self, feast, row_index):
        if feast in self.FARBY_SVIATKOV:
            base = self.FARBY_SVIATKOV[feast]
            return f"{base}1" if row_index % 2 == 0 else f"{base}2"
        return "riadok1" if row_index % 2 == 0 else "riadok2"
    

    # ------------------------------------------------------------
    #  FUNKCIA: FARBY TLAČIDIEL FILTROV
    # ------------------------------------------------------------
    def update_filter_button_colors(self, active):
        farby = {
            "Adventné": "#820fef",
            "Vianočné": "#FFBF00",
            "Pôstne": "#820fef",
            "Veľkonočné": "#FFBF00",
            "Cezročné": "#07BA07",
            None: "#666666"
        }

        for key, (btn, stripe) in self.filter_buttons.items():
            obdobie = None if key == "Všetko" else key

            if obdobie == active:
                # Aktívne tlačidlo – hover vypnúť
                btn.unbind("<Enter>")
                btn.unbind("<Leave>")

                # Stabilné pozadie
                btn.config(
                    bg=self.top.cget("bg"),
                    highlightthickness=0,
                    bd=0,
                    relief="flat"
                )

                # Farebný prúžok hore
                stripe.config(bg=farby[active])

            else:
                # Neaktívne tlačidlá – najprv odstrániť staré handlery
                btn.unbind("<Enter>")
                btn.unbind("<Leave>")

                # Potom pridať nové hover handlery
                btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#e6e6e6"))
                btn.bind("<Leave>", lambda e, b=btn: b.config(bg=self.top.cget("bg")))

                btn.config(
                    bg=self.top.cget("bg"),
                    highlightthickness=0,
                    bd=0,
                    relief="flat"
                )

                # Prúžok skryť
                stripe.config(bg=self.top.cget("bg"))
               
           
    # ------------------------------------------------------------
    #  FUNKCIA: APLIKOVANIE FILTRA
    # ------------------------------------------------------------
    def apply_filter(self, obdobie):
        self.update_filter_button_colors(obdobie)

        # --- OPTIMALIZÁCIA: Skrytie treeview počas úpravy ---
        # Týmto povieme Tkinteru, aby neprekresľoval okno pri každom delete/insert.
        # Výsledkom je okamžité zobrazenie celého zoznamu bez preblikávania.
        self.tree.pack_forget() 

        # Vyčistenie starých dát
        for row in self.tree.get_children():
            self.tree.delete(row)

        row_index = 0   # farby riadkov pokračujú naprieč všetkými sekciami

        def insert_section(title, data):
            nonlocal row_index

            if obdobie:
                filtered = [(f, d) for f, d in data if self.get_obdobie(f) == obdobie]
            else:
                filtered = data

            # Ak daná sekcia nemá v danom období žiadne záznamy, môžeme ju úplne vynechať
            if not filtered:
                return

            # HLAVIČKA SEKCIÍ (napr. "Prikázané sviatky (5)")
            self.tree.insert(
                "",
                "end",
                values=(f"{title} ({len(filtered)})",),
                tags=("obdobie",)
            )

            # Vkladanie jednotlivých slávností
            for feast, datum_str in filtered:       # ← date → datum_str
                # Názov slávnosti (tučný)
                color_tag = self.get_fixed_color(feast, row_index)
                self.tree.insert("", "end", values=("  " + feast,), tags=("bold", color_tag))
                row_index += 1

                # Dátum (normálne písmo)
                color_tag = self.get_fixed_color(feast, row_index)
                self.tree.insert("", "end", values=(self.DATE_PREFIX + datum_str,), tags=(color_tag,))
                row_index += 1

        # Výpočet dátumov pohyblivých slávení pre aktuálny rok
        rok = date.today().year                     # ← teraz správne mimo insert_section
        pohyblive_datumy = vypocitaj_datum_pohyblivych_slaveni(rok)

        pohyblive_s_datumami = []
        for feast, popis in self.pohyblive_data:
            datum = pohyblive_datumy.get(feast)
            if datum:
                popis_s_datumom = (
                    f"{popis}  |  tento rok pripadá na "
                    f"{datum.day}.{datum.month}.{datum.year}"
                )
            else:
                popis_s_datumom = popis
            pohyblive_s_datumami.append((feast, popis_s_datumom))

        # Vloženie všetkých kategórií
        insert_section("Prikázané sviatky na Slovensku", self.slavnosti_data)
        insert_section("Neprikázané sviatky", self.neprikazane_data)
        insert_section("Pohyblivé slávenia", pohyblive_s_datumami)

        # --- VRÁTENIE WIDGETU DO GUI ---
        # pack() musí byť v rovnakom poradí/s rovnakými parametrami ako v __init__
        self.tree.pack(side="left", fill="both", expand=True)
        
                
    # ------------------------------------------------------------
    #  FUNKCIA: SKRYŤ / ZOBRAZIŤ POZNÁMKY
    # ------------------------------------------------------------
    def toggle_notes(self):
        if self.notes_visible:
            self.note_frame1.pack_forget()
            self.note_frame2.pack_forget()
            self.toggle_btn.config(text="Poznámky ▼")
        else:
            self.note_frame1.pack(fill="x", padx=10, pady=5)
            self.note_frame2.pack(fill="x", padx=10, pady=5)
            self.toggle_btn.config(text="Poznámky ▲")

        self.notes_visible = not self.notes_visible
        
 
class Tooltip:
    # Tooltip zobrazí krátky popis pri prechode myšou nad widgetom.
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tipwindow:
            return

        safe_font_name: str = FONT_NAME or "Arial"

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 30
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            background="#555555",
            foreground="white",
            relief="solid",
            borderwidth=1,
            padx=6, pady=3,
            font=(safe_font_name, 11)
        )
        label.pack()

    def hide(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None       
                 
class ControlApp:
    """Hlavné ovládacie okno, ktoré zostane na primárnom monitore."""
    def __init__(self, master):
        log_info("Inicializujem ControlApp...")

        self._loading_settings = True

        # Aktuálna veľkosť písma – spravovaná výhradne cez self.font_size.
        # Nahradza pôvodný globálny mutable FONT_SIZE.
        self.font_size: int = DEFAULT_CONFIG["font_size"]

        # 1. ZÁKLADNÉ STAVOVÉ PREMENNÉ
        self.is_text_visible = False
        log_debug(f"is_text_visible = {self.is_text_visible}")

        # Zámok pre thread-safe ochranu pred súbežným sťahovaním čítaní.
        # Inicializujeme tu – pred vytvorit_gui() – aby GUI udalosť nemohla
        # zavolať aktualizovat_citania_gui() skôr, než lock existuje.
        self._citania_lock = threading.Lock()
        self._vespery_lock = threading.Lock()
        self._refreny_lock = threading.Lock()
        self._cezrocne_tyzdenne_lock = threading.Lock()
        self._liturgicke_tyzdne_lock = threading.Lock()

        self._download_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="KinakDL")
        try:
            atexit.register(self._download_executor.shutdown, wait=False, cancel_futures=True)
        except TypeError:
            atexit.register(self._download_executor.shutdown, wait=False)
        
        # --- Inicializácia hlavného okna ---
        self.master = master
        try:
            self.master.protocol("WM_DELETE_WINDOW", lambda: (self._shutdown_executor(), self.master.destroy()))
        except Exception:
            pass
        self.initializing = True
        self.posledny_nazov_v_labeli = None

        # ------------------------------------------------------------
        #  Hlavné atribúty deklarované vopred.
        #  Konkrétne widgety sa priradia až pri vytváraní GUI/okien.
        # ------------------------------------------------------------
        self.strofa_label: tk.Text = cast(tk.Text, None)
        self.nazov_label: tk.Label = cast(tk.Label, None)
        self.obsah_suboru_text: tk.Text = cast(tk.Text, None)
        self.popis_label: tk.Label = cast(tk.Label, None)
        self.direktorium_label: tk.Label = cast(tk.Label, None)
        self.manual_entry: tk.Entry = cast(tk.Entry, None)
        self.song_combobox: ttk.Combobox = cast(ttk.Combobox, None)
        self.song_folder_label: tk.Label = cast(tk.Label, None)
        self.status_bar_frame: tk.Frame = cast(tk.Frame, None)
        self.status_bar_zaltár_label: tk.Label = cast(tk.Label, None)
        self.live_preview_label: tk.Label = cast(tk.Label, None)
        self.preview_container: tk.Widget = cast(tk.Widget, None)
        self.filter_menu: tk.OptionMenu = cast(tk.OptionMenu, None)
        self.subor_menu: tk.OptionMenu = cast(tk.OptionMenu, None)
        self.vyber_farbu_button: ttk.Button = cast(ttk.Button, None)
        self.obdobie_menu: tk.OptionMenu = cast(tk.OptionMenu, None)
        self.indikator_farby: tk.Canvas = cast(tk.Canvas, None)

        self.projection_window_root: tk.Toplevel = cast(tk.Toplevel, None)
        self.projection_window: ProjectionWindow = cast(ProjectionWindow, None)
        self.pomocnik_okno: tk.Toplevel | None = None
        self.settings_window: tk.Toplevel | None = None
        self.about_window: tk.Toplevel | None = None
        self.direktorium_window: tk.Toplevel | None = None
        self.slavnosti_window: tk.Toplevel | None = None

        self._startup_after_ids: list[str] = []
        self._main_geom_after_id = None
        self._pomocnik_geom_after_id = None
        self._settings_geom_after_id = None
        self._about_geom_after_id = None
        self._direktorium_geom_after_id = None
        self._slavnosti_geom_after_id = None
        self._live_preview_after_id = None
        self._auto_nacitanie_after_id = None

        self._direktorium_open = False
        self._slavnosti_open = False
        self._suppress_vymazat = False
        self._live_preview_updating = False
        self._preview_test_font = None
        self._strofa_test_font = None
        self._aktualna_vigilia = None
        self._aktualna_vynechane = None
        self.font_family: str = FONT_NAME or "Arial"
     
        
        # 2. UPRATOVANIE LOGOV (Spúšťame pred načítaním nastavení)
        # 14 dní, ponechať aspoň 2 najnovšie súbory
        self.vycistit_stare_logy(dni=14, minimalny_pocet=2)

        # 3. NAČÍTANIE NASTAVENÍ A POISTKA FADE SPEED        
        # Ak v konfigu niečo chýba, použije sa default
        self.fade_speed = DEFAULT_CONFIG.get("fade_speed", "mierne rýchle")

        # --- OŠETRENIE MODULU SCREENINFO ---
        if get_monitors is None:
            try:
                log_info("Modul 'screeninfo' nebol nájdený — projekcia sa otvorí na hlavnom monitore.")
                messagebox.showwarning(
                    "Pozor",
                    "Modul 'screeninfo' nebol nájdený.\n\n"
                    "Projekcia sa otvorí na hlavnom monitore.\n"
                    "Ak chcete používať viac monitorov, nainštalujte balík:\n"
                    "pip install screeninfo"
                )
            except Exception as e:
                log_exception("ControlApp.__init__: screeninfo warning zlyhalo", e)

        # --- Tmavý tenký scrollbar – vytvoriť iba raz ---
        style = ttk.Style()
        try:
            # Ak štýl už existuje, Tcl vyhodí chybu, ktorú ignorujeme
            style.element_create("KinakDark.Scrollbar.trough", "from", "default")
            style.element_create("KinakDark.Scrollbar.thumb", "from", "default")
        except tk.TclError:
            pass

        style.layout(
            "KinakDark.Vertical.TScrollbar",
            [("KinakDark.Scrollbar.trough", {"children": [("KinakDark.Scrollbar.thumb", {"sticky": "nswe"})], "sticky": "nswe"})]
        )

        style.configure(
            "KinakDark.Vertical.TScrollbar",
            troughcolor="#1e1e1e",
            background="#333333",
            darkcolor="#222222",
            lightcolor="#444444",
            bordercolor="#1e1e1e",
            arrowcolor="#dddddd",
            width=8
        )

        # --- Inicializácia premenných z konfigurácie ---
        self.bottom_margin = DEFAULT_CONFIG.get("bottom_margin", 40)
        self.bottom_margin_var = tk.IntVar(self.master, value=self.bottom_margin)

        self.reserved_vertical_ratio = DEFAULT_CONFIG.get("reserved_vertical_ratio", 0.20)
        self.reserved_vertical_var = tk.DoubleVar(self.master, value=self.reserved_vertical_ratio)

        # Premenné Pomocníka
        self.pomocnik_font_size = DEFAULT_CONFIG.get("pomocnik_font_size", 14)
        self.pomocnik_x = DEFAULT_CONFIG.get("pomocnik_x", -1)
        self.pomocnik_y = DEFAULT_CONFIG.get("pomocnik_y", -1)
        self.pomocnik_width = DEFAULT_CONFIG.get("pomocnik_width", -1)
        self.pomocnik_height = DEFAULT_CONFIG.get("pomocnik_height", -1)
        self.pomocnik_last_tab = DEFAULT_CONFIG.get("pomocnik_last_tab", 1)

        # Hodnoty ukladané do konfigurácie.
        self.text_color: str = TEXT_COLOR
        self.zobrazit_direktorium: bool = DEFAULT_CONFIG.get("zobrazit_direktorium", False)
        self.zobrazovat_live_preview: bool = DEFAULT_CONFIG.get("zobrazovat_live_preview", True)
        self.zobrazovat_specialne_znaky: bool = DEFAULT_CONFIG.get("zobrazovat_specialne_znaky", True)
        self.zobrazovat_znaky_chorov: bool = DEFAULT_CONFIG.get("zobrazovat_znaky_chorov", True)
        self.statusbar_tyzden_zaltara: bool = DEFAULT_CONFIG.get("statusbar_tyzden_zaltara", True)
        self.statusbar_skratka_zalmu: bool = DEFAULT_CONFIG.get("statusbar_skratka_zalmu", True)
        self.statusbar_jks_piesne: bool = DEFAULT_CONFIG.get("statusbar_jks_piesne", True)
        self.diagnostika_povolena: bool = DEFAULT_CONFIG.get("diagnostika_povolena", True)

        # Premenné geometrie hlavného okna (ukladaná/načítavaná pozícia a veľkosť)
        self.main_window_x:      int = -1
        self.main_window_y:      int = -1
        self.main_window_width:  int = -1
        self.main_window_height: int = -1
        self.settings_window_width: int = DEFAULT_CONFIG.get("settings_window_width", -1)
        self.settings_window_height: int = DEFAULT_CONFIG.get("settings_window_height", -1)
        self.direktorium_window_width: int = DEFAULT_CONFIG.get("direktorium_window_width", -1)
        self.direktorium_window_height: int = DEFAULT_CONFIG.get("direktorium_window_height", -1)
        self.slavnosti_window_width: int = DEFAULT_CONFIG.get("slavnosti_window_width", -1)
        self.slavnosti_window_height: int = DEFAULT_CONFIG.get("slavnosti_window_height", -1)
        self.about_window_width: int = DEFAULT_CONFIG.get("about_window_width", -1)
        self.about_window_height: int = DEFAULT_CONFIG.get("about_window_height", -1)
        self.about_last_tab: int = DEFAULT_CONFIG.get("about_last_tab", 1)
        self.about_font_size: int = DEFAULT_CONFIG.get("about_font_size", 12)

        # --- Načítanie direktória ---
        try:
            # DIREKTORIUM_DATA by malo byť načítané globálne v Kinak.py            
            self.direktorium_data = DIREKTORIUM_DATA
            log_info(f"Direktórium načítané, počet období: {len(self.direktorium_data)}")
        except Exception as e:
            self.direktorium_data = {}
            log_exception("Chyba pri priradení direktória", e)

        # --- Nastavenie geometrie hlavného okna ---
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()

        # Načítanie uloženej geometrie z configu (ak existuje)
        # Config z disku načítame priamo tu – nacitat_nastavenia() sa volá neskôr,
        # ale geometriu potrebujeme nastaviť ešte pred vytvorením GUI widgetov.
        _early_config = {}
        if CONFIG_FILE_PATH.exists():
            try:
                _raw = CONFIG_FILE_PATH.read_text(encoding='utf-8')
                if _raw.strip():
                    _loaded_early_config = json.loads(_raw)
                    if isinstance(_loaded_early_config, dict):
                        _early_config = _loaded_early_config
                    else:
                        log_info(
                            "Predčasné načítanie geometrie: config.json nie je JSON objekt "
                            f"({type(_loaded_early_config).__name__}), používam predvolenú geometriu."
                        )
            except Exception as e:
                log_exception('Predčasné načítanie geometrie z configu zlyhalo', e)

        def _safe_geometry_int(key, default=-1):
            try:
                return int(_early_config.get(key, default))
            except (TypeError, ValueError):
                log_info(f"Predčasné načítanie geometrie: neplatná hodnota {key!r}, používam {default}.")
                return default

        _saved_w = _safe_geometry_int("main_window_width")
        _saved_h = _safe_geometry_int("main_window_height")
        _saved_x = _safe_geometry_int("main_window_x")
        _saved_y = _safe_geometry_int("main_window_y")

        if _saved_w != -1 and _saved_h != -1 and _saved_x != -1 and _saved_y != -1:
            # Použiť uloženú geometriu
            window_width  = _saved_w
            window_height = _saved_h
            x = _saved_x
            y = _saved_y
        else:
            # Predvolená geometria (dynamický výpočet)
            window_width  = int(screen_width * 0.8)
            usable_height = screen_height - 48
            window_height = max(700, min(900, int(usable_height * 0.95)))
            x = (screen_width - window_width) // 2
            y = max(0, (screen_height - window_height) // 2 - 40)

        self.master.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # --- Stavové premenné GUI ---
        self.text_color_var = tk.StringVar(self.master, value=TEXT_COLOR)
        self.default_filter_var = tk.StringVar(self.master, value=DEFAULT_CONFIG.get("default_filter_obdobie", "Cezročné C2"))
        self.obdobie_var = tk.StringVar(self.master)
        self.pouzit_vlastnu_farbu = tk.BooleanVar(self.master, value=DEFAULT_CONFIG.get("pouzit_vlastnu_farbu", False))
        self.fade_speed_var = tk.StringVar(self.master, value=self.fade_speed)
        self.liturgical_year_var = tk.StringVar(self.master, value=vypocitaj_liturgicky_rok())

        self.zobrazit_direktorium_var = tk.BooleanVar(self.master, value=DEFAULT_CONFIG.get("zobrazit_direktorium", False))
        self.zobrazovat_live_preview_var = tk.BooleanVar(self.master, value=DEFAULT_CONFIG.get("zobrazovat_live_preview", True))
        self.zobrazovat_specialne_znaky_var = tk.BooleanVar(self.master, value=DEFAULT_CONFIG.get("zobrazovat_specialne_znaky", True))
        self.zobrazovat_znaky_chorov_var = tk.BooleanVar(self.master, value=DEFAULT_CONFIG.get("zobrazovat_znaky_chorov", True))
        self.statusbar_tyzden_zaltara_var = tk.BooleanVar(self.master, value=DEFAULT_CONFIG.get("statusbar_tyzden_zaltara", True))
        self.statusbar_skratka_zalmu_var = tk.BooleanVar(self.master, value=DEFAULT_CONFIG.get("statusbar_skratka_zalmu", True))
        self.statusbar_jks_piesne_var = tk.BooleanVar(self.master, value=DEFAULT_CONFIG.get("statusbar_jks_piesne", True))
        self.diagnostika_povolena_var = tk.BooleanVar(self.master, value=DEFAULT_CONFIG.get("diagnostika_povolena", True))
        self.aktualna_liturgicka_cast_var = tk.StringVar(
            self.master,
            value=format_aktualna_liturgicka_cast()
        )

        # --- Atribúty pre piesne ---
        self.aktualne_cislo_piesne = "000"
        self.aktualne_strofy = []
        self.aktualny_index_strofa = 0
        self.original_projection_text = ""
        self.nazov_piesne = ""
        self.aktualny_subor_cesta = None

        # Definícia liturgických období
        self.obdobie_subory = {
            "Adventné": ["1AD", "2AD", "3AD", "4AD"],
            "Vianočné": ["1VI", "STEF", "SJE", "NEV", "SR", "PDR", "PMB", "2VI", "NMJ", "KKP"],
            "Pôstne": ["PS", "1P", "2P", "3P", "4P", "5P", "VT", "ZST", "VP", "ZV"],
            "Veľkonočné": ["VG", "1VN", "VPON", "2VN", "3VN", "4VN", "5VN", "6VN", "NP", "7VN"],
            "Turíce a sviatky": ["1TS", "2TS", "3TS", "4TS", "5TS", "6TS", "7TS"],
            "Cezročné sviatky": ["FJ", "NJK", "NAVPM", "CMV", "BEN", "BRI", "PREM", "VAV", "BAR", "NPMAR", "PSK", "MATE", "MGR", "ZOS", "VPLB", "OND"],
            "Cezročné C1": [f"{i}C1" for i in range(1, 35)],
            "Cezročné C2": [f"{i}C2" for i in range(1, 35)],
            "Mesačné": [f"{i}L" for i in range(1, 13)],
            # Sentinel None – reálny zoznam súborov sa počíta dynamicky
            # v _ziskaj_nezaradene_subory() pri každom výbere tohto filtra.
            "Modlitby a iné": None,
        }

        self.popisy_suborov = {
            "1AD": "Prvý adventný týždeň",
            "2AD": "Druhý adventný týždeň",
            "3AD": "Tretí adventný týždeň – Nedeľa Gaudete",
            "4AD": "Štvrtý adventný týždeň",
            "1VI": "Oktáva po narodení Pána", 
            "STEF": "Sv. Štefana, prvého mučeníka (26. XII.)",
            "SJE": "Sv. Jána, apoštola a evanjelistu (27. XII.)",
            "NEV": "Sv. Neviniatok, mučeníkov (28. XII.)",
            "SR": "Svätej rodiny Ježiša, Márie a Jozefa",
            "PDR": "Posledný deň roka",
            "PMB": "Panny Márie Bohorodičky (1. I.)",
            "NMJ": "Najsvätejšie meno Ježiš (3. I.)",
            "2VI": "Vianočné obdobie",
            "KKP": "Krst Krista Pána",
            "PS": "Popolcová streda a dni po nej",
            "1P": "Prvý pôstny týždeň",
            "2P": "Druhý pôstny týždeň",
            "3P": "Tretí pôstny týždeň",
            "4P": "Štvrtý pôstny týždeň – Nedeľa Laetare",
            "5P": "Piaty pôstny týždeň – Smrtná nedeľa",
            "VT": "Veľký týždeň",
            "ZST": "Zelený štvrtok",
            "VP": "Veľký piatok",
            "ZV": "Zvestovanie Pána*",
            
            "VG": "Veľkonočná vigília",
            "1VN": "Veľkonočná nedeľa Pánovho zmŕtvychvstania",            
            "VPON": "Pondelok vo Veľkonočnej oktáve",
            "2VN": "2. veľkonočná nedeľa – Nedeľa Božieho milosrdenstva",
            "3VN": "3. veľkonočná nedeľa",
            "4VN": "4. veľkonočná nedeľa – Nedeľa Dobrého pastiera",
            "5VN": "5. veľkonočná nedeľa",
            "6VN": "6. veľkonočná nedeľa",
            "NP":  "Nanebovstúpenie Pána",
            "7VN": "7. veľkonočná nedeľa",
            "1TS": "Nedeľa zoslania Ducha Svätého", "2TS": "Panny Márie, Matky Cirkvi", "3TS": "Pána Ježiša Krista, najvyššieho a večného kňaza",
            "4TS": "Najsvätejšia Trojica", "5TS": "Najsvätejšieho Kristovho Tela a Krvi", "6TS": "Najsvätejšieho Srdca Ježišovho",
            "7TS": "Nepoškvrnené Srdce Panny Márie",
            "FJ": "Sv. Filipa a Jakuba, apoštolov (3. V.)",
            "NJK": "Narodenie sv. Jána Krstiteľa (24. VI.)",
            "NAVPM": "Návšteva preblahoslavenej Panny Márie (2. VII.)",
            "BEN":   "Sv. Benedikta, opáta, patróna Európy (11. VII.)",
            "BRI":   "Sv. Brigity, rehoľníčky, patrónky Európy (23. VII.)",
            "VAV":   "Sv. Vavrinca, diakona a mučeníka (10. VIII.)",
            "BAR":   "Sv. Bartolomeja, apoštola (24. VIII.)",
            "MATE":  "Sv. Matúša, apoštola a evanjelistu (21. IX.)",
            "OND":   "Sv. Ondreja, apoštola (30. XI.)",
            "CMV":   "Sv. Cyrila a Metoda (5.VII.)",
            "PREM":  "Premenenie Pána (6. VIII.)",
            "NPMAR": "Narodenie Panny Márie (8. IX.)",
            "PSK":   "Povýšenie Svätého kríža (14. IX.)",
            "MGR":   "Sv. Michala, Gabriela a Rafaela, archanieli (29. IX.)",
            "ZOS":   "Spomienka na Všetkých zosnulých veriacich (2. XI.)",
            "VPLB":  "Výročie posviacky Lateránskej baziliky (9. XI.)"
        }

        mesiace = ["Január", "Február", "Marec", "Apríl", "Máj", "Jún", "Júl", "August", "September", "Október", "November", "December"]
        for i, mesiac in enumerate(mesiace, start=1):
            self.popisy_suborov[f"{i}L"] = mesiac
        for i in range(1, 35):
            self.popisy_suborov[f"{i}C1"] = f"{i}. týždeň (nepárny rok)"
            self.popisy_suborov[f"{i}C2"] = f"{i}. týždeň (párny rok)"

        # --- NAČÍTANIE NASTAVENÍ (Pathlib ochrana) ---
        self.nacitat_nastavenia()
        
        # Prevod song_folder z configu (string) na Path objekt
        # Ak config ešte neexistuje, použije sa DEFAULT_SONG_FOLDER (už je Path)
        self.song_folder_path = Path(self.config.get("song_folder", DEFAULT_SONG_FOLDER))
        
        log_debug(f"CONFIG JE TU: {CONFIG_FILE_PATH.resolve()}")
        log_debug(f"PIESNE SÚ V: {self.song_folder_path.resolve()}")
        
        # --- Inicializácia Projekčného okna ---
        self.default_use_fade = self.config.get("default_use_fade", True)

        self.projection_window_root = tk.Toplevel(self.master)

        # Použijeme setattr, aby editor (Pylance/Mypy) nehlásil chybu "Attribute unknown"
        setattr(self.projection_window_root, "control_app_ref", self)

        self.projection_window = ProjectionWindow(
            self.projection_window_root,
            int(self.config.get("font_size", 75)),
            text_color=self.text_color_var.get(),
            fade_enabled=str(self.default_use_fade).lower() == "true",
            bottom_margin=int(self.bottom_margin_var.get()),
            reserved_vertical_ratio=float(self.reserved_vertical_var.get()),
            fade_speed=self.fade_speed_var.get(),
            preferred_monitor_index=getattr(self, "preferred_monitor_index", 0)
        )

        # Nastavenie ďalších vlastností pre projekčné okno
        self.projection_window.fade_speed = self.fade_speed
        self.projection_window.target_text_color = self.text_color_var.get()
        self.projection_window.zobrazovat_specialne_znaky = self.zobrazovat_specialne_znaky_var.get()
        self.projection_window.zobrazovat_znaky_chorov = self.zobrazovat_znaky_chorov_var.get()
        self.projection_window.preferred_monitor_index = getattr(self, "preferred_monitor_index", 0)
        
        # Zabezpečenie existencie priečinka (Pathlib)
        self.song_folder_path.mkdir(parents=True, exist_ok=True)

        # Načítanie zoznamu piesní
        self.zoznam_piesni_data = self.nacitaj_piesne_do_zoznamu_z_priecinka()
        
        # Vytvorenie GUI a skratiek
        self.vytvorit_gui()
        self.nastavit_globalne_skratky()

        # --- KRITICKÝ KROK PRE STABILITU ---
        # Vynútime, aby si Windows uvedomil skutočné rozmery okna skôr, než skončí init
        self.master.update_idletasks()
        self.master.update() 

        # Ukončenie inicializácie
        self.initializing = False
        self.aktualizovat_vzhlad()

        # Vyčistenie projekcie pri štarte
        self.projection_window.update_text("")
        self.projection_window.update_title(name="", current=0, total=None)

        # --- Ukladanie geometrie hlavného okna pri každej zmene veľkosti/pozície ---
        def _uloz_geometriu_hlavneho_okna(event):
            if event.widget is not self.master:
                return
            if self.initializing:
                return

            def zapis_geometrie():
                self.main_window_x = self.master.winfo_x()
                self.main_window_y = self.master.winfo_y()
                self.main_window_width = self.master.winfo_width()
                self.main_window_height = self.master.winfo_height()
                self.ulozit_nastavenia(aktualizovat_label=False)

            self._naplanuj_debounced_zapis(
                "_main_geom_after_id", zapis_geometrie, "_uloz_geometriu_hlavneho_okna"
            )

        self.master.bind('<Configure>', _uloz_geometriu_hlavneho_okna)

        # Focus na vstupné pole
        self.master.focus_set()

        # Jednorazové inicializačné callbacky – ID sledujeme, aby ich
        # potvrdit_ukoncenie mohlo zrušiť pred master.destroy().
        # (Tkinter síce zruší after() pri destroy() automaticky, ale
        # explicitné cancel je bezpečnejšie pri rýchlom zavretí počas initu.)
        _id1 = self.master.after(_STARTUP_FOCUS_DELAY_MS,   lambda: self.manual_entry.focus_set())
        _id2 = self.master.after(_STARTUP_PREVIEW_DELAY_MS, lambda: self.update_live_preview(""))
        _id3 = self.master.after(_STARTUP_SAVE_DELAY_MS,    self.ulozit_nastavenia, False)
        self._startup_after_ids = [_id1, _id2, _id3]

        log_info("ControlApp inicializovaný.")
    

    def vycistit_stare_logy(self, dni=14, minimalny_pocet=2):
        """
        Odstráni diagnostické súbory staršie ako zadaný počet dní.
        Vždy ponechá aspoň 'minimalny_pocet' najnovších súborov.
        """
        try:
            # Predpokladáme, že CONFIG_FILE_PATH je definovaná globálne 
            log_dir = CONFIG_FILE_PATH.parent
            if not log_dir.exists():
                return

            # Získame všetky .txt súbory súvisiace s logovaním
            vsetky_logy = sorted(
                [f for f in log_dir.glob("*.txt") if "log" in f.name or "diagnostika" in f.name],
                key=lambda x: x.stat().st_mtime,
                reverse=True  # Najnovšie sú na začiatku
            )

            # Ak je súborov menej ako limit, nerobíme nič
            if len(vsetky_logy) <= minimalny_pocet:
                return

            hranica_starnutia = datetime.now().timestamp() - (dni * 86400)

            # Preskočíme prvých X najnovších, zvyšok skontrolujeme na vek
            for subor in vsetky_logy[minimalny_pocet:]:
                if subor.stat().st_mtime < hranica_starnutia:
                    try:
                        subor.unlink()
                        log_info(f"Upratovanie: Odstránený starý log {subor.name}")
                    except Exception as e:
                        log_exception(f"Nepodarilo sa odstrániť log {subor.name}", e)
        except Exception as e:
            log_exception("vycistit_stare_logy: chyba pri čistení logov", e)
    
            
    def potvrdit_ukoncenie(self, event=None):
        if messagebox.askyesno("Kinak: Ukončiť", "Naozaj ukončiť program?"):

            # 1) Startup callbacky
            for _aid in self._startup_after_ids:
                try:
                    self.master.after_cancel(_aid)
                except Exception as e:
                    log_exception("potvrdit_ukoncenie: after_cancel zlyhal (_startup_after_ids)", e)
            self._startup_after_ids = []

            # 2) Live preview
            _lp = self._live_preview_after_id
            if _lp:
                try:
                    self.master.after_cancel(_lp)
                except Exception as e:
                    log_exception("potvrdit_ukoncenie: after_cancel zlyhal (_live_preview_after_id)", e)
                self._live_preview_after_id = None

            # 3) Auto-načítanie
            _auto = self._auto_nacitanie_after_id
            if _auto:
                try:
                    self.master.after_cancel(_auto)
                except Exception as e:
                    log_exception("potvrdit_ukoncenie: after_cancel zlyhal (_auto_nacitanie_after_id)", e)
                self._auto_nacitanie_after_id = None

            # 4) Zničenie okna
            self.master.destroy()    
    
     
    def nacitaj_piesne_do_zoznamu_z_priecinka(self):
        """
        Načíta súbory typu NNN*.txt alebo NNNx*.txt (varianty) pomocou pathlib,
        extrahuje prefix (cislo/variant) a vráti zoznam (cislo, nazov).
        Názov sa berie z prvého neprázdneho riadku súboru.
        """
        piesne = []
        folder = self.song_folder_path

        # Ak priečinok neexistuje, vrátime prázdny zoznam (pathlib way)
        if not folder.is_dir():
            return piesne

        # Prechádzame všetky .txt súbory v priečinku
        for filepath in folder.glob("*.txt"):
            # .stem vráti meno súboru bez prípony .txt
            filename_no_ext = filepath.stem
            
            # extrahovať prefix NNN alebo NNNx (napr. 001 alebo 001a)
            m = re.match(r"^([0-9]{3}[a-zA-Z]?)", filename_no_ext)
            if not m:
                continue

            cislo = m.group(1)   # napr. "269b"
            first_line = ""

            try:
                # Pokus o načítanie v UTF-8-SIG (rieši aj BOM)
                try:
                    with filepath.open("r", encoding="utf-8-sig") as f:
                        for line in f:
                            stripped = line.strip()
                            if stripped:
                                first_line = stripped
                                break
                except (UnicodeDecodeError, UnicodeError):
                    # Fallback na CP1250 (bežné kódovanie starších súborov vo Windows)
                    with filepath.open("r", encoding="cp1250") as f:
                        for line in f:
                            stripped = line.strip()
                            if stripped:
                                first_line = stripped
                                break

                # OŠETRENIE PRÁZDNEHO SÚBORU
                # .name vráti celý názov súboru vrátane prípony
                title = first_line if first_line else filepath.name
                piesne.append((cislo, title))

            except Exception as e:
                log_exception(f"Chyba pri načítaní súboru {filepath.name}", e)

        # Utriediť podľa čísla:
        # Najprv podľa číselnej hodnoty (prvé 3 znaky), potom podľa celého reťazca (varianty a, b...)
        piesne.sort(key=lambda x: (int(x[0][:3]), x[0]))

        return piesne               
       
    def ziskaj_aktualnu_a_celkovu(self):
        """
        Vracia (current, total):
        - current = 0 pre nultú strofu, inak 1..total
        - total = počet reálnych strof (bez nultého záznamu, ak ho používate)
        """
        try:
            total = max(0, len(self.aktualne_strofy) - 1)
            if self.aktualny_index_strofa <= 0:
                current = 0
            else:
                current = min(self.aktualny_index_strofa, total)
            return current, total
        except Exception as e:
            log_exception("ziskaj_aktualnu_a_celkovu: neočakávaná chyba", e)
            return 0, 0


    def aktualizovat_info_liturgickeho_roka(self, liturgicky_rok: str | None = None):
        """
        Aktualizuje titulok hlavného okna s liturgickým rokom, aktuálnou
        časťou, dňom týždňa a prípadnými odpočtami / upozorneniami.

        Formát titulku:
          Kinak v2.2 | Liturgický rok A – časť: 25. TÝŽDEŇ CEZROČNÉHO OBDOBIA, štvrtok
          Kinak v2.2 | Liturgický rok A – 3. deň Veľkonočnej oktávy (streda)
          Kinak v2.2 | Liturgický rok A – NANEBOVZATIE PANNY MÁRIE (Slávnosť)
            + voliteľne:  –  vigília: NAZOV SLÁVNOSTI
            + voliteľne:  –  ⚠ nedeľa má prednosť pred: NAZOV SVIATKU
        """
        if not liturgicky_rok and hasattr(self, "liturgical_year_var") and self.liturgical_year_var:
            liturgicky_rok = self.liturgical_year_var.get()
        liturgicky_rok = liturgicky_rok or vypocitaj_liturgicky_rok()

        dnes = date.today()
        aktualna_cast = vypocitaj_aktualnu_liturgicku_cast(dnes)

        if hasattr(self, "aktualna_liturgicka_cast_var") and self.aktualna_liturgicka_cast_var:
            self.aktualna_liturgicka_cast_var.set(f"Aktuálna liturgická časť:\n{aktualna_cast}")

        if hasattr(self, "master") and self.master and self.master.winfo_exists():
            try:
                cz = zostavit_casove_vztahy_titulku(dnes)
            except Exception as e:
                log_exception("aktualizovat_info_liturgickeho_roka: zostavit_casove_vztahy_titulku zlyhalo", e)
                # Fallback na starý formát
                cz = {"predpona": "časť: ", "hlavny": aktualna_cast,
                      "presun": None, "vynechane": None,
                      "vigilia": None, "prednost_nedele": None}

            # Vigília a poznámka o vynechanom slávení sa zobrazujú v status bare
            # (vynechané navyše aj v title bare, aby boli oba miesta konzistentné).
            self._aktualna_vigilia = cz["vigilia"]
            self._aktualna_vynechane = cz["vynechane"]

            self.master.title(zostav_text_hlavicky(liturgicky_rok, dnes, cz))
            self.aktualizovat_status_bar()

             
    def aktualizovat_status_bar(self):
        """Aktualizuje obsah status baru (skratka žalmu + týždeň žaltára + vigília + vynechané slávenie)."""
        try:
            if self.status_bar_frame is None or self.status_bar_zaltár_label is None:
                return

            zobrazit_zalm    = getattr(self, "statusbar_skratka_zalmu_var",  None)
            zobrazit_zaltara = getattr(self, "statusbar_tyzden_zaltara_var", None)
            # zobrazit_jks     = getattr(self, "statusbar_jks_piesne_var",     None)

            text_statusu = zostav_text_status_baru(
                date.today(),
                bool(zobrazit_zalm and zobrazit_zalm.get()),
                bool(zobrazit_zaltara and zobrazit_zaltara.get()),
                getattr(self, "_aktualna_vigilia", None),
                getattr(self, "_aktualna_vynechane", None),
            )

            if text_statusu:
                self.status_bar_zaltár_label.config(text=text_statusu)
                self.status_bar_frame.pack(side=tk.BOTTOM, fill=tk.X)
            else:
                self.status_bar_zaltár_label.config(text="")
                self.status_bar_frame.pack_forget()
        except Exception as e:
            log_exception("aktualizovat_status_bar: chyba", e)


    def nacitat_nastavenia(self):
        """
        Načíta používateľské nastavenia aplikácie z config.json pomocou pathlib,
        zabezpečí ich validitu a zosynchronizuje ich s projekčným oknom.
        """
        # ZABRÁNI AUTOSAVE POČAS NAČÍTANIA
        self._loading_settings = True

        try:
            # Pomocná funkcia pre bezpečné nastavenie TK premenných (ak by ešte neboli vytvorené)
            def set_safe(var_name, value):
                if hasattr(self, var_name):
                    var = getattr(self, var_name)
                    if var is not None:
                        try:
                            var.set(value)
                        except Exception as e_set:
                            log_exception(f"nacitat_nastavenia: nepodarilo sa nastaviť '{var_name}' = {value!r}", e_set)

            # ------------------------------------------------------------
            # 1) Načítanie configu z disku
            # ------------------------------------------------------------
            config_z_disku = {}
            config_exists = CONFIG_FILE_PATH.exists()
            if config_exists:
                try:
                    content = CONFIG_FILE_PATH.read_text(encoding="utf-8")
                    if content.strip():
                        loaded_config = json.loads(content)
                        if isinstance(loaded_config, dict):
                            config_z_disku = loaded_config
                        else:
                            log_info(
                                "nacitat_nastavenia: config.json nie je JSON objekt "
                                f"({type(loaded_config).__name__}), používam predvolené nastavenia."
                            )
                except Exception as e:
                    log_exception("nacitat_nastavenia: chyba pri čítaní alebo dekódovaní JSON", e)

            # ------------------------------------------------------------
            # 2) Spojenie s predvolenými hodnotami (DEFAULT_CONFIG)
            # ------------------------------------------------------------
            full_config = {**DEFAULT_CONFIG, **config_z_disku}
            needs_forced_save = (
                not config_exists
                or any(key not in config_z_disku for key in DEFAULT_CONFIG)
            )

            # ------------------------------------------------------------
            # 3) Validácia čísel (ZÁPIS SPÄŤ DO full_config)
            # ------------------------------------------------------------
            def validate_int(key, min_val, max_val):
                try:
                    val = int(full_config.get(key, DEFAULT_CONFIG[key]))
                    return val if min_val <= val <= max_val else DEFAULT_CONFIG[key]
                except (ValueError, TypeError):
                    return DEFAULT_CONFIG[key]

            full_config["font_size"] = validate_int("font_size", 20, 200)
            full_config["bottom_margin"] = validate_int("bottom_margin", 0, 400)
            full_config["pomocnik_font_size"] = validate_int("pomocnik_font_size", 8, 40)
            full_config["about_font_size"] = validate_int("about_font_size", 8, 40)
            
            try:
                r = float(full_config.get("reserved_vertical_ratio", DEFAULT_CONFIG["reserved_vertical_ratio"]))
                full_config["reserved_vertical_ratio"] = r if 0.10 <= r <= 0.40 else DEFAULT_CONFIG["reserved_vertical_ratio"]
            except (ValueError, TypeError):
                full_config["reserved_vertical_ratio"] = DEFAULT_CONFIG["reserved_vertical_ratio"]

            # ------------------------------------------------------------
            # 4) Validácia ciest (Pathlib logic – bezpečné porovnávanie)
            # ------------------------------------------------------------
            local_songs_path = (BASE_DIR / "piesne").resolve()
            config_song_folder = full_config.get("song_folder")

            # Bezpečné načítanie cesty z configu
            try:
                config_path_resolved = Path(config_song_folder).resolve() if config_song_folder else None
            except (TypeError, ValueError, OSError):
                config_path_resolved = None

            # 1. Priorita: Platná cesta z configu (používateľské nastavenie)
            if config_path_resolved and config_path_resolved.is_dir():
                song_folder = str(config_path_resolved)

            # 2. Priorita: Lokálny priečinok pri EXE (záloha)
            elif local_songs_path.is_dir():
                song_folder = str(local_songs_path)
                # Ak sme museli použiť túto zálohu, lebo v configu bola zlá cesta,
                # poznačíme si, že po načítaní musíme config aktualizovať a uložiť.
                if config_path_resolved != local_songs_path:
                    needs_forced_save = True

            # 3. Priorita: AppData priečinok (posledná záchrana)
            else:
                safe_default_folder, fallback_info = _vytvor_adresar_s_fallbackom(
                    DEFAULT_SONG_FOLDER,
                    "Predvoleny priecinok piesni",
                    "Kinak_piesne",
                )
                if fallback_info:
                    globals()["SONG_FOLDER_FALLBACK_INFO"] = fallback_info
                    needs_forced_save = True

                default_resolved = safe_default_folder.resolve()
                song_folder = str(default_resolved)

                if config_path_resolved != default_resolved:
                    needs_forced_save = True

            # Uložíme absolútnu cestu ako string pre ďalšie spracovanie
            full_config["song_folder"] = song_folder

            # ------------------------------------------------------------
            # 5) Validácia TEXTOVÝCH HODNÔT (FADE, SEZÓNA, FILTER)
            # ------------------------------------------------------------
            # Validácia Fade Speed
            loaded_fade_speed = full_config.get("fade_speed")
            if loaded_fade_speed not in FADE_PRESETS:
                log_info(f"Oprava: fade_speed '{loaded_fade_speed}' -> 'mierne rýchle'")
                full_config["fade_speed"] = "mierne rýchle"
                needs_forced_save = True
            self.fade_speed = full_config["fade_speed"]

            # Validácia Liturgical Season 
            lit_season = full_config.get("liturgical_season")
            if lit_season not in LITURGICKE_OBDOBIA:
                log_info(f"Oprava: liturgical_season '{lit_season}' -> 'Cezročné'")
                lit_season = "Cezročné"
                full_config["liturgical_season"] = "Cezročné"
                needs_forced_save = True
            self.liturgical_season = lit_season

            # Validácia Default Filter 
            ALLOWED_FILTERS = ["Adventné", "Vianočné", "Pôstne", "Veľkonočné", "Turíce a sviatky", "Cezročné sviatky", "Mesačné", "Cezročné C1", "Cezročné C2", "Modlitby a iné"]
            d_filter = full_config.get("default_filter_obdobie")
            if d_filter not in ALLOWED_FILTERS:
                log_info(f"Oprava: default_filter_obdobie '{d_filter}' -> 'Cezročné C2'")
                d_filter = "Cezročné C2"
                full_config["default_filter_obdobie"] = "Cezročné C2"
                needs_forced_save = True
                
            self.default_filter_obdobie = d_filter    

            # Synchronizácia liturgickej farby
            use_custom = bool(full_config.get("pouzit_vlastnu_farbu", False))
            if not use_custom:
                # Ak nie je vlastná farba, vždy použijeme liturgickú farbu sezóny.
                # Hodnota z JSONu sa zámerne ignoruje – zabráni sa tým zobrazeniu
                # "zostatkovej" farby z inej sezóny po reštarte aplikácie.
                full_config["text_color"] = LITURGICKE_OBDOBIA.get(self.liturgical_season, "#ffffff")
            else:
                # Vlastná farba: validujeme, že je platný #rrggbb hex reťazec.
                # Neplatná hodnota (napr. poškodený JSON) by spôsobila TclError
                # pri každom widget.config(fg=...) – fallback na liturgickú farbu.
                raw_color = full_config.get("text_color", "")
                if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(raw_color)):
                    fallback = LITURGICKE_OBDOBIA.get(self.liturgical_season, "#ffffff")
                    log_info(
                        f"nacitat_nastavenia: neplatná vlastná farba {raw_color!r} → "
                        f"fallback na liturgickú farbu {fallback!r}"
                    )
                    full_config["text_color"] = fallback
                    full_config["pouzit_vlastnu_farbu"] = False
                    use_custom = False
                    needs_forced_save = True

            # ------------------------------------------------------------
            # 6) Priradenie hodnôt do aplikácie + GUI 
            # ------------------------------------------------------------
            try:
                # Inštančné premenné (font_size spravujeme výhradne cez self.font_size)
                self.font_size = int(full_config["font_size"])
                self.bottom_margin = full_config["bottom_margin"]
                self.reserved_vertical_ratio = full_config["reserved_vertical_ratio"]
                self.fade_speed = full_config["fade_speed"]
                self.song_folder_path = Path(full_config["song_folder"]).resolve()                

                # Priradenie do TK premenných cez set_safe
                set_safe("font_size_var", self.font_size)
                set_safe("bottom_margin_var", self.bottom_margin)
                set_safe("reserved_vertical_var", self.reserved_vertical_ratio)
                set_safe("fade_speed_var", self.fade_speed)
                set_safe("pouzit_vlastnu_farbu", use_custom)
                set_safe("obdobie_var", self.liturgical_season)
                set_safe("text_color_var", full_config["text_color"])
                set_safe("default_filter_var", self.default_filter_obdobie)

                # Liturgický rok A / B / C – vždy sa použije automaticky vypočítaná hodnota
                lit_year = vypocitaj_liturgicky_rok()
                set_safe("liturgical_year_var", lit_year)

                # Aktualizácia titulku okna podľa načítaného roka a aktuálnej liturgickej časti
                try:
                    self.aktualizovat_info_liturgickeho_roka(lit_year)
                except Exception as e:
                    log_exception("nacitat_nastavenia: nepodarilo sa aktualizovať titulok okna", e)
                
                # Prepínače
                self.zobrazit_direktorium = bool(full_config.get("zobrazit_direktorium", False))
                set_safe("zobrazit_direktorium_var", self.zobrazit_direktorium)
                
                self.zobrazovat_live_preview = bool(full_config.get("zobrazovat_live_preview", True))
                set_safe("zobrazovat_live_preview_var", self.zobrazovat_live_preview)
                
                self.zobrazovat_specialne_znaky = bool(full_config.get("zobrazovat_specialne_znaky", True))
                set_safe("zobrazovat_specialne_znaky_var", self.zobrazovat_specialne_znaky)

                self.zobrazovat_znaky_chorov = bool(full_config.get("zobrazovat_znaky_chorov", True))
                set_safe("zobrazovat_znaky_chorov_var", self.zobrazovat_znaky_chorov)

                self.statusbar_tyzden_zaltara = bool(full_config.get("statusbar_tyzden_zaltara", True))
                set_safe("statusbar_tyzden_zaltara_var", self.statusbar_tyzden_zaltara)
                self.statusbar_skratka_zalmu = bool(full_config.get("statusbar_skratka_zalmu", True))
                set_safe("statusbar_skratka_zalmu_var", self.statusbar_skratka_zalmu)
                self.statusbar_jks_piesne = bool(full_config.get("statusbar_jks_piesne", True))
                set_safe("statusbar_jks_piesne_var", self.statusbar_jks_piesne)
                self.aktualizovat_status_bar()

                self.diagnostika_povolena = bool(full_config.get("diagnostika_povolena", True))
                set_safe("diagnostika_povolena_var", self.diagnostika_povolena)
                nastav_diagnostiku(self.diagnostika_povolena)

                # Pomocník
                self.pomocnik_font_size = full_config["pomocnik_font_size"]
                self.pomocnik_x = full_config.get("pomocnik_x", -1)
                self.pomocnik_y = full_config.get("pomocnik_y", -1)
                self.pomocnik_width = full_config.get("pomocnik_width", -1)
                self.pomocnik_height = full_config.get("pomocnik_height", -1)
                self.pomocnik_last_tab = max(0, min(full_config.get("pomocnik_last_tab", 0), 5))

                # Hlavné okno – uložené rozmery a pozícia
                self.main_window_x      = full_config.get("main_window_x", -1)
                self.main_window_y      = full_config.get("main_window_y", -1)
                self.main_window_width  = full_config.get("main_window_width", -1)
                self.main_window_height = full_config.get("main_window_height", -1)

                # Okno Nastavenia – uložené rozmery
                self.settings_window_width = full_config.get("settings_window_width", -1)
                self.settings_window_height = full_config.get("settings_window_height", -1)

                # Okno Direktórium a Slávenia – uložené rozmery
                self.direktorium_window_width  = full_config.get("direktorium_window_width", -1)
                self.direktorium_window_height = full_config.get("direktorium_window_height", -1)
                self.slavnosti_window_width    = full_config.get("slavnosti_window_width", -1)
                self.slavnosti_window_height   = full_config.get("slavnosti_window_height", -1)

                # Okno O aplikácii – uložené rozmery
                self.about_window_width  = full_config.get("about_window_width", -1)
                self.about_window_height = full_config.get("about_window_height", -1)
                self.about_last_tab = max(1, min(full_config.get("about_last_tab", 1), 4))
                self.about_font_size = max(8, min(full_config.get("about_font_size", 12), 40))

                # Preferovaný monitor – načítanie z configu
                self.preferred_monitor_index = max(0, int(full_config.get("preferred_monitor_index", 0)))

                # Synchronizácia s projekčným oknom
                if self.projection_window is not None:
                    pw = self.projection_window
                    pw.font_size = self.font_size
                    pw.bottom_margin = self.bottom_margin
                    pw.reserved_vertical_ratio = self.reserved_vertical_ratio
                    pw.fade_speed = self.fade_speed
                    pw.zobrazovat_live_preview = self.zobrazovat_live_preview
                    pw.zobrazovat_specialne_znaky = self.zobrazovat_specialne_znaky
                    pw.zobrazovat_znaky_chorov = self.zobrazovat_znaky_chorov
                    pw.preferred_monitor_index = self.preferred_monitor_index

            except Exception as e:
                log_exception("nacitat_nastavenia: chyba pri aplikovaní hodnôt do GUI", e)

            # ------------------------------------------------------------
            # 7) Finálny stav
            # ------------------------------------------------------------
            self.config = full_config    
                
        finally:
            # Tento kód sa vykoná VŽDY, bez ohľadu na to, či vyššie nastala chyba alebo nie.
            self._loading_settings = False

        # Ak sme počas validácie opravili chyby, uložíme opravený súbor.
        # DÔLEŽITÉ: Volanie musí byť AŽ TU, po finally bloku – keď je _loading_settings = False.
        # Keby sme volali ulozit_nastavenia() vnútri try bloku, zablokovala by ju stráž
        # „if _loading_settings: return" a config by sa nikdy nezapísal na disk.
        if needs_forced_save:
            self.ulozit_nastavenia()
    
    
    def _zbieraj_a_normalizuj_nastavenia_z_gui(self) -> dict:
        """
        Načíta hodnoty z GUI premenných (Tkinter *Var objektov) do atribútov
        `self.*` a doplní chýbajúce konfiguračné atribúty defaultmi (potrebné
        napr. pre unit testy vytvárajúce ControlApp cez object.__new__).

        Vracia slovník s hodnotami, ktoré sa nedostávajú priamo do `self`
        (napr. `pouzit_vlastnu_farbu`), a sú potrebné až pri zostavovaní
        slovníka pre config.json v `_zostav_config_dict`.
        """
        try:
            if hasattr(self, "font_size_var"):
                try:
                    self.font_size = int(self.font_size_var.get())
                except ValueError:
                    pass

        except Exception as e:
            log_exception("Chyba pri spracovaní veľkosti fontu", e)

        # ------------------------------------------------------------
        # TOTO MUSÍ BYŤ ÚPLNE MIMO except BLOKU
        # ------------------------------------------------------------

        self.text_color = self.text_color_var.get() if hasattr(self, "text_color_var") else "#ffffff"
        self.zobrazit_direktorium = self.zobrazit_direktorium_var.get() if hasattr(self, "zobrazit_direktorium_var") else False
        self.fade_speed = self.fade_speed_var.get() if hasattr(self, "fade_speed_var") else "mierne rýchle"
        self.zobrazovat_live_preview = self.zobrazovat_live_preview_var.get() if hasattr(self, "zobrazovat_live_preview_var") else True
        self.zobrazovat_specialne_znaky = self.zobrazovat_specialne_znaky_var.get() if hasattr(self, "zobrazovat_specialne_znaky_var") else True
        self.zobrazovat_znaky_chorov = self.zobrazovat_znaky_chorov_var.get() if hasattr(self, "zobrazovat_znaky_chorov_var") else True
        self.statusbar_tyzden_zaltara = self.statusbar_tyzden_zaltara_var.get() if hasattr(self, "statusbar_tyzden_zaltara_var") else True
        self.statusbar_skratka_zalmu = self.statusbar_skratka_zalmu_var.get() if hasattr(self, "statusbar_skratka_zalmu_var") else True
        self.statusbar_jks_piesne = self.statusbar_jks_piesne_var.get() if hasattr(self, "statusbar_jks_piesne_var") else True
        self.aktualizovat_status_bar()
        self.diagnostika_povolena = self.diagnostika_povolena_var.get() if hasattr(self, "diagnostika_povolena_var") else True
        nastav_diagnostiku(self.diagnostika_povolena)
        self.bottom_margin = self.bottom_margin_var.get() if hasattr(self, "bottom_margin_var") else 50
        self.reserved_vertical_ratio = self.reserved_vertical_var.get() if hasattr(self, "reserved_vertical_var") else 0.20

        pouzit_vlastnu = self.pouzit_vlastnu_farbu.get() if hasattr(self, "pouzit_vlastnu_farbu") else False
        lit_season = self.obdobie_var.get() if hasattr(self, "obdobie_var") else "Cezročné"
        def_filter = self.default_filter_var.get() if hasattr(self, "default_filter_var") else "Cezročné C2"

        # Niektoré unit testy vytvárajú ControlApp cez object.__new__ bez __init__.
        # Chýbajúce konfiguračné atribúty preto doplníme na jednom mieste.
        config_attr_defaults = {
            "statusbar_tyzden_zaltara": True,
            "statusbar_skratka_zalmu": True,
            "statusbar_jks_piesne": True,
            "diagnostika_povolena": DEFAULT_CONFIG.get("diagnostika_povolena", True),
            "pomocnik_font_size": DEFAULT_CONFIG.get("pomocnik_font_size", 14),
            "pomocnik_x": DEFAULT_CONFIG.get("pomocnik_x", -1),
            "pomocnik_y": DEFAULT_CONFIG.get("pomocnik_y", -1),
            "pomocnik_width": DEFAULT_CONFIG.get("pomocnik_width", -1),
            "pomocnik_height": DEFAULT_CONFIG.get("pomocnik_height", -1),
            "pomocnik_last_tab": DEFAULT_CONFIG.get("pomocnik_last_tab", 1),
            "main_window_x": -1,
            "main_window_y": -1,
            "main_window_width": -1,
            "main_window_height": -1,
            "settings_window_width": DEFAULT_CONFIG.get("settings_window_width", -1),
            "settings_window_height": DEFAULT_CONFIG.get("settings_window_height", -1),
            "direktorium_window_width": DEFAULT_CONFIG.get("direktorium_window_width", -1),
            "direktorium_window_height": DEFAULT_CONFIG.get("direktorium_window_height", -1),
            "slavnosti_window_width": DEFAULT_CONFIG.get("slavnosti_window_width", -1),
            "slavnosti_window_height": DEFAULT_CONFIG.get("slavnosti_window_height", -1),
            "about_window_width": DEFAULT_CONFIG.get("about_window_width", -1),
            "about_window_height": DEFAULT_CONFIG.get("about_window_height", -1),
            "about_last_tab": DEFAULT_CONFIG.get("about_last_tab", 1),
            "about_font_size": DEFAULT_CONFIG.get("about_font_size", 12),
        }
        for attr_name, default_value in config_attr_defaults.items():
            if not hasattr(self, attr_name):
                setattr(self, attr_name, default_value)

        return {
            "pouzit_vlastnu": pouzit_vlastnu,
            "lit_season": lit_season,
            "def_filter": def_filter,
        }

    def _synchronizuj_zivy_nahlad_a_projekciu(self, aktualizovat_label: bool) -> None:
        """
        Premietne práve načítané nastavenia (farba textu, veľkosť fontu,
        rýchlosť prelínania a pod.) okamžite do živého náhľadu v ovládacom
        okne, do prípadného otvoreného projekčného okna, a prekreslí
        aktuálne zobrazenú strofu. Musí bežať až PO
        `_zbieraj_a_normalizuj_nastavenia_z_gui`, keďže číta hodnoty
        (self.text_color, self.fade_speed, ...), ktoré tá metóda nastavuje.
        """
        # A) AKTUALIZÁCIA LIVE PREVIEW (Farba textu v ovládacom okne)
        # OPRAVA: Použitie správneho názvu premennej self.live_preview_label
        preview_label = getattr(self, "live_preview_label", None)
        if preview_label is not None and preview_label.winfo_exists():
            try:
                preview_label.config(fg=self.text_color)
                # Ak je text zobrazený, vynútime prekreslenie, aby sa aplikovala nová farba
                if getattr(self, "is_text_visible", False):
                     current_text = preview_label.cget("text")
                     if current_text:
                         self.update_live_preview(current_text)
            except Exception as e:
                log_exception("ulozit_nastavenia: Chyba pri aktualizácii live_preview_label farby", e)
                

        # B) AKTUALIZÁCIA PROJEKČNÉHO OKNA
        pw = getattr(self, "projection_window", None)

        if isinstance(pw, ProjectionWindow):
            try:
                pw.fade_speed = self.fade_speed
                pw.bottom_margin = self.bottom_margin
                pw.reserved_vertical_ratio = self.reserved_vertical_ratio
                pw.font_size = self.font_size
                pw.zobrazovat_specialne_znaky = self.zobrazovat_specialne_znaky
                pw.zobrazovat_znaky_chorov = self.zobrazovat_znaky_chorov
                pw.zobrazovat_live_preview = self.zobrazovat_live_preview

                pw.target_text_color = self.text_color

                aktualny_text = getattr(pw, "raw_text_content", "") or getattr(pw, "current_text_content", "")
                if aktualny_text:
                    pw.update_text(aktualny_text)

                if hasattr(self, "aktualizovat_vzhlad"):
                    self.aktualizovat_vzhlad()

            except Exception as e:
                log_exception("ulozit_nastavenia: Chyba pri synchronizácii projekcie", e)

        # C) OKAMŽITÉ PREKRESLENIE AKTUÁLNEJ STROFY
        # Prepínače ako [L]/[P] a špeciálne znaky sú len prezentačná vrstva;
        # aktuálny text preto prekreslíme z pôvodných aktualne_strofy bez reloadu súboru.
        if aktualizovat_label and getattr(self, "aktualne_strofy", None):
            try:
                self._dopln_znaky_chorov_do_aktualnych_vespier()
                self.zobraz_aktualnu_strofu()
            except Exception as e:
                log_exception("ulozit_nastavenia: Chyba pri prekreslení aktuálnej strofy", e)

    def _zostav_config_dict(self, pouzit_vlastnu: bool, lit_season: str, def_filter: str) -> dict:
        """
        Poskladá a vráti slovník so všetkými hodnotami určenými na zápis
        do config.json. Čisto dátová transformácia bez I/O a bez
        vedľajších účinkov na GUI.
        """
        current_song_folder = str(getattr(self, "song_folder_path", Path(DEFAULT_SONG_FOLDER)))

        liturgical_year_var = getattr(self, "liturgical_year_var", None)
        liturgical_year_value = liturgical_year_var.get() if liturgical_year_var is not None else vypocitaj_liturgicky_rok()

        return {
            "text_color": self.text_color,
            "font_size": int(self.font_size),
            "song_folder": current_song_folder,
            "base_dir": str(BASE_DIR),
            "liturgical_season": lit_season,
            "liturgical_year": liturgical_year_value or vypocitaj_liturgicky_rok(),
            "default_filter_obdobie": def_filter,
            "pouzit_vlastnu_farbu": pouzit_vlastnu,
            "bottom_margin": int(self.bottom_margin),
            "reserved_vertical_ratio": float(self.reserved_vertical_ratio),
            "zobrazit_direktorium": bool(self.zobrazit_direktorium),
            "zobrazovat_live_preview": bool(self.zobrazovat_live_preview),
            "zobrazovat_specialne_znaky": bool(self.zobrazovat_specialne_znaky),
            "zobrazovat_znaky_chorov": bool(self.zobrazovat_znaky_chorov),
            "statusbar_tyzden_zaltara": bool(self.statusbar_tyzden_zaltara),
            "statusbar_skratka_zalmu": bool(self.statusbar_skratka_zalmu),
            "statusbar_jks_piesne": bool(self.statusbar_jks_piesne),
            "diagnostika_povolena": bool(self.diagnostika_povolena),
            "fade_speed": self.fade_speed,
            "pomocnik_font_size": int(self.pomocnik_font_size),
            "pomocnik_x": int(self.pomocnik_x),
            "pomocnik_y": int(self.pomocnik_y),
            "pomocnik_width": int(self.pomocnik_width),
            "pomocnik_height": int(self.pomocnik_height),
            "pomocnik_last_tab": int(self.pomocnik_last_tab),
            "main_window_x":      int(self.main_window_x),
            "main_window_y":      int(self.main_window_y),
            "main_window_width":  int(self.main_window_width),
            "main_window_height": int(self.main_window_height),
            "settings_window_width":  int(self.settings_window_width),
            "settings_window_height": int(self.settings_window_height),
            "direktorium_window_width":  int(self.direktorium_window_width),
            "direktorium_window_height": int(self.direktorium_window_height),
            "slavnosti_window_width":    int(self.slavnosti_window_width),
            "slavnosti_window_height":   int(self.slavnosti_window_height),
            "about_window_width":        int(self.about_window_width),
            "about_window_height":       int(self.about_window_height),
            "about_last_tab":            int(self.about_last_tab),
            "about_font_size":           int(self.about_font_size),
            "preferred_monitor_index":   int(getattr(self, "preferred_monitor_index", 0)),
        }

    def _zapis_config_na_disk(self, new_config: dict, aktualizovat_label: bool) -> None:
        """
        Atomicky zapíše `new_config` do CONFIG_FILE_PATH (cez dočasný súbor
        + os.replace). Pri zlyhaní zápisu (napr. PermissionError do AppData)
        ponúkne používateľovi uloženie do náhradného súboru cez dialóg
        "Uložiť ako".
        """
        target_dir = CONFIG_FILE_PATH.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        def uloz_alternativne(temp_path_obj=None):
            alt_path_str = filedialog.asksaveasfilename(
                title="Uložiť nastavenia ako",
                defaultextension=".json",
                filetypes=[("JSON súbory", "*.json"), ("Všetky súbory", "*.*")],
                initialfile="config.json"
            )
            if alt_path_str:
                try:
                    alt_path = Path(alt_path_str)
                    if temp_path_obj and temp_path_obj.exists():
                        config_text = temp_path_obj.read_text(encoding="utf-8")
                    else:
                        config_text = json.dumps(new_config, ensure_ascii=False, indent=4)
                    _zapis_text_atomicky(alt_path, config_text, encoding="utf-8")
                except Exception as ex:
                    log_exception("uloz_alternativne: zlyhalo", ex)

        temp_path = None
        try:
            fd, temp_str = tempfile.mkstemp(dir=str(target_dir), prefix="config_", suffix=".json")
            temp_path = Path(temp_str)

            with os.fdopen(fd, 'w', encoding='utf-8') as tf:
                json.dump(new_config, tf, ensure_ascii=False, indent=4)
                tf.flush()
                os.fsync(tf.fileno())

            os.replace(str(temp_path), str(CONFIG_FILE_PATH))
            temp_path = None 

            self.config = new_config

            if aktualizovat_label and self.song_folder_label is not None:
                self.song_folder_label.config(text=str(new_config.get("song_folder", "")))

        except PermissionError as e:
            log_exception("ulozit_nastavenia: Prístup zamietnutý do AppData", e)
            if messagebox.askyesno("Kinak: Prístup zamietnutý", 
                                  "Aplikácia nemá práva na zápis do konfiguračného priečinka.\nChcete nastavenia uložiť do iného súboru?"):
                uloz_alternativne(temp_path)
        except Exception as e:
            log_exception("ulozit_nastavenia: Kritická chyba pri zápise", e)
            uloz_alternativne(temp_path)
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as e:
                    log_exception("ulozit_nastavenia: nepodarilo sa odstrániť temp súbor", e)

    def ulozit_nastavenia(self, aktualizovat_label=True):
        """
        Uloží aktuálne nastavenia z GUI do súboru config.json pomocou atomického zápisu.
        Aktualizuje vizuálne parametre (farby, fonty, Live Preview) v reálnom čase.

        Táto metóda je už len tenký orchestrátor (SRP) nad štyrmi
        samostatnými krokmi, z ktorých každý má jednu zodpovednosť:
          1. `_zbieraj_a_normalizuj_nastavenia_z_gui` – zber dát z GUI
             premenných + doplnenie chýbajúcich atribútov defaultmi.
          2. `_synchronizuj_zivy_nahlad_a_projekciu` – okamžitá vizuálna
             reakcia (Live Preview, projekčné okno, aktuálna strofa).
          3. `_zostav_config_dict` – poskladanie slovníka pre config.json.
          4. `_zapis_config_na_disk` – atomický zápis na disk vrátane
             fallbacku pri PermissionError.
        """
        # Prevencia zacyklenia (neukladáme, ak práve načítavame)
        if getattr(self, "_loading_settings", False) is True:
            return

        extra = self._zbieraj_a_normalizuj_nastavenia_z_gui()
        self._synchronizuj_zivy_nahlad_a_projekciu(aktualizovat_label)
        new_config = self._zostav_config_dict(**extra)
        self._zapis_config_na_disk(new_config, aktualizovat_label)

    def vytvorit_gui(self):
        style = ttk.Style()
        style.configure("TButton", font=(self.font_family, 12), padding=6)
        style.configure("TLabel", font=(self.font_family, 12))
        style.configure("Header.TLabel", font=(self.font_family, 13, "bold"), foreground="#AAAAAA")
        style.configure("Settings.TButton", font=(self.font_family, 14), padding=2)

        # globálne nastavenie pre combobox listbox
        self.master.option_add("*TCombobox*Listbox.font", (self.font_family, 11))
        self.master.option_add("*TCombobox*Listbox.justify", "left")

        horny_frame = tk.Frame(self.master, bg=PANEL_BG_COLOR, height=60)
        horny_frame.pack_propagate(False)
        horny_frame.pack(side=tk.TOP, fill=tk.X, anchor="ne", pady=(0, 0))

        # --- STATUS BAR (spodok hlavného okna) ---
        self.status_bar_frame = tk.Frame(self.master, bg=PANEL_BG_COLOR, height=28)
        self.status_bar_frame.pack_propagate(False)
        self.status_bar_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_bar_zaltár_label = tk.Label(
            self.status_bar_frame,
            text="",
            font=(self.font_family, 12),
            fg="#aaaaaa",
            bg=PANEL_BG_COLOR,
            anchor="w",
            padx=15
        )
        self.status_bar_zaltár_label.pack(side=tk.LEFT, fill=tk.Y)
        self.aktualizovat_status_bar()

        # --- Combobox "Zoznam piesní" vľavo ---
        self.song_var = tk.StringVar()
        style.configure("Big.TCombobox", padding=5)

        # Povolené písanie (nutné pre vyhľadávanie)
        self.song_combobox = ttk.Combobox(
            horny_frame,
            textvariable=self.song_var,
            state="normal",
            width=38,
            style="Big.TCombobox",
            font=(self.font_family, 12),
            height=12
        )       
        
        # Kompletný zoznam piesní
        self.cele_hodnoty_comboboxu = ["Zoznam piesní"] + [
            f"{num} - {title}" for num, title in self.zoznam_piesni_data
        ]
        self.song_combobox["values"] = self.cele_hodnoty_comboboxu
        self.song_combobox.current(0)
        self.song_combobox.pack(side=tk.LEFT, padx=(10, 0), pady=(8, 2), ipady=1)

        # --- Filtrovanie počas písania ---
        # Normalizácia diakritiky: používa sa globálna funkcia normalize_diacritics()
        def on_combobox_typing(event):
            if event.keysym in ("Up", "Down", "Left", "Right", "Return", "Escape", "Tab"):
                return

            # Zapamätáme si text a pozíciu kurzora
            current_text = self.song_combobox.get()
            cursor_pos = self.song_combobox.index(tk.INSERT)

            if current_text == "":
                nove = self.cele_hodnoty_comboboxu
            else:
                zadany_norm = normalize_diacritics(current_text)
                nove = [
                    h for h in self.cele_hodnoty_comboboxu
                    if zadany_norm in normalize_diacritics(h)
                ]

            # Nastavíme nové hodnoty
            self.song_combobox["values"] = nove

            # Znovu otvoríme dropdown.
            # Používame ttk::combobox::Post namiesto event_generate("<Down>"),
            # pretože Down-event vyžaduje focus a môže spôsobiť dvojité otvorenie.
            # ttk::combobox::Post je síce nedokumentovaná v man pages, ale je
            # verejná Tcl proc definovaná v lib/ttk/combobox.tcl od Tk 8.5 (2007)
            # a stabilná naprieč všetkými relevantými verziami Pythonu/Tk.
            try:
                self.song_combobox.tk.call('ttk::combobox::Post', self.song_combobox)
            except tk.TclError:
                pass

            # Obnovíme text aj kurzor
            self.song_combobox.delete(0, tk.END)
            self.song_combobox.insert(0, current_text)

            try:
                self.song_combobox.icursor(cursor_pos)
            except Exception as e:
                log_exception("vytvorit_gui: icursor zlyhal", e)


        # --- Handler pre výber piesne (kliknutie alebo Enter) ---
        def on_song_selected(event=None):
            selection = self.song_combobox.get()

            if selection == "Zoznam piesní" or not selection:
                return

            # Ak používateľ napísal len časť názvu
            if selection not in self.cele_hodnoty_comboboxu:
                sel_norm = normalize_diacritics(selection)
                zhody = [
                    h for h in self.cele_hodnoty_comboboxu
                    if sel_norm in normalize_diacritics(h)
                ]
                if zhody:
                    selection = zhody[0]
                    self.song_var.set(selection)
                else:
                    return

            self.reset_ui()

            try:
                num_display = selection.split(" - ")[0]
                self.nacitat_piesne(nazov_suboru=num_display)
                self.aktualizuj_popis(num_display)

                self.manual_entry.delete(0, tk.END)
                self.manual_entry.insert(0, format_cislo_piesne_pre_vstup(num_display))

                self.subor_var.set("—")

                # Po výbere obnovíme celý zoznam
                self.song_combobox["values"] = self.cele_hodnoty_comboboxu

                self.master.after_idle(self.manual_entry.focus_set)
                self.nazov_piesne = num_display
                self.aktualne_cislo_piesne = num_display

            except Exception as e:
                log_exception("Chyba pri načítaní piesne", e)


        self.song_combobox.bind("<<ComboboxSelected>>", on_song_selected)
        self.song_combobox.bind("<Return>", on_song_selected)
        for k in ["<KeyPress-plus>", "<KeyPress-minus>", "<KeyPress-KP_Add>", "<KeyPress-KP_Subtract>"]:
            self.song_combobox.bind(k, self.klavesa_plus if 'plus' in k or 'Add' in k else self.klavesa_minus)
        self.song_combobox.bind("=", self.klavesa_plus)

        def prepni_focus_tab(event=None):
            widget = getattr(event, "widget", None)
            try:
                if widget is self.manual_entry:
                    self.song_combobox.focus_set()
                    self.song_combobox.icursor(tk.END)
                else:
                    self.manual_entry.focus_set()
                    self.manual_entry.icursor(tk.END)
            except Exception as e:
                log_exception("prepni_focus_tab: zlyhalo prepnutie fokusu", e)
            return "break"

        self.song_combobox.bind("<Tab>", prepni_focus_tab)

        # bielym písmom "názov súboru - strofa 1/25"
        self.nazov_label = tk.Label(
            self.master,
            font=(self.font_family, 15, "bold"),
            fg="#ffffff",
            bg=BACKGROUND_COLOR,
            anchor="center",
            justify=tk.CENTER
        )
        self.nazov_label.place(relx=0.50, y=30, anchor="center")

        # --- Rámik pre tlačidlá napravo ---
        buttons_frame = tk.Frame(horny_frame, bg=PANEL_BG_COLOR)
        buttons_frame.pack(side=tk.RIGHT, padx=(0, 5), pady=(8, 2))

        # --- ŠTÝL PRE IKONY ---
        style.configure("Icon.TButton", font=("Segoe UI Symbol", 13))
        style.configure("Download.TMenubutton", font=(self.font_family, 13), padding=6)

        toolbar_btn_bg = "#1C1C1C"
        toolbar_btn_fg = "#E0E0E0"
        toolbar_btn_active = "#F2F2F2"
        toolbar_menu_active_bg = "#333333"

        def vytvor_toolbar_menu(parent):
            return tk.Menu(
                parent,
                tearoff=0,
                font=(self.font_family, 13),
                bg=toolbar_btn_bg,
                fg=toolbar_btn_fg,
                activebackground=toolbar_menu_active_bg,
                activeforeground=toolbar_btn_active,
                borderwidth=0
            )

        def styl_toolbar_widget(widget):
            widget.configure(
                bg=toolbar_btn_bg,
                fg=toolbar_btn_fg,
                activebackground=toolbar_btn_bg,
                activeforeground=toolbar_btn_active,
                relief="flat",
                borderwidth=0,
                highlightthickness=0,
                font=(self.font_family, 13),
                padx=10,
                pady=5
            )
            widget.pack(side=tk.LEFT, padx=0)
            return widget

        styl_toolbar_widget(tk.Button(
            buttons_frame,
            text="Nastavenia",
            command=self.zobrazit_nastavenia
        ))

        liturgicke_nastroje_btn = styl_toolbar_widget(tk.Menubutton(buttons_frame, text="Liturgické nástroje"))
        liturgicke_nastroje_menu = vytvor_toolbar_menu(liturgicke_nastroje_btn)
        liturgicke_nastroje_menu.add_command(label="Direktórium", command=self.open_direktorium)
        liturgicke_nastroje_menu.add_command(label="Slávenia", command=self.open_slavnosti)
        liturgicke_nastroje_menu.add_separator()
        liturgicke_nastroje_menu.add_command(label="Stiahnuť čítania", command=self.open_citanie)
        liturgicke_nastroje_menu.add_command(label="Stiahnuť vešpery", command=self.open_vespery)

        refreny_zalmov_menu = vytvor_toolbar_menu(liturgicke_nastroje_menu)
        refreny_zalmov_menu.add_command(label="Mesačné (1L–12L)", command=self.open_refreny_zalmov)
        refreny_zalmov_menu.add_command(label="Adventné (1AD–4AD)", command=self.open_adventne_refreny)
        refreny_zalmov_menu.add_command(label="Vianočné (1VI, 2VI, SJE, NEV...)", command=self.open_vianocne_sviatky)
        refreny_zalmov_menu.add_command(label="Pôstne a veľkonočné (PS, 1P–VT–7VN)", command=self.open_postne_velkonocne_refreny)
        refreny_zalmov_menu.add_command(label="Turíce a nadväzujúce sviatky (1TS–7TS)", command=self.open_turicne_sviatky)
        refreny_zalmov_menu.add_command(label="Cezročné týždne (1C1–34C2)", command=self.open_cezrocne_tyzdenne_refreny)        
        refreny_zalmov_menu.add_command(label="Cezročné sviatky (OND, NJK, BAR...)", command=self.open_liturgicke_sviatky)
        liturgicke_nastroje_menu.add_cascade(label="Stiahnuť refrény žalmov", menu=refreny_zalmov_menu)

        liturgicke_nastroje_btn["menu"] = liturgicke_nastroje_menu

        pomoc_btn = styl_toolbar_widget(tk.Menubutton(buttons_frame, text="Pomoc"))
        pomoc_menu = vytvor_toolbar_menu(pomoc_btn)
        pomoc_menu.add_command(label="Pomocník", command=self.otvorit_pomocnika)       
        pomoc_menu.add_command(label="Rýchly sprievodca", command=self.zobraz_rychly_sprievodca)
        pomoc_menu.add_separator()
        pomoc_menu.add_command(label="O aplikácii", command=self.zobrazit_o_aplikacii)
        pomoc_btn["menu"] = pomoc_menu

        # --- INDIKÁTOR ŽIAROVKY ---
        self.indikator_ziarovka = tk.Canvas(
            horny_frame, width=50, height=52, highlightthickness=0, bg=PANEL_BG_COLOR
        )
        self.indikator_id = self.indikator_ziarovka.create_rectangle(
            8, 8, 42, 42, fill="#888888", outline=""
        )
        self.indikator_ziarovka.pack(side=tk.RIGHT, padx=(0, 0), pady=(8, 2))     

        # --- PANEL AKTUÁLNA STROFA (Hore) ---
        panel_strofa_hore = tk.Frame(self.master, bg=BACKGROUND_COLOR, height=250)
        panel_strofa_hore.pack_propagate(False)
        panel_strofa_hore.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 0))

        self.strofa_label = tk.Text(
            panel_strofa_hore, wrap=tk.WORD, bg=BACKGROUND_COLOR, fg=self.text_color_var.get(),
            relief=tk.FLAT, bd=0, padx=20, pady=10, spacing1=1, spacing2=2, spacing3=1
        )
        self.strofa_label.bind("<Button-1>", lambda e: "break")
        self.strofa_label.tag_configure("center", justify="center", font=(self.font_family, 25, "bold"))
        self.strofa_label.config(state=tk.DISABLED)
        self.strofa_label.pack(fill=tk.BOTH, expand=True)

        # --- HLAVNÝ OBSAH ---
        hlavny_frame = tk.Frame(self.master, bg=PANEL_BG_COLOR)
        hlavny_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Panel výberu (Vľavo)
        frame_vyber = tk.Frame(hlavny_frame, width=205, bg=PANEL_BG_COLOR)
        frame_vyber.pack_propagate(False)
        frame_vyber.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        panel_vyber = tk.LabelFrame(frame_vyber, bg=PANEL_BG_COLOR, padx=10, pady=10)
        panel_vyber.pack(fill=tk.BOTH, expand=True)

        self.manual_entry = tk.Entry(
            panel_vyber, font=(self.font_family, 25, "bold"), bg="#1e1e1e",
            fg=self.text_color_var.get(), insertbackground=self.text_color_var.get(), justify="center"
        )
        self.manual_entry.pack(fill=tk.X, pady=(0, 10))

        self.manual_entry_hint = tk.Label(
            panel_vyber, text="Zadaj č. piesne alebo vyber žalm z menu nižšie", font=(self.font_family, 11, "italic"),
            fg="#aaaaaa", bg=PANEL_BG_COLOR, wraplength=180, justify=tk.CENTER
        )
        self.manual_entry_hint.pack(pady=(0, 10))

        # Bindings
        self.manual_entry.bind("<FocusOut>", self.skus_manualne_nacitanie)
        self.manual_entry.bind("<KeyPress-Return>", self.manual_entry_enter)
        self.manual_entry.bind("<KeyRelease>", self.odlozene_auto_nacitanie)
        for k in ["<KeyPress-plus>", "<KeyPress-minus>", "<KeyPress-KP_Add>", "<KeyPress-KP_Subtract>"]:
            self.manual_entry.bind(k, self.klavesa_plus if 'plus' in k or 'Add' in k else self.klavesa_minus)
        self.manual_entry.bind("=", self.klavesa_plus)
        self.manual_entry.bind("<Right>", self.klavesa_vpravo)
        self.manual_entry.bind("<Left>", self.klavesa_vlavo)
        self.manual_entry.bind("<FocusIn>", self.vymazat_subor_menu)
        self.manual_entry.bind("<Tab>", prepni_focus_tab)

        # Filtre a menu
        self.filter_var = tk.StringVar(value=self.default_filter_var.get())
        self.filter_menu = tk.OptionMenu(panel_vyber, self.filter_var, *list(self.obdobie_subory.keys()), command=self.filtrovat_subory)
        self.filter_menu.config(font=(self.font_family, 14, "bold"), width=16)
        self.filter_menu.pack(pady=(0, 10))

        self.subor_var = tk.StringVar(value="—")
        self.subory_zoznam = self.ziskaj_zoznam_suborov()
        self.subor_menu = tk.OptionMenu(panel_vyber, self.subor_var, *["—"], command=self.nacitat_podla_menu)
        self.subor_menu.config(font=(self.font_family, 14, "bold"), width=16)
        self.subor_menu.pack(pady=(0, 10))

        self.popis_label = tk.Label(panel_vyber, text="", font=(self.font_family, 12, "italic"), fg="#bbbbbb", bg=PANEL_BG_COLOR, wraplength=180)
        self.popis_label.pack(pady=(0, 5))

        self.direktorium_label = tk.Label(panel_vyber, text="", font=(self.font_family, 11), fg=DIREKTORIUM_LABEL_FG, bg=PANEL_BG_COLOR, wraplength=180, justify=tk.LEFT)
        self.direktorium_label.pack()
        self.aktualizovat_direktorium_label()        

        # 2. Panel obsah súboru (V strede)
        panel_obsah = tk.LabelFrame(hlavny_frame, bg=PANEL_BG_COLOR, padx=10, pady=10)
        panel_obsah.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(panel_obsah)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.obsah_suboru_text = tk.Text(
            panel_obsah, wrap=tk.WORD, font=(self.font_family, 14), bg="#1e1e1e", fg="#dddddd",
            yscrollcommand=scrollbar.set, padx=15, pady=10
        )
        self.obsah_suboru_text.bind("<Button-1>", lambda e: "break")
        self.obsah_suboru_text.config(state=tk.DISABLED, spacing3=2)
        self.obsah_suboru_text.tag_config("highlight", background="#444444", foreground=self.text_color_var.get(), font=(self.font_family, 18, "bold"))
        self.obsah_suboru_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.obsah_suboru_text.yview)

        # --- LIVE PREVIEW ---
        self.preview_container = tk.Frame(
            self.master, width=350, height=160, bg=BACKGROUND_COLOR, bd=1, relief="solid",
            highlightthickness=1, highlightbackground="#373737"   # "#373737"   #444444"
        )
        self.preview_container.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")
        self.preview_container.pack_propagate(False)        
       
        # Ak pri štarte nie je náhľad povolený, okamžite ho schováme
        show_preview_var = getattr(self, "zobrazovat_live_preview_var", None)
        if not show_preview_var or not show_preview_var.get():
            self.preview_container.place_forget()

        self.live_preview_label = tk.Label(
            self.preview_container, 
            text="", 
            font=(self.font_family, 14, "bold"),
            fg=self.text_color_var.get(), 
            bg=BACKGROUND_COLOR, 
            justify="center", 
            anchor="center"
        )       
        
        # padx=(ľavé, pravé) -> (25, 10) znamená 25px zľava, 10px sprava
        # pady=(horné, dolné) -> (20, 10) znamená 20px zhora, 10px zdola        
        self.live_preview_label.pack(
            expand=True, 
            fill="both", 
            padx=25,  # 35px vľavo, 15px vpravo
            pady=20   # 25px hore, 15px dole
        )

        # Inicializácia po vytvorení
        self.filtrovat_subory(self.filter_var.get())
        
              
    def _zobraz_dialog_stiahnutia(self, title: str, nadpis: str, akcia):
        """
        Spoločný dialóg na výber dátumu sťahovania (čítania aj vešpery).

        Parametre
        ---------
        title  : titulok okna (napr. "Stiahnuť čítania")
        nadpis : text labelu nad tlačidlami (napr. "Stiahnuť čítania na:")
        akcia  : callable(datum) – zavolá sa po potvrdení výberu;
                 zodpovedá za samotné spustenie sťahovania
        """
        dialog = tk.Toplevel(self.master)
        dialog.title(title)
        dialog.configure(bg="#1e1e1e")
        dialog.resizable(False, False)
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.lift()
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

        self.master.update_idletasks()
        mx = self.master.winfo_x() + self.master.winfo_width() // 2
        my = self.master.winfo_y() + self.master.winfo_height() // 2
        dw, dh = 320, 290
        dialog.geometry(f"{dw}x{dh}+{mx - dw // 2}+{my - dh // 2}")

        tk.Label(
            dialog,
            text=nadpis,
            bg="#1e1e1e",
            fg="#ffffff",
            font=(self.font_family, 13, "bold")
        ).pack(pady=(18, 10))

        btn_style = {
            "bg": "#3a3a3a",
            "fg": "#ffffff",
            "activebackground": "#555555",
            "activeforeground": "#ffffff",
            "font": (self.font_family, 12, "bold"),
            "relief": "flat",
            "bd": 0,
            "padx": 28,
            "pady": 8,
            "cursor": "hand2"
        }

        def _spusti(datum):
            self.reset_ui()
            dialog.destroy()
            akcia(datum)

        # --- Tlačidlo Dnes ---
        tk.Button(
            dialog, text="Dnes",
            command=lambda: _spusti(date.today()),
            **btn_style
        ).pack()

        # --- Oddeľovač ---
        tk.Label(
            dialog,
            text="── alebo vybrať dátum ──",
            bg="#1e1e1e",
            fg="#888888",
            font=(self.font_family, 10)
        ).pack(pady=(14, 6))

        # --- Výber dátumu: DD . MM . YYYY ---
        dnes = date.today()
        frame_datum = tk.Frame(dialog, bg="#1e1e1e")
        frame_datum.pack()

        spin_style = {
            "bg": "#2e2e2e",
            "fg": "#ffffff",
            "buttonbackground": "#3a3a3a",
            "relief": "flat",
            "bd": 1,
            "font": (self.font_family, 13, "bold"),
            "justify": "center",
            "highlightthickness": 1,
            "highlightbackground": "#555555",
            "highlightcolor": "#aaaaaa",
        }

        sp_den = tk.Spinbox(
            frame_datum, from_=1, to=31, width=3,
            format="%02.0f", **spin_style
        )
        sp_den.pack(side=tk.LEFT)
        sp_den.delete(0, tk.END)
        sp_den.insert(0, f"{dnes.day:02d}")

        tk.Label(frame_datum, text=".", bg="#1e1e1e", fg="#888888",
                 font=(self.font_family, 14, "bold")).pack(side=tk.LEFT, padx=2)

        sp_mes = tk.Spinbox(
            frame_datum, from_=1, to=12, width=3,
            format="%02.0f", **spin_style
        )
        sp_mes.pack(side=tk.LEFT)
        sp_mes.delete(0, tk.END)
        sp_mes.insert(0, f"{dnes.month:02d}")

        tk.Label(frame_datum, text=".", bg="#1e1e1e", fg="#888888",
                 font=(self.font_family, 14, "bold")).pack(side=tk.LEFT, padx=2)

        rok_var = tk.StringVar(value=str(dnes.year))
        sp_rok = tk.Spinbox(
            frame_datum, from_=GREGORIANSKY_MIN_ROK, to=GREGORIANSKY_MAX_ROK, width=5,
            textvariable=rok_var, state="readonly", readonlybackground="#2e2e2e", **spin_style
        )
        sp_rok.pack(side=tk.LEFT)

        # --- Chybová správa a tlačidlo Stiahni vybraný dátum ---
        chyba_var = tk.StringVar(value="")
        tk.Label(dialog, textvariable=chyba_var, bg="#1e1e1e",
                 fg="#ff6b6b", font=(self.font_family, 9)).pack(pady=(4, 0))

        def stiahni_vybraty():
            try:
                den = int(sp_den.get())
                mes = int(sp_mes.get())
                rok = _validuj_rok_pre_gui(rok_var.get())
                vybrany = date(rok, mes, den)
            except ValueError:
                chyba_var.set("Neplatný dátum – skontroluj hodnoty.")
                return
            _spusti(vybrany)

        tk.Button(
            dialog, text="Stiahnuť vybraný dátum",
            command=stiahni_vybraty,
            **{**btn_style, "padx": 14}
        ).pack(pady=(2, 0))

        dialog.bind("<Return>", lambda e: stiahni_vybraty())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        dialog.focus_force()
        sp_den.focus_set()

    def open_citanie(self):
        """Zobrazí dialóg: Stiahnuť čítania na Dnes alebo na vybraný dátum."""

        def akcia(datum):
            def po_uspesnom_stiahnuti():
                # Automatická úprava čítaní pre projekciu prebehne potichu
                # (zobrazit_potvrdenie=False) – jediné okno, ktoré používateľ
                # uvidí, je finálne "Čítania aktualizované" zo spracuj_vysledok
                # v aktualizovat_citania_gui (analogicky ako pri vešperách).
                try:
                    self.upravit_citania_pre_projekciu(zobrazit_potvrdenie=False)
                except Exception as e:
                    log_exception("open_citanie/upravit", e)
                    messagebox.showerror("Chyba", f"Úprava čítaní zlyhala: {e}")

            try:
                self.aktualizovat_citania_gui(
                    datum=datum,
                    on_success=po_uspesnom_stiahnuti,
                )
            except Exception as e:
                log_exception("open_citanie/start_thread", e)
                messagebox.showerror("Chyba", f"Nepodarilo sa spustiť sťahovanie: {e}")

        self._zobraz_dialog_stiahnutia(
            title="Stiahnuť čítania",
            nadpis="Stiahnuť čítania na:",
            akcia=akcia,
        )


    def _potvrd_a_spusti_stiahnutie(self, dialog, rok_var, chyba_var, potvrdzujuci_text_fn, akcia_po_potvrdeni):
        """
        Spoločná logika tlačidla "Stiahni refrény" vo všetkých `open_*_refreny`
        dialógoch (nahrádza 7× takmer identicky definovanú lokálnu funkciu
        `spusti`): overí zadaný rok, zobrazí potvrdzujúci dialóg a pri súhlase
        zavrie `dialog` a zavolá `akcia_po_potvrdeni(rok)`.

        - potvrdzujuci_text_fn: funkcia rok -> str, vytvorí text potvrdzujúceho
          dialógu (líši sa pre každý typ sťahovania).
        - akcia_po_potvrdeni: funkcia rok -> None, zavolaná po potvrdení
          (typicky príslušné `self.aktualizovat_..._gui`).

        Vracia True, ak sa sťahovanie spustilo, inak False (neplatný rok
        alebo zamietnuté potvrdenie).
        """
        try:

            rok = _validuj_rok_pre_gui(rok_var.get())
            if rok < 2000 or rok > 2100:
                raise ValueError
        except ValueError:
            chyba_var.set("Zadaj platný rok v rozsahu 2000 – 2100.")
            return False

        if not messagebox.askyesno(
            "Potvrdiť stiahnutie",
            potvrdzujuci_text_fn(rok),
            parent=dialog,
        ):
            return False

        dialog.destroy()
        akcia_po_potvrdeni(rok)
        return True


    def _vytvor_rok_spinbox(self, parent, rok_var: "tk.StringVar | None" = None):
        """
        Vytvorí rok_var (ak nie je zadaný) a Spinbox 2000-2100 so spoločným
        vizuálom (spin_style), ktorý používajú všetky dialógy stiahnutia
        pre daný rok. Nezabalí (nepacke) Spinbox – to robí volajúci, keďže
        poradie/odsadenie sa dialóg od dialógu líši.
        """
        if rok_var is None:
            rok_var = tk.StringVar(value=str(date.today().year))
        spin_style = {
            "bg": "#2e2e2e",
            "fg": "#ffffff",
            "buttonbackground": "#3a3a3a",
            "relief": "flat",
            "bd": 1,
            "font": (self.font_family, 14, "bold"),
            "justify": "center",
            "highlightthickness": 1,
            "highlightbackground": "#555555",
            "highlightcolor": "#aaaaaa",
        }
        sp_rok = tk.Spinbox(parent, from_=GREGORIANSKY_MIN_ROK, to=GREGORIANSKY_MAX_ROK, width=6, textvariable=rok_var, state="readonly", readonlybackground="#2e2e2e", **spin_style)
        return rok_var, sp_rok

    def _zobraz_dialog_stiahnutia_pre_rok(
        self,
        *,
        titulok_okna: str,
        dw: int,
        dh: int,
        zostav_obsah_fn,
        potvrdzujuci_text_fn,
        akcia_po_potvrdeni,
        tlacidlo_text: str = "Stiahni refrény",
    ) -> "tk.Toplevel":
        """
        Spoločný základ pre dialógy stiahnutia refrénov/sviatkov pre daný rok
        (Toplevel okno + vycentrovanie, chybová hláška, tlačidlo, klávesové
        skratky Enter/Escape, fokus). Predtým mala každá z ôsmich `open_*`
        metód (napr. open_cezrocne_tyzdenne_refreny) vlastnú kópiu tohto
        ~25-riadkového obalu.

        Samotný obsah dialógu (nadpis, rok spinbox, informačné popisky) sa
        však medzi dialógmi líši – niekde je pred spinboxom ešte dynamický
        popisok, niekde je info-text zabalený vo Frame, niekde sa aktualizuje
        cez trace_add. Preto ho zostavuje volajúci cez `zostav_obsah_fn(dialog)`,
        ktorá musí vrátiť dvojicu (rok_var, sp_rok) – tie táto metóda použije
        pre potvrdenie sťahovania a nastavenie fokusu.
        """
        dialog = tk.Toplevel(self.master)
        dialog.title(titulok_okna)
        dialog.configure(bg="#1e1e1e")
        dialog.resizable(False, False)
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.lift()
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

        self.master.update_idletasks()
        mx = self.master.winfo_x() + self.master.winfo_width() // 2
        my = self.master.winfo_y() + self.master.winfo_height() // 2
        dialog.geometry(f"{dw}x{dh}+{mx - dw // 2}+{my - dh // 2}")

        rok_var, sp_rok = zostav_obsah_fn(dialog)

        chyba_var = tk.StringVar(value="")
        tk.Label(
            dialog,
            textvariable=chyba_var,
            bg="#1e1e1e",
            fg="#ff6b6b",
            font=(self.font_family, 9),
        ).pack(pady=(0, 4))

        btn_style = {
            "bg": "#3a3a3a",
            "fg": "#ffffff",
            "activebackground": "#555555",
            "activeforeground": "#ffffff",
            "font": (self.font_family, 12, "bold"),
            "relief": "flat",
            "bd": 0,
            "padx": 20,
            "pady": 8,
            "cursor": "hand2",
        }

        def spusti():
            self._potvrd_a_spusti_stiahnutie(
                dialog, rok_var, chyba_var,
                potvrdzujuci_text_fn=potvrdzujuci_text_fn,
                akcia_po_potvrdeni=akcia_po_potvrdeni,
            )

        tk.Button(dialog, text=tlacidlo_text, command=spusti, **btn_style).pack()

        dialog.bind("<Return>", lambda e: spusti())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        dialog.focus_force()
        sp_rok.focus_set()

        return dialog

    def open_refreny_zalmov(self):
        """Zobrazí dialóg na stiahnutie mesačných súborov refrénov žalmov pre celý rok."""
        def zostav_obsah(dialog):
            tk.Label(
                dialog,
                text="Stiahnuť refrény žalmov po mesiacoch:",
                bg="#1e1e1e",
                fg="#ffffff",
                font=(self.font_family, 13, "bold")
            ).pack(pady=(18, 10))

            rok_var, sp_rok = self._vytvor_rok_spinbox(dialog)
            sp_rok.pack(pady=(0, 8))

            tk.Label(
                dialog,
                text="Prepíšu sa súbory 1L.txt až 12L.txt.\nExistujúce súbory sa predtým automaticky zálohujú.",
                bg="#1e1e1e",
                fg="#bbbbbb",
                font=(self.font_family, 10),
                justify=tk.CENTER,
                wraplength=330,
            ).pack(pady=(0, 10))

            return rok_var, sp_rok

        self._zobraz_dialog_stiahnutia_pre_rok(
            titulok_okna="Stiahnuť refrény žalmov (1L–12L)",
            dw=380, dh=245,
            zostav_obsah_fn=zostav_obsah,
            potvrdzujuci_text_fn=lambda rok: (
                f"Naozaj stiahnuť refrény žalmov pre rok {rok}?\n\n"
                "Súbory 1L.txt až 12L.txt sa prepíšu, pôvodné verzie sa uložia do zálohy."
            ),
            akcia_po_potvrdeni=self.aktualizovat_refreny_zalmov_gui,
        )


    def open_cezrocne_tyzdenne_refreny(self):
        """Zobrazí dialóg na stiahnutie 34 súborov cezročných týždňov pre párny/nepárny rok."""
        def zostav_obsah(dialog):
            tk.Label(
                dialog,
                text="Stiahnuť týždne cezročného obdobia:",
                bg="#1e1e1e",
                fg="#ffffff",
                font=(self.font_family, 13, "bold"),
                wraplength=360,
                justify=tk.CENTER,
            ).pack(pady=(18, 10))

            rok_var, sp_rok = self._vytvor_rok_spinbox(dialog)
            sp_rok.pack(pady=(0, 8))

            info_var = tk.StringVar(value="")

            def aktualizuj_info(*_args):
                try:

                    rok = _validuj_rok_pre_gui(rok_var.get())
                    parita = 2 if rok % 2 == 0 else 1
                    parita_text = "párny" if parita == 2 else "nepárny"
                    info_var.set(
                        f"Prepíšu sa súbory 1C{parita}.txt až 34C{parita}.txt ({parita_text} rok).\n"
                        "Existujúce súbory sa predtým automaticky zálohujú."
                    )
                except ValueError:
                    info_var.set("Zadaj rok v rozsahu 2000 - 2100.")

            rok_var.trace_add("write", aktualizuj_info)
            aktualizuj_info()

            tk.Label(
                dialog,
                textvariable=info_var,
                bg="#1e1e1e",
                fg="#bbbbbb",
                font=(self.font_family, 10),
                justify=tk.CENTER,
                wraplength=360,
            ).pack(pady=(0, 10))

            return rok_var, sp_rok

        def cezrocny_potvrdzujuci_text(rok):
            parita = 2 if rok % 2 == 0 else 1
            return (
                f"Naozaj stiahnuť týždne cezročného obdobia pre rok {rok}?\n\n"
                f"Súbory 1C{parita}.txt až 34C{parita}.txt sa prepíšu, "
                "pôvodné verzie sa uložia do zálohy."
            )

        self._zobraz_dialog_stiahnutia_pre_rok(
            titulok_okna="Stiahnuť refrény žalmov",
            dw=420, dh=265,
            zostav_obsah_fn=zostav_obsah,
            potvrdzujuci_text_fn=cezrocny_potvrdzujuci_text,
            akcia_po_potvrdeni=self.aktualizovat_cezrocne_tyzdenne_refreny_gui,
        )


    def _spusti_stahovanie_s_progressom(
        self,
        *,
        lock: threading.Lock,
        zaneprazdnene_sprava: str,
        dialog_titulok: str,
        dw: int,
        dh: int,
        wraplength: int,
        sirka_progressbar: int,
        uvodna_sprava: str,
        maximum: int,
        kontext: str,
        stiahni_funkcia,
        rok: int,
        spracuj_vysledok,
        vysledok_pri_zlyhani: dict,
    ) -> bool:
        """
        Spoločná GUI logika pre všetky "aktualizovat_*_gui" metódy sťahovania
        refrénov žalmov z lc.kbs.sk (nahrádza predtým 7× duplicitne definované
        lokálne funkcie nastav_progress/progress_callback/po_stiahnuti/vlakno).

        Postup:
        1. Pokus o získanie `lock` bez blokovania – ak je už obsadený, zobrazí
           `zaneprazdnene_sprava` a vráti False.
        2. Vytvorí modálny progress dialóg (titulok, rozmery, štítky, Progressbar).
        3. Spustí worker vlákno. To si NAJPRV samo overí internetové pripojenie
           (`_over_internet_socket()` – bez GUI vedľajších účinkov, bezpečné
           z worker vlákna); ak nie je dostupné, `stiahni_funkcia` sa vôbec
           nezavolá a používateľ dostane špecifickú hlášku "Žiadne internetové
           pripojenie". Inak zavolá
           `stiahni_funkcia(rok, self.song_folder_path, progress_callback=...)`.
           Priebeh sa do dialógu hlási thread-safe cez `self.master.after(...)`.
        4. Po dokončení: zavrie dialóg, obnoví kurzor, uvoľní `lock`, nastaví
           fokus na `self.manual_entry`; pri úspechu najprv obnoví zoznam
           súborov a potom vždy zavolá `spracuj_vysledok(vysledok)` – tá
           funkcia (vlastná pre každého volajúceho) zobrazí konkrétny
           messagebox pri úspechu, alebo `zobraz_chybu_stahovania(...)` pri zlyhaní.

        `vysledok_pri_zlyhani` sa použije ako náhradný výsledok, ak samotné
        worker vlákno vyhodí neočakávanú výnimku (aby `spracuj_vysledok` vždy
        dostalo konzistentný slovník s kľúčom "uspech").
        """
        if not lock.acquire(blocking=False):
            messagebox.showinfo("Kinak", zaneprazdnene_sprava)
            return False

        progress_dialog = tk.Toplevel(self.master)
        progress_dialog.title(dialog_titulok)
        progress_dialog.configure(bg="#1e1e1e")
        progress_dialog.resizable(False, False)
        progress_dialog.transient(self.master)
        progress_dialog.lift()

        def zrusit_zobrazenie():
            # Nejde o skutočné zrušenie sťahovania (worker vlákno beží ďalej
            # na pozadí ako daemon a bezpečne dobehne, vrátane finálneho
            # messageboxu cez po_stiahnuti) – len skryje dialóg, aby
            # používateľ nebol pri pomalom pripojení zaseknutý bez možnosti
            # okno zatvoriť. `lock` sa preto zámerne NEUVOĽŇUJE tu – uvoľní
            # ho až po_stiahnuti(), keď sťahovanie na pozadí naozaj skončí.
            try:
                if progress_dialog.winfo_exists():
                    progress_dialog.destroy()
            except tk.TclError:
                pass
            try:
                self.master.config(cursor="")
            except tk.TclError:
                pass
            log_info(f"{kontext}: dialóg priebehu zatvorený používateľom, sťahovanie pokračuje na pozadí.")

        progress_dialog.protocol("WM_DELETE_WINDOW", zrusit_zobrazenie)

        self.master.update_idletasks()
        mx = self.master.winfo_x() + self.master.winfo_width() // 2
        my = self.master.winfo_y() + self.master.winfo_height() // 2
        dh_s_tlacidlom = dh + 46  # miesto navyše pre tlačidlo "Zrušiť" a vysvetľujúci popis pod ním
        progress_dialog.geometry(f"{dw}x{dh_s_tlacidlom}+{mx - dw // 2}+{my - dh_s_tlacidlom // 2}")

        stav_var = tk.StringVar(value=uvodna_sprava)
        pocet_var = tk.StringVar(value="")

        tk.Label(
            progress_dialog,
            textvariable=stav_var,
            bg="#1e1e1e",
            fg="#ffffff",
            font=(self.font_family, 11, "bold"),
            wraplength=wraplength,
            justify=tk.CENTER,
        ).pack(pady=(18, 8))

        progress = ttk.Progressbar(progress_dialog, mode="determinate", length=sirka_progressbar, maximum=maximum)
        progress.pack(pady=(0, 8))

        tk.Label(
            progress_dialog,
            textvariable=pocet_var,
            bg="#1e1e1e",
            fg="#bbbbbb",
            font=(self.font_family, 10),
        ).pack()

        tk.Button(
            progress_dialog,
            text="Zrušiť",
            command=zrusit_zobrazenie,
            width=12,
        ).pack(pady=(10, 2))

        tk.Label(
            progress_dialog,
            text="Sťahovanie bude pokračovať na pozadí.",
            bg="#1e1e1e",
            fg="#888888",
            font=(self.font_family, 8),
        ).pack(pady=(0, 6))

        try:
            self.master.config(cursor="wait")
            self.master.update_idletasks()
        except Exception as e:
            log_exception(f"{kontext}: cursor=wait zlyhal", e)

        def nastav_progress(sprava, aktualny=None, spolu=None):
            try:
                if not progress_dialog.winfo_exists():
                    return
                stav_var.set(sprava)
                if spolu:
                    progress.configure(maximum=spolu)
                if aktualny is not None:
                    progress.configure(value=aktualny)
                if aktualny is not None and spolu:
                    pocet_var.set(f"{aktualny} / {spolu}")
            except tk.TclError:
                pass

        def progress_callback(sprava, aktualny=None, spolu=None):
            try:
                self.master.after(0, lambda: nastav_progress(sprava, aktualny, spolu))
            except Exception as e:
                log_exception(f"{kontext}: progress after zlyhal", e)

        def po_stiahnuti(vysledok):
            try:
                if progress_dialog.winfo_exists():
                    progress_dialog.destroy()

                if vysledok.get("_bez_internetu"):
                    messagebox.showerror(
                        "Žiadne internetové pripojenie",
                        "Nie ste pripojení na internet.\n\nSkontrolujte Wi-Fi/kábel a skúste znova.",
                    )
                    return

                if vysledok.get("uspech"):
                    try:
                        self.subory_zoznam = self.ziskaj_zoznam_suborov()
                        self.filtrovat_subory(self.filter_var.get())
                    except Exception as e:
                        log_exception(f"{kontext}: obnova zoznamu zlyhala", e)

                spracuj_vysledok(vysledok)
            finally:
                try:
                    self.master.config(cursor="")
                except tk.TclError:
                    pass
                try:
                    lock.release()
                except RuntimeError as e:
                    log_exception(f"{kontext}: lock už bol uvoľnený", e)
                try:
                    self.manual_entry.focus_set()
                except Exception as e:
                    log_exception(f"{kontext}: focus_set zlyhal", e)

        def vlakno():
            # Kontrola internetu sa robí až TU (v pozadovom vlákne), nie v GUI
            # vlákne pred spustením – socket.create_connection() je blokujúca
            # operácia a inak by na krátky čas zamrazila celé okno ešte pred
            # zobrazením progress dialógu.
            if not _over_internet_socket():
                vysledok = dict(vysledok_pri_zlyhani)
                vysledok["_bez_internetu"] = True
                try:
                    self.master.after(0, lambda: po_stiahnuti(vysledok))
                except Exception as e:
                    log_exception(f"{kontext}: master.after (bez internetu) zlyhal", e)
                    try:
                        lock.release()
                    except RuntimeError:
                        pass
                return

            try:
                vysledok = stiahni_funkcia(
                    rok,
                    self.song_folder_path,
                    progress_callback=progress_callback,
                )
            except Exception as e:
                log_exception(f"{kontext}: vlákno zlyhalo", e)
                vysledok = dict(vysledok_pri_zlyhani)

            try:
                self.master.after(0, lambda: po_stiahnuti(vysledok))
            except Exception as e:
                log_exception(f"{kontext}: master.after zlyhal", e)
                try:
                    lock.release()
                except RuntimeError:
                    pass

        try:
            self._download_executor.submit(vlakno)
        except RuntimeError:
            threading.Thread(target=vlakno, daemon=True).start()
        return True


    def _priprav_stahovanie_gui(self, kontext: str, mkdir_chybova_sprava: str = "Nepodarilo sa pripraviť priečinok pre súbory.") -> bool:
        """
        Spoločný "preflight" pre GUI downloadery refrénov/sviatkov: over dostupnosť
        knižníc a priečinka piesní, priečinok pripraviť (mkdir).

        Ak niečo zlyhá, sám zobrazí chybové okno (messagebox) a vráti False –
        volajúca metóda má vtedy jednoducho urobiť `return False`.

        Predtým mala každá z ôsmich `aktualizovat_*_gui` metód vlastnú kópiu
        tohto bloku (líšili sa len v texte hlášky pri zlyhaní mkdir); teraz je
        na jednom mieste, takže prípadná zmena poradia kontrol alebo textu sa
        robí len tu.

        POZNÁMKA: kontrola internetového pripojenia sa tu ZÁMERNE nerobí –
        `socket.create_connection()` je blokujúca operácia (až `timeout`
        sekúnd), ktorá by pri jej volaní priamo tu zamrazila GUI vlákno ešte
        predtým, než by sa vôbec zobrazil progress dialóg. Namiesto toho ju
        volajúce `_spusti_stahovanie_s_progressom` / `_spusti_jednoduche_stahovanie`
        vykonávajú (cez _over_internet_socket()) až vnútri worker vlákna.
        """
        if zobraz_chybu_chybajucich_kniznic_pre_stahovanie():
            return False

        if not hasattr(self, "song_folder_path") or self.song_folder_path is None:
            messagebox.showerror("Chyba", "Nie je nastavený priečinok pre dáta.")
            return False

        try:
            self.song_folder_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log_exception(f"{kontext}: mkdir zlyhal", e)
            messagebox.showerror("Chyba", mkdir_chybova_sprava)
            return False

        return True

    def _formatuj_zalohu_text(self, zaloha: "str | None", popis_suborov: str = "súbory") -> str:
        """
        Spoločné formátovanie textu o zálohe pôvodných súborov v hláseniach
        GUI downloaderov (predtým 8× skopírovaný if/else, líšiaci sa len
        v texte `popis_suborov`).
        """
        if zaloha:
            return f"\nZáloha pôvodných súborov:\n{zaloha}\n"
        return f"\nPôvodné {popis_suborov} neexistovali, záloha nebola potrebná.\n"

    def _formatuj_chybne_kody_text(self, chybne_kody, popis: str = "Chybné súbory", pripona: str = "") -> str:
        """
        Spoločné formátovanie riadku o chybných kódoch/súboroch v hláseniach
        GUI downloaderov. Ak je `chybne_kody` prázdne, vráti "".

        - popis: úvodný text pred dvojbodkou (líši sa medzi downloadermi,
          napr. "Týždne s chybou", "Súbory s chybou", "Chybné súbory").
        - pripona: pripojí sa ku každému kódu (napr. ".txt"); default "" = žiadna.
        """
        if not chybne_kody:
            return ""
        polozky = ", ".join(f"{k}{pripona}" for k in chybne_kody)
        return f"{popis}: {polozky}\n"

    def aktualizovat_refreny_zalmov_gui(self, rok=None):
        """
        GUI wrapper pre hromadné stiahnutie refrénov responzóriových žalmov.
        Vytvorí alebo prepíše mesačné súbory 1L.txt až 12L.txt vo zvolenom priečinku piesní.
        """
        if rok is None:
            rok = date.today().year

        if not self._priprav_stahovanie_gui(
            "aktualizovat_refreny_zalmov_gui",
            "Nepodarilo sa pripraviť priečinok pre mesačné súbory.",
        ):
            return False

        def spracuj_vysledok(vysledok):
            if vysledok.get("uspech"):
                zaloha = vysledok.get("zaloha")
                zaloha_text = self._formatuj_zalohu_text(zaloha, "mesačné súbory")
                messagebox.showinfo(
                    "Refrény aktualizované",
                    f"Refrény žalmov pre rok {rok} boli úspešne stiahnuté.\n\n"
                    f"Zdroj: lc.kbs.sk\n"
                    f"Spracovaných dní: {vysledok.get('celkovo', 0)}\n"
                    f"Bez refrénu: {vysledok.get('chyby', 0)}\n"
                    f"Súhrn: {len(vysledok.get('subory', []))} súborov uložených, {vysledok.get('chyby', 0)} chýb.\n"
                    f"Súbory: 1L.txt až 12L.txt\n"
                    f"{zaloha_text}"
                )
            else:
                zobraz_chybu_stahovania("refrény žalmov", "lc.kbs.sk")

        return self._spusti_stahovanie_s_progressom(
            lock=self._refreny_lock,
            zaneprazdnene_sprava="Sťahovanie refrénov už prebieha, čakajte prosím.",
            dialog_titulok="Sťahujem refrény žalmov (1L–12L)",
            dw=430, dh=150, wraplength=380, sirka_progressbar=360,
            uvodna_sprava=f"Pripravujem sťahovanie pre rok {rok}...",
            maximum=366,
            kontext="aktualizovat_refreny_zalmov_gui",
            stiahni_funkcia=stiahni_refreny_zalmov_pre_rok,
            rok=rok,
            spracuj_vysledok=spracuj_vysledok,
            vysledok_pri_zlyhani={"uspech": False, "celkovo": 0, "chyby": 0, "subory": [], "zaloha": None},
        )




    def aktualizovat_cezrocne_tyzdenne_refreny_gui(self, rok=None):
        """
        GUI wrapper pre hromadné stiahnutie cezročných týždňov.
        Vytvorí alebo prepíše 1C1-34C1, resp. 1C2-34C2 podľa párnosti roka.
        """
        if rok is None:
            rok = date.today().year

        if not self._priprav_stahovanie_gui(
            "aktualizovat_cezrocne_tyzdenne_refreny_gui",
            "Nepodarilo sa pripraviť priečinok pre týždenné súbory.",
        ):
            return False

        parita = 2 if rok % 2 == 0 else 1

        def spracuj_vysledok(vysledok):
            if vysledok.get("uspech"):
                zaloha = vysledok.get("zaloha")
                zaloha_text = self._formatuj_zalohu_text(zaloha, "týždenné súbory")
                chybne_kody = vysledok.get("chybne_kody") or []
                chybne_text = self._formatuj_chybne_kody_text(chybne_kody, "Týždne s chybou")
                messagebox.showinfo(
                    "Cezročné týždne aktualizované",
                    f"Refrény žalmov pre týždne cezročného obdobia na rok {rok} boli úspešne stiahnuté.\n\n"
                    f"Zdroj: lc.kbs.sk\n"
                    f"Spracovaných položiek: {vysledok.get('celkovo', 0)}\n"
                    f"Chyby: {vysledok.get('chyby', 0)}\n"
                    f"Súhrn: {len(vysledok.get('subory', []))} súborov uložených, {vysledok.get('chyby', 0)} chýb.\n"
                    f"{chybne_text}"
                    f"Súbory: 1C{parita}.txt až 34C{parita}.txt\n"
                    f"{zaloha_text}"
                )
            else:
                zobraz_chybu_stahovania("týždne cezročného obdobia", "lc.kbs.sk")

        return self._spusti_stahovanie_s_progressom(
            lock=self._cezrocne_tyzdenne_lock,
            zaneprazdnene_sprava="Sťahovanie cezročných týždňov už prebieha, čakajte prosím.",
            dialog_titulok="Sťahujem refrény žalmov",
            dw=470, dh=150, wraplength=420, sirka_progressbar=390,
            uvodna_sprava=f"Pripravujem sťahovanie cezročných týždňov pre rok {rok}...",
            maximum=306,
            kontext="aktualizovat_cezrocne_tyzdenne_refreny_gui",
            stiahni_funkcia=stiahni_cezrocne_tyzdenne_refreny_pre_rok,
            rok=rok,
            spracuj_vysledok=spracuj_vysledok,
            vysledok_pri_zlyhani={"uspech": False, "celkovo": 0, "chyby": 0, "subory": [], "zaloha": None},
        )





    def open_liturgicke_tyzdne_refreny(self):
        """Zobrazí dialóg na stiahnutie refrénov žalmov pre pôstne, VT, veľkonočné a adventné týždne."""
        def zostav_obsah(dialog):
            tk.Label(
                dialog,
                text="Stiahnuť refrény žalmov pre liturgické týždne:",
                bg="#1e1e1e",
                fg="#ffffff",
                font=(self.font_family, 13, "bold"),
                wraplength=400,
                justify=tk.CENTER,
            ).pack(pady=(18, 10))

            rok_var, sp_rok = self._vytvor_rok_spinbox(dialog)
            sp_rok.pack(pady=(0, 8))

            tk.Label(
                dialog,
                text=(
                    "Stiahne refrény žalmov pre:\n"
                    "  • Pôstne týždne: 1P.txt – 5P.txt\n"
                    "  • Veľký týždeň: VT.txt\n"
                    "  • Veľkonočné týždne: 1VN.txt – 7VN.txt\n"
                    "  • Adventné týždne: 1AD.txt – 4AD.txt\n\n"
                    "Existujúce súbory sa pred prepísaním automaticky zálohujú."
                ),
                bg="#1e1e1e",
                fg="#bbbbbb",
                font=(self.font_family, 10),
                justify=tk.LEFT,
                wraplength=410,
            ).pack(pady=(0, 10), padx=20, anchor="w")

            return rok_var, sp_rok

        self._zobraz_dialog_stiahnutia_pre_rok(
            titulok_okna="Stiahnuť liturgické týždne (1P–VT–7VN–4AD)",
            dw=460, dh=300,
            zostav_obsah_fn=zostav_obsah,
            potvrdzujuci_text_fn=lambda rok: (
                f"Naozaj stiahnuť refrény liturgických týždňov pre rok {rok}?\n\n"
                "Súbory 1P–5P, VT, 1VN–7VN, PS, ZV, ZST, VP, VG, VPON, NP sa prepíšu, pôvodné verzie sa uložia do zálohy.\n"
            ),
            akcia_po_potvrdeni=self.aktualizovat_liturgicke_tyzdne_refreny_gui,
        )


    def aktualizovat_liturgicke_tyzdne_refreny_gui(self, rok=None):
        """
        GUI wrapper pre stiahnutie refrénov pôstnych, VT, veľkonočných a adventných týždňov.
        Sťahuje 17 súborov: 1P–5P, VT, 1VN–7VN, 1AD–4AD.
        """
        if rok is None:
            rok = date.today().year

        if not self._priprav_stahovanie_gui("aktualizovat_liturgicke_tyzdne_refreny_gui"):
            return False

        def spracuj_vysledok(vysledok):
            if vysledok.get("uspech"):
                zaloha = vysledok.get("zaloha")
                zaloha_text = self._formatuj_zalohu_text(zaloha)
                messagebox.showinfo(
                    "Liturgické týždne aktualizované",
                    f"Refrény žalmov liturgických týždňov pre rok {rok} boli úspešne stiahnuté.\n\n"
                    f"Zdroj: lc.kbs.sk\n"
                    f"Spracovaných položiek: {vysledok.get('celkovo', 0)}\n"
                    f"Chyby: {vysledok.get('chyby', 0)}\n"
                    f"Súhrn: {len(vysledok.get('subory', []))} súborov uložených, {vysledok.get('chyby', 0)} chýb.\n"
                    f"Súbory: 1P–5P, VT, 1VN–7VN, 1AD–4AD\n"
                    f"{zaloha_text}"
                )
            else:
                zobraz_chybu_stahovania("refrény liturgických týždňov", "lc.kbs.sk")

        return self._spusti_stahovanie_s_progressom(
            lock=self._liturgicke_tyzdne_lock,
            zaneprazdnene_sprava="Sťahovanie liturgických týždňov už prebieha, čakajte prosím.",
            dialog_titulok="Sťahujem refrény žalmov",
            dw=490, dh=150, wraplength=450, sirka_progressbar=420,
            uvodna_sprava=f"Pripravujem sťahovanie liturgických týždňov pre rok {rok}...",
            maximum=153,
            kontext="aktualizovat_liturgicke_tyzdne_refreny_gui",
            stiahni_funkcia=stiahni_liturgicke_tyzdne_refreny,
            rok=rok,
            spracuj_vysledok=spracuj_vysledok,
            vysledok_pri_zlyhani={"uspech": False, "celkovo": 0, "chyby": 0, "subory": [], "zaloha": None},
        )




    def open_postne_velkonocne_refreny(self):
        """Zobrazí dialóg na stiahnutie refrénov žalmov pre pôstne, VT, veľkonočné týždne a špeciálne jednodenné slávenia."""
        def zostav_obsah(dialog):
            tk.Label(
                dialog,
                text="Stiahnuť refrény žalmov – pôstne a veľkonočné:",
                bg="#1e1e1e",
                fg="#ffffff",
                font=(self.font_family, 13, "bold"),
                wraplength=400,
                justify=tk.CENTER,
            ).pack(pady=(18, 10))

            rok_var, sp_rok = self._vytvor_rok_spinbox(dialog)
            sp_rok.pack(pady=(0, 8))

            frame = tk.Frame(dialog, bg="#1e1e1e")
            frame.pack(pady=(0, 10), padx=25, anchor="w")

            tk.Label(
                frame,
                text=(
                    "Stiahne refrény žalmov pre:\n\n"
                    "  • Pôstne týždne: 1P.txt – 5P.txt\n"
                    "  • Veľký týždeň: VT.txt\n"
                    "  • Veľkonočné týždne: 1VN.txt – 7VN.txt\n"
                    "  • Slávenia v tomto období: PS.txt, ZV.txt,\n"
                    "    ZST.txt, VP.txt, VG.txt, VPON.txt, NP.txt\n\n"
                    "Existujúce súbory sa pred prepísaním automaticky zálohujú."
                ),
                bg="#1e1e1e",
                fg="#bbbbbb",
                font=(self.font_family, 10),
                justify=tk.LEFT,
                wraplength=410,
            ).pack(anchor="w", ipadx=10)

            return rok_var, sp_rok

        self._zobraz_dialog_stiahnutia_pre_rok(
            titulok_okna="Stiahnuť refrény žalmov",
            dw=520, dh=380,
            zostav_obsah_fn=zostav_obsah,
            potvrdzujuci_text_fn=lambda rok: (
                f"Naozaj stiahnuť refrény žalmov pre pôstne a veľkonočné obdobie na rok {rok}?\n\n"
                "Súbory 1P–5P, VT, 1VN–7VN, PS, ZV, ZST, VP, VG, VPON, NP sa prepíšu, pôvodné verzie sa uložia do zálohy.\n"
            ),
            akcia_po_potvrdeni=self.aktualizovat_postne_velkonocne_refreny_gui,
        )


    def aktualizovat_postne_velkonocne_refreny_gui(self, rok=None):
        """GUI wrapper pre stiahnutie refrénov pôstnych, VT a veľkonočných týždňov."""
        if rok is None:
            rok = date.today().year

        if not self._priprav_stahovanie_gui("aktualizovat_postne_velkonocne_refreny_gui"):
            return False

        def spracuj_vysledok(vysledok):
            if vysledok.get("uspech"):
                zaloha = vysledok.get("zaloha")
                zaloha_text = self._formatuj_zalohu_text(zaloha)
                chybne_kody = vysledok.get("chybne_kody", [])
                chybne_text = self._formatuj_chybne_kody_text(chybne_kody, pripona=".txt")
                messagebox.showinfo(
                    "Pôstne a veľkonočné obdobie aktualizované",
                    f"Refrény žalmov pre pôstne a veľkonočné obdobie na rok {rok} boli úspešne stiahnuté.\n\n"
                    f"Zdroj: lc.kbs.sk\n"
                    f"Spracovaných položiek: {vysledok.get('celkovo', 0)}\n"
                    f"Preskočených (neslávi sa v {rok}): {vysledok.get('preskocených', 0)}"
                    + (f" ({', '.join(vysledok.get('preskocene_kody', []))})" if vysledok.get('preskocene_kody') else "") + "\n"
                    f"Chyby: {vysledok.get('chyby', 0)}\n"
                    f"{chybne_text}"
                    f"Súbory: 1P–5P, VT, 1VN–7VN, PS, ZV, ZST, VP, VG, VPON, NP\n"
                    f"{zaloha_text}"
                )
            else:
                zobraz_chybu_stahovania("refrény pôstnych a veľkonočných týždňov", "lc.kbs.sk")

        return self._spusti_stahovanie_s_progressom(
            lock=self._liturgicke_tyzdne_lock,
            zaneprazdnene_sprava="Sťahovanie liturgických týždňov už prebieha, čakajte prosím.",
            dialog_titulok="Sťahujem refrény žalmov",
            dw=490, dh=150, wraplength=450, sirka_progressbar=420,
            uvodna_sprava=f"Pripravuje sa sťahovanie refrénov žalmov pre pôstne a veľkonočné obdobie na rok {rok}...",
            maximum=115,
            kontext="aktualizovat_postne_velkonocne_refreny_gui",
            stiahni_funkcia=stiahni_postne_velkonocne_refreny,
            rok=rok,
            spracuj_vysledok=spracuj_vysledok,
            vysledok_pri_zlyhani={"uspech": False, "celkovo": 0, "chyby": 0, "subory": [], "zaloha": None},
        )




    def open_adventne_refreny(self):
        """Zobrazí dialóg na stiahnutie refrénov žalmov pre adventné týždne."""
        def zostav_obsah(dialog):
            tk.Label(
                dialog,
                text="Stiahnuť refrény žalmov – adventné týždne:",
                bg="#1e1e1e",
                fg="#ffffff",
                font=(self.font_family, 13, "bold"),
                wraplength=400,
                justify=tk.CENTER,
            ).pack(pady=(18, 10))

            rok_var, sp_rok = self._vytvor_rok_spinbox(dialog)
            sp_rok.pack(pady=(0, 8))

            tk.Label(
                dialog,
                text="Prepíšu sa súbory 1AD.txt až 4AD.txt.\nExistujúce súbory sa predtým automaticky zálohujú.",
                bg="#1e1e1e",
                fg="#bbbbbb",
                font=(self.font_family, 10),
                justify=tk.CENTER,
                wraplength=330,
            ).pack(pady=(0, 10))

            return rok_var, sp_rok

        self._zobraz_dialog_stiahnutia_pre_rok(
            titulok_okna="Stiahnuť refrény žalmov (1AD–4AD)",
            dw=460, dh=280,
            zostav_obsah_fn=zostav_obsah,
            potvrdzujuci_text_fn=lambda rok: (
                f"Naozaj stiahnuť refrény adventných týždňov pre rok {rok}?\n\n"
                "Súbory 1AD–4AD sa prepíšu.\n"
                "Pôvodné verzie sa uložia do zálohy."
            ),
            akcia_po_potvrdeni=self.aktualizovat_adventne_refreny_gui,
        )


    def aktualizovat_adventne_refreny_gui(self, rok=None):
        """GUI wrapper pre stiahnutie refrénov adventných týždňov."""
        if rok is None:
            rok = date.today().year

        if not self._priprav_stahovanie_gui("aktualizovat_adventne_refreny_gui"):
            return False

        def spracuj_vysledok(vysledok):
            if vysledok.get("uspech"):
                zaloha = vysledok.get("zaloha")
                zaloha_text = self._formatuj_zalohu_text(zaloha)
                chybne_kody = vysledok.get("chybne_kody") or []
                chybne_text = self._formatuj_chybne_kody_text(chybne_kody, "Týždne s chybou")
                messagebox.showinfo(
                    "Adventné týždne aktualizované",
                    f"Refrény žalmov adventných týždňov pre rok {rok} boli úspešne stiahnuté.\n\n"
                    f"Zdroj: lc.kbs.sk\n"
                    f"Spracovaných položiek: {vysledok.get('celkovo', 0)}\n"
                    f"Chyby: {vysledok.get('chyby', 0)}\n"
                    f"Súhrn: {len(vysledok.get('subory', []))} súborov uložených, {vysledok.get('chyby', 0)} chýb.\n"
                    f"{chybne_text}"
                    f"Súbory: 1AD–4AD\n"
                    f"{zaloha_text}"
                )
            else:
                zobraz_chybu_stahovania("refrény adventných týždňov", "lc.kbs.sk")

        return self._spusti_stahovanie_s_progressom(
            lock=self._liturgicke_tyzdne_lock,
            zaneprazdnene_sprava="Sťahovanie liturgických týždňov už prebieha, čakajte prosím.",
            dialog_titulok="Sťahujem refrény žalmov",
            dw=490, dh=150, wraplength=450, sirka_progressbar=420,
            uvodna_sprava=f"Pripravujem sťahovanie adventných týždňov pre rok {rok}...",
            maximum=36,
            kontext="aktualizovat_adventne_refreny_gui",
            stiahni_funkcia=stiahni_adventne_vianocne_refreny,
            rok=rok,
            spracuj_vysledok=spracuj_vysledok,
            vysledok_pri_zlyhani={"uspech": False, "celkovo": 0, "chyby": 0, "subory": [], "zaloha": None},
        )




    def open_turicne_sviatky(self):
        """Zobrazí dialóg na stiahnutie refrénov žalmov pre Turíce a nadväzujúce sviatky (1TS–7TS)."""
        def zostav_obsah(dialog):
            tk.Label(
                dialog,
                text="Stiahnuť refrény žalmov – Turíce a nadväzujúce sviatky:",
                bg="#1e1e1e",
                fg="#ffffff",
                font=(self.font_family, 13, "bold"),
                wraplength=400,
                justify=tk.CENTER,
            ).pack(pady=(18, 10))

            rok_var, sp_rok = self._vytvor_rok_spinbox(dialog)
            sp_rok.pack(pady=(0, 8))

            tk.Label(
                dialog,
                text="Prepíšu sa súbory 1TS.txt až 7TS.txt.\nExistujúce súbory sa predtým automaticky zálohujú.",
                bg="#1e1e1e",
                fg="#bbbbbb",
                font=(self.font_family, 10),
                justify=tk.CENTER,
                wraplength=330,
            ).pack(pady=(0, 10))

            return rok_var, sp_rok

        self._zobraz_dialog_stiahnutia_pre_rok(
            titulok_okna="Stiahnuť refrény žalmov (1TS–7TS)",
            dw=460, dh=280,
            zostav_obsah_fn=zostav_obsah,
            potvrdzujuci_text_fn=lambda rok: (
                f"Naozaj stiahnuť refrény Turíc a nadväzujúcich sviatkov pre rok {rok}?\n\n"
                "Súbory 1TS–7TS sa prepíšu.\n"
                "Pôvodné verzie sa uložia do zálohy."
            ),
            akcia_po_potvrdeni=self.aktualizovat_turicne_sviatky_gui,
        )


    def aktualizovat_turicne_sviatky_gui(self, rok=None):
        """GUI wrapper pre stiahnutie refrénov Turíc a nadväzujúcich sviatkov (1TS–7TS)."""
        if rok is None:
            rok = date.today().year

        if not self._priprav_stahovanie_gui("aktualizovat_turicne_sviatky_gui"):
            return False

        def spracuj_vysledok(vysledok):
            if vysledok.get("uspech"):
                zaloha = vysledok.get("zaloha")
                zaloha_text = self._formatuj_zalohu_text(zaloha)
                chybne_kody = vysledok.get("chybne_kody") or []
                chybne_text = self._formatuj_chybne_kody_text(chybne_kody, "Súbory s chybou")
                messagebox.showinfo(
                    "Turíce a nadväzujúce sviatky aktualizované",
                    f"Refrény žalmov pre Turíce a nadväzujúce sviatky na rok {rok} boli úspešne stiahnuté.\n\n"
                    f"Zdroj: lc.kbs.sk\n"
                    f"Spracovaných položiek: {vysledok.get('celkovo', 0)}\n"
                    f"Preskočených (neslávi sa v {rok}): {vysledok.get('preskocených', 0)}"
                    + (f" ({', '.join(vysledok.get('preskocene_kody', []))})" if vysledok.get('preskocene_kody') else "") + "\n"
                    f"Chyby: {vysledok.get('chyby', 0)}\n"
                    f"{chybne_text}"
                    f"Súbory: 1TS–7TS\n"
                    f"{zaloha_text}"
                )
            else:
                zobraz_chybu_stahovania("refrény Turíc a nadväzujúcich sviatkov", "lc.kbs.sk")

        return self._spusti_stahovanie_s_progressom(
            lock=self._liturgicke_tyzdne_lock,
            zaneprazdnene_sprava="Sťahovanie liturgických týždňov už prebieha, čakajte prosím.",
            dialog_titulok="Sťahujem refrény žalmov",
            dw=490, dh=150, wraplength=450, sirka_progressbar=420,
            uvodna_sprava=f"Pripravujem sťahovanie Turíc a nadväzujúcich sviatkov pre rok {rok}...",
            maximum=19,
            kontext="aktualizovat_turicne_sviatky_gui",
            stiahni_funkcia=stiahni_turicne_sviatky_pre_rok,
            rok=rok,
            spracuj_vysledok=spracuj_vysledok,
            vysledok_pri_zlyhani={"uspech": False, "celkovo": 0, "chyby": 0, "subory": [], "zaloha": None},
        )




    def open_vianocne_sviatky(self):
        """Zobrazí dialóg na stiahnutie refrénov žalmov pre vianočné sviatky daného roku."""
        def zostav_obsah(dialog):
            tk.Label(
                dialog,
                text="Stiahnuť refrény žalmov vianočných sviatkov:",
                bg="#1e1e1e",
                fg="#ffffff",
                font=(self.font_family, 13, "bold"),
                wraplength=380,
                justify=tk.CENTER,
            ).pack(pady=(18, 6))

            rok_var, sp_rok = self._vytvor_rok_spinbox(dialog)
            obdobie_var = tk.StringVar(value="")

            def aktualizuj_obdobie(*_args):
                try:
                    r = int(rok_var.get())
                    obdobie_var.set(f"Vianočné obdobie {r} / {r + 1}  (25.12.{r} – Krst Krista Pána {r + 1})")
                except ValueError:
                    obdobie_var.set("")

            rok_var.trace_add("write", aktualizuj_obdobie)
            aktualizuj_obdobie()

            tk.Label(
                dialog,
                textvariable=obdobie_var,
                bg="#1e1e1e",
                fg="#8fd0ff",
                font=(self.font_family, 10, "bold"),
                justify=tk.CENTER,
                wraplength=390,
            ).pack(pady=(0, 8))

            sp_rok.pack(pady=(0, 8))

            tk.Label(
                dialog,
                text=(
                    "(1VI.txt, 2VI.txt, SR.txt, STEF.txt, SJE.txt, NEV.txt, PDR.txt, PMB.txt, NMJ.txt, KKP.txt).\n"
                    "Existujúce súbory sa pred prepísaním automaticky zálohujú.\n\n"
                    "Zadaný rok = december (25.–31.12.). Januárová časť toho istého\n"
                    "vianočného obdobia (PMB, NMJ, KKP, 2VI) sa stiahne automaticky\n"
                    "z januára nasledujúceho roka.\n\n"
                    "Ak sviatok v danom roku padne na nedeľu (nahradí ho\n"
                    "nedeľný formulár), pôvodný súbor zostane bez zmeny.\n"

                ),
                bg="#1e1e1e",
                fg="#bbbbbb",
                font=(self.font_family, 10),
                justify=tk.CENTER,
                wraplength=390,
            ).pack(pady=(0, 10))

            return rok_var, sp_rok

        self._zobraz_dialog_stiahnutia_pre_rok(
            titulok_okna="Stiahnuť refrény žalmov",
            dw=440, dh=460,
            zostav_obsah_fn=zostav_obsah,
            potvrdzujuci_text_fn=lambda rok: (
                f"Naozaj stiahnuť refrény žalmov vianočného obdobia {rok}/{rok + 1}?\n\n"
                f"December sa stiahne z roku {rok}, január (PMB, NMJ, KKP, 2VI) "
                f"z roku {rok + 1}.\n"
                "Súbory sviatkov, ktoré sa v tomto období slávia, sa prepíšu.\n"
                "Sviatky, ktoré padnú na nedeľu, sa nemenia.\n"
                "Pôvodné verzie sa uložia do zálohy."
            ),
            akcia_po_potvrdeni=self.aktualizovat_vianocne_sviatky_gui,
        )


    def aktualizovat_vianocne_sviatky_gui(self, rok=None):
        """
        GUI wrapper pre stiahnutie refrénov vianočných sviatkov.
        Stiahne len sviatky, ktoré sa v danom vianočnom období skutočne
        slávia (t. j. nepadnú na nedeľu, resp. nie sú prekryté iným
        slávením). Vianočné obdobie prechádza cez prelom kalendárnych rokov:
        december sa berie z roku `rok`, január (PMB, NMJ, KKP, 2VI) už
        z roku `rok + 1`.
        """
        if rok is None:
            rok = date.today().year

        if not self._priprav_stahovanie_gui(
            "aktualizovat_vianocne_sviatky_gui",
            "Nepodarilo sa pripraviť priečinok pre súbory sviatkov.",
        ):
            return False

        celkovo_sviatkov = len(VIANOCNE_SVIATKY_KODY) + 2  # +2: kompilované súbory 1VI a 2VI

        def spracuj_vysledok(vysledok):
            if vysledok.get("uspech"):
                zaloha = vysledok.get("zaloha")
                zaloha_text = self._formatuj_zalohu_text(zaloha, "súbory sviatkov")
                subory = vysledok.get("subory", [])
                subory_text = "\n".join(Path(s).name for s in subory) if subory else "– žiadne –"

                chybne_kody = vysledok.get("chybne_kody", [])
                chybne_text = self._formatuj_chybne_kody_text(chybne_kody, pripona=".txt")
                messagebox.showinfo(
                    "Refrény žalmov aktualizované",
                    f"Refrény žalmov vianočného obdobia {rok}/{rok + 1} boli úspešne stiahnuté.\n\n"
                    f"Zdroj: lc.kbs.sk\n"
                    f"Stiahnutých: {vysledok.get('stiahnutych', 0)}\n"
                    f"Preskočených (neslávi sa v {rok}/{rok + 1}): {vysledok.get('preskocených', 0)}"
                    + (f" ({', '.join(vysledok.get('preskocene_kody', []))})" if vysledok.get('preskocene_kody') else "") + "\n"
                    f"Chyby pri sťahovaní: {vysledok.get('chyby', 0)}\n"
                    f"Súhrn: {vysledok.get('stiahnutych', 0)} súborov uložených, {vysledok.get('preskocených', 0)} preskočených, {vysledok.get('chyby', 0)} chýb.\n"
                    f"{chybne_text}"
                    f"{zaloha_text}"
                    f"\nStiahnuté súbory:\n{subory_text}\n"
                )
            else:
                zobraz_chybu_stahovania("Refrény žalmov vianočných sviatkov", "lc.kbs.sk")

        return self._spusti_stahovanie_s_progressom(
            lock=self._refreny_lock,
            zaneprazdnene_sprava="Sťahovanie už prebieha, čakajte prosím.",
            dialog_titulok="Sťahujem refrény žalmov",
            dw=490, dh=150, wraplength=450, sirka_progressbar=420,
            uvodna_sprava=f"Pripravujem sťahovanie vianočného obdobia {rok}/{rok + 1}...",
            maximum=celkovo_sviatkov,
            kontext="aktualizovat_vianocne_sviatky_gui",
            stiahni_funkcia=stiahni_vianocne_sviatky_pre_rok,
            rok=rok,
            spracuj_vysledok=spracuj_vysledok,
            vysledok_pri_zlyhani={"uspech": False, "celkovo": 0, "stiahnutych": 0,
                                   "chyby": 0, "preskocených": 0, "subory": [], "zaloha": None},
        )




    def open_liturgicke_sviatky(self):
        """Zobrazí dialóg na stiahnutie refrénov žalmov pre liturgické sviatky daného roku."""
        def zostav_obsah(dialog):
            tk.Label(
                dialog,
                text="Stiahnuť refrény žalmov cezročných sviatkov:",
                bg="#1e1e1e",
                fg="#ffffff",
                font=(self.font_family, 13, "bold"),
                wraplength=380,
                justify=tk.CENTER,
            ).pack(pady=(18, 10))

            rok_var, sp_rok = self._vytvor_rok_spinbox(dialog)
            sp_rok.pack(pady=(0, 8))

            tk.Label(
                dialog,
                text=(
                    "(napr. OND.txt, NJK.txt, BAR.txt…).\n"
                    "Existujúce súbory sa pred prepísaním automaticky zálohujú.\n\n"
                    "Ak sa sviatok v danom roku neslávi (je vynechaný alebo\n"
                    "prekrytý iným slávením), pôvodný súbor zostane bez zmeny.\n"

                ),
                bg="#1e1e1e",
                fg="#bbbbbb",
                font=(self.font_family, 10),
                justify=tk.CENTER,
                wraplength=390,
            ).pack(pady=(0, 10))

            return rok_var, sp_rok

        self._zobraz_dialog_stiahnutia_pre_rok(
            titulok_okna="Stiahnuť refrény žalmov",
            dw=500, dh=330,
            zostav_obsah_fn=zostav_obsah,
            potvrdzujuci_text_fn=lambda rok: (
                f"Naozaj stiahnuť refrény žalmov cezročných sviatkov pre rok {rok}?\n\n"
                "Súbory sviatkov, ktoré sa v tomto roku slávia, sa prepíšu.\n"
                "Sviatky prekryté vyššou slávnosťou alebo prenesené na iný deň sa nemenia. "
                "Pôvodné verzie sa uložia do zálohy."
            ),
            akcia_po_potvrdeni=self.aktualizovat_liturgicke_sviatky_gui,
        )


    def aktualizovat_liturgicke_sviatky_gui(self, rok=None):
        """
        GUI wrapper pre stiahnutie refrénov sviatkov.
        Stiahne len sviatky, ktoré sa v danom roku skutočne slávia.
        Sviatky prekryté vyššou slávnosťou alebo prenesené na iný deň sa nemenia.
        """
        if rok is None:
            rok = date.today().year

        if not self._priprav_stahovanie_gui(
            "aktualizovat_liturgicke_sviatky_gui",
            "Nepodarilo sa pripraviť priečinok pre súbory sviatkov.",
        ):
            return False

        celkovo_sviatkov = len(LITURGICKE_SVIATKY_KODY)

        def spracuj_vysledok(vysledok):
            if vysledok.get("uspech"):
                zaloha = vysledok.get("zaloha")
                zaloha_text = self._formatuj_zalohu_text(zaloha, "súbory sviatkov")
                # NOVÉ – zoznam stiahnutých txt
                subory = vysledok.get("subory", [])
                subory_text = "\n".join(Path(s).name for s in subory) if subory else "– žiadne –"

                chybne_kody = vysledok.get("chybne_kody", [])
                chybne_text = self._formatuj_chybne_kody_text(chybne_kody, pripona=".txt")
                messagebox.showinfo(
                    "Refrény žalmov aktualizované",
                    f"Refrény žalmov cezročných sviatkov pre {rok} boli úspešne stiahnuté.\n\n"
                    f"Zdroj: lc.kbs.sk\n"
                    f"Stiahnutých: {vysledok.get('stiahnutych', 0)}\n"
                    f"Preskočených (neslávi sa v {rok}): {vysledok.get('preskocených', 0)}"
                    + (f" ({', '.join(vysledok.get('preskocene_kody', []))})" if vysledok.get('preskocene_kody') else "") + "\n"
                    f"Chyby pri sťahovaní: {vysledok.get('chyby', 0)}\n"
                    f"Súhrn: {vysledok.get('stiahnutych', 0)} súborov uložených, {vysledok.get('preskocených', 0)} preskočených, {vysledok.get('chyby', 0)} chýb.\n"
                    f"{chybne_text}"
                    f"{zaloha_text}"
                    f"\nStiahnuté súbory:\n{subory_text}\n"
                )
            else:
                zobraz_chybu_stahovania("Refrény žalmov cezročných sviatkov", "lc.kbs.sk")

        return self._spusti_stahovanie_s_progressom(
            lock=self._refreny_lock,
            zaneprazdnene_sprava="Sťahovanie už prebieha, čakajte prosím.",
            dialog_titulok="Sťahujem refrény žalmov",
            dw=490, dh=150, wraplength=450, sirka_progressbar=420,
            uvodna_sprava=f"Pripravujem sťahovanie sviatkov pre rok {rok}...",
            maximum=celkovo_sviatkov,
            kontext="aktualizovat_liturgicke_sviatky_gui",
            stiahni_funkcia=stiahni_liturgicke_sviatky_pre_rok,
            rok=rok,
            spracuj_vysledok=spracuj_vysledok,
            vysledok_pri_zlyhani={"uspech": False, "celkovo": 0, "stiahnutych": 0,
                                   "chyby": 0, "preskocených": 0, "subory": [], "zaloha": None},
        )




    def rozdel_text_na_bloky(self, cast, max_chars):
        """
        Rozdelí jeden odsek stiahnutého liturgického čítania na menšie bloky
        vhodné na projekciu. Text sa rozseká na vety a tie sa skladajú do blokov
        tak, aby neprekročili limit max_chars. Príliš dlhé vety tvoria samostatný
        slide. Výsledkom je zoznam blokov pripravených na zobrazenie.
        """
        vety = re.split(r'(?<=[.!?])\s+', cast)
        akt = ""
        bloky = []

        for veta in vety:
            veta = veta.strip()
            if not veta:
                continue

            if len(veta) > max_chars:
                if akt:
                    bloky.append(akt)
                    akt = ""
                bloky.append(veta)
                continue

            if len(akt) + len(veta) + 1 <= max_chars:
                akt = f"{akt} {veta}".strip()
            else:
                bloky.append(akt)
                akt = veta

        if akt:
            bloky.append(akt)

        return bloky              
                    

    def upravit_citania_pre_projekciu(self, max_chars=180, zobrazit_potvrdenie=True):

        subor = self.song_folder_path / "citania.txt"
        if not subor.exists():
            messagebox.showerror("Chyba", "Súbor citania.txt neexistuje.")
            return

        # ------------------------------------------------------------
        # 1. Načítanie a základné čistenie
        # ------------------------------------------------------------
        povodne = subor.read_text(encoding="utf-8").splitlines()
        ciste = []

        dni = ["Pondelok", "Utorok", "Streda", "Štvrtok", "Piatok", "Sobota", "Nedeľa"]
        mesiace = ["január","február","marec","apríl","máj","jún","júl","august","september","október","november","december"]

        preskakovat = False
        reset_preskakovania_nadpisy = ["ZAČIATOK", "ČÍTANIE", "EVANJELIUM", "PRVÉ", "DRUHÉ"]

        for riadok in povodne:
            r = riadok.strip().replace('\xa0', ' ')  # pevná medzera → bežná medzera
            if not r:
                continue

            r = re.sub(r':(?=\S)', ': ', r)
            r = re.sub(r'([ABCČ])\s*\(', r'\1 (', r)

            rl = r.lower()

            if rl.startswith(("zdroj:", "stiahnuté:", "stiahnute:")):
                continue

            if rl.startswith(("r.", "r:")):
                ciste.append(r)
                preskakovat = True
                continue

            # NIKDY nepreskakovať riadky začínajúce na R.
            if ("responzóriový žalm" in rl or "aleluja" in rl) and not rl.startswith(("r.", "r:")):
                preskakovat = True
                continue


            if any(r.upper().startswith(x) for x in reset_preskakovania_nadpisy):
                preskakovat = False

            if preskakovat:
                continue

            if r.upper() == "REFRÉN ŽALMU":   # ← TOTO PRIDAŤ
                continue

            if set(r) <= {"=", "-"} and len(r) > 5:
                continue

            if "meniny:" in rl:
                continue

            if any(d in r for d in dni) and any(m in r for m in mesiace):
                continue

            ciste.append(r)

        # ------------------------------------------------------------
        # 2. Zvýraznenie nadpisov + prázdny riadok po nadpise
        # ------------------------------------------------------------
        nadpisy = ["ZAČIATOK", "ČÍTANIE Z", "ČÍTANIE ZO", "PRVÉ ČÍTANIE", "DRUHÉ ČÍTANIE", "EVANJELIUM"]

        sprac = []
        predosly_bol_nadpis = False

        for r in ciste:
            if any(r.upper().startswith(n) for n in nadpisy):
                sprac.append(f"\n\n{r.upper()}\n")
                predosly_bol_nadpis = True
                continue

            if predosly_bol_nadpis:
                sprac.append("")  # prázdny riadok
                predosly_bol_nadpis = False

            sprac.append(r)

        text = "\n".join(sprac)

        # ------------------------------------------------------------
        # 3. Odstránenie zdrojového bloku
        # ------------------------------------------------------------
        text = re.sub(r"[-=]{5,}.*?zdroj:.*?stiahnuté:.*?[-=]{5,}", "", text, flags=re.I | re.S)

        # ------------------------------------------------------------
        # 4. Odstránenie „Počuli sme slovo Pánovo“
        # ------------------------------------------------------------
        text = re.sub(r'počuli sme slovo pánovo\.?', "", text, flags=re.I)

        # ------------------------------------------------------------
        # 5. Oddelenie „Počuli sme Božie slovo.“
        # ------------------------------------------------------------
        text = re.sub(
            r'(?i)\s*"?\s*počuli sme božie slovo\.?"?',
            r'\n\nPočuli sme Božie slovo.\n',
            text
        )

        # ------------------------------------------------------------
        # 6. Oprava úvodzoviek
        # ------------------------------------------------------------
        text = re.sub(r'\.\s*”', '.”', text)
        text = re.sub(r'\s*”\s*$', '”', text, flags=re.M)

        # ------------------------------------------------------------
        # 7. Oprava skratiek
        # ------------------------------------------------------------
        skratky = [
            "Gn","Ex","Lv","Nm","Dt","Joz","Sdc","Rut","Sam","Kr","Krn","Ezd","Neh","Tob","Jdt","Est",
            "Mach","Job","Prís","Kaz","Pies","Múd","Sir","Iz","Jer","Nár","Bar","Ez","Dan","Oz","Joel",
            "Am","Abd","Jon","Mich","Nah","Hab","Sof","Ag","Zach","Mal",
            "Mt","Mk","Lk","Jn","Sk","Rim","Kor","Gal","Ef","Flp","Kol","Sol","Tim","Tít","Flm","Hebr",
            "Jak","Pt","Júd","Zjv"
        ]

        for sk in skratky:
            text = re.sub(rf'\b{sk}\.', f'{sk}.', text)

        # ------------------------------------------------------------
        # 8. Vloženie prázdneho riadku za krátkou vetou po nadpise
        # ------------------------------------------------------------
        def vloz_prazdny_riadok_za_vetu_bez_bodky(text):
            riadky = text.split("\n")
            nove = []
            po_nadpise = False

            for r in riadky:
                c = r.strip()

                if (
                    c.startswith("PRVÉ ČÍTANIE")
                    or c.startswith("ZAČIATOK")
                    or c.startswith("ČÍTANIE Z")
                    or c.startswith("EVANJELIUM")
                ):
                    po_nadpise = True
                    nove.append(r)
                    continue

                if po_nadpise and c and "." not in c and len(c.split()) <= 12:
                    nove.append(r)
                    nove.append("")
                    po_nadpise = False
                    continue

                nove.append(r)

            return "\n".join(nove)

        text = vloz_prazdny_riadok_za_vetu_bez_bodky(text)

        # ------------------------------------------------------------
        # 9. Extrakcia refrénov
        # ------------------------------------------------------------
        refreny = []
        refreny_seen = set()

        for riadok in text.splitlines():
            r = riadok.strip()

            # zachytí všetky varianty R., R:, R . :, R . . :
            if r.lower().startswith(("r.", "r:")):

                # odstráni prefix R, R., R:, R . :, R . . :
                r = re.sub(r'^[Rr]\s*[.:]\s*', '', r).strip()

                # odstráni úvodné : alebo . alebo : :
                r = r.lstrip(':. ').strip()

                # rozdelenie na hlavný refrén a alternatívu
                casti = re.split(r'\balebo\b', r, flags=re.IGNORECASE)

                # hlavný refrén
                hlavny = casti[0].strip()
                hlavny = re.sub(r'\.\s*$', '', hlavny)  # odstráni koncovú bodku

                # alternatíva (ak existuje)
                alternativa = None
                if len(casti) > 1:
                    alt = casti[1].strip()
                    alt = alt.lstrip(':. ').strip()
                    alt = re.sub(r'\.\s*$', '', alt)
                    alternativa = alt

                if hlavny:
                    kluc = (hlavny, alternativa)
                    if kluc not in refreny_seen:
                        refreny.append(kluc)
                        refreny_seen.add(kluc)

        # odstránenie refrénových riadkov z textu
        text = "\n".join(
            riadok for riadok in text.splitlines()
            if not riadok.strip().lower().startswith(("r.", "r:"))
            and riadok.strip().lower() != "alebo:"  # riadok alternatívy refrénu
        )

        # ------------------------------------------------------------
        # 10. Vyčistenie medzier
        # ------------------------------------------------------------
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text).strip()        

        # ------------------------------------------------------------
        # 11. Rozdelenie na bloky
        # ------------------------------------------------------------
        bloky = []
        casti = text.split("\n\n")
        refren_index = 0

        def vloz_dalsi_refren():
            nonlocal refren_index
            if refren_index >= len(refreny):
                return

            refren, alternativa = refreny[refren_index]
            refren_index += 1

            bloky.append("REFRÉN ŽALMU")
            bloky.append(f"R.: {refren}")

            if alternativa:
                bloky.append("Alebo:")
                bloky.append(f"R.: {alternativa}")

        for blok_cast in casti:
            blok_cast = blok_cast.strip()
            if not blok_cast:
                continue

            if blok_cast.startswith("ČÍTANIA NA SVÄTÚ OMŠU"):
                bloky.append(blok_cast)
                continue

            # krátka veta hneď po nadpise
            if (
                bloky
                and (
                    bloky[-1].startswith("PRVÉ ČÍTANIE")
                    or bloky[-1].startswith("ZAČIATOK")
                )
                and len(blok_cast.split()) <= 12
                and "." not in blok_cast
                and not blok_cast.isupper()
                and not blok_cast.startswith("R.:")
                and "Počuli sme Božie slovo" not in blok_cast
            ):
                bloky.append(blok_cast)
                continue

            # miesto, kde sa vkladá refrén + alternatíva
            if "počuli sme božie slovo" in blok_cast.lower():
                bloky.append("Počuli sme Božie slovo.")
                vloz_dalsi_refren()
                continue

            # nadpisy (PRVÉ ČÍTANIE, EVANJELIUM…) nedelíme ako bežný text.
            # Biblické odkazy v nadpise môžu byť dlhšie než 50 znakov.
            if blok_cast != "REFRÉN ŽALMU" and (
                any(blok_cast.startswith(n) for n in nadpisy)
                or (blok_cast.isupper() and len(blok_cast) < 50)
            ):
                bloky.append(blok_cast)
                continue

            # text po nadpise – rozdelenie na menšie bloky
            if bloky and (
                bloky[-1].startswith("PRVÉ ČÍTANIE")
                or bloky[-1].startswith("ZAČIATOK")
                or bloky[-1].startswith("DRUHÉ ČÍTANIE")
                or bloky[-1].startswith("EVANJELIUM")
            ):
                bloky.extend(self.rozdel_text_na_bloky(blok_cast, max_chars))
                continue

            # bežné rozdelenie textu
            bloky.extend(self.rozdel_text_na_bloky(blok_cast, max_chars))

        while refren_index < len(refreny):
            vloz_dalsi_refren()

        # ------------------------------------------------------------
        # 12. Uloženie
        # ------------------------------------------------------------
        finalny = "\n\n".join(bloky)
        _zapis_text_atomicky(subor, finalny, encoding="utf-8")

        if zobrazit_potvrdenie:
            messagebox.showinfo(
                "Hotovo",
                "Čítania boli upravené pre projekciu. Môžete ich otvoriť priamo v aplikácii Kinak "
                "(do vstupného poľa zadajte 'citania') alebo ich podľa potreby ďalej doladiť pre projekciu v Pomocníkovi."
            )
        try:
            self.manual_entry.focus_set()
        except Exception:
            pass
           
          
    def _spusti_jednoduche_stahovanie(
        self,
        *,
        lock: threading.Lock,
        zaneprazdnene_sprava: str,
        kontext: str,
        stiahni_funkcia,
        stiahni_args: tuple = (),
        stiahni_kwargs: dict | None = None,
        vytvor_log_spravu=None,
        on_success=None,
        spracuj_vysledok,
    ) -> bool:
        """
        Spoločná GUI logika pre jednoduché sťahovania na pozadí bez progress
        dialógu (nahrádza duplicitne definované _po_stiahnuti/_vlakno v
        `aktualizovat_citania_gui` a `aktualizovat_vespery_gui`).

        Postup:
        1. Pokus o získanie `lock` bez blokovania – ak je obsadený, zobrazí
           `zaneprazdnene_sprava` a vráti False.
        2. Nastaví kurzor na "wait" a spustí worker vlákno. To si NAJPRV samo
           overí internetové pripojenie (`_over_internet_socket()` – bez GUI
           vedľajších účinkov, bezpečné z worker vlákna); ak nie je dostupné,
           `stiahni_funkcia` sa vôbec nezavolá a používateľ dostane
           špecifickú hlášku "Žiadne internetové pripojenie". Inak zavolá
           `stiahni_funkcia(*stiahni_args, **stiahni_kwargs)` a vráti bool
           (úspech/neúspech). Ak funkcia doběhne bez výnimky a je zadané
           `vytvor_log_spravu(uspech)`, výsledná správa sa zaloguje cez
           `log_info`.
        3. Po dokončení (thread-safe cez self.master.after): ak hlavné okno
           ešte existuje a sťahovanie uspelo, zavolá voliteľné `on_success()`;
           v oboch prípadoch potom zavolá `spracuj_vysledok(uspech)`, ktoré
           zobrazí konkrétny messagebox a prípadne nastaví fokus (špecifické
           pre volajúceho). Napokon vždy obnoví kurzor a uvoľní `lock`.
        """
        if not lock.acquire(blocking=False):
            messagebox.showinfo("Kinak", zaneprazdnene_sprava)
            return False

        try:
            self.master.config(cursor="wait")
            self.master.update_idletasks()
        except Exception as e:
            log_exception(f"{kontext}: cursor=wait zlyhal", e)

        kwargs = stiahni_kwargs or {}

        def po_stiahnuti(uspech, bez_internetu=False):
            try:
                if not self.master.winfo_exists():
                    return

                if bez_internetu:
                    messagebox.showerror(
                        "Žiadne internetové pripojenie",
                        "Nie ste pripojení na internet.\n\nSkontrolujte Wi-Fi/kábel a skúste znova.",
                    )
                    return

                if uspech and callable(on_success):
                    try:
                        on_success()
                    except Exception as e:
                        log_exception(f"{kontext}: on_success callback zlyhal", e)

                spracuj_vysledok(uspech)
            finally:
                try:
                    self.master.config(cursor="")
                except tk.TclError:
                    pass
                try:
                    lock.release()
                except RuntimeError as e:
                    log_exception(f"{kontext}: lock už bol uvoľnený", e)

        def vlakno():
            # Rovnako ako v _spusti_stahovanie_s_progressom: kontrola internetu
            # sa vykonáva až tu (v pozadovom vlákne), aby blokujúci
            # socket.create_connection() nezamrazil GUI vlákno pred spustením.
            if not _over_internet_socket():
                try:
                    self.master.after(0, lambda: po_stiahnuti(False, bez_internetu=True))
                except Exception as e:
                    log_exception(f"{kontext}: master.after (bez internetu) zlyhal", e)
                    try:
                        lock.release()
                    except RuntimeError:
                        pass
                return

            try:
                uspech = stiahni_funkcia(*stiahni_args, **kwargs)
                if vytvor_log_spravu is not None:
                    log_info(vytvor_log_spravu(uspech))
            except Exception as e:
                log_exception(f"{kontext}: vlákno zlyhalo", e)
                uspech = False

            try:
                self.master.after(0, lambda: po_stiahnuti(uspech))
            except Exception as e:
                # Mainloop skončil, okno je preč – nič už nerobíme
                log_exception(f"{kontext}: master.after zlyhal", e)
                try:
                    lock.release()
                except RuntimeError as e2:
                    log_exception(f"{kontext}: lock už bol uvoľnený", e2)

        try:
            self._download_executor.submit(vlakno)
        except RuntimeError:
            threading.Thread(target=vlakno, daemon=True).start()
        return True


    def aktualizovat_citania_gui(self, datum=None, on_success=None):
        """
        GUI wrapper pre stiahnutie čítaní z lc.kbs.sk.
        Sťahovanie prebieha vo vlákne na pozadí – GUI nezmrazí.
        Po dokončení sa výsledok odovzdá späť do hlavného vlákna cez master.after().
        """

        if datum is None:
            datum = date.today()

        # Spoločný preflight (chýbajúce knižnice, internet, priečinok na piesne
        # + jeho vytvorenie) – rovnaký helper ako pre ostatných 8 GUI
        # downloaderov, aby prípadná budúca zmena poradia/textu kontrol
        # nemusela byť ručne zosúladená na viacerých miestach.
        if not self._priprav_stahovanie_gui(
            "aktualizovat_citania_gui",
            "Nepodarilo sa pripraviť priečinok pre citania.txt.",
        ):
            return False

        vystup_cesta = self.song_folder_path / "citania.txt"

        def spracuj_vysledok(uspech):
            if uspech:
                # Jedno zlúčené potvrdenie (upravenie pre projekciu už prebehlo cez on_success)
                messagebox.showinfo(
                    "Čítania aktualizované",
                    f"Čítania pre {datum.strftime('%d.%m.%Y')} boli úspešne stiahnuté!\n\n"
                    f"Zdroj: Konferencia biskupov Slovenska\n"
                    f"Súbor: {vystup_cesta.name}\n\n"
                    f"Čítania boli pripravené pre projekciu. Môžete ich otvoriť priamo v aplikácii Kinak "
                    f"alebo ich podľa potreby ďalej doladiť pre projekciu v Pomocníkovi."
                )
            else:
                zobraz_chybu_stahovania("čítania", "lc.kbs.sk")

                # fokus späť do vstupného poľa – spoľahlivo
                def vrat_fokus():
                    try:
                        self.manual_entry.focus_set()
                    except Exception as e:
                        log_exception("aktualizovat_citania_gui: focus_set zlyhal", e)

                self.master.after(30, vrat_fokus)

        return self._spusti_jednoduche_stahovanie(
            lock=self._citania_lock,
            zaneprazdnene_sprava="Sťahovanie čítaní už prebieha, čakajte prosím.",
            kontext="aktualizovat_citania_gui",
            stiahni_funkcia=stiahni_citania_z_lc_kbs,
            stiahni_args=(datum, vystup_cesta),
            vytvor_log_spravu=lambda uspech: f"Čítania pre {datum} stiahnuté: {uspech}",
            on_success=on_success,
            spracuj_vysledok=spracuj_vysledok,
        )

    def open_vespery(self):
        """Zobrazí dialóg: Stiahnuť vešpery na Dnes alebo na vybraný dátum."""

        def akcia(datum):
            self.aktualizovat_vespery_gui(datum=datum)

        self._zobraz_dialog_stiahnutia(
            title="Stiahnuť vešpery",
            nadpis="Stiahnuť vešpery na:",
            akcia=akcia,
        )

    def aktualizovat_vespery_gui(self, datum=None, on_success=None):
        """
        GUI wrapper pre stiahnutie Vešpier z breviar.kbs.sk.
        Sťahovanie prebieha vo vlákne na pozadí – GUI nezmrazí.
        """
        if datum is None:
            datum = date.today()

        # Spoločný preflight – pozri poznámku v aktualizovat_citania_gui vyššie.
        if not self._priprav_stahovanie_gui(
            "aktualizovat_vespery_gui",
            "Nepodarilo sa pripraviť priečinok pre vespery.txt.",
        ):
            return False

        vystup_cesta = self.song_folder_path / "vespery.txt"

        oznacit = getattr(self, "zobrazovat_znaky_chorov", True)

        def spracuj_vysledok(uspech):
            if uspech:
                messagebox.showinfo(
                    "Vešpery aktualizované",
                    f"Vešpery pre {datum.strftime('%d.%m.%Y')} boli úspešne stiahnuté!\n\n"
                    f"Zdroj: breviar.kbs.sk\n"
                    f"Súbor: {vystup_cesta.name}\n\n"
                    "Vešpery boli pripravené pre projekciu. Môžete ich otvoriť priamo v aplikácii Kinak "
                    "(do vstupného poľa zadajte 'vespery') alebo ich podľa potreby ďalej doladiť pre projekciu v Pomocníkovi."
                )
                self.manual_entry.focus_set()
            else:
                zobraz_chybu_stahovania("vešpery", "breviar.kbs.sk")
                try:
                    self.master.after(30, lambda: self.manual_entry.focus_set())
                except tk.TclError:
                    pass

        return self._spusti_jednoduche_stahovanie(
            lock=self._vespery_lock,
            zaneprazdnene_sprava="Sťahovanie vešpier už prebieha, čakajte prosím.",
            kontext="aktualizovat_vespery_gui",
            stiahni_funkcia=stiahni_vespery_z_breviar,
            stiahni_args=(datum, vystup_cesta),
            stiahni_kwargs={"oznacit_chory": oznacit},
            vytvor_log_spravu=lambda uspech: f"[BREVIAR] Vešpery pre {datum} stiahnuté: {uspech}",
            on_success=on_success,
            spracuj_vysledok=spracuj_vysledok,
        )

    def aktualizovat_direktorium_label(self):
        """Aktualizuje viditeľnosť a text labelu direktória pri zachovaní pôvodného poradia."""
        if self.direktorium_label is None:
            return

        # Ak je direktórium vypnuté → skryť a skončiť
        if not self.zobrazit_direktorium_var.get():
            self.direktorium_label.pack_forget()
            return

        # Ak je direktórium zapnuté → aktualizovať text a zobraziť
        obdobie = self.obdobie_var.get()
        self.direktorium_label.config(text=f"Odporúčané piesne pre:\n{obdobie}")
        self.direktorium_label.pack(anchor="w", pady=(0, 5))
                
       
    def aktualizuj_popis(self, nazov_bez_ext):
        popis = next((v for k, v in self.popisy_suborov.items() if k.lower() == nazov_bez_ext.lower()), "")
        if popis:
            self.popis_label.config(text=f"Žalmy pre {popis}")
        else:
            self.popis_label.config(text="")
            self.direktorium_label.config(text="")

    def odlozene_auto_nacitanie(self, event=None):
        # 1. Ignorovať klávesy pre posun strofy a navigáciu
        if event is not None:
            keysym = getattr(event, "keysym", "")
            if keysym in (
                "plus", "minus", "equal", "KP_Add", "KP_Subtract",
                "Left", "Right", "Up", "Down", "Return", "Escape", "Tab",
                "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Caps_Lock"
            ):
                return

        aid = self._auto_nacitanie_after_id

        # Zrušenie starého callbacku, ale len ak je to platné after ID
        if isinstance(aid, str) and aid.startswith("after#"):
            try:
                self.master.after_cancel(aid)
            except Exception as e:
                log_exception("odlozene_auto_nacitanie: after_cancel failed", e)

        # Vždy resetujeme ID, aby sme nerušili staré hodnoty
        self._auto_nacitanie_after_id = None

        # Naplánujeme nový callback
        try:
            self._auto_nacitanie_after_id = self.master.after(400, self.auto_nacitanie_suboru)
        except Exception as e:
            log_exception("odlozene_auto_nacitanie: master.after failed", e)        
        

    def _update_nazov_label(self):
        """
        Ovládací panel – horný stavový label.
        -------------------------------------
        - Zobrazuje číslo piesne + stav strofy (napr. "123 — 2/5").
        - Ak je current == 0 → prázdny text. Ak nemáme názov piesne, nič nezobrazujeme.
        - Ovládací panel ukazuje detailný stav, projekcia ukazuje len názov piesne.
        """
        try:
            # 1) Ak nemáme názov piesne → nič nezobrazujeme
            if not getattr(self, "nazov_piesne", ""):
                final_text = ""
                self.nazov_label.config(text=final_text)

                if self.is_text_visible:
                    self.projection_window.update_title(name="", current=0, total=None)
                return

            # 2) Získame číslo piesne
            cislo = self.aktualne_cislo_piesne or self.nazov_piesne

            # čisté vizuálne formátovanie čísla
            if isinstance(cislo, str) and cislo.isdigit():
                cislo = str(int(cislo))

            # 3) Získame stav strofy
            current, total = self.ziskaj_aktualnu_a_celkovu()

            # 4) Vytvoríme výsledný text pre ovládací panel
            if self.aktualne_strofy and current > 0:
                final_text = f"{cislo} — {current}/{total}"
            else:
                final_text = ""

            # 5) POISTKA – ak sa text nezmenil, nič nerobíme
            if self.posledny_nazov_v_labeli == final_text:
                return

            self.posledny_nazov_v_labeli = final_text            

            # 6) Aktualizácia ovládacieho panelu
            self.nazov_label.config(text=final_text)

            # 7) Projekcia dostane len názov piesne (bez strofy)
            if self.is_text_visible:
                self.projection_window.update_title(
                    name=self.nazov_piesne if final_text else "",
                    current=current,
                    total=total
                )

        except Exception as e:            
            log_exception("Chyba pri aktualizácii stavového labelu", e)          
                       
    # Normalizuje text strofy – odstráni pomocné znaky (·, _) a medzery.
    # Vďaka tomu sa rôzne varianty refrénu považujú za rovnaký text
    # a zvýrazňovanie už správne postupuje na ďalší výskyt
    # a teda pri refréne už nepreskakuje na jeho prvý výskyt.
    def _normalize(self, text):
        """
        → interné porovnávanie
        """
        return text.replace("·", "").replace("_", "").strip()  
        
    def format_typography(self, text):
        """
        Ošetruje slovenskú typografiu – nahrádza medzery po jednoznakových
        predložkách a spojkách nezlomiteľnou medzerou.
        """
        
        if not text:
            return ""

        predlozky = "vzuoikasyVZUOIKASY"

        return re.sub(
            rf"(?<!\S)([{predlozky}])\s+",
            "\\1\u00A0",
            text
        )    
    
    def remove_special_chars(self, text):
        """
        → čistenie pre projekciu
        """
        vysledok = text or ""

        if not getattr(self, "zobrazovat_znaky_chorov", True):
            vysledok = re.sub(r"(?m)^\[(?:L|P)\]\s*", "", vysledok)

        if not getattr(self, "zobrazovat_specialne_znaky", True):
            vysledok = vysledok.replace("·", "").replace("_", "")

        return vysledok

    def _dopln_znaky_chorov_do_aktualnych_vespier(self):
        """Doplní [L]/[P] do už načítaných vešpier, ak boli načítané zo staršieho súboru bez značiek."""
        if not getattr(self, "zobrazovat_znaky_chorov", True):
            return

        nazvy = [
            str(getattr(self, "nazov_piesne", "") or ""),
            str(getattr(self, "aktualne_cislo_piesne", "") or ""),
        ]
        aktualny_subor_cesta = getattr(self, "aktualny_subor_cesta", None)
        if aktualny_subor_cesta:
            try:
                aktualny_subor_cesta = Path(aktualny_subor_cesta)
                nazvy.extend([aktualny_subor_cesta.name, aktualny_subor_cesta.stem])
            except TypeError:
                nazvy.append(str(aktualny_subor_cesta))

        nazov_lower = " ".join(nazvy).lower()
        if "vesper" not in nazov_lower and "vešper" not in nazov_lower:
            return

        strofy = getattr(self, "aktualne_strofy", None)
        if not strofy or len(strofy) <= 1:
            return

        obsah = "\n\n".join(strofy[1:])
        if re.search(r"(?m)^\[(?:L|P)\]\s*", obsah):
            return

        riadky = obsah.splitlines()
        if not any(r in _BREVIAR_SEKCIE for r in riadky):
            return

        aktualny_index = getattr(self, "aktualny_index_strofa", 0)
        riadky = oznac_chory(riadky, oznacit_lp=True)
        riadky = _normalizuj_aleluja_v_tretej_antifone_psalmodie(riadky)
        novy_obsah = "\n".join(riadky)
        nove_strofy = [s.strip() for s in re.split(r"\n\s*\n", novy_obsah) if s.strip()]

        if not nove_strofy:
            return

        self.aktualne_strofy = [""] + nove_strofy
        self.aktualny_index_strofa = min(aktualny_index, len(self.aktualne_strofy) - 1)

        text_widget = getattr(self, "obsah_suboru_text", None)
        if text_widget is not None:
            try:
                text_widget.config(state=tk.NORMAL)
                text_widget.delete("1.0", tk.END)
                text_widget.insert(tk.END, novy_obsah)
                text_widget.tag_remove("highlight", "1.0", tk.END)
                text_widget.config(state=tk.DISABLED)
            except Exception as e:
                log_exception("_dopln_znaky_chorov_do_aktualnych_vespier: aktualizacia nahladu zlyhala", e)
                try:
                    text_widget.config(state=tk.DISABLED)
                except Exception:
                    pass
    
    def oznac_aktualnu_strofu_v_obsahu(self):
        """
        Zvýrazní aktuálnu strofu v obsahu súboru.
        Ak sa rovnaký text (napr. refrén) vyskytuje viackrát,
        zvýrazní sa N-tý výskyt podľa aktuálneho indexu strofy.
        """
        # --- Vyčistenie highlightu ---
        try:
            self.obsah_suboru_text.config(state=tk.NORMAL)
            self.obsah_suboru_text.tag_remove("highlight", "1.0", tk.END)
        except Exception as e:
            log_exception("Chyba pri čistení highlightu v náhľade", e)

        # --- Neplatné stavy ---
        if not self.aktualne_strofy:
            try:
                self.obsah_suboru_text.config(state=tk.DISABLED)
            except Exception as e:
                log_exception("Nepodarilo sa uzamknúť obsah_suboru_text (prázdne strofy)", e)
            return

        if not (0 <= self.aktualny_index_strofa < len(self.aktualne_strofy)):
            try:
                self.obsah_suboru_text.config(state=tk.DISABLED)
            except Exception as e:
                log_exception("Nepodarilo sa uzamknúť obsah_suboru_text (index mimo rozsah)", e)
            return

        # ------------------------------------------------------------
        # 0) NULTÁ STROFA – zobraz číslo piesne v ovládacom paneli
        # ------------------------------------------------------------
        if self.aktualny_index_strofa == 0:
            try:
                cislo = self.aktualne_cislo_piesne or self.nazov_piesne or ""
                if isinstance(cislo, str) and cislo.isdigit():
                    cislo = str(int(cislo))

                self.strofa_label.config(state=tk.NORMAL)
                self.strofa_label.delete("1.0", tk.END)

                self.strofa_label.tag_configure(
                    "center",
                    justify="center",
                    font=(self.font_family, 30, "bold")
                )

                self.strofa_label.insert("1.0", cislo, "center")
                self.strofa_label.config(state=tk.DISABLED)

            except Exception as e:
                log_exception("Chyba pri zobrazení čísla piesne v ovládacom paneli", e)

            # Náhľad uzamkneme
            try:
                self.obsah_suboru_text.config(state=tk.DISABLED)
            except Exception as e:
                log_exception("Nepodarilo sa uzamknúť obsah_suboru_text (nultá strofa)", e)

            return

        # ------------------------------------------------------------
        # 1) REÁLNA STROFA – zvýraznenie v náhľade
        # ------------------------------------------------------------
        aktualna_strofa = self.aktualne_strofy[self.aktualny_index_strofa]
        norm_current = self._normalize(aktualna_strofa)

        if not norm_current.strip():
            try:
                self.obsah_suboru_text.config(state=tk.DISABLED)
            except Exception as e:
                log_exception("Nepodarilo sa uzamknúť obsah_suboru_text (prázdna strofa)", e)
            return

        # Koľký výskyt tejto strofy to je?
        count = 0
        for i in range(len(self.aktualne_strofy)):
            if self._normalize(self.aktualne_strofy[i]) == norm_current:
                count += 1
            if i == self.aktualny_index_strofa:
                break

        # Nájdeme N-tý výskyt v Text widgete
        start_index = None
        pos = "1.0"

        try:
            for _ in range(count):
                found = self.obsah_suboru_text.search(norm_current, pos, tk.END)
                if not found:
                    break
                start_index = found
                pos = f"{found} + {len(norm_current)} chars"
        except Exception as e:
            log_exception("Chyba pri vyhľadávaní textu strofy v náhľade", e)
            start_index = None

        # Highlight
        if start_index:
            try:
                end_index = f"{start_index} + {len(norm_current)} chars"
                self.obsah_suboru_text.tag_add("highlight", start_index, end_index)
                self.obsah_suboru_text.see(start_index)
            except Exception as e:
                log_exception("Chyba pri aplikácii tagu highlight", e)

        # ------------------------------------------------------------
        # 2) OVLÁDACÍ PANEL – typografia + font
        # ------------------------------------------------------------
        try:
            text = self.format_typography(aktualna_strofa)
            font_size = self.vypocitaj_velkost_pisma_pre_strofu(text)

            self.strofa_label.config(state=tk.NORMAL)
            self.strofa_label.delete("1.0", tk.END)

            self.strofa_label.tag_configure(
                "center",
                justify="center",
                font=(self.font_family, font_size, "bold")
            )

            self.strofa_label.insert("1.0", text, "center")
            self.strofa_label.config(state=tk.DISABLED)

        except Exception as e:
            log_exception("Chyba pri aktualizácii stredného panelu (strofa_label)", e)

        # ------------------------------------------------------------
        # 3) Aktualizácia horného panelu
        # ------------------------------------------------------------
        try:
            self._update_nazov_label()
        except Exception as e:
            log_exception("Chyba pri volaní _update_nazov_label", e)

        # ------------------------------------------------------------
        # 4) Uzamknutie náhľadu
        # ------------------------------------------------------------
        try:
            self.obsah_suboru_text.config(state=tk.DISABLED)
        except Exception as e:
            log_exception("Záverečné uzamknutie náhľadu zlyhalo", e)       
                                          
                          
    def enter_aktivuj_projekciu(self, event=None):
        raw = self.manual_entry.get().strip()
        clean = re.sub(r'[^0-9A-Za-z_-]', '', raw)
        vybrany_subor = self.subor_var.get().strip()

        # ak už projekcia beží → vypnúť
        if self.is_text_visible:
            self.vypni_projekciu()
            return "break"

        nazov = None
        zadane_manualne = False

        # manuálne zadaný prefix
        if clean:
            hladany_full = self.najdi_subor_podla_prefixu(clean)
            if not hladany_full:
                messagebox.showerror("Kinak: Nenájdené", f"Súbor '{raw}' neexistuje v priečinku piesní.")
                return "break"
            nazov = Path(hladany_full).stem
            zadane_manualne = True

        # výber zo zoznamu
        elif vybrany_subor and vybrany_subor != "—":
            hladany_full = self.najdi_subor_podla_prefixu(vybrany_subor)
            if not hladany_full:
                messagebox.showerror("Kinak: Nenájdené", f"Súbor '{vybrany_subor}' neexistuje v priečinku piesní.")
                return "break"
            nazov = Path(hladany_full).stem

        # nič nezadané
        else:
            self.aktualizuj_popis(self.nazov_piesne)
            return "break"

        # načítať pieseň a zobraziť ju na projekcii
        self.nacitat_piesne(nazov_suboru=nazov, zobrazit_na_projekcii=True)

        # zapnúť projekciu (vrátane indikátora)
        self.zapni_projekciu()

        # reset výberu a popisov po manuálnom vstupe
        if zadane_manualne:
            self.subor_var.set("—")
            self.popis_label.config(text="")
            self.direktorium_label.config(text="")

        self.aktualizuj_popis(nazov)
        return "break"  
           

    def aktivuj_projekciu_pre_subor(self, nazov_bez_ext):
        if not self.aktualne_strofy or self.nazov_piesne != nazov_bez_ext:
            self.nacitat_piesne(nazov_suboru=nazov_bez_ext)
        
        self.zapni_projekciu()
        self.aktualizuj_popis(nazov_bez_ext)
        
        
    def _udalost_je_v_editovatelnom_widgete(self, event=None):
        widget = getattr(event, "widget", None)
        if widget is None:
            return False

        # Hlavne ovladacie polia su zamerne vynimka: + a - tam ovladaju strofy.
        if widget in (getattr(self, "manual_entry", None), getattr(self, "song_combobox", None)):
            return False

        try:
            widget_class = widget.winfo_class()
        except Exception:
            return False

        return widget_class in {"Entry", "Text", "TEntry", "TCombobox", "Combobox", "Spinbox", "TSpinbox"}

    def klavesa_plus(self, event=None):
        if self._udalost_je_v_editovatelnom_widgete(event):
            return None
        return self.posun_strofu(+1)

    def klavesa_minus(self, event=None):
        if self._udalost_je_v_editovatelnom_widgete(event):
            return None
        return self.posun_strofu(-1)

    def klavesa_vpravo(self, event=None):
        return self.posun_strofu(+1)

    def klavesa_vlavo(self, event=None):
        return self.posun_strofu(-1)    

    def posun_strofu(self, direction):
        """
        Posunie aktuálnu strofu o daný smer:
        - direction = +1 → dopredu
        - direction = -1 → dozadu
        Zohľadňuje nultú strofu a vždy aktualizuje projekciu aj horný panel.
        """
        if not self.aktualne_strofy:
            return "break"

        current, total = self.ziskaj_aktualnu_a_celkovu()

        # posun dopredu
        if direction > 0 and self.aktualny_index_strofa < total:
            self.aktualny_index_strofa += 1
            self.zobraz_aktualnu_strofu()

        # posun dozadu
        elif direction < 0 and self.aktualny_index_strofa > 0:
            self.aktualny_index_strofa -= 1
            self.zobraz_aktualnu_strofu()
        return "break"   
    
    def vymazat_subor_menu(self, event=None):
        if getattr(self, "_suppress_vymazat", False):
            return
        self.subor_var.set("—")
        self.popis_label.config(text="")
        self.direktorium_label.config(text="")
        
        
    def normalize_alnum(self, s: str) -> str:
        """
        Prevedie 'Citáty' -> 'citaty'.
        Odstráni diakritiku A ponechá len základné písmená a čísla (ASCII alnum).
        Medzery, zátvorky, interpunkcia sú odstránené.
        Používa sa pri vyhľadávaní súborov piesní podľa prefixu.
        Pozri aj: modul-level normalize_diacritics() – miernejší variant.
        """
        if not s:
            return ""
        # 1. Rozklad znakov (á -> a + dĺžeň)
        nfkd = unicodedata.normalize("NFKD", str(s))
        # 2. Ponecháme len alfanumerické ASCII (zahodí dĺžne, medzery, zátvorky)
        return "".join(c for c in nfkd if c.isalnum() and c.isascii()).lower()

    def najdi_subor_podla_prefixu(self, prefix):
        """
        Robustné vyhľadávanie. Funguje pre 'citát' aj 'citat'.
        """
        if not prefix:
            return None

        # 1. Normalizácia vstupu
        prefix_clean = self.normalize_alnum(prefix)
        if not prefix_clean:
            return None

        # 2. Príprava cesty
        priečinok = self.song_folder_path
        if not priečinok.exists() or not priečinok.is_dir():
            return None

        # 3. Načítanie máp súborov
        try:
            # Zoradenie pre stabilitu (abecedne)
            vsetky_subory = sorted(list(priečinok.glob("*.txt")), key=lambda x: x.name.lower())
            
            bez_ext = {}
            for f in vsetky_subory:
                if f.is_file():
                    norm_name = self.normalize_alnum(f.stem)
                    # Uložíme len ak norm_name nie je prázdne a ešte tam nie je
                    if norm_name and norm_name not in bez_ext:
                        bez_ext[norm_name] = f.name
        except Exception as e:
            if 'log_exception' in globals():
                log_exception("Chyba pri čítaní priečinka", e)
            return None

        # --- STRATÉGIA VYHĽADÁVANIA ---

        # A) PRESNÁ ZHODA (napr. citaty == citaty)
        if prefix_clean in bez_ext:
            return bez_ext[prefix_clean]

        # B) ČÍSELNÁ LOGIKA (003, 3...)
        if prefix_clean.isdigit():
            n = int(prefix_clean)
            padded = f"{n:03d}"
            short = str(n)
            if padded in bez_ext: return bez_ext[padded]
            if short in bez_ext: return bez_ext[short]
            
            for name_noext, full_name in bez_ext.items():
                if name_noext.startswith(padded): return full_name

        # C) ALFANUMERICKÝ PREFIX (najdôležitejšie pre 'citát' -> 'citáty.txt')
        for name_noext, full_name in bez_ext.items():
            if name_noext.startswith(prefix_clean):
                return full_name

        # D) VNÚTORNÁ ZHODA (napr. 'zasvätenia' -> 'KK_Modlitba zasvätenia.txt')
        # Spúšťame ju až po presnej a prefixovej zhode, aby kratšie kódy typu
        # 'KK' alebo čísla stále dostali prioritu pred voľným hľadaním v názve.
        for name_noext, full_name in bez_ext.items():
            if prefix_clean in name_noext:
                return full_name

        # E) POSLEDNÁ ZÁCHRANA (lstrip núl)
        p_nozero = prefix_clean.lstrip("0")
        if p_nozero:
            for name_noext, full_name in bez_ext.items():
                if name_noext.lstrip("0").startswith(p_nozero):
                    return full_name

        return None        
    
    def skus_manualne_nacitanie(self, event=None):
        """
        Pokúsi sa načítať pieseň podľa manuálne zadaného čísla/prefixu.
        Používa pathlib pre prácu s cestami.
        """
        # ------------------------------------------------------------
        # Spúšťať IBA pri Enter v manual_entry
        # (zabráni spusteniu pri minimalizácii okna, focus-out, atď.)
        # ------------------------------------------------------------
        if event is not None:
            if getattr(event, "keysym", None) != "Return":
                return
            if event.widget is not self.manual_entry:
                return

        raw = self.manual_entry.get().strip()
        # Očistíme vstup od diakritiky a nepovolených znakov
        raw_clean = self.normalize_alnum(raw)
        
        if not raw_clean:
            return

        nazov_pre_hladanie = raw_clean
        hladany_subor_meno = self.najdi_subor_podla_prefixu(nazov_pre_hladanie)
        
        if not hladany_subor_meno:
            messagebox.showinfo("Kinak: Nenájdené", f"Súbor '{raw}' neexistuje v priečinku piesní.")
            return

        # --- Pathlib spracovanie ---
        song_folder = self.song_folder_path
        cesta_obj = song_folder / hladany_subor_meno
        
        # .stem vráti názov súboru bez prípony (napr. '256' namiesto '256.txt')
        nazov_bez_ext = cesta_obj.stem

        # Hľadanie popisu (žalmy)
        popis = next((v for k, v in self.popisy_suborov.items() 
                      if k.lower() == nazov_bez_ext.lower()), "")
        
        if popis:
            self.popis_label.config(text=f"Žalmy pre {popis}")
        else:
            self.popis_label.config(text="")
            self.direktorium_label.config(text="")

        # Načítanie samotnej piesne
        self.nacitat_piesne(nazov_suboru=nazov_bez_ext)
        self._aktualizuj_direktorium_pre_subor(nazov_bez_ext)

    def auto_nacitanie_suboru(self, event=None):

        # ------------------------------------------------------------
        # Ignoruj udalosti, ktoré nesúvisia s písaním do manual_entry
        # (minimalizácia okna, focus out, visibility change...)
        # ------------------------------------------------------------
        if event is not None:
            if getattr(event, "type", None) != "3":   # 3 = KeyRelease (EventType je str-enum, porovnanie == funguje)
                return
            if event.widget is not self.manual_entry:
                return

        raw = self.manual_entry.get().strip()
        raw_clean = self.normalize_alnum(raw)

        # ------------------------------------------------------------
        # 1) Prázdny vstup → reset len ak je v menu pomlčka
        # ------------------------------------------------------------
        if not raw_clean:
            if self.subor_var.get().strip() == "—":
                # Vymaž panel "Obsah súboru"
                self.obsah_suboru_text.config(state=tk.NORMAL)
                self.obsah_suboru_text.delete("1.0", tk.END)
                self.obsah_suboru_text.config(state=tk.DISABLED)

                # Vymaž horný rámec so strofou
                self.strofa_label.config(state=tk.NORMAL)
                self.strofa_label.delete("1.0", tk.END)
                self.strofa_label.config(state=tk.DISABLED)

                # Vymaž horný label
                self.nazov_label.config(text="")

                # Reset stavových premenných
                self.nazov_piesne = ""
                self.aktualne_cislo_piesne = "000"
                self.aktualne_strofy = []
                self.aktualny_index_strofa = 0

                # Reset direktória
                self.popis_label.config(text="")
                self.direktorium_label.config(text="")

                # Vypni projekciu, ak beží
                if self.is_text_visible:
                    self.vypni_projekciu()

            return

        # ------------------------------------------------------------
        # 2) Máme vstup → pokús sa nájsť súbor
        # ------------------------------------------------------------
        hladany_subor = self.najdi_subor_podla_prefixu(raw_clean)

        if not hladany_subor:
            # TICHÉ čistenie UI (bez messageboxu)
            self.obsah_suboru_text.config(state=tk.NORMAL)
            self.obsah_suboru_text.delete("1.0", tk.END)
            self.obsah_suboru_text.config(state=tk.DISABLED)

            self.strofa_label.config(state=tk.NORMAL)
            self.strofa_label.delete("1.0", tk.END)
            self.strofa_label.config(state=tk.DISABLED)

            self.nazov_label.config(text="")

            # Reset stavových premenných
            self.nazov_piesne = ""
            self.aktualne_cislo_piesne = "000"
            self.aktualne_strofy = []
            self.aktualny_index_strofa = 0

            # Reset direktória
            self.popis_label.config(text="")
            self.direktorium_label.config(text="")

            # Vypni projekciu, ak beží
            if self.is_text_visible:
                self.vypni_projekciu()

            return

        # ------------------------------------------------------------
        # 3) Súbor existuje → načítaj ho
        # ------------------------------------------------------------
        nazov_bez_ext = Path(hladany_subor).stem

        # Ak je to ten istý súbor → nič nemeníme
        if nazov_bez_ext == self.nazov_piesne:
            return

        # Reset výberov a popisov
        self.subor_var.set("—")
        self.popis_label.config(text="")
        self.direktorium_label.config(text="")

        # Reset comboboxu
        self.song_combobox.current(0)

        # Vypni projekciu, ak beží
        if self.is_text_visible:
            self.vypni_projekciu()

        # Načítaj nový súbor
        self.nacitat_piesne(nazov_suboru=nazov_bez_ext)
        self.aktualizuj_popis(nazov_bez_ext)
        self._aktualizuj_direktorium_pre_subor(nazov_bez_ext)                
                                
    def zapni_projekciu(self):
        if not self.aktualne_strofy:
            return

        try:
            self.is_text_visible = True

            # --- LIVE PREVIEW: zobraziť len ak je povolený ---
            try:
                # OPRAVA: Zjednotený názov premennej na 'live_preview_label'
                if self.live_preview_label is not None and self.zobrazovat_live_preview_var.get():
                    self.live_preview_label.place(relx=0.5, rely=0.5, anchor="center")
            except Exception as e:
                log_exception("zapni_projekciu: live_preview display", e)

            # zobraz aktuálnu strofu na projekcii
            try:
                self.zobraz_aktualnu_strofu()
            except Exception as e:
                log_exception("zapni_projekciu: zobraz_aktualnu_strofu failed", e)

            # indikátor projekcie (Canvas)
            try:
                self.set_projection_indicator(True)
            except Exception as e:
                log_exception("zapni_projekciu: set_projection_indicator failed", e)

        except Exception as e:
            # Zachytí akúkoľvek inú neočakávanú chybu v metóde
            log_exception("zapni_projekciu: hlavná chyba metódy", e)

    def vypni_projekciu(self):
        try:
            self.is_text_visible = False

            # vymazať projekciu
            try:
                self.projection_window.update_text("")
                self.projection_window.update_title("", current=0, total=None)
            except Exception as e:
                log_exception("vypni_projekciu: update_text/title", e)

            # indikátor projekcie (Canvas)
            try:
                self.set_projection_indicator(False)
            except Exception as e:
                log_exception("vypni_projekciu: set_projection_indicator", e)

            # reset uloženého textu projekcie
            self.original_projection_text = ""

            # --- LIVE PREVIEW: úplne skryť ---
            try:
                # OPRAVA: Zjednotený názov premennej na 'live_preview_label'
                if self.live_preview_label is not None:
                    self.live_preview_label.config(text="")
                    self.live_preview_label.place_forget()
            except Exception as e:
                log_exception("vypni_projekciu: live_preview cleanup", e)

        except Exception as e:
            # Hlavný záchytný bod pre celú metódu
            log_exception("vypni_projekciu: hlavná chyba", e)


    def set_projection_indicator(self, active: bool):
        farba = "#00cc00" if active else "#888888"
        self.indikator_ziarovka.itemconfig(self.indikator_id, fill=farba)      
            
        
    def filtrovat_subory(self, vybrane_obdobie):
        # Vyčisti vstupné pole
        try:
            self.manual_entry.delete(0, tk.END)
        except Exception as e:
            log_exception("filtrovat_subory: manual_entry.delete", e)

        # Vymaž popis
        try:
            self.popis_label.config(text="")
            self.direktorium_label.config(text="")
        except Exception as e:
            log_exception("filtrovat_subory: popis_label config", e)

        # Vyčisti panel Obsah súboru
        try:
            self.obsah_suboru_text.config(state=tk.NORMAL)
            self.obsah_suboru_text.delete("1.0", tk.END)
            self.obsah_suboru_text.config(state=tk.DISABLED)
        except Exception as e:
            log_exception("filtrovat_subory: obsah_suboru_text clear", e)

        # Reset projekcie – použijeme iba centrálnu metódu
        if getattr(self, "is_text_visible", False):
            try:
                self.vypni_projekciu()
            except Exception as e:
                log_exception("filtrovat_subory: vypni_projekciu", e)

        # Vyčisti horný panel strofy
        try:
            self.original_projection_text = ""
            self.strofa_label.config(state=tk.NORMAL)
            self.strofa_label.delete("1.0", tk.END)
            self.strofa_label.config(state=tk.DISABLED)
        except Exception as e:
            log_exception("filtrovat_subory: strofa_label clear", e)

        # Vyčisti názov label
        try:
            self.nazov_label.config(text="")
        except Exception as e:
            log_exception("filtrovat_subory: nazov_label config", e)

        # Znovu načítaj zoznam súborov
        try:
            kody = self.obdobie_subory.get(vybrane_obdobie, [])

            # Sentinel None znamená „všetko nezaradené" – vypočítame dynamicky
            if kody is None:
                subory = self._ziskaj_nezaradene_subory()
            else:
                subory = kody

            # Naplň menu súborov
            menu = self.subor_menu["menu"]
            menu.delete(0, "end")
            for subor in subory:
                menu.add_command(
                    label=subor,
                    command=lambda value=subor: self.nacitat_podla_menu(value)
                )

            # Resetuj výber súboru v menu
            self.subor_var.set("—")
        except Exception as e:
            log_exception("filtrovat_subory: menu update", e)
        

    def ziskaj_zoznam_suborov(self):
        """
        Vráti zoznam názvov súborov (bez prípony .txt) v priečinku piesní.
        Optimalizované cez Pathlib.
        """
        # TU KONVERTUJEME: String z configu zmeníme na Path objekt.
        # Ak je cesta prázdna, Path() vráti aktuálny priečinok (.), 
        # preto je dobré mať v configu vždy aspoň DEFAULT_SONG_FOLDER.
        cesta_str = self.song_folder_path if self.song_folder_path else "."
        priečinok = Path(cesta_str)

        # 1. Kontrola existencie a typu (či to nie je súbor namiesto priečinka)
        if not priečinok.exists() or not priečinok.is_dir():
            messagebox.showinfo(
                "Kinak: Vyberte priečinok piesní",
                f"Priečinok s piesňami neexistuje alebo je neplatný:\n{priečinok}\n\n"
                "Vyberte priečinok piesní v Nastaveniach."
            )
            return []

        # 2. Načítanie .txt súborov pomocou glob
        try:
            # f.stem je geniálna vlastnosť pathlib - vráti názov bez .txt
            subory = [f.stem for f in priečinok.glob("*.txt") if f.is_file()]
        except Exception as e:
            log_exception("Chyba pri čítaní zoznamu súborov", e)
            return []

        # 3. Kontrola prázdneho priečinka
        if not subory:
            messagebox.showinfo(
                "Kinak: Žiadne piesne",
                f"V priečinku sa nenašli žiadne súbory .txt.\n\n"
                "Skontrolujte zvolený priečinok v časti Nastavenia → Umiestnenie súborov.\n\n"
                f"Aktuálne nastavená cesta:\n{priečinok.resolve()}"
            )



            return []

        # Vrátime abecedne zoradený zoznam (case-insensitive)
        # s.lower() zabezpečí, že "A" a "a" budú pri sebe
        return sorted(subory, key=lambda s: s.lower())
    

    def _ziskaj_nezaradene_subory(self) -> list[str]:
        """
        Vráti zoznam názvov súborov (stem), ktoré nie sú zaradené v žiadnom
        z existujúcich filtrov v self.obdobie_subory ani medzi číslované piesne.

        Súbor je považovaný za „zaradený" ak jeho stem (normalizovaný cez
        normalize_alnum) začína normalizovaným prefixom niektorého z kódov
        v self.obdobie_subory — rovnaká logika ako najdi_subor_podla_prefixu().

        Číslované piesne (stem zodpovedá r'^[0-9]{3}') sú tiež vylúčené,
        pretože sú dostupné cez hlavný combobox zoznamu piesní.
        """
        priečinok = self.song_folder_path
        if not priečinok.is_dir():
            return []

        # Predpočítame normalizované prefixy všetkých zaradených kódov
        _zaradene_prefixy: set[str] = set()
        for kody in self.obdobie_subory.values():
            if kody is None:
                continue
            for kod in kody:
                _zaradene_prefixy.add(self.normalize_alnum(kod))

        nezaradene: list[str] = []
        try:
            for f in sorted(priečinok.glob("*.txt"), key=lambda x: x.name.lower()):
                if not f.is_file():
                    continue
                stem = f.stem
                norm = self.normalize_alnum(stem)

                # Vylúčiť číslované piesne (001, 002a, …)
                if re.match(r"^[0-9]{3}", norm):
                    continue

                # Vylúčiť ak stem začína niektorým zaradeným prefixom
                if any(re.match(r"^" + re.escape(p) + r"(\d|$)", norm) for p in _zaradene_prefixy):
                    continue

                nezaradene.append(stem)
        except Exception as e:
            log_exception("_ziskaj_nezaradene_subory: chyba pri čítaní priečinka", e)

        return nezaradene

    def nacitat_podla_menu(self, vybrany_subor):
        """
        Načíta pieseň na základe výberu z menu (kalendára) a aktualizuje UI.
        """
        try:
            # Pôvodný debug print nahradený logovaním
            # log_exception tu môžeme použiť aj na informačné správy, ak funkciu upravíte, 
            # alebo použijeme klasický logovací mechanizmus.
            self.subor_var.set(vybrany_subor)

            # 1. Reset vstupných prvkov
            try:
                self.manual_entry.delete(0, tk.END)
                if self.song_combobox is not None:
                    self.song_combobox.current(0)
            except Exception as e:
                log_exception("nacitat_podla_menu: chyba pri resete vstupov", e)

            # 2. Vypnutie aktívnej projekcie (ak beží)
            if getattr(self, "is_text_visible", False):
                try:
                    self.vypni_projekciu()
                except Exception as e:
                    log_exception("nacitat_podla_menu: chyba pri vypínaní projekcie", e)

            if vybrany_subor:
                # 3. Získanie čistého názvu súboru
                try:
                    hladany_full = self.najdi_subor_podla_prefixu(vybrany_subor)
                    nazov_bez_ext = Path(hladany_full).stem if hladany_full else vybrany_subor
                except Exception as e:
                    log_exception("nacitat_podla_menu: chyba pri spracovaní názvu súboru", e)
                    nazov_bez_ext = vybrany_subor

                # 4. Aktualizácia popisu (Žalm pre...)
                try:
                    popis = next(
                        (v for k, v in self.popisy_suborov.items() if k.lower() == nazov_bez_ext.lower()),
                        ""
                    )
                    if popis:
                        # Žalmové súbory majú kód v popisy_suborov; ostatné (modlitby a iné) nie.
                        self.popis_label.config(text=f"Žalmy pre {popis}")
                    else:
                        self.popis_label.config(text=nazov_bez_ext)
                except Exception as e:
                    log_exception("nacitat_podla_menu: chyba pri hľadaní popisu", e)

                # 5. Samotné načítanie textu piesne
                try:
                    self.nacitat_piesne(nazov_suboru=nazov_bez_ext)
                except Exception as e:
                    log_exception(f"nacitat_podla_menu: kritická chyba načítania textu ({nazov_bez_ext})", e)

                # 6. Spracovanie liturgického direktória
                self._aktualizuj_direktorium_pre_subor(nazov_bez_ext)

            else:
                # Ak nie je vybraný súbor, vyčistíme všetko
                self.popis_label.config(text="")
                self.direktorium_label.config(text="", fg=DIREKTORIUM_LABEL_FG)

            # 7. Vrátenie fokusu do vyhľadávacieho poľa
            try:
                self._suppress_vymazat = True
                self.master.after_idle(lambda: self.manual_entry.focus_set())
                self.master.after(150, lambda: setattr(self, "_suppress_vymazat", False))
            except Exception as e:
                log_exception("nacitat_podla_menu: chyba pri obnove fokusu", e)

        except Exception as e:
            log_exception("nacitat_podla_menu: hlavná chyba metódy", e)        
        
    
    def nacitat_z_okna_pomocok(self, kod):
        """Načíta pieseň alebo slávenie po dvojkliku v okne Direktórium alebo Slávenia."""
        # 1. Zrušíme výber v comboboxe a bočnom menu
        if self.song_combobox is not None:
            self.song_combobox.current(0)
        self.subor_var.set("—")
        
        # 2. Vložíme kód do hlavného vyhľadávacieho poľa
        self.manual_entry.delete(0, tk.END)
        self.manual_entry.insert(0, format_cislo_piesne_pre_vstup(kod))
        
        # 3. Načítame pieseň tak, akoby to používateľ zadal ručne
        self.skus_manualne_nacitanie()

    def _obnov_focus_manual_entry_bez_vymazania(self):
        """Vráti fokus do manual_entry po zatvorení okna Direktórium/Slávenia.

        Samotný `focus_set()` vyvolá na manual_entry udalosť <FocusIn>, na
        ktorú je naviazaná `vymazat_subor_menu` – tá by inak hneď vynulovala
        subor_var na "—" a vyčistila popis_label aj direktorium_label, ktoré
        sme práve pred zatvorením okna korektne nastavili (napr. "Žalmy
        pre..." alebo odporúčanie z direktória). Rovnako ako v
        `nacitat_podla_menu` preto na chvíľu potlačíme `vymazat_subor_menu`
        cez `_suppress_vymazat`.
        """
        if not self.master.winfo_exists():
            return
        self._suppress_vymazat = True
        try:
            self.manual_entry.focus_set()
        finally:
            self.master.after(150, lambda: setattr(self, "_suppress_vymazat", False))
    
    def _aktualizuj_direktorium_pre_subor(self, nazov_bez_ext):
        """
        Spoločná pomocná metóda – aktualizuje direktorium_label podľa kódu súboru.
        Volá sa z nacitat_podla_menu, auto_nacitanie_suboru aj skus_manualne_nacitanie.
        """
        try:
            note, piesne = self.nacitaj_piesne_z_direktoria_pre_subor(nazov_bez_ext)
            if piesne:
                odporucane_text = "\n".join(
                    [f"  \u2022 {sekcia}: {text}" for sekcia, text in piesne.items() if text]
                )
                hlavicka = f"Odporúčané piesne: {note}" if note else "  Odporúčané piesne:"
                self.direktorium_label.config(
                    text=f"{hlavicka}\n{odporucane_text}",
                    fg=DIREKTORIUM_LABEL_FG
                )
            elif note:
                self.direktorium_label.config(
                    text=f"Odporúčané piesne:\n{note}",
                    fg=DIREKTORIUM_LABEL_FG
                )
            else:
                self.direktorium_label.config(text="", fg=DIREKTORIUM_LABEL_FG)
        except Exception as e:
            log_exception("_aktualizuj_direktorium_pre_subor: chyba", e)
            self.direktorium_label.config(text="", fg=DIREKTORIUM_LABEL_FG)


    def nacitaj_piesne_z_direktoria_pre_subor(self, kod):
        """
        Načíta odporúčané piesne z DIREKTORIUM_DATA podľa kódu (napr. '2AD', '25C1', '25C2').
        Vracia tuple: (poznámka, slovník s piesňami) alebo (None, {}).
        """
        try:
            # Robustná normalizácia: ak posledný znak je číslica, odstrániť
            if kod and kod[-1].isdigit():
                kod = kod[:-1]

            kod_upper = kod.upper() if kod else ""
            if kod_upper == "1C":
                return (
                    "DIREKTÓRIUM nemá samostatné JKS‑odporúčania pre "
                    "1. cezročnú nedeľu, lebo ju nahrádza sviatok Krstu Pána.",
                    {}
                )

            liturgicky_den = DIREKTORIUM_MAP.get(kod_upper)
            if not liturgicky_den:
                # Toto nemusí byť kritická chyba, ale je dobré o nej vedieť v logu
                return None, {}

            for obdobie, dni in DIREKTORIUM_DATA.items():
                for den in dni:
                    if den.get("den") == liturgicky_den:
                        stupen = STUPEN_OVERRIDE.get(kod.upper()) or den.get("stupen", "")
                        return (
                            den.get("poznamka", ""),
                            {
                                **({"Stupeň": stupen} if stupen else {}),
                                "Úvod": den.get("uvodny", ""),
                                "Ofer.": den.get("ofertorium", ""),
                                "Prijím.": den.get("prijimanie", ""),
                                "Kant.": den.get("kant", ""),
                                "Záver": den.get("po_omsi", "")
                            }
                        )
        except Exception as e:
            log_exception(f"Chyba pri hľadaní liturgického dňa pre kód: {kod}", e)

        return None, {}      
        
                    
    def nacitat_piesne(self, nazov_suboru, zobrazit_na_projekcii=False):
        """Načítava obsah textového súboru piesne a pripravuje strofy na zobrazenie."""
        self.aktualne_cislo_piesne = nazov_suboru
        predchadzajuci_nazov = getattr(self, "nazov_piesne", None)
        zachovat_index = predchadzajuci_nazov == nazov_suboru
        povodny_index = self.aktualny_index_strofa if zachovat_index else 0

        # --- Pathlib: Prístup k priečinku ---
        song_folder = self.song_folder_path
        try:
            # Získame generátor a hneď ho deterministicky zoradíme
            vsetky_subory = sorted(
                song_folder.glob("*.txt"),
                key=lambda x: x.name.lower()
            )
        except Exception as e:
            log_exception("Chyba pri prístupe k priečinku s piesňami", e)
            return

        # Deterministické vyhľadanie súboru podľa prefixu aj číselnej logiky
        # (napr. 1 -> 001.txt, 001a -> 001a.txt).
        try:
            najdeny_subor = self.najdi_subor_podla_prefixu(nazov_suboru)
        except Exception as e:
            log_exception("Chyba pri vyhľadávaní súboru piesne", e)
            najdeny_subor = None

        if najdeny_subor:
            hladany_subor_cesta = song_folder / najdeny_subor
        else:
            prefix = nazov_suboru.lower()
            hladany_subor_cesta = next(
                (p for p in vsetky_subory if p.name.lower().startswith(prefix)),
                None
            )

        if not hladany_subor_cesta:
            return

        self.aktualny_subor_cesta = hladany_subor_cesta

        obsah = ""
        # --- Pathlib: Načítanie obsahu so zjednoteným kódovaním ---
        try:
            obsah = hladany_subor_cesta.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, UnicodeError):
            try:
                obsah = hladany_subor_cesta.read_text(encoding="cp1250")
            except Exception as e:
                log_exception(f"Kódovanie súboru {hladany_subor_cesta.name} nie je podporované", e)
                return
        except Exception as e:
            log_exception(f"Kritická chyba pri otváraní súboru {hladany_subor_cesta.name}", e)
            return

        # Spracovanie strof
        nove_strofy = [s.strip() for s in re.split(r'\n\s*\n', obsah) if s.strip()]
        self.aktualne_strofy = [""] + nove_strofy

        if zachovat_index and 0 <= povodny_index < len(self.aktualne_strofy):
            self.aktualny_index_strofa = povodny_index
        else:
            self.aktualny_index_strofa = 0

        self.nazov_piesne = nazov_suboru

        try:
            self.aktualizuj_popis(nazov_suboru)
        except Exception as e:
            log_exception("Chyba pri aktualizácii popisu piesne", e)

        # Aktualizácia Text widgetu s náhľadom
        try:
            self.obsah_suboru_text.config(state=tk.NORMAL)
            self.obsah_suboru_text.delete("1.0", tk.END)
            self.obsah_suboru_text.insert(tk.END, obsah)
            self.obsah_suboru_text.tag_remove("highlight", "1.0", tk.END)
            self.obsah_suboru_text.config(state=tk.DISABLED)
        except Exception as e:
            log_exception("Chyba pri vkladaní textu do náhľadového okna", e)
            try:
                self.obsah_suboru_text.config(state=tk.DISABLED)
            except Exception as e2:
                log_exception("Nepodarilo sa uzamknúť obsah_suboru_text po chybe", e2)

        # Aktualizácia Labelov a Projekcie
        try:
            self._update_nazov_label()
        except Exception as e:
            log_exception("Chyba pri aktualizácii názvu v hlavnom okne", e)

        self.is_text_visible = zobrazit_na_projekcii

        try:
            self.zobraz_aktualnu_strofu()
        except Exception as e:
            log_exception("Chyba pri odosielaní strofy na projekciu", e)

        # Indikátor a reset projekčného okna
        if zobrazit_na_projekcii:
            self.set_projection_indicator(True)
        else:
            try:
                if self.projection_window is not None:
                    self.projection_window.update_text("")
                    self.projection_window.update_title(name="", current=0, total=None)
                self.set_projection_indicator(False)
            except Exception as e:
                log_exception("Chyba pri resetovaní projekčného okna", e)

        # Označenie riadku v náhľade
        try:
            self.oznac_aktualnu_strofu_v_obsahu()
        except Exception as e:
            log_exception("Chyba pri zvýrazňovaní strofy v náhľade", e)                              
   
       
    def vypocitaj_velkost_pisma_pre_strofu(self, text):
        """
        Dynamické škálovanie písma pre horný panel (strofa_label).

        Používa estimate_text_height() – rovnaký princíp ako update_live_preview():
        iteratívne znižuje font_size, kým sa text zmestí do dostupnej výšky widgetu.

        Fallback na heuristiku ak widget ešte nemá reálne rozmery (inicializácia).
        """

        # Nultá strofa = len číslo piesne → fixná veľkosť
        if self.aktualny_index_strofa == 0:
            return 30

        font_family: str = FONT_NAME or "Arial"

        # ------------------------------------------------------------------
        # 1) Reálne rozmery widgetu
        # ------------------------------------------------------------------
        try:
            w = self.strofa_label.winfo_width()
            h = self.strofa_label.winfo_height()
        except tk.TclError:
            w, h = 0, 0

        # Ak widget ešte nie je vykreslený → heuristický fallback
        if w <= 20 or h <= 20:
            riadky = text.count("\n") + 1
            if riadky <= 1: return 38
            if riadky == 2: return 32
            if riadky == 3: return 26
            if riadky == 4: return 22
            return max(STROFA_FONT_MIN, 18)

        max_w = int(w * 0.92)  # dynamicky 8% padding miesto pevných 60px
        max_h = int(h * 0.85)  # dynamicky 15% padding miesto pevných 30px

        # ------------------------------------------------------------------
        # 2) Iteratívne zmenšovanie – rovnaký vzor ako v update_live_preview
        # ------------------------------------------------------------------
        current_size = STROFA_FONT_INIT
        loop_limit   = STROFA_LOOP_LIMIT

        # Persistent font objekt uložený ako self._strofa_test_font – vytvorí sa raz
        # a ďalšie volania iba reconfigurujú family/size. Predíde sa tým rastu
        # internej Tk tabuľky fontov pri každom volaní tejto metódy.
        test_font = getattr(self, "_strofa_test_font", None)
        if test_font is None:
            test_font = tkfont.Font(family=font_family, size=current_size, weight="bold")
            self._strofa_test_font = test_font
        else:
            test_font.configure(family=font_family, size=current_size)

        while current_size > STROFA_FONT_MIN and loop_limit > 0:
            test_font.configure(size=current_size)
            needed_h  = estimate_text_height(text, test_font, max_w)
            if needed_h <= max_h:
                break
            current_size -= 1
            loop_limit   -= 1

        return current_size
        

    def zobraz_aktualnu_strofu(self):
        """Zobrazí aktuálnu strofu + aktualizuje projekciu + LIVE PREVIEW."""

        # ------------------------------------------------------------
        # 0) Normalizácia čísla piesne (DRY)
        # ------------------------------------------------------------
        raw_cislo = self.aktualne_cislo_piesne or self.nazov_piesne or ""
        cislo_display = str(raw_cislo)
        if cislo_display.isdigit():
            cislo_display = str(int(cislo_display))

        # ------------------------------------------------------------
        # 1) Ak nemáme žiadne strofy → vymaž všetko
        # ------------------------------------------------------------
        if not self.aktualne_strofy:
            try:
                self.strofa_label.config(state=tk.NORMAL)
                self.strofa_label.delete("1.0", tk.END)
                self.strofa_label.config(state=tk.DISABLED)
            except Exception as e:
                log_exception("zobraz_aktualnu_strofu: vymazanie strofa_label", e)

            try:
                self.projection_window.update_title("", None, None)
            except Exception as e:
                log_exception("zobraz_aktualnu_strofu: update_title prázdny", e)

            if self.is_text_visible:
                try:
                    self.projection_window.update_text("")
                except Exception as e:
                    log_exception("zobraz_aktualnu_strofu: update_text prázdny", e)

                try:
                    if self.live_preview_label is not None:
                        self.live_preview_label.config(text="")
                except Exception as e:
                    log_exception("zobraz_aktualnu_strofu: live_preview clear", e)

            return

        # ------------------------------------------------------------
        # 2) NULTÁ STROFA – zobraz len číslo piesne
        # ------------------------------------------------------------
        if self.aktualny_index_strofa == 0:

            # Ovládací panel rieši oznac_aktualnu_strofu_v_obsahu()
            try:
                self.oznac_aktualnu_strofu_v_obsahu()
            except Exception as e:
                log_exception("zobraz_aktualnu_strofu: oznac_aktualnu_strofu failed", e)

            # Projekcia
            if self.is_text_visible:
                try:
                    self.projection_window.update_title(
                        "",
                        current=0,
                        total=len(self.aktualne_strofy) - 1
                    )
                    self.projection_window.update_text(cislo_display)

                except Exception as e:
                    log_exception("zobraz_aktualnu_strofu: nultá strofa projekcia", e)

                # LIVE PREVIEW
                try:
                    if self.live_preview_label is not None:
                        self.live_preview_label.config(text=cislo_display)
                        self.update_live_preview(cislo_display)
                except Exception as e:
                    log_exception("zobraz_aktualnu_strofu: nultá strofa live_preview", e)

            return

        # ------------------------------------------------------------
        # 3) REÁLNE STROFY (index >= 1)
        # ------------------------------------------------------------
        try:
            strofa_raw = self.aktualne_strofy[self.aktualny_index_strofa]

            # typografická úprava
            strofa_typo = self.format_typography(strofa_raw)

            # Ovládací panel rieši oznac_aktualnu_strofu_v_obsahu()
            try:
                self.oznac_aktualnu_strofu_v_obsahu()
            except Exception as e:
                log_exception("zobraz_aktualnu_strofu: oznacovanie obsahu", e)

            # Projekcia
            if self.is_text_visible:
                try:
                    self.projection_window.update_title(
                        cislo_display,
                        current=self.aktualny_index_strofa,
                        total=len(self.aktualne_strofy) - 1
                    )
                    self.projection_window.update_text(strofa_typo)

                except Exception as e:
                    log_exception("zobraz_aktualnu_strofu: projekcia update", e)

                # LIVE PREVIEW
                try:
                    update_fn = getattr(self, "update_live_preview", None)
                    if callable(update_fn):
                        update_fn(strofa_typo)
                except Exception as e:
                    log_exception("zobraz_aktualnu_strofu: live_preview update", e)

        except Exception as e:
            log_exception("zobraz_aktualnu_strofu: kritická chyba spracovania strofy", e)   
                                                 
                  
    def nastavit_globalne_skratky(self):

        # šípky – iba na hlavnom okne (nesmú interferovať s inými widgetmi)
        self.master.bind('<Right>', self.klavesa_vpravo)
        self.master.bind('<Left>', self.klavesa_vlavo)

        # plus/minus - bind_all zachytava udalosti pre celu aplikaciu vratane
        # hlavneho okna. Handler ignoruje editovatelne widgety okrem hlavneho
        # vstupu a zoznamu piesni, kde + a - zamerne posuvaju aktualnu strofu.
        # Dvojite bind (bind + bind_all pre ten isty widget) by sposobilo
        # dvojite posunutie strofy pri kazdom stlaceni.
        self.master.bind_all("<plus>", self.klavesa_plus)
        self.master.bind_all("<minus>", self.klavesa_minus)
        self.master.bind_all("<KP_Add>", self.klavesa_plus)
        self.master.bind_all("<KP_Subtract>", self.klavesa_minus)
        self.master.bind_all("=", self.klavesa_plus)
        self.master.bind_all("-", self.klavesa_minus)

        # Backspace – musí byť KeyRelease
        self.master.bind_all("<KeyRelease-BackSpace>", self._global_backspace_handler)

        # ďalšie skratky
        self.master.bind('<Escape>', self.potvrdit_ukoncenie)
        self.master.bind('c', self.clear_screen)   
        
    
    def _global_backspace_handler(self, event):
        """
        Spracuje stlačenie klávesy Backspace kdekoľvek v aplikácii.
        """
        # POZNÁMKA (Zámerné správanie): 
        # Backspace slúži ako rýchla skratka na okamžité vypnutie projekcie.
        # Je to nastavené tak, aby sa projekcia vypla aj v prípade, 
        # že používateľ práve píše alebo maže text vo vstupnom poli. 
        # Nejde o chybu (bug), ale o požadovanú funkcionalitu (UX).
        
        # ak je projekcia zapnutá → vypni ju
        
        if getattr(self, "is_text_visible", False):
            self.vypni_projekciu()     
                                                                                                                 
    # def manual_entry_enter volá vždy vtedy, keď je na manual_entry widgete naviazaný bind na kláves Enter.
    def manual_entry_enter(self, event=None):
        nazov = self.manual_entry.get().strip()
        if not nazov:
            return self.enter_aktivuj_projekciu(event)

        clean = self.normalize_alnum(nazov)
        if not clean:
            return "break"

        hladany_full = self.najdi_subor_podla_prefixu(clean)
        if not hladany_full:
            messagebox.showinfo(
                "Kinak: Nenájdené",
                f"Súbor „{nazov}“ neexistuje.\n\n"
                "Môžete ho doplniť alebo vytvoriť a pridať do priečinka piesní."
            )
            return "break"

        nazov_bez_ext = Path(hladany_full).stem

        # ------------------------------------------------------------
        # Projekcia je ZAPNUTÁ → vypnúť
        # ------------------------------------------------------------
        if self.is_text_visible:
            self.vypni_projekciu()
            return "break"

        # ------------------------------------------------------------
        # Projekcia je VYPNUTÁ → načítať pieseň + zapnúť projekciu
        # ------------------------------------------------------------
        self.nacitat_piesne(nazov_suboru=nazov_bez_ext, zobrazit_na_projekcii=True)

        # zapnúť projekciu (umiestni Live Preview + nastaví indikátor)
        self.zapni_projekciu()
        self.aktualizuj_popis(nazov_bez_ext)
        self._aktualizuj_direktorium_pre_subor(nazov_bez_ext)

        return "break" 
    

    # ==========================================================
    # Pomocné metódy pre UI (Továreň na prvky nastavení) pre OKNO NASTAVENÍ
    # ==========================================================

    def _vytvor_sekciu(self, rodic, nadpis, popis):
        """Vytvorí LabelFrame s nadpisom a krátkym vysvetlivkovým textom."""
        frame = tk.LabelFrame(rodic, text=f" {nadpis} ", padx=10, pady=8, 
                            font=(self.font_family, 10, "bold"), fg="#333333")
        frame.pack(fill=tk.X, padx=15, pady=8)

        if popis:
            lbl_popis = tk.Label(frame, text=popis, font=(self.font_family, 9, "italic"),
                                fg="#666666", wraplength=550, justify=tk.LEFT)
            lbl_popis.pack(anchor="w", pady=(0, 5))
        
        return frame

    def _pridaj_nastavenie_slider(self, rodic, nadpis, popis, premenna, od, do, rozlisenie=1):
        """Vytvorí sekciu so sliderom (Scale) na celú šírku."""
        sekcia = self._vytvor_sekciu(rodic, nadpis, popis)        
        
        slider = tk.Scale(
            sekcia, 
            from_=od, 
            to=do, 
            variable=premenna, 
            resolution=rozlisenie, 
            orient=tk.HORIZONTAL,
            font=(self.font_family, 11),
            highlightthickness=0  # Odstráni biely obrys pre čistejší vzhľad
        )
        
        # fill=tk.X zabezpečí roztiahnutie po horizontálnej osi
        slider.pack(fill=tk.X, expand=True, padx=5, pady=(0, 5))
        
        # Automatické ukladanie pri pustení tlačidla myši
        slider.bind("<ButtonRelease-1>", lambda e: self.ulozit_nastavenia(aktualizovat_label=False))
        
        return sekcia

    def _pridaj_nastavenie_check(self, rodic, nadpis, popis, premenna, text_check="Zapnuté / Povolené"):
        """Vytvorí sekciu s potvrdzovacím políčkom (Checkbutton)."""
        sekcia = self._vytvor_sekciu(rodic, nadpis, popis)
        chk = tk.Checkbutton(sekcia, text=text_check, variable=premenna, 
                           command=self.ulozit_nastavenia, font=(self.font_family, 11))
        chk.pack(anchor="w")
        return sekcia

    # ==========================================================
    # HLAVNÁ METÓDA OKNA NASTAVENÍ
    # ==========================================================

    def vytvorit_nastavenia_okno(self):
        """Vytvorí konfiguračné okno so všetkými nastaveniami a scrollbarom."""
        settings_window = tk.Toplevel(self.master)
        self.settings_window = settings_window
        settings_window.title("Nastavenia")
        settings_window.protocol("WM_DELETE_WINDOW", self.zatvorit_nastavenia)
        
        # Klúčové mapovanie kláves a fokus
        settings_window.bind("<Escape>", lambda e: self.zatvorit_nastavenia())        
        settings_window.after(
            50,
            lambda: settings_window.winfo_exists() and settings_window.focus_force()
        )

        # Nastavenie geometrie (vycentrovanie)
        saved_w = int(self.settings_window_width)
        saved_h = int(self.settings_window_height)
        window_width  = saved_w if saved_w >= 400 else 620
        window_height = saved_h if saved_h >= 300 else 660
        screen_width = settings_window.winfo_screenwidth()
        screen_height = settings_window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = max(0, (screen_height - window_height) // 2 - 40)
        settings_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        settings_window.withdraw() # Skryjeme kým sa nevykreslí

        # Sledovanie zmien veľkosti okna Nastavenia (s debounce 500ms)
        def _uloz_geometriu_nastaveni(event):
            if event.widget is not self.settings_window:
                return

            def zapis_geometrie():
                if self.settings_window and self.settings_window.winfo_exists():
                    self.settings_window_width = self.settings_window.winfo_width()
                    self.settings_window_height = self.settings_window.winfo_height()
                    self.ulozit_nastavenia(aktualizovat_label=False)

            self._naplanuj_debounced_zapis(
                "_settings_geom_after_id", zapis_geometrie, "_uloz_geometriu_nastaveni"
            )

        settings_window.bind('<Configure>', _uloz_geometriu_nastaveni)

        # --- ZÁLOŽKY: ZÁKLADNÉ / POKROČILÉ ---
        container = tk.Frame(settings_window)
        container.pack(fill=tk.BOTH, expand=True)

        style = ttk.Style()
        style.configure(
            "KinakSettings.TNotebook",
            tabmargins=(12, 8, 12, 0)
        )
        style.configure(
            "KinakSettings.TNotebook.Tab",
            font=(self.font_family, 12, "bold"),
            padding=(32, 12)
        )
        style.map(
            "KinakSettings.TNotebook.Tab",
            foreground=[
                ("selected", "#000000"),
                ("!selected", "#333333")
            ],
            background=[
                ("selected", "#f2f2f2"),
                ("!selected", "#d8d8d8")
            ],
            expand=[
                ("selected", (2, 2, 2, 0))
            ]
        )

        notebook = ttk.Notebook(container, style="KinakSettings.TNotebook")
        notebook.pack(fill=tk.BOTH, expand=True)

        def vytvor_scroll_tab(nazov):
            tab = tk.Frame(notebook)
            notebook.add(tab, text=f"   {nazov}   ")

            canvas = tk.Canvas(tab, highlightthickness=0)
            scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas)

            scrollable_frame.bind(
                "<Configure>",
                lambda e, c=canvas: c.configure(scrollregion=c.bbox("all"))
            )

            canvas_frame = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

            def _configure_canvas(event, c=canvas, cf=canvas_frame):
                c.itemconfig(cf, width=event.width)

            canvas.bind("<Configure>", _configure_canvas)
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            def _on_mousewheel(event, c=canvas):
                c.yview_scroll(int(-1 * (event.delta / 120)), "units")

            canvas.bind("<Enter>", lambda e, c=canvas: c.bind_all("<MouseWheel>", _on_mousewheel))
            canvas.bind("<Leave>", lambda e, c=canvas: c.unbind_all("<MouseWheel>"))

            return scrollable_frame

        zakladne_frame = vytvor_scroll_tab("Základné")
        pokrocile_frame = vytvor_scroll_tab("Pokročilé")

        # --- ŠTÝL ---
        style.configure("Settings.TLabelframe", padding=10)
        
        # Pomocná funkcia pre vytváranie sekcií (LabelFrame)
        def vytvor_sekciu(parent, text):
            f = tk.LabelFrame(parent, text=text, padx=10, pady=10, 
                             font=(self.font_family, 12, "bold"), fg="#333333")
            f.pack(fill=tk.X, padx=15, pady=8)
            return f

        def vytvor_popis(parent, text, color="#555555"):
            l = tk.Label(parent, text=text, font=(self.font_family, 10, "italic"),
                         fg=color, wraplength=550, justify=tk.LEFT)
            l.pack(anchor="w", pady=(0, 5))
            return l

        # 1. INFO PANEL
        frame_info = vytvor_sekciu(zakladne_frame, "Informácia")
        vytvor_popis(frame_info, "Veľkosť písma sa automaticky prispôsobuje veľkosti obrazovky.")

        # 2. VEĽKOSŤ PÍSMA
        frame_font = vytvor_sekciu(zakladne_frame, "Základná veľkosť písma")
        vytvor_popis(
            frame_font,
            "Nastavuje maximálnu povolenú veľkosť písma. Ak nastavíš napr. 105, "
            "písmo nebude nikdy väčšie, ale pri dlhom texte sa automaticky zmenší."
        )

        # IntVar musí dostať istý int
        if not hasattr(self, "font_size_var"):
            self.font_size_var = tk.IntVar(value=int(self.font_size))

        font_size_slider = tk.Scale(
            frame_font,
            variable=self.font_size_var,
            from_=20,
            to=MAX_FONT_SIZE,
            orient=tk.HORIZONTAL,
            font=(self.font_family, 11),
            command=lambda v: None
        )
        font_size_slider.pack(fill=tk.X, expand=True, padx=5, pady=5)

        font_size_slider.bind(
            "<ButtonRelease-1>",
            lambda e: self.ulozit_nastavenia(aktualizovat_label=False)
        )

        vytvor_popis(
            frame_font,
            "Odporúčané: Monitor (< 100cm) → cca 105 | TV/Projektor (> 100cm) → cca 75",
            "#0066cc"
        )
        
        # 3. FARBA TEXTU A OBDOBIA
        frame_color = vytvor_sekciu(zakladne_frame, "Farba textu")
        vytvor_popis(frame_color, "Výber liturgického obdobia automaticky nastaví farbu textu pri projekcii.")

        moznosti_obdobia = list(LITURGICKE_OBDOBIA.keys())
        self.obdobie_menu = tk.OptionMenu(
            frame_color, self.obdobie_var, *moznosti_obdobia,
            command=self.nastavit_farbu_pisma_podla_obdobia
        )
        self.obdobie_menu.config(font=(self.font_family, 11), width=25)
        self.obdobie_menu.pack(anchor="w", pady=(0, 10))

        radek_farba = tk.Frame(frame_color)
        radek_farba.pack(fill=tk.X)

        self.checkbox_vlastna_farba = tk.Checkbutton(
            radek_farba, text="Použiť vlastnú farbu", variable=self.pouzit_vlastnu_farbu,
            command=self.zmenit_rezim_farby, font=(self.font_family, 11)
        )
        self.checkbox_vlastna_farba.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(radek_farba, text="Vybrať farbu…", command=self.vybrat_vlastnu_farbu_textu).pack(side=tk.LEFT)

        # Indikátor farby (Zaoblený polygon)
        self.indikator_farby = tk.Canvas(radek_farba, width=40, height=30, highlightthickness=0)
        self.indikator_farby.pack(side=tk.LEFT, padx=10)
        
        r = 6
        points = [4+r, 4, 34-r, 4, 34, 4, 34, 4+r, 34, 26-r, 34, 26, 34-r, 26, 4+r, 26, 4, 26, 4, 26-r, 4, 4+r, 4, 4]
        self.indikator_farby_id = self.indikator_farby.create_polygon(
            points, smooth=True, fill=self.text_color_var.get(), outline="#444444", width=1
        )
        
        # 4. LITURGICKÝ ROK A / B / C
        frame_lit_rok_sekcia = vytvor_sekciu(pokrocile_frame, "Liturgický rok")
        vytvor_popis(frame_lit_rok_sekcia, "Liturgický cyklus (A, B, C) sa mení v programe Kinak automaticky každú Prvú adventnú nedeľu – začína sa nový liturgický rok.")

        if not hasattr(self, "liturgical_year_var"):
            self.liturgical_year_var = tk.StringVar(
                self.master,
                value=vypocitaj_liturgicky_rok()
            )

        frame_lit_rok = tk.Frame(frame_lit_rok_sekcia)
        frame_lit_rok.pack(anchor="w", pady=(4, 0))

        for rok in ("A", "B", "C"):
            tk.Radiobutton(
                frame_lit_rok,
                text=f"  {rok}  ",
                variable=self.liturgical_year_var,
                value=rok,
                font=(self.font_family, 13, "bold"),
                state=tk.DISABLED,          # hodnota je automatická – len zobrazenie
            ).pack(side=tk.LEFT, padx=4)

        
        # 5. PREDVOLENÝ FILTER (HLAVNÉ OKNO)
        frame_def_filter = vytvor_sekciu(zakladne_frame, "Predvolený filter v ovládaní")
        vytvor_popis(frame_def_filter, "Vyber filter, ktorý sa zobrazí v hlavnom okne po spustení aplikácie.")
        
        moznosti_subory = list(self.obdobie_subory.keys())
        self.default_filter_menu = tk.OptionMenu(frame_def_filter, self.default_filter_var, *moznosti_subory)
        self.default_filter_menu.config(font=(self.font_family, 11), width=25)
        self.default_filter_menu.pack(anchor="w")
        
        # Trace teraz ukladá nastavenia a zároveň okamžite aktualizuje zoznam piesní
        self.default_filter_var.trace_add("write", lambda *a: [
            self.ulozit_nastavenia(), 
            self.filtrovat_subory(self.filter_var.get())
        ])              
        
        # 6. BEŽNÉ A POKROČILÉ PREPÍNAČE ZOBRAZENIA
        def vytvor_check(parent, text, var):
            cb = tk.Checkbutton(parent, text=text, variable=var, font=(self.font_family, 11), 
                                command=self.ulozit_nastavenia, pady=2)
            cb.pack(anchor="w")
            return cb

        frame_basic_view = vytvor_sekciu(zakladne_frame, "Náhľad v ovládaní")

        self.checkbox_live_preview = tk.Checkbutton(
            frame_basic_view,
            text="Zobraziť náhľad projekcie (Live Preview)",
            variable=self.zobrazovat_live_preview_var,
            font=(self.font_family, 11),
            command=lambda: [self.ulozit_nastavenia(), self.update_live_preview(getattr(self, 'posledny_text', ""))],
            pady=2
        )
        self.checkbox_live_preview.pack(anchor="w")

        vytvor_popis(
            frame_basic_view,
            "Náhľad pomáha vtedy, keď premietajúci nevidí priamo na projektor alebo televízor.",
            "#0066cc"
        )

        frame_checks = vytvor_sekciu(pokrocile_frame, "Liturgické pomôcky a znaky")

        # 1. DIREKTÓRIUM:
        self.checkbox_direktorium = tk.Checkbutton(
            frame_checks, 
            text="Zobraziť odporúčané piesne z JKS pod rozbaľovacím filtrom pri výbere súboru", 
            variable=self.zobrazit_direktorium_var, 
            font=(self.font_family, 11),            
            command=lambda: [self.ulozit_nastavenia(), self.aktualizovat_direktorium_label(), self.filtrovat_subory(self.filter_var.get())],
            pady=2
        )
        self.checkbox_direktorium.pack(anchor="w")

        self.checkbox_specialne_znaky = vytvor_check(frame_checks, "Zobraziť špeciálne znaky JKS (·, _) v projekcii", self.zobrazovat_specialne_znaky_var)

        self.checkbox_znaky_chorov = vytvor_check(frame_checks, "Zobraziť znaky [L] / [P] pre striedanie chórov pri vešperách v projekcii", self.zobrazovat_znaky_chorov_var)

        vytvor_popis(
            frame_checks,
            "V hlavnom ovládacom okne zostávajú špeciálne znaky a znaky [L] / [P] "
            "vždy viditeľné, aby sa premietajúci vedel ľahko orientovať. "
            "Prepínače ovplyvňujú iba zobrazenie v projekcii.",
            "#0066cc"
        )

        
        self.checkbox_statusbar_skratka_zalmu = vytvor_check(
            frame_checks,
            "Zobraziť v stavovom riadku skratku žalmu podľa liturgického obdobia",
            self.statusbar_skratka_zalmu_var
        )       
        
        
        self.checkbox_statusbar_zaltara = vytvor_check(
            frame_checks,
            "Zobraziť v stavovom riadku aktuálny týždeň žaltára v breviári",
            self.statusbar_tyzden_zaltara_var
        )
                

        # 7. RÝCHLOSŤ PRECHODU
        frame_fade = vytvor_sekciu(zakladne_frame, "Rýchlosť prechodu textu")
        vytvor_popis(
            frame_fade,
            "Určuje, ako rýchlo sa nová obrazovka (strofa) rozjasní z čiernej."
        )
        self.fade_speed_combo = ttk.Combobox(
            frame_fade, textvariable=self.fade_speed_var,
            values=["veľmi pomalé", "pomalé", "stredné", "mierne stredné", "mierne rýchle", "rýchle", "vypnuté"],
            state="readonly", font=(self.font_family, 11), width=20
        )
        self.fade_speed_combo.pack(anchor="w", pady=5)
        self.fade_speed_combo.bind("<<ComboboxSelected>>", lambda e: self.ulozit_nastavenia())

        # 8. UMIESTNENIE SÚBOROV
        frame_folder = vytvor_sekciu(zakladne_frame, "Umiestnenie súborov")

        self.folder_label = tk.Label(
            frame_folder,
            text=str(self.song_folder_path),   
            wraplength=450,
            font=(self.font_family, 10),
            bg="#f9f9f9",
            anchor="w",
            justify=tk.LEFT,
            relief="sunken",
            padx=5,
            pady=5
        )
        self.folder_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        ttk.Button(
            frame_folder,
            text="Zmeniť…",
            command=self.zmenit_priecinok_piesni
        ).pack(side=tk.RIGHT)

        # 9. REZERVY
        frame_res = vytvor_sekciu(pokrocile_frame, "Globálna (vertikálna) rezerva")
        vytvor_popis(frame_res, "Vzdialenosť textu od horného a dolného okraja obrazovky – necháva priestor hore aj dole, aby text nebol nalepený na okraje. Vyššia hodnota = menší text.")
        
        safe_font_name: str = FONT_NAME or "Arial"

        # Slider upravený na celú šírku (odstránený length, pridaný fill=tk.X)
        self.slider_res_vert = tk.Scale(
            frame_res,
            variable=self.reserved_vertical_var,
            from_=0.10,
            to=0.40,
            resolution=0.01,
            orient=tk.HORIZONTAL,
            font=(safe_font_name, 11),
            highlightthickness=0
        )
        self.slider_res_vert.pack(fill=tk.X, expand=True, padx=5, pady=5)

        # Uložiť až po pustení myši
        self.slider_res_vert.bind(
            "<ButtonRelease-1>",
            lambda e: self.ulozit_nastavenia()
        )

        frame_margin = vytvor_sekciu(pokrocile_frame, "Spodná rezerva (Overscan)")
        vytvor_popis(frame_margin, "Posunie celý text vyššie (ak obrazovka orezáva spodok).")
        
        def validate_num(P):
            return P == "" or (P.isdigit() and 0 <= int(P) <= 400)
        vcmd = (self.settings_window.register(validate_num), "%P")

        # Rámček, ktorý drží všetky prvky v jednom riadku
        spin_frame = tk.Frame(frame_margin)
        spin_frame.pack(fill=tk.X, pady=5)

        # 1. Label (vľavo)
        tk.Label(
            spin_frame,
            text="px (0–400):",
            font=(safe_font_name, 11)
        ).pack(side=tk.LEFT)

        # 2. Spinbox (vľavo, hneď za labelom)
        tk.Spinbox(
            spin_frame, from_=0, to=400, textvariable=self.bottom_margin_var, 
            width=10, font=(self.font_family, 11), validate="key", 
            validatecommand=vcmd, command=self.ulozit_nastavenia
        ).pack(side=tk.LEFT, padx=5)

        # 3. Tlačidlo (vpravo - teraz je v tom istom ráme ako spinbox)
        ttk.Button(
            spin_frame, text="Viac o rezervách", 
            command=self.zobraz_info_rezervy
        ).pack(side=tk.RIGHT)

        # 9b. DIAGNOSTIKA
        frame_diag = vytvor_sekciu(pokrocile_frame, "Diagnostika")
        vytvor_popis(
            frame_diag,
            "Keď je diagnostika zapnutá, aplikácia priebežne zapisuje chyby a technické "
            "udalosti do log súboru nižšie (s automatickou rotáciou, aby súbor nerástol "
            "donekonečna). Pri probléme s aplikáciou tento súbor pomôže zistiť "
            "príčinu – v takom prípade je dobré mať diagnostiku zapnutú."
        )
        self.checkbox_diagnostika = vytvor_check(
            frame_diag,
            "Zapnúť diagnostické logovanie do súboru",
            self.diagnostika_povolena_var
        )
        tk.Label(
            frame_diag,
            text=f"Súbor: {LOG_PATH}",
            wraplength=450,
            font=(self.font_family, 9),
            fg="#555555",
            anchor="w",
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(4, 0))

        # 10. RESET
        frame_reset = vytvor_sekciu(pokrocile_frame, "Reset do pôvodného stavu")
        vytvor_popis(frame_reset, "Vráti všetky nastavenia na pôvodné hodnoty. Použite ho v prípade, že sa nastavenia „rozladia“ tak, že sa text zobrazí mimo obrazovky, je príliš orezaný, nečitateľný alebo sa vôbec nezobrazí kvôli nesprávnym nastaveniam.")
        ttk.Button(frame_reset, text="Obnoviť predvolené", command=self.obnovit_predvolene).pack(anchor="e")

        # FIXNÁ POZNÁMKA NA SPODKU (mimo scrollu)
        frame_restart = tk.Frame(self.settings_window, pady=10)
        frame_restart.pack(fill=tk.X)

        tk.Label(
            frame_restart,
            text="Niektoré nastavenia sa aplikujú až po reštarte aplikácie.",
            font=(safe_font_name, 10),
            fg="#aa0000"
        ).pack()

        # Dokončenie inicializácie
        self.aktualizovat_stav_tlacidla_farby()
        self.aktualizovat_vzhlad()
        self.settings_window.deiconify() 
        
    
    def aktualizovat_titulok_okna(self):
        """Aktualizuje titulok hlavného okna pri zmene liturgického roku v nastaveniach."""
        novy_rok = self.liturgical_year_var.get()
        
        if hasattr(self, "config"):
            self.config["liturgical_year"] = novy_rok
        
        try:
            if hasattr(self, "master") and self.master:
                self.aktualizovat_info_liturgickeho_roka(novy_rok)
        except Exception as e:
            print(f"Nepodarilo sa aktualizovať titulok: {e}")

        # --- AUTOMATICKÉ ULOŽENIE DO SÚBORU ---
        # Skúsime zavolať tvoju existujúcu ukladaciu funkciu
        if hasattr(self, "ulozit_nastavenia"):
            self.ulozit_nastavenia()
        elif hasattr(self, "ulozit_konfiguraciu"):
            self.ulozit_nastavenia()          
        
    def zobraz_info_rezervy(self):
        info_window = tk.Toplevel(self.settings_window)
        info_window.title("Viac o rezervách")
        info_window.geometry("550x660")
        info_window.transient(self.settings_window)  # drží sa nad hlavnými nastaveniami

        text = (
            "Na rôznych zariadeniach (projektor, TV, monitor) sa správanie overscanu aj rozlíšenie obrazovky líši, "
            "preto môže byť výsledná veľkosť písma odlišná.\n\n"
            "Veľkosť písma pri projekcii závisí od typu zobrazovacieho zariadenia a od nastavených rezerv "
            "v aplikácii Kinak (globálnej vertikálnej aj spodnej). Rezervy určujú, koľko miesta zostane okolo textu.\n\n"
            "Logika výpočtu\n\n"
            "Najprv sa odpočíta globálna vertikálna rezerva (rezerva v percentách výšky obrazovky). "
            "Týka sa celej výšky obrazovky, takže ide o „globálny“ parameter. "
            "Potom sa odpočíta pevná spodná rezerva (px). Ide o rezervu proti overscanu, aby spodné riadky neboli príliš nízko " 
            "alebo orezané na zariadeniach s overscanom.\n\n"              
            "Odporúčané hodnoty:\n\n"
            "   • Projektor:   vertikálna 0.30–0.35,     spodná 60–80 px\n"
            "   • TV (16:9):   vertikálna 0.25–0.28,     spodná 40–60 px\n"
            "   • Monitor:    vertikálna 0.20–0.25,     spodná 30–40 px\n\n"  
            "Tip podľa pomeru strán (16:9 je optimálny default)\n\n"                
            "   • 16:9   vertikálna 0.28,                spodná 40 px\n"
            "   • 21:9   vertikálna 0.20–0.25,       spodná 30–40 px\n\n"                    
            "TV/projektor: používajte natívny režim obrazu (Original/Just Scan/Full),\n"
            "bez Zoom alebo Stretch.\n\n"
            "Ak sa zobrazenie aj napriek tomu nehodí, strofu možno upraviť priamo v textovom súbore (napr. rozdeliť riadky). "
            "Namiesto 6 krátkych riadkov strofu rozdeliť na 4 dlhšie, čím sa dosiahne odlišný výsledný vzhľad projekcie."
        )
            
        safe_font_name: str = FONT_NAME or "Arial"

        tk.Label(
            info_window,
            text=text,
            font=(safe_font_name, 11),
            wraplength=500,
            justify=tk.LEFT
        ).pack(padx=10, pady=10, fill=tk.BOTH, expand=True)    


    def zmenit_rezim_farby(self):
        if not self.pouzit_vlastnu_farbu.get():
            vybrane_obdobie = self.obdobie_var.get()
            if vybrane_obdobie in LITURGICKE_OBDOBIA:
                self.text_color_var.set(LITURGICKE_OBDOBIA[vybrane_obdobie])
                self.indikator_farby.itemconfig(self.indikator_farby_id, fill=self.text_color_var.get())
        else:
            # ak sa prepne na vlastnú farbu, zobraz ju v indikátore
            self.indikator_farby.itemconfig(self.indikator_farby_id, fill=self.text_color_var.get())

        self.aktualizovat_stav_tlacidla_farby()
        self.aktualizovat_vzhlad()
        self.ulozit_nastavenia()        
       
    def nastavit_farbu_pisma_podla_obdobia(self, vybrane_obdobie):
        if not self.pouzit_vlastnu_farbu.get() and vybrane_obdobie in LITURGICKE_OBDOBIA:
            nova_farba = LITURGICKE_OBDOBIA[vybrane_obdobie]
            self.text_color_var.set(nova_farba)
            self.liturgical_season = vybrane_obdobie

            # aktualizácia indikátora farby
            if self.indikator_farby is not None and hasattr(self, "indikator_farby_id"):
                self.indikator_farby.itemconfig(self.indikator_farby_id, fill=nova_farba)

            self.aktualizovat_vzhlad()
            self.ulozit_nastavenia()
            

    def zmenit_priecinok_piesni(self):
        # otvorí dialóg na výber priečinka, predvolený je aktuálny self.song_folder_path
        nova_cesta = filedialog.askdirectory(initialdir=self.song_folder_path)
        if not nova_cesta:
            return

        # aktualizuj atribút triedy
        self.song_folder_path = Path(nova_cesta)

        # aktualizuj label v GUI
        self.folder_label.config(text=str(self.song_folder_path))

        # ulož nastavenia do config.json
        self.ulozit_nastavenia()

        # obnov zoznam súborov podľa aktuálneho filtra
        try:
            aktualne_obdobie = self.default_filter_var.get()
        except tk.TclError:
            aktualne_obdobie = None

        if aktualne_obdobie:
            # použijeme aktuálny filter
            self.filtrovat_subory(aktualne_obdobie)
        else:
            # fallback – načítaj všetky súbory
            subory = self.ziskaj_zoznam_suborov()
            menu = self.subor_menu["menu"]
            menu.delete(0, "end")

            for subor in subory:
                menu.add_command(
                    label=subor,
                    command=lambda value=subor: self.subor_var.set(value)
                )               
                

    def obnovit_predvolene(self):
        """
        Obnoví celý config.json na predvolené hodnoty z DEFAULT_CONFIG
        pomocou atomického zápisu (tempfile + os.replace).
        Aktualizuje všetky súvisiace premenné aj GUI.
        """
        if not messagebox.askyesno(
            "Kinak: Obnoviť predvolené",
            "Naozaj chceš obnoviť všetky nastavenia na pôvodné hodnoty?"
        ):
            return

        try:
            from pathlib import PurePath

            # 1. Konverzia Path objektov na stringy
            config_to_save = {
                k: str(v) if isinstance(v, PurePath) or hasattr(v, "__fspath__") else v
                for k, v in DEFAULT_CONFIG.items()
            }

            # 2. Serializácia JSON
            json_data = json.dumps(config_to_save, indent=4, ensure_ascii=False)

            # 3. Atomický zápis na disk
            target_dir = CONFIG_FILE_PATH.parent
            target_dir.mkdir(parents=True, exist_ok=True)

            temp_path = None
            try:
                fd, temp_str = tempfile.mkstemp(
                    dir=str(target_dir),
                    prefix="config_default_",
                    suffix=".json"
                )
                temp_path = Path(temp_str)

                with os.fdopen(fd, 'w', encoding='utf-8') as tf:
                    tf.write(json_data)
                    tf.flush()
                    os.fsync(tf.fileno())

                # Bezpečné nahradenie pôvodného configu
                os.replace(str(temp_path), str(CONFIG_FILE_PATH))
                temp_path = None  # už bolo presunuté

            finally:
                # Ak temp súbor prežil, odstránime ho
                if temp_path and temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception as e:
                        log_exception("obnovit_predvolene: nepodarilo sa odstrániť temp súbor", e)

            # 4. Aktualizácia internej konfigurácie
            self.config = config_to_save.copy()

            # 5. Reset veľkosti písma
            self.font_size = int(self.config.get("font_size", 75))

            # 6. Načítanie nastavení do aplikácie
            self.nacitat_nastavenia()

            # 7. Aktualizácia GUI prvkov (ak existuje)
            callback = getattr(self, "obnovit_nastavenia_v_gui", None)
            if callable(callback):
                callback()

            messagebox.showinfo(
                "Kinak: Hotovo",
                "Predvolené nastavenia boli obnovené.\n\n"
                "Niektoré zmeny sa prejavia až po reštarte aplikácie."
            )

        except Exception as e:
            log_exception("obnovit_predvolene: Chyba", e)
            messagebox.showerror("Kinak: Chyba", f"Nepodarilo sa obnoviť nastavenia:\n{e}")



    # ----------------------------------------------------------------------
    # Aktualizuje všetky prvky v okne Nastavenia podľa hodnoty self.config.
    # Volá sa po načítaní configu aj po stlačení tlačidla „Obnoviť predvolené“.
    # ----------------------------------------------------------------------
    def obnovit_nastavenia_v_gui(self):
        """
        Zosynchronizuje GUI prvky v okne Nastavenia s aktuálnym slovníkom self.config.
        Všetky cesty sú pre istotu ošetrené cez str().
        """
        # --- Veľkosť písma ---
        if hasattr(self, "font_size_var"):
            try:
                value = int(self.config.get("font_size", 100))
            except (TypeError, ValueError):
                value = 100
            self.font_size_var.set(value)

        # Farba textu
        self.text_color_var.set(self.config.get("text_color", "#FFCC33"))
        
        if hasattr(self, "aktualizovat_stav_tlacidla_farby"):
            self.aktualizovat_stav_tlacidla_farby()
        
        # Liturgické obdobie
        self.obdobie_var.set(self.config.get("liturgical_season", "Cezročné"))

        # Predvolený filter
        self.default_filter_var.set(self.config.get("default_filter_obdobie", "Cezročné C2"))

        # Fade speed
        if hasattr(self, "fade_speed_var"):
            self.fade_speed_var.set(self.config.get("fade_speed", "mierne rýchle"))

        # Live preview - malý náhľad projekcie v pravom dolnom rohu 
        if hasattr(self, "zobrazovat_live_preview_var"):
            raw = self.config.get("zobrazovat_live_preview", True)
            self.zobrazovat_live_preview_var.set(bool(raw))

        # Direktórium
        if hasattr(self, "zobrazit_direktorium_var"):
            raw = self.config.get("zobrazit_direktorium", False)
            self.zobrazit_direktorium_var.set(bool(raw))

        # Diagnostika (logovanie do súboru)
        if hasattr(self, "diagnostika_povolena_var"):
            raw = self.config.get("diagnostika_povolena", True)
            self.diagnostika_povolena_var.set(bool(raw))
            self.diagnostika_povolena = bool(raw)
            nastav_diagnostiku(self.diagnostika_povolena)

        # Rezervy
        if hasattr(self, "reserved_vertical_var"):
            raw = self.config.get("reserved_vertical_ratio", 0.20)
            self.reserved_vertical_var.set(float(raw))

        if hasattr(self, "bottom_margin_var"):
            raw = self.config.get("bottom_margin", 40)
            self.bottom_margin_var.set(int(raw))

        # Priečinok piesní
        raw_folder = self.config.get("song_folder", "")
        self.folder_label.config(text=str(raw_folder))

        # Prekreslenie
        if hasattr(self, "aktualizovat_vzhlad"):
            self.aktualizovat_vzhlad()


    def zobrazit_nastavenia(self):
        """
        Zobrazí modálne okno nastavení a deaktivuje ovládacie prvky hlavného okna.
        Ošetrené proti NoneType chybe pomocou explicitnej kontroly na None.
        """
        try:
            # 1. KONTROLA EXISTENCIE OKNA (OPRAVENÁ LOGIKA)
            # Najprv zistíme, či premenná vôbec existuje a či nie je None.
            okno_treba_vytvorit = False
            if not hasattr(self, "settings_window") or self.settings_window is None:
                okno_treba_vytvorit = True
            else:
                # Ak nie je None, až vtedy môžeme bezpečne zavolať winfo_exists()
                try:
                    if not self.settings_window.winfo_exists():
                        okno_treba_vytvorit = True
                except tk.TclError:
                    okno_treba_vytvorit = True

            if okno_treba_vytvorit:
                self.vytvorit_nastavenia_okno()
            
            # 2. ZOBRAZENIE A VYTIAHNUTIE DO POPREDIA
            try:
                if self.settings_window:
                    self.settings_window.deiconify()
                    self.settings_window.lift()
                    self.settings_window.focus_set()
                    self.settings_window.transient(self.master)
            except Exception as e:
                log_exception("zobrazit_nastavenia: zlyhanie pri deiconify/lift", e)

            # 3. NASTAVENIE MODÁLNEHO REŽIMU
            try:
                if self.settings_window:
                    self.settings_window.grab_set()
            except Exception as e:
                log_exception("zobrazit_nastavenia: zlyhanie grab_set", e)

            # 4. DEAKTIVÁCIA MENU PRVKOV
            try:
                if self.filter_menu is not None:
                    self.filter_menu.config(state="disabled")
                if self.subor_menu is not None:
                    self.subor_menu.config(state="disabled")
            except Exception as e:
                log_exception("zobrazit_nastavenia: zlyhanie deaktivácie menu", e)

            # 5. RESET STAVU UI
            try:
                if self.song_combobox is not None:
                    self.song_combobox.current(0)
                
                # Kompletný reset UI (vypnutie projekcie pri vstupe do nastavení)
                self.reset_ui()
            except Exception as e:
                log_exception("zobrazit_nastavenia: zlyhanie reset_ui", e)

        except Exception as e:
            log_exception("zobrazit_nastavenia: kritická chyba metódy", e)


    def aktualizovat_stav_tlacidla_farby(self):
        """Bezpečne aktualizuje stav prvkov podľa voľby vlastnej farby."""
        try:
            # 1. Získame stav (Boolean)
            is_custom = self.pouzit_vlastnu_farbu.get()
            state = "normal" if is_custom else "disabled"
            obdobie_state = "disabled" if is_custom else "normal"

            # 2. Bezpečne aktualizujeme tlačidlo farby
            btn = getattr(self, "vyber_farbu_button", None)
            if btn and btn.winfo_exists():
                btn.config(state=state)

            # 3. Bezpečne aktualizujeme menu období
            menu = getattr(self, "obdobie_menu", None)
            if menu and menu.winfo_exists():
                menu.config(state=obdobie_state)

            # 4. Bezpečne aktualizujeme indikátor farby (pack/forget)
            indikator = getattr(self, "indikator_farby", None)
            if indikator and indikator.winfo_exists():
                if is_custom:
                    indikator.pack(side=tk.LEFT, padx=(6, 0))
                else:
                    indikator.pack_forget()

        except (tk.TclError, RuntimeError) as e:
            # Ak sa metóda spustila počas ničenia widgetov, ticho to odignorujeme
            if "invalid command name" not in str(e):
                log_info(f"Vizuálna aktualizácia preskočená: {e}")    
                        

    def vybrat_vlastnu_farbu_textu(self):
        color_tuple = colorchooser.askcolor(initialcolor=self.text_color_var.get())
        if color_tuple and color_tuple[1]:
            self.text_color_var.set(color_tuple[1])
            self.pouzit_vlastnu_farbu.set(True)
            self.indikator_farby.itemconfig(self.indikator_farby_id, fill=color_tuple[1])
            self.aktualizovat_vzhlad()
            self.ulozit_nastavenia()

    def clear_screen(self, event=None):
        """
        Úplne vyčistí projekčné plátno a resetuje stavové premenné.
        """
        if event is not None and getattr(event, "widget", None) is getattr(self, "manual_entry", None):
            return "break"

        try:
            self.is_text_visible = False
            self.aktualne_strofy = []
            self.original_projection_text = ""
            self.nazov_piesne = ""

            # Vyčistenie textu a titulkov na projekcii
            if self.projection_window is not None:
                self.projection_window.update_text("")
                self.projection_window.update_title(name="", current=0, total=None)
                # Reset štýlu (iba farba pozadia)
                self.projection_window.update_style(BACKGROUND_COLOR)

            # Vyčistenie labelu strofy v ovládacom paneli
            try:
                self.strofa_label.config(state=tk.NORMAL)
                self.strofa_label.delete("1.0", tk.END)
                self.strofa_label.config(state=tk.DISABLED)
            except Exception as e:
                log_exception("clear_screen: chyba pri čistení strofa_label", e)

            # Reset pozadia hlavného okna
            try:
                self.master.configure(bg=BACKGROUND_COLOR)
            except Exception as e:
                log_exception("clear_screen: chyba pri zmene bg master okna", e)

            # Uloženie stavu
            try:
                self.ulozit_nastavenia()
            except Exception as e:
                log_exception("clear_screen: chyba pri ukladaní nastavení", e)

        except Exception as e:
            log_exception("clear_screen: kritické zlyhanie metódy", e)
        

    def aktualizovat_vzhlad(self, *args):
        """
        Aktualizuje vizuálne prvky ovládacieho panelu a projekčného okna.
        Zabezpečuje konzistenciu farieb, písiem a správne zalomenie náhľadu.
        """
        # Ak prebieha inicializácia, zmeny vzhľadu preskočíme 
        if getattr(self, "initializing", False):
            return

        try:
            text_color = self.text_color_var.get()
            background_color = BACKGROUND_COLOR
        except Exception as e:
            log_exception("aktualizovat_vzhlad: nepodarilo sa získať premenné farieb", e)
            return

        # 1) Projekčné okno – nastavenie cieľovej farby a pozadia 
        try:
            if self.projection_window is not None:
                self.projection_window.target_text_color = text_color
                self.projection_window.update_style(bg_color=background_color)
        except Exception as e:
            log_exception("aktualizovat_vzhlad: zlyhala aktualizácia projekčného okna", e)

        # 2) Pozadie hlavného okna 
        try:
            self.master.configure(bg=background_color)
        except Exception as e:
            log_exception("aktualizovat_vzhlad: zlyhala konfigurácia master okna", e)

        # 3) Live Preview – FARBA A ZALOMENIE
        try:
            # Pozor na názov: predtým si mala live_preview, teraz live_preview_label
            preview = getattr(self, "live_preview_label", None)
            if preview and preview.winfo_exists():
                # Nastavenie farieb náhľadu
                preview.config(fg=text_color, bg=background_color)
                
                # Výpočet novej šírky pre zalamovanie (identicky ako v update_live_preview)
                w = preview.winfo_width()
                if w > 10:
                    new_wraplen = int(w * 0.88)
                    preview.config(wraplength=new_wraplen)
                
                # Ak je text momentálne zobrazený, vynútime prekreslenie náhľadu
                # (zabezpečí, že sa zmení aj veľkosť písma podľa nových farieb)
                if getattr(self, "is_text_visible", False):
                    # Získame aktuálny text z labelu a pošleme ho na refresh
                    current_text = preview.cget("text")
                    if current_text:
                        self.update_live_preview(current_text)

        except Exception as e:
            log_exception("aktualizovat_vzhlad: zlyhala konfigurácia live_preview_label", e)

        # 4) Vstupné pole (Manual Entry) 
        try:
            self.manual_entry.config(fg=text_color, insertbackground=text_color)
        except Exception as e:
            log_exception("aktualizovat_vzhlad: zlyhala konfigurácia manual_entry", e)

        # 5) Panel strofy
        try:
            self.strofa_label["foreground"] = text_color
            self.strofa_label["background"] = background_color

            if hasattr(self.strofa_label, "master"):
                master_widget = self.strofa_label.master
                master_widget["background"] = background_color

        except Exception as e:
            log_exception("aktualizovat_vzhlad: zlyhala konfigurácia strofa_label", e)

        # 6) Highlight tag v texte
        try:
            if self.obsah_suboru_text is not None:
                safe_font_name: str = FONT_NAME or "Arial"

                self.obsah_suboru_text.tag_config(
                    "highlight",
                    background="#444444",
                    foreground=text_color,
                    font=(safe_font_name, 18, "bold")
                )
        except Exception as e:
            log_exception("aktualizovat_vzhlad: zlyhala konfigurácia tagu highlight", e)

        # 7) Aktualizácia stavu tlačidiel a čistenie textu, ak je projekcia vypnutá 
        try:
            self.aktualizovat_stav_tlacidla_farby()

            if not getattr(self, "is_text_visible", False):
                if self.projection_window is not None:
                    self.projection_window.update_text("")
                    self.projection_window.update_title(name="", current=0, total=None)
        except Exception as e:
            log_exception("aktualizovat_vzhlad: záverečná aktualizácia stavu zlyhala", e)                        

    def toggle_projection_text(self, event=None):
        try:
            if event is not None:
                ev_type = getattr(event, "type", None)
                ev_widget = getattr(event, "widget", None)
                
                # 2 = KeyPress v tkinteri. Ak to nie je klávesnica, ignorujeme.
                if ev_type != "2":
                    return "break"
                
                # Ak event prišiel zo vstupného poľa (manual_entry), nechceme prepínať projekciu
                if ev_widget is self.manual_entry:
                    return "break"
        except Exception as e:
            log_exception("toggle_projection_text: chyba pri overovaní eventu", e)

        try:
            # ------------------------------------------------------------
            # Projekcia je ZAPNUTÁ → vypnúť
            # ------------------------------------------------------------
            if self.is_text_visible:
                self.vypni_projekciu()
                return "break"

            # ------------------------------------------------------------
            # Projekcia je VYPNUTÁ → zapnúť
            # ------------------------------------------------------------
            self.is_text_visible = True
            
            # Zavoláme zobrazenie strofy – tu sa reálne posiela text na plátno
            self.zobraz_aktualnu_strofu()
            
            # Aktualizácia indikátora v UI (zelené/červené svetielko)
            self.set_projection_indicator(True)

        except Exception as e:
            log_exception("toggle_projection_text: kritická chyba pri prepínaní viditeľnosti", e)

        return "break"              
            
    def zobrazit_o_aplikacii(self):
        """
        Otvára informačné okno s manuálom a verziou aplikácie.
        ------------------------------------------------------------
        - Zobrazuje texty pomocou tk.Text s tagmi pre formátovanie.
        - Implementuje vlastný scrollbar a zablokovanie kliknutia.
        - Obsahuje kompletnú diagnostiku chýb.
        """
        about_window = tk.Toplevel(self.master)
        self.about_window = about_window
        about_window.title("O aplikácii")
        
        try:
            # 1) Základná konfigurácia okna
            about_window.configure(
                bg=BACKGROUND_COLOR,
                highlightthickness=0,
                bd=0
            )

            about_window.transient(self.master)
            about_window.grab_set()

            saved_w = int(self.about_window_width)
            saved_h = int(self.about_window_height)
            window_width = saved_w if saved_w >= 500 else 830
            window_height = saved_h if saved_h >= 400 else 620
            screen_width = about_window.winfo_screenwidth()
            x = max(0, screen_width - window_width - 30)
            y = 30
            about_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

            def _uloz_geometriu_about(event=None, okamzite=False):
                if event is not None and event.widget is not self.about_window:
                    return

                def zapis_geometrie():
                    if self.about_window is not None and self.about_window.winfo_exists():
                        self.about_window_width = self.about_window.winfo_width()
                        self.about_window_height = self.about_window.winfo_height()
                        self.ulozit_nastavenia(aktualizovat_label=False)

                self._naplanuj_debounced_zapis(
                    "_about_geom_after_id", zapis_geometrie, "_uloz_geometriu_about",
                    okamzite=okamzite,
                )

            self.about_window.bind("<Configure>", _uloz_geometriu_about)

            safe_font_name: str = FONT_NAME or "Arial"
            bg, fg, active = "#1C1C1C", "#E0E0E0", "#F2F2F2"

            # 2) Karty s obsahom
            container = tk.Frame(
                self.about_window,
                bg=bg,
                highlightthickness=0,
                bd=0
            )
            container.pack(fill=tk.BOTH, expand=True)

            header = tk.Frame(container, bg=bg)
            header.pack(fill="x", pady=(10, 5))
            top_panel = tk.Frame(header, bg=bg)
            top_panel.pack(side="left", padx=(10, 0))
            zoom_panel = tk.Frame(header, bg=bg)
            zoom_panel.pack(side="left", padx=(5, 0))

            content = tk.Frame(container, bg=bg)
            content.pack(fill="both", expand=True)

            frame1, frame2, frame3, frame4 = (
                tk.Frame(content, bg=bg),
                tk.Frame(content, bg=bg),
                tk.Frame(content, bg=bg),
                tk.Frame(content, bg=bg)
            )
            frames = {1: frame1, 2: frame2, 3: frame3, 4: frame4}
            font_size = tk.IntVar(value=self.about_font_size)
            text_widgets = []

            def vlozit_text(parent, nazov: str, text: str):
                scrollbar = ttk.Scrollbar(
                    parent,
                    orient="vertical",
                    style="KinakDark.Vertical.TScrollbar"
                )
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

                text_widget = tk.Text(
                    parent,
                    wrap="word",
                    font=(safe_font_name, font_size.get()),
                    fg=fg,
                    bg=bg,
                    padx=20,
                    pady=20,
                    relief="flat",
                    highlightthickness=0,
                    borderwidth=0,
                    yscrollcommand=scrollbar.set,
                    insertbackground=fg
                )
                text_widget.pack(fill=tk.BOTH, expand=True)
                scrollbar.config(command=text_widget.yview)

                text_widget.bind("<Button-1>", self._zablokovat_klik)
                text_widget.insert("1.0", f"{nazov}\n\n")
                text_widget.tag_add("nadpis", "1.0", "1.end")
                text_widget.tag_config(
                    "nadpis",
                    font=(safe_font_name, max(font_size.get() + 4, 12), "bold"),
                    foreground="white"
                )
                text_widget.insert("end", text)
                text_widget.config(state="disabled")

                text_widget.bind("<Enter>", lambda e, tw=text_widget: tw.bind_all(
                    "<MouseWheel>",
                    lambda ev, scroll_widget=tw: scroll_widget.yview_scroll(int(-1 * (ev.delta / 120)), "units")
                ))
                text_widget.bind("<Leave>", lambda e, tw=text_widget: tw.unbind_all("<MouseWheel>"))
                text_widgets.append(text_widget)
                return text_widget

            ovladanie_text = (
                "RÝCHLY NÁVOD\n\n"                
                "Zadajte číslo piesne a potom používajte klávesy:\n\n"
                "• PLUS (+)\t\tĎalšia strofa\n"
                "• MÍNUS (-)\t\tPredchádzajúca strofa (možno použiť aj šípky)\n"
                "• ENTER\t\tAktivovať projekciu (skryť/zobraziť text)\n"
                "• BACKSPACE\t\tMaže číslo piesne a zároveň okamžite vypína projekciu\n"
                "• ESC\t\tZavrieť okno / Zavrieť program\n\n"                
                "Kinak je prenosná desktopová aplikácia na projekciu liturgických piesní, žalmov a modlitieb, so zabudovaným liturgickým kalendárom, ktorý automaticky určuje a zobrazuje aktuálne slávenie, cyklus a žaltárový týždeň liturgického roka.\n\n"
                "HLAVNÉ FUNKCIE\n\n"
                "• Projekcia textov na externý monitor alebo projektor\n"
                "• Automatické spustenie projekcie na druhom monitore v režime celej obrazovky\n"
                "  (vyžaduje zapnutú rozšírenú plochu v systéme)\n"
                "• Dynamické prispôsobenie veľkosti písma podľa obsahu\n"
                "• Podpora UTF-8 aj ANSI kódovania\n"
                "• Zobrazenie aktuálnych liturgických informácií z okien Direktória a Slávení priamo v hlavičke a stavovom riadku.\n\n"
                "INDIKÁTOR PROJEKCIE\n\n"
                "• Zelená = projekcia aktívna\n"
                "• Sivá   = projekcia vypnutá\n\n"
                "V nastaveniach je možné zapnúť malý náhľad projekcie v pravom dolnom rohu "
                "ovládacieho okna – užitočné najmä vtedy, ak premietajúci nevidí priamo na projekčnú obrazovku.\n\n"              
                "OKNÁ DIREKTÓRIUM A SLÁVENIA\n\n"
                "Rýchly výber piesne alebo skratky žalmu pre konkrétne slávenie — dvojklik na bunku, bez ručného zadávania."
            )

            vyhladavanie_text = (
                "VYHĽADÁVANIE PIESNÍ, MODLITIEB A ŽALMOV\n\n"
                "Do poľa na zadanie piesne môžete ručne napísať:\n\n"
                "• Čísla piesní (napr. 254)\n"
                "• Skratky modlitieb (napr. dk → Duša Kristova)\n"
                "• Časť názvu piesne alebo modlitby (napr. ruž → Ružencové bratstvo)\n"
                "• Skratku žalmu (napr. 20c2 → 20. týždeň cezročného obdobia, párny rok)\n\n"
                "POZNÁMKY K ŽALMOM\n\n"
                "• A, B, C = liturgické roky (nedeľné žalmy)\n"
                "• 1–6 = dni v týždni (pondelok–sobota)\n\n"
                "Pri práci s Direktóriom stačí dvojklik na bunku — číslo piesne sa odošle do hlavného okna a okamžite sa načíta. "                
                "Rovnako funguje aj okno Slávenia, kde sa odošle skratka príslušného slávenia."                
            )

            priprava_text = (
                "ÚPRAVA PIESNÍ\n\n"
                "Pri piesňach JKS je v poriadku, ak sa jedna strofa zobrazí aj na dve či tri obrazovky. "
                "Ak chcete, aby sa celá strofa zobrazila naraz, odstráňte v textovom súbore prázdne riadky medzi veršami. "
                "Odlišný vzhľad možno dosiahnuť aj rozdelením strofy na dlhšie riadky.\n\n"
                "ŠPECIÁLNE ZNAKY V PIESŇACH JKS\n\n"
                "• BODKA (·)\t\t\tObsahuje Ofertórium (použije sa dvakrát: úvod + obetovanie)\n"
                "• PODČIARKOVNÍK (_)\t\t\tKoniec strofy\n"
                "• KOMBINÁCIA (_·)\t\t\tKoniec úvodnej časti; nižšie sa nachádza Ofertórium\n\n"
                "V nastaveniach je možné tieto znaky pre projekciu skryť. V hlavnom ovládacom okne "
                "však zostanú vždy viditeľné, aby sa premietajúci vedel ľahko orientovať.\n\n"
                "Praktická rada: Ak pieseň začína bodkou (·), pri obetovaní stačí prejsť na najbližší riadok začínajúci bodkou.\n\n"
                "STRIEDANIE CHÓROV VO VEŠPERÁCH\n\n"
                "Striedanie ľavého a pravého chóru je v projekcii dané striedaním obrazoviek.\n"
                "(každá nová obrazovka = zmena chóru)\n\n"
                "Označenie [L] / [P] slúži len ako vizuálna pomôcka – rýchla orientácia, ktorý chór je práve na obrazovke.\n\n"
                "V nastaveniach je možné tieto znaky pre projekciu skryť, avšak v hlavnom ovládacom okne zostávajú vždy viditeľné.\n\n"                
            )

            pomoc_text = (
                "AK PROJEKCIA NIE JE NA SPRÁVNOM MONITORE\n\n"
                "Skontrolujte, či je v systéme zapnutá rozšírená plocha. Aplikácia vie automaticky otvoriť projekciu "
                "na druhom monitore alebo projektore iba vtedy, keď ho operačný systém vidí ako samostatnú obrazovku.\n\n"
                "AK SA PIESNE NENAČÍTAJÚ\n\n"
                "Pri presúvaní aplikácie vždy presuňte celý priečinok Kinak. Súbor Kinak.exe musí mať pri sebe aj priečinok "
                "s názvom 'piesne'.\n\n"                
                "Kinak (priečinok môže mať ľubovoľný názov)\n"
                " ├── Kinak.exe\n"
                " └── piesne/\n"
                "               ├── 001.txt\n"
                "               ├── 002.txt\n"
                "               ├── 003.txt\n"
                "               └──  .  .  .\n\n"                  
                "Skontrolujte, či je v Nastaveniach správne vybraný priečinok piesní. "
                "Ak priečinok neexistuje, je prázdny alebo neobsahuje textové súbory, "
                "piesne sa v aplikácii nezobrazia ani nenačítajú.\n\n"              
                "Kinak\n"
                "Mesto vzniku: Kremnica\n"
                "Dátum vzniku: november 2025\n"
                f"Verzia: {KINAK_VERSION}"
            )

            vlozit_text(frame1, "Ovládanie", ovladanie_text)
            vlozit_text(frame2, "Vyhľadávanie", vyhladavanie_text)
            vlozit_text(frame3, "Úprava textov", priprava_text)
            vlozit_text(frame4, "Pomoc pri probléme", pomoc_text)

            buttons, stripes = self._build_info_tabs_header(
                top_panel, safe_font_name, bg, fg,
                tab_specs=[
                    ("Ovládanie", 13),
                    ("Vyhľadávanie", 15),
                    ("Úprava textov", 17),
                    ("Pomoc pri probléme", 18),
                ],
            )

            def show(which):
                self.about_last_tab = which
                self.ulozit_nastavenia(aktualizovat_label=False)
                self._show_tab(which, frames, stripes, buttons, safe_font_name, bg, active)
                self.manual_entry.focus_set()

            for i in (1, 2, 3, 4):
                buttons[i].config(command=lambda i=i: show(i))

            def apply_font_preserve_focus():
                size = font_size.get()
                for text_widget in text_widgets:
                    text_widget.config(font=(safe_font_name, size))
                    text_widget.tag_config(
                        "nadpis",
                        font=(safe_font_name, max(size + 4, 12), "bold")
                    )
                self.about_font_size = size
                self.ulozit_nastavenia(aktualizovat_label=False)
                self.manual_entry.focus_set()

            tk.Button(
                zoom_panel,
                text="+",
                width=3,
                font=(safe_font_name, 12, "bold"),
                bg=bg,
                fg=fg,
                relief="flat",
                command=lambda: (font_size.set(min(40, font_size.get() + 1)), apply_font_preserve_focus())
            ).pack(side="left")

            tk.Button(
                zoom_panel,
                text="−",
                width=3,
                font=(safe_font_name, 12, "bold"),
                bg=bg,
                fg=fg,
                relief="flat",
                command=lambda: (font_size.set(max(8, font_size.get() - 1)), apply_font_preserve_focus())
            ).pack(side="left")

            def reset_okna():
                self.about_window_width = 830
                self.about_window_height = 620

                if self.about_window is not None and self.about_window.winfo_exists():
                    reset_x = max(0, self.about_window.winfo_screenwidth() - self.about_window_width - 30)
                    self.about_window.geometry(f"{self.about_window_width}x{self.about_window_height}+{reset_x}+30")

                font_size.set(DEFAULT_CONFIG.get("about_font_size", 12))
                apply_font_preserve_focus()

            tk.Button(
                zoom_panel,
                text="Reset",
                width=6,
                font=(safe_font_name, 12, "bold"),
                bg=bg,
                fg=fg,
                relief="flat",
                command=reset_okna
            ).pack(side="left", padx=(5, 0))

            last = max(1, min(int(getattr(self, "about_last_tab", 1) or 1), 4))
            show(last)

            # 6) Zatváranie okna 
            def pri_zatvoreni():
                _uloz_geometriu_about(okamzite=True)

                # Najprv bezpečne zničíme dcérske okno
                if self.about_window is not None and self.about_window.winfo_exists():
                    self.about_window.destroy()
                
                # Focus vrátime len ak manual_entry existuje (poistka proti AttributeError)
                if self.manual_entry is not None and self.manual_entry.winfo_exists():
                    self.manual_entry.focus_set()

            self.about_window.protocol("WM_DELETE_WINDOW", pri_zatvoreni)
            self.about_window.bind("<Escape>", lambda e: pri_zatvoreni())

            # Vynútenie focusu pri otvorení okna
            about_window.after(50, lambda: about_window.focus_force())

            # 7) Reset UI poistka
            self.song_combobox.current(0)
            try:
                self.reset_ui()
                self.manual_entry.focus_set()
            except Exception as e_reset:
                log_exception("Chyba pri reset_ui v okne O aplikácii", e_reset)

        except Exception as e:
            log_exception("Kritická chyba pri otváraní okna O aplikácii", e)  
        
        
    def zatvorit_nastavenia(self):
        """
        Uloží nastavenia bez prebliknutia hlavného rozhrania a korektne zavrie okno.
        Obnovuje prístup k ovládacím prvkom hlavného okna.
        """
        # 1. Pokus o uloženie nastavení (S PARAMETROM False PROTI BLIKANIU)
        try:
            # Tu voláme uloženie s False, aby sme obišli prekreslenie labelu
            self.ulozit_nastavenia(aktualizovat_label=False)
        except Exception as e:
            log_exception("zatvorit_nastavenia: kritická chyba pri ukladaní", e)

        # 2. Uvoľnenie "focusu" (grab) okna
        try:
            if self.settings_window is not None:
                self.settings_window.grab_release()
        except Exception as e:
            log_exception("zatvorit_nastavenia: grab_release failed", e)

        # 3. Zničenie alebo skrytie okna
        try:
            if self.settings_window is not None:
                self.settings_window.destroy()
                # DÔLEŽITÉ: Nastavíme na None, aby sme predišli AttributeError nabudúce
                self.settings_window = None 
        except Exception as e:
            log_exception("zatvorit_nastavenia: destroy failed, skúšam withdraw", e)
            try:
                if self.settings_window:
                    self.settings_window.withdraw()
            except Exception as e2:
                log_exception("zatvorit_nastavenia: withdraw failed", e2)

        # 4. Opätovné povolenie ovládacích prvkov v hlavnom okne
        try:
            if self.manual_entry is not None:
                self.manual_entry.config(state="normal")
            if self.filter_menu is not None:
                self.filter_menu.config(state="normal")
            if self.subor_menu is not None:
                self.subor_menu.config(state="normal")
        except Exception as e:
            log_exception("zatvorit_nastavenia: aktivácia prvkov zlyhala", e)

        # 5. Vrátenie focusu do hlavného poľa
        try:
            if self.manual_entry is not None:
                self.master.after(100, lambda: self.manual_entry.focus_set()
                    if self.master.winfo_exists() else None)
        except Exception as e:
            log_exception("zatvorit_nastavenia: focus_set after 100ms failed", e)       
             
    def _otvor_prehliadaciu_pomocku(
        self,
        flag_attr: str,
        trieda_okna,
        args_okna: tuple,
        width_attr: str,
        height_attr: str,
        reset_ui_kontext: str,
        kriticka_chyba_popis: str,
    ):
        """
        Spoločná logika pre open_direktorium a open_slavnosti: otvorí pomocné
        prehliadacie okno (DirektoriumApp/SlavnostiApp), zapamätá si jeho
        rozmery pri zatvorení a po zavretí obnoví fokus na vyhľadávacie pole.
        Predtým mali obe metódy vlastnú (identickú) kópiu tejto kostry,
        líšiacu sa len v triede okna, atribútoch rozmerov a texte hlásení.
        """
        if getattr(self, flag_attr, False):
            return  # už otvorené, nič nerobíme

        setattr(self, flag_attr, True)
        # Potlačíme vymazat_subor_menu už PRED otvorením okna: pri zatváraní
        # modálneho okna (uvoľnenie grab_set cez destroy()) môže Tk vrátiť
        # fokus na manual_entry OKAMŽITE – ešte skôr, než stihne zabehnúť náš
        # vlastný, už chránený focus_set() o 100 ms nižšie. Bez tohto by sa
        # odporúčané piesne (direktorium_label) aj popis_label v tej medzere
        # stihli vymazať.
        self._suppress_vymazat = True
        try:
            saved_w = int(getattr(self, width_attr))
            saved_h = int(getattr(self, height_attr))

            def _uloz_rozmery(w, h):
                setattr(self, width_attr, w)
                setattr(self, height_attr, h)
                self.ulozit_nastavenia(aktualizovat_label=False)

            app = trieda_okna(
                self.master, *args_okna,
                init_width=saved_w, init_height=saved_h,
                on_close_callback=_uloz_rozmery,
                on_song_select=self.nacitat_z_okna_pomocok,
            )

            self.song_combobox.current(0)

            try:
                self.reset_ui()
            except Exception as e:
                log_exception(f"Chyba pri reset_ui v rámci {reset_ui_kontext}", e)

            self.master.wait_window(app.top)

        except Exception as e:
            log_exception(f"Kritická chyba pri otváraní okna {kriticka_chyba_popis}", e)

        finally:
            setattr(self, flag_attr, False)
            self.master.after(100, self._obnov_focus_manual_entry_bez_vymazania)

    def open_direktorium(self):
        """Otvára okno liturgického direktória a ošetruje stavy okna."""
        self._otvor_prehliadaciu_pomocku(
            "_direktorium_open", DirektoriumApp, (self.direktorium_data,),
            "direktorium_window_width", "direktorium_window_height",
            reset_ui_kontext="open_direktorium",
            kriticka_chyba_popis="Direktória",
        )

    def open_slavnosti(self):
        """Otvára okno s liturgickým direktóriom a ošetruje chyby pri inicializácii."""
        self._otvor_prehliadaciu_pomocku(
            "_slavnosti_open", SlavnostiApp, (SLAVNOSTI_DATA, NEPRIKAZANE_DATA, POHYBLIVE_DATA),
            "slavnosti_window_width", "slavnosti_window_height",
            reset_ui_kontext="open_slavnosti",
            kriticka_chyba_popis="Slávností",
        )
    
    def otvorit_pomocnika(self):
        try:
            # bezpečný názov fontu pre Pylance
            safe_font_name: str = FONT_NAME or "Arial"

            okno = getattr(self, "pomocnik_okno", None)
            if okno and okno.winfo_exists():
                okno.deiconify()
                okno.lift()
                return

            # --- OKNO ---
            self.pomocnik_okno = tk.Toplevel(self.master)
            self.pomocnik_okno.transient(self.master)
            self.pomocnik_okno.title("Pomocník")
            self.pomocnik_okno.configure(bg="#1C1C1C")
            self.pomocnik_okno.protocol("WM_DELETE_WINDOW", self._zatvorit_pomocnika)

            sw, sh = self.master.winfo_screenwidth(), self.master.winfo_screenheight()

            w = self.pomocnik_width if self.pomocnik_width != -1 else 830
            h = self.pomocnik_height if self.pomocnik_height != -1 else 620
            x = self.pomocnik_x if self.pomocnik_x != -1 else sw - w - 30
            y = self.pomocnik_y if self.pomocnik_y != -1 else 30

            self.pomocnik_okno.geometry(f"{w}x{h}+{x}+{y}")

            def uloz_poziciu(event):
                if self.pomocnik_okno is None:
                    return
                if event.widget is not self.pomocnik_okno:
                    return

                new_x, new_y = self.pomocnik_okno.winfo_x(), self.pomocnik_okno.winfo_y()
                new_w, new_h = self.pomocnik_okno.winfo_width(), self.pomocnik_okno.winfo_height()

                if (new_x, new_y, new_w, new_h) == (
                    self.pomocnik_x, self.pomocnik_y,
                    self.pomocnik_width, self.pomocnik_height
                ):
                    return

                self.pomocnik_x, self.pomocnik_y = new_x, new_y
                self.pomocnik_width, self.pomocnik_height = new_w, new_h

                self._naplanuj_debounced_zapis(
                    "_pomocnik_geom_after_id",
                    lambda: self.ulozit_nastavenia(aktualizovat_label=False),
                    "uloz_poziciu Pomocnika",
                )

            self.pomocnik_okno.bind("<Configure>", uloz_poziciu)

            bg, fg, active = "#1C1C1C", "#E0E0E0", "#F2F2F2"

            # --- CESTY ---
            song_folder = self.song_folder_path
            subor1 = song_folder / "1 Poznámky.txt"
            subor2 = song_folder / "2 Poznámky.txt"
            subor3 = song_folder / "citania.txt"
            subor4 = song_folder / "vespery.txt"

            def nacitaj_text(path_obj):
                if not path_obj.exists():
                    return ""
                try:
                    return path_obj.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    return path_obj.read_text(encoding="cp1250")

            # --- HEADER ---
            header = tk.Frame(self.pomocnik_okno, bg=bg)
            header.pack(fill="x", pady=(10, 5))
            top_panel = tk.Frame(header, bg=bg)
            top_panel.pack(side="left", padx=(10, 0))
            zoom_panel = tk.Frame(header, bg=bg)
            zoom_panel.pack(side="left", padx=(5, 0))

            # --- FOOTER ---
            footer_frame = tk.Frame(self.pomocnik_okno, bg=bg, height=60)
            footer_frame.pack(fill="x", side="bottom", pady=(0, 10))
            footer_frame.pack_propagate(False)

            tk.Label(
                footer_frame,
                text=("1 a 2 Poznámky a Skratky žalmov sú len na čítanie. Citania.txt a vespery.txt sú editovateľné.\n"
                    "Po dopísaní vráťte kurzor myšou späť do poľa s piesňami."),
                bg=bg, fg="#CDB00C",
                font=(safe_font_name, 11, "italic"),
                justify="left"
            ).pack(anchor="w", padx=15)

            # --- CONTENT ---
            content = tk.Frame(self.pomocnik_okno, bg=bg)
            content.pack(fill="both", expand=True)
            frame1, frame2, frame3, frame4, frame5 = (
                tk.Frame(content, bg=bg),
                tk.Frame(content, bg=bg),
                tk.Frame(content, bg=bg),
                tk.Frame(content, bg=bg),
                tk.Frame(content, bg=bg)
            )
            frames = {1: frame1, 2: frame2, 3: frame3, 4: frame4, 5: frame5}

            font_size = tk.IntVar(value=self.pomocnik_font_size)

            def vytvor_text(parent, text, readonly=False):
                t = tk.Text(
                    parent,
                    wrap="word",
                    bg=bg,
                    fg=fg,
                    font=(safe_font_name, font_size.get()),
                    borderwidth=0,
                    insertbackground=fg,
                    undo=not readonly
                )
                t.pack(fill="both", expand=True, padx=10, pady=10)
                t.insert("1.0", text)
                if readonly:
                    t.config(state=tk.DISABLED)
                    t.bind("<Button-1>", self._zablokovat_klik)
                return t

            text1 = vytvor_text(frame1, nacitaj_text(subor1), True)
            text2 = vytvor_text(frame2, nacitaj_text(subor2), True)
            text3 = vytvor_text(frame3, nacitaj_text(subor3), False)
            text4 = vytvor_text(frame4, nacitaj_text(subor4), False)

            SKRATKY_ZALMOV_TEXT = (
                "SKRATKY ŽALMOVÉHO DIREKTÓRIA\n"
                "════════════════════════════════════\n\n"
                "Kinak zobrazuje v stavovom riadku skratku žalmu pre dnešok a zajtrajšok "
                "podľa liturgického dňa. Táto skratka nadväzuje na Direktórium a okno Slávenia "
                "a používa sa aj pri vyhľadávaní odporúčaných piesní JKS. "
                "Pre zobrazenie odporúčaných piesní musí byť táto funkcia zapnutá v nastaveniach.\n\n"
                "Liturgický deň sa vypočíta automaticky. Ak slávnosť koliduje s významnejším slávením, program zohľadní jej presun. "               
                "Pri nedeliach sa používa cyklus A/B/C. Pri bežných dňoch cez rok sa rozlišuje "
                "nepárny a párny rok, napr. 20c1 alebo 20c2.\n\n"
                
                "ADVENTNÉ OBDOBIE\n"
                "─────────────────────\n"
                "  1AD  –  1. adventná nedeľa\n"
                "  2AD  –  2. adventná nedeľa\n"
                "  3AD  –  3. adventná nedeľa\n"
                "  4AD  –  4. adventná nedeľa\n\n"
                
                "VIANOČNÉ OBDOBIE\n"
                "─────────────────────\n"
                "  1VI\t–  1. vianočné obdobie: Narodenie Pána a celá oktáva\n"
                "  STEF\t–  Sv. Štefana, prvého mučeníka (26. XII.) – ak nepadne na nedeľu\n" 
                "  SJE\t–  Sv. Jána, apoštola a evanjelistu (27. XII.) – ak nepadne na nedeľu\n"                
                "  NEV\t–  Sv. Neviniatok, mučeníkov (28. XII.) – ak nepadne na nedeľu\n"
                "  SR\t–  Svätej rodiny Ježiša, Márie a Jozefa\n"
                "  PDR\t–  Posledný deň roka (31. XII.) – ak nepadne na nedeľu\n"
                "  PMB\t–  Panny Márie Bohorodičky (1. I.)\n\n"
                "  2VI\t–  2. vianočné obdobie: 2. vianočná nedeľa a celé druhé vianočné obdobie\n"
                "  NMJ\t–  Najsvätejšie meno Ježiš (3. I.) – ak nepadne na nedeľu\n"
                "  1L\t–  Zjavenie Pána (6. I.)\n"
                "  KKP\t–  Krst Krista Pána\n\n"

                "PÔSTNE OBDOBIE\n"
                "─────────────────────\n"
                "  PS   –  Popolcová streda a dni po nej\n"
                "  1P   –  1. pôstna nedeľa / týždeň\n"
                "  2P   –  2. pôstna nedeľa / týždeň\n"
                "  3P   –  3. pôstna nedeľa / týždeň\n"
                "  4P   –  4. pôstna nedeľa / týždeň\n"
                "  5P   –  5. pôstna nedeľa / týždeň\n"              
                "  ZV   –  Zvestovanie Pána (25. III.) – ak nepadne do Veľkonočného obdobia\n\n"
                "VEĽKÝ TÝŽDEŇ\n"
                "─────────────────────\n"
                "  VT\t–  Kvetná nedeľa a Veľký týždeň\n"
                "  ZST\t–  Zelený štvrtok\n"
                "  VP\t–  Veľký piatok\n\n"

                "VEĽKONOČNÉ OBDOBIE\n"
                "─────────────────────\n"
                "  VG\t–  Veľkonočná vigília\n"
                "  1VN\t–  Veľkonočná nedeľa (Veľkonočná oktáva)\n"
                "  VPON\t–  Pondelok vo Veľkonočnej oktáve\n"
                "  2VN\t–  2. veľkonočná nedeľa / týždeň\n"
                "  3VN\t–  3. veľkonočná nedeľa / týždeň\n"
                "  4VN\t–  4. veľkonočná nedeľa / týždeň\n"
                "  5VN\t–  5. veľkonočná nedeľa / týždeň\n"
                "  6VN\t–  6. veľkonočná nedeľa / týždeň\n"
                "  NP\t–  Nanebovstúpenie Pána\n"
                "  7VN\t–  7. veľkonočná nedeľa / týždeň\n\n"

                "TURÍCE A NADVÄZUJÚCE SVIATKY\n"
                "─────────────────────\n"
                "  1TS  –  Nedeľa Zoslania Ducha Svätého – Turíce\n"
                "  2TS  –  Panny Márie, Matky Cirkvi\n"
                "  3TS  –  Pána Ježiša Krista, Najvyššieho a Večného Kňaza\n"
                "  4TS  –  Najsvätejšia Trojica\n"
                "  5TS  –  Najsvätejšieho Kristovho Tela a Krvi\n"
                "  6TS  –  Najsvätejšieho Srdca Ježišovho\n"
                "  7TS  –  Nepoškvrnené Srdce Panny Márie\n\n"
                
                "CEZROČNÉ OBDOBIE\n"
                "─────────────────────\n"
                "  Xc1  –  X. týždeň cezročného obdobia, nepárny rok (napr. 14c1)\n"
                "  Xc2  –  X. týždeň cezročného obdobia, párny rok (napr. 14c2)\n\n"
                "CEZROČNÉ SVIATKY\n"
                "─────────────────────\n"
                # Poznámka „ak nepadne na nedeľu " pri ZOS chýba správne – 2. XI. sa slávi vždy, aj keď padne na nedeľu - hoci je ZOS iba spomienka je tam výnimka.
                "  FJ\t–  Sv. Filipa a Jakuba, apoštolov (3. V.) – ak nepadne na nedeľu\n"
                "  NJK\t–  Narodenie sv. Jána Krstiteľa (24. VI.)\n"
                "  NAVPM\t–  Návšteva preblahoslavenej Panny Márie (2. VII.) – ak nepadne na nedeľu\n"
                "  CMV\t–  Sv. Cyrila a Metoda (5. VII.)\n"
                "  BEN\t–  Sv. Benedikta, opáta, patróna Európy (11. VII.) – ak nepadne na nedeľu\n"
                "  BRI\t–  Sv. Brigity, rehoľníčky, patrónky Európy (23. VII.) – ak nepadne na nedeľu\n"
                "  PREM\t–  Premenenie Pána (6. VIII.)\n"
                "  VAV\t–  Sv. Vavrinca, diakona a mučeníka (10. VIII.) – ak nepadne na nedeľu\n"
                "  BAR\t–  Sv. Bartolomeja, apoštola (24. VIII.) – ak nepadne na nedeľu\n"
                "  NPMAR\t–  Narodenie Panny Márie (8. IX.) – ak nepadne na nedeľu\n"
                "  PSK\t–  Povýšenie Svätého kríža (14. IX.)\n"
                "  MATE\t–  Sv. Matúša, apoštola a evanjelistu (21. IX.) – ak nepadne na nedeľu\n"
                "  MGR\t–  Sv. Michala, Gabriela a Rafaela, archanieli (29. IX.) – ak nepadne na nedeľu\n"
                "  ZOS\t–  Spomienka na Všetkých zosnulých veriacich (2. XI.)\n"
                "  VPLB\t–  Výročie posviacky Lateránskej baziliky (9. XI.)\n"
                "  OND\t–  Sv. Ondreja, apoštola (30. XI.) – ak nepadne na nedeľu\n\n"


                "MESAČNÉ SVIATKY (xL)\n"
                "─────────────────────\n"
                "  1L  –  Zjavenie Pána (6. I.)\n"
                "  2L  –  Obetovanie Pána (2. II.)\n"
                "  3L  –  Sv. Jozef, ženích (19. III.) – ak nepadne na nedeľu\n"
                "  4L  –  Sviatky svätých mužov (v apríli)\n"
                "  5L  –  Sv. Jozef, robotník (1. V.) – ak nepadne na nedeľu\n"
                "  6L  –  Sv. Peter a Pavol, apoštoli (29. VI.)\n"
                "  7L  –  Sviatky apoštolov (v júli)\n"
                "  8L  –  Nanebovzatie Panny Márie (15. VIII.)\n"
                "  9L  –  Sedembolestná Panna Mária (15. IX.)\n"
                " 10L  –  Sviatky mučeníkov (v októbri)\n"
                " 11L  –  Všetkých svätých (1. XI.)\n"
                " 12L  –  Nepoškvrnené počatie Panny Márie (8. XII.) – ak nepadne na nedeľu\n\n"
                " xL?  –  Fixná pripomienka v stavovom riadku (nie chyba). Použi ju, ak si medzi ponúknutými skratkami nenašiel vhodný žalm.\n\n" 
                
                "PRAKTICKÁ POZNÁMKA\n"
                "─────────────────────\n"
                "V menu Liturgické nástroje → Stiahnuť refrény žalmov je možné hromadne stiahnuť refrény responzóriových žalmov. "                
                "Pôvodné súbory sa pred prepísaním automaticky zálohujú.\n"
            )
            text5 = vytvor_text(frame5, SKRATKY_ZALMOV_TEXT, True)
            # TAB STOP 140 px (môžeš upraviť podľa šírky okna)
            text5.config(tabs=("80"))


            text_save_after_ids = {}

            def uloz_text_atomicky(path_obj, text_widget, popis):
                try:
                    _zapis_text_atomicky(path_obj, text_widget.get("1.0", "end-1c"), encoding="utf-8")
                except Exception as e:
                    log_exception(f"Chyba pri zapise {popis}", e)

            def zrus_planovane_ulozenie(path_obj):
                key = str(path_obj)
                after_id = text_save_after_ids.pop(key, None)
                if after_id:
                    try:
                        self.master.after_cancel(after_id)
                    except Exception as e:
                        log_exception(f"Pomocnik: after_cancel zlyhal pre {path_obj.name}", e)

            def naplanuj_ulozenie_textu(path_obj, text_widget, popis, event=None):
                zrus_planovane_ulozenie(path_obj)

                def _zapis():
                    text_save_after_ids.pop(str(path_obj), None)
                    uloz_text_atomicky(path_obj, text_widget, popis)

                text_save_after_ids[str(path_obj)] = self.master.after(500, _zapis)

            def uloz_text3(event=None):
                naplanuj_ulozenie_textu(subor3, text3, "citania.txt", event)

            text3.bind("<KeyRelease>", uloz_text3)

            def uloz_text4(event=None):
                naplanuj_ulozenie_textu(subor4, text4, "vespery.txt", event)

            text4.bind("<KeyRelease>", uloz_text4)

            def uloz_text3_hned(event=None):
                zrus_planovane_ulozenie(subor3)
                uloz_text_atomicky(subor3, text3, "citania.txt")

            def uloz_text4_hned(event=None):
                zrus_planovane_ulozenie(subor4)
                uloz_text_atomicky(subor4, text4, "vespery.txt")

            def backspace_fix(text_widget, save_func):
                if text_widget.tag_ranges("sel"):
                    text_widget.delete("sel.first", "sel.last")
                else:
                    text_widget.delete("insert-1c", "insert")
                save_func()
                return "break"

            text3.bind("<KeyPress-BackSpace>", lambda event: backspace_fix(text3, uloz_text3_hned))
            text4.bind("<KeyPress-BackSpace>", lambda event: backspace_fix(text4, uloz_text4_hned))

            def zatvorit_pomocnika_s_ulozenim(event=None):
                for after_id in list(text_save_after_ids.values()):
                    try:
                        self.master.after_cancel(after_id)
                    except Exception as e:
                        log_exception("Pomocnik: after_cancel pri zatvoreni zlyhal", e)
                text_save_after_ids.clear()
                uloz_text_atomicky(subor3, text3, "citania.txt")
                uloz_text_atomicky(subor4, text4, "vespery.txt")
                self._zatvorit_pomocnika()
                return "break"

            self.pomocnik_okno.protocol("WM_DELETE_WINDOW", zatvorit_pomocnika_s_ulozenim)

            buttons, stripes = self._build_info_tabs_header(
                top_panel, safe_font_name, bg, fg,
                tab_specs=[
                    ("1 Poznámky", 12),
                    ("2 Poznámky", 12),
                    ("Citania 🖉", 12),
                    ("Vespery 🖉", 12),
                    ("Skratky žalmov", 12),
                ],
            )

            def show(which):
                self.pomocnik_last_tab = which
                self.ulozit_nastavenia()
                self._show_tab(which, frames, stripes, buttons, safe_font_name, bg, active)
                self.manual_entry.focus_set()

            for i in (1, 2, 3, 4, 5):
                buttons[i].config(command=lambda i=i: show(i))

            def apply_font_preserve_focus():
                size = font_size.get()
                for t in (text1, text2, text3, text4, text5):
                    # Ak ide o text5 (Skratky žalmov), vynútime monospaced písmo
                    if t == text5:
                        #t.config(font=("Consolas", size))
                        t.config(font=(safe_font_name, size)) 
                    else:
                        # Pre ostatné záložky necháme pôvodné nastavenie
                        t.config(font=(safe_font_name, size))
                
                self.pomocnik_font_size = size
                self.ulozit_nastavenia()
                self.manual_entry.focus_set()

            tk.Button(
                zoom_panel,
                text="+",
                width=3,
                font=(safe_font_name, 12, "bold"),
                bg=bg,
                fg=fg,
                relief="flat",
                command=lambda: (font_size.set(font_size.get() + 1), apply_font_preserve_focus())
            ).pack(side="left")

            tk.Button(
                zoom_panel,
                text="−",
                width=3,
                font=(safe_font_name, 12, "bold"),
                bg=bg,
                fg=fg,
                relief="flat",
                command=lambda: (font_size.set(max(8, font_size.get() - 1)), apply_font_preserve_focus())
            ).pack(side="left")

            def reset_okna():
                # Šírka 820px pokryje najdlhšie riadky záložky Skratky žalmov bez zalomovania.
                # Ostatné záložky (Poznámky, Citania, Vespery) majú wrap="word" → zalamujú sa
                # aj pri užšom okne, takže väčšia šírka im neprekáža.
                self.pomocnik_width = 820
                self.pomocnik_height = int(sh * 0.8)   

                self.pomocnik_x = sw - self.pomocnik_width - 20
                self.pomocnik_y = int(sh * 0.15)

                if self.pomocnik_okno is None or not self.pomocnik_okno.winfo_exists():
                    return

                self.pomocnik_okno.geometry(
                    f"{self.pomocnik_width}x{self.pomocnik_height}+{self.pomocnik_x}+{self.pomocnik_y}"
                )

                font_size.set(13)
                apply_font_preserve_focus()

            tk.Button(
                zoom_panel,
                text="Reset",
                width=6,
                font=(safe_font_name, 12, "bold"),
                bg=bg,
                fg=fg,
                relief="flat",
                command=reset_okna
            ).pack(side="left", padx=(5, 0))

            def esc_handler(event=None):
                return zatvorit_pomocnika_s_ulozenim(event)

            self.pomocnik_okno.bind("<Escape>", esc_handler)
            self.master.bind("<Escape>", lambda e: zatvorit_pomocnika_s_ulozenim(e))

            last = self.pomocnik_last_tab or 1
            #show(last if last != 5 else 1)
            show(last)
            self.pomocnik_okno.focus_set()

        except Exception as e:
            log_exception("otvorit_pomocnika", e)
            messagebox.showerror("Chyba", f"Nepodarilo sa otvoriť pomocníka: {e}")  
                  
    
    def _zatvorit_pomocnika(self):
        old_id = getattr(self, "_pomocnik_geom_after_id", None)
        if old_id:
            try:
                self.master.after_cancel(old_id)
            except Exception as e:
                log_exception("_zatvorit_pomocnika: after_cancel zlyhal", e)
            self._pomocnik_geom_after_id = None
            try:
                self.ulozit_nastavenia(aktualizovat_label=False)
            except Exception as e:
                log_exception("_zatvorit_pomocnika: ulozenie geometrie zlyhalo", e)

        # Skontrolujeme, či okno existuje a je stále živé
        if hasattr(self, "pomocnik_okno") and self.pomocnik_okno and self.pomocnik_okno.winfo_exists():

            # Pokus o odviazanie ESC pred zničením okna
            try:
                self.pomocnik_okno.unbind("<Escape>")
            except tk.TclError:
                pass  # Ak unbind zlyhá, pokračujeme

            # Zničenie okna
            self.pomocnik_okno.destroy()

        # Nastavíme referenciu na None
        self.pomocnik_okno = None

        # Obnovenie pôvodného ESC na hlavnom okne
        self.master.bind("<Escape>", self.potvrdit_ukoncenie)

        # Vrátenie focusu na hlavné vstupné pole
        if hasattr(self, "manual_entry") and self.manual_entry:
            self.manual_entry.focus_set()
            
    
    def zobraz_rychly_sprievodca(self):
        """Manuálne vyvolaný sprievodca z menu Pomoc, preštylizovaný do dark-theme analogicky k Pomocníkovi."""
        wizard = tk.Toplevel(self.master)
        self.wizard_window = wizard
        wizard.title("Kinak – Rýchly sprievodca")

        # --- ZÁKLADNÉ NASTAVENIA OKNA ---
        self._setup_wizard_window(wizard)

        safe_font_name: str = self.font_family
        bg, fg, active = "#1C1C1C", "#E0E0E0", "#F2F2F2"

        # --- HEADER + CONTENT KONTEJNERY ---
        header, top_panel, content = self._build_main_containers(wizard, bg)

        # --- FRAMES PRE KARTY ---
        frame1, frame2, frame3, frames = self._build_tab_frames(content, bg)

        # --- ZÁLOŽKA 1: Ovládanie ---
        self._build_tab_ovladanie(frame1, safe_font_name, bg, fg)

        # --- ZÁLOŽKA 2: Piesne ---
        folder_var = tk.StringVar(value=str(self.song_folder_path))
        self._build_tab_piesne(frame2, safe_font_name, bg, fg, folder_var)

        # --- ZÁLOŽKA 3: Projektor ---
        self._build_tab_projektor(frame3, safe_font_name, bg, fg, wizard)

        # --- LOGIKA KARIET ---
        buttons, stripes = self._build_tabs_header(top_panel, safe_font_name, bg, fg, active)
        self._wire_tab_switching(buttons, stripes, frames, safe_font_name, bg, active)

        # Zobrazenie prvej záložky po štarte
        self._show_tab(1, frames, stripes, buttons, safe_font_name, bg, active)

        # --- FOOTER ---
        self._build_footer(wizard, safe_font_name, bg)

        # Esc zavrie okno
        wizard.bind("<Escape>", lambda e: wizard.destroy())


    # ================== POMOCNÉ METÓDY ==================

    def _setup_wizard_window(self, wizard: tk.Toplevel) -> None:
        wizard.configure(bg="#1C1C1C", highlightthickness=0, bd=0)
        wizard.resizable(False, False)
        wizard.transient(self.master)
        wizard.grab_set()

        window_width, window_height = 700, 520
        screen_width = wizard.winfo_screenwidth()
        x = max(0, screen_width - window_width - 30)
        y = 30
        wizard.geometry(f"{window_width}x{window_height}+{x}+{y}")


    def _build_main_containers(self, wizard, bg):
        header = tk.Frame(wizard, bg=bg)
        header.pack(fill="x", pady=(10, 5))

        top_panel = tk.Frame(header, bg=bg)
        top_panel.pack(side="left", padx=(10, 0))

        content = tk.Frame(wizard, bg=bg)
        content.pack(fill="both", expand=True)

        return header, top_panel, content


    def _build_tab_frames(self, content, bg):
        frame1 = tk.Frame(content, bg=bg)
        frame2 = tk.Frame(content, bg=bg)
        frame3 = tk.Frame(content, bg=bg)
        frames = {1: frame1, 2: frame2, 3: frame3}
        return frame1, frame2, frame3, frames


    def _build_tab_ovladanie(self, parent, safe_font_name, bg, fg):
        scrollbar = ttk.Scrollbar(parent, orient="vertical", style="KinakDark.Vertical.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        txt1 = tk.Text(
            parent, wrap="word", font=(safe_font_name, 12), fg=fg, bg=bg,
            padx=20, pady=20, relief="flat", highlightthickness=0, borderwidth=0,
            yscrollcommand=scrollbar.set, insertbackground=fg
        )
        txt1.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=txt1.yview)

        txt1.insert("1.0", "1. Ovládanie\n\n", "nadpis")
        navod_text = (            
            "Zadajte číslo piesne a potom používajte klávesy:\n\n"
            "• PLUS (+) \t\tĎalšia strofa\n"
            "• MÍNUS (-) \t\tPredchádzajúca strofa (možno použiť aj šípky)\n"
            "• ENTER \t\tAktivovať projekciu (zobraziť/skryť text)\n"
            "• BACKSPACE \t\tMaže číslo piesne a zároveň okamžite vypína projekciu\n"
            "• ESC \t\tZavrieť okno / ukončiť program\n"
        )
        txt1.insert("end", navod_text)
        txt1.tag_config("nadpis", font=(safe_font_name, 16, "bold"), foreground="white")
        txt1.config(state="disabled")

        txt1.bind("<MouseWheel>", lambda ev, w=txt1: w.yview_scroll(int(-ev.delta / 120), "units"))


    def _build_tab_piesne(self, parent, safe_font_name, bg, fg, folder_var: tk.StringVar):
        f2_inner = tk.Frame(parent, bg=bg)
        f2_inner.pack(padx=20, pady=20, fill="both", expand=True)

        tk.Label(
            f2_inner, text="2. Piesne", font=(safe_font_name, 16, "bold"), bg=bg, fg="white"
        ).pack(anchor="w", pady=(0, 20))

        tk.Label(
            f2_inner, text="Priečinok s piesňami", font=(safe_font_name, 13, "bold"), bg=bg, fg=fg
        ).pack(anchor="w", pady=(0, 5))

        entry_folder = tk.Entry(
            f2_inner, textvariable=folder_var, font=(safe_font_name, 11),
            bg="#2e2e2e", fg="white", insertbackground="white", relief="flat",
            highlightthickness=0, state="readonly", readonlybackground="#2e2e2e"
        )
        entry_folder.pack(fill="x", pady=5, ipady=6)

        def vyber_priecinok():
            priecinok = filedialog.askdirectory(title="Výber priečinka", initialdir=folder_var.get())
            if priecinok:
                folder_var.set(priecinok)
                self.song_folder_path = Path(priecinok)
                self.config["song_folder"] = priecinok

        tk.Button(
            f2_inner, text="Vybrať priečinok...", command=vyber_priecinok,
            bg="#3a3a3a", fg="white", font=(safe_font_name, 11, "bold"),
            relief="flat", borderwidth=0, padx=12, pady=6,
            activebackground="#555555", activeforeground="white", cursor="hand2"
        ).pack(pady=15)


    def _build_tab_projektor(self, parent, safe_font_name, bg, fg, wizard):
        f3_inner = tk.Frame(parent, bg=bg)
        f3_inner.pack(padx=20, pady=20, fill="both", expand=True)

        tk.Label(
            f3_inner, text="3. Projektor", font=(safe_font_name, 16, "bold"), bg=bg, fg="white"
        ).pack(anchor="w", pady=(0, 20))

        tk.Label(
            f3_inner, text="Nastavenie monitora", font=(safe_font_name, 13, "bold"), bg=bg, fg=fg
        ).pack(anchor="w", pady=(0, 5))

        monitor_var = tk.StringVar()

        # Bezpečné použitie get_monitors
        try:
            from screeninfo import get_monitors
        except Exception:
            get_monitors = None

        if callable(get_monitors):
            try:
                monitory = get_monitors()
                mena = [f"{i+1}: {m.width}x{m.height} (x={m.x}, y={m.y})" for i, m in enumerate(monitory)]
                monitor_var.set(mena[0] if mena else "")

                combo = ttk.Combobox(
                    f3_inner, values=mena, textvariable=monitor_var,
                    state="readonly", font=(safe_font_name, 11)
                )
                combo.pack(fill="x", pady=5)

                self._wizard_monitor_combo = combo

                def na_zmenu_monitora(event):
                    if getattr(self, "projection_window", None):
                        idx = combo.current()
                        self.preferred_monitor_index = idx
                        setattr(self.projection_window, "preferred_monitor_index", idx)
                        if hasattr(self.projection_window, "move_and_maximize"):
                            self.projection_window.move_and_maximize()
                    self.ulozit_nastavenia(aktualizovat_label=False)

                combo.bind("<<ComboboxSelected>>", na_zmenu_monitora)
            except Exception:
                tk.Label(f3_inner, text="Chyba načítania monitorov", bg=bg, fg="#ff6b6b").pack(anchor="w")

                self._wizard_monitor_combo = None

        # --- WIN + P INFORMÁCIE ---
        tk.Label(
            f3_inner,
            text="Zapnite v systéme Windows pomocou skratky Win + P režim Rozšíriť:",
            font=(safe_font_name, 12, "bold"),
            bg=bg, fg=fg
        ).pack(anchor="w", pady=(20, 5))

        tk.Label(
            f3_inner,
            text=(
                "• Iba PC obrazovka – projektor je vypnutý\n"
                "• Duplikovať – rovnaký obraz na oboch monitoroch\n"
                "• ✓ Rozšíriť – odporúčané pre Kinak (projektor je samostatná plocha)\n"
                "• Iba druhá obrazovka – obraz ide len na projektor"
            ),
            font=(safe_font_name, 11),
            bg=bg, fg=fg, justify="left"
        ).pack(anchor="w", pady=(0, 15))

        def test_projekcie():
            try:
                # 1. Skontrolovať, či existuje combobox
                combo = getattr(self, "_wizard_monitor_combo", None)
                if combo is None:
                    messagebox.showwarning(
                        "Monitory nie sú dostupné",
                        "Nepodarilo sa načítať zoznam monitorov. Test projekcie nie je možné spustiť.",
                        parent=wizard
                    )
                    return

                # 2. Skontrolovať, či je v comboboxe vybraný monitor
                idx = combo.current()
                if idx is None or idx < 0:
                    messagebox.showwarning(
                        "Chýba výber monitora",
                        "Najprv vyberte monitor, na ktorý sa má projekcia zobraziť.",
                        parent=wizard
                    )
                    return

                # 3. Skontrolovať, či existuje projekčné okno
                if not getattr(self, "projection_window", None):
                    messagebox.showwarning(
                        "Projekcia nie je aktívna",
                        "Najprv aktivujte projekciu (ENTER), aby bolo možné ju otestovať.",
                        parent=wizard
                    )
                    return

                # 4. Nastaviť preferovaný monitor
                self.projection_window.preferred_monitor_index = idx

                # 5. Spustiť test
                self.enter_aktivuj_projekciu()
                messagebox.showinfo("Test projekcie", "Test bol úspešný!", parent=wizard)
                self.master.after(2500, self.enter_aktivuj_projekciu)

            except Exception as e:
                messagebox.showerror("Chyba testu", f"Chyba pri pokuse o test: {e}", parent=wizard)





        tk.Button(
            f3_inner, text="Test projekcie (2.5s)", command=test_projekcie,
            bg="#3a3a3a", fg="white", font=(safe_font_name, 11, "bold"),
            relief="flat", borderwidth=0, padx=12, pady=6,
            activebackground="#555555", activeforeground="white", cursor="hand2"
        ).pack(pady=10)


    def _zablokovat_klik(self, event=None):
        """
        Zabráni kliknutiu do needitovateľného textu prebrať focus (napr. zo
        vstupného poľa piesne). Zdieľané okami "O aplikácii" a "Pomocník",
        predtým duplicitne definované ako lokálna funkcia na oboch miestach.
        """
        return "break"


    def _build_info_tabs_header(self, top_panel, safe_font_name, bg, fg, tab_specs):
        """
        Vytvorí riadok záložkových tlačidiel a farebné pásiky pod nimi –
        presne v štýle používanom v oknách "O aplikácii" a "Pomocník"
        (nahrádza 2× duplicitne definovanú lokálnu funkciu `make_tab`).

        Zámerne nepoužíva `_build_tabs_header` nižšie (ten je určený pre
        sprievodcu nastavením a má navyše iné štýlovanie – activebackground/
        activeforeground/columnconfigure), aby sa nezmenil vzhľad týchto
        dvoch okien.

        tab_specs: zoznam (label, width) dvojíc, jedna položka na záložku.
        Vracia (buttons, stripes), oba slovníky indexované od 1.
        """
        buttons, stripes = {}, {}
        for i, (label, width) in enumerate(tab_specs):
            btn = tk.Button(
                top_panel, text=label, bg=bg, fg=fg,
                font=(safe_font_name, 12), relief="flat", width=width,
            )
            btn.grid(row=0, column=i, padx=2)
            stripe = tk.Frame(top_panel, height=3, bg=bg)
            stripe.grid(row=1, column=i, sticky="ew")
            buttons[i + 1], stripes[i + 1] = btn, stripe
        return buttons, stripes


    def _naplanuj_debounced_zapis(
        self,
        after_id_attr: str,
        zapis_funkcia,
        kontext: str,
        oneskorenie_ms: int = 500,
        okamzite: bool = False,
    ) -> None:
        """
        Spoločný debounce mechanizmus pre ukladanie geometrie okien po
        udalosti <Configure> (nahrádza 4× duplicitne definovaný vzor „zruš
        predtým naplánované uloženie, naplánuj nové cez self.master.after").

        - after_id_attr: názov atribútu na self, do ktorého sa ukladá ID
          naplánovaného volania (napr. "_main_geom_after_id"), aby sa dalo
          zrušiť pri ďalšej zmene skôr, než stihlo prebehnúť.
        - zapis_funkcia: bezparametrová funkcia, ktorá vykoná samotné
          čítanie aktuálnej geometrie a jej uloženie (volaná po uplynutí
          oneskorenia, alebo hneď ak `okamzite=True`).
        - kontext: text použitý pri logovaní prípadných výnimiek.
        - okamzite: ak True, obíde debounce a `zapis_funkcia` sa zavolá
          synchrónne hneď (napr. pri zatváraní okna).
        """
        stary_id = getattr(self, after_id_attr, None)
        if stary_id:
            try:
                self.master.after_cancel(stary_id)
            except Exception as e:
                log_exception(f"{kontext}: after_cancel zlyhal", e)

        def _zapis():
            try:
                zapis_funkcia()
            except Exception as e:
                log_exception(f"{kontext}: zápis zlyhal", e)
            setattr(self, after_id_attr, None)

        if okamzite:
            _zapis()
        else:
            setattr(self, after_id_attr, self.master.after(oneskorenie_ms, _zapis))


    def _build_tabs_header(self, top_panel, safe_font_name, bg, fg, active):
        buttons, stripes = {}, {}

        def make_tab(i, label, width=14):
            btn = tk.Button(
                top_panel, text=label, bg=bg, fg=fg, font=(safe_font_name, 12),
                relief="flat", width=width, activebackground=bg,
                activeforeground=active, borderwidth=0
            )
            btn.grid(row=0, column=i, padx=2)
            stripe = tk.Frame(top_panel, height=3, bg=bg)
            stripe.grid(row=1, column=i, sticky="ew")
            top_panel.columnconfigure(i, weight=1)
            buttons[i + 1], stripes[i + 1] = btn, stripe

        make_tab(0, "1. Ovládanie")
        make_tab(1, "2. Piesne")
        make_tab(2, "3. Projektor")

        return buttons, stripes


    def _show_tab(self, which, frames, stripes, buttons, safe_font_name, bg, active):
        for f in frames.values():
            f.pack_forget()
        for s in stripes.values():
            s.config(bg=bg)
        for b in buttons.values():
            b.config(font=(safe_font_name, 12))

        frames[which].pack(fill="both", expand=True)
        stripes[which].config(bg=active)
        buttons[which].config(font=(safe_font_name, 12, "bold"))


    def _wire_tab_switching(self, buttons, stripes, frames, safe_font_name, bg, active):
        for i in (1, 2, 3):
            buttons[i].config(
                command=lambda i=i: self._show_tab(i, frames, stripes, buttons, safe_font_name, bg, active)
            )


    def _build_footer(self, wizard, safe_font_name, bg):
        footer_frame = tk.Frame(wizard, bg=bg, height=60)
        footer_frame.pack(fill="x", side="bottom", pady=(0, 10), padx=20)

        def ulozit():
            self.config["song_folder"] = str(self.song_folder_path)
            self.ulozit_nastavenia()
            wizard.destroy()

        tk.Button(
            footer_frame, text="Zavrieť", command=wizard.destroy,
            bg="#3a3a3a", fg="white", font=(safe_font_name, 11, "bold"),
            relief="flat", borderwidth=0, padx=15, pady=8,
            activebackground="#555555", activeforeground="white", cursor="hand2"
        ).pack(side="left")

        tk.Button(
            footer_frame, text="Uložiť nastavenia", command=ulozit,
            bg="#07BA07", fg="white", font=(safe_font_name, 11, "bold"),
            relief="flat", borderwidth=0, padx=15, pady=8,
            activebackground="#09d109", activeforeground="white", cursor="hand2"
        ).pack(side="right")
    
                    
                            
    def reset_ui(self):
        # vypni projekciu
        self.vypni_projekciu()

        # vyčisti horný panel (strofa_label)
        self.strofa_label.config(state=tk.NORMAL)
        self.strofa_label.delete("1.0", tk.END)
        self.strofa_label.config(state=tk.DISABLED)

        # vyčisti názov label
        self.nazov_label.config(text="")

        # vyčisti panel Obsah súboru
        self.obsah_suboru_text.config(state=tk.NORMAL)
        self.obsah_suboru_text.delete("1.0", tk.END)
        self.obsah_suboru_text.config(state=tk.DISABLED)

        # vyčisti vstupné pole
        self.manual_entry.delete(0, tk.END)

        # Resetuj výber v rolovacom menu a popis + popis piesne z direktória
        self.subor_var.set("—")
        self.popis_label.config(text="")
        self.direktorium_label.config(text="")        

        # reset interných premenných
        self.nazov_piesne = ""
        self.aktualne_strofy = []
        self.aktualny_index_strofa = 0        
    
    # ==========================================================
    # LIVE PREVIEW – oddelenie debounce a exekúcie (oprava leak-u after_id)
    # ==========================================================
    def _cancel_pending_live_preview(self):
        """Zruší čakajúce naplánované volanie live preview, ak existuje."""
        old_id = getattr(self, "_live_preview_after_id", None)
        if old_id:
            try:
                self.master.after_cancel(old_id)
            except Exception as e:
                log_exception("_cancel_pending_live_preview: after_cancel zlyhal", e)
            finally:
                self._live_preview_after_id = None

    def _schedule_live_preview(self, text, delay=100):
        """
        Debounce wrapper: zruší predchádzajúce naplánovanie a naplánuje nové.
        Volá sa pri rýchlom písaní alebo pri retry (malé rozmery / guard).
        """
        # 1. zruš staré
        self._cancel_pending_live_preview()
        # 2. naplánuj nové – closure via default arg t=text aby sa neprepisovalo
        try:
            self._live_preview_after_id = self.master.after(
                delay, lambda t=text: self._on_scheduled_live_preview(t)
            )
        except Exception as e:
            log_exception("_schedule_live_preview: master.after zlyhal", e)
            self._live_preview_after_id = None

    def _on_scheduled_live_preview(self, text):
        """Callback volaný z Tk after – vyčistí ID a spustí skutočný render."""
        # after práve vypršal, jeho ID už nie je pending
        self._live_preview_after_id = None
        self.update_live_preview(text)

    def update_live_preview(self, text):
        """
        Samotná logika aktualizácie – chráni sa len guardom proti re-entry.
        Debouncing (after_cancel + after) rieši _schedule_live_preview(),
        nie táto funkcia. Tým sa zabráni leak-u after_id pri rýchlom písaní.
        """

        # 1. Guard proti súbežnému behu – ak už beží, naplánujeme retry namiesto dropu
        if getattr(self, "_live_preview_updating", False):
            self._schedule_live_preview(text, delay=100)
            return

        # 2. Kontrola widgetov
        preview = getattr(self, "live_preview_label", None)
        container = getattr(self, "preview_container", None)
        if not preview or not container or not preview.winfo_exists():
            self._cancel_pending_live_preview()
            return

        # 3. Kontrola nastavení (či je náhľad zapnutý v UI)
        show_preview_var = getattr(self, "zobrazovat_live_preview_var", None)
        if not show_preview_var or not show_preview_var.get():
            preview.config(text="")
            if container.winfo_ismapped():
                container.place_forget()
            self._cancel_pending_live_preview()
            return

        # 4. Zobrazenie kontajnera (ak bol skrytý)
        if not container.winfo_ismapped():
            container.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")

        # 5. Rozmery kontajnera
        w = container.winfo_width()
        h = container.winfo_height()

        if w <= 10 or h <= 10:
            # Pri inicializácii sú rozmery ešte 1x1 – retry cez debounce, nie priamy after
            try:
                if not self.master.winfo_exists() or not self.master.winfo_viewable():
                    return
            except tk.TclError:
                pass
            self._schedule_live_preview(text, delay=100)
            return

        # 6. Skutočný render s ochranou proti re-entry
        self._live_preview_updating = True
        try:
            if not self.is_text_visible:
                preview.config(text="")
                return

            cisty_text = text or ""
            if hasattr(self, "remove_special_chars"):
                cisty_text = self.remove_special_chars(cisty_text)

            max_w = int(w * 0.88)
            max_h = int(h * 0.82)

            font_family: str = FONT_NAME or "Arial"

            # Persistentný font objekt – vytvorí sa raz, potom len reconfigure
            test_font = getattr(self, "_preview_test_font", None)
            if test_font is None:
                test_font = tkfont.Font(family=font_family, size=PREVIEW_FONT_MIN, weight="bold")
                self._preview_test_font = test_font
            else:
                test_font.configure(family=font_family)

            # --- BINÁRNE VYHĽADÁVANIE (zjednotené s ProjectionWindow) ---
            low = PREVIEW_FONT_MIN
            high = PREVIEW_FONT_INIT
            best_size = PREVIEW_FONT_MIN

            # Rýchly early-exit: ak sa zmestí aj max veľkosť, nemusíme hľadať
            test_font.configure(size=high)
            if estimate_text_height(cisty_text, test_font, max_w) <= max_h:
                best_size = high
            else:
                while low <= high:
                    mid = (low + high) // 2
                    test_font.configure(size=mid)
                    needed_h = estimate_text_height(cisty_text, test_font, max_w)

                    if needed_h <= max_h:
                        best_size = mid      # zmestí sa -> skús väčšie
                        low = mid + 1
                    else:
                        high = mid - 1       # nezmestí sa -> skús menšie

            current_size = best_size

            preview.config(
                text=cisty_text,
                font=(font_family, current_size, "bold"),
                wraplength=max_w,
                justify="center",
                anchor="center"
            )

        except Exception as e:
            log_exception("update_live_preview zlyhal", e)
        finally:
            self._live_preview_updating = False
            # Žiadne after_cancel tu! ID sa čistí v _on_scheduled_live_preview()
            # alebo v _cancel_pending_live_preview() pri debounce. Tým sa zabráni
            # situácii, kedy finally zruší práve naplánovaný nový after.
                                    

    def _shutdown_executor(self) -> None:
        try:
            ex = getattr(self, '_download_executor', None)
            if ex is not None:
                ex.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            try:
                ex.shutdown(wait=False)  # type: ignore[union-attr]
            except Exception:
                pass
        except Exception:
            pass

if __name__ == "__main__":

    root = None  # ← pridane, aby bola premenná vždy definovaná

    try:
        spustit_startovaciu_diagnostiku()

        # 1. Vytvorenie hlavného objektu okna (skrytého pre čistý štart)
        root = tk.Tk()
        root.withdraw()
        
        # Nastavenie titulku – liturgický rok sa doplní z configu v nacitat_nastavenia()
        root.title(f"Kinak v{KINAK_VERSION}")
        
        # 2. Dynamická detekcia systémových fontov
        # (musí byť po tk.Tk(), ale pred ControlApp – pozri docstring _inicializovat_fonty)
        _inicializovat_fonty()

        # 3. Nastavenie ikony s viacúrovňovým fallbackom
        if APP_ICON.exists():
            try:
                root.iconbitmap(str(APP_ICON))
            except Exception as e_ico:
                log_exception("Nastavenie .ico zlyhalo, skúšam PNG fallback", e_ico)
                try:
                    _path_to_img = ICON_PNG if ICON_PNG.exists() else APP_ICON
                    icon_img = tk.PhotoImage(file=str(_path_to_img))
                    root.wm_iconphoto(True, icon_img)
                except Exception as e_png:
                    log_exception("Zlyhal aj PNG fallback pre ikonu", e_png)
        else:
            log_info(f"Ikona nebola nájdená na ceste: {APP_ICON}")

        # 4. Inicializácia hlavnej aplikácie
        app = ControlApp(root)
        
        # 5. Zobrazenie okna – deiconify() pred update_idletasks(), aby sa okno
        # neobjavilo pred dokončením vykresľovania widgetov (zabraňuje bliknutiu).
        root.deiconify()
        root.update_idletasks()
        
        # Vynútenie focusu
        try:
            root.lift()
            root.focus_force()
        except Exception as e:
            log_exception("Nepodarilo sa nastaviť focus na hlavné okno", e)
            
        root.mainloop()       
        
    except Exception as e:
        error_msg = traceback.format_exc()
        log_exception("KRITICKÁ CHYBA V HLAVNOM BLOKU", e)

        # Grafické upozornenie v prípade totálneho zlyhania
        try:
            if root is not None and root.winfo_exists():
                main_win = root
                main_win.deiconify()
            else:
                main_win = tk.Tk()
                main_win.withdraw()

            # Získanie absolútnej cesty k logu
            try:
                display_log_path = LOG_PATH.resolve()
            except Exception as e_path:
                log_exception("Nepodarilo sa získať absolútnu cestu k log súboru", e_path)
                display_log_path = "log_kinak.txt"

            messagebox.showerror(
                "Kritická chyba pri štarte",
                f"Aplikáciu Kinak nebolo možné spustiť.\n\n"
                f"Podrobnosti nájdete v súbore:\n{display_log_path}\n\n"
                f"Chyba: {str(e)}"
            )
            main_win.destroy()

        except Exception as e_ui:
            log_exception("Zlyhanie UI pri zobrazení kritickej chyby", e_ui)
            print(f"Úplné zlyhanie UI: {e_ui}")
            print(f"Pôvodná chyba:\n{error_msg}")







