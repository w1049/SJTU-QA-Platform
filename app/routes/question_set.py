import json
import time
from typing import List

import click
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas
from ..dependencies import get_db, get_user
from ..milvus_util import milvus
from ..models import QuestionSet, Question
from ..schemas import HTTPError

router = APIRouter(
    prefix='/api/question_set',
    tags=['question_set'],
    responses={401: {'model': HTTPError}, 403: {'model': HTTPError}}
)


def can_maintain(user_id, question_set):
    if user_id == question_set.owner_id:
        return True
    # if user in question_set.maintainer:
    #     return True
    return False


@router.get('/{sid}', response_model=schemas.QuestionSetRead, responses={404: {'model': HTTPError}})
def get_question_set(sid: int, db: Session = Depends(get_db), user_id: int = Depends(get_user)):
    question_set = db.query(QuestionSet).get(sid)
    if question_set:
        if not can_maintain(user_id, question_set):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
        ret_set = schemas.QuestionSetRead.from_orm(question_set)
        ret_set.question_ids = [qid[0] for qid in question_set.questions.with_entities(Question.id).all()]
        return ret_set
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QuestionSet not found')


@router.put('/{sid}', responses={404: {'model': HTTPError}, 400: {'model': HTTPError}})
def update_question_set(sid: int, args: schemas.QuestionSetUpdate, db: Session = Depends(get_db),
                        user_id: int = Depends(get_user)):
    op = args.operation
    name = args.name
    qids = args.question_ids

    qs = db.query(QuestionSet).get(sid)
    if qs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QuestionSet not found')

    if not can_maintain(user_id, qs):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')

    if op == 'append':
        if not qids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='问题ID不能为空')
        start = time.time()
        questions = db.query(Question).filter(Question.id.in_(qids)).all()
        qs.questions.extend(questions)
        qs.modified_by_id = user_id
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='不要重复插入问题')

        embeddings = [json.loads(question.embedding) for question in questions]

        end = time.time()
        click.echo('sql time: {}s'.format(end - start))

        milvus.insert('_' + str(sid), embeddings, qids)
        end2 = time.time()
        click.echo('milvus time: {}s'.format(end2 - end))
        return {'message': '问题库增加问题'}

    elif op == 'remove':
        if not qids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='问题ID不能为空')
        questions = db.query(Question).filter(Question.id.in_(qids)).all()
        for question in questions:
            qs.questions.remove(question)
        qs.modified_by_id = user_id
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            print(e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='未插入的问题')

        milvus.delete('_' + str(sid), qids)
        return {'message': '问题库移除问题'}

    elif op == 'rename':
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='名称不能为空')
        qs.name = name
        qs.modified_by_id = user_id
        db.commit()
        return {'message': '问题库更名'}

    # add maintainer
    # change owner

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='无法理解的操作')


@router.delete('/{sid}', responses={404: {'model': HTTPError}})
def delete_question_set(qid: int, db: Session = Depends(get_db), user_id: int = Depends(get_user)):
    question_set = db.query(QuestionSet).get(qid)
    if question_set:
        if not can_maintain(user_id, question_set):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
        milvus.drop_collection('_' + str(question_set.id))
        db.delete(question_set)
        db.commit()
        return {'ok': True}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QuestionSet not found')


@router.get('/', response_model=List[schemas.QuestionSetModel])
def get_question_sets(db: Session = Depends(get_db), user_id: int = Depends(get_user)):
    # if admin
    return db.query(QuestionSet).all()


@router.post('/', response_model=schemas.QuestionSetModel, status_code=status.HTTP_201_CREATED)
def create_question_set(args: schemas.QuestionSetCreate, db: Session = Depends(get_db),
                        user_id: int = Depends(get_user)):
    name = args.name

    qs = QuestionSet(name=name)
    qs.created_by_id = user_id
    qs.owner_id = user_id
    qs.modified_by_id = user_id

    db.add(qs)
    db.commit()
    db.refresh(qs)

    collection_name = '_' + str(qs.id)
    milvus.create_collection(collection_name)  # 按理说这个名字的 collection 是不存在的

    return qs
