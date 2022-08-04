import time

import click
from flask import Flask

from ext import db, milvus
from models import Question, User, QuestionSet


def register_cli(app: Flask):
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
