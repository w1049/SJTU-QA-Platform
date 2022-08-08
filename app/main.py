import time
from typing import Union

import click
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from . import rocketqa
from .config import settings
from .dependencies import get_db
from .milvus_util import milvus
from .models import User, Question
from .routes import question, question_set, auth

app = FastAPI()

app.include_router(question.router)
app.include_router(question_set.router)
app.include_router(auth.router)

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

templates = Jinja2Templates(directory='templates')


@app.get('/')
def hello_world(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@app.post('/register', description='测试用注册')
def register(name: str, institution: Union[str, None] = None, db: Session = Depends(get_db)):
    user = User(name=name, institution=institution)
    db.add(user)
    db.commit()
    return '用户注册成功'


@app.get('/api/query')
def get_query(query: str, set_id: Union[int, None] = 1, db: Session = Depends(get_db)):
    return _query(query, set_id, db)


@app.get('/q/{query_str}', description='测试用，给机器人用着玩玩的')
def q(query_str: str, db: Session = Depends(get_db)):
    ret = _query(query_str, 1, db)
    a = '<html><body><div>'
    for ans in ret:
        a += '<h3>' + ans['title'] + '</h3>\n'
        a += '<p>' + ans['content'] + '</p>\n'
    a += '</div></body></html>'
    return a


def _query(query_str, set_id, db):
    start = time.time()
    if set_id is None:
        set_id = 1
    embedding = rocketqa.get_embedding(query_str)
    end = time.time()
    click.echo('feature extract time: {}s'.format(end - start))

    start = time.time()
    # name = '_' + str(set_id)
    # click.echo(name)

    name = '_' + str(set_id)
    status, search_result = milvus.search(name, embedding, 5)
    qids = []
    if not search_result:
        return {'message': "I'm a teapot"}, 418
    for each_distance in search_result[0]:
        qids.append(each_distance.id)
    end = time.time()
    click.echo('search time: {}s'.format(end - start))

    start = time.time()
    output = []
    for qid in qids:
        question = db.query(Question).get(qid)
        output.append({'title': question.title, 'content': question.content})
    end = time.time()
    click.echo('sql time: {}s'.format(end - start))
    return output
