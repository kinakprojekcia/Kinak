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


class FakeLabel:
    def __init__(self):
        self.config_calls = []
        self.text = ""
        self.fg = None

    def config(self, **kwargs):
        self.config_calls.append(kwargs)
        if "text" in kwargs:
            self.text = kwargs["text"]
        if "fg" in kwargs:
            self.fg = kwargs["fg"]


class FakeTextWidget:
    def __init__(self):
        self.content = ""

    def config(self, **kwargs):
        pass

    def delete(self, *args):
        self.content = ""

    def insert(self, index, text):
        self.content += text

    def tag_remove(self, *args):
        pass


class FakeProjectionWindow:
    def __init__(self):
        self.text_updates = []
        self.title_updates = []

    def update_text(self, text):
        self.text_updates.append(text)

    def update_title(self, *args, **kwargs):
        self.title_updates.append((args, kwargs))


class FakeEntry:
    def __init__(self):
        self.deleted = False
        self.focus_count = 0

    def delete(self, *args):
        self.deleted = True

    def focus_set(self):
        self.focus_count += 1


class FakeCombobox:
    def __init__(self):
        self.current_values = []

    def current(self, value):
        self.current_values.append(value)


class FakeVar:
    def __init__(self, value="—"):
        self.value = value

    def set(self, value):
        self.value = value

    def get(self):
        return self.value


class FakeMaster:
    def __init__(self):
        self.after_idle_calls = 0
        self.after_calls = []

    def after_idle(self, callback):
        self.after_idle_calls += 1
        callback()

    def after(self, delay, callback):
        self.after_calls.append(delay)
        callback()


class OdporucanePiesneChyboveSuboryTest(unittest.TestCase):
    def _app(self, folder):
        app = object.__new__(kinak.ControlApp)
        app.song_folder_path = Path(folder)
        app.aktualny_index_strofa = 0
        app.aktualne_strofy = []
        app.nazov_piesne = None
        app.aktualne_cislo_piesne = ""
        app.is_text_visible = False
        app.popisy_suborov = {"2AD": "2. adventná nedeľa"}
        app.subor_var = FakeVar()
        app.manual_entry = FakeEntry()
        app.song_combobox = FakeCombobox()
        app.popis_label = FakeLabel()
        app.direktorium_label = FakeLabel()
        app.obsah_suboru_text = FakeTextWidget()
        app.projection_window = FakeProjectionWindow()
        app.master = FakeMaster()
        app.zobrazene_strofy = []
        app.indikatory = []

        app.aktualizuj_popis = lambda nazov: setattr(app, "posledny_popis", nazov)
        app._update_nazov_label = lambda: setattr(app, "nazov_label_update", True)
        app.zobraz_aktualnu_strofu = lambda: app.zobrazene_strofy.append(app.aktualny_index_strofa)
        app.oznac_aktualnu_strofu_v_obsahu = lambda: setattr(app, "oznacena_strofa", app.aktualny_index_strofa)
        app.set_projection_indicator = lambda hodnota: app.indikatory.append(hodnota)
        app.vypni_projekciu = lambda: setattr(app, "projekcia_vypnuta", True)
        return app

    def test_vyber_odporucanej_piesne_z_menu_najde_subor_nacita_strofy_a_direktorium(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            obsah = "Druhá adventná pieseň\n\nR.: Príď, Pane Ježišu"
            (folder / "2AD.txt").write_text(obsah, encoding="utf-8")

            app = self._app(folder)
            app.nacitat_podla_menu("2AD")

            self.assertEqual(app.subor_var.get(), "2AD")
            self.assertTrue(app.manual_entry.deleted)
            self.assertEqual(app.song_combobox.current_values, [0])
            self.assertEqual(app.nazov_piesne, "2AD")
            self.assertEqual(app.aktualne_cislo_piesne, "2AD")
            self.assertEqual(
                app.aktualne_strofy,
                ["", "Druhá adventná pieseň", "R.: Príď, Pane Ježišu"],
            )
            self.assertEqual(app.obsah_suboru_text.content, obsah)
            self.assertEqual(app.zobrazene_strofy, [0])
            self.assertEqual(app.indikatory, [False])
            self.assertEqual(app.popis_label.text, "Žalmy pre 2. adventná nedeľa")
            self.assertIn("Odporúčané piesne:", app.direktorium_label.text)
            self.assertIn("Úvod: 16, 1-2", app.direktorium_label.text)
            self.assertEqual(app.manual_entry.focus_count, 1)

    def test_prazdny_txt_sa_nacita_ako_nulta_strofa_bez_realnych_strof(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "777.txt").write_text("", encoding="utf-8")

            app = self._app(folder)
            app.nacitat_piesne("777")

            self.assertEqual(app.aktualne_strofy, [""])
            self.assertEqual(app.aktualny_index_strofa, 0)
            self.assertEqual(app.obsah_suboru_text.content, "")
            self.assertEqual(app.zobrazene_strofy, [0])

    def test_neexistujuci_priecinok_vrati_prazdny_zoznam_a_nenajde_subor(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "neexistuje"
            app = self._app(folder)
            app.aktualne_strofy = ["", "Pôvodný text"]

            self.assertEqual(app.nacitaj_piesne_do_zoznamu_z_priecinka(), [])
            self.assertIsNone(app.najdi_subor_podla_prefixu("001"))

            app.nacitat_piesne("001")
            self.assertEqual(app.aktualne_strofy, ["", "Pôvodný text"])

    def test_poskodene_kodovanie_neprepise_aktualne_strofy(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "888.txt").write_bytes(b"\x81\x81\x81")
            app = self._app(folder)
            app.aktualne_strofy = ["", "Pôvodná strofa"]

            app.nacitat_piesne("888")

            self.assertEqual(app.aktualne_strofy, ["", "Pôvodná strofa"])
            self.assertEqual(app.obsah_suboru_text.content, "")

    def test_necitatelny_subor_neprepise_aktualne_strofy(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "999.txt").write_text("Tento text sa nema nacitat", encoding="utf-8")
            app = self._app(folder)
            app.aktualne_strofy = ["", "Pôvodná strofa"]

            povodne_read_text = Path.read_text

            def read_text_s_chybou(path_obj, *args, **kwargs):
                if path_obj.name == "999.txt":
                    raise PermissionError("subor je zamknuty")
                return povodne_read_text(path_obj, *args, **kwargs)

            Path.read_text = read_text_s_chybou
            try:
                app.nacitat_piesne("999")
            finally:
                Path.read_text = povodne_read_text

            self.assertEqual(app.aktualne_strofy, ["", "Pôvodná strofa"])
            self.assertEqual(app.obsah_suboru_text.content, "")


if __name__ == "__main__":
    unittest.main()
