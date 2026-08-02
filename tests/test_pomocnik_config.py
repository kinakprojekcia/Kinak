# -*- coding: utf-8 -*-

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class FakeVar:
    def __init__(self, value=None, *args, **kwargs):
        self.value = kwargs.get("value", value)

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeManualEntry:
    def __init__(self):
        self.focus_count = 0

    def focus_set(self):
        self.focus_count += 1


class FakeMaster:
    def __init__(self):
        self.bindings = {}
        self.after_ids = []

    def winfo_screenwidth(self):
        return 1280

    def winfo_screenheight(self):
        return 900

    def after(self, delay, callback):
        after_id = f"after-{len(self.after_ids) + 1}"
        self.after_ids.append(after_id)
        callback()
        return after_id

    def after_cancel(self, after_id):
        pass

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def winfo_exists(self):
        return True


class FakeToplevel:
    def __init__(self, master=None):
        self.master = master
        self.protocols = {}
        self.bindings = {}
        self.exists = True
        self.geometry_value = None
        self.focus_count = 0

    def transient(self, master):
        self.master = master

    def title(self, text):
        self.title_text = text

    def configure(self, **kwargs):
        self.configure_kwargs = kwargs

    def protocol(self, name, callback):
        self.protocols[name] = callback

    def geometry(self, value):
        self.geometry_value = value

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def unbind(self, sequence):
        self.bindings.pop(sequence, None)

    def winfo_exists(self):
        return self.exists

    def winfo_x(self):
        return 100

    def winfo_y(self):
        return 110

    def winfo_width(self):
        return 550

    def winfo_height(self):
        return 540

    def deiconify(self):
        pass

    def lift(self):
        pass

    def focus_set(self):
        self.focus_count += 1

    def destroy(self):
        self.exists = False


class FakeWidget:
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.config_calls = []
        self.bindings = {}
        self.packed = False

    def pack(self, *args, **kwargs):
        self.packed = True

    def grid(self, *args, **kwargs):
        self.gridded = True

    def pack_forget(self):
        self.packed = False

    def pack_propagate(self, flag):
        self.pack_propagate_flag = flag

    def config(self, **kwargs):
        self.config_calls.append(kwargs)
        self.kwargs.update(kwargs)

    def configure(self, **kwargs):
        self.config(**kwargs)

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback


class FakeButton(FakeWidget):
    def invoke(self):
        command = self.kwargs.get("command")
        if command:
            return command()
        return None


class FakeText(FakeWidget):
    instances = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = ""
        self.state = kwargs.get("state")
        self.undo = kwargs.get("undo")
        FakeText.instances.append(self)

    def insert(self, index, text):
        self.text += text

    def get(self, start, end):
        if end == "end-1c":
            return self.text
        return self.text

    def config(self, **kwargs):
        super().config(**kwargs)
        if "state" in kwargs:
            self.state = kwargs["state"]

    def tag_ranges(self, tag):
        return []

    def delete(self, start, end=None):
        if self.text:
            self.text = self.text[:-1]


class FakeLabel(FakeWidget):
    pass


