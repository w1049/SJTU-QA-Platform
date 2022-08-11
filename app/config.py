import logging
import os
import sys
from datetime import datetime

from loguru import logger
from pydantic import BaseSettings

from .logging import InterceptHandler


class Settings(BaseSettings):
    secret_key: str
    milvus_host: str
    milvus_port: int
    rocketqa_url: str
    database_uri: str
    log_level: str = 'INFO'

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


settings = Settings()


def setup_logging():
    # intercept everything at the root logger
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(settings.log_level)

    # remove every other logger's handlers
    # and propagate to root logger
    for name in [*logging.root.manager.loggerDict.keys()]:
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # configure loguru
    logger.configure(handlers=[{'sink': sys.stdout, 'level': settings.log_level, 'serialize': False}])

    log_path = 'logs'
    if not os.path.exists(log_path):
        os.mkdir(log_path)
    log_file = os.path.join(log_path, f'{datetime.now().strftime("%Y-%m-%d")}_log.log')
    log_error = os.path.join(log_path, f'{datetime.now().strftime("%Y-%m-%d")}_error.log')
    logger.add(log_file, level=settings.log_level,
               rotation='0:00', encoding='utf-8', retention='3 days', enqueue=True, serialize=False)
    logger.add(log_error, level='ERROR',
               rotation='0:00', encoding='utf-8', retention='7 days', enqueue=True, serialize=False)
