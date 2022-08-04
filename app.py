import json
import time

import click
import flask_login
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
from flask_login import login_required
from flask_migrate import Migrate

from crud import QuestionAPI, QuestionGroupAPI, QuestionSetAPI, QuestionSetGroupAPI
from settings import TestConfig
from ext import db, api, milvus, login_manager
from models import User, Question, QuestionSet
import rocketqa

app = Flask(__name__)

app.config.from_object(TestConfig)

db.init_app(app)
migrate = Migrate(app, db)
CORS(app, supports_credentials=True)  # 允许跨域
login_manager.init_app(app)

api.add_resource(QuestionAPI, '/api/question/<int:qid>')
api.add_resource(QuestionGroupAPI, '/api/question')
api.add_resource(QuestionSetAPI, '/api/question_set/<int:sid>')
api.add_resource(QuestionSetGroupAPI, '/api/question_set')
api.init_app(app)


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


@app.cli.command()
def test():
    start = time.time()
    qs = QuestionSet.query.get(1)
    x = [q[0] for q in qs.questions.with_entities(Question.id).all()]
    end = time.time()
    print(x)
    click.echo("cost: {}s".format(end - start))


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


@app.route('/api/query', methods=['GET', 'POST'])
def query():
    if request.method == 'POST':
        query_str = request.json.get('query')
        set_id = request.json.get('set_id')
    else:
        query_str = request.args.get('query')
        set_id = request.args.get('set_id')

    return _query(query_str, set_id)


@app.route('/q/<query_str>', methods=['GET'])  # 给机器人用着玩玩的
def q(query_str):
    ret = _query(query_str, 1)
    obj = ret.json
    a = '<html><body><div>'
    for ans in obj:
        a += '<h3>' + ans['title'] + '</h3>\n'
        a += '<p>' + ans['content'] + '</p>\n'
    a += '</div></body></html>'
    return a


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
    if not search_result:
        return jsonify({'message': "I'm a teapot"}), 418
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
    return jsonify(output)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/login/<int:uid>', methods=['GET'])
def login(uid):
    user = User.query.get(uid)
    if user:
        flask_login.login_user(user)
        return 'Hello, {}!'.format(user.name)
    else:
        return '不存在！', 400


@app.route('/logout')
@login_required
def logout():
    flask_login.logout_user()
    return 'Logged out'  # redirect somewhere


if __name__ == '__main__':
    app.run()