class PomocnikConfigTest(unittest.TestCase):
    def _patch_tk_for_pomocnik(self):
        FakeText.instances = []
        originals = {
            "Toplevel": kinak.tk.Toplevel,
            "Frame": kinak.tk.Frame,
            "Label": kinak.tk.Label,
            "Text": kinak.tk.Text,
            "IntVar": kinak.tk.IntVar,
            "Button": kinak.tk.Button,
        }
        kinak.tk.Toplevel = FakeToplevel
        kinak.tk.Frame = FakeWidget
        kinak.tk.Label = FakeLabel
        kinak.tk.Text = FakeText
        kinak.tk.IntVar = FakeVar
        kinak.tk.Button = FakeButton
        return originals

    def _restore_tk(self, originals):
        for name, value in originals.items():
            setattr(kinak.tk, name, value)

    def _minimal_app(self, song_folder):
        app = object.__new__(kinak.ControlApp)
        app.master = FakeMaster()
        app.song_folder_path = Path(song_folder)
        app.manual_entry = FakeManualEntry()
        app.pomocnik_font_size = 14
        app.pomocnik_x = -1
        app.pomocnik_y = -1
        app.pomocnik_width = -1
        app.pomocnik_height = -1
        app.pomocnik_last_tab = 3
        app.pomocnik_okno = None
        app.potvrdit_ukoncenie = lambda event=None: "break"
        app.ulozenia_nastaveni = 0
        app.ulozit_nastavenia = lambda *args, **kwargs: setattr(
            app, "ulozenia_nastaveni", app.ulozenia_nastaveni + 1
        )
        return app

    def _config_app(self, song_folder):
        app = object.__new__(kinak.ControlApp)
        app._loading_settings = False
        app.master = FakeMaster()
        app.font_size = 48
        app.font_size_var = FakeVar(48)
        app.text_color_var = FakeVar("#abcdef")
        app.zobrazit_direktorium_var = FakeVar(False)
        app.fade_speed_var = FakeVar("mierne rýchle")
        app.zobrazovat_live_preview_var = FakeVar(True)
        app.zobrazovat_specialne_znaky_var = FakeVar(False)
        app.zobrazovat_znaky_chorov_var = FakeVar(False)
        app.statusbar_tyzden_zaltara_var = FakeVar(False)
        app.statusbar_skratka_zalmu_var = FakeVar(False)
        app.statusbar_jks_piesne_var = FakeVar(True)
        app.bottom_margin_var = FakeVar(44)
        app.reserved_vertical_var = FakeVar(0.25)
        app.pouzit_vlastnu_farbu = FakeVar(True)
        app.obdobie_var = FakeVar("Cezročné")
        app.default_filter_var = FakeVar("Cezročné C2")
        app.liturgical_year_var = FakeVar("A")
        app.song_folder_path = Path(song_folder)
        app.pomocnik_font_size = 14
        app.pomocnik_x = -1
        app.pomocnik_y = -1
        app.pomocnik_width = -1
        app.pomocnik_height = -1
        app.pomocnik_last_tab = 0
        app.song_folder_label = FakeLabel()
        app.folder_label = FakeLabel()
        app.projection_window = None
        app.aktualizovat_status_bar = lambda: None
        app.aktualizovat_info_liturgickeho_roka = lambda rok: setattr(app, "info_rok", rok)
        return app

    def _patch_config_paths(self, temp_root, song_folder):
        originals = {
            "CONFIG_FILE_PATH": kinak.CONFIG_FILE_PATH,
            "BASE_DIR": kinak.BASE_DIR,
            "DEFAULT_CONFIG": kinak.DEFAULT_CONFIG,
        }
        default_config = {**kinak.DEFAULT_CONFIG, "song_folder": str(song_folder)}
        kinak.CONFIG_FILE_PATH = Path(temp_root) / "config.json"
        kinak.BASE_DIR = Path(temp_root)
        kinak.DEFAULT_CONFIG = default_config
        return originals

    def _restore_config_paths(self, originals):
        kinak.CONFIG_FILE_PATH = originals["CONFIG_FILE_PATH"]
        kinak.BASE_DIR = originals["BASE_DIR"]
        kinak.DEFAULT_CONFIG = originals["DEFAULT_CONFIG"]

    def _patch_messagebox(self, odpoved=True):
        originals = {
            "askyesno": kinak.messagebox.askyesno,
            "showinfo": kinak.messagebox.showinfo,
            "showerror": kinak.messagebox.showerror,
        }
        calls = {"askyesno": [], "showinfo": [], "showerror": []}
        kinak.messagebox.askyesno = lambda *args, **kwargs: calls["askyesno"].append((args, kwargs)) or odpoved
        kinak.messagebox.showinfo = lambda *args, **kwargs: calls["showinfo"].append((args, kwargs))
        kinak.messagebox.showerror = lambda *args, **kwargs: calls["showerror"].append((args, kwargs))
        return originals, calls

    def _restore_messagebox(self, originals):
        kinak.messagebox.askyesno = originals["askyesno"]
        kinak.messagebox.showinfo = originals["showinfo"]
        kinak.messagebox.showerror = originals["showerror"]

    def test_pomocnik_nacita_texty_a_urobi_citania_vespery_editovatelne(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "1 Poznámky.txt").write_text("Prvé poznámky", encoding="utf-8")
            (folder / "2 Poznámky.txt").write_text("Druhé poznámky", encoding="utf-8")
            (folder / "citania.txt").write_text("Pôvodné čítania", encoding="utf-8")
            (folder / "vespery.txt").write_text("Pôvodné vešpery", encoding="utf-8")
            app = self._minimal_app(folder)
            originals = self._patch_tk_for_pomocnik()
            try:
                app.otvorit_pomocnika()
            finally:
                self._restore_tk(originals)

            self.assertGreaterEqual(len(FakeText.instances), 5)
            text1, text2, text3, text4 = FakeText.instances[:4]
            self.assertEqual(text1.get("1.0", "end-1c"), "Prvé poznámky")
            self.assertEqual(text2.get("1.0", "end-1c"), "Druhé poznámky")
            self.assertEqual(text3.get("1.0", "end-1c"), "Pôvodné čítania")
            self.assertEqual(text4.get("1.0", "end-1c"), "Pôvodné vešpery")
            self.assertEqual(text1.state, kinak.tk.DISABLED)
            self.assertEqual(text2.state, kinak.tk.DISABLED)
            self.assertFalse(text1.undo)
            self.assertFalse(text2.undo)
            self.assertTrue(text3.undo)
            self.assertTrue(text4.undo)
            self.assertIn("<Button-1>", text1.bindings)
            self.assertIn("<KeyRelease>", text3.bindings)
            self.assertIn("<KeyRelease>", text4.bindings)

    def test_pomocnik_uklada_citania_a_vespery_atomicky_a_poznamky_neprepise(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "1 Poznámky.txt").write_text("Nemeniť 1", encoding="utf-8")
            (folder / "2 Poznámky.txt").write_text("Nemeniť 2", encoding="utf-8")
            (folder / "citania.txt").write_text("Staré čítania", encoding="utf-8")
            (folder / "vespery.txt").write_text("Staré vešpery", encoding="utf-8")
            app = self._minimal_app(folder)
            originals = self._patch_tk_for_pomocnik()
            try:
                app.otvorit_pomocnika()
                text3, text4 = FakeText.instances[2], FakeText.instances[3]
                text3.text = "Nové čítania"
                text4.text = "Nové vešpery"
                text3.bindings["<KeyRelease>"](None)
                text4.bindings["<KeyRelease>"](None)
                app.pomocnik_okno.protocols["WM_DELETE_WINDOW"]()
            finally:
                self._restore_tk(originals)

            self.assertEqual((folder / "citania.txt").read_text(encoding="utf-8"), "Nové čítania")
            self.assertEqual((folder / "vespery.txt").read_text(encoding="utf-8"), "Nové vešpery")
            self.assertEqual((folder / "1 Poznámky.txt").read_text(encoding="utf-8"), "Nemeniť 1")
            self.assertEqual((folder / "2 Poznámky.txt").read_text(encoding="utf-8"), "Nemeniť 2")
            self.assertEqual(list(folder.glob("*.tmp")), [])

    def test_nacitat_nastavenia_chybajuci_config_pouzije_defaulty(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "piesne"
            folder.mkdir()
            originals = self._patch_config_paths(temp, folder)
            app = self._config_app(folder)
            config_path = kinak.CONFIG_FILE_PATH
            expected_specialne = kinak.DEFAULT_CONFIG["zobrazovat_specialne_znaky"]
            expected_chorov = kinak.DEFAULT_CONFIG["zobrazovat_znaky_chorov"]
            expected_status_skratka = kinak.DEFAULT_CONFIG["statusbar_skratka_zalmu"]
            expected_status_zaltar = kinak.DEFAULT_CONFIG["statusbar_tyzden_zaltara"]
            try:
                app.nacitat_nastavenia()
            finally:
                self._restore_config_paths(originals)

            self.assertEqual(app.song_folder_path, folder.resolve())
            self.assertEqual(app.config["song_folder"], str(folder.resolve()))
            self.assertEqual(app.zobrazovat_specialne_znaky, expected_specialne)
            self.assertEqual(app.zobrazovat_znaky_chorov, expected_chorov)
            self.assertEqual(app.statusbar_skratka_zalmu, expected_status_skratka)
            self.assertEqual(app.statusbar_tyzden_zaltara, expected_status_zaltar)
            self.assertTrue(config_path.exists())
            data = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(data["song_folder"], str(folder.resolve()))

    def test_nacitat_nastavenia_poskodeny_json_nepadne_a_pouzije_defaulty(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "piesne"
            folder.mkdir()
            originals = self._patch_config_paths(temp, folder)
            kinak.CONFIG_FILE_PATH.write_text("{ toto nie je json", encoding="utf-8")
            app = self._config_app(folder)
            try:
                app.nacitat_nastavenia()
                data = json.loads(kinak.CONFIG_FILE_PATH.read_text(encoding="utf-8"))
            finally:
                self._restore_config_paths(originals)

            self.assertEqual(app.song_folder_path, folder.resolve())
            self.assertEqual(app.config["song_folder"], str(folder.resolve()))
            self.assertTrue(app.statusbar_jks_piesne)
            self.assertEqual(data["song_folder"], str(folder.resolve()))

    def test_nacitat_nastavenia_stary_config_bez_novych_poloziek_doplni_defaulty(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "piesne"
            folder.mkdir()
            originals = self._patch_config_paths(temp, folder)
            kinak.CONFIG_FILE_PATH.write_text(
                json.dumps(
                    {
                        "song_folder": str(folder),
                        "font_size": 61,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            app = self._config_app(folder)
            try:
                app.nacitat_nastavenia()
                data = json.loads(kinak.CONFIG_FILE_PATH.read_text(encoding="utf-8"))
            finally:
                self._restore_config_paths(originals)

            self.assertEqual(app.font_size, 61)
            self.assertEqual(app.song_folder_path, folder.resolve())
            self.assertIn("statusbar_tyzden_zaltara", data)
            self.assertIn("statusbar_skratka_zalmu", data)
            self.assertIn("zobrazovat_live_preview", data)
            self.assertIn("reserved_vertical_ratio", data)
            self.assertEqual(data["statusbar_tyzden_zaltara"], kinak.DEFAULT_CONFIG["statusbar_tyzden_zaltara"])
            self.assertEqual(data["zobrazovat_live_preview"], kinak.DEFAULT_CONFIG["zobrazovat_live_preview"])

    def test_ulozit_nastavenia_atomicky_ulozi_priecinok_piesni_a_prepinace(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "moje-piesne"
            folder.mkdir()
            originals = self._patch_config_paths(temp, folder)
            app = self._config_app(folder)
            try:
                app.ulozit_nastavenia()
                data = json.loads(kinak.CONFIG_FILE_PATH.read_text(encoding="utf-8"))
                temp_subory = list(Path(temp).glob("config_*.json"))
            finally:
                self._restore_config_paths(originals)

            self.assertEqual(data["song_folder"], str(folder))
            self.assertFalse(data["statusbar_skratka_zalmu"])
            self.assertFalse(data["statusbar_tyzden_zaltara"])
            self.assertFalse(data["zobrazovat_specialne_znaky"])
            self.assertFalse(data["zobrazovat_znaky_chorov"])
            self.assertEqual(temp_subory, [])

    def test_zmenit_priecinok_piesni_ulozi_novu_cestu_label_a_obnovi_filter(self):
        with tempfile.TemporaryDirectory() as temp:
            povodny = Path(temp) / "povodne"
            novy = Path(temp) / "novy-priecinok"
            povodny.mkdir()
            novy.mkdir()

            originals = self._patch_config_paths(temp, povodny)
            app = self._config_app(povodny)
            app.default_filter_var = FakeVar("Advent")
            app.filtre = []
            app.filtrovat_subory = lambda obdobie: app.filtre.append(obdobie)

            povodny_dialog = kinak.filedialog.askdirectory
            kinak.filedialog.askdirectory = lambda **kwargs: str(novy)
            try:
                app.zmenit_priecinok_piesni()
                data = json.loads(kinak.CONFIG_FILE_PATH.read_text(encoding="utf-8"))
            finally:
                kinak.filedialog.askdirectory = povodny_dialog
                self._restore_config_paths(originals)

            self.assertEqual(app.song_folder_path, novy)
            self.assertEqual(app.folder_label.config_calls[-1]["text"], str(novy))
            self.assertEqual(data["song_folder"], str(novy))
            self.assertEqual(app.filtre, ["Advent"])

    def test_zmenit_priecinok_piesni_zruseny_dialog_nemeni_config(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "piesne"
            folder.mkdir()

            originals = self._patch_config_paths(temp, folder)
            app = self._config_app(folder)
            app.filtre = []
            app.filtrovat_subory = lambda obdobie: app.filtre.append(obdobie)
            config_path = kinak.CONFIG_FILE_PATH

            povodny_dialog = kinak.filedialog.askdirectory
            kinak.filedialog.askdirectory = lambda **kwargs: ""
            try:
                app.zmenit_priecinok_piesni()
            finally:
                kinak.filedialog.askdirectory = povodny_dialog
                self._restore_config_paths(originals)

            self.assertEqual(app.song_folder_path, folder)
            self.assertEqual(app.folder_label.config_calls, [])
            self.assertFalse(config_path.exists())
            self.assertEqual(app.filtre, [])

    def test_obnovit_predvolene_resetuje_config_gui_hodnoty_a_necha_cisty_atomicky_zapis(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "predvolene-piesne"
            folder.mkdir()
            originals = self._patch_config_paths(temp, folder)
            msg_originals, msg_calls = self._patch_messagebox(odpoved=True)
            defaulty = {
                **kinak.DEFAULT_CONFIG,
                "font_size": 82,
                "text_color": "#123456",
                "song_folder": str(folder),
                "pouzit_vlastnu_farbu": True,
                "zobrazovat_specialne_znaky": True,
                "zobrazovat_znaky_chorov": True,
                "statusbar_tyzden_zaltara": True,
                "statusbar_skratka_zalmu": True,
                "zobrazit_direktorium": False,
                "zobrazovat_live_preview": True,
            }
            kinak.DEFAULT_CONFIG = defaulty
            kinak.CONFIG_FILE_PATH.write_text(
                json.dumps(
                    {
                        **defaulty,
                        "font_size": 31,
                        "text_color": "#654321",
                        "song_folder": str(Path(temp) / "stary-priecinok"),
                        "zobrazovat_specialne_znaky": False,
                        "zobrazovat_znaky_chorov": False,
                        "statusbar_tyzden_zaltara": False,
                        "statusbar_skratka_zalmu": False,
                    },
                    ensure_ascii=False,
                    indent=4,
                ),
                encoding="utf-8",
            )
            app = self._config_app(folder)
            try:
                app.obnovit_predvolene()
                data = json.loads(kinak.CONFIG_FILE_PATH.read_text(encoding="utf-8"))
                temp_subory = list(Path(temp).glob("config_default_*.json"))
            finally:
                self._restore_messagebox(msg_originals)
                self._restore_config_paths(originals)

            self.assertEqual(data["font_size"], 82)
            self.assertEqual(data["text_color"], "#123456")
            self.assertEqual(data["song_folder"], str(folder))
            self.assertTrue(data["zobrazovat_specialne_znaky"])
            self.assertTrue(data["zobrazovat_znaky_chorov"])
            self.assertTrue(data["statusbar_tyzden_zaltara"])
            self.assertTrue(data["statusbar_skratka_zalmu"])
            self.assertEqual(app.font_size_var.get(), 82)
            self.assertEqual(app.text_color_var.get(), "#123456")
            self.assertEqual(app.song_folder_path, folder.resolve())
            self.assertEqual(app.folder_label.kwargs["text"], str(folder.resolve()))
            self.assertEqual(temp_subory, [])
            self.assertEqual(len(msg_calls["askyesno"]), 1)
            self.assertEqual(len(msg_calls["showinfo"]), 1)
            self.assertEqual(msg_calls["showerror"], [])

    def test_rozmery_okien_sa_ulozia_do_configu_a_nacitaju_spat_do_aplikacie(self):
        hodnoty = {
            "pomocnik_x": 41,
            "pomocnik_y": 42,
            "pomocnik_width": 610,
            "pomocnik_height": 620,
            "main_window_x": 51,
            "main_window_y": 52,
            "main_window_width": 1200,
            "main_window_height": 760,
            "settings_window_width": 700,
            "settings_window_height": 680,
            "direktorium_window_width": 930,
            "direktorium_window_height": 640,
            "slavnosti_window_width": 940,
            "slavnosti_window_height": 650,
        }
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "piesne"
            folder.mkdir()
            originals = self._patch_config_paths(temp, folder)
            app = self._config_app(folder)
            for key, value in hodnoty.items():
                setattr(app, key, value)
            try:
                app.ulozit_nastavenia()
                data = json.loads(kinak.CONFIG_FILE_PATH.read_text(encoding="utf-8"))

                app2 = self._config_app(folder)
                for key in hodnoty:
                    setattr(app2, key, -1)
                app2.nacitat_nastavenia()
            finally:
                self._restore_config_paths(originals)

            for key, value in hodnoty.items():
                self.assertEqual(data[key], value)
                self.assertEqual(getattr(app2, key), value)


if __name__ == "__main__":
    unittest.main()
