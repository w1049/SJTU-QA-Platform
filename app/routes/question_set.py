import json
import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Response
from loguru import logger
from sqlalchemy.orm import Session
from starlette.status import HTTP_200_OK

from ..dependencies import get_db, get_logged_user
from ..models.models import QuestionSet, Question, User, EnumRole, EnumPermission
from ..models.schemas import HTTPError
from ..models.schemas.question_set import QuestionSetDetail, QuestionSetUpdate, QuestionSetList, QuestionSetCreate, \
    QuestionSetCreated
from ..utils import milvus, guardian

router = APIRouter(
    prefix='/api/question_set',
    tags=['question_set'],
    responses={401: {'model': HTTPError}, 403: {'model': HTTPError}}
)


@router.get('/{sid}', response_model=QuestionSetDetail, responses={404: {'model': HTTPError}})
def get_question_set(sid: int, db: Session = Depends(get_db), user_id: int = Depends(get_logged_user)):
    question_set = db.query(QuestionSet).get(sid)
    if question_set:
        if not guardian.can_get_question_set(db.query(User).get(user_id), question_set):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
        ret_set = QuestionSetDetail.from_orm(question_set)
        ret_set.question_ids = [qid[0] for qid in question_set.questions.with_entities(Question.id).all()]
        return ret_set
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QuestionSet not found')


@router.put('/{sid}', responses={404: {'model': HTTPError}, 400: {'model': HTTPError}})
def update_question_set(sid: int, args: QuestionSetUpdate, db: Session = Depends(get_db),
                        user_id: int = Depends(get_logged_user)):
    append_qids = args.append_qids
    remove_qids = args.remove_qids

    qs = db.query(QuestionSet).get(sid)
    if qs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QuestionSet not found')

    if not guardian.can_modify_question_set(db.query(User).get(user_id), qs):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')

    public = qs.permission == EnumPermission.public

    message = []

    if append_qids:
        start = time.time()
        questions = db.query(Question).filter(Question.id.in_(append_qids)).all()
        if len(append_qids) != len(questions):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='??????ID?????????')
        qs.questions.extend(questions)
        qs.modified_by_id = user_id
        if public:
            public_set = db.query(QuestionSet).get(1)
            public_set.questions.extend(questions)
        try:
            db.flush()
        except Exception as e:
            logger.debug(e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='????????????????????????')

        embeddings = [json.loads(question.embedding) for question in questions]
        append_qids = [question.id for question in questions]  # ?????????????????????????????????qids

        end = time.time()
        logger.debug('sql time: {}s', end - start)

        milvus.insert('_' + str(sid), embeddings, append_qids)
        if public:
            milvus.insert('_1', embeddings, append_qids)

        end2 = time.time()
        logger.debug('milvus time: {}s', end2 - end)
        message.append('?????????????????????')

    if remove_qids:
        questions = db.query(Question).filter(Question.id.in_(remove_qids)).all()
        if len(remove_qids) != len(questions):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='??????ID?????????')
        for question in questions:
            qs.questions.remove(question)
        qs.modified_by_id = user_id
        if public:
            public_set = db.query(QuestionSet).get(1)
            for question in questions:
                public_set.questions.remove(question)
        try:
            db.flush()
        except Exception as e:
            logger.debug(e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='??????????????????')

        milvus.delete('_' + str(sid), remove_qids)
        if public:
            milvus.delete('_1', remove_qids)
        message.append('?????????????????????')

    if args.name:
        qs.name = args.name
        qs.modified_by_id = user_id
        db.flush()
        message.append('???????????????')

    if args.description:
        qs.description = args.description
        qs.modified_by_id = user_id
        db.flush()
        message.append('?????????????????????')

    if args.permission == EnumPermission.public.value:
        if qs.permission != EnumPermission.public:
            qs.permission = EnumPermission.public
            qs.modified_by_id = user_id
            public_set = db.query(QuestionSet).get(1)
            questions = qs.questions
            public_set.questions.extend(questions)
            db.flush()

            embeddings = [json.loads(question.embedding) for question in questions]
            qids = [question.id for question in questions]
            milvus.insert('_1', embeddings, qids)
            message.append('????????????')

    if args.permission == EnumPermission.private.value:
        if qs.permission != EnumPermission.private:
            qs.permission = EnumPermission.private
            qs.modified_by_id = user_id
            public_set = db.query(QuestionSet).get(1)
            questions = qs.questions
            for question in questions:
                public_set.questions.remove(question)
            db.flush()

            qids = [question.id for question in questions]
            milvus.delete('_1', qids)
            message.append('????????????')

    # add maintainer
    # change owner
    if len(message) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='?????????????????????')
    else:
        db.commit()
        return Response(status_code=HTTP_200_OK)


@router.delete('/{sid}', responses={404: {'model': HTTPError}})
def delete_question_set(sid: int, db: Session = Depends(get_db), user_id: int = Depends(get_logged_user)):
    question_set = db.query(QuestionSet).get(sid)
    if question_set:
        if not guardian.can_delete_question_set(db.query(User).get(user_id), question_set):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
        milvus.drop_collection('_' + str(question_set.id))
        db.delete(question_set)
        db.commit()
        return Response(status_code=HTTP_200_OK)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QuestionSet not found')


@router.get('/', response_model=List[QuestionSetList])
def get_question_sets(db: Session = Depends(get_db), user_id: int = Depends(get_logged_user)):
    user = db.query(User).get(user_id)
    if not user:
        return []  # return public
    if user.role == EnumRole.admin:
        return db.query(QuestionSet).all()
    return user.maintain.all()


@router.post('/', response_model=QuestionSetCreated, status_code=status.HTTP_201_CREATED)
def create_question_set(args: QuestionSetCreate, db: Session = Depends(get_db),
                        user_id: int = Depends(get_logged_user)):
    user = db.query(User).get(user_id)
    if not guardian.can_create_question_set(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
    qs = QuestionSet(name=args.name,
                     description=args.description,
                     permission=args.permission,
                     created_by=user,
                     owner=user,
                     modified_by=user)
    qs.maintainer.append(user)

    db.add(qs)
    db.commit()

    collection_name = '_' + str(qs.id)
    milvus.create_collection(collection_name)  # ???????????????????????? collection ???????????????

    return qs
