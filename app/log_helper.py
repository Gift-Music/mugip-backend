import logging
import logging.handlers
import sys

from app.settings import AppSettings

LOGGING_FORMAT = (
    "[%(levelname)1.1s "
    "%(asctime)s "
    "P%(process)d "
    "%(threadName)s "
    "%(module)s:%(lineno)d] "
    "%(message)s"
)


def init_logger(root_logger_name: str, app_settings: AppSettings) -> logging.Logger:
    app_logger_level = (
        logging.DEBUG if app_settings.LOGGING_DEBUG_LEVEL else logging.INFO
    )

    app_logger = logging.getLogger(root_logger_name)
    app_logger.setLevel(app_logger_level)

    # STDOUT handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(app_logger_level)
    stdout_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))

    app_logger.info("App logger is started.")

    return app_logger
