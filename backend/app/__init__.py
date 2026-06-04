from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow

db = SQLAlchemy()
jwt = JWTManager()
ma = Marshmallow()

def create_app(config_name='development'):
    app = Flask(__name__)
    
    # Load Configuration
    if config_name == 'development':
        from app.config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)
    elif config_name == 'production':
        from app.config import ProductionConfig
        app.config.from_object(ProductionConfig)
    
    # Initialize Extensions
    db.init_app(app)
    jwt.init_app(app)
    ma.init_app(app)
    CORS(app)
    
    # Register Blueprints
    with app.app_context():
        from app.routes import auth, teacher, student, evaluation, plagiarism, analytics
        
        app.register_blueprint(auth.bp)
        app.register_blueprint(teacher.bp)
        app.register_blueprint(student.bp)
        app.register_blueprint(evaluation.bp)
        app.register_blueprint(plagiarism.bp)
        app.register_blueprint(analytics.bp)
        
        # Create tables
        db.create_all()
    
    return app