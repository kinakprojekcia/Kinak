# -*- coding: utf-8 -*-

import importlib.util
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import threading
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
    def __init__(self, value="—", *args, **kwargs):
        self.value = kwargs.get("value", value)

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


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


class FakeLabel:
    def __init__(self):
        self.text = None
        self.calls = []

    def config(self, **kwargs):
        self.calls.append(kwargs)
        if "text" in kwargs:
            self.text = kwargs["text"]


class FakeTextWidget:
    def __init__(self, text=""):
        self.content = text
        self.state = None
        self.bindings = {}
        self.config_calls = []

    def config(self, **kwargs):
        self.config_calls.append(kwargs)
        if "state" in kwargs:
            self.state = kwargs["state"]

    def configure(self, **kwargs):
        self.config(**kwargs)

    def delete(self, *args):
        self.content = ""

    def insert(self, index, text):
        self.content += text

    def get(self, start, end):
        return self.content

    def tag_remove(self, *args):
        pass

    def tag_ranges(self, tag):
        return []

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def pack(self, *args, **kwargs):
        pass


class FakeWidget:
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.bindings = {}
        self.config_calls = []
        self.exists = True

    def pack(self, *args, **kwargs):
        pass

    def grid(self, *args, **kwargs):
        pass

    def pack_forget(self):
        pass

    def pack_propagate(self, flag):
        self.pack_propagate_flag = flag

    def config(self, **kwargs):
        self.config_calls.append(kwargs)
        self.kwargs.update(kwargs)

    def configure(self, **kwargs):
        self.config(**kwargs)

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def unbind(self, sequence):
        self.bindings.pop(sequence, None)


class FakeButton(FakeWidget):
    def invoke(self):
        command = self.kwargs.get("command")
        if command:
            return command()
        return None


class FakeMaster:
    def __init__(self):
        self.cursor_values = []
        self.after_ids = []

    def config(self, **kwargs):
        if "cursor" in kwargs:
            self.cursor_values.append(kwargs["cursor"])

    def update_idletasks(self):
        pass

    def winfo_exists(self):
        return True

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
        pass


class FakeToplevel(FakeWidget):
    def __init__(self, master=None):
        super().__init__()
        self.master = master
        self.protocols = {}
        self.geometry_value = None

    def transient(self, master):
        self.master = master

    def title(self, text):
        self.title_text = text

    def protocol(self, name, callback):
        self.protocols[name] = callback

    def geometry(self, value):
        self.geometry_value = value

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
        pass

    def destroy(self):
        self.exists = False


class FakeProjectionWindow:
    def __init__(self):
        self.text_updates = []
        self.title_updates = []

    def update_text(self, text):
        self.text_updates.append(text)

    def update_title(self, **kwargs):
        self.title_updates.append(kwargs)


class ImmediateThread:
    def __init__(self, target, daemon=False):
        self.target = target
        self.daemon = daemon

    def start(self):
        self.target()


class LocalElement:
    def __init__(self, tag, text, attrs=None):
        self.tag = tag
        self.text = text
        self.attrs = attrs or {}

    def get_text(self, separator="", strip=False):
        text = self.text
        return text.strip() if strip else text

    def get(self, key):
        return self.attrs.get(key)


