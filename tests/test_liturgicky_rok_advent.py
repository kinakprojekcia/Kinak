# -*- coding: utf-8 -*-

from datetime import timedelta, date
import importlib.util
from pathlib import Path
import unittest
import sys, types

# --- mock tkinter pre headless test ---
tk = types.ModuleType("tkinter")
class _D: pass
for _n in ["Tk","Toplevel","Frame","Label","Button","Canvas","PhotoImage","StringVar","IntVar","BooleanVar","Misc","Widget"]:
    setattr(tk,_n,_D)
tk.font = types.ModuleType("tkinter.font"); tk.font.Font=_D
tk.ttk = types.ModuleType("tkinter.ttk")
for _n in ["Combobox","Progressbar","Style","Treeview","Notebook","Frame"]:
    setattr(tk.ttk,_n,_D)
tk.messagebox = types.ModuleType("tkinter.messagebox"); tk.messagebox.showerror=lambda *a,**k:None
tk.colorchooser = types.ModuleType("tkinter.colorchooser"); tk.filedialog = types.ModuleType("tkinter.filedialog")
sys.modules.update({'tkinter':tk,'tkinter.font':tk.font,'tkinter.ttk':tk.ttk,'tkinter.messagebox':tk.messagebox,'tkinter.colorchooser':tk.colorchooser,'tkinter.filedialog':tk.filedialog,'screeninfo':types.ModuleType("screeninfo")})
sys.modules['screeninfo'].get_monitors=lambda:[]

KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
if not KINAK_PATH.exists():
    KINAK_PATH = Path(__file__).resolve().parent / "Kinak.py"
if not KINAK_PATH.exists():
    KINAK_PATH = Path(__file__).resolve().parent.parent / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class LiturgickyRokAdventTest(unittest.TestCase):
    OCAKAVANE_ROKY = {
        2024: ("B", "C"),
        2025: ("C", "A"),
        2026: ("A", "B"),
        2027: ("B", "C"),
        2028: ("C", "A"),
    }

    def test_liturgicky_rok_sa_zmeni_na_prvu_adventnu_nedelu(self):
        for adventny_rok, (rok_pred_adventom, rok_od_adventu) in self.OCAKAVANE_ROKY.items():
            prva_adventna = kinak.prva_adventna_nedela(adventny_rok)
            for datum, ocakavany_rok in [
                (prva_adventna - timedelta(days=1), rok_pred_adventom),
                (prva_adventna, rok_od_adventu),
                (prva_adventna + timedelta(days=1), rok_od_adventu),
            ]:
                with self.subTest(adventny_rok=adventny_rok, datum=datum):
                    self.assertEqual(ocakavany_rok, kinak.vypocitaj_liturgicky_rok(datum))

    def test_hlavicka_okolo_adventu_obsahuje_spravny_rok_a_text(self):
        for adventny_rok, (rok_pred, rok_od) in self.OCAKAVANE_ROKY.items():
            prva = kinak.prva_adventna_nedela(adventny_rok)
            den_pred = prva - timedelta(days=1)
            hlavicka_pred = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(den_pred), den_pred)
            self.assertIn(f"Liturgický rok {rok_pred}", hlavicka_pred)
            if den_pred.month == 11 and den_pred.day == 30:
                self.assertIn("ONDREJA", hlavicka_pred.upper())
            else:
                self.assertIn("34. TÝŽDEŇ", hlavicka_pred.upper())

            hlavicka_advent = kinak.zostav_text_hlavicky(rok_od, prva)
            self.assertIn(f"Liturgický rok {rok_od}", hlavicka_advent)
            self.assertIn("1. ADVENTNÁ NEDEĽA", hlavicka_advent.upper())

    def test_sviatok_sv_ondreja_sa_vynechava_ked_pripada_na_1_adventnu_nedelu(self):
        kolizne_roky = [2025, 2031]
        for rok in kolizne_roky:
            datum = date(rok, 11, 30)
            with self.subTest(rok=rok):
                self.assertEqual(datum, kinak.prva_adventna_nedela(rok))
                self.assertEqual("1AD", kinak.vypocitaj_kod_liturgickej_casti(datum))

                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum), datum)
                self.assertIn("1. ADVENTNÁ NEDEĽA", hlavicka.upper())
                self.assertNotIn("ONDREJA", hlavicka.upper())

                status = kinak.zostav_text_status_baru(datum)
                self.assertIn("vynechaný", status.lower())
                self.assertIn("sv. ondrej", status.lower())
                self.assertIn("1. adventná nedeľa má prednosť", status.lower())

    def test_sviatok_sv_ondreja_sa_slavi_ked_nie_je_kolizia(self):
        bezne_roky = [2024, 2026, 2027, 2028, 2030]
        for rok in bezne_roky:
            datum = date(rok, 11, 30)
            with self.subTest(rok=rok):
                self.assertEqual("OND", kinak.vypocitaj_kod_liturgickej_casti(datum))

                hlavicka = kinak.zostav_text_hlavicky(kinak.vypocitaj_liturgicky_rok(datum), datum)
                self.assertIn("ONDREJA", hlavicka.upper())
                self.assertIn("SVIATOK", hlavicka.upper())

                status = kinak.zostav_text_status_baru(datum)
                self.assertNotIn("vynechaný", status.lower())
                self.assertIn("OND", status)


if __name__ == "__main__":
    unittest.main()
