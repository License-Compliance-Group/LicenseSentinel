import httpx
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Button, Static, Tree, DataTable, TabbedContent, TabPane


class LicenseSentinelUI(App):
    THEME = "harlequin"
    CSS_PATH = "style.css"

    def compose(self) -> ComposeResult:

        # Barra URL in cima
        with Horizontal(classes="urlbar"):
            yield Input(placeholder="https://api.example.com/endpoint", id="url", classes="url-input")
            yield Button("Invia", id="send", classes="url-button")


        # Container principale sotto la barra URL
        with Vertical(classes="main-container", id="main-container"):

            # Horizontal: Tree a sinistra, colonna destra a destra
            with Horizontal(classes="main-row"):

                # Tree a sinistra
                tree = Tree("Dipendenze")
                root = tree.root
                root.add("requests==2.31.0")
                root.add("numpy==1.26.0")
                root.add("pandas==2.2.0")
                yield tree

                # Colonna destra (Vertical)
                with Vertical(classes="right-column"):

                    # PyPI: occuperà tutto lo spazio disponibile (stessa altezza del Tree)
                    with Vertical(classes="section-box pypi-block"):
                        yield Static("Risultati PyPI", classes="header")
                        with TabbedContent():
                            yield TabPane("Pacchetti", self._pypi_table())
                            yield TabPane("Info", Static("Info pacchetti PyPI..."))

                    # ScanCode: sotto PyPI, altezza minima
                    with Vertical(classes="section-box scancode-block"):
                        yield Static("Risultati ScanCode", classes="header")
                        with TabbedContent():
                            yield TabPane("File", self._scancode_table())
                            yield TabPane("Dettagli", Static("Dettagli analisi ScanCode..."))

    def _pypi_table(self) -> DataTable:
        table = DataTable()
        table.add_columns("Pacchetto", "Licenza dichiarata")
        table.add_row("requests", "Apache-2.0")
        table.add_row("numpy", "BSD")
        table.add_row("pandas", "BSD-3-Clause")
        return table

    def _scancode_table(self) -> DataTable:
        table = DataTable()
        table.add_columns("File", "Licenza rilevata")
        table.add_row("requests/__init__.py", "Apache-2.0")
        table.add_row("numpy/core.py", "BSD")
        table.add_row("pandas/io.py", "BSD-3-Clause")
        return table

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send":
            url = self.query_one("#url", Input).value
            self.log(f"Richiesta a {url}")


if __name__ == "__main__":
    LicenseSentinelUI().run()
