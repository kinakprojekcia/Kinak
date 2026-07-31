# -*- coding: utf-8 -*-

import importlib.util
from pathlib import Path
import tempfile
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class FakeTextWidget:
    def __init__(self):
        self.content = ""
        self.states = []
        self.removed_tags = []

    def config(self, **kwargs):
        if "state" in kwargs:
            self.states.append(kwargs["state"])

    def delete(self, *args):
        self.content = ""

    def insert(self, index, text):
        self.content += text

    def tag_remove(self, *args):
        self.removed_tags.append(args)


class FakeProjectionWindow:
    def __init__(self):
        self.text_updates = []
        self.title_updates = []

    def update_text(self, text):
        self.text_updates.append(text)

    def update_title(self, **kwargs):
        self.title_updates.append(kwargs)


class NacitaniePiesniStrofyTest(unittest.TestCase):
    def _app(self, folder):
        app = object.__new__(kinak.ControlApp)
        app.song_folder_path = Path(folder)
        app.aktualny_index_strofa = 0
        app.aktualne_strofy = []
        app.nazov_piesne = None
        app.obsah_suboru_text = FakeTextWidget()
        app.projection_window = FakeProjectionWindow()
        app.zobrazene_strofy = []
        app.indikatory = []

        app.aktualizuj_popis = lambda nazov: setattr(app, "posledny_popis", nazov)
        app._update_nazov_label = lambda: setattr(app, "nazov_label_update", True)
        app.zobraz_aktualnu_strofu = lambda: app.zobrazene_strofy.append(app.aktualny_index_strofa)
        app.oznac_aktualnu_strofu_v_obsahu = lambda: setattr(app, "oznacena_strofa", app.aktualny_index_strofa)
        app.set_projection_indicator = lambda hodnota: app.indikatory.append(hodnota)

        return app

    def test_zoznam_piesni_berie_prvy_neprazdny_riadok_a_triedi_varianty(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "002.txt").write_text("\nDruhá pieseň\ntext", encoding="utf-8")
            (folder / "001a.txt").write_bytes("Pieseň vo variante\ntext".encode("cp1250"))
            (folder / "Glória.txt").write_text("Glória\ntext", encoding="utf-8")

            app = self._app(folder)

            self.assertEqual(
                app.nacitaj_piesne_do_zoznamu_z_priecinka(),
                [("001a", "Pieseň vo variante"), ("002", "Druhá pieseň")],
            )

    def test_nacitanie_piesne_rozdeli_obsah_na_strofy_podla_prazdnych_riadkov(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            obsah = (
                "Nadpis piesne\n"
                "prvý riadok\n"
                "\n"
                "R.: refrén piesne\n"
                "\n"
                "Druhá strofa\n"
                "ďalší riadok\n"
            )
            (folder / "123 Moja pieseň.txt").write_text(obsah, encoding="utf-8")

            app = self._app(folder)
            app.nacitat_piesne("123")

            self.assertEqual(
                app.aktualne_strofy,
                [
                    "",
                    "Nadpis piesne\nprvý riadok",
                    "R.: refrén piesne",
                    "Druhá strofa\nďalší riadok",
                ],
            )
            self.assertEqual(app.aktualny_index_strofa, 0)
            self.assertEqual(app.nazov_piesne, "123")
            self.assertEqual(app.aktualne_cislo_piesne, "123")
            self.assertEqual(app.obsah_suboru_text.content, obsah)
            self.assertEqual(app.zobrazene_strofy, [0])
            self.assertEqual(app.indikatory, [False])

    def test_nacitanie_piesne_podla_cisla_1_001_a_variantu_001a(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "001.txt").write_text("Prvá pieseň\n\nR.: Aleluja", encoding="utf-8")
            (folder / "001a.txt").write_text("Variant piesne\n\nR.: Iný refrén", encoding="utf-8")

            app = self._app(folder)

            app.nacitat_piesne("1")
            self.assertEqual(app.aktualne_strofy, ["", "Prvá pieseň", "R.: Aleluja"])
            self.assertEqual(app.nazov_piesne, "1")

            app.nacitat_piesne("001")
            self.assertEqual(app.aktualne_strofy, ["", "Prvá pieseň", "R.: Aleluja"])
            self.assertEqual(app.nazov_piesne, "001")

            app.nacitat_piesne("001a")
            self.assertEqual(app.aktualne_strofy, ["", "Variant piesne", "R.: Iný refrén"])
            self.assertEqual(app.nazov_piesne, "001a")

    def test_nacitanie_piesne_s_diakritikou_v_nazve_suboru(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            obsah = "Červený kvet ľúbezne vonia\n\nŽalm: Chváľte Pána, všetky národy"
            (folder / "002a Červený kvet.txt").write_text(obsah, encoding="utf-8")

            app = self._app(folder)
            app.nacitat_piesne("cerveny")

            self.assertEqual(
                app.aktualne_strofy,
                ["", "Červený kvet ľúbezne vonia", "Žalm: Chváľte Pána, všetky národy"],
            )
            self.assertEqual(app.obsah_suboru_text.content, obsah)

    def test_nacitanie_piesne_podporuje_cp1250_subory(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            obsah = "Pieseň č. 124\n\nĎalšia strofa"
            (folder / "124.txt").write_bytes(obsah.encode("cp1250"))

            app = self._app(folder)
            app.nacitat_piesne("124")

            self.assertEqual(app.aktualne_strofy, ["", "Pieseň č. 124", "Ďalšia strofa"])
            self.assertEqual(app.obsah_suboru_text.content, obsah)

    def test_prazdny_subor_a_subor_len_s_nadpisom_sa_nacitaju_bez_padu(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "130.txt").write_text("", encoding="utf-8")
            (folder / "131.txt").write_text("Len nadpis piesne\n", encoding="utf-8")

            app = self._app(folder)

            app.nacitat_piesne("130")
            self.assertEqual(app.aktualne_strofy, [""])
            self.assertEqual(app.obsah_suboru_text.content, "")

            app.nacitat_piesne("131")
            self.assertEqual(app.aktualne_strofy, ["", "Len nadpis piesne"])
            self.assertEqual(app.obsah_suboru_text.content, "Len nadpis piesne\n")

    def test_rozpoznanie_strof_refrenov_a_sloh_s_lomkami(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            obsah = (
                "1. sloha / alternatíva\n"
                "druhý riadok slohy\n"
                "\n"
                "R.: Refrén / opakovanie\n"
                "\n"
                "2. sloha\n"
                "ďalší text / odpoveď ľudu\n"
            )
            (folder / "132.txt").write_text(obsah, encoding="utf-8")

            app = self._app(folder)
            app.nacitat_piesne("132")

            self.assertEqual(
                app.aktualne_strofy,
                [
                    "",
                    "1. sloha / alternatíva\ndruhý riadok slohy",
                    "R.: Refrén / opakovanie",
                    "2. sloha\nďalší text / odpoveď ľudu",
                ],
            )

    def test_slovenske_znaky_sa_zachovaju_pri_citani_a_atomickom_zapise(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            obsah = "Ľúbostná pieseň č. 133\n\nR.: Ó, chváľme Pána žalmom"
            cesta = folder / "133.txt"

            kinak._zapis_text_atomicky(cesta, obsah, encoding="utf-8")

            self.assertEqual(cesta.read_text(encoding="utf-8"), obsah)

            app = self._app(folder)
            app.nacitat_piesne("133")
            self.assertEqual(app.obsah_suboru_text.content, obsah)
            self.assertEqual(
                app.aktualne_strofy,
                ["", "Ľúbostná pieseň č. 133", "R.: Ó, chváľme Pána žalmom"],
            )

    def test_opakovane_nacitanie_rovnakej_piesne_zachova_aktualnu_strofu(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "125.txt").write_text("Prvá\n\nDruhá\n\nTretia", encoding="utf-8")
            (folder / "126.txt").write_text("Iná pieseň\n\nDruhá", encoding="utf-8")

            app = self._app(folder)
            app.nacitat_piesne("125")
            app.aktualny_index_strofa = 2

            app.nacitat_piesne("125")
            self.assertEqual(app.aktualny_index_strofa, 2)

            app.nacitat_piesne("126")
            self.assertEqual(app.aktualny_index_strofa, 0)

    def test_specialne_textove_subory_sa_daju_nacitat_podla_nazvu(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            gloria = "Sláva Bohu na výsostiach\n\nA na zemi pokoj ľuďom dobrej vôle."
            credo = "Verím v jedného Boha\n\nOtca všemohúceho."
            (folder / "Glória.txt").write_text(gloria, encoding="utf-8")
            (folder / "KRÉDO.txt").write_text(credo, encoding="utf-8")

            app = self._app(folder)
            app.nacitat_piesne("Glória")
            self.assertEqual(
                app.aktualne_strofy,
                ["", "Sláva Bohu na výsostiach", "A na zemi pokoj ľuďom dobrej vôle."],
            )

            app.nacitat_piesne("KRÉDO")
            self.assertEqual(
                app.aktualne_strofy,
                ["", "Verím v jedného Boha", "Otca všemohúceho."],
            )

    def test_chybajuci_subor_neprepise_aktualne_strofy(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app(Path(temp))
            app.aktualne_strofy = ["", "Pôvodná strofa"]

            app.nacitat_piesne("999")

            self.assertEqual(app.aktualne_strofy, ["", "Pôvodná strofa"])


if __name__ == "__main__":
    unittest.main()
