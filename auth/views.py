from authlib.integrations.base_client import OAuthError
from authlib.jose import jwt
from authlib.oidc.core import CodeIDToken
from flask import redirect, url_for, jsonify, request
from flask_login import login_required, login_user, logout_user

from ext import login_manager, oauth, db
from models import User
from . import auth_bp

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


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@auth_bp.route('/login/<int:uid>', methods=['GET'])
def login(uid):
    user = User.query.get(uid)
    if user:
        login_user(user)
        return 'Hello, {}!'.format(user.name)
    else:
        return '不存在！', 400


@auth_bp.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return oauth.jaccount.authorize_redirect(redirect_uri)


@auth_bp.route('/authorize')
def authorize():
    try:
        redirect_uri = request.args.get('redirect_uri')
        if redirect_uri:
            token = oauth.jaccount.authorize_access_token(redirect_uri=redirect_uri)
        else:
            token = oauth.jaccount.authorize_access_token()
    except OAuthError:
        return {'message': 'Bad argument!'}, 400
    claims = jwt.decode(token.get('id_token'),
                        oauth.jaccount.client_secret, claims_cls=CodeIDToken)
    account = claims['sub']
    name = account
    user = User.query.filter_by(name=name).first()
    if not user:
        user = User(name=name)
        db.session.commit()
    login_user(user)
    return jsonify({'account': account})


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return 'Logged out'  # redirect somewhere
