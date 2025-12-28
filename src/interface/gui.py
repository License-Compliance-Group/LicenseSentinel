"""The main GUI class of the app.
"""
import asyncio
import logging
import sys
import textwrap
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Input, Button, Static, Tree, DataTable, TabbedContent,
    TabPane, LoadingIndicator, Log, ListView, ListItem
)
from textual import events, on
from interface.controller import Controller
from interface.ui_state import Stage, SuggestionState, CommandResult

ERROR_PATH_PLACEHOLDER = "❌ Invalid path!"
PATH_PLACEHOLDER = "📄 Insert the path to the requirements.txt file"
LICENSE_PLACEHOLDER = "📜 Select the main repository license..."
ERROR_LICENSE_PLACEHOLDER = "❌ Invalid license!"
ANALYSIS_COMPLETE = "\n✅ Analysis complete! Press Enter ↵ to show command line"
ANALYSIS_ERROR = "\n❌ Analysis failed! Press Enter ↵ to exit"
ANALYSIS_STARTING = "⏳ Starting dependency analysis..."
COMMANDS_PLACEHOLDER = "💬 Type a command..."
ERROR_COMMANDS_PLACEHOLDER = "❌ Invalid command!"
DEPENDENCY_TREE_TITLE = "Dependency Tree"


class TextualLogHandler(logging.Handler):
    """Logging handler that writes to a Textual Log widget.

    This handler intercepts log messages and forwards them to the Log widget
    in the UI, ensuring thread-safe communication between background tasks
    and the UI.

    Attributes:
        _app_getter: Callable that returns the application instance.
    """

    def __init__(self, app_getter):
        """Initialize the TextualLogHandler.

        Args:
            app_getter: Callable that returns the LicenseSentinelUI app instance.
        """
        super().__init__()
        self._app_getter = app_getter

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the Textual Log widget.

        Args:
            record: The log record to emit.
        """
        try:
            msg = self.format(record)
        except Exception:  # pylint: disable=broad-exception-caught
            # Logging handler must never crash - catch all formatting errors
            msg = record.getMessage()

        app = self._app_getter()
        if app is None:
            print(f"[DEBUG] App is None, skipping log: {msg}")
            return

        def _write():
            log_widget = getattr(app, "log_view", None)
            if log_widget is None:
                print(f"[DEBUG] log_view is None, skipping: {msg}")
                return
            try:
                log_widget.write_line(msg)
            except Exception as e:  # pylint: disable=broad-exception-caught
                # Widget might be in invalid state - catch all errors
                print(f"[DEBUG] Exception writing to log_view: {e}")

        try:
            app.call_from_thread(_write)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Thread communication might fail in various ways - catch all
            print(f"[DEBUG] Exception in call_from_thread: {e}")


class LicenseSentinelUI(App):
    """Main GUI application for license compatibility analysis.

    A Textual-based TUI application that provides an interactive interface for
    analyzing Python package dependencies and their license compatibility. The
    application guides users through a multi-stage workflow: requirements input,
    license selection, dependency analysis, and interactive exploration.
    """
    # CSS
    CSS_PATH = "style.css"

    # Widget IDs
    ID_PATH_INPUT = "path"
    ID_SEND_BUTTON = "send"
    ID_TREE = "dependency-tree"
    ID_SUGGESTIONS = "suggestions"

    # Table IDs
    ID_PYPI_TABLE = "pypi-info-table"
    ID_INCOMPATIBILITIES_TABLE = "incompatibilities-table"
    ID_SCANCODE_TABLE = "scancode-table"

    def __init__(self):
        """Initialize the LicenseSentinel UI application.
        Sets up the UI components, controller, logging system, and suggestion
        infrastructure. Initializes the application in REQUIREMENTS stage.
        """
        super().__init__()
        self.controller = Controller()

        # Use state objects instead of individual attributes
        self.stage = Stage.REQUIREMENTS
        self.suggestion_state = SuggestionState()

        # UI components
        self.ui_tree = Tree(DEPENDENCY_TREE_TITLE, id=self.ID_TREE)
        self.spinner = LoadingIndicator(id="spinner", classes="hidden")
        self.input_spinner = LoadingIndicator(
            id="input-spinner", classes="hidden")
        self._path_input_has_error = False

        # Log widget for displaying build output
        self.log_view: Log | None = None
        # self._log_handler = None

        self._cleanup_all_loggers()
        self._setup_logging()

    def _pypi_table(self) -> DataTable:
        """Create and configure the PyPI metadata table.
        Returns:
            DataTable: Configured table with columns for package info, license, and source URL.
        """
        table = DataTable(id=self.ID_PYPI_TABLE)
        table.add_columns("Package  ", "Declared License    ", "Source code")

        return table

    def _incompatibilities_table(self) -> DataTable:
        """Create and configure the license incompatibilities table.
        Returns:
            DataTable: Configured table with columns for parent/child packages
            and compatibility explanations.
        """
        table = DataTable(id=self.ID_INCOMPATIBILITIES_TABLE)
        table.add_columns("Package parent",
                          "Package children", "Explanation")

        return table

    def _scancode_table(self) -> DataTable:
        """Create and configure the ScanCode results table.
        Returns:
            DataTable: Configured table with columns for package name, discrepancies, and doubts.
        """
        table = DataTable(id=self.ID_SCANCODE_TABLE)
        table.add_columns("Package Name", "Discrepancies", "Doubts")
        return table

    def compose(self) -> ComposeResult:
        """Compose the application layout and widgets.
        Yields:
            Widgets comprising the complete UI layout including input bar,
            dependency tree, PyPI metadata tables, and ScanCode results.
        """
        with Vertical(id="top-section", classes="top-section"):
            with Horizontal(classes="path-container"):
                with Vertical(id="input-section", classes="input-section"):
                    yield Input(placeholder=PATH_PLACEHOLDER, id=self.ID_PATH_INPUT, classes="path-input")
                yield Button("Next ->", variant="primary", id=self.ID_SEND_BUTTON, classes="analyze-button")
            yield self.input_spinner

        with Vertical(classes="main-container", id="main-container"):
            with Horizontal(classes="main-row"):
                yield from self._compose_dependency_section()
                yield from self._compose_right_column()

    def _compose_dependency_section(self) -> ComposeResult:
        """Compose the dependency tree section.
        Yields:
            Vertical container with tree widget and loading spinner.
        """
        with Vertical(classes="dependency") as block:
            block.border_title = "Dependency Tree"
            block.styles.border_title_align = "right"
            yield self.ui_tree
            yield self.spinner

    def _compose_right_column(self) -> ComposeResult:
        """Compose the right column with PyPI and ScanCode sections.
        Yields:
            Vertical container with PyPI metadata and ScanCode result sections.
        """
        with Vertical(classes="right-column"):
            yield from self._compose_pypi_section()
            yield from self._compose_scancode_section()

    def _compose_pypi_section(self) -> ComposeResult:
        """Compose the PyPI metadata section with tabbed content.
        Yields:
            Vertical container with tabs for package info and incompatibilities.
        """
        with Vertical(classes="section-box pypi-block") as block:
            block.border_title = "PyPI Metadata"
            block.styles.border_title_align = "right"
            with TabbedContent():
                with TabPane("Info"):
                    yield self._pypi_table()
                with TabPane("Incompatibilities"):
                    yield self._incompatibilities_table()

    def _compose_scancode_section(self) -> ComposeResult:
        """Compose the ScanCode results section with tabbed content.
        Yields:
            Vertical container with tab for scan results.
        """
        with Vertical(classes="section-box scancode-block") as block:
            block.border_title = "ScanCode Results"
            block.styles.border_title_align = "right"
            with TabbedContent():
                yield TabPane("Scan results", self._scancode_table())
                # yield TabPane("Dettagli", Static("Dettagli analisi ScanCode..."))

# =================================================================================#
#                                 Event Handlers                                   #
# =================================================================================#

    @on(Button.Pressed, f"#{ID_SEND_BUTTON}")
    async def handle_check_button(self, event: Button.Pressed) -> None:
        """Handle the send/analyze/execute button press.

        Delegates to process_stage_input with the current input value.

        Args:
            event: Button press event from the send button.
        """
        if event.button.id == self.ID_SEND_BUTTON:
            input_widget = self.query_one(f"#{self.ID_PATH_INPUT}", Input)
            await self.process_stage_input(input_widget.value.strip())

    @on(Input.Submitted, f"#{ID_PATH_INPUT}")
    async def on_path_submitted(self) -> None:
        """Handle Enter key press in the input field.

        Delegates to process_stage_input with the current input value.
        """
        input_widget = self.query_one(f"#{self.ID_PATH_INPUT}", Input)
        await self.process_stage_input(input_widget.value.strip())

    @on(Input.Changed, f"#{ID_PATH_INPUT}")
    async def on_path_input_changed(self, event: Input.Changed) -> None:
        """Handle input text changes.

        Clears error state when user types and updates suggestion list
        when in LICENSE or INTERACTIVE stages.

        Args:
            event: Input change event containing the new value.
        """
        if event.input.value.strip() and self._path_input_has_error:
            self._set_input_error(False)

        # Update suggestions when in LICENSE or INTERACTIVE stage (but not during setup)
        if (self.stage in (Stage.LICENSE, Stage.INTERACTIVE) and
            self.suggestion_state.suggestions_list is not None and
                not self.suggestion_state.setting_up):
            await self._update_suggestions(event.input.value)

    async def on_mouse_down(self, event: events.MouseDown) -> None:
        """Handle mouse click events to clear input errors.

        Clears the input error state when user clicks outside the input
        container while an error is displayed.

        Args:
            event: Mouse down event containing widget and position information.
        """
        if not self._path_input_has_error:
            return
        path_input = self.query_one(f"#{self.ID_PATH_INPUT}", Input)
        path_container = self.query_one(".path-container", Horizontal)
        # If click landed on the input or on its container, don't clear yet
        if event.widget is path_input or event.widget is path_container:
            return
        # otherwise clear the error state
        self._set_input_error(False)

    @on(ListView.Selected, f"#{ID_SUGGESTIONS}")
    async def on_suggestion_selected(self, event: ListView.Selected) -> None:
        """Handle suggestion selection from the dropdown list.

        Fills the input field with the selected suggestion value.

        Args:
            event: ListView selection event containing the selected item.
        """
        value = self.suggestion_state.suggestion_data.get(id(event.item))
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
        """Handle tree node selection or highlighting.

        Updates PyPI metadata and incompatibilities tables for the selected package.

        Args:
            event: Tree node selection/highlight event.
        """
        node = getattr(event, "node", None)
        label = getattr(node, "label", None)
        label_str = str(label)  # if label is not None else ""

        # Skip if no node provided or if it's the root node
        if node is None or label_str == DEPENDENCY_TREE_TITLE:
            return

        self._update_pypi_table(label_str)
        self._update_incompatibilities_table(label_str)

    @on(ListView.Highlighted, f"#{ID_SUGGESTIONS}")
    async def on_suggestion_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle suggestion highlight changes for keyboard navigation.

        Applies CSS highlight class to match mouse hover styling during
        keyboard navigation.

        Args:
            event: ListView highlight event containing the highlighted item.
        """

        if self.suggestion_state.suggestions_list is None:
            return
        # Remove highlight from previous item
        if self.suggestion_state.last_highlighted_item is not None:
            self.suggestion_state.last_highlighted_item.remove_class(
                "--highlight")  # was a try
            self.suggestion_state.last_highlighted_item = None
        # Apply highlight to newly highlighted item
        item = getattr(event, "item", None)
        if item is not None:
            try:
                item.add_class("--highlight")
                self.suggestion_state.last_highlighted_item = item
            except (AttributeError, RuntimeError):
                # Widget might not support CSS classes or be in invalid state
                self.suggestion_state.last_highlighted_item = None

    @on(events.Key)
    async def handle_suggestions_keypress(self, event: events.Key) -> None:
        """Handle keyboard navigation for the suggestions dropdown.

        Manages focus transitions between input field and suggestions list
        for arrow key navigation.

        Args:
            event: Key press event.
        """
        # Only handle keys when suggestions overlay is visible
        if (self.suggestion_state.suggestions_list is None or
                self.suggestion_state.suggestions_list.has_class("hidden")):
            return

        # Handle DOWN key from input to move focus to suggestions
        key = event.key.lower()
        if key in ("down", "arrow_down"):
            input_widget = self.query_one(f"#{self.ID_PATH_INPUT}", Input)
            if input_widget.has_focus:
                self.suggestion_state.suggestions_list.focus()
                if hasattr(self.suggestion_state.suggestions_list, "index"):
                    self.suggestion_state.suggestions_list.index = 0
                    if self.suggestion_state.last_highlighted_item is not None:
                        self.suggestion_state.last_highlighted_item.add_class(
                            "--highlight")

            return
        # If first item is highlighted and user presses UP, move focus back to input
        if key in ("up", "arrow_up"):
            suggestion_widget = self.query_one(
                f"#{self.ID_SUGGESTIONS}", ListView)
            if suggestion_widget.has_focus and self.suggestion_state.suggestions_list.index == 0:
                # Remove highlight from current (first) item
                if self.suggestion_state.last_highlighted_item is not None:
                    self.suggestion_state.last_highlighted_item.remove_class(
                        "--highlight")
                    input_widget = self.query_one(
                        f"#{self.ID_PATH_INPUT}", Input)
                    input_widget.focus()
        return

    @on(events.Key)
    async def console_enter_key(self, event: events.Key) -> None:
        """Handle Enter key during ANALYZING stage.
        Transitions from analysis log view to interactive command mode.
        Args:
            event: Key press event.
        """
        # Only act on Enter and when the log console is mounted/visible
        if (event.key.lower() != "enter") or (self.stage not in (Stage.ANALYZING, Stage.ERROR)) or not self.log_view:  # pylint: disable=line-too-long
            return
        await self.process_stage_input("")

