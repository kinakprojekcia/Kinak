# -*- coding: utf-8 -*-

import importlib.util
from pathlib import Path
import unittest


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class FakeProjectionWindow:
    def __init__(self):
        self.text_updates = []
        self.title_updates = []
        self.filter_text = lambda text: text

    def update_text(self, text):
        self.text_updates.append(self.filter_text(text))

    def update_title(self, *args, **kwargs):
        self.title_updates.append((args, kwargs))


class FakeLabel:
    def __init__(self):
        self.config_calls = []

    def config(self, **kwargs):
        self.config_calls.append(kwargs)


class ProjekciaStrofyFormatovanieTest(unittest.TestCase):
    def _app(self):
        app = object.__new__(kinak.ControlApp)
        app.aktualne_cislo_piesne = "007"
        app.nazov_piesne = "007"
        app.aktualne_strofy = [
            "",
            "V nebi ·spievame_",
            "A na zemi pokoj.",
            "Pane, \"počuj\" náš hlas, tys' dobrý  Boh.",
        ]
        app.aktualny_index_strofa = 0
        app.is_text_visible = True
        app.zobrazovat_specialne_znaky = False
        app.zobrazovat_znaky_chorov = True
        app.projection_window = FakeProjectionWindow()
        app.projection_window.filter_text = lambda text: app.remove_special_chars(text)
        app.live_preview_label = FakeLabel()
        app.oznacene_indexy = []
        app.live_preview_updates = []

        app.oznac_aktualnu_strofu_v_obsahu = lambda: app.oznacene_indexy.append(
            app.aktualny_index_strofa
        )
        app.vypocitaj_velkost_pisma_pre_strofu = lambda text: 42
        app.update_live_preview = lambda text: app.live_preview_updates.append(app.remove_special_chars(text))
        return app

    def test_posun_dopredu_z_nultej_strofy_zobrazi_prvu_strofu_na_projekcii(self):
        app = self._app()

        vysledok = app.posun_strofu(+1)

        self.assertEqual(vysledok, "break")
        self.assertEqual(app.aktualny_index_strofa, 1)
        self.assertEqual(app.oznacene_indexy, [1])
        self.assertEqual(app.projection_window.text_updates, ["V\u00a0nebi spievame"])
        self.assertEqual(app.live_preview_updates, ["V\u00a0nebi spievame"])
        self.assertEqual(
            app.projection_window.title_updates[-1],
            (("7",), {"current": 1, "total": 3}),
        )

    def test_opakovane_plus_prejde_po_poslednu_strofu_a_dalej_sa_neposunie(self):
        app = self._app()

        app.posun_strofu(+1)
        app.posun_strofu(+1)
        app.posun_strofu(+1)
        app.posun_strofu(+1)

        self.assertEqual(app.aktualny_index_strofa, 3)
        self.assertEqual(len(app.projection_window.text_updates), 3)
        self.assertEqual(
            app.projection_window.text_updates[-1],
            "Pane, \"počuj\" náš hlas, tys' dobrý  Boh.",
        )

    def test_posun_dozadu_na_nultu_strofu_zobrazi_cislo_piesne(self):
        app = self._app()
        app.aktualny_index_strofa = 1

        app.posun_strofu(-1)

        self.assertEqual(app.aktualny_index_strofa, 0)
        self.assertEqual(app.oznacene_indexy, [0])
        self.assertEqual(app.projection_window.text_updates, ["7"])
        self.assertEqual(app.live_preview_updates, ["7"])
        self.assertEqual(
            app.projection_window.title_updates[-1],
            (("",), {"current": 0, "total": 3}),
        )

    def test_opakovane_minus_sa_zastavi_na_nultej_strofe(self):
        app = self._app()
        app.aktualny_index_strofa = 2

        app.posun_strofu(-1)
        app.posun_strofu(-1)
        app.posun_strofu(-1)

        self.assertEqual(app.aktualny_index_strofa, 0)
        self.assertEqual(app.projection_window.text_updates, ["V\u00a0nebi spievame", "7"])

    def test_posun_bez_strof_len_vrati_break_a_neaktualizuje_projekciu(self):
        app = self._app()
        app.aktualne_strofy = []

        self.assertEqual(app.posun_strofu(+1), "break")
        self.assertEqual(app.projection_window.text_updates, [])
        self.assertEqual(app.projection_window.title_updates, [])

    def test_ziskaj_aktualnu_a_celkovu_ignoruje_nultu_strofu_a_oreze_index(self):
        app = self._app()

        app.aktualny_index_strofa = 0
        self.assertEqual(app.ziskaj_aktualnu_a_celkovu(), (0, 3))

        app.aktualny_index_strofa = 99
        self.assertEqual(app.ziskaj_aktualnu_a_celkovu(), (3, 3))

    def test_format_typography_vklada_nezlomitelne_medzery_a_zachova_interpunkciu(self):
        app = self._app()

        self.assertEqual(
            app.format_typography('V dome a v chráme o "láske", tys\' dobrý  Boh.'),
            'V\u00a0dome a\u00a0v\u00a0chráme o\u00a0"láske", tys\' dobrý  Boh.',
        )

    def test_remove_special_chars_respektuje_prepinac_specialnych_znakov(self):
        app = self._app()

        app.zobrazovat_specialne_znaky = False
        self.assertEqual(app.remove_special_chars("Pane ·zmiluj_ sa"), "Pane zmiluj sa")

        app.zobrazovat_specialne_znaky = True
        self.assertEqual(app.remove_special_chars("Pane ·zmiluj_ sa"), "Pane ·zmiluj_ sa")

    def test_remove_special_chars_respektuje_prepinac_znakov_chorov(self):
        app = self._app()
        text = "[L] Aleluja. Prvý verš\n[P] Druhý verš"

        app.zobrazovat_specialne_znaky = True
        app.zobrazovat_znaky_chorov = False
        self.assertEqual(app.remove_special_chars(text), "Aleluja. Prvý verš\nDruhý verš")

        app.zobrazovat_znaky_chorov = True
        self.assertEqual(app.remove_special_chars(text), text)

    def test_zmena_prepinaca_chorov_prekresli_tu_istu_strofu_bez_reloadu(self):
        app = self._app()
        app.aktualny_index_strofa = 1
        app.aktualne_strofy[1] = "[L] Aleluja. Prvý verš"
        app.zobrazovat_specialne_znaky = True

        app.zobrazovat_znaky_chorov = False
        app.zobraz_aktualnu_strofu()

        app.zobrazovat_znaky_chorov = True
        app.zobraz_aktualnu_strofu()

        self.assertEqual(
            app.projection_window.text_updates[-2:],
            ["Aleluja. Prvý verš", "[L] Aleluja. Prvý verš"],
        )
        self.assertEqual(
            app.live_preview_updates[-2:],
            ["Aleluja. Prvý verš", "[L] Aleluja. Prvý verš"],
        )

    def test_zapnutie_chorov_doplni_znaky_do_starsich_nacitanych_vespier(self):
        app = self._app()
        app.nazov_piesne = "aktualny text"
        app.aktualne_cislo_piesne = "aktualny text"
        app.aktualny_subor_cesta = Path(r"C:\Kinak\piesne\vespery.txt")
        app.aktualne_strofy = [
            "",
            "VEŠPERY  –  VEČERNÁ CHVÁLA\n03.04.2026",
            "HYMNUS",
            "Svetlo tiché svätej slávy\nnesmrteľného Otca nebeského",
            "PSALMÓDIA",
            "Ant. 1 Pán je moje svetlo.",
            "Pán je moje svetlo *\na moja spása.",
        ]
        app.aktualny_index_strofa = 3
        app.zobrazovat_znaky_chorov = True
        app.obsah_suboru_text = None

        app._dopln_znaky_chorov_do_aktualnych_vespier()

        self.assertEqual(app.aktualny_index_strofa, 3)
        self.assertTrue(any(strofa.startswith("[L] ") for strofa in app.aktualne_strofy))

    def test_pomocne_znaky_sa_nezobrazia_na_platne_ale_uvodzovky_a_medzery_zostanu(self):
        app = self._app()
        app.aktualny_index_strofa = 3
        app.aktualne_strofy[3] = 'A ·"počuj"_ nás, tys\' dobrý  Boh.'

        app.zobraz_aktualnu_strofu()

        self.assertEqual(app.projection_window.text_updates, ['A\u00a0"počuj" nás, tys\' dobrý  Boh.'])
        self.assertNotIn("·", app.projection_window.text_updates[-1])
        self.assertNotIn("_", app.projection_window.text_updates[-1])

    def test_zobraz_aktualnu_strofu_bez_viditelnej_projekcie_neposiela_text_na_platno(self):
        app = self._app()
        app.is_text_visible = False
        app.aktualny_index_strofa = 1

        app.zobraz_aktualnu_strofu()

        self.assertEqual(app.oznacene_indexy, [1])
        self.assertEqual(app.projection_window.text_updates, [])
        self.assertEqual(app.projection_window.title_updates, [])


if __name__ == "__main__":
    unittest.main()
