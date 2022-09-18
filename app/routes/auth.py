from typing import Optional

from authlib.integrations.starlette_client import OAuth, OAuthError
from authlib.jose import jwt
from authlib.oidc.core import CodeIDToken
from fastapi import Request, APIRouter, Depends, HTTPException, Response
from loguru import logger
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from starlette.status import HTTP_200_OK

from ..config import settings
from ..dependencies import get_db, get_logged_user
from ..models.models import User
from ..models.schemas import HTTPError
from ..models.schemas.user import UserDetail

router = APIRouter(
    prefix='/api',
    tags=['auth'],
    responses={404: {'description': 'Not found'}}
)

oauth = OAuth()

oauth.register(
    name='jaccount',
    client_id=settings.jaccount_client_id,
    client_secret=settings.jaccount_client_secret,
    access_token_url='https://jaccount.sjtu.edu.cn/oauth2/token',
    authorize_url='https://jaccount.sjtu.edu.cn/oauth2/authorize',
    api_base_url='https://api.sjtu.edu.cn/',
    client_kwargs={'scope': 'basic'}
)


@router.get('/login_id/{user_id}', description='测试用登录')
async def login_id(request: Request, user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    else:
        request.session['user_id'] = user.id
        return 'Hello, {} of {}!'.format(user.name, user.institution)


@router.get('/login')
async def login(request: Request, redirect_uri: Optional[str] = None):  # 禁止重复登录？
    if not redirect_uri:
        redirect_uri = request.url_for('auth')
    return await oauth.jaccount.authorize_redirect(request, redirect_uri)


@router.get('/auth', response_model=UserDetail,
            openapi_extra={
                "parameters": [
                    {
                        "required": True,
                        "schema": {"title": "Code", "type": "string"},
                        "name": "code",
                        "in": "query"
                    },
                    {
                        "required": True,
                        "schema": {"title": "State", "type": "string"},
                        "name": "state",
                        "in": "query"
                    },
                    {
                        "required": False,
                        "schema": {"title": "Redirect Uri", "type": "string"},
                        "name": "redirect_uri",
                        "in": "query"
                    }
                ]
            },
            description="有redirect_uri时，返回307 redirect"
            )
async def auth(request: Request, redirect_uri: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        token = await oauth.jaccount.authorize_access_token(request)
    except OAuthError:
        raise HTTPException(status_code=400, detail='Bad Arguments')
    claims = jwt.decode(token.get('id_token'),
                        oauth.jaccount.client_secret, claims_cls=CodeIDToken)
    account = claims['sub']
    name = account
    user = db.query(User).filter_by(name=name).with_for_update().first()
    if not user:
        user = User(name=name)
        db.add(user)
        db.commit()
        logger.info('New user: {}', user)
    request.session['user_id'] = user.id
    if redirect_uri:
        return RedirectResponse(redirect_uri)
    return user


@router.get('/me', response_model=UserDetail, responses={401: {'model': HTTPError}})
def me(user_id: int = Depends(get_logged_user), db: Session = Depends(get_db)):
    return db.query(User).get(user_id)


@router.get('/logout')
async def logout(request: Request):
    request.session.pop('user_id', None)
    return Response(status_code=HTTP_200_OK)