# =================================================================================#
#                                   State Handling                                 #
# =================================================================================#

    def _validate_stage_input(self, input_value: str) -> bool:
        """Validate input based on current stage.

        Returns:
            bool: True if input is valid for the current stage, False otherwise.
        """
        match self.stage:
            case Stage.REQUIREMENTS:
                return Controller.path_check(input_value)
            case Stage.LICENSE:
                return Controller.license_check(input_value)
            case Stage.ANALYZING:
                return True  # no input expected during analysis
            case Stage.ERROR:
                return True  # any input accepted to exit
            case Stage.INTERACTIVE:
                return self.controller.is_valid_command(input_value)
            case _:
                raise RuntimeError(
                    f"Invalid stage for input validation: {self.stage}")

    async def process_stage_input(self, input_value: str) -> None:
        """Process user input based on current workflow stage.

        Implements stage-based workflow logic:
        - REQUIREMENTS: Validates and stores requirements.txt path, advances to LICENSE stage
        - LICENSE: Validates license selection and initiates analysis
        - ANALYZING: Transitions to INTERACTIVE stage after analysis completion
        - INTERACTIVE: Validates and executes user commands

        Args:
            input_value: User input string from the path/command input field.

        Raises:
            ValueError: If an unknown stage is encountered.
        """

        result = self._validate_stage_input(input_value)
        if self.stage != Stage.ERROR:
            self._set_input_error(not result)
        if not result:
            return
        match self.stage:
            case Stage.REQUIREMENTS:
                self.controller.requirements_path = input_value
                await self._transition_to_license_stage()
            case Stage.LICENSE:
                self.controller.main_license = input_value
                await self._transition_to_analyzing_stage(self.controller.requirements_path)
            case Stage.ANALYZING:
                await self._transition_to_interactive_stage()
            case Stage.ERROR:
                print("Exiting application due to previous error.")
                sys.exit(1)
            case Stage.INTERACTIVE:
                await self._process_command_input(input_value)
            case _:
                raise ValueError(f"Unknown stage: {self.stage}")

    async def _transition_to_license_stage(self) -> None:
        """Configure UI for LICENSE selection stage."""
        logging.disable(logging.CRITICAL)  # Disable logging during rendering

        # Show spinner while loading license database
        path_container = self.query_one(".path-container", Horizontal)
        path_container.add_class("hidden")
        self.input_spinner.remove_class("hidden")

        # Load license names in background thread (blocking I/O operation)
        await asyncio.to_thread(Controller.load_license_names)

        # Mount suggestions system
        await self._mount_suggestions()

        # Hide spinner and re-enable input
        self.input_spinner.add_class("hidden")
        path_container.remove_class("hidden")
        input_widget = self.query_one(f"#{self.ID_PATH_INPUT}", Input)
        input_widget.placeholder = LICENSE_PLACEHOLDER
        input_widget.value = ""
        self.query_one(f"#{self.ID_SEND_BUTTON}", Button).label = "Analyze 📊"
        self.stage = Stage.LICENSE

    async def _transition_to_analyzing_stage(self, requirements_path: str) -> None:
        """Configure UI and start analysis for ANALYZING stage."""
        logging.disable(logging.NOTSET)  # Re-enable logging for analysis
        self.stage = Stage.ANALYZING
        result = await self._start_analysis(requirements_path)
        if not result:
            self.stage = Stage.ERROR

    async def _transition_to_interactive_stage(self) -> None:
        """Configure UI for INTERACTIVE stage after analysis completion."""
        root, graph = self.controller.get_graph()
        if root is None or graph is None:
            raise RuntimeError(
                "Analysis did not produce a valid dependency graph.\n"
                "Ensure that requirements.txt is correct")

        self.update_dependency_tree(root, graph)
        self._highlight_tree_incompatible_nodes()
        await self._unmount_log_console()
        await self._mount_input_bar()

        self.suggestion_state.setting_up = False
        input_widget = self.query_one(f"#{self.ID_PATH_INPUT}", Input)
        input_widget.placeholder = COMMANDS_PLACEHOLDER
        input_widget.value = ""
        self.query_one(f"#{self.ID_SEND_BUTTON}", Button).label = "Execute ▶"
        self.stage = Stage.INTERACTIVE

