# Kinak
Liturgický projekčný program - zdarma pre všetky farnosti na Slovensku

License: MIT
Platform: Windows
Krajina: SK

Zdarma pre všetky farnosti na Slovensku. Dáta čítaní, vešpier a žalmov: zdroj lc.kbs.sk / breviar.kbs.sk

Reálny program, ktorý počas liturgie beží v kostole v Kremnici. Vznikol ako dobrovoľnícky projekt pre našu farnosť a je voľne k dispozícii pre všetky farnosti.

Príbeh
5 rokov som prepisovala piesne do Wordu a hľadala, aký je týždeň žaltára a či má prednosť sviatok. Vytvorila som Kinak, aby premietač mal všetko na 2 kliky – bez internetu, bez stresu pred omšou.

Pre koho je Kinak?
pre premietačov piesní na plátno / TV
pre farnosti, ktoré chcú mať čítania, vešpery, žalmy a piesne a rôzne modlitby pripravené automaticky
Čo vie Kinak?
Premietanie na druhý monitor / projektor s nastavením farieb, veľkosti, prelínania
Piesne – rýchle vyhľadávanie podľa čísla alebo názvu, vlastná knižnica
Liturgický kalendár pre Slovensko – automatický výpočet:
Veľkonočná nedeľa (Meeus-Jones-Butcher)
adventná nedeľa, Advent, Vianoce, Pôst, Veľká noc
Presuny slávení: Zvestovanie, sv. Jozef, Narodenie Jána Krstiteľa atď. Ak slávnosť koliduje s významnejším slávením, program automaticky zohľadní jej presun.
Týždeň žaltára I.-IV., liturgické roky A/B/C, cyklus I/II
Sťahovanie čítaní a vešpier na daný deň (offline cache)
Funguje bez internetu – po prvom stiahnutí
Liturgický kalendár – špecifikácia
Liturgické výpočty sa riadia smernicami pre Rímskokatolícku cirkev na Slovensku, nie americkým modelom.

Krajina / provincia: Slovensko (SK)
Kalendár: všeobecný rímsky + vlastné slávenia slovenskej provincie (sv. Cyril a Metod 5.7., Sedembolestná Panna Mária 15.9. a i.)
Smernice: Všeobecné normy o liturgickom roku a o kalendári + Direktórium KBS
Kľúčový rozdiel oproti US modelu: Zjavenie Pána je na Slovensku pevne 6. januára (prikázaný sviatok, štátny sviatok) a nepresúva sa na nedeľu. Preto Krst Krista Pána = nedeľa PO 6.1., aj keď 6.1. je nedeľa (napr. 13.1.2019, 13.1.2030).
Zdroje dát
Obsah čítaní a vešpier nie je súčasťou programu. Sťahuje sa na požiadanie pre osobnú potrebu farnosti:

Liturgický kalendár a čítania: lc.kbs.sk (Konferencia biskupov Slovenska)
Liturgia hodín / vešpery: breviar.kbs.sk

Inštalácia

Pre bežného používateľa (Windows)
Stiahnite si Kinak_v3.1.exe zo sekcie Releases do priečinka Kinak
Súbor Kinak.exe musí mať pri sebe aj priečinok s názvom piesne
Kinak (priečinok môže mať ľubovoľný názov)
├── Kinak.exe
└── piesne/
    ├── 001.txt
    ├── 002.txt
    ├── 003.txt
    └── ...
Spustite a choďte do menu Pomoc → Rýchly sprievodca

Inštalácia pre vývojára
bash
git clone https://github.com/VASE_MENO/Kinak.git
cd Kinak
pip install requests beautifulsoup4 screeninfo
python Kinak.py
Požiadavky: Python 3.9+, Windows 10/11, knižnice requests, beautifulsoup4, screeninfo

Licencia
MIT License - pozri súbor LICENSE 

Vysvetlenie v skratke:
Toto je slobodný softvér. Môžete ho zdarma používať, upravovať a šíriť pre všetky farnosti na Slovensku aj inde, aj na komerčné účely. Jediná podmienka je zachovať informáciu o autorovi a licencii.

Zdarma pre všetky farnosti na Slovensku. Dáta čítaní: zdroj lc.kbs.sk / breviar.kbs.sk

Copyright (c) 2026 Kinak - Kremnica

Kontakt
Vytvorené ako dobrovoľnícky projekt pre farnosť Kremnica.



