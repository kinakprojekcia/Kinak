# Kinak

**Liturgický projekčný program pre farnosti na Slovensku – zdarma.**

[License: MIT](https://img.shields.io/badge/license-MIT-green)
[Platform: Windows](https://img.shields.io/badge/platform-Windows-blue)

🌐 [kinak.sk](https://kinak.sk/) · ⬇️ [Stiahnuť najnovšie vydanie](https://github.com/kinakprojekcia/Kinak/releases/latest)

Kinak je projekčný softvér na vizuálne sprevádzanie liturgie: premieta texty
piesní, modlitieb, čítaní a žalmov, aby sa veriaci mohli ľahšie zapojiť do
slávenia. Počas svätej omše beží vo všetkých kostoloch v Kremnici a vznikol
ako dobrovoľnícky projekt pre našu farnosť.

[Screenshot](docs/screenshot.png)

## Prečo Kinak

Premietač počas svätej omše často žongluje s Wordom, mobilom, viacerými
stránkami s čítaniami, knižkou žalmov a lístočkom s poznámkou. Je sviatok?
Má prednosť slávnosť? Rok A, B alebo C? Párny či nepárny rok?

Univerzálne nástroje ako PowerPoint, Canva či ProPresenter na toto nestačia.
Kinak je robený priamo pre kostol a pre slovenskú liturgiu: robí jednu vec
a robí ju poriadne.

- **Ovládanie poslepiačky jedným prstom.** Napíšete číslo piesne a ďalej
  stačia klávesy: **+ / −** (ďalšia / predchádzajúca strofa), **Enter**
  (skryť / zobraziť text), **Backspace** (okamžite vypnúť projekciu).
  Počas omše netreba hľadať myš.
- **Detaily z praxe.** Veľkosť písma sa prispôsobí dĺžke textu, rezerva pre
  overscan chráni spodok textu na projektoroch, ktoré orezávajú okraje,
  farby sa menia podľa liturgického obdobia a pre Večeradlo je modrá.
- **Tmavé rozhranie**, ktoré v kostole neruší a dobre sa číta aj v šere.

Liturgický deň, žalm, čítania aj vešpery si program pripraví sám a kalendár
počíta aj bez internetu. Premietač tak má všetko na dva kliky a môže konečne
prežívať svätú omšu, nielen premietať.

## Funkcie

- **Premietanie** na druhý monitor alebo projektor (farby, veľkosť, prelínanie)
- **Piesne:** rýchle vyhľadávanie podľa čísla alebo názvu v databáze piesní
  z Jednotného katolíckeho spevníka (JKS), mládežnícke piesne a piesne
  Večeradla; vlastné piesne si môžete pridať ako textové súbory
  (pozri [Vlastné piesne](#vlastné-piesne))
- **Liturgický kalendár pre Slovensko:** automatický výpočet liturgického dňa,
  Veľkonočnej nedele (Meeus-Jones-Butcher), liturgických období, týždňa
  žaltára I–IV, liturgického roka A/B/C a cyklu I/II
- **Presuny slávení** pri kolízii s významnejším slávením (Zvestovanie,
  sv. Jozef, Narodenie Jána Krstiteľa a i.)
- **Žalmy:** v stavovom riadku zobrazí skratku žalmu podľa liturgického dňa a aktuálny týždeň žaltára v breviári. Odporúčané piesne JKS priradí podľa zvoleného žalmu (prepojenie s oknom Slávenia a Direktóriom)
- **Čítania a vešpery:** stiahnete ich na daný deň a po stiahnutí sú uložené
  v počítači (offline cache). Responzóriové žalmy stačí stiahnuť raz za rok,
  naraz na celý liturgický rok.
- **Ovládanie na diaľku:** program sa dá ovládať aj bezdrôtovou (numerickou)
  klávesnicou. Okno programu však musí byť aktívne.
- **Funguje offline:** kalendár, výpočty a piesne fungujú vždy bez internetu.
  Pripojenie treba len na stiahnutie čítaní a vešpier.

## Inštalácia (Windows)

Kinak sa neinštaluje, stačí ho rozbaliť a spustiť `Kinak.exe`.

1. Stiahnite si ZIP z [Releases](https://github.com/kinakprojekcia/Kinak/releases/latest) a rozbaľte ho.
2. Vedľa `Kinak.exe` musí byť priečinok `piesne/`:

   ```
   Kinak/                     ← rozbalený priečinok zo ZIPu, názov môže byť ľubovoľný
   ├── Kinak.exe              ← samotná aplikácia, dvojklik na spustenie
   └── piesne/                ← musí zostať vedľa Kinak.exe, nemazať
       ├── Mládež/            ← mládežnícke piesne
       ├── Večeradlo/         ← piesne Večeradla
       ├── 001.txt            ← JKS piesne
       ├── 002.txt
       ├── 003.txt
       └── …
   ```

   Priečinok môžete ľubovoľne premenovať (napr. `Kinak_v3.3`), ak zostane zachovaná táto štruktúra. Podpriečinky Mládež a Večeradlo sú súčasťou distribučného balíka. Aplikácia sa spustí aj bez nich, ale pri aktívnom filtri „Mládež“ či „Večeradlo“ sa potom zoznam piesní vľavo hore nenačíta.

3. Spustite program a v menu **Pomoc → Rýchly sprievodca** postupujte podľa pokynov.

   > **Upozornenie Windows:** pri prvom spustení sa môže zobraziť hlásenie
   > „Windows chránil váš počítač“, pretože program zatiaľ nie je digitálne
   > podpísaný. Je to bežné a nejde o chybu. Kliknite na
   > **Ďalšie informácie → Aj tak spustiť**.

4. V **Nastavenia → Umiestnenie súborov** ešte raz skontrolujte nastavenie cesty k priečinku `piesne` (napr. `Kinak_v3.3/piesne`).

## Vlastné piesne

Do priečinka `piesne/` môžete pridať vlastné piesne ako textové súbory (`.txt`).
Rovnako sa dajú pridávať aj do podpriečinkov `Mládež/` a `Večeradlo/`.

- Dodržte existujúcu štruktúru a číslovanie súborov (napr. `001.txt`, `002.txt`).
- Text existujúcich piesní môžete upravovať podľa potreby.
- Nemažte ani nepremenúvajte súbory, ktoré už v priečinku sú, a nemeňte
  štruktúru ostatných súborov, najmä skratky žalmov. Inak môže program
  piesne načítať nesprávne alebo vôbec.
- Pred úpravami odporúčame zálohovať celý priečinok `piesne/`.

## Liturgický kalendár – špecifikácia

Výpočty sa riadia smernicami pre Rímskokatolícku cirkev na Slovensku, nie
americkým modelom.

- **Krajina / provincia:** Slovensko (SK)
- **Kalendár:** všeobecný rímsky + vlastné slávenia slovenskej provincie
  (sv. Cyril a Metod 5. 7., Sedembolestná Panna Mária 15. 9. a i.)
- **Smernice:** Všeobecné normy o liturgickom roku a o kalendári + Direktórium KBS

**Kľúčový rozdiel oproti US modelu:** Zjavenie Pána je na Slovensku pevne
6. januára (prikázaný sviatok, štátny sviatok) a nepresúva sa na nedeľu.
Preto je Krst Krista Pána v nedeľu PO 6. 1., aj keď je 6. 1. nedeľa
(napr. 13. 1. 2019, 13. 1. 2030).

## Zdroje dát a licencia

- Čítania: [lc.kbs.sk](https://lc.kbs.sk/) (Konferencia biskupov Slovenska)
- Vešpery: [breviar.kbs.sk](https://breviar.kbs.sk/)
- Mládežnícke piesne: [mladeznickyspevnik.sk](http://www.mladeznickyspevnik.sk)

Obsah čítaní a vešpier nie je súčasťou programu. Sťahuje sa na požiadanie pre
osobnú potrebu farnosti a nespadá pod licenciu programu.

Program je pod [MIT License](LICENSE), © 2026 Kinak – Kremnica. Môžete ho
zdarma používať, upravovať a šíriť, aj na komerčné účely, pod podmienkou
zachovania informácie o autorovi a licencii.

## Kontakt a podpora

Chyby a nápady nahlasujte cez [Issues](https://github.com/kinakprojekcia/Kinak/issues).

Dobrovoľnícky projekt farnosti Kremnica · [kinak.sk](https://kinak.sk/)
