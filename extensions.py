from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
# from flask_migrate import Migrate

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
# migrate = Migrate()

def init_extensions(app):
    """Initialize Flask extensions with the application"""
    db.init_app(app)
    login_manager.init_app(app)
    # migrate.init_app(app, db)

    # Configure login manager
    login_manager.login_view = 'login'
    login_manager.login_message_category = 'info'

    return app
