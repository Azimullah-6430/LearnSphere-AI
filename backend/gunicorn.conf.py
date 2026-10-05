"""
Gunicorn configuration for LearnSphere AI on Render.
"""
import os

bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
threads = 2
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
