from typing import Union

from authlib.integrations.starlette_client import OAuth, OAuthError
from authlib.jose import jwt
from authlib.oidc.core import CodeIDToken
from fastapi import Request, APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.config import Config
from starlette.responses import RedirectResponse

from ..dependencies import get_db, get_user
from ..models import User
from ..schemas import HTTPError, UserModel

router = APIRouter(
    prefix='/api',
    tags=['auth'],
    responses={404: {'description': 'Not found'}}
)

config = Config('.env')
oauth = OAuth(config)

oauth.register(
    name='jaccount',
    access_token_url='https://jaccount.sjtu.edu.cn/oauth2/token',
    authorize_url='https://jaccount.sjtu.edu.cn/oauth2/authorize',
    api_base_url='https://api.sjtu.edu.cn/',
    client_kwargs={
        'scope': 'openid',
        'token_endpoint_auth_method': 'client_secret_basic',
        'token_placement': 'header'
    }
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
async def login(request: Request):  # 禁止重复登录？
    redirect_uri = request.url_for('auth')
    return await oauth.jaccount.authorize_redirect(request, redirect_uri)


@router.get('/auth')
async def auth(request: Request, redirect_uri: Union[str, None] = None, db: Session = Depends(get_db)):
    try:
        if redirect_uri:
            token = await oauth.jaccount.authorize_access_token(request, redirect_uri=redirect_uri)
        else:
            token = await oauth.jaccount.authorize_access_token(request)
    except OAuthError:
        raise HTTPException(status_code=400, detail='Bad Arguments')
    claims = jwt.decode(token.get('id_token'),
                        oauth.jaccount.client_secret, claims_cls=CodeIDToken)
    account = claims['sub']
    name = account
    user = db.query(User).filter_by(name=name).first()
    if not user:
        user = User(name=name)
        db.commit()
        db.refresh(user)
    request.session['user_id'] = user.id
    return {'account': account}


@router.get('/me', response_model=UserModel, responses={401: {'model': HTTPError}})
def me(user_id: int = Depends(get_user), db: Session = Depends(get_db)):
    return db.query(User).get(user_id)


@router.get('/logout')
async def logout(request: Request):
    request.session.pop('user_id', None)
    return RedirectResponse(url='/')
