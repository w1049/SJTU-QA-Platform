FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9-slim

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirror.sjtu.edu.cn/pypi/web/simple && \
pip install --no-cache-dir --no-dependencies pymilvus==1.1.2 -i https://mirror.sjtu.edu.cn/pypi/web/simple

COPY prestart.sh /app/
COPY ./app /app/app