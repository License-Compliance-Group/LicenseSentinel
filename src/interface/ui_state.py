"""State management classes for the GUI."""
from dataclasses import dataclass, field
from enum import Enum, auto
from textual.widgets import ListView, ListItem


class Stage(Enum):
    """Application workflow stages."""
    REQUIREMENTS = auto()
    LICENSE = auto()
    ANALYZING = auto()
    INTERACTIVE = auto()


@dataclass
class SuggestionState:
    """Manages the suggestion overlay state."""
    suggestions_list: ListView | None = None
    setting_up: bool = False
    filtered_suggestions: list[str] = field(default_factory=list)
    suggestion_data: dict[int, str] = field(default_factory=dict)
    suppress_list_move: bool = False
    last_highlighted_item: ListItem | None = None

    def clear_data(self) -> None:
        """Clear suggestion data."""
        self.suggestion_data.clear()
        self.filtered_suggestions.clear()
        self.last_highlighted_item = None
