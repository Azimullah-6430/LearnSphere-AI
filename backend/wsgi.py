"""
LearnSphere AI - WSGI Entry Point for Gunicorn / Render Deployment
"""
from server import app

if __name__ == "__main__":
    app.run()
