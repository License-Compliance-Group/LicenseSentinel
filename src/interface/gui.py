import asyncio
import logging
from pathlib import Path
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
    LoadingIndicator,
    Log
)
from textual import events, on

# Import del backend
from infrastructure.pypi_client import PyPiHandler
from infrastructure.repo_downloader import RepoDownloader
from infrastructure.dep_tree_builder import DepTreeBuilder
from infrastructure.connectivity import Connectivity
from analyzer.package_metadata_fetcher import PackageMetadataFetcher

ERROR_PLACEHOLDER = "❌ Invalid path!"
INFO_PLACEHOLDER = "📄 Insert the path to the requirements.txt file"


class TextualLogHandler(logging.Handler):
    """Logging handler that writes to a Textual Log widget."""

    def __init__(self, app_getter):
        super().__init__()
        self._app_getter = app_getter

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()

        app = self._app_getter()
        if app is None:
            return

        def _write():
            log_widget = getattr(app, "log_view", None)
            if log_widget:
                try:
                    log_widget.write_line(msg)
                except Exception:
                    pass

        try:
            app.call_from_thread(_write)
        except Exception:
            pass


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
    # THEME = "harlequin"
    CSS_PATH = "style.css"

    def __init__(self):
        super().__init__()
        # self.theme = "tokyo-night"
        # Backend components
        self.pypi_client = PyPiHandler()
        self.repo_downloader = RepoDownloader()
        self.dep_builder = DepTreeBuilder()
        # TODO: reset fetcher on each analysis
        self.fetcher = PackageMetadataFetcher(
            self.pypi_client,
            self.dep_builder,
            self.repo_downloader
        )

        # UI components
        self.ui_tree = Tree("Dependencies")  # Tree
        # Spinner (Initially hidden)
        self.spinner = LoadingIndicator(id="spinner", classes="hidden")
        self._path_input_has_error = False

        # Log widget for displaying build output
        self.log_view: Log | None = None
        self._log_handler = None
        self._setup_logging()

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
            yield Input(placeholder=INFO_PLACEHOLDER, id="path", classes="path-input")
            yield Button("Check", id="send", classes="url-button")

        with Vertical(classes="main-container", id="main-container"):
            with Horizontal(classes="main-row"):
                yield from self._compose_dependency_section()
                yield from self._compose_right_column()

    def _compose_dependency_section(self) -> ComposeResult:
        """Compose the dependency tree section."""
        with Vertical(classes="dependency") as block:
            block.border_title = "Dependency Tree"
            block.styles.border_title_align = "right"
            yield self.ui_tree
            yield self.spinner

    def _compose_right_column(self) -> ComposeResult:
        """Compose the right column with PyPI and ScanCode sections."""
        with Vertical(classes="right-column"):
            yield from self._compose_pypi_section()
            yield from self._compose_scancode_section()

    def _compose_pypi_section(self) -> ComposeResult:
        """Compose the PyPI metadata section."""
        with Vertical(classes="section-box pypi-block") as block:
            block.border_title = "PyPI Metadata"
            block.styles.border_title_align = "right"
            with TabbedContent():
                yield TabPane("Incompatibilities", self._pypi_table())
                yield TabPane("Info", Static("Info PyPI..."))

    def _compose_scancode_section(self) -> ComposeResult:
        """Compose the ScanCode results section."""
        with Vertical(classes="section-box scancode-block") as block:
            block.border_title = "ScanCode Results"
            block.styles.border_title_align = "right"
            with TabbedContent():
                yield TabPane("File", self._scancode_table())
                yield TabPane("Dettagli", Static("Dettagli analisi ScanCode..."))

