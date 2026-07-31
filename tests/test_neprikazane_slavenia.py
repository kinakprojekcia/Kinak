# -*- coding: utf-8 -*-

from datetime import date
import importlib.util
from pathlib import Path
import unittest
import sys
import types

# Mock tkinter pre headless prostredie
tkinter = types.ModuleType('tkinter')
tkinter.Tk = object
tkinter.PhotoImage = lambda *a, **k: None
tkinter.TclError = Exception
sys.modules['tkinter'] = tkinter

sys.modules['tkinter.font'] = types.ModuleType('tkinter.font')
sys.modules['tkinter.font'].Font = lambda *a, **k: type('Font', (), {'configure': lambda s,*a,**k: None})()

sys.modules['tkinter.ttk'] = types.ModuleType('tkinter.ttk')
sys.modules['tkinter.messagebox'] = types.ModuleType('tkinter.messagebox')
sys.modules['tkinter.colorchooser'] = types.ModuleType('tkinter.colorchooser')
sys.modules['tkinter.filedialog'] = types.ModuleType('tkinter.filedialog')

KINAK_PATH = Path(__file__).resolve().parent / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)

def datum_neprikazaneho_slavenia(rok: int, nazov: str, popis: str) -> date:
    if popis == "pohyblivý":
        pohyblive = kinak.vypocitaj_datum_pohyblivych_slaveni(rok)
        if nazov == "Turíčny pondelok":
            return pohyblive["Panny Márie, Matky Cirkvi"]
        return pohyblive[nazov]
    den_text, mesiac_text = popis.split(".")
    return date(rok, int(mesiac_text.strip()), int(den_text.strip()))

class NeprikazaneSlaveniaZobrazenieTest(unittest.TestCase):
    ROK = 2026

    OCAKAVANE = {
        "Najsvätejšie meno Ježiš": ("NMJ", "NAJSVÄTEJŠIE MENO JEŽIŠ"),
        "Obetovanie Pána (Hromnice)": ("2L", "OBETOVANIE PÁNA"),
        "Popolcová streda": ("PS", "POPOLCOVÁ STREDA"),
        "Sv. Jozefa, ženícha Panny Márie": ("3L", "SV. JOZEFA, ŽENÍCHA"),
        "Zvestovanie Pána*": ("ZV", "ZVESTOVANIE PÁNA"),
        "Pondelok vo Veľkonočnej oktáve": ("VPON", "PONDELOK VO VEĽKONOČNEJ OKTÁVE"),
        "Turíčny pondelok": ("2TS", "PANNY MÁRIE, MATKY CIRKVI"),
        "Pána Ježiša Krista, najvyššieho a večného kňaza": ("3TS", "PÁNA JEŽIŠA KRISTA, NAJVYŠŠIEHO A VEČNÉHO KŇAZA"),
        "Najsvätejšieho Srdca Ježišovho": ("6TS", "NAJSVÄTEJŠIEHO SRDCA JEŽIŠOVHO"),
        "Nepoškvrnené Srdce Panny Márie": ("7TS", "NEPOŠKVRNENÉ SRDCE PANNY MÁRIE"),
        "Narodenie sv. Jána Krstiteľa": ("NJK", "NARODENIE SV. JÁNA KRSTITEĽA"),
        "Návšteva preblahoslavenej Panny Márie": ("NAVPM", "NÁVŠTEVA PREBLAHOSLAVENEJ PANNY MÁRIE"),
        "Sv. Cyrila a Metoda, slovanských vierozvestov": ("CMV", "SV. CYRILA A METODA"),
        "Premenenie Pána": ("PREM", "PREMENENIE PÁNA"),
        "Narodenie Panny Márie": ("NPMAR", "NARODENIE PANNY MÁRIE"),
        "Povýšenie Svätého kríža": ("PSK", "POVÝŠENIE SVÄTÉHO KRÍŽA"),
        "Sedembolestnej Panny Márie, patrónky Slovenska": ("9L", "SEDEMBOLESTNEJ PANNY MÁRIE"),
        "Sv. Michala, Gabriela a Rafaela, archanieli": ("MGR", "SV. MICHALA, GABRIELA A RAFAELA, ARCHANJELI"),
        "Spomienka na Všetkých zosnulých veriacich": ("ZOS", "SPOMIENKA NA VŠETKÝCH ZOSNULÝCH VERIACICH"),
        "Výročie posviacky Lateránskej baziliky": ("VPLB", "VÝROČIE POSVIACKY LATERÁNSKEJ BAZILIKY"),
        "Sv. Štefana, prvého mučeníka": ("STEF", "SV. ŠTEFANA, PRVÉHO MUČENÍKA"),
        "Sv. Neviniatok, mučeníkov": ("NEV", "SV. NEVINIATOK, MUČENÍKOV"),
    }

    def test_vsetky_neprikazane_slavenia_su_pokryte_testom(self):
        nazvy = {n for n,_ in kinak.NEPRIKAZANE_DATA}
        self.assertEqual(set(self.OCAKAVANE), nazvy)

    def test_hlavicka_a_status_bar_pre_vsetky_neprikazane_slavenia(self):
        kolizie = []
        for nazov, popis in kinak.NEPRIKAZANE_DATA:
            with self.subTest(slavenie=nazov):
                datum = datum_neprikazaneho_slavenia(self.ROK, nazov, popis)
                skratka, text = self.OCAKAVANE[nazov]

                hlavicka = kinak.zostav_text_hlavicky("A", datum)
                status = kinak.zostav_text_status_baru(datum)

                self.assertIn("Kinak v", hlavicka)
                self.assertIn("Liturgický rok A", hlavicka)
                self.assertNotIn("Vigília:", hlavicka)
                self.assertIn("zajtra ", status)
                self.assertIn("Žaltár v breviári:", status)
                self.assertIn("týždeň", status)

                hl = hlavicka.upper()
                ma_text = text in hl
                ma_zalm = f"Žalm z {skratka}" in status

                if ma_text and ma_zalm:
                    continue
                else:
                    kolizie.append((nazov, datum, hlavicka.strip()))
                    vyssia = ["NEDEĽA","SLÁVNOSŤ","SVIATOK","VEĽKONOČNÁ","PALMOVÁ","ZELENÝ","VEĽKÝ"]
                    self.assertTrue(any(k in hl for k in vyssia),
                        msg=f"{nazov} {datum} – chýba vyššia priorita")
                    self.assertIn("Žalm z", status)

        if kolizie:
            print(f"\n[ROK {self.ROK}] Kolízie ({len(kolizie)}):")
            for n,d,h in kolizie:
                print(f" {d.isoformat()} – {n} → {h}")

    def test_sv_stefan_sa_v_hlavicke_zobrazi_ako_sviatok(self):
        d = date(self.ROK, 12, 26)
        h = kinak.zostav_text_hlavicky("A", d)
        if "ŠTEFANA" in h.upper():
            self.assertIn("SV. ŠTEFANA, PRVÉHO MUČENÍKA", h)
            self.assertIn("(Sviatok)", h)
        else:
            self.assertIn("SVÄTEJ RODINY", h.upper())
            print(f"\n[ROK {self.ROK}] 26.12. kolízia: Štefan → Svätá rodina")

if __name__ == "__main__":
    unittest.main()