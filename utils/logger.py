import sys
import logging

class Logger:
    def __init__(self, name:str = __name__) -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)

        log_format = logging.Formatter(
            "%(asctime)s:%(name)s:%(levelname)s -> %(message)s"
        )

        stream_handler.setFormatter(log_format)

        self.logger.addHandler(stream_handler)
    
    def info(self, message) -> None:
        self.logger.info(message)
    
    def warn(self, message) -> None:
        self.logger.warning(message)
    
    def error(self, message) -> None:
        self.logger.error(message, exc_info=True)
        sys.exit(1)