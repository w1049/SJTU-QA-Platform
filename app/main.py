import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .routes import router
from .utils import instrumentator
from .utils.logging import setup_logging

app = FastAPI()

app.include_router(router)

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

setup_logging()


@app.on_event("startup")
async def startup_event():
    logger.info('Server [{}] starting...', os.getpid())
    instrumentator.instrument(app).expose(app, include_in_schema=True)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info('Server [{}] shutdown.', os.getpid())