# =================================================================================#
#                                   Helpers                                        #
# =================================================================================#

    async def _process_command_input(self, command: str) -> None:
        """Execute a user command in INTERACTIVE stage.\n
        Hides input bar, displays spinner, executes command in background thread,
        and displays output in the ScanCode console tab.
        Args:
            command: User command string to execute.
        Raises:
            RuntimeError: If called when not in INTERACTIVE stage or if log view is not mounted.
        """
        if self.stage != Stage.INTERACTIVE:
            raise RuntimeError(
                "Cannot process commands when not in INTERACTIVE stage.")

        if not self.controller.is_valid_command(command):
            self._set_input_error(True)
            return
        # Hide input bar and show spinner
        path_container = self.query_one(".path-container", Horizontal)
        path_container.add_class("hidden")
        self.input_spinner.remove_class("hidden")

        # Mount log console inside scancode tab if not already mounted
        if self.log_view is None:
            self._mount_scancode_log_console()

        if self.log_view:
            self.log_view.clear()
            self.log_view.write_line(f"⚙️ Executing command: {command}")
            self.log_view.focus()

        # Refresh and yield to event loop to ensure focus takes effect
        self.refresh()

        # Execute command (already async, no need for executor)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self.controller.execute_command, command)
        self._process_command_output(result)
        # Hide spinner and show input bar again
        self.input_spinner.add_class("hidden")
        path_container.remove_class("hidden")

        if self.log_view:
            self.log_view.write_line(
                "\n✅ Command execution complete!")

        # Clear input
        input_widget = self.query_one(f"#{self.ID_PATH_INPUT}", Input)
        input_widget.value = ""
        input_widget.focus()

    def _process_command_output(self, result: CommandResult) -> None:
        """Update UI widgets based on command execution result.

        Dispatches to appropriate view update methods based on result type.

        Args:
            result: CommandResult containing command type and execution data.
        """
        match result.command_type:
            case "scan":
                self._update_scan_results(result)
            case "quit":
                # No UI update needed
                pass
            case _:
                raise ValueError(
                    f"Unknown command type: {result.command_type}")

    async def _start_analysis(self, requirements_path: str) -> bool:
        """Initiate dependency analysis workflow.

        Validates requirements path, mounts log console, executes analysis
        in background thread, and displays progress logs.

        Args:
            requirements_path: Path to requirements.txt file.
        """

        if not Controller.path_check(requirements_path) or self.stage != Stage.ANALYZING:
            raise RuntimeError("Invalid state or requirements path.")

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
        result = await loop.run_in_executor(None, self.controller.start_analysis, path_obj)

        # Nascondi spinner
        self.spinner.add_class("hidden")

        if self.log_view and result:
            self.log_view.write_line(ANALYSIS_COMPLETE)

        if self.log_view and not result:
            self.log_view.write_line(ANALYSIS_ERROR)
        self.refresh()
        return result

    def _cleanup_all_loggers(self) -> None:
        """Remove all handlers from root and child loggers.

        Prevents duplicate log messages by clearing existing handlers before
        setting up the TextualLogHandler.
        """
        # Get root logger
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Also clean up any child loggers that might have been created
        for name in list(logging.Logger.manager.loggerDict.keys()):
            logger = logging.getLogger(name)
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)

    def _setup_logging(self) -> None:
        """Configure logging to display in the UI Log widget.

        Creates and registers a TextualLogHandler that forwards log messages
        to the Log widget in a thread-safe manner.
        """
        # if self._log_handler is not None:
        #    return

        # Get the root logger
        root_logger = logging.getLogger()

        # If a TextualLogHandler for this app is already registered, skip
        for h in list(root_logger.handlers):
            if isinstance(h, TextualLogHandler):
                app_getter = getattr(h, "_app_getter", None)
                if callable(app_getter) and app_getter() is self:
                    return

        # Add TextualLogHandler
        handler = TextualLogHandler(lambda: self)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s [%(name)s]: %(message)s', datefmt='%H:%M:%S'))
        handler.setLevel(logging.INFO)
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
        # self._log_handler = handler

