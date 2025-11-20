import logging

class LoggerFormatter(logging.Formatter):

    grey = "\x1b[38;5;7m"
    white = "\x1b[38;15m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: white + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

    @staticmethod
    def initialize(level):
        logger = logging.getLogger("LicenseSentinel")
        logger.setLevel(level)
        ch = logging.StreamHandler()
        ch.setLevel(level) # handle level can be different than logging level
        ch.setFormatter(LoggerFormatter())
        logger.addHandler(ch)