import os
from datetime import timedelta

class Config:
    """Base Configuration"""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Upload Settings
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    
    # ML Model Settings
    BERT_MODEL = 'bert-base-uncased'
    EVALUATION_ACCURACY_THRESHOLD = 0.95
    PLAGIARISM_SIMILARITY_THRESHOLD = 0.85

class DevelopmentConfig(Config):
    """Development Configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/learnsphere_ai'
    )
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """Production Configuration"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_ECHO = False

class TestingConfig(Config):
    """Testing Configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=5)