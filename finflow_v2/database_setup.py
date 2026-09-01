from pathlib import Path

from sqlalchemy import event


DATABASE_DIRECTORY = Path(__file__).resolve().parent / 'database'


def _read_sql(*path_parts):
    return (DATABASE_DIRECTORY.joinpath(*path_parts)).read_text(encoding='utf-8')


def sqlite_programmability_sql():
    return _read_sql('sqlite', '001_programmability.sql')


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')
    cursor.close()


def _configure_sqlite(engine):
    if not event.contains(engine, 'connect', _enable_sqlite_foreign_keys):
        event.listen(engine, 'connect', _enable_sqlite_foreign_keys)
    with engine.connect() as connection:
        connection.exec_driver_sql('PRAGMA foreign_keys = ON')


def _execute_sqlite_script(engine, script):
    raw_connection = engine.raw_connection()
    try:
        raw_connection.driver_connection.executescript(script)
        raw_connection.commit()
    finally:
        raw_connection.close()


def _execute_postgresql_script(engine, script):
    with engine.begin() as connection:
        connection.exec_driver_sql(script)


def initialize_database(database):
    engine = database.engine
    dialect = engine.dialect.name

    if dialect == 'postgresql':
        _execute_postgresql_script(engine, _read_sql('postgresql', '001_schema.sql'))
        database.create_all()
        with engine.begin() as connection:
            connection.exec_driver_sql('CREATE SCHEMA IF NOT EXISTS finflow;')
            connection.exec_driver_sql('SET search_path TO finflow, public;')
        _execute_postgresql_script(engine, _read_sql('postgresql', '002_programmability.sql'))
        with engine.begin() as connection:
            connection.exec_driver_sql('SET search_path TO finflow, public;')
            connection.exec_driver_sql('CALL rebuild_account_balances()')
        return True

    database.create_all()
    if dialect == 'sqlite':
        _configure_sqlite(engine)
        _execute_sqlite_script(engine, sqlite_programmability_sql())
        return True

    return False


if __name__ == '__main__':
    from app import app, db

    with app.app_context():
        enabled = initialize_database(db)
        print(f'Database setup complete. Managed balance triggers enabled: {enabled}')
