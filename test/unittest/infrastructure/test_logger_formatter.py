import logging
import unittest
from src.infrastructure.logger_formatter import LoggerFormatter


class TestLoggerFormatterClass(unittest.TestCase):
    """Unit tests for LoggerFormatter class."""

    def test_formatter_builds(self):
        """Ensure default config of LoggerFormatter works."""
        formatter = LoggerFormatter.initialize(__name__)
        self.assertIsNotNone(formatter)
        self.assertEqual(formatter.getEffectiveLevel(), LoggerFormatter.DEFAULT)

    def test_formatter_builds_custom_level(self):
        """Ensure passing a custom intended level works."""
        formatter = LoggerFormatter.initialize(__name__, LoggerFormatter.CRITICAL)
        self.assertEqual(formatter.getEffectiveLevel(), LoggerFormatter.CRITICAL)

    def test_formatter_not_builds_wrong_level(self):
        """Ensure a logger is not initialized when incorrect level is passed"""
        with self.assertRaises(ValueError):
            LoggerFormatter.initialize(__name__, "definitely wrong")

    def test_formatter_not_builds_wrong_name(self):
        """Ensure a logger is not initialized when incorrect name is passed"""
        with self.assertRaises(ValueError):
            LoggerFormatter.initialize(None)

    def test_format_debug_color(self):
        """Ensure DEBUG logs are formatted with grey color."""
        formatter = LoggerFormatter()
        record = logging.LogRecord("name", logging.DEBUG, "pathname",
                                   1, "msg", (), None)
        formatted = formatter.format(record)
        self.assertIn(LoggerFormatter.grey, formatted)
        self.assertIn(LoggerFormatter.reset, formatted)

    def test_format_error_color(self):
        """Ensure ERROR logs are formatted with red color."""
        formatter = LoggerFormatter()
        record = logging.LogRecord("name", logging.ERROR, "pathname",
                                   1, "msg", (), None)
        formatted = formatter.format(record)
        self.assertIn(LoggerFormatter.red, formatted)
        self.assertIn(LoggerFormatter.reset, formatted)

    def test_logger_has_handler(self):
        """Ensure initialized logger has a handler with LoggerFormatter."""
        logger = LoggerFormatter.initialize("test_logger_handler")
        self.assertGreater(len(logger.handlers), 0)
        handler = logger.handlers[-1]
        self.assertIsInstance(handler, logging.StreamHandler)
        self.assertIsInstance(handler.formatter, LoggerFormatter)

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
        self.assertEqual(logger.getEffectiveLevel(), LoggerFormatter.CRITICAL)
