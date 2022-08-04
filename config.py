class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = True  # 支持追踪修改

    @staticmethod
    def init_app(app):
        pass


class TestConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://admin:123456@192.168.124.4:5432/test"
    JSON_AS_ASCII = False
    SECRET_KEY = 'e6a21f29d457273ab0a840adb65c6d98ff1b64655fd1f7d0e02f99f3ba0fa2fb'


MILVUS_HOST = "192.168.124.4"
MILVUS_PORT = "19530"
ROCKETQA_URL = "http://127.0.0.1:25565/rocketqa"

config = {
    'test': TestConfig
}
