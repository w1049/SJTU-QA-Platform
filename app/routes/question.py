import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from loguru import logger
from sqlalchemy.orm import Session
from starlette.status import HTTP_200_OK

from ..dependencies import get_db, get_logged_user
from ..models.models import Question, QuestionSet, User, EnumRole, EnumPermission
from ..models.schemas import HTTPError, Pager
from ..models.schemas.question import QuestionDetail, QuestionUpdate, QuestionListPage, QuestionCreate, QuestionCreated
from ..utils import milvus, rocketqa, guardian
from ..utils.database import SessionLocal

router = APIRouter(
    prefix='/api/question',
    tags=['question'],
    responses={401: {'model': HTTPError}, 403: {'model': HTTPError}}
)


@router.get('/', response_model=QuestionListPage, responses={404: {'model': HTTPError}},
            description='无sid: 返回用户创建的问题（admin可获取所有问题）\n\n'
                        '有sid: 返回问题库内的问题')
def get_questions(sid: Optional[int] = None, pager: Pager = Depends(),
                  db: Session = Depends(get_db), user_id: int = Depends(get_logged_user)):
    user = db.query(User).get(user_id)
    if sid is None:
        if user.role == EnumRole.admin:
            query = db.query(Question)
        else:
            query = user.created_question
    else:
        question_set = db.query(QuestionSet).get(sid)
        if question_set:
            if not guardian.can_get_question_set(user, question_set):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
            query = question_set.questions
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QuestionSet not found')
    questions = QuestionListPage()
    query.paginate(pager.page, pager.per_page).update(questions)
    return questions


@router.post('/', response_model=QuestionCreated, status_code=status.HTTP_201_CREATED)
async def create_question(args: QuestionCreate, user_id: int = Depends(get_logged_user)):
    with SessionLocal() as db:
        user = db.query(User).get(user_id)
        if not guardian.can_create_question(user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
        if args.sid:
            qs = db.query(QuestionSet).get(args.sid)
            if qs is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QuestionSet not found')
            if not guardian.can_modify_question_set(user, qs):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
    title, content = args.title, args.content
    emb_array = await rocketqa.async_get_para(title, content)
    embedding = json.dumps(emb_array)  # dumps 只出现在了这里
    with SessionLocal() as db:
        question = Question(title=title, content=content, embedding=embedding)
        question.created_by_id = user_id
        question.modified_by_id = user_id
        db.add(question)
        if args.sid:
            db.flush()
            qs = db.query(QuestionSet).get(args.sid)
            public = qs.permission == EnumPermission.public
            start = time.time()
            qs.questions.append(question)
            qs.modified_by_id = user_id
            if public:
                public_set = db.query(QuestionSet).get(1)
                public_set.questions.append(question)

            db.flush()

            end = time.time()
            logger.debug('sql time: {}s', end - start)

            milvus.insert('_' + str(args.sid), [emb_array], [question.id])
            if public:
                milvus.insert('_1', [emb_array], [question.id])

            end2 = time.time()
            logger.debug('milvus time: {}s', end2 - end)
        db.commit()
        question = QuestionCreated.from_orm(question)
        return question


@router.get('/search', response_model=QuestionListPage, responses={404: {'model': HTTPError}},
            description='关键词搜索')
def search_questions(sid: int, text: str, pager: Pager = Depends(),
                     db: Session = Depends(get_db), user_id: int = Depends(get_logged_user)):
    user = db.query(User).get(user_id)
    question_set = db.query(QuestionSet).get(sid)
    if question_set:
        if not guardian.can_get_question_set(user, question_set):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
        query = question_set.questions.filter(Question.title.like(f'%{text}%'))
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QuestionSet not found')
    questions = QuestionListPage()
    query.paginate(pager.page, pager.per_page).update(questions)
    return questions


@router.get('/{qid}', response_model=QuestionDetail, responses={404: {'model': HTTPError}})
def get_question(qid: int, db: Session = Depends(get_db), user_id: int = Depends(get_logged_user)):
    question = db.query(Question).get(qid)
    if question:
        if not guardian.can_get_question(db.query(User).get(user_id), question):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
        return question
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Question not found')


@router.put('/{qid}', response_model=QuestionDetail, responses={404: {'model': HTTPError}})
def update_question(qid: int, args: QuestionUpdate, db: Session = Depends(get_db),
                    user_id: int = Depends(get_logged_user)):
    question = db.query(Question).get(qid)
    if question:
        if not guardian.can_modify_question(db.query(User).get(user_id), question):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
        if args.title:
            question.title = args.title
            title = args.title
        else:
            title = question.title
        if args.content:
            question.content = args.content
            content = args.content
        else:
            content = question.content
        embedding = rocketqa.get_para(title, content)
        question.embedding = json.dumps(embedding)
        question.modified_by_id = user_id
        db.commit()
        db.refresh(question)
        for sid in question.belongs.with_entities(QuestionSet.id).all():
            collection_name = '_' + str(sid[0])
            milvus.delete(collection_name, [qid])
            milvus.insert(collection_name, [embedding], [qid])
        return question
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Question not found')


@router.delete('/{qid}', responses={404: {'model': HTTPError}})
def delete_question(qid: int, db: Session = Depends(get_db), user_id: int = Depends(get_logged_user)):
    question = db.query(Question).get(qid)
    if question:
        if not guardian.can_delete_question(db.query(User).get(user_id), question):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
        for sid in question.belongs.with_entities(QuestionSet.id).all():
            collection_name = '_' + str(sid[0])
            milvus.delete(collection_name, [qid])
        db.delete(question)
        db.commit()
        return Response(status_code=HTTP_200_OK)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Question not found')
