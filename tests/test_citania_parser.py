# -*- coding: utf-8 -*-

import importlib.util
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from datetime import date


KINAK_PATH = Path(__file__).resolve().parents[1] / "Kinak.py"
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class CitaniaParserTest(unittest.TestCase):
    SELECTED_HTML_TAGS = {"p", "h3", "h4", "h5", "strong", "b", "li", "em", "i"}

    class _Element:
        def __init__(self, text, attrs=None):
            self.text = text
            self.attrs = attrs or {}

        def get_text(self, separator="", strip=False):
            text = self.text
            return text.strip() if strip else text

        def get(self, key):
            return self.attrs.get(key)

    class _Soup:
        def __init__(self, elements=None, selectors=None):
            self.elements = elements or []
            self.selectors = selectors or {}

        def select_one(self, selector):
            return self.selectors.get(selector)

        def find_all(self, names):
            return self.elements

        def get_text(self, separator="\n"):
            return separator.join(elem.text for elem in self.elements)

    def _soup_from_selected_html(self, html_text):
        test_case = self

        class _SelectedTextParser(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.stack = []
                self.elements = []

            def handle_starttag(self, tag, attrs):
                if tag in test_case.SELECTED_HTML_TAGS:
                    self.stack.append([tag, []])
                elif tag == "br" and self.stack:
                    self.stack[-1][1].append(" ")

            def handle_endtag(self, tag):
                if self.stack and self.stack[-1][0] == tag:
                    _, chunks = self.stack.pop()
                    text = " ".join("".join(chunks).split())
                    if text:
                        self.elements.append(test_case._Element(text))

            def handle_data(self, data):
                if self.stack:
                    self.stack[-1][1].append(data)

        parser = _SelectedTextParser()
        parser.feed(html_text)
        return self._Soup(elements=parser.elements)

    def test_info_dna_vytiahne_nazov_a_liturgicku_farbu(self):
        soup = self._Soup(
            selectors={
                ".nazov-dna": self._Element("Utorok po 2. nedeli v Cezrocnom obdobi B"),
                ".farba": self._Element("Liturgicka farba: zelena"),
            }
        )

        info = kinak._extrahovaj_info_dna_lc_kbs(soup, date(2026, 1, 20))

        self.assertEqual(
            info,
            [
                "Utorok po 2. nedeli v Cezrocnom obdobi",
                "Liturgická farba: Zelena",
            ],
        )

    def test_info_dna_pouzije_den_v_tyzdni_ak_nazov_chyba(self):
        soup = self._Soup(
            selectors={
                "h1": self._Element("Liturgicky kalendar"),
                ".farba": self._Element("biela"),
            }
        )

        info = kinak._extrahovaj_info_dna_lc_kbs(soup, date(2026, 6, 30))

        self.assertEqual(info, ["Utorok", "Liturgická farba: Biela"])

    def test_extrahuje_citania_refren_a_ignoruje_text_zalmu(self):
        soup = self._Soup(
            elements=[
                self._Element("1. čítanie z Knihy proroka Izaiáša"),
                self._Element("Hľa, môj služobník bude úspešný a bude veľmi vyvýšený."),
                self._Element("Počuli sme Božie slovo."),
                self._Element("Responzóriový žalm"),
                self._Element("R.: Pane, tvoje slová sú duch a život."),
                self._Element("Text žalmu, ktorý sa nemá dostať do výstupu."),
                self._Element("2. čítanie z Listu Hebrejom"),
                self._Element("Bratia, s dôverou pristúpme k trónu milosti."),
                self._Element("Počuli sme Božie slovo."),
                self._Element("Evanjelium 1 podľa Jána"),
                self._Element("Ježiš povedal svojim učeníkom: Pokoj vám zanechávam."),
                self._Element("Počuli sme slovo Pánovo."),
            ]
        )

        citania = kinak._extrahovaj_vsetky_citania_lc_kbs(soup)
        text = "\n".join(citania)

        self.assertIn("1. ČÍTANIE Z KNIHY PROROKA IZAIÁŠA", text)
        self.assertIn("2. ČÍTANIE Z LISTU HEBREJOM", text)
        self.assertIn("EVANJELIUM 1 PODĽA JÁNA", text)
        self.assertIn("R.: Pane, tvoje slová sú duch a život.", citania)
        self.assertIn("Počuli sme Božie slovo.", text)
        self.assertIn("Počuli sme slovo Pánovo.", text)
        self.assertNotIn("Text žalmu, ktorý sa nemá dostať do výstupu.", text)

    def test_velkonocna_vigilia_extrahuje_viac_refrenovych_zalmov(self):
        refreny = [
            "R.: Zošli svojho ducha a obnov tvárnosť zeme.",
            "R.: Chráň ma, Bože, k tebe sa utiekam.",
            "R.: Spievajme Pánovi, lebo sa preslávil.",
            "R.: Budem ťa, Pane, oslavovať, že si ma vyslobodil.",
            "R.: Čerpajme vodu s radosťou z prameňov spásy.",
            "R.: Pane, ty máš slová večného života.",
            "R.: Ako jeleň dychtí za vodou z prameňa.",
        ]
        elements = [self._Element(refren) for refren in refreny]

        for index, refren in enumerate(refreny, start=1):
            elements.extend(
                [
                    self._Element(f"{index}. čítanie z knihy Veľkonočnej vigílie"),
                    self._Element(f"Text {index}. čítania."),
                    self._Element("Počuli sme Božie slovo."),
                    self._Element("Responzóriový žalm"),
                    self._Element(refren),
                    self._Element("Text žalmu, ktorý sa nemá dostať do výstupu."),
                    self._Element(refren),  # opakovaný refrén v tom istom žalme sa nemá zdvojiť
                ]
            )

        elements.extend(
            [
                self._Element("Evanjelium 1 podľa Lukáša"),
                self._Element("Prečo hľadáte živého medzi mŕtvymi?"),
                self._Element("Počuli sme slovo Pánovo."),
            ]
        )
        soup = self._Soup(elements=elements)

        citania = kinak._extrahovaj_vsetky_citania_lc_kbs(soup)
        text = "\n".join(citania)

        self.assertIn("EVANJELIUM 1 PODĽA LUKÁŠA", text)
        self.assertEqual(7, citania.count("REFRÉN ŽALMU"))
        for refren in refreny:
            self.assertEqual(1, citania.count(refren))
        self.assertNotIn("Text žalmu, ktorý sa nemá dostať do výstupu.", text)

    def test_velkonocna_vigilia_2026_04_04_deduplikuje_prehlad_a_detail(self):
        refreny = [
            "R.: Pane, zošli svojho Ducha a obnov tvárnosť zeme.",
            "R.: Milosti Pánovej plná je zem.",
            "R.: Ochráň ma, Bože, k tebe sa utiekam.",
            "R.: Spievajme Pánovi, lebo sa preslávil.",
            "R.: Budem ťa, Pane, oslavovať, že si ma vyslobodil.",
            "R.: Čerpajme vodu s radosťou z prameňov spásy.",
            "R.: Pane, ty máš slová večného života.",
            "R.: Ako jeleň dychtí za vodou z prameňa, tak moja duša, Bože, túži za tebou.",
            "R.: Bože, stvor vo mne srdce čisté.",
            "R.: Aleluja.",
        ]
        elements = [self._Element(refren) for refren in refreny]

        for index, refren in enumerate(refreny, start=1):
            elements.extend(
                [
                    self._Element(f"{index}. čítanie z Veľkonočnej vigílie"),
                    self._Element(f"Text čítania {index}."),
                    self._Element("Počuli sme Božie slovo."),
                    self._Element("Responzóriový žalm"),
                    self._Element(refren),
                ]
            )

        elements.extend(
            [
                self._Element("Čítanie zo svätého Evanjelia podľa Matúša"),
                self._Element("Po sobote, keď sa brieždilo na prvý deň týždňa."),
                self._Element("Počuli sme slovo Pánovo."),
            ]
        )
        soup = self._Soup(elements=elements)

        citania = kinak._extrahovaj_vsetky_citania_lc_kbs(soup)

        self.assertEqual(10, citania.count("REFRÉN ŽALMU"))
        for refren in refreny:
            self.assertEqual(1, citania.count(refren))

    def test_velkonocna_vigilia_2026_04_04_parser_na_offline_html_fixture(self):
        fixture = Path(__file__).with_name("fixtures") / "lc_kbs_velkonocna_vigilia_2026_04_04.html"
        soup = self._soup_from_selected_html(fixture.read_text(encoding="utf-8"))

        citania = kinak._extrahovaj_vsetky_citania_lc_kbs(soup)
        text = "\n".join(citania)

        self.assertIn("ČÍTANIE ZO SVÄTÉHO EVANJELIA PODĽA MATÚŠA", text)
        self.assertEqual(10, citania.count("REFRÉN ŽALMU"))
        self.assertEqual(1, citania.count("R.: Aleluja."))
        self.assertEqual(1, citania.count("R.: Bože, stvor vo mne srdce čisté."))
        self.assertNotIn("Toto je text žalmového verša", text)

    def test_velkonocna_vigilia_2027_parser_s_evanjeliom_podla_marka(self):
        fixture = Path(__file__).with_name("fixtures") / "lc_kbs_velkonocna_vigilia_2027_marek.html"
        soup = self._soup_from_selected_html(fixture.read_text(encoding="utf-8"))

        citania = kinak._extrahovaj_vsetky_citania_lc_kbs(soup)
        text = "\n".join(citania)

        self.assertIn("ČÍTANIE ZO SVÄTÉHO EVANJELIA PODĽA MARKA", text)
        self.assertIn("Vstal z mŕtvych, niet ho tu.", text)
        self.assertEqual(10, citania.count("REFRÉN ŽALMU"))
        self.assertEqual(1, citania.count("R.: Aleluja."))
        self.assertEqual(1, citania.count("R.: Bože, stvor vo mne srdce čisté."))
        self.assertNotIn("Toto je text žalmového verša", text)

    def test_velkonocna_vigilia_kratšie_citanie_neposunie_nasledujuce_refreny(self):
        soup = self._soup_from_selected_html(
            """
            <h4>Čítanie z Knihy Genezis</h4>
            <p>Dlhší text o Abrahámovi.</p>
            <p>Počuli sme Božie slovo.</p>
            <p><span>alebo kratšie</span></p>
            <h4>Čítanie z Knihy Genezis</h4>
            <p>Kratší text o Abrahámovi.</p>
            <p>Počuli sme Božie slovo.</p>
            <p class="lcRESPblock"><span class="lcRESP">R.:</span> <span class="lcVERS">Ochráň ma, Bože, k tebe sa utiekam.</span></p>
            <h4>Responzóriový žalm Ž 16</h4>
            <p>Toto je text žalmového verša, ktorý sa nemá dostať do výstupu.</p>
            <h4>Čítanie z Knihy Exodus</h4>
            <p>Izraeliti šli stredom mora po suchu.</p>
            <p>Počuli sme Božie slovo.</p>
            <p class="lcRESPblock"><span class="lcRESP">R.:</span> <span class="lcVERS">Spievajme Pánovi, lebo sa preslávil.</span></p>
            <h4>Responzóriový žalm Ex 15</h4>
            <p>Toto je text žalmového verša, ktorý sa nemá dostať do výstupu.</p>
            """
        )

        citania = kinak._extrahovaj_vsetky_citania_lc_kbs(soup)
        text = "\n".join(citania)

        self.assertIn("Dlhší text o Abrahámovi.", text)
        self.assertIn("Kratší text o Abrahámovi.", text)
        self.assertEqual(2, citania.count("REFRÉN ŽALMU"))
        self.assertEqual(1, citania.count("R.: Ochráň ma, Bože, k tebe sa utiekam."))
        self.assertEqual(1, citania.count("R.: Spievajme Pánovi, lebo sa preslávil."))
        self.assertNotIn("Toto je text žalmového verša", text)

    def test_velkonocna_vigilia_deduplikuje_prehlad_detail_ale_zachova_rozne_refreny_pri_tom_istom_citani(self):
        soup = self._soup_from_selected_html(
            """
            <p class="lcRESPblock"><span class="lcRESP">R.:</span> <span class="lcVERS">Prvý refrén k čítaniu.</span></p>
            <p class="lcRESPblock"><span class="lcRESP">R.:</span> <span class="lcVERS">Alternatívny refrén k čítaniu.</span></p>
            <h4>Čítanie z Knihy Genezis</h4>
            <p>Text čítania.</p>
            <p>Počuli sme Božie slovo.</p>
            <p class="lcRESPblock"><span class="lcRESP">R.:</span> <span class="lcVERS">Prvý refrén k čítaniu.</span></p>
            <p class="lcRESPblock"><span class="lcRESP">R.:</span> <span class="lcVERS">Alternatívny refrén k čítaniu.</span></p>
            <h4>Responzóriový žalm Ž 1</h4>
            <p>Toto je text žalmového verša, ktorý sa nemá dostať do výstupu.</p>
            """
        )

        citania = kinak._extrahovaj_vsetky_citania_lc_kbs(soup)

        self.assertEqual(2, citania.count("REFRÉN ŽALMU"))
        self.assertEqual(1, citania.count("R.: Prvý refrén k čítaniu."))
        self.assertEqual(1, citania.count("R.: Alternatívny refrén k čítaniu."))

    def test_extrahuj_refreny_zalmov_vrati_vsetky_refreny_v_poradi(self):
        soup = self._Soup(
            elements=[
                self._Element("Responzoriovy zalm"),
                self._Element("R.: Prvy refren."),
                self._Element("Tento text zalmu sa ma ignorovat."),
                self._Element("Citanie z Knihy proroka Izaiasa"),
                self._Element("Responzoriovy zalm"),
                self._Element("R.: Druhy refren."),
                self._Element("R.: Druhy refren."),
            ]
        )

        refreny = kinak._extrahuj_refreny_zalmov_lc_kbs(soup)

        self.assertEqual(["Prvy refren.", "Druhy refren."], refreny)
        self.assertEqual("Prvy refren.", kinak._extrahuj_refren_zalmu_lc_kbs(soup))

    def test_stiahni_refreny_zalmov_zapise_viac_refrenov_v_jeden_den_s_indexom(self):
        povodne_chybaju_kniznice = kinak.chybaju_kniznice_pre_stahovanie
        povodne_vsetky_dni = kinak._vsetky_dni_roka
        povodne_stiahni_soup = kinak._stiahni_lc_kbs_soup
        povodne_extrahuj_refreny = kinak._extrahuj_refreny_zalmov_lc_kbs
        povodne_delay = kinak.REFRENY_DELAY_S

        fake_soup = object()
        stiahnute_datumy = []

        def fake_stiahni_soup(datum):
            stiahnute_datumy.append(datum)
            return fake_soup

        try:
            kinak.chybaju_kniznice_pre_stahovanie = lambda: False
            kinak._vsetky_dni_roka = lambda rok: [date(rok, 4, 4)]
            kinak._stiahni_lc_kbs_soup = fake_stiahni_soup
            kinak._extrahuj_refreny_zalmov_lc_kbs = lambda soup: [
                "Prvy refren.",
                "Druhy refren.",
                "Treti refren.",
            ]
            kinak.REFRENY_DELAY_S = 0

            with tempfile.TemporaryDirectory() as temp:
                vysledok = kinak.stiahni_refreny_zalmov_pre_rok(2026, Path(temp))
                april = Path(temp) / "4L.txt"
                text = april.read_text(encoding="utf-8")

            self.assertTrue(vysledok["uspech"])
            self.assertEqual([date(2026, 4, 4)], stiahnute_datumy)
            self.assertEqual(0, vysledok["chyby"])
            self.assertIn("4.1 Prvy refren.", text)
            self.assertIn("4.2 Druhy refren.", text)
            self.assertIn("4.3 Treti refren.", text)
            self.assertNotIn("\n4. Prvy refren.", text)
        finally:
            kinak.chybaju_kniznice_pre_stahovanie = povodne_chybaju_kniznice
            kinak._vsetky_dni_roka = povodne_vsetky_dni
            kinak._stiahni_lc_kbs_soup = povodne_stiahni_soup
            kinak._extrahuj_refreny_zalmov_lc_kbs = povodne_extrahuj_refreny
            kinak.REFRENY_DELAY_S = povodne_delay

    @unittest.skipUnless(
        kinak.requests is not None and kinak.BeautifulSoup is not None,
        "requests/BeautifulSoup nie sú dostupné v tomto testovacom Pythone",
    )
    def test_stiahni_citania_z_lc_kbs_pre_velkonocnu_vigiliu_2026_04_04(self):
        with tempfile.TemporaryDirectory() as temp:
            vystup = Path(temp) / "citania.txt"
            uspech = kinak.stiahni_citania_z_lc_kbs(date(2026, 4, 4), vystup)
            if not uspech:
                self.skipTest("LC-KBS stránka alebo sieť nie je momentálne dostupná")

            text = vystup.read_text(encoding="utf-8")

            self.assertIn("04.04.2026", text)
            self.assertIn("ČÍTANIA NA SVÄTÚ OMŠU", text)
            self.assertGreaterEqual(text.count("REFRÉN ŽALMU"), 10)
            self.assertIn("R.: Aleluja.", text)

    def test_spocita_citania_pred_evanjeliom(self):
        oddelovac = "-" * 60
        citania = [
            oddelovac,
            "1. ČÍTANIE Z KNIHY PROROKA IZAIÁŠA",
            oddelovac,
            "Obsah prveho citania",
            oddelovac,
            "R.: Pane, tvoje slová sú duch a život.",
            oddelovac,
            oddelovac,
            "2. ČÍTANIE Z LISTU HEBREJOM",
            oddelovac,
            "Obsah druheho citania",
            oddelovac,
            "EVANJELIUM 1 PODĽA JÁNA",
            oddelovac,
            "Obsah evanjelia",
        ]

        self.assertEqual(kinak._lc_kbs_pocet_citani_pred_evanjeliom(citania), 2)

    def test_nedela_a_slavnost_ocakavaju_dve_citania(self):
        self.assertTrue(kinak._lc_kbs_ocakava_dve_citania(date(2026, 6, 7), []))
        self.assertTrue(
            kinak._lc_kbs_ocakava_dve_citania(
                date(2026, 3, 25),
                ["Zvestovanie Pána (Slávnosť)"],
            )
        )
        self.assertFalse(
            kinak._lc_kbs_ocakava_dve_citania(
                date(2026, 6, 30),
                ["Utorok po 13. nedeli v Cezročnom období"],
            )
        )

    def test_rozdel_text_na_bloky_dodrziava_limit_a_dlhu_vetu_nekrati(self):
        text = (
            "Prva veta je kratka. Druha veta je tiez kratka. "
            "Toto je velmi dlha veta bez vhodneho delenia v strede textu."
        )

        bloky = kinak.ControlApp.rozdel_text_na_bloky(None, text, max_chars=45)

        self.assertEqual(bloky[0], "Prva veta je kratka.")
        self.assertEqual(bloky[1], "Druha veta je tiez kratka.")
        self.assertEqual(
            bloky[2],
            "Toto je velmi dlha veta bez vhodneho delenia v strede textu.",
        )
        self.assertTrue(len(bloky[2]) > 45)

    def test_rozdel_text_na_bloky_deli_dlhe_vety_podla_interpunkcie(self):
        text = (
            "Prva veta je dostatocne dlha, ale stale sa da oddelit. "
            "Druha veta pokracuje dalsim myslienkovym celkom! "
            "Tretia veta uzatvara text?"
        )

        bloky = kinak.ControlApp.rozdel_text_na_bloky(None, text, max_chars=70)

        self.assertEqual(
            bloky,
            [
                "Prva veta je dostatocne dlha, ale stale sa da oddelit.",
                "Druha veta pokracuje dalsim myslienkovym celkom!",
                "Tretia veta uzatvara text?",
            ],
        )

    def test_rozdel_text_na_bloky_zachova_uvodzovky_pomlcky_a_zatvorky(self):
        text = 'Povedal: "Pokoj vám" - a dodal (nebojte sa). Ďalšia veta.'

        bloky = kinak.ControlApp.rozdel_text_na_bloky(None, text, max_chars=55)

        self.assertEqual(bloky[0], 'Povedal: "Pokoj vám" - a dodal (nebojte sa).')
        self.assertEqual(bloky[1], "Ďalšia veta.")

    def test_rozdel_text_na_bloky_nekrati_extremne_dlhe_slovo(self):
        dlhe_slovo = "najdlhsieslovobezmedzier" * 8
        text = f"Uvodna veta. {dlhe_slovo}."

        bloky = kinak.ControlApp.rozdel_text_na_bloky(None, text, max_chars=40)

        self.assertEqual(bloky[0], "Uvodna veta.")
        self.assertEqual(bloky[1], f"{dlhe_slovo}.")
        self.assertTrue(len(bloky[1]) > 40)

    def test_stiahni_citania_vrati_false_ak_chybaju_requests_alebo_bs4(self):
        with tempfile.TemporaryDirectory() as temp:
            vystup = Path(temp) / "citania.txt"
            povodne_requests = kinak.requests
            povodne_bs = kinak.BeautifulSoup
            try:
                kinak.requests = None
                kinak.BeautifulSoup = object
                self.assertFalse(kinak.stiahni_citania_z_lc_kbs(date(2026, 6, 7), vystup))
                self.assertFalse(vystup.exists())

                kinak.requests = object()
                kinak.BeautifulSoup = None
                self.assertFalse(kinak.stiahni_citania_z_lc_kbs(date(2026, 6, 7), vystup))
                self.assertFalse(vystup.exists())
            finally:
                kinak.requests = povodne_requests
                kinak.BeautifulSoup = povodne_bs

    def test_stiahni_lc_kbs_soup_http_500_preskoci_bez_tracebacku(self):
        class FakeHTTPError(Exception):
            pass

        class FakeResponse:
            status_code = 500
            text = ""
            apparent_encoding = "utf-8"
            encoding = None

            def raise_for_status(self):
                exc = FakeHTTPError("500 Server Error")
                exc.response = self
                raise exc

        class FakeRequests:
            RequestException = FakeHTTPError
            HTTPError = FakeHTTPError
            Timeout = TimeoutError
            ConnectionError = ConnectionError

            def __init__(self):
                self.calls = 0

            def get(self, url, headers=None, timeout=None):
                self.calls += 1
                return FakeResponse()

        povodne_requests = kinak.requests
        povodne_bs = kinak.BeautifulSoup
        povodne_log_info = kinak.log_info
        povodne_log_exception = kinak.log_exception
        povodne_pokusy = kinak.LC_KBS_REFRENY_MAX_POKUSOV
        povodne_delay = kinak.LC_KBS_REFRENY_RETRY_DELAY_S
        infos = []
        errors = []
        fake_requests = FakeRequests()

        try:
            kinak.requests = fake_requests
            kinak.BeautifulSoup = lambda *args, **kwargs: object()
            kinak.log_info = lambda message: infos.append(message)
            kinak.log_exception = lambda context, exc: errors.append((context, exc))
            kinak.LC_KBS_REFRENY_MAX_POKUSOV = 2
            kinak.LC_KBS_REFRENY_RETRY_DELAY_S = 0

            self.assertIsNone(kinak._stiahni_lc_kbs_soup(date(2026, 1, 31)))

            self.assertEqual(2, fake_requests.calls)
            self.assertEqual([], errors)
            self.assertTrue(any("HTTP 500" in message for message in infos))
        finally:
            kinak.requests = povodne_requests
            kinak.BeautifulSoup = povodne_bs
            kinak.log_info = povodne_log_info
            kinak.log_exception = povodne_log_exception
            kinak.LC_KBS_REFRENY_MAX_POKUSOV = povodne_pokusy
            kinak.LC_KBS_REFRENY_RETRY_DELAY_S = povodne_delay


if __name__ == "__main__":
    unittest.main()
