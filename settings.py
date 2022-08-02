class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = True  # 支持追踪修改


class TestConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://admin:123456@192.168.1.19:5432/test"
    JSON_AS_ASCII = False


MILVUS_HOST = "192.168.1.19"
MILVUS_PORT = "19530"
ROCKETQA_URL = "http://127.0.0.1:25565/rocketqa"
