from pydantic import BaseSettings


class Settings(BaseSettings):
    secret_key: str
    jaccount_client_id: str
    jaccount_client_secret: str
    milvus_host: str
    milvus_port: int
    rocketqa_url: str
    database_uri: str
    log_level: str = 'INFO'

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


settings = Settings()
