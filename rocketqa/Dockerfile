FROM python:slim

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt -i https://mirror.sjtu.edu.cn/pypi/web/simple && \
pip install --no-cache-dir -r /tmp/requirements-1.txt -i https://mirror.sjtu.edu.cn/pypi/web/simple

WORKDIR /rocketqa
COPY . .
CMD ["python", "rocketqa_service.py"]