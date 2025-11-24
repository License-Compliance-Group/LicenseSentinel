
import logging
from src.infrastructure.logger_formatter import LoggerFormatter


class TestLoggerFormatterClass():
    """Unit tests for LoggerFormatter class."""
    def test_formatter_builds(self):
        """Ensure default config of LoggerFormatter works."""
        formatter = LoggerFormatter.initialize()
        assert formatter is not None \
            and formatter.getEffectiveLevel() == LoggerFormatter.DEFAULT \
            and formatter.name == LoggerFormatter.DEFAULT_NAME

    def test_formatter_builds_custom_level(self):
        """Ensure passing a custom intended level works."""
        formatter = LoggerFormatter.initialize(__name__, LoggerFormatter.CRITICAL)
        assert formatter.getEffectiveLevel() == LoggerFormatter.CRITICAL

    def test_formatter_builds_wrong_level(self):
        """Ensure a sensible default when incorrect level is passed"""
        formatter = LoggerFormatter.initialize(__name__, "definitely wrong")
        assert formatter.getEffectiveLevel() == LoggerFormatter.DEFAULT

    def test_formatter_builds_wrong_name(self):
        """Ensure a sensible default when incorrect name is passed"""   
        formatter = LoggerFormatter.initialize(None)
        assert formatter.name == LoggerFormatter.DEFAULT_NAME

    def test_format_debug_color(self):
        """Ensure DEBUG logs are formatted with grey color."""
        formatter = LoggerFormatter()
        record = logging.LogRecord("name", logging.DEBUG, "pathname", 1, "msg", (), None)
        formatted = formatter.format(record)
        assert LoggerFormatter.grey in formatted
        assert LoggerFormatter.reset in formatted

    def test_format_error_color(self):
        """Ensure ERROR logs are formatted with red color."""
        formatter = LoggerFormatter()
        record = logging.LogRecord("name", logging.ERROR, "pathname", 1, "msg", (), None)
        formatted = formatter.format(record)
        assert LoggerFormatter.red in formatted
        assert LoggerFormatter.reset in formatted

    def test_logger_has_handler(self):
        """Ensure initialized logger has a handler with LoggerFormatter."""
        logger = LoggerFormatter.initialize("test_logger_handler")
        assert len(logger.handlers) > 0
        handler = logger.handlers[-1]
        assert isinstance(handler, logging.StreamHandler)
        assert isinstance(handler.formatter, LoggerFormatter)
