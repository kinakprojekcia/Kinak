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


class FakeVar:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeWidget:
    def __init__(self, text="", width=300, height=160):
        self.text = text
        self.width = width
        self.height = height
        self.config_calls = []
        self.deleted = False
        self.placed = False
        self.place_calls = []
        self.place_forget_count = 0
        self.tag_config_calls = []
        self.exists = True
        self.master = {}

    def config(self, **kwargs):
        self.config_calls.append(kwargs)
        if "text" in kwargs:
            self.text = kwargs["text"]

    def configure(self, **kwargs):
        self.config(**kwargs)

    def cget(self, key):
        if key == "text":
            return self.text
        return None

    def delete(self, *args):
        self.deleted = True

    def insert(self, *args):
        pass

    def tag_remove(self, *args):
        pass

    def tag_config(self, *args, **kwargs):
        self.tag_config_calls.append((args, kwargs))

    def winfo_exists(self):
        return self.exists

    def winfo_width(self):
        return self.width

    def winfo_height(self):
        return self.height

    def winfo_ismapped(self):
        return self.placed

    def place(self, **kwargs):
        self.placed = True
        self.place_calls.append(kwargs)

    def place_forget(self):
        self.placed = False
        self.place_forget_count += 1

    def __setitem__(self, key, value):
        self.config(**{key: value})


class FakeMenu:
    def __init__(self):
        self.labels = []
        self.deleted = False
        self.commands = []

    def delete(self, *args):
        self.deleted = True
        self.labels = []
        self.commands = []

    def add_command(self, label, command):
        self.labels.append(label)
        self.commands.append(command)


class FakeOptionMenu:
    def __init__(self):
        self.menu = FakeMenu()

    def __getitem__(self, key):
        if key == "menu":
            return self.menu
        raise KeyError(key)


class FakeProjectionWindow:
    def __init__(self):
        self.text_updates = []
        self.title_updates = []
        self.bg_updates = []
        self.target_text_color = None

    def update_text(self, text):
        self.text_updates.append(text)

    def update_title(self, *args, **kwargs):
        self.title_updates.append((args, kwargs))

    def update_style(self, bg_color=None):
        self.bg_updates.append(bg_color)


class FakeMaster:
    def __init__(self):
        self.config_calls = []
        self.cancelled = []
        self.after_calls = []

    def configure(self, **kwargs):
        self.config_calls.append(kwargs)

    def after(self, delay, callback):
        self.after_calls.append(delay)
        return "after-id"

    def after_cancel(self, after_id):
        self.cancelled.append(after_id)

    def winfo_exists(self):
        return True

    def winfo_viewable(self):
        return True


class FakeFont:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def configure(self, **kwargs):
        self.kwargs.update(kwargs)


