import json
import time

import click
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
from flask_migrate import Migrate

from settings import TestConfig
from ext import db, MilvusUtil
from models import User, Question, QuestionSet
import rocketqa

app = Flask(__name__)

app.config.from_object(TestConfig)

db.init_app(app)
migrate = Migrate(app, db)
CORS(app, supports_credentials=True)  # 允许跨域
milvus = MilvusUtil()


@app.cli.command()
def db_init():
    """删除并重新构建数据库"""
    click.echo('删除数据库和表')
    db.drop_all()
    click.echo("创建数据库！")
    db.create_all()
    click.echo("数据库创建成功！")


@app.cli.command()
def milvus_init():
    status, collections = milvus.client.list_collections()
    for collection in collections:
        milvus.client.drop_collection(collection)


# @app.cli.command()
# def test():
# click.echo(app.config['MILVUS_HOST'])


@app.cli.command()
def test_add():
    """只能测试SQL，不包括NLP，已经没用了"""
    print("开始测试")
    user = User(name='hello', institution='sjtu')
    db.session.add(user)
    db.session.commit()

    q1 = Question()
    q1.title = '新生群'
    q1.content = '新生群这种东西除了瞎聊胡吹浪费时间以外，' \
                 '唯一存在的价值就是找某人的QQ，希望学弟学妹不要浪费时间在里面。' \
                 '里面的学长学姐尤其是最活跃的几个,—般都是自己生活都过的不咋地的，' \
                 '除了要找对象，要不然谁有闲工夫放在这上面。少瞎聊两句，多做点有用的，行胜于言。'

    q2 = Question()
    q2.title = '选课社区'
    q2.content = 'course.sjtu.plus'

    q3 = Question(title='网管部学什么',
                  content='计算机网络及维修相关技术知识，与用户沟通的能力，与其他优秀Nimoer的交流中成长')

    s1 = QuestionSet(name='Set 1')
    s2 = QuestionSet(name='Set 2')

    s1.questions.append(q1)
    s1.questions.append(q2)
    s2.questions.append(q1)
    s2.questions.append(q3)

    db.session.add_all([q1, q2, q3, s1, s2])
    db.session.commit()
    print("添加成功！")


@app.route('/')
def hello_world():  # 路由全写 app.py 里了，后面应该可以改成蓝图
    return render_template('index.html')


@app.route('/register', methods=['POST'])  # 这个目前没什么用，没接入用户
def register():
    if request.method == 'POST':
        name = request.json.get('name')
        institution = request.json.get('institution')
        user = User(name=name, institution=institution)
        db.session.add(user)
        db.session.commit()
        return '用户注册成功'  # json?
    return 'hello, GET!'


# query 还没改名，预计变成/api/query
@app.route('/query', methods=['GET', 'POST'])
def query():
    if request.method == 'POST':
        query_str = request.json.get('query')
        set_id = request.json.get('set_id')
    else:
        query_str = request.args.get('query')
        set_id = request.args.get('set_id')

    return _query(query_str, set_id)


def _query(query_str, set_id):
    start = time.time()
    if set_id is None:
        set_id = 1
    embedding = rocketqa.get_embedding(query_str)
    end = time.time()
    click.echo("feature extract time: {}s".format(end - start))

    start = time.time()
    # name = '_' + str(set_id)
    # click.echo(name)

    name = '_' + str(set_id)
    status, search_result = milvus.search(name, embedding, 5)
    qids = []
    for each_distance in search_result[0]:
        qids.append(each_distance.id)
    end = time.time()
    click.echo("search time: {}s".format(end - start))

    start = time.time()
    output = []
    for qid in qids:
        question = Question.query.get(qid)
        output.append({'title': question.title, 'content': question.content})
    end = time.time()
    click.echo("sql time: {}s".format(end - start))
    return json.dumps(output, ensure_ascii=False)


# CRUD


# GET 显示数据并不全，很多字段都没显示
# 或许 GET 加参数来决定需不需要某些数据？
# 问题库包含的问题，数据量可能比较大
# 但是用户可能只需要问题库名字？
@app.route('/api/question/<qid>', methods=['GET'])  # 可能改成批量？同理DELETE
def question_get(qid):
    question = Question.query.get(qid)
    if question:
        return jsonify({'code': 200,
                        'questions': [
                            {'title': question.title, 'content': question.content}
                        ]})
    return jsonify({'code': 418, 'msg': "I'm a teapot. Question doesn't exist. "})


