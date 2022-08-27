import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import guardian
from ..models.schemas import schemas
from ..utils import rocketqa
from ..database import SessionLocal
from ..dependencies import get_db, get_logged_user
from ..utils.milvus_util import milvus
from ..models.models import Question, QuestionSet, User, EnumRole
from ..models.schemas.schemas import HTTPError

router = APIRouter(
    prefix='/api/question',
    tags=['question'],
    responses={401: {'model': HTTPError}, 403: {'model': HTTPError}}
)


@router.get('/{qid}', response_model=schemas.QuestionModel, responses={404: {'model': HTTPError}})
def get_question(qid: int, db: Session = Depends(get_db), user_id: int = Depends(get_logged_user)):
    question = db.query(Question).get(qid)
    if question:
        if not guardian.can_get_question(db.query(User).get(user_id), question):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
        return question
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Question not found')


@router.put('/{qid}', response_model=schemas.QuestionModel, responses={404: {'model': HTTPError}})
def update_question(qid: int, args: schemas.QuestionUpdate, db: Session = Depends(get_db),
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
        return {'ok': True}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Question not found')


@router.get('/', response_model=schemas.QuestionListPage, responses={404: {'model': HTTPError}},
            description='无sid: 返回用户创建的问题（admin可获取所有问题）\n\n'
                        '有sid: 返回问题库内的问题')
def get_questions(sid: Optional[int] = None, pager: schemas.Pager = Depends(),
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
            if not guardian.can_get_question_set(db.query(User).get(user_id), question_set):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
            query = question_set.questions
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QuestionSet not found')
    questions = schemas.QuestionListPage()
    query.paginate(pager.page, pager.per_page).update(questions)
    return questions


@router.post('/', response_model=schemas.QuestionModel, status_code=status.HTTP_201_CREATED)
async def create_question(args: schemas.QuestionCreate, user_id: int = Depends(get_logged_user)):
    with SessionLocal() as db:
        if not guardian.can_create_question(db.query(User).get(user_id)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
    title, content = args.title, args.content
    emb_array = await rocketqa.async_get_para(title, content)
    embedding = json.dumps(emb_array)  # dumps 只出现在了这里
    with SessionLocal() as db:
        question = Question(title=title, content=content, embedding=embedding)
        question.created_by_id = user_id
        question.modified_by_id = user_id
        db.add(question)
        db.commit()
        db.refresh(question)
        return question