# =================================================================================#
#                                   View Updaters                                  #
# =================================================================================#

    def _set_input_error(self, show_error: bool) -> None:
        """Toggle input error state with appropriate styling and placeholder.

        Updates input field placeholder and applies error styling based on
        current stage and error state.

        Args:
            show_error: True to display error state, False to clear it.
        """
        path_input = self.query_one(f"#{self.ID_PATH_INPUT}", Input)
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
                info = COMMANDS_PLACEHOLDER
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
        """Populate the tree widget with dependency hierarchy.

        Recursively builds the tree structure from the dependency graph,
        starting with the root package.

        Args:
            root_pkg: Root package name with optional license information.
            graph: Dependency graph mapping packages to their dependencies.
        """
        root = self.ui_tree.root
        root.set_label(root_pkg)
        root.remove_children()

        def add_nodes(parent, pkg):
            for dep in graph.get(pkg, []):
                add_nodes(parent.add(dep), dep)

        add_nodes(root, root_pkg)
        root.expand_all()
        self.ui_tree.refresh(layout=True)

    def _highlight_tree_incompatible_nodes(self) -> None:
        """Highlight all packages with license incompatibilities in the tree.

        Applies yellow styling to tree nodes representing packages with
        detected license conflicts.
        """
        if self.controller.incompatible_edges is None:
            return
        for incompatible in self.controller.incompatible_edges:
            self._find_and_highlight_node(incompatible[0], self.ui_tree.root)
        self.refresh()

    def _find_and_highlight_node(self, node_label: str, node) -> bool:
        """Recursively find and highlight a tree node with yellow styling.

        Args:
            node_label: The label to search for (case-insensitive, package name only).
            node: The current node being examined.

        Returns:
            True if node was found and highlighted, False otherwise.
        """
        # Get label as plain text
        if isinstance(node.label, Text):
            current_label = node.label.plain
        else:
            current_label = str(node.label)

        # Check current node with case-insensitive comparison (remove license part)
        if current_label.lower().split(" ")[0] == node_label.lower():
            # Use Rich Text object with yellow
            styled_label = Text(current_label, style="yellow")
            node.set_label(styled_label)
            return True

        # Recursively search in all children (entire tree, not just direct children)
        for child in node.children:
            if self._find_and_highlight_node(node_label, child):
                return True
        return False

    async def _mount_log_console(self, before_widget) -> None:
        """Create and mount the analysis log console.

        Args:
            before_widget: Widget to mount the log console before.
        """
        self.log_view = Log(classes="log-console")
        self.log_view.border_title = "Console log"
        await self.mount(self.log_view, before=before_widget)
        self.log_view.write_line(ANALYSIS_STARTING)

    async def _unmount_log_console(self) -> None:
        """Remove the log console widget from the UI.

        Attempts async removal first, falls back to sync if needed.
        """
        if self.log_view is None:
            return
        try:
            await self.log_view.remove()
        except (RuntimeError, AttributeError):
            # Fallback to sync removal if async fails
            self.log_view.remove()

        self.log_view = None
        return

    def _mount_scancode_log_console(self) -> None:
        """Adds a new Console tab to the ScanCode section for displaying
        command execution output.
        """
        scancode_block = self.query_one(".scancode-block", Vertical)
        tabbed_content = scancode_block.query_one(TabbedContent)
        # Create log widget (reuse log_view)
        self.log_view = Log(classes="scancode-log", id="scancode-log")
        # Mount inside a new TabPane with explicit ID and activate it
        console_pane = TabPane("Console", self.log_view, id="console-tab")
        tabbed_content.add_pane(console_pane)
        # Switch to the newly added Console tab
        tabbed_content.active = "console-tab"


