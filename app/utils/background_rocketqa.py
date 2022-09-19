import json
from typing import List

from sqlalchemy.orm import Session

from app.models.models import Question
from app.utils import rocketqa, milvus
from app.utils.database import SessionLocal


async def create(titles, contents, questions: List[Question], sid, public):
    emb_arrays = await rocketqa.async_get_paras(titles, contents)
    with SessionLocal() as db:
        for question, emb_array in zip(questions, emb_arrays):
            question.embedding = json.dumps(emb_array)
        db.commit()
    qids = [question.id for question in questions]
    milvus.insert('_' + str(sid), emb_arrays, qids)
    if public:
        milvus.insert('_1', emb_arrays, qids)
