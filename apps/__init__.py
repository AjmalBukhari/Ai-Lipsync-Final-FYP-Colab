from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade, migrate
from importlib import import_module
import os
import subprocess

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def register_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)


def register_blueprints(app):
    for module_name in ('authentication', 'home'):
        module = import_module('apps.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)


def configure_database(app):
    @app.before_request
    def initialize_database():
        # Check if migrations directory exists, if not create it
        if not os.path.exists('migrations'):
            print('> Initializing migrations directory...')
            subprocess.call(['flask', 'db', 'init'])  # Initializes the migrations directory

        # Create initial database if it does not exist
        try:
            db.create_all()
        except Exception as e:
            print('> Error: DBMS Exception: ' + str(e))

            # Fallback to SQLite
            basedir = os.path.abspath(os.path.dirname(__file__))
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite3')
            print('> Fallback to SQLite ')
            db.create_all()

    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()


def create_app(config):
    app = Flask(__name__)
    
    app.config.from_object(config)

    register_extensions(app)

    register_blueprints(app)
    configure_database(app)

    return app
