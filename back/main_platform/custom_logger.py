# custom_logger.py

from termcolor import colored
import logging
import os

CUR_LEVEL = logging.CRITICAL


class CustomFormatter(logging.Formatter):
    COLORS = {
        "WARNING": "yellow",
        "INFO": "cyan",
        "DEBUG": "blue",
        "CRITICAL": "red",
        "ERROR": "red",
    }

    def format(self, record):
        log_message = super(CustomFormatter, self).format(record)
        return colored(log_message, self.COLORS.get(record.levelname))


def setup_custom_logger(name, log_directory="logs"):
    # Create log directory if it doesn't exist
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    logger = logging.getLogger(name)
    logger.setLevel(CUR_LEVEL)

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(CUR_LEVEL)

    # File Handler
    fh = logging.FileHandler(os.path.join(log_directory, f"{name}.log"))
    fh.setLevel(CUR_LEVEL)

    formatter = CustomFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger
