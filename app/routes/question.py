import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas, rocketqa
from ..dependencies import get_db, get_user
from ..milvus_util import milvus
from ..models import Question, QuestionSet
from ..schemas import HTTPError

router = APIRouter(
    prefix='/api/question',
    tags=['question'],
    responses={401: {'model': HTTPError}, 403: {'model': HTTPError}}
)


@router.get('/{qid}', response_model=schemas.QuestionModel, responses={404: {'model': HTTPError}})
def get_question(qid: int, db: Session = Depends(get_db), user_id: int = Depends(get_user)):
    question = db.query(Question).get(qid)
    if question:
        return question
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Question not found')


@router.put('/{qid}', response_model=schemas.QuestionModel, responses={404: {'model': HTTPError}})
def update_question(qid: int, args: schemas.QuestionUpdate, db: Session = Depends(get_db),
                    user_id: int = Depends(get_user)):
    title, content = args.title, args.content
    question = db.query(Question).get(qid)
    if question:
        embedding = rocketqa.get_para(title, content)
        question.title = title
        question.content = content
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
def delete_question(qid: int, db: Session = Depends(get_db), user_id: int = Depends(get_user)):
    question = db.query(Question).get(qid)
    if question:
        for sid in question.belongs.with_entities(QuestionSet.id).all():
            collection_name = '_' + str(sid[0])
            milvus.delete(collection_name, [qid])
        db.delete(question)
        db.commit()
        return {'ok': True}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Question not found')


@router.get('/', response_model=List[schemas.QuestionModel])
def get_questions(db: Session = Depends(get_db), user_id: int = Depends(get_user)):
    return db.query(Question).all()


@router.post('/', response_model=schemas.QuestionModel, status_code=status.HTTP_201_CREATED)
def create_question(args: schemas.QuestionCreate, db: Session = Depends(get_db), user_id: int = Depends(get_user)):
    title, content = args.title, args.content
    embedding = json.dumps(rocketqa.get_para(title, content))  # dumps 只出现在了这里
    question = Question(title=title, content=content, embedding=embedding)
    question.created_by_id = user_id
    question.modified_by_id = user_id
    db.add(question)
    db.commit()
    db.refresh(question)
    return question