class FilterMenuLivePreviewTest(unittest.TestCase):
    def _filter_app(self):
        app = object.__new__(kinak.ControlApp)
        app.manual_entry = FakeWidget()
        app.popis_label = FakeWidget()
        app.direktorium_label = FakeWidget()
        app.obsah_suboru_text = FakeWidget()
        app.strofa_label = FakeWidget()
        app.nazov_label = FakeWidget()
        app.subor_var = FakeVar("Aktuálny výber")
        app.subor_menu = FakeOptionMenu()
        app.obdobie_subory = {
            "Advent": ["1AD", "2AD", "3AD"],
            "Nezaradené": None,
        }
        app.song_folder_path = Path(tempfile.gettempdir())
        app.is_text_visible = False
        app.original_projection_text = "pôvodný text"
        app.nazov_piesne = "777"
        app.aktualne_strofy = ["", "Aktuálna strofa"]
        app.vypnutia = 0
        app.vypni_projekciu = lambda: setattr(app, "vypnutia", app.vypnutia + 1)
        app.nacitania_menu = []
        app.nacitat_podla_menu = lambda value: app.nacitania_menu.append(value)
        return app

    def _preview_app(self):
        app = object.__new__(kinak.ControlApp)
        app.live_preview_label = FakeWidget(width=320, height=180)
        app.preview_container = FakeWidget(width=320, height=180)
        app.zobrazovat_live_preview_var = FakeVar(True)
        app.zobrazovat_specialne_znaky = False
        app.is_text_visible = True
        app.aktualne_cislo_piesne = "000"
        app.nazov_piesne = "000"
        app.master = FakeMaster()
        app._live_preview_after_id = None
        app._live_preview_updating = False
        return app

    def test_filtrovat_subory_naplni_menu_resetuje_vyber_a_nemeni_aktualnu_piesen(self):
        app = self._filter_app()

        app.filtrovat_subory("Advent")

        self.assertEqual(app.subor_menu.menu.labels, ["1AD", "2AD", "3AD"])
        self.assertEqual(app.subor_var.get(), "—")
        self.assertEqual(app.nazov_piesne, "777")
        self.assertEqual(app.aktualne_strofy, ["", "Aktuálna strofa"])
        self.assertEqual(app.vypnutia, 0)
        self.assertTrue(app.manual_entry.deleted)
        self.assertTrue(app.obsah_suboru_text.deleted)
        self.assertTrue(app.strofa_label.deleted)

    def test_filtrovat_subory_pri_zapnutej_projekcii_vypne_projekciu(self):
        app = self._filter_app()
        app.is_text_visible = True

        app.filtrovat_subory("Advent")

        self.assertEqual(app.vypnutia, 1)
        self.assertEqual(app.subor_var.get(), "—")

    def test_vyhladavanie_pre_filter_najde_cislo_variant_text_nazvu_a_ignoruje_diakritiku(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "001.txt").write_text("jedna", encoding="utf-8")
            (folder / "001a.txt").write_text("variant", encoding="utf-8")
            (folder / "Citáty svätých.txt").write_text("text", encoding="utf-8")
            app = self._filter_app()
            app.song_folder_path = folder

            self.assertEqual(app.najdi_subor_podla_prefixu("1"), "001.txt")
            self.assertEqual(app.najdi_subor_podla_prefixu("001a"), "001a.txt")
            self.assertEqual(app.najdi_subor_podla_prefixu("svatych"), "Citáty svätých.txt")
            self.assertEqual(app.najdi_subor_podla_prefixu("citat"), "Citáty svätých.txt")

    def test_update_live_preview_zapnuty_zobrazi_kontajner_a_ocisti_pomocne_znaky(self):
        app = self._preview_app()
        povodny_font = kinak.tkfont.Font
        povodna_vyska = kinak.estimate_text_height
        kinak.tkfont.Font = lambda **kwargs: FakeFont(**kwargs)
        kinak.estimate_text_height = lambda text, font, max_w: 20
        try:
            app.update_live_preview("Pane ·zmiluj_ sa")
        finally:
            kinak.tkfont.Font = povodny_font
            kinak.estimate_text_height = povodna_vyska

        self.assertTrue(app.preview_container.placed)
        self.assertEqual(app.live_preview_label.text, "Pane zmiluj sa")
        posledna_konfiguracia = app.live_preview_label.config_calls[-1]
        self.assertEqual(posledna_konfiguracia["justify"], "center")
        self.assertEqual(posledna_konfiguracia["anchor"], "center")
        self.assertGreater(posledna_konfiguracia["wraplength"], 0)

    def test_update_live_preview_vypnuty_vymaze_text_a_schova_kontajner(self):
        app = self._preview_app()
        app.zobrazovat_live_preview_var.set(False)
        app.preview_container.placed = True
        app._live_preview_after_id = "old-id"

        app.update_live_preview("Text")

        self.assertEqual(app.live_preview_label.text, "")
        self.assertFalse(app.preview_container.placed)
        self.assertEqual(app.preview_container.place_forget_count, 1)
        self.assertEqual(app.master.cancelled, ["old-id"])
        self.assertIsNone(app._live_preview_after_id)

    def test_zobraz_aktualnu_strofu_prazdne_strofy_vymaze_preview(self):
        app = self._preview_app()
        app.aktualne_strofy = []
        app.aktualny_index_strofa = 0
        app.strofa_label = FakeWidget()
        app.projection_window = FakeProjectionWindow()

        app.zobraz_aktualnu_strofu()

        self.assertEqual(app.live_preview_label.text, "")
        self.assertEqual(app.projection_window.text_updates, [""])

    def test_zobraz_aktualnu_strofu_nulta_strofa_ukaze_cislo_v_live_preview(self):
        app = self._preview_app()
        app.aktualne_cislo_piesne = "007"
        app.nazov_piesne = "007"
        app.aktualne_strofy = ["", "Prvá strofa"]
        app.aktualny_index_strofa = 0
        app.projection_window = FakeProjectionWindow()
        app.preview_updates = []
        app.oznac_aktualnu_strofu_v_obsahu = lambda: None
        app.update_live_preview = lambda text: app.preview_updates.append(text)

        app.zobraz_aktualnu_strofu()

        self.assertEqual(app.live_preview_label.text, "7")
        self.assertEqual(app.preview_updates, ["7"])
        self.assertEqual(app.projection_window.text_updates, ["7"])

    def test_aktualizovat_vzhlad_zmeni_farbu_preview_a_projekcneho_okna(self):
        app = self._preview_app()
        app.live_preview_label.text = "Aktuálny text"
        app.text_color_var = FakeVar("#ffcc00")
        app.projection_window = FakeProjectionWindow()
        app.master = FakeMaster()
        app.manual_entry = FakeWidget()
        app.strofa_label = FakeWidget()
        app.obsah_suboru_text = FakeWidget()
        app.refreshes = []
        app.update_live_preview = lambda text: app.refreshes.append(text)
        app.aktualizovat_stav_tlacidla_farby = lambda: None

        app.aktualizovat_vzhlad()

        self.assertEqual(app.projection_window.target_text_color, "#ffcc00")
        self.assertEqual(app.projection_window.bg_updates, [kinak.BACKGROUND_COLOR])
        self.assertIn({"fg": "#ffcc00", "bg": kinak.BACKGROUND_COLOR}, app.live_preview_label.config_calls)
        self.assertEqual(app.refreshes, ["Aktuálny text"])


if __name__ == "__main__":
    unittest.main()
