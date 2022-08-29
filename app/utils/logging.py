import logging
import os
import sys
from datetime import datetime

from loguru import logger

from app.config import settings


class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging():
    # intercept everything at the root logger
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(settings.log_level)

    # remove every other logger's handlers
    # and propagate to root logger
    for name in ['uvicorn', 'uvicorn.access', 'uvicorn.error']:
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # configure loguru
    logger.configure(handlers=[{'sink': sys.stdout, 'level': settings.log_level,
                                'serialize': False, 'backtrace': False, 'diagnose': False}])

    log_path = 'logs'
    if not os.path.exists(log_path):
        os.mkdir(log_path)
    log_file = os.path.join(log_path, f'{datetime.now().strftime("%Y-%m-%d")}_log.log')
    log_error = os.path.join(log_path, f'{datetime.now().strftime("%Y-%m-%d")}_error.log')
    logger.add(log_file, level=settings.log_level, backtrace=False, diagnose=False,
               rotation='0:00', encoding='utf-8', retention='3 days', enqueue=True, serialize=False)
    logger.add(log_error, level='ERROR',
               rotation='0:00', encoding='utf-8', retention='7 days', enqueue=True, serialize=False)
