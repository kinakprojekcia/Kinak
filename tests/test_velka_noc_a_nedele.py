# -*- coding: utf-8 -*-
from datetime import date
import pytest
from Kinak import velkonocna_nedela, prva_adventna_nedela, najblizsia_nedela_po_dni, nedela_zaciatku_tyzdna

@pytest.mark.parametrize(("rok","ocakavany"),[
    (2023, date(2023,4,9)),
    (2024, date(2024,3,31)),
    (2025, date(2025,4,20)),
    (2026, date(2026,4,5)),
    (2030, date(2030,4,21)),
])
def test_velka_noc(rok, ocakavany):
    assert velkonocna_nedela(rok) == ocakavany

def test_najblizsia_nedela():
    assert najblizsia_nedela_po_dni(date(2024,12,1)) == date(2024,12,8)  # nedeľa -> ďalšia nedeľa
    assert najblizsia_nedela_po_dni(date(2024,12,2)) == date(2024,12,8)

def test_nedela_zaciatku_tyzdna():
    # streda 2024-12-04 -> nedeľa 2024-12-01
    assert nedela_zaciatku_tyzdna(date(2024,12,4)) == date(2024,12,1)
    assert nedela_zaciatku_tyzdna(date(2024,12,1)) == date(2024,12,1)
