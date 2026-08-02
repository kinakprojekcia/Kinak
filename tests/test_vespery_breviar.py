# -*- coding: utf-8 -*-

import importlib.util
from datetime import date
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


class FakeSoup:
    def __init__(self, text):
        self.text = text

    def find(self, id=None):
        return None

    def find_all(self, class_=None):
        return []

    def get_text(self, separator="\n"):
        return self.text


class FakeResponse:
    apparent_encoding = "utf-8"
    headers = {}

    def __init__(self, text):
        self.text = text
        self.encoding = None
        self.headers = {}
        self.content = text.encode("utf-8", errors="ignore") if text else b""
        self.status_code = 200

    def raise_for_status(self):
        return None


class FakeRequests:
    class RequestException(Exception):
        pass

    def __init__(self, text=None, exc=None):
        self.text = text
        self.exc = exc
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append((url, headers, timeout))
        if self.exc:
            raise self.exc
        return FakeResponse(self.text)


class VesperyBreviarTest(unittest.TestCase):
    def _html_text(self):
        return "\n".join(
            [
                "Navigácia",
                "Vešpery",
                "HYMNUS",
                "Svetlo tiché svätej slávy",
                "nesmrteľného Otca nebeského",
                "svätého, blaženého",
                "Ježišu Kriste",
                "PSALMÓDIA",
                "Ant. 1",
                "Pán je moje svetlo.",
                "",
                "Pán je moje svetlo *",
                "a moja spása.",
                "Sláva Otcu i Synu",
                "i Duchu Svätému.",
                "Ako bolo",
                "i na veky vekov. Amen.",
                "Ant.",
                "Pán je moje svetlo.",
                "",
                "KRÁTKE ČÍTANIE",
                "Bratia, radujte sa v Pánovi.",
                "KRÁTKE RESPONZÓRIUM",
                "Pán je moje svetlo.",
                "Pán je moja spása.",
                "EVANJELIOVÝ CHVÁLOSPEV",
                "Ant. na Magnifikat:",
                "Môj duch jasá v Bohu.",
                "PROSBY",
                "Pane, zmiluj sa nad nami.",
                "Prosíme ťa za Cirkev.",
                "Pane, zmiluj sa nad nami.",
                "Otče náš",
                "Toto sa už nemá dostať do výstupu.",
                "↑ navrch",
            ]
        )

    def _patch_download_deps(self, fake_requests, fake_soup_factory):
        povodne_requests = kinak.requests
        povodne_bs = kinak.BeautifulSoup
        kinak.requests = fake_requests
        kinak.BeautifulSoup = fake_soup_factory
        return povodne_requests, povodne_bs

    def test_breviar_url_vespery_obsahuje_datum_a_modlitbu_vespier(self):
        url = kinak._breviar_url_vespery(date(2026, 4, 3))

        self.assertIn("d=3", url)
        self.assertIn("m=4", url)
        self.assertIn("r=2026", url)
        self.assertIn("p=mv", url)

    def test_extrahuj_vespery_od_nadpisu_po_otce_nas_a_preskoci_navigaciu(self):
        raw = kinak._breviar_extrahuj(FakeSoup(self._html_text()))

        self.assertEqual(raw[0], "Vešpery")
        self.assertIn("HYMNUS", raw)
        self.assertIn("Otče náš", self._html_text())
        self.assertNotIn("Navigácia", raw)
        self.assertNotIn("Otče náš", raw)
        self.assertNotIn("Toto sa už nemá dostať do výstupu.", raw)

    def test_formatuj_vespery_pripravi_sekcie_magnifikat_a_chory(self):
        raw = kinak._breviar_extrahuj(FakeSoup(self._html_text()))
        riadky = kinak._breviar_formatuj(raw)
        riadky = kinak.oznac_chory(riadky, oznacit_lp=True)

        text = "\n".join(riadky)

        self.assertIn("HYMNUS", riadky)
        self.assertIn("PSALMÓDIA", riadky)
        self.assertIn("KRÁTKE ČÍTANIE", riadky)
        self.assertIn("EVANJELIOVÝ CHVÁLOSPEV", riadky)
        self.assertIn("[L] Svetlo tiché svätej slávy", riadky)
        self.assertIn("Ant. 1 Pán je moje svetlo.", riadky)
        self.assertIn("[P] Sláva Otcu i Synu *", riadky)
        self.assertIn("Velebí *", text)
        self.assertIn("Ant.: Môj duch jasá v Bohu.", riadky)

    def test_normalizacia_aleluja_v_antifone_3_funguje_so_znakmi_chorov(self):
        riadky = [
            "PSALMÓDIA",
            "",
            "Ant. 3 Skúšobná antifóna. Aleluja.",
            "",
            "[L] Aleluja.",
            "Prvý verš chválospevu *",
            "druhý verš.",
            "záver strofy. Aleluja.",
            "",
            "KRÁTKE ČÍTANIE",
        ]

        vysledok = kinak._normalizuj_aleluja_v_tretej_antifone_psalmodie(riadky)

        self.assertIn("[L] Aleluja. Prvý verš chválospevu *", vysledok)
        self.assertNotIn("[L] Aleluja.", vysledok)

    def test_normalizacia_aleluja_v_antifone_3_funguje_bez_znakov_chorov(self):
        riadky = [
            "PSALMÓDIA",
            "",
            "Ant. 3 Skúšobná antifóna. Aleluja.",
            "",
            "Aleluja.",
            "Prvý verš chválospevu *",
            "druhý verš.",
            "záver strofy. Aleluja.",
            "",
            "KRÁTKE ČÍTANIE",
        ]

        vysledok = kinak._normalizuj_aleluja_v_tretej_antifone_psalmodie(riadky)

        self.assertIn("Aleluja. Prvý verš chválospevu *", vysledok)
        self.assertNotIn("Aleluja.", vysledok)

    def test_stiahni_vespery_ulozi_subor_pripraveny_na_projekciu(self):
        fake_requests = FakeRequests(self._html_text())
        povodne_requests, povodne_bs = self._patch_download_deps(
            fake_requests,
            lambda text, parser: FakeSoup(text),
        )

        try:
            with tempfile.TemporaryDirectory() as temp:
                vystup = Path(temp) / "vespery.txt"
                uspech = kinak.stiahni_vespery_z_breviar(
                    date(2026, 4, 3),
                    vystup,
                    oznacit_chory=True,
                )

                self.assertTrue(uspech)
                obsah = vystup.read_text(encoding="utf-8")
        finally:
            kinak.requests = povodne_requests
            kinak.BeautifulSoup = povodne_bs

        self.assertEqual(fake_requests.calls[0][2], 20)
        self.assertIn("VEŠPERY  –  VEČERNÁ CHVÁLA", obsah)
        self.assertIn("03.04.2026", obsah)
        self.assertIn("HYMNUS", obsah)
        self.assertIn("[L] Svetlo tiché svätej slávy", obsah)
        self.assertIn("EVANJELIOVÝ CHVÁLOSPEV", obsah)
        self.assertIn("Ant.: Môj duch jasá v Bohu.", obsah)
        self.assertNotIn("Otče náš", obsah)
        self.assertNotIn("Navigácia", obsah)

    def test_stiahni_vespery_uklada_interne_znaky_chorov_aj_ked_su_skryte(self):
        fake_requests = FakeRequests(self._html_text())
        povodne_requests, povodne_bs = self._patch_download_deps(
            fake_requests,
            lambda text, parser: FakeSoup(text),
        )

        try:
            with tempfile.TemporaryDirectory() as temp:
                vystup = Path(temp) / "vespery.txt"
                uspech = kinak.stiahni_vespery_z_breviar(
                    date(2026, 4, 3),
                    vystup,
                    oznacit_chory=False,
                )

                self.assertTrue(uspech)
                obsah = vystup.read_text(encoding="utf-8")
        finally:
            kinak.requests = povodne_requests
            kinak.BeautifulSoup = povodne_bs

        self.assertIn("[L] Svetlo", obsah)

    def test_stiahni_vespery_vrati_false_pri_prilis_kratkom_parsovani(self):
        fake_requests = FakeRequests("Vešpery\nHYMNUS\nKrátky text\nOtče náš\n↑ navrch")
        povodne_requests, povodne_bs = self._patch_download_deps(
            fake_requests,
            lambda text, parser: FakeSoup(text),
        )

        try:
            with tempfile.TemporaryDirectory() as temp:
                vystup = Path(temp) / "vespery.txt"
                uspech = kinak.stiahni_vespery_z_breviar(date(2026, 4, 3), vystup)
                self.assertFalse(uspech)
                self.assertFalse(vystup.exists())
        finally:
            kinak.requests = povodne_requests
            kinak.BeautifulSoup = povodne_bs

    def test_stiahni_vespery_vrati_false_pri_sietovej_chybe(self):
        fake_requests = FakeRequests(exc=FakeRequests.RequestException("offline"))
        povodne_requests, povodne_bs = self._patch_download_deps(
            fake_requests,
            lambda text, parser: FakeSoup(text),
        )

        try:
            with tempfile.TemporaryDirectory() as temp:
                uspech = kinak.stiahni_vespery_z_breviar(
                    date(2026, 4, 3),
                    Path(temp) / "vespery.txt",
                )
                self.assertFalse(uspech)
        finally:
            kinak.requests = povodne_requests
            kinak.BeautifulSoup = povodne_bs


if __name__ == "__main__":
    unittest.main()
