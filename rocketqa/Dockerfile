FROM python:slim
EXPOSE 25565
WORKDIR /rocketqa

COPY requirements.txt requirements-1.txt ./
RUN sed -i "s|http://deb.debian.org/debian|http://mirror.sjtu.edu.cn/debian|g" /etc/apt/sources.list && \
apt-get update && apt-get install libgomp1 && \
pip install --no-cache-dir -r requirements.txt -i https://mirror.sjtu.edu.cn/pypi/web/simple && \
pip install --no-cache-dir -r requirements-1.txt -i https://mirror.sjtu.edu.cn/pypi/web/simple

COPY rocketqa_service.py .
CMD ["python", "rocketqa_service.py"]