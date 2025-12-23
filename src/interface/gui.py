"""The main GUI class of the app.
"""
import asyncio
import logging
from enum import Enum, auto

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
    Log,
    ListView,
    ListItem
)
from textual import events, on
from interface.controller import Controller

ERROR_PATH_PLACEHOLDER = "❌ Invalid path!"
PATH_PLACEHOLDER = "📄 Insert the path to the requirements.txt file"
LICENSE_PLACEHOLDER = "📜 Select the main repository license..."
ERROR_LICENSE_PLACEHOLDER = "❌ Invalid license!"
ANALYSIS_COMPLETE = "\n✅ Analysis complete! Press Enter ↵ to show command line"
ANALYSIS_STARTING = "⏳ Starting dependency analysis..."
COMMANDS_PLACEHOLDER = "💬 Type a command..."
ERROR_COMMANDS_PLACEHOLDER = "❌ Invalid command!"


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
            try:
                log_widget.write_line(msg)
            except Exception:
                pass

        try:
            app.call_from_thread(_write)
        except Exception:
            pass


class Stage(Enum):
    REQUIREMENTS = auto()
    LICENSE = auto()
    ANALYZING = auto()
    INTERACTIVE = auto()


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
    # self.theme = "tokyo-night"
    CSS_PATH = "style.css"

    def __init__(self):
        super().__init__()

        self.controller = Controller()
        self.stage = Stage.REQUIREMENTS

        # UI components
        self.ui_tree = Tree("Dependencies")  # Tree
        # Spinner (Initially hidden)
        self.spinner = LoadingIndicator(id="spinner", classes="hidden")
        self.input_spinner = LoadingIndicator(
            id="input-spinner", classes="hidden")
        self._path_input_has_error = False

        # Log widget for displaying build output
        self.log_view: Log | None = None
        self._log_handler = None
        self._setup_logging()

        # Suggestion system
        self.suggestions_list: ListView | None = None
        self._setting_up_suggestions = False

        self.filtered_suggestions: list[str] = []
        self._suggestion_data: dict[int, str] = {}
        # Internal flag to avoid double-moving the ListView on a single keypress -> see handle key in suggestions
        self._suppress_list_move = False
        # Track last highlighted item so we can detect deselection
        self._last_highlighted_item: ListItem | None = None

    def _pypi_table(self) -> DataTable:
        table = DataTable(id="pypi-info-table")
        table.add_columns("Package  ", "Declared License    ", "Source code")

        return table

    def _incompatibilities_table(self) -> DataTable:
        table = DataTable(id="incompatibilities-table")
        table.add_columns("Package parent",
                          "Package children", "Incompatibilities")
        return table

    def _scancode_table(self) -> DataTable:
        table = DataTable(id="scancode-table")
        table.add_columns("File", "Detected Licenses")
        return table

    def compose(self) -> ComposeResult:
        with Vertical(id="top-section", classes="top-section"):
            with Horizontal(classes="path-container"):
                with Vertical(id="input-section", classes="input-section"):
                    yield Input(placeholder=PATH_PLACEHOLDER, id="path", classes="path-input")
                yield Button("Next ->", variant="primary", id="send", classes="analyze-button")
            yield self.input_spinner

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
                with TabPane("Info"):
                    yield self._pypi_table()
                with TabPane("Incompatibilities"):
                    yield self._incompatibilities_table()

    def _compose_scancode_section(self) -> ComposeResult:
        """Compose the ScanCode results section."""
        with Vertical(classes="section-box scancode-block") as block:
            block.border_title = "ScanCode Results"
            block.styles.border_title_align = "right"
            with TabbedContent():
                yield TabPane("Scan results", self._scancode_table())
                # yield TabPane("Dettagli", Static("Dettagli analisi ScanCode..."))

