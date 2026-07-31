# -*- coding: utf-8 -*-

import importlib.util
from pathlib import Path
import tempfile
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
if not KINAK_PATH.exists():
    KINAK_PATH = Path(__file__).resolve().parent / "Kinak.py"
if not KINAK_PATH.exists():
    KINAK_PATH = Path(__file__).resolve().parent.parent / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class FakeVar:
    def __init__(self, *args, **kwargs):
        self.value = kwargs.get("value", "")

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeWidget:
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.bindings = {}
        self.config_calls = []
        self.packed = False

    def pack(self, *args, **kwargs):
        self.packed = True

    def pack_forget(self):
        self.packed = False

    def config(self, **kwargs):
        self.config_calls.append(kwargs)
        self.kwargs.update(kwargs)

    def configure(self, **kwargs):
        self.config(**kwargs)

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def unbind(self, sequence):
        self.bindings.pop(sequence, None)

    def cget(self, key):
        return self.kwargs.get(key, "#f0f0f0")


class FakeButton(FakeWidget):
    pass


class FakeTop(FakeWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.protocols = {}
        self.exists = True
        self.width = 1000
        self.height = 660

    def title(self, text):
        self.title_text = text

    def geometry(self, value):
        self.geometry_value = value
        size = value.split("+", 1)[0]
        if "x" in size:
            width, height = size.split("x", 1)
            self.width = int(width)
            self.height = int(height)

    def transient(self, master):
        self.master = master

    def grab_set(self):
        self.grabbed = True

    def focus_set(self):
        self.focused = True

    def protocol(self, name, callback):
        self.protocols[name] = callback

    def winfo_width(self):
        return self.width

    def winfo_height(self):
        return self.height

    def winfo_screenwidth(self):
        return 1280

    def winfo_screenheight(self):
        return 900

    def winfo_exists(self):
        return self.exists

    def destroy(self):
        self.exists = False


class FakeTreeview(FakeWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.children = []
        self.rows = {}
        self.counter = 0
        self.selected = []

    def heading(self, *args, **kwargs):
        pass

    def column(self, *args, **kwargs):
        pass

    def tag_configure(self, *args, **kwargs):
        pass

    def yview(self, *args, **kwargs):
        pass

    def xview(self, *args, **kwargs):
        pass

    def insert(self, parent, index, values=(), tags=()):
        self.counter += 1
        item_id = f"I{self.counter}"
        self.children.append(item_id)
        self.rows[item_id] = {"values": tuple(values), "tags": tuple(tags)}
        return item_id

    def delete(self, *items):
        for item in items:
            if item in self.children:
                self.children.remove(item)
            self.rows.pop(item, None)

    def get_children(self):
        return list(self.children)

    def item(self, item_id, option=None):
        data = self.rows[item_id]
        if option == "values":
            return data["values"]
        if option == "tags":
            return data["tags"]
        return data

    def identify_row(self, y):
        if isinstance(y, str):
            return y
        if 0 <= y < len(self.children):
            return self.children[y]
        return ""

    def identify_column(self, x):
        return x if isinstance(x, str) else "#1"

    def selection(self):
        return list(self.selected)

    def prev(self, item_id):
        index = self.children.index(item_id)
        return self.children[index - 1] if index > 0 else ""


class FakeScrollbar(FakeWidget):
    def set(self, *args, **kwargs):
        pass


class FakeStyle:
    def __init__(self, *args, **kwargs):
        pass

    def configure(self, *args, **kwargs):
        pass


class FakeEntry(FakeWidget):
    pass


class FakeManualEntry:
    def __init__(self):
        self.focus_count = 0
        self.deleted = False
        self.inserted = []
        self._value = ""

    def delete(self, *args):
        self.deleted = True
        self._value = ""

    def insert(self, index, value):
        self.inserted.append(value)
        self._value = value

    def get(self):
        return self._value

    def focus_set(self):
        self.focus_count += 1


class FakeLabel:
    def __init__(self):
        self.text = ""
        self.kwargs = {}

    def config(self, **kwargs):
        self.kwargs.update(kwargs)
        if "text" in kwargs:
            self.text = kwargs["text"]


class FakeCombobox:
    def __init__(self):
        self.current_values = []

    def current(self, index):
        self.current_values.append(index)


class FakeMaster:
    def __init__(self):
        self.waited = []
        self.after_callbacks = []

    def wait_window(self, top):
        self.waited.append(top)
        if hasattr(top, "on_wait"):
            top.on_wait()

    def after(self, delay, callback):
        self.after_callbacks.append(delay)
        callback()

    def after_idle(self, callback):
        callback()

    def winfo_exists(self):
        return True


class DirektoriumSlavnostiOknaTest(unittest.TestCase):
    def _patch_tk_ttk(self):
        originals = {
            "Toplevel": kinak.tk.Toplevel,
            "Frame": kinak.tk.Frame,
            "Label": kinak.tk.Label,
            "Entry": kinak.tk.Entry,
            "Button": kinak.tk.Button,
            "StringVar": kinak.tk.StringVar,
            "Treeview": kinak.ttk.Treeview,
            "Scrollbar": kinak.ttk.Scrollbar,
            "Style": kinak.ttk.Style,
        }
        kinak.tk.Toplevel = FakeTop
        kinak.tk.Frame = FakeWidget
        kinak.tk.Label = FakeWidget
        kinak.tk.Entry = FakeEntry
        kinak.tk.Button = FakeButton
        kinak.tk.StringVar = FakeVar
        kinak.ttk.Treeview = FakeTreeview
        kinak.ttk.Scrollbar = FakeScrollbar
        kinak.ttk.Style = FakeStyle
        return originals

    def _restore_tk_ttk(self, originals):
        kinak.tk.Toplevel = originals["Toplevel"]
        kinak.tk.Frame = originals["Frame"]
        kinak.tk.Label = originals["Label"]
        kinak.tk.Entry = originals["Entry"]
        kinak.tk.Button = originals["Button"]
        kinak.tk.StringVar = originals["StringVar"]
        kinak.ttk.Treeview = originals["Treeview"]
        kinak.ttk.Scrollbar = originals["Scrollbar"]
        kinak.ttk.Style = originals["Style"]

    def _app(self, song_folder):
        app = object.__new__(kinak.ControlApp)
        app.master = FakeMaster()
        app.song_folder_path = Path(song_folder)
        app.song_combobox = FakeCombobox()
        app.manual_entry = FakeManualEntry()
        app.subor_var = FakeVar(value="—")
        app.popis_label = FakeLabel()
        app.direktorium_label = FakeLabel()
        app.is_text_visible = False
        app._suppress_vymazat = False
        app.direktorium_data = {"Adventné": []}
        app.direktorium_window_width = -1
        app.direktorium_window_height = -1
        app.slavnosti_window_width = -1
        app.slavnosti_window_height = -1
        app.popisy_suborov = {"6L": "Sv. Peter a Pavol", "4": "Prvý adventný týždeň"}
        app.nacitania = []
        app.direktoria = []
        app.reset_count = 0
        app.save_count = 0
        app.nacitat_piesne = lambda **kwargs: app.nacitania.append(kwargs)
        app._aktualizuj_direktorium_pre_subor = lambda nazov: app.direktoria.append(nazov)
        app.reset_ui = lambda: setattr(app, "reset_count", app.reset_count + 1)
        app.ulozit_nastavenia = lambda *args, **kwargs: setattr(app, "save_count", app.save_count + 1)
        return app

    def test_direktorium_dvojklik_na_spevovy_stlpec_vyberie_prve_cislo_piesne(self):
        data = {
            "Adventné": [
                {
                    "den": "1. adventná nedeľa",
                    "uvodny": "4, 1-2",
                    "ofertorium": "16/20",
                    "prijimanie": "25",
                    "kant": "8",
                    "po_omsi": "28",
                }
            ]
        }
        vybery = []
        rozmery = []
        originals = self._patch_tk_ttk()
        try:
            app = kinak.DirektoriumApp(
                FakeMaster(),
                data,
                init_width=812,
                init_height=623,
                on_close_callback=lambda w, h: rozmery.append((w, h)),
                on_song_select=vybery.append,
            )
            event = type("Event", (), {"y": 1, "x": "#2"})()
            self.assertEqual(app.tree.bindings["<Double-1>"](event), "break")
            self.assertEqual(app.top.geometry_value, "812x623+448+20")
            app.top.protocols["WM_DELETE_WINDOW"]()
        finally:
            self._restore_tk_ttk(originals)

        self.assertEqual(vybery, ["4"])
        self.assertEqual(rozmery, [(812, 623)])
        self.assertFalse(app.top.winfo_exists())

    def test_slavnosti_dvojklik_na_nazov_aj_datumovy_riadok_vyberie_kod_slavenia(self):
        vybery = []
        originals = self._patch_tk_ttk()
        try:
            app = kinak.SlavnostiApp(
                FakeMaster(),
                [("Sv. Petra a Pavla, apoštolov", "29. 6")],
                [],
                [],
                on_song_select=vybery.append,
            )
            self.assertEqual(app.tree.bindings["<Double-1>"](type("Event", (), {"y": 1, "x": "#1"})()), "break")
            self.assertEqual(app.tree.bindings["<Double-1>"](type("Event", (), {"y": 2, "x": "#1"})()), "break")
            self.assertEqual(app.top.geometry_value, "960x680+300+20")
        finally:
            self._restore_tk_ttk(originals)

        self.assertEqual(vybery, ["6L", "6L"])

    def test_vsetky_slavenia_z_okna_maju_mapovanie_na_kod_piesne(self):
        nazvy = {
            nazov
            for data in (kinak.SLAVNOSTI_DATA, kinak.NEPRIKAZANE_DATA, kinak.POHYBLIVE_DATA)
            for nazov, _ in data
        }

        chybajuce = sorted(nazvy - set(kinak.SLAVNOSTI_KODY_PRE_VYBER))

        self.assertEqual(chybajuce, [])

    def test_open_direktorium_po_kliknuti_nacita_piesen_a_po_zatvoreni_vrati_stav(self):
        class PopupTop:
            def __init__(self, on_wait):
                self.on_wait = on_wait

        class FakeDirektoriumApp:
            def __init__(self, master, direktorium_data, init_width=None, init_height=None, on_close_callback=None, on_song_select=None):
                self.top = PopupTop(lambda: (on_song_select("4"), on_close_callback(811, 622)))

        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "004.txt").write_text("Pieseň", encoding="utf-8")
            app = self._app(folder)
            povodne = kinak.DirektoriumApp
            kinak.DirektoriumApp = FakeDirektoriumApp
            try:
                app.open_direktorium()
            finally:
                kinak.DirektoriumApp = povodne

        self.assertFalse(app._direktorium_open)
        self.assertEqual(app.direktorium_window_width, 811)
        self.assertEqual(app.direktorium_window_height, 622)
        self.assertEqual(app.song_combobox.current_values, [0, 0])
        self.assertEqual(app.reset_count, 1)
        self.assertEqual(app.subor_var.get(), "—")
        self.assertEqual(app.nacitania, [{"nazov_suboru": "004"}])
        self.assertGreaterEqual(app.manual_entry.focus_count, 1)

    def test_open_slavnosti_po_kliknuti_zobrazi_popis_a_po_zatvoreni_vrati_stav(self):
        class PopupTop:
            def __init__(self, on_wait):
                self.on_wait = on_wait

        class FakeSlavnostiApp:
            def __init__(self, master, slavnosti_data, neprikazane_data, pohyblive_data, init_width=None, init_height=None, on_close_callback=None, on_song_select=None):
                self.top = PopupTop(lambda: (on_song_select("6L"), on_close_callback(944, 655)))

        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "6L.txt").write_text("Pieseň", encoding="utf-8")
            app = self._app(folder)
            povodne = kinak.SlavnostiApp
            kinak.SlavnostiApp = FakeSlavnostiApp
            try:
                app.open_slavnosti()
            finally:
                kinak.SlavnostiApp = povodne

        self.assertFalse(app._slavnosti_open)
        self.assertEqual(app.slavnosti_window_width, 944)
        self.assertEqual(app.slavnosti_window_height, 655)
        self.assertEqual(app.song_combobox.current_values, [0, 0])
        self.assertEqual(app.reset_count, 1)
        self.assertEqual(app.subor_var.get(), "—")
        self.assertEqual(app.nacitania, [{"nazov_suboru": "6L"}])
        self.assertEqual(app.popis_label.text, "Žalmy pre Sv. Peter a Pavol")
        self.assertGreaterEqual(app.manual_entry.focus_count, 1)


if __name__ == "__main__":
    unittest.main()
