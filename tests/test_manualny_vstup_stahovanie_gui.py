# -*- coding: utf-8 -*-

import importlib.util
from datetime import date
from pathlib import Path
import tempfile
import threading
import unittest


KINAK_PATH = Path(__file__).resolve().parents[0] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class FakeEntry:
    def __init__(self, text=""):
        self.text = text
        self.focus_count = 0

    def get(self):
        return self.text

    def delete(self, *args):
        self.text = ""

    def focus_set(self):
        self.focus_count += 1


class FakeVar:
    def __init__(self, value="—"):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeLabel:
    def __init__(self):
        self.text = None
        self.calls = []

    def config(self, **kwargs):
        self.calls.append(kwargs)
        if "text" in kwargs:
            self.text = kwargs["text"]


class FakeMaster:
    def __init__(self):
        self.cursor_values = []
        self.after_calls = []

    def config(self, **kwargs):
        if "cursor" in kwargs:
            self.cursor_values.append(kwargs["cursor"])

    def update_idletasks(self):
        pass

    def winfo_exists(self):
        return True

    def after(self, delay, callback):
        self.after_calls.append(delay)
        callback()


class ImmediateThread:
    def __init__(self, target, daemon=False):
        self.target = target
        self.daemon = daemon

    def start(self):
        self.target()


