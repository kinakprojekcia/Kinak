# -*- coding: utf-8 -*-

from datetime import date, timedelta
import importlib.util
from pathlib import Path
import unittest


KINAK_PATH = Path("/mnt/data/Kinak.py")
spec = importlib.util.spec_from_file_location("Kinak", KINAK_PATH)
kinak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinak)


class VianocnaOktavaTest(unittest.TestCase):
    SCENAR_2026 = [
        (date(2026, 12, 25), "1VI", "NARODENIE PÁNA (Slávnosť)", "Žalm z 1VI zajtra STEF", "46, 1-2"),
        (date(2026, 12, 26), "STEF", "SV. ŠTEFANA, PRVÉHO MUČENÍKA (Sviatok)", "Žalm z STEF zajtra SR", "40, 1-2"),
        (date(2026, 12, 27), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA (Sviatok)", "Žalm z SR zajtra NEV", "62, 1-2"),
        (date(2026, 12, 28), "NEV", "SV. NEVINIATOK, MUČENÍKOV (Sviatok)", "Žalm z NEV zajtra 1VI", "455, 1"),
        (date(2026, 12, 29), "1VI", "5. deň Vianočnej oktávy", "Žalm z 1VI zajtra 1VI", "46, 1-2"),
        (date(2026, 12, 30), "1VI", "6. deň Vianočnej oktávy", "Žalm z 1VI zajtra PDR", "46, 1-2"),
        (date(2026, 12, 31), "PDR", "POSLEDNÝ DEŇ ROKA", "Žalm z PDR zajtra PMB", "71, 1-2"),
        (date(2027, 1, 1), "PMB", "PANNY MÁRIE BOHORODIČKY (Slávnosť)", "Žalm z PMB zajtra 2VI", "67, 1-2 / 219, 1-3"),
    ]

    SCENAR_NARODENIE_PANA_V_NEDELU = [
        (date(2022, 12, 25), "1VI", "NARODENIE PÁNA (Slávnosť)", "Žalm z 1VI zajtra STEF", "46, 1-2"),
        (date(2022, 12, 26), "STEF", "SV. ŠTEFANA, PRVÉHO MUČENÍKA (Sviatok)", "Žalm z STEF zajtra SJE", "40, 1-2"),
        (date(2022, 12, 27), "SJE", "SV. JÁNA, APOŠTOLA A EVANJELISTU", "Žalm z SJE zajtra NEV", "62, 1-2"),
        (date(2022, 12, 28), "NEV", "SV. NEVINIATOK, MUČENÍKOV (Sviatok)", "Žalm z NEV zajtra 1VI", "455, 1"),
        (date(2022, 12, 29), "1VI", "5. deň Vianočnej oktávy", "Žalm z 1VI zajtra SR", "46, 1-2"),
        (date(2022, 12, 30), "SR", "SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA (Sviatok)", "Žalm z SR zajtra PDR", "62, 1-2"),
        (date(2022, 12, 31), "PDR", "POSLEDNÝ DEŇ ROKA", "Žalm z PDR zajtra PMB", "71, 1-2"),
        (date(2023, 1, 1), "PMB", "PANNY MÁRIE BOHORODIČKY (Slávnosť)", "Žalm z PMB zajtra 2VI", "67, 1-2 / 219, 1-3"),
    ]

    def assert_den_oktavy(self, datum, kod, text_hlavicky, text_statusu, uvod):
        with self.subTest(datum=datum):
            hlavicka = kinak.zostav_text_hlavicky("A", datum)
            status = kinak.zostav_text_status_baru(datum)
            # ziskaj_jks_odporucania_dnes už neexistuje, skús alternatívy
            odporucania = None
            if hasattr(kinak, "ziskaj_jks_odporucania_dnes"):
                odporucania = kinak.ziskaj_jks_odporucania_dnes(datum)
            elif hasattr(kinak, "ziskaj_odporucania"):
                try:
                    odporucania = kinak.ziskaj_odporucania(datum)
                except Exception:
                    odporucania = None

            self.assertEqual(kod, kinak.vypocitaj_kod_liturgickej_casti(datum))
            self.assertIn(text_hlavicky, hlavicka)
            self.assertIn(text_statusu, status)
            self.assertIn("Žaltár v breviári:", status)
            if odporucania is not None:
                self.assertEqual(uvod, odporucania.get("Úvod"))

    def test_vianocna_oktava_2026_den_po_dni(self):
        for scenar in self.SCENAR_2026:
            self.assert_den_oktavy(*scenar)

    def test_vianocna_oktava_ked_narodenie_pana_pripadne_na_nedelu(self):
        for scenar in self.SCENAR_NARODENIE_PANA_V_NEDELU:
            self.assert_den_oktavy(*scenar)

    def test_svata_rodina_je_30_decembra_ked_narodenie_pana_pripadne_na_nedelu(self):
        self.assertEqual("1VI", kinak.vypocitaj_kod_liturgickej_casti(date(2022, 12, 29)))
        self.assertEqual("SR", kinak.vypocitaj_kod_liturgickej_casti(date(2022, 12, 30)))

    def test_svata_rodina_nahradi_sv_stefana_ked_26_december_pripadne_na_nedelu(self):
        datum = date(2021, 12, 26)
        hlavicka = kinak.zostav_text_hlavicky("A", datum)
        status = kinak.zostav_text_status_baru(datum)

        self.assertEqual("SR", kinak.vypocitaj_kod_liturgickej_casti(datum))
        self.assertIn("SVÄTEJ RODINY JEŽIŠA, MÁRIE A JOZEFA", hlavicka)
        # 26.12.2021 je nedeľa = SR, zajtra 27.12.2021 je SJE
        self.assertIn("Žalm z SR zajtra SJE", status)
        self.assertNotIn("STEF", status)


if __name__ == "__main__":
    unittest.main()
