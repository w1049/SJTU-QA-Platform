import os


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = True  # 支持追踪修改

    @staticmethod
    def init_app(app):
        pass


class TestConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://admin:123456@192.168.124.4:5432/test"
    JSON_AS_ASCII = False
    SECRET_KEY = os.getenv('SECRET_KEY', default='l926o8I7')
    JACCOUNT_CLIENT_ID = os.getenv('JACCOUNT_CLIENT_ID')
    JACCOUNT_CLIENT_SECRET = os.getenv('JACCOUNT_CLIENT_SECRET')


MILVUS_HOST = "192.168.124.4"
MILVUS_PORT = "19530"
ROCKETQA_URL = "http://127.0.0.1:25565/rocketqa"

config = {
    'test': TestConfig
}
