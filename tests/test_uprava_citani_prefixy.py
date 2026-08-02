# -*- coding: utf-8 -*-

import importlib.util
from pathlib import Path
import tempfile
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
if not KINAK_PATH.exists():
    KINAK_PATH = Path(__file__).resolve().parent / "Kinak.py"
if not KINAK_PATH.exists():
    KINAK_PATH = Path(__file__).resolve().parent / "Kinak_1.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class UpravaCitaniPrefixyTest(unittest.TestCase):
    class FakeEntry:
        def __init__(self):
            self.focus_count = 0

        def focus_set(self):
            self.focus_count += 1

    def _app(self, folder):
        app = object.__new__(kinak.ControlApp)
        app.song_folder_path = Path(folder)
        app.manual_entry = self.FakeEntry()
        return app

    def _with_silent_messagebox(self):
        povodne_info = kinak.messagebox.showinfo
        povodne_error = kinak.messagebox.showerror
        infos = []
        errors = []
        kinak.messagebox.showinfo = lambda *args, **kwargs: infos.append((args, kwargs))
        kinak.messagebox.showerror = lambda *args, **kwargs: errors.append((args, kwargs))
        return povodne_info, povodne_error, infos, errors

    def test_uprava_citani_odstrani_hlavicky_zdroj_a_upravi_text_pre_projekciu(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            citania = folder / "citania.txt"
            citania.write_text(
                "\n".join(
                    [
                        "Pondelok 1. január",
                        "Meniny: Nový rok",
                        "==============================",
                        "Zdroj: LC KBS",
                        "Stiahnuté: 1. 1. 2026",
                        "==============================",
                        "PRVÉ ČÍTANIE",
                        "Z Knihy proroka Izaiáša",
                        "Toto je prvá veta čítania. Toto je druhá veta čítania.",
                        "Počuli sme Božie slovo.",
                        "Responzóriový žalm",
                        "R.: Pane, tvoje slová sú duch a život. Alebo: Tvoje slová, Pane, sú život.",
                        "Tento text žalmu sa nemá dostať do výstupu.",
                        "EVANJELIUM",
                        "Ježiš povedal svojim učeníkom: Pokoj vám zanechávam.",
                        "Počuli sme slovo Pánovo.",
                    ]
                ),
                encoding="utf-8",
            )

            povodne_info, povodne_error, infos, errors = self._with_silent_messagebox()
            try:
                self._app(folder).upravit_citania_pre_projekciu(max_chars=35)
            finally:
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            vysledok = citania.read_text(encoding="utf-8")
            bloky = vysledok.split("\n\n")

            self.assertTrue(infos)
            self.assertEqual(errors, [])
            self.assertNotIn("Pondelok 1. január", vysledok)
            self.assertNotIn("Meniny:", vysledok)
            self.assertNotIn("Zdroj:", vysledok)
            self.assertNotIn("Stiahnuté:", vysledok)
            self.assertNotIn("Responzóriový žalm", vysledok)
            self.assertNotIn("Tento text žalmu", vysledok)
            self.assertNotIn("Počuli sme slovo Pánovo", vysledok)

            self.assertIn("PRVÉ ČÍTANIE", bloky)
            self.assertIn("Z Knihy proroka Izaiáša", bloky)
            self.assertIn("Toto je prvá veta čítania.", bloky)
            self.assertIn("Toto je druhá veta čítania.", bloky)
            self.assertIn("Počuli sme Božie slovo.", bloky)
            self.assertIn("REFRÉN ŽALMU", bloky)
            self.assertIn("R.: Pane, tvoje slová sú duch a život", bloky)
            self.assertIn("Alebo:", bloky)
            self.assertIn("R.: Tvoje slová, Pane, sú život", bloky)

    def test_uprava_citani_bez_refrenu_ponecha_bozie_slovo_bez_refrenoveho_bloku(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            citania = folder / "citania.txt"
            citania.write_text(
                "\n".join(
                    [
                        "PRVÉ ČÍTANIE",
                        "Krátky úvod",
                        "Obsah čítania.",
                        "Počuli sme Božie slovo.",
                        "EVANJELIUM",
                        "Obsah evanjelia.",
                        "Počuli sme slovo Pánovo.",
                    ]
                ),
                encoding="utf-8",
            )

            povodne_info, povodne_error, _, _ = self._with_silent_messagebox()
            try:
                self._app(folder).upravit_citania_pre_projekciu(max_chars=80)
            finally:
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            vysledok = citania.read_text(encoding="utf-8")
            self.assertIn("Počuli sme Božie slovo.", vysledok)
            self.assertNotIn("Počuli sme slovo Pánovo", vysledok)
            self.assertNotIn("REFRÉN ŽALMU", vysledok)

    def test_uprava_citani_nedeli_nadpisy_ako_bezny_text(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            citania = folder / "citania.txt"
            nadpis = "ČÍTANIE Z KNIHY PROROKA EZECHIELA EZ 36, 16 -17A. 18-28"
            citania.write_text(
                "\n".join(
                    [
                        nadpis,
                        "Vylejem na vás čistú vodu a dám vám nové srdce",
                        "Text čítania.",
                        "Počuli sme Božie slovo.",
                        "EVANJELIUM",
                        "Text evanjelia.",
                    ]
                ),
                encoding="utf-8",
            )

            povodne_info, povodne_error, _, _ = self._with_silent_messagebox()
            try:
                self._app(folder).upravit_citania_pre_projekciu(max_chars=20)
            finally:
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            bloky = citania.read_text(encoding="utf-8").split("\n\n")

            self.assertIn(nadpis, bloky)
            self.assertNotIn("ČÍTANIE Z KNIHY", bloky)
            self.assertNotIn("PROROKA EZECHIELA", bloky)

    def test_uprava_citani_nezdvoji_opakovany_refren(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            citania = folder / "citania.txt"
            citania.write_text(
                "\n".join(
                    [
                        "PRVÉ ČÍTANIE",
                        "Text čítania.",
                        "Počuli sme Božie slovo.",
                        "EVANJELIUM",
                        "Text evanjelia.",
                        "REFRÉN ŽALMU",
                        "R.: Pane, tvoje slová sú duch a život.",
                        "REFRÉN ŽALMU",
                        "R.: Pane, tvoje slová sú duch a život.",
                    ]
                ),
                encoding="utf-8",
            )

            povodne_info, povodne_error, _, _ = self._with_silent_messagebox()
            try:
                self._app(folder).upravit_citania_pre_projekciu(max_chars=80)
            finally:
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            vysledok = citania.read_text(encoding="utf-8")

            self.assertEqual(1, vysledok.count("REFRÉN ŽALMU"))
            self.assertEqual(1, vysledok.count("R.: Pane, tvoje slová sú duch a život"))

    def test_uprava_citani_poculi_sme_bozie_slovo_je_samostatny_blok(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            citania = folder / "citania.txt"
            citania.write_text(
                "\n".join(
                    [
                        "PRVÉ ČÍTANIE",
                        "Obsah čítania. Počuli sme Božie slovo.",
                        "EVANJELIUM",
                        "Text evanjelia.",
                    ]
                ),
                encoding="utf-8",
            )

            povodne_info, povodne_error, _, _ = self._with_silent_messagebox()
            try:
                self._app(folder).upravit_citania_pre_projekciu(max_chars=80)
            finally:
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            bloky = citania.read_text(encoding="utf-8").split("\n\n")

            self.assertIn("Počuli sme Božie slovo.", bloky)

    def test_uprava_citani_pre_velkonocnu_vigiliu_zachova_viac_refrenov(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            citania = folder / "citania.txt"
            citania.write_text(
                "\n".join(
                    [
                        "ČÍTANIA NA SVÄTÚ OMŠU",
                        "04.04.2026",
                        "ZAČIATOK KNIHY GENEZIS",
                        "Text prvého čítania.",
                        "Počuli sme Božie slovo.",
                        "ČÍTANIE Z KNIHY EXODUS",
                        "Text druhého čítania.",
                        "Počuli sme Božie slovo.",
                        "ČÍTANIE Z LISTU SVÄTÉHO APOŠTOLA PAVLA RIMANOM",
                        "Text epištoly.",
                        "Počuli sme Božie slovo.",
                        "EVANJELIUM",
                        "Text evanjelia.",
                        "Počuli sme slovo Pánovo.",
                        "REFRÉN ŽALMU",
                        "R.: Pane, zošli svojho Ducha a obnov tvárnosť zeme.",
                        "REFRÉN ŽALMU",
                        "R.: Spievajme Pánovi, lebo sa preslávil.",
                        "REFRÉN ŽALMU",
                        "R.: Aleluja.",
                    ]
                ),
                encoding="utf-8",
            )

            povodne_info, povodne_error, _, _ = self._with_silent_messagebox()
            try:
                self._app(folder).upravit_citania_pre_projekciu(max_chars=80)
            finally:
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            vysledok = citania.read_text(encoding="utf-8")

            self.assertEqual(3, vysledok.count("REFRÉN ŽALMU"))
            self.assertIn("R.: Pane, zošli svojho Ducha a obnov tvárnosť zeme", vysledok)
            self.assertIn("R.: Spievajme Pánovi, lebo sa preslávil", vysledok)
            self.assertIn("R.: Aleluja", vysledok)

    def test_uprava_citani_zachova_poradie_refrenov_po_citaniach(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            citania = folder / "citania.txt"
            citania.write_text(
                "\n".join(
                    [
                        "PRVÉ ČÍTANIE",
                        "Text prvého čítania.",
                        "Počuli sme Božie slovo.",
                        "DRUHÉ ČÍTANIE",
                        "Text druhého čítania.",
                        "Počuli sme Božie slovo.",
                        "EVANJELIUM",
                        "Text evanjelia.",
                        "Počuli sme slovo Pánovo.",
                        "REFRÉN ŽALMU",
                        "R.: Prvý refrén.",
                        "REFRÉN ŽALMU",
                        "R.: Druhý refrén.",
                    ]
                ),
                encoding="utf-8",
            )

            povodne_info, povodne_error, _, _ = self._with_silent_messagebox()
            try:
                self._app(folder).upravit_citania_pre_projekciu(max_chars=80)
            finally:
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            vysledok = citania.read_text(encoding="utf-8")

            self.assertLess(vysledok.index("PRVÉ ČÍTANIE"), vysledok.index("R.: Prvý refrén"))
            self.assertLess(vysledok.index("R.: Prvý refrén"), vysledok.index("DRUHÉ ČÍTANIE"))
            self.assertLess(vysledok.index("DRUHÉ ČÍTANIE"), vysledok.index("R.: Druhý refrén"))
            self.assertLess(vysledok.index("R.: Druhý refrén"), vysledok.index("EVANJELIUM"))

    def test_uprava_citani_zachova_aleluja_po_epistole_pred_evanjeliom(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            citania = folder / "citania.txt"
            citania.write_text(
                "\n".join(
                    [
                        "ČÍTANIE Z LISTU SVÄTÉHO APOŠTOLA PAVLA RIMANOM",
                        "Kristus vzkriesený z mŕtvych už neumiera.",
                        "Počuli sme Božie slovo.",
                        "EVANJELIUM",
                        "Vstal z mŕtvych a ide pred vami do Galiley.",
                        "Počuli sme slovo Pánovo.",
                        "REFRÉN ŽALMU",
                        "R.: Aleluja.",
                    ]
                ),
                encoding="utf-8",
            )

            povodne_info, povodne_error, _, _ = self._with_silent_messagebox()
            try:
                self._app(folder).upravit_citania_pre_projekciu(max_chars=80)
            finally:
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            vysledok = citania.read_text(encoding="utf-8")

            self.assertIn("R.: Aleluja", vysledok)
            self.assertLess(vysledok.index("ČÍTANIE Z LISTU"), vysledok.index("R.: Aleluja"))
            self.assertLess(vysledok.index("R.: Aleluja"), vysledok.index("EVANJELIUM"))

    def test_uprava_citani_na_realnom_formate_vigilie_zachova_vsetky_refrenove_bloky(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            citania = folder / "citania.txt"
            citania.write_text(
                "\n".join(
                    [
                        "ČÍTANIA NA SVÄTÚ OMŠU",
                        "04.04.2026",
                        "Biela sobota",
                        "",
                        "ZAČIATOK KNIHY GENEZIS GN 1, 1 – 2, 2",
                        "",
                        "Boh videl všetko, čo urobil, a bolo to veľmi dobré",
                        "",
                        "Text prvého čítania.",
                        "",
                        "Počuli sme Božie slovo.",
                        "",
                        "REFRÉN ŽALMU",
                        "",
                        "R.: Pane, zošli svojho Ducha a obnov tvárnosť zeme",
                        "",
                        "ČÍTANIE Z KNIHY GENEZIS GN 22, 1 -18",
                        "",
                        "Obeta nášho praotca Abraháma",
                        "",
                        "Text druhého čítania.",
                        "",
                        "Počuli sme Božie slovo.",
                        "",
                        "REFRÉN ŽALMU",
                        "",
                        "R.: Ochráň ma, Bože, k tebe sa utiekam",
                        "",
                        "ČÍTANIE Z LISTU SVÄTÉHO APOŠTOLA PAVLA RIMANOM RIM 6, 3 -11",
                        "",
                        "Kristus vzkriesený z mŕtvych už neumiera",
                        "",
                        "Text epištoly.",
                        "",
                        "Počuli sme Božie slovo.",
                        "",
                        "REFRÉN ŽALMU",
                        "",
                        "R.: Aleluja",
                        "",
                        "ČÍTANIE ZO SVÄTÉHO EVANJELIA PODĽA MATÚŠA MT 28, 1 -10",
                        "",
                        "Vstal z mŕtvych a ide pred vami do Galiley",
                        "",
                        "Text evanjelia.",
                    ]
                ),
                encoding="utf-8",
            )

            povodne_info, povodne_error, _, _ = self._with_silent_messagebox()
            try:
                self._app(folder).upravit_citania_pre_projekciu(max_chars=80)
            finally:
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            vysledok = citania.read_text(encoding="utf-8")

            self.assertEqual(3, vysledok.count("REFRÉN ŽALMU"))
            self.assertIn("R.: Pane, zošli svojho Ducha a obnov tvárnosť zeme", vysledok)
            self.assertIn("R.: Ochráň ma, Bože, k tebe sa utiekam", vysledok)
            self.assertIn("R.: Aleluja", vysledok)
            self.assertLess(vysledok.index("R.: Pane"), vysledok.index("ČÍTANIE Z KNIHY GENEZIS GN 22"))
            self.assertLess(vysledok.index("R.: Ochráň"), vysledok.index("ČÍTANIE Z LISTU"))
            self.assertLess(vysledok.index("R.: Aleluja"), vysledok.index("ČÍTANIE ZO SVÄTÉHO EVANJELIA"))

    def test_vyhladavanie_piesne_podla_prefixu_uprednostni_presnu_ciselnu_zhodu(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "001 nieco.txt").write_text("variant s nazvom", encoding="utf-8")
            (folder / "001.txt").write_text("presna zhoda", encoding="utf-8")
            (folder / "001a.txt").write_text("variant a", encoding="utf-8")

            self.assertEqual(self._app(folder).najdi_subor_podla_prefixu("001"), "001.txt")
            self.assertEqual(self._app(folder).najdi_subor_podla_prefixu("1"), "001.txt")

    def test_vyhladavanie_piesne_podla_prefixu_najde_variant_a_normalizuje_diakritiku(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "001.txt").write_text("presna zhoda", encoding="utf-8")
            (folder / "001a.txt").write_text("variant a", encoding="utf-8")
            (folder / "002a Červený kvet.txt").write_text("variant s diakritikou", encoding="utf-8")
            (folder / "Citáty svätých.txt").write_text("text", encoding="utf-8")

            app = self._app(folder)

            self.assertEqual(app.najdi_subor_podla_prefixu("001a"), "001a.txt")
            self.assertEqual(app.najdi_subor_podla_prefixu("002a"), "002a Červený kvet.txt")
            self.assertEqual(app.najdi_subor_podla_prefixu("cerveny"), "002a Červený kvet.txt")
            self.assertEqual(app.najdi_subor_podla_prefixu("citat"), "Citáty svätých.txt")


if __name__ == "__main__":
    unittest.main()