class ManualnyVstupStahovanieGuiTest(unittest.TestCase):
    def _app(self, folder, manual_text=""):
        app = object.__new__(kinak.ControlApp)
        app.song_folder_path = Path(folder)
        app.manual_entry = FakeEntry(manual_text)
        app.subor_var = FakeVar()
        app.popis_label = FakeLabel()
        app.direktorium_label = FakeLabel()
        app.master = FakeMaster()
        app.is_text_visible = False
        app.popisy_suborov = {
            "2AD": "2. adventná nedeľa",
            "7L": "Sv. Tomáša, apoštola (3. VII.)",
        }
        app._citania_lock = threading.Lock()
        app._vespery_lock = threading.Lock()
        app.zobrazovat_znaky_chorov = True
        app.nacitania = []
        app.zapnutia = 0
        app.vypnutia = 0
        app.popisy = []
        app.direktoria = []

        app.nacitat_piesne = lambda **kwargs: app.nacitania.append(kwargs)
        app.zapni_projekciu = lambda: setattr(app, "zapnutia", app.zapnutia + 1)
        app.vypni_projekciu = lambda: setattr(app, "vypnutia", app.vypnutia + 1)
        app.aktualizuj_popis = lambda nazov: app.popisy.append(nazov)
        app._aktualizuj_direktorium_pre_subor = lambda nazov: app.direktoria.append(nazov)
        return app

    def _patch_messagebox(self):
        povodne_info = kinak.messagebox.showinfo
        povodne_error = kinak.messagebox.showerror
        infos = []
        errors = []
        kinak.messagebox.showinfo = lambda *args, **kwargs: infos.append((args, kwargs))
        kinak.messagebox.showerror = lambda *args, **kwargs: errors.append((args, kwargs))
        return povodne_info, povodne_error, infos, errors

    def _patch_immediate_thread(self):
        povodne_thread = kinak.threading.Thread
        kinak.threading.Thread = ImmediateThread
        return povodne_thread

    def _patch_download_precheck(self):
        povodne_precheck = kinak.zobraz_chybu_chybajucich_kniznic_pre_stahovanie
        kinak.zobraz_chybu_chybajucich_kniznic_pre_stahovanie = lambda: False
        return povodne_precheck

    def test_manual_entry_enter_nacita_existujuci_subor_a_zapne_projekciu(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "2AD.txt").write_text("Pieseň\n\nStrofa", encoding="utf-8")
            app = self._app(folder, "2ad")

            self.assertEqual(app.manual_entry_enter(), "break")

            self.assertEqual(app.nacitania, [{"nazov_suboru": "2AD", "zobrazit_na_projekcii": True}])
            self.assertEqual(app.zapnutia, 1)
            self.assertEqual(app.vypnutia, 0)
            self.assertEqual(app.popisy, ["2AD"])
            self.assertEqual(app.direktoria, ["2AD"])

    def test_manual_entry_enter_tom_zobrazi_popis_a_odporucane_piesne(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "7L.txt").write_text("Sv. Tomáš\n\nR.: Pane, ukáž nám cestu", encoding="utf-8")
            app = self._app(folder, "7L")
            app.aktualizuj_popis = kinak.ControlApp.aktualizuj_popis.__get__(app, kinak.ControlApp)
            app._aktualizuj_direktorium_pre_subor = kinak.ControlApp._aktualizuj_direktorium_pre_subor.__get__(app, kinak.ControlApp)

            self.assertEqual(app.manual_entry_enter(), "break")

            self.assertEqual(app.nacitania, [{"nazov_suboru": "7L", "zobrazit_na_projekcii": True}])
            self.assertEqual(app.popis_label.text, "Žalmy pre Sv. Tomáša, apoštola (3. VII.)")
            self.assertIn("Odporúčané piesne: Sviatky apoštolov", app.direktorium_label.text)
            self.assertIn("Úvod: 454, 1-2", app.direktorium_label.text)

    def test_manual_entry_enter_pri_zapnutej_projekcii_len_vypne_projekciu(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "002.txt").write_text("Pieseň", encoding="utf-8")
            app = self._app(folder, "2")
            app.is_text_visible = True

            self.assertEqual(app.manual_entry_enter(), "break")

            self.assertEqual(app.vypnutia, 1)
            self.assertEqual(app.nacitania, [])
            self.assertEqual(app.zapnutia, 0)

    def test_manual_entry_enter_neexistujuci_subor_zobrazi_info_a_nenacita(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app(Path(temp), "999")
            povodne_info, povodne_error, infos, errors = self._patch_messagebox()
            try:
                self.assertEqual(app.manual_entry_enter(), "break")
            finally:
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            self.assertEqual(len(infos), 1)
            self.assertEqual(errors, [])
            self.assertEqual(app.nacitania, [])

    def test_skus_manualne_nacitanie_reaguje_len_na_enter_v_manual_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "002.txt").write_text("Pieseň", encoding="utf-8")
            app = self._app(folder, "2")

            cudzi_event = type("Event", (), {"keysym": "Return", "widget": object()})()
            self.assertIsNone(app.skus_manualne_nacitanie(cudzi_event))
            self.assertEqual(app.nacitania, [])

            spravny_event = type("Event", (), {"keysym": "Return", "widget": app.manual_entry})()
            self.assertIsNone(app.skus_manualne_nacitanie(spravny_event))

            self.assertEqual(app.nacitania, [{"nazov_suboru": "002"}])
            self.assertEqual(app.popis_label.text, "")
            self.assertEqual(app.direktoria, ["002"])

    def test_enter_aktivuj_projekciu_pouzije_vyber_z_menu_ak_manualny_vstup_je_prazdny(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "001.txt").write_text("Pieseň", encoding="utf-8")
            app = self._app(folder, "")
            app.subor_var.set("001")

            self.assertEqual(app.enter_aktivuj_projekciu(), "break")

            self.assertEqual(app.nacitania, [{"nazov_suboru": "001", "zobrazit_na_projekcii": True}])
            self.assertEqual(app.zapnutia, 1)
            self.assertEqual(app.popisy, ["001"])

    def test_aktualizovat_citania_gui_uspech_zobrazi_info_callback_a_uvolni_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app(Path(temp))
            callbacky = []
            volania = []

            povodne_thread = self._patch_immediate_thread()
            povodne_precheck = self._patch_download_precheck()
            povodne_stiahni = kinak.stiahni_citania_z_lc_kbs
            povodne_info, povodne_error, infos, errors = self._patch_messagebox()
            kinak.stiahni_citania_z_lc_kbs = lambda datum, cesta: volania.append((datum, cesta.name)) or True
            try:
                vysledok = app.aktualizovat_citania_gui(
                    datum=date(2026, 4, 3),
                    on_success=lambda: callbacky.append("ok"),
                )
            finally:
                kinak.threading.Thread = povodne_thread
                kinak.zobraz_chybu_chybajucich_kniznic_pre_stahovanie = povodne_precheck
                kinak.stiahni_citania_z_lc_kbs = povodne_stiahni
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            self.assertTrue(vysledok)
            self.assertEqual(volania, [(date(2026, 4, 3), "citania.txt")])
            self.assertEqual(callbacky, ["ok"])
            self.assertEqual(len(infos), 1)
            self.assertEqual(errors, [])
            self.assertEqual(app.master.cursor_values, ["wait", ""])
            self.assertTrue(app._citania_lock.acquire(blocking=False))
            app._citania_lock.release()

    def test_aktualizovat_citania_gui_zlyhanie_zobrazi_error_a_nevola_callback(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app(Path(temp))
            callbacky = []

            povodne_thread = self._patch_immediate_thread()
            povodne_precheck = self._patch_download_precheck()
            povodne_stiahni = kinak.stiahni_citania_z_lc_kbs
            povodne_info, povodne_error, infos, errors = self._patch_messagebox()
            kinak.stiahni_citania_z_lc_kbs = lambda datum, cesta: False
            try:
                vysledok = app.aktualizovat_citania_gui(
                    datum=date(2026, 4, 3),
                    on_success=lambda: callbacky.append("ok"),
                )
            finally:
                kinak.threading.Thread = povodne_thread
                kinak.zobraz_chybu_chybajucich_kniznic_pre_stahovanie = povodne_precheck
                kinak.stiahni_citania_z_lc_kbs = povodne_stiahni
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            self.assertTrue(vysledok)
            self.assertEqual(callbacky, [])
            self.assertEqual(infos, [])
            self.assertEqual(len(errors), 1)
            self.assertEqual(app.manual_entry.focus_count, 1)

    def test_aktualizovat_citania_gui_odmietne_druhe_stahovanie_ked_lock_drzi(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app(Path(temp))
            self.assertTrue(app._citania_lock.acquire(blocking=False))
            volania = []

            povodne_precheck = self._patch_download_precheck()
            povodne_stiahni = kinak.stiahni_citania_z_lc_kbs
            povodne_info, povodne_error, infos, errors = self._patch_messagebox()
            kinak.stiahni_citania_z_lc_kbs = lambda *args, **kwargs: volania.append(args) or True
            try:
                self.assertFalse(app.aktualizovat_citania_gui(datum=date(2026, 4, 3)))
            finally:
                app._citania_lock.release()
                kinak.zobraz_chybu_chybajucich_kniznic_pre_stahovanie = povodne_precheck
                kinak.stiahni_citania_z_lc_kbs = povodne_stiahni
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            self.assertEqual(len(infos), 1)
            self.assertEqual(errors, [])
            self.assertEqual(volania, [])

    def test_aktualizovat_citania_gui_pri_chybajucich_knizniciach_nespusti_stahovanie(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app(Path(temp))
            volania = []

            povodne_precheck = kinak.zobraz_chybu_chybajucich_kniznic_pre_stahovanie
            povodne_stiahni = kinak.stiahni_citania_z_lc_kbs
            povodne_info, povodne_error, infos, errors = self._patch_messagebox()
            kinak.zobraz_chybu_chybajucich_kniznic_pre_stahovanie = lambda: True
            kinak.stiahni_citania_z_lc_kbs = lambda *args, **kwargs: volania.append(args) or True
            try:
                self.assertFalse(app.aktualizovat_citania_gui(datum=date(2026, 4, 3)))
            finally:
                kinak.zobraz_chybu_chybajucich_kniznic_pre_stahovanie = povodne_precheck
                kinak.stiahni_citania_z_lc_kbs = povodne_stiahni
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            self.assertEqual(volania, [])
            self.assertEqual(infos, [])
            self.assertEqual(errors, [])
            self.assertTrue(app._citania_lock.acquire(blocking=False))
            app._citania_lock.release()

    def test_aktualizovat_citania_gui_bez_priecinka_zobrazi_error(self):
        app = self._app(Path(tempfile.gettempdir()))
        app.song_folder_path = None

        povodne_info, povodne_error, infos, errors = self._patch_messagebox()
        try:
            self.assertFalse(app.aktualizovat_citania_gui(datum=date(2026, 4, 3)))
        finally:
            kinak.messagebox.showinfo = povodne_info
            kinak.messagebox.showerror = povodne_error

        self.assertEqual(infos, [])
        self.assertEqual(len(errors), 1)

    def test_aktualizovat_vespery_gui_uspech_zobrazi_info_callback_a_uvolni_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app(Path(temp))
            callbacky = []
            volania = []

            povodne_thread = self._patch_immediate_thread()
            povodne_precheck = self._patch_download_precheck()
            povodne_stiahni = kinak.stiahni_vespery_z_breviar
            povodne_info, povodne_error, infos, errors = self._patch_messagebox()
            kinak.stiahni_vespery_z_breviar = (
                lambda datum, cesta, oznacit_chory=True:
                volania.append((datum, cesta.name, oznacit_chory)) or True
            )
            try:
                vysledok = app.aktualizovat_vespery_gui(
                    datum=date(2026, 4, 3),
                    on_success=lambda: callbacky.append("ok"),
                )
            finally:
                kinak.threading.Thread = povodne_thread
                kinak.zobraz_chybu_chybajucich_kniznic_pre_stahovanie = povodne_precheck
                kinak.stiahni_vespery_z_breviar = povodne_stiahni
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            self.assertTrue(vysledok)
            self.assertEqual(volania, [(date(2026, 4, 3), "vespery.txt", True)])
            self.assertEqual(callbacky, ["ok"])
            self.assertEqual(len(infos), 2)
            self.assertEqual(errors, [])
            self.assertEqual(app.manual_entry.focus_count, 2)
            self.assertTrue(app._vespery_lock.acquire(blocking=False))
            app._vespery_lock.release()

    def test_aktualizovat_vespery_gui_zlyhanie_zobrazi_error_a_nevola_callback(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app(Path(temp))
            callbacky = []

            povodne_thread = self._patch_immediate_thread()
            povodne_precheck = self._patch_download_precheck()
            povodne_stiahni = kinak.stiahni_vespery_z_breviar
            povodne_info, povodne_error, infos, errors = self._patch_messagebox()
            kinak.stiahni_vespery_z_breviar = lambda datum, cesta, oznacit_chory=True: False
            try:
                vysledok = app.aktualizovat_vespery_gui(
                    datum=date(2026, 4, 3),
                    on_success=lambda: callbacky.append("ok"),
                )
            finally:
                kinak.threading.Thread = povodne_thread
                kinak.zobraz_chybu_chybajucich_kniznic_pre_stahovanie = povodne_precheck
                kinak.stiahni_vespery_z_breviar = povodne_stiahni
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            self.assertTrue(vysledok)
            self.assertEqual(callbacky, [])
            self.assertEqual(infos, [])
            self.assertEqual(len(errors), 1)
            self.assertEqual(app.manual_entry.focus_count, 1)

    def test_aktualizovat_vespery_gui_odmietne_druhe_stahovanie_ked_lock_drzi(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app(Path(temp))
            self.assertTrue(app._vespery_lock.acquire(blocking=False))
            volania = []

            povodne_precheck = self._patch_download_precheck()
            povodne_stiahni = kinak.stiahni_vespery_z_breviar
            povodne_info, povodne_error, infos, errors = self._patch_messagebox()
            kinak.stiahni_vespery_z_breviar = lambda *args, **kwargs: volania.append(args) or True
            try:
                self.assertFalse(app.aktualizovat_vespery_gui(datum=date(2026, 4, 3)))
            finally:
                app._vespery_lock.release()
                kinak.zobraz_chybu_chybajucich_kniznic_pre_stahovanie = povodne_precheck
                kinak.stiahni_vespery_z_breviar = povodne_stiahni
                kinak.messagebox.showinfo = povodne_info
                kinak.messagebox.showerror = povodne_error

            self.assertEqual(len(infos), 1)
            self.assertEqual(errors, [])
            self.assertEqual(volania, [])


if __name__ == "__main__":
    unittest.main()
