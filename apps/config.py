import os
import random
import string


class Config(object):
    basedir = os.path.abspath(os.path.dirname(__file__))

    # Set up the App SECRET_KEY
    SECRET_KEY = os.getenv('cyber', None)
    if not SECRET_KEY:
        SECRET_KEY = ''.join(random.choice(string.ascii_lowercase) for i in range(32))

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    USE_SQLITE  = True

    # # PostgreSQL Configuration
    # For local Database
    DB_ENGINE = 'postgresql'
    DB_USERNAME = 'postgres'
    DB_PASS = 'virus'
    DB_HOST = 'localhost'
    DB_PORT = '5432'
    DB_NAME = 'postgres'
    
    # For Supabase database (Online)
    # DB_ENGINE = 'postgresql'
    # DB_USERNAME = 'postgres.awgqqxtyhkvcstfkikan'
    # DB_PASS = 'VirusDB25625'
    # DB_HOST = 'aws-0-us-west-1.pooler.supabase.com'
    # DB_PORT = '5432'
    # DB_NAME = 'postgres'

    if DB_ENGINE and DB_NAME and DB_USERNAME:

        try:

            SQLALCHEMY_DATABASE_URI = '{}://{}:{}@{}:{}/{}'.format(
                DB_ENGINE,
                DB_USERNAME,
                DB_PASS,
                DB_HOST,
                DB_PORT,
                DB_NAME
            ) 

            USE_SQLITE  = False

        except Exception as e:

            print('> Error: DBMS Exception: ' + str(e) )
            print('> Fallback to SQLite ')

    if USE_SQLITE:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'db.sqlite3') 
        print("Creating Sqlite DB: ", SQLALCHEMY_DATABASE_URI)

    # Assets Management
    ASSETS_ROOT = os.getenv('ASSETS_ROOT', '/static/assets')

    # Profile Image Upload Settings
    USER_FOLDER = os.path.join(basedir, 'user_data')
    PROFILE_IMAGE_NAME = 'profile_image.jpg'
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    # User upload folders settings'
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov'}
    ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'aac'}

    # Security
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 3600

class ProductionConfig(Config):
    DEBUG = True
    # Additional production-specific settings if needed


class DebugConfig(Config):
    DEBUG = True

# Load all possible configurations
config_dict = {
    'Production': ProductionConfig,
    'Debug': DebugConfig
}
