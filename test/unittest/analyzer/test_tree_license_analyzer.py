import unittest
from unittest.mock import MagicMock, patch  # Strumenti essenziali per creare oggetti "finti" (mock)
from src.analyzer.tree_license_analyzer import TreeAnalyzer # La classe da testare
from src.entities.pypi_metadata import PyPIMetadata # Una dipendenza necessaria per creare oggetti di input

class TestTreeAnalyzer(unittest.TestCase):

    # @patch sostituisce 'src.analyzer.tree_license_analyzer.LicenseCompatibilityAnalyzer'
    # con un oggetto Mock per la durata del test. Questo isola il test: non usiamo la vera logica di compatibilità.
    @patch('src.analyzer.tree_license_analyzer.LicenseCompatibilityAnalyzer')
    def test_run_tree_compatibility_check_empty_metadata(self, mock_lca_cls):
        """
        Test: Se la lista dei metadati è vuota, la funzione dovrebbe ritornare subito None.
        mock_lca_cls è il mock della classe che abbiamo "patchato".
        """
        # Eseguiamo la funzione con una lista vuota []
        res = TreeAnalyzer.run_tree_compatibility_check([], {})
        # Verifichiamo che il risultato sia None
        self.assertIsNone(res)

    @patch('src.analyzer.tree_license_analyzer.LicenseCompatibilityAnalyzer')
    def test_run_tree_compatibility_check_empty_graph(self, mock_lca_cls):
        """
        Test: Se il grafo delle dipendenze è vuoto, la funzione dovrebbe ritornare None.
        """
        # Creiamo un finto oggetto PyPIMetadata per popolare la lista, ma passiamo un grafo {} vuoto.
        # MagicMock(spec=...) crea un oggetto che imita la struttura della classe specificata.
        metadata = [MagicMock(spec=PyPIMetadata)]
        res = TreeAnalyzer.run_tree_compatibility_check(metadata, {})
        self.assertIsNone(res)

    @patch('src.analyzer.tree_license_analyzer.LicenseCompatibilityAnalyzer')
    def test_detect_incompatible_edges_compatible(self, mock_lca_cls):
        """
        Test: Verifichiamo che non vengano rilevati errori se le licenze sono compatibili.
        """
        # Otteniamo l'istanza del mock (perché LCA viene istanziato dentro la funzione: lca = LicenseCompatibilityAnalyzer())
        mock_lca_instance = mock_lca_cls.return_value
        
        # Configuriamo il mock: quando viene chiamato compare_licenses, deve restituire ("Yes", "Compatible")
        # Questo ci permette di simulare una risposta positiva senza eseguire la vera logica complessa.
        mock_lca_instance.compare_licenses.return_value = ("Yes", "Compatible")

        # Dati di input simulati: grafo semplice e mappa licenze
        graph = {
            "PkgA": ["PkgB"] # PkgA dipende da PkgB
        }
        
        # Usiamo licenze diverse per forzare il controllo (se fossero uguali, il codice potrebbe saltarlo)
        license_by_pkg_diff = {
            "pkga": "mit",
            "pkgb": "bsd-3-clause"
        }

        # Chiamata al metodo statico da testare, passando il mock configurato
        edges = TreeAnalyzer.detect_incompatible_edges(graph, license_by_pkg_diff, mock_lca_instance)
        
        # Assert: ci aspettiamo 0 archi incompatibili
        self.assertEqual(len(edges), 0)

    @patch('src.analyzer.tree_license_analyzer.LicenseCompatibilityAnalyzer')
    def test_detect_incompatible_edges_incompatible(self, mock_lca_cls):
        """
        Test: Verifichiamo che venga rilevata un'incompatibilità in caso di conflitto.
        """
        mock_lca_instance = mock_lca_cls.return_value
        
        # Configuriamo il mock per restituire "No" (Incompatibile)
        mock_lca_instance.compare_licenses.return_value = ("No", "Conflict")

        graph = { "PkgA": ["PkgB"] }
        # Licenza copyleft (GPL) vs Proprietaria -> incompatibili
        license_by_pkg = {
            "pkga": "gpl-2.0-only",
            "pkgb": "proprietary"
        }

        # Esecuzione
        edges = TreeAnalyzer.detect_incompatible_edges(graph, license_by_pkg, mock_lca_instance)
        
        # Verifiche
        self.assertEqual(len(edges), 1) # Deve esserci un errore rilevato
        edge = edges[0]
        # Verifichiamo la struttura della tupla restituita: (parent, lic_parent, dep, lic_dep, (status, msg))
        self.assertEqual(edge[0], "PkgA")
        self.assertEqual(edge[1], "gpl-2.0-only")
        self.assertEqual(edge[2], "PkgB")
        self.assertEqual(edge[4][0], "No") # Il messaggio di stato deve essere "No"

    @patch('src.analyzer.tree_license_analyzer.LicenseCompatibilityAnalyzer')
    def test_run_tree_compatibility_check_integration_mock(self, mock_lca_cls):
        """
        Test di integrazione (mockato): Verifichiamo il flusso completo dalla lista di metadati al risultato.
        """
        mock_lca_instance = mock_lca_cls.return_value
        mock_lca_instance.compare_licenses.return_value = ("No", "Conflict")

        # Preparazione dati complessi con Mock
        pkg_a = MagicMock(spec=PyPIMetadata)
        pkg_a.package = "PkgA"
        pkg_a.license_type = "GPL-2.0" # Verrà normalizzato in gpl-2.0-only

        pkg_b = MagicMock(spec=PyPIMetadata)
        pkg_b.package = "PkgB"
        pkg_b.license_type = "MIT" # Verrà normalizzato in mit

        metadata = [pkg_a, pkg_b]
        graph = {"PkgA": ["PkgB"]}

        # Esecuzione del metodo principale
        result = TreeAnalyzer.run_tree_compatibility_check(metadata, graph)
        
        # Verifica collaterale: ci assicuriamo che la classe LCA sia stata istanziata
        mock_lca_cls.assert_called()
        # E che sia stato chiamato il metodo per aggiornare la matrice
        mock_lca_instance.update_license_matrix.assert_called_once()
        
        # Verifica risultato
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], "gpl-2.0-only") # Verifica che la normalizzazione interna abbia funzionato
