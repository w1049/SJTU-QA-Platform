import click

from .database import engine
from .milvus_util import milvus
from .models import *


@click.command()
def db_init():
    """删除并重新构建数据库"""
    click.echo('删除数据库和表')
    Base.metadata.drop_all(engine)
    click.echo("创建数据库！")
    Base.metadata.create_all(engine)
    click.echo("数据库创建成功！")


@click.command()
def milvus_init():
    status, collections = milvus.client.list_collections()
    for collection in collections:
        milvus.client.drop_collection(collection)


@click.group()
def group():
    pass


group.add_command(db_init)
group.add_command(milvus_init)

if __name__ == '__main__':
    group()
