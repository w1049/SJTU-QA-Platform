import flask_login
from flask_login import login_required

from ext import login_manager
from models import User
from . import auth_bp


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@auth_bp.route('/login/<int:uid>', methods=['GET'])
def login(uid):
    user = User.query.get(uid)
    if user:
        flask_login.login_user(user)
        return 'Hello, {}!'.format(user.name)
    else:
        return '不存在！', 400


@auth_bp.route('/logout')
@login_required
def logout():
    flask_login.logout_user()
    return 'Logged out'  # redirect somewhere
