"""
WSGI entry point for Gunicorn on Render
"""
import sys
import os

# Add finflow_v2 to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'finflow_v2'))

from finflow_v2.app import app

if __name__ == '__main__':
    app.run()