@app.route('/api/question', methods=['POST'])  # 这个也可以改批量
def question_create():
    title = request.json.get('title')
    content = request.json.get('content')

    if title is None or content is None:
        return jsonify({'code': 418, 'msg': "I'm a teapot"})

    embedding = json.dumps(rocketqa.get_embedding(title))
    # json.dumps 现在和 jsonify 是混用的
    question = Question(title=title, content=content, embedding=embedding)
    db.session.add(question)
    db.session.commit()
    return jsonify({'code': 200, 'msg': '问题创建成功'})


@app.route('/api/question', methods=['PUT'])
def question_update():
    qid = request.json.get('id')
    title = request.json.get('title')
    content = request.json.get('content')

    if qid is None or title is None or content is None:
        return jsonify({'code': 418, 'msg': "I'm a teapot"})

    question = Question.query.get(qid)
    if question:
        embedding = json.dumps(rocketqa.get_embedding(title))
        Question.title = title
        Question.content = content
        Question.embedding = embedding
        # TODO
        # 更改所有相关Milvus库
        db.session.submit()
        return jsonify({'code': 200, 'msg': '问题更新成功'})
    return jsonify({'code': 418, 'msg': "I'm a teapot. Question doesn't exist. "})


# 删除都没测试，慎用
@app.route('/api/question/<qid>', methods=['DELETE'])
def question_delete(qid):
    question = Question.query.get(qid)
    if question:
        embedding = Question.embedding
        db.session.delete(question)
        # TODO
        # 在所有相关Milvus库中删除
        db.session.submit()
        return jsonify({'code': 200, 'msg': '问题删除成功'})
    return jsonify({'code': 418, 'msg': "I'm a teapot. Question doesn't exist."})


@app.route('/api/question_set/<sid>', methods=['GET'])
def set_get(sid):
    question_set = QuestionSet.query.get(sid)
    if question_set:
        return jsonify({'code': 200,
                        'question_set': {'name': question_set.name,
                                         'questions': [question.id for question in question_set.questions]
                                         # 这里不知道有没有效率问题
                                         }
                        })
    return jsonify({'code': 418, 'msg': "I'm a teapot. Set doesn't exist. "})


@app.route('/api/question_set', methods=['POST'])
def set_create():
    # 测试的时候这个函数耗时比较长，还没测是sql慢还是milvus慢
    name = request.json.get('name')
    qids = request.json.get('questions')

    if name is None or qids is None:
        return jsonify({'code': 418, 'msg': "I'm a teapot"})

    qs = QuestionSet(name=name)
    embeddings = []
    for qid in qids:
        question = Question.query.get(qid)
        qs.questions.append(question)
        embeddings.append(json.loads(question.embedding))
    db.session.add(qs)
    db.session.commit()

    collection_name = '_' + str(qs.id)
    milvus.create_collection(collection_name)  # 按理说这个名字的 collection 是不存在的
    if len(embeddings) > 0:
        milvus.insert(collection_name, embeddings, qids)
    # 可能 commit 要放到最后面？不是很懂万一出现中断怎么办
    return jsonify({'code': 200, 'msg': '问题库创建成功'})


@app.route('/api/question_set', methods=['PUT'])
def set_update():
    op = request.json.get('op')
    set_id = request.json.get('id')
    qids = request.json.get('questions')

    if op is None or set_id is None or qids is None:
        return jsonify({'code': 418, 'msg': "I'm a teapot"})

    qs = QuestionSet.query.get(set_id)
    if qs is None:  # 或许这里不是None? 可能有什么别的表示?
        return jsonify({'code': 418, 'msg': "I'm a teapot. Set doesn't exist."})

    # 缺少判断 qids 是否为空
    questions = [Question.query.get(qid) for qid in qids]

    if op == 'append':  # 没有检测能不能增加，能不能删除
        embeddings = []
        for question in questions:
            qs.questions.append(question)
            embeddings.append(json.loads(question.embedding))
        db.session.commit()

        milvus.insert('_' + str(qs.id), embeddings, qids)

        return jsonify({'code': 200, 'msg': '问题库增加问题'})

    elif op == 'remove':
        for question in questions:
            qs.questions.remove(question)
        db.session.commit()

        milvus.delete('_' + str(qs.id), qids)

        return jsonify({'code': 200, 'msg': '问题库移除问题'})
    # elif op == 'edit':
    #     qs.questions = [question for question in questions]
    #     db.session.commit()
    #     return 'edit'
    return jsonify({'code': 418, 'msg': "I'm a teapot. Can't understand operation."})


if __name__ == '__main__':
    app.run()
