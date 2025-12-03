import os
from urllib.parse import quote_plus
from datetime import timedelta

class Config:
    # Application Settings
    FLASK_APP = os.environ.get('FLASK_APP', 'app.py')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY and FLASK_ENV == 'production':
        raise ValueError('SECRET_KEY environment variable is required in production')
    
    # Database configuration
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///tour.db')
    
    # Fix for Render.com PostgreSQL (postgres:// -> postgresql://)
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    # Convert relative sqlite path to absolute (for local development)
    if DATABASE_URL.startswith('sqlite:///') and not os.path.isabs(DATABASE_URL[10:]):
        DATABASE_URL = f'sqlite:///{os.path.abspath(DATABASE_URL[10:])}'
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.environ.get('SQLALCHEMY_ECHO', 'false').lower() == 'true'
    
    # Security settings
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_SAMESITE = 'Lax'  # Helps prevent CSRF
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    
    # Rate limiting
    RATELIMIT_DEFAULT = '200 per day;50 per hour'
    RATELIMIT_STORAGE_URL = 'memory://'
    
    # Upload settings
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB default
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    
    # Email settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', MAIL_USERNAME)
    
    # API keys
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    if not GEMINI_API_KEY and FLASK_ENV == 'production':
        raise ValueError('GEMINI_API_KEY environment variable is required in production')
        
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    if not OPENROUTER_API_KEY and FLASK_ENV == 'production':
        raise ValueError('OPENROUTER_API_KEY environment variable is required in production')
        
    PUBLIC_GOOGLE_MAPS_KEY = os.environ.get('PUBLIC_GOOGLE_MAPS_KEY', '')
    
    # Internationalization
    BABEL_DEFAULT_LOCALE = os.environ.get('BABEL_DEFAULT_LOCALE', 'en')
    BABEL_SUPPORTED_LOCALES = os.environ.get('BABEL_SUPPORTED_LOCALES', 'en,hi,kn').split(',')
    BABEL_TRANSLATION_DIRECTORIES = 'translations'
    
    # Password reset token expiration (in seconds)
    PASSWORD_RESET_EXPIRATION = int(os.environ.get('PASSWORD_RESET_EXPIRATION', 3600))  # 1 hour
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @staticmethod
    def init_app(app):
        """Initialize configuration for the Flask app"""
        # Create upload folder if it doesn't exist
        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)
            
        # Set up logging
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Disable SQLAlchemy logging unless in debug mode
        if not app.debug:
            logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        
        # Log to file
        file_handler = RotatingFileHandler(
            'app.log',
            maxBytes=10240,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
        file_handler.setLevel(getattr(logging, Config.LOG_LEVEL))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        app.logger.info('Application startup')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    

class ProductionConfig(Config):
    """Production configuration"""
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log to syslog
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
