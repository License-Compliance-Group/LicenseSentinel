"""State management classes for the GUI."""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
from textual.widgets import ListView, ListItem


class Stage(Enum):
    """Application workflow stages."""
    REQUIREMENTS = auto()
    LICENSE = auto()
    ANALYZING = auto()
    INTERACTIVE = auto()
    ERROR = auto()


@dataclass
class CommandResult:
    """Result Object Pattern implementation for starting a scan command."""
    command_type: str
    success: bool
    message: str = ""
    data: Optional[dict] = None


@dataclass
class SuggestionState:
    """Manages the suggestion overlay state."""
    suggestions_list: ListView | None = None
    setting_up: bool = False
    filtered_suggestions: list[str] = field(default_factory=list)
    suggestion_data: dict[int, str] = field(default_factory=dict)
    suppress_list_move: bool = False
    last_highlighted_item: ListItem | None = None
    # Cached license names loaded in background to avoid blocking the UI
    license_cache: list[str] | None = None

    def clear_data(self) -> None:
        """Clear suggestion data."""
        self.suggestion_data.clear()
        self.filtered_suggestions.clear()
        self.last_highlighted_item = None
