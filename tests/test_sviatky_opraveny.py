# -*- coding: utf-8 -*-
from datetime import date
import pytest
from Kinak import datum_svatej_rodiny, krst_krista_pana, datum_zvestovania_pana

def test_svata_rodina_ked_vianoce_nedela():
    # 2022: 25.12. je nedeľa -> Svätá rodina 30.12.
    assert datum_svatej_rodiny(2022) == date(2022,12,30)

def test_svata_rodina_bezný_rok():
    # 2023: 25.12. pondelok -> nedeľa po je 31.12.
    assert datum_svatej_rodiny(2023) == date(2023,12,31)

def test_krst_pana():
    # Krst je nedeľa po 6.1.
    assert krst_krista_pana(2024) == date(2024,1,7)
    assert krst_krista_pana(2025) == date(2025,1,12)

def test_zvestovanie_presun_2016():
    # 2016: 25.3. Veľký piatok -> presun na 4.4.
    assert datum_zvestovania_pana(2016) == date(2016,4,4)

def test_zvestovanie_bez_presunu():
    # 2024 sa presúva (Svätý týždeň) -> 8.4., preto testujeme rok bez kolízie
    assert datum_zvestovania_pana(2023) == date(2023,3,25)
    assert datum_zvestovania_pana(2025) == date(2025,3,25)
