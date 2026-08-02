# Regresné testy pre Kinak.py

## Inštalácia a spustenie

```bash
pip install pytest python-dateutil
```

Umiestni `test_kinak.py` a `pytest.ini` do rovnakého priečinka ako `Kinak.py`
(ten musí byť importovateľný ako `Kinak` – teda buď v tom istom priečinku,
alebo na `PYTHONPATH`).

```bash
pytest test_kinak.py            # rýchla sada (226 testov, ~9 s)
pytest test_kinak.py -m slow    # + pomalý exhaustívny test cez 1583–2200 (~9 s naviac)
pytest test_kinak.py -v         # podrobný výpis
```

Testy nespúšťajú GUI (Tkinter sa v `Kinak.py` inicializuje až v bloku
`if __name__ == "__main__":`), takže bežia aj headless / v CI bez displeja.

## Čo sada pokrýva

| Skupina | Čo overuje |
|---|---|
| Veľkonočná nedeľa | Zhoda s nezávislou knižnicou `dateutil` pre ~120 rokov (1583–9999), validácia rozsahu/typu |
| Zvestovanie Pána | Presuny cez Veľký týždeň/oktávu (2016, 2035) aj cez bežnú nedeľu (2007, 2012, 2057) |
| Sv. Jozef, ženích | Anticipácia pred Kvetnou nedeľou (Notitiae 2006) – 2008, 2062 |
| Narodenie sv. Jána Krstiteľa | Kolízia s Najsv. Kristovým Telom a Krvou v roku 2038 |
| Nepoškvrnené Srdce PM | Kolízia s pevnými sviatkami v rokoch 2011, 2038, 2095 |
| Nepoškvrnené počatie PM | Presun z nedele na 9.12. (2019, 2024) |
| Obetovanie Pána | Prednosť pred nedeľou (2020–2059) – **regresný test pre opravu mŕtveho kódu `"OP"`** |
| Krst Krista Pána | Slovenské pravidlo "nedeľa po 6.1." aj keď 6.1. je nedeľa (2013–2047), nezávisle overené voči archívu lc.kbs.sk pre rok 2019 |
| Vianočná oktáva | Vynechanie sv. Štefana (2004+), Svätá rodina na 30.12. keď 25.12. = nedeľa (2005+) |
| Sv. Ondrej | Vynechanie pri kolízii s 1. adventnou nedeľou |
| Nanebovstúpenie Pána | Kolízia so sv. Filipom a Jakubom v rokoch 2035, 2046 |
| Žaltárový týždeň / dvojročný cyklus | Reset na I. týždeň pri Advente/Pôste/Veľkej noci, platné hodnoty v celom roku |
| `DEFAULT_CONFIG` | **Regresný test pre opravu "zamrznutej" hodnoty `liturgical_year`** |
| Exhaustívne testy | Žiadna výnimka + konzistentné číslovanie cezročných týždňov cez **každý deň** rokov 1583–2200 (`-m slow`) |

## Poznámka k dôveryhodnosti

Očakávané hodnoty v testoch sú buď (a) porovnané s nezávislým zdrojom
(`dateutil.easter`, archív `lc.kbs.sk`), alebo (b) odvodené priamo z
liturgických pravidiel opísaných v docstringoch `Kinak.py` a ručne
prepočítané (nie skopírované z výstupu testovanej funkcie) – pozri komentáre
pri jednotlivých testoch.

Funkčnosť sady bola overená aj "mutation testingom" – dočasné zámerné
pokazenie Veľkonočného algoritmu aj vrátenie opraveného mŕtveho kódu `"OP"`
spôsobilo presne očakávané zlyhania príslušných testov.
