import click
from sqlalchemy.orm import Session

from .models.models import *
from .utils import milvus
from .utils.database import engine


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
def db_drop():
    """清空数据库和milvus"""
    click.echo('清空数据库')
    Base.metadata.drop_all(engine)

    click.echo('清空milvus')
    status, collections = milvus.client.list_collections()
    for collection in collections:
        milvus.client.drop_collection(collection)


@click.group()
def group():
    pass


group.add_command(db_init)
group.add_command(db_drop)

if __name__ == '__main__':
    group()
