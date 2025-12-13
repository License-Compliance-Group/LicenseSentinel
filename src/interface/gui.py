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
from textual import events

# Import del backend
from infrastructure.pypi_client import PyPiHandler
from infrastructure.repo_downloader import RepoDownloader
from infrastructure.dep_tree_builder import DepTreeBuilder

from analyzer.package_metadata_fetcher import PackageMetadataFetcher


class LicenseSentinelUI(App):
    """
    Main GUI application class for LicenseSentinel.

    This class is responsible for constructing and managing the user interface,
    handling user input, updating the dependency tree visualization, and displaying
    PyPI metadata and ScanCode results. Key attributes include:

    - ui_tree: The Tree widget displaying package dependencies.
    - spinner: A LoadingIndicator shown during background operations.

    The class also provides methods for updating the dependency tree and populating
    data tables for PyPI and ScanCode results.
    """
    THEME = "harlequin"
    CSS_PATH = "style.css"

    def __init__(self):
        super().__init__()

        self.pypi_client = PyPiHandler()
        self.repo_downloader = RepoDownloader()
        self.dep_builder = DepTreeBuilder()
        # Sarà inizializzato al click del bottone
        self.fetcher = None

    def _pypi_table(self) -> DataTable:
        table = DataTable()
        table.add_columns("Pacchetto", "Licenza dichiarata")
        return table

    def _scancode_table(self) -> DataTable:
        table = DataTable()
        table.add_columns("File", "Licenza rilevata")
        return table

    def compose(self) -> ComposeResult:
        with Horizontal(classes="path-container"):
            yield Input(placeholder="Insert requirements.txt path",
                        id="path",
                        classes="path-input")
            yield Button("Check", id="send", classes="url-button")

        with Vertical(classes="main-container", id="main-container"):
            with Horizontal(classes="main-row"):

                with Vertical(classes="dependency") as dependency_block:
                    dependency_block.border_title = "Dependency Tree"
                    dependency_block.styles.border_title_align = "right"

                    # Tree dinamico
                    self.ui_tree = Tree("Dependencies")
                    yield self.ui_tree

                    # Spinner (inizialmente nascosto)
                    self.spinner = LoadingIndicator(
                        id="spinner", classes="hidden")
                    yield self.spinner

                with Vertical(classes="right-column"):
                    with Vertical(classes="section-box pypi-block") as pypi_block:
                        pypi_block.border_title = "PyPI Metadata"
                        pypi_block.styles.border_title_align = "right"
                        with TabbedContent():
                            yield TabPane("Pacchetti", self._pypi_table())
                            yield TabPane("Info", Static("Info pacchetti PyPI..."))
                        # yield Static("Risultati PyPI", classes="footer-title")

                    with Vertical(classes="section-box scancode-block") as scancode_block:
                        scancode_block.border_title = "ScanCode Results"
                        scancode_block.styles.border_title_align = "right"
                        with TabbedContent():
                            yield TabPane("File", self._scancode_table())
                            yield TabPane("Dettagli", Static("Dettagli analisi ScanCode..."))
                        # yield Static("Risultati ScanCode", classes="footer-title")

# ============================================================================#
#                              Event Handlers                                 #
# ============================================================================#

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
            input_widget = self.query_one("#path", Input)
            package = input_widget.value.strip()

            if not package:
                # show message as placeholder and mark input + outer bar as error
                input_widget.placeholder = "PATH is empty"
                input_widget.add_class("path-input-error")
                try:
                    self.query_one(
                        ".path-container").add_class("path-container-error")
                except Exception:
                    pass
                return

            # clear any previous error state and restore placeholder
            input_widget.remove_class("path-input-error")
            try:
                self.query_one(
                    ".path-container").remove_class("path-container-error")
            except Exception:
                pass
            input_widget.placeholder = "Insert requirements.txt path"

            self.fetcher = PackageMetadataFetcher(
                self.pypi_client,
                self.dep_builder,
                self.repo_downloader
            )
            # Mostra spinner
            self.spinner.remove_class("hidden")
            self.refresh()

            # Esegui il backend in un thread separato (compatibile con TUTTE le Textual)
            loop = asyncio.get_running_loop()
            metdt = await loop.run_in_executor(None, self.fetcher.build_package_metadata, package)

            # Nascondi spinner
            self.spinner.add_class("hidden")

            # Aggiorna il Tree nella GUI
            graph = self.fetcher.get_graph()
            self.update_dependency_tree(package, graph)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Clear error state when the user starts typing in the URL input."""
        widget = getattr(event, "input", None) or getattr(
            event, "target", None)
        if widget is None:
            return
        if widget.id == "path" and widget.value.strip():
            widget.remove_class("path-input-error")
            try:
                self.query_one(
                    ".path-container").remove_class("path-container-error")
            except Exception:
                pass
            widget.placeholder = "Insert requirements.txt path"

    async def on_blur(self, event: events.Blur) -> None:
        """Reset styles when the URL input (or its container) loses focus."""
        widget = getattr(event, "target", None)
        if widget is None:
            return
        # If the blurred widget is the path input (or a child), reset styles
        if getattr(widget, "id", None) == "path" or "path" in getattr(widget, "classes", []):
            try:
                url_input = self.query_one("#url", Input)
            except Exception:
                url_input = None
            try:
                self.query_one(
                    ".path-container").remove_class("path-container-error")
            except Exception:
                pass
            if url_input:
                url_input.remove_class("path-input-error")
                url_input.placeholder = "Insert requirements.txt path"

    def update_dependency_tree(self, root_pkg: str, graph: dict):
        """
        Update the dependency tree widget with the given dependency graph.

        Args:
            root_pkg (str): The name of the root package.
            graph (dict): A dictionary representing the dependency graph,
            where keys are package names and values are lists of dependencies.
        """
        self.ui_tree.root.set_label(root_pkg)
        self.ui_tree.root.remove_children()

        def add_nodes(parent, pkg):
            deps = graph.get(pkg, [])
            for dep in deps:
                node = parent.add(dep)
                add_nodes(node, dep)

        add_nodes(self.ui_tree.root, root_pkg)

        # Espandi tutto automaticamente
        self.ui_tree.root.expand_all()

        self.ui_tree.refresh(layout=True)


if __name__ == "__main__":
    LicenseSentinelUI().run()
