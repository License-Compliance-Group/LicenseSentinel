import logging
import pytest
from src.license_hierarchy.infrastructure.logger_formatter import LoggerFormatter


class TestLoggerFormatterClass:
    """Unit tests for LoggerFormatter class."""

    def test_formatter_builds(self):
        """Ensure default config of LoggerFormatter works."""
        formatter = LoggerFormatter.initialize(__name__)
        assert formatter is not None
        assert formatter.getEffectiveLevel() == LoggerFormatter.DEFAULT

    def test_formatter_builds_custom_level(self):
        """Ensure passing a custom intended level works."""
        formatter = LoggerFormatter.initialize(__name__, LoggerFormatter.CRITICAL)
        assert formatter.getEffectiveLevel() == LoggerFormatter.CRITICAL


def test_formatter_not_builds_wrong_level():
    """Ensure a logger is not initialized when incorrect level is passed"""
    with pytest.raises(ValueError):
        LoggerFormatter.initialize(__name__, "definitely wrong")


def test_formatter_not_builds_wrong_name():
    """Ensure a logger is not initialized when incorrect name is passed"""
    with pytest.raises(ValueError):
        LoggerFormatter.initialize(None)


def test_format_debug_color():
    """Ensure DEBUG logs are formatted with grey color."""
    formatter = LoggerFormatter()
    record = logging.LogRecord("name", logging.DEBUG, "pathname",
                               1, "msg", (), None)
    formatted = formatter.format(record)
    assert LoggerFormatter.grey in formatted
    assert LoggerFormatter.reset in formatted


def test_format_error_color():
    """Ensure ERROR logs are formatted with red color."""
    formatter = LoggerFormatter()
    record = logging.LogRecord("name", logging.ERROR, "pathname",
                               1, "msg", (), None)
    formatted = formatter.format(record)
    assert LoggerFormatter.red in formatted
    assert LoggerFormatter.reset in formatted


def test_logger_has_handler():
    """Ensure initialized logger has a handler with LoggerFormatter."""
    logger = LoggerFormatter.initialize("test_logger_handler")
    assert len(logger.handlers) > 0
    handler = logger.handlers[-1]
    assert isinstance(handler, logging.StreamHandler)
    assert isinstance(handler.formatter, LoggerFormatter)

    def test_logger_survives_multiple_inits(self):
        """Multiple initialize() calls should not affect functionality."""
        logger = LoggerFormatter.initialize("test_logger_handler",
        LoggerFormatter.INFO)
        logger = LoggerFormatter.initialize("test_logger_handler",
        LoggerFormatter.DEBUG)
        logger = LoggerFormatter.initialize("test_logger_handler",
        LoggerFormatter.INFO)
        logger = LoggerFormatter.initialize("test_logger_handler",
        LoggerFormatter.CRITICAL)
        assert logger.getEffectiveLevel() == LoggerFormatter.CRITICAL
