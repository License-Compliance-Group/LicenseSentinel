import unittest  # Importiamo il modulo base di Python per il testing
from src.analyzer import license_name_normalizer  # Importiamo il modulo che vogliamo testare (System Under Test)

# Creiamo una classe di test che eredita da unittest.TestCase.
# Questa è la convenzione standard per creare suite di test in Python.
class TestLicenseNameNormalizer(unittest.TestCase):
    
    # Ogni metodo che inizia con 'test_' viene eseguito automaticamente come un caso di test.
    def test_normalize_known_licenses(self):
        """
        Testiamo il "Happy Path": verificare che input validi e noti producano l'output atteso.
        """
        # GPL Family: Verifichiamo che diverse varianti vengano normalizzate allo standard SPDX/OSADL
        # assertEqual verifica che: funzione(input) == risultato_atteso
        self.assertEqual(license_name_normalizer.normalize("GPL-2.0"), "gpl-2.0-only")
        self.assertEqual(license_name_normalizer.normalize("gpl-3.0+"), "gpl-3.0-or-later")
        
        # Apache: Verifichiamo la normalizzazione di Apache 2.0
        self.assertEqual(license_name_normalizer.normalize("Apache License 2.0"), "apache-2.0")
        
        # MIT: Verifichiamo la normalizzazione di MIT
        self.assertEqual(license_name_normalizer.normalize("MIT License"), "mit")
        
        # BSD: Verifichiamo la normalizzazione delle licenze BSD
        self.assertEqual(license_name_normalizer.normalize("BSD 3-Clause"), "bsd-3-clause")
        
    def test_normalize_case_insensitive(self):
        """
        Testiamo la robustezza: la funzione dovrebbe gestire input con maiuscole/minuscole miste.
        """
        # "mit license" (tutto minuscolo) dovrebbe diventare "mit"
        self.assertEqual(license_name_normalizer.normalize("mit license"), "mit")
        # "APACHE LICENSE 2.0" (tutto maiuscolo) dovrebbe diventare "apache-2.0"
        self.assertEqual(license_name_normalizer.normalize("APACHE LICENSE 2.0"), "apache-2.0")

    def test_normalize_unknown_license(self):
        """
        Testiamo i casi limite (Edge Cases): cosa succede se la licenza non è nel dizionario?
        La funzione è progettata per restituire l'input in minuscolo se non trova un match.
        """
        self.assertEqual(license_name_normalizer.normalize("Unknown License xyz"), "unknown license xyz")
        self.assertEqual(license_name_normalizer.normalize(""), "")

    def test_normalize_none_input(self):
        """
        Testiamo la gestione degli errori: cosa succede se passiamo None invece di una stringa?
        Ci aspettiamo che venga sollevata un'eccezione (AttributeError o TypeError),
        perché il codice prova a fare .strip() o .lower() su None.
        """
        # assertRaises è un context manager: il test passa SOLO se il blocco 'with' solleva l'eccezione specificata.
        with self.assertRaises(AttributeError):
            license_name_normalizer.normalize(None)
