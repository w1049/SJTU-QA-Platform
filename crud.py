import json
import time

import click
from flask_login import login_required, current_user
from flask_restful import Resource, reqparse
from sqlalchemy.exc import IntegrityError

import rocketqa
from ext import db, milvus
from models import Question, QuestionSet


def can_maintain(user, question_set):
    if user == question_set.owner:
        return True
    if user in question_set.maintainer:
        return True
    return False


class QuestionAPI(Resource):
    decorators = [login_required]

    # GET 显示数据并不全，很多字段都没显示
    # 或许 GET 加参数来决定需不需要某些数据？
    # 问题库包含的问题，数据量可能比较大
    # 但是用户可能只需要问题库名字？

    # Question 相关没有判断user权限
    # QuestionSet 的 append 也应该判断是否允许加入
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
            embedding = rocketqa.get_para(title, content)
            question.title = title
            question.content = content
            question.embedding = json.dumps(embedding)
            question.modified_by_id = current_user.id
            db.session.commit()
            for sid in question.belongs.with_entities(QuestionSet.id).all():
                collection_name = '_' + str(sid[0])
                milvus.delete(collection_name, [qid])
                milvus.insert(collection_name, [embedding], [qid])
            return {'message': '问题更新成功'}
        return {'message': '问题不存在'}, 400

    def delete(self, qid):
        question = Question.query.get(qid)
        if question:
            for sid in question.belongs.with_entities(QuestionSet.id).all():
                collection_name = '_' + str(sid[0])
                milvus.delete(collection_name, [qid])
            db.session.delete(question)
            db.session.commit()
            return {'message': '问题删除成功'}
        return {'message': '问题不存在'}, 400


class QuestionGroupAPI(Resource):
    decorators = [login_required]

    def get(self):  # 批量获取信息
        pass

    def post(self):
        args = reqparse.RequestParser() \
            .add_argument('many', type=int, location='json', default=0) \
            .add_argument('title', type=str, location='json', action='append', required=True, help='标题不能为空') \
            .add_argument('content', type=str, location='json', action='append', required=True, help='内容不能为空') \
            .parse_args()

        titles = args['title']
        contents = args['content']

        if len(titles) == 1 and len(contents) == 1 and args['many'] == 0:
            title, content = titles[0], contents[0]
            embedding = json.dumps(rocketqa.get_para(title, content))  # dumps 只出现在了这里
            question = Question(title=title, content=content, embedding=embedding)
            question.created_by_id = current_user.id
            db.session.add(question)
            db.session.commit()
            return {'message': '问题创建成功', 'id': question.id}
        if len(titles) == len(contents) and args['many'] == 1:  # 暂时不要用这个，没改好
            embeddings = rocketqa.get_embeddings(titles)
            questions = []
            for title, content, embedding in zip(titles, contents, embeddings):
                question = Question(title=title, content=content, embedding=json.dumps(embedding))
                question.created_by_id = current_user.id
                questions.append(question)
            db.session.add_all(questions)
            db.session.commit()
            return {'message': '问题创建成功', 'id': [question.id for question in questions]}
        return {'message': '问题创建失败'}, 400


class QuestionSetAPI(Resource):
    decorators = [login_required]

    def get(self, sid):
        question_set = QuestionSet.query.get(sid)
        if question_set:
            if not can_maintain(current_user, question_set):
                return {'message': '没权限'}, 400
            return {'id': sid,
                    'name': question_set.name,
                    'questions': [qid[0] for qid in question_set.questions.with_entities(Question.id).all()]
                    # 这里不知道有没有效率问题   update:改了一下 只要qid
                    }
        return {'message': '问题库不存在'}, 400

    def put(self, sid):
        args = reqparse.RequestParser() \
            .add_argument('op', type=str, location='json', required=True, help='操作不能为空') \
            .add_argument('name', type=str, location='json') \
            .add_argument('questions', type=int, action='append', location='json') \
            .parse_args()
        op = args['op']
        name = args['name']
        qids = args['questions']

        qs = QuestionSet.query.get(sid)
        if qs is None:
            return {'message': '问题库不存在'}, 400

        if not can_maintain(current_user, qs):
            return {'message': '没权限'}, 400

        if op == 'append':
            if not qids:
                return {'message': '问题ID不能为空'}, 400
            start = time.time()
            questions = Question.query.filter(Question.id.in_(qids)).all()
            qs.questions.extend(questions)
            qs.modified_by_id = current_user.id
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return {'message': '不要重复插入问题'}, 400

            embeddings = [json.loads(question.embedding) for question in questions]

            end = time.time()
            click.echo("sql time: {}s".format(end - start))

            milvus.insert('_' + str(sid), embeddings, qids)
            end2 = time.time()
            click.echo("milvus time: {}s".format(end2 - end))
            return {'message': '问题库增加问题'}

        elif op == 'remove':
            if not qids:
                return {'message': '问题ID不能为空'}, 400
            questions = Question.query.filter(Question.id.in_(qids)).all()
            for question in questions:
                qs.questions.remove(question)
            qs.modified_by_id = current_user.id
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return {'message': '未插入的问题'}, 400

            milvus.delete('_' + str(sid), qids)
            return {'message': '问题库移除问题'}

        elif op == 'rename':
            if not name:
                return {'message': '名称不能为空'}, 400
            qs.name = name
            qs.modified_by_id = current_user.id
            db.session.commit()
            return {'message': '问题库更名'}

        # add maintainer
        # change owner

        return {'message': '无法理解的操作'}, 400

    def delete(self, sid):
        qs = QuestionSet.query.get(sid)
        if qs:
            if not can_maintain(current_user, qs):
                return {'message': '没权限'}, 400
            milvus.drop_collection('_' + str(qs.id))
            db.session.delete(qs)
            db.session.commit()
            return {'message': '问题库删除成功'}
        return {'message': '问题库不存在'}, 400


class QuestionSetGroupAPI(Resource):
    decorators = [login_required]

    def post(self):
        args = reqparse.RequestParser() \
            .add_argument('name', type=str, location='json', required=True, help='名称不能为空') \
            .parse_args()
        # .add_argument('questions', default=[], type=int, action='append', location='json', help='问题ID不合法') \

        name = args['name']
        # qids = args['questions']

        qs = QuestionSet(name=name)
        qs.created_by_id = current_user.id
        qs.owner_id = current_user.id

        db.session.add(qs)
        db.session.commit()

        collection_name = '_' + str(qs.id)
        milvus.create_collection(collection_name)  # 按理说这个名字的 collection 是不存在的

        return {'message': '问题库创建成功'}
