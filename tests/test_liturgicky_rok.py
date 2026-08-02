# -*- coding: utf-8 -*-
"""
Testy pre vypocitaj_liturgicky_rok
Spustenie: pytest tests/test_liturgicky_rok.py -v
"""
from datetime import date
import pytest
from Kinak import vypocitaj_liturgicky_rok, prva_adventna_nedela

# --- 1. Pôvodné jednotkové testy ---
def test_pred_adventom_2022():
    assert vypocitaj_liturgicky_rok(date(2022, 11, 26)) == "C"

def test_prva_adventna_nedela_2022():
    assert vypocitaj_liturgicky_rok(date(2022, 11, 27)) == "A"

def test_den_pred_adventom_2023():
    assert vypocitaj_liturgicky_rok(date(2023, 12, 2)) == "A"

def test_prva_adventna_nedela_2023():
    assert vypocitaj_liturgicky_rok(date(2023, 12, 3)) == "B"

def test_den_pred_adventom_2024():
    assert vypocitaj_liturgicky_rok(date(2024, 11, 30)) == "B"

def test_prva_adventna_nedela_2024():
    assert vypocitaj_liturgicky_rok(date(2024, 12, 1)) == "C"

def test_den_pred_adventom_2030():
    assert vypocitaj_liturgicky_rok(date(2030, 11, 30)) == "B"

def test_prva_adventna_nedela_2030():
    assert vypocitaj_liturgicky_rok(date(2030, 12, 1)) == "C"

# --- 2. Parametrizovaný test hraníc adventu (lepšia verzia) ---
@pytest.mark.parametrize(
    ("datum", "ocakavany_rok"),
    [
        (date(2022, 11, 26), "C"),
        (date(2022, 11, 27), "A"),
        (date(2023, 12, 2), "A"),
        (date(2023, 12, 3), "B"),
        (date(2024, 11, 30), "B"),
        (date(2024, 12, 1), "C"),
        (date(2030, 11, 30), "B"),
        (date(2030, 12, 1), "C"),
    ],
)
def test_liturgicky_rok_na_hranici_adventu(datum, ocakavany_rok):
    assert vypocitaj_liturgicky_rok(datum) == ocakavany_rok

# --- 3. Robustný test cyklu A/B/C ---
@pytest.mark.parametrize(
    ("datum", "ocakavany_rok"),
    [
        (date(2021, 12, 1), "C"),
        (date(2022, 12, 1), "A"),
        (date(2023, 12, 10), "B"),
        (date(2024, 12, 8), "C"),
        (date(2025, 12, 7), "A"),
        (date(2026, 12, 6), "B"),
        (date(2027, 12, 5), "C"),
    ],
)
def test_abc_cyklus(datum, ocakavany_rok):
    assert vypocitaj_liturgicky_rok(datum) == ocakavany_rok

# --- 4. Extra: kontrola samotnej prvej adventnej nedele ---
@pytest.mark.parametrize(
    ("rok", "ocakavany_datum"),
    [
        (2022, date(2022, 11, 27)),
        (2023, date(2023, 12, 3)),
        (2024, date(2024, 12, 1)),
        (2025, date(2025, 11, 30)),
        (2026, date(2026, 11, 29)),
        (2030, date(2030, 12, 1)),
    ]
)
def test_prva_adventna_nedela_vypocet(rok, ocakavany_datum):
    assert prva_adventna_nedela(rok) == ocakavany_datum
