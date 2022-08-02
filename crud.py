import json

from flask_restful import Resource, reqparse

import rocketqa
from ext import db, milvus
from models import Question


class QuestionAPI(Resource):

    # GET 显示数据并不全，很多字段都没显示
    # 或许 GET 加参数来决定需不需要某些数据？
    # 问题库包含的问题，数据量可能比较大
    # 但是用户可能只需要问题库名字？
    def get(self, qid):
        question = Question.query.get(qid)
        if question:
            return {'id': qid, 'title': question.title, 'content': question.content}
        return {'message': '问题不存在'}, 400

    def put(self, qid):
        args = reqparse.RequestParser() \
            .add_argument('title', type=str, location='json', required=True, help='标题不能为空') \
            .add_argument('content', type=str, location='json', required=True, help='内容不能为空') \
            .parse_args()
        title = args['title']
        content = args['content']

        question = Question.query.get(qid)
        if question:
            embedding = rocketqa.get_embedding(title)
            question.title = title
            question.content = content
            question.embedding = json.dumps(embedding)
            for qs in question.belongs.all():
                collection_name = '_' + str(qs.id)
                milvus.delete(collection_name, [qid])
                milvus.insert(collection_name, [embedding], [qid])
            db.session.commit()
            return {'message': '问题更新成功'}
        return {'message': '问题不存在'}, 400

    def delete(self, qid):
        question = Question.query.get(qid)
        if question:
            for qs in question.belongs.all():
                collection_name = '_' + str(qs.id)
                milvus.delete(collection_name, [qid])
            db.session.delete(question)
            db.session.commit()
            return {'message': '问题删除成功'}
        return {'message': '问题不存在'}, 400


class QuestionGroupAPI(Resource):
    def post(self):
        args = reqparse.RequestParser() \
            .add_argument('title', type=str, location='json', required=True, help='标题不能为空') \
            .add_argument('content', type=str, location='json', required=True, help='内容不能为空') \
            .parse_args()
        title = args['title']
        content = args['content']

        embedding = json.dumps(rocketqa.get_embedding(title))  # dumps 只出现在了这里

        question = Question(title=title, content=content, embedding=embedding)
        db.session.add(question)
        db.session.commit()
        return {'message': '问题创建成功', 'id': question.id}
