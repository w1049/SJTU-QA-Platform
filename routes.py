import time

import click
from flask import Blueprint
from flask import render_template, request, jsonify

import rocketqa
from ext import db, milvus
from models import User, Question

main = Blueprint('main', __name__)


@main.route('/')
def hello_world():
    return render_template('index.html')


@main.route('/register', methods=['POST'])  # 这个目前没什么用，没接入用户
def register():
    if request.method == 'POST':
        name = request.json.get('name')
        institution = request.json.get('institution')
        user = User(name=name, institution=institution)
        db.session.add(user)
        db.session.commit()
        return '用户注册成功'  # json?
    return 'hello, GET!'


@main.route('/api/query', methods=['GET', 'POST'])
def query():
    if request.method == 'POST':
        query_str = request.json.get('query')
        set_id = request.json.get('set_id')
    else:
        query_str = request.args.get('query')
        set_id = request.args.get('set_id')

    return _query(query_str, set_id)


@main.route('/q/<query_str>', methods=['GET'])  # 给机器人用着玩玩的
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
