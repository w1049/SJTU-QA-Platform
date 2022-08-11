import json
import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from .. import schemas, guardian
from ..dependencies import get_db, get_logged_user
from ..milvus_util import milvus
from ..models import QuestionSet, Question, User, EnumRole, EnumPermission
from ..schemas import HTTPError

router = APIRouter(
    prefix='/api/question_set',
    tags=['question_set'],
    responses={401: {'model': HTTPError}, 403: {'model': HTTPError}}
)


@router.get('/{sid}', response_model=schemas.QuestionSetRead, responses={404: {'model': HTTPError}})
def get_question_set(sid: int, db: Session = Depends(get_db), user_id: int = Depends(get_logged_user)):
    question_set = db.query(QuestionSet).get(sid)
    if question_set:
        if not guardian.can_get_question_set(db.query(User).get(user_id), question_set):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
        ret_set = schemas.QuestionSetRead.from_orm(question_set)
        ret_set.question_ids = [qid[0] for qid in question_set.questions.with_entities(Question.id).all()]
        return ret_set
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QuestionSet not found')


@router.put('/{sid}', responses={404: {'model': HTTPError}, 400: {'model': HTTPError}})
def update_question_set(sid: int, args: schemas.QuestionSetUpdate, db: Session = Depends(get_db),
                        user_id: int = Depends(get_logged_user)):
    op = args.operation
    name = args.name
    qids = args.question_ids

    qs = db.query(QuestionSet).get(sid)
    if qs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QuestionSet not found')

    if not guardian.can_modify_question_set(db.query(User).get(user_id), qs):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')

    public = False
    if qs.permission == EnumPermission.public:
        public = True

    if op == 'append':
        if not qids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='问题ID不能为空')
        start = time.time()
        questions = db.query(Question).filter(Question.id.in_(qids)).all()
        if len(qids) != len(questions):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='问题ID有错误')
        qs.questions.extend(questions)
        qs.modified_by_id = user_id
        if public:
            public_set = db.query(QuestionSet).get(1)
            public_set.questions.extend(questions)
        try:
            db.commit()
        except Exception as e:
            db.rollback()  # 或许不需要显式rollback
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='不要重复插入问题')

        embeddings = [json.loads(question.embedding) for question in questions]
        qids = [question.id for question in questions]
        
        end = time.time()
        logger.debug('sql time: {}s', end - start)

        milvus.insert('_' + str(sid), embeddings, qids)
        if public:
            milvus.insert('_1', embeddings, qids)

        end2 = time.time()
        logger.debug('milvus time: {}s', end2 - end)
        return {'message': '问题库增加问题'}

    elif op == 'remove':
        if not qids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='问题ID不能为空')
        questions = db.query(Question).filter(Question.id.in_(qids)).all()
        if len(qids) != len(questions):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='问题ID有错误')
        for question in questions:
            qs.questions.remove(question)
        qs.modified_by_id = user_id
        if public:
            public_set = db.query(QuestionSet).get(1)
            for question in questions:
                public_set.questions.remove(question)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.debug(e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='未插入的问题')

        milvus.delete('_' + str(sid), qids)
        if public:
            milvus.delete('_1', qids)
        return {'message': '问题库移除问题'}

    elif op == 'rename':
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='名称不能为空')
        qs.name = name
        qs.modified_by_id = user_id
        db.commit()
        return {'message': '问题库更名'}

    elif op == 'public':
        if qs.permission != EnumPermission.public:
            qs.permission = EnumPermission.public
            qs.modified_by_id = user_id
            public_set = db.query(QuestionSet).get(1)
            questions = qs.questions
            public_set.questions.extend(questions)
            db.commit()

            embeddings = [json.loads(question.embedding) for question in questions]
            qids = [question.id for question in questions]
            milvus.insert('_1', embeddings, qids)
            return {'message': '设为公开'}

    elif op == 'private':
        if qs.permission != EnumPermission.private:
            qs.permission = EnumPermission.private
            qs.modified_by_id = user_id
            public_set = db.query(QuestionSet).get(1)
            questions = qs.questions
            for question in questions:
                public_set.questions.remove(question)
            db.commit()

            qids = [question.id for question in questions]
            milvus.delete('_1', qids)
            return {'message': '设为私有'}

    # add maintainer
    # change owner

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='无法理解的操作')


@router.delete('/{sid}', responses={404: {'model': HTTPError}})
def delete_question_set(qid: int, db: Session = Depends(get_db), user_id: int = Depends(get_logged_user)):
    question_set = db.query(QuestionSet).get(qid)
    if question_set:
        if not guardian.can_delete_question_set(db.query(User).get(user_id), question_set):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
        milvus.drop_collection('_' + str(question_set.id))
        db.delete(question_set)
        db.commit()
        return {'ok': True}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QuestionSet not found')


@router.get('/', response_model=List[schemas.QuestionSetModel])
def get_question_sets(db: Session = Depends(get_db), user_id: int = Depends(get_logged_user)):
    user = db.query(User).get(user_id)
    if not user:
        return []  # return public
    if user.role == EnumRole.admin:
        return db.query(QuestionSet).all()
    return user.maintain.all()


@router.post('/', response_model=schemas.QuestionSetModel, status_code=status.HTTP_201_CREATED)
def create_question_set(args: schemas.QuestionSetCreate, db: Session = Depends(get_db),
                        user_id: int = Depends(get_logged_user)):
    name = args.name
    user = db.query(User).get(user_id)
    if not guardian.can_create_question_set(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
    qs = QuestionSet(name=name,
                     created_by=user,
                     owner=user,
                     modified_by=user)
    qs.maintainer.append(user)

    db.add(qs)
    db.commit()
    db.refresh(qs)

    collection_name = '_' + str(qs.id)
    milvus.create_collection(collection_name)  # 按理说这个名字的 collection 是不存在的

    return qs
