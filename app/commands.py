import click
from sqlalchemy.orm import Session

from .database import engine
from .milvus_util import milvus
from .models import *


@click.command()
def db_init():
    """初始化数据库，建立system用户与公开库"""
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        qs = db.query(QuestionSet).with_for_update().get(1)
        if not qs:
            user = User(name='system', institution='system', role=EnumRole.admin)
            db.add(user)
            db.flush()
            qs = QuestionSet(name='公开库', permission=EnumPermission.public,
                             created_by=user,
                             owner=user,
                             maintainer=[user],
                             modified_by=user)
            db.add(qs)
            milvus.create_collection('_1')
            db.commit()
            click.echo('PublicSet Created.')
        else:
            click.echo('PublicSet Exists.')


@click.command()
def refresh():
    """清空并重新初始化数据库和milvus"""
    click.echo('清空数据库')
    Base.metadata.drop_all(engine)

    click.echo('清空milvus')
    status, collections = milvus.client.list_collections()
    for collection in collections:
        milvus.client.drop_collection(collection)

    click.echo("初始化数据库与milvus")
    db_init()
    click.echo("数据库创建成功！")


@click.group()
def group():
    pass


group.add_command(db_init)
group.add_command(refresh)

if __name__ == '__main__':
    group()
