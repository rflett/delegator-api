from app import app
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine(f"postgresql://{app.config['DB_USER']}:{app.config['DB_PASS']}@{app.config['DB_HOST']}/etemt")

DBSession = sessionmaker(bind=engine)

DBBase = declarative_base()