# =================================================================================#
#                         Suggestions System                                       #
# =================================================================================#

    async def _mount_input_bar(self) -> None:
        """Display input bar and initialize suggestion system.

        Shows the input container and mounts the suggestions overlay
        for command autocomplete.
        """
        path_container = self.query_one(".path-container", Horizontal)
        # Show input bar again
        if path_container:
            path_container.remove_class("hidden")

        # Set flag to prevent Input.Changed from triggering during setup
        self.suggestion_state.setting_up = True

        # Mount suggestions FIRST, before modifying input
        # (changing input value triggers Input.Changed event)
        await self._mount_suggestions()  # _ensure_suggestions to mount suggestions

    async def _mount_suggestions(self) -> None:
        """Create and mount autocomplete suggestions dropdown.

        Initializes the ListView widget that displays filtered suggestions
        below the input field.
        """
        if self.suggestion_state.suggestions_list is not None:
            return

        suggestions_widget = ListView(
            id=self.ID_SUGGESTIONS, classes="suggestions-overlay hidden")
        # Mount in the input section container, after the input
        input_section = self.query_one("#input-section", Vertical)
        await input_section.mount(suggestions_widget)

        # Set the reference AFTER mount is complete
        self.suggestion_state.suggestions_list = suggestions_widget
        self.suggestion_state.filtered_suggestions = []

    async def _update_suggestions(self, search_term: str) -> None:
        """Filter and display suggestions matching the search term.

        Performs case-insensitive filtering of available suggestions and
        updates the dropdown list visibility.

        Args:
            search_term: User input to filter suggestions against.
        """
        if self.suggestion_state.suggestions_list is None:
            return

        search_lower = search_term.lower().strip()
        # Metti il loading nell'input per le licenze

        pool = self._suggestions_pool_for_stage()

        # Termina il loading
        if not pool:
            self.suggestion_state.suggestions_list.add_class("hidden")
            return

        # Hide suggestions if input is empty
        if not search_lower:
            self.suggestion_state.suggestions_list.add_class("hidden")
            return
        # è una lista di stringhe
        self.suggestion_state.filtered_suggestions = [
            item for item in pool if search_lower in item.lower()
        ]

        # Clear and repopulate the list
        self.suggestion_state.suggestions_list.clear()
        self.suggestion_state.suggestion_data.clear()
        for item_value in self.suggestion_state.filtered_suggestions:
            item = ListItem(Static(item_value), classes="suggestion-item")
            # store value for click/enter selection
            self.suggestion_state.suggestion_data[id(item)] = item_value
            self.suggestion_state.suggestions_list.append(item)
        # Show suggestions if there are any filtered commands
        if self.suggestion_state.filtered_suggestions:
            self.suggestion_state.suggestions_list.remove_class("hidden")
        else:
            self.suggestion_state.suggestions_list.add_class("hidden")

        self.suggestion_state.suggestions_list.refresh(layout=True)

    def _suggestions_pool_for_stage(self) -> list[str]:
        """Get stage-appropriate suggestion pool.

        Returns:
            List of suggestion strings (license names for LICENSE stage,
            commands for INTERACTIVE stage, empty for other stages).
        """
        if self.stage == Stage.LICENSE:
            # le chiede al controller #BUG:
            return Controller.load_license_names()
        if self.stage in (Stage.INTERACTIVE, Stage.ANALYZING):
            return self.controller.get_commands_suggestions()  # le chiede al controller
        return []

    def _apply_suggestion(self, value: str) -> None:
        """Apply selected suggestion to input field.

        Populates input with suggestion value, positions cursor at end,
        and hides the suggestion dropdown.

        Args:
            value: Suggestion text to insert into input field.
        """
        if not value:
            return
        input_widget = self.query_one(f"#{self.ID_PATH_INPUT}", Input)
        input_widget.value = value
        input_widget.cursor_position = len(value)
        input_widget.focus()
        # clear any previous error state
        self._set_input_error(False)
        if self.suggestion_state.suggestions_list:
            self.suggestion_state.suggestions_list.add_class("hidden")

    def _highlight_suggestion(self, event) -> None:
        """Apply visual highlight to suggestion item.

        Removes highlight from previous item and applies it to the newly
        highlighted item.

        Args:
            event: Event containing the item to highlight.
        """
        if self.suggestion_state.suggestions_list is None:
            return

        # Remove highlight from previous item
        if self.suggestion_state.last_highlighted_item is not None:
            self.suggestion_state.last_highlighted_item.remove_class(
                "--highlight")
            self.suggestion_state.last_highlighted_item = None

        # Apply highlight to newly highlighted item
        item = getattr(event, "item", None)
        if item is not None:
            try:
                item.add_class("--highlight")
                self.suggestion_state.last_highlighted_item = item
            except (AttributeError, RuntimeError):
                # Widget might not support CSS classes or be in invalid state
                self.suggestion_state.last_highlighted_item = None