class LocalSoup:
    SELECTED_TAGS = {"p", "h1", "h3", "h4", "h5", "strong", "b", "li", "em", "i", "div"}

    def __init__(self, html_text, parser_name="html.parser"):
        self.elements = []
        self._parse(html_text)

    def _parse(self, html_text):
        soup = self

        class Parser(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.stack = []

            def handle_starttag(self, tag, attrs):
                if tag in soup.SELECTED_TAGS:
                    self.stack.append([tag, dict(attrs), []])
                elif tag == "br" and self.stack:
                    self.stack[-1][2].append(" ")

            def handle_endtag(self, tag):
                if self.stack and self.stack[-1][0] == tag:
                    tag_name, attrs, chunks = self.stack.pop()
                    text = " ".join("".join(chunks).split())
                    if text:
                        soup.elements.append(LocalElement(tag_name, text, attrs))
                    if self.stack and text:
                        self.stack[-1][2].append(text)

            def handle_data(self, data):
                if self.stack:
                    self.stack[-1][2].append(data)

        parser = Parser()
        parser.feed(html_text)

    def select_one(self, selector):
        if selector.startswith("."):
            class_name = selector[1:]
            return next(
                (
                    elem
                    for elem in self.elements
                    if class_name in (elem.attrs.get("class") or "").split()
                ),
                None,
            )
        return next((elem for elem in self.elements if elem.tag == selector), None)

    def find_all(self, names):
        names = set(names)
        return [elem for elem in self.elements if elem.tag in names]

    def get_text(self, separator="\n"):
        return separator.join(elem.text for elem in self.elements)


class FakeResponse:
    def __init__(self, text):
        self.text = text
        self.status_code = 200
        self.apparent_encoding = "utf-8"
        self.encoding = None
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.content = text.encode("utf-8", errors="ignore")

    def raise_for_status(self):
        pass


class FakeRequests:
    def __init__(self, html_text):
        self.html_text = html_text
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append((url, headers, timeout))
        return FakeResponse(self.html_text)


class EndToEndSmokeTest(unittest.TestCase):
    def _app(self, folder, manual_text=""):
        app = object.__new__(kinak.ControlApp)
        app.master = FakeMaster()
        app.song_folder_path = Path(folder)
        app.manual_entry = FakeEntry(manual_text)
        app.subor_var = FakeVar()
        app.popis_label = FakeLabel()
        app.direktorium_label = FakeLabel()
        app.nazov_label = FakeLabel()
        app.strofa_label = FakeTextWidget("zobrazená strofa")
        app.obsah_suboru_text = FakeTextWidget("obsah")
        app.projection_window = FakeProjectionWindow()
        app.popisy_suborov = {}
        app.aktualne_strofy = []
        app.aktualny_index_strofa = 0
        app.nazov_piesne = None
        app.is_text_visible = False
        app._citania_lock = threading.Lock()
        app.vypnutia = 0
        app.indikatory = []
        app.zobrazene_strofy = []
        app.direktoria = []

        app.vypni_projekciu = lambda: setattr(app, "vypnutia", app.vypnutia + 1)
        app.zapni_projekciu = lambda: setattr(app, "is_text_visible", True)
        app.aktualizuj_popis = lambda nazov: setattr(app, "posledny_popis", nazov)
        app._update_nazov_label = lambda: setattr(app, "nazov_label_update", True)
        app.zobraz_aktualnu_strofu = lambda: app.zobrazene_strofy.append(app.aktualny_index_strofa)
        app.oznac_aktualnu_strofu_v_obsahu = lambda: setattr(app, "oznacena_strofa", app.aktualny_index_strofa)
        app.set_projection_indicator = lambda hodnota: app.indikatory.append(hodnota)
        app._aktualizuj_direktorium_pre_subor = lambda nazov: app.direktoria.append(nazov)
        return app

    def _patch_messagebox(self):
        originals = {
            "showinfo": kinak.messagebox.showinfo,
            "showerror": kinak.messagebox.showerror,
        }
        calls = {"showinfo": [], "showerror": []}
        kinak.messagebox.showinfo = lambda *args, **kwargs: calls["showinfo"].append((args, kwargs))
        kinak.messagebox.showerror = lambda *args, **kwargs: calls["showerror"].append((args, kwargs))
        return originals, calls

    def _restore_messagebox(self, originals):
        kinak.messagebox.showinfo = originals["showinfo"]
        kinak.messagebox.showerror = originals["showerror"]

    def _patch_local_download(self, html_text):
        originals = {
            "requests": kinak.requests,
            "BeautifulSoup": kinak.BeautifulSoup,
            "_vytvor_lc_kbs_session": getattr(kinak, "_vytvor_lc_kbs_session", None),
        }
        fake_requests = FakeRequests(html_text)
        kinak.requests = fake_requests
        kinak.BeautifulSoup = LocalSoup
        if "_vytvor_lc_kbs_session" in originals:
            kinak._vytvor_lc_kbs_session = lambda: None
        return originals, fake_requests

    def _restore_local_download(self, originals):
        kinak.requests = originals["requests"]
        kinak.BeautifulSoup = originals["BeautifulSoup"]
        if "_vytvor_lc_kbs_session" in originals and originals["_vytvor_lc_kbs_session"] is not None:
            kinak._vytvor_lc_kbs_session = originals["_vytvor_lc_kbs_session"]

    def _patch_tk_for_pomocnik(self):
        FakeTextWidget.instances = []
        originals = {
            "Toplevel": kinak.tk.Toplevel,
            "Frame": kinak.tk.Frame,
            "Label": kinak.tk.Label,
            "Text": kinak.tk.Text,
            "IntVar": kinak.tk.IntVar,
            "Button": kinak.tk.Button,
        }

        def text_factory(*args, **kwargs):
            widget = FakeTextWidget()
            widget.kwargs = kwargs
            FakeTextWidget.instances.append(widget)
            return widget

        kinak.tk.Toplevel = FakeToplevel
        kinak.tk.Frame = FakeWidget
        kinak.tk.Label = FakeWidget
        kinak.tk.Text = text_factory
        kinak.tk.IntVar = FakeVar
        kinak.tk.Button = FakeButton
        return originals

    def _restore_tk(self, originals):
        for name, value in originals.items():
            setattr(kinak.tk, name, value)

    def test_zadat_citania_nacita_citania_txt(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            obsah = "ČÍTANIA NA SVÄTÚ OMŠU\n\n1. ČÍTANIE\nText čítania"
            (folder / "citania.txt").write_text(obsah, encoding="utf-8")
            app = self._app(folder, "citania")

            app.skus_manualne_nacitanie(
                type("Event", (), {"keysym": "Return", "widget": app.manual_entry})()
            )

            self.assertEqual(app.aktualne_strofy, ["", "ČÍTANIA NA SVÄTÚ OMŠU", "1. ČÍTANIE\nText čítania"])
            self.assertEqual(app.nazov_piesne, "citania")
            self.assertEqual(app.direktoria, ["citania"])

    def test_zadat_cislo_piesne_otvori_spravnu_piesen(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "001.txt").write_text("Správna pieseň\n\nR.: Refrén", encoding="utf-8")
            (folder / "001a.txt").write_text("Variant piesne", encoding="utf-8")
            app = self._app(folder, "1")

            app.skus_manualne_nacitanie(
                type("Event", (), {"keysym": "Return", "widget": app.manual_entry})()
            )

            self.assertEqual(app.aktualne_strofy, ["", "Správna pieseň", "R.: Refrén"])
            self.assertEqual(app.nazov_piesne, "001")
            self.assertEqual(app.obsah_suboru_text.content, "Správna pieseň\n\nR.: Refrén")

    def test_stiahnut_citania_pre_beznu_nedelu_vytvori_dve_citania_refren_a_evanjelium(self):
        html = """
        <html><body>
          <h1 class="nazov-dna">10. nedeľa v Cezročnom období C</h1>
          <p class="farba">Liturgická farba: zelená</p>
          <h4>1. čítanie z Prvej knihy Kráľov</h4>
          <p>Syn tejto ženy ostal živý.</p>
          <p>Počuli sme Božie slovo.</p>
          <h4>Responzóriový žalm Ž 30</h4>
          <p class="lcRESPblock"><span class="lcRESP">R.:</span> <span class="lcVERS">Budem ťa, Pane, oslavovať, že si ma vyslobodil.</span></p>
          <p>Toto je text žalmového verša, ktorý sa nemá dostať do výstupu.</p>
          <h4>2. čítanie z Listu Galaťanom</h4>
          <p>Boh ma povolal svojou milosťou.</p>
          <p>Počuli sme Božie slovo.</p>
          <h4>Čítanie zo svätého Evanjelia podľa Lukáša</h4>
          <p>Mládenec, hovorím ti, vstaň!</p>
          <p>Počuli sme slovo Pánovo.</p>
        </body></html>
        """
        with tempfile.TemporaryDirectory() as temp:
            vystup = Path(temp) / "citania.txt"
            originals, fake_requests = self._patch_local_download(html)
            try:
                self.assertTrue(kinak.stiahni_citania_z_lc_kbs(date(2026, 6, 7), vystup))
            finally:
                self._restore_local_download(originals)

            text = vystup.read_text(encoding="utf-8")
            self.assertEqual(len(fake_requests.calls), 1)
            self.assertIn("1. ČÍTANIE Z PRVEJ KNIHY KRÁĽOV", text)
            self.assertIn("2. ČÍTANIE Z LISTU GALAŤANOM", text)
            self.assertIn("REFRÉN ŽALMU", text)
            self.assertIn("R.: Budem ťa, Pane, oslavovať, že si ma vyslobodil.", text)
            self.assertIn("ČÍTANIE ZO SVÄTÉHO EVANJELIA PODĽA LUKÁŠA", text)
            self.assertNotIn("Toto je text žalmového verša", text)

    def test_stiahnut_velkonocnu_vigiliu_zachova_viac_refrenov(self):
        fixture = Path(__file__).with_name("fixtures") / "lc_kbs_velkonocna_vigilia_2026_04_04.html"
        if not fixture.exists():
            fixture = Path(__file__).resolve().parent / "fixtures" / "lc_kbs_velkonocna_vigilia_2026_04_04.html"
        if not fixture.exists():
            self.skipTest(f"Fixture {fixture} neexistuje - preskakujem")
        html = fixture.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp:
            vystup = Path(temp) / "citania.txt"
            originals, fake_requests = self._patch_local_download(html)
            try:
                self.assertTrue(kinak.stiahni_citania_z_lc_kbs(date(2026, 4, 4), vystup))
            finally:
                self._restore_local_download(originals)

            text = vystup.read_text(encoding="utf-8")
            self.assertEqual(len(fake_requests.calls), 1)
            self.assertGreaterEqual(text.count("REFRÉN ŽALMU"), 10)
            self.assertIn("R.: Pane, zošli svojho Ducha a obnov tvárnosť zeme.", text)
            self.assertIn("R.: Aleluja.", text)
            self.assertIn("ČÍTANIE ZO SVÄTÉHO EVANJELIA PODĽA MATÚŠA", text)

    def test_otvorit_pomocnika_ulozi_editovatelne_poznamky(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "1 Poznámky.txt").write_text("Read-only poznámky 1", encoding="utf-8")
            (folder / "2 Poznámky.txt").write_text("Read-only poznámky 2", encoding="utf-8")
            (folder / "citania.txt").write_text("Staré čítania", encoding="utf-8")
            (folder / "vespery.txt").write_text("Staré vešpery", encoding="utf-8")
            app = self._app(folder)
            app.pomocnik_font_size = 14
            app.pomocnik_x = -1
            app.pomocnik_y = -1
            app.pomocnik_width = -1
            app.pomocnik_height = -1
            app.pomocnik_last_tab = 3
            app.pomocnik_okno = None
            app.potvrdit_ukoncenie = lambda event=None: "break"
            app.ulozit_nastavenia = lambda *args, **kwargs: None

            originals = self._patch_tk_for_pomocnik()
            try:
                app.otvorit_pomocnika()
                text3, text4 = FakeTextWidget.instances[2], FakeTextWidget.instances[3]
                text3.content = "Poznámka k čítaniam"
                text4.content = "Poznámka k vešperám"
                text3.bindings["<KeyRelease>"](None)
                text4.bindings["<KeyRelease>"](None)
                app.pomocnik_okno.protocols["WM_DELETE_WINDOW"]()
            finally:
                self._restore_tk(originals)

            self.assertEqual((folder / "citania.txt").read_text(encoding="utf-8"), "Poznámka k čítaniam")
            self.assertEqual((folder / "vespery.txt").read_text(encoding="utf-8"), "Poznámka k vešperám")
            self.assertEqual((folder / "1 Poznámky.txt").read_text(encoding="utf-8"), "Read-only poznámky 1")
            self.assertEqual((folder / "2 Poznámky.txt").read_text(encoding="utf-8"), "Read-only poznámky 2")

    def test_reset_ui_vycisti_stav(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app(Path(temp), "123")
            app.subor_var.set("001")
            app.popis_label.config(text="Žalmy")
            app.direktorium_label.config(text="Direktórium")
            app.nazov_label.config(text="Názov")
            app.nazov_piesne = "001"
            app.aktualne_strofy = ["", "Strofa"]
            app.aktualny_index_strofa = 1

            app.reset_ui()

            self.assertEqual(app.vypnutia, 1)
            self.assertEqual(app.strofa_label.content, "")
            self.assertEqual(app.obsah_suboru_text.content, "")
            self.assertEqual(app.manual_entry.text, "")
            self.assertEqual(app.subor_var.get(), "—")
            self.assertEqual(app.popis_label.text, "")
            self.assertEqual(app.direktorium_label.text, "")
            self.assertEqual(app.nazov_label.text, "")
            self.assertEqual(app.nazov_piesne, "")
            self.assertEqual(app.aktualne_strofy, [])
            self.assertEqual(app.aktualny_index_strofa, 0)


if __name__ == "__main__":
    unittest.main()
