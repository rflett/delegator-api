from contextlib import contextmanager

from aws_xray_sdk.ext.flask_sqlalchemy.query import XRayFlaskSqlAlchemy

db = XRayFlaskSqlAlchemy()


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    try:
        yield db.session
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