# ==================================================================================#
#                        License Compatibility Explanations                         #
# ==================================================================================#

    def _update_pypi_table(self, package_name: str | None) -> None:
        """Populate PyPI info table for selected package.

        Clears existing table data and adds row with package metadata
        (name, declared license, source URL).

        Args:
            package_name: Name of package to display metadata for.
        """

        table = self.query_one(f"#{self.ID_PYPI_TABLE}", DataTable)
        table.clear()
        print(package_name, "selected")
        if not package_name:  # is None or package_name == "Dependencies":
            return
        metadata = self.controller.get_package_metadata(package_name)
        if not metadata:
            return
        package_name = metadata.package or "N/A"
        declared_license = metadata.license_type or "N/A"
        declered_link = metadata.link or "N/A"
        table.add_row(package_name, declared_license, declered_link)

    def _update_incompatibilities_table(self, package_name: str) -> None:
        """Populate incompatibilities table for selected package.

        Displays parent-child package relationships with license compatibility
        verdicts and explanations. Highlights incompatible packages in the tree.

        Args:
            package_name: Name of package to check for incompatibilities.
        """
        table = self.query_one(
            f"#{self.ID_INCOMPATIBILITIES_TABLE}", DataTable)
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
            verdict = (
                compatibility_info[0] if compatibility_info else "Unknown") or "Unknown"
            explanation = (compatibility_info[1] if compatibility_info and len(
                compatibility_info) > 1 else "N/A")

            # Build a styled cell with a label and wrapped text
            badge_color = "green" if verdict.lower().startswith("yes") else "red"
            cell = Text()
            cell.append("Compatibility: ", style="bold ")
            cell.append(f"[{verdict}]\n", style=f"bold {badge_color}")
            cell.append("\n".join(textwrap.wrap(explanation, width=60)))
            # Use height=None to auto-size for multi-line content
            table.add_row(parent_str, child_str, cell, height=None)

    def _update_scan_results(self, result: CommandResult) -> None:
        """Render scan results in the UI after executing a scan command.

        Displays scan results in the ScanCode table. For 'all' scans, shows
        all packages with their discrepancies and doubts. For single package
        scans, shows only that package's results.

        Args:
            result: CommandResult containing scan results data.
        """
        if not result or not result.success or result.command_type != "scan":
            return

        table = self.query_one(f"#{self.ID_SCANCODE_TABLE}", DataTable)
        table.clear()

        # Get data from result
        if not result.data:
            return

        package_name = result.data.get("package_name", "")
        discrepancies = result.data.get("discrepancies", [])
        doubts = result.data.get("doubts", [])
        print("discrepancies:"+str(discrepancies))
        print("doubts:"+str(doubts))
        # (' packaging' , 'apache—2.O' ,' , 'apache—2. ' ))
        if package_name.lower() == "all":
            # Display all packages with their discrepancies and doubts
            # discrepancies and doubts are lists of package names
            all_packages = set(discrepancies) | set(doubts)

            if all_packages:
                for pkg in sorted(all_packages):
                    # Check if package has discrepancies or doubts
                    has_discrepancy = "Yes" if pkg in discrepancies else "No"
                    has_doubt = "Yes" if pkg in doubts else "No"

                    table.add_row(pkg, has_discrepancy, has_doubt, height=None)
            else:
                # No packages with issues
                table.add_row(
                    "All Packages",
                    "No discrepancies",
                    "No doubts"
                )
        else:
            # Display single package results

            has_discrepancy = "Yes" if package_name in discrepancies else "No discrepancies found"
            has_doubt = "Yes" if package_name in doubts else "No doubts found"

            table.add_row(package_name, has_discrepancy,
                          has_doubt, height=None)


if __name__ == "__main__":
    LicenseSentinelUI().run()
#  C:\Users\Dabaduck\Desktop\LicensesChecker\requirements.txt