# =================================================================================#
#                                 Event Handlers                                   #
# =================================================================================#

    @on(Button.Pressed, "#send")
    async def handle_check_button(self, event: Button.Pressed) -> None:
        """
        Handles the button press event for the "send" button.
        Initiates the process to handle step requirements based on the current stage.
        """
        if event.button.id == "send":
            input_widget = self.query_one("#path", Input)
            await self.process_stage_input(input_widget.value.strip())

    @on(Input.Submitted, "#path")
    async def on_path_submitted(self) -> None:
        """Handle Enter pressed in the path input to start analysis."""
        input_widget = self.query_one("#path", Input)
        await self.process_stage_input(input_widget.value.strip())

    @on(Input.Changed, "#path")
    async def on_path_input_changed(self, event: Input.Changed) -> None:
        """Clear error state when the user starts typing in the path input.
        When in ANALYZING stage, update suggestions based on input."""
        if event.input.value.strip() and self._path_input_has_error:
            self._set_input_error(False)

        # Update suggestions when in LICENSE or INTERACTIVE stage (but not during setup)
        if (self.stage in (Stage.LICENSE, Stage.INTERACTIVE) and
            self.suggestions_list is not None and
                not self._setting_up_suggestions):
            await self._update_suggestions(event.input.value)

    async def on_mouse_down(self, event: events.MouseDown) -> None:
        """When the user clicks anywhere, clear the input error
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
        self._set_input_error(False)

    @on(ListView.Selected, "#suggestions")
    async def on_suggestion_selected(self, event: ListView.Selected) -> None:
        """Populate the input with the selected suggestion."""
        value = self._suggestion_data.get(id(event.item))
        if not value:
            # Fallback: try to read text content from Static widget
            child = getattr(event.item, "children", [None])[0]
            if child and getattr(child, "renderable", None) is not None:
                value = getattr(child.renderable, "plain", None)
        if value:
            self._apply_suggestion(str(value))

    @on(Tree.NodeSelected)
    @on(Tree.NodeHighlighted)
    async def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """When a tree node is selected, print its label to the console."""
        node = getattr(event, "node", None)
        # Skip if no node provided or if it's the root node
        if node is None or getattr(node, "is_root", False):
            return

        label = getattr(node, "label", None)
        label_str = str(label) if label is not None else ""
        self._update_pypi_table(label_str)
        self._update_incompatibilities_table(label_str)
#
    # INVECE DI FARE UN FOR E SEGNARE L'ULTIMO EVIDENZIATO
    # VEDI SE ESISTE UNLIGHTED ITEM E RIMUOVI LA PROPRIETÀ CSS
    # oppure per ogni elemento selezionato salvalo come previous
    # e rimuovi la classe da quello vecchio

    @on(ListView.Highlighted, "#suggestions")
    async def on_suggestion_highlighted(self, event: ListView.Highlighted) -> None:
        """When the ListView highlight changes, sync the visual --highlight class
        so keyboard navigation shows the same background as mouse hover.
        """

        if self.suggestions_list is None:
            return

        # Remove highlight from previous item
        if self._last_highlighted_item is not None:
            self._last_highlighted_item.remove_class(
                "--highlight")  # was a try
            self._last_highlighted_item = None

        # Apply highlight to newly highlighted item
        item = getattr(event, "item", None)
        if item is not None:
            try:
                item.add_class("--highlight")
                self._last_highlighted_item = item
            except Exception:
                self._last_highlighted_item = None

    @on(events.Key)
    async def handle_suggestions_keypress(self, event: events.Key) -> None:
        # Only handle keys when suggestions overlay is visible
        # or self.stage in (Stage.LICENSE, Stage.INTERACTIVE):
        if self.suggestions_list is None or self.suggestions_list.has_class("hidden"):
            return

        # Handle DOWN key from input to move focus to suggestions
        key = event.key.lower()
        if key in ("down", "arrow_down"):
            input_widget = self.query_one("#path", Input)
            if input_widget.has_focus:
                self.suggestions_list.focus()
                if hasattr(self.suggestions_list, "index"):
                    self.suggestions_list.index = 0
                    if self._last_highlighted_item is not None:
                        self._last_highlighted_item.add_class("--highlight")

            return
        # If first item is highlighted and user presses UP, move focus back to input
        if key in ("up", "arrow_up"):
            suggestion_widget = self.query_one("#suggestions", ListView)
            if suggestion_widget.has_focus and self.suggestions_list.index == 0:
                # Remove highlight from current (first) item
                if self._last_highlighted_item is not None:
                    self._last_highlighted_item.remove_class("--highlight")
                    input_widget = self.query_one("#path", Input)
                    input_widget.focus()
        return

    @on(events.Key)
    async def console_enter_key(self, event: events.Key) -> None:
        """When the console is mounted, pressing Enter will unmount it
        and remount the original input bar so the user can type again."""
        # Only act on Enter and when the log console is mounted/visible
        if event.key.lower() != "enter" or self.stage != Stage.ANALYZING or not self.log_view:
            return

        await self.process_stage_input("")

# =================================================================================#
#                                   Helpers                                        #
# =================================================================================#

    async def process_stage_input(self, input_value: str) -> None:
        """Handle the three-step input flow and trigger analysis when ready.

        Behaviour by stage:
        - REQUIREMENTS: validate and store the requirements file path, switch
          to the LICENSE stage and update input/button UI.
        - LICENSE: validate the provided license, store it and start analysis.
        - ANALYZING: input is ignored (analysis in progress).

        Args:
            #path` input.
            input_value: The raw string entered by the user in the `

        Returns:
            None
        """

        match self.stage:
            case Stage.REQUIREMENTS:
                # disable logging for rendering
                logging.disable(logging.CRITICAL)
                if Controller.path_check(input_value):
                    self.controller.requirements_path = input_value
                    self.stage = Stage.LICENSE
                    self.query_one(
                        "#path", Input).placeholder = LICENSE_PLACEHOLDER
                    self.query_one("#send", Button).label = "Analyze 📊"
                    self.query_one("#path", Input).value = ""
                    # clear error state
                    self._set_input_error(False)
                    await self._mount_suggestions()
                else:
                    self.stage = Stage.REQUIREMENTS
                    self._set_input_error(True)
                return

            case Stage.LICENSE:
                if Controller.license_check(input_value) and Controller.path_check(self.controller.requirements_path):
                    self.controller.main_license = input_value  # assign canonical license
                    self.stage = Stage.ANALYZING
                    logging.disable(logging.NOTSET)  # re-enable logging
                    await self._start_analysis(self.controller.requirements_path)
                else:
                    self.stage = Stage.LICENSE
                    # invalid license
                    self._set_input_error(True)
                return

            case Stage.ANALYZING:
                # Carica il tree ottenuto da _start_analysis
                root, graph = self.controller.get_graph()
                self.update_dependency_tree(root, graph)
                # Smonta la vecchia interfaccia e passa alla INTERACTIVE
                await self._unmount_log_console()
                await self._mount_input_bar()
                self._setting_up_suggestions = False
                send_button = self.query_one("#send", Button)
                input_widget = self.query_one("#path", Input)
                input_widget.placeholder = COMMANDS_PLACEHOLDER
                send_button.label = "Execute ▶"
                input_widget.value = ""
                self.stage = Stage.INTERACTIVE
                return

            case Stage.INTERACTIVE:
                if not self.controller.is_valid_command(input_value):
                    self._set_input_error(True)
                    return
                await self._process_command_input(input_value)
                return
        raise ValueError(f"Unknown stage. Actual stage: {self.stage}")

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

    async def _process_command_input(self, command: str) -> None:
        """Process a command input in INTERACTIVE stage."""
        if self.stage != Stage.INTERACTIVE:
            raise RuntimeError(
                "Cannot process commands when not in INTERACTIVE stage.")

        # Hide input bar and show spinner
        path_container = self.query_one(".path-container", Horizontal)
        path_container.add_class("hidden")
        self.input_spinner.remove_class("hidden")

        # Mount log console inside scancode tab if not already mounted
        if self.log_view is None:
            await self._mount_scancode_log_console()

        # Clear previous log content
        self.log_view.clear()
        self.log_view.write_line(f"⚙️ Executing command: {command}")

        self.log_view.focus()
        self.refresh()

        # Execute command (already async, no need for executor)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.controller.execute_command, command)

        # Give time for logs to be processed from the queue

        # Hide spinner and show input bar again
        self.input_spinner.add_class("hidden")
        path_container.remove_class("hidden")

        if self.log_view:
            self.log_view.write_line(
                "\n✅ Command execution complete!")

        # Clear input
        input_widget = self.query_one("#path", Input)
        input_widget.value = ""
        input_widget.focus()

    async def _start_analysis(self, requirements_path: str) -> None:
        """Common logic to start the analysis for a package string."""
        input_widget = self.query_one("#path", Input)

        if not requirements_path or not Controller.path_check(requirements_path) or self.stage != Stage.ANALYZING:
            # show error state
            # In realtà dovrebbe essere impossibile arrivarci metti un RISE
            input_widget.value = ""
            self._set_input_error(True)
            return

        # clear any previous error state
        self._set_input_error(False)
        # Hide input bar and mount log widget
        path_container = self.query_one(".path-container", Horizontal)
        path_container.add_class("hidden")

        if self.log_view is None:
            await self._mount_log_console(path_container)

        # Mostra spinner
        self.spinner.remove_class("hidden")
        self.refresh()
        path_obj = Path(requirements_path)

        # Esegui il backend in un thread separato
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.controller.start_analysis, path_obj)

        # Nascondi spinner
        self.spinner.add_class("hidden")

        if self.log_view:
            self.log_view.write_line(ANALYSIS_COMPLETE)
        self.refresh()
        # Aggiorna il Tree nella GUI
        # root, graph = self.controller.get_graph()
        # self.update_dependency_tree(root, graph)

# =================================================================================#
#                                   View Updaters                                  #
# =================================================================================#

    def _set_input_error(self, show_error: bool) -> None:
        """Set or clear the input widget error state.

        Args:
            show_error: True to show error, False to clear it.
        """
        path_input = self.query_one("#path", Input)
        path_container = self.query_one(".path-container", Horizontal)

        # Prepare placeholders according to the actual stage
        self._path_input_has_error = show_error
        match self.stage:
            case Stage.REQUIREMENTS:
                error = ERROR_PATH_PLACEHOLDER
                info = PATH_PLACEHOLDER
            case Stage.LICENSE:
                error = ERROR_LICENSE_PLACEHOLDER
                info = LICENSE_PLACEHOLDER
            case Stage.INTERACTIVE | Stage.ANALYZING:
                # Will prepare the same input widget for the scan session
                error = ERROR_COMMANDS_PLACEHOLDER
                info = COMMANDS_PLACEHOLDER if self.suggestions_list else ""
        # Update input widget state
        if show_error:
            path_input.value = ""
            path_input.placeholder = error
            path_input.add_class("path-input-error")
            if path_container:
                path_container.add_class("path-container-error")
        else:
            path_input.placeholder = info
            path_input.remove_class("path-input-error")
            if path_container:
                path_container.remove_class("path-container-error")

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

    async def _mount_log_console(self, before_widget) -> None:
        """Create and mount the log console widget."""
        self.log_view = Log(classes="log-console")
        self.log_view.border_title = "Console log"
        # self.log_view.styles.scrollbar_background = "#1e1e1e"
        # self.log_view.styles.scrollbar_corner_color = "#1e1e1e"
        # self.log_view.styles.scrollbar_color = "#cc8a36"
        # self.log_view.styles.scrollbar_color_hover = "#d69a46"
        await self.mount(self.log_view, before=before_widget)
        self.log_view.write_line(ANALYSIS_STARTING)

    async def _unmount_log_console(self) -> None:
        if self.log_view is None:
            return
        try:
            await self.log_view.remove()
        except Exception:
            self.log_view.remove()  # fallback if sync

        self.log_view = None
        return

    async def _mount_scancode_log_console(self) -> None:
        """Create and mount the log console widget inside the scancode tab."""
        scancode_block = self.query_one(".scancode-block", Vertical)
        tabbed_content = scancode_block.query_one(TabbedContent)
        # Create log widget (reuse log_view)
        self.log_view = Log(classes="scancode-log", id="scancode-log")
        # self.log_view.border_title = "Scan Console"
        # Mount inside a new TabPane
        tabbed_content.add_pane(TabPane("Console", self.log_view))


# =================================================================================#
#                         Suggestions System                                       #
# =================================================================================#

    async def _mount_input_bar(self) -> None:
        """Create and mount the input bar for commands."""
        path_container = self.query_one(".path-container", Horizontal)
        # Show input bar again
        if path_container:
            path_container.remove_class("hidden")

        # Set flag to prevent Input.Changed from triggering during setup
        self._setting_up_suggestions = True

        # Mount suggestions FIRST, before modifying input
        # (changing input value triggers Input.Changed event)
        await self._mount_suggestions()  # _ensure_suggestions to mount suggestions

    async def _mount_suggestions(self) -> None:
        """Create and mount the suggestions ListView as an overlay."""
        if self.suggestions_list is not None:
            return

        suggestions_widget = ListView(
            id="suggestions", classes="suggestions-overlay hidden")
        # Mount in the input section container, after the input
        input_section = self.query_one("#input-section", Vertical)
        await input_section.mount(suggestions_widget)

        # Set the reference AFTER mount is complete
        self.suggestions_list = suggestions_widget
        self.filtered_suggestions = []

    async def _update_suggestions(self, search_term: str) -> None:
        """Update the suggestions list based on the search term."""
        if self.suggestions_list is None:
            return

        search_lower = search_term.lower().strip()
        # Metti il loading nell'input per le licenze
        pool = self._suggestions_pool_for_stage()
        # Termina il loading
        if not pool:
            self.suggestions_list.add_class("hidden")
            return

        # Hide suggestions if input is empty
        if not search_lower:
            self.suggestions_list.add_class("hidden")
            return
        # è una lista di stringhe
        self.filtered_suggestions = [
            item for item in pool if search_lower in item.lower()
        ]

        # Clear and repopulate the list
        self.suggestions_list.clear()
        self._suggestion_data.clear()
        for item_value in self.filtered_suggestions:
            item = ListItem(Static(item_value), classes="suggestion-item")
            # store value for click/enter selection
            self._suggestion_data[id(item)] = item_value
            self.suggestions_list.append(item)

        # Show suggestions if there are any filtered commands
        if self.filtered_suggestions:
            self.suggestions_list.remove_class("hidden")
        else:
            self.suggestions_list.add_class("hidden")

        self.suggestions_list.refresh(layout=True)

    def _suggestions_pool_for_stage(self) -> list[str]:
        """Return the correct suggestions list depending on the current stage."""
        if self.stage == Stage.LICENSE:
            return Controller.load_license_names()  # le chiede al controller
        if self.stage in (Stage.INTERACTIVE, Stage.ANALYZING):
            return self.controller.get_commands_suggestions()  # le chiede al controller
        return []

    def _apply_suggestion(self, value: str) -> None:
        """Fill the input with the selected suggestion and hide the overlay."""
        if not value:
            return
        input_widget = self.query_one("#path", Input)
        input_widget.value = value
        input_widget.cursor_position = len(value)
        input_widget.focus()
        # clear any previous error state
        self._set_input_error(False)
        if self.suggestions_list:
            self.suggestions_list.add_class("hidden")

    def _highlight_suggestion(self, event) -> None:
        """Highlight the suggestion at the given index."""
        if self.suggestions_list is None:
            return

        # Remove highlight from previous item
        if self._last_highlighted_item is not None:
            self._last_highlighted_item.remove_class("--highlight")
            self._last_highlighted_item = None

        # Apply highlight to newly highlighted item
        item = getattr(event, "item", None)
        if item is not None:
            try:
                item.add_class("--highlight")
                self._last_highlighted_item = item
            except Exception:
                self._last_highlighted_item = None

# ==================================================================================#
#                        License Compatibility Explanations                        #
# ==================================================================================#

    def _update_pypi_table(self, package_name: str) -> None:
        """Update the PyPI metadata table based on the selected package."""

        table = self.query_one("#pypi-info-table", DataTable)
        table.clear()

        if not package_name:
            return
        metadata = self.controller.get_package_metadata(package_name)
        if not metadata:
            return
        package_name = metadata.package or "N/A"
        declared_license = metadata.license_type or "N/A"
        declered_link = metadata.link or "N/A"
        table.add_row(package_name, declared_license, declered_link)

    def _update_incompatibilities_table(self, package_name: str) -> None:
        """Update the license incompatibilities table based on the selected package."""

        table = self.query_one("#incompatibilities-table", DataTable)
        table.clear()

        if not package_name:
            return

        incompatibilities = self.controller.get_incompatibilities(package_name)
        if not incompatibilities:
            return

        for parent, parent_license, child, child_license, compatibility_info in incompatibilities:
            parent_str = f"{parent} ({parent_license})" if parent and parent_license else parent or "N/A"
            child_str = f"{child} ({child_license})" if child and child_license else child or "N/A"
        # compatibility_info is a tuple like ('No', 'explanation message')
            issues_str = compatibility_info[1] if compatibility_info and len(
                compatibility_info) > 1 else "N/A"
            table.add_row(parent_str, child_str, issues_str)


if __name__ == "__main__":
    LicenseSentinelUI().run()


#  C:\Users\Dabaduck\Desktop\LicensesChecker\requirements.txt
