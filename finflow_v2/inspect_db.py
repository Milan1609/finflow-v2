from app import app, db
from sqlalchemy import inspect

with app.app_context():
    insp = inspect(db.engine)
    print('tables=', insp.get_table_names())
