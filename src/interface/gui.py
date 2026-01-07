"""The main GUI class of the app.
"""
import asyncio
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Input,
    Button,
    Static,
    Tree,
    DataTable,
    TabbedContent,
    TabPane,
    LoadingIndicator
)

# Import del backend
# from analyzer.dep_tree_builder import build_dependency_tree_for


class LicenseSentinelUI(App):
    """
    Main GUI application class for LicenseSentinel.

    This class is responsible for constructing and managing the user interface,
    handling user input, updating the dependency tree visualization, and displaying
    PyPI metadata and ScanCode results. Key attributes include:

    - dep_tree: The Tree widget displaying package dependencies.
    - spinner: A LoadingIndicator shown during background operations.

    The class also provides methods for updating the dependency tree and populating
    data tables for PyPI and ScanCode results.
    """
    THEME = "harlequin"
    CSS_PATH = "style.css"

    def __init__(self):
        super().__init__()
        # Tree dinamico
        self.dep_tree = Tree("Dipendenze")
        # Spinner (inizialmente nascosto)
        self.spinner = LoadingIndicator(
            id="spinner", classes="hidden")
    def compose(self) -> ComposeResult:
        """The base composable method of the program.

        Returns:
            ComposeResult: The result of the composition.

        Yields:
            Iterator[ComposeResult]: Async intermediate composition results
        """
        with Horizontal(classes="urlbar"):
            yield Input(placeholder="Inserisci un package PyPI "\
                "(es: flask)", id="url", classes="url-input")
            yield Button("Invia", id="send", classes="url-button")

        with Vertical(classes="main-container", id="main-container"):
            with Horizontal(classes="main-row"):

                with Vertical(classes="dependency") as dependency_block:
                    dependency_block.border_title = "Dependency Tree"
                    dependency_block.styles.border_title_align = "right"

                    yield self.dep_tree


                    yield self.spinner

                with Vertical(classes="right-column"):
                    with Vertical(classes="section-box pypi-block")\
                    as pypi_block:
                        pypi_block.border_title = "PyPI Metadata"
                        pypi_block.styles.border_title_align = "right"
                        with TabbedContent():
                            yield TabPane("Pacchetti", self._pypi_table())
                            yield TabPane(
                                "Info", 
                                Static("Info pacchetti PyPI..."))
                        # yield Static("Risultati PyPI", classes="footer-title")

                    with Vertical(classes="section-box scancode-block")\
                    as scancode_block:
                        scancode_block.border_title = "ScanCode Results"
                        scancode_block.styles.border_title_align = "right"
                        with TabbedContent():
                            yield TabPane("File", self._scancode_table())
                            yield TabPane(
                                "Dettagli", 
                                Static("Dettagli analisi ScanCode...")
                            )
                        # yield Static("Risultati ScanCode", classes="footer-title")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handles the button press event for the "send" button.

        When the button is pressed, this async handler:
        1. Retrieves the package name from the input field.
        2. Shows a loading spinner in the UI.
        3. Asynchronously builds the dependency tree for the given package
           by running the backend function in a separate thread.
        4. Hides the loading spinner once the backend task is complete.
        5. Updates the dependency tree widget in the UI with the new data.
        """
        if event.button.id == "send":
            package = self.query_one("#url", Input).value.strip()

            if not package:
                self.log("Nessun package inserito")
                return

            # Mostra spinner
            self.spinner.remove_class("hidden")
            self.refresh()

            # Esegui il backend in un thread separato
            # (compatibile con TUTTE le Textual)
            loop = asyncio.get_running_loop()

            # Obviously this fuction should NOT be print
            # I put it here to keep pylint calmer
            graph = await loop.run_in_executor(None, print, package)

            # Nascondi spinner
            self.spinner.add_class("hidden")

            # Aggiorna il Tree nella GUI
            self.update_dependency_tree(package, graph)

    def update_dependency_tree(self, root_pkg: str, graph: dict):
        """
        Update the dependency tree widget with the given dependency graph.

        Args:
            root_pkg (str): The name of the root package.
            graph (dict): A dictionary representing the dependency graph
            where keys are package names and values are 
            lists of dependencies.
        """
        self.dep_tree.root.set_label(root_pkg)
        self.dep_tree.root.remove_children()

        def add_nodes(parent, pkg):
            deps = graph.get(pkg, [])
            for dep in deps:
                node = parent.add(dep)
                add_nodes(node, dep)

        add_nodes(self.dep_tree.root, root_pkg)

        # Espandi tutto automaticamente
        self.dep_tree.root.expand_all()

        self.dep_tree.refresh(layout=True)

    def _pypi_table(self) -> DataTable:
        table = DataTable()
        table.add_columns("Pacchetto", "Licenza dichiarata")
        return table

    def _scancode_table(self) -> DataTable:
        table = DataTable()
        table.add_columns("File", "Licenza rilevata")
        return table


if __name__ == "__main__":
    LicenseSentinelUI().run()
