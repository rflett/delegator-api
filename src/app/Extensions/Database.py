from contextlib import contextmanager

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    try:
        yield db.session
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
