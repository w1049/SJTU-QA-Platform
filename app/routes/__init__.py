from fastapi import APIRouter

from . import auth, question, question_set

router = APIRouter()

router.include_router(question.router)
router.include_router(question_set.router)
router.include_router(auth.router)
