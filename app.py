from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

from commands import register_cli
from config import config


def create_app(config_name='test'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    CORS(app, supports_credentials=True)  # 允许跨域

    from ext import db, login_manager
    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager.init_app(app)

    from api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    from auth import auth_bp
    app.register_blueprint(auth_bp)

    from routes import main
    app.register_blueprint(main)

    register_cli(app)

    return app
