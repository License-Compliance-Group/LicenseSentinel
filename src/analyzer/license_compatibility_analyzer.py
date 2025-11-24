"""Definition of the LicenseCompatibilityAnalyzer class"""

from infrastructure.logger_formatter import LoggerFormatter
logger = LoggerFormatter.initialize(__name__)

class LicenseCompatibilityAnalyzer:
    """Analyzes cross-compatibility of multiple licenses"""

    def __init__(self):
        """Constructor"""
        logger.info("LicenseCompatAnalyzer init")

