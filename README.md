# SJTU-QA-Platform
问答平台后端。

前端：[sjtubot](https://gitee.com/zou-likai/sjtubot)

## 部署
`docker-compose.yml`示例
```yaml
version: '3'
services:
    backend:
        build: ./SJTU-QA-Platform
        ports:
            - "80:80"
        environment:
            SECRET_KEY: secret_key
            JACCOUNT_CLIENT_ID: 
            JACCOUNT_CLIENT_SECRET: 
            MILVUS_HOST: milvus
            MILVUS_PORT: 19530
            ROCKETQA_URL: http://rocketqa:25565/rocketqa
            DATABASE_URI: postgresql+psycopg2://admin:123456@db:5432/test
            LOG_LEVEL: INFO
        volumes:
            - ./SJTU-QA-Platform/templates:/app/templates
            - ./SJTU-QA-Platform/logs:/app/logs
        depends_on:
            - rocketqa
            - db
            - milvus
        tty: true
        restart: always
    rocketqa:
        build: ./SJTU-QA-Platform/rocketqa
        volumes:
            - ./rocketqa:/root/.rocketqa
        restart: always
    db:
        image: postgres:13
        volumes:
            - ./pgdata:/var/lib/postgresql/data
        environment:
            POSTGRES_DB: test
            POSTGRES_USER: admin
            POSTGRES_PASSWORD: 123456
        restart: always
    milvus:
        image: milvusdb/milvus:1.1.1-cpu-d061621-330cc6
        volumes:
            - ./milvus/db:/var/lib/milvus/db
            - ./milvus/conf:/var/lib/milvus/conf
            - ./milvus/logs:/var/lib/milvus/logs
            - ./milvus/wal:/var/lib/milvus/wal
        restart: always
```