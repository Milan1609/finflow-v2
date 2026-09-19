"""WSGI entrypoint for Render/Gunicorn.

Render start command can use either:
  gunicorn --bind 0.0.0.0:$PORT app:app
or:
  gunicorn --bind 0.0.0.0:$PORT wsgi:app
"""

from app import app