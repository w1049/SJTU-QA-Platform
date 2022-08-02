from flask import make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api
from milvus import Milvus, IndexType, MetricType, Status
from settings import MILVUS_HOST, MILVUS_PORT

db = SQLAlchemy()

api = Api()


# 设置自动使用的序列化器
@api.representation('application/json')
def output_json(data, code, headers=None):
    resp = make_response(jsonify(data), code)
    resp.headers.extend(headers or {})
    return resp


# 暂时用Milvus, 还没测PgVector（postgresql的插件）
class MilvusUtil:
    def __init__(self):
        self.client = Milvus(host=MILVUS_HOST, port=MILVUS_PORT)

    def has_collection(self, name):
        try:
            status, ok = self.client.has_collection(name)
            return ok
        except Exception as e:
            print("Milvus has_table error:", e)

    def create_collection(self, name):
        try:
            param = {
                'collection_name': name,
                'dimension': 768,
                'index_file_size': 256,
                'metric_type': MetricType.IP
            }
            status = self.client.create_collection(param)
            print(status)
            return status
        except Exception as e:
            print("Milvus create collection error:", e)

    def create_index(self, name):
        param = {'nlist': 1000}
        try:
            status = self.client.create_index(name, IndexType.IVF_FLAT,
                                              param)
            print(status)
            return status
        except Exception as e:
            print("Milvus create index error:", e)

    def insert(self, name, vectors, ids=None):
        try:
            # if not self.has_collection(name):
            # self.create_collection(name)
            # self.create_index(name)
            # print('collection info: {}'.format(
            #     self.client.get_collection_info(collection_name)[1]))
            status, ids = self.client.insert(collection_name=name,
                                             records=vectors,
                                             ids=ids)
            self.client.flush([name])
            print(
                'Insert {} entities, there are {} entities after insert data.'.
                format(len(ids),
                       self.client.count_entities(name)[1]))
            return status, ids
        except Exception as e:
            print("Milvus insert error:", e)

    def delete(self, name, ids):
        try:
            status = self.client.delete_entity_by_id(name, ids)
            self.client.flush([name])
            return status
        except Exception as e:
            print('Milvus delete error:', e)

    def search(self, name, vector, top_k):
        param = {'nprobe': 20}
        try:
            status, results = self.client.search(
                collection_name=name,
                query_records=[vector],  # 可以批量
                top_k=top_k,
                params=param)
            return status, results
        except Exception as e:
            print('Milvus search error: ', e)


milvus = MilvusUtil()
