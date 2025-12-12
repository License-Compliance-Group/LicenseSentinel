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
    THEME = "harlequin"
    CSS_PATH = "style.css"

    def compose(self) -> ComposeResult:
        with Horizontal(classes="urlbar"):
            yield Input(placeholder="Inserisci un package PyPI (es: flask)", id="url", classes="url-input")
            yield Button("Invia", id="send", classes="url-button")

        with Vertical(classes="main-container", id="main-container"):
            with Horizontal(classes="main-row"):

                with Vertical(classes="dependency") as dependency_block:
                    dependency_block.border_title = "Dependency Tree"
                    dependency_block.styles.border_title_align = "right"

                    # Tree dinamico
                    self.dep_tree = Tree("Dipendenze")
                    yield self.dep_tree

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

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send":
            package = self.query_one("#url", Input).value.strip()

            if not package:
                self.log("Nessun package inserito")
                return

            # Mostra spinner
            self.spinner.remove_class("hidden")
            self.refresh()

            # Esegui il backend in un thread separato (compatibile con TUTTE le Textual)
            graph = await asyncio.to_thread(build_dependency_tree_for, package)

            # Nascondi spinner
            self.spinner.add_class("hidden")

            # Aggiorna il Tree nella GUI
            self.update_dependency_tree(package, graph)

    def update_dependency_tree(self, root_pkg: str, graph: dict):
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
