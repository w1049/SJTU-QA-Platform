import os
import time
from typing import Optional

from loguru import logger
from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .utils import rocketqa
from .config import settings, setup_logging
from .dependencies import get_db, get_user
from .guardian import can_get_question_set
from .utils.milvus_util import milvus
from .models.models import User, Question, QuestionSet
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

setup_logging()


@app.on_event("startup")
def startup_event():
    logger.info('Server [{}] starting...', os.getpid())


@app.on_event("shutdown")
def shutdown_event():
    logger.info('Server [{}] shutdown.', os.getpid())


@app.get('/')
def hello_world(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@app.post('/register', description='测试用注册')
def register(name: str, institution: Optional[str] = None, db: Session = Depends(get_db)):
    user = User(name=name, institution=institution)
    db.add(user)
    db.commit()
    return '用户注册成功'


@app.get('/api/query')
def get_query(query: str, set_id: int = 1, db: Session = Depends(get_db),
              user_id: Optional[int] = Depends(get_user)):
    return _query(query, set_id, db, user_id)


@app.get('/q/{query_str}', description='测试用，给机器人用着玩玩的')
def q(query_str: str, db: Session = Depends(get_db)):
    ret = _query(query_str, 1, db)
    a = '<html><body><div>'
    for ans in ret:
        a += '<h3>' + ans['title'] + '</h3>\n'
        a += '<p>' + ans['content'] + '</p>\n'
    a += '</div></body></html>'
    return a


def _query(query_str: str, set_id: int, db: Session, user_id: Optional[int] = None):
    question_set = db.query(QuestionSet).get(set_id)
    if not can_get_question_set(db.query(User).get(user_id), question_set):
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_403_UNAUTHORIZED, detail="Please login")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
    start = time.time()
    embedding = rocketqa.get_embedding(query_str)
    end = time.time()
    logger.debug('feature extract time: {}s', end - start)

    start = time.time()

    name = '_' + str(set_id)
    search_status, search_result = milvus.search(name, embedding, 5)
    qids = []
    if not search_result:
        return {'message': "I'm a teapot"}, 418
    for each_distance in search_result[0]:
        qids.append(each_distance.id)
    end = time.time()
    logger.debug('search time: {}s', end - start)

    start = time.time()
    output = []
    for qid in qids:
        question = db.query(Question).get(qid)
        output.append({'title': question.title, 'content': question.content})
    end = time.time()
    logger.debug('sql time: {}s', end - start)
    return output
