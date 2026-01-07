import unittest
from unittest.mock import MagicMock
from src.analyzer.license_comparator import LicenseComparator
from src.entities.scan_engine import ScanEngine
from src.entities.pypi_metadata import PyPIMetadata

class TestLicenseComparator(unittest.TestCase):

    def setUp(self):
        """
        setUp viene eseguito PRIMA di OGNI test. È utile per inizializzare oggetti comuni.
        Qui creiamo un mock dello ScanEngine che verrà usato in tutti i test.
        """
        self.mock_scan_engine = MagicMock(spec=ScanEngine)
        
    def test_init_and_process(self):
        """
        Test del costruttore (__init__): verifichiamo che i dati vengano processati (normalizzati) correttamente all'avvio.
        """
        # Creiamo un finto oggetto metadati
        meta = MagicMock(spec=PyPIMetadata)
        meta.package = "PkgA"
        meta.license_type = "MIT License"
        
        tree_a = [meta]
        
        # Istanziamo la classe da testare passando il mock
        comparator = LicenseComparator(tree_a, self.mock_scan_engine)
        
        # Verifiche sullo stato interno dell'oggetto
        self.assertIn("PkgA", comparator.tree_a)
        # Verifichiamo che "MIT License" sia stato normalizzato in "mit"
        self.assertEqual(comparator.tree_a["PkgA"], "mit")

    def test_compare_license_trees_match(self):
        """
        Test caso positivo: la licenza dichiarata su PyPI coincide con quella trovata dallo scanner.
        """
        meta = MagicMock(spec=PyPIMetadata)
        meta.package = "PkgA"
        meta.license_type = "MIT"
        
        comparator = LicenseComparator([meta], self.mock_scan_engine)
        
        # Configuriamo il mock: quando viene chiamato scan_for_license, restituisce ["mit"]
        # Simuliamo che lo scanner abbia trovato "mit" nei file.
        self.mock_scan_engine.scan_for_license.return_value = ["mit"]
        
        # Eseguiamo il confronto
        disc, doubts = comparator.compare_license_trees()
        
        # Ci aspettiamo 0 discrepanze e 0 dubbi (successo totale)
        self.assertEqual(len(disc), 0)
        self.assertEqual(len(doubts), 0)
        
    def test_compare_license_trees_mismatch(self):
        """
        Test discrepanza: PyPI dice MIT, ma lo scanner trova GPL-2.0.
        """
        meta = MagicMock(spec=PyPIMetadata)
        meta.package = "PkgA"
        meta.license_type = "MIT"
        
        comparator = LicenseComparator([meta], self.mock_scan_engine)
        
        # Lo scanner trova una licenza diversa
        self.mock_scan_engine.scan_for_license.return_value = ["gpl-2.0"]
        
        # override_cache=True forza la ri-scansione (utile nel test)
        disc, doubts = comparator.compare_license_trees(override_cache=True)
        
        # Ci aspettiamo 1 discrepanza
        self.assertEqual(len(disc), 1)
        # Verifichiamo i dettagli della discrepanza
        self.assertEqual(disc[0][0], "PkgA")    # Pacchetto
        self.assertEqual(disc[0][1], "mit")     # Dichiarato
        self.assertEqual(disc[0][2], ("gpl-2.0",)) # Trovato

    def test_compare_license_trees_multiple_match(self):
        """
        Test ambiguità risolta: lo scanner trova più licenze, ma UNA di queste corrisponde a quella dichiarata.
        Attualmente il codice lo classifica come "doubt" (dubbio/cauzione).
        """
        meta = MagicMock(spec=PyPIMetadata)
        meta.package = "PkgA"
        meta.license_type = "MIT"
        
        comparator = LicenseComparator([meta], self.mock_scan_engine)
        
        # Simuliamo che lo scanner trovi SIA Apache CHE MIT
        self.mock_scan_engine.scan_for_license.return_value = ["apache-2.0", "mit"]
        
        disc, doubts = comparator.compare_license_trees(override_cache=True)
        
        # Ci aspettiamo un 'doubt'
        self.assertEqual(len(doubts), 1)
        self.assertEqual(len(disc), 0)
        self.assertEqual(doubts[0][0], "PkgA")
        self.assertEqual(doubts[0][1], "mit")
        self.assertIn("apache-2.0", doubts[0][2])

    def test_compare_license_trees_missing_in_scan(self):
        """
        Test gestione errori scanner: cosa succede se lo scanner non restituisce nulla (lista vuota)?
        """
        meta = MagicMock(spec=PyPIMetadata)
        meta.package = "PkgA"
        meta.license_type = "MIT"
        
        comparator = LicenseComparator([meta], self.mock_scan_engine)
        
        self.mock_scan_engine.scan_for_license.return_value = []
        
        # Il codice attuale fallisce con IndexError se la lista è vuota.
        # assertRaises verifica che questo errore venga sollevato come previsto.
        with self.assertRaises(IndexError):
            comparator.compare_license_trees()

    def test_compare_license_trees_single_unknown(self):
        """
        Test scanner fallito parzialmente: lo scanner restituisce 'Unknown'.
        """
        meta = MagicMock(spec=PyPIMetadata)
        meta.package = "PkgA"
        meta.license_type = "MIT"
        
        comparator = LicenseComparator([meta], self.mock_scan_engine)
        
        self.mock_scan_engine.scan_for_license.return_value = ["Unknown"]
        
        disc, doubts = comparator.compare_license_trees()
        
        # Viene classificato come dubbio
        self.assertEqual(len(doubts), 1)
        self.assertEqual(doubts[0][0], "PkgA")
