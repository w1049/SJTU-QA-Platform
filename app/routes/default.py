import time
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends, Request, HTTPException, status, Response
from loguru import logger
from sqlalchemy.orm import Session
from starlette.status import HTTP_200_OK

from ..dependencies import get_db, get_user
from ..models.models import User, Question, QuestionSet
from ..models.schemas.question import QuestionListPage
from ..utils import milvus, rocketqa, guardian, templates

router = APIRouter()


@router.get('/')
def hello_world(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@router.post('/register', description='测试用注册')
def register(name: str, institution: Optional[str] = None, db: Session = Depends(get_db)):
    user = User(name=name, institution=institution)
    db.add(user)
    db.commit()
    return Response(status_code=HTTP_200_OK)


@router.get('/api/query')
def get_query(query: str, set_id: int = 1, db: Session = Depends(get_db),
              user_id: Optional[int] = Depends(get_user)):
    return _query(query, set_id, db, user_id)


@router.get('/q/{query_str}', description='测试用，给机器人用着玩玩的')
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
    if not guardian.can_get_question_set(db.query(User).get(user_id), question_set):
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_403_UNAUTHORIZED, detail="Please login")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
    if len(query_str) <= 4:
        questions = question_set.questions.filter(Question.title.like(f'%{query_str}%')).limit(5).all()
        output = []
        for question in questions:
            output.append({'title': question.title, 'content': question.content})
        return output

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
