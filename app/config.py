from pydantic import BaseSettings


class Settings(BaseSettings):
    secret_key: str
    milvus_host: str
    milvus_port: int
    rocketqa_url: str
    database_uri: str

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


settings = Settings()