# =================================================================================#
#                                   Helpers                                        #
# =================================================================================#

    def _set_path_error(self, show_error: bool) -> None:
        """Set or clear the path input error state.

        Args:
            show_error: True to show error, False to clear it.
        """
        path_input = self.query_one("#path", Input)
        path_container = self.query_one(".path-container", Horizontal)

        self._path_input_has_error = show_error

        if show_error:
            path_input.placeholder = ERROR_PLACEHOLDER
            path_input.add_class("path-input-error")
            if path_container:
                path_container.add_class("path-container-error")
        else:
            path_input.placeholder = INFO_PLACEHOLDER
            path_input.remove_class("path-input-error")
            if path_container:
                path_container.remove_class("path-container-error")

    def _setup_logging(self) -> None:
        """Setup logging handler to forward logs to the UI Log widget."""
        if self._log_handler is not None:
            return

        handler = TextualLogHandler(lambda: self)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s [%(name)s]: %(message)s', datefmt='%H:%M:%S'))
        handler.setLevel(logging.INFO)

        # Attach to the root logger to capture logs from all modules
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

        self._log_handler = handler

    async def _mount_log_console(self, before_widget) -> None:
        """Create and mount the log console widget."""
        self.log_view = Log(classes="log-console")
        self.log_view.styles.scrollbar_background = "#1e1e1e"
        self.log_view.styles.scrollbar_corner_color = "#1e1e1e"
        self.log_view.styles.scrollbar_color = "#cc8a36"
        self.log_view.styles.scrollbar_color_hover = "#d69a46"
        await self.mount(self.log_view, before=before_widget)
        self.log_view.write_line("Starting dependency analysis...")

# =================================================================================#
#                                 Event Handlers                                   #
# =================================================================================#
    @on(Button.Pressed, "#send")
    async def handle_check_button(self, event: Button.Pressed) -> None:
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

            if not package or not self.input_check(package):
                # show error state
                input_widget.value = ""
                self._set_path_error(True)
                return

            # clear any previous error state
            self._set_path_error(False)

            # Hide input bar and mount log widget
            path_container = self.query_one(".path-container", Horizontal)
            path_container.add_class("hidden")

            if self.log_view is None:
                await self._mount_log_console(path_container)

            # Mostra spinner
            self.spinner.remove_class("hidden")
            self.refresh()

            # Esegui il backend in un thread separato (compatibile con TUTTE le Textual)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.fetcher.build_package_metadata, package)

            # Nascondi spinner
            self.spinner.add_class("hidden")

            if self.log_view:
                self.log_view.write_line("\n✅ Analysis complete!")

            # Aggiorna il Tree nella GUI
            graph = self.fetcher.get_graph()
            self.update_dependency_tree("root", graph)

    @on(Input.Changed, "#path")
    async def on_path_input_changed(self, event: Input.Changed) -> None:
        """Clear error state when the user starts typing in the path input."""
        if event.input.value.strip() and self._path_input_has_error:
            self._set_path_error(False)

    async def on_mouse_down(self, event: events.MouseDown) -> None:
        """Fallback: when the user clicks anywhere, clear the input error
        if the path input currently shows an error and the click is outside
        the input/container.
        """
        if not self._path_input_has_error:
            return

        path_input = self.query_one("#path", Input)
        path_container = self.query_one(".path-container", Horizontal)

        # If click landed on the input or on its container, don't clear yet
        if event.widget is path_input or event.widget is path_container:
            return

        # otherwise clear the error state
        self._set_path_error(False)

# =================================================================================#
#                                   View Updaters                                  #
# =================================================================================#

    def update_dependency_tree(self, root_pkg: str, graph: dict):
        """Update the dependency tree with package dependencies."""
        root = self.ui_tree.root
        root.set_label(root_pkg)
        root.remove_children()

        def add_nodes(parent, pkg):
            for dep in graph.get(pkg, []):
                add_nodes(parent.add(dep), dep)

        add_nodes(root, root_pkg)
        root.expand_all()
        self.ui_tree.refresh(layout=True)

# =================================================================================#
#                                   Logic                                          #
# =================================================================================#

    def input_check(self, path: str) -> bool:
        """Check if the input path is valid (non-empty).

        Args:
            path (str): The input path to validate. 
        Returns:
            bool: True if the path is valid, False otherwise.
        """
        path_obj = Path(path.strip())

        return bool(Connectivity.check_file_exists(path_obj))


if __name__ == "__main__":
    LicenseSentinelUI().run()


#  C:\Users\Dabaduck\Desktop\LicensesChecker\src\requirements.txt
